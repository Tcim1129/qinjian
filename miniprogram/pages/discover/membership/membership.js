/**
 * 会员订阅页
 */
Page({
  data: {
    plans: [
      { id: 'free', name: '免费版', price: 0, period: '', features: ['每日打卡', '基础报告', '关系树'], recommended: false },
      { id: 'weekly', name: '周报深度版', price: 29, period: '/月', features: ['所有免费功能', '周报深度分析', '情绪趋势图', '优先客服'], recommended: false },
      { id: 'monthly', name: '月报专业版', price: 29.9, period: '/月', features: ['所有周报功能', '月报专业分析', 'AI建议', '专家问答', '无广告'], recommended: true },
      { id: 'yearly', name: '年度会员', price: 199, period: '/年', features: ['所有月报功能', '专属课程', '无限咨询', '优先新功能'], recommended: false }
    ]
  },

  onLoad() {},

  subscribe(e) {
    const id = e.currentTarget.dataset.id
    if (id === 'free') {
      wx.showToast({ title: '您已是免费用户', icon: 'none' })
      return
    }
    wx.showToast({ title: '支付功能开发中', icon: 'none' })
  }
})
