<template>
  <view class="auth-page">
    <!-- 顶部安全区与返回导航栏 -->
    <QjNavBar :show-back="true" back-text="返回" @back="handleNavBack" />

    <!-- 品牌区：东方人文质感 Logo 与 Slogan -->
    <view class="brand-section">
      <view class="logo-wrap">
        <image src="/static/qinjian-logo.jpg" class="brand-logo" mode="aspectFill" />
      </view>
      <text class="brand-title">亲健</text>
      <text class="brand-slogan">先看见，再靠近</text>
    </view>

    <!-- 核心表单卡片 (玉润纸白半透明微质感) -->
    <view class="auth-card">
      <!-- 顶级分段器：登录 / 注册 -->
      <view class="segmented-tabs">
        <view
          :class="['seg-tab', mode === 'login' ? 'active' : '']"
          @click="switchMode('login')"
        >
          <text class="seg-text">登录</text>
        </view>
        <view
          :class="['seg-tab', mode === 'register' ? 'active' : '']"
          @click="switchMode('register')"
        >
          <text class="seg-text">注册</text>
        </view>
      </view>

      <!-- 登录模式下的方式切换：验证码登录 / 密码登录 -->
      <view v-if="mode === 'login'" class="login-sub-methods">
        <view
          :class="['method-chip', loginMethod === 'phone' ? 'active' : '']"
          @click="loginMethod = 'phone'"
        >
          <text class="chip-text">手机验证码</text>
        </view>
        <view
          :class="['method-chip', loginMethod === 'password' ? 'active' : '']"
          @click="loginMethod = 'password'"
        >
          <text class="chip-text">密码登录</text>
        </view>
      </view>

      <!-- 表单区域 -->
      <view class="form-body">
        <!-- 注册：输入昵称 -->
        <view v-if="mode === 'register'" class="field-item">
          <text class="field-label">昵称</text>
          <input
            v-model.trim="nickname"
            class="qj-input"
            type="text"
            placeholder="请输入您的昵称"
            placeholder-class="input-placeholder"
          />
        </view>

        <!-- 手机验证码登录表单 -->
        <template v-if="mode === 'login' && loginMethod === 'phone'">
          <view class="field-item">
            <text class="field-label">手机号</text>
            <input
              v-model.trim="phone"
              class="qj-input"
              type="number"
              maxlength="11"
              placeholder="请输入 11 位手机号"
              placeholder-class="input-placeholder"
            />
          </view>

          <view class="field-item">
            <text class="field-label">验证码</text>
            <view class="code-row">
              <input
                v-model.trim="code"
                class="qj-input code-input"
                type="number"
                maxlength="6"
                placeholder="6 位验证码"
                placeholder-class="input-placeholder"
              />
              <button
                class="code-btn"
                :disabled="countdown > 0 || sendingCode"
                @click="sendVerificationCode"
              >
                {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
              </button>
            </view>
          </view>
        </template>

        <!-- 密码登录 / 注册表单 -->
        <template v-else>
          <view class="field-item">
            <text class="field-label">账号 / 邮箱</text>
            <input
              v-model.trim="account"
              class="qj-input"
              type="text"
              placeholder="请输入手机号或邮箱"
              placeholder-class="input-placeholder"
            />
          </view>

          <view class="field-item">
            <text class="field-label">密码</text>
            <input
              v-model="password"
              class="qj-input"
              type="password"
              placeholder="至少 6 位密码"
              placeholder-class="input-placeholder"
            />
          </view>
        </template>

        <!-- 协议勾选行 (对齐 Web 版合规规范) -->
        <view class="agreement-row">
          <checkbox-group @change="onAgreementChange">
            <label class="check-label">
              <checkbox
                value="agree"
                :checked="agreementAccepted"
                color="#d76848"
                style="transform: scale(0.75);"
              />
              <text class="agreement-text">我已阅读并同意</text>
            </label>
          </checkbox-group>
          <view class="legal-links">
            <text
              v-for="doc in legalDocs"
              :key="doc.id"
              class="legal-link"
              @click="openLegal(doc)"
            >
              {{ doc.title }}
            </text>
          </view>
        </view>

        <!-- 主提交按钮 (朱砂印红) -->
        <button
          class="primary-submit-btn"
          :disabled="submitting"
          @click="handleSubmit"
        >
          {{ submitting ? '处理中...' : submitBtnText }}
        </button>

        <!-- 体验样例直达入口 (免登录体验 Demo Mode) -->
        <view class="demo-section">
          <view class="divider-line">
            <text class="divider-text">或者</text>
          </view>
          <button class="demo-btn" @click="handleEnterDemo">
            进入体验样例 (免登录探索)
          </button>
          <view class="debug-helper-wrap" @click="quickFillDebugAccount">
            <text class="debug-helper-text">⚡ 调试便捷：一键填入测试账号与验证码</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 协议说明弹窗 -->
    <QjLegalDialog
      :visible="legalDialogVisible"
      :doc="activeLegalDoc"
      :intro="legalNoticeIntro"
      @close="legalDialogVisible = false"
    />
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { post } from '@/utils/request'
import { useUserStore } from '@/stores/user'
import QjNavBar from '@/components/QjNavBar.vue'
import QjLegalDialog from '@/components/QjLegalDialog.vue'
import { LOGIN_LEGAL_NOTICE } from '@/utils/complianceAgreement'

const userStore = useUserStore()

// 模式：login / register
const mode = ref('login')
// 登录方式：phone (验证码) / password (密码)
const loginMethod = ref('phone')

// 表单字段
const nickname = ref('')
const account = ref('')
const password = ref('')
const phone = ref('')
const code = ref('')

// 状态
const countdown = ref(0)
const sendingCode = ref(false)
const submitting = ref(false)
const agreementAccepted = ref(false)

// 协议弹窗
const legalDialogVisible = ref(false)
const activeLegalDoc = ref(null)
const legalDocs = LOGIN_LEGAL_NOTICE.documents
const legalNoticeIntro = LOGIN_LEGAL_NOTICE.intro

const submitBtnText = computed(() => {
  if (mode.value === 'register') return '立即注册'
  return loginMethod.value === 'phone' ? '验证并登录' : '登 录'
})

function switchMode(nextMode) {
  mode.value = nextMode
}

function handleNavBack() {
  const pages = getCurrentPages()
  if (pages && pages.length > 1) {
    uni.navigateBack()
  } else {
    uni.switchTab({ url: '/pages/home/home' })
  }
}

function onAgreementChange(e) {
  agreementAccepted.value = e.detail.value.includes('agree')
}

function openLegal(doc) {
  activeLegalDoc.value = doc
  legalDialogVisible.value = true
}

// 手机验证码发送
async function sendVerificationCode() {
  if (!/^1\d{10}$/.test(phone.value)) {
    uni.showToast({ title: '请输入正确的11位手机号', icon: 'none' })
    return
  }

  sendingCode.value = true
  try {
    const res = await post('/api/v1/auth/phone/send-code', { phone: phone.value })
    if (res.debug_code) {
      uni.showToast({ title: `测试验证码: ${res.debug_code}`, icon: 'none', duration: 3500 })
    } else {
      uni.showToast({ title: '验证码已发送，请查收', icon: 'none' })
    }
    countdown.value = 60
    const timer = setInterval(() => {
      countdown.value -= 1
      if (countdown.value <= 0) {
        clearInterval(timer)
      }
    }, 1000)
  } catch (err) {
    uni.showToast({ title: err.message || '发送失败，请稍后再试', icon: 'none' })
  } finally {
    sendingCode.value = false
  }
}

// 提交表单 (登录 / 注册)
async function handleSubmit() {
  if (!agreementAccepted.value) {
    uni.showToast({ title: '请先阅读并勾选服务协议', icon: 'none' })
    return
  }

  submitting.value = true
  try {
    if (mode.value === 'register') {
      if (!account.value || !password.value) {
        uni.showToast({ title: '请填写账号和密码', icon: 'none' })
        return
      }
      await userStore.register(account.value, nickname.value, password.value)
      uni.showToast({ title: '注册成功，欢迎加入亲健', icon: 'success' })
      setTimeout(() => {
        uni.switchTab({ url: '/pages/home/home' })
      }, 500)
    } else if (loginMethod.value === 'phone') {
      if (!phone.value || !code.value) {
        uni.showToast({ title: '请填写手机号和验证码', icon: 'none' })
        return
      }
      await userStore.phoneLogin(phone.value, code.value)
      uni.showToast({ title: '登录成功，欢迎回来', icon: 'success' })
      setTimeout(() => {
        uni.switchTab({ url: '/pages/home/home' })
      }, 500)
    } else {
      if (!account.value || !password.value) {
        uni.showToast({ title: '请输入账号和密码', icon: 'none' })
        return
      }
      await userStore.login(account.value, password.value)
      uni.showToast({ title: '登录成功，欢迎回来', icon: 'success' })
      setTimeout(() => {
        uni.switchTab({ url: '/pages/home/home' })
      }, 500)
    }
  } catch (err) {
    uni.showToast({ title: err.message || '操作失败，请重试', icon: 'none' })
  } finally {
    submitting.value = false
  }
}

// 进入体验样例 (Demo 模式)
function handleEnterDemo() {
  if (!agreementAccepted.value) {
    // 友善自动勾选或提示
    agreementAccepted.value = true
  }
  userStore.enterDemo()
  uni.showToast({ title: '已开启体验样例', icon: 'success' })
  setTimeout(() => {
    uni.switchTab({ url: '/pages/home/home' })
  }, 400)
}

function quickFillDebugAccount() {
  mode.value = 'login'
  loginMethod.value = 'phone'
  phone.value = '13800138000'
  code.value = '123456'
  agreementAccepted.value = true
  uni.showToast({ title: '已自动填入测试手机号与验证码', icon: 'none' })
}
</script>

<style scoped lang="scss">
@import '@/styles/tokens.scss';

.auth-page {
  min-height: 100vh;
  padding-bottom: 60rpx;
  box-sizing: border-box;
}

.brand-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 20rpx;
  margin-bottom: 40rpx;
}

.logo-wrap {
  width: 140rpx;
  height: 140rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(255, 253, 250, 0.85);
  border: 2rpx solid rgba(215, 104, 72, 0.36);
  box-shadow: 0 16rpx 38rpx rgba(94, 62, 43, 0.12);
  margin-bottom: 18rpx;
}

.brand-logo {
  width: 104rpx;
  height: 104rpx;
  border-radius: 50%;
}

.brand-title {
  font-family: $font-serif;
  font-size: 54rpx;
  font-weight: 800;
  color: $color-seal-deep;
  letter-spacing: 4rpx;
  margin-bottom: 8rpx;
}

.brand-slogan {
  font-size: 26rpx;
  font-weight: 600;
  color: $color-ink-soft;
  letter-spacing: 2rpx;
}

.auth-card {
  margin: 0 32rpx;
  padding: 40rpx 32rpx;
  background: $color-paper-strong;
  border: 1px solid $color-paper-line-strong;
  border-radius: $radius-lg;
  box-shadow: $shadow-md;
}

.segmented-tabs {
  display: flex;
  background: rgba(245, 238, 231, 0.74);
  border: 1px solid rgba(68, 52, 40, 0.14);
  border-radius: 16rpx;
  padding: 6rpx;
  margin-bottom: 28rpx;
}

.seg-tab {
  flex: 1;
  height: 68rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12rpx;
  transition: all 0.2s ease;

  &.active {
    background: #fffdfa;
    box-shadow: 0 4rpx 14rpx rgba(74, 52, 36, 0.08);

    .seg-text {
      color: $color-ink;
      font-weight: 800;
    }
  }
}

.seg-text {
  font-size: 28rpx;
  font-weight: 600;
  color: $color-ink-soft;
}

.login-sub-methods {
  display: flex;
  gap: 16rpx;
  margin-bottom: 28rpx;
}

.method-chip {
  padding: 8rpx 24rpx;
  border-radius: 30rpx;
  background: rgba(245, 238, 231, 0.5);
  border: 1px solid transparent;

  &.active {
    background: rgba(215, 104, 72, 0.12);
    border-color: rgba(215, 104, 72, 0.4);

    .chip-text {
      color: $color-seal-deep;
      font-weight: 700;
    }
  }
}

.chip-text {
  font-size: 24rpx;
  color: $color-ink-soft;
}

.form-body {
  display: flex;
  flex-direction: column;
  gap: 22rpx;
}

.field-item {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}

.field-label {
  font-size: 26rpx;
  font-weight: 700;
  color: $color-ink-soft;
}

.qj-input {
  width: 100%;
  height: 84rpx;
  padding: 0 24rpx;
  background: rgba(246, 240, 234, 0.78);
  border: 1px solid rgba(68, 52, 40, 0.16);
  border-radius: 14rpx;
  font-size: 28rpx;
  color: $color-ink;

  &:focus {
    background: #fffdfa;
    border-color: rgba(181, 83, 56, 0.54);
  }
}

.input-placeholder {
  color: rgba(91, 102, 108, 0.45);
}

.code-row {
  display: flex;
  gap: 16rpx;
}

.code-input {
  flex: 1;
}

.code-btn {
  width: 220rpx;
  height: 84rpx;
  line-height: 84rpx;
  padding: 0;
  font-size: 26rpx;
  font-weight: 700;
  background: rgba(255, 253, 250, 0.9);
  color: $color-seal-deep;
  border: 1px solid rgba(215, 104, 72, 0.3);
  border-radius: 14rpx;

  &[disabled] {
    color: $color-ink-faint;
    border-color: rgba(68, 52, 40, 0.1);
    background: rgba(245, 238, 231, 0.6);
  }
}

.agreement-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8rpx;
  margin-top: 10rpx;
}

.check-label {
  display: flex;
  align-items: center;
}

.agreement-text {
  font-size: 24rpx;
  color: $color-ink-soft;
}

.legal-links {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
}

.legal-link {
  font-size: 24rpx;
  font-weight: 700;
  color: $color-seal-deep;
  text-decoration: underline;
}

.primary-submit-btn {
  width: 100%;
  height: 88rpx;
  line-height: 88rpx;
  margin-top: 16rpx;
  border-radius: 16rpx;
  background: $color-seal;
  color: #fffdfa;
  font-size: 30rpx;
  font-weight: 800;
  border: none;
  box-shadow: $shadow-seal;
  letter-spacing: 2rpx;

  &:active {
    background: $color-seal-deep;
    transform: scale(0.99);
  }

  &[disabled] {
    opacity: 0.6;
  }
}

.demo-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 10rpx;
}

.divider-line {
  position: relative;
  width: 100%;
  text-align: center;
  margin: 20rpx 0;

  &::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 0;
    right: 0;
    height: 1px;
    background: rgba(68, 52, 40, 0.12);
  }
}

.divider-text {
  position: relative;
  display: inline-block;
  padding: 0 16rpx;
  background: $color-paper-strong;
  font-size: 22rpx;
  color: $color-ink-faint;
}

.demo-btn {
  width: 100%;
  height: 80rpx;
  line-height: 80rpx;
  background: rgba(245, 238, 231, 0.8);
  border: 1px dashed rgba(215, 104, 72, 0.5);
  border-radius: 16rpx;
  color: $color-seal-deep;
  font-size: 28rpx;
  font-weight: 700;

  &:active {
    background: rgba(244, 221, 212, 0.7);
  }
}

.debug-helper-wrap {
  margin-top: 18rpx;
  padding: 10rpx 20rpx;
  background: rgba(240, 213, 184, 0.3);
  border-radius: 12rpx;

  &:active {
    background: rgba(240, 213, 184, 0.6);
  }
}

.debug-helper-text {
  font-size: 22rpx;
  color: $color-ink-soft;
  font-weight: 600;
}
</style>
