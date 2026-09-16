import assert from 'node:assert/strict'
import test from 'node:test'

import { mergeVoiceTranscriptIntoDraft } from './voiceDraft.js'

test('mergeVoiceTranscriptIntoDraft fills an empty draft with transcript', () => {
  assert.equal(
    mergeVoiceTranscriptIntoDraft('', ' 我想先把这句话说清楚 '),
    '我想先把这句话说清楚'
  )
})

test('mergeVoiceTranscriptIntoDraft appends new transcript on a new line', () => {
  assert.equal(
    mergeVoiceTranscriptIntoDraft('我现在有点着急', '但我还是想好好说'),
    '我现在有点着急\n但我还是想好好说'
  )
})

test('mergeVoiceTranscriptIntoDraft skips duplicate transcript text', () => {
  assert.equal(
    mergeVoiceTranscriptIntoDraft('我想先确认一下。', '想先确认'),
    '我想先确认一下。'
  )
})
