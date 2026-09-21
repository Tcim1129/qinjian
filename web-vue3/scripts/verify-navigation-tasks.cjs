const assert = require('node:assert/strict')
const { chromium } = require(process.env.QJ_PLAYWRIGHT_MODULE || 'playwright')
;(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true })
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 960 } })
    await context.addInitScript(() => sessionStorage.setItem('qj_token', 'demo-mode'))
    await context.route('**/*', route => new URL(route.request().url()).pathname.startsWith('/api/') ? route.abort() : route.continue())
    const page = await context.newPage()
    const errors = []
    page.on('pageerror', e => errors.push(e.message))
    await page.goto('http://127.0.0.1:3014/')
    await page.waitForLoadState('networkidle')
    const nav = page.getByRole('navigation', { name: '主导航' })
    const record = nav.locator('.nav-item').filter({ hasText: '记录' })
    const overview = nav.locator('.nav-item').filter({ hasText: '总览' })
    await record.hover()
    await page.locator('.nav-menu').waitFor()
    await record.click()
    await overview.hover()
    assert.equal(await page.locator('.nav-menu').count(), 1)
    assert.match(await page.locator('.nav-menu').innerText(), /全部功能/)
    await page.mouse.move(10, 350)
    await page.locator('.nav-menu').waitFor({ state: 'detached' })
    // Traverse the actual gap between the button and the lowest entry.
    await record.hover()
    const menuTarget = nav.getByRole('button', { name: '今日安排', exact: true })
    const box = await menuTarget.boundingBox()
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 12 })
    await menuTarget.click()
    await page.locator('.challenges-page').waitFor()
    await page.waitForLoadState('networkidle')
    assert.equal(await page.locator('.nav-menu').count(), 0)
    const entries = [
      ['记录', '发前看看', '/message-simulation'],
      ['记录', '今日记录', '/checkin'],
      ['记录', '聊一聊', '/chat'],
      ['总览', '全部功能', '/discover'],
      ['总览', '双视角', '/alignment'],
      ['总览', '关系体检', '/health-test'],
      ['总览', '异地关系', '/longdistance'],
      ['简报', '关系简报', '/report'],
      ['简报', '关系日历', '/timeline'],
      ['简报', '判断说明', '/methodology'],
      ['我的', '隐私安全', '/privacy-security'],
      ['我的', '个人中心', '/profile'],
      ['我的', '关系管理', '/pair'],
      ['我的', '关系空间', '/relationship-spaces'],
    ]
    for (const [group, child, path] of entries) {
      await nav.locator('.nav-item').filter({ hasText: group }).hover()
      await nav.getByRole('button', { name: child, exact: true }).click()
      await page.waitForURL(url => url.pathname === path)
      await page.waitForLoadState('networkidle')
      await page.waitForFunction(() => document.querySelector('main')?.innerText.trim().length > 20)
      console.log('Opened', child, new URL(page.url()).pathname)
    }
    await nav.locator('.nav-item').filter({ hasText: '首页' }).click()
    await page.waitForURL(url => url.pathname === '/')
    await page.getByRole('button', { name: '更新结果', exact: true }).first().click()
    await page.getByRole('button', { name: '已完成', exact: true }).click()
    await page.getByRole('button', { name: '保存结果', exact: true }).click()
    await page.locator('.task-result-dialog').waitFor({ state: 'detached' })
    const firstCard = page.locator('.home-list--scroll .home-list__item').first()
    assert.match(await firstCard.innerText(), /已完成/)
    await firstCard.getByRole('button', { name: '更新结果' }).click()
    await page.getByRole('button', { name: '未完成', exact: true }).click()
    await page.locator('.task-result-dialog textarea').fill('今天下班晚了，没找到时间。')
    await page.getByRole('button', { name: '保存结果', exact: true }).click()
    await page.locator('.task-result-dialog').waitFor({ state: 'detached' })
    assert.doesNotMatch(await firstCard.innerText(), /已完成/)
    await record.hover()
    await nav.getByRole('button', { name: '今日安排', exact: true }).click()
    await page.locator('[data-task-row]').first().waitFor()
    await page.getByRole('button', { name: /先给彼此.*更新结果/ }).click()
    assert.equal(await page.locator('.task-result-dialog textarea').inputValue(), '今天下班晚了，没找到时间。')
    let sceneRequest
    await page.route('**/api/v1/agent/**', async route => {
      const path = new URL(route.request().url()).pathname
      if (path.endsWith('/chat')) {
        sceneRequest = route.request().postDataJSON()
        return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: '测试：模型暂时不可用' }) })
      }
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify(path.endsWith('/messages') ? [] : { session_id: 'test-session' }) })
    })
    await page.getByRole('button', { name: '保存并聊聊原因', exact: true }).click()
    await page.getByText('测试：模型暂时不可用', { exact: true }).first().waitFor()
    assert.match(sceneRequest.scene_context.summary, /今天下班晚了，没找到时间/)
    assert.match(sceneRequest.content, /不要替我猜测/)
    await page.getByRole('button', { name: '关闭智能体复盘' }).click()
    await page.getByRole('group', { name: '安排日期切换' }).getByRole('button', { name: '明天', exact: true }).click()
    await page.waitForURL(url => url.searchParams.get('scope') === 'tomorrow')
    await page.getByRole('heading', { name: '明天想做的事', exact: true }).waitFor()
    await page.waitForLoadState('networkidle')
    await page.waitForFunction(() => !document.querySelector('button[aria-label$="：更新结果"]'))
    await page.waitForFunction(() => document.querySelectorAll('[data-task-row]').length === 3 && !document.querySelector('.page-leave-active, .page-enter-active'))
    await page.screenshot({ path: 'output/playwright/navigation-tasks.png' })
    await page.setViewportSize({ width: 390, height: 844 })
    await page.getByRole('group', { name: '安排日期切换' }).getByRole('button', { name: '今天', exact: true }).click()
    await page.getByRole('button', { name: /先给彼此.*更新结果/ }).click()
    await page.screenshot({ path: 'output/playwright/task-result-mobile.png' })
    const dialogBox = await page.locator('.task-result-dialog').boundingBox()
    assert.ok(dialogBox.x >= 0 && dialogBox.x + dialogBox.width <= 390)
    assert.deepEqual(errors, [])
    console.log('PASS: exclusive hover menus, navigation, home completion/reopen, cross-page feedback, tomorrow read-only results')
  } finally { await browser.close() }
})().catch(e => { console.error(e); process.exitCode = 1 })
