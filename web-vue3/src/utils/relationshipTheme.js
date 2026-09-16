const STORAGE_KEY = 'qj_relationship_space_theme'

export const DEFAULT_RELATIONSHIP_SPACE_THEME = 'classic'

export const RELATIONSHIP_SPACE_THEMES = [
  {
    value: 'classic',
    label: '经典暖光',
    shortLabel: '经典',
    description: '浅色、温柔、最干净。',
  },
  {
    value: 'stardust',
    label: '星尘微光',
    shortLabel: '星尘',
    description: '保留浅色基底，加入轻粒子和呼吸光晕。',
  },
  {
    value: 'engine',
    label: '引擎聚焦',
    shortLabel: '引擎',
    description: '双核更亮，粒子更明显，聚焦时更有推进感。',
  },
]

const THEME_VALUES = new Set(RELATIONSHIP_SPACE_THEMES.map((item) => item.value))

function getLocalStorage() {
  if (typeof window === 'undefined') return null
  return window.localStorage
}

export function normalizeRelationshipSpaceTheme(value) {
  const normalized = String(value || '').trim().toLowerCase()
  return THEME_VALUES.has(normalized) ? normalized : DEFAULT_RELATIONSHIP_SPACE_THEME
}

export function loadStoredRelationshipSpaceTheme(storage = getLocalStorage()) {
  if (!storage) return DEFAULT_RELATIONSHIP_SPACE_THEME
  return normalizeRelationshipSpaceTheme(storage.getItem(STORAGE_KEY))
}

export function saveStoredRelationshipSpaceTheme(theme, storage = getLocalStorage()) {
  const normalized = normalizeRelationshipSpaceTheme(theme)
  if (storage) {
    storage.setItem(STORAGE_KEY, normalized)
  }
  return normalized
}

export function resolveRelationshipSpaceTheme(profileTheme, storage = getLocalStorage()) {
  const normalizedProfileTheme = normalizeRelationshipSpaceTheme(profileTheme)
  if (profileTheme && normalizedProfileTheme !== DEFAULT_RELATIONSHIP_SPACE_THEME) {
    return normalizedProfileTheme
  }

  if (profileTheme === DEFAULT_RELATIONSHIP_SPACE_THEME) {
    return DEFAULT_RELATIONSHIP_SPACE_THEME
  }

  return loadStoredRelationshipSpaceTheme(storage)
}

export function getRelationshipThemeOption(theme) {
  const normalized = normalizeRelationshipSpaceTheme(theme)
  return RELATIONSHIP_SPACE_THEMES.find((item) => item.value === normalized) || RELATIONSHIP_SPACE_THEMES[0]
}
