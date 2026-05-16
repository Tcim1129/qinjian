import { shallowRef } from 'vue'

const HOME_ROUTE = '/pages/index/index'

function normalizePath(rawPath = '') {
  const [pathOnly] = String(rawPath || '').split('?')
  if (!pathOnly || pathOnly === '/' || pathOnly === '/index.html') {
    return HOME_ROUTE
  }
  return pathOnly.startsWith('/') ? pathOnly : `/${pathOnly}`
}

export const currentRoutePath = shallowRef(normalizePath(window.location.pathname))
export const routeStack = shallowRef([currentRoutePath.value])

window.history.replaceState({ qjPath: currentRoutePath.value }, '', currentRoutePath.value)

export function getCurrentRoutePath() {
  return currentRoutePath.value
}

export function getRouteStack() {
  return routeStack.value.slice()
}

export function relaunchRoute(url) {
  const nextPath = normalizePath(url)
  routeStack.value = [nextPath]
  window.history.replaceState({ qjPath: nextPath }, '', nextPath)
  currentRoutePath.value = nextPath
  window.scrollTo({ top: 0, behavior: 'auto' })
}

export function replaceRoute(url) {
  const nextPath = normalizePath(url)
  const nextStack = routeStack.value.slice()
  if (nextStack.length) {
    nextStack[nextStack.length - 1] = nextPath
  } else {
    nextStack.push(nextPath)
  }
  routeStack.value = nextStack
  window.history.replaceState({ qjPath: nextPath }, '', nextPath)
  currentRoutePath.value = nextPath
  window.scrollTo({ top: 0, behavior: 'auto' })
}

export function pushRoute(url) {
  const nextPath = normalizePath(url)
  routeStack.value = [...routeStack.value, nextPath]
  window.history.pushState({ qjPath: nextPath }, '', nextPath)
  currentRoutePath.value = nextPath
  window.scrollTo({ top: 0, behavior: 'auto' })
}

export function popRoute(delta = 1) {
  const steps = Math.max(1, Number(delta) || 1)
  const currentStack = routeStack.value.slice()

  if (currentStack.length <= 1) {
    relaunchRoute(HOME_ROUTE)
    return HOME_ROUTE
  }

  currentStack.splice(-steps, steps)
  const nextPath = currentStack[currentStack.length - 1] || HOME_ROUTE
  routeStack.value = currentStack.length ? currentStack : [nextPath]
  window.history.replaceState({ qjPath: nextPath }, '', nextPath)
  currentRoutePath.value = nextPath
  window.scrollTo({ top: 0, behavior: 'auto' })
  return nextPath
}

window.addEventListener('popstate', () => {
  const nextPath = normalizePath(window.location.pathname)
  const currentStack = routeStack.value.slice()
  const existingIndex = currentStack.lastIndexOf(nextPath)

  if (existingIndex >= 0) {
    routeStack.value = currentStack.slice(0, existingIndex + 1)
  } else {
    routeStack.value = [...currentStack, nextPath]
  }

  currentRoutePath.value = nextPath
})
