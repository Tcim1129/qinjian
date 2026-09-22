<template>
  <view class="home-page">
    <!-- 体验样例模式提示条 -->
    <view v-if="userStore.isDemoMode" class="demo-banner">
      <view class="demo-banner-content">
        <text class="demo-badge">样例体验中</text>
        <text class="demo-text">已载入“陈一 & 林夏”真实互动数据</text>
      </view>
      <text class="demo-action" @click="goLogin">切换账号</text>
    </view>

    <!-- 未登录提示条 -->
    <view v-else-if="!userStore.isLoggedIn" class="guest-banner" @click="goLogin">
      <text class="guest-text">您当前为游客模式，点击登录或进入体验样例</text>
      <text class="guest-btn">去登录 →</text>
    </view>

    <!-- 顶部问候与日期 -->
    <view class="header-section">
      <view class="greeting-wrap">
        <text class="greeting-text">你好，{{ userDisplayName }}</text>
        <text class="greeting-sub">先看见，再靠近</text>
      </view>
      <view class="date-badge">
        <text class="date-text">{{ currentDate }}</text>
      </view>
    </view>

    <!-- 当前伴侣关系卡片 -->
    <view class="partner-card">
      <view class="partner-left">
        <view class="partner-avatar">
          <text class="avatar-text">{{ partnerInitial }}</text>
        </view>
        <view class="partner-info">
          <view class="partner-name-row">
            <text class="partner-name">{{ userStore.partnerName || '待绑定伴侣' }}</text>
            <text class="relationship-tag">{{ relationshipTag }}</text>
          </view>
          <text class="partner-subtext">{{ partnerStatusDesc }}</text>
        </view>
      </view>
      <view class="partner-right" @click="goPair">
        <text class="switch-link">空间 →</text>
      </view>
    </view>

    <!-- 关系概览指标卡片 (纸墨印红美学) -->
    <view class="summary-card">
      <view class="card-head">
        <text class="card-title">关系脉络感知</text>
        <text class="card-extra" @click="goReport">查看简报详情</text>
      </view>

      <view class="stats-grid">
        <view class="stat-box">
          <text class="stat-number stat-seal">{{ checkinStreak }}</text>
          <text class="stat-unit">天</text>
          <text class="stat-label">连续记录</text>
        </view>

        <view class="stat-divider"></view>

        <view class="stat-box">
          <text class="stat-number stat-moss">{{ healthScore }}</text>
          <text class="stat-unit">分</text>
          <text class="stat-label">关系健康分</text>
        </view>

        <view class="stat-divider"></view>

        <view class="stat-box">
          <text class="stat-number stat-ochre">{{ pairCount }}</text>
          <text class="stat-unit">个</text>
          <text class="stat-label">活跃连线</text>
        </view>
      </view>

      <!-- 今日共鸣与教练寄语 -->
      <view class="coach-preview">
        <text class="coach-quote-mark">“</text>
        <text class="coach-quote">{{ coachQuote }}</text>
      </view>
    </view>

    <!-- 核心快捷操作 -->
    <view class="actions-grid">
      <view class="action-card action-primary" @click="goCheckin">
        <view class="action-icon-wrap icon-seal">
          <text class="action-emoji">✍️</text>
        </view>
        <view class="action-info">
          <text class="action-title">今日记录</text>
          <text class="action-desc">沉淀感受与微小瞬间</text>
        </view>
      </view>

      <view class="action-card" @click="goReport">
        <view class="action-icon-wrap icon-moss">
          <text class="action-emoji">📊</text>
        </view>
        <view class="action-info">
          <text class="action-title">双人简报</text>
          <text class="action-desc">看清彼此节奏与关怀</text>
        </view>
      </view>

      <view class="action-card" @click="goTimeline">
        <view class="action-icon-wrap icon-ochre">
          <text class="action-emoji">⏳</text>
        </view>
        <view class="action-info">
          <text class="action-title">时间轴</text>
          <text class="action-desc">回忆与里程碑沉淀</text>
        </view>
      </view>

      <view class="action-card" @click="goPair">
        <view class="action-icon-wrap icon-sand">
          <text class="action-emoji">🌿</text>
        </view>
        <view class="action-info">
          <text class="action-title">关系空间</text>
          <text class="action-desc">配对绑定与私密设置</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { demoFixture } from '@/demo/fixtures'

const userStore = useUserStore()

const currentDate = ref('')
const pairCount = ref(1)
const checkinStreak = ref(7)
const healthScore = ref(86)
const coachQuote = ref('懂得给彼此留出20分钟放空期，是成熟亲密关系中最温柔的默契。')

const userDisplayName = computed(() => {
  return userStore.me?.nickname || (userStore.isDemoMode ? '陈一' : '亲友')
})

const partnerInitial = computed(() => {
  const name = userStore.partnerName || '林夏'
  return name.slice(0, 1)
})

const relationshipTag = computed(() => {
  const pair = userStore.activePair
  if (!pair) return '伴侣'
  if (pair.type === 'couple') return '伴侣'
  if (pair.type === 'friend') return '挚友'
  if (pair.type === 'family') return '家人'
  return '陪伴'
})

const partnerStatusDesc = computed(() => {
  if (userStore.isDemoMode) {
    return '今日双方已完成共鸣对齐，彼此理解度 88%'
  }
  return userStore.isLoggedIn ? '连线稳定运行中' : '请先登录以同步最新动态'
})

onMounted(() => {
  const now = new Date()
  const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  currentDate.value = `${now.getMonth() + 1}月${now.getDate()}日 ${days[now.getDay()]}`
  loadData()
})

async function loadData() {
  await userStore.bootstrap()
  if (userStore.isDemoMode) {
    pairCount.value = demoFixture.pairs?.length || 2
    checkinStreak.value = 14
    healthScore.value = 88
    coachQuote.value = '双方节奏有细微差异时，先把事实说明白，比先宣泄情绪更让人安心。'
  }
}

function goCheckin() {
  uni.switchTab({ url: '/pages/checkin/checkin' })
}

function goReport() {
  uni.switchTab({ url: '/pages/report/report' })
}

function goPair() {
  uni.navigateTo({ url: '/pages/pair/pair' })
}

function goTimeline() {
  uni.navigateTo({ url: '/pages/timeline/timeline' })
}

function goLogin() {
  uni.navigateTo({ url: '/pages/auth/login' })
}
</script>

<style scoped lang="scss">
@import '@/styles/tokens.scss';

.home-page {
  min-height: 100vh;
  padding: 30rpx 32rpx 60rpx;
  box-sizing: border-box;
}

.demo-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(215, 104, 72, 0.12);
  border: 1px solid rgba(215, 104, 72, 0.35);
  border-radius: 16rpx;
  padding: 16rpx 24rpx;
  margin-bottom: 24rpx;
}

.demo-banner-content {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.demo-badge {
  font-size: 20rpx;
  font-weight: 700;
  color: #fffdfa;
  background: $color-seal;
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
}

.demo-text {
  font-size: 24rpx;
  color: $color-seal-deep;
  font-weight: 600;
}

.demo-action {
  font-size: 24rpx;
  font-weight: 700;
  color: $color-seal-deep;
  text-decoration: underline;
}

.guest-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(240, 213, 184, 0.45);
  border: 1px solid rgba(68, 52, 40, 0.16);
  border-radius: 16rpx;
  padding: 18rpx 24rpx;
  margin-bottom: 24rpx;
}

.guest-text {
  font-size: 24rpx;
  color: $color-ink-soft;
}

.guest-btn {
  font-size: 24rpx;
  font-weight: 800;
  color: $color-seal-deep;
}

.header-section {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 30rpx;
}

.greeting-text {
  font-family: $font-serif;
  font-size: 44rpx;
  font-weight: 800;
  color: $color-ink;
  display: block;
}

.greeting-sub {
  font-size: 24rpx;
  color: $color-ink-soft;
  margin-top: 6rpx;
  display: block;
}

.date-badge {
  background: rgba(255, 253, 250, 0.85);
  border: 1px solid $color-paper-line;
  padding: 8rpx 20rpx;
  border-radius: 30rpx;
  box-shadow: $shadow-sm;
}

.date-text {
  font-size: 24rpx;
  color: $color-ink-soft;
  font-weight: 600;
}

.partner-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: $color-paper-strong;
  border: 1px solid $color-paper-line-strong;
  border-radius: $radius-lg;
  padding: 26rpx 28rpx;
  margin-bottom: 28rpx;
  box-shadow: $shadow-sm;
}

.partner-left {
  display: flex;
  align-items: center;
  gap: 20rpx;
}

.partner-avatar {
  width: 84rpx;
  height: 84rpx;
  border-radius: 50%;
  background: $color-seal-soft;
  border: 2rpx solid rgba(215, 104, 72, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-text {
  font-family: $font-serif;
  font-size: 38rpx;
  font-weight: 800;
  color: $color-seal-deep;
}

.partner-name-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.partner-name {
  font-size: 32rpx;
  font-weight: 800;
  color: $color-ink;
}

.relationship-tag {
  font-size: 20rpx;
  color: $color-moss-deep;
  background: $color-moss-soft;
  padding: 2rpx 12rpx;
  border-radius: 8rpx;
  font-weight: 700;
}

.partner-subtext {
  font-size: 22rpx;
  color: $color-ink-faint;
  margin-top: 6rpx;
  display: block;
}

.switch-link {
  font-size: 26rpx;
  font-weight: 700;
  color: $color-seal-deep;
}

.summary-card {
  background: $color-paper-strong;
  border: 1px solid $color-paper-line-strong;
  border-radius: $radius-lg;
  padding: 32rpx;
  margin-bottom: 30rpx;
  box-shadow: $shadow-md;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 28rpx;
}

.card-title {
  font-family: $font-serif;
  font-size: 30rpx;
  font-weight: 800;
  color: $color-ink;
}

.card-extra {
  font-size: 24rpx;
  font-weight: 600;
  color: $color-seal-deep;
}

.stats-grid {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 16rpx 0 28rpx;
}

.stat-box {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-number {
  font-family: $font-serif;
  font-size: 52rpx;
  font-weight: 800;
  line-height: 1;
}

.stat-unit {
  font-size: 22rpx;
  color: $color-ink-soft;
  margin-top: 4rpx;
}

.stat-seal {
  color: $color-seal;
}

.stat-moss {
  color: $color-moss;
}

.stat-ochre {
  color: $color-ochre;
}

.stat-label {
  font-size: 24rpx;
  color: $color-ink-soft;
  margin-top: 8rpx;
  font-weight: 600;
}

.stat-divider {
  width: 1px;
  height: 60rpx;
  background: rgba(68, 52, 40, 0.12);
}

.coach-preview {
  background: rgba(246, 240, 234, 0.6);
  border-radius: 14rpx;
  padding: 18rpx 22rpx;
  display: flex;
  gap: 10rpx;
  align-items: flex-start;
}

.coach-quote-mark {
  font-family: $font-serif;
  font-size: 32rpx;
  font-weight: 800;
  color: $color-seal;
  line-height: 1;
}

.coach-quote {
  flex: 1;
  font-size: 24rpx;
  line-height: 1.5;
  color: $color-ink-soft;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20rpx;
}

.action-card {
  display: flex;
  align-items: center;
  gap: 18rpx;
  background: $color-paper-strong;
  border: 1px solid $color-paper-line;
  border-radius: $radius-md;
  padding: 24rpx 20rpx;
  box-shadow: $shadow-sm;

  &:active {
    background: rgba(244, 221, 212, 0.5);
    transform: scale(0.99);
  }
}

.action-icon-wrap {
  width: 68rpx;
  height: 68rpx;
  border-radius: 16rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-emoji {
  font-size: 32rpx;
}

.icon-seal {
  background: rgba(215, 104, 72, 0.15);
}

.icon-moss {
  background: rgba(95, 135, 111, 0.15);
}

.icon-ochre {
  background: rgba(199, 138, 63, 0.15);
}

.icon-sand {
  background: rgba(240, 213, 184, 0.4);
}

.action-title {
  font-size: 28rpx;
  font-weight: 700;
  color: $color-ink;
  display: block;
}

.action-desc {
  font-size: 20rpx;
  color: $color-ink-faint;
  margin-top: 4rpx;
  display: block;
}
</style>
