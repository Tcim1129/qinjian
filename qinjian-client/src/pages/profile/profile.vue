<template>
  <view class="container">
    <view class="user-card">
      <view class="avatar">
        <text class="avatar-text">{{ avatarText }}</text>
      </view>
      <text class="nickname">{{ nickname || '未登录' }}</text>
      <text class="email">{{ email }}</text>
    </view>

    <view class="menu">
      <view class="menu-item" @click="goPair">
        <text class="menu-label">关系管理</text>
        <text class="menu-arrow">&gt;</text>
      </view>
      <view class="menu-item" @click="goTimeline">
        <text class="menu-label">时间轴</text>
        <text class="menu-arrow">&gt;</text>
      </view>
    </view>

    <button class="logout-btn" @click="handleLogout">退出登录</button>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { get } from '../../utils/request'

const nickname = ref('')
const email = ref('')

const avatarText = computed(() => (nickname.value ? nickname.value.charAt(0) : '亲'))

onMounted(async () => {
  try {
    const data = await get('/api/v1/auth/me')
    nickname.value = data.nickname || ''
    email.value = data.email || ''
  } catch (error) {
    nickname.value = ''
    email.value = ''
  }
})

const goPair = () => {
  uni.navigateTo({ url: '/pages/pair/pair' })
}

const goTimeline = () => {
  uni.navigateTo({ url: '/pages/timeline/timeline' })
}

const handleLogout = () => {
  uni.removeStorageSync('token')
  uni.reLaunch({ url: '/pages/auth/login' })
}
</script>

<style scoped>
.container {
  min-height: 100vh;
  background: #f5f5f5;
  padding: 20rpx;
}

.user-card {
  background: #fff;
  border-radius: 20rpx;
  padding: 60rpx 30rpx;
  text-align: center;
  margin-bottom: 20rpx;
}

.avatar {
  width: 140rpx;
  height: 140rpx;
  margin: 0 auto 30rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-text {
  font-size: 56rpx;
  color: #fff;
  font-weight: bold;
}

.nickname {
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
  display: block;
  margin-bottom: 10rpx;
}

.email {
  font-size: 24rpx;
  color: #999;
}

.menu {
  background: #fff;
  border-radius: 20rpx;
  margin-bottom: 40rpx;
}

.menu-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 35rpx 30rpx;
  border-bottom: 1px solid #f0f0f0;
}

.menu-item:last-child {
  border-bottom: none;
}

.menu-label {
  font-size: 28rpx;
  color: #333;
}

.menu-arrow {
  font-size: 28rpx;
  color: #ccc;
}

.logout-btn {
  background: #fff;
  color: #ff4444;
  border-radius: 20rpx;
  font-size: 28rpx;
}
</style>
