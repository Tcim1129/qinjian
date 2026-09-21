<template>
  <view class="container">
    <view class="header">
      <text class="greeting">你好，{{ userName }}</text>
      <text class="date">{{ currentDate }}</text>
    </view>

    <view class="summary-card">
      <text class="card-title">关系概览</text>
      <view class="stats">
        <view class="stat-item">
          <text class="stat-value">{{ pairCount }}</text>
          <text class="stat-label">活跃关系</text>
        </view>
        <view class="stat-item">
          <text class="stat-value">{{ checkinStreak }}</text>
          <text class="stat-label">连续记录</text>
        </view>
        <view class="stat-item">
          <text class="stat-value">{{ healthScore }}</text>
          <text class="stat-label">健康分</text>
        </view>
      </view>
    </view>

    <view class="quick-actions">
      <view class="action-btn" @click="goCheckin">
        <text class="action-text">今日记录</text>
      </view>
      <view class="action-btn" @click="goReport">
        <text class="action-text">查看简报</text>
      </view>
      <view class="action-btn" @click="goPair">
        <text class="action-text">关系管理</text>
      </view>
      <view class="action-btn" @click="goTimeline">
        <text class="action-text">时间轴</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const userName = ref('用户')
const currentDate = ref('')
const pairCount = ref(0)
const checkinStreak = ref(0)
const healthScore = ref(0)

onMounted(() => {
  const now = new Date()
  currentDate.value = `${now.getMonth() + 1}月${now.getDate()}日`
  loadUserData()
})

const loadUserData = async () => {
  // TODO: 从后端加载真实数据
  userName.value = '测试用户'
  pairCount.value = 1
  checkinStreak.value = 7
  healthScore.value = 85
}

const goCheckin = () => {
  uni.switchTab({ url: '/pages/checkin/checkin' })
}

const goReport = () => {
  uni.switchTab({ url: '/pages/report/report' })
}

const goPair = () => {
  uni.navigateTo({ url: '/pages/pair/pair' })
}

const goTimeline = () => {
  uni.navigateTo({ url: '/pages/timeline/timeline' })
}
</script>

<style scoped>
.container {
  min-height: 100vh;
  background: #f5f5f5;
  padding: 40rpx;
}

.header {
  margin-bottom: 40rpx;
}

.greeting {
  font-size: 40rpx;
  font-weight: bold;
  color: #333;
  display: block;
  margin-bottom: 10rpx;
}

.date {
  font-size: 24rpx;
  color: #999;
}

.summary-card {
  background: #fff;
  border-radius: 20rpx;
  padding: 40rpx;
  margin-bottom: 40rpx;
}

.card-title {
  font-size: 28rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 30rpx;
  display: block;
}

.stats {
  display: flex;
  justify-content: space-around;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 40rpx;
  font-weight: bold;
  color: #667eea;
  display: block;
  margin-bottom: 10rpx;
}

.stat-label {
  font-size: 24rpx;
  color: #999;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20rpx;
}

.action-btn {
  background: #fff;
  border-radius: 20rpx;
  padding: 40rpx;
  text-align: center;
}

.action-text {
  font-size: 28rpx;
  color: #333;
}
</style>
