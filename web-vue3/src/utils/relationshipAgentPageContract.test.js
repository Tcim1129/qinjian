import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const routerSource = readFileSync(fileURLToPath(new URL('../router/index.js', import.meta.url)), 'utf8')
const appSource = readFileSync(fileURLToPath(new URL('../App.vue', import.meta.url)), 'utf8')
const chatSource = readFileSync(fileURLToPath(new URL('../views/chat/ChatPage.vue', import.meta.url)), 'utf8')
const pageUrl = new URL('../views/agent/RelationshipAgentPage.vue', import.meta.url)
const legacyDemoUrl = new URL('../../public/preview-demo.html', import.meta.url)

test('relationship agent restores the approved layered demo instead of the wrong three-column mock', () => {
  assert.match(routerSource, /path:\s*['"]\/relationship-agent['"]/) 
  const pageSource = readFileSync(fileURLToPath(pageUrl), 'utf8')
  assert.match(pageSource, /关系协作智能体/)
  assert.match(pageSource, /relationship-agent-concept-v3\.png/)
  assert.match(pageSource, /class="demo-artboard"/)
  assert.match(pageSource, /class="demo-live-layer"/)
  assert.doesNotMatch(pageSource, /Agent 演示实验室/)
})

test('approved demo exposes scenario, evidence, action and conversation interactions', () => {
  const pageSource = readFileSync(fileURLToPath(pageUrl), 'utf8')
  assert.match(pageSource, /label: '今晚怎么开口？'/)
  assert.match(pageSource, /aria-label="它为什么这样判断"/)
  assert.match(pageSource, /aria-label="确认创建"/)
  assert.match(pageSource, /aria-label="换个更小的"/)
  assert.match(pageSource, /openConversation/)
  assert.match(pageSource, /toggleEvidence/)
  assert.match(pageSource, /startReasoning/)
  assert.match(pageSource, /prefers-reduced-motion/)
})

test('relationship agent owns the viewport and can prefill the embedded real chat surface', () => {
  assert.match(appSource, /route\.name\s*!==\s*['"]relationship-agent['"]/)
  assert.match(chatSource, /v-if="!embedded"/)
  assert.match(chatSource, /ref="composerInput"/)
  assert.match(chatSource, /defineExpose\(\{ applySuggestedPrompt, focusComposer(?:,\s*\w+)* \}\)/)
})

test('the unified preview entry defaults to the approved relationship agent route', () => {
  const legacySource = readFileSync(fileURLToPath(legacyDemoUrl), 'utf8')
  assert.match(legacySource, /params\.get\(['"]route['"]\)\s*\|\|\s*['"]\/relationship-agent['"]/)
  assert.doesNotMatch(legacySource, /agent-demo-reference\.png/)
})

test('interactive surfaces stay inside their matching work areas instead of floating over the whole demo', () => {
  const pageSource = readFileSync(fileURLToPath(pageUrl), 'utf8')
  assert.match(pageSource, /interaction-panel--evidence interaction-panel--docked/)
  assert.match(pageSource, /interaction-panel--action action-dock/)
  assert.match(pageSource, /conversation-dialog conversation-workspace/)
  assert.doesNotMatch(pageSource, /class="demo-live-status"/)
  assert.doesNotMatch(pageSource, /\.conversation-dialog\s*\{[^}]*position:\s*fixed/s)
  assert.doesNotMatch(pageSource, /\.conversation-dialog::before/)
})

test('only one interactive surface opens at a time and Escape closes the active surface', () => {
  const pageSource = readFileSync(fileURLToPath(pageUrl), 'utf8')
  assert.match(pageSource, /@keydown\.esc="closeOpenSurfaces"/)
  assert.match(pageSource, /function closeOpenSurfaces\(\)/)
  assert.match(pageSource, /function openConversation\(\)\s*\{\s*closeOpenSurfaces\(\)/)
  assert.match(pageSource, /function openEvidence\([^)]*\)\s*\{[\s\S]*?closeOpenSurfaces\(\)/)
  assert.match(pageSource, /function openAction\([^)]*\)\s*\{\s*closeOpenSurfaces\(\)/)
})

test('the desktop artboard is constrained by both viewport width and height', () => {
  const pageSource = readFileSync(fileURLToPath(pageUrl), 'utf8')
  assert.match(pageSource, /width:\s*min\(100vw,\s*1568px,\s*156\.331vh\)/)
  assert.match(pageSource, /place-items:\s*start center/)
})

test('embedded chat keeps the composer visible inside the central workspace', () => {
  const pageSource = readFileSync(fileURLToPath(pageUrl), 'utf8')
  assert.match(pageSource, /\.conversation-dialog :deep\(\.chat-page\)[^{]*\{[^}]*height:\s*100%[^}]*overflow:\s*hidden/s)
  assert.match(pageSource, /\.conversation-dialog :deep\(\.chat-shell\)[^{]*\{[^}]*display:\s*flex[^}]*flex-direction:\s*column[^}]*overflow:\s*hidden/s)
  assert.match(pageSource, /\.conversation-dialog :deep\(\.chat-list\)[^{]*\{[^}]*flex:\s*1 1 120px[^}]*min-height:\s*0/s)
  assert.match(pageSource, /\.conversation-dialog :deep\(\.chat-composer__input\)[^{]*\{[^}]*min-height:\s*72px/s)
})
