# Deploy

Ship code, manage releases, configure builds, and set up CI/CD pipelines.

## Deploy code

### Standard deploy

```bash
railway up --detach -m "<release summary>"
```

`--detach` returns immediately instead of streaming build logs. Always include `-m` with a release summary for auditability.

### Watch the build

```bash
railway up --ci -m "<release summary>"
```

`--ci` streams build logs and exits when the build completes. Use when the user wants to see build output or when you need to triage build failures immediately.

### Targeted deploy

When multiple services exist, target explicitly:

```bash
railway up --service <service> --environment <environment> --detach -m "<summary>"
```

### Deploy to an unlinked project

For CI or cross-project deploys:

```bash
railway up --project <project-id> --environment <environment> --detach -m "<summary>"
```

`--project` requires `--environment`. Railway needs both to resolve context.

## Manage releases

### Redeploy and restart

```bash
railway redeploy --service <service> --yes       # rebuild and deploy from same source
railway restart --service <service> --yes         # restart without rebuilding
```

Redeploy triggers a full build cycle. Restart only restarts the running container. Use restart when the code hasn't changed but the service needs a fresh process (e.g. after variable changes that didn't auto-trigger).

### Remove latest deployment

```bash
railway down --service <service> --yes
```

Removes the latest successful deployment but doesn't delete the service. To delete a service entirely, use environment config patching (see [configure.md](configure.md)).

### Rollback

To roll back to a previous deployment, redeploy a specific commit:

```bash
railway environment edit --service-config <service> source.commitSha "<commit-sha>"
railway redeploy --service <service> --yes
```

After the rollback deploys successfully, clear the pinned commit to resume normal deploys:

```bash
railway environment edit --service-config <service> source.commitSha ""
```

## Deployment history and logs

```bash
railway deployment list --service <service> --limit 20 --json
railway logs --service <service> --lines 200 --json              # runtime logs
railway logs --service <service> --build --lines 200 --json      # build logs
railway logs --latest --lines 200 --json                         # latest deployment
```

`railway logs` streams indefinitely when no bounding flags are given. Always use `--lines`, `--since`, or `--until` to get a bounded fetch.

## Build configuration

Railway uses Railpack as the default builder. It detects language and framework from repo contents automatically.

### Builder selection

Three builder options:

- **RAILPACK** — auto-detects language and framework, builds from source (default, recommended)
- **NIXPACKS** — legacy builder. Do not use; use RAILPACK instead.
- **DOCKERFILE** — uses a Dockerfile you provide

```bash
railway environment edit --service-config <service> build.builder RAILPACK
railway environment edit --service-config <service> build.builder DOCKERFILE
railway environment edit --service-config <service> build.dockerfilePath "docker/Dockerfile.prod"
```

### Build and start commands

Override when auto-detection gets it wrong:

```bash
railway environment edit --service-config <service> build.buildCommand "npm run build"
railway environment edit --service-config <service> deploy.startCommand "npm start"
```

### Pre-deploy commands

Run migrations or setup steps before the new deployment receives traffic:

```bash
railway environment edit --service-config <service> deploy.preDeployCommand "npx prisma migrate deploy"
```

Pre-deploy commands run after the build succeeds but before traffic shifts. If the command fails, the deployment fails and the previous version continues serving.

### Railpack environment variables

Control Railpack behavior by setting these as service variables:

| Variable | Purpose |
|---|---|
| `RAILPACK_NODE_VERSION` | Pin Node.js version (e.g. `20`, `22.1.0`) |
| `RAILPACK_PYTHON_VERSION` | Pin Python version (e.g. `3.12`) |
| `RAILPACK_GO_BIN` | Go binary name to build |
| `RAILPACK_STATIC_FILE_ROOT` | Directory for static site output (e.g. `dist`, `build`) |
| `RAILPACK_SPA_OUTPUT_DIR` | SPA output directory with client-side routing support |
| `RAILPACK_PACKAGES` | Additional system packages for the build |
| `RAILPACK_BUILD_APT_PACKAGES` | Apt packages available during build only |
| `RAILPACK_DEPLOY_APT_PACKAGES` | Apt packages available at runtime only |

Full Railpack docs: https://railpack.com/llms.txt

### Static sites

Railpack detects static sites from `Staticfile`, `index.html`, or `RAILPACK_STATIC_FILE_ROOT` and serves them with a built-in static file server. If the build outputs to a non-standard directory, set `RAILPACK_STATIC_FILE_ROOT`.

## Monorepo patterns

### Isolated monorepo

When services don't share code, isolate each with its own root directory:

```bash
railway environment edit --service-config <service> source.rootDirectory "/packages/api"
```

### Shared monorepo

When services depend on shared packages, scope via build/start commands instead:

```bash
# pnpm workspaces
railway environment edit --service-config <service> build.buildCommand "pnpm --filter api build"
railway environment edit --service-config <service> deploy.startCommand "pnpm --filter api start"

# yarn workspaces
railway environment edit --service-config <service> build.buildCommand "yarn workspace api build"
railway environment edit --service-config <service> deploy.startCommand "yarn workspace api start"

# turborepo
railway environment edit --service-config <service> build.buildCommand "npx turbo run build --filter=api"
railway environment edit --service-config <service> deploy.startCommand "npx turbo run start --filter=api"
```

Don't set a restrictive `rootDirectory` in this case. The build needs access to the workspace root.

### Watch paths

Prevent unrelated package changes from redeploying every service:

```bash
railway environment edit --service-config <service> build.watchPatterns '["packages/api/**","packages/shared/**"]'
```

### Common monorepo pitfalls

- **Using `rootDirectory` with shared imports**: if service A imports from `packages/shared/`, setting `rootDirectory: "/packages/a"` hides the shared code.
- **Forgetting watch paths**: without them, every push redeploys all services.
- **Wrong filter target**: `pnpm --filter api` uses the `name` field in `package.json`, not the directory name.

## GitHub integration and PR deploys

### Enable PR deploys

PR deploys create isolated preview environments for every pull request. Enable via GraphQL:

```bash
scripts/railway-api.sh \
  'mutation updateProject($id: String!, $input: ProjectUpdateInput!) {
    projectUpdate(id: $id, input: $input) { id prDeploys botPrEnvironments }
  }' \
  '{"id":"<project-id>","input":{"prDeploys":true}}'
```

Set `botPrEnvironments: true` to also create PR environments for bot-authored PRs (e.g. Dependabot).

### How PR deploys work

1. A PR is opened against the linked branch
2. Railway creates a temporary environment cloned from the target branch's environment
3. The PR code is deployed into this temporary environment
4. The environment is destroyed when the PR is closed or merged

PR environments inherit all variables and configuration from the source environment.

### Auto-deploy from GitHub

When a service is linked to a GitHub repo, Railway automatically builds and deploys on every push to the linked branch. To change the tracked branch:

```bash
railway environment edit --service-config <service> source.branch "main"
```

### Check suites

Control whether Railway waits for GitHub check suites (CI) to pass before deploying:

```bash
railway environment edit --service-config <service> source.checkSuites true
```

## CI/CD patterns

### Deploy from CI (GitHub Actions example)

```yaml
- name: Deploy to Railway
  env:
    RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
  run: |
    npm i -g @railway/cli
    railway up --project <project-id> --environment production --detach -m "CI deploy ${{ github.sha }}"
```

Generate a project token via Railway dashboard or GraphQL API. Set it as `RAILWAY_TOKEN` environment variable — the CLI auto-detects it.

### Deploy and wait for healthy

Use `scripts/railway-deploy-wait.sh` for CI pipelines that need to verify the deployment succeeded:

```bash
scripts/railway-deploy-wait.sh <service> <environment> "Deploy message"
```

## Troubleshoot deploys

- **No project/service context**: run `railway link` or pass `--project` with `--environment`
- **Build fails before compile**: check dependency graph, lockfiles, and whether the right builder is selected
- **Build succeeds but app crashes**: verify start command and required runtime variables
- **Wrong files in build**: check root directory and watch patterns
- **`railway down` treated as delete**: `down` only removes the latest deployment, not the service
- **Wrong Node/Python version**: set `RAILPACK_NODE_VERSION` or `RAILPACK_PYTHON_VERSION`
- **Missing system package at runtime**: add to `RAILPACK_DEPLOY_APT_PACKAGES`
- **Pre-deploy command fails**: check logs with `railway logs --latest --build --lines 400 --json`
