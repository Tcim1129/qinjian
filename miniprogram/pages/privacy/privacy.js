/**
 * 隐私中心页面
 * 对接后端 /privacy/status, /privacy/delete-request, /privacy/delete-request/cancel
 */
const api = require('../../utils/api.js')
const auth = require('../../utils/auth.js')

Page({
  data: {
    loading: true,
    privacyStatus: null,
    deletionRequest: null,
    showDeleteConfirm: false,
    deleteReason: '',
  },

  onLoad() {
    if (!auth.checkLogin()) return
    this.loadPrivacyStatus()
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 4 })
    }
  },

  async loadPrivacyStatus() {
    this.setData({ loading: true })
    try {
      const res = await api.getPrivacyStatus()
      if (res) {
        this.setData({
          privacyStatus: res,
          deletionRequest: res.deletion_request || null,
          loading: false,
        })
      } else {
        this.setData({ loading: false, privacyStatus: null })
      }
    } catch (e) {
      console.error('获取隐私状态失败:', e)
      this.setData({ loading: false })
    }
  },

  showDeleteDialog() {
    this.setData({ showDeleteConfirm: true })
  },

  hideDeleteDialog() {
    this.setData({ showDeleteConfirm: false, deleteReason: '' })
  },

  onReasonInput(e) {
    this.setData({ deleteReason: e.detail.value })
  },

  async confirmDelete() {
    try {
      await api.createPrivacyDeleteRequest()
      this.setData({ showDeleteConfirm: false, deleteReason: '' })
      wx.showToast({ title: '删除请求已提交', icon: 'success' })
      this.loadPrivacyStatus()
    } catch (e) {
      wx.showToast({ title: e.message || '提交失败', icon: 'none' })
    }
  },

  async cancelDelete() {
    try {
      await api.cancelPrivacyDeleteRequest()
      wx.showToast({ title: '已取消删除请求', icon: 'success' })
      this.setData({ deletionRequest: null })
      this.loadPrivacyStatus()
    } catch (e) {
      wx.showToast({ title: e.message || '取消失败', icon: 'none' })
    }
  },

  goBack() {
    wx.navigateBack()
  },
})
