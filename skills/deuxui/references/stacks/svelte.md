# Svelte 5 and SvelteKit

The static tier scans `.svelte` files for markup, attributes and classes. Svelte's
own directives need a little translation.

## Attribute mapping

| React | Svelte |
|---|---|
| `onClick` | `on:click` (Svelte 4) / `onclick` (Svelte 5) |
| `className` | `class` |
| `htmlFor` | `for` |
| `tabIndex` | `tabindex` |
| `aria-*` | same |

`S-A11Y-DIVCLICK` recognises `on:click` and `onclick` on a non-interactive element.
Svelte's own compiler warns about this too (`a11y_click_events_have_key_events`) —
if you are silencing those warnings, this skill will keep finding what they were
telling you.

## Svelte 5 runes

- `$state` mutations are synchronous, but a pending flag still needs to exist for an
  async action. `$state` alone is not a loading state.
- `$derived` values are recomputed, not refetched — a stale server value stays stale.
- `{#await}` gives you pending, resolved and rejected in one block. Use all three
  branches; a missing `:catch` is STATE-001.
- `$effect` is the wrong place for data fetching; the waterfall it creates shows up
  in LCP.

## Useful patterns

```svelte
{#await rows}
  <p role="status">Loading your rows…</p>
{:then list}
  {#if list.length === 0}
    <p>No rows yet. <button onclick={create}>Add your first</button></p>
  {:else}
    <ul>{#each list as row (row.id)}<li>{row.name}</li>{/each}</ul>
  {/if}
{:catch err}
  <p role="alert">We could not load your rows. <button onclick={retry}>Retry</button></p>
{/await}
```

That block satisfies STATE-001, UX-001, UX-009 and the empty-collection contract in
one structure, which is why it is worth making the default shape.

## SvelteKit

- `+page.server.ts` load failures need an `+error.svelte`; the default page is not a
  designed state.
- Form actions: use `use:enhance`, and keep the submitted values on failure (FORM-004).
- `+layout.svelte` is where a skip link and the page landmarks belong.
- Route-level `export const prerender` changes what the runtime tier sees — audit the
  rendered output, not the source assumption.

## Primitives

Bits UI, Melt UI and Skeleton are the Svelte equivalents of Radix. If one is
installed, compose it rather than writing another dialog.
