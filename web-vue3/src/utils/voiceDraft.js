export function mergeVoiceTranscriptIntoDraft(currentText, transcript) {
  const current = String(currentText || '').trim()
  const incoming = String(transcript || '').trim()
  if (!incoming) return current
  if (!current) return incoming
  if (current.includes(incoming)) return current
  return `${current}\n${incoming}`
}
