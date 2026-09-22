# init — bootstrap project memory

Goal: create `.deuxui/` by **inspecting** the repo, asking only what inspection
cannot answer. Every question you ask is a chance for the user to abandon the tool,
so earn each one.

## 1. Inspect

```bash
python3 scripts/ux_check.py <project> --signals
python3 scripts/ux_check.py <project> --inventory ""     # full component list
```

Read directly: the package manifest (framework, Tailwind major, primitive libraries,
i18n, chart and motion libraries), the theme source (`@theme` block for Tailwind v4,
`tailwind.config.*` for v3, or `:root` custom properties), the routes, and three or
four representative components to learn the house conventions.

## 2. Infer, do not ask

| Fact | Where it comes from |
|---|---|
| Framework and versions | package manifest |
| Tailwind v3 vs v4 | dependency range, or `@theme` present |
| Token names and values | `@theme` / `:root` / config |
| Component inventory | `components/`, `ui/`, `primitives/` directories |
| Routes | the router directory or config |
| Density and spacing scale | the components you read |
| Dark mode support | `dark:` usage or a theme attribute |
| i18n | an i18n dependency plus a locales directory |

## 3. Ask only these

Three questions, at most. They are the ones no repository contains:

1. **Who uses this, and what are they trying to finish?** (audience and primary tasks)
2. **Which actions are irreversible or cost money?** (delete, pay, send, publish, revoke)
3. **What must never change?** (brand constraints, a component you must not touch)

If the user does not answer, record reversible defaults as assumptions and continue.
Blocking on an unanswered question helps nobody.

## 4. Write

Copy from `assets/templates/`, filled in:

```
.deuxui/
  PRODUCT.md        audience, jobs, primary tasks, rare high-impact tasks,
                    irreversible actions, supported devices, locales, network
  DESIGN.md         tokens, component inventory, stack, density, themes, motion
  ux.config.yaml    dev URL, routes, API glob, viewports, declared features,
                    threshold overrides, disabled checks, excluded directories
  reports/          written by the scripts
```

`PRODUCT.md` holds no colours and no fonts — those live in `DESIGN.md`. Keeping them
apart is what stops one file trying to be both a brief and a style guide.

Set `api_pattern` in `ux.config.yaml` while you are here. Without it `ux_browser.sh`
has no request glob to intercept, so the aborted, empty and offline probes cannot run
and every `STATE-*` rule reports NOT_RUN — and those probes find more real defects
than the rest of the runtime tier together.

Declare `features:` honestly in the same pass. A feature you do not declare makes its
rules NOT_APPLICABLE, so over-declaring buries you in irrelevant findings and
under-declaring quietly excuses you from real ones.

## 5. Confirm and stop

Show the user what you inferred, especially the irreversible actions. Then stop —
`init` sets up, it does not redesign. Recommend two or three next modes based on what
the inspection found (many components and no `references/`? `audit`. No empty states
anywhere? `harden`).
