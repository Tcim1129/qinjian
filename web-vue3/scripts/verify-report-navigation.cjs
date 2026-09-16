// Isolated sample/browser-contract checks; never uses the user's login or writes to a backend.
const assert = require('node:assert/strict')
const path = require('node:path')
const { chromium } = require(process.env.QJ_PLAYWRIGHT_MODULE || 'playwright')
;(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' })
  try {
    const context = await browser.newContext()
    await context.addInitScript(() => sessionStorage.setItem('qj_token', 'demo-mode'))
    await context.route('**/*', route => {
      const url = new URL(route.request().url())
      return url.hostname === '127.0.0.1' && !url.pathname.startsWith('/api/') ? route.continue() : route.abort()
    })
    const page = await context.newPage()
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    for (const width of [1365, 390]) {
      await page.setViewportSize({ width, height: 950 })
      await page.goto('http://127.0.0.1:3003/report')
      await page.waitForLoadState('networkidle')
      await page.locator('.report-paper').waitFor()
      assert.equal(await page.locator('.report-trend-legend').count(), 0)
      assert.equal(await page.locator('.report-trend-footer').count(), 0)
      const daily = await page.locator('.report-paper__intro h3').innerText()
      for (const label of ['周报', '月报', '日报']) {
        await page.getByRole('button', { name: label, exact: true }).click()
        assert.equal(await page.locator('.report-meta span').first().innerText(), label)
        assert.equal(await page.locator('.report-history h3').innerText(), `查看往期${label}`)
        if (label !== '日报') assert.notEqual(await page.locator('.report-paper__intro h3').innerText(), daily)
        const original = await page.locator('.report-paper__intro h3').innerText()
        await page.locator('.history-item').nth(1).click()
        assert.notEqual(await page.locator('.report-paper__intro h3').innerText(), original)
        assert.equal(await page.locator('.history-item[aria-pressed="true"]').count(), 1)
        assert.equal(await page.locator('.history-item').nth(1).getAttribute('aria-pressed'), 'true')
      }
      const options = await page.locator('#report-pair option').evaluateAll(nodes => nodes.map(node => ({ value: node.value, label: node.textContent })))
      await page.getByLabel('查看关系').selectOption(options[0].value)
      const name = options[0].label.split(' · ')[0]
      assert.ok((await page.locator('.report-meta').innerText()).includes(name))
      assert.ok((await page.locator('.report-paper__intro h3').innerText()).includes(name))
      assert.equal(await page.locator('.history-item').first().getAttribute('aria-pressed'), 'true')
      assert.ok((await page.locator('.report-trend__label').allTextContents()).every(label => /\d+\/\d+/.test(label)))
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
      await page.screenshot({ path: path.resolve(`output/playwright/report-navigation-${width}.png`), fullPage: true })
      await page.goto('http://127.0.0.1:3003/discover')
      await page.waitForLoadState('networkidle')
      await page.getByRole('heading', { name: '全部功能', exact: true }).waitFor()
      assert.equal(await page.locator('.discover-page').getByText('理解', { exact: true }).count(), 0)
      const color = await page.locator('.discover-entry[href="/alignment"] span').evaluate(el => getComputedStyle(el).color)
      assert.equal(color, 'rgb(67, 110, 174)')
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
      await page.screenshot({ path: path.resolve(`output/playwright/discover-navigation-${width}.png`), fullPage: true })
      console.log(`${width}px: sample types, complete history selection, direct relationship selection, dates, color and overflow passed`)
    }
    await context.close()
    const real = await browser.newContext()
    await real.addInitScript(() => sessionStorage.setItem('qj_token', 'report-contract-test'))
    const requests = []
    await real.route('**/*', async route => {
      const url = new URL(route.request().url())
      if (url.hostname !== '127.0.0.1') return route.abort()
      if (!url.pathname.startsWith('/api/')) return route.continue()
      requests.push(url.pathname + url.search)
      let body = []
      if (url.pathname.endsWith('/auth/me')) body = { id: 'report-tester', nickname: '测试', product_prefs: {} }
      if (url.pathname.endsWith('/pairs/me')) body = [{ id: 'pair-one', status: 'active', partner_nickname: '甲' }, { id: 'pair-two', status: 'active', partner_nickname: '乙' }]
      const type = url.searchParams.get('report_type') || 'daily'
      if (url.pathname.endsWith('/reports/latest')) body = { id: `${type}-latest`, report_type: type, report_date: '2026-09-07', status: 'completed', health_score: null, content: { insight: `${type}正文` } }
      if (url.pathname.endsWith('/reports/history')) body = [
        { id: `${type}-old`, report_type: type, report_date: '2026-09-06', created_at: '2026-09-06T12:00:00Z', status: 'completed', health_score: 0, content: { insight: '历史正文' } },
        { id: `${type}-older`, report_type: type, report_date: '2026-09-06', created_at: '2026-09-06T01:00:00Z', status: 'completed', health_score: 3 },
      ]
      if (url.pathname.endsWith('/reports/trend')) body = { trend: [] }
      await route.fulfill({ json: body })
    })
    const rp = await real.newPage()
    rp.on('pageerror', error => errors.push(error.message))
    await rp.goto('http://127.0.0.1:3003/report')
    await rp.waitForLoadState('networkidle')
    await rp.getByRole('button', { name: '周报', exact: true }).click()
    await rp.getByRole('heading', { name: 'weekly正文', exact: true }).waitFor()
    assert.ok(requests.some(url => url.includes('report_type=weekly') && url.includes('/reports/history')))
    assert.equal(await rp.locator('.report-score small').innerText(), '暂无评分')
    assert.equal(await rp.locator('.history-item').count(), 1)
    await rp.locator('.history-item').click()
    await rp.getByRole('heading', { name: '历史正文', exact: true }).waitFor()
    assert.equal(await rp.locator('.report-score > span').innerText(), '0')
    await Promise.all([
      rp.waitForResponse(response => response.url().includes('/reports/latest?pair_id=pair-two')),
      rp.getByLabel('查看关系').selectOption('pair-two'),
    ])
    assert.ok(requests.some(url => url.includes('pair_id=pair-two') && url.includes('report_type=weekly')), JSON.stringify(requests))
    await rp.getByLabel('查看关系').selectOption('')
    assert.equal(await rp.getByRole('button', { name: '周报', exact: true }).isDisabled(), true)
    assert.equal(await rp.getByRole('button', { name: '日报', exact: true }).getAttribute('class'), 'active')
    assert.deepEqual(errors, [])
    console.log('Real-mode mocked API contract: scoped report type, missing score, deduplicated history, solo guard passed. Page errors: 0.')
  } finally { await browser.close() }
})().catch(error => { console.error(error); process.exitCode = 1 })
