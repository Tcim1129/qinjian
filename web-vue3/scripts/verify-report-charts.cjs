// Layout-only checks with isolated test responses. Does not use the running user's session or backend.
const assert = require('node:assert/strict')
const path = require('node:path')
const { chromium } = require(process.env.QJ_PLAYWRIGHT_MODULE || 'playwright')

;(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' })
  try {
    const context = await browser.newContext()
    const page = await context.newPage()
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    await context.addInitScript(() => sessionStorage.setItem('qj_token', 'chart-layout-test-only'))
    let scores = [80, 81, 80, 82, 82, 81]
    const dimensions = ['沟通与表达', '信任', '缓和', '共同愿景', '活力'].map((label, i) => ({ id: `dim-${i}`, label, score: [8, 82, 85, 76, 90][i] }))
    await context.route('**/*', async route => {
      const url = new URL(route.request().url())
      if (url.hostname !== '127.0.0.1') return route.abort()
      if (!url.pathname.startsWith('/api/')) return route.continue()
      let body = []
      if (url.pathname.endsWith('/auth/me')) body = { id: 'chart-tester', nickname: '图表测试', product_prefs: {} }
      if (url.pathname.endsWith('/pairs/me')) body = [{ id: 'chart-pair', status: 'active', partner_nickname: '测试关系' }]
      if (url.pathname.endsWith('/reports/latest')) body = { id: 'chart-report', status: 'completed', health_score: 81, content: { insight: '图表排版验证', dimensions } }
      if (url.pathname.endsWith('/reports/trend')) body = { trend: scores.map((score, i) => ({ date: `2026-09-${String(i + 1).padStart(2, '0')}`, score })) }
      await route.fulfill({ json: body })
    })

    async function checkLayout(width, dense = false) {
      await page.setViewportSize({ width, height: 950 })
      await page.goto('http://127.0.0.1:3003/report')
      await page.getByRole('heading', { name: '图表排版验证', exact: true }).waitFor()
      await page.locator('.report-trend__score').first().waitFor()
      await page.evaluate(() => document.fonts.ready)
      const result = await page.evaluate(() => {
        const radar = document.querySelector('.report-radar')
        const viewBox = radar.viewBox.baseVal
        const labels = [...radar.querySelectorAll('text')]
        const unclipped = labels.every(text => { const b = text.getBBox(); return b.x >= 0 && b.y >= 0 && b.x + b.width <= viewBox.width && b.y + b.height <= viewBox.height })
        const polygon = radar.querySelector('.report-radar__grid--outer').getAttribute('points').split(' ').map(pair => pair.split(',').map(Number))
        function inside(x, y) {
          let hit = false
          for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
            const [xi, yi] = polygon[i], [xj, yj] = polygon[j]
            if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) hit = !hit
          }
          return hit
        }
        const outside = labels.every(text => { const b = text.getBBox(); return [[b.x,b.y],[b.x+b.width,b.y],[b.x,b.y+b.height],[b.x+b.width,b.y+b.height]].every(([x,y]) => !inside(x,y)) })
        const boxes = selector => [...document.querySelectorAll(selector)].map(el => el.getBoundingClientRect())
        const values = boxes('.report-trend__score'), ticks = boxes('.report-trend__tick')
        const overlap = (a,b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom
        const trendClear = values.every(value => ticks.every(tick => !overlap(value,tick))) && values.every((value, i) => values.slice(i+1).every(other => !overlap(value,other)))
        const scroll = document.querySelector('.report-trend-scroll')
        return {
          unclipped, outside, trendClear,
          pageFits: document.documentElement.scrollWidth <= innerWidth,
          repeatedList: document.querySelectorAll('.report-dimension-list').length,
          scoreFont: parseFloat(getComputedStyle(radar.querySelector('.report-radar__value')).fontSize) * radar.getBoundingClientRect().width / viewBox.width,
          localScroll: scroll.scrollWidth > scroll.clientWidth,
        }
      })
      assert.ok(result.unclipped, `radar text clipped at ${width}px`)
      assert.ok(result.outside, `radar label inside polygon at ${width}px`)
      assert.ok(result.trendClear, `trend annotations overlap at ${width}px`)
      assert.ok(result.pageFits, `page overflow at ${width}px`)
      assert.equal(result.repeatedList, 0)
      assert.ok(result.scoreFont >= 18, `score too small at ${width}px`)
      if (dense && width === 390) assert.ok(result.localScroll)
      if (!dense) await page.locator('.report-visual-grid').screenshot({ path: path.resolve(`output/playwright/report-charts-${width}.png`) })
      console.log(`${width}px ${dense ? '14 points' : 'close scores'}: labels outside, no clipping or overlaps, readable score font ${result.scoreFont.toFixed(1)}px`)
    }
    await checkLayout(1365)
    await checkLayout(390)
    scores = Array.from({ length: 14 }, (_, i) => 80 + i / 10)
    await checkLayout(390, true)
    assert.deepEqual(errors, [])
    console.log('Chart rendering errors: 0. Test responses only; no backend writes.')
  } finally { await browser.close() }
})().catch(error => { console.error(error); process.exitCode = 1 })
