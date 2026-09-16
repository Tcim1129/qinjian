import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { getDemoPersonaQA } from '../demo/fixtures.js'

const chatSource = readFileSync(fileURLToPath(new URL('../views/chat/ChatPage.vue', import.meta.url)), 'utf8')

test('ChatPage keeps compact embedded layout but gives standalone desktop chat room to scroll', () => {
  // 页面使用 100dvh 视口高度
  assert.match(chatSource, /height:\s*calc\(100dvh\s*-\s*var\(--header-height/)
  // 聊天外层卡片与消息列表采用弹性伸展
  assert.match(chatSource, /\.chat-shell\s*\{[^}]*flex:\s*1/s)
  assert.match(chatSource, /\.chat-list\s*\{[^}]*flex:\s*1[^}]*overflow-y:\s*auto/s)
  assert.match(chatSource, /\.chat-page:not\(\.chat-page--embedded\)[^{]*\{\s*height:\s*auto/s)
  assert.match(chatSource, /\.chat-page:not\(\.chat-page--embedded\) \.chat-list\s*\{[^}]*height:\s*clamp\(480px, 65dvh, 900px\)/s)
  // 底部输入框默认行高合理紧凑，不再锁死 140px
  assert.doesNotMatch(chatSource, /\.chat-composer__input\s*\{[^}]*min-height:\s*140px/s)
})

test('ChatPage mobile media query avoids vertical stacking disaster for action buttons', () => {
  // 移动端不再将头部与底部按钮强制变成 column 100%
  assert.doesNotMatch(chatSource, /@media\s*\(max-width:\s*600px\)\s*\{[^}]*\.chat-composer__actions[^{]*\{[^}]*flex-direction:\s*column/s)
  assert.doesNotMatch(chatSource, /@media\s*\(max-width:\s*600px\)\s*\{[^}]*\.chat-head__actions[^{]*\{[^}]*flex-direction:\s*column/s)
})

test('ChatPage preserves user messages and handles suggested questions with persona responses', () => {
  // 模板包含快捷提问与场景提示
  assert.match(chatSource, /class="chat-suggestions-bar"/)
  assert.match(chatSource, /askSuggestedQuestion\(q\)/)
  // 监听回车快捷发送
  assert.match(chatSource, /@keydown\.enter="handleEnterKey"/)

  // 绝不能在 catch 中把用户消息直接过滤删除
  assert.doesNotMatch(chatSource, /messages\.value\s*=\s*messages\.value\.filter\(\(item\)\s*=>\s*item\.id\s*!==\s*optimisticId\)/)

  // Demo 模式下回复能正确匹配 fixtures 中的 Persona 问答
  const linXiaQA = getDemoPersonaQA('b2222222-2222-4222-8222-222222222222')
  assert.ok(linXiaQA)
  assert.ok(linXiaQA.suggestedQuestions.length >= 4)
  const q1 = linXiaQA.suggestedQuestions[0]
  assert.ok(linXiaQA.replies[q1])
  assert.match(linXiaQA.replies[q1], /别问她/)
})
