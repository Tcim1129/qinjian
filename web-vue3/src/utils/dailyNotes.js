export const MAX_DAILY_NOTE_LENGTH = 28

export const DAILY_NOTE_CANDIDATES = [
  '今天先把联系接回来，不用一次聊很多。',
  '先说容易接上的话，今天不翻旧账。',
  '给彼此留一点呼吸空隙，慢一点没关系。',
  '先把今天过顺，别急着把心结一次解开。',
  '分享点轻松的小事，不用刻意找严肃话题。',
  '不用每句话都秒回，知道彼此在就挺安心。',
  '晚上喝杯热饮，把白天攒的疲惫先放一放。',
  '两个人步调一致最舒服，今天按自然节奏来。',
  '把今天最想分享的一件小事，留到睡前聊。',
  '哪怕只是发个表情包，也是今天的温暖连接。',
  '今天先挑两三件轻松小事，找回舒服的节奏。',
  '遇到累的时候先抱抱，话留着心平气和再说。',
]

export function clampDailyNote(note) {
  if (!note || typeof note !== 'string') return ''
  const trimmed = note.trim()
  return trimmed.length > MAX_DAILY_NOTE_LENGTH ? trimmed.slice(0, MAX_DAILY_NOTE_LENGTH) : trimmed
}

export function getNextDailyNote(currentNote) {
  const normalized = (currentNote || '').trim()
  const currentIndex = DAILY_NOTE_CANDIDATES.findIndex((item) => item === normalized)
  if (currentIndex === -1) {
    return DAILY_NOTE_CANDIDATES[0]
  }
  return DAILY_NOTE_CANDIDATES[(currentIndex + 1) % DAILY_NOTE_CANDIDATES.length]
}
