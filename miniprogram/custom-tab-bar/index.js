Component({
  data: {
    selected: 0,
    color: '#7C8393',
    selectedColor: '#214B8F',
    list: [
      { pagePath: '/pages/home/home', text: '首页', icon: '../images/tab-home.svg', selectedIcon: '../images/tab-home-active.svg' },
      { pagePath: '/pages/checkin/checkin', text: '记录', icon: '../images/tab-checkin.svg', selectedIcon: '../images/tab-checkin-active.svg' },
      { pagePath: '/pages/discover/discover', text: '体检', icon: '../images/tab-discover.svg', selectedIcon: '../images/tab-discover-active.svg' },
      { pagePath: '/pages/report/report', text: '报告', icon: '../images/tab-report.svg', selectedIcon: '../images/tab-report-active.svg' },
      { pagePath: '/pages/profile/profile', text: '我的', icon: '../images/tab-profile.svg', selectedIcon: '../images/tab-profile-active.svg' },
    ]
  },
  methods: {
    switchTab(e) {
      const { path, index } = e.currentTarget.dataset
      if (!path) return
      this.setData({ selected: index })
      wx.switchTab({ url: path })
    }
  }
})
