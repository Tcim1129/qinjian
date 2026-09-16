import test from 'node:test'
import assert from 'node:assert/strict'

import { buildPairStatusSummary } from './pairStatusSummary.js'
import { buildRelationshipSpaceDetailModel, buildRelationshipSpaceModel } from './relationshipSpaceModel.js'

test('buildRelationshipSpaceModel maps score and trend into stable node positions', () => {
  const model = buildRelationshipSpaceModel({
    me: { nickname: '阿青' },
    currentPairId: 'pair-1',
    pairs: [
      { id: 'pair-1', type: 'couple', status: 'active', custom_partner_nickname: '林夏' },
      { id: 'pair-2', type: 'friend', status: 'active', custom_partner_nickname: '周宁' },
    ],
    metricsByPairId: {
      'pair-1': { score: 82, trend: 'up', summary: '今天互动顺了一点', nextAction: '约一个 10 分钟电话' },
      'pair-2': { score: 63, trend: 'down', summary: '最近有点别扭', nextAction: '先发一条简单问候' },
    },
  })

  assert.equal(model.center.label, '阿青')
  assert.equal(model.nodes[0].pairId, 'pair-1')
  assert.ok(model.nodes[0].distance < model.nodes[1].distance)
  assert.equal(model.nodes[0].trend, 'up')
  assert.match(model.nodes[0].sidebar.summary, /顺|回暖|稳定/)
  assert.equal(model.selectedPairId, 'pair-1')
  assert.equal(model.selectedSidebar.title, '林夏')
  assert.match(model.selectedSidebar.nextAction, /电话|沟通|解释/)
})

test('buildRelationshipSpaceDetailModel gathers hero, moments, and actions for a selected relationship', () => {
  const detail = buildRelationshipSpaceDetailModel({
    me: { nickname: '阿青' },
    pair: {
      id: 'pair-1',
      type: 'couple',
      status: 'active',
      custom_partner_nickname: '林夏',
    },
    metricsByPairId: {
      'pair-1': {
        score: 78,
        trend: 'up',
        summary: '今天双方都愿意补一句解释。',
        nextAction: '先约一个 10 分钟电话。',
      },
    },
    moments: ['昨天因为回复慢有误会', '今天双方愿意补一句解释'],
  })

  assert.equal(detail.hero.title, '阿青 · 林夏')
  assert.equal(detail.hero.score, 78)
  assert.match(detail.hero.stageLabel, /变好|稳定|紧绷|别扭|冷/)
  assert.equal(detail.moments.length, 2)
  assert.match(detail.primaryAction.label, /电话|建议|记录|时间线/)
})

test('buildRelationshipSpaceModel groups overflowing relationships without hiding the selected one', () => {
  const pairs = Array.from({ length: 14 }, (_, index) => ({
    id: `pair-${index + 1}`,
    type: 'friend',
    status: 'active',
    custom_partner_nickname: `朋友${index + 1}`,
  }))

  const metricsByPairId = Object.fromEntries(
    pairs.map((pair, index) => [
      pair.id,
      {
        score: 90 - index * 3,
        trend: index % 3 === 0 ? 'up' : 'flat',
        summary: `${pair.custom_partner_nickname} 最近有新的互动`,
        nextAction: `继续和 ${pair.custom_partner_nickname} 保持联系`,
      },
    ])
  )

  const model = buildRelationshipSpaceModel({
    me: { nickname: '阿青' },
    currentPairId: 'pair-14',
    pairs,
    metricsByPairId,
  })

  assert.equal(model.selectedPairId, 'pair-14')
  assert.equal(model.selectedSidebar.title, '朋友14')
  assert.ok(model.nodes.length <= 12)
  assert.ok(model.nodes.some((node) => node.pairId === 'pair-14'))

  const overflowNode = model.nodes.find((node) => node.kind === 'overflow')
  assert.ok(overflowNode)
  assert.equal(overflowNode.pairId, '__overflow__')
  assert.match(overflowNode.label, /\+\d+/)
  assert.match(overflowNode.sidebar.recentSummary, /还有/)
  assert.equal(overflowNode.sidebar.hiddenPairs.length, 3)
  assert.ok(overflowNode.sidebar.hiddenPairs.every((item) => item.pairId !== 'pair-14'))

  const promoted = buildRelationshipSpaceModel({
    me: { nickname: '阿青' },
    currentPairId: overflowNode.sidebar.hiddenPairs[0].pairId,
    pairs,
    metricsByPairId,
  })

  assert.equal(promoted.selectedPairId, overflowNode.sidebar.hiddenPairs[0].pairId)
  assert.ok(promoted.nodes.some((node) => node.pairId === overflowNode.sidebar.hiddenPairs[0].pairId))
})

test('buildRelationshipSpaceModel enters dual-focus mode when a relationship is explicitly focused', () => {
  const model = buildRelationshipSpaceModel({
    me: { nickname: '阿青' },
    currentPairId: 'pair-2',
    focusPairId: 'pair-2',
    pairs: [
      { id: 'pair-1', type: 'couple', status: 'active', custom_partner_nickname: '林夏' },
      { id: 'pair-2', type: 'friend', status: 'active', custom_partner_nickname: '周宁' },
      { id: 'pair-3', type: 'friend', status: 'active', custom_partner_nickname: '顾遥' },
    ],
    metricsByPairId: {
      'pair-1': { score: 82, trend: 'up', summary: '今天互动顺了一点', nextAction: '约一个 10 分钟电话' },
      'pair-2': { score: 63, trend: 'flat', summary: '最近整体稳定', nextAction: '继续保持联系' },
      'pair-3': { score: 54, trend: 'down', summary: '最近有点别扭', nextAction: '发一条简单问候' },
    },
  })

  assert.equal(model.focusNode?.pairId, 'pair-2')
  assert.equal(model.focusNode?.label, '周宁')
  assert.ok(model.nodes.every((node) => node.pairId !== 'pair-2'))
  assert.ok(model.nodes.every((node) => node.distance >= 170))
  assert.ok(model.nodes.every((node) => node.size <= 66))
  assert.ok(model.nodes.every((node) => node.angle < 0))
  assert.ok(model.nodes.every((node) => node.angle > -Math.PI))
})

test('buildRelationshipSpaceModel keeps honest status labels when no real score exists yet', () => {
  const pair = {
    id: 'pair-1',
    type: 'friend',
    status: 'active',
    custom_partner_nickname: '周宁',
  }

  const model = buildRelationshipSpaceModel({
    me: { nickname: '阿青' },
    currentPairId: 'pair-1',
    pairs: [pair],
    metricsByPairId: {
      'pair-1': buildPairStatusSummary({
        pair,
        isCurrent: true,
        inviteCode: 'A6DL4654LY',
      }),
    },
  })

  assert.equal(model.selectedSidebar.scoreHeading, '当前状态')
  assert.equal(model.selectedSidebar.scoreLabel, '已建立')
  assert.match(model.selectedSidebar.trendLabel, /真实记录|已建立/)
  assert.doesNotMatch(model.selectedSidebar.scoreLabel, /\d{2}/)
  assert.equal(model.nodes[0].score, null)
})

test('buildRelationshipSpaceModel leaves scores empty when real-mode metrics are absent', () => {
  const model = buildRelationshipSpaceModel({
    me: { nickname: '阿青' },
    currentPairId: 'pair-1',
    pairs: [
      { id: 'pair-1', type: 'couple', status: 'active', custom_partner_nickname: '林夏' },
      { id: 'pair-2', type: 'friend', status: 'pending', custom_partner_nickname: '周宁' },
    ],
    metricsByPairId: {},
  })

  assert.ok(model.nodes.every((node) => node.score === null))
  assert.equal(model.selectedSidebar.score, null)
  assert.equal(model.selectedSidebar.scoreLabel, '已建立')
  assert.equal(model.selectedSidebar.scoreHeading, '当前状态')
  assert.match(model.selectedSidebar.summary, /已经建立|邀请码/)
})

test('buildRelationshipSpaceDetailModel stays honest when no real metric exists yet', () => {
  const detail = buildRelationshipSpaceDetailModel({
    me: { nickname: '阿青' },
    pair: {
      id: 'pair-1',
      type: 'friend',
      status: 'active',
      custom_partner_nickname: '周宁',
    },
    metricsByPairId: {},
    moments: [],
  })

  assert.equal(detail.hero.score, null)
  assert.match(detail.hero.stageLabel, /真实记录|已建立/)
  assert.doesNotMatch(detail.hero.stageLabel, /稳定/)
})
