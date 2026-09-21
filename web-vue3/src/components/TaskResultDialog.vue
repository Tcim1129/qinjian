<template>
  <dialog ref="dialog" class="task-result-dialog" aria-labelledby="task-result-title" @cancel.prevent="close" @click="backdrop">
    <form @submit.prevent="save(false)">
      <div class="task-result-head"><h3 id="task-result-title">这件事做得怎么样？</h3><button class="btn btn-ghost btn-sm" type="button" :disabled="saving" @click="close">关闭</button></div>
      <p>{{ task.title }}</p>
      <div class="task-result-options" role="group" aria-label="完成状态">
        <button v-for="choice in choices" :key="choice.value" type="button" class="btn" :class="status === choice.value ? 'btn-secondary' : 'btn-ghost'" :aria-pressed="status === choice.value" :disabled="saving" @click="status = choice.value">{{ choice.label }}</button>
      </div>
      <fieldset v-if="status === 'completed'" class="task-result-effect" :disabled="saving">
        <legend>感觉怎么样（选填）</legend>
        <div class="task-result-options" role="group" aria-label="实际感受">
          <button v-for="choice in outcomeChoices" :key="choice.value" type="button" class="btn btn-sm" :class="outcome === choice.value ? 'btn-secondary' : 'btn-ghost'" :aria-pressed="outcome === choice.value" @click="outcome = outcome === choice.value ? null : choice.value">{{ choice.label }}</button>
        </div>
      </fieldset>
      <label class="field"><span>{{ status === 'completed' ? '后来怎么样（选填）' : '想补充什么（选填）' }}</span><textarea v-model="note" class="input input-textarea" rows="3" maxlength="200" :disabled="saving" :placeholder="status === 'completed' ? '比如：聊了一会儿，心里轻松了一点。' : '比如：下班太晚了，想改天再聊。'" /></label>
      <p v-if="error" role="alert">{{ error }}</p>
      <div class="task-result-actions">
        <button class="btn btn-primary" :disabled="saving" type="submit">{{ saving ? '保存中…' : '保存结果' }}</button>
        <button class="btn btn-secondary" :disabled="saving" type="button" @click="save(true)">保存并接着聊</button>
      </div>
    </form>
  </dialog>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useUserStore } from '@/stores/user'
import { api } from '@/api'
import { demoScheduleCache, feedbackOutcomes, buildTaskResultFeedback, buildTaskResultContext, scheduleDate } from '@/utils/taskSchedule'
import { saveSoloTaskResultEntry } from '@/utils/soloWorkspace'
const props = defineProps({ task: { type: Object, required: true }, pairId: { default: null }, date: { type: String, default: () => scheduleDate('today') } })
const emit = defineEmits(['close', 'saved', 'analyze'])
const userStore = useUserStore()
const dialog = ref(null)
const status = ref(props.task.status === 'completed' ? 'completed' : 'pending')
const note = ref(props.task.feedback?.note || '')
const outcome = ref(['helped', 'difficult', 'uncertain'].includes(props.task.feedback?.outcome) ? props.task.feedback.outcome : null)
const outcomeChoices = feedbackOutcomes.filter(choice => choice.value !== 'not_yet')
const error = ref('')
const saving = ref(false)
const choices = [{ value: 'completed', label: '已完成' }, { value: 'pending', label: '未完成' }]
let disposed = false
let previousFocus
const scope = JSON.stringify([userStore.token, userStore.me?.id, userStore.activePairId])
const current = () => !disposed && scope === JSON.stringify([userStore.token, userStore.me?.id, userStore.activePairId])
function close() { if (!saving.value) emit('close') }
function backdrop(event) { if (event.target === dialog.value) close() }
async function save(analyze) {
  if (saving.value || !current()) return
  saving.value = true
  error.value = ''
  const completed = status.value === 'completed'
  const feedback = buildTaskResultFeedback(props.task, { status: status.value, outcome: outcome.value, note: note.value })
  let updated = { ...props.task, status: status.value, status_label: completed ? '已完成' : '未完成', completed_at: completed ? props.task.completed_at || new Date().toISOString() : null, feedback, needs_feedback: completed && !feedback }
  try {
    if (props.date > scheduleDate('today')) throw new Error('还没到计划日期，先不用填写结果')
    if (userStore.isDemoMode) {
      const key = { owner: userStore.me?.id || 'sample', pairId: props.pairId, date: props.date }
      const pack = demoScheduleCache.read(key)
      if (!pack?.tasks?.some(task => task.id === props.task.id)) throw new Error('安排已更新，请关闭后重试')
      demoScheduleCache.save(key, { ...pack, tasks: pack.tasks.map(task => task.id === updated.id ? updated : task) })
    } else if (!props.pairId) {
      const pack = saveSoloTaskResultEntry(props.task.id, { status: status.value, feedback }, { isoDate: props.date })
      updated = pack.tasks.find(task => task.id === props.task.id) || updated
    } else {
      const result = await api.saveTaskResult(props.task.id, { status: status.value, feedback })
      if (!current()) return
      updated = result.task
    }
    emit('saved', updated)
    if (analyze) emit('analyze', buildTaskResultContext(updated, { date: props.date, pairId: props.pairId }))
    emit('close')
  } catch (e) { if (current()) error.value = e.message || '结果没保存上，请重试' }
  finally { saving.value = false }
}
watch(status, () => { outcome.value = null })
watch(() => [userStore.token, userStore.me?.id, userStore.activePairId], () => emit('close'), { flush: 'sync' })
onMounted(() => { previousFocus = document.activeElement; dialog.value.showModal() })
onBeforeUnmount(() => { disposed = true; dialog.value?.close(); previousFocus?.focus?.() })
</script>

<style scoped>
.task-result-dialog { width: min(460px, calc(100vw - 28px)); margin: auto; padding: 22px; max-height: 85dvh; overflow: auto; color: var(--ink-soft); background: var(--paper-soft, #fffaf4); border: 1px solid var(--border-strong); border-radius: 18px; }
.task-result-dialog::backdrop { background: #30271f66; }
form { display: grid; gap: 16px; }
.task-result-head, .task-result-options, .task-result-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.task-result-head { justify-content: space-between; }
h3 { font-size: 18px; }
.task-result-effect { margin: 0; padding: 0; border: 0; min-width: 0; }
.task-result-effect legend { margin-bottom: 8px; font-size: 14px; }
</style>
