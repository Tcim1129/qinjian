<template>
  <view class="profile-page">
    <!-- 用户个人信息卡片 -->
    <view class="user-hero-card">
      <view class="avatar-ring">
        <text class="avatar-text">{{ avatarInitial }}</text>
      </view>

      <view class="user-meta">
        <view class="name-badge-row">
          <text class="user-nickname">{{ displayName }}</text>
          <text v-if="userStore.isDemoMode" class="demo-badge">样例体验中</text>
          <text v-else-if="userStore.isLoggedIn" class="status-badge">已认证</text>
        </view>
        <text class="user-sub">{{ displayAccount }}</text>
      </view>
    </view>

    <!-- 伴侣与空间信息简卡 -->
    <view class="partner-card" @click="goPair">
      <view class="partner-left">
        <text class="partner-icon">🌿</text>
        <view class="partner-texts">
          <text class="partner-title">当前主空间：{{ userStore.partnerName || '待绑定' }}</text>
          <text class="partner-desc">点击切换伴侣或查看邀请码</text>
        </view>
      </view>
      <text class="card-arrow">→</text>
    </view>

    <!-- 功能菜单列表 -->
    <view class="menu-card">
      <view class="menu-item" @click="goCheckin">
        <view class="item-left">
          <text class="item-emoji">✍️</text>
          <text class="item-label">今日情感记录</text>
        </view>
        <text class="item-arrow">→</text>
      </view>

      <view class="menu-item" @click="goReport">
        <view class="item-left">
          <text class="item-emoji">📊</text>
          <text class="item-label">双人共鸣简报</text>
        </view>
        <text class="item-arrow">→</text>
      </view>

      <view class="menu-item" @click="goTimeline">
        <view class="item-left">
          <text class="item-emoji">⏳</text>
          <text class="item-label">时光回忆轨迹</text>
        </view>
        <text class="item-arrow">→</text>
      </view>

      <view class="menu-item" @click="goPair">
        <view class="item-left">
          <text class="item-emoji">💌</text>
          <text class="item-label">关系配对与邀请码</text>
        </view>
        <text class="item-arrow">→</text>
      </view>
    </view>

    <!-- 操作按钮：退出或去登录 -->
    <view class="action-footer">
      <button
        v-if="userStore.isDemoMode"
        class="exit-demo-btn"
        @click="handleExitDemo"
      >
        退出体验样例，登录真实账号
      </button>

      <button
        v-else-if="userStore.isLoggedIn"
        class="logout-btn"
        @click="handleLogout"
      >
        退出登录
      </button>

      <button
        v-else
        class="login-btn"
        @click="goLogin"
      >
        立即登录 / 体验样例
      </button>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

onMounted(async () => {
  await userStore.bootstrap()
})

const displayName = computed(() => {
  if (userStore.isDemoMode) return '陈一 (体验)'
  return userStore.me?.nickname || (userStore.isLoggedIn ? '亲健朋友' : '未登录访客')
})

const displayAccount = computed(() => {
  if (userStore.isDemoMode) return '伴侣连线：林夏 · 体验账号'
  return userStore.me?.phone || userStore.me?.email || (userStore.isLoggedIn ? '已登录' : '点击去登录解锁完整功能')
})

const avatarInitial = computed(() => {
  if (userStore.isDemoMode) return '陈'
  const name = userStore.me?.nickname || '亲'
  return name.charAt(0)
})

function goPair() {
  uni.navigateTo({ url: '/pages/pair/pair' })
}

function goTimeline() {
  uni.navigateTo({ url: '/pages/timeline/timeline' })
}

function goCheckin() {
  uni.switchTab({ url: '/pages/checkin/checkin' })
}

function goReport() {
  uni.switchTab({ url: '/pages/report/report' })
}

function goLogin() {
  uni.navigateTo({ url: '/pages/auth/login' })
}

function handleExitDemo() {
  userStore.logout()
  uni.showToast({ title: '已退出体验模式', icon: 'none' })
  setTimeout(() => {
    uni.reLaunch({ url: '/pages/auth/login' })
  }, 400)
}

function handleLogout() {
  userStore.logout()
  uni.showToast({ title: '已安全退出', icon: 'none' })
  setTimeout(() => {
    uni.reLaunch({ url: '/pages/auth/login' })
  }, 400)
}
</script>

<style scoped lang="scss">
@import '@/styles/tokens.scss';

.profile-page {
  min-height: 100vh;
  padding: 30rpx 32rpx 60rpx;
  box-sizing: border-box;
}

.user-hero-card {
  background: $color-paper-strong;
  border: 1px solid $color-paper-line-strong;
  border-radius: $radius-lg;
  padding: 40rpx 32rpx;
  display: flex;
  align-items: center;
  gap: 28rpx;
  margin-bottom: 24rpx;
  box-shadow: $shadow-sm;
}

.avatar-ring {
  width: 120rpx;
  height: 120rpx;
  border-radius: 50%;
  background: $color-seal-soft;
  border: 2rpx solid rgba(215, 104, 72, 0.36);
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-text {
  font-family: $font-serif;
  font-size: 52rpx;
  font-weight: 800;
  color: $color-seal-deep;
}

.user-meta {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.name-badge-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.user-nickname {
  font-family: $font-serif;
  font-size: 38rpx;
  font-weight: 800;
  color: $color-ink;
}

.demo-badge {
  font-size: 18rpx;
  font-weight: 700;
  color: #fffdfa;
  background: $color-seal;
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
}

.status-badge {
  font-size: 18rpx;
  font-weight: 700;
  color: $color-moss-deep;
  background: $color-moss-soft;
  padding: 4rpx 12rpx;
  border-radius: 8rpx;
}

.user-sub {
  font-size: 24rpx;
  color: $color-ink-faint;
  margin-top: 8rpx;
}

.partner-card {
  background: $color-paper-strong;
  border: 1px solid $color-paper-line;
  border-radius: $radius-md;
  padding: 24rpx 28rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 28rpx;
  box-shadow: $shadow-sm;

  &:active {
    background: rgba(244, 221, 212, 0.4);
  }
}

.partner-left {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.partner-icon {
  font-size: 36rpx;
}

.partner-texts {
  display: flex;
  flex-direction: column;
}

.partner-title {
  font-size: 26rpx;
  font-weight: 700;
  color: $color-ink;
}

.partner-desc {
  font-size: 20rpx;
  color: $color-ink-faint;
  margin-top: 4rpx;
}

.card-arrow {
  font-size: 28rpx;
  color: $color-seal-deep;
  font-weight: 700;
}

.menu-card {
  background: $color-paper-strong;
  border: 1px solid $color-paper-line-strong;
  border-radius: $radius-lg;
  padding: 10rpx 28rpx;
  margin-bottom: 40rpx;
  box-shadow: $shadow-sm;
}

.menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 30rpx 0;
  border-bottom: 1px solid rgba(68, 52, 40, 0.08);

  &:last-child {
    border-bottom: none;
  }

  &:active {
    opacity: 0.7;
  }
}

.item-left {
  display: flex;
  align-items: center;
  gap: 18rpx;
}

.item-emoji {
  font-size: 32rpx;
}

.item-label {
  font-size: 28rpx;
  font-weight: 600;
  color: $color-ink;
}

.item-arrow {
  font-size: 26rpx;
  color: $color-ink-faint;
}

.action-footer {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.exit-demo-btn {
  width: 100%;
  height: 84rpx;
  line-height: 84rpx;
  border-radius: 14rpx;
  background: rgba(215, 104, 72, 0.12);
  border: 1px solid rgba(215, 104, 72, 0.4);
  color: $color-seal-deep;
  font-size: 26rpx;
  font-weight: 700;
}

.logout-btn {
  width: 100%;
  height: 84rpx;
  line-height: 84rpx;
  border-radius: 14rpx;
  background: rgba(68, 52, 40, 0.08);
  color: $color-ink-soft;
  font-size: 26rpx;
  font-weight: 700;
  border: none;
}

.login-btn {
  width: 100%;
  height: 84rpx;
  line-height: 84rpx;
  border-radius: 14rpx;
  background: $color-seal;
  color: #fffdfa;
  font-size: 28rpx;
  font-weight: 800;
  border: none;
}
</style>
