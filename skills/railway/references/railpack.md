# Railpack

Railway's build system that auto-detects language, framework, and dependencies to produce optimized container images. This reference covers `railpack.json` configuration, `railway.toml` config-as-code, language providers, and programmatic build customization.

## railway.toml — Config as Code

Define build and deploy configuration in code. Lives in the project root. Overrides dashboard settings.

### Complete schema

```toml
[build]
builder = "RAILPACK"                          # RAILPACK | DOCKERFILE
buildCommand = "npm run build"                # override auto-detected build
dockerfilePath = "Dockerfile"                 # path to Dockerfile (DOCKERFILE builder only)
watchPatterns = ["src/**", "package.json"]    # trigger deploys only on matching changes
railpackVersion = "0.5.0"                     # pin Railpack version

[deploy]
startCommand = "node dist/index.js"           # container entrypoint
preDeployCommand = ["npx prisma migrate deploy"]  # run before traffic shifts
healthcheckPath = "/health"                   # HTTP GET must return 200
healthcheckTimeout = 300                      # seconds before marking failed
restartPolicyType = "ON_FAILURE"              # ON_FAILURE | ALWAYS | NEVER
restartPolicyMaxRetries = 5                   # max restart attempts
cronSchedule = "0 */6 * * *"                  # cron expression (UTC)
overlapSeconds = "10"                         # keep old deployment running during switch
drainingSeconds = "30"                        # drain connections before stopping old

# Multi-region (object with region keys)
[deploy.multiRegionConfig]
us-west2 = { numReplicas = 2 }
europe-west4-drams3a = { numReplicas = 1 }
```

### Environment overrides

Override settings per environment. PR environments use `[environments.pr]`:

```toml
[build]
buildCommand = "npm run build"

[deploy]
startCommand = "npm start"
healthcheckPath = "/health"

[environments.staging.deploy]
startCommand = "npm run start:staging"
healthcheckPath = "/health"
healthcheckTimeout = 120

[environments.pr.deploy]
startCommand = "npm run start:preview"
```

Config in code always overrides dashboard values.

## railpack.json — Build customization

Fine-grained control over the build process. Lives in the project root.

### Full schema

```json
{
  "$schema": "https://schema.railpack.com",
  "provider": "node",
  "buildAptPackages": ["git", "build-essential"],
  "packages": {
    "node": "22",
    "python": "3.13"
  },
  "caches": {
    "npm": { "directory": "/root/.npm", "type": "shared" },
    "apt": { "directory": "/var/cache/apt", "type": "locked" }
  },
  "secrets": ["DATABASE_URL", "API_KEY"],
  "steps": {
    "custom-build": {
      "inputs": [{ "step": "install" }],
      "commands": ["npm run custom-build"],
      "secrets": ["DATABASE_URL"],
      "caches": ["npm"],
      "deployOutputs": ["dist/**"]
    }
  },
  "deploy": {
    "startCommand": "node dist/index.js",
    "variables": { "NODE_ENV": "production" },
    "aptPackages": ["curl", "ffmpeg"],
    "paths": ["/custom/bin"]
  }
}
```

### Steps

Steps define build phases. Each step can have:

| Field | Type | Description |
|---|---|---|
| `inputs` | array | Source layers (other steps, images, local files) |
| `commands` | array | Commands to execute sequentially |
| `secrets` | array | Secret names available to this step |
| `assets` | object | Inline file contents |
| `variables` | object | Build-time variables |
| `caches` | array | Cache IDs to mount |
| `deployOutputs` | array | Paths to include in final image |

Extend existing step arrays with `"..."`:

```json
{ "commands": ["...", "./custom-build.sh"] }
```

### Layers

Three input types for steps:

```json
// From another step
{ "step": "build", "include": ["dist"], "exclude": ["node_modules"] }

// From a Docker image
{ "image": "node:22", "include": ["/usr/bin/node"] }

// From local files
{ "local": true, "include": ["."] }
```

### Deploy config

```json
{
  "deploy": {
    "base": { "image": "debian:bookworm" },
    "startCommand": "node dist/index.js",
    "variables": { "NODE_ENV": "production" },
    "aptPackages": ["curl"],
    "paths": ["/app/bin"],
    "inputs": [
      { "step": "build", "include": ["dist", "package.json"] }
    ]
  }
}
```

## Environment variables

Control Railpack behavior via service variables:

### Universal

| Variable | Purpose |
|---|---|
| `RAILPACK_BUILD_CMD` | Override build command |
| `RAILPACK_INSTALL_CMD` | Override install command |
| `RAILPACK_START_CMD` | Container start command |
| `RAILPACK_PACKAGES` | Install packages via Mise (`pkg[@version]`, space-separated) |
| `RAILPACK_BUILD_APT_PACKAGES` | Build-time APT packages (space-separated) |
| `RAILPACK_DEPLOY_APT_PACKAGES` | Runtime APT packages (space-separated) |
| `RAILPACK_DISABLE_CACHES` | Disable caches (space-separated or `*`) |
| `RAILPACK_CONFIG_FILE` | Custom config path |

### Node.js

| Variable | Purpose |
|---|---|
| `RAILPACK_NODE_VERSION` | Pin Node.js version (e.g. `22`, `22.1.0`) |
| `RAILPACK_BUN_VERSION` | Pin Bun version |
| `RAILPACK_SPA_OUTPUT_DIR` | SPA output directory (default: `dist`) |
| `RAILPACK_STATIC_FILE_ROOT` | Static site output directory |
| `RAILPACK_NO_SPA` | Disable SPA mode |
| `RAILPACK_PRUNE_DEPS` | Remove dev dependencies |
| `RAILPACK_NODE_PRUNE_CMD` | Custom pruning command |
| `RAILPACK_ANGULAR_PROJECT` | Angular project name |

### Python

| Variable | Purpose |
|---|---|
| `RAILPACK_PYTHON_VERSION` | Pin Python version (e.g. `3.12`) |
| `RAILPACK_DJANGO_APP_NAME` | Django WSGI app name |

### Go

| Variable | Purpose |
|---|---|
| `RAILPACK_GO_VERSION` | Pin Go version |
| `RAILPACK_GO_BIN` | Binary name in `cmd/` to build |
| `RAILPACK_GO_WORKSPACE_MODULE` | Go workspace module to build |
| `CGO_ENABLED` | Set to `1` for non-static binaries |

### Other languages

| Variable | Purpose |
|---|---|
| `RAILPACK_RUBY_VERSION` | Pin Ruby version |
| `RAILPACK_PHP_ROOT_DIR` | PHP document root |
| `RAILPACK_PHP_EXTENSIONS` | PHP extensions (comma-separated) |
| `RAILPACK_SKIP_MIGRATIONS` | Skip Laravel migrations |
| `RAILPACK_JDK_VERSION` | Pin JDK version |
| `RAILPACK_ELIXIR_VERSION` | Pin Elixir version |
| `RAILPACK_ERLANG_VERSION` | Pin Erlang/OTP version |
| `RAILPACK_DENO_VERSION` | Pin Deno version |
| `RAILPACK_DOTNET_VERSION` | Pin .NET version |
| `RAILPACK_RUST_VERSION` | Pin Rust version |

## Language detection

Railpack auto-detects the language from marker files:

| Marker | Language | Default version |
|---|---|---|
| `package.json` | Node.js | 22 |
| `requirements.txt`, `pyproject.toml`, `Pipfile` | Python | 3.13 |
| `go.mod`, `main.go` | Go | 1.23 |
| `Cargo.toml` | Rust | 1.89 |
| `Gemfile` | Ruby | 3.4 |
| `composer.json`, `index.php` | PHP | 8.4 |
| `mix.exs` | Elixir | 1.18 |
| `deno.json` | Deno | 2 |
| `*.csproj` | .NET | 6.0 |
| `gradlew`, `pom.xml` | Java | 21 |
| `Staticfile`, `index.html` | Static | — |
| `CMakeLists.txt`, `meson.build` | C/C++ | — |
| `gleam.toml` | Gleam | — |
| `start.sh` | Shell | — |

## Package manager detection (Node.js)

Priority order:

1. `packageManager` field in `package.json` (uses Corepack)
2. `pnpm-lock.yaml` → pnpm
3. `bun.lockb` / `bun.lock` → bun
4. `.yarnrc.yml` → yarn (berry)
5. `yarn.lock` → yarn
6. `package-lock.json` → npm
7. Default: npm

## Framework auto-detection

| Framework | Detection | Static serving |
|---|---|---|
| Vite | `vite.config.*` or `vite build` script | Caddy |
| Next.js | `next.config.*` | Node.js |
| Nuxt | `nuxt.config.*` | Node.js |
| Astro | `astro.config.*` (output != "server") | Caddy |
| Angular | `angular.json` | Caddy |
| Create React App | `react-scripts` dependency | Caddy |
| React Router | `react-router.config.*` | Caddy |
| Remix | `remix.config.*` | Node.js |
| FastAPI | `fastapi` in requirements | uvicorn |
| Flask | `flask` in requirements | gunicorn |
| Django | `manage.py` + django dependency | gunicorn |
| Rails | `config/application.rb` | puma |
| Laravel | `artisan` file | FrankenPHP |
| Phoenix | `mix.exs` with Phoenix | Node.js |

## Common patterns

### Pin language version

```toml
# railway.toml — no code changes needed
[build]
builder = "RAILPACK"
```

Then set `RAILPACK_NODE_VERSION=22` (or Python, Go, etc.) as a service variable.

### Add system packages at runtime

```bash
railway variable set RAILPACK_DEPLOY_APT_PACKAGES="ffmpeg curl imagemagick" --service <service>
```

### Custom build with railpack.json

```json
{
  "$schema": "https://schema.railpack.com",
  "steps": {
    "install": {
      "commands": ["...", "npm run postinstall"]
    }
  },
  "deploy": {
    "aptPackages": ["ffmpeg"],
    "startCommand": "node dist/server.js"
  }
}
```

### Monorepo with railway.toml per service

Each service gets its own `railway.toml` with appropriate build/start commands:

```toml
# apps/api/railway.toml
[build]
buildCommand = "pnpm --filter api build"

[deploy]
startCommand = "pnpm --filter api start"
healthcheckPath = "/health"
```

### Static site with SPA routing

```bash
railway variable set RAILPACK_SPA_OUTPUT_DIR="dist" --service <service>
```

Or in railpack.json:

```json
{
  "provider": "node",
  "deploy": {
    "variables": { "RAILPACK_SPA_OUTPUT_DIR": "dist" }
  }
}
```

### Dockerfile builder

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "docker/Dockerfile.prod"
```

## Choosing: railway.toml vs railpack.json vs env vars

| Need | Use |
|---|---|
| Start/build commands, healthcheck, restart, cron | `railway.toml` |
| Custom build steps, layers, caches, apt packages | `railpack.json` |
| Pin language version, add runtime packages | Environment variables |
| Per-environment overrides | `railway.toml` `[environments.*]` |
| Quick one-off change | `railway environment edit --service-config` |

`railway.toml` is the recommended starting point. Add `railpack.json` only when you need build step customization beyond what `railway.toml` offers.
