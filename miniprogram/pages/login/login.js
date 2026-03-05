/**
 * 登录/注册页
 * Tab 切换：登录 / 注册
 * 登录：邮箱 + 密码
 * 注册：邮箱 + 密码 + 确认密码 + 昵称
 */
const api = require('../../utils/api.js')

Page({
  data: {
    currentTab: 'login',

    loginMode: 'email',
    regMode: 'email',

    loginEmail: '',
    loginPassword: '',
    loginPhone: '',
    loginCode: '',

    regEmail: '',
    regPassword: '',
    regPasswordConfirm: '',
    regNickname: '',
    regPhone: '',
    regCode: '',

    submitting: false,
    showLoginPwd: false,
    showRegPwd: false
  },

  onLoad() {
    const app = getApp()
    if (app.globalData.isLoggedIn) {
      wx.switchTab({ url: '/pages/home/home' })
    }
  },

  switchTab(e) {
    this.setData({ currentTab: e.currentTarget.dataset.tab })
  },

  switchLoginMode(e) {
    this.setData({ loginMode: e.currentTarget.dataset.mode })
  },

  switchRegMode(e) {
    this.setData({ regMode: e.currentTarget.dataset.mode })
  },

  onLoginEmailInput(e) {
    this.setData({ loginEmail: e.detail.value })
  },

  onLoginPasswordInput(e) {
    this.setData({ loginPassword: e.detail.value })
  },

  onLoginPhoneInput(e) {
    this.setData({ loginPhone: e.detail.value })
  },

  onLoginCodeInput(e) {
    this.setData({ loginCode: e.detail.value })
  },

  toggleLoginPwd() {
    this.setData({ showLoginPwd: !this.data.showLoginPwd })
  },

  onRegEmailInput(e) {
    this.setData({ regEmail: e.detail.value })
  },

  onRegPasswordInput(e) {
    this.setData({ regPassword: e.detail.value })
  },

  onRegPasswordConfirmInput(e) {
    this.setData({ regPasswordConfirm: e.detail.value })
  },

  onRegNicknameInput(e) {
    this.setData({ regNickname: e.detail.value })
  },

  onRegPhoneInput(e) {
    this.setData({ regPhone: e.detail.value })
  },

  onRegCodeInput(e) {
    this.setData({ regCode: e.detail.value })
  },

  toggleRegPwd() {
    this.setData({ showRegPwd: !this.data.showRegPwd })
  },

  async handleLogin() {
    const { loginEmail, loginPassword, loginMode, loginPhone, loginCode } = this.data

    if (loginMode === 'email') {
      if (!loginEmail.trim()) {
        wx.showToast({ title: '请输入邮箱', icon: 'none' })
        return
      }
      if (!loginPassword) {
        wx.showToast({ title: '请输入密码', icon: 'none' })
        return
      }
    } else {
      if (!loginPhone.trim()) {
        wx.showToast({ title: '请输入手机号', icon: 'none' })
        return
      }
      if (!loginCode.trim()) {
        wx.showToast({ title: '请输入验证码', icon: 'none' })
        return
      }
    }

    this.setData({ submitting: true })

    try {
      const res = loginMode === 'email'
        ? await api.post('/auth/login', {
            email: loginEmail.trim(),
            password: loginPassword
          })
        : await api.post('/auth/phone/login', {
            phone: loginPhone.trim(),
            code: loginCode.trim()
          })

      const app = getApp()
      app.setLoginState(res.access_token || res.token, res.user || res)
      try {
        const pairs = await api.get('/pairs/me')
        const list = Array.isArray(pairs) ? pairs : [pairs]
        const activePair = list.find(p => p.status === 'active') || list[0] || null
        if (activePair) {
          app.setPairInfo(activePair)
        }
      } catch (e2) {
        console.warn('获取配对信息失败', e2)
      }

      wx.showToast({ title: '登录成功', icon: 'success' })

      setTimeout(() => {
        wx.switchTab({ url: '/pages/home/home' })
      }, 800)
    } catch (e) {
      wx.showToast({ title: e.message || '登录失败', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  },

  async handleRegister() {
    const {
      regMode,
      regEmail,
      regPassword,
      regPasswordConfirm,
      regNickname,
      regPhone,
      regCode
    } = this.data

    if (regMode === 'email') {
      if (!regEmail.trim()) {
        wx.showToast({ title: '请输入邮箱', icon: 'none' })
        return
      }
      if (!regPassword || regPassword.length < 6) {
        wx.showToast({ title: '密码至少6位', icon: 'none' })
        return
      }
      if (regPassword !== regPasswordConfirm) {
        wx.showToast({ title: '两次密码不一致', icon: 'none' })
        return
      }
    } else {
      if (!regPhone.trim()) {
        wx.showToast({ title: '请输入手机号', icon: 'none' })
        return
      }
      if (!regCode.trim()) {
        wx.showToast({ title: '请输入验证码', icon: 'none' })
        return
      }
    }
    if (!regNickname.trim()) {
      wx.showToast({ title: '请输入昵称', icon: 'none' })
      return
    }

    this.setData({ submitting: true })

    try {
      if (regMode === 'email') {
        await api.post('/auth/register', {
          email: regEmail.trim(),
          password: regPassword,
          nickname: regNickname.trim()
        })

        wx.showToast({ title: '注册成功，请登录', icon: 'success' })

        this.setData({
          currentTab: 'login',
          loginEmail: regEmail.trim()
        })
      } else {
        const res = await api.post('/auth/phone/login', {
          phone: regPhone.trim(),
          code: regCode.trim()
        })
        const app = getApp()
        app.setLoginState(res.access_token || res.token, res.user || res)
        wx.showToast({ title: '注册成功', icon: 'success' })
        setTimeout(() => {
          wx.switchTab({ url: '/pages/home/home' })
        }, 800)
      }
    } catch (e) {
      wx.showToast({ title: e.message || '注册失败', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  },

  async sendPhoneCode() {
    const { loginPhone } = this.data
    if (!loginPhone.trim()) {
      wx.showToast({ title: '请输入手机号', icon: 'none' })
      return
    }
    try {
      await api.post('/auth/phone/send-code', { phone: loginPhone.trim() })
      wx.showToast({ title: '验证码已发送(测试码123456)', icon: 'none' })
    } catch (e) {
      wx.showToast({ title: e.message || '发送失败', icon: 'none' })
    }
  },

  async sendRegPhoneCode() {
    const { regPhone } = this.data
    if (!regPhone.trim()) {
      wx.showToast({ title: '请输入手机号', icon: 'none' })
      return
    }
    try {
      await api.post('/auth/phone/send-code', { phone: regPhone.trim() })
      wx.showToast({ title: '验证码已发送(测试码123456)', icon: 'none' })
    } catch (e) {
      wx.showToast({ title: e.message || '发送失败', icon: 'none' })
    }
  },

  async handleWechatLogin() {
    if (this.data.submitting) return
    this.setData({ submitting: true })

    try {
      const loginRes = await wx.login()
      if (!loginRes.code) {
        wx.showToast({ title: '微信登录失败', icon: 'none' })
        this.setData({ submitting: false })
        return
      }

      const userProfile = await wx.getUserProfile({
        desc: '用于完善资料与生成关系报告'
      })

      const res = await api.post('/auth/wechat/login', {
        code: loginRes.code,
        nickname: userProfile.userInfo.nickName,
        avatar_url: userProfile.userInfo.avatarUrl
      })

      const app = getApp()
      app.setLoginState(res.access_token || res.token, res.user || res)
      try {
        const pairs = await api.get('/pairs/me')
        const list = Array.isArray(pairs) ? pairs : [pairs]
        const activePair = list.find(p => p.status === 'active') || list[0] || null
        if (activePair) {
          app.setPairInfo(activePair)
        }
      } catch (e2) {
        console.warn('获取配对信息失败', e2)
      }

      wx.showToast({ title: '登录成功', icon: 'success' })
      setTimeout(() => {
        wx.switchTab({ url: '/pages/home/home' })
      }, 800)
    } catch (e) {
      wx.showToast({ title: e.message || '微信登录失败', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  }
})
