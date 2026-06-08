#!/usr/bin/env node
import { spawnSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptArgs = process.argv.slice(2)
if (scriptArgs.length === 0) {
  console.error('Usage: node scripts/run_python.mjs <script.py> [args...]')
  process.exit(2)
}

const scriptDir = dirname(fileURLToPath(import.meta.url))
const defaultsPath = join(scriptDir, 'acceptance.defaults.json')

function pythonFromDefaults() {
  if (!existsSync(defaultsPath)) return ''
  try {
    const data = JSON.parse(readFileSync(defaultsPath, 'utf8'))
    return typeof data.python_exe === 'string' ? data.python_exe : ''
  } catch {
    return ''
  }
}

const candidates = [
  process.env.PROJECT_A_PYTHON_EXE,
  pythonFromDefaults(),
  'python',
  'python3',
  'py',
].filter(Boolean)

function isWindowsAppsAlias(path) {
  return /WindowsApps/i.test(path || '')
}

function checkCandidate(candidate) {
  if (candidate.includes('\\') || candidate.includes('/')) {
    if (!existsSync(candidate) || isWindowsAppsAlias(candidate)) return false
  }
  const args = candidate === 'py' ? ['-3', '--version'] : ['--version']
  const result = spawnSync(candidate, args, { encoding: 'utf8', shell: false })
  if (result.status !== 0) return false
  const output = `${result.stdout || ''}${result.stderr || ''}`
  return /^Python\s+3\./.test(output.trim())
}

let python = ''
for (const candidate of candidates) {
  if (checkCandidate(candidate)) {
    python = candidate
    break
  }
}

if (!python) {
  console.error('Unable to find a Python 3 executable. Set PROJECT_A_PYTHON_EXE to an absolute python.exe path.')
  process.exit(1)
}

const args = python === 'py' ? ['-3', ...scriptArgs] : scriptArgs
const result = spawnSync(python, args, { stdio: 'inherit', shell: false })
process.exit(result.status ?? 1)
