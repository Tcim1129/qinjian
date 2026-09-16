import test from 'node:test'
import assert from 'node:assert/strict'

import {
  extractReportInsights,
  extractReportRecommendations,
  firstNonEmptyList,
  normalizeReportList,
  reportHasDisplayContent,
} from './reportContent.js'

test('normalizeReportList turns strings into one-item arrays and ignores empties', () => {
  assert.deepEqual(normalizeReportList('  先缓一缓  '), ['先缓一缓'])
  assert.deepEqual(normalizeReportList(['', '先发一句说明', null]), ['先发一句说明'])
  assert.deepEqual(normalizeReportList(null), [])
})

test('firstNonEmptyList skips empty arrays and finds the first real content', () => {
  assert.deepEqual(
    firstNonEmptyList([
      [],
      ['先确认情绪'],
      ['这条不该被选中'],
    ]),
    ['先确认情绪'],
  )
})

test('extractReportInsights uses later fallback fields when earlier arrays are empty', () => {
  const report = {
    content: {
      highlights: [],
      weekly_highlights: [],
      strengths: ['这次能把委屈说出来了'],
    },
    key_insights: ['这条不该被选中'],
  }

  assert.deepEqual(extractReportInsights(report), ['这次能把委屈说出来了'])
})

test('extractReportRecommendations uses nested and top-level fallback fields correctly', () => {
  const report = {
    content: {
      action_plan: [],
      next_month_goals: [],
      recommendations: ['先把今天那句最在意的话说完整'],
    },
    recommendations: [],
  }

  assert.deepEqual(extractReportRecommendations(report), ['先把今天那句最在意的话说完整'])
})

test('reportHasDisplayContent hides pending placeholders and keeps completed content visible', () => {
  assert.equal(reportHasDisplayContent({ status: 'pending', content: null }), false)
  assert.equal(reportHasDisplayContent({ status: 'completed', content: null }), true)
  assert.equal(reportHasDisplayContent({ status: 'pending', content: { insight: '先停一下' } }), true)
})
