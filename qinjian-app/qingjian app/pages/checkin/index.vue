<template>
  <view class="checkin-page">
    <view class="top-panel">
      <view>
        <text class="eyebrow">CHECK-IN</text>
        <text class="page-title">{{ mode === 'voice' ? 'AI 语音陪伴打卡' : '四步情绪打卡' }}</text>
        <text class="page-subtitle">{{ mode === 'voice' ? '像豆包一样边聊边完成记录，系统会自动提炼成今天的打卡。' : '先快速记录，再生成更准确的 AI 洞察和报告。' }}</text>
      </view>
      <view class="mode-toggle">
        <text class="mode-chip" :class="{ active: mode === 'form' }" @click="switchMode('form')">表单</text>
        <text class="mode-chip" :class="{ active: mode === 'voice' }" @click="switchMode('voice')">语音</text>
      </view>
    </view>

    <scroll-view class="checkin-scroll" scroll-y>
      <view v-if="mode === 'form'" class="form-mode">
        <view class="progress-card">
          <view class="progress-track"><view class="progress-fill" :style="{ width: `${(step / 4) * 100}%` }"></view></view>
          <text class="progress-text">步骤 {{ step }}/4</text>
        </view>

        <view v-if="step === 1" class="panel-card">
          <text class="panel-title">今天的心情如何？</text>
          <view class="mood-grid">
            <view v-for="m in moods" :key="m.score" class="mood-item" :class="{ active: form.mood_score === m.score }" @click="form.mood_score = m.score">
              <text class="mood-emoji">{{ m.icon }}</text>
              <text class="mood-label">{{ m.label }}</text>
            </view>
          </view>
        </view>

        <view v-if="step === 2" class="panel-card">
          <text class="panel-title">今天和对方有几次有效互动？</text>
          <view class="counter-wrap">
            <button class="counter-btn" @click="adjustCount(-1)">−</button>
            <text class="counter-value">{{ form.interaction_freq }}</text>
            <button class="counter-btn" @click="adjustCount(1)">+</button>
          </view>
          <text class="panel-hint">0 也没关系，最重要的是记录真实状态。</text>
        </view>

        <view v-if="step === 3" class="panel-card">
          <text class="panel-title">今天有没有深一点的交流？</text>
          <view class="choice-row">
            <view class="choice-item" :class="{ active: form.deep_conversation === true }" @click="form.deep_conversation = true">有</view>
            <view class="choice-item" :class="{ active: form.deep_conversation === false }" @click="form.deep_conversation = false">没有</view>
          </view>
        </view>

        <view v-if="step === 4" class="panel-card">
          <text class="panel-title">补一句今天最想留下的话</text>
          <textarea v-model="form.content" class="memo-box" maxlength="300" placeholder="比如：今天一起吃饭时终于说开了那件事。"></textarea>
          <view class="task-line" @click="form.task_completed = !form.task_completed">
            <text class="task-name">今日小任务：给对方一个具体赞美</text>
            <text class="task-badge">{{ form.task_completed ? '已完成' : '待完成' }}</text>
          </view>
        </view>

        <view class="action-bar action-bar-form">
          <button v-if="step > 1" class="action-btn ghost" @click="step -= 1">上一步</button>
          <button v-if="step < 4" class="action-btn primary" @click="nextStep">下一步</button>
          <button v-else class="action-btn primary" @click="submitForm">提交打卡</button>
        </view>
      </view>

      <view v-else class="voice-mode">
        <view class="panel-card voice-hero">
          <text class="voice-title">AI 关系陪伴</text>
          <text class="voice-copy">你可以直接打字，也可以先按住录音。系统会引导你说出今天的心情、互动情况和值得记录的时刻。</text>
          <view class="voice-actions">
            <button class="action-btn primary" @click="toggleRecording">{{ isRecording ? '结束录音' : '开始录音' }}</button>
            <button class="action-btn ghost" @click="startVoiceRecognize">{{ recognizing ? '识别中' : '语音识别' }}</button>
            <button class="action-btn ghost" @click="playLastReply" :disabled="!lastReply">播放回复</button>
          </view>
        </view>

        <view class="panel-card chat-card">
          <view class="chat-list">
            <view v-for="msg in messages" :key="msg.id || msg.localId" class="chat-item" :class="msg.role === 'user' ? 'chat-user' : 'chat-ai'">
              <text class="chat-role">{{ msg.role === 'user' ? '我' : '亲健 AI' }}</text>
              <text class="chat-bubble">{{ msg.content }}</text>
            </view>
          </view>
          <view class="chat-input-row">
            <textarea v-model="chatInput" class="chat-input" maxlength="200" placeholder="输入一句话，或者先录音再发送"></textarea>
            <button class="send-btn" @click="sendChat">发送</button>
          </view>
        </view>
      </view>

      <view class="page-spacer"></view>
    </scroll-view>

    <FloatingTabBar current="/pages/checkin/index" />
  </view>
</template>

<script>
import { mapState } from 'vuex'
import api from '../../utils/api.js'
import { syncSession } from '../../utils/session.js'
import FloatingTabBar from '../../components/FloatingTabBar.vue'

export default {
  components: { FloatingTabBar },
  data() {
    return {
      mode: 'form',
      step: 1,
      moods: [
        { score: 1, icon: '◔', label: '低落' },
        { score: 2, icon: '◑', label: '一般' },
        { score: 3, icon: '◕', label: '不错' },
        { score: 4, icon: '●', label: '很好' },
      ],
      form: {
        mood_score: 0,
        interaction_freq: 1,
        deep_conversation: null,
        task_completed: false,
        content: '',
      },
      sessionId: '',
      chatInput: '',
      isRecording: false,
      recordManager: null,
      hasDraftRecording: false,
      messages: [],
      lastReply: '',
      speechSupported: false,
      recognitionSupported: false,
      recognizing: false,
    }
  },
  computed: {
    ...mapState(['pairInfo']),
  },
  onShow() {
    this.mode = uni.getStorageSync('qj_checkin_mode') || 'form'
    this.bootstrap()
  },
  onUnload() {
    uni.removeStorageSync('qj_checkin_mode')
    if (this.recognizing && typeof plus !== 'undefined' && plus.speech && typeof plus.speech.stopRecognize === 'function') {
      plus.speech.stopRecognize()
    }
  },
  methods: {
    async bootstrap() {
      if (api.isLoggedIn()) {
        try {
          await syncSession(this.$store)
        } catch (e) {
          console.warn('checkin sync failed', e)
        }
      }
      this.speechSupported = typeof plus !== 'undefined' && !!plus.speech && typeof plus.speech.speak === 'function'
      this.recognitionSupported = typeof plus !== 'undefined' && !!plus.speech && typeof plus.speech.startRecognize === 'function'
      if (this.mode === 'voice') {
        await this.ensureSession()
      }
    },
    switchMode(mode) {
      this.mode = mode
      uni.setStorageSync('qj_checkin_mode', mode)
      if (mode === 'voice') {
        this.ensureSession()
      }
    },
    adjustCount(delta) {
      this.form.interaction_freq = Math.max(0, (this.form.interaction_freq || 0) + delta)
    },
    nextStep() {
      if (this.step === 1 && !this.form.mood_score) {
        uni.showToast({ title: '先选一个心情', icon: 'none' })
        return
      }
      this.step += 1
    },
    async submitForm() {
      try {
        const payload = {
          pair_id: this.pairInfo?.id || null,
          content: this.form.content || '今天完成了一次情绪记录。',
          mood_score: this.form.mood_score,
          interaction_freq: this.form.interaction_freq,
          interaction_initiative: 'equal',
          deep_conversation: this.form.deep_conversation,
          task_completed: this.form.task_completed,
        }
        await api.submitCheckin(payload, this.pairInfo?.id ? '' : 'solo')
        uni.showToast({ title: '打卡成功', icon: 'success' })
        this.step = 1
        this.form = {
          mood_score: 0,
          interaction_freq: 1,
          deep_conversation: null,
          task_completed: false,
          content: '',
        }
      } catch (e) {
        uni.showToast({ title: e.message || '提交失败', icon: 'none' })
      }
    },
    async ensureSession() {
      if (this.sessionId) return
      try {
        const session = await api.createAgentSession(this.pairInfo?.id || null)
        this.sessionId = session.session_id
        const history = await api.getAgentMessages(this.sessionId)
        this.messages = history || []
      } catch (e) {
        uni.showToast({ title: 'AI 会话启动失败', icon: 'none' })
      }
    },
    async sendChat() {
      if (!this.chatInput.trim()) return
      await this.ensureSession()
      const content = this.chatInput.trim()
      this.messages.push({ localId: `${Date.now()}-u`, role: 'user', content })
      this.chatInput = ''
      try {
        const res = await api.chatWithAgent(this.sessionId, content)
        this.messages.push({ localId: `${Date.now()}-a`, role: 'assistant', content: res.reply })
        this.lastReply = res.reply
        if (res.action === 'checkin_extracted') {
          uni.showToast({ title: '已自动生成打卡', icon: 'success' })
        }
        this.playLastReply()
      } catch (e) {
        uni.showToast({ title: e.message || '发送失败', icon: 'none' })
      }
    },
    toggleRecording() {
      if (typeof uni.getRecorderManager !== 'function') {
        uni.showToast({ title: '当前环境不支持录音', icon: 'none' })
        return
      }
      if (!this.recordManager) {
        this.recordManager = uni.getRecorderManager()
        this.recordManager.onStop(() => {
          this.isRecording = false
          this.hasDraftRecording = true
          uni.showToast({ title: '录音完成，可转文字后发送', icon: 'none' })
        })
        this.recordManager.onError(() => {
          this.isRecording = false
          this.hasDraftRecording = false
          uni.showToast({ title: '录音失败', icon: 'none' })
        })
      }

      if (this.isRecording) {
        this.recordManager.stop()
        return
      }

      this.isRecording = true
      this.hasDraftRecording = false
      this.recordManager.start({ duration: 60000, format: 'mp3' })
      uni.showToast({ title: '录音中，可稍后转文字发送', icon: 'none' })
    },
    startVoiceRecognize() {
      if (!this.recognitionSupported) {
        uni.showToast({ title: '当前环境不支持语音识别', icon: 'none' })
        return
      }
      if (this.recognizing && typeof plus !== 'undefined' && plus.speech && typeof plus.speech.stopRecognize === 'function') {
        plus.speech.stopRecognize()
        this.recognizing = false
        return
      }
      this.recognizing = true
      plus.speech.startRecognize({ engine: 'baidu' }, (result) => {
        this.recognizing = false
        this.chatInput = (result || '').trim()
        if (this.chatInput) {
          this.sendChat()
        } else {
          uni.showToast({ title: '没有识别到内容', icon: 'none' })
        }
      }, () => {
        this.recognizing = false
        uni.showToast({ title: '语音识别失败', icon: 'none' })
      })
    },
    playLastReply() {
      if (!this.lastReply) return
      if (this.speechSupported) {
        plus.speech.speak(this.lastReply)
        return
      }
      uni.showToast({ title: '当前环境不支持语音播报', icon: 'none' })
    },
  }
}
</script>

<style scoped>
.checkin-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: linear-gradient(180deg, #fff9f3 0%, #f5eee7 100%);
}

.top-panel {
  padding: 84rpx 28rpx 36rpx;
  background: linear-gradient(135deg, #5d4037, #d4a373);
  border-radius: 0 0 42rpx 42rpx;
}

.eyebrow {
  font-size: 20rpx;
  letter-spacing: 4rpx;
  text-transform: uppercase;
  color: rgba(255,255,255,0.72);
}

.page-title {
  display: block;
  margin-top: 18rpx;
  font-size: 48rpx;
  font-weight: 800;
  color: #fff;
}

.page-subtitle {
  display: block;
  margin-top: 14rpx;
  font-size: 22rpx;
  line-height: 1.8;
  color: rgba(255,255,255,0.8);
}

.mode-toggle {
  display: flex;
  gap: 12rpx;
  margin-top: 20rpx;
}

.mode-chip {
  padding: 10rpx 18rpx;
  border-radius: 999rpx;
  background: rgba(255,255,255,0.14);
  color: rgba(255,255,255,0.78);
  font-size: 20rpx;
  font-weight: 700;
}

.mode-chip.active {
  background: rgba(255,255,255,0.92);
  color: #5d4037;
}

.checkin-scroll {
  flex: 1;
  min-height: 0;
  padding: 24rpx 28rpx 0;
  box-sizing: border-box;
}

.progress-card,
.panel-card {
  background: rgba(255,255,255,0.96);
  border-radius: 32rpx;
  box-shadow: 0 16rpx 32rpx rgba(62, 39, 35, 0.08);
  border: 1rpx solid rgba(212, 163, 115, 0.12);
}

.progress-card {
  padding: 24rpx;
}

.progress-track {
  height: 10rpx;
  border-radius: 999rpx;
  background: #efe3d7;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #5d4037, #d4a373);
}

.progress-text {
  display: block;
  margin-top: 12rpx;
  text-align: center;
  font-size: 20rpx;
  color: #8d6e63;
}

.panel-card {
  margin-top: 20rpx;
  padding: 28rpx;
}

.panel-title,
.voice-title {
  display: block;
  font-size: 30rpx;
  font-weight: 800;
  color: #2f2522;
}

.panel-hint,
.voice-copy {
  display: block;
  margin-top: 14rpx;
  font-size: 22rpx;
  line-height: 1.8;
  color: #8d6e63;
}

.mood-grid,
.choice-row,
.voice-actions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16rpx;
  margin-top: 22rpx;
}

.mood-item,
.choice-item {
  padding: 24rpx;
  border-radius: 26rpx;
  background: #fcf4ed;
  text-align: center;
}

.mood-item.active,
.choice-item.active {
  background: linear-gradient(135deg, #5d4037, #d4a373);
  color: #fff;
}

.mood-emoji {
  display: block;
  font-size: 34rpx;
}

.mood-label {
  display: block;
  margin-top: 12rpx;
  font-size: 24rpx;
  font-weight: 700;
}

.counter-wrap {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 24rpx;
  margin-top: 26rpx;
}

.counter-btn,
.action-btn,
.send-btn {
  border: none;
}

.counter-btn {
  width: 86rpx;
  height: 86rpx;
  border-radius: 43rpx;
  background: #f4e7db;
  color: #5d4037;
  font-size: 36rpx;
}

.counter-value {
  font-size: 64rpx;
  font-weight: 900;
  color: #3e2723;
}

.memo-box,
.chat-input {
  width: 100%;
  margin-top: 20rpx;
  min-height: 180rpx;
  border-radius: 24rpx;
  background: #fbf3eb;
  padding: 24rpx;
  box-sizing: border-box;
  color: #3e2723;
}

.task-line {
  margin-top: 18rpx;
  padding: 20rpx;
  border-radius: 24rpx;
  background: #fff8f1;
  display: flex;
  justify-content: space-between;
  gap: 18rpx;
}

.task-name,
.task-badge {
  font-size: 22rpx;
}

.task-badge {
  color: #8d6e63;
  font-weight: 700;
}

.action-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: calc(112rpx + env(safe-area-inset-bottom));
  padding: 0 28rpx;
  display: flex;
  gap: 16rpx;
}

.action-bar-form {
  justify-content: space-between;
}

.action-btn,
.send-btn {
  flex: 1;
  height: 86rpx;
  border-radius: 999rpx;
  font-size: 26rpx;
  font-weight: 700;
}

.action-btn.primary,
.send-btn {
  background: linear-gradient(135deg, #5d4037, #d4a373);
  color: #fff;
}

.action-btn.ghost {
  background: #f4ece3;
  color: #6d4c41;
}

.chat-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.chat-item {
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.chat-user {
  align-items: flex-end;
}

.chat-ai {
  align-items: flex-start;
}

.chat-role {
  font-size: 20rpx;
  color: #a1887f;
}

.chat-bubble {
  max-width: 88%;
  padding: 18rpx 22rpx;
  border-radius: 24rpx;
  background: #f7efe6;
  color: #3e2723;
  line-height: 1.8;
  font-size: 23rpx;
}

.chat-user .chat-bubble {
  background: linear-gradient(135deg, #5d4037, #8d6e63);
  color: #fff;
}

.chat-input-row {
  margin-top: 22rpx;
  display: flex;
  gap: 14rpx;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
  min-height: 120rpx;
  margin-top: 0;
}

.send-btn {
  flex: none;
  width: 148rpx;
}

.page-spacer {
  height: 340rpx;
}
</style>
