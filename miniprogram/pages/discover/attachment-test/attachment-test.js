/**
 * 依恋风格测试页
 */
Page({
  data: {
    currentQuestion: 0,
    answers: [],
    showResult: false,
    resultType: '',
    
    questions: [
      { q: '当伴侣需要独处时，你会感到？', options: ['担心被抛弃', '理解并尊重', '松了一口气', '无所谓'] },
      { q: '你倾向于如何表达爱意？', options: ['频繁联系和确认', '适度表达', '较少主动', '不太表达'] },
      { q: '当关系变得亲密时，你会？', options: ['感到安心', '保持平衡', '有些不安', '想要逃离'] },
      { q: '伴侣的情绪变化对你影响多大？', options: ['非常大', '比较大', '一般', '较小'] }
    ]
  },

  selectOption(e) {
    const idx = e.currentTarget.dataset.idx
    const answers = [...this.data.answers, idx]
    
    if (this.data.currentQuestion < this.data.questions.length - 1) {
      this.setData({
        currentQuestion: this.data.currentQuestion + 1,
        answers
      })
    } else {
      this.calculateResult(answers)
    }
  },

  calculateResult(answers) {
    const sum = answers.reduce((a, b) => a + b, 0)
    let type = '安全型'
    if (sum <= 4) type = '焦虑型'
    else if (sum <= 8) type = '安全型'
    else if (sum <= 12) type = '回避型'
    else type = '恐惧型'
    
    this.setData({ showResult: true, resultType: type })
  },

  restart() {
    this.setData({
      currentQuestion: 0,
      answers: [],
      showResult: false,
      resultType: ''
    })
  }
})
