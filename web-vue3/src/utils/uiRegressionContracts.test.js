import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))

function source(path) {
  return readFileSync(resolve(__dirname, path), 'utf8')
}

test('real report UI uses scoped pair and backend trend instead of fabricated scores', () => {
  const reportSource = source('../views/report/ReportPage.vue')
  const apiSource = source('../api/index.js')

  assert.match(apiSource, /getReportTrend\s*\(/)
  assert.match(reportSource, /selectedPairId\.value/)
  assert.match(reportSource, /api\.getReportTrend/)
  assert.doesNotMatch(reportSource, /trend_points:\s*buildFallbackTrend\(score\)/)
  assert.doesNotMatch(reportSource, /dimensions:\s*buildFallbackDimensions\(score\)/)
})

test('profile settings save through the user API and avatar upload is persisted', () => {
  const profileSource = source('../views/profile/ProfilePage.vue')

  assert.match(profileSource, /await\s+userStore\.updateMe\s*\(/)
  assert.match(profileSource, /await\s+api\.uploadFile\s*\(\s*['"]image['"]/)
  assert.match(profileSource, /task_planner_defaults/)
})

test('login agreements render readable dialog content', () => {
  const loginSource = source('../views/auth/LoginPage.vue')

  assert.match(loginSource, /role="dialog"/)
  assert.match(loginSource, /activeLegalDoc\.sections/)
  assert.doesNotMatch(loginSource, /当前已保留入口/)
})

test('relationship detail participates in the relationship header section', () => {
  const headerSource = source('../components/AppHeader.vue')

  assert.match(headerSource, /['"]relationship-space-detail['"]:\s*['"]关系['"]/)
  assert.match(headerSource, /match:\s*\[[^\]]*['"]relationship-space-detail['"]/)
})
