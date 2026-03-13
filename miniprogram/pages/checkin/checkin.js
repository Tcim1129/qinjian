const api = require('../../utils/api.js')
const auth = require('../../utils/auth.js')
let plugin = null
try {
  plugin = requirePlugin('WechatSI')
} catch (error) {
  plugin = null
}

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
    voiceSupported: !!plugin,
    recognizingVoice: false,
    playingReply: false,
  },

  onLoad() {
    this.initVoiceTools()
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
    this.stopVoicePlayback()
    this.stopRecognitionIfNeeded()
  },

  onUnload() {
    this.stopVoicePlayback()
    this.stopRecognitionIfNeeded()
  },

  switchMode(e) {
    const mode = e.currentTarget.dataset.mode
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
      if (e.code === 404) {
        this.setData({ hasCheckedIn: false, todayCheckin: null })
      }
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
      if (this.recorderManager) this.recorderManager.stop()
      return
    }

    if (!this.recorderManager) {
      this.recorderManager = wx.getRecorderManager()
      this.recorderManager.onStop((res) => {
        this.setData({ voicePath: res.tempFilePath, isRecording: false })
        if (this._recordTimer) {
          clearTimeout(this._recordTimer)
          this._recordTimer = null
        }
      })
      this.recorderManager.onError(() => {
        this.setData({ isRecording: false })
        wx.showToast({ title: '录音失败', icon: 'none' })
      })
    }
    this.setData({ isRecording: true })
    this.recorderManager.start({ duration: 60000, format: 'mp3' })
    this._recordTimer = setTimeout(() => this.recorderManager.stop(), 5000)
    wx.showToast({ title: '录音中（5秒后自动停止）', icon: 'none', duration: 3000 })
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
      wx.showToast({ title: e.message || 'AI 会话启动失败', icon: 'none' })
    }
  },

  initVoiceTools() {
    if (this.innerAudioContext) {
      return
    }
    this.innerAudioContext = wx.createInnerAudioContext()
    this.innerAudioContext.onEnded(() => {
      this.setData({ playingReply: false })
    })
    this.innerAudioContext.onError(() => {
      this.setData({ playingReply: false })
      wx.showToast({ title: '语音播放失败', icon: 'none' })
    })
  },

  ensureRecognitionManager() {
    if (!plugin) return null
    if (this.recognitionManager) return this.recognitionManager

    const manager = plugin.getRecordRecognitionManager()
    manager.onStart = () => {
      this.setData({ recognizingVoice: true, isRecording: true })
      wx.showToast({ title: '正在识别语音', icon: 'none' })
    }
    manager.onRecognize = (res) => {
      if (res && res.result) {
        this.setData({ chatInput: res.result })
      }
    }
    manager.onStop = async (res) => {
      this.setData({ recognizingVoice: false, isRecording: false })
      const result = (res && res.result ? res.result : '').trim()
      if (!result) {
        return
      }
      this.setData({ chatInput: result })
      await this.sendChat()
    }
    manager.onError = () => {
      this.setData({ recognizingVoice: false, isRecording: false })
      wx.showToast({ title: '语音识别失败', icon: 'none' })
    }
    this.recognitionManager = manager
    return manager
  },

  stopRecognitionIfNeeded() {
    if (this.data.recognizingVoice && this.recognitionManager && typeof this.recognitionManager.stop === 'function') {
      this.recognitionManager.stop()
    }
    this.setData({ recognizingVoice: false, isRecording: false })
  },

  stopVoicePlayback() {
    if (this.innerAudioContext) {
      this.innerAudioContext.stop()
    }
    this.setData({ playingReply: false })
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
  },

  toggleVoiceChatRecord() {
    if (this.data.isRecording) {
      this.setData({ isRecording: false })
      this.stopRecognitionIfNeeded()
      return
    }
    const manager = this.ensureRecognitionManager()
    if (!manager) {
      wx.showToast({ title: '当前环境未启用语音识别插件', icon: 'none' })
      return
    }
    this.setData({ isRecording: true })
    manager.start({
      lang: 'zh_CN',
      duration: 60000,
    })
  },

  async startVoiceRecognize() {
    const manager = this.ensureRecognitionManager()
    if (!manager) {
      wx.showToast({ title: '当前环境未启用语音识别插件', icon: 'none' })
      return
    }
    if (this.data.recognizingVoice) {
      this.stopRecognitionIfNeeded()
      return
    }

    manager.start({
      lang: 'zh_CN',
      duration: 60000,
    })
  },

  playLastReply() {
    if (!this.data.lastReply) {
      wx.showToast({ title: '还没有可播放的回复', icon: 'none' })
      return
    }
    if (!plugin || typeof plugin.textToSpeech !== 'function') {
      wx.showToast({ title: '当前环境暂不支持语音播报', icon: 'none' })
      return
    }
    this.initVoiceTools()
    this.stopVoicePlayback()
    this.setData({ playingReply: true })
    plugin.textToSpeech({
      lang: 'zh_CN',
      tts: this.data.lastReply,
      success: (res) => {
        const filePath = res.filename || res.filePath
        if (!filePath) {
          this.setData({ playingReply: false })
          wx.showToast({ title: '语音生成失败', icon: 'none' })
          return
        }
        this.innerAudioContext.src = filePath
        this.innerAudioContext.play()
      },
      fail: () => {
        this.setData({ playingReply: false })
        wx.showToast({ title: '语音生成失败', icon: 'none' })
      }
    })
  }
})
