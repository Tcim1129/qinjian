<template>
  <view class="auth-page">
    <!-- 顶部导航栏：提供返回按钮，确保任何端均可安全返回 -->
    <QjNavBar :show-back="true" back-text="返回" @back="handleNavBack" />

    <view class="auth-container">
      <!-- 品牌区：东方人文徽标 Logo 与 Slogan -->
      <view class="auth-brand">
        <view class="brand-logo-wrap">
          <image src="/static/qinjian-logo.jpg" class="brand-logo" mode="aspectFill" />
        </view>
        <view class="brand-titles">
          <text class="brand-name">亲健</text>
          <text class="brand-slogan">先看见，再靠近</text>
        </view>
      </view>

      <!-- 核心表单卡片 (1:1 严格对齐 01-login.png) -->
      <view class="auth-card">
        <view class="card-eyebrow-row">
          <text class="eyebrow">{{ modeLabel }}</text>
        </view>
        <text class="auth-title">{{ titleText }}</text>

        <!-- 模式分段器 (登录 / 注册) -->
        <view v-if="mode !== 'reset'" class="segmented-tabs" role="tablist">
          <view
            class="seg-tab"
            :class="{ active: mode === 'login' }"
            @click="switchMode('login')"
          >
            <text class="seg-text">登录</text>
          </view>
          <view
            class="seg-tab"
            :class="{ active: mode === 'register' }"
            @click="switchMode('register')"
          >
            <text class="seg-text">注册</text>
          </view>
        </view>

        <!-- 表单区域 -->
        <view class="form-stack">
          <!-- 注册特有：昵称 -->
          <view v-if="mode === 'register'" class="field">
            <text class="field-label">昵称</text>
            <input
              v-model.trim="form.nickname"
              class="input"
              type="text"
              placeholder="请输入昵称"
              placeholder-class="input-ph"
            />
          </view>

          <!-- 登录或注册模式 -->
          <template v-if="mode !== 'reset'">
            <!-- 登录模式下的方式切换 (验证码登录 / 密码登录) -->
            <view v-if="mode === 'login'" class="method-toggle-row">
              <text
                class="method-toggle-btn"
                :class="{ active: loginMethod === 'phone' }"
                @click="loginMethod = 'phone'"
              >
                手机验证码
              </text>
              <text class="method-toggle-sep">|</text>
              <text
                class="method-toggle-btn"
                :class="{ active: loginMethod === 'password' }"
                @click="loginMethod = 'password'"
              >
                密码登录
              </text>
            </view>

            <!-- 手机验证码登录 -->
            <template v-if="mode === 'login' && loginMethod === 'phone'">
              <view class="field">
                <text class="field-label">手机号</text>
                <input
                  v-model.trim="form.phone"
                  class="input"
                  type="number"
                  maxlength="11"
                  placeholder="请输入11位手机号"
                  placeholder-class="input-ph"
                />
              </view>
              <view class="field">
                <text class="field-label">验证码</text>
                <view class="code-row">
                  <input
                    v-model.trim="form.code"
                    class="input code-input"
                    type="number"
                    maxlength="6"
                    placeholder="6位验证码"
                    placeholder-class="input-ph"
                  />
                  <button
                    class="code-button"
                    :disabled="cooldown > 0 || sendingCode"
                    @click="sendVerificationCode"
                  >
                    {{ cooldown > 0 ? `${cooldown}s` : '获取验证码' }}
                  </button>
                </view>
              </view>
            </template>

            <!-- 账号密码登录 / 注册 -->
            <template v-else>
              <view class="field">
                <text class="field-label">账号</text>
                <input
                  v-model.trim="form.account"
                  class="input"
                  type="text"
                  placeholder="请输入手机号或邮箱"
                  placeholder-class="input-ph"
                />
              </view>
              <view class="field">
                <text class="field-label">密码</text>
                <input
                  v-model="form.password"
                  class="input"
                  type="password"
                  placeholder="请输入密码（至少6位）"
                  placeholder-class="input-ph"
                />
              </view>
            </template>

            <view class="auth-options">
              <view class="checkline" @click="rememberAccount = !rememberAccount">
                <view class="check-box" :class="{ checked: rememberAccount }">
                  <text v-if="rememberAccount" class="check-mark">✓</text>
                </view>
                <text class="check-text">记住账号</text>
              </view>
              <text class="text-button" @click="switchMode('reset')">忘记密码</text>
            </view>
          </template>

          <!-- 忘记密码/找回密码模式 -->
          <template v-else>
            <view class="field">
              <text class="field-label">手机号</text>
              <input
                v-model.trim="form.phone"
                class="input"
                type="number"
                maxlength="11"
                placeholder="已绑定的手机号"
                placeholder-class="input-ph"
              />
            </view>

            <view class="field">
              <text class="field-label">验证码</text>
              <view class="code-row">
                <input
                  v-model.trim="form.code"
                  class="input code-input"
                  type="number"
                  maxlength="6"
                  placeholder="6位验证码"
                  placeholder-class="input-ph"
                />
                <button
                  class="code-button"
                  :disabled="cooldown > 0 || sendingCode"
                  @click="sendVerificationCode"
                >
                  {{ cooldown > 0 ? `${cooldown}s` : '获取验证码' }}
                </button>
              </view>
            </view>

            <view class="field">
              <text class="field-label">新密码</text>
              <input
                v-model="form.newPassword"
                class="input"
                type="password"
                placeholder="至少 6 位新密码"
                placeholder-class="input-ph"
              />
            </view>
          </template>

          <!-- 合规协议勾选行 -->
          <view class="agreement-row">
            <view class="checkline" @click="agreementAccepted = !agreementAccepted">
              <view class="check-box" :class="{ checked: agreementAccepted }">
                <text v-if="agreementAccepted" class="check-mark">✓</text>
              </view>
              <text class="check-text">我已阅读并同意</text>
            </view>
            <view class="legal-links">
              <text
                v-for="doc in legalDocs"
                :key="doc.id"
                class="legal-link"
                @click.stop="showLegal(doc)"
              >
                {{ doc.title }}
              </text>
            </view>
          </view>

          <!-- 主提交按钮 (纯色朱砂红) -->
          <button
            class="primary-submit"
            :disabled="submitting"
            @click="handleSubmit"
          >
            {{ submitting ? '处理中...' : submitText }}
          </button>

          <!-- 底部体验样例入口 / 返回登录 -->
          <view class="bottom-actions">
            <button
              v-if="mode !== 'reset'"
              class="demo-button"
              type="button"
              @click="enterDemo"
            >
              进入体验样例
            </button>
            <button
              v-else
              class="demo-button"
              type="button"
              @click="switchMode('login')"
            >
              返回登录
            </button>
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
import { ref, reactive, computed, onMounted } from 'vue'
import { post } from '@/utils/request'
import { useUserStore } from '@/stores/user'
import QjNavBar from '@/components/QjNavBar.vue'
import QjLegalDialog from '@/components/QjLegalDialog.vue'
import { LOGIN_LEGAL_NOTICE } from '@/utils/complianceAgreement'

const userStore = useUserStore()

// 模式：login / register / reset
const mode = ref('login')
// 登录方式：phone (验证码) / password (密码)
const loginMethod = ref('phone')

const form = reactive({
  nickname: '',
  account: '',
  password: '',
  phone: '',
  code: '',
  newPassword: '',
})

const rememberAccount = ref(true)
const agreementAccepted = ref(true)
const submitting = ref(false)
const cooldown = ref(0)
const sendingCode = ref(false)

// 协议弹窗
const legalDialogVisible = ref(false)
const activeLegalDoc = ref(null)
const legalDocs = LOGIN_LEGAL_NOTICE.documents
const legalNoticeIntro = LOGIN_LEGAL_NOTICE.intro

const modeLabel = computed(() => {
  if (mode.value === 'login') return '登录'
  if (mode.value === 'register') return '注册'
  return '重置密码'
})

const titleText = computed(() => {
  if (mode.value === 'login') return '登录亲健'
  if (mode.value === 'register') return '创建账号'
  return '找回密码'
})

const submitText = computed(() => {
  if (mode.value === 'register') return '创建账号'
  if (mode.value === 'reset') return '重置并登录'
  return loginMethod.value === 'phone' ? '验证并登录' : '登 录'
})

onMounted(() => {
  const savedAccount = uni.getStorageSync('qj_saved_account')
  if (savedAccount) {
    form.account = savedAccount
    form.phone = savedAccount
  }
})

function switchMode(target) {
  mode.value = target
}

function handleNavBack() {
  const pages = getCurrentPages()
  if (pages && pages.length > 1) {
    uni.navigateBack()
  } else {
    uni.switchTab({ url: '/pages/home/home' })
  }
}

function showLegal(doc) {
  activeLegalDoc.value = doc
  legalDialogVisible.value = true
}

// 获取手机验证码
async function sendVerificationCode() {
  const targetPhone = form.phone.trim()
  if (!/^1\d{10}$/.test(targetPhone)) {
    uni.showToast({ title: '请输入有效的11位手机号', icon: 'none' })
    return
  }

  sendingCode.value = true
  try {
    const res = await post('/api/v1/auth/phone/send-code', { phone: targetPhone })
    if (res?.debug_code) {
      form.code = res.debug_code
      uni.showToast({ title: `测试验证码: ${res.debug_code}`, icon: 'none', duration: 3500 })
    } else {
      uni.showToast({ title: '验证码已发送', icon: 'none' })
    }
    cooldown.value = 60
    const timer = setInterval(() => {
      cooldown.value -= 1
      if (cooldown.value <= 0) {
        clearInterval(timer)
      }
    }, 1000)
  } catch (err) {
    uni.showToast({ title: err.message || '发送失败，请稍后重试', icon: 'none' })
  } finally {
    sendingCode.value = false
  }
}

// 提交表单
async function handleSubmit() {
  if (!agreementAccepted.value) {
    uni.showToast({ title: '请先阅读并同意服务协议', icon: 'none' })
    return
  }

  submitting.value = true
  try {
    if (rememberAccount.value) {
      const acc = form.phone || form.account
      if (acc) uni.setStorageSync('qj_saved_account', acc)
    } else {
      uni.removeStorageSync('qj_saved_account')
    }

    if (mode.value === 'register') {
      if (!form.account || !form.password) {
        uni.showToast({ title: '请填写账号和密码', icon: 'none' })
        return
      }
      await userStore.register(form.account, form.nickname, form.password)
      uni.showToast({ title: '注册成功', icon: 'success' })
      setTimeout(() => {
        uni.switchTab({ url: '/pages/home/home' })
      }, 400)
    } else if (mode.value === 'reset') {
      if (!form.phone || !form.code || !form.newPassword) {
        uni.showToast({ title: '请完整填写手机号、验证码和新密码', icon: 'none' })
        return
      }
      await post('/api/v1/auth/phone/reset-password', {
        phone: form.phone,
        code: form.code,
        new_password: form.newPassword
      })
      uni.showToast({ title: '密码重置成功，正在登录', icon: 'success' })
      await userStore.phoneLogin(form.phone, form.code)
      setTimeout(() => {
        uni.switchTab({ url: '/pages/home/home' })
      }, 400)
    } else {
      // 登录模式
      if (loginMethod.value === 'phone') {
        if (!form.phone || !form.code) {
          uni.showToast({ title: '请填写手机号和验证码', icon: 'none' })
          return
        }
        await userStore.phoneLogin(form.phone, form.code)
      } else {
        if (!form.account || !form.password) {
          uni.showToast({ title: '请填写账号和密码', icon: 'none' })
          return
        }
        await userStore.login(form.account, form.password)
      }
      uni.showToast({ title: '登录成功', icon: 'success' })
      setTimeout(() => {
        uni.switchTab({ url: '/pages/home/home' })
      }, 400)
    }
  } catch (err) {
    uni.showToast({ title: err.message || '操作失败，请重试', icon: 'none' })
  } finally {
    submitting.value = false
  }
}

// 进入体验样例
function enterDemo() {
  userStore.enterDemo()
  uni.showToast({ title: '已进入体验样例', icon: 'none' })
  setTimeout(() => {
    uni.switchTab({ url: '/pages/home/home' })
  }, 300)
}
</script>

<style lang="scss" scoped>
.auth-page {
  min-height: 100vh;
  padding-bottom: 60rpx;
  background-color: #f7f1eb;
  background-image:
    radial-gradient(800rpx circle at 10% -10%, rgba(215, 104, 72, 0.16), transparent 45%),
    radial-gradient(600rpx circle at 90% -5%, rgba(240, 213, 184, 0.4), transparent 50%),
    linear-gradient(180deg, #fcf7f2 0%, #f6efe7 100%);
  display: flex;
  flex-direction: column;
}

.auth-container {
  width: 90%;
  max-width: 680rpx;
  margin: 20rpx auto 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* 品牌区 */
.auth-brand {
  display: flex;
  align-items: center;
  gap: 24rpx;
  margin-bottom: 36rpx;
  padding: 10rpx 0;

  .brand-logo-wrap {
    width: 88rpx;
    height: 88rpx;
    border-radius: 50%;
    overflow: hidden;
    border: 2rpx solid rgba(215, 104, 72, 0.25);
    box-shadow: 0 4rpx 14rpx rgba(170, 77, 51, 0.12);
    display: flex;
    align-items: center;
    justify-content: center;
    background: #ffffff;
  }

  .brand-logo {
    width: 100%;
    height: 100%;
  }

  .brand-titles {
    display: flex;
    flex-direction: column;
  }

  .brand-name {
    font-family: $font-serif;
    font-size: 40rpx;
    font-weight: 700;
    color: #1f2a2f;
    line-height: 1.2;
    letter-spacing: 2rpx;
  }

  .brand-slogan {
    font-size: 24rpx;
    color: #5b666c;
    margin-top: 6rpx;
    letter-spacing: 1rpx;
  }
}

/* 核心卡片 (100% 对齐 01-login.png) */
.auth-card {
  width: 100%;
  background: rgba(255, 250, 244, 0.94);
  border: 1px solid rgba(68, 52, 40, 0.12);
  border-radius: 16rpx;
  padding: 36rpx 32rpx;
  box-shadow: 0 12rpx 32rpx rgba(74, 52, 36, 0.07);
}

.card-eyebrow-row {
  display: flex;
  align-items: center;
  margin-bottom: 8rpx;
}

.auth-title {
  font-family: $font-serif;
  font-size: 38rpx;
  font-weight: 700;
  color: #1f2a2f;
  margin-bottom: 24rpx;
  display: block;
}

/* 分段器 */
.segmented-tabs {
  display: flex;
  background: rgba(68, 52, 40, 0.06);
  padding: 6rpx;
  border-radius: 12rpx;
  margin-bottom: 28rpx;

  .seg-tab {
    flex: 1;
    text-align: center;
    padding: 14rpx 0;
    border-radius: 8rpx;
    transition: all 0.2s ease;

    .seg-text {
      font-size: 28rpx;
      font-weight: 500;
      color: #5b666c;
    }

    &.active {
      background: #ffffff;
      box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.06);

      .seg-text {
        color: #1f2a2f;
        font-weight: 600;
      }
    }
  }
}

.method-toggle-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 16rpx;
  margin-bottom: 16rpx;

  .method-toggle-btn {
    font-size: 24rpx;
    color: #7c837f;
    &.active {
      color: #d76848;
      font-weight: 600;
    }
  }

  .method-toggle-sep {
    font-size: 20rpx;
    color: rgba(68, 52, 40, 0.15);
  }
}

/* 表单字段 */
.form-stack {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8rpx;

  .field-label {
    font-size: 24rpx;
    color: #5b666c;
    font-weight: 500;
  }

  .input {
    width: 100%;
    height: 76rpx;
    border: 1px solid rgba(68, 52, 40, 0.15);
    background: #ffffff;
    border-radius: 10rpx;
    padding: 0 20rpx;
    font-size: 28rpx;
    color: #1f2a2f;

    &:focus {
      border-color: #d76848;
    }
  }

  .input-ph {
    color: #b4bab8;
    font-size: 26rpx;
  }
}

.code-row {
  display: flex;
  gap: 16rpx;

  .code-input {
    flex: 1;
  }

  .code-button {
    min-width: 190rpx;
    height: 76rpx;
    line-height: 74rpx;
    padding: 0 16rpx;
    background: #fceee8;
    border: 1px solid rgba(215, 104, 72, 0.3);
    border-radius: 10rpx;
    color: #c4573b;
    font-size: 24rpx;
    font-weight: 500;
    text-align: center;
    margin: 0;

    &[disabled] {
      opacity: 0.6;
      background: #f0ebe5;
      border-color: rgba(68, 52, 40, 0.1);
      color: #7c837f;
    }
  }
}

/* 选项行 (记住账号 / 忘记密码) */
.auth-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4rpx 0;

  .text-button {
    font-size: 24rpx;
    color: #5b666c;
  }
}

.checkline {
  display: inline-flex;
  align-items: center;
  gap: 12rpx;

  .check-box {
    width: 32rpx;
    height: 32rpx;
    border: 1px solid rgba(68, 52, 40, 0.25);
    border-radius: 6rpx;
    background: #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;

    &.checked {
      background: #d76848;
      border-color: #d76848;
    }

    .check-mark {
      color: #ffffff;
      font-size: 22rpx;
      line-height: 1;
    }
  }

  .check-text {
    font-size: 24rpx;
    color: #5b666c;
  }
}

/* 协议行 */
.agreement-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8rpx;
  padding: 8rpx 0;

  .legal-links {
    display: inline-flex;
    align-items: center;
    gap: 8rpx;
  }

  .legal-link {
    font-size: 24rpx;
    color: #d76848;
    text-decoration: underline;
  }
}

/* 主提交按钮 (纯正朱砂红) */
.primary-submit {
  width: 100%;
  height: 84rpx;
  line-height: 84rpx;
  background: #d76848;
  border: 1px solid #aa4d33;
  border-radius: 12rpx;
  color: #ffffff;
  font-size: 30rpx;
  font-weight: 600;
  letter-spacing: 2rpx;
  text-align: center;
  box-shadow: 0 8rpx 20rpx rgba(215, 104, 72, 0.25);
  margin-top: 12rpx;

  &[disabled] {
    opacity: 0.65;
  }
}

/* 底部纯文字直达按钮 (进入体验样例 / 返回登录) */
.bottom-actions {
  display: flex;
  justify-content: center;
  padding-top: 12rpx;

  .demo-button {
    background: none;
    border: none;
    color: #5b666c;
    font-size: 26rpx;
    padding: 10rpx 24rpx;
    line-height: 1.4;

    &::after {
      border: none;
    }
  }
}
</style>
