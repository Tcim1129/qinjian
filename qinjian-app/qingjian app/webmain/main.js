import { createApp } from 'vue'
import './web-base.css'
import { installWebUni } from './uni-shim.js'
import { ViewElement, TextElement, ImageElement, ScrollViewElement } from './native-elements.js'
import { createQinjianStore } from './store.js'

function runCustomOption(instance, optionName) {
  const handler = instance?.$options?.[optionName]
  if (!handler) return
  if (Array.isArray(handler)) {
    handler.forEach((item) => typeof item === 'function' && item.call(instance))
    return
  }
  if (typeof handler === 'function') {
    handler.call(instance)
  }
}

async function bootstrap() {
  installWebUni()
  const { default: App } = await import('./App.vue')
  const app = createApp(App)
  app.use(createQinjianStore())
  app.component('view', ViewElement)
  app.component('text', TextElement)
  app.component('image', ImageElement)
  app.component('scroll-view', ScrollViewElement)
  app.mixin({
    mounted() {
      runCustomOption(this, 'onShow')
    },
    beforeUnmount() {
      runCustomOption(this, 'onUnload')
    },
  })
  app.mount('#app')
}

bootstrap()
