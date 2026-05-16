<template>
  <view class="profile-page">
    <scroll-view class="profile-scroll" scroll-y>
      <view class="hero-shell">
        <view class="brand-chip">
          <image class="brand-chip__logo" src="../../static/brand-logo.jpg" mode="aspectFit"></image>
          <view class="brand-chip__copy">
            <text class="brand-chip__eyebrow">QINJIAN APP</text>
            <text class="brand-chip__name">我的关系空间</text>
          </view>
        </view>

        <view class="hero-main">
          <view class="avatar-orbit">
            <view class="avatar-dot avatar-dot--top"></view>
            <view class="avatar-dot avatar-dot--bottom"></view>
            <view class="avatar-core">{{ avatarLetter }}</view>
          </view>
        <view class="hero-copy">
          <text class="hero-name">{{ displayName }}</text>
          <text class="hero-meta">{{ accountMeta }}</text>
          <view class="section-rule"></view>
          <view class="hero-chip-row">
            <text class="hero-chip" :class="pairInfo ? 'hero-chip--good' : 'hero-chip--warm'">{{ pairTag }}</text>
            <text class="hero-chip hero-chip--soft">{{ channelTag }}</text>
            </view>
          </view>
        </view>
      </view>

      <view class="cockpit-grid">
        <view class="cockpit-card">
          <text class="section-eyebrow">RELATIONSHIP</text>
          <text class="card-title">当前连接状态</text>
          <text class="cockpit-value">{{ pairStatus }}</text>
          <text class="panel-copy">{{ pairInfo ? ('当前对象：' + partnerName) : '还没有双人关系也没关系，系统会先按单人轨迹持续判断。' }}</text>
          <view class="detail-list">
            <view class="detail-row">
              <text class="detail-label">邀请码</text>
              <text class="detail-value">{{ inviteCode }}</text>
            </view>
            <view class="detail-row">
              <text class="detail-label">解绑状态</text>
              <text class="detail-value">{{ unbindText }}</text>
            </view>
          </view>
        </view>

        <view class="cockpit-card" v-if="assessmentLatest">
          <text class="section-eyebrow">ASSESSMENT</text>
          <text class="card-title">最近一次正式体检</text>
          <view class="score-line">
            <text class="score-value">{{ assessmentLatest.totalScore }}</text>
            <text class="score-unit">/ 100</text>
          </view>
          <text class="panel-copy">{{ assessmentLatest.levelLabel }}</text>
          <text class="support-copy">{{ assessmentLatest.changeSummary }}</text>
        </view>
      </view>

      <view class="cockpit-card" v-if="safetyStatus">
        <text class="section-eyebrow">TRUST & BOUNDARY</text>
        <text class="card-title">系统为什么现在这样提醒你</text>
        <view class="risk-row">
          <text class="risk-pill">{{ safetyStatus.risk_level || 'low' }}</text>
          <text class="risk-copy">{{ safetyStatus.why_now }}</text>
        </view>
        <view v-if="safetyStatus.evidence_summary && safetyStatus.evidence_summary.length" class="evidence-chip-list">
          <text v-for="item in safetyStatus.evidence_summary" :key="item" class="evidence-chip">{{ item }}</text>
        </view>
        <text class="panel-copy">{{ safetyStatus.limitation_note }}</text>
        <view v-if="safetyStatus.handoff_recommendation" class="handoff-box">{{ safetyStatus.handoff_recommendation }}</view>
      </view>

      <view class="cockpit-card" v-if="policyAudit">
        <text class="section-eyebrow">POLICY</text>
        <text class="card-title">当前策略与下一步观察点</text>
        <view class="policy-grid">
          <view class="mini-card">
            <text class="mini-label">当前策略</text>
            <text class="mini-value mini-value--title">{{ policyAudit.current_policy ? policyAudit.current_policy.title : '继续观察' }}</text>
          </view>
          <view class="mini-card">
            <text class="mini-label">推荐下一步</text>
            <text class="mini-value mini-value--title">{{ policyAudit.recommended_policy ? policyAudit.recommended_policy.title : '先保持当前版本' }}</text>
          </view>
        </view>
        <text class="panel-copy">{{ policyAudit.selection_reason || policyAudit.schedule_summary || '系统会把体检、打卡和任务反馈合并后，再决定要不要切策略。' }}</text>
      </view>

      <view class="cockpit-card" v-if="privacyStatus">
        <text class="section-eyebrow">PRIVACY</text>
        <text class="card-title">隐私保护与删除治理</text>
        <view class="evidence-chip-list">
          <text v-for="item in privacyStatus.protectionTags" :key="item" class="evidence-chip">{{ item }}</text>
        </view>
        <view class="policy-grid">
          <view class="mini-card">
            <text class="mini-label">审计保留</text>
            <text class="mini-value mini-value--title">{{ privacyStatus.retentionText }}</text>
          </view>
          <view class="mini-card">
            <text class="mini-label">票据有效期</text>
            <text class="mini-value mini-value--title">{{ privacyStatus.ticketText }}</text>
          </view>
        </view>
        <text class="panel-copy">当前删除状态：{{ privacyStatus.deleteText }}</text>
        <view class="action-grid">
          <view class="action-chip" :class="{ disabled: false }" @click="privacyStatus.canCancel ? cancelPrivacyDeletion() : requestPrivacyDeletion()">
            <text class="action-name">{{ privacyStatus.canCancel ? '撤回删除请求' : '发起删除请求' }}</text>
            <text class="action-copy">{{ privacyStatus.canCancel ? '宽限期内可以撤回' : '7 天宽限期后执行私有数据删除' }}</text>
          </view>
        </view>
      </view>

      <view class="cockpit-card">
        <text class="section-eyebrow">ACTION</text>
        <text class="card-title">接下来可以做什么</text>
        <view class="action-grid">
          <view class="action-chip" @click="openEditProfile">
            <text class="action-name">修改名称</text>
            <text class="action-copy">更新公开昵称</text>
          </view>
          <view class="action-chip" @click="openPasswordModal">
            <text class="action-name">修改密码</text>
            <text class="action-copy">账号安全管理</text>
          </view>
          <view class="action-chip" :class="{ disabled: !pairInfo }" @click="openNicknameModal">
            <text class="action-name">对象备注</text>
            <text class="action-copy">为对方加一个亲密称呼</text>
          </view>
          <view class="action-chip" :class="{ disabled: !pairInfo }" @click="handleUnbind">
            <text class="action-name">解绑管理</text>
            <text class="action-copy">处理解绑申请与撤回</text>
          </view>
          <view class="action-chip" @click="openReport">
            <text class="action-name">关系简报</text>
            <text class="action-copy">查看最新判断与边界</text>
          </view>
          <view class="action-chip" @click="openAssessment">
            <text class="action-name">关系体检</text>
            <text class="action-copy">正式提交本周评估</text>
          </view>
          <view class="action-chip" @click="openPair">
            <text class="action-name">绑定入口</text>
            <text class="action-copy">创建或加入双人空间</text>
          </view>
          <view class="action-chip" @click="logout">
            <text class="action-name">退出登录</text>
            <text class="action-copy">返回账号入口</text>
          </view>
        </view>
      </view>

      <view class="cockpit-card support-card">
        <text class="section-eyebrow">SUPPORT</text>
        <text class="card-title">使用提示</text>
        <text class="panel-copy">每次回到这个页面，系统都会重拉账号、关系摘要、安全边界和体检摘要，所以它更像一张实时关系工作台，而不只是设置页。</text>
        <text class="panel-copy">如果你刚提交过体检、完成了任务或触发了新的简报，稍等一会再回来，这里的判断会更接近最新状态。</text>
      </view>

      <view class="copyright-card">
        <text class="section-eyebrow">COPYRIGHT</text>
        <text class="panel-copy">这页现在展示的是你的个人关系空间，不只是账号操作，还包括系统对当前关系节奏、安全边界和策略阶段的解释。</text>
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
        <input v-model="passwordForm.next" class="modal-input" password placeholder="新密码（至少 8 位）" />
        <view class="modal-actions">
          <button class="modal-btn ghost" @click="showPasswordModal = false">取消</button>
          <button class="modal-btn primary" @click="savePassword">保存</button>
        </view>
      </view>
    </view>

    <view v-if="showNicknameModal" class="modal-wrap">
      <view class="modal-mask" @click="showNicknameModal = false"></view>
      <view class="modal-card">
        <text class="modal-title">设置对象备注</text>
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

function normalizeAssessment(payload) {
  if (!payload) return null
  const score = Number(payload.total_score || 0)
  let levelLabel = '先记录这一周的真实状态'

  if (score >= 80) {
    levelLabel = '这周整体更稳定'
  } else if (score >= 60) {
    levelLabel = '还在可修复区间'
  } else {
    levelLabel = '更需要减压和修复'
  }

  return {
    totalScore: score,
    levelLabel,
    changeSummary: payload.change_summary || '系统会把正式体检继续回流到后续策略。'
  }
}

function normalizePrivacyStatus(payload) {
  if (!payload) return null
  const latest = payload.latest_delete_request || null
  return {
    protectionTags: [
      payload.sandbox_enabled ? '隐私沙盒已开启' : '隐私沙盒未开启',
      payload.log_masking ? '日志脱敏' : '日志明文',
      payload.llm_redaction ? '模型输入脱敏' : '模型输入不脱敏',
      payload.private_upload_access ? '私有上传访问' : '公开上传兼容',
    ],
    retentionText: `${payload.audit_retention_days || '--'} 天`,
    ticketText: `${payload.upload_ticket_ttl_minutes || '--'} 分钟`,
    deleteText: latest
      ? `${latest.status}${latest.scheduled_for ? ` · ${String(latest.scheduled_for).slice(0, 10)}` : ''}`
      : '当前没有删除请求',
    canCancel: !!(latest && latest.can_cancel),
  }
}

export default {
  components: { FloatingTabBar },
  data() {
    return {
      unbindStatus: null,
      safetyStatus: null,
      assessmentLatest: null,
      privacyStatus: null,
      policyAudit: null,
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
      return this.pairInfo ? '已绑定关系' : '单人模式'
    },
    channelTag() {
      if (this.userInfo?.wechat_bound) return '微信已绑定'
      if (this.userInfo?.phone) return '手机号已绑定'
      return '邮箱账号'
    },
    pairStatus() {
      return this.pairInfo ? '稳定连接中' : '尚未建立双人关系'
    },
    partnerName() {
      return this.pairInfo?.partner_nickname || this.pairInfo?.partner_name || '还没有绑定对象'
    },
    inviteCode() {
      return this.pairInfo?.invite_code || '------'
    },
    unbindText() {
      if (!this.unbindStatus?.has_request) return '暂无申请'
      if (this.unbindStatus.requested_by_me) {
        return `你已发起，还剩 ${this.unbindStatus.days_remaining} 天`
      }
      return '对方已发起，等待你处理'
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
      await Promise.all([this.loadUnbindStatus(), this.loadInsights()])
    },
    async loadInsights() {
      const pairId = this.$store.state.pairInfo?.id || null
      try {
        const [safetyStatus, assessmentLatest, privacyStatus, policyAudit] = await Promise.all([
          api.getSafetyStatus(pairId).catch(() => null),
          api.getWeeklyAssessmentLatest(pairId).catch(() => null),
          api.getPrivacyStatus().catch(() => null),
          api.getPolicyDecisionAudit(pairId).catch(() => null)
        ])
        this.safetyStatus = safetyStatus
        this.assessmentLatest = normalizeAssessment(assessmentLatest)
        this.privacyStatus = normalizePrivacyStatus(privacyStatus)
        this.policyAudit = policyAudit
      } catch (e) {
        console.warn('profile insights failed', e)
      }
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
      if (!this.pairInfo) {
        uni.showToast({ title: '先绑定关系，再设置对象备注', icon: 'none' })
        uni.reLaunch({ url: '/pages/pair/index' })
        return
      }
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
      if (!this.pairInfo?.id) {
        uni.showToast({ title: '先创建或加入关系空间', icon: 'none' })
        uni.reLaunch({ url: '/pages/pair/index' })
        return
      }
      try {
        if (this.unbindStatus?.has_request && !this.unbindStatus.requested_by_me) {
          await api.confirmUnbind(this.pairInfo.id)
          await syncSession(this.$store)
          await Promise.all([this.loadUnbindStatus(), this.loadInsights()])
          uni.showToast({ title: '已解除绑定', icon: 'success' })
          return
        }
        if (this.unbindStatus?.has_request && this.unbindStatus.requested_by_me) {
          await api.cancelUnbind(this.pairInfo.id)
          await syncSession(this.$store)
          await Promise.all([this.loadUnbindStatus(), this.loadInsights()])
          uni.showToast({ title: '已撤回解绑', icon: 'success' })
          return
        }
        await api.requestUnbind(this.pairInfo.id)
        await syncSession(this.$store)
        await Promise.all([this.loadUnbindStatus(), this.loadInsights()])
        uni.showToast({ title: '已发起解绑', icon: 'success' })
      } catch (e) {
        uni.showToast({ title: e.message || '操作失败', icon: 'none' })
      }
    },
    openReport() {
      uni.reLaunch({ url: '/pages/report/index' })
    },
    openAssessment() {
      uni.navigateTo({ url: '/pages/discover/health-test/index' })
    },
    openPair() {
      uni.reLaunch({ url: '/pages/pair/index' })
    },
    async requestPrivacyDeletion() {
      const confirmed = await new Promise((resolve) => {
        uni.showModal({
          title: '发起删除请求',
          content: '系统会进入 7 天宽限期，到期后删除你的私有数据；共享关系数据会转入人工复核。确认继续吗？',
          success: resolve,
          fail: () => resolve({ confirm: false }),
        })
      })
      if (!confirmed?.confirm) return
      try {
        await api.createPrivacyDeleteRequest()
        uni.showToast({ title: '删除请求已创建', icon: 'success' })
        await this.loadInsights()
      } catch (e) {
        uni.showToast({ title: e.message || '创建失败', icon: 'none' })
      }
    },
    async cancelPrivacyDeletion() {
      const confirmed = await new Promise((resolve) => {
        uni.showModal({
          title: '撤回删除请求',
          content: '确认撤回当前删除请求吗？',
          success: resolve,
          fail: () => resolve({ confirm: false }),
        })
      })
      if (!confirmed?.confirm) return
      try {
        await api.cancelPrivacyDeleteRequest()
        uni.showToast({ title: '已撤回删除请求', icon: 'success' })
        await this.loadInsights()
      } catch (e) {
        uni.showToast({ title: e.message || '撤回失败', icon: 'none' })
      }
    },
    logout() {
      api.clearToken()
      persistSession(null, null)
      this.$store.commit('SET_USER_INFO', null)
      this.$store.commit('SET_PAIR_SUMMARY', null)
      uni.reLaunch({ url: '/pages/auth/index' })
    }
  }
}
</script>

<style scoped>
.profile-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: linear-gradient(180deg, #fff8f2 0%, #f5eee8 100%);
}

.profile-scroll {
  flex: 1;
  min-height: 0;
  padding: 28rpx 28rpx calc(28rpx + env(safe-area-inset-bottom));
  box-sizing: border-box;
}

.hero-shell,
.cockpit-card,
.copyright-card,
.modal-card {
  border-radius: 36rpx;
  background: rgba(255, 255, 255, 0.96);
  border: 1rpx solid rgba(212, 163, 115, 0.12);
  box-shadow: 0 18rpx 36rpx rgba(62, 39, 35, 0.08);
}

.hero-shell {
  padding: 32rpx;
  background: linear-gradient(145deg, rgba(255, 248, 241, 0.98), rgba(239, 247, 252, 0.92));
  position: relative;
  overflow: hidden;
  animation: profileHeroFloat 7.8s ease-in-out infinite;
}

.hero-shell::after {
  content: "";
  position: absolute;
  right: -70rpx;
  top: -90rpx;
  width: 220rpx;
  height: 220rpx;
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
.section-eyebrow,
.detail-label,
.mini-label {
  font-size: 18rpx;
  letter-spacing: 4rpx;
  text-transform: uppercase;
  color: #a1887f;
}

.brand-chip__name,
.card-title,
.modal-title {
  font-size: 30rpx;
  font-weight: 800;
  color: #2f2522;
  font-family: "Times New Roman", "Georgia", "Songti SC", serif;
  letter-spacing: 0.4rpx;
}

.hero-main {
  display: flex;
  gap: 24rpx;
  align-items: center;
  margin-top: 24rpx;
}

.avatar-orbit {
  position: relative;
  width: 150rpx;
  height: 150rpx;
  border-radius: 50%;
  background: radial-gradient(circle at 50% 50%, rgba(255, 255, 255, 0.96), rgba(245, 232, 221, 0.9));
  border: 1rpx solid rgba(212, 163, 115, 0.16);
}

.avatar-core {
  position: absolute;
  inset: 18rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #5d4037, #d4a373);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 58rpx;
  font-weight: 900;
  box-shadow: 0 16rpx 34rpx rgba(93, 64, 55, 0.18);
}

.avatar-dot {
  position: absolute;
  width: 22rpx;
  height: 22rpx;
  border-radius: 50%;
  background: #d4a373;
}

.avatar-dot--top {
  top: 18rpx;
  right: 14rpx;
}

.avatar-dot--bottom {
  bottom: 18rpx;
  left: 8rpx;
  background: #8d6e63;
}

.hero-copy {
  flex: 1;
}

.hero-name {
  display: block;
  font-size: 40rpx;
  font-weight: 800;
  color: #2f2522;
  font-family: "Times New Roman", "Georgia", "Songti SC", serif;
  letter-spacing: 0.5rpx;
}

.section-rule {
  width: 96rpx;
  height: 6rpx;
  margin-top: 16rpx;
  border-radius: 999rpx;
  background: linear-gradient(90deg, rgba(212, 163, 115, 0.92), rgba(93, 64, 55, 0.88));
}

.hero-meta,
.panel-copy,
.support-copy,
.risk-copy,
.action-copy {
  display: block;
  margin-top: 12rpx;
  font-size: 22rpx;
  line-height: 1.8;
  color: #6d4c41;
}

.hero-chip-row {
  display: flex;
  gap: 12rpx;
  flex-wrap: wrap;
  margin-top: 18rpx;
}

.hero-chip {
  padding: 8rpx 18rpx;
  border-radius: 999rpx;
  font-size: 20rpx;
  font-weight: 700;
}

.hero-chip--good {
  background: rgba(232, 245, 233, 0.95);
  color: #2e7d32;
}

.hero-chip--warm {
  background: rgba(255, 243, 224, 0.95);
  color: #ef6c00;
}

.hero-chip--soft {
  background: rgba(248, 241, 235, 0.95);
  color: #8d6e63;
}

.cockpit-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16rpx;
  margin-top: 24rpx;
}

.cockpit-card,
.copyright-card {
  margin-top: 24rpx;
  padding: 28rpx;
}

.cockpit-value {
  display: block;
  margin-top: 16rpx;
  font-size: 34rpx;
  font-weight: 800;
  color: #3e2723;
}

.detail-list {
  margin-top: 18rpx;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  gap: 18rpx;
  padding: 16rpx 0;
  border-bottom: 1rpx solid #f2e9df;
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-value {
  font-size: 22rpx;
  font-weight: 700;
  color: #3e2723;
  text-align: right;
}

.score-line {
  display: flex;
  align-items: flex-end;
  gap: 10rpx;
  margin-top: 18rpx;
}

.score-value {
  font-size: 56rpx;
  line-height: 1;
  font-weight: 900;
  color: #5d4037;
}

.score-unit {
  padding-bottom: 8rpx;
  font-size: 22rpx;
  color: #8d6e63;
}

.risk-row {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
  margin-top: 18rpx;
}

.risk-pill {
  align-self: flex-start;
  padding: 8rpx 18rpx;
  border-radius: 999rpx;
  background: rgba(255, 244, 231, 0.94);
  color: #8d5b3e;
  font-size: 20rpx;
  font-weight: 700;
  text-transform: uppercase;
}

.evidence-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-top: 18rpx;
}

.evidence-chip,
.mini-card,
.action-chip {
  border-radius: 24rpx;
}

.evidence-chip {
  padding: 14rpx 18rpx;
  background: #fcf4ed;
  color: #6d4c41;
  font-size: 22rpx;
  line-height: 1.6;
}

.handoff-box {
  margin-top: 18rpx;
  padding: 22rpx;
  border-radius: 24rpx;
  background: rgba(255, 236, 229, 0.92);
  color: #8a3b2f;
  font-size: 22rpx;
  line-height: 1.8;
}

.policy-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16rpx;
  margin-top: 20rpx;
}

.mini-card,
.action-chip {
  padding: 22rpx;
  background: #fcf4ed;
  border: 1rpx solid rgba(212, 163, 115, 0.12);
  box-shadow: 0 12rpx 24rpx rgba(93, 64, 55, 0.06);
}

.mini-value {
  display: block;
  margin-top: 12rpx;
  font-size: 34rpx;
  font-weight: 900;
  color: #3e2723;
}

.mini-value--title {
  font-size: 26rpx;
  line-height: 1.45;
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16rpx;
  margin-top: 22rpx;
}

.action-chip.disabled {
  opacity: 0.45;
}

.action-name {
  display: block;
  font-size: 26rpx;
  font-weight: 800;
  color: #3e2723;
}

.action-chip {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 156rpx;
  background: linear-gradient(145deg, rgba(255, 249, 242, 0.98), rgba(248, 241, 234, 0.96));
  transition: transform 0.22s ease, box-shadow 0.22s ease;
}

.action-chip:active {
  transform: scale(0.985) translateY(2rpx);
  box-shadow: 0 6rpx 14rpx rgba(93, 64, 55, 0.08);
}

.support-card {
  margin-top: 24rpx;
}

@keyframes profileHeroFloat {
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
  height: 120rpx;
}

@media (max-width: 390px) {
  .hero-main {
    flex-direction: column;
    align-items: flex-start;
  }

  .cockpit-grid,
  .policy-grid,
  .action-grid {
    grid-template-columns: 1fr;
  }
}
</style>
