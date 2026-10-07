#!/usr/bin/env node
// tanstack-preflight: report which TanStack libraries a project uses, at which installed versions,
// which version-sensitive APIs apply, whether the TanStack CLI can `add` to it, and which
// version-matched skills ship inside node_modules. Read-only; never installs or edits anything.
//
// Usage: node tanstack-preflight.mjs [project-dir] [--json]
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs'
import { join, resolve } from 'node:path'

const args = process.argv.slice(2)
const asJson = args.includes('--json')
const root = resolve(args.find((a) => !a.startsWith('--')) ?? '.')

const readJson = (p) => {
  try { return JSON.parse(readFileSync(p, 'utf8')) } catch { return null }
}
const major = (v) => (v ? Number(String(v).replace(/^[^\d]*/, '').split('.')[0]) : NaN)
const cmp = (a, b) => {
  const pa = String(a).replace(/^[^\d]*/, '').split(/[.-]/).map(Number)
  const pb = String(b).split('.').map(Number)
  for (let i = 0; i < 3; i++) if ((pa[i] || 0) !== (pb[i] || 0)) return (pa[i] || 0) - (pb[i] || 0)
  return 0
}

const pkg = readJson(join(root, 'package.json'))
if (!pkg) {
  const msg = `No readable package.json in ${root}`
  if (asJson) console.log(JSON.stringify({ ok: false, error: msg }))
  else console.error(msg)
  process.exit(1)
}

const declared = { ...pkg.peerDependencies, ...pkg.devDependencies, ...pkg.dependencies }
const LEGACY = ['react-query', 'react-table', 'react-virtual', 'react-charts', '@tanstack/router-devtools', '@tanstack/zod-form-adapter', 'vinxi']
const names = Object.keys(declared).filter((n) => n.startsWith('@tanstack/') || LEGACY.includes(n))

const installedVersion = (name) => readJson(join(root, 'node_modules', name, 'package.json'))?.version ?? null
const packages = names.sort().map((name) => ({ name, declared: declared[name], installed: installedVersion(name) }))
const ver = (name) => packages.find((p) => p.name === name)?.installed ?? packages.find((p) => p.name === name)?.declared

// Map package names to library ids (adapter-agnostic).
const LIB_PATTERNS = [
  ['start', /-start($|-)/], ['router', /(^|-)router($|-)/], ['query', /(^|-)query($|-)/], ['table', /(^|-)table($|-)/],
  ['charts', /charts/], ['form', /(^|-)form($|-)/], ['db', /(^|-)db($|-)|db-collection/], ['ai', /(^|-)ai($|-)/],
  ['intent', /^intent$/], ['virtual', /virtual/], ['pacer', /pacer/], ['hotkeys', /hotkeys/], ['markdown', /markdown/],
  ['highlight', /highlight/], ['store', /(^|-)store$/], ['config', /^((vite|eslint|publish|typedoc)-)?config$/],
  // only the unified panel counts as "devtools"; react-query-devtools etc. belong to their own library
  ['devtools', /^((react|solid|vue|preact|svelte|angular)-)?devtools(-vite)?$/], ['cli', /^cli$/],
]
const libraries = new Set()
for (const { name } of packages) {
  if (!name.startsWith('@tanstack/')) continue
  const short = name.slice('@tanstack/'.length)
  for (const [id, re] of LIB_PATTERNS) if (re.test(short)) libraries.add(id)
}

// Version-sensitive findings an agent writing from memory would get wrong.
const findings = []
const add = (level, lib, message) => findings.push({ level, lib, message })

const rt = ver('@tanstack/react-table') ?? ver('@tanstack/table-core')
if (rt) {
  if (major(rt) >= 9) add('info', 'table', `Table v${major(rt)}: use useTable + features: tableFeatures({...}); useReactTable/getCoreRowModel exist only in '/legacy'.`)
  else add('info', 'table', `Table v${major(rt)}: v8 API (useReactTable, getCoreRowModel). Do not write v9 code unless upgrading.`)
}
const rq = ver('@tanstack/react-query') ?? ver('@tanstack/query-core')
if (rq) {
  if (major(rq) < 5) add('warn', 'query', `Query v${major(rq)}: positional signatures, cacheTime, isLoading semantics differ from v5.`)
  else if (cmp(rq, '5.102.0') < 0) add('info', 'query', `Query ${rq} < 5.102: queryClient.query() does not exist; use ensureQueryData/prefetchQuery/fetchQuery.`)
  else add('info', 'query', `Query ${rq} >= 5.102: prefer queryClient.query(); ensureQueryData/prefetchQuery/fetchQuery are deprecated.`)
}
const st = ver('@tanstack/store') ?? ver('@tanstack/react-store')
if (st && cmp(st, '0.9.0') < 0) add('info', 'store', `Store ${st} < 0.9: class API (new Store/Derived/Effect). 0.9+ uses createStore/createAtom.`)
else if (st) add('info', 'store', `Store ${st}: createStore/createAtom API; new Store/Derived/Effect are gone; prefer useSelector over useStore (0.11+).`)
const db = ver('@tanstack/db')
if (db && cmp(db, '0.8.0') >= 0) add('info', 'db', `DB ${db}: prefer collectionOptions + DbClient/DbProvider (SSR-safe) over module-level createCollection.`)
for (const legacy of ['react-query', 'react-table', 'react-virtual', 'react-charts']) {
  if (declared[legacy]) add('warn', legacy, `Legacy unscoped package '${legacy}' is installed; its API predates the @tanstack/* versions.`)
}
if (declared['@tanstack/router-devtools']) add('warn', 'router', `'@tanstack/router-devtools' is the old name; current is '@tanstack/react-router-devtools'.`)
if (declared['@tanstack/zod-form-adapter']) add('warn', 'form', `'@tanstack/zod-form-adapter' is pre-1.0; Form v1 takes Standard Schemas directly in validators.`)
const hasStart = packages.some((p) => /@tanstack\/(react|solid)-start$/.test(p.name))
if (hasStart) {
  if (existsSync(join(root, 'app.config.ts')) || declared.vinxi) add('warn', 'start', 'Legacy Start layout (app.config.ts / vinxi). Current Start is a Vite plugin: tanstackStart() in vite.config.ts.')
  const startTs = ['src/start.ts', 'src/start.tsx'].find((f) => existsSync(join(root, f)))
  if (startTs) add('info', 'start', `${startTs} exists: Start no longer auto-adds CSRF middleware for server functions; confirm createCsrfMiddleware is registered.`)
}

// TanStack CLI scaffold metadata (precondition for `tanstack add`).
const cta = readJson(join(root, '.cta.json'))
const cli = cta
  ? { ctaJson: true, mode: cta.mode, framework: cta.framework, routerOnly: !!cta.routerOnly, chosenAddOns: cta.chosenAddOns ?? [], addOnOptions: cta.addOnOptions ?? {} }
  : { ctaJson: false, note: 'No .cta.json: `tanstack add` cannot be used here; install packages manually.' }

// Version-matched skills shipped inside installed packages (TanStack Intent convention: <pkg>/skills/**/SKILL.md).
const bundledSkills = []
const walkSkills = (dir, pkgName, prefix = '') => {
  let entries = []
  try { entries = readdirSync(dir) } catch { return }
  for (const e of entries) {
    const p = join(dir, e)
    try { if (!statSync(p).isDirectory()) continue } catch { continue }
    if (existsSync(join(p, 'SKILL.md'))) bundledSkills.push(`${pkgName}#${prefix}${e}`)
    walkSkills(p, pkgName, `${prefix}${e}/`)
  }
}
const scopeDir = join(root, 'node_modules', '@tanstack')
if (existsSync(scopeDir)) {
  for (const d of readdirSync(scopeDir)) walkSkills(join(scopeDir, d, 'skills'), `@tanstack/${d}`)
}

const lock = [['pnpm-lock.yaml', 'pnpm'], ['bun.lock', 'bun'], ['bun.lockb', 'bun'], ['yarn.lock', 'yarn'], ['package-lock.json', 'npm'], ['deno.lock', 'deno']]
  .find(([f]) => existsSync(join(root, f)))?.[1] ?? null

const report = {
  ok: true,
  root,
  packageManager: lock,
  nodeModules: existsSync(join(root, 'node_modules')),
  libraries: [...libraries].sort(),
  packages,
  findings,
  cli,
  bundledSkills,
  intentAllowlist: pkg.intent?.skills ?? null,
}

if (asJson) {
  console.log(JSON.stringify(report, null, 2))
} else {
  console.log(`TanStack preflight: ${root}`)
  console.log(`package manager: ${lock ?? 'unknown'} · node_modules: ${report.nodeModules ? 'yes' : 'NO (installed versions unknown)'}`)
  console.log(`libraries: ${report.libraries.join(', ') || 'none'}`)
  for (const p of packages) console.log(`  ${p.name.padEnd(40)} declared ${String(p.declared).padEnd(12)} installed ${p.installed ?? '-'}`)
  if (findings.length) console.log('findings:')
  for (const f of findings) console.log(`  [${f.level}] ${f.lib}: ${f.message}`)
  console.log(cta ? `CLI: .cta.json present (${cli.framework}, ${cli.mode}${cli.routerOnly ? ', router-only' : ''}); add-ons: ${cli.chosenAddOns.join(', ') || 'none'}` : `CLI: ${cli.note}`)
  console.log(bundledSkills.length
    ? `bundled skills (${bundledSkills.length}): load with  npx -y @tanstack/intent@latest load <id>\n  ${bundledSkills.join('\n  ')}`
    : 'bundled skills: none found under node_modules/@tanstack/*/skills')
  console.log('  (only direct @tanstack/* dirs are scanned; with pnpm, `npx -y @tanstack/intent@latest list` also sees transitive packages such as router-core)')
}
