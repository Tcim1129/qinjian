/**
 * 关系健康测试页
 */
Page({
  data: {
    currentQuestion: 0,
    answers: [],
    showResult: false,
    score: 0,
    
    questions: [
      { q: '你们多久进行一次深入交流？', options: ['每天', '每周几次', '每月几次', '很少'] },
      { q: '发生冲突时，你们通常如何处理？', options: ['坦诚沟通解决', '冷静后讨论', '回避或冷战', '经常争吵'] },
      { q: '你对这段关系的满意度如何？', options: ['非常满意', '比较满意', '一般', '不太满意'] },
      { q: '你们是否有共同的目标和规划？', options: ['有明确规划', '有一些讨论', '很少讨论', '没有'] },
      { q: '你感到被伴侣理解和支持吗？', options: ['总是', '经常', '偶尔', '很少'] }
    ]
  },

  selectOption(e) {
    const idx = e.currentTarget.dataset.idx
    const answers = [...this.data.answers, 4 - idx]
    
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
    const score = answers.reduce((a, b) => a + b, 0)
    this.setData({ showResult: true, score })
  },

  restart() {
    this.setData({
      currentQuestion: 0,
      answers: [],
      showResult: false,
      score: 0
    })
  }
})
