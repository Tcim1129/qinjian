const api = require('../../utils/api.js')
const auth = require('../../utils/auth.js')

Page({
  data: {
    mode: 'form',
    currentStep: 1,
    totalSteps: 4,
    moodScore: 0,
    moodOptions: [
      { score: 1, emoji: '😟', label: '低落' },
      { score: 2, emoji: '😐', label: '一般' },
      { score: 3, emoji: '🙂', label: '不错' },
      { score: 4, emoji: '😊', label: '很好' }
    ],
    interactionCount: 1,
    initiativeScore: 'equal',
    deepConversation: null,
    taskCompleted: false,
    freeText: '',
    selectedTags: [],
    emotionTags: ['感恩', '甜蜜', '思念', '担忧', '争吵', '冷战', '惊喜', '日常', '成长', '包容'],
    imageList: [],
    voicePath: '',
    hasCheckedIn: false,
    todayCheckin: null,
    submitting: false,
    sessionId: '',
    chatInput: '',
    chatMessages: [],
    isRecording: false,
    lastReply: '',
    voiceSupported: true,
    transcribingVoice: false,
    recognizingVoice: false,
    realtimeAsrStatus: '',
  },

  onLoad() {
    this.realtimeAsr = null
    this.skipNextVoiceTranscription = false
    this.initRecorder()
  },

  onShow() {
    if (!auth.checkLogin()) return
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 1 })
    }
    const mode = wx.getStorageSync('qj_checkin_mode') || 'form'
    this.setData({ mode })
    this.checkTodayCheckin()
    if (mode === 'voice') {
      this.ensureAgentSession()
    }
  },

  onHide() {
    this.stopRealtimeRecognition({ discard: true })
    if (this.data.isRecording) {
      this.skipNextVoiceTranscription = true
    }
    this.stopRecording()
  },

  onUnload() {
    this.stopRealtimeRecognition({ discard: true })
    if (this.data.isRecording) {
      this.skipNextVoiceTranscription = true
    }
    this.stopRecording()
  },

  // 初始化录音管理器
  initRecorder() {
    this.recorderManager = wx.getRecorderManager()
    this.recorderManager.onStart(() => {
      this.setData({ isRecording: true })
      wx.showToast({ title: '正在录音...', icon: 'none' })
    })
    this.recorderManager.onStop((res) => {
      this.setData({ isRecording: false })
      if (this.realtimeAsr && this.realtimeAsr.active) {
        this.finishRealtimeRecognition()
        return
      }
      if (this.skipNextVoiceTranscription) {
        this.skipNextVoiceTranscription = false
        return
      }
      // 如果是语音转文字模式，自动上传转录
      if (this.data.mode === 'voice' && res.tempFilePath) {
        this.transcribeVoice(res.tempFilePath)
      } else {
        // 表单模式，保存语音路径用于打卡
        this.setData({ voicePath: res.tempFilePath })
      }
    })
    this.recorderManager.onError((err) => {
      this.setData({ isRecording: false, transcribingVoice: false, recognizingVoice: false, realtimeAsrStatus: '' })
      if (this.realtimeAsr && this.realtimeAsr.active) {
        this.cleanupRealtimeRecognition()
      }
      wx.showToast({ title: '录音失败：' + err.message, icon: 'none' })
    })
    if (typeof this.recorderManager.onFrameRecorded === 'function') {
      this.recorderManager.onFrameRecorded((res) => {
        if (!this.realtimeAsr || !this.realtimeAsr.active || !this.realtimeAsr.socketReady) return
        const audio = wx.arrayBufferToBase64(res.frameBuffer)
        if (!audio) return
        this.realtimeAsr.socket.send({
          data: JSON.stringify({ type: 'audio.chunk', audio })
        })
      })
    }
  },

  // 开始录音
  startRecording() {
    this.recorderManager.start({
      duration: 60000,
      sampleRate: 16000,
      numberOfChannels: 1,
      encodeBitRate: 48000,
      format: 'mp3'
    })
  },

  // 停止录音
  stopRecording() {
    if (this.data.isRecording) {
      this.recorderManager.stop()
    }
  },

  // 切换录音状态（语音模式）
  toggleVoiceRecord() {
    if (this.data.isRecording) {
      this.stopRecording()
    } else {
      this.startRecording()
    }
  },

  toggleVoiceChatRecord() {
    if (this.realtimeAsr && this.realtimeAsr.stopping) {
      wx.showToast({ title: '正在整理最后一句，请稍候', icon: 'none' })
      return
    }
    if (this.data.recognizingVoice) {
      this.stopRealtimeRecognition({ discard: true })
    }
    this.toggleVoiceRecord()
  },

  async startVoiceRecognize() {
    if (this.realtimeAsr && this.realtimeAsr.stopping) {
      wx.showToast({ title: '正在整理最后一句，请稍候', icon: 'none' })
      return
    }
    if (this.data.recognizingVoice) {
      this.stopRealtimeRecognition()
      return
    }

    try {
      await this.startRealtimeRecognition()
    } catch (error) {
      this.cleanupRealtimeRecognition()
      wx.showToast({ title: error.message || '实时识别不可用，已切换录完转写', icon: 'none' })
      if (!this.data.isRecording) {
        this.startRecording()
      }
    }
  },

  async startRealtimeRecognition() {
    if (!this.recorderManager || typeof wx.connectSocket !== 'function' || typeof this.recorderManager.onFrameRecorded !== 'function') {
      throw new Error('当前环境不支持实时识别')
    }

    const socket = wx.connectSocket({
      url: api.getRealtimeAsrSocketUrl(),
      timeout: 10000,
    })

    this.realtimeAsr = {
      active: true,
      socket,
      socketReady: false,
      finalDelivered: false,
      stopping: false,
    }

    socket.onOpen(() => {
      if (!this.realtimeAsr || this.realtimeAsr.socket !== socket) return
      this.realtimeAsr.socketReady = true
      this.setData({
        recognizingVoice: true,
        realtimeAsrStatus: '正在实时转写，说完后再点一次结束识别。',
      })
      socket.send({
        data: JSON.stringify({
          type: 'session.start',
          format: 'pcm',
          sample_rate: 16000,
          language: 'zh',
        })
      })
      this.recorderManager.start({
        duration: 60000,
        sampleRate: 16000,
        numberOfChannels: 1,
        encodeBitRate: 256000,
        format: 'pcm',
        frameSize: 16,
      })
    })

    socket.onMessage(async (event) => {
      let payload = null
      try {
        payload = JSON.parse(event.data)
      } catch (error) {
        return
      }

      if (payload.type === 'partial') {
        this.setData({ chatInput: payload.text || '' })
        return
      }

      if (payload.type === 'final') {
        const finalText = (payload.text || '').trim()
        if (this.realtimeAsr) {
          this.realtimeAsr.finalDelivered = true
        }
        this.setData({
          chatInput: finalText,
          recognizingVoice: false,
          realtimeAsrStatus: '',
        })
        this.cleanupRealtimeRecognition()
        if (finalText) {
          await this.sendChat()
        }
        return
      }

      if (payload.type === 'error') {
        this.cleanupRealtimeRecognition()
        this.setData({ recognizingVoice: false, realtimeAsrStatus: '' })
        wx.showToast({ title: payload.message || '实时识别失败', icon: 'none' })
      }
    })

    socket.onError(() => {
      const shouldFallback = this.realtimeAsr && !this.realtimeAsr.finalDelivered
      this.cleanupRealtimeRecognition()
      this.setData({ recognizingVoice: false, realtimeAsrStatus: '' })
      if (shouldFallback && !this.data.isRecording) {
        wx.showToast({ title: '实时识别失败，已切换录完转写', icon: 'none' })
        this.startRecording()
      }
    })

    socket.onClose(() => {
      const shouldNotify = this.realtimeAsr && !this.realtimeAsr.finalDelivered && !this.realtimeAsr.stopping
      this.cleanupRealtimeRecognition()
      this.setData({ recognizingVoice: false, realtimeAsrStatus: '' })
      if (shouldNotify) {
        wx.showToast({ title: '实时识别已中断', icon: 'none' })
      }
    })
  },

  finishRealtimeRecognition() {
    if (!this.realtimeAsr || !this.realtimeAsr.active) return
    this.realtimeAsr.stopping = true
    this.setData({
      recognizingVoice: false,
      realtimeAsrStatus: '正在整理最后一句，请稍候。',
    })
    if (this.realtimeAsr.socketReady) {
      this.realtimeAsr.socket.send({
        data: JSON.stringify({ type: 'session.stop' })
      })
      return
    }
    this.cleanupRealtimeRecognition()
  },

  stopRealtimeRecognition(options = {}) {
    const { discard = false } = options
    if (!this.realtimeAsr || !this.realtimeAsr.active) return
    this.realtimeAsr.stopping = true
    if (discard) {
      this.cleanupRealtimeRecognition()
      this.setData({ recognizingVoice: false, realtimeAsrStatus: '' })
      return
    }
    if (this.data.isRecording) {
      this.stopRecording()
      return
    }
    this.finishRealtimeRecognition()
  },

  cleanupRealtimeRecognition() {
    if (this.realtimeAsr && this.realtimeAsr.socket) {
      try {
        this.realtimeAsr.socket.close({})
      } catch (error) {
        // noop
      }
    }
    this.realtimeAsr = null
  },

  playLastReply() {
    const text = this.data.lastReply
    if (!text) {
      wx.showToast({ title: '还没有回复可以播放', icon: 'none' })
      return
    }
    wx.showModal({
      title: '回复',
      content: text,
      showCancel: false,
      confirmText: '好的'
    })
  },

  // 上传语音并转录
  async transcribeVoice(filePath) {
    this.setData({ transcribingVoice: true })
    try {
      const result = await api.uploadAndTranscribe(filePath)
      this.setData({ chatInput: result.text, transcribingVoice: false })
      // 自动发送转录结果
      await this.sendChat()
    } catch (e) {
      this.setData({ transcribingVoice: false })
      wx.showToast({ title: e.message || '语音转文字失败', icon: 'none' })
    }
  },

  switchMode(e) {
    const mode = e.currentTarget.dataset.mode
    if (mode !== 'voice') {
      this.stopRealtimeRecognition({ discard: true })
    }
    this.setData({ mode })
    wx.setStorageSync('qj_checkin_mode', mode)
    if (mode === 'voice') {
      this.ensureAgentSession()
    }
  },

  async checkTodayCheckin() {
    const pairId = auth.getPairId()
    try {
      const res = pairId
        ? await api.get(`/checkins/today?pair_id=${pairId}`)
        : await api.get('/checkins/today?mode=solo')
      this.setData({
        hasCheckedIn: !!res.my_done,
        todayCheckin: res.my_checkin || res
      })
    } catch (e) {
      this.setData({ hasCheckedIn: false, todayCheckin: null })
    }
  },

  selectMood(e) {
    this.setData({ moodScore: e.currentTarget.dataset.score })
  },

  onInteractionInput(e) {
    const delta = e.currentTarget && e.currentTarget.dataset ? Number(e.currentTarget.dataset.delta) : NaN
    if (Number.isFinite(delta)) {
      this.setData({ interactionCount: Math.max(0, (this.data.interactionCount || 0) + delta) })
      return
    }
    this.setData({ interactionCount: Math.max(0, parseInt(e.detail.value, 10) || 0) })
  },

  selectInitiative(e) {
    this.setData({ initiativeScore: e.currentTarget.dataset.value })
  },

  toggleDeepConversation(e) {
    this.setData({ deepConversation: e.currentTarget.dataset.val === 'true' })
  },

  toggleTaskCompleted() {
    this.setData({ taskCompleted: !this.data.taskCompleted })
  },

  onFreeTextInput(e) {
    this.setData({ freeText: e.detail.value })
  },

  toggleTag(e) {
    const tag = e.currentTarget.dataset.tag
    const selectedTags = [...this.data.selectedTags]
    const idx = selectedTags.indexOf(tag)
    if (idx >= 0) {
      selectedTags.splice(idx, 1)
    } else {
      selectedTags.push(tag)
    }
    this.setData({ selectedTags })
  },

  chooseImage() {
    wx.chooseMedia({
      count: 3,
      mediaType: ['image'],
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const newImages = res.tempFiles.map(f => f.tempFilePath)
        this.setData({
          imageList: this.data.imageList.concat(newImages).slice(0, 3)
        })
      }
    })
  },

  removeImage(e) {
    const idx = e.currentTarget.dataset.idx
    const imageList = [...this.data.imageList]
    imageList.splice(idx, 1)
    this.setData({ imageList })
  },

  chooseVoice() {
    if (this.data.isRecording) {
      this.stopRecording()
      return
    }
    this.startRecording()
  },

  clearVoice() {
    this.setData({ voicePath: '' })
  },

  nextStep() {
    if (this.data.currentStep === 1 && this.data.moodScore === 0) {
      wx.showToast({ title: '请选择今日心情', icon: 'none' })
      return
    }
    if (this.data.currentStep === 3 && this.data.deepConversation === null) {
      wx.showToast({ title: '请选择是否有深度交流', icon: 'none' })
      return
    }
    if (this.data.currentStep < this.data.totalSteps) {
      this.setData({ currentStep: this.data.currentStep + 1 })
    }
  },

  prevStep() {
    if (this.data.currentStep > 1) {
      this.setData({ currentStep: this.data.currentStep - 1 })
    }
  },

  async submitCheckin() {
    if (this.data.submitting) return
    if (this.data.moodScore === 0) {
      wx.showToast({ title: '请选择今日心情', icon: 'none' })
      return
    }

    const pairId = auth.getPairId()
    this.setData({ submitting: true })

    try {
      let imageUrl = null
      let voiceUrl = null
      if (this.data.imageList[0]) {
        const imageRes = await api.upload('/upload/image', this.data.imageList[0])
        imageUrl = imageRes.url
      }
      if (this.data.voicePath) {
        const voiceRes = await api.upload('/upload/voice', this.data.voicePath)
        voiceUrl = voiceRes.url
      }

      const payload = {
        pair_id: pairId || null,
        content: this.data.freeText || '今天完成了一次关系打卡。',
        mood_tags: this.data.selectedTags.length ? this.data.selectedTags : null,
        image_url: imageUrl,
        voice_url: voiceUrl,
        mood_score: this.data.moodScore,
        interaction_freq: this.data.interactionCount,
        interaction_initiative: this.data.initiativeScore,
        deep_conversation: this.data.deepConversation,
        task_completed: this.data.taskCompleted,
      }

      await (pairId
        ? api.post('/checkins/', payload)
        : api.post('/checkins/?mode=solo', payload))

      wx.showToast({ title: '打卡成功', icon: 'success' })
      this.resetForm()
      this.checkTodayCheckin()
    } catch (e) {
      wx.showToast({ title: e.message || '提交失败', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  },

  resetForm() {
    this.setData({
      currentStep: 1,
      moodScore: 0,
      interactionCount: 1,
      initiativeScore: 'equal',
      deepConversation: null,
      taskCompleted: false,
      freeText: '',
      selectedTags: [],
      imageList: [],
      voicePath: '',
    })
  },

  async ensureAgentSession() {
    if (this.data.sessionId) return
    try {
      const pairId = auth.getPairId() || null
      const query = pairId ? `?pair_id=${pairId}` : ''
      const session = await api.post(`/agent/sessions${query}`)
      const messages = await api.get(`/agent/sessions/${session.session_id}/messages`)
      this.setData({
        sessionId: session.session_id,
        chatMessages: messages || []
      })
    } catch (e) {
      wx.showToast({ title: e.message || '会话启动失败', icon: 'none' })
    }
  },

  onChatInput(e) {
    this.setData({ chatInput: e.detail.value })
  },

  async sendChat() {
    const content = (this.data.chatInput || '').trim()
    if (!content) return
    if (!this.data.sessionId) {
      await this.ensureAgentSession()
    }

    const chatMessages = this.data.chatMessages.concat([{ localId: `u-${Date.now()}`, role: 'user', content }])
    this.setData({ chatMessages, chatInput: '' })

    try {
      const res = await api.post(`/agent/sessions/${this.data.sessionId}/chat`, { content })
      const nextMessages = this.data.chatMessages.concat([{ localId: `a-${Date.now()}`, role: 'assistant', content: res.reply }])
      this.setData({ chatMessages: nextMessages, lastReply: res.reply })
      if (res.action === 'checkin_extracted') {
        wx.showToast({ title: '已自动生成打卡', icon: 'success' })
        this.checkTodayCheckin()
      }
    } catch (e) {
      wx.showToast({ title: e.message || '发送失败', icon: 'none' })
    }
  }
})
