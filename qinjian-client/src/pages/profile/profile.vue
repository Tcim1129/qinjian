<template>
  <view class="profile-page">
    <view class="profile-head">
      <text class="eyebrow">我的</text>
      <text class="page-title">个人中心</text>
    </view>

    <!-- 用户身份卡片 -->
    <view class="user-hero-card">
      <view class="avatar-ring">
        <text class="avatar-char">{{ avatarInitial }}</text>
      </view>

      <view class="user-meta">
        <view class="name-badge-row">
          <text class="user-nickname">{{ displayName }}</text>
          <text v-if="userStore.isDemoMode" class="demo-badge">样例体验中</text>
          <text v-else-if="userStore.isLoggedIn" class="status-badge">已认证</text>
        </view>
        <text class="user-sub">{{ displayAccount }}</text>
      </view>
    </view>

    <!-- 伴侣主空间微卡 -->
    <view class="partner-space-card" @click="goPair">
      <view class="partner-meta">
        <text class="eyebrow">当前空间</text>
        <text class="partner-title">{{ userStore.partnerName || '林夏' }} 的专属空间</text>
        <text class="partner-desc">管理关系连线、邀请码与状态设置</text>
      </view>
      <text class="card-arrow">&gt;</text>
    </view>

    <!-- 常用功能分组列表 (纯文字排版，无任何卡通 Emoji) -->
    <view class="menu-group-card">
      <view class="menu-item" @click="goPair">
        <view class="item-text-group">
          <text class="item-title">关系管理</text>
          <text class="item-sub">切换伴侣、添加关系与邀请码</text>
        </view>
        <text class="item-arrow">&gt;</text>
      </view>

      <view class="menu-item" @click="goCheckin">
        <view class="item-text-group">
          <text class="item-title">今日记录</text>
          <text class="item-sub">沉淀真实的交流与微小心境</text>
        </view>
        <text class="item-arrow">&gt;</text>
      </view>

      <view class="menu-item" @click="goReport">
        <view class="item-text-group">
          <text class="item-title">双人简报</text>
          <text class="item-sub">查看日报、周报与五项关系状态</text>
        </view>
        <text class="item-arrow">&gt;</text>
      </view>

      <view class="menu-item" @click="goTimeline">
        <view class="item-text-group">
          <text class="item-title">关系日历</text>
          <text class="item-sub">回忆轨迹与时间轴沉淀</text>
        </view>
        <text class="item-arrow">&gt;</text>
      </view>
    </view>

    <!-- 偏好与回复方式卡片 -->
    <view class="pref-card">
      <view class="pref-head">
        <text class="eyebrow">偏好</text>
        <text class="pref-title">AI 交流风格</text>
      </view>

      <view class="pref-options">
        <view
          v-for="tone in toneOptions"
          :key="tone.key"
          class="tone-chip"
          :class="{ active: selectedTone === tone.key }"
          @click="selectedTone = tone.key"
        >
          <text class="tone-label">{{ tone.label }}</text>
        </view>
      </view>
    </view>

    <!-- 底部退出与登录按钮 -->
    <view class="action-footer">
      <button
        v-if="userStore.isDemoMode"
        class="ghost-action-btn"
        @click="handleExitDemo"
      >
        退出体验样例，登录真实账号
      </button>

      <button
        v-else-if="userStore.isLoggedIn"
        class="ghost-action-btn"
        @click="handleLogout"
      >
        退出当前登录
      </button>

      <button
        v-else
        class="primary-action-btn"
        @click="goLogin"
      >
        立即登录 / 体验样例
      </button>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const selectedTone = ref('gentle')
const toneOptions = [
  { key: 'gentle', label: '温柔体谅，先共情' },
  { key: 'direct', label: '直接简洁，给行动' },
  { key: 'rational', label: '理性分析，拆重点' },
]

onMounted(async () => {
  await userStore.bootstrap()
})

const displayName = computed(() => {
  if (userStore.isDemoMode) return '陈一 (样例)'
  return userStore.me?.nickname || (userStore.isLoggedIn ? '亲健朋友' : '访客')
})

const displayAccount = computed(() => {
  if (userStore.isDemoMode) return '伴侣连线：林夏 · 体验账号'
  return userStore.me?.phone || userStore.me?.email || (userStore.isLoggedIn ? '已登录' : '点击去登录')
})

const avatarInitial = computed(() => {
  if (userStore.isDemoMode) return '陈'
  const name = userStore.me?.nickname || '亲'
  return name.charAt(0)
})

function goPair() {
  uni.navigateTo({ url: '/pages/pair/pair' })
}

function goTimeline() {
  uni.navigateTo({ url: '/pages/timeline/timeline' })
}

function goCheckin() {
  uni.switchTab({ url: '/pages/checkin/checkin' })
}

function goReport() {
  uni.switchTab({ url: '/pages/report/report' })
}

function goLogin() {
  uni.navigateTo({ url: '/pages/auth/login' })
}

function handleExitDemo() {
  userStore.logout()
  uni.showToast({ title: '已退出样例模式', icon: 'none' })
  setTimeout(() => {
    uni.navigateTo({ url: '/pages/auth/login' })
  }, 400)
}

function handleLogout() {
  uni.showModal({
    title: '提示',
    content: '确认退出当前登录吗？',
    success: (res) => {
      if (res.confirm) {
        userStore.logout()
        uni.showToast({ title: '已退出登录', icon: 'none' })
        setTimeout(() => {
          uni.navigateTo({ url: '/pages/auth/login' })
        }, 400)
      }
    }
  })
}
</script>

<style lang="scss" scoped>
.profile-page {
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

.profile-head {
  padding: 10rpx 0;

  .page-title {
    font-family: $font-serif;
    font-size: 42rpx;
    font-weight: 700;
    color: #1f2a2f;
    line-height: 1.3;
    display: block;
  }
}

/* 用户卡片 */
.user-hero-card {
  background: rgba(255, 250, 244, 0.94);
  border: 1px solid rgba(68, 52, 40, 0.12);
  border-radius: 16rpx;
  padding: 30rpx;
  box-shadow: 0 8rpx 22rpx rgba(74, 52, 36, 0.05);
  display: flex;
  align-items: center;
  gap: 24rpx;

  .avatar-ring {
    width: 96rpx;
    height: 96rpx;
    border-radius: 50%;
    background: #fceee8;
    border: 2rpx solid rgba(215, 104, 72, 0.3);
    display: flex;
    align-items: center;
    justify-content: center;

    .avatar-char {
      font-family: $font-serif;
      font-size: 42rpx;
      font-weight: 700;
      color: #d76848;
    }
  }

  .user-meta {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 8rpx;

    .name-badge-row {
      display: flex;
      align-items: center;
      gap: 12rpx;

      .user-nickname {
        font-family: $font-serif;
        font-size: 32rpx;
        font-weight: 700;
        color: #1f2a2f;
      }

      .demo-badge {
        font-size: 20rpx;
        background: #fceee8;
        color: #aa4d33;
        padding: 2rpx 12rpx;
        border-radius: 6rpx;
        border: 1px solid rgba(215, 104, 72, 0.25);
      }

      .status-badge {
        font-size: 20rpx;
        background: #eaf2ea;
        color: #5f876f;
        padding: 2rpx 12rpx;
        border-radius: 6rpx;
      }
    }

    .user-sub {
      font-size: 24rpx;
      color: #7c837f;
    }
  }
}

/* 伴侣空间卡 */
.partner-space-card {
  background:
    linear-gradient(140deg, rgba(215, 104, 72, 0.08) 0%, rgba(240, 213, 184, 0.14) 100%),
    rgba(255, 250, 244, 0.94);
  border: 1px solid rgba(68, 52, 40, 0.12);
  border-radius: 16rpx;
  padding: 28rpx 30rpx;
  box-shadow: 0 8rpx 22rpx rgba(74, 52, 36, 0.05);
  display: flex;
  align-items: center;
  justify-content: space-between;

  .partner-meta {
    display: flex;
    flex-direction: column;
    gap: 6rpx;

    .partner-title {
      font-size: 28rpx;
      font-weight: 600;
      color: #1f2a2f;
    }

    .partner-desc {
      font-size: 22rpx;
      color: #7c837f;
    }
  }

  .card-arrow {
    font-size: 28rpx;
    color: #7c837f;
  }
}

/* 分组菜单列表 */
.menu-group-card {
  background: rgba(255, 250, 244, 0.94);
  border: 1px solid rgba(68, 52, 40, 0.12);
  border-radius: 16rpx;
  overflow: hidden;
  box-shadow: 0 8rpx 22rpx rgba(74, 52, 36, 0.05);

  .menu-item {
    padding: 26rpx 30rpx;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid rgba(68, 52, 40, 0.06);

    &:last-child {
      border-bottom: none;
    }

    .item-text-group {
      display: flex;
      flex-direction: column;
      gap: 4rpx;

      .item-title {
        font-size: 28rpx;
        font-weight: 600;
        color: #1f2a2f;
      }

      .item-sub {
        font-size: 22rpx;
        color: #7c837f;
      }
    }

    .item-arrow {
      font-size: 28rpx;
      color: #b4bab8;
    }
  }
}

/* 偏好卡片 */
.pref-card {
  background: rgba(255, 250, 244, 0.94);
  border: 1px solid rgba(68, 52, 40, 0.12);
  border-radius: 16rpx;
  padding: 30rpx;
  box-shadow: 0 8rpx 22rpx rgba(74, 52, 36, 0.05);
  display: flex;
  flex-direction: column;
  gap: 18rpx;

  .pref-title {
    font-family: $font-serif;
    font-size: 30rpx;
    font-weight: 700;
    color: #1f2a2f;
    display: block;
  }

  .pref-options {
    display: flex;
    flex-direction: column;
    gap: 12rpx;

    .tone-chip {
      padding: 16rpx 20rpx;
      border-radius: 10rpx;
      background: #ffffff;
      border: 1px solid rgba(68, 52, 40, 0.1);

      .tone-label {
        font-size: 26rpx;
        color: #5b666c;
      }

      &.active {
        background: #fceee8;
        border-color: #d76848;

        .tone-label {
          color: #aa4d33;
          font-weight: 600;
        }
      }
    }
  }
}

/* 底部操作 */
.action-footer {
  padding-top: 10rpx;

  .primary-action-btn {
    width: 100%;
    height: 80rpx;
    line-height: 78rpx;
    background: #d76848;
    border: 1px solid #aa4d33;
    border-radius: 12rpx;
    color: #ffffff;
    font-size: 28rpx;
    font-weight: 600;
    text-align: center;
  }

  .ghost-action-btn {
    width: 100%;
    height: 80rpx;
    line-height: 78rpx;
    background: #ffffff;
    border: 1px solid rgba(68, 52, 40, 0.15);
    border-radius: 12rpx;
    color: #5b666c;
    font-size: 26rpx;
    font-weight: 500;
    text-align: center;
  }
}
</style>
