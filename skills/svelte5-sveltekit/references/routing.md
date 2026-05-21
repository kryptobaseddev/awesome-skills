# SvelteKit Routing

## Filesystem-Based Routing

Routes are defined by directories in `src/routes/`:
- `src/routes/` → `/`
- `src/routes/about/` → `/about`
- `src/routes/blog/[slug]/` → `/blog/:slug`
- `src/routes/blog/[...rest]/` → `/blog/*`

## Route Files

### +page.svelte
Defines a page component:
```svelte
<script>
let { data } = $props();
</script>

<h1>{data.title}</h1>
```

### +page.js / +page.ts
Universal load function (runs on server and client):
```typescript
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
  const res = await fetch(`/api/posts/${params.slug}`);
  const post = await res.json();
  return { post };
};

// Page options
export const prerender = true; // or false or 'auto'
export const ssr = true; // enable/disable SSR
export const csr = true; // enable/disable CSR
```

### +page.server.js / +page.server.ts
Server-only load function:
```typescript
import type { PageServerLoad } from './$types';
import { db } from '$lib/server/database';

export const load: PageServerLoad = async ({ params, cookies }) => {
  const post = await db.getPost(params.slug);
  return { post };
};
```

### +layout.svelte
Layout wrapper for nested routes:
```svelte
<script>
let { children, data } = $props();
</script>

<nav>{/* navigation */}</nav>
<main>{@render children()}</main>
<footer>{/* footer */}</footer>
```

### +layout.js / +layout.server.js
Layout data loading:
```typescript
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async () => {
  return {
    sections: [
      { slug: 'profile', title: 'Profile' },
      { slug: 'settings', title: 'Settings' }
    ]
  };
};
```

### +error.svelte
Error boundary:
```svelte
<script>
import { page } from '$app/state';
</script>

<h1>{page.status}: {page.error.message}</h1>
```

### +server.js / +server.ts
API endpoints:
```typescript
import type { RequestHandler } from './$types';
import { json } from '@sveltejs/kit';

export const GET: RequestHandler = async ({ params }) => {
  const data = await fetchData(params.id);
  return json(data);
};

export const POST: RequestHandler = async ({ request }) => {
  const data = await request.json();
  // process data
  return json({ success: true });
};
```

## Dynamic Routes

### Route Parameters
```
[slug]     → matches single segment: /blog/hello
[...rest]  → matches rest of path: /files/a/b/c
[[optional]] → optional parameter
```

### Param Matchers
Create custom matchers in `src/params/`:
```typescript
// src/params/uuid.ts
import type { ParamMatcher } from '@sveltejs/kit';

export const match: ParamMatcher = (param) => {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(param);
};

// Use: src/routes/users/[id=uuid]/
```

## Advanced Routing

### Route Groups
Organize routes without affecting URLs:
```
src/routes/
  (app)/
    dashboard/
    settings/
  (marketing)/
    about/
    pricing/
```

### Breaking Out of Layouts
Reset layouts with `@` prefix:
```
src/routes/
  +layout.svelte
  admin/
    +layout.svelte
    @/+page.svelte  ← uses root layout, not admin layout
```

### Multiple Named Layouts
```
src/routes/
  +layout.svelte
  +layout@named.svelte  ← named layout
  (group)@named/        ← uses named layout
```

### Optional Route Segments
```
[[lang]]/blog/[slug]
→ matches /blog/hello and /en/blog/hello
```

## Routing Hooks

### `$app/navigation`
```typescript
import { goto, invalidate, invalidateAll } from '$app/navigation';

// Navigate programmatically
goto('/dashboard');
goto('/dashboard', { replaceState: true });

// Invalidate data
invalidate('/api/data');
invalidate(url => url.pathname.startsWith('/api/'));
invalidateAll();
```

### `$app/state`
```typescript
import { page, navigating, updated } from '$app/state';

// Current page state
page.url      // URL object
page.params   // route parameters
page.route    // route info
page.status   // HTTP status
page.error    // error object
page.data     // combined load data
page.form     // form action data

// Navigation state
navigating.from  // previous page
navigating.to    // destination page
navigating.type  // navigation type

// Update availability
updated  // true when new version available
```

## Link Options

Control navigation behavior with data attributes:
```svelte
<!-- Reload from server -->
<a href="/path" data-sveltekit-reload>Link</a>

<!-- Replace history instead of push -->
<a href="/path" data-sveltekit-replacestate>Link</a>

<!-- Don't scroll to top -->
<a href="/path" data-sveltekit-noscroll>Link</a>

<!-- Keep focus on current element -->
<a href="/path" data-sveltekit-keepfocus>Link</a>

<!-- Preload data on hover/tap -->
<a href="/path" data-sveltekit-preload-data="hover">Link</a>

<!-- Preload code on hover/tap -->
<a href="/path" data-sveltekit-preload-code="hover">Link</a>
```

## Server-Only Routes

Create server-only routes with `+server.js`:
```typescript
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ url }) => {
  const min = Number(url.searchParams.get('min') ?? '0');
  const max = Number(url.searchParams.get('max') ?? '1');
  
  if (isNaN(min) || isNaN(max)) {
    error(400, 'Invalid parameters');
  }
  
  const random = min + Math.random() * (max - min);
  return new Response(String(random));
};
```

## Content Negotiation

+server.js handles non-HTML requests, +page.js handles HTML:
```
GET /api/data (Accept: application/json) → +server.js
GET /api/data (Accept: text/html) → +page.svelte (if exists)
```
