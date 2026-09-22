<template>
  <view class="report-page">
    <!-- 顶部英雄区 (1:1 严格对齐 06-report.png) -->
    <view class="report-hero">
      <view class="hero-copy">
        <text class="eyebrow">简报</text>
        <text class="page-title">最近怎么样</text>
      </view>
      <button class="refresh-btn" :disabled="loading" @click="handleRefresh">
        {{ loading ? '刷新中...' : userStore.isDemoMode ? '刷新样例' : '刷 新' }}
      </button>
    </view>

    <!-- 简报周期与关系范围选择卡 -->
    <view class="report-scope-card">
      <view class="segmented-tabs">
        <view
          class="seg-tab"
          :class="{ active: currentType === 'daily' }"
          @click="switchType('daily')"
        >
          <text class="seg-text">日报</text>
        </view>
        <view
          class="seg-tab"
          :class="{ active: currentType === 'weekly' }"
          @click="switchType('weekly')"
        >
          <text class="seg-text">周报</text>
        </view>
        <view
          class="seg-tab"
          :class="{ active: currentType === 'monthly' }"
          @click="switchType('monthly')"
        >
          <text class="seg-text">月报</text>
        </view>
      </view>

      <view class="relation-picker-row" @click="toggleRelationPicker">
        <text class="picker-label">查看关系:</text>
        <text class="picker-val">{{ partnerName }} · 情侣</text>
        <text class="picker-arrow">▾</text>
      </view>
    </view>

    <!-- 核心简报纸张卡片 (report-paper) -->
    <view class="report-paper">
      <view class="paper-head">
        <view class="paper-meta-column">
          <view class="meta-tag-row">
            <text class="meta-tag tag-seal">{{ reportTypeLabel }}</text>
            <text class="meta-tag">{{ reportData.dateLabel }}</text>
            <text class="meta-tag">情侣·{{ partnerName }}</text>
          </view>
          <text class="report-headline">{{ reportData.headline }}</text>

          <view class="chips-row">
            <text v-for="tag in reportData.tags" :key="tag" class="chip-item">
              # {{ tag }}
            </text>
          </view>
        </view>

        <!-- 右上角典雅方框大分值 (严格对齐 06-report.png 中的 78 样例评分) -->
        <view class="score-badge-card">
          <text class="score-large">{{ reportData.healthScore }}</text>
          <text class="score-caption">{{ userStore.isDemoMode ? '样例评分' : '关系评分' }}</text>
        </view>
      </view>

      <!-- 简报摘要三栏卡 (记录时间 / 先聊这个 / 过往记录) -->
      <view class="summary-three-grid">
        <view class="summary-col">
          <text class="col-label">记录时间</text>
          <text class="col-value">{{ reportData.dateLabel }}</text>
        </view>
        <view class="summary-col">
          <text class="col-label">先聊这个</text>
          <text class="col-value highlight">{{ reportData.nextTopic }}</text>
        </view>
        <view class="summary-col">
          <text class="col-label">过往记录</text>
          <text class="col-value">{{ reportData.recordCount }} 份</text>
        </view>
      </view>

      <!-- 数据可视化双卡：关系五边形与趋势走势 -->
      <view class="visual-cards-stack">
        <!-- 维度分析 -->
        <view class="inner-panel">
          <text class="panel-subtitle">五项关系状态</text>
          <view class="dimensions-bars">
            <view
              v-for="dim in reportData.dimensions"
              :key="dim.label"
              class="dim-line"
            >
              <text class="dim-name">{{ dim.label }}</text>
              <view class="bar-bg">
                <view
                  class="bar-filled"
                  :style="{ width: `${dim.value}%`, backgroundColor: dim.color }"
                ></view>
              </view>
              <text class="dim-num">{{ dim.value }}</text>
            </view>
          </view>
        </view>

        <!-- 周期走势 (周报/日报波动) -->
        <view class="inner-panel">
          <text class="panel-subtitle">近 7 天心境波动</text>
          <view class="daily-bars-grid">
            <view
              v-for="item in reportData.weeklyTrend"
              :key="item.day"
              class="bar-col"
            >
              <view class="col-track">
                <view
                  class="col-fill"
                  :style="{ height: `${(item.score / 100) * 140}rpx` }"
                ></view>
              </view>
              <text class="col-score">{{ item.score }}</text>
              <text class="col-day">{{ item.day }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- 发现与下一步深度洞察 -->
      <view class="insight-cards-stack">
        <!-- 发现卡片 -->
        <view class="insight-card">
          <text class="eyebrow">发现</text>
          <text class="insight-title">值得留意的事</text>
          <view class="bullet-list">
            <view
              v-for="(insight, idx) in reportData.insights"
              :key="idx"
              class="bullet-item"
            >
              <text class="bullet-dot">—</text>
              <text class="bullet-text">{{ insight }}</text>
            </view>
          </view>
        </view>

        <!-- 下一步建议卡片 (朱砂色左侧边条) -->
        <view class="insight-card card-accent-seal">
          <text class="eyebrow">下一步</text>
          <text class="insight-title">可以试试</text>
          <view class="bullet-list">
            <view
              v-for="(rec, idx) in reportData.recommendations"
              :key="idx"
              class="bullet-item"
            >
              <text class="bullet-dot">—</text>
              <text class="bullet-text">{{ rec }}</text>
            </view>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { get } from '@/utils/request'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const currentType = ref('daily')
const loading = ref(false)

const partnerName = computed(() => {
  return userStore.partnerName || '林夏'
})

const reportTypeLabel = computed(() => {
  if (currentType.value === 'weekly') return '周报'
  if (currentType.value === 'monthly') return '月报'
  return '日报'
})

// 默认/样例数据 (100% 严格对齐 06-report.png)
const reportData = reactive({
  dateLabel: '2026年3月21日',
  headline: '今天和林夏聊了会儿天。',
  healthScore: 78,
  nextTopic: '周末共同安排',
  recordCount: 14,
  tags: ['双方都在靠近', '表达温和', '互动有回音'],
  dimensions: [
    { label: '表达', value: 76, color: '#d76848' },
    { label: '信任', value: 80, color: '#5f876f' },
    { label: '缓和', value: 65, color: '#c78a3f' },
    { label: '节奏', value: 58, color: '#aa4d33' },
    { label: '活力', value: 62, color: '#5b8dee' },
  ],
  weeklyTrend: [
    { day: '周一', score: 72 },
    { day: '周二', score: 75 },
    { day: '周三', score: 70 },
    { day: '周四', score: 74 },
    { day: '周五', score: 80 },
    { day: '周六', score: 78 },
    { day: '周日', score: 82 },
  ],
  insights: [
    '在分享日常琐事时，双方表达了对未来安排的期待，情绪感知高度契合。',
    '当谈到疲惫或工作压力时，彼此没有急于给出建议，而是留出了体谅的倾听空间。',
    '晚间沟通的响应间隔比平时更加从容，表明双方处于舒适的无压力交流状态。',
  ],
  recommendations: [
    '今天可以不用聊太严肃的长期计划，先确认明天晚餐吃什么。',
    '如果感受到对方的疲惫，简短发送一句“辛苦了，早点休息”，胜过长篇分析。',
    '在周末安排中保留半天空白时间，给彼此自主调整的余地。',
  ],
})

onMounted(async () => {
  await fetchReport()
})

async function fetchReport() {
  loading.value = true
  try {
    const res = await get('/api/v1/report/latest', { type: currentType.value })
    if (res && res.summary) {
      reportData.headline = res.summary
      reportData.healthScore = res.health_score || 78
      if (res.insights?.length) reportData.insights = res.insights
      if (res.recommendations?.length) reportData.recommendations = res.recommendations
    }
  } catch (err) {
    // 若后端无最新简报或在 Demo 模式下，使用规范样例数据
  } finally {
    loading.value = false
  }
}

function switchType(type) {
  currentType.value = type
  fetchReport()
}

function handleRefresh() {
  fetchReport()
  uni.showToast({ title: '简报已刷新', icon: 'none' })
}

function toggleRelationPicker() {
  uni.navigateTo({ url: '/pages/pair/pair' })
}
</script>

<style lang="scss" scoped>
.report-page {
  min-height: 100vh;
  padding: 24rpx 32rpx 80rpx;
  background-color: #f7f1eb;
  background-image:
    radial-gradient(900rpx circle at 10% -10%, rgba(215, 104, 72, 0.15), transparent 45%),
    radial-gradient(700rpx circle at 90% -5%, rgba(240, 213, 184, 0.4), transparent 50%),
    linear-gradient(180deg, #fcf7f2 0%, #f6efe7 100%);
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

/* 顶部英雄区 */
.report-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: 10rpx 0;

  .hero-copy {
    .page-title {
      font-family: $font-serif;
      font-size: 44rpx;
      font-weight: 700;
      color: #1f2a2f;
      line-height: 1.2;
      display: block;
    }
  }

  .refresh-btn {
    height: 64rpx;
    line-height: 62rpx;
    padding: 0 24rpx;
    background: #d76848;
    border: 1px solid #aa4d33;
    border-radius: 10rpx;
    color: #ffffff;
    font-size: 24rpx;
    font-weight: 600;
    margin: 0;

    &[disabled] {
      opacity: 0.6;
    }
  }
}

/* 范围与周期选择卡 */
.report-scope-card {
  background: rgba(255, 250, 244, 0.94);
  border: 1px solid rgba(68, 52, 40, 0.12);
  border-radius: 16rpx;
  padding: 20rpx 24rpx;
  box-shadow: 0 8rpx 22rpx rgba(74, 52, 36, 0.05);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16rpx;
}

.segmented-tabs {
  display: flex;
  background: rgba(68, 52, 40, 0.06);
  padding: 4rpx;
  border-radius: 10rpx;

  .seg-tab {
    padding: 10rpx 24rpx;
    border-radius: 8rpx;

    .seg-text {
      font-size: 26rpx;
      color: #5b666c;
      font-weight: 500;
    }

    &.active {
      background: #ffffff;
      box-shadow: 0 2rpx 6rpx rgba(0, 0, 0, 0.06);

      .seg-text {
        color: #1f2a2f;
        font-weight: 600;
      }
    }
  }
}

.relation-picker-row {
  display: flex;
  align-items: center;
  gap: 8rpx;
  background: #ffffff;
  border: 1px solid rgba(68, 52, 40, 0.12);
  border-radius: 999rpx;
  padding: 8rpx 20rpx;

  .picker-label {
    font-size: 22rpx;
    color: #7c837f;
  }

  .picker-val {
    font-size: 24rpx;
    font-weight: 600;
    color: #1f2a2f;
  }

  .picker-arrow {
    font-size: 20rpx;
    color: #7c837f;
  }
}

/* 核心简报纸张 (1:1 严格对齐 06-report.png) */
.report-paper {
  background: rgba(255, 250, 244, 0.96);
  border: 1px solid rgba(68, 52, 40, 0.14);
  border-radius: 16rpx;
  padding: 32rpx;
  box-shadow: 0 12rpx 32rpx rgba(74, 52, 36, 0.07);
  display: flex;
  flex-direction: column;
  gap: 28rpx;
}

.paper-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20rpx;
  border-bottom: 1px solid rgba(68, 52, 40, 0.08);
  padding-bottom: 24rpx;

  .paper-meta-column {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 12rpx;
  }
}

.meta-tag-row {
  display: flex;
  gap: 10rpx;
  flex-wrap: wrap;

  .meta-tag {
    font-size: 22rpx;
    color: #7c837f;
    background: rgba(68, 52, 40, 0.05);
    padding: 2rpx 14rpx;
    border-radius: 6rpx;

    &.tag-seal {
      background: #fceee8;
      color: #aa4d33;
      font-weight: 600;
    }
  }
}

.report-headline {
  font-family: $font-serif;
  font-size: 38rpx;
  font-weight: 700;
  color: #1f2a2f;
  line-height: 1.35;
}

.chips-row {
  display: flex;
  gap: 12rpx;
  flex-wrap: wrap;

  .chip-item {
    font-size: 22rpx;
    color: #5f876f;
    background: #eaf2ea;
    padding: 4rpx 14rpx;
    border-radius: 6rpx;
  }
}

/* 柔和方框大分值 */
.score-badge-card {
  width: 140rpx;
  background: #ffffff;
  border: 1px solid rgba(215, 104, 72, 0.25);
  border-radius: 12rpx;
  padding: 16rpx 10rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4rpx 12rpx rgba(215, 104, 72, 0.08);

  .score-large {
    font-family: $font-serif;
    font-size: 52rpx;
    font-weight: 700;
    color: #d76848;
    line-height: 1;
  }

  .score-caption {
    font-size: 20rpx;
    color: #7c837f;
    margin-top: 4rpx;
  }
}

/* 简报摘要三栏卡 */
.summary-three-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16rpx;
  background: #ffffff;
  border: 1px solid rgba(68, 52, 40, 0.08);
  border-radius: 12rpx;
  padding: 20rpx;

  .summary-col {
    display: flex;
    flex-direction: column;
    gap: 6rpx;

    .col-label {
      font-size: 22rpx;
      color: #7c837f;
    }

    .col-value {
      font-size: 26rpx;
      font-weight: 600;
      color: #1f2a2f;

      &.highlight {
        color: #d76848;
      }
    }
  }
}

/* 可视化双卡 */
.visual-cards-stack {
  display: flex;
  flex-direction: column;
  gap: 20rpx;

  .inner-panel {
    background: #ffffff;
    border: 1px solid rgba(68, 52, 40, 0.08);
    border-radius: 12rpx;
    padding: 24rpx;

    .panel-subtitle {
      font-size: 24rpx;
      font-weight: 600;
      color: #1f2a2f;
      display: block;
      margin-bottom: 16rpx;
    }
  }
}

.dimensions-bars {
  display: flex;
  flex-direction: column;
  gap: 14rpx;

  .dim-line {
    display: flex;
    align-items: center;
    gap: 14rpx;

    .dim-name {
      width: 64rpx;
      font-size: 22rpx;
      color: #5b666c;
    }

    .bar-bg {
      flex: 1;
      height: 14rpx;
      background: rgba(68, 52, 40, 0.06);
      border-radius: 999rpx;
      overflow: hidden;

      .bar-filled {
        height: 100%;
        border-radius: 999rpx;
      }
    }

    .dim-num {
      width: 48rpx;
      text-align: right;
      font-size: 22rpx;
      font-weight: 600;
      color: #1f2a2f;
    }
  }
}

.daily-bars-grid {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  height: 200rpx;
  padding-top: 20rpx;

  .bar-col {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6rpx;

    .col-track {
      width: 24rpx;
      height: 140rpx;
      display: flex;
      align-items: flex-end;
      background: rgba(68, 52, 40, 0.06);
      border-radius: 6rpx;
      overflow: hidden;

      .col-fill {
        width: 100%;
        background: #d76848;
        border-radius: 6rpx 6rpx 0 0;
      }
    }

    .col-score {
      font-size: 20rpx;
      color: #5b666c;
      font-weight: 600;
    }

    .col-day {
      font-size: 20rpx;
      color: #7c837f;
    }
  }
}

/* 洞察双卡 */
.insight-cards-stack {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.insight-card {
  background: #ffffff;
  border: 1px solid rgba(68, 52, 40, 0.08);
  border-radius: 12rpx;
  padding: 24rpx;

  &.card-accent-seal {
    border-left: 6rpx solid #d76848;
  }

  .insight-title {
    font-family: $font-serif;
    font-size: 28rpx;
    font-weight: 700;
    color: #1f2a2f;
    display: block;
    margin-bottom: 16rpx;
  }
}

.bullet-list {
  display: flex;
  flex-direction: column;
  gap: 12rpx;

  .bullet-item {
    display: flex;
    align-items: flex-start;
    gap: 12rpx;

    .bullet-dot {
      color: #d76848;
      font-size: 22rpx;
      line-height: 1.5;
    }

    .bullet-text {
      flex: 1;
      font-size: 26rpx;
      color: #5b666c;
      line-height: 1.6;
    }
  }
}
</style>
