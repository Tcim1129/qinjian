// Isolated layout check. Uses sample state only and makes no backend writes.
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

    for (const width of [562, 390, 320]) {
      await page.setViewportSize({ width, height: 844 })
      await page.goto('http://127.0.0.1:3014/discover')
      await page.waitForLoadState('networkidle')
      const header = page.locator('.app-header')
      const pill = header.locator('.header-object-pill')
      await pill.waitFor()
      const state = await page.evaluate(() => {
        const header = document.querySelector('.app-header')
        const pill = header.querySelector('.header-object-pill')
        const h = header.getBoundingClientRect()
        const p = pill.getBoundingClientRect()
        return {
          headerTop: h.top, headerHeight: h.height,
          pillDisplay: getComputedStyle(pill).display,
          pillInside: p.left >= h.left && p.right <= h.right && p.top >= h.top && p.bottom <= h.bottom,
          overflow: document.documentElement.scrollWidth > innerWidth,
          rawCssVisible: document.body.innerText.includes('.header-object-wrap {'),
        }
      })
      assert.equal(state.headerTop, 0, `${width}px header displaced`)
      assert.equal(state.headerHeight, 58, `${width}px header height changed`)
      assert.equal(state.pillDisplay, 'inline-flex', `${width}px selector is unstyled`)
      assert.ok(state.pillInside, `${width}px selector escapes header`)
      assert.equal(state.overflow, false, `${width}px page overflows horizontally`)
      assert.equal(state.rawCssVisible, false, `${width}px raw CSS rendered as page content`)

      await pill.click()
      const menu = header.locator('.header-object-menu')
      await menu.waitFor()
      const box = await menu.boundingBox()
      assert.ok(box.x >= 8 && box.x + box.width <= width - 8, `${width}px menu leaves viewport`)
      assert.equal(await menu.getByRole('button').count(), 3)
      await menu.getByRole('button').nth(1).click()
      assert.match(await pill.innerText(), /周宁/)
      assert.equal(await menu.count(), 0)
      await page.screenshot({ path: path.resolve(`output/playwright/header-object-${width}.png`) })
    }
    assert.deepEqual(errors, [])
    console.log('Header object selector passed at 562px, 390px and 320px; menu stays usable and within viewport.')
  } finally {
    await browser.close()
  }
})().catch(error => { console.error(error); process.exitCode = 1 })
