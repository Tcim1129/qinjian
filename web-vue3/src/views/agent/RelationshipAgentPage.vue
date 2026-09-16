<template>
  <main class="demo-page">
    <h1 class="sr-only">关系协作智能体</h1>

    <section
      class="demo-artboard"
      tabindex="-1"
      aria-label="关系协作智能体演示画布"
      @keydown.esc="closeOpenSurfaces"
    >
      <img
        class="demo-artboard__image"
        src="/competition/relationship-agent-concept-v3.png"
        alt="关系协作智能体：真实场景库、对话推演、证据与推理、建议行动"
      />

      <div
        v-if="demoState !== 'idle'"
        class="demo-live-layer"
        :data-state="demoState"
      >
        <svg class="demo-live-path" viewBox="0 0 1568 1003" preserveAspectRatio="none" aria-hidden="true">
          <path d="M360 500 C430 350 510 520 595 465 S760 515 840 460 S1010 520 1100 440" />
          <circle cx="1100" cy="440" r="8" />
        </svg>
        <p class="sr-only" aria-live="polite">{{ liveStateTitle }}。{{ liveStateMessage }}</p>
      </div>

      <div class="demo-hotspot-layer" aria-label="可操作元素">
        <button
          v-for="scenario in scenarios"
          :key="scenario.id"
          class="demo-hotspot demo-hotspot--scenario"
          :style="scenario.hotspot"
          type="button"
          :aria-label="scenario.label"
          @click="openScenario(scenario)"
        >
          <span class="sr-only">{{ scenario.label }}：{{ scenario.prompt }}</span>
        </button>

        <button
          class="demo-hotspot demo-hotspot--why"
          type="button"
          aria-label="它为什么这样判断"
          @click="toggleEvidence"
        ></button>

        <button
          v-for="step in steps"
          :key="step.id"
          class="demo-hotspot demo-hotspot--step"
          :style="step.hotspot"
          type="button"
          :aria-label="step.title"
          @click="openEvidence(step)"
        >
          <span class="sr-only">{{ step.title }}：{{ step.detail }}</span>
        </button>

        <button
          class="demo-hotspot demo-hotspot--confirm"
          type="button"
          aria-label="确认创建"
          @click="openAction('confirm')"
        ></button>
        <button
          class="demo-hotspot demo-hotspot--smaller"
          type="button"
          aria-label="换个更小的"
          @click="openAction('smaller')"
        ></button>
      </div>

      <aside
        v-if="evidenceOpen"
        class="interaction-panel interaction-panel--evidence interaction-panel--docked"
        role="dialog"
        aria-modal="false"
        aria-label="证据与推理"
      >
        <button class="interaction-panel__close" type="button" aria-label="关闭证据" @click="closeEvidence">×</button>
        <small>EVIDENCE · {{ activeStep.no }}/04</small>
        <h2>证据与推理</h2>
        <strong>{{ activeStep.title }}</strong>
        <p>{{ activeStep.detail }}</p>
        <button
          v-for="tool in activeStep.tools"
          :key="tool.name"
          class="evidence-row"
          type="button"
          @click="expandedTool = expandedTool === tool.name ? '' : tool.name"
        >
          <span>工具调用</span>
          <b>{{ tool.name }}</b>
          <em>{{ tool.state }}</em>
          <p v-if="expandedTool === tool.name">{{ tool.reason }}</p>
        </button>
        <div class="interaction-panel__rule">高风险先转介 · 不代发消息 · 行动前由你决定</div>
      </aside>

      <aside
        v-if="actionOpen"
        class="interaction-panel interaction-panel--action action-dock"
        role="dialog"
        aria-modal="false"
        aria-label="建议行动"
      >
        <button class="interaction-panel__close" type="button" aria-label="关闭行动" @click="closeAction">×</button>
        <small>建议行动 · 低风险 · 需确认</small>
        <h2>{{ actionTitle }}</h2>
        <p>{{ actionDescription }}</p>
        <div class="interaction-panel__buttons">
          <button class="interaction-panel__primary" type="button" @click="startReasoning">交给智能体判断</button>
          <button type="button" @click="closeAction">先不创建</button>
        </div>
      </aside>

      <section
        v-if="conversationOpen"
        class="conversation-dialog conversation-workspace"
        role="dialog"
        aria-modal="false"
        aria-label="真实对话"
      >
        <header>
          <div><small>真实对话</small><strong>{{ activeScenario.label }}</strong></div>
          <button type="button" aria-label="关闭对话" @click="closeConversation">×</button>
        </header>
        <ChatPage ref="chatPageRef" embedded />
      </section>
    </section>
  </main>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import ChatPage from '@/views/chat/ChatPage.vue'

const scenarios = [
  {
    id: 'repair',
    label: '今晚怎么开口？',
    prompt: '我们最近因为周末要不要回老家这件事又有分歧，我担心一开口就会吵起来，今晚该怎么说才好？',
    hotspot: { left: '1.3%', top: '14.6%', width: '17.7%', height: '18.2%' },
  },
  {
    id: 'wording',
    label: '要不要换个说法？',
    prompt: '我已经写好一段想说的话，但担心听起来像在责备对方。请帮我换一种更容易被听见的说法。',
    hotspot: { left: '1.3%', top: '31.7%', width: '17.7%', height: '18.2%' },
  },
  {
    id: 'care',
    label: '怎样不伤和气？',
    prompt: '我想表达关心，但又不想让对方觉得有压力。请结合关系状态，帮我找一个轻一点的开场。',
    hotspot: { left: '1.3%', top: '48.8%', width: '17.7%', height: '18.2%' },
  },
]

const steps = [
  {
    id: 'context',
    no: '01',
    title: '读取授权信息',
    detail: '只检索与你当前困扰相关、并且已经授权的关系上下文。',
    hotspot: { left: '20.2%', top: '39.5%', width: '15.4%', height: '23%' },
    tools: [
      { name: '关系状态读取', state: '已完成', reason: '确认当前关系阶段和最近状态。' },
      { name: '历史事件检索', state: '可展开', reason: '只查找近期互动与重复触发点。' },
    ],
  },
  {
    id: 'risk',
    no: '02',
    title: '风险判断',
    detail: '识别冲突强度、情绪触发点和危机信号，决定是否继续建议。',
    hotspot: { left: '36.4%', top: '39.2%', width: '14.9%', height: '24%' },
    tools: [
      { name: '行为与风险分析', state: '进行中', reason: '判断冲突是否正在升级。' },
      { name: '修复协议匹配', state: '候选', reason: '匹配更低压力的修复方式。' },
    ],
  },
  {
    id: 'action',
    no: '03',
    title: '提出小行动',
    detail: '把判断转成今天能完成、可撤回的小行动。',
    hotspot: { left: '51.2%', top: '39.6%', width: '15.5%', height: '22.8%' },
    tools: [
      { name: '表达策略匹配', state: '待运行', reason: '根据风险与语气偏好提出一句开场。' },
      { name: '小行动生成', state: '待运行', reason: '把建议缩成今天可以完成的一步。' },
    ],
  },
  {
    id: 'confirm',
    no: '04',
    title: '等待你确认',
    detail: '行动只有在你明确确认后才会创建，反馈会改变下一步。',
    hotspot: { left: '65.4%', top: '39.3%', width: '15.5%', height: '23%' },
    tools: [
      { name: '任务创建', state: '需确认', reason: '不会自动代办或代发消息。' },
      { name: '效果反馈', state: '后续', reason: '把完成结果带回下一轮建议。' },
    ],
  },
]

const activeScenario = ref(scenarios[0])
const activeStep = ref(steps[1])
const expandedTool = ref(steps[1].tools[0].name)
const evidenceOpen = ref(false)
const actionOpen = ref(false)
const conversationOpen = ref(false)
const actionType = ref('confirm')
const demoState = ref('idle')
const chatPageRef = ref(null)

const actionTitle = computed(() => actionType.value === 'smaller' ? '换个更小的行动' : '确认创建前，再看一眼')
const actionDescription = computed(() => actionType.value === 'smaller'
  ? '先把这件事缩成一个今天可以完成、不会增加压力的小动作。'
  : '智能体会先结合授权上下文判断，真正创建仍需要你的明确确认。')
const liveStateTitle = computed(() => ({
  context: '已读取授权信息',
  reasoning: '智能体正在判断',
  evidence: activeStep.value.title,
  proposal: '行动提案待确认',
}[demoState.value] || ''))
const liveStateMessage = computed(() => ({
  context: '只取当前关系所需的内容',
  reasoning: '风险与下一步正在被逐项核对',
  evidence: '点开右侧证据查看为什么',
  proposal: '先判断，再由你决定是否创建',
}[demoState.value] || ''))
function openScenario(scenario) {
  activeScenario.value = scenario
  openConversation()
  demoState.value = 'context'
}

function openConversation() {
  closeOpenSurfaces()
  conversationOpen.value = true
  nextTick(() => chatPageRef.value?.applySuggestedPrompt?.(activeScenario.value.prompt))
}

function openEvidence(step = activeStep.value) {
  closeOpenSurfaces()
  activeStep.value = step
  expandedTool.value = step.tools[0]?.name || ''
  demoState.value = 'evidence'
  evidenceOpen.value = true
}

function toggleEvidence() {
  if (evidenceOpen.value) {
    closeOpenSurfaces()
    return
  }
  openEvidence(activeStep.value)
}

function openAction(type) {
  closeOpenSurfaces()
  actionType.value = type
  demoState.value = 'proposal'
  actionOpen.value = true
}

function startReasoning() {
  openConversation()
  demoState.value = 'reasoning'
}

function closeOpenSurfaces() {
  evidenceOpen.value = false
  actionOpen.value = false
  conversationOpen.value = false
  demoState.value = 'idle'
}

function closeEvidence() {
  closeOpenSurfaces()
}

function closeAction() {
  closeOpenSurfaces()
}

function closeConversation() {
  closeOpenSurfaces()
}
</script>

<style scoped>
.demo-page {
  min-height: 100vh;
  display: grid;
  place-items: start center;
  overflow: auto;
  background: #f5f1e7;
}
.demo-artboard {
  position: relative;
  width: min(100vw, 1568px, 156.331vh);
  min-width: 1180px;
  margin: 0;
  aspect-ratio: 1568 / 1003;
  overflow: hidden;
  isolation: isolate;
}
.demo-artboard__image {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: fill;
  user-select: none;
}
.demo-live-layer {
  position: absolute;
  z-index: 1;
  inset: 0;
  pointer-events: none;
  font-family: "Noto Serif SC", "Songti SC", serif;
}
.demo-live-path {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
}
.demo-live-path path {
  fill: none;
  stroke: #d96842;
  stroke-width: 3;
  stroke-dasharray: 10 9;
  opacity: .9;
  vector-effect: non-scaling-stroke;
  animation: demoPathFlow 3.5s linear infinite;
}
.demo-live-path circle {
  fill: #d96842;
  stroke: #fff7e9;
  stroke-width: 5;
  animation: demoPulse 1.6s ease-in-out infinite;
}
@keyframes demoPathFlow {
  to { stroke-dashoffset: -76; }
}
@keyframes demoPulse {
  0%, 100% { r: 8; opacity: 1; }
  50% { r: 13; opacity: .58; }
}
.demo-hotspot-layer { position: absolute; inset: 0; z-index: 2; }
.demo-hotspot { position: absolute; display: block; padding: 0; border: 0; border-radius: 5px; background: transparent; cursor: pointer; }
.demo-hotspot:hover, .demo-hotspot:focus-visible { outline: 2px solid rgba(220, 92, 50, .8); background: rgba(220, 92, 50, .08); }
.demo-hotspot--why { left: 60.7%; top: 9.6%; width: 12.4%; height: 6.2%; }
.demo-hotspot--confirm { left: 66.1%; top: 84%; width: 15.1%; height: 7.2%; }
.demo-hotspot--smaller { left: 66.1%; top: 91.7%; width: 15.1%; height: 6.2%; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }

.interaction-panel {
  position: absolute;
  z-index: 5;
  box-sizing: border-box;
  padding: 24px;
  background:
    radial-gradient(circle at 16% 0, rgba(217, 104, 66, .045), transparent 34%),
    #faf7ee;
  color: #173b31;
  font-family: "Noto Serif SC", "Songti SC", serif;
}
.interaction-panel--evidence {
  top: 7.15%;
  right: .05%;
  bottom: 20.35%;
  width: 23.9%;
  overflow-y: auto;
  border: 0;
  border-left: 1px solid rgba(23, 59, 49, .28);
  border-bottom: 1px solid rgba(23, 59, 49, .18);
  box-shadow: -12px 0 28px rgba(39, 45, 35, .075);
  animation: dockInRight 220ms ease-out;
}
.interaction-panel--action {
  left: 13.9%;
  right: 1.3%;
  bottom: 1.45%;
  height: 16.9%;
  display: grid;
  grid-template-columns: minmax(210px, .75fr) minmax(310px, 1.35fr) minmax(260px, .9fr);
  grid-template-rows: auto 1fr;
  column-gap: 28px;
  align-items: center;
  padding: 20px 38px 20px 26px;
  border: 1px solid rgba(23, 59, 49, .28);
  box-shadow: 0 -10px 30px rgba(39, 45, 35, .07);
  animation: dockInBottom 220ms ease-out;
}
.interaction-panel__close { position: absolute; right: 10px; top: 6px; border: 0; background: transparent; color: inherit; font-size: 24px; cursor: pointer; }
.interaction-panel > small { color: #d96842; font: 10px ui-monospace, monospace; letter-spacing: .15em; }
.interaction-panel h2 { margin: 7px 0 14px; font: 700 25px "Noto Serif SC", "Songti SC", serif; }
.interaction-panel > strong { display: block; margin-bottom: 8px; font-size: 17px; }
.interaction-panel > p { margin: 0 0 16px; color: #64756e; font-size: 12px; line-height: 1.7; }
.evidence-row { width: 100%; display: grid; grid-template-columns: auto 1fr auto; gap: 8px; align-items: center; margin-top: 8px; padding: 11px; border: 1px solid rgba(23,59,49,.18); background: rgba(255,253,247,.8); color: inherit; font: inherit; text-align: left; cursor: pointer; }
.evidence-row span { color: #849087; font-size: 9px; }
.evidence-row b { font-size: 11px; }
.evidence-row em { color: #d96842; font-size: 9px; font-style: normal; }
.evidence-row p { grid-column: 1 / -1; margin: 3px 0 0; padding-top: 8px; border-top: 1px dashed rgba(23,59,49,.16); color: #64756e; font-size: 10px; line-height: 1.6; }
.interaction-panel__rule { margin-top: 17px; padding-top: 13px; border-top: 1px solid rgba(23,59,49,.18); color: #d96842; font-size: 10px; line-height: 1.6; }
.interaction-panel__buttons { display: flex; gap: 9px; margin-top: 19px; }
.interaction-panel__buttons button { flex: 1; padding: 11px 12px; border: 1px solid #173b31; background: transparent; color: #173b31; font: inherit; cursor: pointer; }
.interaction-panel__buttons .interaction-panel__primary { border-color: #d96842; background: #d96842; color: white; }

.interaction-panel--action > small { grid-column: 1; grid-row: 1; align-self: end; }
.interaction-panel--action h2 { grid-column: 1; grid-row: 2; align-self: start; margin: 6px 0 0; font-size: 22px; }
.interaction-panel--action > p { grid-column: 2; grid-row: 1 / 3; align-self: center; margin: 0; padding-left: 24px; border-left: 1px solid rgba(23,59,49,.16); font-size: 13px; }
.interaction-panel--action .interaction-panel__buttons { grid-column: 3; grid-row: 1 / 3; flex-direction: column; align-self: center; margin: 0; }
.interaction-panel--action .interaction-panel__buttons button { width: 100%; min-height: 42px; }

.conversation-dialog { position: absolute; z-index: 5; left: 18.95%; right: 23.9%; top: 7.15%; bottom: 20.35%; display: grid; grid-template-rows: auto 1fr; min-width: 0; overflow: hidden; border: 0; border-right: 1px solid rgba(23,59,49,.2); border-bottom: 1px solid rgba(23,59,49,.18); background: #f6f0e6; box-shadow: 10px 0 28px rgba(26,38,32,.07); animation: workspaceIn 200ms ease-out; }
.conversation-dialog > header { display: flex; align-items: center; justify-content: space-between; padding: 14px 20px; border-bottom: 1px solid rgba(23,59,49,.18); }
.conversation-dialog > header div { display: grid; gap: 3px; }
.conversation-dialog > header small { color: #d96842; font: 10px ui-monospace, monospace; letter-spacing: .15em; }
.conversation-dialog > header strong { font-size: 18px; }
.conversation-dialog > header button { border: 0; background: transparent; color: #173b31; font-size: 26px; cursor: pointer; }
.conversation-dialog :deep(.chat-page) { box-sizing: border-box; width: 100%; height: 100%; min-height: 0; margin: 0; overflow: hidden; padding: 12px 16px 16px; }
.conversation-dialog :deep(.chat-shell) { height: 100%; min-height: 0; display: flex; flex-direction: column; gap: 10px; overflow: hidden; padding: 14px 16px; border: 0; border-radius: 0; background: transparent; box-shadow: none; }
.conversation-dialog :deep(.chat-shell__toolbar) { flex: 0 0 auto; }
.conversation-dialog :deep(.chat-list) { flex: 1 1 120px; min-height: 0; max-height: none; padding: 12px; }
.conversation-dialog :deep(.chat-composer) { flex: 0 0 auto; gap: 6px; padding: 10px 12px; border-radius: 18px; }
.conversation-dialog :deep(.chat-composer__input) { min-height: 72px; max-height: 88px; line-height: 1.55; }

@keyframes dockInRight {
  from { opacity: 0; transform: translateX(18px); }
}
@keyframes dockInBottom {
  from { opacity: 0; transform: translateY(14px); }
}
@keyframes workspaceIn {
  from { opacity: 0; transform: translateY(6px); }
}

@media (prefers-reduced-motion: reduce) {
  .demo-live-path path,
  .demo-live-path circle,
  .interaction-panel,
  .conversation-dialog { animation: none !important; }
}

@media (max-width: 1179px) {
  .demo-page { place-items: start; }
  .demo-artboard { min-width: 1180px; }
}
</style>
