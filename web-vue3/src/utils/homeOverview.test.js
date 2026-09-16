import test from 'node:test'
import assert from 'node:assert/strict'

import { buildHomeOverview } from './homeOverview.js'

test('paired home overview prefers real pending tasks and milestones', () => {
  const overview = buildHomeOverview({
    relationshipView: {
      kind: 'paired',
      relationLabel: '情侣 · 林夏',
      partnerMetricLabel: '对方状态',
    },
    snapshot: {
      todayStatus: {
        my_done: true,
        partner_done: false,
        has_report: true,
        report_status: 'completed',
      },
    },
    crisis: {
      crisis_level: 'moderate',
    },
    tasks: [
      { id: 'task-1', title: '先发一句说明', status: 'pending' },
      { id: 'task-2', title: '约十分钟电话', status: 'pending' },
      { id: 'task-3', title: '记录反馈', status: 'completed' },
    ],
    milestones: [
      { id: 'm-1', title: '第一次认真复盘', date: '2026-02-14' },
    ],
  })

  assert.equal(overview.focus.title, '先看这一期简报')
  assert.match(overview.focus.detail, /简报/)
  assert.deepEqual(
    overview.todoItems.map((item) => item.label),
    ['先发一句说明', '约十分钟电话'],
  )
  assert.equal(overview.statusItems[0].value, '你已写，对方待同步')
  assert.equal(overview.statusItems[1].value, '已整理')
  assert.equal(overview.milestoneItems[0].label, '第一次认真复盘')
  assert.equal(overview.primaryAction.label, '打开简报')
  assert.equal(overview.primaryAction.route, '/report')
  assert.match(overview.primaryAction.slipLabel, /简报/)
})

test('solo home overview stays honest when there is no paired data yet', () => {
  const overview = buildHomeOverview({
    relationshipView: {
      kind: 'solo',
      relationLabel: '单人整理',
      partnerMetricLabel: '当前状态',
    },
    snapshot: {
      todayStatus: {
        my_done: false,
        partner_done: false,
        has_report: false,
      },
    },
    crisis: {},
    tasks: [],
    milestones: [],
  })

  assert.equal(overview.focus.title, '先记下今天发生的事')
  assert.match(overview.focus.detail, /还没有可同步的关系数据/)
  assert.deepEqual(overview.todoItems, [
    { label: '去记录页写下今天的事', note: '先把事实写下来，再决定要不要继续展开。' },
  ])
  assert.equal(overview.statusItems[0].value, '今天还没开始')
  assert.equal(overview.milestoneItems[0].label, '还没有最近节点')
  assert.equal(overview.primaryAction.label, '去记录页')
  assert.equal(overview.primaryAction.route, '/checkin')
  assert.match(overview.primaryAction.slipLabel, /记录页写下今天发生的事/)
})

test('paired home overview keeps the primary action on the next unfinished step before report is ready', () => {
  const overview = buildHomeOverview({
    relationshipView: {
      kind: 'paired',
      relationLabel: '朋友 · 周宁',
      partnerMetricLabel: '对方状态',
    },
    snapshot: {
      todayStatus: {
        my_done: true,
        partner_done: false,
        has_report: false,
      },
    },
    crisis: {
      crisis_level: 'mild',
    },
    tasks: [
      { id: 'task-1', title: '先发一句说明', status: 'pending' },
    ],
    milestones: [],
  })

  assert.equal(overview.primaryAction.label, '继续下一步')
  assert.equal(overview.primaryAction.route, '/challenges')
  assert.match(overview.primaryAction.slipLabel, /先发一句说明|下一步/)
})

test('paired home overview shows solo report as pending while waiting for partner sync', () => {
  const overview = buildHomeOverview({
    relationshipView: {
      kind: 'paired',
      relationLabel: '朋友 · 周宁',
      partnerMetricLabel: '对方状态',
    },
    snapshot: {
      todayStatus: {
        my_done: true,
        partner_done: false,
        has_report: false,
        has_solo_report: true,
        solo_report_status: 'pending',
      },
    },
    crisis: {},
    tasks: [],
    milestones: [],
  })

  assert.equal(overview.primaryAction.route, '/report')
  assert.equal(overview.primaryAction.buttonLabel, '查看整理进度')
  assert.equal(overview.focus.title, '先看你的这一份正在整理')
  assert.equal(overview.statusItems[1].value, '你的这一份整理中')
  assert.equal(overview.todoItems[0].label, '查看整理进度')
})

test('paired home overview keeps relation-state action literal while waiting for partner sync', () => {
  const overview = buildHomeOverview({
    relationshipView: {
      kind: 'paired',
      relationLabel: '朋友 · 周宁',
      partnerMetricLabel: '对方状态',
    },
    snapshot: {
      todayStatus: {
        my_done: true,
        partner_done: false,
        has_report: false,
        has_solo_report: false,
      },
    },
    crisis: {
      crisis_level: 'mild',
    },
    tasks: [],
    milestones: [],
  })

  assert.equal(overview.primaryAction.route, '/pair')
  assert.equal(overview.primaryAction.buttonLabel, '查看关系状态')
  assert.equal(overview.primaryAction.slipLabel, '对方还没同步，先看关系状态')
  assert.equal(overview.focus.title, '先看关系状态')
  assert.deepEqual(overview.todoItems, [
    { label: '查看关系状态', note: '先把这段关系推进到下一步，再决定后面的动作。' },
  ])
})
