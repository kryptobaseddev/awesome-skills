# TanStack Config

> Verified 2026-10-07 against TanStack Config docs and npm: `@tanstack/config@0.22.2` (umbrella), `@tanstack/vite-config@0.6.0`, `@tanstack/eslint-config@0.4.0`, `@tanstack/publish-config@0.2.7`, `@tanstack/typedoc-config@0.3.4` (TanStack CLI 0.71.1). Re-check with `tanstack doc config <path>`.

**This is tooling for library maintainers who publish npm packages the way TanStack does. It is not for app developers.** App builds use your framework's Vite config (for example TanStack Start's plugin). Do not add `@tanstack/config` or `tanstackViteConfig` to an application.

## When to use / when not to

- Use it if you maintain a TanStack-style pnpm + Nx monorepo and want the shared ESLint flat config, programmatic `publish()` helper, or the legacy dual ESM/CJS Vite library build.
- Do not use it for application builds, or with npm, yarn or bun. **pnpm v10+ is the only supported package manager.** It also needs Node 20.17+, the Git CLI and the GitHub CLI.
- For new libraries, the docs themselves recommend **tsdown** (or `tsc` for ESM-only) over the custom Vite setup.

## Packages

| Package | Purpose | Import |
|---|---|---|
| `@tanstack/eslint-config` | Shared flat config (ESLint 9+): `@eslint/js`, typescript-eslint, import-x, n | `import { tanstackConfig } from '@tanstack/eslint-config'` |
| `@tanstack/vite-config` | Legacy dual ESM/CJS library build | `import { tanstackViteConfig } from '@tanstack/vite-config'` |
| `@tanstack/publish-config` | Programmatic release/publish (ESM only) | `import { publish } from '@tanstack/publish-config'` |
| `@tanstack/typedoc-config` | Shared TypeDoc setup (no doc page; unverified usage) | |
| `@tanstack/config` | Umbrella that re-exports the above as `/eslint`, `/vite`, `/publish`, `/typedoc`. It pins **older** sub-package versions (`vite-config@0.4.1` and others) | `@tanstack/config/vite` etc. |

```bash
pnpm add -D @tanstack/eslint-config @tanstack/vite-config @tanstack/publish-config
```

## Core API

```js
// eslint.config.js
import { tanstackConfig } from '@tanstack/eslint-config'
export default [...tanstackConfig, { rules: { /* overrides */ } }]
```

```ts
// vite.config.ts (library). Merge your config FIRST, then tanstackViteConfig. Do not set `build` yourself.
import { defineConfig, mergeConfig } from 'vite'
import { tanstackViteConfig } from '@tanstack/vite-config'

export default mergeConfig(
  defineConfig({ /* framework plugins, vitest */ }),
  tanstackViteConfig({ entry: './src/index.ts', srcDir: './src' }),
)
```

```ts
// scripts/publish.ts (package.json needs "type": "module")
import { publish } from '@tanstack/publish-config'
await publish({ branchConfigs, packages, rootDir, branch: process.env.BRANCH, tag: process.env.TAG, ghToken: process.env.GH_TOKEN })
```

## Traps

1. **Using it in an app.** It builds library `dist/esm` + `dist/cjs` output and is not an app bundler config (`vite`).
2. **Choosing `@tanstack/config` for the newest code.** The umbrella pins older sub-packages. Depend on `@tanstack/*-config` directly.
3. **The Vite setup also needs package changes:** `"type": "module"`, an `exports` map (`import`/`require` with their own `types`), `moduleResolution: "bundler"`, and `vite.config.ts` in tsconfig `include`. The docs recommend `vite build && publint --strict` (`vite`).
4. **Calling `publish` from CJS fails.** It is ESM-only. npm trusted publishing (OIDC) needs a one-time setup per package on npmjs.com (`publish`).
5. **Package layout conventions:** tests go in `./tests` (not `src`), and each package has `test:eslint`, `test:types`, `test:lib`, `build` and `test:build` scripts, which Nx caches (`package-structure`, `ci-cd`).

## Go deeper

- `tanstack doc config overview`: prerequisites, utilities list
- `tanstack doc config vite`: legacy dual-publish build, tsdown advice
- `tanstack doc config eslint`: flat config setup
- `tanstack doc config publish`: publish(), trusted publishing
- `tanstack doc config package-structure`: monorepo package conventions
- `tanstack doc config ci-cd`: Nx, Changesets, pkg-pr-new workflows
