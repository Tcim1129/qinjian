function crisisLevelLabel(level) {
  const map = {
    none: '平稳',
    mild: '可以留意',
    moderate: '需要放慢一点',
    severe: '先照顾安全',
  }
  return map[String(level || '').toLowerCase()] || '待整理'
}

function formatMilestoneDate(value) {
  if (!value) return ''
  const [year, month, day] = String(value).slice(0, 10).split('-')
  if (!year || !month || !day) return ''
  return `${month}月${day}日`
}

function pairedStatusText(todayStatus = {}) {
  const myDone = Boolean(todayStatus.my_done)
  const partnerDone = Boolean(todayStatus.partner_done)
  if (myDone && partnerDone) return '今天都写了'
  if (myDone) return '你已写，对方待同步'
  if (partnerDone) return '对方已写，你待补充'
  return '今天都还没写'
}

function normalizeReportStatus(value, hasReport = false) {
  const status = String(value || '').toLowerCase()
  if (status) return status
  return hasReport ? 'completed' : 'idle'
}

function resolveReportState(todayStatus = {}) {
  return {
    pairReportStatus: normalizeReportStatus(todayStatus.report_status, todayStatus.has_report),
    soloReportStatus: normalizeReportStatus(todayStatus.solo_report_status, todayStatus.has_solo_report),
  }
}

function reportStatusLabel(status, { solo = false } = {}) {
  if (status === 'completed') return solo ? '你的这一份已整理' : '已整理'
  if (status === 'pending') return solo ? '你的这一份整理中' : '整理中'
  return '记录后可整理'
}

function focusBlock({ relationshipView, todayStatus, tasks, crisis, primaryAction }) {
  const pendingTasks = tasks.filter((item) => item.status !== 'completed')
  if (primaryAction.route === '/report') {
    if (primaryAction.reportState === 'pending') {
      return {
        title: primaryAction.isSoloReport ? '先看你的这一份正在整理' : '先看这一期正在整理',
        detail: relationshipView.kind === 'paired'
          ? (todayStatus.partner_done
            ? '两边的记录已经收到了，亲健正在整理这一期简报。'
            : '你的记录已经收到了，亲健正在先整理你这一份。')
          : '今天这条记录已经收到了，亲健正在整理重点和下一步。',
      }
    }

    return {
      title: primaryAction.isSoloReport ? '先看你的这一份简报' : '先看这一期简报',
      detail: relationshipView.kind === 'paired'
        ? '这期简报可以看了。'
        : '你的这一份简报可以看了。',
    }
  }

  if (pendingTasks.length > 0) {
    const relationHint = relationshipView.kind === 'paired'
      ? (todayStatus.partner_done ? '对方已经写了，可以接着做。' : '对方还没写，先做轻一点的一步。')
      : '先把今天最关键的一步做完。'
    return {
      title: '先把这一步做完',
      detail: relationHint,
    }
  }

  if (relationshipView.kind === 'paired') {
    return {
      title: '先看关系状态',
      detail: `当前关系信号是${crisisLevelLabel(crisis.crisis_level)}，先别急着把所有问题一次说完。`,
    }
  }

  return {
    title: '先记下今天发生的事',
    detail: '现在还没有可同步的关系数据，先把今天发生的事实写下来就够了。',
  }
}

function buildTodoItems({ tasks = [], primaryAction, relationshipView }) {
  const pendingTasks = tasks
    .filter((item) => item.status !== 'completed')
    .slice(0, 3)
    .map((item) => ({
      label: item.title || '今天的小动作',
      note: item.description || '先做一件足够轻的小事。',
    }))

  if (pendingTasks.length > 0) return pendingTasks

  if (primaryAction.route === '/report') {
    return [
      {
        label: primaryAction.buttonLabel,
        note: primaryAction.reportState === 'pending'
          ? '亲健正在整理这一期，等它出来后再决定下一步。'
          : '先把这一期看完，再决定还要不要继续补充。',
      },
    ]
  }

  if (primaryAction.route === '/pair') {
    return [
      {
        label: primaryAction.buttonLabel,
        note: '先把这段关系推进到下一步，再决定后面的动作。',
      },
    ]
  }

  return [
    {
      label: relationshipView.kind === 'paired' ? '去记录页写下今天的情况' : '去记录页写下今天的事',
      note: relationshipView.kind === 'paired'
        ? '先把今天的情况写下来，再看后面的动作。'
        : '先把事实写下来，再决定要不要继续展开。',
    },
  ]
}

function buildMilestoneItems(milestones = []) {
  const items = milestones
    .slice()
    .sort((a, b) => String(b.date || '').localeCompare(String(a.date || '')))
    .slice(0, 3)
    .map((item) => ({
      label: item.title || '最近节点',
      note: formatMilestoneDate(item.date) || '已记录',
    }))

  if (items.length > 0) return items

  return [
    {
      label: '还没有最近节点',
      note: '之后补上的纪念日和关键时刻，会进关系日历。',
    },
  ]
}

function buildPrimaryAction({ relationshipView, todayStatus, tasks }) {
  const pendingTasks = tasks.filter((item) => item.status !== 'completed')
  const firstPendingTask = pendingTasks[0]
  const myDone = Boolean(todayStatus.my_done)
  const partnerDone = Boolean(todayStatus.partner_done)
  const { pairReportStatus, soloReportStatus } = resolveReportState(todayStatus)

  if (!myDone) {
    return {
      label: '去记录页',
      buttonLabel: '开始今日记录',
      route: '/checkin',
      slipLabel: relationshipView.kind === 'paired'
        ? '先去记录页写下今天的情况'
        : '先去记录页写下今天发生的事',
      actionKind: 'checkin',
    }
  }

  if (pairReportStatus === 'completed') {
    return {
      label: '打开简报',
      buttonLabel: '打开今日简报',
      route: '/report',
      slipLabel: '这一期简报已经整理好了',
      reportState: 'completed',
      actionKind: 'report',
      isSoloReport: false,
    }
  }

  if (pairReportStatus === 'pending') {
    return {
      label: '打开简报',
      buttonLabel: '查看整理进度',
      route: '/report',
      slipLabel: '这一期简报正在整理',
      reportState: 'pending',
      actionKind: 'report',
      isSoloReport: false,
    }
  }

  if (relationshipView.kind === 'paired' && !partnerDone && soloReportStatus === 'completed') {
    return {
      label: '打开简报',
      buttonLabel: '看我的简报',
      route: '/report',
      slipLabel: '你的这一份已经整理好了',
      reportState: 'completed',
      actionKind: 'report',
      isSoloReport: true,
    }
  }

  if (relationshipView.kind === 'paired' && !partnerDone && soloReportStatus === 'pending') {
    return {
      label: '打开简报',
      buttonLabel: '查看整理进度',
      route: '/report',
      slipLabel: '你的这一份正在整理',
      reportState: 'pending',
      actionKind: 'report',
      isSoloReport: true,
    }
  }

  if (pendingTasks.length > 0) {
    const nextLabel = firstPendingTask?.title || '继续下一步'

    return {
      label: '继续下一步',
      buttonLabel: nextLabel,
      route: '/challenges',
      slipLabel: `先继续这一步：${nextLabel}`,
      actionKind: 'task',
    }
  }

  if (relationshipView.kind === 'pending') {
    return {
      label: '去关系页',
      buttonLabel: '继续关系设置',
      route: '/pair',
      slipLabel: '先把邀请码发出去',
      actionKind: 'pair',
    }
  }

  if (relationshipView.kind === 'paired') {
    if (partnerDone) {
      return {
        label: '打开简报',
        buttonLabel: '去看简报进度',
        route: '/report',
        slipLabel: '两边都写完了，去看这一期简报',
        reportState: 'pending',
        actionKind: 'report',
        isSoloReport: false,
      }
    }

    return {
      label: '去关系页',
      buttonLabel: '查看关系状态',
      route: '/pair',
      slipLabel: '对方还没同步，先看关系状态',
      actionKind: 'pair',
    }
  }

  return {
    label: '继续整理',
    buttonLabel: '继续记录',
    route: '/checkin',
    slipLabel: '需要补充时，再去记录页继续写',
    actionKind: 'checkin',
  }
}

export function buildHomeOverview({
  relationshipView = { kind: 'solo', relationLabel: '单人整理' },
  snapshot = {},
  crisis = {},
  tasks = [],
  milestones = [],
} = {}) {
  const todayStatus = snapshot?.todayStatus || {}
  const primaryAction = buildPrimaryAction({
    relationshipView,
    todayStatus,
    tasks,
  })
  const { pairReportStatus, soloReportStatus } = resolveReportState(todayStatus)

  return {
    primaryAction,
    focus: focusBlock({
      relationshipView,
      todayStatus,
      tasks,
      crisis,
      primaryAction,
    }),
    todoItems: buildTodoItems({
      tasks,
      primaryAction,
      relationshipView,
    }),
    milestoneItems: buildMilestoneItems(milestones),
    statusItems: [
      {
        label: relationshipView.kind === 'paired' ? '今天进度' : '今天状态',
        value: relationshipView.kind === 'paired'
          ? pairedStatusText(todayStatus)
          : (todayStatus.my_done ? '已经开始' : '今天还没开始'),
      },
      {
        label: '简报',
        value: relationshipView.kind === 'paired' && pairReportStatus === 'idle' && !todayStatus.partner_done
          ? reportStatusLabel(soloReportStatus, { solo: true })
          : reportStatusLabel(pairReportStatus),
      },
      {
        label: relationshipView.kind === 'paired' ? '关系' : '模式',
        value: relationshipView.relationLabel || '单人整理',
      },
    ],
  }
}
