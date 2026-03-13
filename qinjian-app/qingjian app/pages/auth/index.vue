<template>
  <view class="auth-page">
    <view class="auth-hero">
      <text class="eyebrow">QINJIAN</text>
      <text class="title">把关系照顾好，也把自己照顾好</text>
      <text class="subtitle">先登录，再把网页、小程序和 app 的数据统一到同一个账户里。</text>
    </view>

    <view class="auth-card">
      <view class="tab-row">
        <text class="tab-chip" :class="{ active: mode === 'login' }" @click="mode = 'login'">登录</text>
        <text class="tab-chip" :class="{ active: mode === 'register' }" @click="mode = 'register'">注册</text>
      </view>

      <input v-model="form.email" class="input" type="text" placeholder="邮箱" />
      <input v-model="form.password" class="input" password placeholder="密码" />
      <input v-if="mode === 'register'" v-model="form.nickname" class="input" type="text" placeholder="昵称" />

      <button class="submit-btn" @click="submit">{{ mode === 'login' ? '登录进入' : '注册并进入' }}</button>

      <view class="helper-row">
        <text class="helper-link" @click="goBackHome">先看看首页</text>
      </view>
    </view>
  </view>
</template>

<script>
import api from '../../utils/api.js'
 import { syncSession } from '../../utils/session.js'

export default {
  data() {
    return {
      mode: 'login',
      form: {
        email: '',
        password: '',
        nickname: '',
      }
    }
  },
  methods: {
    async submit() {
      if (!this.form.email || !this.form.password) {
        uni.showToast({ title: '请填写邮箱和密码', icon: 'none' })
        return
      }
      if (this.mode === 'register' && !this.form.nickname) {
        uni.showToast({ title: '请填写昵称', icon: 'none' })
        return
      }

      try {
        if (this.mode === 'login') {
          await api.login(this.form.email.trim(), this.form.password)
        } else {
          await api.register(this.form.email.trim(), this.form.nickname.trim(), this.form.password)
        }
        await syncSession(this.$store)
        uni.showToast({ title: this.mode === 'login' ? '登录成功' : '注册成功', icon: 'success' })
        setTimeout(() => {
          uni.reLaunch({ url: '/pages/index/index' })
        }, 500)
      } catch (e) {
        uni.showToast({ title: e.message || '操作失败', icon: 'none' })
      }
    },
    goBackHome() {
      uni.reLaunch({ url: '/pages/index/index' })
    }
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  padding: 88rpx 28rpx;
  background: linear-gradient(180deg, #fff8f2 0%, #f5eee7 100%);
  box-sizing: border-box;
}

.eyebrow {
  font-size: 20rpx;
  letter-spacing: 4rpx;
  color: #a1887f;
}

.title {
  display: block;
  margin-top: 18rpx;
  font-size: 54rpx;
  line-height: 1.18;
  font-weight: 800;
  color: #2f2522;
}

.subtitle {
  display: block;
  margin-top: 14rpx;
  font-size: 24rpx;
  line-height: 1.8;
  color: #6d4c41;
}

.auth-card {
  margin-top: 34rpx;
  padding: 30rpx;
  border-radius: 36rpx;
  background: rgba(255,255,255,0.96);
  box-shadow: 0 18rpx 36rpx rgba(62, 39, 35, 0.08);
}

.tab-row {
  display: flex;
  gap: 14rpx;
  margin-bottom: 22rpx;
}

.tab-chip {
  padding: 12rpx 22rpx;
  border-radius: 999rpx;
  background: #f4ece3;
  color: #8d6e63;
  font-size: 22rpx;
  font-weight: 700;
}

.tab-chip.active {
  background: linear-gradient(135deg, #5d4037, #d4a373);
  color: #fff;
}

.input {
  width: 100%;
  height: 88rpx;
  margin-top: 16rpx;
  padding: 0 24rpx;
  border-radius: 24rpx;
  background: #fbf3eb;
  color: #3e2723;
  box-sizing: border-box;
}

.submit-btn {
  margin-top: 22rpx;
  height: 88rpx;
  border-radius: 999rpx;
  border: none;
  background: linear-gradient(135deg, #5d4037, #d4a373);
  color: #fff;
  font-size: 28rpx;
  font-weight: 800;
}

.helper-row {
  display: flex;
  justify-content: center;
  margin-top: 18rpx;
}

.helper-link {
  color: #8d6e63;
  font-size: 22rpx;
}
</style>
