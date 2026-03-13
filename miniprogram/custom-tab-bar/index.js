Component({
  data: {
    selected: 0,
    color: '#BCAAA4',
    selectedColor: '#5D4037',
    list: [
      { pagePath: '/pages/home/home', text: '首页', icon: '/images/tab-home.png', selectedIcon: '/images/tab-home-active.png' },
      { pagePath: '/pages/checkin/checkin', text: '打卡', icon: '/images/tab-checkin.png', selectedIcon: '/images/tab-checkin-active.png' },
      { pagePath: '/pages/discover/discover', text: '发现', icon: '/images/tab-discover.png', selectedIcon: '/images/tab-discover-active.png' },
      { pagePath: '/pages/report/report', text: '报告', icon: '/images/tab-report.png', selectedIcon: '/images/tab-report-active.png' },
      { pagePath: '/pages/profile/profile', text: '我的', icon: '/images/tab-profile.png', selectedIcon: '/images/tab-profile-active.png' },
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
