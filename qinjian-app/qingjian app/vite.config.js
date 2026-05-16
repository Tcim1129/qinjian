import path from 'path'
import { fileURLToPath } from 'url'
import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'

const configFilePath = fileURLToPath(import.meta.url)
const projectRoot = path.dirname(configFilePath)
const inputDir = path.resolve(projectRoot)

process.env.VITE_ROOT_DIR = process.env.VITE_ROOT_DIR || inputDir
process.env.UNI_INPUT_DIR = process.env.UNI_INPUT_DIR || inputDir

export default defineConfig({
  root: inputDir,
  plugins: [
    uni(),
  ],
  resolve: {
    alias: {
      '@': inputDir,
    },
  },
})
