<template>
  <view class="container">
    <view class="header">
      <text class="title">时间轴</text>
    </view>

    <view v-if="items.length > 0" class="timeline">
      <view v-for="item in items" :key="item.id" class="timeline-item">
        <view class="dot"></view>
        <view class="content">
          <text class="date">{{ item.date }}</text>
          <text class="text">{{ item.summary }}</text>
        </view>
      </view>
    </view>

    <view v-else class="empty">
      <text class="text">暂无记录</text>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'

const items = ref([])
</script>

<style scoped>
.container {
  min-height: 100vh;
  background: #f5f5f5;
  padding: 20rpx;
}

.header {
  background: #fff;
  padding: 30rpx;
  border-radius: 20rpx;
  margin-bottom: 20rpx;
}

.title {
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
}

.timeline {
  background: #fff;
  border-radius: 20rpx;
  padding: 30rpx;
}

.timeline-item {
  display: flex;
  position: relative;
  padding-bottom: 40rpx;
}

.timeline-item:last-child {
  padding-bottom: 0;
}

.dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  background: #667eea;
  margin: 12rpx 24rpx 0 0;
  flex-shrink: 0;
}

.content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}

.date {
  font-size: 24rpx;
  color: #999;
}

.text {
  font-size: 28rpx;
  color: #333;
  line-height: 1.6;
}

.empty {
  background: #fff;
  border-radius: 20rpx;
  padding: 100rpx 30rpx;
  text-align: center;
}

.empty .text {
  font-size: 28rpx;
  color: #999;
}
</style>
