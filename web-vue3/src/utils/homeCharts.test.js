import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const homePageSource = readFileSync(
  new URL('../views/home/HomePage.vue', import.meta.url),
  'utf8',
)

test('real home analytics do not ship hard-coded demo trend scores', () => {
  assert.equal(
    /const\s+homeTrendPoints\s*=\s*\[\s*\{\s*label:\s*'30天前'/.test(homePageSource),
    false,
  )
  assert.equal(homePageSource.includes('本周 +6'), false)
})

test('home analytics expose an explicit empty state for accounts without data', () => {
  assert.match(homePageSource, /还没有趋势数据/)
  assert.match(homePageSource, /还没有维度数据/)
})
