export function mergeChatHistory(history = [], localMessages = []) {
  const result = [...history]
  for (const message of localMessages.filter(item => item.deliveryPending || item.error)) {
    const index = result.findIndex(item => item.id === message.id || item.id === message.clientMessageId)
    if (index < 0) result.push(message)
    else if (result[index].payload?._delivery?.state !== 'completed') result[index] = message
  }
  return result
}
