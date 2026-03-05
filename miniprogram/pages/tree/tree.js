/**
 * 关系树页 - 可视化展示关系成长
 * 显示当前等级、浇水进度、升级提示
 */
const api = require('../../utils/api.js')
const auth = require('../../utils/auth.js')

Page({
  data: {
    treeStatus: null,
    loading: true,
    watering: false
  },

  onLoad() {
    if (!auth.checkLogin()) return
    if (!auth.checkPaired()) return
    this.loadTreeStatus()
  },

  async loadTreeStatus() {
    this.setData({ loading: true })
    const pairId = auth.getPairId()
    if (!pairId) {
      this.setData({ loading: false, treeStatus: null })
      return
    }
    try {
      const res = await api.get(`/tree/status?pair_id=${pairId}`)
      this.setData({ treeStatus: res })
    } catch (e) {
      console.error('获取关系树状态失败:', e)
    } finally {
      this.setData({ loading: false })
    }
  },

  async waterTree() {
    if (this.data.watering) return
    const pairId = auth.getPairId()
    if (!pairId) {
      wx.showToast({ title: '配对后可使用关系树', icon: 'none' })
      return
    }
    this.setData({ watering: true })

    try {
      const res = await api.post(`/tree/water?pair_id=${pairId}`)
      wx.showToast({ title: '浇水成功！', icon: 'success' })
      this.setData({ treeStatus: res })
    } catch (e) {
      wx.showToast({ title: e.message || '浇水失败', icon: 'none' })
    } finally {
      this.setData({ watering: false })
    }
  }
})
