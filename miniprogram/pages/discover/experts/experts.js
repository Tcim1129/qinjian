/**
 * 专家咨询页
 */
Page({
  data: {
    experts: [
      { id: 1, name: '李医生', title: '心理咨询师', specialty: '情感问题、沟通障碍', rating: 4.9, consults: 328, price: 199 },
      { id: 2, name: '王老师', title: '婚姻家庭咨询师', specialty: '婚姻危机、家庭关系', rating: 4.8, consults: 256, price: 169 },
      { id: 3, name: '张博士', title: '心理学博士', specialty: '亲密关系、自我成长', rating: 4.9, consults: 412, price: 299 }
    ]
  },

  onLoad() {},

  consult(e) {
    const id = e.currentTarget.dataset.id
    wx.showToast({ title: '咨询功能开发中', icon: 'none' })
  }
})
