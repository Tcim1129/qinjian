// Browser behavior checks with isolated storage and intercepted APIs only.
const assert = require('node:assert/strict')
const path = require('node:path')
const fs = require('node:fs')
const { chromium } = require(process.env.QJ_PLAYWRIGHT_MODULE || 'playwright')
const base = process.env.QJ_TEST_URL || 'http://127.0.0.1:3003'
;(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' })
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
    await context.addInitScript(() => {
      sessionStorage.setItem('qj_token', 'demo-mode')
      sessionStorage.setItem('qj_real_agent', '1')
    })
    const requests = [], errors = []
    let mode = 'error', release
    const gate = new Promise(resolve => { release = resolve })
    await context.route('**/*', async route => {
      const url = new URL(route.request().url())
      if (url.origin !== base) return route.abort()
      if (!url.pathname.startsWith('/api/')) return route.continue()
      if (url.pathname.endsWith('/agent/sessions')) return route.fulfill({ json: { session_id: 'test-session' } })
      if (url.pathname.endsWith('/messages')) return route.fulfill({ json: [] })
      if (url.pathname.endsWith('/chat')) {
        requests.push(route.request().postDataJSON())
        if (mode === 'error') {
          await gate
          return route.fulfill({ status: 502, json: { detail: '这次没能连上助手，请重试。' } })
        }
        return route.fulfill({ json: { reply: '浏览器测试回复：周末方便时再说。', message_id: 'reply-test', task_proposals: [], trace: [] } })
      }
      return route.fulfill({ json: [] })
    })
    const page = await context.newPage()
    page.setDefaultTimeout(6000)
    page.on('pageerror', error => errors.push(error.message))
    await page.goto(`${base}/chat`)
    await page.waitForLoadState('networkidle')
    console.log('Initial chat:', (await page.locator('.chat-page').innerText()).slice(0, 220))
    const initialReplies = await page.locator('.chat-msg:not(.chat-msg--user)').count()
    const input = page.locator('.chat-composer__input')
    const original = '产品验证：今天有点累，周末再聊这件事。'
    await input.fill(original)
    await page.getByRole('button', { name: '发送', exact: true }).click()
    await page.locator('.chat-waiting').waitFor()
    await input.fill('还没发送的新草稿')
    release()
    await page.locator('.chat-msg--error').waitFor()
    assert.equal(await page.locator('.chat-msg:not(.chat-msg--user)').count(), initialReplies)
    assert.equal(await input.inputValue(), '还没发送的新草稿')
    assert.equal(await page.getByText(original, { exact: true }).count(), 1)
    fs.mkdirSync(path.resolve('output/playwright'), { recursive: true })
    await page.locator('.chat-msg--error').screenshot({ path: path.resolve('output/playwright/product-chat-retry.png') })
    mode = 'success'
    await page.getByRole('button', { name: '重试', exact: true }).click()
    await page.getByText('浏览器测试回复：周末方便时再说。', { exact: true }).waitFor()
    assert.equal(requests.length, 2)
    assert.ok(requests[0].client_message_id)
    assert.deepEqual(requests[1], requests[0])
    assert.equal(await page.getByText(original, { exact: true }).count(), 1)
    assert.equal(await page.locator('.chat-msg--error').count(), 0)
    assert.equal(await input.inputValue(), '还没发送的新草稿')
    await page.evaluate(() => window.scrollTo(0, 0))
    await page.screenshot({ path: path.resolve('output/playwright/product-chat-desktop.png'), fullPage: true })
    await page.setViewportSize({ width: 390, height: 844 })
    await page.locator('.chat-msg').last().scrollIntoViewIfNeeded()
    await input.scrollIntoViewIfNeeded()
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    await page.screenshot({ path: path.resolve('output/playwright/product-chat-mobile.png'), fullPage: true })
    assert.deepEqual(errors, [])
    console.log('PASS: error stays visible without preset reply; retry uses original turn identity and preserves a new draft; desktop/mobile render.')

    const real = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
    await real.addInitScript(() => sessionStorage.setItem('qj_token', 'product-test-only'))
    const today = new Date().toLocaleDateString('en-CA')
    let task = { id: 'product-task', title: '聊聊近况', description: '有空时聊一会儿', status: 'pending', due_date: today, source: 'manual', target_scope: 'self', feedback: null }
    const saves = [], discussions = []
    let failSave = false
    await real.route('**/*', async route => {
      const url = new URL(route.request().url())
      if (url.origin !== base) return route.abort()
      if (!url.pathname.startsWith('/api/')) return route.continue()
      const p = url.pathname.replace('/api/v1', '')
      let body = {}
      if (p === '/auth/me') body = { id: 'product-user', nickname: '产品测试', product_prefs: {} }
      else if (p === '/pairs/me') body = [{ id: 'product-pair', status: 'active', type: 'couple', partner_nickname: '测试关系' }]
      else if (p.includes('notifications')) body = []
      else if (p.startsWith('/tasks/daily/')) body = { tasks: [task], for_date: today, effective_settings: {} }
      else if (p.endsWith('/result')) {
        const request = route.request().postDataJSON()
        saves.push(request)
        if (failSave) return route.fulfill({ status: 503, json: { detail: '测试：结果没保存上' } })
        task = { ...task, ...request, completed_at: request.status === 'completed' ? new Date().toISOString() : null, needs_feedback: request.status === 'completed' && !request.feedback }
        body = { task }
      } else if (p === '/agent/sessions') body = { session_id: 'result-discussion' }
      else if (p.endsWith('/messages')) body = []
      else if (p.endsWith('/chat')) {
        discussions.push(route.request().postDataJSON())
        body = { reply: '测试回复：先不用急着安排下一件事。', message_id: 'discussion-reply', task_proposals: [], trace: [] }
      }
      return route.fulfill({ json: body })
    })
    const resultPage = await real.newPage()
    resultPage.setDefaultTimeout(8000)
    resultPage.on('pageerror', error => errors.push(error.message))
    await resultPage.goto(`${base}/challenges`)
    await resultPage.waitForLoadState('networkidle')
    console.log('Tasks:', (await resultPage.locator('main').innerText()).slice(0, 190))
    const openResult = () => resultPage.getByRole('button', { name: '聊聊近况：更新结果', exact: true }).click()
    const dialog = resultPage.locator('.task-result-dialog')
    await openResult()
    await dialog.getByRole('button', { name: '已完成', exact: true }).click()
    await dialog.getByRole('button', { name: '保存结果', exact: true }).click()
    await dialog.waitFor({ state: 'detached' })
    assert.deepEqual(saves.at(-1), { status: 'completed', feedback: null })
    await openResult()
    await dialog.getByRole('button', { name: '还说不准', exact: true }).click()
    await dialog.locator('textarea').fill('聊了一会儿，还不知道有没有帮助。')
    failSave = true
    await dialog.getByRole('button', { name: '保存结果', exact: true }).click()
    await dialog.getByText('测试：结果没保存上', { exact: true }).waitFor()
    assert.equal(task.feedback, null)
    assert.equal(await dialog.locator('textarea').inputValue(), '聊了一会儿，还不知道有没有帮助。')
    failSave = false
    await dialog.getByRole('button', { name: '保存结果', exact: true }).click()
    await dialog.waitFor({ state: 'detached' })
    assert.equal(task.feedback.outcome, 'uncertain')
    assert.equal(task.feedback.usefulness_score, null)
    await resultPage.reload()
    await openResult()
    assert.equal(await dialog.getByRole('button', { name: '还说不准', exact: true }).getAttribute('aria-pressed'), 'true')
    assert.equal(await dialog.locator('textarea').inputValue(), '聊了一会儿，还不知道有没有帮助。')
    await dialog.screenshot({ path: path.resolve('output/playwright/product-task-desktop.png') })
    await resultPage.setViewportSize({ width: 390, height: 844 })
    const box = await dialog.boundingBox()
    assert.ok(box.x >= 0 && box.x + box.width <= 390)
    await dialog.screenshot({ path: path.resolve('output/playwright/product-task-mobile.png') })
    await dialog.getByRole('button', { name: '未完成', exact: true }).click()
    assert.equal(await dialog.getByRole('button', { name: '还说不准', exact: true }).count(), 0)
    await dialog.locator('textarea').fill('记错了，还没找到时间。')
    await dialog.getByRole('button', { name: '保存并接着聊', exact: true }).click()
    await resultPage.getByText('测试回复：先不用急着安排下一件事。', { exact: true }).waitFor()
    assert.equal(task.status, 'pending')
    assert.equal(task.feedback.outcome, 'not_yet')
    assert.match(discussions.at(-1).scene_context.summary, /记错了，还没找到时间/)
    assert.match(discussions.at(-1).scene_context.summary, /未完成/)
    assert.deepEqual(errors, [])
    console.log('PASS: real-account task UI sends one result request, supports unrated/uncertain, preserves failed inputs, reloads and carries actual feedback to discussion. APIs remain mocked.')
  } finally {
    await browser.close()
  }
})().catch(error => { console.error(error); process.exitCode = 1 })
