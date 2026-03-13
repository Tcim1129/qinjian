<template>
  <view class="discover-page">
    <view class="discover-header">
      <text class="eyebrow">DISCOVER</text>
      <text class="title">把疗愈感和陪伴感收进同一个空间</text>
      <text class="subtitle">这里负责承接课程、测试、关系工具和更多服务，不再做散乱入口。</text>
    </view>

    <scroll-view class="discover-scroll" scroll-y>
      <view class="feature-hero">
        <view>
          <text class="hero-title">今日推荐：AI 语音陪伴打卡</text>
          <text class="hero-copy">像聊天一样完成今天的关系记录，特别适合不想面对表单的时候。</text>
        </view>
        <text class="hero-icon">◎</text>
      </view>

      <view class="section-card">
        <text class="section-title">热门功能</text>
        <view class="feature-grid">
          <view class="feature-item" v-for="item in features" :key="item.name">
            <text class="feature-icon">{{ item.icon }}</text>
            <text class="feature-name">{{ item.name }}</text>
            <text class="feature-desc">{{ item.desc }}</text>
          </view>
        </view>
      </view>

      <view class="section-card">
        <text class="section-title">内容与服务</text>
        <view class="service-list">
          <view class="service-row" v-for="item in services" :key="item.title">
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
      features: [
        { icon: '◌', name: '依恋测试', desc: '看懂自己的互动习惯' },
        { icon: '◍', name: '关系体检', desc: '快速判断当前状态' },
        { icon: '◎', name: '异地关系', desc: '为异地恋设计的协作工具' },
        { icon: '✦', name: '情侣挑战', desc: '每天一个小动作让关系升温' },
      ],
      services: [
        { title: '心理课程', desc: '把复杂关系议题讲得清楚，也讲得温柔。', tag: '内容' },
        { title: '专家咨询', desc: '需要更专业帮助时，服务入口继续保留。', tag: '服务' },
        { title: '会员方案', desc: '把高频陪伴、报告和课程做成持续价值。', tag: '商业化' },
      ]
    }
  }
}
</script>

<style scoped>
.discover-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #fff9f3 0%, #f5eee7 100%);
}

.discover-header {
  padding: 84rpx 28rpx 32rpx;
}

.eyebrow {
  font-size: 20rpx;
  letter-spacing: 4rpx;
  text-transform: uppercase;
  color: #a1887f;
}

.title {
  display: block;
  margin-top: 18rpx;
  font-size: 48rpx;
  line-height: 1.2;
  font-weight: 800;
  color: #2f2522;
}

.subtitle {
  display: block;
  margin-top: 14rpx;
  font-size: 22rpx;
  line-height: 1.8;
  color: #6d4c41;
}

.discover-scroll {
  height: calc(100vh - 140rpx);
  padding: 0 28rpx;
  box-sizing: border-box;
}

.feature-hero,
.section-card {
  background: rgba(255,255,255,0.96);
  border-radius: 32rpx;
  box-shadow: 0 16rpx 32rpx rgba(62, 39, 35, 0.08);
  border: 1rpx solid rgba(212, 163, 115, 0.12);
}

.feature-hero {
  padding: 28rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #5d4037, #8d6e63 52%, #d4a373 100%);
}

.hero-title,
.hero-copy,
.hero-icon {
  color: #fff;
}

.hero-title {
  display: block;
  font-size: 30rpx;
  font-weight: 800;
}

.hero-copy {
  display: block;
  margin-top: 14rpx;
  font-size: 22rpx;
  line-height: 1.8;
  opacity: 0.84;
}

.hero-icon {
  font-size: 52rpx;
  margin-left: 20rpx;
}

.section-card {
  margin-top: 24rpx;
  padding: 28rpx;
}

.section-title {
  display: block;
  font-size: 30rpx;
  font-weight: 800;
  color: #2f2522;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16rpx;
  margin-top: 22rpx;
}

.feature-item {
  padding: 22rpx;
  border-radius: 26rpx;
  background: #fcf4ed;
}

.feature-icon {
  font-size: 34rpx;
}

.feature-name {
  display: block;
  margin-top: 14rpx;
  font-size: 25rpx;
  font-weight: 800;
  color: #3e2723;
}

.feature-desc,
.service-desc {
  display: block;
  margin-top: 10rpx;
  font-size: 20rpx;
  line-height: 1.7;
  color: #8d6e63;
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

.service-title {
  font-size: 24rpx;
  font-weight: 800;
  color: #3e2723;
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
  height: 180rpx;
}
</style>
