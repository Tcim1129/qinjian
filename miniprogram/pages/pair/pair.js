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

    // WXML 兼容派生字段
    inviteCodeDisplay: '------',
    hasInviteDraft: false,
    bindBtnClass: '',
    pairTypeText: '情侣',
    hasPartnerContact: false,
    partnerContact: '',
    pairCreatedAt: '--',
    hasPartnerId: false,
    checkinDays: '0',
    relationshipDays: '0',
    hasInviteCode: false,
    joinBtnText: '加入配对',

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
      '双人空间建立后，体检、报告与时间轴会共享同一段关系上下文',
      '邀请码只用于建立双方关系档案，不会公开你的私密记录',
      '配对完成后，系统会把双方的记录放进同一条关系主线'
    ],
    featureIcons: [
      { name: '共同记录', icon: '✍', bg: '#EAF1FB' },
      { name: '周体检', icon: '🩺', bg: '#F4ECE3' },
      { name: '关系报告', icon: '📊', bg: '#E7F3EE' },
      { name: '时间轴', icon: '🕒', bg: '#F6EEF7' },
      { name: '叙事对齐', icon: '🧭', bg: '#FFF2E6' },
      { name: '修复建议', icon: '🧩', bg: '#EEF4FD' }
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
      const activePair = pairs.find(p => p.status === 'active') || null
      const pendingPair = pairs.find(p => p.status === 'pending') || null
      const app = getApp()
      if (activePair) {
        const displayName = activePair.partner_nickname || activePair.partner_name || activePair.partnerNickname || '伴侣'
        app.setPairInfo(activePair)
        this.setData({
          isPaired: true,
          pairInfo: activePair,
          partnerDisplay: displayName,
          partnerInitial: displayName ? displayName[0] : '❤',
          pairList: pairs.map(p => this.enrichPairItem(p)),
          // WXML 兼容派生字段
          pairTypeText: this.getPairTypeText(activePair.type),
          hasPartnerContact: !!(activePair.partner_email || activePair.partner_phone),
          partnerContact: activePair.partner_phone || activePair.partner_email || '',
          pairCreatedAt: activePair.created_at || '--',
          hasPartnerId: !!activePair.partner_id,
          checkinDays: String(activePair.checkin_days || 0),
          relationshipDays: String(activePair.relationship_days || 0),
          hasInviteCode: !!activePair.invite_code,
          joinBtnText: '加入配对',
          inviteCodeDisplay: activePair.invite_code || '------',
          hasInviteDraft: !!activePair.invite_code
        })
      } else if (pendingPair) {
        // 有 pending 配对：显示邀请码供分享
        app.setPairInfo(null)
        this.setData({
          isPaired: false,
          pairInfo: pendingPair,
          partnerDisplay: '伴侣',
          partnerInitial: '❤',
          pairList: pairs.map(p => this.enrichPairItem(p)),
          // WXML 兼容派生字段
          inviteCodeDisplay: pendingPair.invite_code || '------',
          hasInviteDraft: !!pendingPair.invite_code,
          bindBtnClass: this.data.inviteCode.length >= 6 ? 'active' : '',
          joinBtnText: '加入配对'
        })
      } else {
        app.setPairInfo(null)
        this.setData({
          isPaired: false,
          pairInfo: null,
          partnerDisplay: '伴侣',
          partnerInitial: '❤',
          pairList: [],
          // WXML 兼容派生字段
          inviteCodeDisplay: '------',
          hasInviteDraft: false,
          bindBtnClass: '',
          joinBtnText: '加入配对'
        })
      }
    } catch (e) {
      if (e.code === 404) {
        this.setData({
          isPaired: false,
          pairInfo: null,
          partnerDisplay: '伴侣',
          partnerInitial: '❤',
          pairList: [],
          inviteCodeDisplay: '------',
          hasInviteDraft: false,
          bindBtnClass: '',
          joinBtnText: '加入配对'
        })
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
      partnerInitial: displayName ? displayName[0] : '❤',
      pairTypeText: this.getPairTypeText(pair.type),
      hasPartnerContact: !!(pair.partner_email || pair.partner_phone),
      partnerContact: pair.partner_phone || pair.partner_email || '',
      pairCreatedAt: pair.created_at || '--',
      hasPartnerId: !!pair.partner_id,
      checkinDays: String(pair.checkin_days || 0),
      relationshipDays: String(pair.relationship_days || 0),
      hasInviteCode: !!pair.invite_code,
      inviteCodeDisplay: pair.invite_code || '------'
    })
    wx.showToast({ title: '已切换配对', icon: 'success' })
  },

  /**
   * 邀请码输入
   */
  onInviteCodeInput(e) {
    const value = e.detail.value
    this.setData({
      inviteCode: value,
      bindBtnClass: value.length >= 6 ? 'active' : ''
    })
  },

  /**
   * 获取配对类型文本
   */
  getPairTypeText(type) {
    if (type === 'spouse') return '夫妻'
    if (type === 'bestfriend') return '挚友'
    if (type === 'parent') return '亲子'
    return '情侣'
  },

  /**
   * 获取配对状态文本
   */
  getPairStatusText(status) {
    if (status === 'pending') return '待确认'
    if (status === 'inactive') return '未激活'
    if (status === 'unbinding') return '解绑处理中'
    return '已激活'
  },

  /**
   * 为配对列表项添加 WXML 兼容字段
   */
  enrichPairItem(item) {
    return {
      ...item,
      partnerDisplayName: item.partner_nickname || item.partner_name || item.partnerNickname || '伴侣',
      typeText: this.getPairTypeText(item.type),
      statusText: this.getPairStatusText(item.status)
    }
  },

  /**
   * 创建配对（生成邀请码）
   */
  async createPair() {
    if (this.data.creating) return
    this.setData({ creating: true })

    try {
      const res = await api.post('/pairs/create', { type: 'couple' })
      this.setData({
        inviteCodeDisplay: res.invite_code || res.code || '------',
        hasInviteDraft: !!(res.invite_code || res.code)
      })
      wx.showModal({
        title: '配对码已生成',
        content: `请将此配对码分享给伴侣：${res.invite_code || res.code}`,
        showCancel: false,
        confirmColor: '#214B8F'
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

    this.setData({ joining: true, joinBtnText: '加入中...' })

    try {
      const res = await api.post('/pairs/join', { invite_code: code })
      const app = getApp()
      app.setPairInfo(normalizePair(res))
      await syncUserAndPair()
      wx.showToast({ title: '配对成功！', icon: 'success' })
      this.loadPairStatus()
    } catch (e) {
      wx.showToast({ title: e.message || '加入失败', icon: 'none' })
      this.setData({ joinBtnText: '加入配对' })
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
    const code = (this.data.pairInfo && this.data.pairInfo.invite_code) || this.data.inviteCodeDisplay
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
    const currentNickname = (this.data.pairInfo && this.data.pairInfo.custom_partner_nickname) || ''
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
    const pairId = this.data.pairInfo && (this.data.pairInfo.id || this.data.pairInfo.pair_id)
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
      
      const displayName = normalized.partner_nickname || '伴侣'
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
