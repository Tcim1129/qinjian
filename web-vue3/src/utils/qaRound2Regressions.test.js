import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

import { clearStorageOwner, setStorageOwner } from './accountStorage.js'
import { resolveScopedPairId } from './reportScopeSelection.js'
import { createSoloTaskEntry, loadSoloTaskPack } from './soloWorkspace.js'

const __dirname = dirname(fileURLToPath(import.meta.url))

function source(relPath) {
  return readFileSync(resolve(__dirname, relPath), 'utf8')
}

test('BUG-01: solo mode on /challenges renders composer and persists created personal tasks', () => {
  const store = new Map()
  globalThis.window = {
    localStorage: {
      getItem: (key) => (store.has(key) ? store.get(key) : null),
      setItem: (key, val) => store.set(key, String(val)),
      removeItem: (key) => store.delete(key),
    },
    sessionStorage: {
      getItem: (key) => (key === 'qj_token' ? 'token-solo-1' : null),
    },
  }
  try {
    setStorageOwner('qa-solo-user-1', 'token-solo-1')
    createSoloTaskEntry(
      {
        title: '晚上散步十五分钟',
        description: '吃完晚饭下楼透气放松一下',
        category: 'activity',
        importance_level: 'high',
      },
      { isoDate: '2026-11-25' }
    )
    const reloaded = loadSoloTaskPack({ isoDate: '2026-11-25' })
    const created = reloaded.tasks.find((item) => item.title === '晚上散步十五分钟')
    assert.ok(created, 'personal task should persist across reload')
    assert.equal(created.importance_level, 'high')
    assert.equal(created.source, 'manual')
  } finally {
    clearStorageOwner()
    delete globalThis.window
  }

  const challengesSource = source('../views/challenges/ChallengesPage.vue')
  assert.doesNotMatch(challengesSource, /<template v-else>\s*<div class="challenge-shell">/)
  assert.match(challengesSource, /class="card challenge-solo-banner"/)
  assert.match(challengesSource, /ref="composerCardRef"/)
  assert.match(challengesSource, /createSoloTaskEntry\(payload,\s*\{\s*isoDate:\s*activeDate\.value\s*\}\)/)
})

test('BUG-02: /report falls back to solo personal record when user only has a pending invite pair', () => {
  const pendingPairOnly = [{ id: 'pending-pair-uuid', status: 'pending' }]
  const activePairs = pendingPairOnly.filter((pair) => pair.status === 'active')
  const resolved = resolveScopedPairId({
    preferredPairId: '',
    fallbackPairId: '',
    availablePairs: activePairs,
  })
  assert.equal(resolved, '')

  const reportSource = source('../views/report/ReportPage.vue')
  assert.match(reportSource, /function resolveInitialPairId\(\)/)
  assert.match(reportSource, /resolveScopedPairId\(\{/)
  assert.match(reportSource, /const pairId = selectedPair\.value\?\.id \|\| null/)
  assert.doesNotMatch(reportSource, /userStore\.currentPair\?\.id \|\| userStore\.activePairId/)
})

test('BUG-04: /health-test unifies radar header score and auto-restores latest result on mount', () => {
  const healthSource = source('../views/health/HealthTestPage.vue')
  assert.match(healthSource, /void loadAssessment\(\{\s*autoRestoreResult:\s*true\s*\}\)/)
  assert.match(healthSource, /submitted\.value = Boolean\(autoRestoreResult && !rotate && latest\.value\)/)
  assert.match(healthSource, /查看上次结果/)
  assert.match(healthSource, /开始新一轮体检/)
  assert.match(healthSource, /const reported = result\.value\?\.total_score/)
})

test('BUG-05 & BUG-06: checkup demo copy and timeline normalizer prevent raw low/none leaks', () => {
  const apiSource = source('../api/index.js')
  const chatSource = source('../views/chat/ChatPage.vue')
  const timelineSource = source('../views/report/TimelinePage.vue')

  assert.doesNotMatch(apiSource, /当前风险等级为「low」/)
  assert.match(apiSource, /当前风险等级为“低风险（整体平稳）”/)
  assert.match(chatSource, /none:\s*'整体平稳'/)
  assert.match(chatSource, /mild:\s*'轻度波动/)
  assert.match(timelineSource, /RAW_TIMELINE_PLACEHOLDERS/)
  assert.match(timelineSource, /cleanTimelineText/)
})

test('BUG-07: /methodology renders real methodology explanation instead of unopen placeholder', () => {
  const methodologySource = source('../views/coach/MethodologyPage.vue')
  const apiSource = source('../api/index.js')

  assert.doesNotMatch(methodologySource, /未开放/)
  assert.doesNotMatch(methodologySource, /暂不开放/)
  assert.match(methodologySource, /api\.getMethodology/)
  assert.match(methodologySource, /隐私与使用边界/)
  assert.match(apiSource, /getMethodology\s*\(/)
})

test('BUG-09: /pair route registers invite, join, and list aliases so recreating invite code stays on /pair', () => {
  const routerSource = source('../router/index.js')
  assert.match(routerSource, /path:\s*'\/pair'[\s\S]*?alias:\s*\['\/pair\/list',\s*'\/pair\/invite',\s*'\/pair\/join'\]/)
})

test('BUG-10: router and App shell expose lightweight progress bar and skeleton during route transitions', () => {
  const routerSource = source('../router/index.js')
  const appSource = source('../App.vue')

  assert.match(routerSource, /export const routeLoading = ref\(false\)/)
  assert.match(routerSource, /router\.afterEach/)
  assert.match(routerSource, /router\.onError/)
  assert.match(appSource, /class="route-progress-bar"/)
  assert.match(appSource, /class="route-skeleton/)
})

test('BUG-11: /auth provides accessible password visibility toggles for login/register and reset', () => {
  const loginSource = source('../views/auth/LoginPage.vue')
  assert.match(loginSource, /showPassword = ref\(false\)/)
  assert.match(loginSource, /showNewPassword = ref\(false\)/)
  assert.match(loginSource, /:type="showPassword \? 'text' : 'password'"/)
  assert.match(loginSource, /:aria-label="showPassword \? '隐藏密码' : '显示密码'"/)
  assert.match(loginSource, /:aria-label="showNewPassword \? '隐藏新密码' : '显示新密码'"/)
})

test('BUG-12: /repair-protocol supports custom conflict scenario input and /attachment-test guides record-based analysis', () => {
  const repairSource = source('../views/coach/RepairProtocolPage.vue')
  const attachSource = source('../views/health/AttachmentPage.vue')

  assert.match(repairSource, /自定义冲突场景/)
  assert.match(repairSource, /openCustomScenarioAgent/)
  assert.match(repairSource, /按这个场景给缓和建议/)
  assert.match(attachSource, /依恋倾向不是固定问卷答题/)
  assert.match(attachSource, /去写今日记录/)
  assert.match(attachSource, /先做关系体检/)
})
