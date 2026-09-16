<template>
  <section class="relationship-management-panel">
    <div class="relationship-management-panel__header">
      <div class="relationship-management-panel__header-main">
        <p class="eyebrow">关系管理</p>
        <h3>关系管理</h3>
      </div>

      <div
        v-if="displayShortcuts.length"
        class="relationship-management-panel__tabs"
        role="tablist"
        aria-label="关系管理操作"
      >
        <button
          v-for="shortcut in displayShortcuts"
          :key="shortcut.to || shortcut.label"
          class="relationship-management-panel__tab"
          :class="{ active: shortcut.isDisplayActive }"
          type="button"
          @click="emit('shortcut', shortcut)"
        >
          <span class="relationship-management-panel__tab-step">{{ shortcut.step }}</span>
          <span class="relationship-management-panel__tab-copy">
            <strong>{{ shortcut.label }}</strong>
          </span>
        </button>
      </div>
    </div>

    <div class="relationship-management-panel__layout">
      <aside class="relationship-management-panel__sidebar">
        <div class="relationship-management-panel__section-head">
          <div>
            <h4>我的关系</h4>
          </div>
          <span class="relationship-management-panel__count">{{ pairCountBadge }}</span>
        </div>

        <div v-if="pairs.length" class="relationship-management-panel__list">
          <button
            v-for="pair in pairs"
            :key="pair.id"
            class="relationship-management-panel__item"
            :class="{ active: pair.id === currentPairId }"
            type="button"
            @click="emit('select-pair', pair)"
          >
            <div class="relationship-management-panel__item-copy">
              <strong>{{ pair.label }}</strong>
              <span>{{ pair.meta }}</span>
            </div>
            <span class="relationship-management-panel__item-mark">
              {{ pair.id === currentPairId ? '当前' : '切换' }}
            </span>
          </button>
        </div>
        <div v-else class="relationship-management-panel__empty">
          <strong>还没有建立关系</strong>
        </div>

        <div v-if="editablePair" class="relationship-management-panel__editor">
          <div class="relationship-management-panel__section-head relationship-management-panel__section-head--compact">
            <div>
              <h5>当前关系类型</h5>
            </div>
          </div>

          <div class="relationship-management-panel__types relationship-management-panel__types--sidebar">
            <button
              v-for="option in createOptions"
              :key="`edit-${option.value}`"
              class="relationship-management-panel__type"
              :class="{ active: option.value === selectedEditType }"
              type="button"
              @click="emit('select-edit-type', option.value)"
            >
              {{ option.label }}
            </button>
          </div>

          <button
            class="btn btn-secondary btn-block relationship-management-panel__action"
            type="button"
            :disabled="updatingType || selectedEditType === editablePair.type"
            @click="emit('update-type')"
          >
            {{ updatingType ? '保存中...' : '保存关系类型' }}
          </button>
        </div>
      </aside>

      <div class="relationship-management-panel__workspace">
        <div class="relationship-management-panel__workspace-head">
          <div>
            <p class="relationship-management-panel__workspace-kicker">{{ activeWorkspace.kicker }}</p>
            <h4>{{ activeWorkspace.title }}</h4>
          </div>
          <span class="relationship-management-panel__workspace-badge">{{ activeWorkspace.badge }}</span>
        </div>

        <template v-if="panelMode === 'join'">
          <label class="field relationship-management-panel__field">
            <span>对方发给你的邀请码</span>
            <input
              :value="joinCode"
              class="input relationship-management-panel__input"
              type="text"
              maxlength="10"
              autocomplete="off"
              autocapitalize="characters"
              spellcheck="false"
              placeholder="请输入 10 位邀请码，如 A3H7K8M9Q2"
              @input="emit('join-input', $event)"
            />
          </label>
          <button
            class="btn btn-primary btn-block relationship-management-panel__action relationship-management-panel__action--primary"
            type="button"
            :disabled="joining"
            @click="emit('join')"
          >
            {{ joining ? '加入中...' : '确认加入这段关系' }}
          </button>
        </template>

        <template v-else-if="panelMode === 'invite'">
          <div class="relationship-management-panel__types relationship-management-panel__types--workspace">
            <button
              v-for="option in createOptions"
              :key="option.value"
              class="relationship-management-panel__type"
              :class="{ active: option.value === selectedType }"
              type="button"
              @click="emit('select-type', option.value)"
            >
              {{ option.label }}
            </button>
          </div>
          <button
            class="btn btn-primary btn-block relationship-management-panel__action relationship-management-panel__action--primary"
            type="button"
            :disabled="creating"
            @click="emit('create')"
          >
            {{ creating ? '创建中...' : '创建邀请码' }}
          </button>
        </template>

        <template v-else-if="panelMode === 'view'">
          <div class="relationship-management-panel__overview">
            <article class="relationship-management-panel__overview-card">
              <span>当前关系</span>
              <strong>{{ currentPairLabel }}</strong>
            </article>
            <article class="relationship-management-panel__overview-card">
              <span>下一步</span>
              <strong>{{ editablePair ? '调整关系类型' : '先选一段关系' }}</strong>
            </article>
          </div>
        </template>

        <template v-else>
          <div class="relationship-management-panel__quick-actions">
            <button
              v-for="shortcut in displayShortcuts"
              :key="`quick-${shortcut.to || shortcut.label}`"
              class="relationship-management-panel__quick-card"
              type="button"
              @click="emit('shortcut', shortcut)"
            >
              <span class="relationship-management-panel__quick-step">{{ shortcut.step }}</span>
              <strong>{{ shortcut.label }}</strong>
            </button>
          </div>
        </template>
      </div>
    </div>

    <div v-if="inviteCode" class="relationship-management-panel__invite">
      <div class="relationship-management-panel__invite-copy">
        <div class="relationship-management-panel__invite-head">
          <p class="eyebrow">{{ inviteTitle || '当前邀请码' }}</p>
          <span
            class="relationship-management-panel__invite-status"
            :class="`is-${inviteMode}`"
          >
            {{ inviteModeLabel }}
          </span>
        </div>
        <strong>{{ inviteCode }}</strong>
      </div>

      <div class="relationship-management-panel__invite-actions">
        <button class="btn btn-primary" type="button" @click="emit('copy-code')">复制邀请码</button>
        <button
          v-if="inviteMode === 'pending'"
          class="btn btn-ghost"
          type="button"
          :disabled="refreshing"
          @click="emit('refresh-status')"
        >
          {{ refreshing ? '查看中...' : '查看加入状态' }}
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  shortcuts: { type: Array, default: () => [] },
  pairs: { type: Array, default: () => [] },
  currentPairId: { type: String, default: '' },
  createOptions: { type: Array, default: () => [] },
  selectedType: { type: String, default: '' },
  editablePair: { type: Object, default: null },
  selectedEditType: { type: String, default: '' },
  updatingType: { type: Boolean, default: false },
  creating: { type: Boolean, default: false },
  joinCode: { type: String, default: '' },
  joining: { type: Boolean, default: false },
  inviteCode: { type: String, default: '' },
  inviteMode: { type: String, default: 'none' },
  inviteTitle: { type: String, default: '' },
  inviteNote: { type: String, default: '' },
  refreshing: { type: Boolean, default: false },
})

const emit = defineEmits([
  'shortcut',
  'select-pair',
  'select-type',
  'select-edit-type',
  'create',
  'update-type',
  'join-input',
  'join',
  'copy-code',
  'refresh-status',
])

const displayShortcuts = computed(() => {
  const hasActiveShortcut = props.shortcuts.some((shortcut) => shortcut.isActive)

  return props.shortcuts.map((shortcut, index) => ({
    ...shortcut,
    isDisplayActive: shortcut.isActive || (!hasActiveShortcut && index === 0),
    step: `0${index + 1}`,
  }))
})

const currentPairItem = computed(() =>
  props.pairs.find((pair) => pair.id === props.currentPairId) || props.pairs[0] || null
)

const pairCountBadge = computed(() => {
  if (!props.pairs.length) return '未建立'
  return `${props.pairs.length} 段关系`
})

const panelMode = computed(() => {
  const activeShortcut = props.shortcuts.find((shortcut) => shortcut.isActive)

  switch (activeShortcut?.label) {
    case '输入邀请码':
      return 'join'
    case '发起邀请':
      return 'invite'
    case '查看关系':
      return 'view'
    default:
      return 'overview'
  }
})

const activeWorkspace = computed(() => {
  switch (panelMode.value) {
    case 'join':
      return {
        kicker: '加入关系',
        title: '输入邀请码',
        badge: '10 位邀请码',
      }
    case 'invite':
      return {
        kicker: '邀请对方',
        title: '先选关系类型，再创建邀请码',
        badge: props.inviteCode ? '已有邀请码' : '待创建',
      }
    case 'view':
      return {
        kicker: '查看与切换',
        title: '当前关系',
        badge: currentPairItem.value ? '已选中关系' : '待选择',
      }
    default:
      return {
        kicker: '常用操作',
        title: '管理关系',
        badge: props.pairs.length ? '先看左侧' : '从邀请或加入开始',
      }
  }
})

const currentPairLabel = computed(() => currentPairItem.value?.label || '还没有选中关系')

const inviteModeLabel = computed(() => {
  if (props.inviteMode === 'pending') return '待对方加入'
  if (props.inviteMode === 'active') return '关系已建立'
  return '邀请码'
})
</script>

<style scoped>
.relationship-management-panel {
  display: grid;
  gap: 20px;
  padding: 24px;
  border: 1px solid rgba(68, 52, 40, 0.08);
  border-radius: 30px;
  background:
    linear-gradient(180deg, rgba(255, 252, 247, 0.92), rgba(250, 244, 237, 0.84));
  box-shadow: 0 18px 36px rgba(91, 67, 51, 0.05);
}

.relationship-management-panel__header {
  display: grid;
  gap: 18px;
}

.relationship-management-panel__header-main {
  display: grid;
  gap: 8px;
}

.relationship-management-panel__header :deep(.eyebrow) {
  margin-bottom: 0;
  font-size: 13px;
  font-weight: 700;
}

.relationship-management-panel__header h3 {
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: clamp(30px, 2.8vw, 38px);
  line-height: 1.2;
}

.relationship-management-panel__tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.relationship-management-panel__tab {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 38px;
  padding: 6px 12px 6px 8px;
  border: 1px solid rgba(68, 52, 40, 0.1);
  border-radius: 999px;
  background: rgba(255, 253, 250, 0.68);
  text-align: left;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}

.relationship-management-panel__tab:hover {
  transform: translateY(-1px);
  border-color: rgba(189, 75, 53, 0.22);
  box-shadow: 0 12px 24px rgba(170, 77, 51, 0.06);
}

.relationship-management-panel__tab.active {
  border-color: rgba(189, 75, 53, 0.28);
  background: var(--seal-soft);
  box-shadow: 0 8px 18px rgba(170, 77, 51, 0.06);
}

.relationship-management-panel__tab-step,
.relationship-management-panel__quick-step {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border-radius: 999px;
  background: rgba(189, 75, 53, 0.1);
  color: var(--seal-deep);
  font-size: 11px;
  font-weight: 800;
  line-height: 1;
}

.relationship-management-panel__tab-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.relationship-management-panel__tab-copy strong {
  color: var(--ink);
  font-size: 14px;
  font-weight: 800;
  line-height: 1.2;
}

.relationship-management-panel__layout {
  display: grid;
  grid-template-columns: minmax(0, 380px) minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.relationship-management-panel__sidebar,
.relationship-management-panel__workspace {
  display: grid;
  align-content: start;
  gap: 16px;
  padding: 20px;
  border: 1px solid rgba(68, 52, 40, 0.08);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.64);
}

.relationship-management-panel__section-head,
.relationship-management-panel__workspace-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.relationship-management-panel__section-head h4,
.relationship-management-panel__workspace-head h4 {
  color: var(--ink);
  font-family: var(--font-serif);
  font-size: 24px;
  line-height: 1.3;
}

.relationship-management-panel__section-head h5 {
  color: var(--ink);
  font-size: 18px;
  font-weight: 800;
  line-height: 1.4;
}

.relationship-management-panel__section-head--compact {
  display: grid;
}

.relationship-management-panel__count,
.relationship-management-panel__workspace-badge,
.relationship-management-panel__invite-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
}

.relationship-management-panel__count,
.relationship-management-panel__workspace-badge {
  border: 1px solid rgba(189, 75, 53, 0.18);
  background: rgba(255, 244, 237, 0.8);
  color: var(--seal-deep);
}

.relationship-management-panel__list,
.relationship-management-panel__types {
  display: grid;
  gap: 10px;
}

.relationship-management-panel__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  min-height: 86px;
  padding: 16px;
  border: 1px solid rgba(68, 52, 40, 0.08);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.82);
  text-align: left;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}

.relationship-management-panel__item:hover {
  transform: translateY(-1px);
  border-color: rgba(189, 75, 53, 0.22);
  box-shadow: 0 10px 22px rgba(170, 77, 51, 0.05);
}

.relationship-management-panel__item.active {
  border-color: rgba(189, 75, 53, 0.28);
  background: linear-gradient(180deg, rgba(255, 248, 243, 0.98), rgba(255, 252, 248, 0.94));
  box-shadow: 0 12px 24px rgba(170, 77, 51, 0.08);
}

.relationship-management-panel__item-copy {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.relationship-management-panel__item-copy strong {
  color: var(--ink);
  font-size: 18px;
  font-weight: 800;
  line-height: 1.45;
}

.relationship-management-panel__item-copy span {
  color: var(--ink-soft);
  font-size: 14px;
  line-height: 1.75;
}

.relationship-management-panel__item-mark {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 52px;
  min-height: 32px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(68, 52, 40, 0.05);
  color: var(--ink-faint);
  font-size: 13px;
  font-weight: 700;
}

.relationship-management-panel__item.active .relationship-management-panel__item-mark {
  background: rgba(189, 75, 53, 0.1);
  color: var(--seal-deep);
}

.relationship-management-panel__editor {
  display: grid;
  gap: 14px;
  padding-top: 4px;
  border-top: 1px solid rgba(68, 52, 40, 0.08);
}

.relationship-management-panel__types--sidebar {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.relationship-management-panel__types--workspace {
  display: flex;
  flex-wrap: wrap;
}

.relationship-management-panel__type {
  min-height: 36px;
  padding: 0 13px;
  border: 1px solid rgba(68, 52, 40, 0.08);
  border-radius: 999px;
  background: rgba(255, 253, 250, 0.72);
  color: var(--ink);
  font-size: 13px;
  font-weight: 700;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease, color 0.18s ease;
}

.relationship-management-panel__type:hover {
  transform: translateY(-1px);
  border-color: rgba(189, 75, 53, 0.22);
}

.relationship-management-panel__type.active {
  border-color: rgba(189, 75, 53, 0.3);
  background: var(--seal-soft);
  color: var(--seal-deep);
}

.relationship-management-panel__workspace-kicker {
  color: var(--seal-deep);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.02em;
}

.relationship-management-panel__field {
  gap: 10px;
}

.relationship-management-panel__field :deep(span) {
  font-size: 15px;
  font-weight: 800;
  color: var(--ink);
}

.relationship-management-panel__input {
  min-height: 56px;
  padding: 0 18px;
  font-size: 18px;
  font-weight: 600;
}

.relationship-management-panel__input::placeholder {
  font-weight: 400;
}

.relationship-management-panel__action {
  min-height: 46px;
  font-size: 15px;
  font-weight: 700;
}

.relationship-management-panel__action--primary {
  min-height: 52px;
  font-size: 17px;
}

.relationship-management-panel__overview,
.relationship-management-panel__quick-actions {
  display: grid;
  gap: 10px;
}

.relationship-management-panel__overview {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.relationship-management-panel__overview-card,
.relationship-management-panel__quick-card {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 48px;
  padding: 10px 12px;
  border: 1px solid rgba(68, 52, 40, 0.08);
  border-radius: var(--radius-lg);
  background: rgba(255, 253, 250, 0.72);
  text-align: left;
}

.relationship-management-panel__overview-card {
  display: grid;
  align-items: start;
  gap: 8px;
}

.relationship-management-panel__overview-card span {
  color: var(--ink-faint);
  font-size: 13px;
  font-weight: 800;
}

.relationship-management-panel__overview-card strong {
  color: var(--ink);
  font-size: 22px;
  font-family: var(--font-serif);
  line-height: 1.35;
}

.relationship-management-panel__quick-card strong {
  color: var(--ink);
  font-size: 15px;
  line-height: 1.35;
}

.relationship-management-panel__quick-actions {
  grid-template-columns: 1fr;
}

.relationship-management-panel__quick-card {
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}

.relationship-management-panel__quick-card:hover {
  transform: translateY(-1px);
  border-color: rgba(189, 75, 53, 0.24);
  box-shadow: 0 10px 22px rgba(170, 77, 51, 0.05);
}

.relationship-management-panel__empty {
  display: grid;
  gap: 8px;
  padding: 20px;
  border: 1px dashed rgba(189, 75, 53, 0.22);
  border-radius: var(--radius-lg);
  background: rgba(255, 249, 244, 0.82);
}

.relationship-management-panel__empty strong {
  color: var(--ink);
  font-size: 18px;
  font-weight: 800;
}

.relationship-management-panel__invite {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 22px 24px;
  border: 1px solid rgba(189, 75, 53, 0.16);
  border-radius: 24px;
  background:
    linear-gradient(120deg, rgba(255, 247, 240, 0.96), rgba(255, 252, 248, 0.92));
}

.relationship-management-panel__invite-copy {
  display: grid;
  gap: 8px;
}

.relationship-management-panel__invite-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.relationship-management-panel__invite-head :deep(.eyebrow) {
  margin-bottom: 0;
  font-size: 13px;
}

.relationship-management-panel__invite strong {
  color: var(--seal-deep);
  font-family: var(--font-serif);
  font-size: clamp(34px, 4vw, 46px);
  line-height: 1;
  letter-spacing: 0.02em;
}

.relationship-management-panel__invite-status {
  border: 1px solid rgba(189, 75, 53, 0.16);
}

.relationship-management-panel__invite-status.is-pending {
  background: rgba(198, 138, 63, 0.14);
  color: var(--amber-deep);
}

.relationship-management-panel__invite-status.is-active {
  background: rgba(88, 124, 98, 0.14);
  color: var(--success);
}

.relationship-management-panel__invite-status.is-none {
  background: rgba(68, 52, 40, 0.06);
  color: var(--ink-faint);
}

.relationship-management-panel__invite-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

@media (max-width: 1080px) {
  .relationship-management-panel__tabs,
  .relationship-management-panel__quick-actions,
  .relationship-management-panel__overview {
    grid-template-columns: 1fr;
  }

  .relationship-management-panel__layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .relationship-management-panel {
    gap: 16px;
    padding: 18px;
    border-radius: 24px;
  }

  .relationship-management-panel__header h3 {
    font-size: 26px;
    line-height: 1.26;
  }

  .relationship-management-panel__sidebar,
  .relationship-management-panel__workspace,
  .relationship-management-panel__invite {
    padding: 16px;
    border-radius: 20px;
  }

  .relationship-management-panel__section-head,
  .relationship-management-panel__workspace-head,
  .relationship-management-panel__invite {
    display: grid;
  }

  .relationship-management-panel__section-head h4,
  .relationship-management-panel__workspace-head h4 {
    font-size: 22px;
  }

  .relationship-management-panel__types--sidebar,
  .relationship-management-panel__types--workspace {
    grid-template-columns: 1fr 1fr;
  }

  .relationship-management-panel__item {
    min-height: 78px;
    padding: 14px;
  }

  .relationship-management-panel__item-copy strong {
    font-size: 17px;
  }

  .relationship-management-panel__type {
    min-height: 52px;
    font-size: 16px;
  }

  .relationship-management-panel__input {
    min-height: 52px;
    font-size: 17px;
  }

  .relationship-management-panel__invite strong {
    font-size: 30px;
  }

  .relationship-management-panel__invite-actions {
    width: 100%;
  }

  .relationship-management-panel__invite-actions .btn {
    width: 100%;
  }
}

@media (max-width: 560px) {
  .relationship-management-panel__tabs,
  .relationship-management-panel__types--sidebar,
  .relationship-management-panel__types--workspace {
    grid-template-columns: 1fr;
  }
}
</style>
