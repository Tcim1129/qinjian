<template>
  <view class="discover-page">
    <view class="discover-header">
      <text class="eyebrow">DISCOVER</text>
      <text class="title">把疗愈感和陪伴感收进同一个空间</text>
      <text class="subtitle">这里负责承接课程、测试、关系工具和更多服务，不再做散乱入口。</text>
    </view>

    <scroll-view class="discover-scroll" scroll-y>
      <view class="feature-hero" @click="openVoiceCheckin">
        <view>
          <text class="hero-title">今日推荐：AI 语音陪伴打卡</text>
          <text class="hero-copy">像聊天一样完成今天的关系记录，特别适合不想面对表单的时候。</text>
          <text class="hero-cta">立即开始 ></text>
        </view>
        <text class="hero-icon">◎</text>
      </view>

      <view class="section-card">
        <text class="section-title">现在就能用</text>
        <view class="feature-grid">
          <view class="feature-item" v-for="item in features" :key="item.name" @click="openFeature(item)">
            <text class="feature-icon">{{ item.icon }}</text>
            <text class="feature-name">{{ item.name }}</text>
            <text class="feature-desc">{{ item.desc }}</text>
          </view>
        </view>
      </view>

      <view class="section-card">
        <text class="section-title">继续探索</text>
        <view class="service-list">
          <view class="service-row" v-for="item in services" :key="item.title" @click="openService(item)">
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
        { icon: '◎', name: '语音陪伴', desc: '像聊天一样完成今天记录', type: 'voice-checkin' },
        { icon: '✦', name: '四步打卡', desc: '用表单快速补齐今天状态', path: '/pages/checkin/index' },
        { icon: '▥', name: '关系报告', desc: '查看日报、周报和趋势', path: '/pages/report/index' },
        { icon: '◌', name: '绑定关系', desc: '创建或加入你们的关系空间', path: '/pages/pair/index' },
      ],
      services: [
        { title: '继续完善主页记录', desc: '回到首页补看今天的脉搏、连击天数和成长树状态。', tag: '首页', path: '/pages/index/index' },
        { title: '同步账户与关系信息', desc: '进入我的页面更新昵称、备注、解绑状态与账号信息。', tag: '我的', path: '/pages/profile/index' },
        { title: '开始建立关系', desc: '如果你还没绑定，可以直接进入绑定入口生成邀请码或加入对方。', tag: '关系', path: '/pages/pair/index' },
      ]
    }
  },
  methods: {
    go(path) {
      if (!path) return
      uni.reLaunch({ url: path })
    },
    openVoiceCheckin() {
      uni.setStorageSync('qj_checkin_mode', 'voice')
      this.go('/pages/checkin/index')
    },
    openFeature(item) {
      if (item.type === 'voice-checkin') {
        this.openVoiceCheckin()
        return
      }
      this.go(item.path)
    },
    openService(item) {
      this.go(item.path)
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

.hero-cta {
  display: inline-block;
  margin-top: 18rpx;
  font-size: 22rpx;
  font-weight: 800;
  color: #fff;
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
