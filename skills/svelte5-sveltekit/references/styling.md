# Styling in Svelte

## Scoped Styles

Component styles are scoped by default:
```svelte
<script>
let { title } = $props();
</script>

<h1>{title}</h1>

<style>
/* Only affects h1 in this component */
h1 {
  color: purple;
  font-size: 2em;
}
</style>
```

Svelte adds a unique class (e.g., `svelte-abc123`) to elements and scopes CSS accordingly.

## Global Styles

### :global() Modifier
Style elements globally:
```svelte
<style>
:global(body) {
  background: black;
  color: white;
}

/* Target global class */
:global(.error) {
  color: red;
}

/* Mixed: scoped selector with global target */
.container :global(.error) {
  padding: 1em;
}
</style>
```

### Global Stylesheets
Import in root layout:
```svelte
<!-- +layout.svelte -->
<script>
import '$lib/styles/global.css';
let { children } = $props();
</script>

{@render children()}
```

## CSS Custom Properties

Pass reactive values to CSS:
```svelte
<script>
let color = $state('red');
let size = $state(16);
</script>

<div class="box" style:background-color={color} style:font-size="{size}px">
  Styled box
</div>

<!-- or with CSS variables -->
<div class="box" style="--color: {color}; --size: {size}px">
  Styled box
</div>

<style>
.box {
  background-color: var(--color);
  font-size: var(--size);
}
</style>
```

### Component-Level Variables
```svelte
<script>
let { theme = 'light' } = $props();
</script>

<div class="component">
  <slot />
</div>

<style>
.component {
  --primary: var(--theme-primary, #4a5568);
  --background: var(--theme-background, white);
  
  background: var(--background);
  color: var(--primary);
}
</style>
```

## Class Directives

### Dynamic Classes
```svelte
<script>
let active = $state(false);
let urgent = $state(true);
</script>

<!-- Add class conditionally -->
<div class:active={active} class:urgent>
  Content
</div>

<!-- Shorthand when variable name matches class -->
<div class:active class:urgent>
  Content
</div>
```

### Class String Composition
```svelte
<script>
let variant = $state('primary');
let size = $state('large');
</script>

<button class="btn {variant} {size}">
  Click me
</button>

<!-- or with conditional -->
<button class="btn" class:primary={variant === 'primary'}>
  Click me
</button>
```

## Style Directives

Apply inline styles reactively:
```svelte
<script>
let x = $state(0);
let color = $state('red');
</script>

<!-- Individual properties -->
<div style:transform="translate({x}px, 0)" style:color>
  Moved element
</div>

<!-- With important -->
<div style:color|important={color}>
  Important color
</div>
```

## Nested Style Elements

Multiple `<style>` blocks in one component:
```svelte
<style>
/* Styles for light theme */
.light-theme {
  --bg: white;
  --text: black;
}
</style>

<style>
/* Styles for dark theme */
.dark-theme {
  --bg: black;
  --text: white;
}
</style>

<div class="theme">
  Content
</div>

<style>
.theme {
  background: var(--bg);
  color: var(--text);
}
</style>
```

## CSS Preprocessors

### Setup (e.g., Sass)
```bash
npm install -D sass
```

```svelte
<style lang="scss">
$primary: #4a5568;

.component {
  background: $primary;
  
  &:hover {
    background: darken($primary, 10%);
  }
  
  .nested {
    color: lighten($primary, 20%);
  }
}
</style>
```

## Tailwind CSS Integration

### Setup
```bash
npx sv add tailwindcss
```

### Usage
```svelte
<script>
let active = $state(false);
</script>

<div class="p-4 bg-white rounded-lg shadow-md">
  <h1 class="text-2xl font-bold text-gray-900">
    Title
  </h1>
  <button 
    class="px-4 py-2 rounded"
    class:bg-blue-500={active}
    class:bg-gray-300={!active}
  >
    Toggle
  </button>
</div>
```

### Conditional Tailwind Classes
```svelte
<script>
let variant = $state<'primary' | 'secondary'>('primary');

const buttonClasses = $derived(
  variant === 'primary' 
    ? 'bg-blue-500 hover:bg-blue-600' 
    : 'bg-gray-500 hover:bg-gray-600'
);
</script>

<button class="px-4 py-2 rounded {buttonClasses}">
  Click me
</button>
```

## CSS Modules

```svelte
<script>
import styles from './Component.module.css';
</script>

<div class={styles.container}>
  <h1 class={styles.title}>Title</h1>
</div>
```

## Animation

### Transition Directive
```svelte
<script>
import { fade, fly, slide } from 'svelte/transition';
let visible = $state(true);
</script>

{#if visible}
  <div transition:fade>
    Fades in and out
  </div>
{/if}

{#if visible}
  <div transition:fly={{ y: 200, duration: 300 }}>
    Flies in and out
  </div>
{/if}
```

### In/Out Transitions
```svelte
<script>
import { fade, fly } from 'svelte/transition';
let visible = $state(true);
</script>

{#if visible}
  <div in:fly={{ y: 200 }} out:fade>
    Different in/out animations
  </div>
{/if}
```

### Animation Directive
```svelte
<script>
import { flip } from 'svelte/animate';

let items = $state([1, 2, 3, 4, 5]);

function shuffle() {
  items = items.sort(() => Math.random() - 0.5);
}
</script>

<button onclick={shuffle}>Shuffle</button>

{#each items as item (item)}
  <div animate:flip={{ duration: 300 }}>
    {item}
  </div>
{/each}
```

### CSS Animations
```svelte
<div class="animated">
  Content
</div>

<style>
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.animated {
  animation: pulse 2s infinite;
}
</style>
```

## Component Styling Patterns

### CSS Variables for Theming
```svelte
<!-- ThemeProvider.svelte -->
<div class="theme-provider" style="
  --primary: {theme.primary};
  --secondary: {theme.secondary};
  --background: {theme.background};
">
  {@render children()}
</div>

<style>
.theme-provider {
  width: 100%;
  height: 100%;
}
</style>
```

### Style Props Pattern
```svelte
<script>
let {
  background = '#fff',
  color = '#000',
  padding = '1rem',
  ...rest
} = $props();
</script>

<div
  {...rest}
  style:background
  style:color
  style:padding
>
  <slot />
</div>
```

### Composable Style Classes
```svelte
<script>
let { variant = 'default', size = 'medium', class: className = '' } = $props();

const classes = $derived([
  'button',
  `button--${variant}`,
  `button--${size}`,
  className
].join(' '));
</script>

<button class={classes}>
  <slot />
</button>

<style>
.button {
  /* Base styles */
}
.button--primary { /* ... */ }
.button--secondary { /* ... */ }
.button--small { /* ... */ }
.button--medium { /* ... */ }
.button--large { /* ... */ }
</style>
```

## Best Practices

1. **Prefer scoped styles**: Use component styles by default
2. **CSS custom properties for themes**: Flexible and maintainable
3. **Minimize global styles**: Only for true global elements
4. **Use class directives**: More performant than inline conditionals
5. **Leverage Tailwind or CSS-in-JS**: For utility-first or dynamic styling
6. **Keep specificity low**: Avoid deep nesting
7. **Use CSS variables for dynamic values**: Better than inline styles
8. **Animate with transitions**: Built-in Svelte features are optimized
9. **Component-scoped design tokens**: Pass through props or CSS vars
10. **Test accessibility**: Ensure sufficient contrast, focus states
