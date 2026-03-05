/**
 * 里程碑页 - 记录关系中的重要时刻
 * 时间线展示、添加里程碑、生成回顾
 */
const api = require('../../utils/api.js')
const auth = require('../../utils/auth.js')
const util = require('../../utils/util.js')

Page({
  data: {
    milestones: [],
    loading: true,

    // 添加表单
    showAddForm: false,
    newTitle: '',
    newDate: '',
    newDesc: '',
    submitting: false
  },

  onLoad() {
    if (!auth.checkLogin()) return
    if (!auth.checkPaired()) return
    this.loadMilestones()
  },

  async loadMilestones() {
    this.setData({ loading: true })
    const pairId = auth.getPairId()
    try {
      const res = await api.get(`/milestones/${pairId}`)
      this.setData({ milestones: res || [] })
    } catch (e) {
      console.error('获取里程碑失败:', e)
    } finally {
      this.setData({ loading: false })
    }
  },

  showAdd() {
    this.setData({
      showAddForm: true,
      newDate: util.formatDate(new Date())
    })
  },

  hideAdd() {
    this.setData({ showAddForm: false, newTitle: '', newDesc: '' })
  },

  onTitleInput(e) {
    this.setData({ newTitle: e.detail.value })
  },

  onDatePick(e) {
    this.setData({ newDate: e.detail.value })
  },

  onDescInput(e) {
    this.setData({ newDesc: e.detail.value })
  },

  async submitMilestone() {
    if (this.data.submitting) return
    if (!this.data.newTitle.trim()) {
      wx.showToast({ title: '请输入标题', icon: 'none' })
      return
    }

    this.setData({ submitting: true })
    const pairId = auth.getPairId()

    try {
      await api.post('/milestones/', {
        pair_id: pairId,
        title: this.data.newTitle.trim(),
        date: this.data.newDate,
        description: this.data.newDesc || ''
      })
      wx.showToast({ title: '添加成功', icon: 'success' })
      this.hideAdd()
      this.loadMilestones()
    } catch (e) {
      wx.showToast({ title: e.message || '添加失败', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  },

  async generateReview(e) {
    const id = e.currentTarget.dataset.id
    wx.showLoading({ title: '生成中...' })
    try {
      const res = await api.post(`/milestones/${id}/generate-review`)
      wx.hideLoading()
      wx.showModal({
        title: '里程碑回顾',
        content: res.review || '回顾生成完成',
        showCancel: false
      })
    } catch (e) {
      wx.hideLoading()
      wx.showToast({ title: e.message || '生成失败', icon: 'none' })
    }
  }
})
