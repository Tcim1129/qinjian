import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

import {
  formatBeijingDate,
  formatBeijingDateTime,
  formatBeijingMonthDayTime,
  formatBeijingShortDate,
  getServerTimestampMs,
  parseServerDateTime,
} from './datetime.js'
import { buildHomeRadarAxes, buildHomeTrendView } from './homeAnalytics.js'

const __dirname = dirname(fileURLToPath(import.meta.url))
const read = (relPath) => readFileSync(resolve(__dirname, relPath), 'utf8')

// QJ-09: 无时区后缀的后端 UTC 时间与带 Z 的 UTC 时间统一按北京时间展示，消除 8 小时偏差
test('QJ-09 server naive UTC timestamps align with explicit Z timestamps in Beijing time', () => {
  const naiveUtc = '2026-11-25T08:40:00'
  const explicitUtc = '2026-11-25T08:40:00Z'

  assert.equal(parseServerDateTime(naiveUtc)?.getTime(), parseServerDateTime(explicitUtc)?.getTime())
  assert.equal(getServerTimestampMs(naiveUtc), getServerTimestampMs(explicitUtc))
  assert.equal(formatBeijingMonthDayTime(naiveUtc), '11-25 16:40')
  assert.equal(formatBeijingMonthDayTime(explicitUtc), '11-25 16:40')
  assert.equal(formatBeijingDateTime(naiveUtc), '2026-11-25 16:40')
  assert.equal(formatBeijingDate(naiveUtc), '2026-11-25')
  // 纯日期字符串不应发生跨天漂移
  assert.equal(formatBeijingShortDate('2026-11-25'), '11月25日')
  assert.equal(formatBeijingDate('2026-11-25'), '2026-11-25')

  for (const relPath of [
    '../components/AppHeader.vue',
    '../views/chat/ChatPage.vue',
    '../views/profile/PrivacySecurityPage.vue',
    '../views/health/HealthTestPage.vue',
    '../views/community/CommunityPage.vue',
    '../views/report/ReportPage.vue',
    '../views/relationship/RelationshipSpacesPage.vue',
    '../components/SavedExpressionEditor.vue',
  ]) {
    const src = read(relPath)
    assert.match(src, /@\/utils\/datetime/, `${relPath} should use @/utils/datetime`)
  }
})

// QJ-05: 首页阶段回顾在真实账号下展示已有体检分数与五项维度，不写死为空
test('QJ-05 home analytics render real assessment and report data for non-demo users', () => {
  const assessmentTrend = {
    latest_score: 80,
    dimension_scores: [
      { id: 'connection', label: '连接与表达', score: 82 },
      { id: 'trust', label: '信任与安全', score: 78 },
      { id: 'repair', label: '修复能力', score: 74 },
      { id: 'shared_future', label: '共同愿景', score: 84 },
      { id: 'vitality', label: '关系活力', score: 82 },
    ],
    trend_points: [
      { submitted_at: '2026-11-04T08:00:00', total_score: 58 },
      { submitted_at: '2026-11-11T08:00:00', total_score: 65 },
      { submitted_at: '2026-11-18T08:00:00', total_score: 72 },
      { submitted_at: '2026-11-25T08:00:00', total_score: 80 },
    ],
  }

  const trendView = buildHomeTrendView({
    isDemoMode: false,
    reportTrend: { trend: [] },
    assessmentTrend,
  })
  assert.equal(trendView.points.length, 4)
  assert.deepEqual(trendView.points.map((p) => p.score), [58, 65, 72, 80])
  assert.match(trendView.badge, /80分/)

  const radarAxes = buildHomeRadarAxes({ isDemoMode: false, assessmentTrend })
  assert.equal(radarAxes.length, 5)
  assert.deepEqual(radarAxes.map((a) => a.value), [82, 78, 74, 84, 82])

  const emptyTrend = buildHomeTrendView({ isDemoMode: false, reportTrend: { trend: [] }, assessmentTrend: { trend_points: [] } })
  assert.equal(emptyTrend.points.length, 0)
  assert.equal(emptyTrend.badge, '暂无数据')
  assert.equal(buildHomeRadarAxes({ isDemoMode: false, assessmentTrend: { dimension_scores: [] } }).length, 0)
})

// QJ-02: 智能体总览图片位于生产保留目录且窄屏不再锁死 min-width: 1180px
test('QJ-02 relationship agent image lives outside stripped competition folder and adapts on narrow screens', () => {
  const pageSrc = read('../views/agent/RelationshipAgentPage.vue')
  const stripSrc = read('../../scripts/strip-demo-pages.mjs')

  assert.match(pageSrc, /src="\/agent\/relationship-agent-concept-v3\.png"/)
  assert.doesNotMatch(pageSrc, /\/competition\/relationship-agent-concept-v3\.png/)
  assert.equal(existsSync(resolve(__dirname, '../../public/agent/relationship-agent-concept-v3.png')), true)
  assert.doesNotMatch(stripSrc, /['"]agent['"]/)
  assert.match(pageSrc, /@media\s*\(max-width:\s*1179px\)\s*\{[\s\S]*?\.demo-artboard\s*\{[\s\S]*?min-width:\s*0/)
  assert.match(pageSrc, /class="demo-mobile-controls"/)
})

// QJ-06, QJ-07, QJ-10, QJ-11 前端交互与布局契约
test('QJ-06/07/10/11 frontend contracts cover pack rotation, honest attachment feedback, deletion flow, and header/chat layout', () => {
  const healthSrc = read('../views/health/HealthTestPage.vue')
  assert.match(healthSrc, /excludeItemIds:\s*previousRotationIds/)
  assert.match(healthSrc, /packVariant\.value \+= 1/)

  const attachSrc = read('../views/health/AttachmentPage.vue')
  assert.match(attachSrc, /status === 'insufficient_data'/)
  assert.match(attachSrc, /sampleProgressText/)

  const privacySrc = read('../views/profile/PrivacySecurityPage.vue')
  assert.match(privacySrc, /api\.requestPrivacyDelete\(\)/)
  assert.match(privacySrc, /api\.cancelPrivacyDelete\(\)/)
  assert.match(privacySrc, /申请注销账号/)
  assert.match(privacySrc, /撤回注销申请/)

  const headerSrc = read('../components/AppHeader.vue')
  assert.match(headerSrc, /grid-template-columns:\s*auto minmax\(0,\s*1fr\)\s*auto/)

  const chatSrc = read('../views/chat/ChatPage.vue')
  assert.match(chatSrc, /\.chat-head__actions\s*\{[^}]*flex-wrap:\s*wrap/s)
})
