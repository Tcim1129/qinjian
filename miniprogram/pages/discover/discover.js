/**
 * 体检页 - AI 能力与正式评估入口
 */
Page({
  data: {
    heroActions: [
      {
        id: 'health',
        icon: '🩺',
        title: '正式周体检',
        desc: '提交本周关系评估，形成更稳定的趋势判断。',
        path: '/pages/discover/health-test/health-test'
      },
      {
        id: 'report',
        icon: '📊',
        title: '打开关系报告',
        desc: '查看系统如何把记录和体检转成建议。',
        path: '/pages/report/report',
        isTab: true
      }
    ],
    coreModules: [
      {
        id: 'health',
        icon: '💚',
        title: '关系健康测试',
        desc: '正式提交本周评估，进入后续趋势分析。',
        path: '/pages/discover/health-test/health-test'
      },
      {
        id: 'timeline',
        icon: '🕒',
        title: '关系时间轴',
        desc: '回看记录、报告和关键事件如何串联。',
        path: '/pages/timeline/timeline'
      },
      {
        id: 'privacy',
        icon: '🔒',
        title: '隐私与边界',
        desc: '查看数据权限、删除请求与安全边界说明。',
        path: '/pages/privacy/privacy'
      }
    ],
    supportModules: [
      {
        id: 'attachment',
        icon: '🔗',
        title: '依恋测试',
        desc: '补充理解彼此在关系中的反应模式。',
        path: '/pages/discover/attachment-test/attachment-test'
      },
      {
        id: 'longdistance',
        icon: '🌏',
        title: '异地支持',
        desc: '为长期异地关系提供节奏和连接建议。',
        path: '/pages/discover/longdistance/longdistance'
      },
      {
        id: 'experts',
        icon: '🧑‍⚕️',
        title: '专业支持',
        desc: '当系统建议转人工时，可以继续了解服务入口。',
        path: '/pages/discover/experts/experts'
      },
      {
        id: 'courses',
        icon: '📚',
        title: '结构化课程',
        desc: '把关系议题拆成更可执行的学习路径。',
        path: '/pages/discover/courses/courses'
      },
      {
        id: 'community',
        icon: '👥',
        title: '案例社区',
        desc: '看他人经验，但不替代你们自己的判断。',
        path: '/pages/discover/community/community'
      },
      {
        id: 'membership',
        icon: '👑',
        title: '会员与专项计划',
        desc: '延展功能与长期陪伴入口。',
        path: '/pages/discover/membership/membership'
      }
    ]
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 2 })
    }
  },

  openPath(e) {
    const { path, istab } = e.currentTarget.dataset
    if (!path) return
    if (istab) {
      wx.switchTab({ url: path })
      return
    }
    wx.navigateTo({ url: path })
  },

  goCheckin() {
    wx.switchTab({ url: '/pages/checkin/checkin' })
  },

  goProfile() {
    wx.switchTab({ url: '/pages/profile/profile' })
  }
})
