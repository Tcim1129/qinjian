<template>
  <main class="auth-page">
    <section class="auth-brand" aria-label="亲健">
      <span class="brand-logo-wrap">
        <img src="/qinjian-logo.jpg" alt="亲健 logo" class="brand-logo" />
      </span>
      <div>
        <h1>亲健</h1>
        <p>先看见，再靠近</p>
      </div>
    </section>

    <section class="auth-card" aria-labelledby="auth-title">
      <p class="eyebrow">{{ modeLabel }}</p>
      <h2 id="auth-title">{{ titleText }}</h2>

      <div v-if="mode !== 'reset'" class="segmented auth-tabs" role="tablist" aria-label="账号入口">
        <button type="button" :class="{ active: mode === 'login' }" @click="switchMode('login')">登录</button>
        <button type="button" :class="{ active: mode === 'register' }" @click="switchMode('register')">注册</button>
      </div>

      <form class="form-stack" @submit.prevent="handleSubmit">
        <label v-if="mode === 'register'" class="field">
          <span>昵称</span>
          <input
            v-model.trim="form.nickname"
            class="input"
            type="text"
            autocomplete="nickname"
            placeholder="希望被怎么称呼"
          />
        </label>

        <template v-if="mode !== 'reset'">
          <label class="field">
            <span>账号</span>
            <input
              v-model.trim="form.account"
              class="input"
              type="text"
              autocomplete="username"
              inputmode="email"
              placeholder="请输入手机号或邮箱"
              required
            />
          </label>

          <label class="field">
            <span>密码</span>
            <input
              v-model="form.password"
              class="input"
              type="password"
              autocomplete="current-password"
              placeholder="请输入密码"
              minlength="6"
              required
            />
          </label>

          <div class="auth-options">
            <label class="checkline">
              <input v-model="rememberAccount" type="checkbox" />
              <span>记住账号</span>
            </label>
            <button type="button" class="text-button" @click="switchMode('reset')">忘记密码</button>
          </div>
        </template>

        <template v-else>
          <label class="field">
            <span>手机号</span>
            <input
              v-model.trim="form.phone"
              class="input"
              type="tel"
              inputmode="numeric"
              maxlength="11"
              autocomplete="tel"
              placeholder="已绑定的手机号"
              required
            />
          </label>

          <div class="field">
            <span>验证码</span>
            <div class="code-row">
              <input
                v-model.trim="form.code"
                class="input"
                type="text"
                inputmode="numeric"
                maxlength="6"
                autocomplete="one-time-code"
                placeholder="6 位验证码"
                required
              />
              <button type="button" class="code-button" :disabled="cooldown > 0" @click="sendCode">
                {{ cooldown > 0 ? `${cooldown}s` : '获取验证码' }}
              </button>
            </div>
          </div>

          <label class="field">
            <span>新密码</span>
            <input
              v-model="form.newPassword"
              class="input"
              type="password"
              autocomplete="new-password"
              placeholder="至少 6 位"
              minlength="6"
              required
            />
          </label>
        </template>

        <div class="agreement-row">
          <label class="checkline">
            <input v-model="agreementAccepted" type="checkbox" />
            <span>我已阅读并同意</span>
          </label>
          <div class="legal-links" aria-label="协议文档">
            <button
              v-for="doc in legalDocs"
              :key="doc.id"
              type="button"
              class="legal-link"
              @click="showLegal(doc)"
            >
              {{ doc.title }}
            </button>
          </div>
        </div>

        <button type="submit" class="primary-submit" :disabled="submitting">
          {{ submitting ? '处理中...' : submitText }}
        </button>

        <button v-if="mode !== 'reset'" type="button" class="demo-button" @click="enterDemo">
          进入体验样例
        </button>
        <button v-else type="button" class="demo-button" @click="switchMode('login')">
          返回登录
        </button>
      </form>
    </section>

    <Teleport to="body">
      <div v-if="activeLegalDoc" class="legal-overlay" @click.self="closeLegal">
        <section
          class="legal-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="legal-dialog-title"
        >
          <header class="legal-dialog__head">
            <div>
              <p class="eyebrow">使用前请阅读</p>
              <h3 id="legal-dialog-title">{{ activeLegalDoc.title }}</h3>
            </div>
            <button type="button" class="legal-dialog__close" aria-label="关闭协议" @click="closeLegal">×</button>
          </header>
          <p class="legal-dialog__intro">{{ LOGIN_LEGAL_NOTICE.intro }}</p>
          <div class="legal-dialog__body">
            <section v-for="section in activeLegalDoc.sections" :key="section.heading" class="legal-section">
              <h4>{{ section.heading }}</h4>
              <ul>
                <li v-for="item in section.items" :key="item">{{ item }}</li>
              </ul>
            </section>
          </div>
          <footer class="legal-dialog__foot">
            <button type="button" class="primary-submit" @click="closeLegal">读完了</button>
          </footer>
        </section>
      </div>
    </Teleport>
  </main>
</template>

<script setup>
import { computed, inject, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import { useUserStore } from '@/stores/user'
import {
  AGREEMENT_BLOCK_MESSAGE,
  LOGIN_LEGAL_NOTICE,
  canEnterService,
} from '@/utils/complianceAgreement'

const router = useRouter()
const userStore = useUserStore()
const injectedToast = inject('showToast', null)

const mode = ref('login')
const rememberAccount = ref(false)
const agreementAccepted = ref(false)
const submitting = ref(false)
const cooldown = ref(0)
const activeLegalDoc = ref(null)

const form = reactive({
  account: '',
  password: '',
  nickname: '',
  phone: '',
  code: '',
  newPassword: '',
})

const legalDocs = LOGIN_LEGAL_NOTICE.documents

const modeLabel = computed(() => {
  if (mode.value === 'register') return '注册'
  if (mode.value === 'reset') return '找回密码'
  return '登录'
})
const titleText = computed(() => {
  if (mode.value === 'register') return '创建新的记录'
  if (mode.value === 'reset') return '重新设置密码'
  return '继续你的记录'
})
const submitText = computed(() => {
  if (mode.value === 'register') return '注册'
  if (mode.value === 'reset') return '重设密码'
  return '登录'
})

onMounted(() => {
  const savedAccount = localStorage.getItem('qj_saved_account') || ''
  if (savedAccount) {
    form.account = savedAccount
    rememberAccount.value = true
  }
})

function toast(message) {
  if (typeof injectedToast === 'function') {
    injectedToast(message)
    return
  }
  window.alert(message)
}

function switchMode(nextMode) {
  mode.value = nextMode
}

function normalizeAccount(value) {
  return String(value || '').trim()
}

function persistLoginPreference() {
  if (rememberAccount.value && form.account) {
    localStorage.setItem('qj_saved_account', form.account)
  } else {
    localStorage.removeItem('qj_saved_account')
  }
}

function validateAgreement() {
  const result = canEnterService(agreementAccepted.value)
  if (!result.allowed) {
    toast(result.message || AGREEMENT_BLOCK_MESSAGE)
    return false
  }
  return true
}

async function handleSubmit() {
  if (!validateAgreement()) return

  submitting.value = true
  try {
    if (mode.value === 'reset') {
      if (!/^1\d{10}$/.test(form.phone)) {
        toast('请输入正确的手机号')
        return
      }
      if (!/^\d{6}$/.test(form.code)) {
        toast('请输入 6 位验证码')
        return
      }
      await api.resetPasswordByPhone(form.phone, form.code, form.newPassword)
      toast('密码已重设，请重新登录')
      mode.value = 'login'
      return
    }

    form.account = normalizeAccount(form.account)
    if (!form.account || !form.password) {
      toast('请填写账号和密码')
      return
    }
    if (mode.value === 'register' && !form.nickname) {
      toast('请填写昵称')
      return
    }

    if (mode.value === 'register') {
      await userStore.register(form.account, form.nickname, form.password)
    } else {
      await userStore.login(form.account, form.password)
    }
    persistLoginPreference()
    toast('登录成功，欢迎回来')
    router.push('/')
  } catch (error) {
    toast(error.message || '操作失败，请稍后再试')
  } finally {
    submitting.value = false
  }
}

async function sendCode() {
  if (!/^1\d{10}$/.test(form.phone)) {
    toast('请输入正确的手机号')
    return
  }
  try {
    const res = await api.sendPhoneCode(form.phone)
    toast(res.debug_code ? `验证码已发送：${res.debug_code}` : '验证码已发送，请查收')
    cooldown.value = 60
    const timer = window.setInterval(() => {
      cooldown.value -= 1
      if (cooldown.value <= 0) window.clearInterval(timer)
    }, 1000)
  } catch (error) {
    toast(error.message || '发送失败，请稍后再试')
  }
}

function showLegal(doc) {
  activeLegalDoc.value = doc
}

function closeLegal() {
  activeLegalDoc.value = null
}

function enterDemo() {
  if (!validateAgreement()) return
  userStore.enterDemo()
  toast('已进入体验样例')
  router.push('/')
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  min-height: 100dvh;
  position: relative;
  display: grid;
  grid-template-columns: minmax(320px, 1fr) 410px;
  align-items: center;
  gap: 148px;
  width: min(980px, calc(100% - 56px));
  margin: 0 auto;
  padding: 88px 0;
}

.auth-brand {
  display: flex;
  align-items: center;
  justify-self: start;
  gap: 18px;
  transform: translateY(108px);
}

.brand-logo-wrap {
  width: 72px;
  height: 72px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(215, 104, 72, 0.36);
  border-radius: 50%;
  background: rgba(255, 253, 250, 0.78);
  box-shadow: 0 16px 38px rgba(94, 62, 43, 0.12);
}

.brand-logo {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  object-fit: cover;
}

.auth-brand h1 {
  color: var(--seal-deep);
  font-family: var(--font-serif);
  font-size: 40px;
  line-height: 1.05;
  font-weight: 800;
}

.auth-brand p {
  margin-top: 8px;
  color: #5d6870;
  font-size: 16px;
  font-weight: 700;
}

.auth-card {
  min-height: 576px;
  align-self: center;
  padding: 40px 24px 34px;
  border: 1px solid rgba(68, 52, 40, 0.18);
  border-radius: 8px;
  background: rgba(255, 253, 250, 0.72);
  box-shadow: 0 26px 64px rgba(74, 52, 36, 0.12);
  backdrop-filter: blur(18px);
}

.eyebrow {
  margin-bottom: 8px;
  color: #5f696d;
  font-size: 12px;
  font-weight: 600;
}

.auth-card h2 {
  margin-bottom: 24px;
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 25px;
  line-height: 1.25;
  font-weight: 800;
}

.auth-tabs {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  height: 44px;
  margin-bottom: 14px;
  padding: 4px;
  border: 1px solid rgba(68, 52, 40, 0.18);
  border-radius: 8px;
  background: rgba(245, 238, 231, 0.74);
}

.auth-tabs button {
  border-radius: 7px;
  color: #4e5659;
  font-size: 14px;
  font-weight: 800;
}

.auth-tabs button.active {
  color: var(--ink);
  background: rgba(255, 253, 250, 0.82);
  box-shadow: 0 8px 18px rgba(74, 52, 36, 0.08);
}

.form-stack {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field {
  display: grid;
  gap: 8px;
}

.field span,
.checkline span {
  color: #4f5b60;
  font-size: 13px;
  font-weight: 700;
}

.input {
  width: 100%;
  height: 44px;
  padding: 0 12px;
  border: 1px solid rgba(68, 52, 40, 0.18);
  border-radius: 8px;
  background: rgba(246, 240, 234, 0.78);
  color: var(--ink);
  font-size: 14px;
}

.input::placeholder {
  color: rgba(80, 88, 92, 0.58);
}

.input:focus {
  border-color: rgba(181, 83, 56, 0.54);
  background: rgba(255, 253, 250, 0.9);
  box-shadow: 0 0 0 3px rgba(215, 104, 72, 0.12);
}

.auth-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 2px;
}

.checkline {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.checkline input {
  width: 13px;
  height: 13px;
  accent-color: var(--seal);
}

.text-button,
.legal-link {
  color: var(--seal-deep);
  font-size: 13px;
  font-weight: 800;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.code-row {
  display: grid;
  grid-template-columns: 1fr 104px;
  gap: 8px;
}

.code-button {
  height: 44px;
  border: 1px solid rgba(68, 52, 40, 0.18);
  border-radius: 8px;
  background: rgba(255, 253, 250, 0.78);
  color: var(--seal-deep);
  font-size: 13px;
  font-weight: 800;
}

.agreement-row {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 8px 10px;
  align-items: start;
}

.agreement-row .checkline {
  margin-top: 1px;
}

.legal-links {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  justify-content: flex-start;
}

.primary-submit {
  height: 46px;
  margin-top: 8px;
  border-radius: 8px;
  background: var(--seal);
  color: #fffdfa;
  font-size: 15px;
  font-weight: 800;
  box-shadow: 0 14px 24px rgba(181, 83, 56, 0.18);
  transition: transform 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}

.primary-submit:hover:not(:disabled) {
  transform: translateY(-1px);
  background: var(--seal-deep);
  box-shadow: 0 18px 28px rgba(181, 83, 56, 0.22);
}

.demo-button {
  align-self: center;
  min-height: 30px;
  padding: 0 16px;
  color: #4f5b60;
  font-size: 13px;
  font-weight: 800;
}

.legal-overlay {
  position: fixed;
  inset: 0;
  z-index: 300;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(37, 40, 33, 0.42);
  backdrop-filter: blur(8px);
}

.legal-dialog {
  width: min(720px, 100%);
  max-height: min(82vh, 760px);
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  gap: 14px;
  overflow: hidden;
  padding: 22px;
  border: 1px solid var(--border-strong);
  border-radius: 24px;
  background: var(--paper-soft);
  box-shadow: var(--shadow-lg);
}

.legal-dialog__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.legal-dialog__head h3 {
  margin-top: 5px;
  color: var(--ink);
  font-size: 21px;
}

.legal-dialog__close {
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  border: 1px solid var(--border-strong);
  border-radius: 50%;
  background: rgba(255, 253, 250, 0.82);
  color: var(--ink-soft);
  font-size: 22px;
  line-height: 1;
}

.legal-dialog__intro {
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.7;
}

.legal-dialog__body {
  display: grid;
  gap: 20px;
  overflow-y: auto;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 16px;
  background: rgba(255, 253, 250, 0.7);
}

.legal-section h4 {
  margin-bottom: 8px;
  color: var(--ink);
  font-size: 15px;
}

.legal-section ul {
  display: grid;
  gap: 8px;
  padding-left: 20px;
  color: var(--ink-soft);
  font-size: 13px;
  line-height: 1.75;
}

.legal-dialog__foot {
  display: flex;
  justify-content: flex-end;
}

.legal-dialog__foot .primary-submit {
  width: 120px;
  margin-top: 0;
}

@media (max-width: 900px) {
  .auth-page {
    grid-template-columns: 1fr;
    gap: 32px;
    width: min(430px, calc(100% - 32px));
    padding: 42px 0;
  }

  .auth-brand {
    justify-self: center;
    transform: none;
  }

  .auth-card {
    min-height: auto;
  }

  .legal-overlay {
    padding: 12px;
  }

  .legal-dialog {
    max-height: 90vh;
    padding: 18px;
  }
}
</style>
