import test from 'node:test'
import assert from 'node:assert/strict'

import {
  getManualCheckinValidation,
  getMissingBackgroundFields,
  normalizeManualCheckinContent,
} from './checkinForm.js'

test('normalizeManualCheckinContent falls back to image analysis summary', () => {
  assert.equal(
    normalizeManualCheckinContent({
      content: '   ',
      imageAnalysisSummary: '两个人在晚饭时把卡住的话题重新说开了',
    }),
    '图片记录：两个人在晚饭时把卡住的话题重新说开了',
  )
})

test('getMissingBackgroundFields no longer requires the removed 5 background items', () => {
  assert.deepEqual(getMissingBackgroundFields({}), [])
})

test('getManualCheckinValidation allows submitting non-empty text without extra scoring fields', () => {
  assert.deepEqual(
    getManualCheckinValidation({
      content: '今天先把这句写下来。',
    }),
    {
      normalizedManualContent: '今天先把这句写下来。',
      missingBackgroundFields: [],
      isBackgroundComplete: true,
      canSubmitManualCheckin: true,
    },
  )
})

test('getManualCheckinValidation allows image summary fallback without extra scoring fields', () => {
  assert.deepEqual(
    getManualCheckinValidation({
      content: '   ',
      imageAnalysisSummary: '今天聊天时的气氛明显比昨天更松',
    }),
    {
      normalizedManualContent: '图片记录：今天聊天时的气氛明显比昨天更松',
      missingBackgroundFields: [],
      isBackgroundComplete: true,
      canSubmitManualCheckin: true,
    },
  )
})

test('getManualCheckinValidation blocks submission when both text and image summary are empty', () => {
  assert.deepEqual(
    getManualCheckinValidation({
      content: '   ',
      imageAnalysisSummary: '',
    }),
    {
      normalizedManualContent: '',
      missingBackgroundFields: [],
      isBackgroundComplete: true,
      canSubmitManualCheckin: false,
    },
  )
})
