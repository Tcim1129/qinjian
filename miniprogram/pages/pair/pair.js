/**
 * 配对管理页
 * 未配对：输入邀请码 + 创建/加入配对
 * 已配对：伴侣信息、关系统计、解除配对
 */
const api = require('../../utils/api.js')
const auth = require('../../utils/auth.js')

Page({
  data: {
    // 配对状态
    isPaired: false,
    pairInfo: null,

    // 未配对表单
    inviteCode: '',

    // 加载状态
    loading: true,
    creating: false,
    joining: false
  },

  onLoad() {
    if (!auth.checkLogin()) return
    this.loadPairStatus()
  },

  /**
   * 获取当前配对状态
   */
  async loadPairStatus() {
    this.setData({ loading: true })
    try {
      const res = await api.get('/pairs/me')
      // 后端返回列表，取第一个 active 配对
      const pairs = Array.isArray(res) ? res : [res]
      const activePair = pairs.find(p => p.status === 'active') || pairs[0] || null
      const app = getApp()
      if (activePair) {
        app.setPairInfo(activePair)
        this.setData({
          isPaired: true,
          pairInfo: activePair
        })
      } else {
        app.setPairInfo(null)
        this.setData({ isPaired: false, pairInfo: null })
      }
    } catch (e) {
      if (e.code === 404) {
        this.setData({ isPaired: false, pairInfo: null })
      } else {
        console.error('获取配对状态失败:', e)
      }
    } finally {
      this.setData({ loading: false })
    }
  },

  /**
   * 邀请码输入
   */
  onInviteCodeInput(e) {
    this.setData({ inviteCode: e.detail.value })
  },

  /**
   * 创建配对（生成邀请码）
   */
  async createPair() {
    if (this.data.creating) return
    this.setData({ creating: true })

    try {
      const res = await api.post('/pairs/create', { type: 'couple' })
      wx.showModal({
        title: '配对码已生成',
        content: `请将此配对码分享给伴侣：${res.invite_code || res.code}`,
        showCancel: false,
        confirmColor: '#6C5CE7'
      })
      this.loadPairStatus()
    } catch (e) {
      wx.showToast({ title: e.message || '创建失败', icon: 'none' })
    } finally {
      this.setData({ creating: false })
    }
  },

  /**
   * 加入配对
   */
  async joinPair() {
    if (this.data.joining) return
    const code = this.data.inviteCode.trim()
    if (!code) {
      wx.showToast({ title: '请输入配对码', icon: 'none' })
      return
    }

    this.setData({ joining: true })

    try {
      const res = await api.post('/pairs/join', { invite_code: code })
      const app = getApp()
      app.setPairInfo(res)
      wx.showToast({ title: '配对成功！', icon: 'success' })
      this.loadPairStatus()
    } catch (e) {
      wx.showToast({ title: e.message || '加入失败', icon: 'none' })
    } finally {
      this.setData({ joining: false })
    }
  },

  /**
   * 发起解除配对（后端需 request-unbind → confirm-unbind 两步）
   */
  handleUnbind() {
    const pairId = this.data.pairInfo && (this.data.pairInfo.id || this.data.pairInfo.pair_id)
    if (!pairId) {
      wx.showToast({ title: '配对信息异常', icon: 'none' })
      return
    }
    wx.showModal({
      title: '确认解除配对',
      content: '将发起解绑请求，对方确认后解除（或7天冷静期后自动生效）。',
      confirmColor: '#FF6B6B',
      confirmText: '发起解绑',
      success: async (res) => {
        if (res.confirm) {
          try {
            await api.post(`/pairs/request-unbind?pair_id=${pairId}`)
            wx.showToast({ title: '解绑请求已发起', icon: 'success' })
            this.loadPairStatus()
          } catch (e) {
            // 如果已有解绑请求，尝试直接确认
            if (e.message && e.message.includes('已有解绑请求')) {
              try {
                await api.post(`/pairs/confirm-unbind?pair_id=${pairId}`)
                const app = getApp()
                app.globalData.pairInfo = null
                wx.removeStorageSync('pairInfo')
                wx.showToast({ title: '已解除配对', icon: 'success' })
                this.setData({ isPaired: false, pairInfo: null })
              } catch (e2) {
                wx.showToast({ title: e2.message || '操作失败', icon: 'none' })
              }
            } else {
              wx.showToast({ title: e.message || '操作失败', icon: 'none' })
            }
          }
        }
      }
    })
  },

  /**
   * 复制邀请码
   */
  copyInviteCode() {
    const code = this.data.pairInfo && this.data.pairInfo.invite_code
    if (code) {
      wx.setClipboardData({
        data: code,
        success: () => {
          wx.showToast({ title: '已复制', icon: 'success' })
        }
      })
    }
  }
})
