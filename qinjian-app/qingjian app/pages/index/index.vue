<template>
  <view class="home-page">
    <view class="hero-panel">
      <view class="hero-copy">
        <text class="eyebrow">QINJIAN APP</text>
        <text class="hero-title">{{ greeting }}</text>
        <text class="hero-subtitle">{{ pairSubtitle }}</text>
      </view>
      <view class="hero-pill">
        <text class="hero-pill-emoji">{{ hasCheckedIn ? '✓' : '○' }}</text>
        <text class="hero-pill-label">{{ hasCheckedIn ? '今日已记录' : '等待打卡' }}</text>
      </view>
    </view>

    <scroll-view class="content-scroll" scroll-y>
      <view class="floating-score-card">
        <view>
          <text class="score-caption">连续打卡</text>
          <text class="score-value">{{ streak }}</text>
          <text class="score-tail">天</text>
        </view>
        <view class="score-side">
          <text class="score-side-label">当前关系</text>
          <text class="score-side-value">{{ pairDisplayName }}</text>
        </view>
      </view>

      <view class="module-card insight-card">
        <view class="module-header">
          <text class="module-title">今日关系脉搏</text>
          <text class="module-badge">{{ treeLabel }}</text>
        </view>
        <text class="module-copy">{{ insightText }}</text>
        <view class="pulse-grid">
          <view class="pulse-item">
            <text class="pulse-name">心情</text>
            <text class="pulse-value">{{ moodLabel }}</text>
          </view>
          <view class="pulse-item">
            <text class="pulse-name">互动</text>
            <text class="pulse-value">{{ interactionLabel }}</text>
          </view>
          <view class="pulse-item">
            <text class="pulse-name">深聊</text>
            <text class="pulse-value">{{ deepTalkLabel }}</text>
          </view>
        </view>
      </view>

      <view class="module-card quick-card">
        <view class="module-header">
          <text class="module-title">今天想从哪开始</text>
          <text class="module-link" @click="goProfile">去我的</text>
        </view>
        <view class="action-grid">
          <view class="action-item action-item-primary" @click="goCheckin">
            <text class="action-icon">✦</text>
            <text class="action-name">表单打卡</text>
            <text class="action-desc">四步快速记录</text>
          </view>
          <view class="action-item" @click="goCheckin('voice')">
            <text class="action-icon">◉</text>
            <text class="action-name">语音陪伴</text>
            <text class="action-desc">像豆包那样聊着完成</text>
          </view>
          <view class="action-item" @click="goReport">
            <text class="action-icon">▥</text>
            <text class="action-name">关系报告</text>
            <text class="action-desc">看趋势和建议</text>
          </view>
          <view class="action-item" @click="goDiscover">
            <text class="action-icon">◎</text>
            <text class="action-name">发现空间</text>
            <text class="action-desc">课程、测试、玩法</text>
          </view>
        </view>
      </view>

      <view class="module-card relation-card">
        <view class="module-header">
          <text class="module-title">关系状态</text>
          <text class="module-badge soft">{{ pairStatusLabel }}</text>
        </view>
        <view class="status-row">
          <view class="status-box">
            <text class="status-label">对象</text>
            <text class="status-value">{{ pairDisplayName }}</text>
          </view>
          <view class="status-box">
            <text class="status-label">成长树</text>
            <text class="status-value">{{ treeLabel }}</text>
          </view>
        </view>
        <view class="status-row">
          <view class="status-box">
            <text class="status-label">今日状态</text>
            <text class="status-value">{{ hasCheckedIn ? '已打卡' : '待打卡' }}</text>
          </view>
          <view class="status-box">
            <text class="status-label">模式</text>
            <text class="status-value">{{ pairInfo ? '双人关系' : '单人模式' }}</text>
          </view>
        </view>
      </view>

      <view class="page-spacer"></view>
    </scroll-view>

    <FloatingTabBar current="/pages/index/index" />
  </view>
</template>

<script>
import { mapState } from 'vuex'
import api from '../../utils/api.js'
import { loadCachedSession, syncSession } from '../../utils/session.js'
import FloatingTabBar from '../../components/FloatingTabBar.vue'

export default {
  components: { FloatingTabBar },
  data() {
    return {
      greeting: '今天也适合把关系照顾好',
      treeStatus: null,
    }
  },
  computed: {
    ...mapState(['userInfo', 'pairInfo', 'todayCheckin', 'hasCheckedIn', 'streak']),
    pairDisplayName() {
      return this.pairInfo?.partner_nickname || this.pairInfo?.partner_name || '还没绑定'
    },
    pairSubtitle() {
      if (this.pairInfo) {
        return `已绑定 · 和 ${this.pairDisplayName} 的关系空间正在生长`
      }
      return '未绑定也能先记录自己，把情绪和关系慢慢理顺'
    },
    pairStatusLabel() {
      return this.pairInfo ? '已绑定' : '未绑定'
    },
    treeLabel() {
      return this.treeStatus?.level_name || '关系萌芽'
    },
    moodLabel() {
      const score = this.todayCheckin?.mood_score
      return score ? `${score}/4` : '未记录'
    },
    interactionLabel() {
      const count = this.todayCheckin?.interaction_freq
      return count || count === 0 ? `${count} 次` : '待记录'
    },
    deepTalkLabel() {
      if (this.todayCheckin?.deep_conversation === true) return '有'
      if (this.todayCheckin?.deep_conversation === false) return '无'
      return '待记录'
    },
    insightText() {
      if (!this.todayCheckin) {
        return '今天先留一句话也可以。记录得越真实，后面的 AI 洞察和报告越有价值。'
      }
      if (this.todayCheckin.deep_conversation) {
        return '你们今天已经出现了有效连接，适合趁热把感受写清楚，让报告更准确。'
      }
      return '今天的记录还偏轻，试着补一句真实感受，AI 会更容易读懂你们的节奏。'
    }
  },
  onShow() {
    this.bootstrap()
  },
  methods: {
    async bootstrap() {
      const cached = loadCachedSession()
      if (cached.userInfo) {
        this.$store.commit('SET_USER_INFO', cached.userInfo)
      }
      if (cached.pairSummary) {
        this.$store.commit('SET_PAIR_SUMMARY', cached.pairSummary)
      }

      if (api.isLoggedIn()) {
        try {
          await syncSession(this.$store)
        } catch (e) {
          console.warn('sync session failed', e)
        }
      } else {
        uni.reLaunch({ url: '/pages/auth/index' })
        return
      }

      const name = this.$store.state.userInfo?.nickname || '亲爱的'
      this.greeting = `${this.getGreeting()}，${name}`
      await this.loadStatus()
    },
    getGreeting() {
      const hour = new Date().getHours()
      if (hour < 11) return '早上好'
      if (hour < 18) return '下午好'
      return '晚上好'
    },
    async loadStatus() {
      if (!api.isLoggedIn()) return
      const pairId = this.$store.state.pairInfo?.id || null
      try {
        const [todayStatus, streak, tree] = await Promise.all([
          api.getTodayStatus(pairId),
          api.getCheckinStreak(pairId),
          pairId ? api.getTreeStatus(pairId) : Promise.resolve(null),
        ])
        this.$store.commit('SET_CHECKIN_STATUS', !!todayStatus?.my_done)
        this.$store.commit('SET_TODAY_CHECKIN', todayStatus?.my_checkin || null)
        this.$store.commit('SET_STREAK', streak?.streak || 0)
        this.treeStatus = tree
      } catch (e) {
        console.warn('load status failed', e)
      }
    },
    goCheckin(mode = 'form') {
      uni.setStorageSync('qj_checkin_mode', mode)
      uni.reLaunch({ url: '/pages/checkin/index' })
    },
    goDiscover() {
      uni.reLaunch({ url: '/pages/discover/index' })
    },
    goReport() {
      uni.reLaunch({ url: '/pages/report/index' })
    },
    goProfile() {
      uni.reLaunch({ url: '/pages/profile/index' })
    }
  }
}
</script>

<style scoped>
.home-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #fff8f2 0%, #f7efe8 100%);
}

.hero-panel {
  padding: 88rpx 32rpx 132rpx;
  background: linear-gradient(135deg, #3f2b26 0%, #6d4c41 48%, #d4a373 100%);
  border-radius: 0 0 48rpx 48rpx;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20rpx;
}

.eyebrow {
  font-size: 20rpx;
  letter-spacing: 4rpx;
  text-transform: uppercase;
  color: rgba(255,255,255,0.72);
}

.hero-title {
  display: block;
  margin-top: 18rpx;
  font-size: 56rpx;
  line-height: 1.18;
  font-weight: 800;
  color: #fff;
}

.hero-subtitle {
  display: block;
  margin-top: 18rpx;
  font-size: 24rpx;
  line-height: 1.7;
  color: rgba(255,255,255,0.78);
}

.hero-pill {
  margin-top: 8rpx;
  padding: 16rpx 22rpx;
  border-radius: 999rpx;
  background: rgba(255,255,255,0.14);
  border: 1rpx solid rgba(255,255,255,0.16);
  display: flex;
  align-items: center;
  gap: 10rpx;
}

.hero-pill-emoji,
.hero-pill-label {
  color: #fff;
  font-size: 22rpx;
  font-weight: 700;
}

.content-scroll {
  margin-top: -72rpx;
  height: calc(100vh - 160rpx);
  padding: 0 28rpx;
  box-sizing: border-box;
}

.floating-score-card,
.module-card {
  background: rgba(255,255,255,0.95);
  border-radius: 36rpx;
  box-shadow: 0 18rpx 36rpx rgba(62, 39, 35, 0.08);
  border: 1rpx solid rgba(212, 163, 115, 0.12);
}

.floating-score-card {
  padding: 32rpx;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
}

.score-caption,
.score-tail,
.score-side-label {
  font-size: 22rpx;
  color: #a1887f;
}

.score-value {
  font-size: 88rpx;
  line-height: 1;
  font-weight: 900;
  color: #5d4037;
  margin-right: 10rpx;
}

.score-side {
  text-align: right;
}

.score-side-value {
  display: block;
  margin-top: 12rpx;
  font-size: 28rpx;
  font-weight: 700;
  color: #3e2723;
}

.module-card {
  margin-top: 24rpx;
  padding: 30rpx;
}

.module-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16rpx;
}

.module-title {
  font-size: 30rpx;
  font-weight: 800;
  color: #2f2522;
}

.module-badge,
.module-link {
  padding: 8rpx 18rpx;
  border-radius: 999rpx;
  background: #f8efe6;
  color: #8d6e63;
  font-size: 20rpx;
  font-weight: 700;
}

.module-badge.soft {
  background: #ecf5ef;
  color: #50725a;
}

.module-copy {
  display: block;
  margin-top: 18rpx;
  font-size: 24rpx;
  line-height: 1.8;
  color: #6d4c41;
}

.pulse-grid,
.status-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16rpx;
  margin-top: 22rpx;
}

.status-row {
  grid-template-columns: repeat(2, 1fr);
}

.pulse-item,
.status-box {
  padding: 20rpx;
  border-radius: 24rpx;
  background: #fff7f1;
}

.pulse-name,
.status-label {
  font-size: 20rpx;
  color: #a1887f;
}

.pulse-value,
.status-value {
  display: block;
  margin-top: 12rpx;
  font-size: 26rpx;
  font-weight: 700;
  color: #3e2723;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 18rpx;
  margin-top: 22rpx;
}

.action-item {
  padding: 24rpx;
  border-radius: 28rpx;
  background: #fcf4ed;
}

.action-item-primary {
  background: linear-gradient(135deg, #5d4037, #8d6e63);
}

.action-icon {
  font-size: 36rpx;
  color: inherit;
}

.action-name {
  display: block;
  margin-top: 16rpx;
  font-size: 28rpx;
  font-weight: 800;
  color: #3e2723;
}

.action-desc {
  display: block;
  margin-top: 10rpx;
  font-size: 20rpx;
  color: #8d6e63;
}

.action-item-primary .action-icon,
.action-item-primary .action-name,
.action-item-primary .action-desc {
  color: #fff;
}

.page-spacer {
  height: 180rpx;
}
</style>
