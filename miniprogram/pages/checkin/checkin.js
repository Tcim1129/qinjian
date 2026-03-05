/**
 * 打卡页 - 每日关系健康记录
 * 4步表单流程：心情 → 互动 → 深度对话 → 任务完成
 * 支持文本备注、情绪标签、图片/语音上传
 */
const api = require('../../utils/api.js')
const auth = require('../../utils/auth.js')

Page({
  data: {
    // 表单步骤 (1-4)
    currentStep: 1,
    totalSteps: 4,

    // 步骤1：心情评分 (1-4)
    moodScore: 0,
    moodOptions: [
      { score: 1, emoji: '😟', label: '低落' },
      { score: 2, emoji: '😐', label: '一般' },
      { score: 3, emoji: '🙂', label: '不错' },
      { score: 4, emoji: '😊', label: '很好' }
    ],

    // 步骤2：互动次数 & 主动性
    interactionCount: 0,
    initiativeScore: 0,

    // 步骤3：深度对话
    deepConversation: false,

    // 步骤4：任务完成
    taskCompleted: false,

    // 附加信息
    freeText: '',
    selectedTags: [],
    emotionTags: ['感恩', '甜蜜', '思念', '担忧', '争吵', '冷战', '惊喜', '日常', '成长', '包容'],
    imageList: [],
    voicePath: '',

    // 是否已打卡
    hasCheckedIn: false,
    todayCheckin: null,

    // 录音状态
    isRecording: false,

    // 提交状态
    submitting: false
  },

  onLoad() {
    // 页面加载时检查登录
  },

  onShow() {
    if (!auth.checkLogin()) return
    this.checkTodayCheckin()
  },

  /**
   * 检查今日是否已打卡
   */
  async checkTodayCheckin() {
    const pairId = auth.getPairId()
    try {
      const res = pairId
        ? await api.get(`/checkins/today?pair_id=${pairId}`)
        : await api.get('/checkins/today?mode=solo')
      if (res) {
        this.setData({
          hasCheckedIn: !!res.my_done,
          todayCheckin: res.my_checkin || res
        })
      }
    } catch (e) {
      if (e.code === 404) {
        this.setData({ hasCheckedIn: false, todayCheckin: null })
      }
    }
  },

  /**
   * 选择心情评分
   */
  selectMood(e) {
    const score = e.currentTarget.dataset.score
    this.setData({ moodScore: score })
  },

  /**
   * 互动次数输入
   */
  onInteractionInput(e) {
    const val = parseInt(e.detail.value) || 0
    this.setData({ interactionCount: val })
  },

  /**
   * 主动性滑动选择
   */
  onInitiativeChange(e) {
    this.setData({ initiativeScore: e.detail.value })
  },

  /**
   * 切换深度对话
   */
  toggleDeepConversation(e) {
    const val = e.currentTarget.dataset.val === 'true'
    this.setData({ deepConversation: val })
  },

  /**
   * 切换任务完成
   */
  toggleTaskCompleted(e) {
    const val = e.currentTarget.dataset.val === 'true'
    this.setData({ taskCompleted: val })
  },

  /**
   * 自由文本输入
   */
  onFreeTextInput(e) {
    this.setData({ freeText: e.detail.value })
  },

  /**
   * 切换情绪标签选中状态
   */
  toggleTag(e) {
    const tag = e.currentTarget.dataset.tag
    const tags = this.data.selectedTags.slice()
    const idx = tags.indexOf(tag)
    if (idx >= 0) {
      tags.splice(idx, 1)
    } else {
      tags.push(tag)
    }
    this.setData({ selectedTags: tags })
  },

  /**
   * 选择图片上传
   */
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

  /**
   * 删除已选图片
   */
  removeImage(e) {
    const idx = e.currentTarget.dataset.idx
    const list = this.data.imageList.slice()
    list.splice(idx, 1)
    this.setData({ imageList: list })
  },

  /**
   * 录制/选择语音
   */
  chooseVoice() {
    if (this.data.isRecording) {
      // 手动停止录音
      const recorderManager = wx.getRecorderManager()
      recorderManager.stop()
      return
    }

    const recorderManager = wx.getRecorderManager()
    recorderManager.onStop((res) => {
      this.setData({ voicePath: res.tempFilePath, isRecording: false })
      if (this._recordTimer) {
        clearTimeout(this._recordTimer)
        this._recordTimer = null
      }
    })
    recorderManager.onError(() => {
      this.setData({ isRecording: false })
      wx.showToast({ title: '录音失败', icon: 'none' })
    })

    this.setData({ isRecording: true })
    recorderManager.start({
      duration: 60000,
      format: 'mp3'
    })
    // 5秒后自动停止
    this._recordTimer = setTimeout(() => {
      recorderManager.stop()
    }, 5000)
    wx.showToast({ title: '录音中（5秒后自动停止）', icon: 'none', duration: 5000 })
  },

  /**
   * 清除语音
   */
  clearVoice() {
    this.setData({ voicePath: '' })
  },

  /**
   * 下一步
   */
  nextStep() {
    if (this.data.currentStep === 1 && this.data.moodScore === 0) {
      wx.showToast({ title: '请选择今日心情', icon: 'none' })
      return
    }
    if (this.data.currentStep < this.data.totalSteps) {
      this.setData({ currentStep: this.data.currentStep + 1 })
    }
  },

  /**
   * 上一步
   */
  prevStep() {
    if (this.data.currentStep > 1) {
      this.setData({ currentStep: this.data.currentStep - 1 })
    }
  },

  /**
   * 提交打卡
   */
  async submitCheckin() {
    if (this.data.submitting) return
    if (this.data.moodScore === 0) {
      wx.showToast({ title: '请选择今日心情', icon: 'none' })
      return
    }

    const pairId = auth.getPairId()

    this.setData({ submitting: true })

    try {
      const initiative = this.data.initiativeScore === 1 ? 'me' : 'partner'

      const checkinData = {
        pair_id: pairId || null,
        content: this.data.freeText || '今日打卡',
        mood_tags: this.data.selectedTags.length > 0 ? this.data.selectedTags : null,
        mood_score: this.data.moodScore,
        interaction_freq: this.data.interactionCount,
        interaction_initiative: initiative,
        deep_conversation: this.data.deepConversation,
        task_completed: this.data.taskCompleted
      }

      const res = pairId
        ? await api.post('/checkins/', checkinData)
        : await api.post('/checkins/?mode=solo', checkinData)

      wx.showToast({ title: '打卡成功！', icon: 'success' })
      this.setData({
        hasCheckedIn: true,
        todayCheckin: res
      })
    } catch (e) {
      wx.showToast({ title: e.message || '提交失败', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  }
})
