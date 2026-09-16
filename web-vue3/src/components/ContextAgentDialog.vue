<template>
  <dialog ref="dialog" class="context-agent-dialog" aria-labelledby="context-agent-title" @cancel.prevent="close" @click="onBackdropClick">
    <div class="context-agent-shell">
      <header class="context-agent-header">
        <div><p>{{ scopeLabel }} · {{ context.sourceLabel || '当前记录' }}</p><h2 id="context-agent-title">{{ context.title || '和 AI 聊聊' }}</h2></div>
        <button class="btn btn-ghost btn-sm" type="button" aria-label="关闭智能体复盘" @click="close">关闭</button>
      </header>
      <p v-if="userStore.isDemoMode" class="context-agent-notice">样例场景</p>
      <div v-if="!scopeCurrent" class="context-agent-draft">
        <p role="alert">这段关系已不可用，请重新选择记录。</p>
      </div>
      <div v-else-if="!chatOpen" class="context-agent-draft">
        <details v-if="context.summary" class="context-agent-reference">
          <summary>查看这次带入的内容</summary>
          <p>{{ context.summary }}</p>
        </details>
        <div class="context-agent-intents" aria-label="这次想怎么聊">
          <button v-for="option in intentOptions" :key="option.value" class="btn btn-sm" :class="intent === option.value ? 'btn-secondary' : 'btn-ghost'" type="button" :aria-pressed="intent === option.value" @click="selectIntent(option)">{{ option.label }}</button>
        </div>
        <label for="context-agent-prompt">想问什么</label>
        <textarea id="context-agent-prompt" v-model="draft" class="input input-textarea" rows="3" maxlength="600"></textarea>
        <div class="context-agent-footer"><button class="btn btn-primary" type="button" :disabled="!draft.trim()" @click="handoff">开始聊</button></div>
      </div>
      <section v-if="chatOpen && scopeCurrent" class="context-agent-chat" aria-label="围绕当前记录的对话">
        <ChatPage ref="chatPage" embedded isolated :context-pair-id="context.pairId || null" :scene-context="{ ...context, intent }" />
      </section>
    </div>
  </dialog>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import ChatPage from '@/views/chat/ChatPage.vue'
import { useUserStore } from '@/stores/user'
import { isContextScopeAvailable } from '@/utils/contextAgent'

const props = defineProps({ context: { type: Object, required: true } })
const emit = defineEmits(['close'])
const userStore = useUserStore()
const dialog = ref(null)
const chatPage = ref(null)
const chatOpen = ref(false)
const draft = ref(String(props.context.question || '帮我理一理这件事。').slice(0, 600))
const intent = ref(props.context.intent || 'reflect')
const intentOptions = [
  { value: 'reflect', label: '理一理', question: '帮我理一理这件事。' },
  { value: 'wording', label: '换个说法', question: '这件事我怎么开口比较自然？' },
  { value: 'plan', label: '想想下一步', question: '现在先做什么比较合适？给我一个简单的办法。' },
]
function selectIntent(option) { intent.value = option.value; draft.value = option.question }
const scopeCurrent = computed(() => isContextScopeAvailable(props.context, userStore.activePairId, userStore.pairs))
const scopeLabel = computed(() => props.context.pairId ? (userStore.pairs.find(pair => pair.id === props.context.pairId)?.partner_nickname || '所选关系') : '我的记录')
let returnFocus = null

function close() { dialog.value?.close(); emit('close') }
function onBackdropClick(event) { if (event.target === dialog.value) close() }
async function handoff() {
  if (!scopeCurrent.value || !draft.value.trim()) return
  chatOpen.value = true
  await nextTick()
  await chatPage.value?.beginScene(draft.value)
}
watch(() => [userStore.token, userStore.me?.id, userStore.activePairId, scopeCurrent.value], close, { flush: 'sync' })
onMounted(() => {
  returnFocus = document.activeElement
  dialog.value?.showModal()
  if (props.context.autoStart) handoff()
})
onBeforeUnmount(() => { dialog.value?.close(); returnFocus?.focus?.() })
</script>

<style scoped>
.context-agent-dialog { width: min(900px, calc(100vw - 32px)); max-height: calc(100dvh - 40px); padding: 0; margin: auto; color: var(--ink); background: var(--paper, #fffaf4); border: 1px solid var(--border-strong); border-radius: 20px; box-shadow: 0 24px 80px #382a1e30; }
.context-agent-dialog::backdrop { background: #2d251b70; }
.context-agent-shell { display: flex; flex-direction: column; max-height: calc(100dvh - 42px); }
.context-agent-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; padding: 22px 24px 16px; border-bottom: 1px solid var(--border); }
.context-agent-header p { margin: 0 0 4px; color: var(--ink-soft); font-size: 13px; }
.context-agent-header h2 { margin: 0; font-family: var(--font-serif); font-size: 25px; }
.context-agent-notice { padding: 9px 24px; margin: 0; background: #f3e6d4; color: #765537; font-size: 13px; }
.context-agent-draft { display: grid; gap: 12px; padding: 20px 24px 24px; overflow: auto; }
.context-agent-draft textarea { min-height: 100px; max-height: 30dvh; resize: vertical; line-height: 1.8; }
.context-agent-reference { color: var(--ink-soft); font-size: 14px; }
.context-agent-reference summary { cursor: pointer; }
.context-agent-reference p { white-space: pre-wrap; max-height: 180px; overflow: auto; line-height: 1.7; }
.context-agent-intents { display: flex; flex-wrap: wrap; gap: 8px; }
.context-agent-footer { display: flex; align-items: center; justify-content: flex-end; gap: 12px; }
.context-agent-chat { height: min(680px, calc(100dvh - 160px)); min-height: 0; overflow: hidden; padding: 12px; }
.context-agent-chat :deep(.chat-page) { height: 100%; width: 100%; padding: 0; min-height: 0; overflow: hidden; display: flex; flex-direction: column; }
.context-agent-chat :deep(.chat-shell) { flex: 1; display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
.context-agent-chat :deep(.chat-list) { flex: 1 1 120px; min-height: 0; overflow-y: auto; }
.context-agent-chat :deep(.chat-composer) { flex-shrink: 0; }
.context-agent-chat :deep(.chat-composer) { padding: 12px; }
.context-agent-chat :deep(.chat-composer__input) { min-height: 72px; height: 80px; max-height: 120px; line-height: 1.6; }
.context-agent-chat :deep(.chat-composer__actions) { flex-direction: row; flex-wrap: nowrap; gap: 6px; }
.context-agent-chat :deep(.chat-composer__actions .btn) { width: auto; flex: 1; padding: 8px 6px; gap: 5px; font-size: 12px; white-space: nowrap; }
@media (max-width: 600px) { .context-agent-header { padding: 16px; } .context-agent-draft { padding: 16px; } .context-agent-footer { align-items: stretch; flex-direction: column; } .context-agent-chat { padding: 6px; } }
</style>
