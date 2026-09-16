const BACKGROUND_FIELD_RULES = [
  {
    key: 'moodScore',
    label: '今天整体感受',
    isMissing: (value) => value == null,
  },
  {
    key: 'interactionFreq',
    label: '互动频率',
    isMissing: (value) => value == null,
  },
  {
    key: 'initiative',
    label: '谁先开口',
    isMissing: (value) => !String(value ?? '').trim(),
  },
  {
    key: 'deepConversation',
    label: '有没有深聊',
    isMissing: (value) => value == null,
  },
  {
    key: 'taskCompleted',
    label: '之前的约定',
    isMissing: (value) => value == null,
  },
]

export function normalizeManualCheckinContent({ content = '', imageAnalysisSummary = '' } = {}) {
  const normalizedContent = String(content || '').trim()
  if (normalizedContent) return normalizedContent

  const normalizedImageSummary = String(imageAnalysisSummary || '').trim()
  return normalizedImageSummary ? `图片记录：${normalizedImageSummary}` : ''
}

export function getMissingBackgroundFields(form = {}) {
  return BACKGROUND_FIELD_RULES
    .filter(({ key, isMissing }) => isMissing(form[key]))
    .map(({ label }) => label)
}

export function getManualCheckinValidation({
  content = '',
  imageAnalysisSummary = '',
  moodScore = null,
  interactionFreq = null,
  initiative = '',
  deepConversation = null,
  taskCompleted = null,
} = {}) {
  const normalizedManualContent = normalizeManualCheckinContent({
    content,
    imageAnalysisSummary,
  })
  const missingBackgroundFields = getMissingBackgroundFields({
    moodScore,
    interactionFreq,
    initiative,
    deepConversation,
    taskCompleted,
  })
  const isBackgroundComplete = missingBackgroundFields.length === 0

  return {
    normalizedManualContent,
    missingBackgroundFields,
    isBackgroundComplete,
    canSubmitManualCheckin: Boolean(normalizedManualContent) && isBackgroundComplete,
  }
}
