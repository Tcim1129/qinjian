<template>
  <view class="floating-shell">
    <view class="floating-glow"></view>
    <view class="floating-bar">
      <view
        v-for="item in items"
        :key="item.path"
        class="tab-item"
        :class="{ active: current === item.path }"
        @click="go(item.path)"
      >
        <view class="tab-icon-shell">
          <view class="tab-icon">{{ item.icon }}</view>
        </view>
        <text class="tab-label">{{ item.label }}</text>
        <view class="tab-dot"></view>
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
  left: 50%;
  right: auto;
  bottom: calc(20rpx + env(safe-area-inset-bottom));
  transform: translateX(-50%);
  width: calc(100vw - 48rpx);
  max-width: 760rpx;
  z-index: 999;
  pointer-events: none;
}

.floating-glow {
  position: absolute;
  left: 50%;
  bottom: 8rpx;
  transform: translateX(-50%);
  width: 72%;
  height: 46rpx;
  border-radius: 999rpx;
  background: radial-gradient(circle, rgba(212, 163, 115, 0.22), rgba(212, 163, 115, 0));
  filter: blur(12rpx);
}

.floating-bar {
  pointer-events: auto;
  width: 100%;
  margin: 0;
  padding: 14rpx 16rpx;
  box-sizing: border-box;
  border-radius: 999rpx;
  background: rgba(255, 251, 247, 0.96);
  border: 1rpx solid rgba(212, 163, 115, 0.18);
  box-shadow: 0 16rpx 36rpx rgba(62, 39, 35, 0.14);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.tab-item {
  flex: 1;
  width: auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6rpx;
  padding: 10rpx 6rpx 8rpx;
  color: #a1887f;
  border-radius: 28rpx;
  transition: all 0.22s ease;
}

.tab-item.active {
  color: #5d4037;
  background: linear-gradient(145deg, rgba(255, 248, 241, 0.98), rgba(248, 240, 232, 0.94));
  box-shadow: inset 0 1rpx 0 rgba(255, 255, 255, 0.9);
  transform: translateY(-4rpx);
}

.tab-icon-shell {
  width: 50rpx;
  height: 50rpx;
  border-radius: 25rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  background: #efe7df;
  transition: all 0.22s ease;
}

.tab-item.active .tab-icon-shell {
  background: linear-gradient(135deg, #5d4037, #d4a373);
  box-shadow: 0 10rpx 20rpx rgba(93, 64, 55, 0.18);
  animation: tabPulse 2.8s ease-in-out infinite;
}

.tab-icon {
  color: #fff;
}

.tab-label {
  font-size: 20rpx;
  font-weight: 700;
}

.tab-dot {
  width: 10rpx;
  height: 10rpx;
  border-radius: 50%;
  background: transparent;
  transition: all 0.22s ease;
}

.tab-item.active .tab-dot {
  background: #d4a373;
}

@keyframes tabPulse {
  0%,
  100% {
    transform: scale(1);
    box-shadow: 0 10rpx 20rpx rgba(93, 64, 55, 0.18);
  }
  50% {
    transform: scale(1.06);
    box-shadow: 0 14rpx 26rpx rgba(93, 64, 55, 0.24);
  }
}
</style>
