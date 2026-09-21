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
          @click.stop="objectMenuOpen = !objectMenuOpen"
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
          @keydown.down.prevent="openNavKey = item.key"
          @click.stop="goNav(item)"
        >
          <span class="nav-item__label">{{ item.label }}</span>
          <ChevronDown v-if="item.children?.length" class="nav-item__chevron" :size="14" stroke-width="2.4" />
        </button>

        <div v-if="item.children?.length && openNavKey === item.key" class="nav-menu">
          <button
            v-for="child in item.children"
            :key="child.to"
            type="button"
            class="nav-menu__item"
            @click.stop="openNavKey = ''; router.push(child.to)"
          >
            {{ child.label }}
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
          placeholder="搜索页面或入口"
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

      <button class="btn btn-ghost btn-sm header-action--optional" type="button" @click="exitAccount">
        {{ userStore.isDemoMode ? '退出样例' : '退出登录' }}
      </button>
      <button class="btn btn-secondary btn-sm header-write-action" type="button" @click="router.push('/checkin')">写今天</button>
      <button v-if="userStore.notifications.length" class="header-bell" type="button" @click="showNotif = !showNotif">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M18 15V11a6 6 0 1 0-12 0v4l-2 2h16z" />
          <path d="M10 19a2 2 0 0 0 4 0" />
        </svg>
        <span v-if="userStore.unreadCount > 0" class="bell-badge">{{ userStore.unreadCount > 9 ? '9+' : userStore.unreadCount }}</span>
      </button>
    </div>
  </header>

  <Teleport to="body">
    <div v-if="showNotif" class="notif-overlay" @click.self="showNotif = false">
      <div class="notif-drawer">
        <div class="notif-drawer__head">
          <h3>消息</h3>
          <button class="btn btn-ghost btn-sm" @click="markRead">全部已读</button>
        </div>
        <div class="notif-drawer__body">
          <div v-if="!userStore.notifications.length" class="empty-state">暂无消息</div>
          <div v-else class="stack-list">
            <div v-for="n in userStore.notifications" :key="n.id" class="stack-item">
              <div class="stack-item__icon" style="background:var(--warm-100);color:var(--warm-600);">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path d="M18 15V11a6 6 0 1 0-12 0v4l-2 2h16z" />
                </svg>
              </div>
              <div class="stack-item__content">
                <strong>{{ n.content }}</strong>
                <div class="stack-item__meta">{{ formatDate(n.created_at) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { api } from '@/api'
import { ChevronDown } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const showNotif = ref(false)
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
watch(() => route.fullPath, () => { openNavKey.value = ''; objectMenuOpen.value = false })

const titleMap = {
  home: '首页',
  checkin: '记录',
  chat: '聊一聊',
  discover: '总览',
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
  'message-simulation': '预演',
  'repair-protocol': '缓和',
  methodology: '说明',
  'privacy-security': '隐私',
}

const navItems = [
  { key: 'home', label: '首页', to: '/', match: ['home'], accent: '#d76848', soft: 'rgba(215, 104, 72, 0.14)' },
  {
    key: 'record',
    label: '记录',
    to: '/checkin',
    match: ['checkin', 'chat', 'message-simulation', 'repair-protocol', 'challenges'],
    accent: '#c78a3f',
    soft: 'rgba(199, 138, 63, 0.16)',
    children: [
      { label: '今日记录', to: '/checkin' },
      { label: '聊一聊', to: '/chat' },
      { label: '发前看看', to: '/message-simulation' },
      { label: '今日安排', to: '/challenges' },
    ],
  },
  {
    key: 'overview',
    label: '总览',
    to: '/discover',
    match: ['discover', 'alignment', 'health-test', 'attachment-test', 'longdistance', 'community', 'courses', 'experts', 'membership'],
    accent: '#5f876f',
    soft: 'rgba(95, 135, 111, 0.16)',
    children: [
      { label: '全部功能', to: '/discover' },
      { label: '双视角', to: '/alignment' },
      { label: '关系体检', to: '/health-test' },
      { label: '异地关系', to: '/longdistance' },
    ],
  },
  {
    key: 'report',
    label: '简报',
    to: '/report',
    match: ['report', 'timeline', 'methodology'],
    accent: '#305d68',
    soft: 'rgba(48, 93, 104, 0.14)',
    children: [
      { label: '关系简报', to: '/report' },
      { label: '关系日历', to: '/timeline' },
      { label: '判断说明', to: '/methodology' },
    ],
  },
  {
    key: 'mine',
    label: '我的',
    to: '/profile',
    match: ['profile', 'pair', 'pair-waiting', 'relationship-spaces', 'relationship-space-detail', 'milestones', 'privacy-security'],
    accent: '#aa4d33',
    soft: 'rgba(170, 77, 51, 0.14)',
    children: [
      { label: '个人中心', to: '/profile' },
      { label: '关系管理', to: '/pair' },
      { label: '关系空间', to: '/relationship-spaces' },
      { label: '隐私安全', to: '/privacy-security' },
    ],
  },
]

const searchItems = [
  { label: '首页', title: '首页', to: '/', keywords: ['首页', '简报可以看了'] },
  { label: '记录', title: '今日记录', to: '/checkin', keywords: ['记录', '打卡', '写今天'] },
  { label: '聊一聊', title: '像聊天一样整理今天', to: '/chat', keywords: ['聊天', '聊一聊', '整理今天'] },
  { label: '总览', title: '全部功能', to: '/discover', keywords: ['总览', '发现', '目录'] },
  { label: '简报', title: '关系简报', to: '/report', keywords: ['简报', '报告'] },
  { label: '双视角', title: '双视角', to: '/alignment', keywords: ['双视角', '对齐'] },
  { label: '预演', title: '发前看看', to: '/message-simulation', keywords: ['预演', '消息', '发前看看'] },
  { label: '缓和', title: '缓和建议', to: '/repair-protocol', keywords: ['缓和', '修复', '建议'] },
  { label: '关系日历', title: '关系日历', to: '/timeline', keywords: ['关系日历', '日历', '历史'] },
  { label: '我的', title: '个人中心', to: '/profile', keywords: ['我的', '头像', '手机号'] },
  { label: '关系', title: '关系管理', to: '/pair', keywords: ['关系', '邀请', '切换'] },
]

const currentSectionLabel = computed(() => titleMap[route.name] || '首页')
const filteredSearchItems = computed(() => {
  const keyword = searchQuery.value.trim().toLowerCase()
  if (!keyword) return searchItems.slice(0, 5)
  return searchItems
    .filter((item) => [item.label, item.title, ...item.keywords].some((value) => String(value).toLowerCase().includes(keyword)))
    .slice(0, 6)
})

function isNavActive(item) {
  return item.match.includes(String(route.name || ''))
}

function goNav(item) {
  clearTimeout(navCloseTimer)
  if (item.children?.length) {
    openNavKey.value = item.key
    return
  }
  openNavKey.value = ''
  router.push(item.to)
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
  if (!v) return ''
  const d = new Date(v)
  return `${d.getMonth() + 1}-${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function markRead() {
  try { await api.markNotificationsRead() } catch {}
  userStore.notifications.forEach((n) => { n.is_read = true })
}

import { listDemoPersonas } from '@/demo/fixtures'

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
  return (userStore.pairs || []).filter(p => p.status === 'active').map(pair => ({
    id: pair.id,
    name: pair.partner_name || pair.name || '伙伴',
    roleLabel: pair.type === 'couple' ? '伴侣' : pair.type === 'friend' ? '朋友' : '伙伴',
    avatar: (pair.partner_name || '伴')[0],
    themeColor: '#b86248',
  }))
})

const currentHeaderObject = computed(() => {
  return headerObjects.value.find(o => String(o.id) === String(userStore.activePairId)) || headerObjects.value[0] || null
})

async function switchHeaderObject(targetId) {
  objectMenuOpen.value = false
  if (String(targetId) === String(userStore.activePairId)) return
  await userStore.switchPair(targetId)
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
  grid-template-columns: minmax(230px, 294px) minmax(500px, 650px) minmax(300px, 1fr);
  align-items: center;
  gap: 14px;
  height: var(--header-height);
  padding: 0 max(18px, calc((100vw - var(--content-max)) / 2));
  border-bottom: 1px solid rgba(44, 48, 39, 0.14);
  background:
    linear-gradient(90deg, rgba(215, 104, 72, 0.1), transparent 28%, rgba(95, 135, 111, 0.08)),
    rgba(255, 252, 248, 0.92);
  backdrop-filter: blur(18px);
  box-shadow: 0 10px 24px rgba(56, 40, 30, 0.05);
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
  gap: 10px;
}

.header-back {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  background: rgba(255, 253, 250, 0.72);
  color: var(--seal-deep);
}

.header-brand-block {
  min-width: 0;
  gap: 10px;
}

.header-logo-wrap {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border: 1px solid rgba(189, 75, 53, 0.32);
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
}

.header-page-pill {
  max-width: 72px;
  padding: 3px 8px;
  overflow: hidden;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  background: rgba(255, 253, 250, 0.76);
  color: var(--ink-soft);
  font-size: 12px;
  font-weight: 800;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-nav {
  height: 48px;
  justify-content: center;
  gap: 8px;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.nav-item-wrap {
  position: relative;
}

.nav-item {
  min-width: 72px;
  height: 38px;
  justify-content: center;
  gap: 5px;
  padding: 0 12px;
  border: 1px solid transparent;
  border-radius: 14px;
  background: transparent;
  color: var(--ink-soft);
  font-size: 14px;
  font-weight: 800;
  box-shadow: none;
  transition: transform 0.18s ease, background 0.18s ease, border-color 0.18s ease, color 0.18s ease, box-shadow 0.18s ease;
}

.nav-item::after {
  display: none;
}

.nav-item__label {
  white-space: nowrap;
}

.nav-item__chevron {
  flex: 0 0 auto;
  opacity: 0.66;
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.nav-item-wrap:hover .nav-item,
.nav-item-wrap.is-open .nav-item,
.nav-item.active {
  border-color: color-mix(in srgb, var(--nav-accent) 42%, transparent);
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--nav-accent) 17%, rgba(255, 253, 250, 0.94)), rgba(255, 253, 250, 0.9));
  color: var(--nav-accent);
  box-shadow: 0 9px 20px rgba(56, 40, 30, 0.08);
  transform: translateY(-1px);
}

.nav-item-wrap:hover .nav-item__chevron,
.nav-item-wrap.is-open .nav-item__chevron,
.nav-item.active .nav-item__chevron {
  opacity: 0.9;
  transform: translateY(1px);
}

.nav-menu {
  position: absolute;
  top: calc(100% + 8px);
  left: 50%;
  z-index: 20;
  min-width: 132px;
  display: grid;
  gap: 4px;
  padding: 8px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  background: rgba(255, 253, 250, 0.98);
  box-shadow: var(--shadow-md);
  transform: translateX(-50%);
}

.nav-menu::before {
  content: '';
  position: absolute;
  inset: -10px 0 auto;
  height: 10px;
}

.nav-menu__item {
  width: 100%;
  padding: 8px 10px;
  border-radius: var(--radius-md);
  color: var(--ink-soft);
  font-size: 13px;
  font-weight: 800;
  text-align: left;
}

.nav-menu__item:hover {
  background: var(--nav-soft);
  color: var(--nav-accent);
}

.header-right {
  justify-content: flex-end;
  gap: 8px;
  min-width: 0;
}

.header-search {
  position: relative;
  width: 180px;
}

.header-search__input {
  width: 100%;
  height: 38px;
  padding: 0 16px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-pill);
  background: rgba(255, 253, 250, 0.76);
  color: var(--ink);
  font-size: 13px;
}

.header-search__panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 30;
  width: 260px;
  display: grid;
  gap: 4px;
  padding: 8px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  background: rgba(255, 253, 250, 0.98);
  box-shadow: var(--shadow-md);
}

.header-search__item {
  display: grid;
  grid-template-columns: 52px 1fr;
  align-items: center;
  gap: 8px;
  padding: 9px 10px;
  border-radius: var(--radius-md);
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
  font-weight: 800;
}

.header-bell {
  position: relative;
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-lg);
  background: rgba(255, 253, 250, 0.56);
  color: var(--ink-soft);
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
  border-radius: var(--radius-sm);
  background: var(--danger);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
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

@media (max-width: 1080px) {
  .app-header {
    grid-template-columns: auto minmax(430px, 1fr) auto;
    gap: 10px;
    padding-inline: 16px;
  }

  .header-nav {
    gap: 5px;
  }

  .nav-item {
    min-width: 68px;
    padding-inline: 7px;
    font-size: 13px;
  }

  .header-action--optional {
    display: none;
  }

  .header-search {
    width: min(180px, 20vw);
  }
}

@media (max-width: 920px) {
  .app-header {
    grid-template-columns: auto minmax(360px, 1fr) auto;
  }

  .header-search {
    display: none;
  }

  .nav-item {
    min-width: 60px;
    gap: 5px;
    padding-inline: 6px;
  }
}

@media (max-width: 767px) {
  .app-header {
    display: flex;
    padding: 0 12px;
  }

  .header-page-pill,
  .header-nav,
  .header-action--optional,
  .header-write-action {
    display: none;
  }

  .header-left {
    flex: 0 0 auto;
    gap: 8px;
  }

  .header-brand-block {
    gap: 8px;
  }

  .header-right {
    flex: 1 1 auto;
    justify-content: flex-end;
    gap: 8px;
  }

  .header-search {
    display: block;
    flex: 1 1 auto;
    width: auto;
    min-width: 112px;
    max-width: 154px;
  }

  .header-search__input {
    height: 36px;
    padding-inline: 14px;
    font-size: 13px;
  }

  .header-search__panel {
    right: -44px;
    width: min(284px, calc(100vw - 24px));
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

  .header-search {
    min-width: 96px;
    max-width: 126px;
  }
}
.header-object-wrap {
  position: relative;
  min-width: 0;
  margin-left: 4px;
}
.header-object-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px 4px 5px;
  background: #fffdfa;
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  font-size: 13px;
  color: var(--ink);
  cursor: pointer;
  box-shadow: var(--shadow-xs);
  transition: all 0.15s ease;
  max-width: 124px;
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
  max-width: 80px;
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
  padding: 6px 10px;
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
    min-height: 34px;
  }

  .header-object-menu {
    right: 0;
    left: auto;
  }
}

@media (max-width: 520px) {
  .header-search {
    display: none;
  }

  .header-left {
    flex: 1 1 auto;
  }

  .header-object-wrap {
    margin-right: auto;
  }
}

@media (max-width: 370px) {
  .header-brand {
    display: none;
  }

  .header-object-pill {
    max-width: 106px;
  }

  .header-object-menu {
    right: auto;
    left: 0;
  }
}
</style>
