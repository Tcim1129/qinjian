import { createSSRApp } from 'vue'
import { createStore } from 'vuex'
import App from './App.vue'
import api from './utils/api.js'
import { loadCachedSession } from './utils/session.js'

const store = createStore({
  state() {
    return {
      userInfo: null,
      pairInfo: null,
      pairSummary: null,
      hasCheckedIn: false,
      todayCheckin: null,
      streak: 0,
      currentSessionId: '',
      agentMessages: []
    }
  },
  mutations: {
    SET_USER_INFO(state, payload) {
      state.userInfo = payload || null
    },
    SET_PAIR_SUMMARY(state, payload) {
      state.pairSummary = payload || null
      state.pairInfo = payload?.active_pair || null
    },
    SET_CHECKIN_STATUS(state, status) {
      state.hasCheckedIn = status
    },
    SET_TODAY_CHECKIN(state, payload) {
      state.todayCheckin = payload || null
    },
    SET_STREAK(state, payload) {
      state.streak = payload || 0
    },
    SET_AGENT_SESSION(state, payload) {
      state.currentSessionId = payload || ''
    },
    SET_AGENT_MESSAGES(state, payload) {
      state.agentMessages = Array.isArray(payload) ? payload : []
    },
    PUSH_AGENT_MESSAGE(state, payload) {
      state.agentMessages.push(payload)
    }
  },
  actions: {
    async syncUserAndPair({ commit }) {
      if (!api.isLoggedIn()) {
        commit('SET_USER_INFO', null)
        commit('SET_PAIR_SUMMARY', null)
        return null
      }
      const [me, summary] = await Promise.all([
        api.getMe(),
        api.getPairSummary(),
      ])
      commit('SET_USER_INFO', me)
      commit('SET_PAIR_SUMMARY', summary)
      return { me, summary }
    }
  }
})

export function createApp() {
  const app = createSSRApp(App)
  app.use(store)
  const cached = loadCachedSession()
  if (cached.userInfo) {
    store.commit('SET_USER_INFO', cached.userInfo)
  }
  if (cached.pairSummary) {
    store.commit('SET_PAIR_SUMMARY', cached.pairSummary)
  }
  return { app }
}
