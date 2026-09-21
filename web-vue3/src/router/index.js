import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

function requireAuth(to, from, next) {
  const token = sessionStorage.getItem('qj_token')
  if (!token) return next('/auth')
  next()
}

const routes = [
  {
    path: '/privacy-security',
    name: 'privacy-security',
    component: () => import('@/views/profile/PrivacySecurityPage.vue'),
    meta: { title: '隐私与安全' },
    beforeEnter: requireAuth,
  },
  {
    path: '/relationship-spaces/:pairId',
    name: 'relationship-space-detail',
    component: () => import('@/views/relationship/RelationshipSpacesPage.vue'),
    meta: { title: '关系空间' },
    beforeEnter: requireAuth,
  },
  {
    path: '/auth',
    name: 'auth',
    component: () => import('@/views/auth/LoginPage.vue'),
    meta: { title: '登录', guest: true },
  },
  {
    path: '/pair',
    name: 'pair',
    component: () => import('@/views/pair/PairPage.vue'),
    meta: { title: '建立关系' },
    beforeEnter: requireAuth,
  },
  {
    path: '/pair-waiting',
    name: 'pair-waiting',
    component: () => import('@/views/pair/PairWaitingPage.vue'),
    meta: { title: '等待加入' },
    beforeEnter: requireAuth,
  },
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/home/HomePage.vue'),
    meta: { title: '关系档案馆' },
    beforeEnter: requireAuth,
  },
  {
    path: '/checkin',
    name: 'checkin',
    component: () => import('@/views/checkin/CheckinPage.vue'),
    meta: { title: '关系记录' },
    beforeEnter: requireAuth,
  },
  {
    path: '/discover',
    name: 'discover',
    component: () => import('@/views/discover/DiscoverPage.vue'),
    meta: { title: '目录' },
    beforeEnter: requireAuth,
  },
  {
    path: '/report',
    name: 'report',
    component: () => import('@/views/report/ReportPage.vue'),
    meta: { title: '关系简报' },
    beforeEnter: requireAuth,
  },
  {
    path: '/alignment',
    name: 'alignment',
    component: () => import('@/views/alignment/AlignmentPage.vue'),
    meta: { title: '双视角分析' },
    beforeEnter: requireAuth,
  },
  {
    path: '/message-simulation',
    name: 'message-simulation',
    component: () => import('@/views/coach/MessageSimulationPage.vue'),
    meta: { title: '聊天前预演' },
    beforeEnter: requireAuth,
  },
  {
    path: '/repair-protocol',
    name: 'repair-protocol',
    component: () => import('@/views/coach/RepairProtocolPage.vue'),
    meta: { title: '修复协议' },
    beforeEnter: requireAuth,
  },
  {
    path: '/methodology',
    name: 'methodology',
    component: () => import('@/views/coach/MethodologyPage.vue'),
    meta: { title: '判断说明' },
    beforeEnter: requireAuth,
  },
  {
    path: '/chat',
    name: 'chat',
    component: () => import('@/views/chat/ChatPage.vue'),
    meta: { title: '聊一聊' },
    beforeEnter: requireAuth,
  },
  {
    path: '/relationship-agent',
    name: 'relationship-agent',
    component: () => import('@/views/agent/RelationshipAgentPage.vue'),
    meta: { title: '关系协作智能体' },
    beforeEnter: requireAuth,
  },
  {
    path: '/relationship-spaces',
    name: 'relationship-spaces',
    component: () => import('@/views/relationship/RelationshipSpacesPage.vue'),
    meta: { title: '关系空间' },
    beforeEnter: requireAuth,
  },
  {
    path: '/timeline',
    name: 'timeline',
    component: () => import('@/views/report/TimelinePage.vue'),
    meta: { title: '关系日历' },
    beforeEnter: requireAuth,
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('@/views/profile/ProfilePage.vue'),
    meta: { title: '我的' },
    beforeEnter: requireAuth,
  },
  {
    path: '/milestones',
    name: 'milestones',
    component: () => import('@/views/milestones/MilestonesPage.vue'),
    meta: { title: '关系纪念日' },
    beforeEnter: requireAuth,
  },
  {
    path: '/longdistance',
    name: 'longdistance',
    component: () => import('@/views/longdistance/LongDistancePage.vue'),
    meta: { title: '异地关系' },
    beforeEnter: requireAuth,
  },
  {
    path: '/health-test',
    name: 'health-test',
    component: () => import('@/views/health/HealthTestPage.vue'),
    meta: { title: '关系体检' },
    beforeEnter: requireAuth,
  },
  {
    path: '/attachment-test',
    name: 'attachment-test',
    component: () => import('@/views/health/AttachmentPage.vue'),
    meta: { title: '依恋类型' },
    beforeEnter: requireAuth,
  },
  {
    path: '/community',
    name: 'community',
    component: () => import('@/views/community/CommunityPage.vue'),
    meta: { title: '关系技巧' },
    beforeEnter: requireAuth,
  },
  {
    path: '/challenges',
    name: 'challenges',
    component: () => import('@/views/challenges/ChallengesPage.vue'),
    meta: { title: '今日任务' },
    beforeEnter: requireAuth,
  },
  {
    path: '/courses',
    name: 'courses',
    component: () => import('@/views/courses/CoursesPage.vue'),
    meta: { title: '课程' },
    beforeEnter: requireAuth,
  },
  {
    path: '/experts',
    name: 'experts',
    component: () => import('@/views/experts/ExpertsPage.vue'),
    meta: { title: '咨询' },
    beforeEnter: requireAuth,
  },
  {
    path: '/membership',
    name: 'membership',
    component: () => import('@/views/membership/MembershipPage.vue'),
    meta: { title: '会员' },
    beforeEnter: requireAuth,
  },
]

export function warmCoreRouteComponents() {
  const coreRouteNames = new Set(['home', 'checkin', 'discover', 'report', 'timeline', 'profile'])
  for (const route of routes) {
    if (!coreRouteNames.has(route.name) || typeof route.component !== 'function') continue
    route.component().catch(() => null)
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, from, next) => {
  document.title = '亲健'
  const token = sessionStorage.getItem('qj_token')
  const userStore = useUserStore()
  if (to.meta.guest && token) {
    return next('/')
  }
  if (!to.meta.guest && !to.meta.public && token && !userStore.me) {
    const ok = await userStore.bootstrap()
    if (!ok) return next('/auth')
  }
  next()
})

export default router
