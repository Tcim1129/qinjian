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

test('getMissingBackgroundFields reports the specific missing background item', () => {
  assert.deepEqual(
    getMissingBackgroundFields({
      moodScore: 8,
      interactionFreq: null,
      initiative: 'me',
      deepConversation: false,
      taskCompleted: true,
    }),
    ['互动频率'],
  )
})

test('getManualCheckinValidation rejects filled content when one background item is missing', () => {
  assert.deepEqual(
    getManualCheckinValidation({
      content: '今天先把这句写下来。',
      moodScore: 7,
      interactionFreq: 4,
      initiative: '',
      deepConversation: true,
      taskCompleted: false,
    }),
    {
      normalizedManualContent: '今天先把这句写下来。',
      missingBackgroundFields: ['谁先开口'],
      isBackgroundComplete: false,
      canSubmitManualCheckin: false,
    },
  )
})

test('getManualCheckinValidation allows image summary fallback when background is complete', () => {
  assert.deepEqual(
    getManualCheckinValidation({
      content: '   ',
      imageAnalysisSummary: '今天聊天时的气氛明显比昨天更松',
      moodScore: 6,
      interactionFreq: 5,
      initiative: 'partner',
      deepConversation: false,
      taskCompleted: true,
    }),
    {
      normalizedManualContent: '图片记录：今天聊天时的气氛明显比昨天更松',
      missingBackgroundFields: [],
      isBackgroundComplete: true,
      canSubmitManualCheckin: true,
    },
  )
})

test('getManualCheckinValidation keeps restored incomplete drafts unsubmitable', () => {
  const restoredDraft = {
    content: '晚饭那句还卡在心里。',
    moodScore: 5,
    interactionFreq: 3,
    initiative: 'equal',
    deepConversation: null,
    taskCompleted: false,
  }

  const validation = getManualCheckinValidation(restoredDraft)

  assert.equal(validation.canSubmitManualCheckin, false)
  assert.deepEqual(validation.missingBackgroundFields, ['有没有深聊'])
})
