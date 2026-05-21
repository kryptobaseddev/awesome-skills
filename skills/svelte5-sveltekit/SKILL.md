---
name: svelte5-sveltekit
description: Comprehensive guide for building modern web applications with Svelte 5 and SvelteKit. Use when creating Svelte components, implementing Svelte 5 runes ($state, $derived, $effect, $props), building SvelteKit applications with filesystem routing, loading data, handling forms, styling components, or deploying Svelte/SvelteKit apps. Essential for questions about Svelte reactivity, SvelteKit project structure, SSR/CSR configuration, form actions, adapters, or migration from Svelte 4.
---

# Svelte 5 and SvelteKit Development

## When to Use This Skill

Use this skill when working with:
- Svelte 5 components and runes ($state, $derived, $effect, $props, $bindable)
- SvelteKit web applications (routing, data loading, forms, deployment)
- Modern reactive web development with Svelte
- Server-side rendering (SSR) and static site generation (SSG)
- Full-stack TypeScript applications with SvelteKit

## Quick Reference

### Essential Links
- Official Docs: https://svelte.dev/docs
- Tutorial: https://svelte.dev/tutorial
- Playground: https://svelte.dev/playground
- GitHub: https://github.com/sveltejs/svelte

## Core Concepts

### Svelte 5 Runes (New Reactivity)

Runes are compiler keywords with `$` prefix that control reactivity:

```svelte
<script>
// State
let count = $state(0);
let user = $state({ name: 'Alice' });

// Derived values
let doubled = $derived(count * 2);

// Side effects
$effect(() => {
  console.log(`Count: ${count}`);
  return () => console.log('cleanup');
});

// Props
let { title, count = 0 } = $props();

// Bindable props
let { value = $bindable() } = $props();
</script>

<button onclick={() => count++}>
  Count: {count} (doubled: {doubled})
</button>
```

**For detailed runes documentation:** Read [references/runes-reactivity.md](references/runes-reactivity.md)

### SvelteKit Project Structure

```
src/
├── lib/                    # Shared code ($lib alias)
│   ├── server/            # Server-only code ($lib/server)
│   └── components/        # Reusable components
├── routes/                # File-based routing
│   ├── +page.svelte       # Page component
│   ├── +page.js           # Universal load function
│   ├── +page.server.js    # Server load / form actions
│   ├── +layout.svelte     # Layout wrapper
│   ├── +layout.js         # Layout data
│   ├── +error.svelte      # Error boundary
│   └── +server.js         # API endpoint
├── app.html               # HTML template
└── hooks.server.js        # Server hooks
```

### File-Based Routing

Routes map to directories:
- `src/routes/` → `/`
- `src/routes/about/` → `/about`
- `src/routes/blog/[slug]/` → `/blog/:slug` (dynamic)
- `src/routes/[...rest]/` → `/*` (catch-all)

**For advanced routing patterns:** Read [references/routing.md](references/routing.md)

## Development Workflow

### 1. Creating Components

```svelte
<!-- Button.svelte -->
<script>
let { 
  variant = 'primary', 
  disabled = false,
  onclick 
} = $props();

let pressed = $state(false);
</script>

<button 
  class="btn {variant}" 
  {disabled}
  {onclick}
  onmousedown={() => pressed = true}
  onmouseup={() => pressed = false}
  class:pressed
>
  <slot />
</button>

<style>
.btn { /* scoped styles */ }
.btn.primary { /* ... */ }
.pressed { transform: scale(0.95); }
</style>
```

### 2. Loading Data

**Universal load** (+page.js) - runs on server and client:
```typescript
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
  const res = await fetch(`/api/posts/${params.slug}`);
  return { post: await res.json() };
};
```

**Server load** (+page.server.js) - server-only with database access:
```typescript
import type { PageServerLoad } from './$types';
import { db } from '$lib/server/database';

export const load: PageServerLoad = async ({ params }) => {
  const post = await db.getPost(params.slug);
  return { post };
};
```

Access data in component:
```svelte
<script>
let { data } = $props();
</script>

<h1>{data.post.title}</h1>
```

**For comprehensive data loading guide:** Read [references/data-loading.md](references/data-loading.md)

### 3. Form Actions

Handle form submissions server-side:
```typescript
// +page.server.ts
import { fail } from '@sveltejs/kit';
import type { Actions } from './$types';

export const actions = {
  default: async ({ request, cookies }) => {
    const data = await request.formData();
    const email = data.get('email');
    
    if (!email) {
      return fail(400, { email, missing: true });
    }
    
    // Process form...
    return { success: true };
  }
} satisfies Actions;
```

Progressive enhancement in component:
```svelte
<script>
import { enhance } from '$app/forms';
let { form } = $props();
</script>

<form method="POST" use:enhance>
  {#if form?.missing}
    <p class="error">Email required</p>
  {/if}
  <input name="email" type="email">
  <button>Submit</button>
</form>
```

**For detailed forms guide:** Read [references/forms-actions.md](references/forms-actions.md)

### 4. Styling

Svelte provides scoped styles by default:
```svelte
<div class="card" class:featured={isFeatured}>
  Content
</div>

<style>
.card { /* scoped to this component */ }
.featured { /* ... */ }
</style>
```

**For comprehensive styling guide:** Read [references/styling.md](references/styling.md)

## Common Patterns

### Authentication Guard

```typescript
// hooks.server.ts
export const handle: Handle = async ({ event, resolve }) => {
  event.locals.user = await getUserFromCookie(event.cookies);
  return resolve(event);
};
```

```typescript
// +layout.server.ts
import { redirect } from '@sveltejs/kit';

export const load: LayoutServerLoad = async ({ locals, url }) => {
  if (!locals.user && url.pathname.startsWith('/dashboard')) {
    redirect(307, '/login');
  }
  return { user: locals.user };
};
```

### API Routes

```typescript
// src/routes/api/posts/+server.ts
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async () => {
  const posts = await db.getPosts();
  return json(posts);
};

export const POST: RequestHandler = async ({ request }) => {
  const data = await request.json();
  const post = await db.createPost(data);
  return json(post, { status: 201 });
};
```

### Streaming Data

Return promises for progressive loading:
```typescript
export const load: PageServerLoad = async ({ params }) => {
  return {
    post: await getPost(params.slug),        // Blocks render
    comments: getComments(params.slug),      // Streams
    related: getRelatedPosts(params.slug)    // Streams
  };
};
```

```svelte
<article>{data.post.content}</article>

{#await data.comments}
  Loading...
{:then comments}
  {#each comments as comment}
    <div>{comment.text}</div>
  {/each}
{/await}
```

## Page Options

Configure rendering per route:
```typescript
// +page.js or +layout.js
export const prerender = true;    // Static generation
export const ssr = true;          // Server-side rendering
export const csr = true;          // Client-side rendering
export const trailingSlash = 'never';  // URL format
```

## State Management

### Component State (Runes)
```svelte
<script>
let count = $state(0);
let doubled = $derived(count * 2);
</script>
```

### Cross-Component State (Stores)
```typescript
// stores.js
import { writable } from 'svelte/store';
export const count = writable(0);
```

```svelte
<script>
import { count } from './stores';
</script>

<p>Count: {$count}</p>
<button onclick={() => $count++}>Increment</button>
```

## Deployment

### 1. Choose Adapter

```bash
npm install -D @sveltejs/adapter-auto      # Auto-detect
npm install -D @sveltejs/adapter-node      # Node.js
npm install -D @sveltejs/adapter-static    # Static
npm install -D @sveltejs/adapter-vercel    # Vercel
npm install -D @sveltejs/adapter-netlify   # Netlify
```

### 2. Configure

```javascript
// svelte.config.js
import adapter from '@sveltejs/adapter-auto';

export default {
  kit: {
    adapter: adapter()
  }
};
```

### 3. Build

```bash
npm run build
npm run preview  # Test production build
```

**For deployment details:** Read [references/deployment-config.md](references/deployment-config.md)

## Best Practices

### Component Design
- Use runes ($state, $derived) for local reactive state
- Prop destructuring: `let { title, count = 0 } = $props()`
- Keep components small and focused
- Use TypeScript for type safety

### Data Loading
- Use server loads for database/secrets
- Use universal loads for public APIs
- Avoid waterfalls with parallel loading
- Stream slow data with promises

### Forms
- Build forms that work without JavaScript first
- Progressively enhance with `use:enhance`
- Validate on both client and server
- Return validation errors with `fail()`

### Performance
- Enable prerendering where possible
- Use preload attributes on important links
- Lazy load heavy components
- Optimize images with @sveltejs/enhanced-img

### Type Safety
- Use generated `$types` for load functions
- Type component props properly
- Enable strict TypeScript checks

## Troubleshooting

### Common Issues

**"Cannot find module '$app/...'**: Run `npm run dev` to generate .svelte-kit directory

**Load function not running**: Check file naming (+page.js vs +page.svelte)

**Styles not scoped**: Ensure `<style>` tag is in .svelte file

**Form not submitting**: Verify `method="POST"` and action points to correct route

**Hydration mismatch**: Ensure SSR and CSR render same output

## Reference Documentation

For detailed information on specific topics, read the reference files:

1. **[runes-reactivity.md](references/runes-reactivity.md)** - Complete guide to Svelte 5 runes ($state, $derived, $effect, etc.) and stores
2. **[routing.md](references/routing.md)** - File-based routing, dynamic routes, layouts, and advanced patterns
3. **[data-loading.md](references/data-loading.md)** - Universal vs server loads, streaming, invalidation, and cookies
4. **[forms-actions.md](references/forms-actions.md)** - Form actions, validation, progressive enhancement
5. **[styling.md](references/styling.md)** - Scoped styles, global styles, CSS variables, Tailwind integration
6. **[deployment-config.md](references/deployment-config.md)** - Adapters, configuration, prerendering, SEO, service workers

## Migration from Svelte 4

Key changes in Svelte 5:
- `export let prop` → `let { prop } = $props()`
- `$: derived = value * 2` → `let derived = $derived(value * 2)`
- `$: { sideEffect }` → `$effect(() => { sideEffect })`
- Stores still work but runes are preferred for local state

## Additional Resources

### CLI Commands
```bash
# Create new project
npx sv create my-app

# Add integrations
npx sv add tailwindcss
npx sv add playwright
npx sv add vitest

# Development
npm run dev
npm run build
npm run preview
npm run check  # Type checking
```

### TypeScript Support
SvelteKit provides full TypeScript support with generated types. Use `./$types` imports for type-safe development.

### Community
- Discord: https://svelte.dev/chat
- GitHub Discussions: https://github.com/sveltejs/svelte/discussions
- Stack Overflow: Tag with `svelte` or `sveltekit`
