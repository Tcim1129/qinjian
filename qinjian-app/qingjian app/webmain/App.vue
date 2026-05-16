<template>
  <div class="web-page-host">
    <component :is="currentView" :key="currentPath" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { currentRoutePath } from './route-state.js'
import AuthPage from '@app/pages/auth/index.vue'
import CheckinPage from '@app/pages/checkin/index.vue'
import DiscoverPage from '@app/pages/discover/index.vue'
import HealthTestPage from '@app/pages/discover/health-test/index.vue'
import HomePage from '@app/pages/index/index.vue'
import PairPage from '@app/pages/pair/index.vue'
import ProfilePage from '@app/pages/profile/index.vue'
import ReportPage from '@app/pages/report/index.vue'

const pageMap = {
  '/pages/auth/index': AuthPage,
  '/pages/checkin/index': CheckinPage,
  '/pages/discover/index': DiscoverPage,
  '/pages/discover/health-test/index': HealthTestPage,
  '/pages/index/index': HomePage,
  '/pages/pair/index': PairPage,
  '/pages/profile/index': ProfilePage,
  '/pages/report/index': ReportPage,
}

const currentPath = computed(() => currentRoutePath.value)
const currentView = computed(() => pageMap[currentPath.value] || HomePage)
</script>
