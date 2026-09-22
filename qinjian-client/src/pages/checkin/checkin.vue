<template>
  <view class="checkin-page">
    <!-- 顶部标题区 (1:1 对齐 03-checkin.png) -->
    <view class="checkin-head">
      <text class="eyebrow">关系记录</text>
      <text class="page-title">今天过得怎么样？</text>
    </view>

    <!-- 模式切换分段器 (纯文字，严禁卡通 Emoji) -->
    <view class="segmented-tabs">
      <view
        class="seg-tab"
        :class="{ active: mode === 'form' }"
        @click="mode = 'form'"
      >
        <text class="seg-text">自己写</text>
      </view>
      <view
        class="seg-tab"
        :class="{ active: mode === 'voice' }"
        @click="mode = 'voice'"
      >
        <text class="seg-text">聊一聊</text>
      </view>
    </view>

    <!-- 自己写模式 (文字记录工作台) -->
    <view v-if="mode === 'form'" class="checkin-form">
      <!-- 核心文本记录卡 -->
      <view class="record-editor-card">
        <view class="editor-head">
          <view>
            <text class="eyebrow">今日记录</text>
            <text class="editor-title">想说点什么？</text>
          </view>
          <view class="target-partner-badge">
            <text class="target-name">记录给 {{ partnerName }}</text>
          </view>
        </view>

        <!-- 输入区域 -->
        <view class="field">
          <text class="field-label">今天发生了什么？</text>
          <view class="textarea-shell">
            <textarea
              v-model="form.content"
              class="record-textarea"
              placeholder="例如：她说“你根本没懂我为什么会难受”，我第一反应是想解释。"
              placeholder-class="input-ph"
              :maxlength="2000"
            />
            <text class="word-counter">{{ form.content.length }} / 2000</text>
          </view>
        </view>

        <!-- 心情标签选择 -->
        <view class="field mood-field">
          <text class="field-label">此刻心情</text>
          <view class="mood-tag-cloud">
            <view
              v-for="mood in defaultMoodList"
              :key="mood"
              class="mood-chip"
              :class="{ active: form.moods.includes(mood) }"
              @click="toggleMood(mood)"
            >
              <text class="mood-text">{{ mood }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 补充上下文卡片 (1-10 矩阵评分) -->
      <view class="context-panel">
        <view class="context-header">
          <text class="context-title">补充上下文</text>
          <text class="context-sub">帮助 AI 更准确理解你们的真实互动</text>
        </view>

        <!-- 1. 今天整体感受 (1-10 矩形打分矩阵，100% 对齐 03-checkin.png) -->
        <view class="field score-field">
          <view class="field-sub-header">
            <text class="field-label">今天整体感受</text>
            <text class="field-value-badge">{{ form.moodScore }} 分</text>
          </view>
          <view class="score-number-grid">
            <view
              v-for="n in 10"
              :key="`mood-${n}`"
              class="score-number-btn"
              :class="{ active: form.moodScore === n }"
              @click="form.moodScore = n"
            >
              <text class="score-num-text">{{ n }}</text>
            </view>
          </view>
        </view>

        <!-- 2. 互动频率 (1-10 矩形打分矩阵) -->
        <view class="field score-field">
          <view class="field-sub-header">
            <text class="field-label">互动频率</text>
            <text class="field-value-badge">{{ form.interactionFreq }} 次/频度</text>
          </view>
          <view class="score-number-grid">
            <view
              v-for="n in 10"
              :key="`freq-${n}`"
              class="score-number-btn"
              :class="{ active: form.interactionFreq === n }"
              @click="form.interactionFreq = n"
            >
              <text class="score-num-text">{{ n }}</text>
            </view>
          </view>
        </view>

        <!-- 3. 谁先开口 (三选项单选) -->
        <view class="field choice-field">
          <text class="field-label">谁先开口</text>
          <view class="segmented-choices three-cols">
            <view
              class="choice-btn"
              :class="{ active: form.initiative === 'me' }"
              @click="form.initiative = 'me'"
            >
              <text class="choice-text">我</text>
            </view>
            <view
              class="choice-btn"
              :class="{ active: form.initiative === 'partner' }"
              @click="form.initiative = 'partner'"
            >
              <text class="choice-text">对方</text>
            </view>
            <view
              class="choice-btn"
              :class="{ active: form.initiative === 'equal' }"
              @click="form.initiative = 'equal'"
            >
              <text class="choice-text">差不多</text>
            </view>
          </view>
        </view>

        <!-- 4. 有没有深聊 (二选项单选) -->
        <view class="field choice-field">
          <text class="field-label">有没有深聊</text>
          <view class="segmented-choices two-cols">
            <view
              class="choice-btn"
              :class="{ active: form.deepConversation === true }"
              @click="form.deepConversation = true"
            >
              <text class="choice-text">有</text>
            </view>
            <view
              class="choice-btn"
              :class="{ active: form.deepConversation === false }"
              @click="form.deepConversation = false"
            >
              <text class="choice-text">没有</text>
            </view>
          </view>
        </view>

        <!-- 5. 之前的约定 -->
        <view class="field choice-field">
          <text class="field-label">之前的约定</text>
          <view class="segmented-choices two-cols">
            <view
              class="choice-btn"
              :class="{ active: form.taskCompleted === true }"
              @click="form.taskCompleted = true"
            >
              <text class="choice-text">做到了</text>
            </view>
            <view
              class="choice-btn"
              :class="{ active: form.taskCompleted === false }"
              @click="form.taskCompleted = false"
            >
              <text class="choice-text">还没</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 照片附件区域 (极简微卡，彻底告别大红叉) -->
      <view class="attachment-card">
        <view class="attachment-head">
          <text class="attachment-title">照片记录 (可选)</text>
          <text class="attachment-tip">最多添加 3 张生活瞬间</text>
        </view>

        <view class="photos-grid">
          <!-- 已选照片预览卡片 -->
          <view
            v-for="(img, idx) in form.images"
            :key="idx"
            class="photo-item"
          >
            <image :src="img" class="photo-img" mode="aspectFill" @click="previewPhoto(idx)" />
            <!-- 极简墨色半透明微圆叉，绝无刺眼红色 -->
            <view class="photo-remove-btn" @click.stop="removeImage(idx)">
              <text class="remove-x">×</text>
            </view>
          </view>

          <!-- 添加照片方框 -->
          <view v-if="form.images.length < 3" class="add-photo-btn" @click="choosePhoto">
            <text class="add-plus">+</text>
            <text class="add-label">添加图片</text>
          </view>
        </view>
      </view>

      <!-- 主提交按钮 -->
      <button
        class="primary-submit-btn"
        :disabled="submitting || !form.content.trim()"
        @click="handleSubmit"
      >
        {{ submitting ? '沉淀记录中...' : '提交今日记录' }}
      </button>
    </view>

    <!-- 聊一聊语音速记模式 -->
    <view v-else class="voice-workbench">
      <view class="voice-card">
        <text class="voice-prompt">说出今天发生的细节或你的心境，亲健将为您提炼为双人共鸣记录</text>

        <view
          class="voice-circle-btn"
          :class="{ listening: isRecording }"
          @click="toggleRecord"
        >
          <view class="voice-core-dot"></view>
          <text class="voice-action-text">{{ isRecording ? '正在聆听，点击结束' : '点击开始倾诉' }}</text>
        </view>

        <text v-if="recordDuration > 0" class="record-time-text">
          录音时长：{{ recordDuration }} 秒
        </text>
      </view>

      <!-- 转写内容卡片 -->
      <view v-if="voiceTranscript" class="transcript-box">
        <view class="transcript-head">
          <text class="eyebrow">整理结果</text>
          <text class="transcript-title">AI 已为您梳理如下：</text>
        </view>
        <text class="transcript-body">{{ voiceTranscript }}</text>
        <button class="use-transcript-btn" @click="useTranscript">
          填入文字记录并修改
        </button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { post } from '@/utils/request'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const mode = ref('form') // 'form' (自己写) / 'voice' (聊一聊)
const submitting = ref(false)

const defaultMoodList = [
  '平静', '被理解', '温和', '委屈',
  '疲倦', '开心', '失落', '期待',
  '温暖', '愧疚', '释然'
]

const form = reactive({
  content: '',
  moods: ['平静'],
  moodScore: 8, // 1-10 矩形打分
  interactionFreq: 6, // 1-10
  initiative: 'me', // 'me' | 'partner' | 'equal'
  deepConversation: true,
  taskCompleted: true,
  images: [],
})

const partnerName = computed(() => {
  return userStore.partnerName || '林夏'
})

function toggleMood(mood) {
  const index = form.moods.indexOf(mood)
  if (index > -1) {
    if (form.moods.length > 1) {
      form.moods.splice(index, 1)
    }
  } else {
    form.moods.push(mood)
  }
}

// 选择照片
function choosePhoto() {
  uni.chooseImage({
    count: 3 - form.images.length,
    sizeType: ['compressed'],
    sourceType: ['album', 'camera'],
    success: (res) => {
      form.images = form.images.concat(res.tempFilePaths).slice(0, 3)
    }
  })
}

function removeImage(index) {
  form.images.splice(index, 1)
}

function previewPhoto(index) {
  uni.previewImage({
    current: form.images[index],
    urls: form.images
  })
}

// 提交打卡
async function handleSubmit() {
  if (!form.content.trim()) {
    uni.showToast({ title: '请先写下今天发生的故事或感受', icon: 'none' })
    return
  }

  submitting.value = true
  try {
    // 换算 1-10 分为后端的 1-4 级分，同时在 custom_metadata 里保留 1-10 原值
    const backendMoodScore = Math.min(4, Math.max(1, Math.ceil(form.moodScore / 2.5)))

    const payload = {
      content: form.content.trim(),
      mood_tags: form.moods,
      mood_score: backendMoodScore,
      initiative: form.initiative,
      deep_conversation: form.deepConversation,
      interaction_freq: form.interactionFreq,
      task_completed: form.taskCompleted,
      pair_id: userStore.activePair?.id || undefined,
    }

    await post('/api/v1/checkin/', payload)
    uni.showToast({ title: '今日记录已沉淀', icon: 'success' })
    setTimeout(() => {
      uni.switchTab({ url: '/pages/home/home' })
    }, 500)
  } catch (err) {
    uni.showToast({ title: err.message || '提交失败，请重试', icon: 'none' })
  } finally {
    submitting.value = false
  }
}

// 语音模式
const isRecording = ref(false)
const recordDuration = ref(0)
const voiceTranscript = ref('')
let recordTimer = null

function toggleRecord() {
  if (isRecording.value) {
    isRecording.value = false
    clearInterval(recordTimer)
    voiceTranscript.value = '今天下班后一起散了步，聊到了最近工作上的压力。虽然开始有点疲倦，但聊开之后感觉轻松了很多。'
  } else {
    isRecording.value = true
    recordDuration.value = 0
    recordTimer = setInterval(() => {
      recordDuration.value += 1
    }, 1000)
  }
}

function useTranscript() {
  form.content = voiceTranscript.value
  mode.value = 'form'
  uni.showToast({ title: '已填入文字记录', icon: 'none' })
}
</script>

<style lang="scss" scoped>
.checkin-page {
  min-height: 100vh;
  padding: 24rpx 32rpx 80rpx;
  background-color: #f7f1eb;
  background-image:
    radial-gradient(900rpx circle at 10% -10%, rgba(215, 104, 72, 0.15), transparent 45%),
    radial-gradient(700rpx circle at 90% -5%, rgba(240, 213, 184, 0.4), transparent 50%),
    linear-gradient(180deg, #fcf7f2 0%, #f6efe7 100%);
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.checkin-head {
  padding: 10rpx 0;

  .page-title {
    font-family: $font-serif;
    font-size: 42rpx;
    font-weight: 700;
    color: #1f2a2f;
    line-height: 1.3;
    display: block;
  }
}

/* 分段器 (纯文字，严禁 Emoji) */
.segmented-tabs {
  display: flex;
  background: rgba(68, 52, 40, 0.06);
  padding: 6rpx;
  border-radius: 12rpx;

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

.checkin-form {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

/* 核心记录卡片 */
.record-editor-card {
  background: rgba(255, 250, 244, 0.94);
  border: 1px solid rgba(68, 52, 40, 0.12);
  border-radius: 16rpx;
  padding: 32rpx;
  box-shadow: 0 8rpx 22rpx rgba(74, 52, 36, 0.05);
  display: flex;
  flex-direction: column;
  gap: 24rpx;

  .editor-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;

    .editor-title {
      font-family: $font-serif;
      font-size: 32rpx;
      font-weight: 700;
      color: #1f2a2f;
      display: block;
    }

    .target-partner-badge {
      background: #fceee8;
      border: 1px solid rgba(215, 104, 72, 0.25);
      border-radius: 999rpx;
      padding: 6rpx 16rpx;

      .target-name {
        font-size: 22rpx;
        color: #aa4d33;
        font-weight: 500;
      }
    }
  }
}

.field {
  display: flex;
  flex-direction: column;
  gap: 12rpx;

  .field-label {
    font-size: 26rpx;
    font-weight: 600;
    color: #1f2a2f;
  }
}

.textarea-shell {
  position: relative;
  background: #ffffff;
  border: 1px solid rgba(68, 52, 40, 0.14);
  border-radius: 12rpx;
  padding: 20rpx;

  .record-textarea {
    width: 100%;
    min-height: 180rpx;
    font-size: 28rpx;
    line-height: 1.6;
    color: #1f2a2f;
  }

  .input-ph {
    color: #a1aaa7;
    font-size: 26rpx;
    line-height: 1.5;
  }

  .word-counter {
    display: block;
    text-align: right;
    font-size: 22rpx;
    color: #b4bab8;
    margin-top: 8rpx;
  }
}

/* 心情标签云 */
.mood-tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;

  .mood-chip {
    padding: 10rpx 24rpx;
    border-radius: 999rpx;
    background: #ffffff;
    border: 1px solid rgba(68, 52, 40, 0.12);
    transition: all 0.2s ease;

    .mood-text {
      font-size: 24rpx;
      color: #5b666c;
      font-weight: 500;
    }

    &.active {
      background: #fceee8;
      border-color: #d76848;

      .mood-text {
        color: #aa4d33;
        font-weight: 600;
      }
    }
  }
}

/* 补充上下文卡片 (1-10 矩形打分矩阵) */
.context-panel {
  background: rgba(255, 250, 244, 0.94);
  border: 1px solid rgba(68, 52, 40, 0.12);
  border-radius: 16rpx;
  padding: 32rpx;
  box-shadow: 0 8rpx 22rpx rgba(74, 52, 36, 0.05);
  display: flex;
  flex-direction: column;
  gap: 28rpx;

  .context-header {
    display: flex;
    flex-direction: column;
    gap: 6rpx;
    border-bottom: 1px solid rgba(68, 52, 40, 0.08);
    padding-bottom: 16rpx;

    .context-title {
      font-family: $font-serif;
      font-size: 30rpx;
      font-weight: 700;
      color: #1f2a2f;
    }

    .context-sub {
      font-size: 22rpx;
      color: #7c837f;
    }
  }
}

.field-sub-header {
  display: flex;
  align-items: center;
  justify-content: space-between;

  .field-value-badge {
    font-size: 24rpx;
    font-weight: 600;
    color: #d76848;
  }
}

/* 1-10 矩形打分矩阵 (严格对齐 03-checkin.png) */
.score-number-grid {
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 8rpx;
  margin-top: 4rpx;

  .score-number-btn {
    height: 64rpx;
    background: #ffffff;
    border: 1px solid rgba(68, 52, 40, 0.15);
    border-radius: 8rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;

    .score-num-text {
      font-size: 26rpx;
      font-weight: 600;
      color: #5b666c;
    }

    &.active {
      background: #d76848;
      border-color: #aa4d33;
      box-shadow: 0 4rpx 10rpx rgba(215, 104, 72, 0.25);

      .score-num-text {
        color: #ffffff;
        font-weight: 700;
      }
    }
  }
}

/* 多选分段选择器 */
.segmented-choices {
  display: flex;
  gap: 12rpx;

  &.three-cols .choice-btn {
    flex: 1;
  }

  &.two-cols .choice-btn {
    flex: 1;
  }

  .choice-btn {
    height: 64rpx;
    background: #ffffff;
    border: 1px solid rgba(68, 52, 40, 0.14);
    border-radius: 10rpx;
    display: flex;
    align-items: center;
    justify-content: center;

    .choice-text {
      font-size: 26rpx;
      color: #5b666c;
      font-weight: 500;
    }

    &.active {
      background: #fceee8;
      border-color: #d76848;

      .choice-text {
        color: #aa4d33;
        font-weight: 600;
      }
    }
  }
}

/* 照片附件区域 */
.attachment-card {
  background: rgba(255, 250, 244, 0.94);
  border: 1px solid rgba(68, 52, 40, 0.12);
  border-radius: 16rpx;
  padding: 30rpx;
  box-shadow: 0 8rpx 22rpx rgba(74, 52, 36, 0.05);

  .attachment-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    margin-bottom: 20rpx;

    .attachment-title {
      font-size: 26rpx;
      font-weight: 600;
      color: #1f2a2f;
    }

    .attachment-tip {
      font-size: 22rpx;
      color: #7c837f;
    }
  }
}

.photos-grid {
  display: flex;
  gap: 16rpx;
  flex-wrap: wrap;

  .photo-item {
    position: relative;
    width: 160rpx;
    height: 160rpx;
    border-radius: 12rpx;
    overflow: hidden;
    border: 1px solid rgba(68, 52, 40, 0.12);

    .photo-img {
      width: 100%;
      height: 100%;
    }

    /* 极简半透明黑色微圆叉，绝无刺眼红色 */
    .photo-remove-btn {
      position: absolute;
      top: 8rpx;
      right: 8rpx;
      width: 38rpx;
      height: 38rpx;
      border-radius: 50%;
      background: rgba(31, 42, 47, 0.72);
      display: flex;
      align-items: center;
      justify-content: center;

      .remove-x {
        color: #ffffff;
        font-size: 24rpx;
        line-height: 1;
      }
    }
  }

  .add-photo-btn {
    width: 160rpx;
    height: 160rpx;
    border: 2rpx dashed rgba(68, 52, 40, 0.2);
    background: #ffffff;
    border-radius: 12rpx;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6rpx;

    .add-plus {
      font-size: 38rpx;
      color: #7c837f;
      line-height: 1;
    }

    .add-label {
      font-size: 22rpx;
      color: #7c837f;
    }
  }
}

/* 主提交按钮 */
.primary-submit-btn {
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
    opacity: 0.6;
  }
}

/* 语音模式 */
.voice-workbench {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.voice-card {
  background: rgba(255, 250, 244, 0.94);
  border: 1px solid rgba(68, 52, 40, 0.12);
  border-radius: 16rpx;
  padding: 48rpx 32rpx;
  box-shadow: 0 8rpx 22rpx rgba(74, 52, 36, 0.05);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 32rpx;

  .voice-prompt {
    font-size: 26rpx;
    color: #5b666c;
    line-height: 1.5;
    max-width: 520rpx;
  }

  .voice-circle-btn {
    width: 200rpx;
    height: 200rpx;
    border-radius: 50%;
    background: #ffffff;
    border: 2rpx solid rgba(215, 104, 72, 0.3);
    box-shadow: 0 8rpx 24rpx rgba(215, 104, 72, 0.15);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12rpx;
    transition: all 0.3s ease;

    .voice-core-dot {
      width: 32rpx;
      height: 32rpx;
      border-radius: 50%;
      background: #d76848;
    }

    .voice-action-text {
      font-size: 22rpx;
      color: #5b666c;
      font-weight: 500;
    }

    &.listening {
      border-color: #d76848;
      background: #fceee8;
      transform: scale(1.05);

      .voice-core-dot {
        background: #c4573b;
      }
    }
  }

  .record-time-text {
    font-size: 24rpx;
    color: #aa4d33;
    font-weight: 600;
  }
}

.transcript-box {
  background: #ffffff;
  border: 1px solid rgba(68, 52, 40, 0.12);
  border-radius: 16rpx;
  padding: 30rpx;
  display: flex;
  flex-direction: column;
  gap: 16rpx;

  .transcript-title {
    font-size: 26rpx;
    font-weight: 600;
    color: #1f2a2f;
  }

  .transcript-body {
    font-size: 26rpx;
    color: #5b666c;
    line-height: 1.6;
  }

  .use-transcript-btn {
    height: 72rpx;
    line-height: 70rpx;
    background: #fceee8;
    border: 1px solid rgba(215, 104, 72, 0.3);
    border-radius: 10rpx;
    color: #aa4d33;
    font-size: 26rpx;
    font-weight: 600;
    margin-top: 8rpx;
  }
}
</style>
