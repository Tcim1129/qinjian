import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildSoloConnectionHealth,
  buildSoloSystemTasks,
  buildSoloTaskPayload,
} from './soloWorkspace.js'

test('buildSoloSystemTasks seeds three self-directed tasks for the current day', () => {
  const tasks = buildSoloSystemTasks({ isoDate: '2026-04-22', streak: 4 })

  assert.equal(tasks.length, 3)
  assert.equal(tasks[0].source, 'system')
  assert.equal(tasks[0].target_scope, 'self')
  assert.equal(tasks[1].title.includes('发前'), true)
})

test('buildSoloTaskPayload keeps only current-day tasks and adds a solo note', () => {
  const payload = buildSoloTaskPayload({
    isoDate: '2026-04-22',
    streak: 2,
    tasks: [
      {
        id: 'today-root',
        title: '今天任务',
        description: '今天做',
        source: 'manual',
        target_scope: 'self',
        parent_task_id: null,
        status: 'pending',
        due_date: '2026-04-22',
        created_at: '2026-04-22T10:00:00.000Z',
      },
      {
        id: 'yesterday-root',
        title: '昨天任务',
        description: '昨天做',
        source: 'manual',
        target_scope: 'self',
        parent_task_id: null,
        status: 'pending',
        due_date: '2026-04-21',
        created_at: '2026-04-21T10:00:00.000Z',
      },
    ],
  })

  assert.equal(payload.tasks.length, 1)
  assert.equal(payload.tasks[0].id, 'today-root')
  assert.equal(payload.daily_pack_label, '单人整理')
  assert.match(payload.daily_note, /今天|节奏/)
})

test('buildSoloConnectionHealth rewards completed connection plans', () => {
  const today = new Date().toISOString()
  const payload = buildSoloConnectionHealth([
    { id: '1', status: 'completed', created_at: today },
    { id: '2', status: 'pending', created_at: today },
  ])

  assert.equal(payload.completed_count, 1)
  assert.equal(payload.pending_count, 1)
  assert.equal(payload.plan_count, 2)
  assert.equal(payload.health_index >= 50, true)
})
