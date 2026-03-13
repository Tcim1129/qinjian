<template>
  <view class="floating-shell">
    <view class="floating-bar">
      <view
        v-for="item in items"
        :key="item.path"
        class="tab-item"
        :class="{ active: current === item.path }"
        @click="go(item.path)"
      >
        <view class="tab-icon">{{ item.icon }}</view>
        <text class="tab-label">{{ item.label }}</text>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  props: {
    current: {
      type: String,
      default: '/pages/index/index'
    }
  },
  data() {
    return {
      items: [
        { path: '/pages/index/index', label: '首页', icon: '◐' },
        { path: '/pages/checkin/index', label: '打卡', icon: '✦' },
        { path: '/pages/discover/index', label: '发现', icon: '◎' },
        { path: '/pages/report/index', label: '报告', icon: '▥' },
        { path: '/pages/profile/index', label: '我的', icon: '◌' }
      ]
    }
  },
  methods: {
    go(path) {
      if (path === this.current) return
      uni.reLaunch({ url: path })
    }
  }
}
</script>

<style scoped>
.floating-shell {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 999;
  pointer-events: none;
}

.floating-bar {
  pointer-events: auto;
  margin: 0 24rpx calc(20rpx + env(safe-area-inset-bottom));
  padding: 14rpx;
  border-radius: 999rpx;
  background: rgba(255, 251, 247, 0.96);
  border: 1rpx solid rgba(212, 163, 115, 0.18);
  box-shadow: 0 16rpx 36rpx rgba(62, 39, 35, 0.14);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.tab-item {
  width: 20%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6rpx;
  padding: 10rpx 0;
  color: #a1887f;
}

.tab-item.active {
  color: #5d4037;
}

.tab-icon {
  width: 44rpx;
  height: 44rpx;
  border-radius: 22rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  background: #efe7df;
}

.tab-item.active .tab-icon {
  background: linear-gradient(135deg, #5d4037, #d4a373);
  color: #fff;
}

.tab-label {
  font-size: 20rpx;
  font-weight: 700;
}
</style>
