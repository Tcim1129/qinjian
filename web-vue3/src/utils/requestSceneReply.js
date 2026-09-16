export async function requestSceneReply(api, pairId, context, question, isCurrent = () => true) {
  const check = () => { if (!isCurrent()) throw new Error('页面已切换，请重新操作。') }
  check()
  const session = await api.createAgentSession(pairId, { forceNew: true, surface: 'chat' })
  check()
  const id = session?.session_id || session?.id
  if (!id) throw new Error('暂时无法开始对话，请重试。')
  const result = await api.chatWithAgent(id, {
    content: question, surface: 'chat',
    scene_context: { intent: 'wording', source_label: String(context.sourceLabel || '改写').slice(0, 100), summary: String(context.summary || '').slice(0, 3200) },
  })
  check()
  const reply = String(result?.reply || result?.content || '').trim()
  if (!reply) throw new Error('这次没有收到回复，请重试。')
  return reply
}
