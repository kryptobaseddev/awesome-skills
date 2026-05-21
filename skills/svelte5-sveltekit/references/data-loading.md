# Data Loading in SvelteKit

## Load Functions

### Universal Load (+page.js, +layout.js)
Runs on both server and client:
```typescript
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch, parent, depends, url }) => {
  // fetch with SvelteKit features
  const res = await fetch(`/api/posts/${params.slug}`);
  const post = await res.json();
  
  // Access parent data
  const parentData = await parent();
  
  // Manual dependency tracking
  depends('app:posts');
  
  return { post, ...parentData };
};
```

### Server Load (+page.server.js, +layout.server.js)
Runs only on server:
```typescript
import type { PageServerLoad } from './$types';
import { db } from '$lib/server/database';
import { error } from '@sveltejs/kit';

export const load: PageServerLoad = async ({ params, cookies, locals, request }) => {
  // Direct database access
  const post = await db.getPost(params.slug);
  
  if (!post) {
    error(404, 'Post not found');
  }
  
  // Access cookies
  const sessionId = cookies.get('sessionid');
  
  // Access locals (from hooks)
  const user = locals.user;
  
  return { post, user };
};
```

## Load Event Properties

### Universal Load Properties
- `params` - Route parameters
- `route` - Route information (id, etc.)
- `url` - URL object (pathname, searchParams, etc.)
- `fetch` - Enhanced fetch function
- `setHeaders` - Set response headers (SSR only)
- `parent` - Access parent load data
- `depends` - Manual dependency tracking
- `untrack` - Exclude from dependency tracking
- `data` - Data from corresponding +page.server.js (if exists)

### Server Load Additional Properties
- `cookies` - Get/set cookies
- `locals` - Server-side shared data
- `platform` - Deployment platform adapter
- `request` - Request object
- `clientAddress` - Client IP address
- `isDataRequest` - Whether this is a data-only request
- `isSubRequest` - Whether this is a sub-request

## Load Strategies

### When to Use Universal Load
- Fetching from external APIs
- Client-side only data
- Returning non-serializable data (component constructors, functions)
- Data that needs to work offline

### When to Use Server Load
- Database access
- Private API keys/environment variables
- Server-only operations
- Authentication checks

## Loading Data

### Making Fetch Requests
```typescript
export const load: PageLoad = async ({ fetch }) => {
  // Inherits cookies/headers
  // Works with relative URLs on server
  // Response captured and inlined during SSR
  const res = await fetch('/api/posts');
  const posts = await res.json();
  return { posts };
};
```

### Setting Headers
```typescript
export const load: PageLoad = async ({ fetch, setHeaders }) => {
  const res = await fetch('https://api.example.com/data');
  
  // Cache the page for same duration as API response
  setHeaders({
    'cache-control': res.headers.get('cache-control')
  });
  
  return { data: await res.json() };
};
```

### Using Parent Data
```typescript
// +layout.server.js
export const load: LayoutServerLoad = async () => {
  return { theme: 'dark' };
};

// +page.js
export const load: PageLoad = async ({ parent }) => {
  const { theme } = await parent();
  // Avoid waterfall: fetch data first, then call parent if needed
  const data = await fetchData();
  const parentData = await parent();
  return { data, theme };
};
```

## Handling Errors

### Expected Errors
```typescript
import { error } from '@sveltejs/kit';

export const load: PageServerLoad = async ({ params }) => {
  const post = await db.getPost(params.slug);
  
  if (!post) {
    error(404, 'Post not found');
  }
  
  return { post };
};
```

### Unexpected Errors
```typescript
// Thrown errors are caught and handled as 500 errors
export const load: PageServerLoad = async () => {
  const data = await riskyOperation(); // might throw
  return { data };
};
```

## Redirects

```typescript
import { redirect } from '@sveltejs/kit';

export const load: LayoutServerLoad = async ({ locals }) => {
  if (!locals.user) {
    redirect(307, '/login');
  }
  
  return { user: locals.user };
};
```

## Streaming with Promises

Return unwrapped promises for streaming:
```typescript
export const load: PageServerLoad = async ({ params }) => {
  return {
    post: await getPost(params.slug),      // Blocks rendering
    comments: getComments(params.slug),    // Streams after initial render
    recommendations: getRecommendations()  // Also streams
  };
};
```

Use in components:
```svelte
<script>
let { data } = $props();
</script>

<article>{data.post.content}</article>

{#await data.comments}
  Loading comments...
{:then comments}
  {#each comments as comment}
    <div>{comment.text}</div>
  {/each}
{:catch error}
  Failed to load comments: {error.message}
{/await}
```

## Rerunning Load Functions

Load functions automatically rerun when:
1. Referenced `params` change
2. Referenced `url` properties change
3. `url.searchParams` accessed properties change
4. `await parent()` called and parent reruns
5. Manually invalidated with `invalidate()` or `invalidateAll()`

### Manual Invalidation
```typescript
import { invalidate, invalidateAll } from '$app/navigation';

// Invalidate specific URL
invalidate('/api/data');

// Invalidate custom dependency
invalidate('app:data');

// Invalidate all load functions
invalidateAll();

// Invalidate by pattern
invalidate(url => url.pathname.startsWith('/api/'));
```

### Manual Dependencies
```typescript
export const load: PageLoad = async ({ fetch, depends }) => {
  depends('app:posts'); // Custom identifier
  
  const res = await fetch('https://api.example.com/posts');
  return { posts: await res.json() };
};

// Later, trigger reload:
invalidate('app:posts');
```

### Untracking Dependencies
```typescript
export const load: PageLoad = async ({ untrack, url }) => {
  // Don't rerun when pathname changes
  if (untrack(() => url.pathname === '/')) {
    return { message: 'Welcome!' };
  }
};
```

## Cookies

Server load functions can read and write cookies:
```typescript
import { db } from '$lib/server/database';

export const load: LayoutServerLoad = async ({ cookies }) => {
  // Get cookie
  const sessionId = cookies.get('sessionid');
  
  // Set cookie
  cookies.set('visited', 'true', {
    path: '/',
    maxAge: 60 * 60 * 24 * 365, // 1 year
    httpOnly: true,
    secure: true,
    sameSite: 'lax'
  });
  
  // Delete cookie
  cookies.delete('sessionid', { path: '/' });
  
  const user = await db.getUser(sessionId);
  return { user };
};
```

## Type Safety with $types

```typescript
import type { PageLoad, PageData, PageProps } from './$types';

// Load function
export const load: PageLoad = async ({ params }) => {
  return { title: 'Hello', count: 42 };
};

// In component
let { data }: PageProps = $props();
// data.title is string
// data.count is number
```

## Accessing Page Data

### In Pages
```svelte
<script>
let { data } = $props();
</script>
```

### In Layouts
```svelte
<script>
// Layout gets its own data + children
let { data, children } = $props();
</script>
```

### Anywhere via page store
```svelte
<script>
import { page } from '$app/state';
// page.data contains all data from load functions
</script>

<title>{page.data.title}</title>
```

## Best Practices

1. **Avoid waterfalls**: Fetch data in parallel, call parent() last
2. **Use server loads for secrets**: Keep API keys and DB access server-side
3. **Stream slow data**: Return promises for non-essential data
4. **Cache appropriately**: Use setHeaders to control caching
5. **Handle errors gracefully**: Use error() for expected failures
6. **Type everything**: Use $types for full type safety
7. **Minimize reruns**: Be careful what you reference in load functions
8. **Return serializable data**: Server loads must return JSON-safe data
