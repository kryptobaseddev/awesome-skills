# Form Actions in SvelteKit

## Overview
Form actions allow posting data to the server using native `<form>` elements. They work without JavaScript but can be progressively enhanced.

## Default Actions

```typescript
// +page.server.ts
import type { Actions } from './$types';

export const actions = {
  default: async ({ request, cookies }) => {
    const data = await request.formData();
    const email = data.get('email');
    const password = data.get('password');
    
    // Process login
    const user = await authenticateUser(email, password);
    cookies.set('sessionid', user.sessionId, { path: '/' });
    
    return { success: true };
  }
} satisfies Actions;
```

Usage:
```svelte
<form method="POST">
  <input name="email" type="email" required>
  <input name="password" type="password" required>
  <button>Log in</button>
</form>
```

## Named Actions

```typescript
export const actions = {
  login: async ({ request, cookies }) => {
    // Handle login
  },
  register: async ({ request }) => {
    // Handle registration
  },
  logout: async ({ cookies }) => {
    cookies.delete('sessionid', { path: '/' });
  }
} satisfies Actions;
```

Usage:
```svelte
<!-- Invoke named action with ?/ prefix -->
<form method="POST" action="?/login">
  <button>Log in</button>
</form>

<form method="POST" action="?/register">
  <button>Register</button>
</form>

<!-- Or use formaction on button -->
<form method="POST" action="?/login">
  <button>Log in</button>
  <button formaction="?/register">Register</button>
</form>
```

## Action Anatomy

Actions receive a RequestEvent object:
```typescript
import type { RequestEvent } from '@sveltejs/kit';

export const actions = {
  default: async (event: RequestEvent) => {
    const {
      request,      // Request object
      cookies,      // Cookie handler
      locals,       // App.Locals from hooks
      params,       // Route parameters
      url,          // URL object
      platform,     // Platform adapter
      getClientAddress // Get client IP
    } = event;
    
    // Get form data
    const data = await request.formData();
    const name = data.get('name') as string;
    
    // Return data for the page
    return { success: true, name };
  }
};
```

## Validation and Errors

Use `fail()` to return validation errors:
```typescript
import { fail } from '@sveltejs/kit';
import type { Actions } from './$types';

export const actions = {
  default: async ({ request }) => {
    const data = await request.formData();
    const email = data.get('email');
    const password = data.get('password');
    
    // Validation
    if (!email) {
      return fail(400, { email, missing: true });
    }
    
    if (typeof password !== 'string' || password.length < 8) {
      return fail(400, { email, passwordTooShort: true });
    }
    
    // Authenticate
    const user = await db.getUser(email);
    if (!user || user.password !== hash(password)) {
      return fail(400, { email, incorrect: true });
    }
    
    // Success
    return { success: true };
  }
} satisfies Actions;
```

Display errors in template:
```svelte
<script>
let { form } = $props();
</script>

<form method="POST">
  {#if form?.missing}
    <p class="error">Email is required</p>
  {/if}
  {#if form?.passwordTooShort}
    <p class="error">Password must be at least 8 characters</p>
  {/if}
  {#if form?.incorrect}
    <p class="error">Invalid credentials</p>
  {/if}
  
  <input name="email" type="email" value={form?.email ?? ''}>
  <input name="password" type="password">
  <button>Submit</button>
</form>
```

## Redirects

```typescript
import { redirect } from '@sveltejs/kit';

export const actions = {
  login: async ({ cookies, request, url }) => {
    const data = await request.formData();
    const user = await authenticateUser(data);
    
    cookies.set('sessionid', user.sessionId, { path: '/' });
    
    // Redirect after successful login
    if (url.searchParams.has('redirectTo')) {
      redirect(303, url.searchParams.get('redirectTo'));
    }
    
    redirect(303, '/dashboard');
  }
} satisfies Actions;
```

Common redirect status codes:
- `303` - See Other (GET request, most common for form redirects)
- `307` - Temporary Redirect (preserves method)
- `308` - Permanent Redirect (preserves method)

## Progressive Enhancement

### Basic Enhancement
```svelte
<script>
import { enhance } from '$app/forms';
let { form } = $props();
</script>

<form method="POST" use:enhance>
  <!-- Form content -->
</form>
```

Without arguments, `use:enhance`:
- Updates `form` prop and `page.form` on response
- Resets the form on success
- Invalidates all data
- Handles redirects
- Shows nearest error boundary on failure

### Custom Enhancement
```svelte
<script>
import { enhance } from '$app/forms';

let submitting = $state(false);
</script>

<form
  method="POST"
  use:enhance={({ formData, formElement, cancel, submitter }) => {
    // Before submission
    submitting = true;
    
    // Modify form data
    formData.append('timestamp', new Date().toISOString());
    
    // Optionally cancel
    // cancel();
    
    return async ({ result, update }) => {
      // After submission
      submitting = false;
      
      if (result.type === 'success') {
        // Custom success handling
        console.log('Success!', result.data);
      }
      
      // Trigger default behavior
      await update();
    };
  }}
>
  <button disabled={submitting}>
    {submitting ? 'Submitting...' : 'Submit'}
  </button>
</form>
```

### applyAction
Control exactly what happens after submission:
```svelte
<script>
import { enhance, applyAction } from '$app/forms';
import { invalidateAll } from '$app/navigation';
</script>

<form
  method="POST"
  use:enhance={() => {
    return async ({ result }) => {
      if (result.type === 'redirect') {
        goto(result.location);
      } else if (result.type === 'error') {
        // Custom error handling
        showErrorToast(result.error.message);
      } else {
        await applyAction(result);
      }
    };
  }}
>
```

### Manual Submission
For complete control:
```svelte
<script>
import { deserialize, applyAction } from '$app/forms';
import { invalidateAll } from '$app/navigation';

let submitting = $state(false);

async function handleSubmit(event: SubmitEvent & { 
  currentTarget: EventTarget & HTMLFormElement 
}) {
  event.preventDefault();
  submitting = true;
  
  const data = new FormData(event.currentTarget);
  
  const response = await fetch(event.currentTarget.action, {
    method: 'POST',
    body: data
  });
  
  const result = deserialize(await response.text());
  
  if (result.type === 'success') {
    await invalidateAll();
  }
  
  await applyAction(result);
  submitting = false;
}
</script>

<form method="POST" onsubmit={handleSubmit}>
  <!-- Form content -->
</form>
```

## Loading Data After Actions

After an action runs, the page's load functions rerun. Access action result via `form` prop:
```svelte
<script>
let { data, form } = $props();
</script>

{#if form?.success}
  <p class="success">Welcome back, {data.user.name}!</p>
{/if}
```

## File Uploads

```typescript
export const actions = {
  upload: async ({ request }) => {
    const data = await request.formData();
    const file = data.get('file') as File;
    
    if (!file) {
      return fail(400, { missing: true });
    }
    
    // Save file
    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);
    await saveFile(file.name, buffer);
    
    return { success: true, filename: file.name };
  }
} satisfies Actions;
```

```svelte
<form method="POST" action="?/upload" enctype="multipart/form-data">
  <input name="file" type="file" required>
  <button>Upload</button>
</form>
```

## Posting to +server.js

To POST to an action instead of a +server.js endpoint:
```typescript
const response = await fetch('/path', {
  method: 'POST',
  body: data,
  headers: {
    'x-sveltekit-action': 'true'  // Routes to action
  }
});
```

## Best Practices

1. **Validate on both client and server**: Client for UX, server for security
2. **Return meaningful errors**: Include field-specific validation messages
3. **Preserve form values on error**: Return failed values so users don't retype
4. **Use 303 redirects**: After successful POST, redirect to prevent resubmission
5. **Progressive enhancement first**: Build forms that work without JS
6. **Handle edge cases**: Loading states, disabled buttons, error boundaries
7. **Consider CSRF**: Use SvelteKit's built-in CSRF protection (automatic)
8. **Rate limiting**: Implement on server for production apps

## GET vs POST

Use `method="POST"` for forms that change data (actions).
Use `method="GET"` (or no method) for search/filter forms:
```svelte
<!-- Search form - uses GET, no action needed -->
<form action="/search">
  <input name="q" placeholder="Search...">
  <button>Search</button>
</form>
```

This will navigate to `/search?q=...` and invoke the load function.
