import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { get, post } from '@/utils/request'
import { DEMO_TOKEN, cloneDemo, demoFixture } from '@/demo/fixtures'

export const useUserStore = defineStore('user', () => {
  const token = ref(uni.getStorageSync('token') || '')
  const me = ref(null)
  const pairs = ref([])
  const currentPair = ref(null)

  const isLoggedIn = computed(() => Boolean(token.value))
  const isDemoMode = computed(() => token.value === DEMO_TOKEN)
  const activePair = computed(() => {
    if (currentPair.value?.status === 'active') return currentPair.value
    return pairs.value.find((p) => p.status === 'active') || null
  })
  const partnerName = computed(() => {
    const pair = activePair.value || currentPair.value
    if (!pair) return ''
    return pair.custom_partner_nickname || pair.partner_nickname || pair.partner_email || '对方'
  })

  // 体验样例模式 (Demo Mode)
  function enterDemo(targetPairId = null) {
    token.value = DEMO_TOKEN
    uni.setStorageSync('token', DEMO_TOKEN)
    me.value = cloneDemo(demoFixture.me)
    pairs.value = cloneDemo(demoFixture.pairs)
    const chosenId = targetPairId || demoFixture.currentPairId
    currentPair.value = pairs.value.find((p) => p.id === chosenId) || pairs.value[0] || null
    uni.setStorageSync('qj_current_pair', currentPair.value?.id || '')
  }

  // 退出登录 / 退出体验模式
  function logout() {
    token.value = ''
    me.value = null
    pairs.value = []
    currentPair.value = null
    uni.removeStorageSync('token')
    uni.removeStorageSync('qj_current_pair')
  }

  // 手机号验证码登录
  async function phoneLogin(phone, code) {
    const res = await post('/api/v1/auth/phone/login', { phone, code })
    token.value = res.access_token
    uni.setStorageSync('token', res.access_token)
    if (res.user) {
      me.value = res.user
    } else {
      await fetchMe()
    }
    return res
  }

  // 账号密码登录
  async function login(account, password) {
    const res = await post('/api/v1/auth/login', { account, password })
    token.value = res.access_token
    uni.setStorageSync('token', res.access_token)
    if (res.user) {
      me.value = res.user
    } else {
      await fetchMe()
    }
    return res
  }

  // 账号注册
  async function register(account, nickname, password) {
    const res = await post('/api/v1/auth/register', { account, nickname, password })
    token.value = res.access_token
    uni.setStorageSync('token', res.access_token)
    if (res.user) {
      me.value = res.user
    } else {
      await fetchMe()
    }
    return res
  }

  // 获取当前用户信息
  async function fetchMe() {
    if (isDemoMode.value) {
      me.value = cloneDemo(demoFixture.me)
      return me.value
    }
    if (!token.value) return null
    try {
      const res = await get('/api/v1/auth/me')
      me.value = res
      return res
    } catch (err) {
      return null
    }
  }

  // 初始化加载
  async function bootstrap() {
    if (isDemoMode.value) {
      enterDemo()
      return
    }
    if (token.value) {
      await fetchMe()
    }
  }

  return {
    token,
    me,
    pairs,
    currentPair,
    isLoggedIn,
    isDemoMode,
    activePair,
    partnerName,
    enterDemo,
    logout,
    phoneLogin,
    login,
    register,
    fetchMe,
    bootstrap
  }
})
