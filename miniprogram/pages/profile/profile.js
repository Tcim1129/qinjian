/**
 * 个人中心页 - 用户信息与功能菜单
 * 展示头像、昵称、配对状态，提供各功能入口
 */
const auth = require('../../utils/auth.js')

Page({
  data: {
    userInfo: null,
    pairInfo: null,
    isPaired: false,

    // 菜单列表
    menuItems: [
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
    this.loadUserInfo()
  },

  /**
   * 从全局数据加载用户信息
   */
  loadUserInfo() {
    const app = getApp()
    const userInfo = app.globalData.userInfo
    const pairInfo = app.globalData.pairInfo

    this.setData({
      userInfo: userInfo,
      pairInfo: pairInfo,
      isPaired: !!(pairInfo && pairInfo.pair_id)
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
      content: '亲健 v1.0.0\n青年亲密关系健康管理专家\n让爱有据可循',
      showCancel: false,
      confirmColor: '#6C5CE7'
    })
  }
})
