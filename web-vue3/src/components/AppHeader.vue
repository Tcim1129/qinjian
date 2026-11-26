<template>
  <header class="app-header">
    <div class="header-left">
      <button class="header-back" type="button" aria-label="返回上一页" @click="goBack">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M15 18l-6-6 6-6" />
        </svg>
      </button>

      <button class="header-brand-block" type="button" @click="router.push('/')">
        <span class="header-logo-wrap">
          <img src="/qinjian-logo.jpg" alt="亲健 logo" class="header-logo" />
        </span>
        <span class="header-brand">亲健</span>
        <span class="header-page-pill">{{ currentSectionLabel }}</span>
      </button>

      <div v-if="headerObjects.length > 1" class="header-object-wrap">
        <button
          type="button"
          class="header-object-pill"
          :class="{ active: objectMenuOpen }"
          :aria-expanded="objectMenuOpen"
          @click.stop="toggleObjectMenu"
          title="切换当前互动对象"
        >
          <span class="header-object-avatar" :style="{ backgroundColor: currentHeaderObject?.themeColor }">
            {{ currentHeaderObject?.avatar }}
          </span>
          <span class="header-object-name">{{ currentHeaderObject?.name }}</span>
          <ChevronDown class="header-object-chevron" :size="13" />
        </button>

        <div v-if="objectMenuOpen" class="header-object-menu" @click.stop>
          <p class="header-object-menu__title">切换对象</p>
          <button
            v-for="obj in headerObjects"
            :key="obj.id"
            type="button"
            class="header-object-menu__item"
            :class="{ active: String(obj.id) === String(userStore.activePairId) }"
            @click="switchHeaderObject(obj.id)"
          >
            <span class="header-object-avatar" :style="{ backgroundColor: obj.themeColor }">
              {{ obj.avatar }}
            </span>
            <div class="header-object-menu__text">
              <strong>{{ obj.name }}</strong>
              <span>{{ obj.roleLabel }}</span>
            </div>
          </button>
        </div>
      </div>
    </div>

    <nav class="header-nav" aria-label="主导航">
      <div
        v-for="item in navItems"
        :key="item.key"
        class="nav-item-wrap"
        :class="{ 'is-open': openNavKey === item.key }"
        @pointerenter="enterNav(item, $event)"
        @pointerleave="leaveNav"
        @focusout="leaveNavFocus($event)"
        @keydown.esc.stop="openNavKey = ''"
        :style="{ '--nav-accent': item.accent, '--nav-soft': item.soft }"
      >
        <button
          type="button"
          class="nav-item"
          :class="{ active: isNavActive(item) }"
          :aria-expanded="item.children?.length ? openNavKey === item.key : undefined"
          @keydown.down.prevent="item.children?.length && (openNavKey = item.key)"
          @click.stop="goNav(item)"
        >
          <span class="nav-item__label">{{ item.label }}</span>
          <ChevronDown v-if="item.children?.length" class="nav-item__chevron" :size="13" stroke-width="2.4" />
        </button>

        <div v-if="item.children?.length && openNavKey === item.key" class="nav-menu">
          <button
            v-for="child in item.children"
            :key="child.to"
            type="button"
            class="nav-menu__item"
            :class="{ active: isChildActive(child.to) }"
            @click.stop="openNavKey = ''; router.push(child.to)"
          >
            <span>{{ child.label }}</span>
            <small v-if="child.desc">{{ child.desc }}</small>
          </button>
        </div>
      </div>
    </nav>

    <div class="header-right">
      <form class="header-search" @submit.prevent="submitSearch">
        <input
          v-model.trim="searchQuery"
          class="header-search__input"
          type="search"
          placeholder="搜索功能"
          @focus="searchOpen = true"
          @blur="closeSearchLater"
        />
        <div v-if="searchOpen && filteredSearchItems.length" class="header-search__panel">
          <button
            v-for="item in filteredSearchItems"
            :key="item.to"
            type="button"
            class="header-search__item"
            @mousedown.prevent="openSearchItem(item)"
          >
            <span>{{ item.label }}</span>
            <strong>{{ item.title }}</strong>
          </button>
        </div>
      </form>

      <button
        class="header-write-action"
        :class="{ active: route.name === 'checkin' }"
        type="button"
        @click="router.push('/checkin')"
      >
        <PenLine :size="14" stroke-width="2.3" />
        <span>写今天</span>
      </button>

      <button
        class="header-mobile-discover"
        :class="{ active: route.name === 'discover' }"
        type="button"
        aria-label="全部功能"
        @click="router.push('/discover')"
      >
        <LayoutGrid :size="15" stroke-width="2.1" />
        <span>全部</span>
      </button>

      <button class="header-bell" type="button" aria-label="打开消息通知" @click="showNotif = !showNotif">
        <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9">
          <path d="M18 15V11a6 6 0 1 0-12 0v4l-2 2h16z" />
          <path d="M10 19a2 2 0 0 0 4 0" />
        </svg>
        <span v-if="userStore.unreadCount > 0" class="bell-badge">{{ userStore.unreadCount > 9 ? '9+' : userStore.unreadCount }}</span>
      </button>

      <div
        class="nav-item-wrap header-user-wrap"
        :class="{ 'is-open': openNavKey === mineNavItem.key }"
        @pointerenter="enterNav(mineNavItem, $event)"
        @pointerleave="leaveNav"
        @focusout="leaveNavFocus($event)"
        @keydown.esc.stop="openNavKey = ''"
        :style="{ '--nav-accent': mineNavItem.accent, '--nav-soft': mineNavItem.soft }"
      >
        <button
          type="button"
          class="header-user-pill"
          :class="{ active: isNavActive(mineNavItem) }"
          :aria-expanded="openNavKey === mineNavItem.key"
          @keydown.down.prevent="openNavKey = mineNavItem.key"
          @click.stop="goNav(mineNavItem)"
        >
          <span class="header-user-avatar">
            <img v-if="userAvatarUrl" :src="userAvatarUrl" alt="我的头像" />
            <span v-else>{{ userAvatarInitial }}</span>
          </span>
          <span class="header-user-label">我的</span>
          <ChevronDown class="nav-item__chevron" :size="13" stroke-width="2.4" />
        </button>

        <div v-if="openNavKey === mineNavItem.key" class="nav-menu nav-menu--right">
          <button
            v-for="child in mineNavItem.children"
            :key="child.to"
            type="button"
            class="nav-menu__item"
            :class="{ active: isChildActive(child.to) }"
            @click.stop="openNavKey = ''; router.push(child.to)"
          >
            <span>{{ child.label }}</span>
          </button>
          <button
            v-if="userStore.isDemoMode"
            type="button"
            class="nav-menu__item nav-menu__item--danger"
            @click.stop="openNavKey = ''; exitAccount()"
          >
            <span>退出样例</span>
          </button>
        </div>
      </div>
    </div>
  </header>

  <Teleport to="body">
    <div v-if="showNotif" class="notif-overlay" @click.self="showNotif = false">
      <div class="notif-drawer">
        <div class="notif-drawer__head">
          <h3>消息</h3>
          <button
            v-if="userStore.notifications.length"
            class="btn btn-ghost btn-sm"
            :disabled="markingAllRead"
            @click="markRead"
          >
            {{ markingAllRead ? '处理中...' : '全部已读' }}
          </button>
        </div>
        <div class="notif-drawer__body">
          <div v-if="!userStore.notifications.length" class="empty-state">暂无消息</div>
          <div v-else class="stack-list">
            <button
              v-for="n in userStore.notifications"
              :key="n.id"
              type="button"
              class="stack-item notif-item"
              :class="{ 'notif-item--unread': !n.is_read, 'notif-item--clickable': Boolean(n.target_path) }"
              @click="openNotification(n)"
            >
              <div class="stack-item__icon" style="background:var(--warm-100);color:var(--warm-600);">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="M18 15V11a6 6 0 1 0-12 0v4l-2 2h16z" />
                </svg>
              </div>
              <div class="stack-item__content">
                <strong>{{ n.content }}</strong>
                <div class="stack-item__meta">
                  <span>{{ formatDate(n.created_at) }}</span>
                  <span v-if="n.target_path" class="notif-item__hint">查看</span>
                </div>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { api } from '@/api'
import { listDemoPersonas } from '@/demo/fixtures'
import { relationshipTypeLabel } from '@/utils/displayText'
import { getPartnerDisplayName } from '@/utils/relationshipSpaces'
import { formatBeijingMonthDayTime } from '@/utils/datetime'
import { ChevronDown, LayoutGrid, PenLine } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const showToast = inject('showToast', () => {})
const showNotif = ref(false)
const markingAllRead = ref(false)
const markingNotificationIds = new Set()
const searchQuery = ref('')
const searchOpen = ref(false)
const objectMenuOpen = ref(false)
const openNavKey = ref('')
let navCloseTimer

function enterNav(item, event) {
  if (event.pointerType === 'touch') return
  clearTimeout(navCloseTimer)
  objectMenuOpen.value = false
  openNavKey.value = item.children?.length ? item.key : ''
}

function leaveNav() {
  clearTimeout(navCloseTimer)
  navCloseTimer = setTimeout(() => { openNavKey.value = '' }, 160)
}

function leaveNavFocus(event) {
  if (!event.currentTarget.contains(event.relatedTarget)) openNavKey.value = ''
}

function toggleObjectMenu() {
  openNavKey.value = ''
  objectMenuOpen.value = !objectMenuOpen.value
}

watch(() => route.fullPath, () => {
  openNavKey.value = ''
  objectMenuOpen.value = false
})

const titleMap = {
  home: '首页',
  checkin: '记录',
  chat: '聊一聊',
  discover: '全部功能',
  report: '简报',
  profile: '我的',
  pair: '关系',
  'pair-waiting': '关系',
  'relationship-spaces': '关系',
  'relationship-space-detail': '关系',
  milestones: '纪念日',
  longdistance: '异地',
  'health-test': '体检',
  'attachment-test': '依恋',
  community: '技巧',
  challenges: '安排',
  courses: '课程',
  experts: '咨询',
  membership: '会员',
  alignment: '双视角',
  timeline: '关系日历',
  'message-simulation': '发前看看',
  'repair-protocol': '缓和',
  methodology: '说明',
  'privacy-security': '隐私',
}

const navItems = [
  {
    key: 'home',
    label: '首页',
    to: '/',
    match: ['home'],
    accent: '#d76848',
    soft: 'rgba(215, 104, 72, 0.13)',
  },
  {
    key: 'chat',
    label: '聊一聊',
    to: '/chat',
    match: ['chat', 'repair-protocol'],
    accent: '#bd4b35',
    soft: 'rgba(189, 75, 53, 0.14)',
    children: [
      { label: '聊一聊', desc: '随时整理情绪和想法', to: '/chat' },
      { label: '缓和建议', desc: '吵架后先降火再开口', to: '/repair-protocol' },
    ],
  },
  {
    key: 'simulation',
    label: '发前看看',
    to: '/message-simulation',
    match: ['message-simulation'],
    accent: '#c7763f',
    soft: 'rgba(199, 118, 63, 0.15)',
  },
  {
    key: 'alignment',
    label: '双视角',
    to: '/alignment',
    match: ['alignment'],
    accent: '#3b6d8c',
    soft: 'rgba(59, 109, 140, 0.14)',
  },
  {
    key: 'report',
    label: '简报',
    to: '/report',
    match: ['report', 'timeline', 'challenges', 'methodology'],
    accent: '#305d68',
    soft: 'rgba(48, 93, 104, 0.14)',
    children: [
      { label: '关系简报', desc: '日报、周报与走势', to: '/report' },
      { label: '关系日历', desc: '按日期回看往事', to: '/timeline' },
      { label: '今日安排', desc: '今天的小事与约定', to: '/challenges' },
      { label: '判断说明', desc: '了解分析依据', to: '/methodology' },
    ],
  },
  {
    key: 'overview',
    label: '全部功能',
    to: '/discover',
    match: ['discover', 'health-test', 'attachment-test', 'longdistance', 'milestones', 'community', 'courses', 'experts', 'membership'],
    accent: '#4f7a62',
    soft: 'rgba(79, 122, 98, 0.15)',
    children: [
      { label: '全部功能目录', desc: '按分类浏览全部入口', to: '/discover' },
      { label: '关系体检', desc: '定期评估相处状态', to: '/health-test' },
      { label: '依恋测评', desc: '了解各自相处习惯', to: '/attachment-test' },
      { label: '异地陪伴', desc: '远距离也能保持节奏', to: '/longdistance' },
      { label: '关系纪念日', desc: '记住值得留念的日子', to: '/milestones' },
      { label: '相处技巧', desc: '日常沟通参考方法', to: '/community' },
    ],
  },
]

const mineNavItem = {
  key: 'mine',
  label: '我的',
  to: '/profile',
  match: ['profile', 'pair', 'pair-waiting', 'relationship-spaces', 'relationship-space-detail', 'privacy-security'],
  accent: '#aa4d33',
  soft: 'rgba(170, 77, 51, 0.14)',
  children: [
    { label: '个人中心', to: '/profile' },
    { label: '关系管理', to: '/pair' },
    { label: '关系空间', to: '/relationship-spaces' },
    { label: '隐私安全', to: '/privacy-security' },
  ],
}

const searchItems = [
  { label: '首页', title: '首页工作台', to: '/', keywords: ['首页', '简报可以看了'] },
  { label: '聊一聊', title: '像聊天一样整理今天', to: '/chat', keywords: ['聊天', '聊一聊', '整理今天', '对话', 'AI'] },
  { label: '发前看看', title: '发送前语气预演与改写', to: '/message-simulation', keywords: ['预演', '消息', '发前看看', '改写'] },
  { label: '双视角', title: '双方视角对照与换位看', to: '/alignment', keywords: ['双视角', '对齐', '双方说法', '换视角'] },
  { label: '记录', title: '写下今日记录', to: '/checkin', keywords: ['记录', '打卡', '写今天'] },
  { label: '缓和', title: '缓和建议', to: '/repair-protocol', keywords: ['缓和', '修复', '建议', '吵架'] },
  { label: '简报', title: '关系简报', to: '/report', keywords: ['简报', '报告', '周报', '月报'] },
  { label: '日历', title: '关系日历', to: '/timeline', keywords: ['关系日历', '日历', '历史', '时间线'] },
  { label: '安排', title: '今日安排', to: '/challenges', keywords: ['安排', '任务', '提醒'] },
  { label: '全部', title: '全部功能目录', to: '/discover', keywords: ['总览', '发现', '目录', '全部'] },
  { label: '体检', title: '关系体检', to: '/health-test', keywords: ['体检', '问卷', '评估', '测试'] },
  { label: '依恋', title: '依恋类型', to: '/attachment-test', keywords: ['依恋', '相处方式', '焦虑', '回避'] },
  { label: '异地', title: '异地陪伴', to: '/longdistance', keywords: ['异地', '远程', '活动'] },
  { label: '纪念日', title: '关系纪念日', to: '/milestones', keywords: ['纪念日', '重要日期', '周年'] },
  { label: '技巧', title: '相处技巧', to: '/community', keywords: ['技巧', '方法', '社区'] },
  { label: '关系', title: '关系管理', to: '/pair', keywords: ['关系', '邀请', '切换', '建立关系'] },
  { label: '空间', title: '关系空间', to: '/relationship-spaces', keywords: ['关系空间', '空间', '关系树'] },
  { label: '我的', title: '个人中心', to: '/profile', keywords: ['我的', '头像', '昵称', '偏好'] },
  { label: '隐私', title: '隐私与安全', to: '/privacy-security', keywords: ['隐私', '安全', '注销', '删除账号'] },
  { label: '说明', title: '判断说明', to: '/methodology', keywords: ['说明', '怎么判断', '方法'] },
]

const currentSectionLabel = computed(() => titleMap[route.name] || '首页')
const userAvatarUrl = computed(() => userStore.me?.avatar_url || '')
const userAvatarInitial = computed(() => String(userStore.me?.nickname || '我').slice(0, 1))
const filteredSearchItems = computed(() => {
  const keyword = searchQuery.value.trim().toLowerCase()
  if (!keyword) return searchItems.slice(0, 6)
  return searchItems
    .filter((item) => [item.label, item.title, ...item.keywords].some((value) => String(value).toLowerCase().includes(keyword)))
    .slice(0, 8)
})

function isNavActive(item) {
  return item.match.includes(String(route.name || ''))
}

function isChildActive(path) {
  return route.path === path
}

function goNav(item) {
  clearTimeout(navCloseTimer)
  if (item.children?.length && route.path === item.to) {
    openNavKey.value = openNavKey.value === item.key ? '' : item.key
    return
  }
  openNavKey.value = ''
  router.push(item.to)
}

async function openNotification(item) {
  showNotif.value = false
  if (item?.target_path) {
    router.push(item.target_path)
  }
  if (!item || item.is_read) return
  if (userStore.isDemoMode) {
    item.is_read = true
    return
  }
  if (!item.id || markingNotificationIds.has(item.id)) return
  const requestToken = userStore.token
  const requestUserId = userStore.me?.id
  markingNotificationIds.add(item.id)
  try {
    await api.markNotificationRead(item.id)
    if (userStore.token === requestToken && userStore.me?.id === requestUserId) {
      item.is_read = true
      const matched = userStore.notifications.find((n) => n.id === item.id)
      if (matched) matched.is_read = true
    }
  } catch (error) {
    if (userStore.token === requestToken && userStore.me?.id === requestUserId) {
      showToast(error?.message || '这条消息暂时没标成已读，请稍后再试')
    }
  } finally {
    markingNotificationIds.delete(item.id)
  }
}

function openSearchItem(item) {
  searchQuery.value = ''
  searchOpen.value = false
  router.push(item.to)
}

function submitSearch() {
  const first = filteredSearchItems.value[0]
  if (first) openSearchItem(first)
}

function closeSearchLater() {
  window.setTimeout(() => {
    searchOpen.value = false
  }, 120)
}

function goBack() {
  showNotif.value = false
  if (window.history.length > 1) {
    router.back()
    return
  }
  router.push('/')
}

function exitAccount() {
  userStore.logout()
  router.push('/auth')
}

function formatDate(v) {
  return formatBeijingMonthDayTime(v)
}

async function markRead() {
  if (markingAllRead.value) return
  const unreadItems = userStore.notifications.filter((n) => !n.is_read)
  if (!unreadItems.length) return
  if (userStore.isDemoMode) {
    unreadItems.forEach((n) => { n.is_read = true })
    return
  }
  const requestToken = userStore.token
  const requestUserId = userStore.me?.id
  markingAllRead.value = true
  try {
    await api.markNotificationsRead()
    if (userStore.token === requestToken && userStore.me?.id === requestUserId) {
      userStore.notifications.forEach((n) => { n.is_read = true })
    }
  } catch (error) {
    if (userStore.token === requestToken && userStore.me?.id === requestUserId) {
      showToast(error?.message || '全部已读没成功，请稍后再试')
    }
  } finally {
    markingAllRead.value = false
  }
}

const headerObjects = computed(() => {
  if (userStore.isDemoMode) {
    return listDemoPersonas().map(p => ({
      id: p.id,
      name: p.name,
      roleLabel: p.roleLabel,
      avatar: p.avatar,
      themeColor: p.themeColor,
    }))
  }
  return (userStore.pairs || []).filter(p => p.status === 'active').map(pair => {
    const displayName = getPartnerDisplayName(pair)
    return {
      id: pair.id,
      name: displayName,
      roleLabel: relationshipTypeLabel(pair.type),
      avatar: displayName.slice(0, 1) || '伴',
      themeColor: '#b86248',
    }
  })
})

const currentHeaderObject = computed(() => {
  return headerObjects.value.find(o => String(o.id) === String(userStore.activePairId)) || headerObjects.value[0] || null
})

async function switchHeaderObject(targetId) {
  objectMenuOpen.value = false
  if (String(targetId) === String(userStore.activePairId) && (!route.query.pair_id || String(route.query.pair_id) === String(targetId))) return
  await userStore.switchPair(targetId)
  if (route.query.pair_id) {
    await router.replace({ query: { ...route.query, pair_id: targetId } })
  }
}

function closeObjectMenu() {
  objectMenuOpen.value = false
  openNavKey.value = ''
}

onMounted(() => {
  window.addEventListener('click', closeObjectMenu)
})
onBeforeUnmount(() => {
  clearTimeout(navCloseTimer)
  window.removeEventListener('click', closeObjectMenu)
})
</script>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  height: var(--header-height);
  padding: 0 max(18px, calc((100vw - var(--content-max)) / 2));
  border-bottom: 1px solid rgba(44, 48, 39, 0.12);
  background:
    linear-gradient(90deg, rgba(215, 104, 72, 0.08), transparent 28%, rgba(95, 135, 111, 0.07)),
    rgba(255, 252, 248, 0.94);
  backdrop-filter: blur(18px);
  box-shadow: 0 8px 22px rgba(56, 40, 30, 0.045);
}

.header-left,
.header-right,
.header-brand-block,
.header-nav,
.nav-item-wrap,
.nav-item {
  display: flex;
  align-items: center;
}

.header-left {
  min-width: 0;
  gap: 8px;
}

.header-back {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border: 1px solid var(--border-strong);
  border-radius: 11px;
  background: rgba(255, 253, 250, 0.78);
  color: var(--seal-deep);
  transition: background 0.16s ease, border-color 0.16s ease;
}

.header-back:hover {
  background: #fff8f2;
  border-color: rgba(189, 75, 53, 0.34);
}

.header-brand-block {
  min-width: 0;
  gap: 8px;
}

.header-logo-wrap {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border: 1px solid rgba(189, 75, 53, 0.3);
  border-radius: 50%;
  background: #fffdfa;
  box-shadow: var(--shadow-xs);
}

.header-logo {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  object-fit: cover;
}

.header-brand {
  color: var(--seal-deep);
  font-family: var(--font-serif);
  font-size: 18px;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
}

.header-page-pill {
  max-width: 72px;
  padding: 3px 8px;
  overflow: hidden;
  border: 1px solid rgba(68, 52, 40, 0.14);
  border-radius: 999px;
  background: rgba(255, 253, 250, 0.8);
  color: var(--ink-soft);
  font-size: 11px;
  font-weight: 700;
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-nav {
  height: 44px;
  justify-self: center;
  justify-content: center;
  max-width: 100%;
  gap: 4px;
  padding: 3px;
  border: 1px solid rgba(68, 52, 40, 0.09);
  border-radius: 16px;
  background: rgba(255, 251, 246, 0.72);
}

.nav-item-wrap {
  position: relative;
}

.nav-item {
  height: 36px;
  justify-content: center;
  gap: 4px;
  padding: 0 11px;
  border: 1px solid transparent;
  border-radius: 12px;
  background: transparent;
  color: var(--ink-soft);
  font-size: 13.5px;
  font-weight: 700;
  transition: transform 0.16s ease, background 0.16s ease, border-color 0.16s ease, color 0.16s ease, box-shadow 0.16s ease;
}

.nav-item__label {
  white-space: nowrap;
}

.nav-item__chevron {
  flex: 0 0 auto;
  opacity: 0.62;
  transition: opacity 0.16s ease, transform 0.16s ease;
}

.nav-item-wrap:hover .nav-item,
.nav-item-wrap.is-open .nav-item,
.nav-item.active {
  border-color: color-mix(in srgb, var(--nav-accent) 32%, transparent);
  background: linear-gradient(135deg, color-mix(in srgb, var(--nav-accent) 14%, rgba(255, 253, 250, 0.96)), rgba(255, 253, 250, 0.94));
  color: var(--nav-accent);
  box-shadow: 0 4px 12px rgba(56, 40, 30, 0.07);
}

.nav-item-wrap.is-open .nav-item__chevron {
  opacity: 0.95;
  transform: rotate(180deg);
}

.nav-menu {
  position: absolute;
  top: calc(100% + 8px);
  left: 50%;
  z-index: 30;
  min-width: 176px;
  display: grid;
  gap: 3px;
  padding: 6px;
  border: 1px solid var(--border-strong);
  border-radius: 14px;
  background: rgba(255, 253, 250, 0.98);
  box-shadow: 0 14px 32px rgba(56, 40, 30, 0.12);
  transform: translateX(-50%);
}

.nav-menu--right {
  left: auto;
  right: 0;
  min-width: 148px;
  transform: none;
}

.nav-menu::before {
  content: '';
  position: absolute;
  inset: -10px 0 auto;
  height: 10px;
}

.nav-menu__item {
  width: 100%;
  min-height: 36px;
  display: grid;
  gap: 1px;
  padding: 7px 10px;
  border-radius: 10px;
  color: var(--ink);
  font-size: 13px;
  font-weight: 700;
  text-align: left;
  transition: background 0.14s ease, color 0.14s ease;
}

.nav-menu__item small {
  color: var(--ink-faint);
  font-size: 11px;
  font-weight: 500;
  line-height: 1.35;
}

.nav-menu__item:hover,
.nav-menu__item.active {
  background: var(--nav-soft);
  color: var(--nav-accent);
}

.nav-menu__item.active small {
  color: color-mix(in srgb, var(--nav-accent) 76%, var(--ink-soft));
}

.nav-menu__item--danger {
  margin-top: 3px;
  padding-top: 9px;
  border-top: 1px dashed rgba(68, 52, 40, 0.14);
  border-radius: 0 0 10px 10px;
  color: var(--danger);
}

.header-right {
  justify-content: flex-end;
  gap: 8px;
  min-width: 0;
  flex-shrink: 0;
}

.header-search {
  position: relative;
  width: 132px;
  flex-shrink: 0;
  transition: width 0.2s ease;
}

.header-search:focus-within {
  width: 176px;
}

.header-search__input {
  width: 100%;
  height: 36px;
  padding: 0 13px;
  border: 1px solid rgba(68, 52, 40, 0.15);
  border-radius: 999px;
  background: rgba(255, 253, 250, 0.82);
  color: var(--ink);
  font-size: 13px;
  transition: border-color 0.16s ease, background 0.16s ease;
}

.header-search__input:focus {
  border-color: rgba(189, 75, 53, 0.4);
  background: #fffdfa;
}

.header-search__panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 40;
  width: 268px;
  display: grid;
  gap: 3px;
  padding: 8px;
  border: 1px solid var(--border-strong);
  border-radius: 14px;
  background: rgba(255, 253, 250, 0.98);
  box-shadow: var(--shadow-md);
}

.header-search__item {
  display: grid;
  grid-template-columns: 58px 1fr;
  align-items: center;
  gap: 8px;
  padding: 9px 10px;
  border-radius: 10px;
  text-align: left;
}

.header-search__item:hover {
  background: var(--seal-soft);
}

.header-search__item span {
  color: var(--seal-deep);
  font-size: 12px;
  font-weight: 800;
}

.header-search__item strong {
  color: var(--ink);
  font-size: 13px;
  font-weight: 700;
}

.header-write-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 36px;
  padding: 0 14px;
  flex-shrink: 0;
  border: 1px solid rgba(170, 77, 51, 0.2);
  border-radius: 999px;
  background: linear-gradient(135deg, var(--seal), var(--seal-deep));
  color: #fffdfa;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
  box-shadow: 0 6px 14px rgba(170, 77, 51, 0.22);
  transition: transform 0.16s ease, box-shadow 0.16s ease, filter 0.16s ease;
}

.header-write-action:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(170, 77, 51, 0.28);
  filter: brightness(1.03);
}

.header-write-action.active {
  box-shadow: 0 0 0 3px rgba(215, 104, 72, 0.22);
}

.header-mobile-discover {
  display: none;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 34px;
  padding: 0 11px;
  flex-shrink: 0;
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  background: rgba(255, 253, 250, 0.86);
  color: var(--ink);
  font-size: 12.5px;
  font-weight: 700;
  white-space: nowrap;
  transition: border-color 0.16s ease, background 0.16s ease, color 0.16s ease;
}

.header-mobile-discover.active {
  border-color: rgba(79, 122, 98, 0.42);
  background: rgba(220, 231, 218, 0.72);
  color: var(--moss-deep);
}

.header-bell {
  position: relative;
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border: 1px solid var(--border-strong);
  border-radius: 12px;
  background: rgba(255, 253, 250, 0.78);
  color: var(--ink-soft);
  transition: background 0.16s ease, border-color 0.16s ease, color 0.16s ease;
}

.header-bell:hover {
  background: #fff8f2;
  border-color: rgba(189, 75, 53, 0.34);
  color: var(--seal-deep);
}

.bell-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 16px;
  height: 16px;
  display: grid;
  place-items: center;
  padding: 0 4px;
  border-radius: 999px;
  background: var(--danger);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
}

.header-user-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 3px 10px 3px 4px;
  flex-shrink: 0;
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  background: rgba(255, 253, 250, 0.86);
  color: var(--ink);
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
  transition: border-color 0.16s ease, background 0.16s ease, color 0.16s ease;
}

.header-user-wrap:hover .header-user-pill,
.header-user-wrap.is-open .header-user-pill,
.header-user-pill.active {
  border-color: rgba(170, 77, 51, 0.38);
  background: #fff6f0;
  color: var(--seal-deep);
}

.header-user-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  overflow: hidden;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, var(--warm-300), var(--seal-deep));
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.header-user-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.notif-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  justify-content: flex-end;
  background: rgba(37, 40, 33, 0.28);
}

.notif-drawer {
  width: min(380px, 90vw);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--paper-soft);
  box-shadow: var(--shadow-lg);
}

.notif-drawer__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px;
  border-bottom: 1px solid var(--border-strong);
}

.notif-drawer__head h3 {
  font-family: var(--font-serif);
  font-size: 18px;
  font-weight: 700;
}

.notif-drawer__body {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.notif-item {
  width: 100%;
  border: 1px solid transparent;
  background: transparent;
  text-align: left;
  transition: background 0.16s ease, border-color 0.16s ease;
}

.notif-item--clickable {
  cursor: pointer;
}

.notif-item--clickable:hover {
  background: rgba(255, 252, 246, 0.96);
  border-color: var(--border-strong);
}

.notif-item--unread {
  background: rgba(215, 104, 72, 0.06);
}

.notif-item .stack-item__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.notif-item__hint {
  color: var(--seal-deep);
  font-weight: 700;
}

@media (max-width: 1280px) {
  .header-page-pill {
    display: none;
  }

  .nav-item {
    padding: 0 9px;
  }

  .header-search {
    width: 120px;
  }

  .header-search:focus-within {
    width: 156px;
  }
}

@media (max-width: 1180px) {
  .app-header {
    grid-template-columns: auto 1fr auto;
    gap: 10px;
    padding-inline: 14px;
  }

  .header-search {
    display: none;
  }

  .nav-item {
    padding: 0 9px;
    font-size: 13px;
  }

  .header-user-label {
    display: none;
  }

  .header-user-pill {
    padding: 3px 6px 3px 4px;
  }
}

@media (max-width: 900px) {
  .app-header {
    display: flex;
    justify-content: space-between;
    padding: 0 12px;
  }

  .header-page-pill,
  .header-nav,
  .header-search,
  .header-write-action,
  .header-user-wrap {
    display: none;
  }

  .header-mobile-discover {
    display: inline-flex;
  }

  .header-left {
    flex: 1 1 auto;
    gap: 8px;
  }

  .header-brand-block {
    gap: 7px;
  }

  .header-right {
    flex: 0 0 auto;
    justify-content: flex-end;
    gap: 8px;
  }

  .notif-drawer {
    width: 100vw;
  }
}

@media (max-width: 370px) {
  .app-header {
    padding-inline: 10px;
  }

  .header-back,
  .header-logo-wrap,
  .header-bell {
    width: 32px;
    height: 32px;
  }

  .header-logo {
    width: 24px;
    height: 24px;
  }

  .header-brand {
    font-size: 16px;
  }
}

.header-object-wrap {
  position: relative;
  min-width: 0;
  margin-left: 2px;
}

.header-object-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding: 4px 10px 4px 5px;
  background: #fffdfa;
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  font-size: 13px;
  color: var(--ink);
  cursor: pointer;
  box-shadow: var(--shadow-xs);
  transition: all 0.15s ease;
  max-width: 120px;
}

.header-object-pill:hover,
.header-object-pill.active {
  border-color: var(--seal);
  background: #fff8f3;
}

.header-object-avatar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: #fff;
  font-size: 11px;
  font-weight: bold;
  flex: 0 0 auto;
}

.header-object-name {
  font-weight: 600;
  max-width: 72px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-object-chevron {
  color: var(--ink-soft);
  transition: transform 0.2s ease;
}

.header-object-pill.active .header-object-chevron {
  transform: rotate(180deg);
}

.header-object-menu {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  width: 190px;
  background: #fffdfa;
  border: 1px solid var(--border-strong);
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(56, 40, 30, 0.12);
  padding: 8px;
  z-index: 100;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.header-object-menu__title {
  margin: 4px 8px 6px;
  font-size: 11px;
  color: var(--ink-soft);
  font-weight: 600;
}

.header-object-menu__item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px;
  border-radius: 8px;
  background: none;
  border: 0;
  text-align: left;
  cursor: pointer;
  width: 100%;
  transition: background 0.15s ease;
}

.header-object-menu__item:hover {
  background: #f7ede3;
}

.header-object-menu__item.active {
  background: #faede6;
}

.header-object-menu__text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.header-object-menu__text strong {
  font-size: 13px;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-object-menu__text span {
  font-size: 11px;
  color: var(--ink-soft);
}

@media (max-width: 767px) {
  .header-object-wrap {
    margin-left: 0;
  }

  .header-object-pill {
    max-width: 112px;
  }
}

@media (max-width: 370px) {
  .header-brand {
    display: none;
  }

  .header-object-pill {
    max-width: 106px;
  }
}
</style>
