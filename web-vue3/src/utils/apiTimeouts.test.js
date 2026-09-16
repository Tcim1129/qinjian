import assert from 'node:assert/strict'
import test from 'node:test'

import {
  AI_INTERACTION_TIMEOUT_MS,
  DEFAULT_API_TIMEOUT_MS,
  MESSAGE_SIMULATION_TIMEOUT_MS,
  normalizeApiErrorMessage,
} from './apiTimeouts.js'

test('message simulation timeout uses the same one minute user-facing cap', () => {
  assert.equal(DEFAULT_API_TIMEOUT_MS, 15_000)
  assert.equal(AI_INTERACTION_TIMEOUT_MS, 60_000)
  assert.equal(MESSAGE_SIMULATION_TIMEOUT_MS, AI_INTERACTION_TIMEOUT_MS)
})

test('regular API timeout errors use a generic user-facing Chinese message', () => {
  assert.equal(
    normalizeApiErrorMessage({
      code: 'ECONNABORTED',
      config: { timeout: DEFAULT_API_TIMEOUT_MS },
      message: 'timeout of 15000ms exceeded',
    }),
    '这次处理有点慢，请稍后再试'
  )
})

test('AI interaction timeout errors explain the one minute limit', () => {
  assert.equal(
    normalizeApiErrorMessage({
      code: 'ECONNABORTED',
      config: { timeout: AI_INTERACTION_TIMEOUT_MS },
      message: 'timeout of 60000ms exceeded',
    }),
    '处理超过 1 分钟，已自动超时，请稍后再试'
  )
})

test('server error messages still take precedence over client timeout text', () => {
  assert.equal(
    normalizeApiErrorMessage({
      response: {
        data: {
          detail: '看得有点频繁了，请稍后再试',
        },
      },
      message: 'Request failed with status code 429',
    }),
    '看得有点频繁了，请稍后再试'
  )
})
