<template>
  <aside class="relationship-sidebar" :class="[themeClass, { 'is-empty': !summary }]">
    <span class="relationship-sidebar__handle" aria-hidden="true"></span>
    <div class="relationship-sidebar__header">
      <p class="eyebrow">当前关系</p>
      <h3>{{ summary?.title || '还没有选中关系' }}</h3>
      <div class="relationship-sidebar__meta">
        <span class="relationship-sidebar__type">{{ summary?.typeLabel || '未选择' }}</span>
        <span v-if="showStatusBadge" class="relationship-sidebar__status">{{ summary.statusLabel }}</span>
      </div>
    </div>

    <div v-if="summary" class="relationship-sidebar__body">
      <div v-if="showScoreCard" class="relationship-sidebar__score">
        <span>{{ summary.scoreHeading || '关系评分' }}</span>
        <strong>{{ summary.scoreLabel || summary.score }}</strong>
      </div>

      <div class="relationship-sidebar__card">
        <p class="relationship-sidebar__label">最近相处状态</p>
        <strong>{{ summary.trendLabel }}</strong>
      </div>

      <div class="relationship-sidebar__card">
        <p class="relationship-sidebar__label">最近发生了什么</p>
        <span>{{ summary.recentSummary }}</span>
      </div>

      <div class="relationship-sidebar__card">
        <p class="relationship-sidebar__label">现在最适合做什么</p>
        <span>{{ summary.nextAction }}</span>
      </div>

      <div v-if="summary.kind === 'overflow' && summary.hiddenPairs?.length" class="relationship-sidebar__card">
        <p class="relationship-sidebar__label">已收起的关系</p>
        <div class="relationship-sidebar__hidden-list">
          <button
            v-for="item in summary.hiddenPairs"
            :key="item.pairId"
            class="relationship-sidebar__hidden-item"
            type="button"
            @click="emit('select-pair', item.pairId)"
          >
            <strong>{{ item.title }}</strong>
            <span>{{ item.typeLabel }} · {{ item.trendLabel }}</span>
          </button>
        </div>
      </div>

      <div v-if="summary.kind !== 'overflow' && summary.pairId" class="relationship-sidebar__actions">
        <button
          v-if="isFocusMode"
          class="btn btn-ghost btn-block"
          type="button"
          @click="emit('clear-focus')"
        >
          回到关系列表
        </button>
        <button class="btn btn-primary btn-block" type="button" @click="emit('open-detail', summary.pairId)">
          进入专属关系页
        </button>
      </div>
    </div>

  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { normalizeRelationshipSpaceTheme } from '@/utils/relationshipTheme'

const props = defineProps({
  summary: {
    type: Object,
    default: null,
  },
  isFocusMode: {
    type: Boolean,
    default: false,
  },
  theme: {
    type: String,
    default: 'classic',
  },
})

const emit = defineEmits(['open-detail', 'select-pair', 'clear-focus'])
const themeClass = computed(() => `theme-${normalizeRelationshipSpaceTheme(props.theme)}`)
const showScoreCard = computed(() => {
  if (!props.summary) return false
  if (Number.isFinite(Number(props.summary.score))) return true
  const scoreLabel = String(props.summary.scoreLabel || '').trim()
  const statusLabel = String(props.summary.statusLabel || '').trim()
  return Boolean(scoreLabel && scoreLabel !== statusLabel)
})
const showStatusBadge = computed(() => {
  if (!props.summary?.statusLabel) return false
  if (!showScoreCard.value) return false
  const scoreLabel = String(props.summary.scoreLabel || '').trim()
  const statusLabel = String(props.summary.statusLabel || '').trim()
  return Boolean(statusLabel && statusLabel !== scoreLabel)
})
</script>

<style scoped>
.relationship-sidebar {
  position: relative;
  display: grid;
  grid-template-rows: auto auto;
  gap: 12px;
  padding: 16px;
  border: 1px solid rgba(68, 52, 40, 0.08);
  border-radius: 24px;
  background:
    linear-gradient(180deg, rgba(255, 253, 249, 0.92), rgba(248, 239, 229, 0.96));
  box-shadow: 0 12px 24px rgba(170, 77, 51, 0.06);
}

.relationship-sidebar.theme-stardust {
  background:
    linear-gradient(180deg, rgba(255, 252, 248, 0.94), rgba(245, 239, 244, 0.98));
  box-shadow: 0 12px 26px rgba(145, 123, 168, 0.08);
}

.relationship-sidebar.theme-engine {
  background:
    linear-gradient(180deg, rgba(255, 252, 248, 0.94), rgba(239, 244, 247, 0.98));
  box-shadow: 0 14px 28px rgba(111, 186, 204, 0.08);
}

.relationship-sidebar__header h3 {
  color: var(--relationship-ink-700);
  font-family: var(--font-serif);
  font-size: 22px;
  line-height: 1.35;
  overflow: hidden;
}

.relationship-sidebar__header {
  display: grid;
  gap: 8px;
}

.relationship-sidebar__handle {
  display: none;
}

.relationship-sidebar__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.relationship-sidebar__type,
.relationship-sidebar__label,
.relationship-sidebar__score span {
  color: rgba(95, 71, 60, 0.68);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.relationship-sidebar__status {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(240, 184, 116, 0.14);
  color: var(--relationship-ink-700);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.relationship-sidebar__body {
  display: grid;
  align-content: start;
  grid-auto-rows: min-content;
  gap: 10px;
}

.relationship-sidebar__score {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 12px;
  min-height: 74px;
  padding: 12px;
  border: 1px solid rgba(159, 118, 84, 0.12);
  border-radius: 18px;
  background:
    linear-gradient(135deg, rgba(240, 184, 116, 0.12), rgba(255, 255, 255, 0.52));
}

.relationship-sidebar.theme-stardust .relationship-sidebar__score {
  background:
    linear-gradient(135deg, rgba(235, 196, 243, 0.16), rgba(255, 255, 255, 0.52), rgba(203, 214, 255, 0.16));
}

.relationship-sidebar.theme-engine .relationship-sidebar__score {
  background:
    linear-gradient(135deg, rgba(255, 184, 112, 0.16), rgba(255, 255, 255, 0.54), rgba(118, 228, 255, 0.18));
}

.relationship-sidebar__score strong {
  color: var(--seal-deep);
  font-family: var(--font-serif);
  font-size: 36px;
  line-height: 1;
}

.relationship-sidebar__card {
  display: grid;
  grid-template-rows: auto auto;
  gap: 5px;
  padding: 10px 12px;
  border: 1px solid rgba(68, 52, 40, 0.08);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.44);
}

.relationship-sidebar.theme-stardust .relationship-sidebar__card,
.relationship-sidebar.theme-stardust .relationship-sidebar__hidden-item {
  background: rgba(255, 255, 255, 0.52);
  border-color: rgba(145, 123, 168, 0.1);
}

.relationship-sidebar.theme-engine .relationship-sidebar__card,
.relationship-sidebar.theme-engine .relationship-sidebar__hidden-item {
  background: rgba(255, 255, 255, 0.5);
  border-color: rgba(100, 184, 204, 0.12);
}

.relationship-sidebar__card strong,
.relationship-sidebar__card span {
  color: rgba(95, 71, 60, 0.88);
  font-size: 13px;
  line-height: 1.62;
}

.relationship-sidebar__card strong,
.relationship-sidebar__card span {
  overflow: hidden;
}

.relationship-sidebar__card strong {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.relationship-sidebar__card span {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.relationship-sidebar__hidden-list {
  display: grid;
  gap: 8px;
}

.relationship-sidebar__hidden-item {
  display: grid;
  gap: 3px;
  justify-items: start;
  padding: 10px 12px;
  border: 1px solid rgba(68, 52, 40, 0.08);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.58);
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.relationship-sidebar__hidden-item:hover {
  transform: translateY(-1px);
  border-color: rgba(189, 75, 53, 0.22);
  background: rgba(255, 251, 246, 0.92);
}

.relationship-sidebar__hidden-item strong {
  color: var(--relationship-ink-700);
  font-size: 14px;
  line-height: 1.5;
}

.relationship-sidebar__hidden-item span {
  color: rgba(95, 71, 60, 0.72);
  font-size: 12px;
  line-height: 1.5;
}

.relationship-sidebar__actions {
  display: grid;
  gap: 10px;
  margin-top: auto;
}

@media (max-width: 900px) {
  .relationship-sidebar {
    position: sticky;
    bottom: 12px;
    z-index: 3;
    padding: 14px 18px 18px;
    border-radius: 26px;
    background:
      linear-gradient(180deg, rgba(255, 253, 249, 0.96), rgba(248, 239, 229, 0.98));
    box-shadow: 0 22px 40px rgba(170, 77, 51, 0.14);
  }

  .relationship-sidebar.theme-stardust {
    background:
      linear-gradient(180deg, rgba(255, 252, 248, 0.96), rgba(245, 239, 244, 0.99));
  }

  .relationship-sidebar.theme-engine {
    background:
      linear-gradient(180deg, rgba(255, 252, 248, 0.96), rgba(239, 244, 247, 0.99));
  }

  .relationship-sidebar__handle {
    display: block;
    width: 54px;
    height: 4px;
    margin: 0 auto 2px;
    border-radius: 999px;
    background: rgba(159, 118, 84, 0.24);
  }

  .relationship-sidebar__body {
    max-height: min(52vh, 400px);
    overflow: auto;
    padding-right: 4px;
    overscroll-behavior: contain;
  }

  .relationship-sidebar__header h3,
  .relationship-sidebar__card {
    min-height: 0;
  }

  .relationship-sidebar__header h3 {
    font-size: 20px;
  }

  .relationship-sidebar__score {
    min-height: 0;
    padding: 12px 14px;
  }

  .relationship-sidebar__score strong {
    font-size: 32px;
  }

  .relationship-sidebar__card {
    grid-template-rows: auto auto auto;
    min-height: 0;
  }

  .relationship-sidebar__actions {
    position: sticky;
    bottom: -4px;
    padding-top: 6px;
    background: linear-gradient(180deg, rgba(248, 239, 229, 0), rgba(248, 239, 229, 0.96) 44%);
  }

  .relationship-sidebar.is-empty {
    bottom: 0;
  }
}

@media (max-width: 640px) {
  .relationship-sidebar {
    gap: 12px;
    padding: 14px 14px 16px;
    border-radius: 24px;
  }

  .relationship-sidebar__meta {
    gap: 6px;
  }

  .relationship-sidebar__score {
    align-items: start;
  }

  .relationship-sidebar__score strong {
    font-size: 28px;
  }

  .relationship-sidebar__body {
    max-height: min(48vh, 360px);
    gap: 10px;
  }
}
</style>
