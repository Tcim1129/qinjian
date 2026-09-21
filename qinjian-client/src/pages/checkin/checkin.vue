<template>
  <view class="container">
    <view class="header">
      <text class="title">今日记录</text>
      <text class="date">{{ todayDate }}</text>
    </view>

    <view class="tabs">
      <view :class="['tab', mode === 'write' ? 'active' : '']" @click="mode = 'write'">
        写下来
      </view>
      <view :class="['tab', mode === 'voice' ? 'active' : '']" @click="mode = 'voice'">
        边说边整理
      </view>
    </view>

    <!-- 写下来模式 -->
    <view v-if="mode === 'write'" class="write-mode">
      <view class="section">
        <text class="label">今天发生了什么</text>
        <textarea 
          v-model="content" 
          placeholder="记录今天和TA的互动、感受、或者想说的话..."
          class="textarea"
          :maxlength="2000"
        />
        <text class="char-count">{{ content.length }}/2000</text>
      </view>

      <view class="section">
        <text class="label">情绪标签</text>
        <view class="emotion-tags">
          <view 
            v-for="emotion in emotionOptions" 
            :key="emotion"
            :class="['tag', selectedEmotions.includes(emotion) ? 'selected' : '']"
            @click="toggleEmotion(emotion)"
          >
            {{ emotion }}
          </view>
        </view>
      </view>

      <view class="section">
        <text class="label">整体感受 (1-10分)</text>
        <slider 
          :min="1" 
          :max="10" 
          :value="feelingScore"
          @change="onScoreChange"
          activeColor="#667eea"
          block-size="20"
        />
        <text class="score-text">{{ feelingScore }} 分</text>
      </view>

      <view class="section">
        <text class="label">补充材料</text>
        <view class="upload-area">
          <view class="upload-btn" @click="chooseImage">
            <text>添加图片</text>
          </view>
          <view class="upload-btn" @click="chooseVoice">
            <text>添加语音</text>
          </view>
        </view>
        
        <view v-if="images.length > 0" class="preview-list">
          <view v-for="(img, index) in images" :key="index" class="preview-item">
            <image :src="img" class="preview-img" />
            <view class="delete-btn" @click="removeImage(index)">×</view>
          </view>
        </view>
      </view>

      <button @click="submitCheckin" type="primary" class="submit-btn" :disabled="!content">
        提交记录
      </button>
    </view>

    <!-- 边说边整理模式 -->
    <view v-else class="voice-mode">
      <view class="voice-area">
        <view :class="['voice-btn', isRecording ? 'recording' : '']" @click="toggleRecord">
          <text class="text">{{ isRecording ? '点击停止' : '点击录音' }}</text>
        </view>
        <text v-if="recordDuration > 0" class="duration">{{ formatDuration(recordDuration) }}</text>
      </view>

      <view v-if="voiceTranscript" class="transcript-area">
        <text class="label">语音转写结果</text>
        <view class="transcript-box">
          <text>{{ voiceTranscript }}</text>
        </view>
        <button @click="useTranscript" size="mini" type="primary">使用该内容</button>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { post } from '../../utils/request'

const mode = ref('write')
const content = ref('')
const selectedEmotions = ref([])
const feelingScore = ref(7)
const images = ref([])
const isRecording = ref(false)
const recordDuration = ref(0)
const voiceTranscript = ref('')

const emotionOptions = [
  '开心', '平静', '兴奋', '温暖', '感动',
  '焦虑', '失落', '委屈', '愤怒', '困惑'
]

const todayDate = computed(() => {
  const now = new Date()
  return `${now.getMonth() + 1}月${now.getDate()}日`
})

const toggleEmotion = (emotion) => {
  const index = selectedEmotions.value.indexOf(emotion)
  if (index > -1) {
    selectedEmotions.value.splice(index, 1)
  } else {
    selectedEmotions.value.push(emotion)
  }
}

const onScoreChange = (e) => {
  feelingScore.value = e.detail.value
}

const chooseImage = () => {
  uni.chooseImage({
    count: 3,
    success: (res) => {
      images.value.push(...res.tempFilePaths)
    }
  })
}

const removeImage = (index) => {
  images.value.splice(index, 1)
}

const chooseVoice = () => {
  uni.showToast({
    title: '语音功能开发中',
    icon: 'none'
  })
}

let recordTimer = null
const toggleRecord = () => {
  if (isRecording.value) {
    // 停止录音
    isRecording.value = false
    clearInterval(recordTimer)
    
    // 模拟语音转写
    setTimeout(() => {
      voiceTranscript.value = '今天和TA一起吃了晚饭，聊了很多工作的事情，感觉挺开心的。'
    }, 1000)
  } else {
    // 开始录音
    isRecording.value = true
    recordDuration.value = 0
    recordTimer = setInterval(() => {
      recordDuration.value++
    }, 1000)
  }
}

const formatDuration = (seconds) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

const useTranscript = () => {
  content.value = voiceTranscript.value
  mode.value = 'write'
}

const submitCheckin = async () => {
  if (!content.value) {
    uni.showToast({ title: '请填写记录内容', icon: 'none' })
    return
  }

  uni.showLoading({ title: '提交中...' })
  
  try {
    await post('/api/v1/checkins', {
      content: content.value,
      emotions: selectedEmotions.value,
      feeling_score: feelingScore.value,
      images: images.value
    })
    
    uni.hideLoading()
    uni.showToast({ title: '提交成功', icon: 'success' })
    
    // 清空表单
    content.value = ''
    selectedEmotions.value = []
    feelingScore.value = 7
    images.value = []
    
    // 跳转到简报页
    setTimeout(() => {
      uni.switchTab({ url: '/pages/report/report' })
    }, 1500)
    
  } catch (error) {
    uni.hideLoading()
    uni.showToast({ title: '提交失败', icon: 'none' })
  }
}
</script>

<style scoped>
.container {
  min-height: 100vh;
  background: #f5f5f5;
  padding: 20rpx;
}

.header {
  background: #fff;
  padding: 30rpx;
  border-radius: 20rpx;
  margin-bottom: 20rpx;
}

.title {
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
  display: block;
  margin-bottom: 10rpx;
}

.date {
  font-size: 24rpx;
  color: #999;
}

.tabs {
  display: flex;
  background: #fff;
  border-radius: 20rpx;
  padding: 10rpx;
  margin-bottom: 20rpx;
}

.tab {
  flex: 1;
  text-align: center;
  padding: 20rpx;
  font-size: 28rpx;
  color: #666;
  border-radius: 15rpx;
  transition: all 0.3s;
}

.tab.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-weight: bold;
}

.write-mode {
  background: #fff;
  border-radius: 20rpx;
  padding: 30rpx;
}

.section {
  margin-bottom: 40rpx;
}

.label {
  font-size: 28rpx;
  font-weight: bold;
  color: #333;
  display: block;
  margin-bottom: 20rpx;
}

.textarea {
  width: 100%;
  min-height: 300rpx;
  padding: 20rpx;
  border: 1px solid #eee;
  border-radius: 10rpx;
  font-size: 28rpx;
  line-height: 1.6;
}

.char-count {
  font-size: 24rpx;
  color: #999;
  text-align: right;
  display: block;
  margin-top: 10rpx;
}

.emotion-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 15rpx;
}

.tag {
  padding: 15rpx 30rpx;
  border: 1px solid #ddd;
  border-radius: 50rpx;
  font-size: 26rpx;
  color: #666;
  background: #f9f9f9;
}

.tag.selected {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border-color: transparent;
}

.score-text {
  font-size: 32rpx;
  color: #667eea;
  font-weight: bold;
  display: block;
  text-align: center;
  margin-top: 20rpx;
}

.upload-area {
  display: flex;
  gap: 20rpx;
}

.upload-btn {
  flex: 1;
  padding: 30rpx;
  border: 2px dashed #ddd;
  border-radius: 10rpx;
  text-align: center;
  color: #999;
}

.preview-list {
  display: flex;
  gap: 20rpx;
  margin-top: 20rpx;
  flex-wrap: wrap;
}

.preview-item {
  position: relative;
  width: 150rpx;
  height: 150rpx;
}

.preview-img {
  width: 100%;
  height: 100%;
  border-radius: 10rpx;
}

.delete-btn {
  position: absolute;
  top: -10rpx;
  right: -10rpx;
  width: 40rpx;
  height: 40rpx;
  background: #ff4444;
  color: #fff;
  border-radius: 50%;
  text-align: center;
  line-height: 40rpx;
  font-size: 32rpx;
}

.submit-btn {
  margin-top: 40rpx;
  border-radius: 50rpx;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.submit-btn[disabled] {
  background: #ccc;
}

/* 语音模式样式 */
.voice-mode {
  background: #fff;
  border-radius: 20rpx;
  padding: 60rpx 30rpx;
}

.voice-area {
  text-align: center;
  margin-bottom: 60rpx;
}

.voice-btn {
  width: 200rpx;
  height: 200rpx;
  margin: 0 auto 30rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8rpx 24rpx rgba(102, 126, 234, 0.3);
}

.voice-btn.recording {
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

.voice-btn .text {
  font-size: 24rpx;
  color: #fff;
}

.duration {
  font-size: 40rpx;
  color: #667eea;
  font-weight: bold;
}

.transcript-area {
  padding: 30rpx;
  background: #f9f9f9;
  border-radius: 15rpx;
}

.transcript-box {
  padding: 30rpx;
  background: #fff;
  border-radius: 10rpx;
  margin: 20rpx 0;
  min-height: 200rpx;
  line-height: 1.8;
  color: #333;
}
</style>
