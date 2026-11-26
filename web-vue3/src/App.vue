<template>
  <div id="app-shell" :class="appShellClasses">
    <div
      v-if="routeLoading"
      class="route-progress-bar"
      role="progressbar"
      aria-label="页面加载中"
    ></div>
    <AppHeader v-if="showChrome" />
    <main class="app-main">
      <router-view v-slot="{ Component, route }">
        <transition name="page" mode="out-in">
          <component v-if="Component" :is="Component" :key="route.name" class="route-view" />
          <div v-else key="route-skeleton" class="route-skeleton page-shell" role="status" aria-live="polite">
            <div class="route-skeleton__bar route-skeleton__bar--title"></div>
            <div class="route-skeleton__card"></div>
            <div class="route-skeleton__card route-skeleton__card--short"></div>
            <span class="route-skeleton__text">正在加载页面内容…</span>
          </div>
        </transition>
      </router-view>
    </main>
    <TabBar v-if="showMobileTabBar" />
    <div ref="toastRef" class="toast" :class="{ show: toast.visible }">{{ toast.message }}</div>
  </div>
</template>

<script setup>
import { provide, ref, reactive, onMounted, onBeforeUnmount, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { routeLoading, warmCoreRouteComponents } from '@/router'
import AppHeader from '@/components/AppHeader.vue'
import TabBar from '@/components/TabBar.vue'

const userStore = useUserStore()
const route = useRoute()
const isMobileViewport = ref(false)
const showChrome = computed(() => userStore.isLoggedIn && route.name !== 'auth' && route.name !== 'relationship-agent')
const showMobileTabBar = computed(() => showChrome.value && isMobileViewport.value)
const appShellClasses = computed(() => ({
  'has-tabbar': showMobileTabBar.value,
}))

const toast = reactive({ visible: false, message: '' })
let toastTimer = null
let mobileViewportQuery = null

function showToast(message, duration = 2400) {
  toast.message = message
  toast.visible = true
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.visible = false }, duration)
}

provide('showToast', showToast)

function warmLoggedInRoutes() {
  if (userStore.isLoggedIn) {
    warmCoreRouteComponents()
  }
}

function syncMobileViewport(event) {
  isMobileViewport.value = Boolean(event?.matches ?? mobileViewportQuery?.matches)
}

onMounted(() => {
  warmLoggedInRoutes()
  mobileViewportQuery = window.matchMedia('(max-width: 900px)')
  syncMobileViewport(mobileViewportQuery)
  if (typeof mobileViewportQuery.addEventListener === 'function') {
    mobileViewportQuery.addEventListener('change', syncMobileViewport)
  } else {
    mobileViewportQuery.addListener(syncMobileViewport)
  }
})

onBeforeUnmount(() => {
  if (!mobileViewportQuery) return
  if (typeof mobileViewportQuery.removeEventListener === 'function') {
    mobileViewportQuery.removeEventListener('change', syncMobileViewport)
  } else {
    mobileViewportQuery.removeListener(syncMobileViewport)
  }
})

watch(() => userStore.isLoggedIn, warmLoggedInRoutes, { flush: 'post' })
</script>

<style scoped>
#app-shell {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
}
.app-main {
  flex: 1;
  padding-bottom: 0;
  position: relative;
  overflow-x: hidden;
  background:
    linear-gradient(180deg, rgba(255, 250, 245, 0.3), rgba(255, 250, 245, 0.06)),
    radial-gradient(680px circle at 50% -10%, rgba(215, 104, 72, 0.08), transparent 58%);
}
#app-shell.has-tabbar .app-main {
  padding-bottom: calc(var(--tabbar-height) + env(safe-area-inset-bottom, 0px));
}
.route-view {
  display: block;
  min-height: calc(100vh - var(--header-height));
  min-height: calc(100dvh - var(--header-height));
}
.route-progress-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  z-index: 1200;
  background: linear-gradient(90deg, rgba(189, 75, 53, 0.2), var(--seal, #c65d40), rgba(189, 75, 53, 0.2));
  background-size: 200% 100%;
  animation: route-progress-slide 1.1s linear infinite;
}
.route-skeleton {
  display: grid;
  gap: 16px;
  padding-top: 28px;
  padding-bottom: 32px;
}
.route-skeleton__bar,
.route-skeleton__card {
  border-radius: 16px;
  background: linear-gradient(90deg, rgba(242, 232, 221, 0.65) 25%, rgba(252, 247, 241, 0.92) 50%, rgba(242, 232, 221, 0.65) 75%);
  background-size: 200% 100%;
  animation: route-progress-slide 1.4s ease infinite;
}
.route-skeleton__bar--title {
  width: 180px;
  height: 28px;
}
.route-skeleton__card {
  height: 150px;
}
.route-skeleton__card--short {
  height: 96px;
}
.route-skeleton__text {
  font-size: 13px;
  color: var(--ink-soft);
}
@keyframes route-progress-slide {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@media (min-width: 901px) {
  #app-shell.has-tabbar .app-main {
    padding-bottom: 0;
  }
}

@media (max-width: 900px) {
  #app-shell.has-tabbar .route-view {
    min-height: calc(100vh - var(--header-height) - var(--tabbar-height) - env(safe-area-inset-bottom, 0px));
    min-height: calc(100dvh - var(--header-height) - var(--tabbar-height) - env(safe-area-inset-bottom, 0px));
  }
}
</style>
