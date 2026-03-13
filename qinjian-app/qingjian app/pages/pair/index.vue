<template>
  <view class="pair-page">
    <view class="pair-hero">
      <text class="eyebrow">PAIR</text>
      <text class="title">还差一步，把关系空间真正连起来</text>
      <text class="subtitle">创建邀请码给对方，或者输入对方的邀请码完成绑定。</text>
    </view>

    <view class="pair-card">
      <text class="section-title">创建邀请码</text>
      <view class="type-row">
        <text v-for="item in types" :key="item.value" class="type-chip" :class="{ active: pairType === item.value }" @click="pairType = item.value">{{ item.label }}</text>
      </view>
      <button class="primary-btn" @click="createPair">创建邀请码</button>
      <view v-if="createdPair" class="invite-box">
        <text class="invite-label">邀请码</text>
        <text class="invite-code">{{ createdPair.invite_code }}</text>
      </view>
    </view>

    <view class="pair-card">
      <text class="section-title">输入邀请码</text>
      <input v-model="inviteCode" class="invite-input" maxlength="6" placeholder="6 位邀请码" />
      <button class="primary-btn" @click="joinPair">立即绑定</button>
    </view>
  </view>
</template>

<script>
import api from '../../utils/api.js'
import { syncSession } from '../../utils/session.js'

export default {
  data() {
    return {
      pairType: 'couple',
      inviteCode: '',
      createdPair: null,
      types: [
        { value: 'couple', label: '情侣' },
        { value: 'spouse', label: '夫妻' },
        { value: 'bestfriend', label: '挚友' },
        { value: 'parent', label: '育儿夫妻' },
      ]
    }
  },
  methods: {
    async createPair() {
      try {
        const res = await api.createPair(this.pairType)
        this.createdPair = res
        await syncSession(this.$store).catch(() => null)
        uni.showToast({ title: '邀请码已生成', icon: 'success' })
      } catch (e) {
        uni.showToast({ title: e.message || '创建失败', icon: 'none' })
      }
    },
    async joinPair() {
      if (!this.inviteCode.trim()) {
        uni.showToast({ title: '请输入邀请码', icon: 'none' })
        return
      }
      try {
        await api.joinPair(this.inviteCode.trim())
        await syncSession(this.$store)
        uni.showToast({ title: '绑定成功', icon: 'success' })
        setTimeout(() => uni.reLaunch({ url: '/pages/index/index' }), 500)
      } catch (e) {
        uni.showToast({ title: e.message || '绑定失败', icon: 'none' })
      }
    }
  }
}
</script>

<style scoped>
.pair-page {
  min-height: 100vh;
  padding: 88rpx 28rpx;
  box-sizing: border-box;
  background: linear-gradient(180deg, #fff8f2 0%, #f5eee7 100%);
}

.eyebrow {
  font-size: 20rpx;
  letter-spacing: 4rpx;
  color: #a1887f;
}

.title {
  display: block;
  margin-top: 18rpx;
  font-size: 52rpx;
  line-height: 1.2;
  font-weight: 800;
  color: #2f2522;
}

.subtitle {
  display: block;
  margin-top: 14rpx;
  font-size: 24rpx;
  line-height: 1.8;
  color: #6d4c41;
}

.pair-card {
  margin-top: 26rpx;
  padding: 30rpx;
  border-radius: 36rpx;
  background: rgba(255,255,255,0.96);
  box-shadow: 0 18rpx 36rpx rgba(62, 39, 35, 0.08);
}

.section-title {
  display: block;
  font-size: 30rpx;
  font-weight: 800;
  color: #2f2522;
}

.type-row {
  display: flex;
  gap: 12rpx;
  flex-wrap: wrap;
  margin-top: 20rpx;
}

.type-chip {
  padding: 12rpx 20rpx;
  border-radius: 999rpx;
  background: #f4ece3;
  color: #8d6e63;
  font-size: 22rpx;
  font-weight: 700;
}

.type-chip.active {
  background: linear-gradient(135deg, #5d4037, #d4a373);
  color: #fff;
}

.primary-btn {
  margin-top: 22rpx;
  height: 88rpx;
  border-radius: 999rpx;
  border: none;
  background: linear-gradient(135deg, #5d4037, #d4a373);
  color: #fff;
  font-size: 28rpx;
  font-weight: 800;
}

.invite-box {
  margin-top: 20rpx;
  padding: 24rpx;
  border-radius: 26rpx;
  background: #fbf3eb;
}

.invite-label {
  font-size: 22rpx;
  color: #8d6e63;
}

.invite-code {
  display: block;
  margin-top: 10rpx;
  font-size: 48rpx;
  font-weight: 900;
  letter-spacing: 6rpx;
  color: #5d4037;
}

.invite-input {
  width: 100%;
  height: 88rpx;
  margin-top: 18rpx;
  padding: 0 24rpx;
  border-radius: 24rpx;
  background: #fbf3eb;
  color: #3e2723;
  box-sizing: border-box;
}
</style>
