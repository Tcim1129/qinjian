<template>
  <view class="profile-page">
    <scroll-view class="profile-scroll" scroll-y>
      <view class="profile-hero">
        <view class="avatar-badge">{{ avatarLetter }}</view>
        <view class="hero-main">
          <text class="hero-name">{{ displayName }}</text>
          <text class="hero-meta">{{ accountMeta }}</text>
          <view class="hero-tag-row">
            <text class="hero-tag">{{ pairTag }}</text>
            <text class="hero-tag soft">{{ channelTag }}</text>
          </view>
        </view>
      </view>

      <view class="panel-card pair-card">
        <view class="panel-header">
          <text class="panel-title">绑定与关系</text>
          <text class="panel-badge">{{ pairStatus }}</text>
        </view>
        <view class="detail-row">
          <text class="detail-label">当前对象</text>
          <text class="detail-value">{{ partnerName }}</text>
        </view>
        <view class="detail-row">
          <text class="detail-label">邀请码</text>
          <text class="detail-value">{{ inviteCode }}</text>
        </view>
        <view class="detail-row">
          <text class="detail-label">待处理解绑</text>
          <text class="detail-value">{{ unbindText }}</text>
        </view>
      </view>

      <view class="panel-card quick-grid-card">
        <view class="panel-header">
          <text class="panel-title">账户操作</text>
        </view>
        <view class="quick-grid">
          <view class="quick-item" @click="openEditProfile">
            <text class="quick-icon">✎</text>
            <text class="quick-name">修改名称</text>
          </view>
          <view class="quick-item" @click="openPasswordModal">
            <text class="quick-icon">◫</text>
            <text class="quick-name">修改密码</text>
          </view>
          <view class="quick-item" @click="openNicknameModal" :class="{ disabled: !pairInfo }">
            <text class="quick-icon">◎</text>
            <text class="quick-name">对象备注</text>
          </view>
          <view class="quick-item" @click="handleUnbind" :class="{ disabled: !pairInfo }">
            <text class="quick-icon">↺</text>
            <text class="quick-name">解绑管理</text>
          </view>
          <view class="quick-item" @click="goAuth">
            <text class="quick-icon">◌</text>
            <text class="quick-name">账号登录</text>
          </view>
          <view class="quick-item" @click="goPair">
            <text class="quick-icon">◎</text>
            <text class="quick-name">绑定入口</text>
          </view>
        </view>
      </view>

      <view class="panel-card setting-card">
        <view class="panel-header">
          <text class="panel-title">使用提示</text>
        </view>
        <text class="setting-copy">进入本页时会自动同步账号、关系摘要和解绑状态，不用手动刷新。</text>
        <text class="setting-copy">如果你刚完成绑定、备注或解绑，停留片刻再回到这里，就能看到最新状态。</text>
      </view>

      <view class="page-spacer"></view>
    </scroll-view>

    <view v-if="showProfileModal" class="modal-wrap">
      <view class="modal-mask" @click="showProfileModal = false"></view>
      <view class="modal-card">
        <text class="modal-title">修改名称</text>
        <input v-model="profileForm.nickname" class="modal-input" maxlength="20" placeholder="输入新的昵称" />
        <view class="modal-actions">
          <button class="modal-btn ghost" @click="showProfileModal = false">取消</button>
          <button class="modal-btn primary" @click="saveProfile">保存</button>
        </view>
      </view>
    </view>

    <view v-if="showPasswordModal" class="modal-wrap">
      <view class="modal-mask" @click="showPasswordModal = false"></view>
      <view class="modal-card">
        <text class="modal-title">修改密码</text>
        <input v-model="passwordForm.current" class="modal-input" password placeholder="当前密码" />
        <input v-model="passwordForm.next" class="modal-input" password placeholder="新密码（至少 6 位）" />
        <view class="modal-actions">
          <button class="modal-btn ghost" @click="showPasswordModal = false">取消</button>
          <button class="modal-btn primary" @click="savePassword">保存</button>
        </view>
      </view>
    </view>

    <view v-if="showNicknameModal" class="modal-wrap">
      <view class="modal-mask" @click="showNicknameModal = false"></view>
      <view class="modal-card">
        <text class="modal-title">设置伴侣备注</text>
        <input v-model="pairNickname" class="modal-input" maxlength="20" placeholder="例如 宝宝 / 搭子" />
        <view class="modal-actions">
          <button class="modal-btn ghost" @click="showNicknameModal = false">取消</button>
          <button class="modal-btn primary" @click="savePartnerNickname">保存</button>
        </view>
      </view>
    </view>

    <FloatingTabBar current="/pages/profile/index" />
  </view>
</template>

<script>
import { mapState } from 'vuex'
import api from '../../utils/api.js'
import { loadCachedSession, normalizeSummary, persistSession, syncSession } from '../../utils/session.js'
import FloatingTabBar from '../../components/FloatingTabBar.vue'

export default {
  components: { FloatingTabBar },
  data() {
    return {
      unbindStatus: null,
      showProfileModal: false,
      showPasswordModal: false,
      showNicknameModal: false,
      profileForm: { nickname: '' },
      passwordForm: { current: '', next: '' },
      pairNickname: '',
    }
  },
  computed: {
    ...mapState(['userInfo', 'pairInfo']),
    displayName() {
      return this.userInfo?.nickname || '未登录用户'
    },
    avatarLetter() {
      return this.displayName.slice(0, 1) || '亲'
    },
    accountMeta() {
      return this.userInfo?.email || this.userInfo?.phone || '账号信息待同步'
    },
    pairTag() {
      return this.pairInfo ? '已绑定关系' : '未绑定关系'
    },
    channelTag() {
      if (this.userInfo?.wechat_openid) return '微信已绑定'
      if (this.userInfo?.phone) return '手机号已绑定'
      return '邮箱账号'
    },
    pairStatus() {
      return this.pairInfo ? '稳定连接中' : '尚未建立'
    },
    partnerName() {
      return this.pairInfo?.partner_nickname || '还没有绑定对象'
    },
    inviteCode() {
      return this.pairInfo?.invite_code || '------'
    },
    unbindText() {
      if (!this.unbindStatus?.has_request) return '无'
      return this.unbindStatus.requested_by_me ? `你已发起，还剩 ${this.unbindStatus.days_remaining} 天` : '对方已发起，等待处理'
    }
  },
  onShow() {
    this.bootstrap()
  },
  methods: {
    async bootstrap() {
      const cached = loadCachedSession()
      if (cached.userInfo) this.$store.commit('SET_USER_INFO', cached.userInfo)
      if (cached.pairSummary) this.$store.commit('SET_PAIR_SUMMARY', cached.pairSummary)
      if (api.isLoggedIn()) {
        try {
          await syncSession(this.$store)
        } catch (e) {
          console.warn('profile sync failed', e)
        }
      }
      this.profileForm.nickname = this.$store.state.userInfo?.nickname || ''
      this.pairNickname = this.$store.state.pairInfo?.custom_partner_nickname || ''
      await this.loadUnbindStatus()
    },
    async loadUnbindStatus() {
      const pairId = this.$store.state.pairInfo?.id
      if (!pairId) {
        this.unbindStatus = null
        return
      }
      try {
        this.unbindStatus = await api.getUnbindStatus(pairId)
      } catch (e) {
        this.unbindStatus = null
      }
    },
    openEditProfile() {
      this.profileForm.nickname = this.displayName
      this.showProfileModal = true
    },
    openPasswordModal() {
      this.passwordForm = { current: '', next: '' }
      this.showPasswordModal = true
    },
    openNicknameModal() {
      if (!this.pairInfo) return
      this.pairNickname = this.pairInfo.custom_partner_nickname || ''
      this.showNicknameModal = true
    },
    async saveProfile() {
      try {
        const res = await api.updateMe({ nickname: this.profileForm.nickname })
        this.$store.commit('SET_USER_INFO', res)
        persistSession(res, this.$store.state.pairSummary)
        this.showProfileModal = false
        uni.showToast({ title: '名称已更新', icon: 'success' })
      } catch (e) {
        uni.showToast({ title: e.message || '保存失败', icon: 'none' })
      }
    },
    async savePassword() {
      try {
        await api.changePassword(this.passwordForm.current, this.passwordForm.next)
        this.showPasswordModal = false
        uni.showToast({ title: '密码已更新', icon: 'success' })
      } catch (e) {
        uni.showToast({ title: e.message || '修改失败', icon: 'none' })
      }
    },
    async savePartnerNickname() {
      if (!this.pairInfo?.id) return
      try {
        const res = await api.updatePartnerNickname(this.pairInfo.id, this.pairNickname)
        const nextSummary = normalizeSummary({
          ...(this.$store.state.pairSummary || {}),
          active_pair: res,
        })
        this.$store.commit('SET_PAIR_SUMMARY', nextSummary)
        persistSession(this.$store.state.userInfo, nextSummary)
        this.showNicknameModal = false
        uni.showToast({ title: '备注已更新', icon: 'success' })
      } catch (e) {
        uni.showToast({ title: e.message || '保存失败', icon: 'none' })
      }
    },
    async handleUnbind() {
      if (!this.pairInfo?.id) return
      try {
        if (this.unbindStatus?.has_request && !this.unbindStatus.requested_by_me) {
          await api.confirmUnbind(this.pairInfo.id)
          await syncSession(this.$store)
          await this.loadUnbindStatus()
          uni.showToast({ title: '已解除绑定', icon: 'success' })
          return
        }
        if (this.unbindStatus?.has_request && this.unbindStatus.requested_by_me) {
          await api.cancelUnbind(this.pairInfo.id)
          await syncSession(this.$store)
          await this.loadUnbindStatus()
          uni.showToast({ title: '已撤回解绑', icon: 'success' })
          return
        }
        await api.requestUnbind(this.pairInfo.id)
        await syncSession(this.$store)
        await this.loadUnbindStatus()
        uni.showToast({ title: '已发起解绑', icon: 'success' })
      } catch (e) {
        uni.showToast({ title: e.message || '操作失败', icon: 'none' })
      }
    },
    goAuth() {
      uni.reLaunch({ url: '/pages/auth/index' })
    },
    goPair() {
      uni.reLaunch({ url: '/pages/pair/index' })
    }
  }
}
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #fff8f2 0%, #f6efe9 100%);
}

.profile-scroll {
  height: 100vh;
  padding: 28rpx;
}

.profile-hero,
.panel-card,
.modal-card {
  background: rgba(255,255,255,0.95);
  border-radius: 36rpx;
  box-shadow: 0 18rpx 36rpx rgba(62, 39, 35, 0.08);
  border: 1rpx solid rgba(212, 163, 115, 0.12);
}

.profile-hero {
  padding: 30rpx;
  display: flex;
  gap: 20rpx;
  align-items: center;
}

.avatar-badge {
  width: 110rpx;
  height: 110rpx;
  border-radius: 55rpx;
  background: linear-gradient(135deg, #5d4037, #d4a373);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 42rpx;
  font-weight: 800;
}

.hero-main {
  flex: 1;
}

.hero-name {
  display: block;
  font-size: 40rpx;
  font-weight: 800;
  color: #2f2522;
}

.hero-meta {
  display: block;
  margin-top: 10rpx;
  font-size: 22rpx;
  color: #8d6e63;
}

.hero-tag-row {
  display: flex;
  gap: 12rpx;
  flex-wrap: wrap;
  margin-top: 14rpx;
}

.hero-tag,
.panel-badge {
  padding: 8rpx 18rpx;
  border-radius: 999rpx;
  background: #f8efe6;
  color: #8d6e63;
  font-size: 20rpx;
  font-weight: 700;
}

.hero-tag.soft {
  background: #eef5ef;
  color: #587260;
}

.panel-card {
  margin-top: 24rpx;
  padding: 28rpx;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-title {
  font-size: 30rpx;
  font-weight: 800;
  color: #2f2522;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  gap: 20rpx;
  padding: 22rpx 0;
  border-bottom: 1rpx solid #f2e9df;
}

.detail-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.detail-label {
  font-size: 22rpx;
  color: #a1887f;
}

.detail-value {
  font-size: 24rpx;
  font-weight: 700;
  color: #3e2723;
  text-align: right;
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16rpx;
  margin-top: 22rpx;
}

.quick-item {
  padding: 24rpx;
  border-radius: 26rpx;
  background: #fcf4ed;
}

.quick-item.disabled {
  opacity: 0.45;
}

.quick-icon {
  font-size: 34rpx;
}

.quick-name {
  display: block;
  margin-top: 14rpx;
  font-size: 24rpx;
  font-weight: 700;
  color: #3e2723;
}

.setting-copy {
  display: block;
  margin-top: 14rpx;
  font-size: 22rpx;
  line-height: 1.8;
  color: #6d4c41;
}

.modal-wrap {
  position: fixed;
  inset: 0;
  z-index: 1001;
}

.modal-mask {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
}

.modal-card {
  position: absolute;
  left: 28rpx;
  right: 28rpx;
  top: 50%;
  transform: translateY(-50%);
  padding: 30rpx;
}

.modal-title {
  display: block;
  font-size: 30rpx;
  font-weight: 800;
  color: #2f2522;
}

.modal-input {
  width: 100%;
  margin-top: 18rpx;
  height: 84rpx;
  padding: 0 24rpx;
  border-radius: 22rpx;
  background: #fbf3eb;
  color: #3e2723;
}

.modal-actions {
  display: flex;
  gap: 16rpx;
  margin-top: 24rpx;
}

.modal-btn {
  flex: 1;
  height: 84rpx;
  border-radius: 999rpx;
  border: none;
  font-size: 26rpx;
  font-weight: 700;
}

.modal-btn.primary {
  background: linear-gradient(135deg, #5d4037, #d4a373);
  color: #fff;
}

.modal-btn.ghost {
  background: #f4ece3;
  color: #6d4c41;
}

.page-spacer {
  height: 180rpx;
}
</style>
