# CLI Reference

Complete Railway CLI command reference. Use `--json` on most commands for machine-readable output. Use `-s`/`--service` and `-e`/`--environment` to target specific resources.

## Authentication

```bash
railway login                         # browser-based login
railway login --browserless           # token-based login (CI/headless)
railway logout                        # clear credentials
railway whoami --json                 # current user, workspaces, teams
```

Token location: `~/.railway/config.json` under `user.token`.

For CI/CD, set `RAILWAY_TOKEN` (project-scoped) or `RAILWAY_API_TOKEN` (account-scoped) as environment variables — the CLI auto-detects them.

## Project lifecycle

```bash
railway init --name <project-name>                        # create + link
railway init --name <name> --workspace <workspace>        # create in specific workspace
railway link --project <project-id-or-name>               # link existing project
railway unlink                                            # unlink project from directory
railway unlink --service                                  # unlink service only (keep project)
railway status --json                                     # show linked context
railway list --json                                       # all projects across workspaces
railway project list --json                               # projects in current workspace
railway open                                              # open dashboard in browser
railway open --print                                      # print dashboard URL instead
railway delete --project <name> --yes                     # delete project (destructive)
railway delete --project <name> --yes --2fa-code 123456   # with 2FA
```

## Services

```bash
railway add --service <name>                  # create empty service
railway add --database postgres               # managed database (postgres, redis, mysql, mongodb)
railway add --repo <user/repo>                # service from GitHub repo
railway add                                   # interactive mode
railway service link                          # interactive service picker
railway service link <name>                   # link by name
railway service status --all --json           # all services in project
railway service status --service <svc> --json # specific service
```

## Deployments

```bash
railway up --detach -m "<summary>"                          # deploy (non-blocking)
railway up --ci -m "<summary>"                              # deploy (stream build logs)
railway up --service <svc> --environment <env> --detach -m "<msg>"  # targeted deploy
railway up --project <id> --environment <env> --detach -m "<msg>"   # unlinked deploy (CI)
railway redeploy --service <svc> --yes                      # rebuild from same source
railway restart --service <svc> --yes                       # restart without rebuilding
railway down --service <svc> --yes                          # remove latest deployment
railway deployment list --service <svc> --limit 20 --json   # deployment history
railway deploy --template <code>                            # deploy from template
```

### `railway up` flags

| Flag | Purpose |
|---|---|
| `-d, --detach` | Return immediately, don't stream logs |
| `--ci` | Stream build logs, exit when build completes |
| `-m, --message` | Deployment message for auditability |
| `-s, --service` | Target service |
| `-e, --environment` | Target environment |
| `-p, --project` | Target project (requires `--environment`) |
| `--no-gitignore` | Include gitignored files |
| `-v, --verbose` | Verbose output |

## Variables

```bash
railway variable list --service <svc> --json                         # list all
railway variable list --service <svc> --environment <env> --json     # scoped to env
railway variable set KEY=value --service <svc>                       # set single
railway variable set KEY1=val1 KEY2=val2 --service <svc>             # set multiple
railway variable delete KEY --service <svc>                          # delete
```

Variable changes trigger redeployment by default.

## Environments

```bash
railway environment list --json                           # list environments
railway environment link <name>                           # switch active environment
railway environment new <name>                            # create environment
railway environment new <name> --duplicate <source>       # clone from existing
railway environment delete <name>                         # delete environment
railway environment config --json                         # full config dump
railway environment edit --service-config <svc> <path> <value>  # dot-path patch
railway environment edit --json <<'JSON'                  # JSON patch
{"services":{"<id>":{"deploy":{"startCommand":"npm start"}}}}
JSON
```

## Logs

```bash
railway logs --service <svc> --lines 200 --json           # recent runtime logs
railway logs --service <svc> --build --lines 200 --json    # build logs
railway logs --latest --lines 200 --json                   # latest deployment
railway logs --service <svc> --since 1h --lines 400 --json # time-bounded
railway logs --service <svc> --since 30m --until 10m --lines 400 --json
railway logs --service <svc> --filter "@level:error" --json # filtered
```

### `railway logs` flags

| Flag | Purpose |
|---|---|
| `-n, --lines` | Number of lines to fetch (prevents infinite stream) |
| `--since` | Start time (`1h`, `30m`, `2d`) |
| `--until` | End time |
| `--filter` | Log filter expression (`@level:error`, `AND`/`OR`/`-`) |
| `--build` | Show build logs instead of runtime |
| `--latest` | Logs from latest deployment |
| `-s, --service` | Target service |
| `-e, --environment` | Target environment |

**Always use `--lines`, `--since`, or `--until`** — without them, `railway logs` streams indefinitely and blocks execution.

## Domains

```bash
railway domain --service <svc> --json                     # generate Railway domain
railway domain example.com --service <svc> --json         # add custom domain
railway domain example.com --service <svc> --port 8080    # with target port
```

## Volumes

```bash
railway volume list --service <svc> --json                # list volumes
railway volume add --service <svc> --mount-path /data     # add volume
railway volume delete --service <svc> --yes               # delete volume (destructive)
```

Volume CLI commands are the preferred way to manage volumes (simpler than JSON config patches).

## Scaling

```bash
railway scale --service <svc> --json                      # show current scale config
railway scale --service <svc> --<region>=<replicas>       # set replicas per region
```

Region flags use the region identifier as the flag name:

```bash
railway scale --service api --us-west2=3 --europe-west4-drams3a=1
```

## Buckets (Object Storage)

```bash
railway bucket list --json                                # list buckets
railway bucket create <name> --region sjc --json          # create bucket
railway bucket info --bucket <name> --json                # storage info
railway bucket credentials --bucket <name> --json         # S3 credentials
railway bucket credentials --bucket <name> --reset --yes  # reset credentials
railway bucket rename --bucket <name> --name <new> --json # rename
railway bucket delete --bucket <name> --yes               # delete (destructive)
```

## Local development

```bash
railway run <command>                         # run command with Railway env vars injected
railway run --service <svc> <command>         # from specific service
railway shell                                 # open subshell with Railway env vars
railway shell --service <svc>                 # from specific service
railway shell --silent                        # without banner
railway connect                               # connect to database shell (interactive)
railway connect <service-name>                # connect to specific database
railway connect --environment <env>           # in specific environment
```

### `railway run` flags

| Flag | Purpose |
|---|---|
| `-s, --service` | Service to pull variables from |
| `-e, --environment` | Environment to pull variables from |
| `-p, --project` | Project ID |
| `--no-local` | Skip local develop overrides |
| `-v, --verbose` | Show domain replacement info |

### `railway connect` — database shells

Automatically detects the database type and opens the appropriate shell:

| Database | Shell |
|---|---|
| Postgres | `psql` |
| MySQL | `mysql` |
| MongoDB | `mongosh` |
| Redis | `redis-cli` |

Requires the database client to be installed locally.

### `railway dev` — local development with Docker

Run Railway services locally using Docker Compose:

```bash
railway dev                           # start services (interactive setup)
railway dev up                        # start services
railway dev down                      # stop services
railway dev --verbose                 # show domain replacement info
```

`railway dev` generates a Docker Compose configuration that:
- Pulls environment variables from Railway
- Sets up local networking between services
- Optionally configures HTTPS via mkcert
- Replaces Railway private domains with local addresses

Requires Docker and docker-compose installed locally.

## SSH

```bash
railway ssh --service <svc>           # SSH into running service container
```

Useful for debugging runtime state, inspecting files, checking environment variables, or running one-off commands.

## Utility commands

```bash
railway upgrade                       # upgrade CLI to latest version
railway --version                     # show CLI version
railway docs                          # open Railway docs in browser
railway completion bash               # generate shell completions (bash, zsh, fish, powershell)
```

## Global flags

| Flag | Short | Purpose |
|---|---|---|
| `--service` | `-s` | Target service by name or ID |
| `--environment` | `-e` | Target environment by name or ID |
| `--json` | | Output in JSON format |
| `--yes` | `-y` | Skip confirmation prompts |
| `--help` | `-h` | Display help information |
| `--version` | `-V` | Display CLI version |

## Environment variables

| Variable | Scope | Purpose |
|---|---|---|
| `RAILWAY_TOKEN` | Project | Project-scoped token for CI deploys |
| `RAILWAY_API_TOKEN` | Account | Account-scoped token for admin operations |

Generate tokens via the Railway dashboard under project or account settings.

## Command cheat sheet

| Task | Command |
|---|---|
| Check context | `railway status --json` |
| Who am I | `railway whoami --json` |
| List projects | `railway list --json` |
| Create project | `railway init --name <name>` |
| Link project | `railway link --project <name>` |
| Add service | `railway add --service <name>` |
| Add database | `railway add --database postgres` |
| Deploy | `railway up --detach -m "<msg>"` |
| View logs | `railway logs --service <svc> --lines 200 --json` |
| Set variable | `railway variable set KEY=val --service <svc>` |
| Add domain | `railway domain example.com --service <svc>` |
| Add volume | `railway volume add --service <svc> --mount-path /data` |
| Scale | `railway scale --service <svc> --us-west2=3` |
| Connect to DB | `railway connect` |
| Run locally | `railway run npm start` |
| SSH debug | `railway ssh --service <svc>` |
| Upgrade CLI | `railway upgrade` |
