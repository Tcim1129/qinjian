// Isolated browser contract checks. API responses are mocked, no real account/provider writes.
const assert = require('node:assert/strict')
const path = require('node:path')
const { chromium } = require(process.env.QJ_PLAYWRIGHT_MODULE || 'playwright')
;(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' })
  try {
    const context = await browser.newContext({ viewport: { width: 390, height: 900 } })
    await context.addInitScript(() => sessionStorage.setItem('qj_token', 'demo-mode'))
    const page = await context.newPage(), errors = [], chats = []
    page.setDefaultTimeout(10000)
    page.on('pageerror', error => errors.push(error.message))
    let release, mode = 'hold', count = 0
    const gate = new Promise(resolve => { release = resolve })
    await context.route('**/*', async route => {
      const url = new URL(route.request().url())
      if (url.hostname !== '127.0.0.1') return route.abort()
      if (!url.pathname.startsWith('/api/')) return route.continue()
      if (url.pathname.endsWith('/agent/sessions') && route.request().method() === 'POST') return route.fulfill({ json: { session_id: `test-session-${++count}` } })
      if (url.pathname.endsWith('/messages')) return route.fulfill({ json: [] })
      if (url.pathname.endsWith('/chat')) {
        chats.push(route.request().postDataJSON())
        if (mode === 'hold') { await gate; return route.fulfill({ status: 502, json: { detail: '测试连接失败，请重试。' } }) }
        if (mode === 'error') return route.fulfill({ status: 502, json: { detail: '测试连接失败，请重试。' } })
        return route.fulfill({ json: { reply: '我们明天再聊，好吗？', message_id: `reply-${chats.length}`, trace: [], task_proposals: [] } })
      }
      return route.fulfill({ json: [] })
    })
    await page.goto('http://127.0.0.1:3013/alignment')
    await page.waitForLoadState('networkidle')
    await page.getByText('展开 ▾', { exact: true }).first().click()
    await page.getByRole('button', { name: '请 AI 帮我梳理 ↗', exact: true }).click()
    const dialog = page.getByRole('dialog')
    const original = await dialog.getByRole('textbox', { name: '想问什么', exact: true }).inputValue()
    await dialog.getByRole('button', { name: '开始聊', exact: true }).click()
    await dialog.locator('.chat-waiting').waitFor()
    assert.equal(await dialog.getByRole('button', { name: '发送中...', exact: true }).isDisabled(), true)
    assert.match(await dialog.locator('.chat-waiting .chat-spinner').evaluate(el => getComputedStyle(el).animationName), /^chat-turn/)
    await dialog.screenshot({ path: path.resolve('output/playwright/agent-waiting-mobile.png') })
    release()
    await dialog.locator('.chat-send-error').waitFor()
    assert.equal(await dialog.locator('.chat-waiting').count(), 0)
    assert.equal(await dialog.getByRole('textbox', { name: '想说的话', exact: true }).inputValue(), original)
    mode = 'success'
    await dialog.getByRole('button', { name: '发送', exact: true }).click()
    await dialog.getByText('我们明天再聊，好吗？', { exact: true }).waitFor()
    assert.equal(chats.length, 2)
    assert.equal(chats[0].content, chats[1].content)
    assert.ok(chats[0].scene_context.summary)
    mode = 'error'
    await dialog.getByRole('button', { name: '换个说法', exact: true }).last().click()
    await dialog.getByRole('button', { name: '换个说法', exact: true }).last().waitFor()
    assert.equal(await dialog.getByText('我们明天再聊，好吗？', { exact: true }).count(), 1)
    await page.goto('http://127.0.0.1:3013/message-simulation')
    await page.waitForLoadState('networkidle')
    await page.getByRole('textbox', { name: '原句', exact: true }).fill('这周末我需要休息，下次再约。')
    mode = 'success'
    await page.getByRole('button', { name: '换个改法', exact: true }).click()
    await page.getByText('我们明天再聊，好吗？', { exact: true }).waitFor()
    assert.ok(chats.at(-1).scene_context.summary.includes('这周末我需要休息'))
    mode = 'error'
    await page.getByRole('button', { name: '换个改法', exact: true }).click()
    await page.getByRole('button', { name: '换个改法', exact: true }).waitFor()
    assert.equal(await page.getByText('我们明天再聊，好吗？', { exact: true }).count(), 1)
    await page.setViewportSize({ width: 320, height: 900 })
    await page.goto('http://127.0.0.1:3013/discover')
    await page.waitForLoadState('networkidle')
    assert.equal(await page.locator('.discover-page').getByText('理解', { exact: true }).count(), 0)
    const wraps = await page.locator('.discover-entry__body strong,.growth-card__body strong').evaluateAll(es => es.filter(e => e.getBoundingClientRect().height > parseFloat(getComputedStyle(e).lineHeight) + 1 || e.scrollWidth > e.clientWidth).map(e => e.textContent))
    assert.deepEqual(wraps, [])
    assert.deepEqual(errors, [])
    console.log('PASS: sample scene starts, spinner while pending, failure restores draft, retry works, rewrite uses source, no preset fallback, one-line cards. Mock API only.')
  } finally { await browser.close() }
})().catch(error => { console.error(error); process.exitCode = 1 })
