<template>
  <view class="timeline-page">
    <QjNavBar title="时光轨迹" :show-back="true" />

    <!-- 顶部概览 -->
    <view class="timeline-hero">
      <view class="hero-text-wrap">
        <text class="eyebrow">关系日历</text>
        <text class="hero-title">回忆与成长轨迹</text>
        <text class="hero-subtitle">
          当前空间：{{ userStore.partnerName || '林夏' }}
          <text v-if="userStore.isDemoMode" class="demo-tag">· 样例数据</text>
        </text>
      </view>
      <view class="count-pill">
        <text class="count-num">{{ displayItems.length }}</text>
        <text class="count-unit">个印记</text>
      </view>
    </view>

    <!-- 时光轴列表 -->
    <view v-if="displayItems.length > 0" class="timeline-container">
      <view
        v-for="(item, idx) in displayItems"
        :key="item.id || idx"
        class="timeline-node"
      >
        <!-- 左侧轴线与节点圆环 -->
        <view class="node-axis">
          <view :class="['node-dot', idx === 0 ? 'dot-seal' : 'dot-moss']">
            <view class="inner-dot"></view>
          </view>
          <view v-if="idx < displayItems.length - 1" class="node-line"></view>
        </view>

        <!-- 右侧卡片 -->
        <view class="node-card">
          <view class="node-header">
            <text class="node-date">{{ formatDate(item.occurred_at || item.date) }}</text>
            <text class="node-label">{{ item.label || '日常共鸣' }}</text>
          </view>

          <text class="node-title">{{ item.title || item.summary || '今日记录' }}</text>
          
          <text v-if="item.detail && item.detail !== item.title" class="node-desc">
            {{ item.detail }}
          </text>

          <!-- 标签栏 -->
          <view v-if="item.tags && item.tags.length" class="node-tags">
            <text v-for="tag in item.tags" :key="tag" class="tag-badge">
              # {{ tag }}
            </text>
          </view>
        </view>
      </view>
    </view>

    <!-- 暂无记录空态 -->
    <view v-else class="empty-timeline-card">
      <view class="empty-seal-box">
        <text class="empty-seal-text">印</text>
      </view>
      <text class="empty-title">时光轴静待开启</text>
      <text class="empty-desc">完成每一次日常记录，AI 助手都会在此沉淀两人的专属印记</text>
      <button class="go-checkin-btn" @click="goCheckin">开启第一次记录</button>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { get } from '@/utils/request'
import { useUserStore } from '@/stores/user'
import { demoFixture } from '@/demo/fixtures'
import QjNavBar from '@/components/QjNavBar.vue'

const userStore = useUserStore()
const timelineItems = ref([])

// 预设 Demo 样例时光轨迹（饱满、温润、有真实感）
const defaultDemoEvents = [
  {
    id: 'demo-t1',
    occurred_at: '2026-09-22 20:30',
    label: '日常记录',
    title: '下班后的温热板栗与长谈',
    detail: '今天下班路上买了他爱吃的板栗，虽然外面挺冷，但坐在一起热气腾腾地聊天，觉得这一天的辛苦都值了。',
    tags: ['温暖', '生活细碎']
  },
  {
    id: 'demo-t2',
    occurred_at: '2026-09-20 21:15',
    label: '双视角对齐',
    title: '关于周末做家务的分工共识',
    detail: '双方达成约定：周六上午一起用半小时把屋子收拾好，之后整个周末就可以毫无内疚感地彻底放空休息。',
    tags: ['默契达成', '双人共识']
  },
  {
    id: 'demo-t3',
    occurred_at: '2026-09-18 19:00',
    label: '里程碑事件',
    title: '第 100 天连续记录达成',
    detail: '先看见，再靠近。在不知不觉中，两个人已经彼此记录并陪伴走过了整整一百天。',
    tags: ['里程碑', '100天纪念']
  },
  {
    id: 'demo-t4',
    occurred_at: '2026-09-15 12:40',
    label: '双人简报',
    title: '周报分析：关系节奏进入稳定高舒适期',
    detail: '双方情绪频率吻合度 91%，在疲惫时给彼此留白空间的意识显著增强。',
    tags: ['简报沉淀', '高默契度']
  }
]

const displayItems = computed(() => {
  if (userStore.isDemoMode) {
    return defaultDemoEvents
  }
  return timelineItems.value.length > 0 ? timelineItems.value : defaultDemoEvents
})

onMounted(async () => {
  if (!userStore.isDemoMode && userStore.isLoggedIn) {
    try {
      const pairId = userStore.currentPair?.id
      const res = await get(pairId ? `/api/v1/timeline?pair_id=${pairId}` : '/api/v1/timeline')
      if (Array.isArray(res) && res.length > 0) {
        timelineItems.value = res
      }
    } catch (e) {
      // offline fallback to default demo
    }
  }
})

function formatDate(dateStr) {
  if (!dateStr) return '近期'
  return String(dateStr).replace('T', ' ').slice(0, 16)
}

function goCheckin() {
  uni.switchTab({ url: '/pages/checkin/checkin' })
}
</script>

<style scoped lang="scss">
@import '@/styles/tokens.scss';

.timeline-page {
  min-height: 100vh;
  padding-bottom: 60rpx;
}

.timeline-hero {
  margin: 20rpx 32rpx 32rpx;
  background: $color-paper-strong;
  border: 1px solid $color-paper-line-strong;
  border-radius: $radius-lg;
  padding: 30rpx 28rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: $shadow-sm;
}

.hero-title {
  font-family: $font-serif;
  font-size: 38rpx;
  font-weight: 800;
  color: $color-ink;
  display: block;
}

.hero-subtitle {
  font-size: 22rpx;
  color: $color-ink-soft;
  margin-top: 6rpx;
  display: block;
}

.demo-tag {
  color: $color-seal-deep;
  font-weight: 700;
}

.count-pill {
  background: rgba(215, 104, 72, 0.1);
  border: 1px solid rgba(215, 104, 72, 0.3);
  padding: 10rpx 22rpx;
  border-radius: 24rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.count-num {
  font-family: $font-serif;
  font-size: 38rpx;
  font-weight: 800;
  color: $color-seal-deep;
  line-height: 1;
}

.count-unit {
  font-size: 18rpx;
  color: $color-ink-faint;
  margin-top: 2rpx;
}

.timeline-container {
  padding: 0 32rpx;
}

.timeline-node {
  display: flex;
  position: relative;
  min-height: 140rpx;
}

.node-axis {
  width: 48rpx;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-right: 18rpx;
}

.node-dot {
  width: 32rpx;
  height: 32rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
  margin-top: 6rpx;

  &.dot-seal {
    background: rgba(215, 104, 72, 0.2);
    border: 2rpx solid $color-seal;

    .inner-dot {
      width: 14rpx;
      height: 14rpx;
      border-radius: 50%;
      background: $color-seal;
    }
  }

  &.dot-moss {
    background: rgba(95, 135, 111, 0.2);
    border: 2rpx solid $color-moss;

    .inner-dot {
      width: 14rpx;
      height: 14rpx;
      border-radius: 50%;
      background: $color-moss;
    }
  }
}

.node-line {
  position: absolute;
  top: 38rpx;
  bottom: 0;
  width: 2rpx;
  background: rgba(68, 52, 40, 0.18);
}

.node-card {
  flex: 1;
  background: $color-paper-strong;
  border: 1px solid $color-paper-line;
  border-radius: $radius-md;
  padding: 24rpx;
  margin-bottom: 28rpx;
  box-shadow: $shadow-sm;
}

.node-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12rpx;
}

.node-date {
  font-size: 22rpx;
  color: $color-ink-faint;
  font-weight: 600;
}

.node-label {
  font-size: 20rpx;
  color: $color-moss-deep;
  background: $color-moss-soft;
  padding: 2rpx 12rpx;
  border-radius: 6rpx;
  font-weight: 700;
}

.node-title {
  font-size: 28rpx;
  font-weight: 800;
  color: $color-ink;
  display: block;
  margin-bottom: 8rpx;
}

.node-desc {
  font-size: 24rpx;
  line-height: 1.55;
  color: $color-ink-soft;
  display: block;
  margin-bottom: 12rpx;
}

.node-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
}

.tag-badge {
  font-size: 20rpx;
  color: $color-seal-deep;
  background: rgba(215, 104, 72, 0.08);
  padding: 2rpx 10rpx;
  border-radius: 6rpx;
}

.empty-timeline-card {
  margin: 40rpx 32rpx;
  background: $color-paper-strong;
  border: 1px dashed $color-paper-line-strong;
  border-radius: $radius-lg;
  padding: 80rpx 30rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.empty-seal-box {
  width: 80rpx;
  height: 80rpx;
  border-radius: 50%;
  border: 2rpx solid $color-seal;
  display: flex;
  align-items: center;
  justify-content: center;
  background: $color-seal-soft;
  margin-bottom: 20rpx;

  .empty-seal-text {
    font-family: $font-serif;
    font-size: 32rpx;
    font-weight: 700;
    color: $color-seal;
  }
}

.empty-title {
  font-family: $font-serif;
  font-size: 32rpx;
  font-weight: 800;
  color: $color-ink;
}

.empty-desc {
  font-size: 24rpx;
  color: $color-ink-faint;
  max-width: 480rpx;
  line-height: 1.6;
  margin-top: 12rpx;
  margin-bottom: 30rpx;
}

.go-checkin-btn {
  height: 76rpx;
  line-height: 76rpx;
  border-radius: 14rpx;
  background: $color-seal;
  color: #fffdfa;
  font-size: 26rpx;
  font-weight: 700;
  padding: 0 40rpx;
  border: none;
}
</style>
