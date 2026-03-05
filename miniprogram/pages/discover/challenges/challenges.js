/**
 * 关系挑战赛页 - 每日任务
 */
const api = require('../../../utils/api.js')
const auth = require('../../../utils/auth.js')

Page({
  data: {
    tasks: [],
    loading: true
  },

  onLoad() {
    if (!auth.checkLogin()) return
    if (!auth.checkPaired()) return
    this.loadTasks()
  },

  async loadTasks() {
    this.setData({ loading: true })
    const pairId = auth.getPairId()
    try {
      const res = await api.get(`/tasks/daily/${pairId}`)
      this.setData({ tasks: res || [] })
    } catch (e) {
      console.error('加载任务失败:', e)
    } finally {
      this.setData({ loading: false })
    }
  },

  async completeTask(e) {
    const id = e.currentTarget.dataset.id
    try {
      await api.post(`/tasks/${id}/complete`)
      wx.showToast({ title: '完成！', icon: 'success' })
      this.loadTasks()
    } catch (e) {
      wx.showToast({ title: e.message || '操作失败', icon: 'none' })
    }
  }
})
