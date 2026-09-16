// Browser contract checks only. All API/model replies are isolated test fixtures.
const assert = require('node:assert/strict')
const path = require('node:path')
const { chromium } = require(process.env.QJ_PLAYWRIGHT_MODULE || 'playwright')

;(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'msedge' })
  try {
    const context = await browser.newContext({ viewport: { width: 1365, height: 950 } })
    await context.addInitScript(() => sessionStorage.setItem('qj_token', 'life-flow-test-only'))
    const page = await context.newPage(), errors = [], requests = []
    page.on('pageerror', error => errors.push(error.message))
    const today = new Date().toLocaleDateString('en-CA')
    const task = { id: 'life-task', title: '问问方便的时间', description: '只问时间，不急着聊具体的事。', due_date: today, status: 'pending', source: 'manual', target_scope: 'self', feedback: null }
    let saved = false, confirmationCount = 0, sessionCount = 0, messageCount = 0
    const histories = {}
    const alignment = { checkin_date: today, user_a_label: '我', user_b_label: '对方', view_a_summary: '为今晚留了时间，临时取消让我失落。', view_b_summary: '今天有些忙，想换个时间。', suggested_opening: '下次有变化，能不能早点告诉我？', bridge_actions: ['约一个方便的时间'], shared_story: '需要先确认彼此方便的时间。' }
    await context.route('**/*', async route => {
      const url = new URL(route.request().url())
      if (url.hostname !== '127.0.0.1') return route.abort()
      if (!url.pathname.startsWith('/api/')) return route.continue()
      const p = url.pathname.replace('/api/v1', ''), method = route.request().method()
      let body = {}
      if (p === '/auth/me') body = { id: 'life-user', nickname: '演示测试', product_prefs: {} }
      else if (p === '/pairs/me') body = [{ id: 'life-pair', status: 'active', type: 'couple', partner_nickname: '测试关系' }]
      else if (p.includes('notifications')) body = []
      else if (p.endsWith('/alignment/latest')) body = alignment
      else if (p === '/agent/sessions') { const id = `session-${++sessionCount}`; histories[id] = []; body = { session_id: id } }
      else if (p.endsWith('/messages')) body = histories[p.split('/')[3]] || []
      else if (p.endsWith('/chat')) {
        const request = route.request().postDataJSON(); requests.push(request)
        const id = `message-${++messageCount}`, session = p.split('/')[3]
        const planning = request.scene_context?.intent === 'plan'
        const reply = planning ? '先问问明天什么时候方便。你愿意的话，再把它加入安排。' : request.content.includes('短一点') ? '临时取消我有点失落。我们明天再聊吧。' : '我今晚特意空了时间，临时取消让我挺失落的。下次有变化，能不能早点跟我说？'
        const proposals = planning ? [{ proposal_id: 'life-proposal', title: task.title, description: task.description, due_date: today, requires_confirmation: true }] : []
        const trace = [{ thought: 'HIDDEN_THOUGHT', tool_results: [{ name: 'get_recent_events', result: { status: 'success', data: [{ text: 'HIDDEN_TOOL_RAW' }] } }] }]
        const message = { id, role: 'assistant', content: reply, payload: { task_proposals: proposals }, trace }
        histories[session].push({ id: `user-${id}`, role: 'user', content: request.content, payload: { scene_context: request.scene_context } }, message)
        body = { reply, message_id: id, action: 'chat', task_proposals: proposals, trace }
      } else if (p.endsWith('/confirm')) { confirmationCount++; saved = true; body = { task } }
      else if (p.startsWith('/tasks/daily/')) body = { tasks: saved ? [task] : [], for_date: today, effective_settings: {} }
      else if (p.endsWith('/feedback')) { const request = route.request().postDataJSON(); task.feedback = request; body = { ...request, task_id: task.id, submitted_at: new Date().toISOString() } }
      await route.fulfill({ json: body })
    })
    await page.goto('http://127.0.0.1:3003/alignment')
    await page.getByRole('button', { name: '换个说法 ↗', exact: true }).waitFor()
    console.log('Rendered alignment entry:', (await page.locator('main').innerText()).slice(0, 160))
    await page.getByRole('button', { name: '换个说法 ↗', exact: true }).click()
    const dialog = page.getByRole('dialog')
    assert.equal(await dialog.getByText('聊天草稿', { exact: true }).count(), 0)
    assert.ok((await dialog.getByRole('textbox', { name: '想问什么' }).inputValue()).length < 160)
    await dialog.getByRole('button', { name: '开始聊', exact: true }).click()
    await dialog.getByRole('button', { name: '短一点', exact: true }).waitFor()
    assert.equal(requests.length, 1)
    assert.equal(requests[0].scene_context.intent, 'wording')
    assert.ok(requests[0].scene_context.summary.includes('临时取消'))
    await dialog.getByRole('button', { name: '短一点', exact: true }).click()
    await dialog.getByText('临时取消我有点失落。我们明天再聊吧。', { exact: true }).waitFor()
    assert.equal(requests.length, 2)
    await dialog.getByRole('button', { name: '查看实际调用', exact: true }).last().click()
    assert.ok(!(await dialog.innerText()).includes('HIDDEN_'))
    await dialog.screenshot({ path: path.resolve('output/playwright/life-agent-chat-desktop.png') })
    await page.setViewportSize({ width: 390, height: 844 })
    const conversationRatio = await dialog.evaluate(element => element.querySelector('.chat-list').getBoundingClientRect().height / element.querySelector('.chat-shell').getBoundingClientRect().height)
    assert.ok(conversationRatio >= 0.55, 'narrow conversation should have more space than its composer')
    await dialog.getByRole('button', { name: '发送', exact: true }).scrollIntoViewIfNeeded()
    await dialog.getByText('临时取消我有点失落。我们明天再聊吧。', { exact: true }).scrollIntoViewIfNeeded()
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    await dialog.screenshot({ path: path.resolve('output/playwright/life-agent-chat-mobile.png') })
    await dialog.getByRole('button', { name: '关闭智能体复盘' }).click()
    await page.getByRole('button', { name: '和 AI 商量下一步' }).click()
    await dialog.getByRole('button', { name: '开始聊', exact: true }).click()
    await dialog.getByRole('button', { name: '加入安排', exact: true }).waitFor()
    assert.equal(confirmationCount, 0)
    await dialog.getByRole('button', { name: '加入安排', exact: true }).click()
    await dialog.getByRole('button', { name: '已加入安排', exact: true }).waitFor()
    assert.equal(confirmationCount, 1)
    await page.goto('http://127.0.0.1:3003/challenges')
    await page.getByText(task.title, { exact: true }).click()
    await page.getByRole('button', { name: '后来怎么样', exact: true }).click()
    assert.equal(await page.getByRole('button', { name: '有帮助', exact: true }).count(), 0)
    await page.getByRole('button', { name: '还没做', exact: true }).click()
    await page.getByRole('textbox', { name: '补充一句（选填）' }).fill('今天太累，不想聊')
    await page.getByRole('button', { name: '记下结果', exact: true }).click()
    await page.getByText(task.title, { exact: true }).click().catch(() => {})
    if (!await page.getByRole('button', { name: '想想明天', exact: true }).isVisible()) await page.getByText(task.title, { exact: true }).click()
    assert.equal(task.status, 'pending')
    assert.equal(task.feedback.outcome, 'not_yet')
    assert.equal(task.feedback.usefulness_score, null)
    await page.reload()
    await page.getByText(task.title, { exact: true }).click()
    await page.getByRole('button', { name: '想想明天', exact: true }).click()
    await dialog.getByText('查看这次带入的内容', { exact: true }).click()
    assert.ok((await dialog.innerText()).includes('今天太累，不想聊'))
    await dialog.screenshot({ path: path.resolve('output/playwright/life-agent-followup-mobile.png') })
    await dialog.getByRole('button', { name: '开始聊', exact: true }).click()
    await dialog.getByRole('button', { name: '换个轻松的办法', exact: true }).waitFor()
    assert.ok(requests.at(-1).scene_context.summary.includes('未完成'))
    assert.deepEqual(errors, [])
    console.log('PASS: scene entry, one-click start, rewrite, safe tool summary, confirm-only task, feedback without fake completion, reload and next-day context; desktop + 390px.')
    console.log('All API/model replies were intercepted fixtures. No live backend writes or model-quality claims.')
  } finally { await browser.close() }
})().catch(error => { console.error(error); process.exitCode = 1 })
