const PHONE_REGEX = /(1\d{2})\d{4}(\d{4})/g
const EMAIL_REGEX = /\b([A-Za-z0-9._%+-]{1,3})[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b/g
const WECHAT_REGEX = /\b(wxid_[a-zA-Z0-9_-]{5,}|[a-zA-Z][-_a-zA-Z0-9]{5,19})\b/g
const NAME_REGEX = /((?:我|他|她|ta|TA|对方|对象|伴侣|朋友)?(?:叫|是))([\u4e00-\u9fa5]{2,4})/g
const ADDRESS_HINT_REGEX = /(地址|住在|学校|学院|大学|宿舍|公司|工位|小区|班级|学号|工号)\s*[:：]?\s*([^\n，。；]{2,18})/g

const HIGH_RISK_RULES = [
  { label: '自伤自杀', regex: /自杀|轻生|不想活|想死|结束生命|割腕|跳楼|自残|活着没意思/i },
  { label: '家暴暴力', regex: /家暴|动手打|扇耳光|打我|打她|打他|掐我|掐她|掐他|推我|推她|推他/i },
  { label: '人身威胁', regex: /威胁杀|威胁我|威胁她|威胁他|跟踪我|跟踪她|跟踪他|报复我|报复她|报复他/i },
]

const WATCH_RISK_RULES = [
  { label: '控制限制', regex: /控制|不准我|不让我|查手机|定位我|限制我|监听/i },
  { label: '极端羞辱', regex: /羞辱|侮辱|骂我废物|骂她废物|骂他废物|贬低我|贬低她|贬低他/i },
  { label: '关系升级', regex: /冷战|分手|拉黑|删好友|不信任|失控|吵崩了|吵炸了/i },
]

const EMOTION_RULES = [
  { tag: '开心', tone: 'positive', words: ['开心', '高兴', '快乐', '好开心', '很棒', '轻松'] },
  { tag: '平静', tone: 'positive', words: ['平静', '安心', '稳定', '踏实', '放松'] },
  { tag: '感动', tone: 'positive', words: ['感动', '被看见', '谢谢', '温柔', '拥抱', '理解我'] },
  { tag: '期待', tone: 'positive', words: ['期待', '希望', '想要', '盼着', '准备'] },
  { tag: '焦虑', tone: 'negative', words: ['焦虑', '担心', '害怕', '慌', '不安', '压力', '紧张'] },
  { tag: '委屈', tone: 'negative', words: ['委屈', '难受', '没被理解', '心酸', '憋屈', '被忽略'] },
  { tag: '生气', tone: 'negative', words: ['生气', '愤怒', '火大', '吵架', '气死', '不爽'] },
  { tag: '疲惫', tone: 'negative', words: ['累', '疲惫', '耗尽', '没力气', '撑不住', '麻木'] },
]

const INTENT_RULES = {
  crisis: ['自杀', '自残', '家暴', '威胁', '跟踪', '不想活'],
  emergency: ['吵架', '冷战', '分手', '怎么回', '怎么说', '要不要发', '误会', '沟通'],
  reflection: ['复盘', '总结', '为什么', '规律', '趋势', '回顾', '变化'],
}

const EMOTION_BASE_WEIGHT = {
  positive: 1.2,
  negative: 2.6,
}

const NEGATED_MOOD_PREFIX = /(不|没|没有|不是|并不|并不是|不再|已经不|已经没有|并没有)$/

function isDigit(char) {
  return /\d/.test(String(char || ''))
}

function isStandaloneNumberMatch(text, index, length) {
  const prev = index > 0 ? text[index - 1] : ''
  const next = text[index + length] || ''
  return !isDigit(prev) && !isDigit(next)
}

function collectMatches(regex, text, category) {
  const items = []
  const localRegex = new RegExp(regex.source, regex.flags)
  let match = null
  while ((match = localRegex.exec(text)) !== null) {
    items.push({ category, match: match[0], index: match.index })
    if (!localRegex.global) break
  }
  return items
}

function summarizePii(text) {
  const phoneHits = collectMatches(PHONE_REGEX, text, 'phone').filter((item) => (
    isStandaloneNumberMatch(text, item.index, String(item.match || '').length)
  ))

  const hits = [
    ...phoneHits,
    ...collectMatches(EMAIL_REGEX, text, 'email'),
    ...collectMatches(NAME_REGEX, text, 'name'),
    ...collectMatches(ADDRESS_HINT_REGEX, text, 'address_hint'),
  ]

  const wechatHits = collectMatches(WECHAT_REGEX, text, 'wechat').filter((item) => {
    const token = String(item.match || '').toLowerCase()
    return token.startsWith('wxid_') || token.includes('wechat') || token.includes('vx')
  })
  hits.push(...wechatHits)

  const categories = hits.reduce((acc, item) => {
    acc[item.category] = (acc[item.category] || 0) + 1
    return acc
  }, {})

  return {
    hits,
    summary: {
      total_hits: hits.length,
      categories,
    },
  }
}

function redactText(text) {
  return text
    .replace(PHONE_REGEX, (match, prefix, suffix, offset, source) => (
      isStandaloneNumberMatch(source, offset, match.length)
        ? `${prefix}****${suffix}`
        : match
    ))
    .replace(EMAIL_REGEX, '$1***@$2')
    .replace(NAME_REGEX, '$1[姓名已隐藏]')
    .replace(ADDRESS_HINT_REGEX, '$1：[位置已隐藏]')
    .replace(/\bwxid_[a-zA-Z0-9_-]{5,}\b/g, '[微信号已隐藏]')
    .replace(/\b([a-zA-Z][-_a-zA-Z0-9]{5,19})\b/g, (token) => {
      if (/^(wxid_|vx|wechat)/i.test(token)) return '[账号已隐藏]'
      return token
    })
}

function detectRisk(text) {
  const highHits = HIGH_RISK_RULES.filter((rule) => rule.regex.test(text)).map((rule) => rule.label)
  if (highHits.length) return { level: 'high', hits: highHits }
  const watchHits = WATCH_RISK_RULES.filter((rule) => rule.regex.test(text)).map((rule) => rule.label)
  if (watchHits.length) return { level: 'watch', hits: watchHits }
  return { level: 'none', hits: [] }
}

function classifyIntent(text, riskLevel) {
  if (riskLevel === 'high') return 'crisis'
  const normalized = String(text || '').toLowerCase()
  const emergencyScore = INTENT_RULES.emergency.filter((keyword) => normalized.includes(keyword)).length
  const reflectionScore = INTENT_RULES.reflection.filter((keyword) => normalized.includes(keyword)).length
  if (emergencyScore > 0) return 'emergency'
  if (reflectionScore > 0) return 'reflection'
  return 'daily'
}

function countEmotionWord(text, word) {
  let count = 0
  let index = text.indexOf(word)
  while (index !== -1) {
    const prefix = text.slice(Math.max(0, index - 8), index)
    if (!NEGATED_MOOD_PREFIX.test(prefix)) count += 1
    index = text.indexOf(word, index + word.length)
  }
  return count
}

export function analyzeEmotion(text) {
  const normalized = String(text || '').trim()
  if (!normalized) {
    return {
      sentiment: 'neutral',
      sentimentLabel: '等你写下',
      moodTags: [],
      moodLabel: '等你写下',
      primaryMood: null,
      secondaryMoods: [],
      emotionWeights: [],
      score: 0,
      confidence: 0,
      reason: '先留下一句原话，亲健会在本地判断情绪倾向。',
    }
  }

  const matches = EMOTION_RULES.map((rule) => ({
    ...rule,
    rawScore: rule.words.reduce((sum, word) => sum + countEmotionWord(normalized, word), 0),
  }))
    .filter((rule) => rule.rawScore > 0)
    .map((rule) => ({
      tag: rule.tag,
      tone: rule.tone,
      score: Number((rule.rawScore * (EMOTION_BASE_WEIGHT[rule.tone] || 1)).toFixed(2)),
    }))
    .sort((a, b) => b.score - a.score)

  const positive = matches.filter((rule) => rule.tone === 'positive').reduce((sum, rule) => sum + rule.score, 0)
  const negative = matches.filter((rule) => rule.tone === 'negative').reduce((sum, rule) => sum + rule.score, 0)
  const sentiment = negative > positive ? 'negative' : positive > negative ? 'positive' : 'neutral'
  const moodTags = matches
    .slice(0, 3)
    .map((rule) => rule.tag)

  const moodLabel = moodTags[0] || (sentiment === 'negative' ? '有压力' : sentiment === 'positive' ? '有修复感' : '平静')
  const confidence = matches.length ? Math.min(0.95, 0.55 + matches[0].score * 0.16 + moodTags.length * 0.08) : 0.35
  const score = matches.length ? Math.min(10, Math.round((positive + negative) * 2)) : 0

  return {
    sentiment,
    sentimentLabel: sentiment === 'negative' ? '偏负向' : sentiment === 'positive' ? '偏正向' : '平静',
    moodTags,
    moodLabel,
    primaryMood: moodTags[0] || null,
    secondaryMoods: moodTags.slice(1),
    emotionWeights: matches,
    score,
    confidence: Number(confidence.toFixed(2)),
    reason: moodTags.length
      ? `识别到 ${moodTags.join('、')} 相关表达。`
      : '暂未发现明显情绪词，先按日常记录处理。',
  }
}

export function determineUploadPolicy(precheck, prefs = {}) {
  const privacyMode = prefs.privacyMode === 'local_first' ? 'local_first' : 'cloud'
  if (privacyMode !== 'local_first') return 'full'
  if (!window.navigator.onLine) return 'local_only'
  if ((precheck?.risk_level || 'none') === 'high') return 'local_only'
  if ((precheck?.pii_summary?.total_hits || 0) > 0) return 'redacted_only'
  return 'full'
}

export function precheckText(text, options = {}) {
  const content = String(text || '').trim()
  const privacyMode = options.privacyMode === 'local_first' ? 'local_first' : 'cloud'
  const aiAssistEnabled = options.aiAssistEnabled !== false
  const pii = summarizePii(content)
  const risk = detectRisk(content)
  const emotion = aiAssistEnabled ? analyzeEmotion(content) : analyzeEmotion('')
  const intent = aiAssistEnabled ? classifyIntent(content, risk.level) : (risk.level === 'high' ? 'crisis' : 'daily')
  const redactedText = pii.summary.total_hits > 0 ? redactText(content) : content
  const sourceTypes = ['text']
  if (options.deviceMeta?.image) sourceTypes.push('image')
  if (options.deviceMeta?.voice) sourceTypes.push('voice')

  const clientTags = []
  if (intent !== 'daily') clientTags.push(intent)
  if (risk.level !== 'none') clientTags.push(`risk:${risk.level}`)
  if ((pii.summary?.total_hits || 0) > 0) clientTags.push('contains_pii')
  if (emotion.sentiment !== 'neutral') clientTags.push(`sentiment:${emotion.sentiment}`)
  if (emotion.moodTags?.length) clientTags.push(...emotion.moodTags.map((tag) => `emotion:${tag}`))
  if (/截图|聊天记录|微信|消息/.test(content)) clientTags.push('message_context')
  if (/异地|距离|见面/.test(content)) clientTags.push('distance_context')
  if (options.deviceMeta?.voice) clientTags.push('voice_attached')
  if (options.deviceMeta?.image) clientTags.push('image_attached')

  const precheck = {
    source_type: sourceTypes.length > 1 ? 'mixed' : sourceTypes[0],
    intent,
    risk_level: risk.level,
    risk_hits: risk.hits,
    pii_summary: pii.summary,
    privacy_mode: privacyMode,
    upload_policy: 'full',
    redacted_text: redactedText,
    client_tags: Array.from(new Set(clientTags)),
    device_meta: {
      ...(options.deviceMeta || {}),
      emotion: {
        sentiment: emotion.sentiment,
        mood_label: emotion.moodLabel,
        mood_tags: emotion.moodTags,
        confidence: emotion.confidence,
      },
    },
    ai_assist_enabled: aiAssistEnabled,
    sentiment_hint: emotion.sentiment,
    emotion,
  }

  precheck.upload_policy = determineUploadPolicy(precheck, { privacyMode })
  return precheck
}

export function buildClientGuidance(precheck) {
  if (!precheck) return '写下内容后，亲健会先在本地识别情绪、风险和隐私线索。'
  if (precheck.risk_level === 'high') return '本地识别到高风险信号，建议先停下来，优先找可信任的人或专业支持。'
  if (precheck.intent === 'emergency') return '这次更像正在处理眼前冲突，先让表达降一点刺激，再决定下一步。'
  if (precheck.device_meta?.image?.storage?.mode === 'analysis_only') return '这张图只保留分析结果。'
  if (precheck.upload_policy === 'redacted_only') return '内容里有隐私线索，提交时会优先带上脱敏版本。'
  if (precheck.upload_policy === 'local_only') return '当前更适合先本地留存，等你确认后再同步。'
  if (precheck.intent === 'reflection') return '这次更像复盘材料，后续可以和关系日历一起看变化。'
  return '情绪和上下文已在本地预检，提交后再进入后端深分析。'
}

export function getAudioDuration(file) {
  const objectUrl = URL.createObjectURL(file)
  return new Promise((resolve) => {
    const audio = document.createElement('audio')
    audio.preload = 'metadata'
    audio.onloadedmetadata = () => {
      URL.revokeObjectURL(objectUrl)
      resolve(Number(audio.duration) || null)
    }
    audio.onerror = () => {
      URL.revokeObjectURL(objectUrl)
      resolve(null)
    }
    audio.src = objectUrl
  })
}

export async function analyzeAudioSignal(file) {
  if (typeof window.AudioContext === 'undefined' && typeof window.webkitAudioContext === 'undefined') {
    return { silence_ratio: null, peak_level: null }
  }

  const AudioContextCtor = window.AudioContext || window.webkitAudioContext
  const context = new AudioContextCtor()
  try {
    const buffer = await file.arrayBuffer()
    const audioBuffer = await context.decodeAudioData(buffer.slice(0))
    const channel = audioBuffer.getChannelData(0)
    if (!channel?.length) return { silence_ratio: null, peak_level: null }

    let silentSamples = 0
    let peak = 0
    for (let index = 0; index < channel.length; index += 1) {
      const amplitude = Math.abs(channel[index])
      if (amplitude < 0.015) silentSamples += 1
      if (amplitude > peak) peak = amplitude
    }

    return {
      silence_ratio: Number((silentSamples / channel.length).toFixed(3)),
      peak_level: Number(peak.toFixed(3)),
    }
  } catch {
    return { silence_ratio: null, peak_level: null }
  } finally {
    context.close?.().catch(() => null)
  }
}

export async function inspectVoiceFile(file) {
  const [durationSeconds, signal] = await Promise.all([
    getAudioDuration(file).catch(() => null),
    analyzeAudioSignal(file),
  ])

  const tags = []
  if ((durationSeconds || 0) > 0 && durationSeconds < 2) tags.push('short_voice')
  if ((signal.silence_ratio || 0) > 0.55) tags.push('mostly_silent_voice')

  return {
    file,
    deviceMeta: {
      mime_type: file.type,
      size_bytes: file.size,
      duration_seconds: durationSeconds ? Number(durationSeconds.toFixed(1)) : null,
      silence_ratio: signal.silence_ratio,
      peak_level: signal.peak_level,
    },
    clientTags: tags,
  }
}

