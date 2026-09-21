import test from 'node:test'
import assert from 'node:assert/strict'

import {
  DEFAULT_REALTIME_MAX_SECONDS,
  createBackendRealtimeAsr,
  describeVoiceStartError,
  formatRecordingCountdown,
  normalizeRealtimeFinalPayload,
  resolveRealtimeMaxDurationSeconds,
  startBrowserSpeech,
} from './realtimeVoice.js'

function installBackendVoiceFakes(t) {
  const originalWindow = globalThis.window
  const navigatorDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'navigator')

  class FakeWebSocket {
    static CONNECTING = 0
    static OPEN = 1
    static CLOSING = 2
    static CLOSED = 3
    static instances = []

    constructor(url) {
      this.url = url
      this.readyState = FakeWebSocket.CONNECTING
      this.listeners = new Map()
      this.sent = []
      FakeWebSocket.instances.push(this)
    }

    addEventListener(type, handler) {
      const handlers = this.listeners.get(type) || []
      handlers.push(handler)
      this.listeners.set(type, handlers)
    }

    emit(type, payload = {}) {
      for (const handler of this.listeners.get(type) || []) handler(payload)
    }

    send(payload) {
      this.sent.push(payload)
    }

    close() {
      this.readyState = FakeWebSocket.CLOSED
    }
  }

  class FakeAudioContext {
    constructor() {
      this.sampleRate = 16000
      this.destination = {}
    }

    async resume() {}

    createMediaStreamSource() {
      return { connect() {}, disconnect() {} }
    }

    createScriptProcessor() {
      return { onaudioprocess: null, connect() {}, disconnect() {} }
    }

    createGain() {
      return { gain: { value: 1 }, connect() {}, disconnect() {} }
    }

    async close() {}
  }

  globalThis.window = {
    isSecureContext: true,
    location: { hostname: 'localhost' },
    AudioContext: FakeAudioContext,
    WebSocket: FakeWebSocket,
    setInterval: globalThis.setInterval,
    clearInterval: globalThis.clearInterval,
    setTimeout: globalThis.setTimeout,
    clearTimeout: globalThis.clearTimeout,
    btoa: (value) => Buffer.from(value, 'binary').toString('base64'),
  }
  globalThis.WebSocket = FakeWebSocket
  Object.defineProperty(globalThis, 'navigator', {
    configurable: true,
    value: {
      mediaDevices: {
        getUserMedia: async () => ({
          getTracks: () => [{ stop() {} }],
        }),
      },
    },
  })

  t.after(() => {
    globalThis.window = originalWindow
    delete globalThis.WebSocket
    if (navigatorDescriptor) Object.defineProperty(globalThis, 'navigator', navigatorDescriptor)
    else delete globalThis.navigator
  })

  return { FakeWebSocket }
}

function installBrowserSpeechFake(t) {
  const originalWindow = globalThis.window

  class FakeSpeechRecognition {
    static instances = []

    constructor() {
      this.lang = ''
      this.continuous = false
      this.interimResults = false
      FakeSpeechRecognition.instances.push(this)
    }

    start() {
      this.onstart?.()
    }

    stop() {}

    emitResult(entries) {
      const results = entries.map((entry) => {
        const result = [{ transcript: entry.transcript }]
        result.isFinal = Boolean(entry.isFinal)
        return result
      })
      this.onresult?.({ resultIndex: 0, results })
    }
  }

  globalThis.window = {
    SpeechRecognition: FakeSpeechRecognition,
    setTimeout: globalThis.setTimeout,
    clearTimeout: globalThis.clearTimeout,
  }

  t.after(() => {
    globalThis.window = originalWindow
  })

  return { FakeSpeechRecognition }
}

test('normalizeRealtimeFinalPayload keeps realtime chinese emotion metadata', () => {
  const result = normalizeRealtimeFinalPayload({
    type: 'final',
    text: '今天我其实不是想吵架，我只是希望对方能先听懂我的委屈。',
    content_emotion: {
      sentiment: 'negative',
      sentiment_label: '偏负向',
      mood_label: '委屈',
      score: 7,
    },
    voice_emotion: {
      code: '',
      label: '待识别',
    },
    transcript_language: {
      code: 'zh',
      label: '中文',
    },
  })

  assert.equal(result.text, '今天我其实不是想吵架，我只是希望对方能先听懂我的委屈。')
  assert.equal(result.contentEmotion?.mood_label, '委屈')
  assert.equal(result.contentEmotion?.sentiment_label, '偏负向')
  assert.equal(result.contentEmotion?.score, 7)
  assert.deepEqual(result.voiceEmotion, { code: '', label: '待识别' })
  assert.deepEqual(result.transcriptLanguage, { code: 'zh', label: '中文' })
})

test('resolveRealtimeMaxDurationSeconds defaults to a one minute guardrail', () => {
  assert.equal(DEFAULT_REALTIME_MAX_SECONDS, 60)
  assert.equal(resolveRealtimeMaxDurationSeconds(undefined), 60)
  assert.equal(resolveRealtimeMaxDurationSeconds(60), 60)
  assert.equal(resolveRealtimeMaxDurationSeconds(5), 15)
  assert.equal(resolveRealtimeMaxDurationSeconds(999), 300)
})

test('formatRecordingCountdown renders compact minute second text', () => {
  assert.equal(formatRecordingCountdown(120), '02:00')
  assert.equal(formatRecordingCountdown(7), '00:07')
  assert.equal(formatRecordingCountdown(-1), '00:00')
})

test('describeVoiceStartError gives recoverable mobile permission guidance', () => {
  assert.match(
    describeVoiceStartError({ name: 'NotAllowedError' }),
    /允许麦克风/
  )
  assert.match(
    describeVoiceStartError(new Error('实时语音输入需要 HTTPS 或 localhost 访问')),
    /HTTPS/
  )
  assert.match(
    describeVoiceStartError(new Error('当前浏览器不支持实时语音')),
    /上传录音|改用文字/
  )
})

test('backend realtime ASR stops partial updates after user stops recording', async (t) => {
  const { FakeWebSocket } = installBackendVoiceFakes(t)
  const partials = []
  const finals = []
  const errors = []

  const controller = createBackendRealtimeAsr({
    getSocketUrl: async () => 'wss://example.test/asr',
    onPartial: (text) => partials.push(text),
    onFinal: (payload) => finals.push(payload),
    onError: (message) => errors.push(message),
  })

  await controller.start()
  const socket = FakeWebSocket.instances[0]
  socket.readyState = FakeWebSocket.OPEN
  socket.emit('open')
  socket.emit('message', { data: JSON.stringify({ type: 'partial', text: '还在听' }) })

  assert.deepEqual(partials, ['还在听'])

  controller.stop()
  socket.emit('message', { data: JSON.stringify({ type: 'partial', text: '不该继续写' }) })
  socket.emit('close')

  assert.deepEqual(partials, ['还在听'])
  assert.deepEqual(errors, [])
  assert.deepEqual(finals, ['还在听'])
})

test('backend realtime ASR auto-finalizes from last partial when provider does not close after stop', async (t) => {
  const { FakeWebSocket } = installBackendVoiceFakes(t)
  const finals = []

  const controller = createBackendRealtimeAsr({
    getSocketUrl: async () => 'wss://example.test/asr',
    stopFinalizeTimeoutMs: 5,
    onPartial() {},
    onFinal: (payload) => finals.push(payload),
  })

  await controller.start()
  const socket = FakeWebSocket.instances[0]
  socket.readyState = FakeWebSocket.OPEN
  socket.emit('open')
  socket.emit('message', { data: JSON.stringify({ type: 'partial', text: '先保留这句' }) })

  controller.stop()
  await new Promise((resolve) => setTimeout(resolve, 20))

  assert.deepEqual(finals, ['先保留这句'])
})

test('browser speech fallback stops preview updates after user stops recording', (t) => {
  const { FakeSpeechRecognition } = installBrowserSpeechFake(t)
  const partials = []
  const finals = []

  const controller = startBrowserSpeech({
    onPartial: (text) => partials.push(text),
    onFinal: (text) => finals.push(text),
  })
  const recognition = FakeSpeechRecognition.instances[0]

  recognition.emitResult([{ transcript: '第一句', isFinal: false }])
  controller.stop()
  recognition.emitResult([{ transcript: '第二句不该刷出来', isFinal: false }])
  recognition.emitResult([{ transcript: '最后一句', isFinal: true }])
  recognition.onend()

  assert.deepEqual(partials, ['第一句'])
  assert.deepEqual(finals, ['最后一句'])
})

test('browser speech fallback auto-finalizes if stop never emits onend', async (t) => {
  const { FakeSpeechRecognition } = installBrowserSpeechFake(t)
  const finals = []

  const controller = startBrowserSpeech({
    stopFinalizeTimeoutMs: 5,
    onFinal: (text) => finals.push(text),
  })
  const recognition = FakeSpeechRecognition.instances[0]

  recognition.emitResult([{ transcript: '已经说完', isFinal: true }])
  controller.stop()
  await new Promise((resolve) => setTimeout(resolve, 20))

  assert.deepEqual(finals, ['已经说完'])
})
