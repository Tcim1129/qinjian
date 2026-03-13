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
    ],
    // 快速导航 (参考图 2)
    quickNavs: [
      { name: '测评', icon: '📝' },
      { name: '读书会', icon: '📔' },
      { name: '文章', icon: '📄' },
      { name: '问答', icon: '❓' },
      { name: '冥想', icon: '🧘' }
    ],
    // 限时福利 (参考图 2)
    benefits: [
      { id: 1, title: '心理咨询半价', tag: '每人仅限1次', price: '199', img: '🏡' },
      { id: 2, title: '倾诉首单优惠', tag: '1v1即时情绪疏解', price: '59', img: '🦊' },
      { id: 3, title: '21天关系修复营', tag: '限时 3 折', price: '299', img: '🏕️' }
    ]
  },

  onLoad() {
    // 发现页无需特殊初始化
  },

  onShow() {
    if (typeof this.getTabBar === 'function' && this.getTabBar()) {
      this.getTabBar().setData({ selected: 2 })
    }
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
