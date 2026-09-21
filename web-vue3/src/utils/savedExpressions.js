import { reactive } from 'vue'

function requestId() {
  // getRandomValues also works on HTTP LAN previews, unlike randomUUID.
  const bytes = globalThis.crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 15) | 64
  bytes[8] = (bytes[8] & 63) | 128
  const hex = [...bytes].map(value => value.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

export function createSavedExpressions(api, { makeId = requestId } = {}) {
  const state = reactive({ items: [], loading: false, saving: false, deletingId: '',
    loadError: '', saveError: '', deleteError: '', failedText: '', savedText: '', savedId: '' })
  let revision = 0, listRevision = 0, scope = { enabled: false, pairId: null }, retry = null

  function setScope(next) {
    revision++
    listRevision++
    scope = { ...next }
    retry = null
    Object.assign(state, { items: [], loading: false, saving: false, deletingId: '',
      loadError: '', saveError: '', deleteError: '', failedText: '', savedText: '', savedId: '' })
  }

  async function load() {
    if (!scope.enabled || state.saving || state.deletingId) return false
    const generation = revision, sequence = ++listRevision
    const current = () => generation === revision && sequence === listRevision
    state.loading = true
    state.loadError = ''
    try {
      const items = await api.listExpressions(scope.pairId)
      if (!current()) return false
      if (!Array.isArray(items) || items.some(item => !item?.id || typeof item.text !== 'string')) throw new Error('保存列表没能加载，请重试。')
      state.items = items
      return true
    } catch (error) {
      if (current()) state.loadError = error.message || '保存列表没能加载，请重试。'
      return false
    } finally { if (current()) state.loading = false }
  }

  async function save(value) {
    if (!scope.enabled || state.saving || state.deletingId) return false
    const text = String(value || '').trim()
    state.saveError = ''
    state.failedText = text
    if (!text || text.length > 2000) {
      state.saveError = text ? '最多保存 2000 字' : '先写下要保存的话'
      return false
    }
    if (state.savedText === text && state.savedId) return true
    const generation = revision
    state.saving = true
    try {
      if (!retry || retry.data.text !== text) retry = { id: makeId(), data: { text, pair_id: scope.pairId || null } }
      const request = retry
      const saved = await api.saveExpression(request.id, request.data)
      if (generation !== revision) return false
      if (saved?.id !== request.id || saved.text !== text || (saved.pair_id || null) !== request.data.pair_id) throw new Error('还未确认保存结果，请重试。')
      listRevision++
      state.loading = false
      state.items = [saved, ...state.items.filter(item => item.id !== saved.id)].slice(0, 20)
      state.savedText = text
      state.savedId = saved.id
      return true
    } catch (error) {
      if (generation === revision) state.saveError = error.message || '没能保存，文字还在，请重试。'
      return false
    } finally { if (generation === revision) state.saving = false }
  }

  async function remove(id) {
    if (!scope.enabled || state.saving || state.deletingId || !state.items.some(item => item.id === id)) return false
    const generation = revision
    state.deletingId = id
    state.deleteError = ''
    try {
      try { await api.deleteExpression(id) } catch (error) { if ((error.statusCode || error.status) !== 404) throw error }
      if (generation !== revision) return false
      listRevision++
      state.loading = false
      state.items = state.items.filter(item => item.id !== id)
      if (retry?.id === id) retry = null
      if (state.savedId === id) { state.savedId = ''; state.savedText = '' }
      return true
    } catch (error) {
      if (generation === revision) state.deleteError = error.message || '没能删除，请重试。'
      return false
    } finally { if (generation === revision) state.deletingId = '' }
  }

  return { state, setScope, load, save, remove }
}
