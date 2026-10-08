#!/usr/bin/env node
// ux-laws walk: visit every route at every width, mobile first, run probe.js, save a screenshot and the
// probe JSON as <route>@<width>.json. Feed the folder to scorecard.py --probes.
//
// Needs the `playwright` npm package. It is looked up in the project (cwd), next to this script, in
// $UX_LAWS_PW_DIR, and in a private cache (~/.cache/ux-laws). If none has it, run once with --install:
// that installs playwright + Chromium into the cache only (nothing is added to the project). Or skip the
// batch walk and do it by hand with any browser tool - references/browser-walkthrough.md has the recipe.
//
// Usage:
//   node walk.mjs --base http://localhost:5173 --routes / /products /checkout [--widths 320,390,768,1024,1440]
//                 [--out ux-audit/captures] [--full-page] [--wait 600] [--routes-file routes.txt]
//                 [--storage-state auth.json] [--slices] [--install]
// --slices also saves viewport-height screenshots down the page (<name>-s1.png …): review those, not only
// --full-page, because full-page captures paint fixed and sticky bars in the wrong place and hide overlaps.
// Narrow widths (< 768) are emulated as touch devices (hasTouch, isMobile) so pointer:coarse and
// hover:none media queries behave as on a phone. Read-only: it navigates and measures, never clicks.
import { mkdirSync, readFileSync, writeFileSync, existsSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'
import { homedir } from 'node:os'
import { spawnSync } from 'node:child_process'

const here = dirname(fileURLToPath(import.meta.url))
const argv = process.argv.slice(2)
const opt = (name, dflt) => {
  const i = argv.indexOf(`--${name}`)
  if (i < 0) return dflt
  const vals = []
  for (let j = i + 1; j < argv.length && !argv[j].startsWith('--'); j++) vals.push(argv[j])
  return vals.length ? vals : true
}
const base = (opt('base', ['http://localhost:3000'])[0]).replace(/\/$/, '')
let routes = opt('routes', null) || []
const rf = opt('routes-file', null)
if (rf) routes = routes.concat(readFileSync(rf[0], 'utf8').split('\n').map((s) => s.trim()).filter((s) => s && !s.startsWith('#')))
if (!routes.length) routes = ['/']
const widths = String(opt('widths', ['320,390,768,1024,1440'])[0]).split(',').map(Number)
const out = resolve(opt('out', ['ux-audit/captures'])[0])
const fullPage = opt('full-page', false) === true
const waitMs = Number(opt('wait', ['600'])[0])
const storageState = opt('storage-state', null)?.[0]
const slices = opt('slices', false) === true

const cacheDir = process.env.UX_LAWS_PW_DIR || join(homedir(), '.cache', 'ux-laws')
const lookIn = [process.cwd() + '/', here + '/', cacheDir + '/']
const findChromium = () => {
  for (const from of lookIn) { try { return createRequire(from)('playwright').chromium } catch {} }
  return null
}
let chromium = findChromium()
if (!chromium && opt('install', false) === true) {
  console.error(`installing playwright + chromium into ${cacheDir} (one time, outside the project)`)
  mkdirSync(cacheDir, { recursive: true })
  if (!existsSync(join(cacheDir, 'package.json'))) writeFileSync(join(cacheDir, 'package.json'), '{"name":"ux-laws-browser","private":true}')
  const run = (cmd, args) => { const r = spawnSync(cmd, args, { cwd: cacheDir, stdio: 'inherit', shell: process.platform === 'win32' }); if (r.status !== 0) { console.error(`failed: ${cmd} ${args.join(' ')}`); process.exit(2) } }
  run('npm', ['install', '--no-audit', '--no-fund', 'playwright@1.56.1'])
  run('npx', ['playwright', 'install', 'chromium'])
  chromium = findChromium()
}
if (!chromium) {
  console.error('playwright was not found (looked in the project, next to this script and in ' + cacheDir + ').\n' +
    'Run again with --install to set it up in that cache (one time, nothing added to the project),\n' +
    'or walk by hand with your browser tool (see references/browser-walkthrough.md).')
  process.exit(2)
}

const probeSrc = readFileSync(join(here, 'probe.js'), 'utf8')
mkdirSync(out, { recursive: true })
const slug = (r) => (r === '/' ? 'home' : r.replace(/^\//, '').replace(/[^a-z0-9]+/gi, '-').replace(/-+$/, '')) || 'home'

const browser = await chromium.launch()
const summary = []
try {
  for (const route of routes) {
    for (const w of widths) {
      const mobile = w < 768
      const ctx = await browser.newContext({
        viewport: { width: w, height: mobile ? 844 : 900 },
        deviceScaleFactor: mobile ? 2 : 1,
        isMobile: mobile,
        hasTouch: mobile,
        ...(storageState && existsSync(storageState) ? { storageState } : {}),
      })
      const page = await ctx.newPage()
      const consoleErrors = []
      page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 200)) })
      page.on('pageerror', (e) => consoleErrors.push(String(e).slice(0, 200)))
      const name = `${slug(route)}@${w}`
      try {
        const resp = await page.goto(base + route, { waitUntil: 'networkidle', timeout: 30000 })
        await page.waitForTimeout(waitMs)
        const data = await page.evaluate(`(${probeSrc})()`)
        data.requestedWidth = w
        data.status = resp?.status() ?? null
        data.consoleErrors = consoleErrors
        writeFileSync(join(out, `${name}.json`), JSON.stringify(data, null, 2))
        await page.screenshot({ path: join(out, `${name}.png`), fullPage })
        if (slices) {
          const total = await page.evaluate(() => document.documentElement.scrollHeight), vh = page.viewportSize().height
          for (let i = 0, y = 0; y < total && i < 10; i++, y += Math.round(vh * 0.85)) {
            await page.evaluate((top) => window.scrollTo(0, top), y); await page.waitForTimeout(150)
            await page.screenshot({ path: join(out, `${name}-s${i + 1}.png`) })
          }
        }
        summary.push(`${name}: overflow=${data.reflow.horizontalOverflow} <24px=${data.targets.below24} contrast=${data.text.lowContrast} ctas=${data.primaryActions.firstViewportFilled}`)
      } catch (e) {
        summary.push(`${name}: ERROR ${String(e).split('\n')[0]}`)
      } finally {
        await ctx.close()
      }
    }
  }
} finally {
  await browser.close()
}
console.log(summary.join('\n'))
console.log(`\ncaptures in ${out}\nnext: python3 ${join(here, 'scorecard.py')} --probes ${out} [--inventory inventory.json]`)
