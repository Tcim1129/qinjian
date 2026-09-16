<template>
  <div class="profile-page">
    <div class="page-head">
      <p class="eyebrow">我的</p>
      <h2>个人中心</h2>
    </div>

    <div class="profile-content">
      <div class="profile-identity">
        <input
          ref="avatarInput"
          class="profile-avatar-input"
          type="file"
          accept="image/*"
          @change="handleAvatarChange"
        />
        <button class="profile-avatar-button" type="button" aria-label="更换头像" :disabled="avatarSaving" @click="openAvatarPicker">
          <span class="profile-avatar">
            <img v-if="avatarImage" :src="avatarImage" alt="头像预览" />
            <span v-else>{{ avatarInitial }}</span>
            <span class="profile-avatar-change">{{ avatarSaving ? '上传中...' : '更换头像' }}</span>
          </span>
        </button>
        <h3>{{ displayName }}</h3>
      </div>

      <div>
        <p class="eyebrow" style="margin-left: 12px; margin-bottom: 8px;">关系</p>
        <div class="ios-list-group">
          <div v-if="userStore.currentPair" class="ios-list-item" @click="$router.push('/pair')">
            <div class="ios-item-icon" style="background: linear-gradient(135deg, var(--warm-300), var(--seal));">
              <HeartHandshake :size="18" stroke-width="2.5" />
            </div>
            <div class="ios-item-content">
              <span>关系管理</span>
              <div class="ios-item-value">
                <ChevronRight :size="16" />
              </div>
            </div>
          </div>
          <div v-else class="empty-state-art">
            <div class="art-icon">
              <Heart :size="28" stroke-width="2" />
            </div>
            <p>还没有绑定关系。<br/>可以先邀请对方一起记录，也可以先一个人体验。</p>
            <button class="btn btn-primary btn-sm" style="margin-top: 12px; border-radius: 20px; padding: 0 20px;" @click="$router.push('/pair')">
              <PlusCircle :size="16" /> 建立关系
            </button>
          </div>
        </div>
      </div>

      <div>
        <p class="eyebrow" style="margin-left: 12px; margin-bottom: 8px;">账号</p>
        <div class="ios-list-group">
          <div class="ios-list-item">
            <div class="ios-item-icon" style="background: var(--sand);">
              <User :size="18" stroke-width="2.5" />
            </div>
            <div class="ios-item-content">
              <span>昵称</span>
              <div class="ios-item-value">
                <span>{{ userStore.me?.nickname || '未设置' }}</span>
                <ChevronRight :size="16" />
              </div>
            </div>
          </div>
          <div class="ios-list-item">
            <div class="ios-item-icon" style="background: var(--moss-soft); color: var(--moss-deep);">
              <MapPin :size="18" stroke-width="2.5" />
            </div>
            <div class="ios-item-content">
              <span>生活地区</span>
              <div class="ios-item-value">
                <span>{{ livingRegion }}</span>
                <ChevronRight :size="16" />
              </div>
            </div>
          </div>
          <div class="ios-list-item">
            <div class="ios-item-icon" style="background: var(--moss-soft); color: var(--moss-deep);">
              <Mail :size="18" stroke-width="2.5" />
            </div>
            <div class="ios-item-content">
              <span>邮箱</span>
              <div class="ios-item-value">
                <span>{{ displayEmail }}</span>
                <ChevronRight :size="16" />
              </div>
            </div>
          </div>
          <div class="ios-list-item">
            <div class="ios-item-icon" style="background: var(--moss-soft); color: var(--moss-deep);">
              <Smartphone :size="18" stroke-width="2.5" />
            </div>
            <div class="ios-item-content">
              <span>手机号</span>
              <div class="ios-item-value">
                <span>{{ maskPhone(userStore.me?.phone) }}</span>
                <ChevronRight :size="16" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div>
        <p class="eyebrow" style="margin-left: 12px; margin-bottom: 8px;">偏好</p>
        <div class="glass-card profile-preferences">
          <div class="profile-preferences__head">
            <h3>回复方式</h3>
            <button class="btn btn-primary btn-sm" type="button" :disabled="savingPreferences" @click="savePreferences">
              {{ savingPreferences ? '保存中...' : '保存设置' }}
            </button>
          </div>
          <div class="profile-preferences__grid">
            <label class="field">
              <span>你希望亲健用什么态度回复你?</span>
              <select v-model="replyTone" class="input">
                <option value="gentle">温柔耐心一点，多给我一点安慰</option>
                <option value="direct">直接一点，先告诉我下一步</option>
                <option value="warm">先共情，再给具体建议</option>
              </select>
            </label>
            <label class="field">
              <span>回答需要多详细?</span>
              <select v-model="detailLevel" class="input">
                <option value="medium">长短适中</option>
                <option value="short">短一点，只要重点</option>
                <option value="long">详细一点，帮我拆清楚</option>
              </select>
            </label>
            <label class="field">
              <span>默认每天安排几件事?</span>
              <input v-model.number="dailyTaskCount" class="input" type="number" min="3" max="8" />
            </label>
            <label class="field">
              <span>晚上提醒我看明天安排</span>
              <select v-model="eveningReminder" class="input">
                <option value="on">开启</option>
                <option value="off">关闭</option>
              </select>
            </label>
            <label class="field">
              <span>默认提醒时间</span>
              <input v-model="reminderTime" class="input" type="time" />
            </label>
          </div>
        </div>

        <!-- 相处习惯与避雷画像 -->
        <div class="glass-card profile-preferences" style="margin-top: 14px;">
          <div class="profile-preferences__head">
            <div>
              <h3>相处习惯与避雷画像</h3>
              <p class="field-hint" style="margin: 4px 0 0; font-size: 12px; color: var(--ink-soft);">
                写下偏好，回复会更贴近你的习惯。
              </p>
            </div>
            <button class="btn btn-primary btn-sm" type="button" :disabled="savingPreferences" @click="savePreferences">
              {{ savingPreferences ? '保存中...' : '保存习惯' }}
            </button>
          </div>

          <div class="habit-section">
            <div class="habit-subtitle">
              <span class="habit-badge habit-badge--danger">不喜欢的说法</span>
              <span class="habit-counter">{{ taboos.length }}/12</span>
            </div>

            <!-- 已选雷点 Chips -->
            <div class="habit-chips-wrap">
              <span v-for="tag in taboos" :key="tag" class="habit-chip habit-chip--danger">
                {{ tag }}
                <button type="button" class="habit-chip__remove" aria-label="删除雷点" @click.stop="removeTaboo(tag)">×</button>
              </span>
              <span v-if="taboos.length === 0" class="habit-empty-hint">暂未添加雷点，点击下方快捷预设或手动添加</span>
            </div>

            <!-- 自定义雷点输入 -->
            <div class="habit-custom-input-row">
              <input
                v-model="newTabooInput"
                class="input habit-input"
                type="text"
                placeholder="输入你的雷点（如：讨厌冷战逼问）"
                maxlength="24"
                @keyup.enter="addCustomTaboo"
              />
              <button class="btn btn-secondary btn-sm" type="button" @click="addCustomTaboo">
                + 添加
              </button>
            </div>

            <!-- 快捷预设雷点 -->
            <div class="habit-presets">
              <span class="habit-presets__label">快速添加：</span>
              <button
                v-for="preset in PRESET_TABOOS"
                :key="preset"
                type="button"
                class="habit-preset-btn"
                :class="{ 'is-active': taboos.includes(preset) }"
                @click="toggleTaboo(preset)"
              >
                {{ taboos.includes(preset) ? '✓ ' : '+ ' }}{{ preset }}
              </button>
            </div>
          </div>

          <div class="habit-divider"></div>

          <div class="habit-section">
            <div class="habit-subtitle">
              <span class="habit-badge habit-badge--comfort">舒适偏好（习惯风格）</span>
              <span class="habit-counter">{{ comfortPreferences.length }}/8</span>
            </div>

            <div class="habit-presets">
              <button
                v-for="preset in PRESET_COMFORTS"
                :key="preset"
                type="button"
                class="habit-preset-btn habit-preset-btn--comfort"
                :class="{ 'is-active': comfortPreferences.includes(preset) }"
                @click="toggleComfort(preset)"
              >
                {{ comfortPreferences.includes(preset) ? '✓ ' : '+ ' }}{{ preset }}
              </button>
            </div>

            <div class="field" style="margin-top: 10px;">
              <span style="font-size: 13px; font-weight: 500; color: var(--ink);">补充说明 / 私人习惯</span>
              <textarea
                v-model="customHabitNotes"
                class="input habit-textarea"
                rows="2"
                placeholder="例如：晚上加班回家后需要先放空20分钟，不想立刻谈复杂事情..."
                maxlength="150"
              ></textarea>
            </div>
          </div>
        </div>
      </div>

      <div>
        <div class="ios-list-group">
          <div class="ios-list-item" @click="$router.push('/privacy-security')">
            <div class="ios-item-icon" style="background: var(--sage); color: var(--ink-reverse);">
              <Shield :size="18" stroke-width="2.5" />
            </div>
            <div class="ios-item-content">
              <span>隐私与安全</span>
              <div class="ios-item-value">
                <ChevronRight :size="16" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="ios-list-group" style="margin-top: 10px;">
        <div class="ios-list-item" style="justify-content: center; background: rgba(185, 61, 50, 0.05);" @click="handleLogout">
          <div class="ios-item-content" style="justify-content: center; gap: 8px;">
            <LogOut :size="18" style="color: var(--danger)" stroke-width="2.5" />
            <span style="color: var(--danger); font-weight: 600;">退出登录</span>
          </div>
        </div>
      </div>

      <button class="profile-cancel" type="button" disabled>注销账号</button>

    </div>
  </div>
</template>

<script setup>
import { computed, inject, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import { useUserStore } from '@/stores/user'
import { HeartHandshake, User, Smartphone, Mail, Shield, LogOut, ChevronRight, Heart, PlusCircle, MapPin } from 'lucide-vue-next'

const router = useRouter()
const userStore = useUserStore()
const showToast = inject('showToast', () => {})
const replyTone = ref('gentle')
const detailLevel = ref('medium')
const dailyTaskCount = ref(5)
const eveningReminder = ref('on')
const reminderTime = ref('21:00')
const avatarInput = ref(null)
const avatarPreview = ref('')
const savingPreferences = ref(false)
const avatarSaving = ref(false)

const displayName = computed(() => userStore.me?.nickname || '亲健用户')
const avatarInitial = computed(() => displayName.value.slice(0, 1) || '用')
const avatarImage = computed(() => avatarPreview.value || userStore.me?.avatar_url || '')
const displayEmail = computed(() => {
  const email = String(userStore.me?.email || '').trim()
  if (!email || email.endsWith('@qinjian.local')) return '未绑定'
  return email
})
const livingRegion = computed(() => userStore.me?.living_region || '未设置')

watch(
  () => userStore.me,
  (profile) => {
    if (!profile) return
    const defaults = profile.task_planner_defaults || {}
    replyTone.value = profile.tone_preference || 'gentle'
    detailLevel.value = profile.response_length || 'medium'
    dailyTaskCount.value = Number(defaults.daily_ai_task_count || 5)
    eveningReminder.value = defaults.reminder_enabled === false ? 'off' : 'on'
    reminderTime.value = defaults.reminder_time || '21:00'
    const habit = profile.habit_profile || {}
    taboos.value = Array.isArray(habit.taboos) ? [...habit.taboos] : []
    comfortPreferences.value = Array.isArray(habit.comfort_preferences) ? [...habit.comfort_preferences] : []
    customHabitNotes.value = habit.custom_notes || ''
  },
  { immediate: true },
)

function maskPhone(phone) {
  if (!phone) return '未绑定'
  return String(phone).replace(/^(\d{3})\d+(\d{4})$/, '$1****$2')
}

async function savePreferences() {
  const payload = {
    tone_preference: replyTone.value,
    response_length: detailLevel.value,
    task_planner_defaults: {
      daily_ai_task_count: Math.min(8, Math.max(3, Number(dailyTaskCount.value || 5))),
      reminder_enabled: eveningReminder.value === 'on',
      reminder_time: reminderTime.value || '21:00',
    },
    habit_profile: {
      taboos: taboos.value,
      comfort_preferences: comfortPreferences.value,
      custom_notes: customHabitNotes.value.trim(),
    },
  }

  savingPreferences.value = true
  try {
    if (userStore.isDemoMode) {
      userStore.me = {
        ...(userStore.me || {}),
        ...payload,
      }
      showToast('样例设置已更新，本次体验内有效')
    } else {
      await userStore.updateMe(payload)
      showToast('设置已保存')
    }
  } catch (error) {
    showToast(error.message || '设置没保存上，请稍后再试')
  } finally {
    savingPreferences.value = false
  }
}

function openAvatarPicker() {
  avatarInput.value?.click()
}

async function handleAvatarChange(event) {
  const file = event.target.files?.[0]
  if (!file) return

  if (!String(file.type || '').startsWith('image/')) {
    showToast('请选择图片文件')
    event.target.value = ''
    return
  }

  avatarSaving.value = true
  try {
    avatarPreview.value = await readFileAsDataUrl(file)
    if (userStore.isDemoMode) {
      showToast('样例头像已更新，本次体验内有效')
      return
    }

    const uploaded = await api.uploadFile('image', file)
    if (!uploaded?.url) throw new Error('头像上传结果无效')
    await userStore.updateMe({ avatar_url: uploaded.url })
    avatarPreview.value = ''
    showToast('头像已保存')
  } catch (error) {
    avatarPreview.value = ''
    showToast(error.message || '头像没保存上，请稍后再试')
  } finally {
    avatarSaving.value = false
    event.target.value = ''
  }
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(new Error('图片读取失败'))
    reader.readAsDataURL(file)
  })
}

function handleLogout() {
  userStore.logout()
  showToast('已安全退出')
  router.push('/auth')
}
</script>

<style scoped>
.profile-page {
  width: min(960px, calc(100% - 40px));
  margin: 0 auto;
  padding-bottom: 36px;
}

.profile-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-bottom: 30px;
}

.profile-identity {
  text-align: center;
  padding: 10px 0 18px;
}

.profile-avatar-input {
  display: none;
}

.profile-avatar-button {
  border: 0;
  padding: 0;
  background: transparent;
  cursor: pointer;
}

.profile-avatar {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--warm-400), var(--seal-deep));
  color: #fff;
  font-size: 26px;
  font-weight: 700;
  display: grid;
  place-items: center;
  margin: 0 auto;
  box-shadow: 0 8px 24px rgba(134, 58, 43, 0.25);
  border: 2px solid rgba(255, 255, 255, 0.6);
  position: relative;
}

.profile-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: inherit;
}

.profile-identity h3 {
  margin-top: 22px;
  font-size: 20px;
  line-height: 1.25;
  color: var(--ink);
}

.profile-avatar-change {
  position: absolute;
  left: 50%;
  bottom: -12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 64px;
  height: 24px;
  padding: 0 9px;
  border: 1px solid rgba(143, 95, 75, 0.2);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  color: var(--seal-deep);
  box-shadow: 0 5px 16px rgba(134, 58, 43, 0.14);
  transform: translateX(-50%);
  font-size: 11px;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
  pointer-events: none;
}

.ios-item-value {
  gap: 6px;
}

.profile-preferences {
  padding: 18px;
}

.profile-preferences__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.profile-preferences__head h3 {
  font-size: 18px;
  color: var(--ink);
}

.profile-preferences__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.profile-cancel {
  border: 0;
  background: transparent;
  color: rgba(120, 113, 107, 0.42);
  font-size: 14px;
}

@media (max-width: 760px) {
  .profile-page {
    width: min(100% - 24px, 560px);
    padding-bottom: 86px;
  }

  .profile-identity {
    padding-top: 4px;
    padding-bottom: 14px;
  }

  .profile-preferences__grid {
    grid-template-columns: 1fr;
  }
}

/* 习惯画像与避雷清单样式 */
.habit-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 8px;
}

.habit-subtitle {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.habit-badge {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 6px;
}

.habit-badge--danger {
  background: rgba(194, 75, 60, 0.12);
  color: #c24b3c;
}

.habit-badge--comfort {
  background: rgba(77, 114, 176, 0.12);
  color: #4d72b0;
}

.habit-counter {
  font-size: 11px;
  color: var(--ink-soft);
}

.habit-chips-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-height: 28px;
  align-items: center;
}

.habit-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 14px;
  font-weight: 500;
}

.habit-chip--danger {
  background: #faeceb;
  color: #c24b3c;
  border: 1px solid rgba(194, 75, 60, 0.25);
}

.habit-chip__remove {
  border: none;
  background: none;
  color: inherit;
  font-size: 14px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  opacity: 0.7;
}

.habit-chip__remove:hover {
  opacity: 1;
}

.habit-empty-hint {
  font-size: 12px;
  color: var(--ink-muted);
  font-style: italic;
}

.habit-custom-input-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.habit-input {
  flex: 1;
  font-size: 13px;
  padding: 8px 12px;
  border-radius: 8px;
}

.habit-presets {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.habit-presets__label {
  font-size: 11px;
  color: var(--ink-soft);
  margin-right: 2px;
}

.habit-preset-btn {
  border: 1px dashed var(--line);
  background: var(--surface);
  color: var(--ink-soft);
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.habit-preset-btn:hover {
  border-color: var(--seal);
  color: var(--ink);
}

.habit-preset-btn.is-active {
  border-style: solid;
  border-color: #c24b3c;
  background: #faeceb;
  color: #c24b3c;
  font-weight: 500;
}

.habit-preset-btn--comfort.is-active {
  border-color: #4d72b0;
  background: #edf2f9;
  color: #4d72b0;
}

.habit-divider {
  height: 1px;
  background: var(--line-subtle, rgba(0,0,0,0.06));
  margin: 8px 0;
}

.habit-textarea {
  resize: vertical;
  min-height: 52px;
  font-size: 13px;
  line-height: 1.4;
}
</style>
