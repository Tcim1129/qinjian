<template>
  <view class="container">
    <view class="logo-section">
      <text class="app-name">亲健</text>
    </view>

    <view class="form-section">
      <view class="tab-bar">
        <text :class="['tab', loginType === 'email' ? 'active' : '']" @click="loginType = 'email'">邮箱登录</text>
        <text :class="['tab', loginType === 'phone' ? 'active' : '']" @click="loginType = 'phone'">手机登录</text>
      </view>

      <view v-if="loginType === 'email'" class="form">
        <input v-model="email" placeholder="请输入邮箱" type="text" class="input" />
        <input v-model="password" placeholder="请输入密码" type="password" class="input" />
        <button @click="handleLogin" type="primary" class="login-btn">登录</button>
        <text class="register-link" @click="goRegister">还没有账号？立即注册</text>
      </view>

      <view v-else class="form">
        <input v-model="phone" placeholder="请输入手机号" type="number" class="input" />
        <view class="code-row">
          <input v-model="code" placeholder="请输入验证码" type="number" class="input code-input" />
          <button @click="sendCode" :disabled="codeCountdown > 0" class="code-btn">
            {{ codeCountdown > 0 ? `${codeCountdown}s` : '发送验证码' }}
          </button>
        </view>
        <button @click="handlePhoneLogin" type="primary" class="login-btn">登录</button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref } from 'vue'
import { post } from '../../utils/request'

const loginType = ref('email')
const email = ref('')
const password = ref('')
const phone = ref('')
const code = ref('')
const codeCountdown = ref(0)

const handleLogin = async () => {
  if (!email.value || !password.value) {
    uni.showToast({ title: '请填写完整信息', icon: 'none' })
    return
  }
  
  try {
    const data = await post('/api/v1/auth/login', {
      email: email.value,
      password: password.value
    })

    if (data.access_token) {
      uni.setStorageSync('token', data.access_token)
      uni.switchTab({ url: '/pages/home/home' })
    }
  } catch (error) {
    uni.showToast({ title: '登录失败', icon: 'none' })
  }
}

const handlePhoneLogin = async () => {
  if (!phone.value || !code.value) {
    uni.showToast({ title: '请填写完整信息', icon: 'none' })
    return
  }
  
  // TODO: 实现手机验证码登录
  uni.showToast({ title: '手机登录功能开发中', icon: 'none' })
}

const sendCode = () => {
  if (!phone.value || phone.value.length !== 11) {
    uni.showToast({ title: '请输入正确的手机号', icon: 'none' })
    return
  }
  
  // TODO: 调用发送验证码接口
  codeCountdown.value = 60
  const timer = setInterval(() => {
    codeCountdown.value--
    if (codeCountdown.value <= 0) {
      clearInterval(timer)
    }
  }, 1000)
}

const goRegister = () => {
  uni.showToast({ title: '请使用邮箱注册', icon: 'none' })
}
</script>

<style scoped>
.container {
  min-height: 100vh;
  background: #f5f5f5;
  padding: 80rpx 40rpx;
}

.logo-section {
  text-align: center;
  margin-bottom: 80rpx;
}

.app-name {
  font-size: 56rpx;
  font-weight: bold;
  color: #333;
}

.form-section {
  background: #fff;
  border-radius: 20rpx;
  padding: 40rpx;
}

.tab-bar {
  display: flex;
  justify-content: center;
  margin-bottom: 40rpx;
  border-bottom: 1px solid #eee;
}

.tab {
  padding: 20rpx 40rpx;
  font-size: 28rpx;
  color: #666;
  position: relative;
}

.tab.active {
  color: #667eea;
  font-weight: bold;
}

.tab.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 60%;
  height: 4rpx;
  background: #667eea;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 30rpx;
}

.input {
  height: 80rpx;
  padding: 0 30rpx;
  border: 1px solid #ddd;
  border-radius: 10rpx;
  font-size: 28rpx;
}

.code-row {
  display: flex;
  gap: 20rpx;
}

.code-input {
  flex: 1;
}

.code-btn {
  width: 200rpx;
  height: 80rpx;
  line-height: 80rpx;
  font-size: 24rpx;
  background: #667eea;
  color: #fff;
  border-radius: 10rpx;
  border: none;
}

.code-btn[disabled] {
  background: #ccc;
}

.login-btn {
  margin-top: 20rpx;
  border-radius: 10rpx;
}

.register-link {
  text-align: center;
  font-size: 24rpx;
  color: #667eea;
  margin-top: 20rpx;
}
</style>
