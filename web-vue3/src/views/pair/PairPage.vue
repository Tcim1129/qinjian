<template>
  <div class="pair-page page-shell page-shell--wide page-stack" :class="themeClass">
    <div class="page-head pair-page__head">
      <p class="eyebrow">关系管理</p>
      <h2>每段关系现在是什么状态</h2>
    </div>

    <section v-if="showPairOverview" id="pair-list" class="pair-overview">
      <div class="pair-overview__main">
        <div class="pair-list-panel">
          <div class="pair-list-panel__head">
            <div>
              <p class="eyebrow">我的关系</p>
              <h3>选择当前关系</h3>
            </div>
            <span class="pair-list-count">共 {{ activePairs.length }} 段</span>
          </div>

          <div class="pair-list-panel__grid">
            <button
              v-for="item in relationshipListItems"
              :key="item.pairId"
              class="pair-list-card"
              :class="{ active: item.pairId === selectedPairId }"
              type="button"
              @click="selectRelationshipPair(item.pairId)"
            >
              <div class="pair-list-card__avatar">{{ item.shortLabel }}</div>
              <div class="pair-list-card__copy">
                <strong>{{ item.title }}</strong>
                <span>{{ item.metaLabel }}</span>
              </div>
              <span class="pair-list-card__score">{{ item.scoreLabel }}</span>
            </button>
          </div>
        </div>
      </div>

      <RelationshipSidebarPanel
        class="pair-overview__sidebar"
        :summary="selectedSidebar"
        :theme="selectedTheme"
        @open-detail="openRelationshipDetail"
        @select-pair="selectRelationshipPair"
      />
    </section>

    <section v-else id="pair-list" class="pair-solo-intro">
      <div class="pair-solo-intro__copy">
        <p class="eyebrow">单人模式</p>
        <h3>邀请或加入一段关系</h3>
      </div>
    </section>

    <section class="pair-actions">
      <article
        id="pair-join"
        class="pair-entry-card"
        :class="{ 'is-active': route.path === RELATIONSHIP_JOIN_ROUTE }"
      >
        <div class="pair-entry-card__head">
          <p class="eyebrow">加入关系邀请码</p>
          <h3>输入对方给你的邀请码</h3>
        </div>

        <label class="field pair-entry-card__field">
          <span>邀请码</span>
          <input
            :value="joinCode"
            class="input pair-entry-card__input"
            type="text"
            maxlength="10"
            autocomplete="off"
            autocapitalize="characters"
            spellcheck="false"
            placeholder="请输入 10 位邀请码，如 A3H7K8M9Q2"
            @focus="handleInviteCodeFocus"
            @blur="handleInviteCodeBlur"
            @compositionstart="handleInviteCodeCompositionStart"
            @compositionend="handleInviteCodeCompositionEnd"
            @input="handleInviteCodeInput"
          />
        </label>

        <div class="pair-entry-card__actions">
          <button
            class="btn btn-primary pair-entry-card__primary"
            type="button"
            :disabled="joining"
            @click="handlePreviewJoin"
          >
            {{ joining ? '校验中...' : '选择关系类型' }}
          </button>
          <button
            v-if="currentJoinRequestPairId"
            class="btn btn-ghost"
            type="button"
            @click="openRelationshipDetail(currentJoinRequestPairId)"
          >
            去专属关系页
          </button>
        </div>
      </article>

      <article
        id="pair-create"
        class="pair-entry-card"
        :class="{ 'is-active': route.path === RELATIONSHIP_INVITE_ROUTE }"
      >
        <div class="pair-entry-card__head">
          <p class="eyebrow">当前邀请码</p>
          <h3>把邀请码发给对方</h3>
        </div>

        <div v-if="currentPairInviteCode" class="pair-invite-code">
          <span class="pair-invite-code__status" :class="`is-${currentInviteState}`">
            {{ currentInviteStateLabel }}
          </span>
          <strong>{{ currentPairInviteCode }}</strong>
        </div>
        <div v-else class="pair-empty-state">
          <strong>正在准备邀请码</strong>
        </div>

        <div class="pair-entry-card__actions">
          <button
            v-if="currentPairInviteCode"
            class="btn btn-primary pair-entry-card__primary"
            type="button"
            :disabled="refreshingInviteCode"
            @click="copyCode"
          >
            复制邀请码
          </button>
          <button
            v-if="currentPairInviteCode"
            class="btn btn-ghost"
            type="button"
            :disabled="refreshingInviteCode"
            @click="handleRefreshInviteCode"
          >
            {{ refreshingInviteCode ? '刷新中...' : '刷新邀请码' }}
          </button>
          <button
            v-else
            class="btn btn-primary pair-entry-card__primary"
            type="button"
            :disabled="creating"
            @click="handleCreate"
          >
            {{ creating ? '准备中...' : '重新创建邀请码' }}
          </button>
          <button
            v-if="currentInvitePair?.id && currentInvitePendingRequest"
            class="btn btn-ghost"
            type="button"
            @click="openRelationshipDetail(currentInvitePair.id)"
          >
            去专属关系页
          </button>
        </div>
      </article>
    </section>

    <div
      v-if="joinModalOpen && joinPreview"
      class="pair-modal"
      role="dialog"
      aria-modal="true"
      @click.self="closeJoinModal"
    >
      <section class="pair-modal__paper">
        <div class="pair-modal__head">
          <p class="eyebrow">选择关系类型</p>
          <h3>按什么关系加入</h3>
        </div>

        <div class="pair-modal__types">
          <button
            v-for="option in createOptions"
            :key="option.value"
            class="pair-modal__type"
            :class="{ active: joinSelectedType === option.value }"
            type="button"
            @click="joinSelectedType = option.value"
          >
            {{ option.label }}
          </button>
        </div>

        <div class="pair-modal__actions">
          <button class="btn btn-ghost" type="button" @click="closeJoinModal">取消</button>
          <button
            class="btn btn-primary"
            type="button"
            :disabled="submittingJoinRequest"
            @click="submitJoinRequest"
          >
            {{ submittingJoinRequest ? '提交中...' : '提交给对方确认' }}
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, inject, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import RelationshipSidebarPanel from '@/components/relationship/RelationshipSidebarPanel.vue'
import { demoFixture } from '@/demo/fixtures'
import { useUserStore } from '@/stores/user'
import { buildPairStatusSummary } from '@/utils/pairStatusSummary'
import {
  isPairChangeRequestedByMe,
  isPairChangeWaitingForMe,
} from '@/utils/pairChangeRequests'
import { resolveRelationshipSelection } from '@/utils/relationshipSelection'
import { buildRelationshipSpaceModel } from '@/utils/relationshipSpaceModel'
import {
  getRelationshipThemeOption,
  RELATIONSHIP_SPACE_THEMES,
  resolveRelationshipSpaceTheme,
  saveStoredRelationshipSpaceTheme,
} from '@/utils/relationshipTheme'
import { CREATABLE_RELATIONSHIP_TYPE_LABELS } from '@/utils/displayText'
import {
  buildRelationshipSectionLocation,
  getRelationshipRouteSection,
  RELATIONSHIP_INVITE_ROUTE,
  RELATIONSHIP_JOIN_ROUTE,
  RELATIONSHIP_LIST_ROUTE,
  buildRelationshipSpaceDetailRoute,
} from '@/utils/relationshipRouting'
import { getPartnerDisplayName } from '@/utils/relationshipSpaces'
import { createRefreshAttemptGuard, parseRetryAfterSeconds } from '@/utils/refreshGuards'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const showToast = inject('showToast')

const INVITE_CODE_LENGTH = 10
const INVITE_CODE_PATTERN = /^[23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{10}$/
const INVITE_REFRESH_WINDOW_MS = 60 * 1000
const INVITE_REFRESH_MAX_ATTEMPTS = 3

const joinCode = ref('')
const creating = ref(false)
const joining = ref(false)
const savingTheme = ref(false)
const selectedPairId = ref('')
const focusPairId = ref('')
const selectedTheme = ref(resolveRelationshipSpaceTheme())
const joinModalOpen = ref(false)
const joinPreview = ref(null)
const joinSelectedType = ref('friend')
const submittingJoinRequest = ref(false)
const inviteAutoPrimed = ref(false)
const refreshingInviteCode = ref(false)
const joinInputFocused = ref(false)
const joinCodeComposing = ref(false)
const pendingRouteSectionScroll = ref('')
let sectionSyncFrame = 0
const inviteRefreshGuard = createRefreshAttemptGuard({
  maxAttempts: INVITE_REFRESH_MAX_ATTEMPTS,
  windowMs: INVITE_REFRESH_WINDOW_MS,
})

const activePairs = computed(() => userStore.pairs.filter((pair) => pair.status === 'active'))
const pendingPairs = computed(() => userStore.pairs.filter((pair) => pair.status === 'pending'))
const showPairOverview = computed(() => activePairs.value.length > 0)
const relationshipThemeOptions = RELATIONSHIP_SPACE_THEMES
const themeClass = computed(() => `pair-page--theme-${selectedTheme.value}`)
const currentUserId = computed(() => String(userStore.me?.id || ''))
const activeRouteSection = computed(() => getRelationshipRouteSection(route.path, route.hash) || 'pair-list')
const currentPair = computed(() => userStore.currentPair || null)
const currentInvitePair = computed(() => {
  if (currentPair.value?.status === 'pending' && String(currentPair.value?.user_a_id || '') === currentUserId.value) {
    return currentPair.value
  }
  return pendingPairs.value.find((pair) => String(pair.user_a_id || '') === currentUserId.value) || null
})
const currentPairInviteCode = computed(() => String(currentInvitePair.value?.invite_code || '').trim())
const currentInvitePendingRequest = computed(() => currentInvitePair.value?.pending_change_request || null)
const currentJoinRequestPair = computed(() => {
  const currentRequest = currentPair.value?.pending_change_request
  if (
    currentPair.value?.status === 'pending'
    && currentRequest?.kind === 'join_request'
    && isPairChangeRequestedByMe(currentRequest, currentUserId.value)
  ) {
    return currentPair.value
  }

  return pendingPairs.value.find((pair) => {
    const request = pair.pending_change_request
    return request?.kind === 'join_request' && isPairChangeRequestedByMe(request, currentUserId.value)
  }) || null
})
const currentJoinRequest = computed(() => {
  const request = currentJoinRequestPair.value?.pending_change_request
  return request?.kind === 'join_request' ? request : null
})
const currentJoinRequestPairId = computed(() => String(currentJoinRequestPair.value?.id || ''))
const currentInviteState = computed(() => {
  if (!currentPairInviteCode.value) return 'none'
  if (currentInvitePendingRequest.value && isPairChangeWaitingForMe(currentInvitePendingRequest.value, currentUserId.value)) return 'waiting-for-me'
  if (currentInvitePendingRequest.value && isPairChangeRequestedByMe(currentInvitePendingRequest.value, currentUserId.value)) return 'waiting-other'
  return 'pending'
})
const currentInviteStateLabel = computed(() => {
  if (currentInviteState.value === 'waiting-for-me') return '待你确认'
  if (currentInviteState.value === 'waiting-other') return '待对方确认'
  if (currentInviteState.value === 'pending') return '待对方输入'
  return '暂无邀请码'
})
const sectionShortcuts = computed(() => [
  {
    label: '查看关系',
    to: RELATIONSHIP_LIST_ROUTE,
    sectionId: 'pair-list',
    isActive: activeRouteSection.value === 'pair-list',
  },
  {
    label: '输入邀请码',
    to: RELATIONSHIP_JOIN_ROUTE,
    sectionId: 'pair-join',
    isActive: activeRouteSection.value === 'pair-join',
  },
  {
    label: '发起邀请',
    to: RELATIONSHIP_INVITE_ROUTE,
    sectionId: 'pair-create',
    isActive: activeRouteSection.value === 'pair-create',
  },
])

const createOptions = computed(() =>
  Object.entries(CREATABLE_RELATIONSHIP_TYPE_LABELS).map(([value, label]) => ({
    value,
    label,
  }))
)

const metricsByPairId = computed(() => {
  if (userStore.isDemoMode) {
    return demoFixture.relationshipMetrics || {}
  }

  return Object.fromEntries(
    userStore.pairs.map((pair) => [
      pair.id,
      buildPairStatusSummary({
        pair,
        label: getPartnerDisplayName(pair),
        isCurrent: pair.id === (userStore.activePairId || userStore.currentPairId),
        inviteCode: pair.id === userStore.currentPairId
          ? currentPairInviteCode.value
          : String(pair.invite_code || '').trim(),
      }),
    ])
  )
})

const spaceModel = computed(() =>
  buildRelationshipSpaceModel({
    me: userStore.me,
    currentPairId: selectedPairId.value,
    focusPairId: focusPairId.value,
    pairs: userStore.pairs,
    metricsByPairId: metricsByPairId.value,
  })
)

const selectedSidebar = computed(() => spaceModel.value.selectedSidebar)
const relationshipListItems = computed(() =>
  activePairs.value.map((pair) => {
    const label = getPartnerDisplayName(pair)
    const summary = buildPairStatusSummary({
      pair,
      label,
      isCurrent: pair.id === (userStore.activePairId || userStore.currentPairId),
      inviteCode: pair.id === userStore.currentPairId
        ? currentPairInviteCode.value
        : String(pair.invite_code || '').trim(),
    })
    const trendLabel = normalizePairTrendLabel(summary.trendLabel)

    return {
      pairId: pair.id,
      title: label,
      shortLabel: String(label || '对').slice(0, 1),
      typeLabel: summary.typeLabel,
      trendLabel,
      metaLabel: trendLabel ? `${summary.typeLabel} · ${trendLabel}` : summary.typeLabel,
      scoreLabel: summary.scoreLabel || summary.score || summary.statusLabel || '--',
    }
  })
)

function normalizePairTrendLabel(value) {
  return String(value || '')
    .replace(/断绝/g, '移除')
    .replace(/^已建立，?/, '')
    .replace(/^已建立$/, '')
    .replace(/^，|，$/g, '')
    .trim()
}

watch(
  () => [
    userStore.activePairId,
    userStore.currentPairId,
    userStore.pairs.map((pair) => `${pair.id}:${pair.status}`).join('|'),
  ],
  () => {
    if (!activePairs.value.length) {
      selectedPairId.value = ''
      focusPairId.value = ''
      return
    }
    const stillExists = activePairs.value.some((pair) => pair.id === selectedPairId.value)
    if (!stillExists) {
      selectedPairId.value = userStore.activePairId || activePairs.value[0]?.id || ''
    }
    const focusStillExists = activePairs.value.some((pair) => pair.id === focusPairId.value)
    if (!focusStillExists) {
      focusPairId.value = ''
    }
  },
  { immediate: true }
)

watch(
  () => userStore.me?.relationship_space_theme,
  () => {
    selectedTheme.value = resolveRelationshipSpaceTheme(userStore.isDemoMode ? '' : userStore.me?.relationship_space_theme)
  },
  { immediate: true }
)

watch(
  () => [route.path, currentInvitePair.value?.id || '', currentPairInviteCode.value],
  async ([path, invitePairId, inviteCode]) => {
    if (path !== RELATIONSHIP_INVITE_ROUTE) {
      inviteAutoPrimed.value = false
      return
    }
    if (invitePairId || inviteCode || creating.value || inviteAutoPrimed.value) return
    inviteAutoPrimed.value = true
    await handleCreate({ silentToast: true })
  },
  { immediate: true }
)

watch(
  () => [route.path, route.hash],
  ([path, hash], previousValue = []) => {
    const sectionId = getRelationshipRouteSection(path, hash)
    const previousSectionId = getRelationshipRouteSection(previousValue[0], previousValue[1])
    if (!sectionId || sectionId === previousSectionId) return
    queueRouteSectionSync(sectionId)
  },
  { immediate: true }
)

watch(
  () => [joinInputFocused.value, joinCodeComposing.value],
  ([focused, composing]) => {
    if (focused || composing || !pendingRouteSectionScroll.value) return
    flushPendingRouteSectionSync()
  }
)

onBeforeUnmount(() => {
  if (sectionSyncFrame) {
    cancelAnimationFrame(sectionSyncFrame)
  }
})

function normalizeInviteCode(value) {
  return String(value || '').toUpperCase().replace(/[^0-9A-Z]/g, '').slice(0, INVITE_CODE_LENGTH)
}

function setNormalizedJoinCode(value, target = null) {
  const normalizedValue = normalizeInviteCode(value)
  joinCode.value = normalizedValue
  if (target && target.value !== normalizedValue) {
    target.value = normalizedValue
  }
  return normalizedValue
}

function handleSelectNode(pairId) {
  const nextSelection = resolveRelationshipSelection({
    nextPairId: pairId,
    focusPairId: focusPairId.value,
  })
  if (!nextSelection.selectedPairId) return

  selectedPairId.value = nextSelection.selectedPairId
  focusPairId.value = nextSelection.focusPairId
}

function handleInviteCodeInput(event) {
  const rawValue = String(event?.target?.value || '')
  if (joinCodeComposing.value) {
    joinCode.value = rawValue.slice(0, INVITE_CODE_LENGTH)
    return
  }
  setNormalizedJoinCode(rawValue, event?.target)
}

function handleInviteCodeFocus() {
  joinInputFocused.value = true
}

function handleInviteCodeBlur(event) {
  joinInputFocused.value = false
  if (!joinCodeComposing.value) {
    setNormalizedJoinCode(event?.target?.value, event?.target)
  }
}

function handleInviteCodeCompositionStart() {
  joinCodeComposing.value = true
}

function handleInviteCodeCompositionEnd(event) {
  joinCodeComposing.value = false
  setNormalizedJoinCode(event?.target?.value, event?.target)
}

function goToShortcut(shortcut) {
  if (!shortcut?.sectionId) return
  const target = buildRelationshipSectionLocation(shortcut.sectionId, shortcut.to)
  if (route.path === target.path && route.hash === target.hash) {
    queueRouteSectionSync(shortcut.sectionId, { behavior: 'smooth', force: true })
    return
  }
  router.push(target)
}

function clearFocusMode() {
  focusPairId.value = ''
}

function selectRelationshipPair(pairId) {
  const normalizedPairId = String(pairId || '').trim()
  if (!normalizedPairId) return
  selectedPairId.value = normalizedPairId
  focusPairId.value = ''
}

async function handleThemeChange(theme) {
  const normalizedTheme = saveStoredRelationshipSpaceTheme(theme)
  const previousTheme = selectedTheme.value

  if (normalizedTheme === previousTheme && userStore.me?.relationship_space_theme === normalizedTheme) {
    return
  }

  selectedTheme.value = normalizedTheme

  if (!userStore.me || userStore.isDemoMode) {
    if (userStore.me) {
      userStore.me = {
        ...userStore.me,
        relationship_space_theme: normalizedTheme,
      }
    }
    showToast(`已切换到${getRelationshipThemeOption(normalizedTheme).label}`)
    return
  }

  savingTheme.value = true
  try {
    await userStore.updateMe({ relationship_space_theme: normalizedTheme })
    showToast(`已保存${getRelationshipThemeOption(normalizedTheme).label}`)
  } catch (e) {
    selectedTheme.value = previousTheme
    saveStoredRelationshipSpaceTheme(previousTheme)
    userStore.me = {
      ...userStore.me,
      relationship_space_theme: previousTheme,
    }
    showToast(e.message || '主题没保存上，请稍后再试')
  } finally {
    savingTheme.value = false
  }
}

async function openRelationshipDetail(pairId) {
  const targetPairId = String(pairId || selectedPairId.value || '')
  if (!targetPairId) return
  if (targetPairId !== userStore.currentPairId) {
    await userStore.switchPair(targetPairId)
  }
  router.push(buildRelationshipSpaceDetailRoute(targetPairId))
}

async function handleCreate(options = {}) {
  const { silentToast = false } = options
  creating.value = true
  try {
    const pair = await userStore.createPair()
    selectedPairId.value = pair?.id || selectedPairId.value
    focusPairId.value = pair?.id || focusPairId.value
    if (!silentToast) {
      showToast('邀请码已准备好')
    }
    if (route.path !== RELATIONSHIP_INVITE_ROUTE) {
      await router.push(RELATIONSHIP_INVITE_ROUTE)
    }
  } catch (e) {
    showToast(e.message || '邀请码没创建出来，请稍后再试')
  } finally {
    creating.value = false
  }
}

async function handlePreviewJoin() {
  const normalizedCode = normalizeInviteCode(joinCode.value)
  joinCode.value = normalizedCode
  if (normalizedCode.length !== INVITE_CODE_LENGTH) {
    showToast('请输入 10 位邀请代码')
    return
  }
  if (!INVITE_CODE_PATTERN.test(normalizedCode)) {
    showToast('邀请代码格式不对，请核对后再试')
    return
  }

  joining.value = true
  try {
    const preview = await userStore.previewJoinPair(normalizedCode)
    if (preview?.pending_request) {
      await userStore.fetchPairs()
      showToast('你已经提交过加入请求了，等对方确认就好')
      return
    }
    joinPreview.value = preview
    joinSelectedType.value = createOptions.value[0]?.value || 'friend'
    joinModalOpen.value = true
    if (route.path !== RELATIONSHIP_JOIN_ROUTE) {
      await router.push(RELATIONSHIP_JOIN_ROUTE)
    }
  } catch (e) {
    showToast(e.message || '邀请码没核对上，请稍后再试')
  } finally {
    joining.value = false
  }
}

function closeJoinModal() {
  joinModalOpen.value = false
  joinPreview.value = null
  submittingJoinRequest.value = false
}

async function submitJoinRequest() {
  if (!joinPreview.value?.invite_code) return

  submittingJoinRequest.value = true
  try {
    const res = await userStore.joinPair(joinPreview.value.invite_code, joinSelectedType.value)
    const pairId = res?.pair?.id || ''
    if (pairId) {
      selectedPairId.value = pairId
      focusPairId.value = pairId
    }
    closeJoinModal()
    showToast('已提交给对方确认，确认后才会正式生效')
    if (route.path !== RELATIONSHIP_LIST_ROUTE) {
      await router.push(RELATIONSHIP_LIST_ROUTE)
    }
  } catch (e) {
    showToast(e.message || '这次没提交上，请稍后再试')
  } finally {
    submittingJoinRequest.value = false
  }
}

async function handleRefreshInviteCode() {
  const pairId = String(currentInvitePair.value?.id || '')
  if (!pairId) return
  const remainingSeconds = inviteRefreshGuard.getRemainingSeconds()
  if (remainingSeconds > 0) {
    showToast(`邀请码换得有点频繁了，请 ${remainingSeconds} 秒后再试`)
    return
  }

  refreshingInviteCode.value = true
  try {
    await userStore.refreshPairInviteCode(pairId)
    inviteRefreshGuard.markRun()
    if (currentInvitePendingRequest.value) {
      showToast('邀请码已刷新，当前待确认申请不受影响')
    } else {
      showToast('邀请码已刷新，旧码已失效')
    }
  } catch (e) {
    const retryAfterSeconds = parseRetryAfterSeconds(e.message)
    if (retryAfterSeconds > 0) {
      inviteRefreshGuard.setCooldown(retryAfterSeconds)
    }
    showToast(e.message || '邀请码没换成功，请稍后再试')
  } finally {
    refreshingInviteCode.value = false
  }
}

async function copyCode() {
  const code = currentPairInviteCode.value
  if (!code) return
  try {
    await navigator.clipboard.writeText(code)
    showToast('邀请码已复制')
  } catch {
    showToast('没复制成功，可以手动复制')
  }
}

function shouldDeferRouteSectionSync() {
  return activeRouteSection.value === 'pair-join' && (joinInputFocused.value || joinCodeComposing.value)
}

function queueRouteSectionSync(sectionId, { behavior = 'auto', force = false } = {}) {
  const normalizedSectionId = String(sectionId || '').replace(/^#/, '').trim()
  if (!normalizedSectionId) return
  if (!force && shouldDeferRouteSectionSync()) {
    pendingRouteSectionScroll.value = normalizedSectionId
    return
  }

  pendingRouteSectionScroll.value = ''
  nextTick(() => {
    if (sectionSyncFrame) {
      cancelAnimationFrame(sectionSyncFrame)
    }
    sectionSyncFrame = requestAnimationFrame(() => {
      sectionSyncFrame = 0
      scrollToSection(normalizedSectionId, { behavior })
    })
  })
}

function flushPendingRouteSectionSync() {
  const sectionId = pendingRouteSectionScroll.value
  if (!sectionId) return
  pendingRouteSectionScroll.value = ''
  queueRouteSectionSync(sectionId, { behavior: 'auto', force: true })
}

function scrollToSection(sectionId, { behavior = 'auto' } = {}) {
  const element = document.getElementById(sectionId)
  if (!element) return
  element.scrollIntoView({ behavior, block: 'start' })
}
</script>

<style scoped>
.pair-page {
  --pair-theme-glow-a: rgba(215, 104, 72, 0.08);
  --pair-theme-glow-b: rgba(220, 235, 238, 0.24);
  --pair-theme-surface-start: rgba(255, 250, 244, 0.82);
  --pair-theme-surface-end: rgba(249, 241, 232, 0.92);
  --pair-theme-chip-active-bg: rgba(189, 75, 53, 0.12);
  --pair-theme-chip-active-border: rgba(189, 75, 53, 0.24);
  --pair-theme-chip-active-color: var(--warm-700);
  gap: 18px;
  padding-bottom: 36px;
}

.pair-page__head {
  width: 100%;
  padding-bottom: 0;
}

.pair-shortcuts {
  flex-wrap: wrap;
  gap: 8px;
}

.pair-shortcuts__button.active {
  background: var(--pair-theme-chip-active-bg);
  border-color: var(--pair-theme-chip-active-border);
  color: var(--pair-theme-chip-active-color);
}

.pair-overview__main {
  display: grid;
  align-content: start;
  gap: 14px;
  min-width: 0;
}

.pair-list-panel {
  display: grid;
  gap: 16px;
  padding: 20px;
  border: 1px solid rgba(68, 52, 40, 0.08);
  border-radius: 26px;
  background: rgba(255, 253, 250, 0.68);
}

.pair-list-panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.pair-list-panel__head h3 {
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: clamp(28px, 2.4vw, 38px);
  line-height: 1.25;
}

.pair-list-panel__head > span,
.pair-list-card__score {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(189, 75, 53, 0.1);
  color: var(--seal-deep);
  font-size: 13px;
  font-weight: 800;
}

.pair-list-panel__head > .pair-list-count {
  min-width: 82px;
  padding-inline: 12px;
  white-space: nowrap;
}

.pair-list-panel__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.pair-list-card {
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  min-height: 92px;
  padding: 16px;
  border: 1px solid rgba(68, 52, 40, 0.08);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.66);
  text-align: left;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}

.pair-list-card:hover,
.pair-list-card.active {
  transform: translateY(-1px);
  border-color: rgba(189, 75, 53, 0.24);
  background: rgba(255, 248, 243, 0.92);
  box-shadow: 0 12px 24px rgba(170, 77, 51, 0.06);
}

.pair-list-card__avatar {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(255, 225, 206, 0.96), rgba(255, 240, 232, 0.92));
  color: var(--seal-deep);
  font-size: 18px;
  font-weight: 900;
}

.pair-list-card__copy {
  display: grid;
  gap: 5px;
  min-width: 0;
}

.pair-list-card__copy strong {
  color: var(--ink);
  font-size: 18px;
  line-height: 1.35;
}

.pair-list-card__copy span {
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.5;
}

.pair-list-card__score {
  background: rgba(232, 240, 244, 0.88);
  color: var(--sky-deep);
}

.pair-theme-switch {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: fit-content;
  max-width: 100%;
  margin: 0 auto;
  padding: 6px;
  border: 1px solid rgba(68, 52, 40, 0.08);
  border-radius: 999px;
  background: rgba(255, 251, 247, 0.72);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(10px);
}

.pair-theme-switch__label {
  color: rgba(95, 71, 60, 0.72);
  padding: 0 8px 0 4px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  white-space: nowrap;
}

.pair-theme-switch__button {
  min-height: 30px;
  padding: 0 12px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: transparent;
  color: rgba(95, 71, 60, 0.76);
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease, color 0.18s ease;
}

.pair-theme-switch__button:hover {
  transform: translateY(-1px);
  color: rgba(68, 52, 40, 0.92);
}

.pair-theme-switch__button.active {
  border-color: rgba(189, 75, 53, 0.24);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(255, 248, 242, 0.92));
  box-shadow: 0 6px 14px rgba(170, 77, 51, 0.08);
  color: var(--seal-deep);
}

.pair-overview {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.28fr) minmax(320px, 0.72fr);
  gap: 16px;
  align-items: start;
}

.pair-overview__sidebar {
  width: 100%;
}

.pair-overview.is-empty .pair-overview__sidebar {
  align-self: center;
}

.pair-solo-intro {
  display: grid;
  gap: 12px;
  padding: 20px 22px;
  border: 1px solid rgba(68, 52, 40, 0.08);
  border-radius: 28px;
  background: linear-gradient(180deg, rgba(255, 252, 247, 0.94), rgba(250, 244, 237, 0.9));
  box-shadow: 0 14px 28px rgba(91, 67, 51, 0.05);
}

.pair-solo-intro__copy {
  display: grid;
  gap: 6px;
}

.pair-solo-intro__copy h3 {
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: clamp(28px, 2.2vw, 34px);
  line-height: 1.24;
}

.pair-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.pair-entry-card {
  display: grid;
  align-content: start;
  gap: 16px;
  padding: 22px;
  border: 1px solid rgba(68, 52, 40, 0.08);
  border-radius: 26px;
  background: linear-gradient(180deg, rgba(255, 252, 247, 0.95), rgba(250, 244, 237, 0.9));
  box-shadow: 0 16px 32px rgba(91, 67, 51, 0.05);
}

.pair-entry-card.is-active {
  border-color: rgba(189, 75, 53, 0.22);
  box-shadow: 0 20px 40px rgba(170, 77, 51, 0.08);
}

.pair-entry-card__head {
  display: grid;
  gap: 6px;
}

.pair-entry-card__head h3 {
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: clamp(28px, 2.2vw, 34px);
  line-height: 1.24;
}

.pair-entry-card__field {
  gap: 10px;
}

.pair-entry-card__field :deep(span) {
  color: var(--ink);
  font-size: 15px;
  font-weight: 800;
}

.pair-entry-card__input {
  min-height: 58px;
  padding: 0 18px;
  font-size: 18px;
  font-weight: 600;
}

.pair-entry-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.pair-entry-card__primary {
  min-height: 50px;
  font-size: 16px;
  font-weight: 800;
}

.pair-invite-code,
.pair-empty-state {
  display: grid;
  gap: 10px;
  padding: 18px;
  border: 1px solid rgba(68, 52, 40, 0.08);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.76);
}

.pair-empty-state strong {
  color: var(--ink);
  font-size: 22px;
  font-family: var(--font-serif);
  line-height: 1.35;
}

.pair-invite-code strong {
  color: var(--seal-deep);
  font-family: var(--font-serif);
  font-size: clamp(32px, 4vw, 44px);
  line-height: 1.05;
  letter-spacing: 0.03em;
  word-break: break-all;
}

.pair-invite-code__status {
  display: inline-flex;
  width: fit-content;
  align-items: center;
  justify-content: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
}

.pair-invite-code__status.is-pending,
.pair-invite-code__status.is-none {
  background: rgba(189, 75, 53, 0.1);
  color: var(--seal-deep);
}

.pair-invite-code__status.is-active {
  background: rgba(88, 124, 98, 0.14);
  color: var(--success);
}

.pair-invite-code__status.is-waiting-for-me {
  background: rgba(240, 184, 116, 0.2);
  color: var(--amber-deep);
}

.pair-invite-code__status.is-waiting-other {
  background: rgba(132, 150, 205, 0.16);
  color: #4a5d8a;
}

.pair-modal {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(29, 20, 16, 0.38);
  backdrop-filter: blur(10px);
}

.pair-modal__paper {
  width: min(100%, 620px);
  max-height: min(82vh, 720px);
  overflow-y: auto;
  scrollbar-gutter: stable;
  display: grid;
  gap: 18px;
  padding: 24px;
  border-radius: 28px;
  border: 1px solid rgba(68, 52, 40, 0.08);
  background: linear-gradient(180deg, rgba(255, 252, 248, 0.98), rgba(250, 244, 237, 0.96));
  box-shadow: 0 24px 54px rgba(28, 18, 13, 0.18);
}

.pair-modal__head {
  display: grid;
  gap: 6px;
}

.pair-modal__head h3 {
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: clamp(28px, 2.3vw, 34px);
  line-height: 1.24;
}

.pair-modal__types {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pair-modal__type {
  min-height: 36px;
  padding: 0 14px;
  border: 1px solid rgba(68, 52, 40, 0.1);
  border-radius: 999px;
  background: rgba(255, 253, 250, 0.72);
  color: var(--ink);
  font-size: 13px;
  font-weight: 700;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease, color 0.18s ease;
}

.pair-modal__type:hover {
  transform: translateY(-1px);
  border-color: rgba(189, 75, 53, 0.22);
}

.pair-modal__type.active {
  border-color: rgba(189, 75, 53, 0.3);
  background: var(--seal-soft);
  color: var(--seal-deep);
}

.pair-modal__actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.pair-page--theme-stardust {
  --pair-theme-glow-a: rgba(206, 173, 233, 0.14);
  --pair-theme-glow-b: rgba(202, 222, 255, 0.28);
  --pair-theme-surface-start: rgba(255, 251, 247, 0.88);
  --pair-theme-surface-end: rgba(246, 240, 243, 0.94);
  --pair-theme-chip-active-bg: rgba(219, 204, 245, 0.2);
  --pair-theme-chip-active-border: rgba(158, 132, 214, 0.22);
  --pair-theme-chip-active-color: #6f5f97;
}

.pair-page--theme-engine {
  --pair-theme-glow-a: rgba(255, 185, 112, 0.16);
  --pair-theme-glow-b: rgba(170, 235, 244, 0.28);
  --pair-theme-surface-start: rgba(255, 251, 247, 0.88);
  --pair-theme-surface-end: rgba(239, 244, 247, 0.94);
  --pair-theme-chip-active-bg: rgba(170, 235, 244, 0.2);
  --pair-theme-chip-active-border: rgba(92, 191, 214, 0.24);
  --pair-theme-chip-active-color: #326a78;
}

@media (max-width: 1080px) {
  .pair-overview,
  .pair-actions {
    grid-template-columns: 1fr;
  }

  .pair-overview {
    min-height: auto;
  }

  .pair-overview__sidebar {
    min-height: 0;
  }

  .pair-theme-switch {
    justify-content: flex-start;
    margin: 0;
  }
}

@media (max-width: 760px) {
  .pair-page {
    width: min(100% - 20px, 1200px);
    padding-bottom: calc(var(--tabbar-height) + env(safe-area-inset-bottom, 0px) + 28px);
  }

  .pair-overview {
    border-radius: 24px;
  }

  .pair-theme-switch {
    justify-content: center;
    gap: 6px;
    width: 100%;
    padding: 6px;
  }

  .pair-theme-switch__label {
    width: 100%;
    padding: 0 2px 2px;
    text-align: center;
  }

  .pair-list-panel {
    padding: 16px;
    border-radius: 22px;
  }

  .pair-list-panel__head {
    display: flex;
  }

  .pair-list-panel__grid {
    grid-template-columns: 1fr;
  }

  .pair-list-card {
    min-height: 78px;
    padding: 13px;
    border-radius: 18px;
  }

  .pair-entry-card {
    padding: 18px;
    border-radius: 22px;
  }

  .pair-entry-card__head h3,
  .pair-modal__head h3 {
    font-size: 26px;
  }

  .pair-modal__paper {
    padding: 20px;
    border-radius: 24px;
  }
}

@media (max-width: 560px) {
  .pair-entry-card__actions,
  .pair-modal__actions {
    grid-template-columns: 1fr;
    display: grid;
  }

  .pair-entry-card__actions .btn,
  .pair-modal__actions .btn {
    width: 100%;
  }
}
</style>
