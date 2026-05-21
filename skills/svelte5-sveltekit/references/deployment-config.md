# Deployment, Adapters, and Configuration

## Adapters

Adapters transform SvelteKit apps for different deployment platforms.

### Installation
```bash
npm install -D @sveltejs/adapter-auto        # Auto-detects platform
npm install -D @sveltejs/adapter-node        # Node.js server
npm install -D @sveltejs/adapter-static      # Static site generation
npm install -D @sveltejs/adapter-vercel      # Vercel
npm install -D @sveltejs/adapter-netlify     # Netlify
npm install -D @sveltejs/adapter-cloudflare  # Cloudflare Pages/Workers
```

### Configuration (svelte.config.js)
```javascript
import adapter from '@sveltejs/adapter-auto';

export default {
  kit: {
    adapter: adapter()
  }
};
```

### Adapter-Specific Options

#### adapter-node
```javascript
import adapter from '@sveltejs/adapter-node';

export default {
  kit: {
    adapter: adapter({
      out: 'build',
      precompress: true,
      envPrefix: 'MY_'
    })
  }
};
```

#### adapter-static
```javascript
import adapter from '@sveltejs/adapter-static';

export default {
  kit: {
    adapter: adapter({
      pages: 'build',
      assets: 'build',
      fallback: '404.html', // SPA mode
      precompress: false,
      strict: true
    })
  }
};
```

#### adapter-vercel
```javascript
import adapter from '@sveltejs/adapter-vercel';

export default {
  kit: {
    adapter: adapter({
      runtime: 'nodejs20.x',
      regions: ['iad1'],
      split: false
    })
  }
};
```

## Page Options

Configure rendering per route in `+page.js` or `+layout.js`:

### prerender
```typescript
// Prerender at build time
export const prerender = true;

// Don't prerender
export const prerender = false;

// Auto-detect (default)
export const prerender = 'auto';
```

### ssr
```typescript
// Server-side rendering enabled (default)
export const ssr = true;

// Client-side only (SPA mode)
export const ssr = false;
```

### csr
```typescript
// Client-side rendering enabled (default)
export const csr = true;

// No client-side JS
export const csr = false;
```

### trailingSlash
```typescript
// URLs: /about/
export const trailingSlash = 'always';

// URLs: /about
export const trailingSlash = 'never';

// URLs: /about or /about/ (both work)
export const trailingSlash = 'ignore';
```

## Environment Variables

### Public Variables
Accessible in browser and server:
```bash
# .env
PUBLIC_API_URL=https://api.example.com
PUBLIC_ANALYTICS_ID=abc123
```

```typescript
import { PUBLIC_API_URL } from '$env/static/public';
// or
import { env } from '$env/dynamic/public';
console.log(env.PUBLIC_API_URL);
```

### Private Variables
Server-only:
```bash
# .env
DATABASE_URL=postgres://...
API_SECRET=secret123
```

```typescript
import { DATABASE_URL } from '$env/static/private';
// or
import { env } from '$env/dynamic/private';
console.log(env.DATABASE_URL);
```

### Static vs Dynamic
- `static`: Replaced at build time, faster
- `dynamic`: Read at runtime, flexible

## Project Configuration

### svelte.config.js
```javascript
import adapter from '@sveltejs/adapter-auto';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

export default {
  preprocess: vitePreprocess(),
  
  kit: {
    adapter: adapter(),
    
    // Aliases
    alias: {
      $components: 'src/lib/components',
      $utils: 'src/lib/utils'
    },
    
    // App directory (default: 'src')
    appDir: '_app',
    
    // Asset paths
    paths: {
      base: process.env.NODE_ENV === 'production' ? '/my-app' : '',
      assets: 'https://cdn.example.com'
    },
    
    // CSP configuration
    csp: {
      mode: 'auto',
      directives: {
        'script-src': ['self']
      }
    },
    
    // Service worker
    serviceWorker: {
      register: true,
      files: (filepath) => !/\.DS_Store/.test(filepath)
    },
    
    // TypeScript
    typescript: {
      config: (config) => {
        // Modify config
        return config;
      }
    },
    
    // Version management
    version: {
      name: process.env.npm_package_version,
      pollInterval: 60000
    }
  }
};
```

### vite.config.js
```javascript
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  
  server: {
    port: 3000,
    strictPort: false
  },
  
  optimizeDeps: {
    include: ['some-package']
  },
  
  ssr: {
    noExternal: ['package-name']
  }
});
```

## Prerendering

### Enable Prerendering
```typescript
// +page.js
export const prerender = true;
```

### Prerender Entire Site
```typescript
// src/routes/+layout.js
export const prerender = true;
```

### Exclude Specific Pages
```typescript
// src/routes/dashboard/+page.js
export const prerender = false;
```

### Prerender Paths
```typescript
// +page.server.js
export const prerender = true;

export const entries = () => {
  return [
    { slug: 'hello-world' },
    { slug: 'another-post' }
  ];
};
```

### Crawl for Prerender
```javascript
// svelte.config.js
export default {
  kit: {
    prerender: {
      crawl: true,
      entries: ['*'],
      handleHttpError: 'warn'
    }
  }
};
```

## Performance Optimization

### Code Splitting
Automatic per-route code splitting. Manual chunks:
```typescript
// Lazy load components
const HeavyComponent = await import('$lib/HeavyComponent.svelte');
```

### Preloading
```svelte
<a href="/dashboard" data-sveltekit-preload-data="hover">
  Dashboard
</a>
```

Options:
- `hover` - Preload on hover
- `tap` - Preload on touch/click (mobile)
- `viewport` - Preload when in viewport
- `off` - Disable preloading

### Image Optimization
```typescript
// Use @sveltejs/enhanced-img
import { Image } from '@sveltejs/enhanced-img';
```

```svelte
<Image src={myImage} alt="Description" />
```

## SEO

### Meta Tags
```svelte
<svelte:head>
  <title>{title}</title>
  <meta name="description" content={description} />
  <meta property="og:title" content={title} />
  <meta property="og:description" content={description} />
  <meta property="og:image" content={imageUrl} />
  <meta name="twitter:card" content="summary_large_image" />
  <link rel="canonical" href={canonicalUrl} />
</svelte:head>
```

### Sitemap
Generate in `+server.js`:
```typescript
// src/routes/sitemap.xml/+server.ts
export async function GET() {
  const posts = await getPosts();
  
  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      ${posts.map(post => `
        <url>
          <loc>https://example.com/blog/${post.slug}</loc>
          <lastmod>${post.updated}</lastmod>
        </url>
      `).join('')}
    </urlset>`;
  
  return new Response(sitemap, {
    headers: {
      'Content-Type': 'application/xml'
    }
  });
}
```

### robots.txt
```typescript
// src/routes/robots.txt/+server.ts
export function GET() {
  return new Response(`
User-agent: *
Allow: /
Sitemap: https://example.com/sitemap.xml
  `.trim());
}
```

## Service Workers

Create service worker in `src/service-worker.js`:
```javascript
import { build, files, version } from '$service-worker';

const CACHE = `cache-${version}`;
const ASSETS = [...build, ...files];

self.addEventListener('install', (event) => {
  async function addFilesToCache() {
    const cache = await caches.open(CACHE);
    await cache.addAll(ASSETS);
  }
  
  event.waitUntil(addFilesToCache());
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  
  async function respond() {
    const cache = await caches.open(CACHE);
    const cached = await cache.match(event.request);
    
    if (cached) return cached;
    
    const response = await fetch(event.request);
    cache.put(event.request, response.clone());
    
    return response;
  }
  
  event.respondWith(respond());
});
```

## Testing

### Unit Tests (Vitest)
```typescript
// src/lib/utils.test.ts
import { describe, it, expect } from 'vitest';
import { formatDate } from './utils';

describe('formatDate', () => {
  it('formats dates correctly', () => {
    const date = new Date('2024-01-01');
    expect(formatDate(date)).toBe('January 1, 2024');
  });
});
```

### Integration Tests (Playwright)
```typescript
// tests/home.spec.ts
import { expect, test } from '@playwright/test';

test('home page loads', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle('My App');
});
```

## Deployment Checklist

1. ✅ Set environment variables
2. ✅ Configure adapter for platform
3. ✅ Enable prerendering where applicable
4. ✅ Configure CSP headers
5. ✅ Set up error tracking (Sentry, etc.)
6. ✅ Configure caching headers
7. ✅ Test in production mode locally
8. ✅ Enable compression (gzip/brotli)
9. ✅ Configure CDN for static assets
10. ✅ Set up monitoring and analytics
