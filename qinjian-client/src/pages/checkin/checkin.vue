<template>
  <view class="checkin-page">
    <!-- 顶部状态栏与标题 -->
    <view class="header-card">
      <view class="header-top">
        <text class="page-title">今日记录</text>
        <text class="date-badge">{{ todayDate }}</text>
      </view>
      <text class="page-sub">真实写下此刻的发生与触动，系统将为您生成双人共鸣简报</text>
    </view>

    <!-- 记录模式切换：写下来 / 边说边整理 -->
    <view class="segmented-mode">
      <view
        :class="['mode-item', mode === 'write' ? 'active' : '']"
        @click="mode = 'write'"
      >
        <text class="mode-text">✍️ 文字记录</text>
      </view>
      <view
        :class="['mode-item', mode === 'voice' ? 'active' : '']"
        @click="mode = 'voice'"
      >
        <text class="mode-text">🎙️ 语音速记</text>
      </view>
    </view>

    <!-- 文字模式 -->
    <view v-if="mode === 'write'" class="form-container">
      <!-- 记录内容输入区 -->
      <view class="input-card">
        <text class="card-label">今天发生了什么？</text>
        <textarea
          v-model="content"
          placeholder="记录今天和TA的交流、微小感受，或者想表达的心理话..."
          placeholder-class="placeholder-text"
          class="content-textarea"
          :maxlength="2000"
        />
        <text class="word-counter">{{ content.length }}/2000</text>
      </view>

      <!-- 情绪标签选择 -->
      <view class="input-card">
        <text class="card-label">当时的情绪底色</text>
        <view class="tag-cloud">
          <view
            v-for="emotion in emotionOptions"
            :key="emotion"
            :class="['emotion-chip', selectedEmotions.includes(emotion) ? 'selected' : '']"
            @click="toggleEmotion(emotion)"
          >
            <text class="chip-text">{{ emotion }}</text>
          </view>
        </view>
      </view>

      <!-- 整体心境打分 (对齐后端 1-4 分规范) -->
      <view class="input-card">
        <view class="score-header">
          <text class="card-label">整体感受打分</text>
          <text class="score-badge">{{ scoreLabels[moodScore - 1] }} ({{ moodScore }}级)</text>
        </view>
        <view class="score-selector">
          <view
            v-for="score in [1, 2, 3, 4]"
            :key="score"
            :class="['score-btn', moodScore === score ? 'active' : '']"
            @click="moodScore = score"
          >
            <text class="score-emoji">{{ scoreEmojis[score - 1] }}</text>
            <text class="score-name">{{ scoreLabels[score - 1] }}</text>
          </view>
        </view>
      </view>

      <!-- 照片与多媒体附件 (极简体验，告别大红叉) -->
      <view class="input-card">
        <view class="media-header">
          <text class="card-label">照片记录 (可选)</text>
          <text class="media-tip">最多添加 3 张生活瞬间</text>
        </view>

        <view class="photos-grid">
          <!-- 已选照片预览卡片 -->
          <view
            v-for="(img, idx) in images"
            :key="idx"
            class="photo-preview-item"
          >
            <image :src="img" class="photo-img" mode="aspectFill" @click="previewPhoto(idx)" />
            <!-- 温润优雅的半透明墨色删除键，绝无大红叉 -->
            <view class="photo-delete-btn" @click.stop="removeImage(idx)">
              <text class="delete-icon">×</text>
            </view>
          </view>

          <!-- 添加照片按钮 -->
          <view v-if="images.length < 3" class="add-photo-box" @click="choosePhoto">
            <text class="add-plus">📷</text>
            <text class="add-text">添加照片</text>
          </view>
        </view>
      </view>

      <!-- 提交记录按钮 -->
      <button
        class="submit-checkin-btn"
        :disabled="submitting || !content.trim()"
        @click="submitCheckin"
      >
        {{ submitting ? '沉淀中...' : '提交今日记录' }}
      </button>
    </view>

    <!-- 语音速记模式 -->
    <view v-else class="voice-container">
      <view class="voice-card">
        <text class="voice-guide">长按或点击开启语音，亲健 AI 助手将为您整理成结构化感受</text>

        <view
          :class="['record-circle', isRecording ? 'pulsing' : '']"
          @click="toggleRecord"
        >
          <text class="mic-icon">{{ isRecording ? '⏹' : '🎙️' }}</text>
          <text class="record-state-text">{{ isRecording ? '录音中，点击停止' : '点击开始倾诉' }}</text>
        </view>

        <text v-if="recordDuration > 0" class="record-time">
          {{ formatDuration(recordDuration) }}
        </text>
      </view>

      <!-- 转写模拟展示 -->
      <view v-if="voiceTranscript" class="transcript-card">
        <text class="transcript-title">AI 已为您整理</text>
        <text class="transcript-body">{{ voiceTranscript }}</text>
        <button class="use-transcript-btn" @click="useTranscript">
          填入文字记录
        </button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed } from 'vue'
import { post } from '@/utils/request'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const mode = ref('write')
const content = ref('')
const selectedEmotions = ref([])
const moodScore = ref(3) // 1=低落, 2=平缓, 3=温和, 4=欣喜 (后端 1-4 规范)
const images = ref([])
const submitting = ref(false)

// 语音状态
const isRecording = ref(false)
const recordDuration = ref(0)
const voiceTranscript = ref('')
let recordTimer = null

const emotionOptions = [
  '欣慰', '平静', '温暖', '感动', '雀跃',
  '疲惫', '委屈', '失落', '焦虑', '迷茫'
]

const scoreLabels = ['低落', '平缓', '温和', '欣喜']
const scoreEmojis = ['🌧️', '☁️', '🌤️', '☀️']

const todayDate = computed(() => {
  const now = new Date()
  const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return `${now.getMonth() + 1}月${now.getDate()}日 ${days[now.getDay()]}`
})

function toggleEmotion(emotion) {
  const idx = selectedEmotions.value.indexOf(emotion)
  if (idx > -1) {
    selectedEmotions.value.splice(idx, 1)
  } else {
    selectedEmotions.value.push(emotion)
  }
}

// 选择与压缩照片 (极简、轻量、不卡顿)
function choosePhoto() {
  uni.chooseImage({
    count: 3 - images.value.length,
    sizeType: ['compressed'],
    sourceType: ['album', 'camera'],
    success: (res) => {
      images.value.push(...res.tempFilePaths)
      uni.showToast({ title: '照片已添加', icon: 'none' })
    },
    fail: () => {
      // 用户取消选择
    }
  })
}

function removeImage(idx) {
  images.value.splice(idx, 1)
}

function previewPhoto(currentIdx) {
  uni.previewImage({
    current: currentIdx,
    urls: images.value
  })
}

// 语音录制模拟
function toggleRecord() {
  if (isRecording.value) {
    isRecording.value = false
    clearInterval(recordTimer)
    voiceTranscript.value = '今天下班路上买了他爱吃的板栗，虽然外面挺冷，但坐在一起热气腾腾地聊天，觉得这一天的辛苦都值了。'
  } else {
    isRecording.value = true
    recordDuration.value = 0
    recordTimer = setInterval(() => {
      recordDuration.value++
    }, 1000)
  }
}

function formatDuration(sec) {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function useTranscript() {
  content.value = voiceTranscript.value
  mode.value = 'write'
  uni.showToast({ title: '已同步至记录内容', icon: 'none' })
}

// 提交打卡 (字段严格契合后端 CheckinRequest 规范)
async function submitCheckin() {
  if (!content.value.trim()) {
    uni.showToast({ title: '请写下今日感受', icon: 'none' })
    return
  }

  submitting.value = true

  // 1. 如果在 Demo 模式下，直接模拟成功闭环
  if (userStore.isDemoMode) {
    setTimeout(() => {
      submitting.value = false
      uni.showToast({ title: '记录沉淀成功', icon: 'success' })
      content.value = ''
      selectedEmotions.value = []
      images.value = []
      setTimeout(() => {
        uni.switchTab({ url: '/pages/report/report' })
      }, 600)
    }, 400)
    return
  }

  // 2. 真实网络提交
  try {
    const payload = {
      pair_id: userStore.currentPair?.id || null,
      content: content.value.trim(),
      mood_tags: selectedEmotions.value,
      mood_score: moodScore.value,
      image_url: images.value.length > 0 ? images.value[0] : null
    }

    await post('/api/v1/checkins', payload)
    uni.showToast({ title: '记录已安全沉淀', icon: 'success' })
    content.value = ''
    selectedEmotions.value = []
    images.value = []

    setTimeout(() => {
      uni.switchTab({ url: '/pages/report/report' })
    }, 600)
  } catch (err) {
    uni.showToast({ title: err.message || '提交失败，请重试', icon: 'none' })
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped lang="scss">
@import '@/styles/tokens.scss';

.checkin-page {
  min-height: 100vh;
  padding: 24rpx 32rpx 60rpx;
  box-sizing: border-box;
}

.header-card {
  margin-bottom: 24rpx;
}

.header-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-title {
  font-family: $font-serif;
  font-size: 44rpx;
  font-weight: 800;
  color: $color-ink;
}

.date-badge {
  font-size: 24rpx;
  color: $color-ink-soft;
  background: rgba(255, 253, 250, 0.85);
  border: 1px solid $color-paper-line;
  padding: 6rpx 18rpx;
  border-radius: 20rpx;
}

.page-sub {
  font-size: 24rpx;
  color: $color-ink-faint;
  margin-top: 8rpx;
  display: block;
}

.segmented-mode {
  display: flex;
  background: rgba(245, 238, 231, 0.74);
  border: 1px solid rgba(68, 52, 40, 0.14);
  border-radius: 16rpx;
  padding: 6rpx;
  margin-bottom: 28rpx;
}

.mode-item {
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

    .mode-text {
      color: $color-seal-deep;
      font-weight: 800;
    }
  }
}

.mode-text {
  font-size: 28rpx;
  font-weight: 600;
  color: $color-ink-soft;
}

.form-container {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.input-card {
  background: $color-paper-strong;
  border: 1px solid $color-paper-line-strong;
  border-radius: $radius-lg;
  padding: 28rpx;
  box-shadow: $shadow-sm;
}

.card-label {
  font-family: $font-serif;
  font-size: 28rpx;
  font-weight: 800;
  color: $color-ink;
  display: block;
  margin-bottom: 16rpx;
}

.content-textarea {
  width: 100%;
  min-height: 240rpx;
  background: rgba(246, 240, 234, 0.6);
  border: 1px solid rgba(68, 52, 40, 0.14);
  border-radius: 14rpx;
  padding: 20rpx;
  font-size: 28rpx;
  line-height: 1.6;
  color: $color-ink;
  box-sizing: border-box;

  &:focus {
    background: #fffdfa;
    border-color: rgba(215, 104, 72, 0.4);
  }
}

.placeholder-text {
  color: rgba(91, 102, 108, 0.4);
  font-size: 26rpx;
}

.word-counter {
  display: block;
  text-align: right;
  font-size: 22rpx;
  color: $color-ink-faint;
  margin-top: 10rpx;
}

.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 14rpx;
}

.emotion-chip {
  padding: 10rpx 24rpx;
  border-radius: 30rpx;
  background: rgba(246, 240, 234, 0.7);
  border: 1px solid rgba(68, 52, 40, 0.12);
  transition: all 0.2s ease;

  &.selected {
    background: rgba(215, 104, 72, 0.14);
    border-color: rgba(215, 104, 72, 0.5);

    .chip-text {
      color: $color-seal-deep;
      font-weight: 800;
    }
  }
}

.chip-text {
  font-size: 24rpx;
  color: $color-ink-soft;
}

.score-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.score-badge {
  font-size: 24rpx;
  font-weight: 700;
  color: $color-seal-deep;
  background: rgba(215, 104, 72, 0.12);
  padding: 4rpx 14rpx;
  border-radius: 10rpx;
}

.score-selector {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16rpx;
  margin-top: 10rpx;
}

.score-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 18rpx 0;
  border-radius: 14rpx;
  background: rgba(246, 240, 234, 0.5);
  border: 1px solid transparent;

  &.active {
    background: rgba(255, 253, 250, 0.95);
    border-color: rgba(215, 104, 72, 0.4);
    box-shadow: 0 4rpx 14rpx rgba(74, 52, 36, 0.08);

    .score-name {
      color: $color-seal-deep;
      font-weight: 800;
    }
  }
}

.score-emoji {
  font-size: 36rpx;
  margin-bottom: 6rpx;
}

.score-name {
  font-size: 22rpx;
  color: $color-ink-soft;
}

.media-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

.media-tip {
  font-size: 22rpx;
  color: $color-ink-faint;
}

.photos-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 18rpx;
  margin-top: 10rpx;
}

.photo-preview-item {
  position: relative;
  width: 170rpx;
  height: 170rpx;
  border-radius: 14rpx;
  overflow: hidden;
  border: 1px solid rgba(68, 52, 40, 0.16);
}

.photo-img {
  width: 100%;
  height: 100%;
}

/* 优雅半透明软墨色微小圆标，绝非粗暴的大红叉 */
.photo-delete-btn {
  position: absolute;
  top: 8rpx;
  right: 8rpx;
  width: 40rpx;
  height: 40rpx;
  border-radius: 50%;
  background: rgba(31, 42, 47, 0.65);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;

  &:active {
    background: rgba(215, 104, 72, 0.9);
  }
}

.delete-icon {
  font-size: 28rpx;
  color: #fffdfa;
  line-height: 1;
  font-weight: bold;
}

.add-photo-box {
  width: 170rpx;
  height: 170rpx;
  border-radius: 14rpx;
  border: 2rpx dashed rgba(68, 52, 40, 0.25);
  background: rgba(246, 240, 234, 0.4);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8rpx;

  &:active {
    background: rgba(244, 221, 212, 0.4);
  }
}

.add-plus {
  font-size: 36rpx;
}

.add-text {
  font-size: 22rpx;
  color: $color-ink-faint;
  font-weight: 600;
}

.submit-checkin-btn {
  width: 100%;
  height: 90rpx;
  line-height: 90rpx;
  border-radius: 16rpx;
  background: $color-seal;
  color: #fffdfa;
  font-size: 30rpx;
  font-weight: 800;
  border: none;
  box-shadow: $shadow-seal;
  margin-top: 10rpx;
  letter-spacing: 2rpx;

  &:active {
    background: $color-seal-deep;
  }

  &[disabled] {
    opacity: 0.5;
  }
}

/* 语音速记模式 */
.voice-container {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.voice-card {
  background: $color-paper-strong;
  border: 1px solid $color-paper-line-strong;
  border-radius: $radius-lg;
  padding: 60rpx 32rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  box-shadow: $shadow-sm;
}

.voice-guide {
  font-size: 26rpx;
  color: $color-ink-soft;
  text-align: center;
  margin-bottom: 50rpx;
  line-height: 1.6;
}

.record-circle {
  width: 220rpx;
  height: 220rpx;
  border-radius: 50%;
  background: rgba(215, 104, 72, 0.12);
  border: 2rpx solid rgba(215, 104, 72, 0.4);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10rpx 30rpx rgba(215, 104, 72, 0.15);
  transition: all 0.3s ease;

  &.pulsing {
    background: rgba(215, 104, 72, 0.25);
    transform: scale(1.06);
  }
}

.mic-icon {
  font-size: 56rpx;
  margin-bottom: 8rpx;
}

.record-state-text {
  font-size: 20rpx;
  font-weight: 700;
  color: $color-seal-deep;
}

.record-time {
  font-family: $font-serif;
  font-size: 40rpx;
  font-weight: 800;
  color: $color-seal;
  margin-top: 30rpx;
}

.transcript-card {
  background: $color-paper-strong;
  border: 1px solid $color-paper-line;
  border-radius: $radius-md;
  padding: 28rpx;
  box-shadow: $shadow-sm;
}

.transcript-title {
  font-family: $font-serif;
  font-size: 26rpx;
  font-weight: 700;
  color: $color-ink;
  display: block;
  margin-bottom: 12rpx;
}

.transcript-body {
  font-size: 26rpx;
  color: $color-ink-soft;
  line-height: 1.6;
  background: rgba(246, 240, 234, 0.6);
  padding: 20rpx;
  border-radius: 12rpx;
  display: block;
  margin-bottom: 20rpx;
}

.use-transcript-btn {
  height: 72rpx;
  line-height: 72rpx;
  border-radius: 12rpx;
  background: $color-seal;
  color: #fffdfa;
  font-size: 26rpx;
  font-weight: 700;
  border: none;
}
</style>
