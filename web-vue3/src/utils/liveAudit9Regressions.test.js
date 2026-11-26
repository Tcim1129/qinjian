import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

import {
  extractReportInsights,
  extractReportRecommendations,
  extractReportSummary,
  extractStructuredReportDimensions,
} from './reportContent.js'
import { selectReportHistory } from './reportPeriods.js'

const __dirname = dirname(fileURLToPath(import.meta.url))

function source(relPath) {
  return readFileSync(resolve(__dirname, relPath), 'utf8')
}

test('solo report summary, insights, recommendations, and history render real solo AI fields', () => {
  const soloReport = {
    id: 'solo-1',
    type: 'solo',
    status: 'completed',
    health_score: 78,
    report_date: '2026-11-26',
    content: {
      health_score: 78,
      self_insight: '今天压力让情绪短暂上扬，但晚上已经慢慢稳下来了。',
      emotional_pattern: '遇到节奏紧张时容易先憋着，冷静后会自己整理。',
      self_care_tip: '睡前留十分钟远离手机，给情绪一点缓冲空间。',
      relationship_note: '先照顾好自己的节奏，再开口表达会更轻松。',
    },
  }

  assert.equal(extractReportSummary(soloReport), soloReport.content.self_insight)
  assert.deepEqual(extractReportInsights(soloReport), [
    soloReport.content.emotional_pattern,
    soloReport.content.relationship_note,
  ])
  assert.deepEqual(extractReportRecommendations(soloReport), [soloReport.content.self_care_tip])

  const history = selectReportHistory([soloReport], 'solo')
  assert.equal(history.length, 1)
  assert.equal(history[0].id, 'solo-1')
})

test('pair daily report extracts real 5-dimension radar scores without fabricating missing fields', () => {
  const pairDailyReport = {
    type: 'daily',
    content: {
      mood_a: { score: 6, label: '略委屈' },
      mood_b: { score: 8, label: '平静' },
      communication_quality: { score: 7, note: '愿意表达' },
      emotional_sync: { score: 68, note: '基本同步' },
      interaction_balance: { score: 72, note: '互动较平衡' },
    },
  }

  const dims = extractStructuredReportDimensions(pairDailyReport)
  assert.equal(dims.length, 5)
  assert.deepEqual(
    dims.map((item) => [item.label, item.score]),
    [
      ['沟通质量', 70],
      ['情绪同步', 68],
      ['互动平衡', 72],
      ['一方情绪', 60],
      ['另一方情绪', 80],
    ],
  )

  assert.deepEqual(extractStructuredReportDimensions({ type: 'daily', content: { insight: '只有文案' } }), [])
})

test('all remaining live-audit UI defects are fixed in source contracts', () => {
  const attachmentSource = source('../views/health/AttachmentPage.vue')
  assert.match(attachmentSource, /const hasMy = Boolean\(normalized\.my\.type && normalized\.my\.type !== 'unknown'\)/)
  assert.match(attachmentSource, /const hasPartner = Boolean\(normalized\.partner\?\.type && normalized\.partner\.type !== 'unknown'\)/)
  assert.match(attachmentSource, /个人记录还不足/)

  const communitySource = source('../views/community/CommunityPage.vue')
  assert.match(communitySource, /class="community-tip-desc"/)
  assert.match(communitySource, /function tipDescription\(tip\)/)

  const dialogSource = source('../components/TaskResultDialog.vue')
  assert.match(dialogSource, /class="task-result-panel"/)
  assert.match(dialogSource, /position:\s*sticky/)
  assert.match(dialogSource, /showToast\(completed \? '已记为已完成' : '结果已保存'\)/)

  const simSource = source('../views/coach/MessageSimulationPage.vue')
  assert.match(simSource, /showReactionShiftPill/)
  assert.match(simSource, /shouldShowReactionShift\(result\.value\)/)

  const pairSource = source('../views/pair/PairPage.vue')
  assert.match(pairSource, /还没有生成邀请码/)
  assert.match(pairSource, /生成邀请码/)

  const agentPageSource = source('../views/agent/RelationshipAgentPage.vue')
  assert.match(agentPageSource, /<ChatPage ref="chatPageRef" :key="activeScenario\.id" embedded isolated :scene-context=/)

  const repairSource = source('../views/coach/RepairProtocolPage.vue')
  assert.match(repairSource, /缓和建议已按最新状态重新整理/)

  const chatSource = source('../views/chat/ChatPage.vue')
  assert.match(chatSource, /function formatSwarmSummary\(value\)/)

  const profileSource = source('../views/profile/ProfilePage.vue')
  assert.match(profileSource, /<button[\s\S]*?@click="handleLogout"/)
})
