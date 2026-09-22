<template>
  <view class="pair-page">
    <!-- 顶部导航与标题 (1:1 严格对齐 04-pairs.png) -->
    <QjNavBar title="关系管理" :show-back="true" />

    <view class="pair-head">
      <text class="eyebrow">关系管理</text>
      <text class="page-title">我的关系</text>
    </view>

    <!-- 关系列表与选择卡 -->
    <view class="pair-list-card">
      <view class="card-head">
        <view>
          <text class="eyebrow">我的关系</text>
          <text class="card-title">选择当前关系</text>
        </view>
        <text class="pair-count-badge">共 {{ pairList.length }} 段</text>
      </view>

      <view class="pairs-grid">
        <view
          v-for="item in pairList"
          :key="item.id"
          class="pair-item"
          :class="{ active: item.id === selectedPairId }"
          @click="selectRelationship(item)"
        >
          <view class="avatar-box">
            <text class="avatar-char">{{ item.name.slice(0, 1) }}</text>
          </view>
          <view class="pair-meta">
            <text class="pair-name">{{ item.name }}</text>
            <text class="pair-type-tag">{{ item.relationLabel }} · {{ item.statusLabel }}</text>
          </view>
          <view class="pair-score-wrap">
            <text class="score-digit">{{ item.score }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 当前选中关系详情微卡 -->
    <view v-if="currentSelectedPair" class="current-pair-card">
      <view class="card-head">
        <view>
          <text class="eyebrow">当前关系</text>
          <text class="card-title">{{ currentSelectedPair.name }} ({{ currentSelectedPair.relationLabel }} {{ currentSelectedPair.statusLabel }})</text>
        </view>
      </view>

      <view class="current-score-row">
        <view class="score-main">
          <text class="score-large">{{ currentSelectedPair.score }}</text>
          <text class="score-label">关系评分</text>
        </view>
        <view class="status-trend-box">
          <text class="trend-text">最近相处状态: 在变好</text>
          <text class="trend-sub">互动平稳，彼此回应积极</text>
        </view>
      </view>

      <button class="primary-action-btn" @click="enterRelationshipSpace">
        进入专属关系页
      </button>
    </view>

    <!-- 底部两大功能卡 (加入关系邀请码 + 当前邀请码) -->
    <view class="pair-actions-container">
      <!-- 卡片 1: 加入关系邀请码 -->
      <view class="action-panel">
        <view class="panel-head">
          <text class="eyebrow">加入关系邀请码</text>
          <text class="panel-title">输入对方给你的邀请码</text>
        </view>

        <view class="field">
          <text class="field-label">邀请码</text>
          <input
            v-model.trim="joinCodeInput"
            class="input code-input"
            type="text"
            maxlength="10"
            placeholder="请输入 10 位邀请码，如 A3H7K8M9Q2"
            placeholder-class="input-ph"
          />
        </view>

        <button
          class="primary-btn"
          :disabled="joining || !joinCodeInput.trim()"
          @click="handleJoinPair"
        >
          {{ joining ? '校验中...' : '选择关系类型' }}
        </button>
      </view>

      <!-- 卡片 2: 当前邀请码 -->
      <view class="action-panel">
        <view class="panel-head">
          <text class="eyebrow">当前邀请码</text>
          <text class="panel-title">把邀请码发给对方</text>
        </view>

        <view class="invite-code-pill">
          <text class="code-status-tag">有效</text>
          <text class="invite-code-text">{{ myInviteCode }}</text>
        </view>

        <view class="code-actions-row">
          <button class="primary-btn flex-btn" @click="copyInviteCode">
            复制邀请码
          </button>
          <button class="ghost-btn flex-btn" @click="refreshInviteCode">
            重新生成
          </button>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { post } from '@/utils/request'
import { useUserStore } from '@/stores/user'
import QjNavBar from '@/components/QjNavBar.vue'

const userStore = useUserStore()

const selectedPairId = ref('pair-linxia')
const joinCodeInput = ref('')
const joining = ref(false)
const myInviteCode = ref('A3H7K8M9Q2')

// 真实/样例关系列表 (对齐 04-pairs.png 中的 林夏、周宁、顾遥)
const pairList = ref([
  {
    id: 'pair-linxia',
    name: '林夏',
    relationLabel: '情侣',
    statusLabel: '已建立',
    score: 78,
    active: true,
  },
  {
    id: 'pair-zhouning',
    name: '周宁',
    relationLabel: '朋友',
    statusLabel: '已建立',
    score: 74,
    active: false,
  },
  {
    id: 'pair-guyao',
    name: '顾遥',
    relationLabel: '朋友',
    statusLabel: '待对方决定',
    score: 62,
    active: false,
  },
])

const currentSelectedPair = computed(() => {
  return pairList.value.find(p => p.id === selectedPairId.value) || pairList.value[0]
})

onMounted(async () => {
  await userStore.fetchMe()
  if (userStore.activePair) {
    const p = userStore.activePair
    const partner = userStore.partnerName || '伴侣'
    // 若有真实绑定关系，插入至首位
    const exists = pairList.value.find(item => item.name === partner)
    if (!exists) {
      pairList.value.unshift({
        id: p.id || 'current-pair',
        name: partner,
        relationLabel: p.type === 'couple' ? '情侣' : '朋友',
        statusLabel: '已建立',
        score: 82,
        active: true,
      })
    }
  }
})

function selectRelationship(item) {
  selectedPairId.value = item.id
}

function enterRelationshipSpace() {
  uni.switchTab({ url: '/pages/home/home' })
}

// 加入关系
async function handleJoinPair() {
  if (!joinCodeInput.value.trim()) {
    uni.showToast({ title: '请输入10位邀请码', icon: 'none' })
    return
  }

  joining.value = true
  try {
    await post('/api/v1/pair/join', { invite_code: joinCodeInput.value.trim().toUpperCase() })
    uni.showToast({ title: '加入成功，已建立空间', icon: 'success' })
    await userStore.fetchMe()
  } catch (err) {
    uni.showToast({ title: err.message || '邀请码无效或已过期', icon: 'none' })
  } finally {
    joining.value = false
  }
}

// 复制邀请码
function copyInviteCode() {
  uni.setClipboardData({
    data: myInviteCode.value,
    success: () => {
      uni.showToast({ title: '邀请码已复制', icon: 'none' })
    }
  })
}

// 重新生成
function refreshInviteCode() {
  const chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
  let newCode = ''
  for (let i = 0; i < 10; i++) {
    newCode += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  myInviteCode.value = newCode
  uni.showToast({ title: '已生成新邀请码', icon: 'none' })
}
</script>

<style lang="scss" scoped>
.pair-page {
  min-height: 100vh;
  padding: 16rpx 32rpx 80rpx;
  background-color: #f7f1eb;
  background-image:
    radial-gradient(900rpx circle at 10% -10%, rgba(215, 104, 72, 0.15), transparent 45%),
    radial-gradient(700rpx circle at 90% -5%, rgba(240, 213, 184, 0.4), transparent 50%),
    linear-gradient(180deg, #fcf7f2 0%, #f6efe7 100%);
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.pair-head {
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

/* 关系选择卡 */
.pair-list-card {
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
      font-size: 30rpx;
      font-weight: 700;
      color: #1f2a2f;
      display: block;
    }

    .pair-count-badge {
      font-size: 24rpx;
      color: #7c837f;
    }
  }
}

.pairs-grid {
  display: flex;
  flex-direction: column;
  gap: 14rpx;
}

.pair-item {
  display: flex;
  align-items: center;
  gap: 20rpx;
  padding: 20rpx;
  background: #ffffff;
  border: 1px solid rgba(68, 52, 40, 0.1);
  border-radius: 12rpx;
  transition: all 0.2s ease;

  &.active {
    border-color: #d76848;
    background: #fdf8f4;
    box-shadow: 0 4rpx 14rpx rgba(215, 104, 72, 0.12);
  }

  .avatar-box {
    width: 68rpx;
    height: 68rpx;
    border-radius: 50%;
    background: #fceee8;
    border: 1px solid rgba(215, 104, 72, 0.25);
    display: flex;
    align-items: center;
    justify-content: center;

    .avatar-char {
      font-family: $font-serif;
      font-size: 30rpx;
      font-weight: 700;
      color: #d76848;
    }
  }

  .pair-meta {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4rpx;

    .pair-name {
      font-size: 28rpx;
      font-weight: 600;
      color: #1f2a2f;
    }

    .pair-type-tag {
      font-size: 22rpx;
      color: #7c837f;
    }
  }

  .pair-score-wrap {
    .score-digit {
      font-family: $font-serif;
      font-size: 34rpx;
      font-weight: 700;
      color: #d76848;
    }
  }
}

/* 当前选中关系微卡 */
.current-pair-card {
  background: rgba(255, 250, 244, 0.94);
  border: 1px solid rgba(68, 52, 40, 0.12);
  border-radius: 16rpx;
  padding: 30rpx;
  box-shadow: 0 8rpx 22rpx rgba(74, 52, 36, 0.05);
  display: flex;
  flex-direction: column;
  gap: 20rpx;

  .card-head {
    .card-title {
      font-family: $font-serif;
      font-size: 32rpx;
      font-weight: 700;
      color: #1f2a2f;
      display: block;
    }
  }

  .current-score-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16rpx 0;
    border-top: 1px solid rgba(68, 52, 40, 0.06);
    border-bottom: 1px solid rgba(68, 52, 40, 0.06);

    .score-main {
      display: flex;
      align-items: baseline;
      gap: 10rpx;

      .score-large {
        font-family: $font-serif;
        font-size: 54rpx;
        font-weight: 700;
        color: #d76848;
        line-height: 1;
      }

      .score-label {
        font-size: 24rpx;
        color: #7c837f;
      }
    }

    .status-trend-box {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 4rpx;

      .trend-text {
        font-size: 26rpx;
        font-weight: 600;
        color: #5f876f;
      }

      .trend-sub {
        font-size: 22rpx;
        color: #7c837f;
      }
    }
  }

  .primary-action-btn {
    width: 100%;
    height: 76rpx;
    line-height: 74rpx;
    background: #d76848;
    border: 1px solid #aa4d33;
    border-radius: 12rpx;
    color: #ffffff;
    font-size: 28rpx;
    font-weight: 600;
    text-align: center;
    box-shadow: 0 6rpx 16rpx rgba(215, 104, 72, 0.2);
  }
}

/* 底部两大功能卡 */
.pair-actions-container {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.action-panel {
  background: rgba(255, 250, 244, 0.94);
  border: 1px solid rgba(68, 52, 40, 0.12);
  border-radius: 16rpx;
  padding: 30rpx;
  box-shadow: 0 8rpx 22rpx rgba(74, 52, 36, 0.05);
  display: flex;
  flex-direction: column;
  gap: 20rpx;

  .panel-head {
    .panel-title {
      font-family: $font-serif;
      font-size: 30rpx;
      font-weight: 700;
      color: #1f2a2f;
      display: block;
    }
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 8rpx;

    .field-label {
      font-size: 24rpx;
      color: #5b666c;
      font-weight: 500;
    }

    .code-input {
      height: 76rpx;
      background: #ffffff;
      border: 1px solid rgba(68, 52, 40, 0.15);
      border-radius: 10rpx;
      padding: 0 20rpx;
      font-size: 28rpx;
      color: #1f2a2f;
      font-weight: 600;
      letter-spacing: 2rpx;
    }

    .input-ph {
      color: #a1aaa7;
      font-size: 24rpx;
      letter-spacing: normal;
    }
  }

  .invite-code-pill {
    background: #ffffff;
    border: 1px solid rgba(68, 52, 40, 0.15);
    border-radius: 12rpx;
    padding: 24rpx;
    display: flex;
    align-items: center;
    justify-content: space-between;

    .code-status-tag {
      font-size: 20rpx;
      background: #eaf2ea;
      color: #5f876f;
      padding: 4rpx 12rpx;
      border-radius: 6rpx;
      font-weight: 600;
    }

    .invite-code-text {
      font-family: monospace;
      font-size: 36rpx;
      font-weight: 700;
      color: #1f2a2f;
      letter-spacing: 4rpx;
    }
  }

  .code-actions-row {
    display: flex;
    gap: 16rpx;

    .flex-btn {
      flex: 1;
    }
  }

  .primary-btn {
    width: 100%;
    height: 76rpx;
    line-height: 74rpx;
    background: #d76848;
    border: 1px solid #aa4d33;
    border-radius: 12rpx;
    color: #ffffff;
    font-size: 28rpx;
    font-weight: 600;
    text-align: center;
    box-shadow: 0 6rpx 16rpx rgba(215, 104, 72, 0.2);

    &[disabled] {
      opacity: 0.6;
    }
  }

  .ghost-btn {
    height: 76rpx;
    line-height: 74rpx;
    background: #ffffff;
    border: 1px solid rgba(68, 52, 40, 0.18);
    border-radius: 12rpx;
    color: #5b666c;
    font-size: 28rpx;
    font-weight: 500;
    text-align: center;
  }
}
</style>
