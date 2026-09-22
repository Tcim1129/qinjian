<template>
  <view v-if="visible" class="legal-overlay" @click.self="handleClose">
    <view class="legal-dialog">
      <view class="dialog-header">
        <view>
          <text class="dialog-eyebrow">使用前请阅读</text>
          <text class="dialog-title">{{ doc?.title || '协议说明' }}</text>
        </view>
        <view class="close-btn" @click="handleClose">
          <text class="close-icon">×</text>
        </view>
      </view>

      <scroll-view scroll-y class="dialog-body">
        <text class="dialog-intro">{{ intro }}</text>
        <view v-for="section in doc?.sections || []" :key="section.heading" class="legal-section">
          <text class="section-heading">{{ section.heading }}</text>
          <view v-for="(item, idx) in section.items" :key="idx" class="section-item">
            <text class="bullet">•</text>
            <text class="item-text">{{ item }}</text>
          </view>
        </view>
      </scroll-view>

      <view class="dialog-footer">
        <button class="confirm-btn" @click="handleClose">读完了</button>
      </view>
    </view>
  </view>
</template>

<script setup>
const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  doc: {
    type: Object,
    default: () => null
  },
  intro: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['close'])

function handleClose() {
  emit('close')
}
</script>

<style scoped lang="scss">
@import '@/styles/tokens.scss';

.legal-overlay {
  position: fixed;
  inset: 0;
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40rpx;
  background: rgba(31, 42, 47, 0.55);
}

.legal-dialog {
  width: 100%;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  background: $color-paper-soft;
  border: 1px solid $color-paper-line-strong;
  border-radius: 24rpx;
  box-shadow: $shadow-lg;
  overflow: hidden;
  padding: 32rpx;
}

.dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20rpx;
}

.dialog-eyebrow {
  display: block;
  font-size: 22rpx;
  color: $color-ink-soft;
  margin-bottom: 6rpx;
}

.dialog-title {
  display: block;
  font-size: 34rpx;
  font-weight: 800;
  color: $color-ink;
  font-family: $font-serif;
}

.close-btn {
  width: 56rpx;
  height: 56rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(68, 52, 40, 0.08);

  &:active {
    background: rgba(68, 52, 40, 0.16);
  }
}

.close-icon {
  font-size: 36rpx;
  color: $color-ink-soft;
  line-height: 1;
}

.dialog-body {
  flex: 1;
  max-height: 55vh;
  margin-bottom: 24rpx;
}

.dialog-intro {
  display: block;
  font-size: 26rpx;
  line-height: 1.6;
  color: $color-ink-soft;
  margin-bottom: 24rpx;
  background: rgba(240, 213, 184, 0.3);
  padding: 16rpx 20rpx;
  border-radius: 12rpx;
}

.legal-section {
  margin-bottom: 24rpx;
}

.section-heading {
  display: block;
  font-size: 28rpx;
  font-weight: 700;
  color: $color-ink;
  margin-bottom: 12rpx;
}

.section-item {
  display: flex;
  align-items: flex-start;
  gap: 12rpx;
  margin-bottom: 10rpx;
}

.bullet {
  color: $color-seal;
  font-size: 28rpx;
  line-height: 1.5;
}

.item-text {
  flex: 1;
  font-size: 26rpx;
  line-height: 1.5;
  color: $color-ink;
}

.dialog-footer {
  display: flex;
  justify-content: center;
}

.confirm-btn {
  width: 100%;
  height: 80rpx;
  line-height: 80rpx;
  border-radius: 16rpx;
  background: $color-seal;
  color: #fffdfa;
  font-size: 28rpx;
  font-weight: 700;
  border: none;

  &:active {
    background: $color-seal-deep;
  }
}
</style>
