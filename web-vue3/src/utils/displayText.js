export const RELATIONSHIP_TYPE_LABELS = {
  '': '待双方确认',
  couple: '情侣',
  spouse: '夫妻',
  friend: '朋友',
  bestfriend: '挚友',
  parent: '育儿夫妻',
}

export const CREATABLE_RELATIONSHIP_TYPE_LABELS = {
  friend: RELATIONSHIP_TYPE_LABELS.friend,
  couple: RELATIONSHIP_TYPE_LABELS.couple,
  spouse: RELATIONSHIP_TYPE_LABELS.spouse,
  bestfriend: RELATIONSHIP_TYPE_LABELS.bestfriend,
  parent: RELATIONSHIP_TYPE_LABELS.parent,
}

export const PAIR_STATUS_LABELS = {
  pending: '待确认',
  active: '已建立',
  ended: '已结束',
  approved: '已确认',
  rejected: '未确认',
  cancelled: '已取消',
}

export const MILESTONE_TYPE_LABELS = {
  anniversary: '纪念日',
  proposal: '重要承诺',
  wedding: '婚礼',
  friendship_day: '关系节点',
  custom: '自定义',
}

export const LONG_DISTANCE_ACTIVITY_LABELS = {
  movie: '一起看电影',
  meal: '共享一顿饭',
  chat: '视频深聊',
  gift: '寄一份礼物',
  exercise: '同步运动',
}

export const TASK_CATEGORY_LABELS = {
  communication: '沟通类',
  repair: '缓和类',
  activity: '陪伴类',
  reflection: '调节类',
  connection: '连接类',
}

export const REPORT_TYPE_LABELS = {
  daily: '日报',
  weekly: '周报',
  monthly: '月报',
  solo: '个人简报',
}

export const RISK_LEVEL_LABELS = {
  none: '平稳',
  low: '轻度',
  mild: '轻度',
  watch: '值得留意',
  medium: '中度',
  moderate: '中度',
  high: '高风险',
  severe: '高风险',
}

export const PROTOCOL_TYPE_LABELS = {
  steady_maintenance: '低压维护建议',
  gentle_repair: '轻度缓和建议',
  structured_repair: '分步骤缓和建议',
  de_escalation_protocol: '冲突止损建议',
  conflict_repair_plan: '冲突缓和安排',
}

export const PLAN_TYPE_LABELS = {
  conflict_repair_plan: '冲突缓和安排',
  low_connection_recovery: '低连接缓和安排',
  distance_compensation_plan: '异地连接计划',
  self_regulation_plan: '自我调节计划',
}

export const REACTION_SHIFT_LABELS = {
  stable: '这次心情和最近的节奏差不多，挺平稳的~',
  unknown: '记录还在慢慢沉淀，先看这一次的心情~',
  more_defensive: '这次稍微带了点小刺，可能是委屈坏了想护住自己~',
  more_withdrawn: '这次累得有点想缩回壳子里，需要自己静静~',
  more_urgent: '心里有点着急，特别盼着能快点收到回应~',
  more_repair_oriented: '特别想递个台阶，把气氛暖回来~',
  more_support_seeking: '这会儿心里软软的，特别需要被好好抱抱和哄哄~',
  more_clarifying: '想认真把误会聊开，免得彼此心里留疙瘩~',
  more_reflective: '正在静下心整理思绪，想把日子过得更舒服~',
  shifted: '这次的心情状态和平时不太一样，多给彼此一点耐心~',
}

export const BASELINE_MATCH_LABELS = {
  match: '和你平时差不多',
  slight_deviation: '比平时更容易让关系紧张',
  strong_deviation: '这次和你平时差别比较大',
  insufficient_history: '记录还不够，先按常见情况看',
}

export const DECISION_FEEDBACK_LABELS = {
  judgement_too_high: '说重了',
  judgement_too_low: '说轻了',
  direction_off: '方向不太对',
  copy_unnatural: '说法不顺',
  acceptable: '还可以',
}

const INLINE_CODE_LABELS = {
  ...RISK_LEVEL_LABELS,
  ...PLAN_TYPE_LABELS,
  ...PROTOCOL_TYPE_LABELS,
  ...REACTION_SHIFT_LABELS,
  ...BASELINE_MATCH_LABELS,
  ...DECISION_FEEDBACK_LABELS,
  rule_engine_with_safety_first: '先顾安全的规则判断',
  long_distance: '异地',
  reduce_load: '先降负荷',
  steady: '稳步推进',
  deepen: '加深连接',
  long: '偏长',
  medium: '适中',
  short: '偏短',
  intense: '强烈',
  gentle: '温和',
  warm: '温暖',
  neutral: '平稳',
  withdraw: '退开',
  defend: '防御',
  urgent: '急着追问',
  repair: '缓和',
  seek_support: '寻求安慰',
  clarify: '澄清',
  reflect: '复盘',
  zh: '中文',
  en: '英文',
  mixed: '中英混合',
}

function normalizeKey(value) {
  return String(value ?? '').trim()
}

export function labelFrom(map, value, fallback) {
  const key = normalizeKey(value)
  return map[key] || fallback
}

export function relationshipTypeLabel(value) {
  return labelFrom(RELATIONSHIP_TYPE_LABELS, value, '待双方确认')
}

export function pairStatusLabel(value) {
  return labelFrom(PAIR_STATUS_LABELS, value, '待确认')
}

export function milestoneTypeLabel(value) {
  return labelFrom(MILESTONE_TYPE_LABELS, value, '重要时刻')
}

export function longDistanceActivityLabel(value) {
  return labelFrom(LONG_DISTANCE_ACTIVITY_LABELS, value, '同步活动')
}

export function taskCategoryLabel(value) {
  return labelFrom(TASK_CATEGORY_LABELS, value, '安排类')
}

export function reportTypeLabel(value) {
  return labelFrom(REPORT_TYPE_LABELS, value, '简报')
}

export function riskLevelLabel(value) {
  return labelFrom(RISK_LEVEL_LABELS, value, '待评估')
}

export function protocolTypeLabel(value) {
  return labelFrom(PROTOCOL_TYPE_LABELS, value, '缓和建议')
}

export function baselineMatchLabel(value) {
  return labelFrom(BASELINE_MATCH_LABELS, value, '还没有基线判断')
}

export function decisionFeedbackLabel(value) {
  return labelFrom(DECISION_FEEDBACK_LABELS, value, '可接受')
}

export function reactionShiftLabel(value) {
  const key = normalizeKey(value)
  return REACTION_SHIFT_LABELS[key] || readableChineseFallback(key, '这次和你平时的反应方式有什么不同，亲健还没看清楚。')
}

export function messageRoleLabel(role) {
  return role === 'user' ? '我' : '亲健'
}

export function displaySystemName(value) {
  const text = normalizeKey(value)
  if (!text) return '亲健整理方式'
  return translateInlineCodes(text.replace(/\bv1\b/gi, '第一版'))
}

export function displayModelFamily(value) {
  const text = normalizeKey(value)
  if (!text) return '记录和反馈一起看'
  return translateInlineCodes(text)
}

export function translateInlineCodes(value) {
  let text = String(value ?? '')
  for (const [code, label] of Object.entries(INLINE_CODE_LABELS)) {
    const pattern = new RegExp(`(^|[^A-Za-z0-9_])${escapeRegExp(code)}(?=$|[^A-Za-z0-9_])`, 'g')
    text = text.replace(pattern, (_match, prefix) => `${prefix}${label}`)
  }
  return text
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function readableChineseFallback(value, fallback) {
  return /[\u4e00-\u9fff]/.test(value) ? value : fallback
}
