<template>
  <view class="pair-page">
    <QjNavBar title="关系空间" :show-back="true" />

    <!-- 顶部说明 -->
    <view class="hero-card">
      <view class="hero-left">
        <text class="hero-title">亲密空间管理</text>
        <text class="hero-desc">管理您的伴侣、密友与家庭连线，支持多空间无缝切换</text>
      </view>
      <view class="hero-icon-wrap">
        <text class="hero-icon">🌱</text>
      </view>
    </view>

    <!-- 关系列表 -->
    <view class="section-container">
      <text class="section-heading">我的连线空间</text>

      <view v-if="displayPairs.length > 0" class="pairs-stack">
        <view
          v-for="pair in displayPairs"
          :key="pair.id"
          :class="['pair-item-card', isCurrentPair(pair) ? 'current-active' : '']"
          @click="selectPair(pair)"
        >
          <view class="card-left">
            <view class="avatar-ring">
              <text class="avatar-initial">{{ getPartnerName(pair).charAt(0) }}</text>
            </view>
            <view class="name-meta">
              <view class="name-line">
                <text class="partner-name-text">{{ getPartnerName(pair) }}</text>
                <text class="type-pill">{{ formatType(pair.type) }}</text>
                <text v-if="isCurrentPair(pair)" class="current-badge">当前主空间</text>
              </view>
              <text class="code-line">邀请码: {{ pair.invite_code || '已绑定' }}</text>
            </view>
          </view>

          <view class="card-right">
            <view class="score-display">
              <text class="score-num">{{ getPairHealth(pair) }}</text>
              <text class="score-caption">健康分</text>
            </view>
          </view>
        </view>
      </view>

      <view v-else class="empty-state-box">
        <text class="empty-icon">🤝</text>
        <text class="empty-text">当前暂未建立双人关系</text>
        <text class="empty-sub">生成专属邀请码发送给TA，即可开启双人空间</text>
      </view>
    </view>

    <!-- 快捷操作：创建邀请 / 加入关系 -->
    <view class="actions-container">
      <view class="action-card-btn" @click="showCreateInvite = true">
        <text class="action-emoji">💌</text>
        <view class="action-texts">
          <text class="action-main">创建邀请码</text>
          <text class="action-sub">生成 6 位专属码邀请 TA 加入</text>
        </view>
      </view>

      <view class="action-card-btn" @click="showJoinInput = true">
        <text class="action-emoji">🔑</text>
        <view class="action-texts">
          <text class="action-main">加入TA的空间</text>
          <text class="action-sub">输入 TA 发送给您的邀请码</text>
        </view>
      </view>
    </view>

    <!-- 弹窗：创建邀请码 -->
    <view v-if="showCreateInvite" class="modal-backdrop" @click="closeCreatePopup">
      <view class="modal-card" @click.stop>
        <view class="modal-head">
          <text class="modal-title">生成关系邀请码</text>
          <view class="close-x" @click="closeCreatePopup"><text>×</text></view>
        </view>

        <view v-if="!generatedCode" class="modal-form">
          <view class="form-group">
            <text class="form-label">关系类别</text>
            <picker @change="onTypeChange" :value="typeIndex" :range="relationshipTypes">
              <view class="custom-picker-box">
                <text>{{ relationshipTypes[typeIndex] }}</text>
                <text class="picker-arrow">▾</text>
              </view>
            </picker>
          </view>

          <view class="form-group">
            <text class="form-label">给 TA 设置的昵称 (可选)</text>
            <input
              v-model="partnerCustomName"
              placeholder="例如：夏夏、宁子"
              class="form-input"
            />
          </view>

          <button class="modal-submit-btn" @click="handleCreateInvite">立即生成</button>
        </view>

        <view v-else class="invite-success-view">
          <text class="success-tip">邀请码已就绪，请复制发给 TA</text>
          <view class="invite-code-pill">
            <text class="code-digits">{{ generatedCode }}</text>
          </view>
          <button class="modal-submit-btn" @click="copyInviteCode">复制邀请码</button>
        </view>
      </view>
    </view>

    <!-- 弹窗：输入邀请码加入 -->
    <view v-if="showJoinInput" class="modal-backdrop" @click="showJoinInput = false">
      <view class="modal-card" @click.stop>
        <view class="modal-head">
          <text class="modal-title">加入关系空间</text>
          <view class="close-x" @click="showJoinInput = false"><text>×</text></view>
        </view>

        <view class="modal-form">
          <view class="form-group">
            <text class="form-label">输入对方发给您的邀请码</text>
            <input
              v-model.trim="inputInviteCode"
              placeholder="请输入邀请码"
              maxlength="10"
              class="form-input code-center-input"
            />
          </view>

          <button
            class="modal-submit-btn"
            :disabled="!inputInviteCode"
            @click="handleJoinRelationship"
          >
            确认加入
          </button>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { get, post } from '@/utils/request'
import { useUserStore } from '@/stores/user'
import QjNavBar from '@/components/QjNavBar.vue'

const userStore = useUserStore()

const localPairs = ref([])
const showCreateInvite = ref(false)
const showJoinInput = ref(false)
const generatedCode = ref('')
const inputInviteCode = ref('')
const partnerCustomName = ref('')
const typeIndex = ref(0)
const relationshipTypes = ['伴侣', '朋友', '家人', '工作搭档']
const relationshipTypeKeys = ['couple', 'friend', 'family', 'colleague']

const displayPairs = computed(() => {
  if (userStore.isDemoMode) {
    return userStore.pairs && userStore.pairs.length > 0 ? userStore.pairs : []
  }
  return localPairs.value.length > 0 ? localPairs.value : (userStore.pairs || [])
})

onMounted(async () => {
  await loadPairsData()
})

async function loadPairsData() {
  if (userStore.isDemoMode) {
    return
  }
  try {
    const res = await get('/api/v1/pairs')
    localPairs.value = Array.isArray(res) ? res : (res.items || [])
    userStore.pairs = localPairs.value
  } catch (err) {
    // offline or demo fallback
  }
}

function getPartnerName(pair) {
  return pair.custom_partner_nickname || pair.partner_nickname || pair.partner_name || 'TA'
}

function getPairHealth(pair) {
  return pair.health_score || (pair.type === 'couple' ? 88 : 82)
}

function formatType(type) {
  const map = { couple: '伴侣', friend: '朋友', family: '家人', colleague: '搭档' }
  return map[type] || '伴侣'
}

function isCurrentPair(pair) {
  return userStore.currentPair?.id === pair.id
}

function selectPair(pair) {
  userStore.currentPair = pair
  uni.setStorageSync('qj_current_pair', pair.id)
  uni.showToast({ title: `已切换主空间至: ${getPartnerName(pair)}`, icon: 'none' })
}

function onTypeChange(e) {
  typeIndex.value = e.detail.value
}

function closeCreatePopup() {
  showCreateInvite.value = false
  generatedCode.value = ''
  partnerCustomName.value = ''
}

async function handleCreateInvite() {
  if (userStore.isDemoMode) {
    generatedCode.value = 'QJ' + Math.floor(1000 + Math.random() * 9000)
    uni.showToast({ title: '演示邀请码已生成', icon: 'none' })
    return
  }

  try {
    const res = await post('/api/v1/pairs/invite', {
      relationship_type: relationshipTypeKeys[typeIndex.value],
      partner_name: partnerCustomName.value
    })
    generatedCode.value = res.invite_code || 'QJ8888'
    uni.showToast({ title: '邀请码生成成功', icon: 'success' })
  } catch (err) {
    uni.showToast({ title: err.message || '生成失败，请重试', icon: 'none' })
  }
}

function copyInviteCode() {
  uni.setClipboardData({
    data: generatedCode.value,
    success: () => {
      uni.showToast({ title: '邀请码已复制', icon: 'success' })
    }
  })
}

async function handleJoinRelationship() {
  if (!inputInviteCode.value.trim()) return

  if (userStore.isDemoMode) {
    uni.showToast({ title: '已成功加入该关系空间', icon: 'success' })
    showJoinInput.value = false
    inputInviteCode.value = ''
    return
  }

  try {
    await post('/api/v1/pairs/join', {
      invite_code: inputInviteCode.value.trim()
    })
    uni.showToast({ title: '加入成功', icon: 'success' })
    showJoinInput.value = false
    inputInviteCode.value = ''
    await loadPairsData()
  } catch (err) {
    uni.showToast({ title: err.message || '邀请码无效或已失效', icon: 'none' })
  }
}
</script>

<style scoped lang="scss">
@import '@/styles/tokens.scss';

.pair-page {
  min-height: 100vh;
  padding-bottom: 60rpx;
}

.hero-card {
  margin: 20rpx 32rpx 32rpx;
  background: $color-paper-strong;
  border: 1px solid $color-paper-line-strong;
  border-radius: $radius-lg;
  padding: 32rpx 28rpx;
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

.hero-desc {
  font-size: 22rpx;
  color: $color-ink-soft;
  margin-top: 8rpx;
  display: block;
}

.hero-icon-wrap {
  width: 80rpx;
  height: 80rpx;
  border-radius: 50%;
  background: rgba(95, 135, 111, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
}

.hero-icon {
  font-size: 40rpx;
}

.section-container {
  padding: 0 32rpx;
  margin-bottom: 36rpx;
}

.section-heading {
  font-family: $font-serif;
  font-size: 30rpx;
  font-weight: 800;
  color: $color-ink;
  margin-bottom: 20rpx;
  display: block;
}

.pairs-stack {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
}

.pair-item-card {
  background: $color-paper-strong;
  border: 1px solid $color-paper-line;
  border-radius: $radius-md;
  padding: 24rpx 26rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: $shadow-sm;
  transition: all 0.2s ease;

  &.current-active {
    border-color: rgba(215, 104, 72, 0.5);
    background: rgba(255, 250, 244, 0.95);
    box-shadow: 0 8rpx 24rpx rgba(215, 104, 72, 0.1);
  }
}

.card-left {
  display: flex;
  align-items: center;
  gap: 20rpx;
}

.avatar-ring {
  width: 76rpx;
  height: 76rpx;
  border-radius: 50%;
  background: $color-seal-soft;
  border: 2rpx solid rgba(215, 104, 72, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-initial {
  font-family: $font-serif;
  font-size: 34rpx;
  font-weight: 800;
  color: $color-seal-deep;
}

.name-line {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.partner-name-text {
  font-size: 30rpx;
  font-weight: 800;
  color: $color-ink;
}

.type-pill {
  font-size: 20rpx;
  background: $color-moss-soft;
  color: $color-moss-deep;
  padding: 2rpx 12rpx;
  border-radius: 8rpx;
  font-weight: 700;
}

.current-badge {
  font-size: 18rpx;
  background: $color-seal;
  color: #fffdfa;
  padding: 2rpx 10rpx;
  border-radius: 6rpx;
  font-weight: 700;
}

.code-line {
  font-size: 22rpx;
  color: $color-ink-faint;
  margin-top: 6rpx;
  display: block;
}

.score-display {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.score-num {
  font-family: $font-serif;
  font-size: 40rpx;
  font-weight: 800;
  color: $color-moss;
  line-height: 1;
}

.score-caption {
  font-size: 20rpx;
  color: $color-ink-faint;
  margin-top: 4rpx;
}

.empty-state-box {
  background: $color-paper-strong;
  border: 1px dashed $color-paper-line-strong;
  border-radius: $radius-lg;
  padding: 60rpx 30rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.empty-icon {
  font-size: 56rpx;
  margin-bottom: 16rpx;
}

.empty-text {
  font-size: 28rpx;
  font-weight: 700;
  color: $color-ink;
}

.empty-sub {
  font-size: 22rpx;
  color: $color-ink-faint;
  margin-top: 8rpx;
}

.actions-container {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20rpx;
  padding: 0 32rpx;
}

.action-card-btn {
  background: $color-paper-strong;
  border: 1px solid $color-paper-line;
  border-radius: $radius-md;
  padding: 26rpx 22rpx;
  display: flex;
  flex-direction: column;
  gap: 12rpx;
  box-shadow: $shadow-sm;

  &:active {
    background: rgba(244, 221, 212, 0.5);
  }
}

.action-emoji {
  font-size: 44rpx;
}

.action-main {
  font-size: 28rpx;
  font-weight: 800;
  color: $color-ink;
  display: block;
}

.action-sub {
  font-size: 20rpx;
  color: $color-ink-faint;
  margin-top: 4rpx;
  display: block;
}

/* 弹窗通用样式 */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(31, 42, 47, 0.5);
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40rpx;
}

.modal-card {
  width: 100%;
  background: $color-paper-strong;
  border: 1px solid $color-paper-line-strong;
  border-radius: $radius-lg;
  padding: 36rpx;
  box-shadow: $shadow-lg;
}

.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 28rpx;
}

.modal-title {
  font-family: $font-serif;
  font-size: 34rpx;
  font-weight: 800;
  color: $color-ink;
}

.close-x {
  width: 50rpx;
  height: 50rpx;
  border-radius: 50%;
  background: rgba(68, 52, 40, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32rpx;
  color: $color-ink-soft;
}

.modal-form {
  display: flex;
  flex-direction: column;
  gap: 22rpx;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}

.form-label {
  font-size: 24rpx;
  font-weight: 700;
  color: $color-ink-soft;
}

.custom-picker-box {
  height: 80rpx;
  background: rgba(246, 240, 234, 0.7);
  border: 1px solid rgba(68, 52, 40, 0.16);
  border-radius: 12rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24rpx;
  font-size: 28rpx;
  color: $color-ink;
}

.form-input {
  height: 80rpx;
  background: rgba(246, 240, 234, 0.7);
  border: 1px solid rgba(68, 52, 40, 0.16);
  border-radius: 12rpx;
  padding: 0 24rpx;
  font-size: 28rpx;
  color: $color-ink;
}

.code-center-input {
  text-align: center;
  font-size: 36rpx;
  letter-spacing: 6rpx;
  font-weight: 800;
}

.modal-submit-btn {
  height: 84rpx;
  line-height: 84rpx;
  border-radius: 14rpx;
  background: $color-seal;
  color: #fffdfa;
  font-size: 28rpx;
  font-weight: 800;
  border: none;
  margin-top: 10rpx;

  &:active {
    background: $color-seal-deep;
  }
}

.invite-success-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20rpx 0;
}

.success-tip {
  font-size: 26rpx;
  color: $color-ink-soft;
  margin-bottom: 20rpx;
}

.invite-code-pill {
  background: rgba(215, 104, 72, 0.12);
  border: 2rpx dashed $color-seal;
  padding: 20rpx 40rpx;
  border-radius: 16rpx;
  margin-bottom: 30rpx;
}

.code-digits {
  font-family: $font-serif;
  font-size: 52rpx;
  font-weight: 800;
  color: $color-seal-deep;
  letter-spacing: 8rpx;
}
</style>
