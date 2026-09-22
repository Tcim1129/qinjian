<template>
  <view class="home-page">
    <!-- 顶部状态栏与关系切换器 -->
    <view class="home-top-bar">
      <view class="top-title-group">
        <text class="top-brand">亲健</text>
        <text class="top-page-name">首页</text>
      </view>

      <view class="partner-capsule" @click="goPair">
        <view class="partner-avatar-mini">
          <text>{{ partnerInitial }}</text>
        </view>
        <text class="partner-name-text">{{ partnerName }}</text>
        <text class="partner-capsule-arrow">▾</text>
      </view>
    </view>

    <!-- 体验样例条提示 (仅 Demo 模式下显示) -->
    <view v-if="userStore.isDemoMode" class="demo-banner">
      <text class="demo-badge">样例模式</text>
      <text class="demo-text">正在浏览“陈一 & 林夏”真实互动数据</text>
      <text class="demo-switch-link" @click="goLogin">切换账号</text>
    </view>

    <!-- 核心 Hero Dossier 卡片 (1:1 严格对齐 02-home.png) -->
    <view class="home-dossier">
      <view class="dossier-stamp">
        <view class="stamp-icon-box">
          <text class="stamp-dot"></text>
        </view>
        <text class="stamp-text">今天的记录</text>
      </view>

      <view class="eyebrow-row">
        <text class="eyebrow">首页</text>
      </view>

      <text class="hero-headline">{{ heroHeadline }}</text>

      <!-- 双主操作按钮 -->
      <view class="hero-actions">
        <button class="btn-primary" @click="goReport">
          {{ primaryActionText }}
        </button>
        <button class="btn-secondary" @click="openSampleAlignment">
          看双视角样例 &gt;
        </button>
      </view>

      <!-- 快捷小胶囊行 (纯文字，严禁任何卡通 Emoji) -->
      <scroll-view class="subactions-scroll" scroll-x :show-scrollbar="false">
        <view class="subactions-row">
          <view class="subaction-chip" @click="goVoiceCheckin">
            <text class="chip-label">聊一聊</text>
          </view>
          <view class="subaction-chip" @click="goMessageSimulation">
            <text class="chip-label">发前看看</text>
          </view>
          <view class="subaction-chip" @click="goRepairProtocol">
            <text class="chip-label">缓和建议</text>
          </view>
          <view class="subaction-chip" @click="scrollToTasks">
            <text class="chip-label">今日安排</text>
          </view>
          <view class="subaction-chip" @click="goTimeline">
            <text class="chip-label">关系日历</text>
          </view>
        </view>
      </scroll-view>

      <!-- 四格状态摘要微卡 (100% 对齐 02-home.png) -->
      <view class="home-metrics-grid">
        <view class="metric-card metric-warm">
          <text class="metric-title">连续记录</text>
          <text class="metric-value">{{ streakDays }} 天</text>
        </view>
        <view class="metric-card metric-moss">
          <text class="metric-title">我的状态</text>
          <text class="metric-value">{{ myDone ? '已记录' : '未记录' }}</text>
        </view>
        <view class="metric-card metric-sky">
          <text class="metric-title">对方状态</text>
          <text class="metric-value">{{ partnerMetricValue }}</text>
        </view>
        <view class="metric-card metric-amber">
          <text class="metric-title">关系信号</text>
          <text class="metric-value">{{ signalMetricValue }}</text>
        </view>
      </view>
    </view>

    <!-- 数据概览区域 (30 天变化最近走势 + 关系五边形) -->
    <view class="analytics-section">
      <!-- 走势卡片 -->
      <view class="chart-card">
        <view class="card-head">
          <view>
            <text class="eyebrow">30 天变化</text>
            <text class="card-title">最近走势</text>
          </view>
          <view class="trend-badge">
            <text class="badge-text">在变好</text>
          </view>
        </view>

        <!-- SVG 折线走势图 (与 02-home 完全一致) -->
        <view class="svg-chart-container">
          <svg class="trend-svg" viewBox="0 0 340 140">
            <!-- 横向虚线网格 -->
            <line x1="20" y1="30" x2="320" y2="30" stroke="rgba(68, 52, 40, 0.08)" stroke-width="1" stroke-dasharray="3,3" />
            <line x1="20" y1="70" x2="320" y2="70" stroke="rgba(68, 52, 40, 0.08)" stroke-width="1" stroke-dasharray="3,3" />
            <line x1="20" y1="110" x2="320" y2="110" stroke="rgba(68, 52, 40, 0.08)" stroke-width="1" />

            <!-- 折线 -->
            <polyline
              points="40,85 105,75 170,90 235,65 300,50"
              fill="none"
              stroke="#d76848"
              stroke-width="2.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            />

            <!-- 数据圆点与数值 -->
            <!-- 3/1: 72 -->
            <circle cx="40" cy="85" r="4" fill="#ffffff" stroke="#d76848" stroke-width="2" />
            <text x="40" y="75" text-anchor="middle" font-size="11" fill="#1f2a2f" font-weight="600">72</text>

            <!-- 3/8: 75 -->
            <circle cx="105" cy="75" r="4" fill="#ffffff" stroke="#d76848" stroke-width="2" />
            <text x="105" y="65" text-anchor="middle" font-size="11" fill="#1f2a2f" font-weight="600">75</text>

            <!-- 3/15: 70 -->
            <circle cx="170" cy="90" r="4" fill="#ffffff" stroke="#d76848" stroke-width="2" />
            <text x="170" y="80" text-anchor="middle" font-size="11" fill="#1f2a2f" font-weight="600">70</text>

            <!-- 3/20: 78 -->
            <circle cx="235" cy="65" r="4" fill="#ffffff" stroke="#d76848" stroke-width="2" />
            <text x="235" y="55" text-anchor="middle" font-size="11" fill="#1f2a2f" font-weight="600">78</text>

            <!-- 3/21: 82 -->
            <circle cx="300" cy="50" r="4.5" fill="#d76848" stroke="#ffffff" stroke-width="2" />
            <text x="300" y="40" text-anchor="middle" font-size="11" fill="#d76848" font-weight="700">82</text>
          </svg>

          <!-- 日期刻度 -->
          <view class="chart-dates-row">
            <text class="date-col">3/1</text>
            <text class="date-col">3/8</text>
            <text class="date-col">3/15</text>
            <text class="date-col">3/20</text>
            <text class="date-col">3/21</text>
          </view>
        </view>
      </view>

      <!-- 关系五边形状态卡片 -->
      <view class="chart-card">
        <view class="card-head">
          <view>
            <text class="eyebrow">关系五边形</text>
            <text class="card-title">五项关系状态</text>
          </view>
          <view class="radar-score-box">
            <text class="radar-score-num">68</text>
            <text class="radar-score-unit">/ 100</text>
          </view>
        </view>

        <!-- 5项指标水平进度柱 (优雅直观，符合移动端阅读习惯) -->
        <view class="dimensions-list">
          <view
            v-for="dim in radarDimensions"
            :key="dim.label"
            class="dimension-row"
          >
            <text class="dim-label">{{ dim.label }}</text>
            <view class="dim-bar-track">
              <view
                class="dim-bar-fill"
                :style="{ width: `${dim.value}%`, backgroundColor: dim.color }"
              ></view>
            </view>
            <text class="dim-value">{{ dim.value }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 今日安排卡片 (代办任务与行动建议) -->
    <view id="tasks-section" class="tasks-card">
      <view class="card-head">
        <view>
          <text class="eyebrow">今日安排</text>
          <text class="card-title">今天先做这些</text>
        </view>
        <text class="task-summary-text">已完成 {{ completedTaskCount }} / {{ tasks.length }}</text>
      </view>

      <view class="task-items-list">
        <view
          v-for="(task, idx) in tasks"
          :key="task.id"
          class="task-item"
          :class="{ done: task.completed }"
          @click="toggleTask(idx)"
        >
          <view class="task-checkbox" :class="{ checked: task.completed }">
            <text v-if="task.completed" class="check-tick">✓</text>
          </view>
          <view class="task-text-group">
            <text class="task-title">{{ task.title }}</text>
            <text class="task-desc">{{ task.desc }}</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

// 状态数据
const streakDays = ref(6)
const myDone = ref(true)
const partnerMetricValue = ref('已记录')
const signalMetricValue = ref('先慢一点')

const radarDimensions = ref([
  { label: '表达', value: 76, color: '#d76848' },
  { label: '信任', value: 80, color: '#5f876f' },
  { label: '缓和', value: 65, color: '#c78a3f' },
  { label: '节奏', value: 58, color: '#aa4d33' },
  { label: '活力', value: 62, color: '#5b8dee' },
])

const tasks = ref([
  { id: 1, title: '留出20分钟放空期', desc: '不追问、不复盘，给彼此缓冲的情绪空间', completed: true },
  { id: 2, title: '确认周末共同行程', desc: '在晚餐时温和同步周六的外出偏好', completed: false },
  { id: 3, title: '发送睡前问候', desc: '简短分享今天遇到的有趣小事', completed: false },
])

const completedTaskCount = computed(() => {
  return tasks.value.filter(t => t.completed).length
})

const partnerName = computed(() => {
  return userStore.partnerName || '林夏'
})

const partnerInitial = computed(() => {
  return partnerName.value.slice(0, 1) || '林'
})

const heroHeadline = computed(() => {
  return myDone.value ? '这期简报可以看了' : '今天过得怎么样？'
})

const primaryActionText = computed(() => {
  return myDone.value ? '打开今日简报' : '去记录今天'
})

onMounted(async () => {
  await userStore.bootstrap()
})

onShow(async () => {
  await userStore.fetchMe()
})

function goLogin() {
  uni.navigateTo({ url: '/pages/auth/login' })
}

function goPair() {
  uni.navigateTo({ url: '/pages/pair/pair' })
}

function goReport() {
  uni.switchTab({ url: '/pages/report/report' })
}

function openSampleAlignment() {
  uni.switchTab({ url: '/pages/report/report' })
}

function goVoiceCheckin() {
  uni.switchTab({ url: '/pages/checkin/checkin' })
}

function goMessageSimulation() {
  uni.showToast({ title: '发前看看：输入消息测算语气反应', icon: 'none' })
}

function goRepairProtocol() {
  uni.showToast({ title: '缓和建议：先停住情绪，留出20分钟缓冲', icon: 'none' })
}

function scrollToTasks() {
  uni.pageScrollTo({ selector: '#tasks-section', duration: 300 })
}

function goTimeline() {
  uni.navigateTo({ url: '/pages/timeline/timeline' })
}

function toggleTask(idx) {
  tasks.value[idx].completed = !tasks.value[idx].completed
}
</script>

<style lang="scss" scoped>
.home-page {
  min-height: 100vh;
  padding: 24rpx 32rpx 60rpx;
  background-color: #f7f1eb;
  background-image:
    radial-gradient(900rpx circle at 10% -10%, rgba(215, 104, 72, 0.15), transparent 45%),
    radial-gradient(700rpx circle at 90% -5%, rgba(240, 213, 184, 0.4), transparent 50%),
    linear-gradient(180deg, #fcf7f2 0%, #f6efe7 100%);
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

/* 顶部状态栏 */
.home-top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8rpx 0;

  .top-title-group {
    display: flex;
    align-items: baseline;
    gap: 12rpx;

    .top-brand {
      font-family: $font-serif;
      font-size: 38rpx;
      font-weight: 700;
      color: #1f2a2f;
      letter-spacing: 1rpx;
    }

    .top-page-name {
      font-size: 26rpx;
      color: #7c837f;
      font-weight: 500;
    }
  }

  .partner-capsule {
    display: flex;
    align-items: center;
    gap: 12rpx;
    background: rgba(255, 250, 244, 0.95);
    border: 1px solid rgba(68, 52, 40, 0.12);
    border-radius: 999rpx;
    padding: 6rpx 16rpx 6rpx 8rpx;
    box-shadow: 0 4rpx 12rpx rgba(74, 52, 36, 0.05);

    .partner-avatar-mini {
      width: 44rpx;
      height: 44rpx;
      border-radius: 50%;
      background: #df6b4d;
      color: #ffffff;
      font-size: 22rpx;
      font-family: $font-serif;
      font-weight: 600;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .partner-name-text {
      font-size: 26rpx;
      font-weight: 600;
      color: #1f2a2f;
    }

    .partner-capsule-arrow {
      font-size: 22rpx;
      color: #7c837f;
    }
  }
}

/* 样例条 */
.demo-banner {
  display: flex;
  align-items: center;
  gap: 12rpx;
  background: #fceee8;
  border: 1px solid rgba(215, 104, 72, 0.25);
  border-radius: 12rpx;
  padding: 12rpx 20rpx;

  .demo-badge {
    font-size: 20rpx;
    background: #d76848;
    color: #ffffff;
    padding: 2rpx 10rpx;
    border-radius: 6rpx;
    font-weight: 500;
  }

  .demo-text {
    flex: 1;
    font-size: 22rpx;
    color: #aa4d33;
  }

  .demo-switch-link {
    font-size: 22rpx;
    color: #d76848;
    text-decoration: underline;
  }
}

/* 核心 Hero Dossier 卡片 (1:1 严格对齐 02-home.png) */
.home-dossier {
  background:
    linear-gradient(140deg, rgba(215, 104, 72, 0.08) 0%, rgba(240, 213, 184, 0.16) 56%, rgba(223, 233, 221, 0.1) 100%),
    rgba(255, 250, 244, 0.94);
  border: 1px solid rgba(68, 52, 40, 0.12);
  border-radius: 16rpx;
  padding: 32rpx;
  box-shadow: 0 12rpx 28rpx rgba(170, 77, 51, 0.07);
  display: flex;
  flex-direction: column;
}

.dossier-stamp {
  display: inline-flex;
  align-items: center;
  gap: 10rpx;
  margin-bottom: 8rpx;

  .stamp-icon-box {
    width: 24rpx;
    height: 24rpx;
    border-radius: 50%;
    border: 2rpx solid #d76848;
    display: flex;
    align-items: center;
    justify-content: center;

    .stamp-dot {
      width: 10rpx;
      height: 10rpx;
      border-radius: 50%;
      background: #d76848;
    }
  }

  .stamp-text {
    font-size: 24rpx;
    font-weight: 600;
    color: #d76848;
    letter-spacing: 1rpx;
  }
}

.eyebrow-row {
  margin-top: 4rpx;
}

.hero-headline {
  font-family: $font-serif;
  font-size: 44rpx;
  font-weight: 700;
  color: #1f2a2f;
  line-height: 1.32;
  margin: 10rpx 0 24rpx;
}

.hero-actions {
  display: flex;
  gap: 16rpx;
  margin-bottom: 24rpx;

  .btn-primary {
    flex: 1;
    height: 76rpx;
    line-height: 74rpx;
    background: #d76848;
    border: 1px solid #aa4d33;
    border-radius: 12rpx;
    color: #ffffff;
    font-size: 28rpx;
    font-weight: 600;
    text-align: center;
    box-shadow: 0 6rpx 16rpx rgba(215, 104, 72, 0.22);
    margin: 0;
  }

  .btn-secondary {
    flex: 1;
    height: 76rpx;
    line-height: 74rpx;
    background: #fceee8;
    border: 1px solid rgba(215, 104, 72, 0.35);
    border-radius: 12rpx;
    color: #aa4d33;
    font-size: 28rpx;
    font-weight: 600;
    text-align: center;
    margin: 0;
  }
}

/* 快捷胶囊 */
.subactions-scroll {
  width: 100%;
  white-space: nowrap;
  margin-bottom: 28rpx;

  .subactions-row {
    display: inline-flex;
    gap: 12rpx;
  }

  .subaction-chip {
    display: inline-block;
    padding: 10rpx 22rpx;
    background: #ffffff;
    border: 1px solid rgba(68, 52, 40, 0.12);
    border-radius: 999rpx;

    .chip-label {
      font-size: 24rpx;
      color: #5b666c;
      font-weight: 500;
    }
  }
}

/* 四格状态微卡 */
.home-metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16rpx;

  .metric-card {
    padding: 20rpx;
    border-radius: 12rpx;
    display: flex;
    flex-direction: column;
    gap: 6rpx;
    border: 1px solid transparent;

    .metric-title {
      font-size: 22rpx;
      color: #7c837f;
    }

    .metric-value {
      font-size: 30rpx;
      font-weight: 700;
      color: #1f2a2f;
    }

    &.metric-warm {
      background: #fcf4ef;
      border-color: rgba(215, 104, 72, 0.15);
      .metric-value { color: #d76848; }
    }

    &.metric-moss {
      background: #eaf2ea;
      border-color: rgba(95, 135, 111, 0.15);
      .metric-value { color: #5f876f; }
    }

    &.metric-sky {
      background: #eef6f8;
      border-color: rgba(91, 141, 238, 0.15);
      .metric-value { color: #305d68; }
    }

    &.metric-amber {
      background: #fbf5ea;
      border-color: rgba(199, 138, 63, 0.18);
      .metric-value { color: #c78a3f; }
    }
  }
}

/* 分析卡片 */
.analytics-section {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.chart-card {
  background: rgba(255, 250, 244, 0.94);
  border: 1px solid rgba(68, 52, 40, 0.12);
  border-radius: 16rpx;
  padding: 30rpx;
  box-shadow: 0 8rpx 22rpx rgba(74, 52, 36, 0.05);

  .card-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 20rpx;

    .card-title {
      font-family: $font-serif;
      font-size: 32rpx;
      font-weight: 700;
      color: #1f2a2f;
      display: block;
    }

    .trend-badge {
      background: #eaf2ea;
      border: 1px solid rgba(95, 135, 111, 0.2);
      border-radius: 8rpx;
      padding: 4rpx 14rpx;
      .badge-text {
        font-size: 22rpx;
        color: #5f876f;
        font-weight: 600;
      }
    }

    .radar-score-box {
      display: flex;
      align-items: baseline;
      gap: 4rpx;

      .radar-score-num {
        font-family: $font-serif;
        font-size: 40rpx;
        font-weight: 700;
        color: #d76848;
      }

      .radar-score-unit {
        font-size: 22rpx;
        color: #7c837f;
      }
    }
  }
}

.svg-chart-container {
  width: 100%;
  margin-top: 10rpx;

  .trend-svg {
    width: 100%;
    height: 240rpx;
  }

  .chart-dates-row {
    display: flex;
    justify-content: space-between;
    padding: 0 30rpx;
    margin-top: 4rpx;

    .date-col {
      font-size: 22rpx;
      color: #7c837f;
    }
  }
}

.dimensions-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
  margin-top: 10rpx;

  .dimension-row {
    display: flex;
    align-items: center;
    gap: 16rpx;

    .dim-label {
      width: 72rpx;
      font-size: 24rpx;
      color: #5b666c;
      font-weight: 500;
    }

    .dim-bar-track {
      flex: 1;
      height: 16rpx;
      background: rgba(68, 52, 40, 0.08);
      border-radius: 999rpx;
      overflow: hidden;

      .dim-bar-fill {
        height: 100%;
        border-radius: 999rpx;
      }
    }

    .dim-value {
      width: 50rpx;
      text-align: right;
      font-size: 24rpx;
      font-weight: 600;
      color: #1f2a2f;
    }
  }
}

/* 安排卡片 */
.tasks-card {
  background: rgba(255, 250, 244, 0.94);
  border: 1px solid rgba(68, 52, 40, 0.12);
  border-radius: 16rpx;
  padding: 30rpx;
  box-shadow: 0 8rpx 22rpx rgba(74, 52, 36, 0.05);

  .card-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 24rpx;

    .card-title {
      font-family: $font-serif;
      font-size: 32rpx;
      font-weight: 700;
      color: #1f2a2f;
      display: block;
    }

    .task-summary-text {
      font-size: 24rpx;
      color: #7c837f;
    }
  }
}

.task-items-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.task-item {
  display: flex;
  align-items: flex-start;
  gap: 16rpx;
  padding: 20rpx;
  background: #ffffff;
  border: 1px solid rgba(68, 52, 40, 0.08);
  border-radius: 12rpx;
  transition: all 0.2s ease;

  &.done {
    opacity: 0.6;
    .task-title {
      text-decoration: line-through;
    }
  }

  .task-checkbox {
    width: 36rpx;
    height: 36rpx;
    border: 2rpx solid rgba(68, 52, 40, 0.3);
    border-radius: 6rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-top: 2rpx;

    &.checked {
      background: #5f876f;
      border-color: #5f876f;
    }

    .check-tick {
      color: #ffffff;
      font-size: 24rpx;
      line-height: 1;
    }
  }

  .task-text-group {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4rpx;

    .task-title {
      font-size: 28rpx;
      font-weight: 600;
      color: #1f2a2f;
    }

    .task-desc {
      font-size: 24rpx;
      color: #7c837f;
      line-height: 1.4;
    }
  }
}
</style>
