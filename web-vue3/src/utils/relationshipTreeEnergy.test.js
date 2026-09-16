import test from 'node:test'
import assert from 'node:assert/strict'

import {
  collectEnergyNodeLocally,
  normalizeEnergyNodes,
} from './relationshipTreeEnergy.js'

test('normalizes backend energy nodes into stable clickable node copy', () => {
  const nodes = normalizeEnergyNodes([
    {
      key: 'my_record',
      label: '记录',
      points: 10,
      state: 'available',
      collected: false,
      available: true,
      hint: '点击抓取成长值',
    },
    {
      key: 'partner_record',
      label: '同步',
      points: 8,
      state: 'locked',
      collected: false,
      available: false,
      hint: '等对方同步',
    },
  ])

  assert.deepEqual(nodes.map((node) => node.key), ['my_record', 'partner_record', 'small_repair'])
  assert.equal(nodes[0].label, '记录')
  assert.equal(nodes[0].value, '+10')
  assert.equal(nodes[0].state, 'available')
  assert.equal(nodes[1].hint, '等对方同步')
  assert.equal(nodes[2].hint, '完成小行动后出现')
})

test('maps legacy display bubbles to the new node vocabulary', () => {
  const nodes = normalizeEnergyNodes([
    { label: '记录', value: '+12' },
    { label: '共情', value: '+8' },
    { label: '缓和', value: '+16' },
  ])

  assert.equal(nodes[0].key, 'my_record')
  assert.equal(nodes[0].points, 12)
  assert.equal(nodes[0].available, true)
  assert.equal(nodes[1].label, '同步')
  assert.equal(nodes[2].label, '小行动')
})

test('collects a demo energy node locally and prevents collecting it again', () => {
  const tree = {
    growth_points: 30,
    next_level_at: 50,
    energy_nodes: [
      { key: 'my_record', label: '记录', points: 10, state: 'available', available: true },
      { key: 'partner_record', label: '同步', points: 8, state: 'locked', available: false },
    ],
  }

  const collected = collectEnergyNodeLocally(tree, 'my_record')
  assert.equal(collected.growth_points, 40)
  assert.equal(collected.points_added, 10)
  assert.equal(collected.can_water, false)
  assert.equal(collected.energy_nodes[0].state, 'collected')
  assert.equal(collected.energy_nodes[0].hint, '已抓取')

  assert.throws(
    () => collectEnergyNodeLocally(collected, 'my_record'),
    /已经抓取过/,
  )
})
