/**
 * 通用工具函数模块
 */

/**
 * 数字补零
 * @param {number} n - 数字
 * @returns {string}
 */
function padZero(n) {
  return n < 10 ? '0' + n : '' + n
}

/**
 * 格式化日期为 YYYY-MM-DD
 * @param {Date|string|number} date - 日期对象或可解析的日期值
 * @returns {string}
 */
function formatDate(date) {
  if (!(date instanceof Date)) {
    date = new Date(date)
  }
  const year = date.getFullYear()
  const month = padZero(date.getMonth() + 1)
  const day = padZero(date.getDate())
  return `${year}-${month}-${day}`
}

/**
 * 格式化日期为 YYYY-MM-DD HH:mm
 * @param {Date|string|number} date - 日期对象或可解析的日期值
 * @returns {string}
 */
function formatTime(date) {
  if (!(date instanceof Date)) {
    date = new Date(date)
  }
  const year = date.getFullYear()
  const month = padZero(date.getMonth() + 1)
  const day = padZero(date.getDate())
  const hour = padZero(date.getHours())
  const minute = padZero(date.getMinutes())
  return `${year}-${month}-${day} ${hour}:${minute}`
}

/**
 * 格式化为相对时间
 * @param {string} dateStr - 日期字符串
 * @returns {string} 相对时间描述
 */
function formatRelativeTime(dateStr) {
  if (!dateStr) return ''

  const now = Date.now()
  const target = new Date(dateStr).getTime()
  const diff = now - target

  // 无效日期或未来时间
  if (isNaN(diff) || diff < 0) return ''

  const MINUTE = 60 * 1000
  const HOUR = 60 * MINUTE
  const DAY = 24 * HOUR

  if (diff < MINUTE) {
    return '刚刚'
  } else if (diff < HOUR) {
    return Math.floor(diff / MINUTE) + '分钟前'
  } else if (diff < DAY) {
    return Math.floor(diff / HOUR) + '小时前'
  } else if (diff < 30 * DAY) {
    return Math.floor(diff / DAY) + '天前'
  } else {
    return formatDate(new Date(target))
  }
}

// 心情等级配置
const MOOD_CONFIG = {
  1: { emoji: '😢', text: '低落' },
  2: { emoji: '😐', text: '一般' },
  3: { emoji: '🙂', text: '不错' },
  4: { emoji: '😊', text: '很好' }
}

/**
 * 获取心情等级对应的表情
 * @param {number} level - 心情等级 1-4
 * @returns {string} 表情符号
 */
function getMoodEmoji(level) {
  const config = MOOD_CONFIG[level]
  return config ? config.emoji : ''
}

/**
 * 获取心情等级对应的文字描述
 * @param {number} level - 心情等级 1-4
 * @returns {string} 心情文字
 */
function getMoodText(level) {
  const config = MOOD_CONFIG[level]
  return config ? config.text : ''
}

// 亲密树成长等级名称
const TREE_LEVELS = {
  1: '种子',
  2: '嫩芽',
  3: '树苗',
  4: '小树',
  5: '花开'
}

/**
 * 获取亲密树等级名称
 * @param {number} level - 树等级 1-5
 * @returns {string} 等级名称
 */
function getTreeLevelName(level) {
  return TREE_LEVELS[level] || ''
}

/**
 * 节流函数
 * 在指定时间间隔内，最多执行一次目标函数
 * @param {Function} fn - 目标函数
 * @param {number} delay - 间隔时间（毫秒）
 * @returns {Function}
 */
function throttle(fn, delay) {
  let lastTime = 0
  let timer = null

  return function (...args) {
    const now = Date.now()
    const remaining = delay - (now - lastTime)

    if (remaining <= 0) {
      // 已超过间隔，立即执行
      if (timer) {
        clearTimeout(timer)
        timer = null
      }
      lastTime = now
      fn.apply(this, args)
    } else if (!timer) {
      // 未超过间隔且无待执行定时器，设置尾部调用
      timer = setTimeout(() => {
        lastTime = Date.now()
        timer = null
        fn.apply(this, args)
      }, remaining)
    }
  }
}

/**
 * 防抖函数
 * 在最后一次调用后等待指定时间再执行
 * @param {Function} fn - 目标函数
 * @param {number} delay - 等待时间（毫秒）
 * @returns {Function}
 */
function debounce(fn, delay) {
  let timer = null

  return function (...args) {
    if (timer) {
      clearTimeout(timer)
    }
    timer = setTimeout(() => {
      timer = null
      fn.apply(this, args)
    }, delay)
  }
}

module.exports = {
  formatDate,
  formatTime,
  formatRelativeTime,
  getMoodEmoji,
  getMoodText,
  getTreeLevelName,
  throttle,
  debounce
}
