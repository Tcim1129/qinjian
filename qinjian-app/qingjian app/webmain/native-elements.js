import { h } from 'vue'

function mergeStyle(inlineStyle, extraStyle) {
  if (!inlineStyle) return extraStyle
  return Array.isArray(inlineStyle) ? [...inlineStyle, extraStyle] : [inlineStyle, extraStyle]
}

export const ViewElement = {
  name: 'view',
  inheritAttrs: false,
  setup(_, { attrs, slots }) {
    return () => h('div', attrs, slots.default ? slots.default() : [])
  },
}

export const TextElement = {
  name: 'text',
  inheritAttrs: false,
  setup(_, { attrs, slots }) {
    return () => h('span', attrs, slots.default ? slots.default() : [])
  },
}

export const ImageElement = {
  name: 'image',
  inheritAttrs: false,
  props: {
    src: {
      type: String,
      default: '',
    },
    mode: {
      type: String,
      default: 'cover',
    },
  },
  setup(props, { attrs }) {
    return () =>
      h('img', {
        ...attrs,
        src: props.src || attrs.src || '',
        class: attrs.class,
      })
  },
}

export const ScrollViewElement = {
  name: 'scroll-view',
  inheritAttrs: false,
  props: {
    scrollY: {
      type: [Boolean, String],
      default: false,
    },
  },
  setup(props, { attrs, slots }) {
    return () =>
      h(
        'div',
        {
          ...attrs,
          class: attrs.class,
          style: mergeStyle(
            attrs.style,
            props.scrollY ? { overflowY: 'auto', overflowX: 'hidden' } : { overflow: 'visible' }
          ),
        },
        slots.default ? slots.default() : []
      )
  },
}
