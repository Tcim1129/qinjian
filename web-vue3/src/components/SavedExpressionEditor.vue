<template>
  <section class="card expression-workspace" aria-label="我的表达">
    <div v-if="hasSuggestion || modelValue" class="expression-editor">
      <div class="expression-heading">
        <h3>最后怎么说，你来定</h3>
        <span>{{ isDemo ? '样例不保存' : '仅自己可见' }}</span>
      </div>
      <label class="field">
        <span class="sr-only">确认后的表达</span>
        <textarea ref="editor" class="input input-textarea" rows="4" maxlength="2000"
          aria-label="确认后的表达" :value="modelValue" :disabled="disabled"
          @input="$emit('update:modelValue', $event.target.value)"></textarea>
      </label>
      <div class="expression-footer">
        <span role="status">{{ isSaved ? '已保存' : `${modelValue.length}/2000` }}</span>
        <div class="expression-buttons">
          <button type="button" class="btn btn-ghost btn-sm" :disabled="disabled || !cleanText" @click="copyText">复制</button>
          <button type="button" class="btn btn-primary btn-sm" :disabled="disabled || !cleanText || isDemo || !ownerKey || state.saving || Boolean(state.deletingId) || isSaved" @click="store.save(modelValue)">
            <Loader2 v-if="state.saving" :size="15" class="expression-spinner" />
            {{ state.saving ? '保存中' : isSaved ? '已保存' : '确认保存' }}
          </button>
        </div>
      </div>
      <p v-if="state.saveError && state.failedText === cleanText" class="expression-error" role="alert">{{ state.saveError }}</p>
      <p v-if="copyNotice" class="expression-note" role="status">{{ copyNotice }}</p>
    </div>

    <details v-if="!isDemo && ownerKey" class="expression-history">
      <summary>最近保存 <span>{{ state.items.length || '' }}</span></summary>
      <p v-if="state.loading" role="status">正在加载…</p>
      <div v-else-if="state.loadError" class="expression-error" role="alert">
        {{ state.loadError }} <button type="button" class="btn btn-ghost btn-xs" @click="store.load">重试</button>
      </div>
      <p v-else-if="!state.items.length" class="expression-note">保存后，可以在这里找回。</p>
      <ul v-else class="expression-list">
        <li v-for="item in state.items" :key="item.id">
          <p>{{ item.text }}</p>
          <div class="expression-footer">
            <time :datetime="item.created_at">{{ displayDate(item.created_at) }}</time>
            <div class="expression-buttons">
              <button type="button" class="btn btn-ghost btn-xs" :disabled="disabled || state.saving" @click="reuse(item.text)">继续编辑</button>
              <button type="button" class="btn btn-ghost btn-xs" :disabled="state.saving || Boolean(state.deletingId)" @click="remove(item.id)">{{ state.deletingId === item.id ? '删除中' : '删除' }}</button>
            </div>
          </div>
        </li>
      </ul>
      <p v-if="state.items.length >= 20" class="expression-note">显示最近 20 条。</p>
      <p v-if="state.deleteError" class="expression-error" role="alert">{{ state.deleteError }}</p>
    </details>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { Loader2 } from 'lucide-vue-next'
import { api } from '@/api'
import { createSavedExpressions } from '@/utils/savedExpressions'
import { formatBeijingMonthDayTime } from '@/utils/datetime'

const props = defineProps({ modelValue: { type: String, default: '' }, hasSuggestion: Boolean,
  pairId: { type: String, default: null }, ownerKey: { type: String, default: '' }, isDemo: Boolean, disabled: Boolean })
const emit = defineEmits(['update:modelValue'])
const store = createSavedExpressions(api)
const { state } = store
const editor = ref(null)
const copyNotice = ref('')
let scopeRevision = 0
const cleanText = computed(() => props.modelValue.trim())
const isSaved = computed(() => Boolean(state.savedId) && cleanText.value === state.savedText)

watch(() => [props.ownerKey, props.pairId, props.isDemo], () => {
  scopeRevision++
  copyNotice.value = ''
  store.setScope({ key: props.ownerKey, pairId: props.pairId, enabled: Boolean(props.ownerKey) && !props.isDemo })
  void store.load()
}, { immediate: true, flush: 'sync' })
watch(() => props.modelValue, () => { copyNotice.value = '' })
onBeforeUnmount(() => { scopeRevision++; store.setScope({ enabled: false }) })

function displayDate(value) {
  return formatBeijingMonthDayTime(value)
}
async function reuse(text) {
  emit('update:modelValue', text)
  await nextTick()
  editor.value?.focus()
  editor.value?.scrollIntoView({ block: 'center', behavior: 'auto' })
}
async function copyText() {
  const revision = scopeRevision, text = cleanText.value
  try {
    if (!navigator.clipboard?.writeText) throw new Error('unavailable')
    await navigator.clipboard.writeText(text)
    if (revision === scopeRevision && text === cleanText.value) copyNotice.value = '已复制，发送前再看一眼。'
  } catch {
    if (revision !== scopeRevision || text !== cleanText.value) return
    editor.value?.focus()
    editor.value?.select()
    copyNotice.value = '文字已选中，请复制。'
  }
}
function remove(id) {
  if (window.confirm('删除这条保存的表达？')) void store.remove(id)
}
</script>

<style scoped>
.expression-workspace { display: grid; gap: 18px; min-width: 0; }
.expression-editor { display: grid; gap: 12px; }
.expression-heading, .expression-footer { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
.expression-heading h3 { margin: 0; font-size: 18px; }
.expression-heading span, .expression-footer > span, time, .expression-note { color: var(--text-secondary, #65716b); font-size: 13px; }
.expression-editor textarea { width: 100%; min-height: 130px; line-height: 1.8; box-sizing: border-box; resize: vertical; }
.expression-buttons { display: flex; gap: 8px; flex-wrap: wrap; }
.expression-error { margin: 0; color: var(--color-danger, #a24631); font-size: 14px; overflow-wrap: anywhere; }
.expression-note { margin: 0; }
.expression-history summary { cursor: pointer; font-weight: 600; padding: 8px 0; }
.expression-history summary span { margin-left: 8px; font-weight: 400; }
.expression-list { list-style: none; margin: 0; padding: 0; }
.expression-list li { padding: 16px 0; border-bottom: 1px solid var(--border-color, #e5dfd5); }
.expression-list li p { margin: 0 0 8px; white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.8; }
.expression-spinner { animation: expression-spin 1s linear infinite; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
@keyframes expression-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .expression-spinner { animation: none; } }
@media (max-width: 480px) { .expression-heading h3 { font-size: 17px; } .expression-footer { align-items: flex-start; } }
</style>
