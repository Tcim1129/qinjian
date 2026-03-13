/**
 * 配对管理页
 * 未配对：输入邀请码 + 创建/加入配对
 * 已配对：伴侣信息、关系统计、解除配对
 */
const api = require('../../utils/api.js')
const auth = require('../../utils/auth.js')
const { syncUserAndPair, normalizePair } = require('../../utils/user-sync.js')

Page({
  data: {
    // 配对状态
    isPaired: false,
    pairInfo: null,
    partnerDisplay: '伴侣',
    partnerInitial: '❤',
    pairList: [],

    // 未配对表单
    inviteCode: '',

    // 加载状态
    loading: true,
    creating: false,
    joining: false,

    // 自定义昵称
    customNicknameInput: '',
    showNicknameModal: false,

    // 奶油风 UI 专属数据
    notices: [
      "恭喜 242***打卡挑战成功奖励 1520元",
      "用户 '小木' 刚刚完成了 7 天亲密打卡",
      "今日已有 1284 对情侣通过 AI 陪伴完成记录"
    ],
    featureIcons: [
      { name: '蜜语聊天', icon: '💬', bg: '#E3F2FD' },
      { name: '情侣定位', icon: '📍', bg: '#FCE4EC' },
      { name: '恋爱日记', icon: '📒', bg: '#E8F5E9' },
      { name: '私密相册', icon: '🖼️', bg: '#FFF3E0' },
      { name: '一起养娃', icon: '🍼', bg: '#F3E5F5' },
      { name: '一起睡', icon: '🌙', bg: '#EDE7F6' },
      { name: '打卡赚钱', icon: '💰', bg: '#FFFDE7' },
      { name: '答题赚钱', icon: '❓', bg: '#F1F8E9' },
      { name: '结婚登记', icon: '💍', bg: '#FCE4EC' },
      { name: '想你', icon: '☁️', bg: '#E1F5FE' },
      { name: '恋爱课堂', icon: '🎓', bg: '#E8EAF6' },
      { name: '纪念日提醒', icon: '📅', bg: '#FFEBEE' },
      { name: '恩爱果园', icon: '🌳', bg: '#E8F5E9' },
      { name: '姨妈助手', icon: '🩸', bg: '#FCE4EC' },
      { name: '生你气', icon: '😤', bg: '#FFF3E0' },
      { name: '恋爱记账本', icon: '📒', bg: '#F9FBE7' },
      { name: '恋爱清单', icon: '📜', bg: '#E0F2F1' },
      { name: '许愿', icon: '🎋', bg: '#F3E5F5' },
      { name: '一起看爽片', icon: '🎬', bg: '#EFEBE9' },
      { name: '秀恩爱', icon: '💜', bg: '#FCE4EC' }
    ]
  },

  onLoad() {
    if (!auth.checkLogin()) return
    this.loadPairStatus()
  },

  onShow() {
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
      const pairs = (Array.isArray(res) ? res : [res]).map(normalizePair)
      const activePair = pairs.find(p => p.status === 'active') || pairs[0] || null
      const app = getApp()
      if (activePair) {
        const displayName = activePair.partner_nickname || activePair.partner_name || activePair.partnerNickname || '伴侣'
        app.setPairInfo(activePair)
        this.setData({
          isPaired: activePair.status === 'active',
          pairInfo: activePair,
          partnerDisplay: displayName,
          partnerInitial: displayName ? displayName[0] : '❤',
          pairList: pairs
        })
      } else {
        app.setPairInfo(null)
        this.setData({ isPaired: false, pairInfo: null, partnerDisplay: '伴侣', partnerInitial: '❤', pairList: [] })
      }
    } catch (e) {
      if (e.code === 404) {
        this.setData({ isPaired: false, pairInfo: null, partnerDisplay: '伴侣', partnerInitial: '❤', pairList: [] })
      } else {
        console.error('获取配对状态失败:', e)
      }
    } finally {
      this.setData({ loading: false })
    }
  },

  setCurrentPair(e) {
    const pair = e.currentTarget.dataset.pair
    if (!pair) return
    const displayName = pair.partner_nickname || pair.partner_name || pair.partnerNickname || '伴侣'
    const app = getApp()
    app.setPairInfo(pair)
    this.setData({
      pairInfo: pair,
      partnerDisplay: displayName,
      partnerInitial: displayName ? displayName[0] : '❤'
    })
    wx.showToast({ title: '已切换配对', icon: 'success' })
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
      app.setPairInfo(normalizePair(res))
      await syncUserAndPair()
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
  },

  /**
   * 显示设置备注名弹窗
   */
  showSetNicknameModal() {
    const currentNickname = this.data.pairInfo?.custom_partner_nickname || ''
    this.setData({
      showNicknameModal: true,
      customNicknameInput: currentNickname
    })
  },

  /**
   * 隐藏设置备注名弹窗
   */
  hideNicknameModal() {
    this.setData({ showNicknameModal: false })
  },

  /**
   * 输入自定义昵称
   */
  onNicknameInput(e) {
    this.setData({ customNicknameInput: e.detail.value })
  },

  /**
   * 保存自定义昵称
   */
  async saveCustomNickname() {
    const pairId = this.data.pairInfo?.id || this.data.pairInfo?.pair_id
    if (!pairId) {
      wx.showToast({ title: '配对信息异常', icon: 'none' })
      return
    }

    const nickname = this.data.customNicknameInput.trim()
    
    try {
      const res = await api.post(`/pairs/${pairId}/partner-nickname`, {
        custom_nickname: nickname
      })
      const normalized = normalizePair(res)
      
      // 更新本地数据
      const app = getApp()
      app.setPairInfo(normalized)
      
      const displayName = nickname || normalized.partner_nickname || '伴侣'
      this.setData({
        pairInfo: normalized,
        partnerDisplay: displayName,
        partnerInitial: displayName ? displayName[0] : '❤',
        showNicknameModal: false
      })
      
      wx.showToast({ title: '备注名已保存', icon: 'success' })
    } catch (e) {
      wx.showToast({ title: e.message || '保存失败', icon: 'none' })
    }
  }
})
