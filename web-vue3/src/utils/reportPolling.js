export function createReportPoller({ schedule = setTimeout, cancel = clearTimeout, now = Date.now, intervalMs = 2000, maxWaitMs = 90000 } = {}) {
  let version = 0
  let timer = null
  function stop() { version++; if (timer != null) cancel(timer); timer = null }
  function start({ read, onResult, onError = () => {}, onTimeout = () => {} }) {
    stop()
    const ticket = version
    const started = now()
    async function tick() {
      if (ticket !== version) return
      if (now() - started >= maxWaitMs) { stop(); onTimeout(); return }
      try {
        const result = await read()
        if (ticket !== version) return
        onResult(result)
        if (ticket !== version) return
        if (result?.status === 'completed' || result?.status === 'failed') { stop(); return }
        timer = schedule(tick, intervalMs)
      } catch (error) {
        if (ticket !== version) return
        stop(); onError(error)
      }
    }
    timer = schedule(tick, intervalMs)
  }
  return { start, stop }
}
