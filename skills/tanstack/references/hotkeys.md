# TanStack Hotkeys

> Verified 2026-10-07 against `@tanstack/hotkeys@0.11.0` / `@tanstack/react-hotkeys@0.13.0` docs (TanStack CLI 0.71.1). Pre-1.0: minors break. Re-check with `tanstack doc hotkeys <path>` when the installed version differs.

## Contents
When to use · Packages · Mental model · Core API · Patterns · Traps · Migration notes · Go deeper

## When to use / when not to
- Use for: app keyboard shortcuts (`Mod+S`), Vim/VS Code-style sequences (`g g`, `Mod+K Mod+C`), user-rebindable shortcuts (recorder), shortcut help palettes built from live registrations, held-modifier hints, and platform-correct `<kbd>` labels.
- Skip for: plain `onKeyDown` on one input (Enter-to-submit inside a form), or typing behavior inside an editor component that already owns its keymap (CodeMirror, ProseMirror).
- It is headless: no UI, no command palette component. You render everything.

## Packages
| Package | Notes |
|---|---|
| `@tanstack/react-hotkeys` | Hooks + `HotkeysProvider`. Re-exports all of `@tanstack/hotkeys`, so no separate core install is needed. Peer `react >=16.8` |
| `@tanstack/hotkeys` | Vanilla core: `HotkeyManager`, `SequenceManager`, `createSequenceMatcher`, `formatForDisplay`, `parseHotkey`, `getKeyStateTracker` |
| Other adapters | `@tanstack/{preact,solid,vue,svelte,angular,lit,alpine,ember,octane}-hotkeys` |
| Devtools | `@tanstack/react-hotkeys-devtools` + `@tanstack/react-devtools` (no-ops in production; explicit `/production` export exists) |

ESM-only, ES2022, Node >= 20 (since hotkeys 0.10 / react-hotkeys 0.12).
```bash
npm i @tanstack/react-hotkeys
npm i -D @tanstack/react-devtools @tanstack/react-hotkeys-devtools
```

## Mental model
- `useHotkey` registers with a singleton `HotkeyManager`, which attaches listeners per target (default `document`). Unmount unregisters. The callback is synced every render, so there are no stale closures.
- A binding is **logical** (`'Mod+S'`, `{ key: 'S', mod: true }`), matched on `event.key` and layout-aware. Or it is **physical** (`'Mod+[KeyS]'`, `{ code: 'KeyS', mod: true }`), matched on exact `event.code`. Brackets mean physical.
- `Mod` = Command on macOS, Control elsewhere.
- Sequences go through a singleton `SequenceManager`, which tracks per-sequence progress with a timeout between steps (default 1000 ms).
- "Scope" means `target` (element or ref) + `enabled`. There is no named-scope stack. `meta.group` is descriptive only.
- `HotkeysProvider defaultOptions={{ hotkey, hotkeySequence, hotkeyRecorder, ... }}` sets defaults. Hook options win.
- While a recorder is active, every registered hotkey/sequence callback is suppressed automatically.

## Core API
```tsx
import { useHotkey } from '@tanstack/react-hotkeys'

useHotkey('Mod+S', (event, context) => save(), {
  enabled: true,           // disabled stays registered (visible in devtools), just doesn't fire
  preventDefault: true,    // default true
  stopPropagation: true,   // default true
  eventType: 'keydown',    // or 'keyup'
  requireReset: false,     // true = once per physical press, ignores key repeat
  ignoreInputs: undefined, // smart default (see Traps)
  target: document,        // element, document, window, or a React ref
  conflictBehavior: 'warn',// 'error' | 'replace' | 'allow'
  platform: undefined,     // auto-detect; 'mac' etc. for tests
  meta: { name: 'Save', description: 'Save the document', group: 'File' },
})
```
`context.hotkey` is the string and `context.parsedHotkey` is a `ParsedHotkey`, a union with `key` **or** `code`. Narrow with `parsed.code !== undefined`.

Hooks (React):
| Hook | Purpose |
|---|---|
| `useHotkey(binding, cb, opts?)` | one shortcut |
| `useHotkeys(defs, commonOpts?)` | array `{ hotkey, callback, options? }`, for dynamic lists |
| `useHotkeySequence(steps, cb, opts?)` | one sequence (`timeout`, `enabled`, `meta`) |
| `useHotkeySequences(defs, commonOpts?)` | array `{ sequence, callback, options? }` |
| `useHotkeyRecorder(opts)` | `{ isRecording, recordedHotkey, startRecording, stopRecording, cancelRecording }` |
| `useHotkeySequenceRecorder(opts)` | sequence recorder |
| `useHeldKeys()` / `useHeldKeyCodes()` / `useKeyHold(key)` | live key state |
| `useHotkeyHint(binding, { exact?, platform? })` | true while relevant modifiers are held |
| `useHotkeyRegistrations()` | `{ hotkeys, sequences }` live registrations for help UIs |

Non-hook: `formatForDisplay(binding, { platform?, parts?, useSymbols?, separatorToken?, layoutMap?, keyLabels? })`, `formatWithLabels`, `getHotkeyManager()`, `getKeyStateTracker()`, `createSequenceMatcher(steps, { timeout })`, `matchesHeldModifiers`, `findHotkeyConflicts`.

Other adapters: Solid uses `create*`, Angular `inject*`, Svelte its own runes-based API, Lit uses controllers (`HotkeySequenceController`), and Ember uses template helpers plus `onHotkey` modifiers. Binding syntax is identical everywhere.

## Patterns
**1. Editor shortcuts with a dynamic list**
```tsx
useHotkeys(
  items.map((item) => ({ hotkey: item.shortcut, callback: item.action, options: { enabled: item.enabled, meta: { name: item.label } } })),
  { preventDefault: true },
)
```
**2. Modal-scoped Escape**
```tsx
useHotkey('Escape', onClose, { enabled: isOpen, requireReset: true })
// or element-scoped:
const ref = useRef<HTMLDivElement>(null)
useHotkey('Escape', closePanel, { target: ref })
return <div ref={ref} tabIndex={0}>...</div>   // target must be focusable
```
**3. Sequences**
```tsx
useHotkeySequence(['G', 'G'], scrollToTop)
useHotkeySequence(['Mod+K', 'Mod+C'], commentSelection)       // VS Code chord
useHotkeySequences([{ sequence: ['D', 'D'], callback: deleteLine, options: { timeout: 500 } }])
```
Sequences can share prefixes (`dd`, `dw`, `diw`). Modifier-only presses, IME composition and key repeats neither advance nor reset progress.

**4. User-rebindable shortcut**
```tsx
const [binding, setBinding] = useState<string>('Mod+K')
useHotkey(binding, openPalette)
const rec = useHotkeyRecorder({ onRecord: setBinding, onClear: () => setBinding('Mod+K') })
<button onClick={rec.isRecording ? rec.stopRecording : rec.startRecording}>
  {rec.isRecording ? 'Press keys...' : formatForDisplay(binding)}
</button>
```
The recorder stores physical strings such as `Mod+[KeyK]` by default. Pass `recordBy: 'key'` for logical. Escape cancels and Backspace/Delete clears. You persist the string in your own state.

**5. Shortcut help palette**
```tsx
const { hotkeys, sequences } = useHotkeyRegistrations()
hotkeys.map((r) => <li key={r.id}><kbd>{formatForDisplay(r.hotkey)}</kbd> {r.options.meta?.name}</li>)
sequences.map((r) => <li key={r.id}>{r.sequence.map((s) => formatForDisplay(s)).join(' → ')}</li>)
```
Extend `HotkeyMeta` via `declare module '@tanstack/hotkeys' { interface HotkeyMeta { icon?: string } }`.

**6. Display labels**
```ts
formatForDisplay('Mod+S', { platform: 'mac' })                  // '⌘ S'
formatForDisplay('Mod+S', { platform: 'windows' })              // 'Ctrl+S'
formatForDisplay('Mod+[KeyS]', { platform: 'mac', parts: true }) // ['⌘', 'S'] -> one <kbd> each
```

**Devtools**
```tsx
import { TanStackDevtools } from '@tanstack/react-devtools'
import { hotkeysDevtoolsPlugin } from '@tanstack/react-hotkeys-devtools'
<TanStackDevtools plugins={[hotkeysDevtoolsPlugin()]} />
```

## Traps
1. **Hijacking typing.** Single keys (`'K'`, `'/'`) and `Shift`/`Alt` combos are ignored by default while focus is in a text input, textarea, select or contentEditable. `Ctrl`/`Meta` combos and `Escape` **do** fire there. If you set `ignoreInputs: false` on a single-letter shortcut, users can no longer type that letter. Button-type inputs never block. Since 0.6.2 the check uses `document.activeElement`. (`framework/react/guides/hotkeys`)
2. **`preventDefault` and `stopPropagation` default to true.** Binding a browser or OS-standard key (`Mod+F`, `Mod+C`, `Tab`, `Space`) silently removes native behavior and can break accessibility, for example keyboard users who need Tab and Space. Opt out with `preventDefault: false`, or choose non-conflicting combos. Never bind bare `Tab`. (`framework/react/guides/hotkeys`)
3. **Ref target not focusable.** `target: ref` only receives events when focus is inside that element. Give the element `tabIndex`. (`framework/react/quick-start`)
4. **Calling `useHotkey` in a loop or conditionally.** That breaks the rules of hooks. Use `useHotkeys([...])` / `useHotkeySequences([...])`, and use `enabled` for conditions. Reordering the array re-registers the entries. (`framework/react/guides/hotkeys`)
5. **Physical vs logical mix-ups.** `'Mod+[KeyS]'` and `'Mod+S'` display identically but are different identities. On AZERTY/Dvorak they fire on different keys. A bracketed code inside `{ key: ... }` is rejected, so use `{ code: 'KeyS' }`. A binding has `key` or `code`, never both. (`overview`)
6. **Recorder output changed (0.9 core / 0.11 react).** Recorders now default to `recordBy: 'code'` and return strings like `Alt+[KeyS]`, not `Alt+S`. Clearing calls `onClear` only; `onRecord('')` is no longer called. Store the raw string and render it with `formatForDisplay`. Don't parse brackets out. (changelog 0.9.0, `framework/react/guides/hotkey-recording`)
7. **Extending `RawHotkey` / `ParsedHotkey` with `interface X extends`.** They are unions now. Use type intersections. (changelog 0.9.0)
8. **Using `formatHotkeySequence` for UI.** It keeps brackets and code names. Map each step through `formatForDisplay` and join it yourself. (`framework/react/guides/formatting-display`)
9. **Treating `meta.group` as a scope.** Groups don't affect matching. Scope comes from `target` and `enabled`. (`framework/react/guides/hotkeys`)
10. **Duplicate registrations.** The default `conflictBehavior: 'warn'` lets both fire. When an inner component should override a global shortcut, set `'replace'` deliberately, or toggle `enabled`. (`framework/react/guides/hotkeys`)
11. **Disabling hotkeys while recording.** It's unnecessary, because the library suppresses callbacks during recording, and toggling `enabled` from `isRecording` only adds churn. (`framework/react/guides/hotkey-recording`)
12. **Reading held keys in a memoized handler.** `useHeldKeys()` and `useKeyHold()` are render-time values. In stable callbacks, use `getKeyStateTracker().getHeldKeys()` / `.isKeyHeld()`. (`framework/react/guides/key-state-tracking`)
13. **CommonJS / `require`.** Since 0.10, the packages are ESM-only. Use `import()` from CJS. (`overview`)

## Migration notes
| Old | Current |
|---|---|
| Recorder returns logical `Alt+S` | default `recordBy: 'code'` -> `Alt+[KeyS]`; pass `recordBy: 'key'` for old behavior |
| `onRecord('')` on clear | `onClear()` only |
| `interface MyHotkey extends RawHotkey` | `type MyHotkey = RawHotkey & {...}` (union) |
| Logical-only bindings | logical + physical (`[Code]` / `{ code }`), F1–F24, more named keys |
| Sequence recorder names (pre-0.5) | `HotkeySequenceRecorder`, `useHotkeySequenceRecorder`, provider key `hotkeySequenceRecorder` |
| No registration introspection (pre-0.7) | `meta` + `useHotkeyRegistrations` |
| `event.target` input check (pre-0.6.2) | `document.activeElement` |
| CJS builds | ESM-only, Node 20+ (0.10 core / 0.12 react) |
| macOS label order arbitrary | Control, Option, Shift, Command (`⇧ ⌘ S`), identity unchanged (0.10.1) |

## Go deeper
- `tanstack doc hotkeys overview`: logical vs physical, recording, display
- `tanstack doc hotkeys installation`: packages, devtools installs
- `tanstack doc hotkeys framework/react/quick-start`: first hotkey, provider, devtools
- `tanstack doc hotkeys framework/react/guides/hotkeys`: all options, useHotkeys, meta
- `tanstack doc hotkeys framework/react/guides/sequences`: sequence options, overlap rules
- `tanstack doc hotkeys framework/react/guides/key-state-tracking`: held keys, hints
- `tanstack doc hotkeys framework/react/guides/hotkey-recording`: rebindable shortcut UIs
- `tanstack doc hotkeys framework/react/guides/formatting-display`: platform labels, keycaps
- `tanstack doc hotkeys reference/interfaces/HotkeyOptions`: option types
- `tanstack doc hotkeys devtools`: devtools setup, production export
