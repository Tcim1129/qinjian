const api = require('../../../utils/api.js')
const auth = require('../../../utils/auth.js')

const QUESTIONS = [
  {
    dim: '沟通质量',
    prompt: '过去一周，你们在重要话题上能把话说清楚吗？',
    hint: '不是看有没有分歧，而是看能不能说到彼此都听懂。'
  },
  {
    dim: '情感支持',
    prompt: '最近遇到压力时，你感到被理解和接住了吗？',
    hint: '这代表关系里的陪伴感，而不只是是否天天聊天。'
  },
  {
    dim: '信任程度',
    prompt: '你对这段关系的可靠感和安全感如何？',
    hint: '如果最近反复猜测、担心失联，这一项通常会下降。'
  },
  {
    dim: '修复能力',
    prompt: '出现摩擦后，你们能否比较快地修复关系氛围？',
    hint: '关键不是不争执，而是争执后有没有回到可沟通状态。'
  },
  {
    dim: '共同愿景',
    prompt: '你们对于接下来这段关系往哪走，有没有比较一致的预期？',
    hint: '一致感越强，系统越容易给出更积极的推进建议。'
  }
]

const OPTIONS = [
  { label: '明显卡住', caption: '这块最近经常失衡', score: 35 },
  { label: '偶尔吃力', caption: '有一些基础，但还不稳定', score: 55 },
  { label: '基本稳定', caption: '大多数时候能做到', score: 75 },
  { label: '很有力量', caption: '这是这周关系里的优势', score: 92 }
]

function buildResultView(payload) {
  if (!payload) return null
  const score = Number(payload.total_score || 0)
  let levelLabel = '先让系统多记录几轮，再看更稳定的变化'
  let description = '现在最重要的是继续留下真实记录。'

  if (score >= 82) {
    levelLabel = '这周关系状态很稳'
    description = '可以把注意力放在更深的表达和共同规划上。'
  } else if (score >= 65) {
    levelLabel = '整体还在可修复区间'
    description = '继续维持低摩擦沟通，比急着推进更重要。'
  } else if (score >= 48) {
    levelLabel = '系统建议先减压再推进'
    description = '先修复低分维度，别用更高强度沟通去硬顶。'
  } else {
    levelLabel = '这周需要更强边界和支持'
    description = '这更像高负荷阶段，先把安全感和止损放在前面。'
  }

  return {
    totalScore: score,
    levelLabel,
    description,
    changeSummary: payload.change_summary || '系统已经记录这次正式周评估。',
    dimensions: (payload.dimension_scores || []).map((item) => ({
      id: item.id,
      label: item.label,
      score: item.score,
      status: item.status
    })),
    submittedAt: payload.submitted_at || ''
  }
}

function buildTrendView(payload) {
  if (!payload) return null
  return {
    latestScore: payload.latest_score,
    changeSummary: payload.change_summary,
    points: (payload.trend_points || []).slice(-4).map((item) => ({
      id: item.event_id,
      label: (item.submitted_at || '').slice(5, 10) || '本周',
      score: item.total_score,
      summary: item.change_summary || '系统已记录本次评估'
    })),
    dimensions: (payload.dimension_scores || []).slice(0, 5).map((item) => ({
      id: item.id,
      label: item.label,
      score: item.score
    }))
  }
}

Page({
  data: {
    questions: QUESTIONS,
    options: OPTIONS,
    currentQuestion: 0,
    answers: {},
    loading: false,
    submitting: false,
    showResult: false,
    resultView: null,
    trendView: null,
    safetyStatus: null
  },

  onShow() {
    if (!auth.checkLogin()) return
    this.loadAssessmentOverview()
  },

  async loadAssessmentOverview() {
    this.setData({ loading: true })
    const pairId = auth.getPairId()
    try {
      const [latest, trend, safetyStatus] = await Promise.all([
        api.getWeeklyAssessmentLatest(pairId).catch(() => null),
        api.getWeeklyAssessmentTrend(pairId).catch(() => null),
        api.getSafetyStatus(pairId).catch(() => null)
      ])
      this.setData({
        resultView: buildResultView(latest),
        trendView: buildTrendView(trend),
        safetyStatus,
        showResult: !!latest
      })
    } catch (e) {
      console.warn('assessment overview load failed', e)
    } finally {
      this.setData({ loading: false })
    }
  },

  selectOption(e) {
    if (this.data.submitting) return
    const optionIndex = Number(e.currentTarget.dataset.index)
    const question = this.data.questions[this.data.currentQuestion]
    const option = this.data.options[optionIndex]
    const nextAnswers = Object.assign({}, this.data.answers, {
      [question.dim]: { dim: question.dim, score: option.score }
    })

    if (this.data.currentQuestion < this.data.questions.length - 1) {
      this.setData({
        answers: nextAnswers,
        currentQuestion: this.data.currentQuestion + 1
      })
      return
    }

    this.submitAssessment(nextAnswers)
  },

  async submitAssessment(answerMap) {
    if (this.data.submitting) return
    this.setData({ submitting: true })
    const pairId = auth.getPairId()
    const answers = Object.keys(answerMap).map((key) => answerMap[key])

    try {
      const result = await api.submitWeeklyAssessment(pairId, {
        answers,
        submitted_at: new Date().toISOString()
      })
      wx.showToast({ title: '本周体检已记录', icon: 'success' })
      this.setData({
        answers: answerMap,
        resultView: buildResultView(result),
        showResult: true
      })
      await this.loadAssessmentOverview()
    } catch (e) {
      wx.showToast({ title: e.message || '提交失败', icon: 'none' })
    } finally {
      this.setData({ submitting: false })
    }
  },

  restart() {
    this.setData({
      currentQuestion: 0,
      answers: {},
      showResult: false
    })
  },

  openReport() {
    wx.switchTab({ url: '/pages/report/report' })
  }
})
