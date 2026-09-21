// Isolated browser contract checks; every API request is intercepted, no real data or model calls.
const assert = require('node:assert/strict')
const path = require('node:path')
const { chromium } = require(process.env.QJ_PLAYWRIGHT_MODULE || 'playwright')

;(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' })
  try {
    const context = await browser.newContext({ viewport: { width: 1365, height: 950 } })
    const errors = []
    const page = await context.newPage()
    page.on('pageerror', error => errors.push(error.message))
    await context.addInitScript(() => { sessionStorage.setItem('qj_token', 'audit-test-only'); localStorage.setItem('qj_current_pair', 'pair-a') })
    const pairs = ['a', 'b'].map(id => ({ id: `pair-${id}`, status: 'active', type: 'couple', partner_nickname: id === 'a' ? '测试关系甲' : '测试关系乙' }))
    let releaseLate, lateDoneResolve
    const lateDone = new Promise(resolve => { lateDoneResolve = resolve })
    let generating = false, reportReads = 0, confirmationCount = 0, saved = false
    const proposal = { proposal_id: 'suggestion-1', title: '饭后散步十分钟', description: '不赶时间的时候再出门。', due_date: '2026-09-07', requires_confirmation: true }
    const message = () => ({ id: 'message-1', role: 'assistant', content: '可以从一件小事开始，要加入明天的安排吗？', payload: { task_proposals: [{ ...proposal, ...(saved ? { confirmed_task_id: 'task-1' } : {}) }] } })
    const report = (pair, type, status = 'completed') => ({ id: `${pair}-${type}`, status, report_type: type, report_date: '2026-09-06', health_score: 70, content: { insight: `${pair === 'pair-a' ? '甲' : '乙'}的${type === 'daily' ? '日报' : '周报'}${generating && status === 'completed' ? '已更新' : ''}`, recommendations: ['约好聊天时间'] } })
    await context.route('**/*', async route => {
      const url = new URL(route.request().url())
      if (url.hostname !== '127.0.0.1') return route.abort()
      if (!url.pathname.startsWith('/api/')) return route.continue()
      let body = {}
      const method = route.request().method(), p = url.pathname.replace('/api/v1', '')
      if (p === '/auth/me') body = { id: 'audit-user', nickname: '界面验证账号', email: 'audit@example.test', product_prefs: {} }
      else if (p === '/pairs/me') body = pairs
      else if (p.includes('notifications')) body = []
      else if (p === '/reports/latest') {
        const pair = url.searchParams.get('pair_id'), type = url.searchParams.get('report_type')
        if (pair === 'pair-a' && type === 'weekly') {
          await new Promise(resolve => { releaseLate = resolve })
          body = report(pair, type)
          await route.fulfill({ json: body }); lateDoneResolve(); return
        }
        const status = generating && ++reportReads < 3 ? 'pending' : 'completed'
        body = report(pair, type, status)
      } else if (p === '/reports/history') body = []
      else if (p === '/reports/trend') body = { trend: [] }
      else if (method === 'POST' && p.startsWith('/reports/')) { generating = true; reportReads = 0; body = report('pair-b', 'weekly', 'pending') }
      else if (p === '/agent/sessions' && method === 'POST') body = { session_id: 'session-1' }
      else if (p.endsWith('/messages')) body = saved ? [message()] : []
      else if (p.endsWith('/chat')) body = { reply: message().content, message_id: 'message-1', action: 'chat', trace: [], task_proposals: [proposal] }
      else if (p.endsWith('/confirm')) { confirmationCount++; saved = true; body = { task: { id: 'task-1' } } }
      else if (p.includes('/agent/sessions')) body = []
      await route.fulfill({ json: body })
    })
    await page.goto('http://127.0.0.1:3003/report')
    await page.getByRole('heading', { name: '甲的日报', exact: true }).waitFor()
    console.log('Report initial render: OK')
    await Promise.all([
      page.waitForRequest(request => request.url().includes('/reports/latest') && request.url().includes('report_type=weekly')),
      page.getByRole('button', { name: '周报', exact: true }).click(),
    ])
    await page.getByRole('button', { name: '测试关系甲 切换' }).click()
    await page.getByRole('heading', { name: '乙的周报', exact: true }).waitFor()
    assert.ok(releaseLate)
    releaseLate(); await lateDone
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))))
    assert.equal(await page.getByRole('heading', { name: '乙的周报', exact: true }).count(), 1)
    console.log('Late relationship response ignored: OK')
    await page.getByRole('button', { name: '刷新', exact: true }).click()
    await page.getByRole('button', { name: '生成中…', exact: true }).waitFor()
    assert.ok(await page.getByRole('button', { name: '生成中…', exact: true }).isDisabled())
    await page.getByRole('heading', { name: '乙的周报已更新', exact: true }).waitFor({ timeout: 15000 })
    assert.ok(reportReads >= 3)
    console.log('Pending report polling and completion: OK')
    await page.goto('http://127.0.0.1:3003/chat')
    await page.getByRole('textbox', { name: '想说的话', exact: true }).fill('明天想安排一点轻松的事')
    await page.getByRole('button', { name: '发送', exact: true }).click()
    await page.getByRole('button', { name: '加入安排', exact: true }).waitFor()
    assert.equal(confirmationCount, 0)
    await page.setViewportSize({ width: 390, height: 844 })
    await page.getByRole('button', { name: '加入安排', exact: true }).click()
    await page.getByRole('button', { name: '已加入安排', exact: true }).waitFor()
    assert.equal(confirmationCount, 1)
    assert.ok(await page.getByRole('button', { name: '已加入安排', exact: true }).isDisabled())
    await page.reload()
    await page.getByRole('button', { name: '已加入安排', exact: true }).waitFor()
    assert.equal(confirmationCount, 1)
    await page.setViewportSize({ width: 390, height: 844 })
    await page.getByRole('button', { name: '已加入安排', exact: true }).scrollIntoViewIfNeeded()
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth))
    await page.screenshot({ path: path.resolve('output/playwright/web-audit-task-confirmed.png'), fullPage: true })
    assert.deepEqual(errors, [])
    console.log('Task proposal / explicit confirmation / reload / narrow layout: OK')
    console.log('Browser page errors: 0; API mode: intercepted test responses only')
  } finally { await browser.close() }
})().catch(error => { console.error(error); process.exitCode = 1 })
