import assert from 'node:assert/strict'
import test from 'node:test'

import * as feedback from './aiWaitFeedback.js'

const {
  AI_WAITING_NOTICE,
  VOICE_TRANSCRIPTION_WAITING_NOTICE,
} = feedback

test('AI waiting notices tell users to wait and explain the one minute cap', () => {
  assert.match(AI_WAITING_NOTICE, /请稍等/)
  assert.match(AI_WAITING_NOTICE, /1 分钟/)
  assert.match(VOICE_TRANSCRIPTION_WAITING_NOTICE, /转写录音/)
  assert.match(VOICE_TRANSCRIPTION_WAITING_NOTICE, /1 分钟/)
})

test('AI waiting feedback does not advertise timeout fallback results', () => {
  assert.equal('AI_TIMEOUT_FALLBACK_NOTICE' in feedback, false)
  assert.equal('isAiTimeoutFallback' in feedback, false)
})
