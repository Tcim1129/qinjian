/**
 * 危机预警页 - 展示关系危机提醒和资源
 */
const api = require('../../utils/api.js')
const auth = require('../../utils/auth.js')

Page({
  data: {
    alerts: [],
    resources: [],
    loading: true
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
      const [alertsRes, resourcesRes] = await Promise.all([
        api.get(`/crisis/alerts/${pairId}`).catch(() => []),
        api.get('/crisis/resources').catch(() => [])
      ])
      this.setData({
        alerts: alertsRes || [],
        resources: resourcesRes || []
      })
    } catch (e) {
      console.error('加载危机数据失败:', e)
    } finally {
      this.setData({ loading: false })
    }
  },

  async acknowledgeAlert(e) {
    const id = e.currentTarget.dataset.id
    try {
      await api.post(`/crisis/alerts/${id}/acknowledge`)
      wx.showToast({ title: '已确认', icon: 'success' })
      this.loadData()
    } catch (e) {
      wx.showToast({ title: e.message || '操作失败', icon: 'none' })
    }
  },

  async resolveAlert(e) {
    const id = e.currentTarget.dataset.id
    try {
      await api.post(`/crisis/alerts/${id}/resolve`, { note: '' })
      wx.showToast({ title: '已解决', icon: 'success' })
      this.loadData()
    } catch (e) {
      wx.showToast({ title: e.message || '操作失败', icon: 'none' })
    }
  }
})
