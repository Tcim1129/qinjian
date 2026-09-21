<template>
  <view class="container">
    <view class="header">
      <text class="title">关系管理</text>
    </view>

    <!-- 当前关系列表 -->
    <view v-if="pairs.length > 0" class="pairs-section">
      <text class="section-title">我的关系</text>
      <view 
        v-for="pair in pairs" 
        :key="pair.id"
        class="pair-card"
        @click="goToRelationshipSpace(pair.id)"
      >
        <view class="pair-info">
          <view class="avatar">
            <text class="avatar-text">{{ pair.partner_name.charAt(0) }}</text>
          </view>
          <view class="info">
            <text class="name">{{ pair.partner_name }}</text>
            <text class="type">{{ pair.relationship_type }}</text>
          </view>
        </view>
        <view class="pair-stats">
          <view class="stat">
            <text class="value">{{ pair.health_score }}</text>
            <text class="label">健康分</text>
          </view>
          <view class="stat">
            <text class="value">{{ pair.days }}</text>
            <text class="label">天</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 操作区域 -->
    <view class="actions-section">
      <view class="action-card" @click="showCreateInvite = true">
        <view class="action-content">
          <text class="action-title">创建邀请码</text>
          <text class="action-desc">生成邀请码，邀请TA加入</text>
        </view>
      </view>

      <view class="action-card" @click="showJoinInput = true">
        <view class="action-content">
          <text class="action-title">加入关系</text>
          <text class="action-desc">输入对方的邀请码</text>
        </view>
      </view>
    </view>

    <!-- 创建邀请码弹窗 -->
    <view v-if="showCreateInvite" class="modal-mask" @click="closeCreatePopup">
      <view class="popup-content" @click.stop>
        <text class="popup-title">创建邀请码</text>
        
        <view v-if="!inviteCode" class="form">
          <view class="form-item">
            <text class="label">关系类型</text>
            <picker @change="onTypeChange" :value="typeIndex" :range="relationshipTypes">
              <view class="picker">
                {{ relationshipTypes[typeIndex] }}
              </view>
            </picker>
          </view>

          <view class="form-item">
            <text class="label">对方昵称（可选）</text>
            <input v-model="partnerName" placeholder="TA的昵称" class="input" />
          </view>

          <button @click="createInviteCode" type="primary" class="btn">生成邀请码</button>
        </view>

        <view v-else class="invite-result">
          <text class="code">{{ inviteCode }}</text>
          <text class="tip">将此邀请码发送给对方</text>
          <view class="btn-group">
            <button @click="copyCode" size="mini" type="primary">复制邀请码</button>
            <button @click="closeCreatePopup" size="mini">关闭</button>
          </view>
        </view>
      </view>
    </view>

    <!-- 加入关系弹窗 -->
    <view v-if="showJoinInput" class="modal-mask" @click="closeJoinPopup">
      <view class="popup-content" @click.stop>
        <text class="popup-title">加入关系</text>
        
        <view class="form">
          <view class="form-item">
            <text class="label">邀请码</text>
            <input v-model="inputCode" placeholder="请输入6位邀请码" maxlength="6" class="input" />
          </view>

          <view class="form-item">
            <text class="label">关系类型</text>
            <picker @change="onJoinTypeChange" :value="joinTypeIndex" :range="relationshipTypes">
              <view class="picker">
                {{ relationshipTypes[joinTypeIndex] }}
              </view>
            </picker>
          </view>

          <button @click="joinRelationship" type="primary" class="btn" :disabled="inputCode.length !== 6">
            提交申请
          </button>
          <button @click="closeJoinPopup" size="mini" class="btn-cancel">取消</button>
        </view>
      </view>
    </view>

    <!-- 等待确认提示 -->
    <view v-if="pendingPairs.length > 0" class="pending-section">
      <text class="section-title">等待确认</text>
      <view 
        v-for="pending in pendingPairs" 
        :key="pending.id"
        class="pending-card"
      >
        <view class="pending-info">
          <text class="name">{{ pending.partner_name || '对方' }}</text>
          <text class="type">{{ pending.relationship_type }}</text>
        </view>
        <view class="pending-status">
          <text class="status-text">等待对方确认</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { post } from '../../utils/request'

const pairs = ref([
  {
    id: 1,
    partner_name: '小美',
    relationship_type: '情侣',
    health_score: 85,
    days: 120
  }
])

const pendingPairs = ref([])
const showCreateInvite = ref(false)
const showJoinInput = ref(false)
const inviteCode = ref('')
const inputCode = ref('')
const partnerName = ref('')
const typeIndex = ref(0)
const joinTypeIndex = ref(0)
const relationshipTypes = ['情侣', '夫妻', '挚友', '家人', '其他']

const onTypeChange = (e) => {
  typeIndex.value = e.detail.value
}

const onJoinTypeChange = (e) => {
  joinTypeIndex.value = e.detail.value
}

const createInviteCode = async () => {
  uni.showLoading({ title: '生成中...' })
  
  try {
    const data = await post('/api/v1/pairs/invite', {
      relationship_type: relationshipTypes[typeIndex.value],
      partner_name: partnerName.value
    })

    inviteCode.value = data.invite_code
    uni.hideLoading()
    
  } catch (error) {
    uni.hideLoading()
    uni.showToast({ title: '生成失败', icon: 'none' })
  }
}

const copyCode = () => {
  uni.setClipboardData({
    data: inviteCode.value,
    success: () => {
      uni.showToast({ title: '已复制', icon: 'success' })
    }
  })
}

const closeCreatePopup = () => {
  showCreateInvite.value = false
  inviteCode.value = ''
  partnerName.value = ''
  typeIndex.value = 0
}

const joinRelationship = async () => {
  if (inputCode.value.length !== 6) {
    uni.showToast({ title: '请输入6位邀请码', icon: 'none' })
    return
  }

  uni.showLoading({ title: '提交中...' })
  
  try {
    await post('/api/v1/pairs/join', {
      invite_code: inputCode.value,
      relationship_type: relationshipTypes[joinTypeIndex.value]
    })

    uni.hideLoading()
    uni.showToast({ title: '申请已提交', icon: 'success' })
    closeJoinPopup()
    loadPairs()
    
  } catch (error) {
    uni.hideLoading()
    uni.showToast({ title: '邀请码无效或已使用', icon: 'none' })
  }
}

const closeJoinPopup = () => {
  showJoinInput.value = false
  inputCode.value = ''
  joinTypeIndex.value = 0
}

const goToRelationshipSpace = (pairId) => {
  uni.navigateTo({ url: `/pages/relationship-space/relationship-space?id=${pairId}` })
}

const loadPairs = async () => {
  // TODO: 从后端加载真实数据
}

onMounted(() => {
  loadPairs()
})
</script>

<style scoped>
.container {
  min-height: 100vh;
  background: #f5f5f5;
  padding: 20rpx;
}

.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 40rpx 30rpx;
  border-radius: 20rpx;
  margin-bottom: 20rpx;
}

.title {
  font-size: 40rpx;
  font-weight: bold;
  color: #fff;
}

.section-title {
  font-size: 28rpx;
  font-weight: bold;
  color: #333;
  margin: 30rpx 20rpx 20rpx;
  display: block;
}

.pairs-section {
  margin-bottom: 20rpx;
}

.pair-card {
  background: #fff;
  border-radius: 20rpx;
  padding: 30rpx;
  margin-bottom: 15rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pair-info {
  display: flex;
  align-items: center;
  flex: 1;
}

.avatar {
  width: 100rpx;
  height: 100rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20rpx;
}

.avatar-text {
  font-size: 40rpx;
  color: #fff;
  font-weight: bold;
}

.info {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}

.name {
  font-size: 32rpx;
  font-weight: bold;
  color: #333;
}

.type {
  font-size: 24rpx;
  color: #999;
}

.pair-stats {
  display: flex;
  gap: 30rpx;
}

.stat {
  text-align: center;
}

.stat .value {
  font-size: 36rpx;
  font-weight: bold;
  color: #667eea;
  display: block;
}

.stat .label {
  font-size: 20rpx;
  color: #999;
}

.actions-section {
  display: flex;
  flex-direction: column;
  gap: 15rpx;
}

.action-card {
  background: #fff;
  border-radius: 20rpx;
  padding: 30rpx;
  display: flex;
  align-items: center;
  gap: 20rpx;
}

.action-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.action-title {
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
}

.action-desc {
  font-size: 24rpx;
  color: #999;
}

.pending-section {
  margin-top: 40rpx;
}

.pending-card {
  background: #fff;
  border-radius: 20rpx;
  padding: 30rpx;
  margin-bottom: 15rpx;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-left: 4rpx solid #ffa500;
}

.pending-info {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}

.pending-status {
  padding: 10rpx 20rpx;
  background: #fff5e6;
  border-radius: 20rpx;
}

.status-text {
  font-size: 24rpx;
  color: #ffa500;
}

/* 弹窗样式 */
.modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.popup-content {
  width: 600rpx;
  background: #fff;
  border-radius: 20rpx;
  padding: 40rpx;
}

.popup-title {
  font-size: 36rpx;
  font-weight: bold;
  color: #333;
  text-align: center;
  display: block;
  margin-bottom: 40rpx;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 30rpx;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 15rpx;
}

.label {
  font-size: 28rpx;
  color: #333;
  font-weight: bold;
}

.input {
  height: 80rpx;
  padding: 0 20rpx;
  border: 1px solid #ddd;
  border-radius: 10rpx;
  font-size: 28rpx;
}

.picker {
  height: 80rpx;
  line-height: 80rpx;
  padding: 0 20rpx;
  border: 1px solid #ddd;
  border-radius: 10rpx;
  font-size: 28rpx;
  color: #333;
}

.btn {
  border-radius: 50rpx;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.btn[disabled] {
  background: #ccc;
}

.btn-cancel {
  background: #f5f5f5;
  color: #666;
}

.invite-result {
  text-align: center;
  padding: 40rpx 0;
}

.code {
  font-size: 64rpx;
  font-weight: bold;
  color: #667eea;
  letter-spacing: 10rpx;
  display: block;
  margin-bottom: 30rpx;
}

.tip {
  font-size: 24rpx;
  color: #999;
  display: block;
  margin-bottom: 40rpx;
}

.btn-group {
  display: flex;
  gap: 20rpx;
}
</style>
