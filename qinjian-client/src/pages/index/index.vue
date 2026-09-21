<template>
  <view class="container">
    <view class="welcome">
      <text class="title">欢迎使用亲健</text>
      <text class="subtitle">基于生成式 AI 的关系智能维系平台</text>
    </view>
    <button @click="goLogin" type="primary" class="start-btn">开始使用</button>
  </view>
</template>

<script setup>
const goLogin = () => {
  uni.navigateTo({ url: '/pages/auth/login' })
}
</script>

<style scoped>
.container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  padding: 40rpx;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.welcome {
  text-align: center;
  margin-bottom: 80rpx;
}

.title {
  font-size: 48rpx;
  color: #fff;
  font-weight: bold;
  display: block;
  margin-bottom: 20rpx;
}

.subtitle {
  font-size: 28rpx;
  color: rgba(255, 255, 255, 0.8);
  display: block;
}

.start-btn {
  width: 400rpx;
  border-radius: 50rpx;
}
</style>
