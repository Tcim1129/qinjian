<template>
  <div class="alignment-page">
    <!-- 顶部正常对象切换栏（像正常社交/协作应用一样直接切换对象） -->
    <section v-if="availableObjects.length > 1" class="object-switch-bar">
      <div class="object-switch-bar__head">
        <div class="object-switch-bar__identity">
          <span class="object-switch-tag">当前对象</span>
          <strong class="object-switch-name">{{ currentObject?.name }}（{{ currentObject?.roleLabel }}）</strong>
          <span v-if="currentObject?.scenarioDescription" class="object-switch-desc">{{ currentObject?.scenarioDescription }}</span>
        </div>
        <div class="object-switch-bar__actions">
          <button
            class="perspective-invert-chip"
            :class="{ active: invertedPerspective }"
            type="button"
            @click="togglePerspectiveInvert"
            :title="invertedPerspective ? '点击切回本人主视角' : '点击切换为对方第一人称视角'"
          >
            <RefreshCw :size="13" />
            <span>{{ invertedPerspective ? '以对方视角体验中' : '🔄 换个视角看' }}</span>
          </button>
        </div>
      </div>
      <div class="object-switch-chips" role="tablist" aria-label="切换关系对象">
        <button
          v-for="obj in availableObjects"
          :key="obj.id"
          type="button"
          class="object-chip"
          :class="{ active: String(obj.id) === String(userStore.activePairId) }"
          @click="handleSwitchObject(obj.id)"
        >
          <span class="object-chip__avatar" :style="{ backgroundColor: obj.themeColor }">{{ obj.avatar }}</span>
          <span class="object-chip__text">{{ obj.name }}（{{ obj.roleLabel }}）</span>
        </button>
      </div>
    </section>

    <!-- 页面标题与主控制区 -->
    <header class="page-head alignment-head">
      <div class="alignment-head__title">
        <h2>双视角</h2>
        <div class="alignment-meta-tags">
          <span class="meta-badge">{{ experienceMode.isDemoMode ? '样例模式' : 'AI 深度分析' }}</span>
          <span v-if="invertedPerspective" class="meta-badge meta-badge--inverted">视角已互换：以【{{ myPerspective?.label }}】角色查看</span>
          <button v-if="alignment?.checkin_date" class="text-button text-button--link" type="button" @click="openRecordDay">
            {{ alignment.checkin_date }} · 当天记录 ↗
          </button>
        </div>
      </div>
      <div class="alignment-head__actions">
        <button
          v-if="alignment"
          class="btn btn-ghost btn-sm collapse-all-btn"
          type="button"
          @click="toggleAllSections"
        >
          {{ isAllCollapsed ? '全部展开 ▾' : '全部折叠 ▴' }}
        </button>
        <button class="btn btn-primary btn-sm" type="button" :disabled="loading || generating || !experienceMode.canUseDualPerspective" @click="handleGenerateAlignment">
          {{ generateButtonLabel }}
        </button>
      </div>
    </header>

    <p v-if="loadError" class="alignment-error" role="alert">
      {{ loadError }}
      <button class="text-button" type="button" :disabled="loading || generating" @click="loadAlignment">重试</button>
    </p>

    <!-- 当有双视角结果时，4 大可折叠板块（切换对象时一起折叠起来） -->
    <template v-if="alignment">
      <p v-if="alignment.is_fallback" class="alignment-note">本次为备用结果，仅供参考。</p>

      <!-- 板块 1：双方记录对照（可折叠） -->
      <section class="collapsible-card" :class="{ 'is-collapsed': !sectionsState.perspectives }">
        <button class="collapsible-card__header" type="button" @click="toggleSection('perspectives')">
          <div class="collapsible-card__title">
            <span class="panel-emoji">⚖️</span>
            <div>
              <h3>双方记录对照</h3>
              <p class="collapsible-card__subtitle">
                {{ myPerspective?.label }}（我的视角）与 {{ partnerPerspective?.label }}（对方视角）的真实认知对比
              </p>
            </div>
          </div>
          <div class="collapsible-card__status">
            <span class="collapse-hint">{{ sectionsState.perspectives ? '收起 ▴' : '展开 ▾' }}</span>
          </div>
        </button>

        <div v-show="sectionsState.perspectives" class="collapsible-card__content">
          <div class="perspective-grid" aria-label="双方记录的对照">
            <article class="perspective-card perspective-card--mine">
              <div class="perspective-card__head">
                <span class="perspective-badge perspective-badge--mine">
                  {{ invertedPerspective ? '对方角色 (当前体验)' : '我的视角' }}
                </span>
                <h3>{{ myPerspective?.label }} 的理解</h3>
              </div>
              <p>{{ myPerspective?.summary || '暂无摘要。' }}</p>
            </article>
            <article class="perspective-card perspective-card--partner">
              <div class="perspective-card__head">
                <span class="perspective-badge perspective-badge--partner">
                  {{ invertedPerspective ? '我的原视角' : '对方视角' }}
                </span>
                <h3>{{ partnerPerspective?.label }} 的理解</h3>
              </div>
              <p>{{ partnerPerspective?.summary || '暂无摘要。' }}</p>
            </article>
          </div>
        </div>
      </section>

      <!-- 板块 2：放在一起看与分歧识别（可折叠） -->
      <section class="collapsible-card" :class="{ 'is-collapsed': !sectionsState.compare }">
        <button class="collapsible-card__header" type="button" @click="toggleSection('compare')">
          <div class="collapsible-card__title">
            <span class="panel-emoji">🔍</span>
            <div>
              <h3>放在一起看与分歧识别</h3>
              <p class="collapsible-card__subtitle">
                {{ alignment.shared_story ? alignment.shared_story.slice(0, 36) + '...' : '综合梳理分歧与误读风险' }}
              </p>
            </div>
          </div>
          <div class="collapsible-card__status">
            <span class="collapse-hint">{{ sectionsState.compare ? '收起 ▴' : '展开 ▾' }}</span>
          </div>
        </button>

        <div v-show="sectionsState.compare" class="collapsible-card__content">
          <div class="shared-story">
            <h3>放在一起看</h3>
            <p class="shared-summary">{{ alignment.shared_story || '记录还不够，暂时无法比较。' }}</p>
            <button class="text-button" type="button" @click="openContext('compare')">请 AI 帮我梳理 ↗</button>
          </div>
          <div class="alignment-section">
            <h3>可能的误会</h3>
            <p>{{ alignment.misread_risk || '暂未发现明显分歧。' }}</p>
            <ul v-if="alignment.divergence_points?.length" class="plain-list">
              <li v-for="(item, index) in alignment.divergence_points" :key="index">{{ item }}</li>
            </ul>
          </div>
        </div>
      </section>

      <!-- 板块 3：试着这样说与行动建议（可折叠） -->
      <section class="collapsible-card" :class="{ 'is-collapsed': !sectionsState.actions }">
        <button class="collapsible-card__header" type="button" @click="toggleSection('actions')">
          <div class="collapsible-card__title">
            <span class="panel-emoji">💬</span>
            <div>
              <h3>试着这样说与破冰行动</h3>
              <p class="collapsible-card__subtitle">
                {{ alignment.suggested_opening ? '推荐高情商开场白与低负担下一步动作' : 'AI 缓和建议' }}
              </p>
            </div>
          </div>
          <div class="collapsible-card__status">
            <span class="collapse-hint">{{ sectionsState.actions ? '收起 ▴' : '展开 ▾' }}</span>
          </div>
        </button>

        <div v-show="sectionsState.actions" class="collapsible-card__content">
          <div class="alignment-grid">
            <article class="alignment-section opening-section">
              <div class="opening-head">
                <h3>试着这样说</h3>
                <button
                  class="btn btn-ghost btn-xs btn-refresh-opening"
                  type="button"
                  :disabled="refreshingOpening || generating"
                  @click="handleRefreshOpening"
                  title="换一种表达思路"
                >
                  <RefreshCw :size="13" :class="{ 'is-spinning': refreshingOpening }" />
                  <span>{{ refreshingOpening ? '构思中...' : '换个说法' }}</span>
                </button>
              </div>
              <blockquote>{{ currentSuggestedOpening || alignment.suggested_opening || '暂无合适的说法。' }}</blockquote>
              <button class="text-button" type="button" @click="openContext('opening')">深入和 AI 商量细节 ↗</button>
            </article>
            <article class="alignment-section next-step-section">
              <h3>可以试试</h3>
              <ul v-if="alignment.bridge_actions?.length" class="plain-list">
                <li v-for="(item, index) in alignment.bridge_actions" :key="index">{{ item }}</li>
              </ul>
              <p v-else>暂无具体建议。</p>
              <button class="btn btn-primary btn-sm" type="button" @click="openContext('action')">和 AI 商量下一步</button>
            </article>
          </div>
        </div>
      </section>

      <!-- 板块 4：和平时相比（可折叠） -->
      <section v-if="alignment.reaction_shift || displayDeviationReasons.length" class="collapsible-card" :class="{ 'is-collapsed': !sectionsState.history }">
        <button class="collapsible-card__header" type="button" @click="toggleSection('history')">
          <div class="collapsible-card__title">
            <span class="panel-emoji">📈</span>
            <div>
              <h3>和平时相比</h3>
              <p class="collapsible-card__subtitle">{{ reactionShiftLabel }}</p>
            </div>
          </div>
          <div class="collapsible-card__status">
            <span class="collapse-hint">{{ sectionsState.history ? '收起 ▴' : '展开 ▾' }}</span>
          </div>
        </button>

        <div v-show="sectionsState.history" class="collapsible-card__content">
          <div class="history-content">
            <p>{{ reactionShiftLabel }}</p>
            <p class="alignment-note">{{ historyLabel }}</p>
            <ul v-if="displayDeviationReasons.length" class="plain-list">
              <li v-for="(item, index) in displayDeviationReasons" :key="index">{{ item }}</li>
            </ul>
          </div>
        </div>
      </section>

      <!-- 反馈区 -->
      <section class="feedback-section" aria-label="对这次分析的反馈">
        <h3>分析得准吗？需要系统调整吗？</h3>
        <p class="feedback-section__desc">如果觉得分析偏离了你们的真实相处情况，请选定评级或输入备注，点击提交校准：</p>
        <div class="feedback-row">
          <button
            v-for="option in feedbackOptions"
            :key="option.value"
            class="btn btn-ghost btn-sm"
            :class="{ active: selectedFeedbackType === option.value }"
            type="button"
            :disabled="feedbackBusy || generating"
            @click="selectedFeedbackType = option.value"
          >
            {{ option.label }}
          </button>
        </div>
        <label class="feedback-note">
          <span>调整说明或补充情况</span>
          <textarea
            v-model="feedbackNote"
            class="input input-textarea"
            rows="2"
            maxlength="1000"
            :disabled="feedbackBusy"
            placeholder="例如：其实我们平时都这样开玩笑；或者对方当时并没有介意..."
          ></textarea>
        </label>
        <div class="feedback-actions">
          <button
            class="btn btn-primary btn-sm"
            type="button"
            :disabled="feedbackBusy || (!selectedFeedbackType && !feedbackNote.trim())"
            @click="handleSubmitAdjustment"
          >
            <Check :size="14" v-if="!feedbackBusy" />
            <Loader2 :size="14" v-else class="spin-icon" />
            <span>{{ feedbackBusy ? '提交中...' : '提交调整与反馈' }}</span>
          </button>
          <span v-if="feedbackSubmitted" class="feedback-status" role="status">
            ✓ {{ experienceMode.isDemoMode ? '已记录反馈，系统已为您校准~' : '反馈已提交，系统已根据调整完成校准~' }}
          </span>
        </div>
      </section>
    </template>

    <div v-else class="alignment-empty" :aria-busy="loading || generating">
      <strong>{{ loading ? '加载中…' : generating ? '分析中…' : loadError ? '加载失败' : '还没有分析结果' }}</strong>
      <p v-if="!loading && !generating && !loadError">{{ emptyHint || '双方都有记录后，即可生成分析。' }}</p>
      <div v-if="!loading && !generating" class="empty-actions">
        <button class="btn btn-ghost" type="button" @click="$router.push('/checkin')">去写记录</button>
        <button v-if="experienceMode.isSoloExperience" class="btn btn-ghost" type="button" @click="$router.push('/pair')">建立关系</button>
      </div>
    </div>

    <ContextAgentDialog v-if="agentContext" :context="agentContext" @close="agentContext = null" />
  </div>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { api } from '@/api'
import { cloneDemo, demoFixture, getDemoNarrativeAlignment, listDemoPersonas } from '@/demo/fixtures'
import ContextAgentDialog from '@/components/ContextAgentDialog.vue'
import { requestSceneReply } from '@/utils/requestSceneReply'
import { featureUnavailableReason, resolveExperienceMode } from '@/utils/experienceMode'
import { createRefreshAttemptGuard } from '@/utils/refreshGuards'
import { buildAlignmentContext } from '@/utils/contextAgent'
import { buildPairQuery } from '@/utils/reportScopeSelection'
import { Check, Loader2, RefreshCw } from 'lucide-vue-next'

const router = useRouter()
const userStore = useUserStore()
const showToast = inject('showToast', () => {})
const alignment = ref(null)
const loading = ref(false)
const generating = ref(false)
const loadError = ref('')
const emptyHint = ref('')
const feedbackNote = ref('')
const feedbackBusy = ref(false)
const feedbackSubmitted = ref('')
const selectedFeedbackType = ref('')
const refreshingOpening = ref(false)
const customOpening = ref('')
const openingVariantIndex = ref(0)
const currentSuggestedOpening = computed(() => customOpening.value || alignment.value?.suggested_opening || '')
const agentContext = ref(null)
const invertedPerspective = ref(false)
let requestVersion = 0
let disposed = false
const alignmentRefreshGuard = createRefreshAttemptGuard({ maxAttempts: 2, windowMs: 60000 })
const experienceMode = computed(() => resolveExperienceMode({ isDemoMode: userStore.isDemoMode, testingUnrestricted: userStore.testingUnrestricted, activePairId: userStore.activePairId, currentPair: userStore.currentPair, pairs: userStore.pairs }))
const feedbackOptions = [{ value: 'acceptable', label: '挺贴切的' }, { value: 'direction_off', label: '理解偏了' }, { value: 'copy_unnatural', label: '说法不自然' }, { value: 'judgement_too_high', label: '说得太严重' }, { value: 'judgement_too_low', label: '没说到重点' }]
const generateButtonLabel = computed(() => generating.value ? '分析中…' : experienceMode.value.isDemoMode ? '刷新样例' : alignment.value ? '重新分析' : '生成分析')

// --- 对象切换体系（像正常多对象应用一样平滑切换） ---
const availableObjects = computed(() => {
  if (experienceMode.value.isDemoMode) {
    return listDemoPersonas().map(p => ({
      id: p.id,
      name: p.name,
      roleLabel: p.roleLabel,
      avatar: p.avatar,
      themeColor: p.themeColor,
      scenarioDescription: p.scenarioDescription,
    }))
  }
  return (userStore.pairs || []).map(pair => ({
    id: pair.id,
    name: pair.partner_name || pair.name || '伙伴',
    roleLabel: pair.type === 'couple' ? '伴侣' : pair.type === 'friend' ? '朋友' : '伙伴',
    avatar: (pair.partner_name || '伴')[0],
    themeColor: '#b86248',
    scenarioDescription: pair.description || '',
  }))
})

const currentObject = computed(() => {
  return availableObjects.value.find(o => String(o.id) === String(userStore.activePairId)) || availableObjects.value[0] || null
})

// --- 内部板块受控折叠系统（“把里面的一起折叠起来”） ---
const sectionsState = ref({
  perspectives: true,  // 双方记录对照（默认展开）
  compare: false,       // 放在一起看与分歧识别（默认折叠）
  actions: false,       // 试着这样说与行动建议（默认折叠）
  history: false,       // 和平时相比（默认折叠）
})

function toggleSection(key) {
  sectionsState.value[key] = !sectionsState.value[key]
}

function collapseAll() {
  sectionsState.value.perspectives = false
  sectionsState.value.compare = false
  sectionsState.value.actions = false
  sectionsState.value.history = false
}

function expandAll() {
  sectionsState.value.perspectives = true
  sectionsState.value.compare = true
  sectionsState.value.actions = true
  sectionsState.value.history = true
}

const isAllCollapsed = computed(() => {
  return !sectionsState.value.perspectives &&
         !sectionsState.value.compare &&
         !sectionsState.value.actions &&
         !sectionsState.value.history
})

function toggleAllSections() {
  if (isAllCollapsed.value) {
    expandAll()
  } else {
    collapseAll()
  }
}

// 切换对象核心逻辑：触发切换时，把内部板块全部折叠起来
async function handleSwitchObject(targetId) {
  if (String(targetId) === String(userStore.activePairId)) return
  collapseAll()
  invertedPerspective.value = false
  await userStore.switchPair(targetId)
  showToast(`已切换至【${currentObject.value?.name || '新对象'}】，详细内容已自动收起~`)
}

// 视角翻转（无需重新登录，一键体验对方第一人称视角）
function togglePerspectiveInvert() {
  invertedPerspective.value = !invertedPerspective.value
  showToast(invertedPerspective.value ? '已切入对方第一人称视角体验~' : '已恢复本人视角~')
}

// 视角主客体计算（支持自动根据账号 + 页面内一键翻转）
const isUserB = computed(() => {
  const myId = userStore.me?.id
  const currentPair = userStore.currentPair
  let userB = false
  if (currentPair?.user_b_id && myId) {
    userB = String(currentPair.user_b_id) === String(myId)
  } else {
    const myNickname = userStore.me?.nickname
    if (alignment.value?.user_b_label && myNickname) {
      userB = alignment.value.user_b_label === myNickname
    }
  }
  return invertedPerspective.value ? !userB : userB
})

const myPerspective = computed(() => {
  if (!alignment.value) return null
  if (isUserB.value) {
    return {
      label: alignment.value.user_b_label || userStore.me?.nickname || '我',
      summary: alignment.value.view_b_summary || '暂无摘要。',
      isMine: true,
    }
  }
  return {
    label: alignment.value.user_a_label || userStore.me?.nickname || '我',
    summary: alignment.value.view_a_summary || '暂无摘要。',
    isMine: true,
  }
})

const partnerPerspective = computed(() => {
  if (!alignment.value) return null
  const partnerName = userStore.currentPair?.partner_name
  if (isUserB.value) {
    return {
      label: alignment.value.user_a_label || partnerName || '对方',
      summary: alignment.value.view_a_summary || '暂无摘要。',
      isMine: false,
    }
  }
  return {
    label: alignment.value.user_b_label || partnerName || '对方',
    summary: alignment.value.view_b_summary || '暂无摘要。',
    isMine: false,
  }
})

const inlineCodeLabels = {
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

const reactionShiftCopy = {
  more_defensive: '这会儿心里有点委屈，容易下意识自我防卫~',
  more_withdrawn: '太累了想先缩回小壳子里喘口气~',
  more_urgent: '心里很急切，盼着对方能马上给个准话~',
  more_repair_oriented: '想递个温柔台阶，把僵局快点化解开~',
  more_support_seeking: '现在特别需要一句知冷知热的体贴话~',
  more_clarifying: '想把真实想法摊开说，不想彼此猜来猜去~',
  more_reflective: '正在默默回味和梳理两个人相处的细节~',
  shifted: '状态和平时有点不同，适合先慢下来聊~',
}

const reactionShiftLabel = computed(() => {
  const shift = String(alignment.value?.reaction_shift || '').trim()
  if (!shift || shift === 'stable') return '这次的心情和平时差不多，挺平稳的~'
  if (shift === 'unknown') return '之前的记录还不够，暂时无法比较。'
  return shift
    .split(/[；;]/)
    .map((part) => renderReactionShift(part.trim()))
    .filter(Boolean)
    .join('；')
})

const historyLabel = computed(() => {
  const map = {
    sufficient: '参考了近期记录。',
    limited: '参考记录较少，仅供参考。',
    insufficient: '记录不足，暂时无法判断变化。',
  }
  return map[alignment.value?.history_sufficiency] || '历史记录不足。'
})

const displayDeviationReasons = computed(() =>
  (alignment.value?.deviation_reasons || []).map(translateInlineCodes)
)

function renderReactionShift(value) {
  if (!value) return ''
  const [label, code] = value.split(/[：:]/).map((item) => item.trim())
  if (code && reactionShiftCopy[code]) return reactionShiftCopy[code]
  if (code) return translateInlineCodes(code)
  if (reactionShiftCopy[label]) return reactionShiftCopy[label]
  return translateInlineCodes(value)
}

function translateInlineCodes(value) {
  const pattern = new RegExp(`\\b(${Object.keys(inlineCodeLabels).join('|')})\\b`, 'g')
  return String(value || '').replace(pattern, (match) => inlineCodeLabels[match] || match)
}

function resetFeedback() { feedbackNote.value = ''; feedbackBusy.value = false; feedbackSubmitted.value = ''; selectedFeedbackType.value = '' }
function isCurrent(version) { return !disposed && version === requestVersion }
function loadSample() {
  const demoData = getDemoNarrativeAlignment(experienceMode.value.activePairId)
  alignment.value = demoData ? cloneDemo(demoData) : null
  emptyHint.value = alignment.value ? '' : '这段关系还没有双视角样例。'
}

async function loadAlignment() {
  const version = ++requestVersion
  loading.value = true
  refreshingOpening.value = false
  generating.value = false
  loadError.value = ''
  emptyHint.value = ''
  agentContext.value = null
  resetFeedback()
  try {
    if (experienceMode.value.isDemoMode) { loadSample(); return }
    if (!experienceMode.value.canUseDualPerspective) { alignment.value = null; emptyHint.value = featureUnavailableReason('dual-perspective', experienceMode.value); return }
    const result = await api.getLatestNarrativeAlignment(experienceMode.value.activePairId)
    if (isCurrent(version)) alignment.value = result || null
  } catch (error) {
    if (!isCurrent(version)) return
    alignment.value = null
    if (error.statusCode === 404) emptyHint.value = error.message || '还没有分析结果，可以先整理一次。'
    else loadError.value = error.message || '最近一次分析没能加载出来，请重试。'
  } finally { if (isCurrent(version)) loading.value = false }
}

async function handleGenerateAlignment() {
  if (loading.value || generating.value || !experienceMode.value.canUseDualPerspective) return
  const seconds = alignmentRefreshGuard.getRemainingSeconds()
  if (seconds) return showToast('整理得有点频繁，请 ' + seconds + ' 秒后再试')
  alignmentRefreshGuard.markRun()
  const version = ++requestVersion
  generating.value = true
  loadError.value = ''
  agentContext.value = null
  resetFeedback()
  try {
    const result = await api.generateNarrativeAlignment(experienceMode.value.activePairId, { force: Boolean(alignment.value) })
    if (isCurrent(version)) { alignment.value = result || null; emptyHint.value = '' }
  } catch (error) {
    if (!isCurrent(version)) return
    if (error.statusCode === 404) { alignment.value = null; emptyHint.value = error.message || '还没有足够的双方记录。' }
    else loadError.value = (error.message || '这次没整理出来，请稍后重试。') + (alignment.value ? ' 当前仍显示上一次结果。' : '')
  } finally { if (isCurrent(version)) generating.value = false }
}

async function handleRefreshOpening() {
  if (refreshingOpening.value || !alignment.value) return
  const version = requestVersion
  const pair = experienceMode.value.activePairId
  const context = buildAlignmentContext(alignment.value, 'opening', {
    pairId: pair, myLabel: myPerspective.value?.label, partnerLabel: partnerPerspective.value?.label,
    mySummary: myPerspective.value?.summary, partnerSummary: partnerPerspective.value?.summary,
  })
  refreshingOpening.value = true
  try {
    const reply = await requestSceneReply(api, pair, context,
      '请根据双方记录，把当前开场白换一种说法。保留原意和边界，不编造已做过的事，只返回改写后的话。',
      () => isCurrent(version))
    if (isCurrent(version)) customOpening.value = reply
  } catch (error) {
    if (isCurrent(version)) showToast(error.message || '这次没改出来，请重试。')
  } finally { if (isCurrent(version)) refreshingOpening.value = false }
}
async function handleSubmitAdjustment() {
  if (feedbackBusy.value || feedbackSubmitted.value || generating.value) return
  if (!selectedFeedbackType.value && !feedbackNote.value.trim()) {
    showToast('请选择反馈评级或输入调整说明')
    return
  }
  const feedbackType = selectedFeedbackType.value || 'acceptable'
  if (experienceMode.value.isDemoMode) {
    feedbackSubmitted.value = feedbackType
    showToast('已记下本次样例反馈')
    return
  }
  const eventId = alignment.value?.event_id
  if (!eventId) return showToast('这条结果暂时不能提交反馈')
  const version = requestVersion
  feedbackBusy.value = true
  try {
    await api.submitDecisionFeedback(eventId, feedbackType, feedbackNote.value.trim())
    if (isCurrent(version)) {
      feedbackSubmitted.value = feedbackType
      showToast('已记录反馈')
    }
  } catch (error) {
    if (isCurrent(version)) showToast(error.message || '反馈没提交上，可以再试一次')
  } finally {
    if (isCurrent(version)) feedbackBusy.value = false
  }
}

async function submitFeedback(feedbackType) {
  selectedFeedbackType.value = feedbackType
  await handleSubmitAdjustment()
}

function openRecordDay() { router.push({ path: '/timeline', query: { ...buildPairQuery(experienceMode.value.activePairId), date: alignment.value?.checkin_date } }) }

function openContext(kind) {
  if (alignment.value) {
    agentContext.value = buildAlignmentContext(alignment.value, kind, {
      pairId: experienceMode.value.activePairId,
      isDemoMode: experienceMode.value.isDemoMode,
      myLabel: myPerspective.value?.label,
      partnerLabel: partnerPerspective.value?.label,
      mySummary: myPerspective.value?.summary,
      partnerSummary: partnerPerspective.value?.summary,
    })
  }
}

watch(() => [userStore.activePairId, userStore.token, userStore.me?.id], () => {
  alignment.value = null
  void loadAlignment()
}, { flush: 'sync' })

onMounted(loadAlignment)
onBeforeUnmount(() => { disposed = true; requestVersion++ })
</script>

<style scoped>
.alignment-page { width: min(var(--content-max), calc(100% - 32px)); margin: 0 auto; padding-bottom: 40px; }

/* 顶部对象切换条 */
.object-switch-bar {
  background: #fdfaf6;
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 14px 18px;
  margin-bottom: 20px;
  box-shadow: 0 4px 16px rgba(91, 67, 51, 0.03);
}
.object-switch-bar__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}
.object-switch-bar__identity {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.object-switch-tag {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 4px;
  background: #f2e9db;
  color: var(--seal-deep);
}
.object-switch-name {
  font-size: 15px;
  color: var(--ink);
  font-family: var(--font-serif);
}
.object-switch-desc {
  font-size: 12px;
  color: var(--ink-soft);
}
.perspective-invert-btn,
.perspective-invert-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  color: var(--seal-deep);
  background: #fff;
  border: 1px solid var(--border-strong);
  cursor: pointer;
  transition: all 0.15s ease;
}
.perspective-invert-chip:hover {
  background: #faede6;
  border-color: var(--seal);
}
.perspective-invert-chip.active {
  background: #faede6;
  border-color: var(--seal-deep);
  color: var(--seal-deep);
  font-weight: 600;
}

.object-switch-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.object-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 999px;
  background: #fff;
  border: 1px solid var(--border);
  color: var(--ink-soft);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.18s ease;
}
.object-chip:hover {
  border-color: var(--seal-light);
  color: var(--ink);
  transform: translateY(-1px);
}
.object-chip.active {
  background: #2b2523;
  color: #fff;
  border-color: #2b2523;
  box-shadow: 0 4px 12px rgba(43, 37, 35, 0.16);
}
.object-chip__avatar {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: #fff;
  font-size: 11px;
  font-weight: bold;
}

/* 页面头部 */
.alignment-head { display: flex; align-items: center; justify-content: space-between; gap: 18px; width: 100%; padding-bottom: 12px; }
.alignment-head__title { display: flex; align-items: baseline; flex-wrap: wrap; gap: 12px; }
.alignment-head__title h2 { margin: 0; }
.alignment-meta-tags { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.meta-badge { font-size: 12px; padding: 2px 8px; border-radius: 999px; background: #f0ebe4; color: var(--ink-soft); }
.meta-badge--inverted { background: #fcebe6; color: #b86248; font-weight: 600; border: 1px solid #f6cfc4; }
.alignment-head__actions { display: flex; align-items: center; gap: 10px; }
.collapse-all-btn { color: var(--ink-soft); border-color: var(--border); }

/* 可折叠卡片体系（把里面的一起折叠起来） */
.collapsible-card {
  margin-bottom: 16px;
  border: 1px solid var(--border-strong);
  border-radius: 12px;
  background: #fff;
  overflow: hidden;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.collapsible-card:hover {
  border-color: #d1c5b8;
}
.collapsible-card.is-collapsed {
  background: #fdfbf8;
}
.collapsible-card__header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px;
  background: none;
  border: 0;
  cursor: pointer;
  text-align: left;
}
.collapsible-card__header:hover {
  background: rgba(245, 238, 228, 0.4);
}
.collapsible-card__title {
  display: flex;
  align-items: center;
  gap: 12px;
}
.panel-emoji {
  font-size: 20px;
}
.collapsible-card__title h3 {
  margin: 0 0 4px;
  font: 18px/1.4 var(--font-serif);
  color: var(--ink);
}
.collapsible-card__subtitle {
  margin: 0;
  font-size: 13px;
  color: var(--ink-soft);
  line-height: 1.5;
}
.collapsible-card__status {
  flex-shrink: 0;
}
.collapse-hint {
  font-size: 13px;
  font-weight: 600;
  color: var(--seal-deep);
  background: #faede6;
  padding: 3px 10px;
  border-radius: 999px;
}
.collapsible-card__content {
  padding: 4px 20px 22px;
  border-top: 1px dashed var(--border);
}

/* 内部对照卡片 */
.perspective-grid, .alignment-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; margin-top: 16px; }
.perspective-card { padding: 22px; background: #fffaf4; border: 1px solid var(--border-strong); border-top: 3px solid #b86248; border-radius: 4px 4px 14px 14px; }
.perspective-card--mine { border-top-color: #b86248; background: #fffaf4; }
.perspective-card--partner { border-top-color: #818b73; background: #fbfaf3; }
.perspective-card__head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.perspective-card__head h3 { margin: 0; font: 20px/1.5 var(--font-serif); }
.perspective-badge { display: inline-flex; align-items: center; font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 999px; letter-spacing: 0.5px; }
.perspective-badge--mine { background: #faede6; color: #b86248; border: 1px solid #f0cfc3; }
.perspective-badge--partner { background: #f0f3eb; color: #626c54; border: 1px solid #d5ddc8; }
.perspective-card > p:last-child { color: var(--ink-soft); line-height: 1.85; margin: 0; }

.shared-story { padding: 18px 0; border-bottom: 1px solid var(--border); margin-bottom: 18px; }
.shared-story h3 { margin: 0 0 10px; font: 20px/1.5 var(--font-serif); }
.shared-summary { max-width: 850px; margin: 0; color: var(--ink-soft); font-size: 15px; line-height: 1.8; }
.text-button { padding: 4px 0; color: var(--seal-deep); background: none; border: 0; text-align: left; font: inherit; cursor: pointer; }
.text-button--link { font-size: 13px; margin-left: 6px; }
.shared-story .text-button { margin-top: 10px; font-size: 13px; }
.alignment-section { min-width: 0; padding: 4px 0; line-height: 1.8; }
.alignment-section h3, .next-step-section h3 { font: 19px/1.5 var(--font-serif); margin: 0 0 10px; }
.alignment-section > p:not(.eyebrow), .plain-list { color: var(--ink-soft); font-size: 14px; }
.plain-list { display: grid; gap: 8px; padding-left: 18px; margin: 10px 0 16px; line-height: 1.7; }
.opening-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.btn-refresh-opening {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--seal-deep);
  font-size: 13px;
  padding: 3px 8px;
}

.btn-refresh-opening:hover:not(:disabled) {
  background: rgba(184, 98, 72, 0.08);
}

.opening-section { padding: 18px 20px; background: #f2e9db; border-radius: 12px; }
.opening-section blockquote { padding: 0; margin: 10px 0 16px; font: 17px/1.8 var(--font-serif); }
.next-step-section { padding: 4px 0; }
.history-content { padding: 12px 0; color: var(--ink-soft); font-size: 14px; line-height: 1.8; }

.feedback-section { border-top: 1px solid var(--border-strong); margin-top: 18px; padding-top: 20px; }
.feedback-section h3 { margin: 0 0 8px; font: 18px var(--font-serif); }
.feedback-section__desc { font-size: 13px; color: var(--ink-soft); margin: 0 0 12px; }
.feedback-note { display: grid; gap: 8px; max-width: 640px; color: var(--ink-soft); font-size: 13px; }
.feedback-note textarea { min-height: 64px; }
.feedback-row, .empty-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.feedback-row button[aria-pressed="true"], .feedback-row .btn.active {
  background: var(--seal);
  color: #fff;
  border-color: var(--seal);
  opacity: 1;
}
.feedback-actions { display: flex; align-items: center; gap: 14px; margin-top: 14px; }
.feedback-status, .alignment-note { color: var(--ink-soft); font-size: 13px; line-height: 1.7; margin-top: 8px; }
.feedback-actions .feedback-status { margin-top: 0; color: #16a34a; font-weight: 500; }
.alignment-error { background: #fbede5; border-radius: 10px; padding: 12px 16px; color: #88422f; font-size: 13px; line-height: 1.8; }
.alignment-empty { min-height: 260px; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 24px; text-align: center; border: 1px dashed var(--border-strong); border-radius: 16px; }
.alignment-empty p { color: var(--ink-soft); line-height: 1.8; }

.is-spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

button:focus-visible, summary:focus-visible { outline: 3px solid var(--seal); outline-offset: 3px; }
@media (max-width: 760px) {
  .perspective-grid, .alignment-grid { grid-template-columns: 1fr; gap: 16px; }
  .alignment-head { align-items: flex-start; flex-direction: column; }
  .object-switch-bar__head { flex-direction: column; align-items: flex-start; }
}
@media (max-width: 500px) {
  .alignment-page { width: calc(100% - 24px); }
  .perspective-card, .opening-section { padding: 16px; }
}
</style>\n
