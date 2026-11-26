<template>
  <nav class="tab-bar" aria-label="底部主导航">
    <router-link
      v-for="tab in tabs"
      :key="tab.to"
      :to="tab.to"
      class="tab-item"
      :class="{ active: isActive(tab.to), 'tab-item--featured': tab.featured }"
      :style="{ '--tab-accent': tab.accent, '--tab-soft': tab.soft }"
    >
      <span class="tab-icon" v-html="tab.icon" />
      <span class="tab-label">{{ tab.label }}</span>
    </router-link>
  </nav>
</template>

<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()

const tabs = [
  {
    to: '/',
    label: '首页',
    accent: '#d76848',
    soft: 'rgba(215, 104, 72, 0.13)',
    icon: '<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/><path d="M9 21v-6h6v6"/></svg>',
  },
  {
    to: '/chat',
    label: '聊一聊',
    accent: '#bd4b35',
    soft: 'rgba(189, 75, 53, 0.14)',
    icon: '<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>',
  },
  {
    to: '/checkin',
    label: '记录',
    featured: true,
    accent: '#c85a3a',
    soft: 'rgba(215, 104, 72, 0.16)',
    icon: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>',
  },
  {
    to: '/report',
    label: '简报',
    accent: '#305d68',
    soft: 'rgba(48, 93, 104, 0.13)',
    icon: '<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.85" stroke-linecap="round"><path d="M4 19h16"/><path d="M7 16v-4"/><path d="M12 16V8"/><path d="M17 16V5"/></svg>',
  },
  {
    to: '/profile',
    label: '我的',
    accent: '#aa4d33',
    soft: 'rgba(170, 77, 51, 0.13)',
    icon: '<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.85"><circle cx="12" cy="8" r="4"/><path d="M5 20a7 7 0 0 1 14 0" stroke-linecap="round"/></svg>',
  },
]

function isActive(path) {
  if (path === '/') return route.path === '/'
  if (path === '/chat') {
    return route.path.startsWith('/chat') || route.path.startsWith('/message-simulation') || route.path.startsWith('/repair-protocol')
  }
  if (path === '/checkin') {
    return route.path.startsWith('/checkin') || route.path.startsWith('/challenges')
  }
  if (path === '/report') {
    return route.path.startsWith('/report') || route.path.startsWith('/alignment') || route.path.startsWith('/timeline') || route.path.startsWith('/methodology')
  }
  if (path === '/profile') {
    return route.path.startsWith('/profile') || route.path.startsWith('/pair') || route.path.startsWith('/relationship-space') || route.path.startsWith('/privacy-security')
  }
  return route.path.startsWith(path)
}
</script>

<style scoped>
.tab-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 100;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  align-items: center;
  height: calc(var(--tabbar-height) + env(safe-area-inset-bottom, 0px));
  padding: 4px 6px calc(4px + env(safe-area-inset-bottom, 0px));
  border-top: 1px solid rgba(68, 52, 40, 0.12);
  background:
    linear-gradient(90deg, rgba(215, 104, 72, 0.06), transparent 38%, rgba(48, 93, 104, 0.06)),
    rgba(253, 249, 244, 0.96);
  backdrop-filter: blur(20px);
  box-shadow: 0 -8px 24px rgba(56, 40, 30, 0.06);
}

.tab-item {
  min-height: 52px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  border-radius: 14px;
  text-decoration: none;
  color: var(--ink-faint);
  transition: color 0.18s ease, transform 0.14s ease;
  position: relative;
  -webkit-tap-highlight-color: transparent;
}

.tab-item:active {
  transform: scale(0.95);
}

.tab-icon {
  width: 40px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  transition: background 0.18s ease, color 0.18s ease, transform 0.18s ease, box-shadow 0.18s ease;
}

.tab-label {
  font-size: 11px;
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: 0.01em;
}

.tab-item.active {
  color: var(--tab-accent);
}

.tab-item.active .tab-icon {
  background: var(--tab-soft);
  color: var(--tab-accent);
  transform: translateY(-1px);
}

.tab-item--featured .tab-icon {
  width: 46px;
  height: 32px;
  border: 1px solid rgba(215, 104, 72, 0.24);
  background: linear-gradient(135deg, rgba(255, 242, 235, 0.96), rgba(247, 224, 212, 0.9));
  color: var(--seal-deep);
}

.tab-item--featured .tab-label {
  color: var(--seal-deep);
}

.tab-item--featured.active .tab-icon {
  border-color: transparent;
  background: linear-gradient(135deg, var(--seal), var(--seal-deep));
  color: #fffdfa;
  box-shadow: 0 6px 14px rgba(170, 77, 51, 0.28);
}

.tab-item:hover {
  color: var(--tab-accent);
}
</style>
