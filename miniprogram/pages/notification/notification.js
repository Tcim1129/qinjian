/**
 * 通知中心页面
 * 对接后端 /community/notifications 和 /community/notifications/read-all
 */
const api = require('../../utils/api.js')
const auth = require('../../utils/auth.js')

Page({
  data: {
    notifications: [],
    loading: true,
    unreadCount: 0,
  },

  onLoad() {
    if (!auth.checkLogin()) return
    this.loadNotifications()
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 3 })
    }
  },

  onPullDownRefresh() {
    this.loadNotifications().finally(() => wx.stopPullDownRefresh())
  },

  async loadNotifications() {
    this.setData({ loading: true })
    try {
      const res = await api.get('/community/notifications?limit=50')
      const unreadCount = (res || []).filter(n => !n.is_read).length
      this.setData({
        notifications: res || [],
        unreadCount,
        loading: false,
      })
    } catch (e) {
      console.error('获取通知列表失败:', e)
      this.setData({ loading: false, notifications: [] })
      if (e.code !== 404 && e.code !== 403) {
        wx.showToast({ title: '通知加载失败', icon: 'none' })
      }
    }
  },

  async markAllRead() {
    try {
      await api.post('/community/notifications/read-all')
      const notifications = this.data.notifications.map(n => ({ ...n, is_read: true }))
      this.setData({ notifications, unreadCount: 0 })
      wx.showToast({ title: '全部已读', icon: 'success' })
    } catch (e) {
      wx.showToast({ title: e.message || '标记失败', icon: 'none' })
    }
  },

  onNotificationTap(e) {
    const idx = e.currentTarget.dataset.idx
    const notifications = [...this.data.notifications]
    if (notifications[idx] && !notifications[idx].is_read) {
      notifications[idx].is_read = true
      this.setData({
        notifications,
        unreadCount: Math.max(0, this.data.unreadCount - 1),
      })
    }
  },

  formatTime(timeStr) {
    if (!timeStr) return ''
    const d = new Date(timeStr)
    const now = new Date()
    const diff = now - d
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (minutes < 1) return '刚刚'
    if (minutes < 60) return `${minutes}分钟前`
    if (hours < 24) return `${hours}小时前`
    if (days < 7) return `${days}天前`
    return `${d.getMonth() + 1}月${d.getDate()}日`
  },

  goBack() {
    wx.navigateBack()
  },
})
