/**
 * 个人中心页 - 用户信息与功能菜单
 * 展示头像、昵称、配对状态，提供各功能入口
 */
const auth = require('../../utils/auth.js')
const { syncUserAndPair, normalizePair } = require('../../utils/user-sync.js')

Page({
  data: {
    userInfo: null,
    pairInfo: null,
    isPaired: false,

    // 菜单列表
    menuItems: [
      { id: 'edit-name', title: '修改名称', icon: '✏️', path: '' },
      { id: 'change-password', title: '修改密码', icon: '🔒', path: '' },
      { id: 'pair', title: '配对管理', icon: '🤝', path: '/pages/pair/pair' },
      { id: 'tree', title: '关系树', icon: '🌳', path: '/pages/tree/tree' },
      { id: 'milestone', title: '里程碑', icon: '🏅', path: '/pages/milestone/milestone' },
      { id: 'history', title: '打卡历史', icon: '📅', path: '' },
      { id: 'membership', title: '会员订阅', icon: '👑', path: '/pages/discover/membership/membership' },
      { id: 'about', title: '关于亲健', icon: 'ℹ️', path: '' },
      { id: 'logout', title: '退出登录', icon: '🚪', path: '' }
    ]
  },

  onLoad() {
    // 初始化
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 4 })
    }
    this.refreshData()
  },

  /**
   * 刷新数据，包括用户信息和最新的配对状态
   */
  async refreshData() {
    try {
      const synced = await syncUserAndPair()
      this.setData({
        userInfo: synced.userInfo,
        pairInfo: synced.pairInfo,
        isPaired: !!(synced.summary && synced.summary.is_paired)
      })
      if (!synced.summary) {
        this.loadLocalData()
      }
    } catch (e) {
      console.warn('Profile拉取配对状态失败', e)
      this.loadLocalData()
    }
  },

  /**
   * 从全局数据加载本地缓存的信息
   */
  loadLocalData() {
    const app = getApp()
    const userInfo = app.globalData.userInfo
    const pairInfo = app.globalData.pairInfo
    const normalizedPair = normalizePair(pairInfo)

    this.setData({
      userInfo: userInfo,
      pairInfo: normalizedPair,
      isPaired: !!(normalizedPair && normalizedPair.status === 'active' && (normalizedPair.id || normalizedPair.pair_id))
    })
  },

  /**
   * 菜单项点击处理
   */
  onMenuTap(e) {
    const id = e.currentTarget.dataset.id
    const path = e.currentTarget.dataset.path

    switch (id) {
      case 'logout':
        this.handleLogout()
        break
      case 'about':
        this.showAbout()
        break
      case 'history':
        this.goCheckinHistory()
        break
      case 'edit-name':
        this.editName()
        break
      case 'change-password':
        this.changePassword()
        break
      default:
        if (path) {
          wx.navigateTo({ url: path })
        }
        break
    }
  },

  /**
   * 退出登录
   */
  handleLogout() {
    wx.showModal({
      title: '提示',
      content: '确定要退出登录吗？',
      confirmColor: '#6C5CE7',
      success: (res) => {
        if (res.confirm) {
          const app = getApp()
          app.logout()
          wx.reLaunch({ url: '/pages/login/login' })
        }
      }
    })
  },

  /**
   * 查看打卡历史（跳转到打卡页或单独页面）
   */
  goCheckinHistory() {
    // 暂时跳转到打卡tab
    wx.switchTab({ url: '/pages/checkin/checkin' })
  },

  /**
   * 关于亲健
   */
  showAbout() {
    wx.showModal({
      title: '关于亲健',
      content: '亲健 v2.8.0\n青年亲密关系健康管理专家\n让爱有据可循',
      showCancel: false,
      confirmColor: '#6C5CE7'
    })
  },

  editName() {
    wx.showModal({
      title: '修改名称',
      editable: true,
      placeholderText: '输入新的昵称',
      content: this.data.userInfo?.nickname || '',
      success: async (res) => {
        if (!res.confirm) return
        const nickname = (res.content || '').trim()
        if (!nickname) {
          wx.showToast({ title: '昵称不能为空', icon: 'none' })
          return
        }
        try {
          const api = require('../../utils/api.js')
          const updated = await api.put('/auth/me', { nickname })
          const app = getApp()
          app.globalData.userInfo = updated
          wx.setStorageSync('userInfo', updated)
          this.setData({ userInfo: updated })
          wx.showToast({ title: '名称已更新', icon: 'success' })
        } catch (e) {
          wx.showToast({ title: e.message || '保存失败', icon: 'none' })
        }
      }
    })
  },

  changePassword() {
    wx.showToast({ title: '请在网页版或App中修改密码', icon: 'none' })
  }
})
