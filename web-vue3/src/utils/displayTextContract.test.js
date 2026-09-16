import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import test from 'node:test'

const __dirname = dirname(fileURLToPath(import.meta.url))
const displayTextSource = readFileSync(resolve(__dirname, './displayText.js'), 'utf8')

test('parent relationship type is shown as parenting spouse copy', () => {
  assert.match(displayTextSource, /parent:\s*'育儿夫妻'/)
})
