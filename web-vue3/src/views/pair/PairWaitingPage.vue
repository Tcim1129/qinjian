<template>
  <div class="waiting-page">
    <div class="card card-accent" style="max-width:420px;margin:60px auto;text-align:center;">
      <p class="eyebrow">等待加入</p>
      <h2 style="font-family:var(--font-serif);font-size:22px;margin-bottom:16px;">关系已创建，等待对方加入</h2>
      <div class="invite-code">{{ userStore.currentPair?.invite_code || '------' }}</div>
      <p style="font-size:14px;color:var(--ink-soft);margin:16px 0;">
        把这个邀请码发给对方，对方输入后会自动进入你们的共享空间。
      </p>
      <div class="hero-actions" style="justify-content:center;">
        <button class="btn btn-secondary" @click="copyCode">复制邀请码</button>
        <button class="btn btn-ghost" @click="$router.push('/')">刷新状态</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { inject } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const showToast = inject('showToast')

async function copyCode() {
  const code = userStore.currentPair?.invite_code
  if (!code) return
  try {
    await navigator.clipboard.writeText(code)
    showToast('邀请码已复制')
  } catch {
    showToast('复制失败，请手动复制')
  }
}
</script>

<style scoped>
.invite-code {
  font-size: 36px;
  font-weight: 700;
  font-family: var(--font-serif);
  letter-spacing: 0.15em;
  color: var(--warm-600);
  padding: 20px;
  background: var(--warm-50);
  border-radius: var(--radius-lg);
  border: 2px dashed var(--warm-300);
}
</style>
