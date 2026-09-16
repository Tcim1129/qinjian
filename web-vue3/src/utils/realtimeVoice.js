export const DEFAULT_REALTIME_MAX_SECONDS = 60
const MIN_REALTIME_MAX_SECONDS = 15
const MAX_REALTIME_MAX_SECONDS = 300
const DEFAULT_STOP_FINALIZE_TIMEOUT_MS = 3500

export function resolveRealtimeMaxDurationSeconds(value) {
  const seconds = Number(value ?? DEFAULT_REALTIME_MAX_SECONDS)
  if (!Number.isFinite(seconds)) return DEFAULT_REALTIME_MAX_SECONDS
  return Math.max(MIN_REALTIME_MAX_SECONDS, Math.min(MAX_REALTIME_MAX_SECONDS, Math.round(seconds)))
}

export function formatRecordingCountdown(value) {
  const seconds = Math.max(0, Math.ceil(Number(value) || 0))
  const minutes = Math.floor(seconds / 60)
  const remain = seconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(remain).padStart(2, '0')}`
}

export function describeVoiceStartError(error) {
  const name = String(error?.name || '')
  const message = String(error?.message || error || '')
  if (name === 'NotAllowedError' || name === 'PermissionDeniedError' || /permission|not.?allowed|denied|拒绝/i.test(message)) {
    return '浏览器没有允许麦克风权限，可以允许麦克风后重试，或者上传录音、改用文字。'
  }
  if (/HTTPS|secure|安全/i.test(message)) {
    return '实时语音输入需要 HTTPS 或 localhost 访问。'
  }
  if (/不支持|not supported|SpeechRecognition|mediaDevices|AudioContext|WebSocket/i.test(message)) {
    return '当前浏览器不支持实时语音，可以上传录音或改用文字。'
  }
  return message || '暂时无法开启语音，可以上传录音或改用文字。'
}

export function normalizeRealtimeFinalPayload(payload = {}) {
  return {
    text: String(payload?.text || payload?.transcript || '').trim(),
    audioInfo: payload?.audio_info || null,
    voiceEmotion: payload?.voice_emotion || null,
    contentEmotion: payload?.content_emotion || null,
    transcriptLanguage: payload?.transcript_language || null,
  }
}

function downsampleFloat32Buffer(buffer, inputRate, outputRate = 16000) {
  if (!buffer?.length) return new Float32Array()
  if (inputRate === outputRate) return buffer.slice(0)
  const ratio = inputRate / outputRate
  const newLength = Math.max(1, Math.round(buffer.length / ratio))
  const result = new Float32Array(newLength)
  let offset = 0
  for (let index = 0; index < newLength; index += 1) {
    const nextOffset = Math.min(buffer.length, Math.round((index + 1) * ratio))
    let sum = 0
    let count = 0
    for (let cursor = offset; cursor < nextOffset; cursor += 1) {
      sum += buffer[cursor]
      count += 1
    }
    result[index] = count ? sum / count : 0
    offset = nextOffset
  }
  return result
}

function float32ToPCM16Bytes(buffer) {
  const arrayBuffer = new ArrayBuffer(buffer.length * 2)
  const view = new DataView(arrayBuffer)
  for (let index = 0; index < buffer.length; index += 1) {
    const sample = Math.max(-1, Math.min(1, buffer[index] || 0))
    view.setInt16(index * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true)
  }
  return new Uint8Array(arrayBuffer)
}

function uint8ArrayToBase64(bytes) {
  if (!bytes?.length) return ''
  let binary = ''
  const chunkSize = 0x8000
  for (let index = 0; index < bytes.length; index += chunkSize) {
    const chunk = bytes.subarray(index, index + chunkSize)
    binary += String.fromCharCode(...chunk)
  }
  return window.btoa(binary)
}

function buildWavBlobFromPcm16Chunks(chunks, sampleRate = 16000) {
  const totalLength = chunks.reduce((total, chunk) => total + chunk.length, 0)
  if (!totalLength) return null
  const headerLength = 44
  const wav = new Uint8Array(headerLength + totalLength)
  const view = new DataView(wav.buffer)

  function writeAscii(offset, value) {
    for (let index = 0; index < value.length; index += 1) {
      wav[offset + index] = value.charCodeAt(index)
    }
  }

  writeAscii(0, 'RIFF')
  view.setUint32(4, 36 + totalLength, true)
  writeAscii(8, 'WAVE')
  writeAscii(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeAscii(36, 'data')
  view.setUint32(40, totalLength, true)

  let offset = headerLength
  for (const chunk of chunks) {
    wav.set(chunk, offset)
    offset += chunk.length
  }
  return new Blob([wav], { type: 'audio/wav' })
}

function assertSecureVoiceContext() {
  const hostname = String(window.location.hostname || '').replace(/^\[|\]$/g, '')
  const isLoopbackHost = hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1'
  if (!window.isSecureContext && !isLoopbackHost) {
    throw new Error('实时语音输入需要 HTTPS 或 localhost 访问')
  }
}

export function createBackendRealtimeAsr(options) {
  const state = {
    socket: null,
    stream: null,
    audioContext: null,
    sourceNode: null,
    processorNode: null,
    sinkNode: null,
    active: false,
    stopping: false,
    finalDelivered: false,
    disposed: false,
    timerId: null,
    stopTimerId: null,
    startedAt: null,
    rawPcmChunks: [],
    lastPartialText: '',
  }

  function cleanupAudio() {
    if (state.processorNode) {
      state.processorNode.onaudioprocess = null
      state.processorNode.disconnect()
      state.processorNode = null
    }
    if (state.sourceNode) {
      state.sourceNode.disconnect()
      state.sourceNode = null
    }
    if (state.sinkNode) {
      state.sinkNode.disconnect()
      state.sinkNode = null
    }
    if (state.stream) {
      state.stream.getTracks().forEach((track) => track.stop())
      state.stream = null
    }
    if (state.audioContext) {
      state.audioContext.close?.().catch(() => null)
      state.audioContext = null
    }
  }

  function buildFinalPayload(payload = {}) {
    const finalPayload = normalizeRealtimeFinalPayload(payload)
    if (!finalPayload.text && state.lastPartialText) {
      finalPayload.text = state.lastPartialText
    }
    const durationSeconds = state.startedAt ? Math.max(0, (Date.now() - state.startedAt) / 1000) : null
    const rawAudioBlob = options.captureRawAudio
      ? buildWavBlobFromPcm16Chunks(state.rawPcmChunks)
      : null
    return options.captureRawAudio
      ? { ...finalPayload, durationSeconds, rawAudioBlob }
      : finalPayload.text
  }

  function clearStopTimer() {
    if (state.stopTimerId) {
      window.clearTimeout(state.stopTimerId)
      state.stopTimerId = null
    }
  }

  async function deliverFinal(payload = {}) {
    if (state.finalDelivered || state.disposed) return
    state.finalDelivered = true
    const finalPayload = buildFinalPayload(payload)
    cleanup()
    await options.onFinal?.(finalPayload)
  }

  function scheduleStopFallback() {
    clearStopTimer()
    const timeoutMs = Number(options.stopFinalizeTimeoutMs ?? DEFAULT_STOP_FINALIZE_TIMEOUT_MS)
    state.stopTimerId = window.setTimeout(() => {
      void deliverFinal({ text: state.lastPartialText }).catch(() => null)
    }, Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : DEFAULT_STOP_FINALIZE_TIMEOUT_MS)
  }

  function cleanup() {
    state.disposed = true
    if (state.timerId) {
      window.clearInterval(state.timerId)
      state.timerId = null
    }
    clearStopTimer()
    cleanupAudio()
    if (state.socket) {
      try {
        state.socket.close()
      } catch {
        // ignore close errors
      }
      state.socket = null
    }
    state.active = false
    state.stopping = false
    state.startedAt = null
    state.rawPcmChunks = []
    state.lastPartialText = ''
  }

  async function start() {
    assertSecureVoiceContext()
    if (!navigator.mediaDevices?.getUserMedia || !(window.AudioContext || window.webkitAudioContext) || !window.WebSocket) {
      throw new Error('当前浏览器不支持实时语音')
    }

    const socketUrl = await options.getSocketUrl()
    const maxDurationSeconds = resolveRealtimeMaxDurationSeconds(options.maxDurationSeconds)
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
    })
    const AudioContextCtor = window.AudioContext || window.webkitAudioContext
    const audioContext = new AudioContextCtor()
    await audioContext.resume?.()
    const sourceNode = audioContext.createMediaStreamSource(stream)
    const processorNode = audioContext.createScriptProcessor(4096, 1, 1)
    const sinkNode = audioContext.createGain()
    sinkNode.gain.value = 0

    const socket = new WebSocket(socketUrl)
    Object.assign(state, {
      socket,
      stream,
      audioContext,
      sourceNode,
      processorNode,
      sinkNode,
      active: false,
      stopping: false,
      finalDelivered: false,
      disposed: false,
      timerId: null,
      stopTimerId: null,
      startedAt: null,
      rawPcmChunks: [],
      lastPartialText: '',
    })

    sourceNode.connect(processorNode)
    processorNode.connect(sinkNode)
    sinkNode.connect(audioContext.destination)

    processorNode.onaudioprocess = (event) => {
      if (!state.active || state.stopping || state.socket?.readyState !== WebSocket.OPEN) return
      const samples = event.inputBuffer.getChannelData(0)
      const downsampled = downsampleFloat32Buffer(samples, audioContext.sampleRate, 16000)
      const pcmBytes = float32ToPCM16Bytes(downsampled)
      if (options.captureRawAudio) state.rawPcmChunks.push(pcmBytes)
      const audio = uint8ArrayToBase64(pcmBytes)
      if (audio) state.socket.send(JSON.stringify({ type: 'audio.chunk', audio }))
    }

    socket.addEventListener('open', () => {
      state.active = true
      state.startedAt = Date.now()
      options.onActive?.()
      options.onStatus?.('麦克风已开启，正在听你说。')
      options.onTick?.({ remainingSeconds: maxDurationSeconds, elapsedSeconds: 0 })
      state.timerId = window.setInterval(() => {
        if (!state.active || state.stopping || !state.startedAt) return
        const elapsedSeconds = Math.floor((Date.now() - state.startedAt) / 1000)
        const remainingSeconds = Math.max(0, maxDurationSeconds - elapsedSeconds)
        options.onTick?.({ remainingSeconds, elapsedSeconds })
        if (remainingSeconds <= 0) {
          options.onTimeLimit?.()
          stop()
        }
      }, 1000)
      socket.send(JSON.stringify({
        type: 'session.start',
        format: 'pcm',
        sample_rate: 16000,
        language: 'zh',
      }))
    })

    socket.addEventListener('message', async (event) => {
      if (state.disposed) return
      let payload
      try {
        payload = JSON.parse(event.data)
      } catch {
        return
      }
      if (payload.type === 'partial') {
        if (state.stopping) return
        const text = String(payload.text || '')
        if (text) state.lastPartialText = text
        options.onPartial?.(text)
        return
      }
      if (payload.type === 'final') {
        await deliverFinal(payload)
        return
      }
      if (payload.type === 'error') {
        const shouldFinalize = state.stopping && !state.finalDelivered
        if (shouldFinalize) {
          await deliverFinal({ text: state.lastPartialText })
          return
        }
        cleanup()
        options.onError?.(payload.message || '实时识别失败，请重试')
      }
    })

    socket.addEventListener('close', async () => {
      const shouldFinalize = !state.finalDelivered && state.stopping && !state.disposed
      const shouldNotify = !state.finalDelivered && !state.stopping && !state.disposed
      if (shouldFinalize) {
        await deliverFinal({ text: state.lastPartialText })
        return
      }
      cleanup()
      if (shouldNotify) options.onError?.('语音已中断，请重试')
    })

    socket.addEventListener('error', () => {
      if (state.disposed) return
      cleanup()
      options.onError?.('语音连接失败')
    })
  }

  function stop({ discard = false } = {}) {
    state.stopping = true
    cleanupAudio()
    if (discard) {
      cleanup()
      return false
    }
    if (state.socket?.readyState === WebSocket.OPEN) {
      state.socket.send(JSON.stringify({ type: 'session.stop' }))
      scheduleStopFallback()
      return true
    }
    void deliverFinal({ text: state.lastPartialText }).catch(() => null)
    return false
  }

  return { start, stop, cleanup, get active() { return state.active } }
}

export function startBrowserSpeech(options = {}) {
  const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!SpeechRecognitionCtor) throw new Error('浏览器不支持语音识别')

  const recognition = new SpeechRecognitionCtor()
  let finalTranscript = ''
  let discarded = false
  let stopping = false
  let ended = false
  let stopTimerId = null
  recognition.lang = 'zh-CN'
  recognition.continuous = true
  recognition.interimResults = true

  recognition.onstart = () => {
    options.onActive?.()
    options.onStatus?.(options.reason ? `已切到浏览器转写：${options.reason}` : '浏览器语音识别已开启，正在听你说。')
  }
  recognition.onresult = (event) => {
    if (discarded) return
    let interim = ''
    for (let index = event.resultIndex; index < event.results.length; index += 1) {
      const transcript = event.results[index][0]?.transcript || ''
      if (event.results[index].isFinal) finalTranscript += transcript
      else if (!stopping) interim += transcript
    }
    if (!stopping) options.onPartial?.(`${finalTranscript}${interim}`.trim())
  }
  recognition.onerror = (event) => {
    if (discarded || stopping) return
    const message = event.error === 'not-allowed' ? '麦克风权限被拒绝' : '语音识别失败'
    options.onError?.(message)
  }
  function clearStopTimer() {
    if (stopTimerId) {
      window.clearTimeout(stopTimerId)
      stopTimerId = null
    }
  }

  function finish() {
    if (ended) return
    ended = true
    clearStopTimer()
    options.onFinal?.(discarded ? '' : finalTranscript.trim())
  }

  recognition.onend = finish
  recognition.start()

  return {
    stop({ discard = false } = {}) {
      discarded = discard
      stopping = true
      try {
        recognition.stop()
      } catch {
        finish()
      }
      if (!discard && !ended) {
        const timeoutMs = Number(options.stopFinalizeTimeoutMs ?? DEFAULT_STOP_FINALIZE_TIMEOUT_MS)
        stopTimerId = window.setTimeout(
          finish,
          Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : DEFAULT_STOP_FINALIZE_TIMEOUT_MS,
        )
      }
    },
    cleanup() {
      discarded = true
      stopping = true
      clearStopTimer()
      recognition.onend = null
      recognition.onresult = null
      recognition.onerror = null
      try {
        recognition.stop()
      } catch {
        // ignore cleanup errors
      }
    },
  }
}
