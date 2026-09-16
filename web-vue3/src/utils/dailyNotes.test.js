import test from 'node:test'
import assert from 'node:assert/strict'
import {
  MAX_DAILY_NOTE_LENGTH,
  DAILY_NOTE_CANDIDATES,
  clampDailyNote,
  getNextDailyNote,
} from './dailyNotes.js'

test('all candidate daily notes are within length bounds', () => {
  assert.ok(DAILY_NOTE_CANDIDATES.length >= 8)
  for (const note of DAILY_NOTE_CANDIDATES) {
    assert.ok(note.length <= MAX_DAILY_NOTE_LENGTH, 'Note too long: ' + note)
    assert.ok(note.length >= 10, 'Note too short: ' + note)
  }
})

test('clampDailyNote respects max length and edge cases', () => {
  assert.equal(clampDailyNote(''), '')
  assert.equal(clampDailyNote(null), '')
  assert.equal(clampDailyNote(undefined), '')
  assert.equal(clampDailyNote('  今天先把联系接回来。  '), '今天先把联系接回来。')
  const longNote = '这是一段超过二十八个字的非常非常非常非常非常非常非常非常非常长的每日寄语文本'
  const clamped = clampDailyNote(longNote)
  assert.equal(clamped.length, MAX_DAILY_NOTE_LENGTH)
  assert.equal(clamped, longNote.slice(0, 28))
})

test('getNextDailyNote cycles through candidates smoothly', () => {
  const first = DAILY_NOTE_CANDIDATES[0]
  const second = DAILY_NOTE_CANDIDATES[1]
  assert.equal(getNextDailyNote(first), second)
  assert.equal(getNextDailyNote('non-existent note'), first)
  const last = DAILY_NOTE_CANDIDATES[DAILY_NOTE_CANDIDATES.length - 1]
  assert.equal(getNextDailyNote(last), first)
})
