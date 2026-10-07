# TanStack CLI

> Verified 2026-10-07 against `@tanstack/cli@0.71.1` by running every command below in throwaway projects. The upstream skill spec targets v0.61.0; where they disagree, the observed 0.71.1 behaviour wins. Re-check with `npx -y @tanstack/cli@latest <cmd> --help` when the installed version differs.

## Contents
- [Run it](#run-it)
- [Command map](#command-map)
- [Discovery for agents (JSON)](#discovery-for-agents-json)
- [Scaffold: `create`](#scaffold-create)
- [Add-on catalogue snapshot](#add-on-catalogue-snapshot)
- [Evolve: `add`](#evolve-add)
- [Author add-ons and templates](#author-add-ons-and-templates)
- [Housekeeping](#housekeeping)
- [Traps (observed)](#traps-observed)

## Run it

```bash
npx -y @tanstack/cli@latest <command>      # no global install needed; bin name is `tanstack`
pnpm dlx @tanstack/cli@latest <command>    # or bunx / yarn dlx
```
The CLI writes spinners and `│ ■` boxes to stderr/stdout. For machine use, always pass `--json` and parse stdout. Do not
rely on exit codes alone: several failures exit 0 (see Traps).

## Command map

| Command | Purpose |
|---|---|
| `create [name]` | Scaffold a TanStack Start app (React or Solid), or a Router-only app with `--router-only` |
| `add <ids...>` | Layer add-ons into a project the CLI created (needs `.cta.json`) |
| `libraries [--group g] [--json]` | List TanStack libraries; groups: `state`, `headlessUI`, `performance`, `tooling` |
| `doc <library> <path> [--docs-version v] [--json]` | Fetch one docs page as Markdown (`{title, content}`) |
| `search-docs <query> [--library id] [--framework f] [--limit n≤50] [--json]` | Algolia search across tanstack.com docs |
| `ecosystem [--category c] [--library id] [--json]` | Partner list — **broken in 0.71.1**, see Traps |
| `create --list-add-ons [--framework f] [--router-only] --json` | Add-on catalogue for that framework/mode |
| `create --addon-details <id> --json` | Full add-on record: `options`, `routes`, `files`, `dependsOn`, `exclusive` |
| `pin-versions` | Rewrites `^x` TanStack ranges in package.json to exact versions |
| `clean-demos [dir] [--dry-run] [-y]` | Deletes demo/example files the scaffold added |
| `add-on init / compile / dev` | Turn the current project into a custom add-on |
| `template init / compile` | Turn the current project into a template (`starter *` = deprecated alias) |
| `dev [name] --dev-watch <path>` | Sandbox app that live-syncs a framework/add-on directory (maintainers) |
| `telemetry status / enable / disable` | Anonymous telemetry toggle |

`tanstack mcp` was removed — `error: unknown command 'mcp'`. Use the JSON discovery commands instead.

## Discovery for agents (JSON)

```bash
tanstack libraries --json                         # {group, count, libraries:[{id,name,tagline,description,frameworks[],latestVersion,docsUrl,githubUrl}]}
tanstack libraries --group state --json
tanstack search-docs "loader prefetch" --library router --framework react --limit 5 --json
#   → {query,totalHits,results:[{title,url,snippet(html-highlighted),library,breadcrumb[]}]}
tanstack doc router integrations/query --json     # → {title, content}
tanstack doc query framework/react/guides/query-keys --docs-version v5 --json
```

Turning a search hit into a `doc` call: the path is everything after `/docs/` in `url`, minus the `#anchor`.
`https://tanstack.com/router/latest/docs/integrations/query#prefetching` → `tanstack doc router integrations/query`.
Framework-specific pages live under `framework/<fw>/...` (e.g. `framework/react/overview`). A wrong path prints
`Document not found: <Lib> / <path>` and exits 1 — search first instead of guessing paths.

Library ids (0.71.1, 18 total): `start router query table charts form db ai intent virtual pacer hotkeys markdown highlight store config devtools cli`.
Groups as the CLI reports them: **state** = query, db, ai, store · **headlessUI** = table, charts, form, hotkeys, markdown, highlight ·
**performance** = virtual, pacer · **tooling** = intent, config, devtools, cli. `start` and `router` belong to no group.

## Scaffold: `create`

```bash
# Non-interactive, agent-safe React Start app
tanstack create my-app --framework react --package-manager pnpm \
  --add-ons tanstack-query,form,drizzle --add-on-config '{"drizzle":{"database":"sqlite"}}' \
  --deployment cloudflare --toolchain biome --no-examples --git --no-intent -y
```

| Flag | Notes |
|---|---|
| `--framework React\|Solid` | Case-insensitive. The add-on catalogue differs per framework — list it with the same `--framework`. |
| `--add-ons a,b,c` | Comma list of **ids**. Bare `--add-ons` non-interactively fails: "pass explicit add-ons via --add-ons <ids>". |
| `--add-on-config '<json>'` | `{"<addonId>":{"<option>":"<value>"}}`; option names/values from `--addon-details <id> --json`. Unset → the add-on's `default` (prisma: `postgres`, drizzle: `postgresql`). Stored in `.cta.json#addOnOptions`. |
| `--deployment` | `cloudflare\|netlify\|nitro\|railway\|render\|vercel`. Same as adding that deployment add-on; deploy is exclusive. |
| `--toolchain biome\|eslint` / `--no-toolchain` | Linter category is exclusive. |
| `--blank` | One-route app: no starter UI, no Tailwind, no devtools, no tests. Replaces the old `--no-tailwind`. |
| `--tailwind` / `--no-tailwind` | Deprecated no-ops. Standard scaffolds always use Tailwind; use `--blank` to avoid it. |
| `--examples` / `--no-examples` | Demo pages under `src/routes/demo/*`. Remove later with `clean-demos`. |
| `--router-only` | File-based TanStack Router SPA **without Start**. Drops templates, deployment and every Start-dependent add-on — see Traps. |
| `--template <url-or-id>` | Template ids need a registry (`CTA_REGISTRY`); without one only URLs work. `--starter` is the deprecated name. |
| `--intent` / `--no-intent` | Sets up TanStack Intent skill mappings for coding agents (see `intent.md`). |
| `--no-install`, `--no-git`, `--target-dir`, `-f/--force`, `--package-manager` | As named. `-y`/`--non-interactive` skips prompts. |

Generated (React Start, 0.71.1): `vite.config.ts` (plugins in order `devtools(), <deploy>(), tailwindcss(), tanstackStart(), viteReact()`),
`src/router.tsx`, `src/routes/__root.tsx`, `tsr.config.json`, `.cta.json`, scripts `dev` (`vite dev --port 3000`), `build`, `preview`.

`.cta.json` is the project's scaffold record and the precondition for `add`:
```json
{ "projectName": "app", "mode": "file-router", "framework": "react", "typescript": true, "tailwind": true,
  "packageManager": "npm", "routerOnly": false, "includeExamples": true, "intent": false,
  "addOnOptions": { "drizzle": { "database": "sqlite" } }, "chosenAddOns": ["db", "drizzle", "netlify", "tanstack-query"], "version": 1 }
```

## Add-on catalogue snapshot

Snapshot of `create --list-add-ons --json` (React, 0.71.1). **Re-list before use** — it changes between releases and per framework.
`modes`: `file-router` (Start/file routes) and/or `code-router`. `exclusive` = categories where only one add-on may be chosen.

| Category (exclusive?) | React ids | Notes |
|---|---|---|
| deploy (yes) | `cloudflare` `netlify` `railway` `nitro` (file+code) · `vercel` `render` (file only) | Use `--deployment` or the id |
| auth (yes) | `better-auth` `clerk` `workos` | file-router only |
| orm (yes) | `prisma` `drizzle` | Optionized: `database` select |
| database | `convex` (exclusive with database **and** orm), `neon` (exclusive database), `powersync` | |
| tanstack | `tanstack-query` `form` `table` `store` (file+code) · `db` (needs tanstack-query) · `ai` (needs store) | |
| api | `tRPC` `oRPC` (need tanstack-query) · `apollo-client` · `mcp` | ids are case-sensitive: `tRPC`, `oRPC` |
| other | `shopify` (needs tanstack-query), `strapi` (cms), `sentry`, `posthog`, `paraglide` (i18n), `shadcn`, `t3env`, `compiler`, `storybook` | |
| toolchain (linter, yes) | `biome` `eslint` | |
| examples | `events` `resume` `shopify-storefront` | full demo apps (`type: example`) |

Solid has a much smaller set (18): deploy ids, `better-auth`, `convex`, `form`, `store`, `tanstack-query`, `sentry`, `strapi`, `t3env`,
`solid-ui`, `biome`, `eslint`, example `tanchat`. Asking Solid for `tRPC`, `clerk`, `prisma`, `drizzle`, `db`, `ai`, `table` fails with
`Add-on <id> not found` (exit 1).

`dependsOn` is resolved automatically: `--add-ons db` also installs `tanstack-query`, and `.cta.json` records both.

## Evolve: `add`

```bash
cd my-app
tanstack add form table --forced --no-intent      # space- or comma-separated ids
```
- Requires `.cta.json` in the cwd. Projects not created by this CLI (or by the old `create-tsrouter-app`/`create-start-app`) cannot use it —
  install the packages manually instead (each library reference lists them).
- It shows the files it will change and **asks for confirmation**. With no TTY the prompt blocks forever. `--forced` skips it.
- It runs the package manager install itself, then appends ids to `.cta.json#chosenAddOns`.
- Commit or stash first: it edits `package.json` and shared files such as `src/components/Header.tsx`, so review `git diff` afterwards.
- Exclusivity and mode rules from the catalogue still apply; `add` does not protect you from a second ORM or auth provider.

## Author add-ons and templates

Maintainer workflow, in a project that **the CLI created in file-router mode** (needs `.cta.json`; code-router projects are rejected for add-on authoring):
```bash
tanstack add-on init        # snapshot the diff vs. the base scaffold into .add-on/ + add-on.json
tanstack add-on dev         # watch and keep .add-on/ + add-on.json in sync while you edit
tanstack add-on compile     # one-shot refresh
tanstack template init && tanstack template compile   # same idea for a whole-project template (template.json)
```
Consume a custom add-on/template by URL: `tanstack create app --add-ons https://.../add-on.json` or `--template https://.../template.json`.

Framework-maintainer loop: `tanstack dev sandbox --dev-watch ./path/to/framework --run-dev` builds a sandbox app and re-syncs on change.
`--dev-watch` needs dependency installation (do not combine with `--no-install`) and a directory with a valid package entry.

## Housekeeping

- `tanstack clean-demos --dry-run` then `tanstack clean-demos -y` — removes `src/routes/demo/*`, `demo.*` components/hooks.
  Run it before building real features so demo routes do not ship.
- `tanstack pin-versions` — **avoid in 0.71.1** (Trap 12). Pin with your package manager instead, e.g. `npm pkg set dependencies.@tanstack/react-query=5.104.1` or `pnpm add -E <pkg>@<version>`.
- `tanstack telemetry disable` — for CI or privacy-sensitive users.

## Traps (observed)

1. **Exclusive categories are not enforced on the command line.** `--add-ons prisma,drizzle` (both `orm`) exits 0 and scaffolds both. Read
   `exclusive` in `--list-add-ons --json` and pick at most one per category yourself (deploy, auth, orm, database, linter).
2. **`--router-only` silently discards intent.** With `--deployment netlify --add-ons tanstack-query` it exits 0 and creates a project with
   `chosenAddOns: []`; only a `▲ Ignoring --add-ons in router-only compatibility mode` line hints at it. Router-only supports the base template
   and a toolchain only. If the user wants deployment, auth, ORM or Start features, they want Start — drop `--router-only`. If they truly
   want an SPA, scaffold router-only, then install libraries (e.g. `@tanstack/react-query`) by hand.
3. **`--router-only --list-add-ons --json` puts a warning banner before the JSON** on stdout. Strip lines before the first `[` or do not
   combine those flags when parsing.
4. **`ecosystem` fails in 0.71.1** with a zod error (`partners[n].libraries: Required`) because the API response changed shape. Fallback:
   `curl -s https://tanstack.com/api/data/partners` (JSON `{partners:[{id,name,tagline,description,category,...}]}`). Partner ids
   are **not** add-on ids — map them to `--list-add-ons` ids before passing to `--add-ons`.
5. **`tanstack add` without `.cta.json` exits 0** after printing "There is no .cta.json file in your project". Check for the file first.
6. **`tanstack add` blocks on a confirmation prompt** in non-interactive shells; pass `--forced`.
7. **Invalid ids fail loudly in `create`** (`Add-on nope not found`, exit 1, no directory) — ids are framework-specific and case-sensitive.
8. **`--no-tailwind` no longer removes Tailwind** — it is a deprecated no-op; use `--blank`.
9. **Template ids without a registry fail**: `Could not resolve template id ... no template registry is configured`. Pass a URL.
10. **Optionized add-ons default silently.** Prisma and Drizzle pick Postgres unless `--add-on-config` says otherwise; check
    `--addon-details <id> --json` and pass the user's database explicitly.
11. **Add-ons may be file-router only** (`modes: ["file-router"]`): every auth, ORM, database and most API add-ons. They cannot be used in
    code-router projects.
12. **`pin-versions` writes versions that do not exist.** In a fresh 0.71.1 scaffold it reported "7 packages updated" and added
    vinxi-era packages pinned to the Start version — `@tanstack/react-start-config@1.168.60` and `react-start-plugin@1.168.60` were never
    published (their last versions are 1.120.x / 1.131.x), so the next install fails with `ETARGET`. If it already ran, `git checkout package.json`.
13. **The `table` add-on installs v9 but its demo is v8 code.** It adds `@tanstack/react-table@latest` (9.x) plus `@faker-js/faker` and
    `@tanstack/match-sorter-utils`. When examples are enabled (`.cta.json#includeExamples: true`, the default), it also writes
    `src/routes/demo/table.tsx`, which imports `useReactTable` / `getCoreRowModel` — no longer exported from v9's main entry — so
    `vite build` fails. In a `--no-examples` project no demo route is written, but `@faker-js/faker` is still added (remove it).
    Simplest: `pnpm add @tanstack/react-table`. Check other demo-bearing add-ons the same way after a library's major bump.
14. **Add-on wiring is a starting point, not a working stack.** Observed in 0.71.1: Drizzle's `sqlite` option uses `better-sqlite3`, a
    native Node module that cannot run on Cloudflare Workers (use D1 or a Postgres/Hyperdrive driver there), and the auth add-ons are not
    connected to the chosen ORM. After scaffolding, read `src/db/*`, the auth files and `vite.config.ts` and reconcile them with the
    deployment target before telling the user the project works.
