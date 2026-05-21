---
name: railway
description: "Operate Railway infrastructure: create projects, provision services and databases, manage object storage buckets, deploy code, configure environments and variables, manage domains and networking, set up volumes and persistent storage, configure scaling with replicas and multi-region, set up cron jobs and healthchecks, manage PR deploy previews, configure railway.toml and railpack.json for programmatic builds, troubleshoot build and runtime failures, check status and metrics, query Railway docs and community, and interact with the Railway GraphQL API. Use this skill whenever the user mentions Railway, deployments, services, environments, buckets, object storage, build failures, infrastructure operations, volumes, cron, scaling, replicas, healthchecks, PR deploys, app sleeping, railway.toml, railpack, Railpack config, Railway CLI commands, local development, database connections, or Railway project management, even if they don't say 'Railway' explicitly."
---

# Use Railway

## Railway resource model

Railway organizes infrastructure in a hierarchy:

- **Workspace** — billing and team scope. A user belongs to one or more workspaces.
- **Project** — a collection of services under one workspace.
- **Environment** — an isolated configuration plane inside a project (e.g. `production`, `staging`). Each environment has its own variables, config, and deployment history.
- **Service** — a single deployable unit inside a project. It can be an app from a repo, a Docker image, or a managed database.
- **Bucket** — S3-compatible object storage inside a project. Each bucket has credentials (endpoint, access key, secret key) for S3-compatible access.
- **Volume** — persistent NVMe SSD storage attached to a service. Survives redeploys and restarts.
- **Deployment** — a point-in-time release of a service in an environment. Has build logs, runtime logs, and a status lifecycle.

Most CLI commands operate on the linked project/environment/service context. Use `railway status --json` to see the context, and `--project`, `--environment`, `--service` flags to override.

## Preflight

Before any mutation, verify context. Use `scripts/railway-preflight.sh` or run manually:

```bash
command -v railway                # CLI installed
railway whoami --json             # authenticated
railway --version                 # check CLI version
railway status --json             # linked project/environment/service
```

If the CLI is missing:

```bash
bash <(curl -fsSL cli.new)        # Shell script (macOS, Linux, WSL)
brew install railway              # Homebrew (macOS)
npm i -g @railway/cli             # npm (requires Node.js 16+)
```

If not authenticated, run `railway login`. If not linked, run `railway link --project <id-or-name>`.

If a command is not recognized, the CLI may be outdated. Upgrade with `railway upgrade`.

## Common quick operations

These are frequent enough to handle without loading a reference:

```bash
railway status --json                                    # current context
railway whoami --json                                    # auth and workspace info
railway project list --json                              # list projects
railway service status --all --json                      # all services in current context
railway variable list --service <svc> --json             # list variables
railway variable set KEY=value --service <svc>           # set a variable
railway logs --service <svc> --lines 200 --json          # recent logs
railway up --detach -m "<summary>"                       # deploy current directory
railway bucket list --json                               # list buckets
railway bucket credentials --bucket <name> --json        # S3 credentials
```

## Routing

For anything beyond quick operations, load the reference that matches the user's intent. Load only what you need — one reference is usually enough, two at most.

| Intent | Reference | Use for |
|---|---|---|
| CLI command lookup | [cli.md](references/cli.md) | Full CLI reference, all commands, flags, cheat sheet, local dev, DB connect |
| Create or connect resources | [setup.md](references/setup.md) | Projects, services, databases, buckets, volumes, templates, workspaces |
| Ship code or manage releases | [deploy.md](references/deploy.md) | Deploy, redeploy, restart, rollback, build config, monorepo, Dockerfile, CI/CD, PR deploys |
| Change configuration | [configure.md](references/configure.md) | Environments, variables, config patches, domains, networking, TCP proxies |
| Config as code or build system | [railpack.md](references/railpack.md) | railway.toml, railpack.json, language detection, framework config, env overrides |
| Scale, schedule, and harden | [scale.md](references/scale.md) | Replicas, multi-region, cron jobs, healthchecks, app sleeping, volumes, restart policies |
| Check health or debug failures | [operate.md](references/operate.md) | Status, logs, metrics, build/runtime triage, recovery, SSH |
| Query API, docs, or community | [request.md](references/request.md) | Railway GraphQL API, metrics queries, Central Station, official docs, templates |

If the request spans two areas (e.g. "deploy and then check if it's healthy"), load both references and compose one response.

## Execution rules

1. Prefer Railway CLI. Fall back to `scripts/railway-api.sh` for operations the CLI doesn't expose.
2. Use `--json` output where available for reliable parsing.
3. Resolve context before mutation. Know which project, environment, and service you're acting on.
4. For destructive actions (delete service, remove deployment, drop database, delete bucket), confirm intent and state impact before executing.
5. After mutations, verify the result with a read-back command.

## Composition patterns

Multi-step workflows follow natural chains:

- **First deploy**: setup (create project + service) → configure (set variables and source) → deploy → operate (verify healthy)
- **Add a database**: setup (create db) → configure (wire variables) → deploy (redeploy app) → operate (verify connection)
- **Add object storage**: setup (create bucket + get credentials) → configure (set S3 variables on app service)
- **Fix a failure**: operate (triage logs) → configure (fix config or variables) → deploy (redeploy) → operate (verify recovery)
- **Add a domain**: configure (add domain + set port) → operate (verify DNS and service health)
- **Scale up**: scale (add replicas or regions) → operate (verify distribution)
- **Add cron job**: scale (set cron schedule) → operate (verify execution)
- **Docs to action**: request (fetch docs answer) → route to the relevant operational reference

When composing, return one unified response covering all steps.

## Setup decision flow

When the user wants to create or deploy something, determine the right action from current context:

1. Run `railway status --json` in the current directory.
2. **If linked**: add a service to the existing project (`railway add --service <name>`). Do not create a new project unless the user explicitly says "new project" or "separate project".
3. **If not linked**: check the parent directory (`cd .. && railway status --json`).
   - **Parent linked**: this is likely a monorepo sub-app. Add a service and set `rootDirectory` to the sub-app path.
   - **Parent not linked**: run `railway list --json` and look for a project matching the directory name.
     - **Match found**: link to it (`railway link --project <name>`).
     - **No match**: create a new project (`railway init --name <name>`).
4. When multiple workspaces exist, match by name from `railway whoami --json`.

**Naming heuristic**: app names like "flappy-bird" or "my-api" are service names, not project names. Use the directory or repo name for the project.

## Response format

For all operational responses, return:
1. What was done (action and scope).
2. The result (IDs, status, key output).
3. What to do next (or confirmation that the task is complete).

Keep output concise. Include command evidence only when it helps the user understand what happened.
