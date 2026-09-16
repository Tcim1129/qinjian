<template>
  <section v-for="proposal in proposals" :key="proposal.proposal_id" class="agent-task-proposal" aria-label="待确认的行动建议">
    <small>{{ proposal.due_date }} · 我的安排</small>
    <strong>{{ proposal.title }}</strong>
    <p v-if="proposal.description">{{ proposal.description }}</p>
    <button class="btn btn-secondary btn-sm" type="button" :disabled="Boolean(proposal.confirmed_task_id) || pending.has(proposal.proposal_id)" @click="confirm(proposal)">
      {{ proposal.confirmed_task_id ? '已加入安排' : pending.has(proposal.proposal_id) ? '保存中…' : '加入安排' }}
    </button>
    <p v-if="errors[proposal.proposal_id]" role="alert">{{ errors[proposal.proposal_id] }}</p>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { api } from '@/api'
import { useUserStore } from '@/stores/user'

const props = defineProps({ message: { type: Object, required: true }, sessionId: { type: String, required: true } })
const emit = defineEmits(['confirmed'])
const userStore = useUserStore()
const pending = ref(new Set())
const errors = ref({})
let disposed = false
const proposals = computed(() => Array.isArray(props.message.payload?.task_proposals) ? props.message.payload.task_proposals : [])
const scopeKey = () => JSON.stringify([userStore.token, userStore.me?.id, props.sessionId, props.message.id])
onBeforeUnmount(() => { disposed = true })

async function confirm(proposal) {
  const id = proposal.proposal_id
  if (disposed || proposal.confirmed_task_id || pending.value.has(id)) return
  const scope = scopeKey()
  pending.value.add(id)
  errors.value[id] = ''
  try {
    const result = await api.confirmAgentTask(props.sessionId, props.message.id, id)
    if (disposed || scope !== scopeKey()) return
    emit('confirmed', { proposalId: id, taskId: result.task.id })
  } catch (error) {
    if (!disposed && scope === scopeKey()) errors.value[id] = error.message || '没保存成功，请重试'
  } finally { pending.value.delete(id) }
}
</script>

<style scoped>
.agent-task-proposal { display: grid; gap: 8px; margin-top: 14px; padding: 14px; border: 1px solid var(--border); border-radius: 12px; background: var(--paper, #fffaf4); }
.agent-task-proposal small { color: var(--ink-soft); }
.agent-task-proposal p { margin: 0; white-space: pre-wrap; }
.agent-task-proposal button { justify-self: start; }
</style>
