import path from 'path'
import { fileURLToPath } from 'url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const configFilePath = fileURLToPath(import.meta.url)
const projectRoot = path.dirname(configFilePath)
const webRoot = path.resolve(projectRoot, 'webmain')
const outputRoot = path.resolve(projectRoot, '..', '..', 'web-vue-dist')

function rpxToCssVar() {
  return {
    postcssPlugin: 'qj-rpx-to-css-var',
    Declaration(decl) {
      if (!decl.value || !decl.value.includes('rpx')) return
      decl.value = decl.value.replace(
        /(-?\d*\.?\d+)rpx/g,
        (_, number) => `calc(var(--qj-rpx) * ${number})`
      )
    },
  }
}

rpxToCssVar.postcss = true

export default defineConfig({
  root: webRoot,
  plugins: [vue()],
  resolve: {
    alias: {
      '@app': projectRoot,
      '@web': webRoot,
    },
  },
  css: {
    postcss: {
      plugins: [rpxToCssVar()],
    },
  },
  build: {
    outDir: outputRoot,
    emptyOutDir: true,
  },
})
