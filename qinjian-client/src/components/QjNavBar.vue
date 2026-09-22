<template>
  <view class="qj-navbar" :style="{ paddingTop: `${statusBarHeight}px` }">
    <view class="navbar-content" :style="{ height: `${navHeight}px` }">
      <view v-if="showBack" class="back-btn" @click="handleBack">
        <text class="back-arrow">←</text>
        <text v-if="backText" class="back-text">{{ backText }}</text>
      </view>
      <view v-else class="placeholder"></view>

      <view class="title-wrap">
        <text class="navbar-title">{{ title }}</text>
      </view>

      <view class="right-slot">
        <slot name="right"></slot>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: ''
  },
  showBack: {
    type: Boolean,
    default: true
  },
  backText: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['back'])

const statusBarHeight = ref(20)
const navHeight = ref(44)

onMounted(() => {
  try {
    const sys = uni.getSystemInfoSync()
    if (sys.statusBarHeight) {
      statusBarHeight.value = sys.statusBarHeight
    }
    // #ifdef MP-WEIXIN
    const menu = uni.getMenuButtonBoundingClientRect()
    if (menu && menu.top) {
      navHeight.value = (menu.top - sys.statusBarHeight) * 2 + menu.height
    }
    // #endif
  } catch (e) {
    // fallback defaults
  }
})

function handleBack() {
  emit('back')
  const pages = getCurrentPages()
  if (pages && pages.length > 1) {
    uni.navigateBack()
  } else {
    uni.switchTab({ url: '/pages/home/home' })
  }
}
</script>

<style scoped lang="scss">
@import '@/styles/tokens.scss';

.qj-navbar {
  position: relative;
  z-index: 100;
  width: 100%;
  background: transparent;
}

.navbar-content {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24rpx;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 8rpx;
  height: 64rpx;
  padding: 0 16rpx;
  border-radius: 32rpx;
  background: rgba(255, 253, 250, 0.7);
  border: 1px solid rgba(68, 52, 40, 0.12);
  box-shadow: 0 4rpx 12rpx rgba(56, 40, 30, 0.05);

  &:active {
    background: rgba(244, 221, 212, 0.8);
  }
}

.back-arrow {
  font-size: 34rpx;
  font-weight: 700;
  color: $color-ink;
  line-height: 1;
}

.back-text {
  font-size: 24rpx;
  color: $color-ink-soft;
  font-weight: 600;
}

.placeholder {
  width: 64rpx;
}

.title-wrap {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  max-width: 50%;
  text-align: center;
}

.navbar-title {
  font-size: 32rpx;
  font-weight: 800;
  color: $color-ink;
  font-family: $font-serif;
  letter-spacing: 1rpx;
}

.right-slot {
  min-width: 64rpx;
  display: flex;
  justify-content: flex-end;
}
</style>
