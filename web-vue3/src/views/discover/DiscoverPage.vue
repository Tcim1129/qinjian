<template>
  <div class="discover-page">
    <div class="page-head discover-head">
      <p class="eyebrow">总览</p>
      <h2>全部功能</h2>
    </div>

    <section class="main-lines" aria-label="核心主线">
      <router-link
        v-for="item in mainLineActions"
        :key="item.to"
        :to="item.to"
        class="discover-entry"
        :class="[item.className, { 'discover-entry--primary': item.primary }]"
      >
        <div class="discover-entry__icon-shell" :class="item.iconShellClass">
          <component :is="item.icon" :size="22" class="discover-entry__icon" />
        </div>
        <div class="discover-entry__body">
          <span>{{ item.label }}</span>
          <strong>{{ item.title }}</strong>
        </div>
      </router-link>
    </section>

    <section class="growth-hub" aria-label="拓展入口">
      <div class="growth-grid">
        <router-link
          v-for="item in secondaryCards"
          :key="item.to"
          :to="item.to"
          class="growth-card"
          :class="['growth-card--compact', item.className]"
        >
          <div class="growth-card__icon-shell" :class="item.iconShellClass">
            <component :is="item.icon" :size="20" class="growth-card__icon" />
          </div>
          <div class="growth-card__body">
            <span>{{ item.label }}</span>
            <strong>{{ item.title }}</strong>
          </div>
        </router-link>
      </div>
    </section>
  </div>
</template>

<script setup>
import {
  PenLine,
  LineChart,
  Clock,
  UserRoundCheck,
  Users,
  MessageSquare,
  HeartPulse,
  Link2,
  MapPinned,
  SquareCheck,
  BookOpen,
  CircleUserRound,
  Star,
  SendHorizontal,
} from 'lucide-vue-next'

const primaryActions = [
  {
    to: '/checkin',
    label: '记录',
    title: '写下今天',
    icon: PenLine,
    iconShellClass: 'growth-card__icon-shell--peach',
    className: 'growth-card--peach',
    primary: true,
  },
  {
    to: '/report',
    label: '简报',
    title: '回顾近况',
    icon: LineChart,
    iconShellClass: 'growth-card__icon-shell--mint',
    className: 'growth-card--mint',
    primary: false,
  },
  {
    to: '/timeline',
    label: '关系日历',
    title: '回看往事',
    icon: Clock,
    iconShellClass: 'growth-card__icon-shell--gold',
    className: 'growth-card--gold',
    primary: false,
  },
]

const featuredCards = [
  {
    to: '/community',
    label: '交流社区',
    title: '看看大家怎么说',
    icon: MessageSquare,
    iconShellClass: 'growth-card__icon-shell--peach',
    className: 'growth-card--peach',
  },
  {
    to: '/alignment',
    label: '双视角',
    title: '听听彼此的想法',
    icon: Users,
    iconShellClass: 'growth-card__icon-shell--sky',
    className: 'growth-card--sky',
  },
  {
    to: '/pair',
    label: '我的关系',
    title: '管理关系',
    icon: UserRoundCheck,
    iconShellClass: 'growth-card__icon-shell--mint',
    className: 'growth-card--mint',
  },
]

const mainLineActions = [
  ...primaryActions,
  ...featuredCards,
]

const secondaryCards = [
  {
    to: '/health-test',
    label: '关系体检',
    title: '看看相处状态',
    icon: HeartPulse,
    iconShellClass: 'growth-card__icon-shell--rose',
    className: 'growth-card--rose',
  },
  {
    to: '/attachment-test',
    label: '依恋测评',
    title: '了解相处习惯',
    icon: Link2,
    iconShellClass: 'growth-card__icon-shell--sky',
    className: 'growth-card--sky',
  },
  {
    to: '/longdistance',
    label: '异地陪伴',
    title: '远一点，也陪伴',
    icon: MapPinned,
    iconShellClass: 'growth-card__icon-shell--mint',
    className: 'growth-card--mint',
  },
  {
    to: '/challenges',
    label: '每日安排',
    title: '一起做件小事',
    icon: SquareCheck,
    iconShellClass: 'growth-card__icon-shell--peach',
    className: 'growth-card--peach',
  },
  {
    to: '/courses',
    label: '沟通课程',
    title: '学着好好说话',
    icon: BookOpen,
    iconShellClass: 'growth-card__icon-shell--iris',
    className: 'growth-card--iris',
  },
  {
    to: '/experts',
    label: '咨询',
    title: '了解咨询',
    icon: CircleUserRound,
    iconShellClass: 'growth-card__icon-shell--violet',
    className: 'growth-card--violet',
  },
  {
    to: '/membership',
    label: '会员',
    title: '查看权益',
    icon: Star,
    iconShellClass: 'growth-card__icon-shell--gold',
    className: 'growth-card--gold',
  },
  {
    to: '/message-simulation',
    label: '发前看看',
    title: '换个说法试试',
    icon: SendHorizontal,
    iconShellClass: 'growth-card__icon-shell--peach',
    className: 'growth-card--peach',
  },
]
</script>

<style scoped>
.discover-page {
  width: min(var(--content-max), calc(100% - 32px));
  margin: 0 auto;
  padding-bottom: 28px;
}

.discover-head {
  width: 100%;
}

.main-lines {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.discover-entry,
.growth-card {
  display: grid;
  place-items: center;
  gap: 14px;
  border: 1px solid rgba(68, 52, 40, 0.08);
  border-radius: 26px;
  color: var(--ink);
  text-align: center;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(255, 251, 247, 0.88));
  box-shadow: 0 12px 28px rgba(91, 67, 51, 0.045);
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.discover-entry {
  min-height: 156px;
  padding: 22px 18px;
}

.discover-entry--primary {
  place-items: center;
}

.growth-hub {
  margin-top: 12px;
}

.growth-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.growth-card--featured {
  min-height: 148px;
  padding: 20px 18px;
}

.growth-card--compact {
  min-height: 132px;
  padding: 18px 16px;
}

.discover-entry:hover,
.growth-card:hover {
  transform: translateY(-2px);
  border-color: rgba(189, 75, 53, 0.22);
  box-shadow: 0 16px 34px rgba(91, 67, 51, 0.06);
}

.discover-entry__icon-shell,
.growth-card__icon-shell {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 13px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
}

.growth-card__icon-shell {
  width: 34px;
  height: 34px;
  border-radius: 12px;
}

.discover-entry__icon,
.growth-card__icon {
  stroke-width: 2.2;
}

.discover-entry__body,
.growth-card__body {
  display: grid;
  gap: 9px;
  justify-items: center;
}

.discover-entry__body span,
.growth-card__body span {
  display: block;
  font-size: 15px;
  font-weight: 800;
  line-height: 1.2;
}

.discover-entry__body strong,
.growth-card__body strong {
  display: block;
  color: var(--ink-soft);
  font-size: 15px;
  font-weight: 800;
  line-height: 1.45;
}

.growth-card--peach {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(255, 246, 240, 0.9));
}

.growth-card--mint {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(240, 251, 246, 0.9));
}

.growth-card--gold {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(255, 248, 237, 0.9));
}

.growth-card--rose {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(255, 244, 246, 0.9));
}

.growth-card--sky {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(242, 247, 255, 0.9));
}

.growth-card--iris {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(243, 244, 255, 0.9));
}

.growth-card--violet {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 243, 255, 0.9));
}

.growth-card__icon-shell--peach {
  background: linear-gradient(180deg, rgba(255, 225, 206, 0.96), rgba(255, 240, 232, 0.9));
  color: #d27c4e;
}

.growth-card__icon-shell--mint {
  background: linear-gradient(180deg, rgba(193, 246, 225, 0.96), rgba(221, 250, 237, 0.9));
  color: #329874;
}

.growth-card__icon-shell--gold {
  background: linear-gradient(180deg, rgba(255, 214, 129, 0.96), rgba(255, 235, 187, 0.9));
  color: #c8861f;
}

.growth-card__icon-shell--rose {
  background: linear-gradient(180deg, rgba(255, 214, 225, 0.96), rgba(255, 233, 240, 0.9));
  color: #db6d92;
}

.growth-card__icon-shell--sky {
  background: linear-gradient(180deg, rgba(204, 228, 255, 0.96), rgba(228, 240, 255, 0.9));
  color: #5b8fe6;
}

.growth-card__icon-shell--iris {
  background: linear-gradient(180deg, rgba(214, 217, 255, 0.96), rgba(235, 237, 255, 0.9));
  color: #6672d6;
}

.growth-card__icon-shell--violet {
  background: linear-gradient(180deg, rgba(234, 217, 255, 0.96), rgba(242, 232, 255, 0.9));
  color: #8a63cf;
}

.growth-card--peach .discover-entry__body span,
.growth-card--peach .growth-card__body span {
  color: #ce7a4f;
}

.growth-card--mint .discover-entry__body span,
.growth-card--mint .growth-card__body span {
  color: #318b6c;
}

.growth-card--gold .discover-entry__body span,
.growth-card--gold .growth-card__body span {
  color: #bc8221;
}

.growth-card--rose .growth-card__body span {
  color: #d06a89;
}

.growth-card--sky .discover-entry__body span,
.growth-card--sky .growth-card__body span {
  color: #436eae;
}

.growth-card--iris .growth-card__body span {
  color: #6876cf;
}

.growth-card--violet .growth-card__body span {
  color: #8660c6;
}

@media (max-width: 900px) {
  .main-lines,
  .growth-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 520px) {
  .discover-page {
    width: min(100% - 20px, var(--content-max));
  }

  .main-lines,
  .growth-grid {
    gap: 10px;
  }

  .discover-entry--primary {
    place-items: center;
  }

  .discover-entry,
  .growth-card--featured,
  .growth-card--compact {
    min-height: 112px;
    padding: 14px 12px;
    border-radius: 22px;
  }

  .discover-entry__icon-shell,
  .growth-card__icon-shell {
    width: 32px;
    height: 32px;
    border-radius: 11px;
  }

  .discover-entry__body,
  .growth-card__body {
    gap: 6px;
  }

  .discover-entry__body span,
  .growth-card__body span {
    font-size: 14px;
  }

  .discover-entry__body strong,
  .growth-card__body strong {
    font-size: 14px;
    line-height: 1.4;
  }
}
</style>
