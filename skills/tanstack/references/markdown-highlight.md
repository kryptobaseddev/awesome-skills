# TanStack Markdown + TanStack Highlight

> Verified 2026-10-07 against `@tanstack/markdown@1.0.0` and `@tanstack/highlight@1.0.0` docs and their package `exports` (TanStack CLI 0.71.1). Both are ESM-only with zero runtime dependencies. Both packages ship Intent skills (`intent list`). Re-check with `tanstack doc markdown <path>` / `tanstack doc highlight <path>`.

## When to use / when not to

- **Markdown**: a small, **synchronous** parser and renderer for docs, blogs and **streamed AI responses**. It is safe by default: raw HTML is escaped and `javascript:`-style URLs are stripped. It is not full CommonMark/GFM, it has no MDX and no autolinking, and it is not an HTML sanitizer. Check the syntax profile before migrating a corpus.
- **Highlight**: a small, synchronous, isomorphic highlighter that emits **semantic `th-*` classes**, with themes supplied as CSS variables. There is no WASM, no async init, no TextMate grammars and no automatic language detection. It is not for editors.
- They are **independent**. Combine them through `createTanStackMarkdownHighlighter()`.

## Packages

| Package | Entry points |
|---|---|
| `@tanstack/markdown` | `.` (parser + HTML + types), `/parser`, `/html`, `/react` (peer react >=18), `/octane`, `/extensions/{docs,streaming,callouts,headings,tabs,framework,comment-components}` |
| `@tanstack/highlight` | `.` (all languages, about 18 KB gzip), `/core`, `/languages/<name>`, `/theme`, `/themes/<name>`, `/markdown`, `/react` (data helper only, no React import), `/remark`, `/rehype`, `/octane` |

There are **no** `@tanstack/react-markdown` or `@tanstack/react-highlight` packages. React support comes from subpath exports.

```bash
npm i @tanstack/markdown @tanstack/highlight
```

## Mental model

- `parseMarkdown(src)` returns a `MarkdownDocument`: plain JSON (`children` block nodes, each with a discriminating `type`; `frontmatter` kept as the raw string). Parse once, cache with `JSON.stringify`, and render many times.
- Every renderer (`renderHtml`, React `<Markdown>`, Octane) accepts **either** a source string **or** a document.
- Markdown owns the `<pre><code>` wrapper. The `highlighter` callback returns **trusted inner markup**, which is inserted unescaped.
- Highlight: `createHighlighter({ languages })` builds an immutable instance at module scope that you reuse on both server and client. Unregistered languages fall back to escaped `plaintext`.
- Highlight output is one `<pre class="th-code th-code--ts" data-language="ts"><code>…` tree. Light and dark are only CSS (`createThemeCss`), so no re-highlighting is needed when the theme changes.

## Core API

```ts
// Markdown: HTML, no framework
import { parseMarkdown } from '@tanstack/markdown/parser'
import { renderHtml } from '@tanstack/markdown/html'

const doc = parseMarkdown(source)
const html = renderHtml(doc, { headingAnchors: { content: '#', className: 'heading-anchor' } })
```

```tsx
// Markdown: React
import { Markdown } from '@tanstack/markdown/react'
import { Link } from './Link'

export const Article = ({ source }: { source: string }) => (
  <Markdown components={{ a: Link }}>{source}</Markdown>
)
```

Other options seen in the docs: `allowHtml`, `urlTransform(url, kind, defaultUrl)`, `extensions`, `highlighter`, `codeLineNumbers`, `frontmatter`, `headingIds`.

```ts
// Highlight: selective core (recommended)
import { createHighlighter } from '@tanstack/highlight/core'
import { ts } from '@tanstack/highlight/languages/ts'
import { tsx } from '@tanstack/highlight/languages/tsx'
import { css } from '@tanstack/highlight/languages/css'
import { createThemeCss } from '@tanstack/highlight/theme'
import { githubLightTheme } from '@tanstack/highlight/themes/github-light'
import { githubDarkTheme } from '@tanstack/highlight/themes/github-dark'

export const highlighter = createHighlighter({ languages: [ts, tsx, css] })
const { html, tokens } = highlighter.highlight('const a = 1', { lang: 'ts', lineNumbers: true })
export const themeCss = createThemeCss({ light: githubLightTheme, dark: githubDarkTheme, darkSelector: '.dark' })
```

`Highlighter` methods: `highlight`, `highlightToHtml`, `tokenize`, `renderCodeBlockData({ code, lang, title, decorations })` (returns `{ copyText, htmlMarkup, lang, title, tokens }` with trailing whitespace trimmed), `listLanguages`, `normalizeLanguage`. Decorations are line (`lines: n | [start, end]`) or character-range annotations. Themes: `auroraX`, `dracula`, `githubDark`, `githubLight`, `gruvboxDark/Light`, `monokai`, `nord`, `oneDarkPro`, `solarizedDark/Light` (each exported as `<name>Theme`). There are about 39 languages, each under `languages/<name>`. Examples: `js`, `ts`, `tsx`, `jsx`, `html`, `css`, `json`, `shell` (aliases `bash`, `sh`), `python`, `rust`, `go`, `sql`, `diff`, `markdown`, `svelte`, `plaintext`.

## Patterns

**Markdown + Highlight (the supported bridge):**

```ts
// markdown-highlighter.ts
import { createHighlighter } from '@tanstack/highlight/core'
import { plaintext } from '@tanstack/highlight/languages/plaintext'
import { ts } from '@tanstack/highlight/languages/ts'
import { tsx } from '@tanstack/highlight/languages/tsx'
import { createTanStackMarkdownHighlighter } from '@tanstack/highlight/markdown'
import type { CodeHighlighter } from '@tanstack/markdown'

export const highlightMarkdownCode: CodeHighlighter = createTanStackMarkdownHighlighter(
  createHighlighter({ languages: [plaintext, ts, tsx] }),
)
```

```tsx
const themeCss = createThemeCss({
  light: githubLightTheme, dark: githubDarkTheme,
  lightSelector: '.markdown-renderer', darkSelector: '.dark .markdown-renderer',
  codeBlockSelector: '.markdown-renderer pre.tm-code',
  lineNumbersSelector: '.markdown-renderer .tm-code--line-numbers',
})
<article className="markdown-renderer">
  <style>{themeCss}</style>
  <Markdown highlighter={highlightMarkdownCode} codeLineNumbers>{source}</Markdown>
</article>
```

Fence metadata (`tsx file="app.tsx" {2,4-6}`) is parsed even without a highlighter. It is available as `CodeBlockNode.meta`, as `options.meta` in the callback, and as `data-meta` on `<pre>`.

**Streaming AI output.** Reparse the accumulated text on every update; the parser keeps no state between updates:

```tsx
import { streamingMarkdownExtension } from '@tanstack/markdown/extensions/streaming'
const streaming = [streamingMarkdownExtension()] // module scope, stable identity

<Markdown extensions={streaming} frontmatter={false} headingIds={false}>{accumulatedText}</Markdown>
```

**Highlight in a React code block.** `createHighlightedCodeBlockProps({ highlighter, code, lang, title, className })` from `@tanstack/highlight/react` returns data. You render it with `dangerouslySetInnerHTML={{ __html: block.htmlMarkup }}` and own the copy button UI. Call it during SSR; it is deterministic, so hydration matches.

**Docs preset.** `docsMarkdownExtensions()` from `@tanstack/markdown/extensions/docs` adds callouts, heading collection (`document.headings`) and comment components. Pass the same `extensions` to both parse and render.

**Unified/MDX pipelines.** Use `remarkHighlightCodeBlocks({ highlighter })` from `@tanstack/highlight/remark` (or the `/rehype` adapter).

## Traps

1. **Passing Highlight's own HTML as the Markdown highlighter.** `highlight().html` and `highlightToHtml` include their own `<pre><code>`, which produces nested code blocks. Use `createTanStackMarkdownHighlighter(highlighter)` (markdown `guides/syntax-highlighting`).
2. **Importing `{ highlight }` from the root on a docs site.** That pulls in every language (about 18 KB gzip). Use `/core` plus `/languages/<name>` (highlight `installation`).
3. **Expecting a language to "just work."** Unregistered languages render as escaped plaintext and aliases resolve only when their target is registered. `html` delegates `<script>`/`<style>` only if `js`/`css` are registered (highlight `language-support`, `quick-start`).
4. **Enabling `allowHtml` for AI or user content.** React then uses `dangerouslySetInnerHTML`. Keep it off, and never enable it just to match another parser's output (markdown `core-concepts/security`).
5. **Trusting a stored AST from untrusted JSON.** URL screening happens at parse time, not render time. Validate the structure before rendering (`core-concepts/security`).
6. **Streaming without `frontmatter: false` / `headingIds: false`.** A late `---` can turn the start of a response into frontmatter, and heading IDs change on every token. Batch very fast token streams before re-rendering (markdown `guides/ai-streaming`).
7. **Rebuilding `extensions` arrays inline on each render.** Create them once at module scope, as the docs do.
8. **Expecting a `<Highlight>` React component.** `/react` only prepares data and owns no UI or CSS (highlight `guides/react`).
9. **Diffing token snapshots across patch releases.** Highlight 1.x allows patch-level changes to token boundaries and classes. Snapshot semantics, not HTML bytes (highlight `guides/migrating-to-v1`).
10. **Re-highlighting server output during hydration.** Share one registry and one version on server and client, and send the finished markup (highlight `guides/ssr-and-client`).

## Migration notes

| From | To 1.0 |
|---|---|
| `@tanstack/markdown@0.0.16` | `^1.0.0`. No API migration needed. Rebuild cached ASTs and recheck anchors and custom components. New: `MarkdownExtension.inlineParser` |
| `@tanstack/highlight@0.1.x` | `^1.0.0` (a `^0.x` range does **not** pick up 1.x). Same entry points. JS/TS keyword-named properties now get property styling |
| Markdown + Highlight adapter | Requires `@tanstack/highlight >= 0.0.6`. Fine on 1.0 |

## Go deeper

- `tanstack doc markdown quick-start`: HTML, React, parse-once
- `tanstack doc markdown guides/ai-streaming`: streaming profile
- `tanstack doc markdown guides/syntax-highlighting`: Highlight bridge, themes
- `tanstack doc markdown core-concepts/security`: allowHtml, urlTransform
- `tanstack doc markdown core-concepts/document-model`: AST shape
- `tanstack doc markdown reference/react`: `<Markdown>` props
- `tanstack doc highlight quick-start`: selective highlighter + theme
- `tanstack doc highlight guides/themes`: theme matrix, custom themes
- `tanstack doc highlight language-support`: language/alias matrix
- `tanstack doc highlight reference/core`: Highlighter API, tokens
- `tanstack doc highlight guides/markdown-pipelines`: remark/rehype usage
