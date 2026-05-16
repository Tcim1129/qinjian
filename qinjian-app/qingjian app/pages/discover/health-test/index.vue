<template>
  <view class="assessment-page">
    <scroll-view class="assessment-scroll" scroll-y>
      <view class="hero-shell">
        <view class="hero-topline">
          <view class="brand-chip">
            <image class="brand-chip__logo" src="../../../static/brand-logo.jpg" mode="aspectFit"></image>
            <view class="brand-chip__copy">
              <text class="brand-chip__eyebrow">QINJIAN APP</text>
              <text class="brand-chip__name">关系体检</text>
            </view>
          </view>
          <text class="back-chip" @click="goBack">返回</text>
        </view>
        <text class="hero-title">把“这周到底怎样”变成正式可追踪的关系评估</text>
        <view class="section-rule"></view>
        <text class="hero-subtitle">提交后，结果会直接写回事件流，影响后续简报、任务强度和策略切换。</text>
      </view>

      <view v-if="loading" class="panel-card">正在整理最近的体检记录...</view>

      <template v-if="!loading && !showResult">
        <view class="panel-card question-card">
          <view class="question-topline">
            <view>
              <text class="section-eyebrow">WEEKLY ASSESSMENT</text>
              <text class="card-title">第 {{ currentQuestion + 1 }} 题 / 共 {{ questions.length }} 题</text>
            </view>
            <text class="progress-text">{{ Math.floor(((currentQuestion + 1) / questions.length) * 100) }}%</text>
          </view>
          <view class="progress-track">
            <view class="progress-fill" :style="{ width: `${((currentQuestion + 1) / questions.length) * 100}%` }"></view>
          </view>
          <text class="question-title">{{ questions[currentQuestion].prompt }}</text>
          <text class="question-copy">{{ questions[currentQuestion].hint }}</text>
          <view class="option-list">
            <view v-for="(item, index) in options" :key="item.label" class="option-card" @click="selectOption(index)">
              <text class="option-title">{{ item.label }}</text>
              <text class="option-copy">{{ item.caption }}</text>
            </view>
          </view>
        </view>

        <view v-if="safetyStatus" class="panel-card">
          <text class="section-eyebrow">BOUNDARY</text>
          <text class="card-title">系统当前的安全边界</text>
          <text class="risk-pill">{{ safetyStatus.risk_level || 'low' }}</text>
          <text class="panel-copy">{{ safetyStatus.why_now }}</text>
        </view>
      </template>

      <template v-if="!loading && showResult && resultView">
        <view class="panel-card result-card">
          <text class="section-eyebrow">LATEST RESULT</text>
          <text class="result-score">{{ resultView.totalScore }}</text>
          <text class="result-unit">/ 100</text>
          <text class="card-title">{{ resultView.levelLabel }}</text>
          <text class="panel-copy">{{ resultView.description }}</text>
          <text class="support-copy">{{ resultView.changeSummary }}</text>
          <view class="result-actions">
            <button class="ghost-btn" @click="restart">重新体检</button>
            <button class="primary-btn" @click="openReport">查看简报</button>
          </view>
        </view>

        <view v-if="resultView.dimensions.length" class="panel-card">
          <text class="section-eyebrow">DIMENSIONS</text>
          <text class="card-title">这次体检最关键的维度</text>
          <view class="mini-grid three-column">
            <view v-for="item in resultView.dimensions" :key="item.id" class="mini-card">
              <text class="mini-label">{{ item.label }}</text>
              <text class="mini-value">{{ item.score !== null && item.score !== undefined ? item.score : '--' }}</text>
              <view class="mini-meter">
                <view class="mini-meter__fill" :style="{ width: `${item.score || 0}%` }"></view>
              </view>
            </view>
          </view>
        </view>
      </template>

      <view v-if="trendView" class="panel-card">
        <text class="section-eyebrow">TREND</text>
        <text class="card-title">近 4 次正式关系体检</text>
        <text class="panel-copy">{{ trendView.changeSummary }}</text>
        <view v-if="trendView.points.length" class="mini-grid two-column">
          <view v-for="item in trendView.points" :key="item.id" class="mini-card">
            <text class="mini-label">{{ item.label }}</text>
            <text class="mini-value">{{ item.score }}</text>
            <text class="mini-copy">{{ item.summary }}</text>
          </view>
        </view>
      </view>

      <view v-if="showResult && safetyStatus" class="panel-card">
        <text class="section-eyebrow">TRUST & BOUNDARY</text>
        <text class="card-title">什么时候该减少依赖系统，转向人工支持</text>
        <text class="panel-copy">{{ safetyStatus.limitation_note }}</text>
        <view v-if="safetyStatus.handoff_recommendation" class="handoff-box">{{ safetyStatus.handoff_recommendation }}</view>
      </view>

      <view class="page-spacer"></view>
    </scroll-view>
  </view>
</template>

<script>
import api from '../../../utils/api.js'
import { syncSession } from '../../../utils/session.js'

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
    hint: '重点不是不争执，而是争执后能不能回到可沟通状态。'
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
  let levelLabel = '先让系统继续积累更多体检记录'
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
      score: item.score
    }))
  }
}

function buildTrendView(payload) {
  if (!payload) return null
  return {
    changeSummary: payload.change_summary,
    points: (payload.trend_points || []).slice(-4).map((item) => ({
      id: item.event_id,
      label: (item.submitted_at || '').slice(5, 10) || '本周',
      score: item.total_score,
      summary: item.change_summary || '系统已记录本次评估'
    }))
  }
}

export default {
  data() {
    return {
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
    }
  },
  computed: {
    pairId() {
      return this.$store.state.pairInfo?.id || null
    }
  },
  onShow() {
    this.bootstrap()
  },
  methods: {
    async bootstrap() {
      if (!api.isLoggedIn()) {
        uni.reLaunch({ url: '/pages/auth/index' })
        return
      }
      try {
        await syncSession(this.$store)
      } catch (error) {
        console.warn('assessment sync failed', error)
      }
      await this.loadAssessmentOverview()
    },
    async loadAssessmentOverview() {
      this.loading = true
      try {
        const [latest, trend, safetyStatus] = await Promise.all([
          api.getWeeklyAssessmentLatest(this.pairId).catch(() => null),
          api.getWeeklyAssessmentTrend(this.pairId).catch(() => null),
          api.getSafetyStatus(this.pairId).catch(() => null)
        ])
        this.resultView = buildResultView(latest)
        this.trendView = buildTrendView(trend)
        this.safetyStatus = safetyStatus
        this.showResult = !!latest
      } catch (error) {
        console.warn('assessment overview failed', error)
      } finally {
        this.loading = false
      }
    },
    selectOption(index) {
      if (this.submitting) return
      const question = this.questions[this.currentQuestion]
      const option = this.options[index]
      const nextAnswers = {
        ...this.answers,
        [question.dim]: { dim: question.dim, score: option.score }
      }

      if (this.currentQuestion < this.questions.length - 1) {
        this.answers = nextAnswers
        this.currentQuestion += 1
        return
      }

      this.submitAssessment(nextAnswers)
    },
    async submitAssessment(answerMap) {
      if (this.submitting) return
      this.submitting = true
      try {
        const result = await api.submitWeeklyAssessment(this.pairId, {
          answers: Object.values(answerMap),
          submitted_at: new Date().toISOString()
        })
        this.answers = answerMap
        this.resultView = buildResultView(result)
        this.showResult = true
        uni.showToast({ title: '本周体检已记录', icon: 'success' })
        await this.loadAssessmentOverview()
      } catch (error) {
        uni.showToast({ title: error.message || '提交失败', icon: 'none' })
      } finally {
        this.submitting = false
      }
    },
    restart() {
      this.currentQuestion = 0
      this.answers = {}
      this.showResult = false
    },
    openReport() {
      uni.reLaunch({ url: '/pages/report/index' })
    },
    goBack() {
      if (getCurrentPages().length > 1) {
        uni.navigateBack()
        return
      }
      uni.reLaunch({ url: '/pages/discover/index' })
    }
  }
}
</script>

<style scoped>
.assessment-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #fff9f3 0%, #f4ede6 100%);
}

.assessment-scroll {
  min-height: 100vh;
  padding: 28rpx 28rpx calc(28rpx + env(safe-area-inset-bottom));
  box-sizing: border-box;
}

.hero-shell,
.panel-card {
  border-radius: 34rpx;
  background: rgba(255, 255, 255, 0.96);
  border: 1rpx solid rgba(212, 163, 115, 0.12);
  box-shadow: 0 18rpx 36rpx rgba(62, 39, 35, 0.08);
}

.hero-shell,
.panel-card {
  padding: 30rpx;
}

.hero-shell {
  background: linear-gradient(145deg, rgba(255, 248, 241, 0.98), rgba(239, 247, 252, 0.92));
  position: relative;
  overflow: hidden;
  animation: assessmentHeroFloat 7.1s ease-in-out infinite;
}

.hero-shell::after {
  content: "";
  position: absolute;
  right: -88rpx;
  top: -96rpx;
  width: 236rpx;
  height: 236rpx;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(212, 163, 115, 0.22), rgba(212, 163, 115, 0));
}

.hero-topline {
  display: flex;
  justify-content: space-between;
  gap: 18rpx;
  align-items: flex-start;
}

.brand-chip {
  display: inline-flex;
  align-items: center;
  gap: 14rpx;
  padding: 12rpx 18rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.82);
  border: 1rpx solid rgba(212, 163, 115, 0.14);
}

.brand-chip__logo {
  width: 64rpx;
  height: 64rpx;
  border-radius: 18rpx;
}

.brand-chip__copy {
  display: flex;
  flex-direction: column;
  gap: 2rpx;
}

.brand-chip__eyebrow,
.section-eyebrow,
.mini-label {
  font-size: 18rpx;
  letter-spacing: 4rpx;
  text-transform: uppercase;
  color: #a1887f;
}

.brand-chip__name,
.card-title {
  font-size: 30rpx;
  font-weight: 800;
  color: #2f2522;
  font-family: "Times New Roman", "Georgia", "Songti SC", serif;
  letter-spacing: 0.4rpx;
}

.back-chip {
  padding: 12rpx 18rpx;
  border-radius: 999rpx;
  background: #f8efe6;
  color: #8d6e63;
  font-size: 20rpx;
  font-weight: 700;
}

.hero-title {
  display: block;
  margin-top: 22rpx;
  font-size: 40rpx;
  line-height: 1.42;
  font-weight: 800;
  color: #2f2522;
  font-family: "Times New Roman", "Georgia", "Songti SC", serif;
  letter-spacing: 0.6rpx;
}

.section-rule {
  width: 96rpx;
  height: 6rpx;
  margin-top: 16rpx;
  border-radius: 999rpx;
  background: linear-gradient(90deg, rgba(212, 163, 115, 0.92), rgba(93, 64, 55, 0.88));
}

.hero-subtitle,
.question-copy,
.panel-copy,
.support-copy,
.mini-copy {
  display: block;
  margin-top: 12rpx;
  font-size: 22rpx;
  line-height: 1.8;
  color: #6d4c41;
}

.panel-card {
  margin-top: 24rpx;
}

.question-topline {
  display: flex;
  justify-content: space-between;
  gap: 18rpx;
  align-items: flex-start;
}

.progress-text {
  font-size: 26rpx;
  font-weight: 800;
  color: #8d6e63;
}

.progress-track {
  height: 10rpx;
  margin-top: 22rpx;
  border-radius: 999rpx;
  background: #f4e9df;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 999rpx;
  background: linear-gradient(90deg, #5d4037, #d4a373);
}

.question-title {
  display: block;
  margin-top: 24rpx;
  font-size: 34rpx;
  line-height: 1.55;
  font-weight: 800;
  color: #3e2723;
}

.option-list,
.result-actions,
.mini-grid {
  display: grid;
  gap: 16rpx;
  margin-top: 22rpx;
}

.option-list {
  grid-template-columns: 1fr;
}

.two-column {
  grid-template-columns: repeat(2, 1fr);
}

.three-column {
  grid-template-columns: repeat(3, 1fr);
}

.option-card,
.mini-card {
  padding: 22rpx;
  border-radius: 24rpx;
  background: #fcf4ed;
  border: 1rpx solid rgba(212, 163, 115, 0.12);
  box-shadow: 0 12rpx 24rpx rgba(93, 64, 55, 0.06);
  transition: transform 0.22s ease, box-shadow 0.22s ease;
}

.option-card:active,
.mini-card:active {
  transform: scale(0.985) translateY(2rpx);
  box-shadow: 0 6rpx 14rpx rgba(93, 64, 55, 0.08);
}

.option-title {
  display: block;
  font-size: 26rpx;
  font-weight: 800;
  color: #3e2723;
}

.option-copy {
  display: block;
  margin-top: 10rpx;
  font-size: 20rpx;
  line-height: 1.7;
  color: #8d6e63;
}

.risk-pill {
  display: inline-flex;
  margin-top: 18rpx;
  padding: 8rpx 18rpx;
  border-radius: 999rpx;
  background: rgba(255, 244, 231, 0.94);
  color: #8d5b3e;
  font-size: 20rpx;
  font-weight: 700;
  text-transform: uppercase;
}

.result-card {
  text-align: center;
}

.result-score {
  display: block;
  margin-top: 18rpx;
  font-size: 96rpx;
  line-height: 1;
  font-weight: 900;
  color: #5d4037;
}

.result-unit {
  display: block;
  margin-top: 10rpx;
  font-size: 24rpx;
  color: #8d6e63;
}

.result-actions {
  grid-template-columns: repeat(2, 1fr);
}

.primary-btn,
.ghost-btn {
  height: 80rpx;
  border-radius: 999rpx;
  border: none;
  font-size: 24rpx;
  font-weight: 800;
}

.primary-btn {
  background: linear-gradient(135deg, #5d4037, #d4a373);
  color: #fff;
}

@keyframes assessmentHeroFloat {
  0%,
  100% {
    transform: translateY(0);
    box-shadow: 0 20rpx 44rpx rgba(62, 39, 35, 0.08);
  }
  50% {
    transform: translateY(-4rpx);
    box-shadow: 0 26rpx 56rpx rgba(62, 39, 35, 0.12);
  }
}

.ghost-btn {
  background: #f4ece3;
  color: #6d4c41;
}

.mini-value {
  display: block;
  margin-top: 12rpx;
  font-size: 34rpx;
  font-weight: 900;
  color: #3e2723;
}

.mini-meter {
  height: 10rpx;
  margin-top: 14rpx;
  border-radius: 999rpx;
  background: rgba(212, 163, 115, 0.16);
  overflow: hidden;
}

.mini-meter__fill {
  height: 100%;
  border-radius: 999rpx;
  background: linear-gradient(90deg, #5d4037, #d4a373);
}

.handoff-box {
  margin-top: 18rpx;
  padding: 22rpx;
  border-radius: 24rpx;
  background: rgba(255, 236, 229, 0.92);
  color: #8a3b2f;
  font-size: 22rpx;
  line-height: 1.8;
}

.page-spacer {
  height: 120rpx;
}

@media (max-width: 390px) {
  .hero-topline {
    flex-direction: column;
    align-items: flex-start;
  }

  .three-column {
    grid-template-columns: repeat(2, 1fr);
  }

  .result-actions {
    grid-template-columns: 1fr;
  }
}
</style>
