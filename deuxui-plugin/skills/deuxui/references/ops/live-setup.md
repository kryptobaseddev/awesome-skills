# live-setup — wire the loop once so it runs without arguments

Everything the runtime and live tiers need, in one file, so the commands are
short enough to run often. A loop you have to remember four flags for is a loop
nobody runs.

## Check what is missing first

```bash
python3 scripts/doctor.py .
```

Read it before writing anything. It names each thing that is absent, what that
costs in rules, and how to fix it. A page of NOT_RUN caused by a missing browser
is a different situation from unfinished work.

## The config

`.deuxui/ux.config.yaml` — `deuxui init` writes it; this fills the `app:` block:

```yaml
app:
  dev_url: http://localhost:5173
  routes: /,/login,/settings,/projects/1     # real routes, including a deep one
  api_pattern: '**/api/**'                   # what to intercept for forced states
  viewports: 320,390,768,1024,1440
```

Each line removes a flag from every later command, and two of them do more:

**`routes`** should include one route that needs data and one that needs
authentication. A probe set run only against `/` measures the marketing page of
an application, which is the part with no states in it.

**`api_pattern`** is the one that matters most. Without it the forced-state
probes cannot run, so `R-STATE-ERROR`, `R-STATE-EMPTY` and `R-STATE-OFFLINE`
report NOT_RUN — and those three are the whole reason the runtime tier is worth
having. Aborting a request and finding an immortal spinner is a defect nobody
finds by reading source.

## Authentication

If the routes that matter are behind a login, the loop stops at the login page
and every probe measures it. Options, in order of preference:

1. A seeded development session the dev server accepts — a cookie or a token set
   from an environment variable.
2. `agent-browser` driven through the login once, then reused for the probe run;
   the browser keeps the session between commands.
3. Fewer routes. An honest measurement of three public routes beats a NOT_RUN on
   twelve.

Record which one you used. `R-*` results measured against a login page are not
results about the application, and the report cannot tell.

## Confirm it works

```bash
bash scripts/ux_browser.sh          # no arguments -- reads the config
python3 scripts/ux_report.py --collect .deuxui/reports/runtime
```

Then read the runtime rows. If `R-STATE-*` are NOT_RUN, `api_pattern` is wrong or
the routes do not fetch anything. Fix that before trusting a runtime pass — it is
the difference between a tier that measures behaviour and one that measures
markup twice.

Then: [live.md](live.md).
