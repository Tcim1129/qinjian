/**
 * 异地恋工具页 - 活动建议、健康指数
 */
const api = require('../../../utils/api.js')
const auth = require('../../../utils/auth.js')

Page({
  data: {
    activities: [],
    healthIndex: null,
    loading: true,
    
    // 新建活动表单
    showAddForm: false,
    newActivityTitle: '',
    newActivityDesc: '',
    submitting: false
  },

  onLoad() {
    if (!auth.checkLogin()) return
    if (!auth.checkPaired()) return
    this.loadData()
  },

  async loadData() {
    this.setData({ loading: true })
    const pairId = auth.getPairId()
    try {
      const [activitiesRes, healthRes] = await Promise.all([
        api.get(`/longdistance/activities/${pairId}`).catch(() => []),
        api.get(`/longdistance/health-index/${pairId}`).catch(() => null)
      ])
      this.setData({
        activities: activitiesRes || [],
        healthIndex: healthRes
      })
    } catch (e) {
      console.error('加载异地恋数据失败:', e)
    } finally {
      this.setData({ loading: false })
    }
  },

  showAdd() {
    this.setData({ showAddForm: true })
  },

  hideAdd() {
    this.setData({ showAddForm: false, newActivityTitle: '', newActivityDesc: '' })
  },

  onTitleInput(e) {
    this.setData({ newActivityTitle: e.detail.value })
  },

  onDescInput(e) {
    this.setData({ newActivityDesc: e.detail.value })
  },

  async submitActivity() {
    if (this.data.submitting) return
    if (!this.data.newActivityTitle.trim()) {
      wx.showToast({ title: '请输入活动名称', icon: 'none' })
      return
    }

    this.setData({ submitting: true })
    const pairId = auth.getPairId()

    try {
      await api.post(`/longdistance/activities?pair_id=${pairId}`, {
        title: this.data.newActivityTitle,
        description: this.data.newActivityDesc
      })
      wx.showToast({ title: '添加成功', icon: 'success' })
      this.hideAdd()
      this.loadData()
    } catch (e) {
      wx.showToast({ title: e.message || '添加失败', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  },

  async completeActivity(e) {
    const id = e.currentTarget.dataset.id
    try {
      await api.post(`/longdistance/activities/${id}/complete`)
      wx.showToast({ title: '已完成', icon: 'success' })
      this.loadData()
    } catch (e) {
      wx.showToast({ title: e.message || '操作失败', icon: 'none' })
    }
  }
})
