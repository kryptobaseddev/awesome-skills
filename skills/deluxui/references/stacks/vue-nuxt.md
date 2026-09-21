# Vue 3 and Nuxt

## Attribute mapping

| React | Vue |
|---|---|
| `onClick` | `@click` / `v-on:click` |
| `className` | `class` |
| `htmlFor` | `for` |
| conditional render | `v-if` / `v-else` |
| list render | `v-for` |

`S-A11Y-DIVCLICK` recognises `@click` on non-interactive elements. `v-for` without a
sibling `v-if` for the empty case is the Vue shape of the missing empty state.

## What goes wrong

- `v-if` / `v-else` covers two states. Data has more than two: loading, empty, error,
  stale. Three branches minimum for anything fetched.
- `v-html` bypasses escaping — a real injection risk (TRUST-005) and it drops any
  scoped styling and semantics you expected.
- `<Transition>` animates by default. Wrap it in `prefers-reduced-motion`.
- Scoped styles do not reach child component roots; a focus style written in a parent
  may silently not apply.
- `v-model` on a custom component hides which native element actually receives focus.
  Check the rendered output, not the template.

## Nuxt

- `useFetch` / `useAsyncData` return `pending` and `error`. Use both; destructuring
  only `data` is STATE-001.
- `<NuxtImg>` needs `alt` plus `width`/`height` or an aspect ratio.
- `error.vue` is a designed state, not a fallback. It needs a route back.
- `useHead` sets the page title — NAV-001 wants one per route, and it is what screen
  reader users hear on navigation.

## Primitives

Reka UI (formerly Radix Vue), Headless UI Vue and Ark UI Vue. Same rule: if one is
installed, compose it.
