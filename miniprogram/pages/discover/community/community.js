/**
 * 关系社区页 - 小贴士、通知
 */
const api = require('../../../utils/api.js')
const auth = require('../../../utils/auth.js')

Page({
  data: {
    tips: [],
    notifications: [],
    currentTab: 'tips',
    loading: true
  },

  onLoad() {
    if (!auth.checkLogin()) return
    this.loadData()
  },

  async loadData() {
    this.setData({ loading: true })
    try {
      const [tipsRes, notificationsRes] = await Promise.all([
        api.get('/community/tips').catch(() => []),
        api.get('/community/notifications').catch(() => [])
      ])
      this.setData({
        tips: tipsRes || [],
        notifications: notificationsRes || []
      })
    } catch (e) {
      console.error('加载社区数据失败:', e)
    } finally {
      this.setData({ loading: false })
    }
  },

  switchTab(e) {
    this.setData({ currentTab: e.currentTarget.dataset.tab })
  },

  async readAllNotifications() {
    try {
      await api.post('/community/notifications/read-all')
      wx.showToast({ title: '已全部已读', icon: 'success' })
      this.loadData()
    } catch (e) {
      wx.showToast({ title: e.message || '操作失败', icon: 'none' })
    }
  }
})
