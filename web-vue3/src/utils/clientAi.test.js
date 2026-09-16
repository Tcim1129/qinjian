import test from 'node:test'
import assert from 'node:assert/strict'

import { analyzeEmotion, buildClientGuidance } from './clientAi.js'

test('analyzeEmotion returns a score and Chinese labels for voice-style emotion text', () => {
  const result = analyzeEmotion('今天我其实不是想吵架，我只是希望对方能先听懂我的委屈。')

  assert.equal(result.sentiment, 'negative')
  assert.equal(result.sentimentLabel, '偏负向')
  assert.equal(result.moodLabel, '委屈')
  assert.equal(typeof result.score, 'number')
  assert.ok(result.score >= 5)
})

test('analyzeEmotion skips negated mood and recognizes emotional resolution', () => {
  const result = analyzeEmotion('我现在已经不焦虑了，反而慢慢平静下来了。')

  assert.equal(result.sentiment, 'positive')
  assert.equal(result.moodLabel, '平静')
  assert.equal(result.primaryMood, '平静')
  assert.deepEqual(result.secondaryMoods, [])
  assert.ok(!result.moodTags.includes('焦虑'))
})

test('analyzeEmotion keeps mixed moods and prefers the heavier primary mood', () => {
  const result = analyzeEmotion('我其实很累，但还是期待这周末能和你好好待一会儿。')

  assert.equal(result.sentiment, 'negative')
  assert.equal(result.moodLabel, '疲惫')
  assert.equal(result.primaryMood, '疲惫')
  assert.ok(result.moodTags.includes('期待'))
  assert.ok(result.secondaryMoods.includes('期待'))
  assert.equal(result.emotionWeights[0]?.tag, '疲惫')
})

test('analyzeEmotion removes negated mood from the result list', () => {
  const result = analyzeEmotion('我不是生气，我只是很难过也有点委屈。')

  assert.equal(result.moodLabel, '委屈')
  assert.equal(result.primaryMood, '委屈')
  assert.ok(!result.moodTags.includes('生气'))
})

test('buildClientGuidance prefers privacy-aware image retention guidance', () => {
  const result = buildClientGuidance({
    device_meta: {
      image: {
        storage: {
          mode: 'analysis_only',
        },
      },
    },
    risk_level: 'none',
    intent: 'daily',
    upload_policy: 'full',
  })

  assert.equal(result, '这张图只保留分析结果。')
})
