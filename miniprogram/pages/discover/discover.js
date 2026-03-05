/**
 * 发现页 - 功能入口导航
 * 8个功能卡片网格布局，点击跳转对应子页面
 */
Page({
  data: {
    // 功能卡片列表
    features: [
      {
        id: 'longdistance',
        icon: '🌏',
        title: '异地恋工具',
        desc: '距离不是问题',
        path: '/pages/discover/longdistance/longdistance'
      },
      {
        id: 'attachment',
        icon: '🔗',
        title: '依恋测试',
        desc: '了解依恋风格',
        path: '/pages/discover/attachment-test/attachment-test'
      },
      {
        id: 'health',
        icon: '💚',
        title: '关系健康测试',
        desc: '全面健康评估',
        path: '/pages/discover/health-test/health-test'
      },
      {
        id: 'community',
        icon: '👥',
        title: '关系社区',
        desc: '经验分享交流',
        path: '/pages/discover/community/community'
      },
      {
        id: 'challenges',
        icon: '🏆',
        title: '关系挑战赛',
        desc: '趣味互动任务',
        path: '/pages/discover/challenges/challenges'
      },
      {
        id: 'courses',
        icon: '📚',
        title: '精品课程',
        desc: '专业关系指导',
        path: '/pages/discover/courses/courses'
      },
      {
        id: 'experts',
        icon: '🧑‍⚕️',
        title: '专家咨询',
        desc: '一对一答疑',
        path: '/pages/discover/experts/experts'
      },
      {
        id: 'membership',
        icon: '👑',
        title: '会员订阅',
        desc: '解锁全部功能',
        path: '/pages/discover/membership/membership'
      }
    ]
  },

  onLoad() {
    // 发现页无需特殊初始化
  },

  /**
   * 跳转到功能子页面
   */
  goFeature(e) {
    const path = e.currentTarget.dataset.path
    if (path) {
      wx.navigateTo({ url: path })
    }
  }
})
