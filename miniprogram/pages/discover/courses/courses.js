/**
 * 精品课程页
 */
Page({
  data: {
    courses: [
      { id: 1, title: '有效沟通的艺术', desc: '学习如何与伴侣进行深度对话', duration: '45分钟', level: '入门', price: 0 },
      { id: 2, title: '冲突解决技巧', desc: '化解矛盾，增进理解', duration: '60分钟', level: '进阶', price: 29 },
      { id: 3, title: '亲密关系维护', desc: '保持关系新鲜感的秘诀', duration: '50分钟', level: '进阶', price: 29 },
      { id: 4, title: '异地恋生存指南', desc: '距离不是问题，心在一起', duration: '40分钟', level: '入门', price: 0 }
    ]
  },

  onLoad() {},

  viewCourse(e) {
    const id = e.currentTarget.dataset.id
    wx.showToast({ title: '课程详情开发中', icon: 'none' })
  }
})
