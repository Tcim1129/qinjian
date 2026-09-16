<template>
  <div class="relationship-tree" :class="{ 'relationship-tree--resting': resting }">
    <svg class="tree-art" viewBox="0 0 320 320" role="img" aria-label="关系树，枝叶随风轻轻摆动">
      <ellipse cx="160" cy="284" rx="88" ry="13" fill="#657951" opacity=".09" />
      <path d="M48 286 Q109 271 163 283 Q213 273 272 286" fill="none" stroke="#a8b29a" stroke-width="1.2" />
      <g class="tree-body">
        <g class="canopy canopy--back">
          <path d="M66 188 C37 180 35 145 58 129 C44 105 65 81 89 83 C87 58 113 42 139 53 C158 27 197 37 209 60 C236 53 259 76 252 101 C282 109 286 140 267 158 C279 186 246 210 223 199 C204 220 173 213 162 202 C132 225 102 211 101 199 C84 208 70 200 66 188Z" fill="#78916b" />
          <path d="M55 151 C81 120 111 116 135 129 C160 90 202 86 231 103 C246 118 252 153 238 169 C213 204 181 186 160 193 C130 211 85 196 55 174Z" fill="#587455" opacity=".75" />
        </g>
        <g class="branches" fill="none" stroke-linecap="round">
          <path d="M145 284 C155 251 153 230 155 199 C146 169 138 143 144 112 C151 149 157 167 168 187 C177 164 194 146 210 133 C192 155 181 179 172 209 C165 238 172 266 180 284 C166 280 157 278 145 284Z" fill="#8b6849" stroke="none" />
          <path d="M160 221 Q124 201 98 158 M158 203 Q180 189 213 181 M146 159 Q116 145 96 114 M171 185 Q171 130 189 100" stroke="#8b6849" stroke-width="7" />
          <path d="M124 192 Q109 185 86 184 M127 186 Q132 159 123 137 M183 179 Q208 164 225 144 M171 147 Q154 126 158 102" stroke="#8b6849" stroke-width="3.5" />
          <path d="M156 276 Q163 242 160 223 M147 151 Q151 171 159 187" stroke="#b59268" stroke-width="2" opacity=".75" />
          <path d="M155 278 Q144 283 126 287 M169 279 Q184 283 192 287" stroke="#8b6849" stroke-width="3" />
        </g>
        <g class="canopy canopy--front">
          <g v-for="(branch, index) in foliage" :key="index" :transform="`translate(${branch.x} ${branch.y}) rotate(${branch.angle}) scale(${branch.scale})`">
            <g class="leaf-spray" :style="{ '--delay': `${index * -.53}s` }">
              <path d="M0 25 Q-3 -3 2 -24" fill="none" stroke="#667c50" stroke-width="1.1" />
              <path d="M0 14 C-24 16 -28 0 -28 -10 C-9 -12 2 0 0 14Z" :fill="branch.color" />
              <path d="M1 3 C9 -18 26 -17 33 -13 C28 6 15 12 1 3Z" :fill="branch.color" />
              <path d="M1 -10 C-16 -11 -20 -28 -15 -36 C2 -32 8 -21 1 -10Z" :fill="branch.light" />
              <path d="M2 -24 C0 -39 12 -46 22 -45 C23 -30 16 -21 2 -24Z" :fill="branch.light" />
              <path d="M-2 11 L-22 -5 M6 1 L26 -10" fill="none" stroke="#f2edcb" stroke-width=".7" opacity=".45" />
            </g>
          </g>
        </g>
      </g>
      <g fill="#a1ad83"><path d="M89 286 Q77 270 75 279 Q78 286 89 286 M229 284 Q241 271 243 279 Q239 286 229 284" /><path d="M209 286 Q207 276 202 276 L209 286" /></g>
    </svg>
    <TransitionGroup name="harvest" tag="div" class="tree-orbs" aria-label="可收取的成长值">
      <button v-for="node in nodes.filter(item => !item.collected)" :key="node.key"
        class="tree-orb" :class="[`tree-orb--${node.key}`, { 'tree-orb--locked': !node.available }]"
        type="button" :disabled="!node.available || Boolean(collectingKey)"
        :aria-label="node.available ? `收取${node.label}，成长值${node.value}` : `${node.label}，${node.hint}`"
        @click="$emit('collect', node)">
        <strong>{{ collectingKey === node.key ? '…' : node.value }}</strong><span>{{ node.label }}</span>
      </button>
    </TransitionGroup>
    <span v-if="feedback" :key="feedback.id" class="tree-gain" :class="`tree-orb--${feedback.key}`" aria-hidden="true">+{{ feedback.points }}</span>
    <span class="tree-announcement" role="status">{{ feedback ? `已收取，成长值增加 ${feedback.points}` : '' }}</span>
  </div>
</template>

<script setup>
defineProps({ nodes: { type: Array, default: () => [] }, collectingKey: { type: String, default: '' }, feedback: { type: Object, default: null }, resting: Boolean })
defineEmits(['collect'])
const foliage = [
  { x: 72, y: 139, angle: -48, scale: .85, color: '#8fa77b', light: '#b4c695' },
  { x: 91, y: 105, angle: -24, scale: .85, color: '#8ea77a', light: '#bacb9b' },
  { x: 128, y: 85, angle: -15, scale: .86, color: '#9caf7e', light: '#c0ce9d' },
  { x: 170, y: 74, angle: 25, scale: .8, color: '#a8ba84', light: '#c4d3a1' },
  { x: 212, y: 89, angle: 54, scale: .8, color: '#8ba579', light: '#b3c792' },
  { x: 242, y: 124, angle: 70, scale: .79, color: '#95ac7c', light: '#b9c996' },
  { x: 235, y: 164, angle: 107, scale: .8, color: '#829b6c', light: '#a4b982' },
  { x: 195, y: 153, angle: 37, scale: .85, color: '#92ac76', light: '#afc08b' },
  { x: 161, y: 115, angle: -30, scale: .72, color: '#a0b584', light: '#c5d3a1' },
  { x: 127, y: 150, angle: -64, scale: .84, color: '#7f9b6d', light: '#a4ba8a' },
  { x: 83, y: 182, angle: -110, scale: .7, color: '#91a778', light: '#acbb89' },
  { x: 185, y: 193, angle: 105, scale: .68, color: '#799765', light: '#a1b680' },
]
</script>

<style scoped>
.relationship-tree { position: relative; isolation: isolate; aspect-ratio: 1; margin: 8px 0 14px; border-radius: 16px; background: radial-gradient(ellipse at 50% 40%, #f4f1da90, transparent 69%); }
.tree-art { display: block; width: 100%; height: 100%; overflow: visible; }
.tree-body { transform-origin: 160px 282px; animation: tree-sway 9s ease-in-out infinite; }
.leaf-spray { transform-origin: 0 20px; animation: leaf-sway 6s ease-in-out infinite; animation-delay: var(--delay); }
.relationship-tree--resting .canopy { filter: saturate(.7); }
.tree-orbs { position: absolute; inset: 0; pointer-events: none; }
.tree-orb { position: absolute; pointer-events: auto; display: flex; flex-direction: column; align-items: center; justify-content: center; width: 58px; height: 58px; padding: 4px; border: 1px solid #ffffffe0; border-radius: 50%; color: #654f27; background: radial-gradient(circle at 35% 25%, #fffdf1, #f0daa1d9 65%, #d8bc7d); box-shadow: 0 4px 16px #725e2820, inset 0 0 10px #fff8d3; animation: orb-float 4.8s ease-in-out infinite; }
.tree-orb strong { font-size: 18px; line-height: 1.2; font-weight: 650; }.tree-orb span { font-size: 10px; line-height: 1.5; }
.tree-orb:hover:not(:disabled) { filter: brightness(1.07); box-shadow: 0 0 0 5px #edd79d35, 0 5px 20px #725e2830; }
.tree-orb:focus-visible { outline: 2px solid #657d49; outline-offset: 4px; }
.tree-orb--my_record { left: 9%; top: 39%; }
.tree-orb--partner_record { right: 8%; top: 25%; animation-delay: -.8s; }
.tree-orb--small_repair { left: 47%; top: 58%; animation-delay: -1.7s; }
.tree-orb--locked { opacity: .55; color: #636d5c; background: #eef0e7df; box-shadow: none; animation: none; }
.harvest-leave-active { transition: opacity .8s ease, scale .8s ease, filter .8s ease; pointer-events: none; animation-play-state: paused; }
.harvest-leave-to { opacity: 0; scale: .6; filter: blur(4px); }
.tree-gain { position: absolute; z-index: 3; width: 58px; text-align: center; padding-top: 10px; pointer-events: none; font-size: 24px; font-weight: 700; color: #57723f; text-shadow: 0 1px 8px #fff; animation: gain-rise 1.3s ease-out both; }
.tree-announcement { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
@keyframes tree-sway { 0%,100% { transform: rotate(-.65deg); } 50% { transform: rotate(.65deg); } }
@keyframes leaf-sway { 0%,100% { transform: rotate(-1.7deg); } 50% { transform: rotate(1.7deg); } }
@keyframes orb-float { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-5px); } }
@keyframes gain-rise { 0% { opacity: 0; transform: translateY(0); } 20% { opacity: 1; } 100% { opacity: 0; transform: translateY(-42px); } }
@media (prefers-reduced-motion: reduce) { .tree-body, .leaf-spray, .tree-orb { animation: none; } .harvest-leave-active { transition: opacity .2s; } .harvest-leave-to { scale: 1; filter: none; } .tree-gain { animation-name: gain-fade; } @keyframes gain-fade { 0%,80% { opacity: 1; } 100% { opacity: 0; } } }
</style>
