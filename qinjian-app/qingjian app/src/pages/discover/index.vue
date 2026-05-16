<template>
  <view class="discover-page">
    <scroll-view class="discover-scroll" scroll-y>
      <view class="hero-shell">
        <view class="brand-chip">
          <image class="brand-chip__logo" src="../../static/brand-logo.jpg" mode="aspectFit"></image>
          <view class="brand-chip__copy">
            <text class="brand-chip__eyebrow">QINJIAN APP</text>
            <text class="brand-chip__name">发现与工具</text>
          </view>
        </view>
        <text class="hero-title">把体检、简报、打卡和绑定入口编排成同一条关系工作流</text>
        <view class="section-rule"></view>
        <text class="hero-subtitle">这里不再只是功能堆叠，而是给你一条从记录、评估到判断再到行动的连续路径。</text>
      </view>

      <view class="spotlight-card" @click="openFeature(spotlight)">
        <view>
          <text class="section-eyebrow">TODAY'S SPOTLIGHT</text>
          <text class="spotlight-title">{{ spotlight.title }}</text>
          <text class="spotlight-copy">{{ spotlight.desc }}</text>
          <text class="spotlight-cta">立即进入</text>
        </view>
        <text class="spotlight-icon">{{ spotlight.icon }}</text>
      </view>

      <view class="panel-card">
        <text class="section-eyebrow">CORE TOOLS</text>
        <text class="card-title">现在就能用的关系入口</text>
        <view class="feature-grid">
          <view class="feature-card" v-for="item in features" :key="item.name" @click="openFeature(item)">
            <text class="feature-icon">{{ item.icon }}</text>
            <text class="feature-name">{{ item.name }}</text>
            <text class="feature-desc">{{ item.desc }}</text>
          </view>
        </view>
      </view>

      <view class="panel-card">
        <text class="section-eyebrow">NEXT STEP</text>
        <text class="card-title">继续往前走</text>
        <view class="service-list">
          <view class="service-row" v-for="item in services" :key="item.title" @click="openFeature(item)">
            <view>
              <text class="service-title">{{ item.title }}</text>
              <text class="service-desc">{{ item.desc }}</text>
            </view>
            <text class="service-tag">{{ item.tag }}</text>
          </view>
        </view>
      </view>

      <view class="page-spacer"></view>
    </scroll-view>

    <FloatingTabBar current="/pages/discover/index" />
  </view>
</template>

<script>
import FloatingTabBar from '../../components/FloatingTabBar.vue'

export default {
  components: { FloatingTabBar },
  data() {
    return {
      spotlight: {
        title: '本周关系体检',
        desc: '正式提交一次周评估，让系统把你的分数、维度和变化趋势写回报告页。',
        icon: '◐',
        path: '/pages/discover/health-test/index',
        mode: 'navigate'
      },
      features: [
        { icon: '◌', name: '语音陪伴', desc: '像聊天一样完成今天的记录', path: '/pages/checkin/index', mode: 'reLaunch' },
        { icon: '✦', name: '关系体检', desc: '正式提交本周评估并回看趋势', path: '/pages/discover/health-test/index', mode: 'navigate' },
        { icon: '▣', name: '关系简报', desc: '查看最新判断与安全边界', path: '/pages/report/index', mode: 'reLaunch' },
        { icon: '◎', name: '绑定关系', desc: '创建或加入双人空间', path: '/pages/pair/index', mode: 'reLaunch' },
      ],
      services: [
        { title: '继续补上今天的记录', desc: '打卡完成后，系统的边界判断和策略切换会更稳。', tag: '记录', path: '/pages/checkin/index', mode: 'reLaunch' },
        { title: '回到我的关系空间', desc: '查看最新的体检摘要、安全边界和策略状态。', tag: '空间', path: '/pages/profile/index', mode: 'reLaunch' },
        { title: '进入关系报告', desc: '从简报页集中查看判断、证据和下一步动作。', tag: '简报', path: '/pages/report/index', mode: 'reLaunch' },
      ]
    }
  },
  methods: {
    openFeature(item) {
      if (!item?.path) return
      if (item.mode === 'navigate') {
        uni.navigateTo({ url: item.path })
        return
      }
      uni.reLaunch({ url: item.path })
    }
  }
}
</script>

<style scoped>
.discover-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: linear-gradient(180deg, #fff9f3 0%, #f4ede6 100%);
}

.discover-scroll {
  flex: 1;
  min-height: 0;
  padding: 28rpx 28rpx calc(28rpx + env(safe-area-inset-bottom));
  box-sizing: border-box;
}

.hero-shell,
.spotlight-card,
.panel-card {
  border-radius: 34rpx;
  background: rgba(255, 255, 255, 0.96);
  border: 1rpx solid rgba(212, 163, 115, 0.12);
  box-shadow: 0 18rpx 36rpx rgba(62, 39, 35, 0.08);
}

.hero-shell {
  padding: 32rpx;
  background: linear-gradient(145deg, rgba(255, 248, 241, 0.98), rgba(239, 247, 252, 0.92));
  position: relative;
  overflow: hidden;
  animation: discoverHeroFloat 7.2s ease-in-out infinite;
}

.hero-shell::after {
  content: "";
  position: absolute;
  right: -90rpx;
  top: -100rpx;
  width: 240rpx;
  height: 240rpx;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(212, 163, 115, 0.22), rgba(212, 163, 115, 0));
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
.section-eyebrow {
  font-size: 18rpx;
  letter-spacing: 4rpx;
  text-transform: uppercase;
  color: #a1887f;
}

.brand-chip__name,
.card-title,
.spotlight-title {
  font-size: 30rpx;
  font-weight: 800;
  color: #2f2522;
  font-family: "Times New Roman", "Georgia", "Songti SC", serif;
  letter-spacing: 0.4rpx;
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
.spotlight-copy,
.feature-desc,
.service-desc {
  display: block;
  margin-top: 12rpx;
  font-size: 22rpx;
  line-height: 1.8;
  color: #6d4c41;
}

.spotlight-card,
.panel-card {
  margin-top: 24rpx;
  padding: 28rpx;
}

.spotlight-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 22rpx;
  background: linear-gradient(135deg, #5d4037, #8d6e63 52%, #d4a373 100%);
}

.spotlight-title,
.spotlight-copy,
.spotlight-cta,
.spotlight-icon,
.section-eyebrow {
  color: inherit;
}

.spotlight-card .section-eyebrow,
.spotlight-card .spotlight-title,
.spotlight-card .spotlight-copy,
.spotlight-card .spotlight-cta,
.spotlight-card .spotlight-icon {
  color: #fff;
}

.spotlight-cta {
  display: inline-block;
  margin-top: 18rpx;
  font-size: 22rpx;
  font-weight: 800;
}

.spotlight-icon {
  font-size: 54rpx;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16rpx;
  margin-top: 22rpx;
}

.feature-card {
  padding: 22rpx;
  border-radius: 26rpx;
  background: #fcf4ed;
  border: 1rpx solid rgba(212, 163, 115, 0.12);
  box-shadow: 0 12rpx 24rpx rgba(93, 64, 55, 0.06);
  transition: transform 0.22s ease, box-shadow 0.22s ease;
}

.feature-card:active {
  transform: scale(0.985) translateY(2rpx);
  box-shadow: 0 6rpx 14rpx rgba(93, 64, 55, 0.08);
}

.feature-icon {
  font-size: 34rpx;
}

.feature-name,
.service-title {
  display: block;
  margin-top: 14rpx;
  font-size: 26rpx;
  font-weight: 800;
  color: #3e2723;
}

.service-list {
  margin-top: 18rpx;
}

.service-row {
  display: flex;
  justify-content: space-between;
  gap: 20rpx;
  padding: 22rpx 0;
  border-bottom: 1rpx solid #f2e9df;
}

.service-row:last-child {
  border-bottom: none;
}

.service-tag {
  align-self: flex-start;
  padding: 8rpx 18rpx;
  border-radius: 999rpx;
  background: #f8efe6;
  color: #8d6e63;
  font-size: 20rpx;
  font-weight: 700;
}

.page-spacer {
  height: 120rpx;
}

@keyframes discoverHeroFloat {
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

@media (max-width: 390px) {
  .feature-grid {
    grid-template-columns: 1fr;
  }

  .service-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
