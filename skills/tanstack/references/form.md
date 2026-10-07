# TanStack Form

> Verified 2026-10-07 against `@tanstack/react-form@1.33.5` docs and package source (TanStack CLI 0.71.1). Re-check with `tanstack doc form <path>` when the installed major differs.

## Contents
- When to use / when not to
- Packages
- Mental model
- Core API
- Patterns (validation, schema, arrays, linked fields, listeners, composition, form groups, Start SSR)
- Traps
- Migration notes
- Go deeper

## When to use / when not to
- Use for any non-trivial form: typed deep field names (`'people[0].name'`), per-field + form-level validation, async validation with debounce, array fields, multi-step forms, reusable field components.
- Skip for a single uncontrolled input or a search box; React state or `<form action>` is enough.
- Server data that pre-fills a form is owned by TanStack Query; the form only owns the edit buffer (see `framework/react/guides/async-initial-values`).

## Packages
| Need | Package |
|---|---|
| React | `@tanstack/react-form` (peer: react 17/18/19; depends on `@tanstack/react-store@^0.11`, `@tanstack/form-core`) |
| Other frameworks | `@tanstack/vue-form`, `@tanstack/angular-form`, `@tanstack/solid-form`, `@tanstack/lit-form`, `@tanstack/svelte-form` |
| TanStack Start server validation | `@tanstack/react-form-start` (peer `@tanstack/react-start`; re-exports all of `react-form`) |
| Next.js / Remix | `@tanstack/react-form-nextjs`, `@tanstack/react-form-remix` |
| Devtools | `@tanstack/react-devtools` + `@tanstack/react-form-devtools` (`formDevtoolsPlugin()`) |
| Validation | any Standard Schema lib: zod >=3.24, valibot >=1.0, arktype >=2.1.20, yup >=1.7, Effect Schema. No adapter package. |

```sh
npm i @tanstack/react-form zod
```

## Mental model
- `useForm()` returns a stable `FormApi` instance; it does **not** re-render your component when values change.
- State lives in TanStack Store (`form.store`). Read reactively with `useSelector(form.store, sel)` or `<form.Subscribe selector>`; `form.state` is a non-reactive snapshot.
- `<form.Field name>` owns one value + its `meta` (`errors`, `errorMap`, `isTouched`, `isDirty`, `isPristine`, `isBlurred`, `isDefaultValue`, `isValidating`, `isValid`). The render prop gets a `FieldApi`.
- You wire inputs by hand: `value={field.state.value}`, `onChange={e => field.handleChange(...)}`, `onBlur={field.handleBlur}`. Without `handleBlur`, `onBlur` validators never run.
- Validators exist per event: `onMount`, `onChange`, `onBlur`, `onSubmit`, `onDynamic`, each with an `...Async` twin and `...AsyncDebounceMs`. Return `undefined` for valid, anything else is the error (string, object, …) and is typed through to `errors`/`errorMap`.
- Field-level and form-level validators both run; a form validator can push errors to fields via `{ form, fields: { 'a.b': 'msg' } }`.
- `createFormHook` builds an app-wide `useAppForm` with pre-bound field/form components; `withForm` / `withFieldGroup` split big forms with full typing.
- Listeners (`listeners.onChange` etc.) are for side effects; validators are for errors. Do not mix.

## Core API
```tsx
import { useForm, useSelector } from '@tanstack/react-form'
import { z } from 'zod'

const schema = z.object({ username: z.string().min(3), age: z.number().min(13) })

export function Signup() {
  const form = useForm({
    defaultValues: { username: '', age: 0 },
    validators: { onChange: schema },               // form-level Standard Schema
    onSubmit: async ({ value }) => { await save(value) },
  })
  const canSubmit = useSelector(form.store, (s) => s.canSubmit)

  return (
    <form onSubmit={(e) => { e.preventDefault(); e.stopPropagation(); void form.handleSubmit() }}>
      <form.Field
        name="username"
        validators={{
          onChangeAsyncDebounceMs: 500,
          onChangeAsync: async ({ value }) => (await isTaken(value) ? 'Taken' : undefined),
        }}
        children={(field) => (
          <>
            <input
              name={field.name}
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(e) => field.handleChange(e.target.value)}
            />
            {!field.state.meta.isValid && <em role="alert">{field.state.meta.errors.map(String).join(', ')}</em>}
          </>
        )}
      />
      <form.Subscribe
        selector={(s) => [s.canSubmit, s.isSubmitting]}
        children={([ok, busy]) => <button type="submit" disabled={!ok}>{busy ? '…' : 'Save'}</button>}
      />
    </form>
  )
}
```
Key options (`useForm`): `defaultValues`, `defaultState`, `validators`, `validationLogic`, `asyncAlways`, `asyncDebounceMs`, `canSubmitWhenInvalid`, `listeners`, `onSubmit`, `onSubmitInvalid`, `onSubmitMeta`, `transform`, `formId`.
Key `FormApi` methods: `handleSubmit(meta?)`, `reset(values?, { keepDefaultValues })`, `setFieldValue`, `getFieldValue`, `validateField`, `validateAllFields`, `resetField`, `deleteField`, array helpers `pushFieldValue/insertFieldValue/removeFieldValue/swapFieldValues/moveFieldValues/replaceFieldValue/clearFieldValues`, `parseValuesWithSchema(Async)`.
Field API: `handleChange`, `handleBlur`, `setValue`, `pushValue`, `insertValue`, `removeValue`, `swapValues`, `moveValue`, `replaceValue`, `clearValues`, `parseValueWithSchema`.
Other adapters: same `form-core` options and validators; hook/component names differ per framework (check `tanstack doc form framework/<fw>/quick-start` before writing non-React code).

## Patterns

### Sync + async + debounce, error display by source
```tsx
<form.Field
  name="age"
  asyncDebounceMs={500}                       // default for all async validators on this field
  validators={{
    onBlur: ({ value }) => (value < 13 ? 'Too young' : undefined),
    onBlurAsync: async ({ value }) => (value < (await currentAge()) ? 'Can only increase' : undefined),
  }}
  children={(field) => <em>{field.state.meta.errorMap.onBlur}</em>}
/>
```
Async runs only if the sync validator of the same event passed, unless `asyncAlways: true`.

### Form-level submit validation pushing field errors
```tsx
validators: {
  onSubmitAsync: async ({ value }) => {
    const bad = await verifyOnServer(value)
    return bad ? { form: 'Invalid data', fields: { age: 'Must be 13+', 'details.email': 'Required' } } : null
  },
}
```

### Validate-on-submit, then revalidate on change (`onDynamic`)
```tsx
import { revalidateLogic, useForm } from '@tanstack/react-form'
const form = useForm({
  defaultValues: { firstName: '' },
  validationLogic: revalidateLogic({ mode: 'submit', modeAfterSubmission: 'change' }),
  validators: { onDynamic: schema },
})
```

### Arrays
```tsx
<form.Field name="people" mode="array">
  {(field) => (
    <>
      {field.state.value.map((_, i) => (
        <form.Field key={i} name={`people[${i}].name`}>
          {(sub) => <input value={sub.state.value} onChange={(e) => sub.handleChange(e.target.value)} />}
        </form.Field>
      ))}
      <button type="button" onClick={() => field.pushValue({ name: '', age: 0 })}>Add</button>
    </>
  )}
</form.Field>
```

### Linked fields and listeners
```tsx
<form.Field name="confirm_password" validators={{
  onChangeListenTo: ['password'],
  onChange: ({ value, fieldApi }) => value !== fieldApi.form.getFieldValue('password') ? 'No match' : undefined,
}} />
<form.Field name="country" listeners={{
  onChangeDebounceMs: 300,
  onChange: () => form.setFieldValue('province', ''),
}} />
```
Form-level `listeners: { onMount, onChange, onBlur, onSubmit, onChangeDebounceMs }` (autosave lives here).

### App-wide form hook (composition)
```tsx
// form.ts
import { createFormHook, createFormHookContexts } from '@tanstack/react-form'
export const { fieldContext, formContext, useFieldContext, useFormContext } = createFormHookContexts()

function TextField({ label }: { label: string }) {
  const field = useFieldContext<string>()
  return <label>{label}<input value={field.state.value} onChange={(e) => field.handleChange(e.target.value)} /></label>
}
function SubmitButton() {
  const form = useFormContext()
  return <form.Subscribe selector={(s) => s.isSubmitting}>{(b) => <button disabled={b}>Save</button>}</form.Subscribe>
}
export const { useAppForm, withForm, withFieldGroup, useTypedAppFormContext } = createFormHook({
  fieldContext, formContext, fieldComponents: { TextField }, formComponents: { SubmitButton },
})

// usage
const form = useAppForm({ ...formOpts, onSubmit })
<form.AppField name="firstName" children={(f) => <f.TextField label="First" />} />
<form.AppForm><form.SubmitButton /></form.AppForm>

// splitting: types come from formOpts, not runtime
const Address = withForm({ ...formOpts, props: { title: '' }, render: function Render({ form, title }) { /* form.AppField … */ return null } })
```
Share options with `formOptions({ defaultValues })`. Reusable field sets: `withFieldGroup({ defaultValues, render({ group }) })`, mount with `<Group form={form} fields="account" />` or a map from `createFieldMap(defaults)`. Library forms extend via `ProfileForm.extendForm({ fieldComponents })`.

### Multi-step: `form.FormGroup`
```tsx
<form.FormGroup name="step1" validators={{ onChange: step1Schema }} onGroupSubmit={() => setStep(1)}
  children={(group) => <button type="button" onClick={() => group.handleSubmit()}>Next</button>} />
```
Group field error keys are relative to the group (`name`, not `step1.name`).

### TanStack Start server validation
```tsx
import { createServerFn } from '@tanstack/react-start'
import { createServerValidate, formOptions, getFormData, mergeForm, ServerValidateError,
  useForm, useTransform } from '@tanstack/react-form-start'

export const formOpts = formOptions({ defaultValues: { firstName: '', age: 0 } })
const serverValidate = createServerValidate({
  ...formOpts,
  onServerValidate: ({ value }) => (value.age < 12 ? 'Must be 12+' : undefined),
})
export const handleForm = createServerFn({ method: 'POST' })
  .validator((data: unknown) => { if (!(data instanceof FormData)) throw new Error('Invalid'); return data })
  .handler(async ({ data }) => {
    try { const v = await serverValidate(data); /* persist v */ }
    catch (e) { if (e instanceof ServerValidateError) return e.response; throw e }
    return 'ok'
  })
// route: loader: async () => ({ state: await getFormData() })
const { state } = Route.useLoaderData()
const form = useForm({ ...formOpts, transform: useTransform((base) => mergeForm(base, state), [state]) })
// <form action={handleForm.url} method="post" encType="multipart/form-data"> … inputs need name={field.name}
```
`getFormData` is already a server function (reads + deletes a temp cookie). On error `serverValidate` throws `ServerValidateError` whose `response` is a 302 back to the referer; `formState` holds `errorMap.onServer`. Next.js: same helpers from `@tanstack/react-form-nextjs`, return `e.formState` from the action and use `useActionState(action, initialFormState)`.

## Traps
1. **`useStore` from older examples** → still exported but deprecated alias (store 0.11). Use `useSelector(form.store, selector, { compare })`; the 3rd arg is now an options object, not a bare compare fn. (`framework/react/guides/reactivity`)
2. **`useSelector(form.store)` with no selector** → re-renders on every keystroke anywhere in the form. Always select the slice. (`framework/react/guides/basic-concepts`)
3. **Reading `form.state.values.x` in render** → not reactive; UI goes stale. Use `useSelector`/`form.Subscribe`. (`framework/react/guides/reactivity`)
4. **`validatorAdapter: zodValidator()` / `@tanstack/zod-form-adapter`** → pre-1.0 API; adapters were frozen at 0.42 and v1 takes Standard Schemas directly. Pass the schema to `validators.onChange`. (`framework/react/guides/validation`)
5. **Expecting schema output in `onSubmit`** (transforms, coerced numbers, defaults) → Form only validates; `value` is the schema *input*. Call `schema.parse(value)` in `onSubmit` and type `defaultValues` as `z.input<typeof schema>`. (`framework/react/guides/submission-handling`)
6. **Form-level schema error shape** → with a Standard Schema, `state.errorMap.onChange` is `Record<fieldName, Issue[]>`, not a string; `{errorMap.onChange}` renders `[object Object]`. Iterate `Object.values(...).flat().map(i => i.message)`. (`framework/react/guides/validation`)
7. **Async function in `onChange`** → typed as `RejectPromiseValidator`; promises are rejected. Use `onChangeAsync` (+ `onChangeAsyncDebounceMs`). (form-core `FieldApi.ts`)
8. **`onDynamic` never fires** → it requires `validationLogic: revalidateLogic()` on `useForm`. (`framework/react/guides/dynamic-validation`)
9. **onBlur validation silently off** → input lacks `onBlur={field.handleBlur}`. (`framework/react/guides/validation`)
10. **`canSubmit` true on an empty invalid form** → it only goes false after interaction. Disable with `!canSubmit || isPristine`, or rely on submit-time validation. (`framework/react/guides/validation`)
11. **`isDirty` stays true after reverting** → dirty is persistent by design; use `!meta.isDefaultValue` for RHF-style dirty. (`framework/react/guides/basic-concepts`)
12. **Field-level error hides form-level one** → for the same event, the field validator's error overwrites the form validator's `fields` entry. Keep one source per rule. (`framework/react/guides/validation`)
13. **`<button type="reset">` calling `form.reset()`** → native reset also fires and resets `<select>`s to HTML defaults. `preventDefault()` or use `type="button"`. (`framework/react/guides/basic-concepts`)
14. **Async default values** → `defaultValues` are read once. Gate render on the query (`if (isLoading) return …`) or call `form.reset(data)` when data arrives; don't expect `defaultValues` changes to re-seed. (`framework/react/guides/async-initial-values`)
15. **`withForm` render as an arrow fn** → ESLint rules-of-hooks errors. Use `render: function Render({ form }) {}`. `withForm` `defaultValues` are type-only. (`framework/react/guides/form-composition`)
16. **`useTypedAppFormContext` everywhere** → no compile-time check that the form shape matches; last resort for `<Outlet />`. Prefer `withForm`. (`framework/react/guides/form-composition`)
17. **Native POST loses fields** → with `action={handleForm.url}` the browser posts FormData, so every input needs `name={field.name}`, and the server fn must accept `FormData` (Start docs at this date show `.validator(...)` on `createServerFn`; match your installed Start). (`framework/react/guides/ssr`)
18. **`useField` for reactivity** → discouraged; it's meant inside `form.Field`. (`framework/react/guides/basic-concepts`)

## Migration notes
| Older (v0.x / early v1) | Current (1.33) |
|---|---|
| `validatorAdapter: zodValidator()` + `@tanstack/zod-form-adapter` | pass Standard Schema directly to `validators.*` |
| `useStore(form.store, sel, compareFn)` | `useSelector(form.store, sel, { compare })` (`useStore` deprecated) |
| hand-rolled "validate on submit then on change" | `validationLogic: revalidateLogic()` + `onDynamic` |
| prop-drilling `form` with generics | `createFormHook` → `useAppForm`, `withForm`, `withFieldGroup` |
| separate form per wizard step | `form.FormGroup` with `onGroupSubmit` |
| `fieldApi.form` everywhere in groups | `group.getFieldValue`, `group.store` |

## Go deeper
- `tanstack doc form framework/react/quick-start` - createFormHook vs useForm
- `tanstack doc form framework/react/guides/basic-concepts` - field meta, arrays, reset
- `tanstack doc form framework/react/guides/validation` - sync/async/schema/form-level
- `tanstack doc form framework/react/guides/dynamic-validation` - onDynamic, revalidateLogic
- `tanstack doc form framework/react/guides/form-composition` - useAppForm, withForm, withFieldGroup
- `tanstack doc form framework/react/guides/form-groups` - multi-step FormGroup
- `tanstack doc form framework/react/guides/arrays` - array field rendering
- `tanstack doc form framework/react/guides/linked-fields` - onChangeListenTo
- `tanstack doc form framework/react/guides/listeners` - side effects, autosave
- `tanstack doc form framework/react/guides/reactivity` - useSelector vs Subscribe
- `tanstack doc form framework/react/guides/ssr` - Start, Next.js, Remix server validation
- `tanstack doc form framework/react/guides/submission-handling` - onSubmitMeta, schema output
- `tanstack doc form framework/react/guides/custom-errors` - non-string error types
- `tanstack doc form framework/react/guides/focus-management` - focus first invalid field
- `tanstack doc form framework/react/reference/functions/createFormHook` - full hook typings
