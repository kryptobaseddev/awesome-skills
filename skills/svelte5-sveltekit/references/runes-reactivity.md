# Svelte 5 Runes and Reactivity

## Overview
Runes are symbols that control the Svelte compiler. They have a `$` prefix and look like functions but are keywords, not values.

## Core State Runes

### $state
Declare reactive state:
```svelte
<script>
let count = $state(0);
let user = $state({ name: 'Alice', age: 30 });
</script>
```

### $derived
Declare derived values that automatically update:
```svelte
<script>
let count = $state(0);
let doubled = $derived(count * 2);
let message = $derived(`Count is ${count}`);
</script>
```

### $effect
Run side effects when dependencies change:
```svelte
<script>
let count = $state(0);

$effect(() => {
  console.log(`Count changed to ${count}`);
  // Cleanup function (optional)
  return () => console.log('Cleanup');
});
</script>
```

### $props
Declare component props:
```svelte
<script>
let { title, count = 0, onClick } = $props();
// title is required
// count has default value
// onClick is optional callback
</script>
```

### $bindable
Create two-way bindable props:
```svelte
<script>
let { value = $bindable() } = $props();
// Parent can bind to this prop
</script>

<!-- Usage: <Component bind:value={myValue} /> -->
```

### $inspect
Debug reactive state (development only):
```svelte
<script>
let count = $state(0);
$inspect(count); // Logs to console when count changes
$inspect(count).with(console.trace); // Custom inspector
</script>
```

### $host
Access the component's host element (for custom elements):
```svelte
<script>
const element = $host();
</script>
```

## Stores for Cross-Component Reactivity

### Writable Stores
```javascript
import { writable } from 'svelte/store';

const count = writable(0);

// Subscribe
const unsubscribe = count.subscribe(value => console.log(value));

// Update
count.set(5);
count.update(n => n + 1);

// Unsubscribe
unsubscribe();
```

### Readable Stores
```javascript
import { readable } from 'svelte/store';

const time = readable(new Date(), (set) => {
  const interval = setInterval(() => set(new Date()), 1000);
  return () => clearInterval(interval);
});
```

### Derived Stores
```javascript
import { derived } from 'svelte/store';

const doubled = derived(count, $count => $count * 2);
```

### Custom Stores
Any object with a subscribe method is a store:
```javascript
function createCounter() {
  const { subscribe, set, update } = writable(0);
  
  return {
    subscribe,
    increment: () => update(n => n + 1),
    decrement: () => update(n => n - 1),
    reset: () => set(0)
  };
}
```

### Store Context with $state
Combine stores with runes for reactive cross-component state:
```svelte
<!-- store.svelte.js -->
<script>
export const userStore = $state({ name: '', loggedIn: false });
</script>

<!-- ComponentA.svelte -->
<script>
import { userStore } from './store.svelte.js';
// userStore is reactive across all components
</script>
```

## Auto-Subscription in Templates
Use `$` prefix to auto-subscribe to stores in templates:
```svelte
<script>
import { count } from './stores.js';
</script>

<p>Count: {$count}</p>
<!-- Automatically subscribes and unsubscribes -->
```

## Reactivity Rules

1. Runes are compile-time keywords, not runtime values
2. `$state` creates reactive state - mutations are tracked
3. `$derived` recalculates when dependencies change
4. `$effect` runs after DOM updates
5. Assignment triggers reactivity: `count += 1` works
6. Array/object mutations tracked: `arr.push(item)` triggers updates
7. Stores require explicit subscription or `$` syntax

## Migration from Svelte 4

### Svelte 4 Pattern
```svelte
<script>
export let title;
export let count = 0;
let doubled;
$: doubled = count * 2;
$: console.log('Count changed:', count);
</script>
```

### Svelte 5 Pattern
```svelte
<script>
let { title, count = 0 } = $props();
let doubled = $derived(count * 2);
$effect(() => console.log('Count changed:', count));
</script>
```
