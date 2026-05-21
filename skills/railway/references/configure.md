# Configure

Manage environments, variables, service config, domains, and networking.

## Environments

### List and switch

```bash
railway environment list --json
railway environment link <environment>           # switch active environment
```

### Create

```bash
railway environment new <name>
railway environment new <name> --duplicate <source-environment>    # clone config from existing
```

Duplicating copies all service configurations and variables from the source environment.

## Variables

### Read, set, and delete

```bash
railway variable list --service <service> --environment <env> --json
railway variable set KEY=value --service <service> --environment <env>
railway variable delete KEY --service <service> --environment <env>
```

Variable changes trigger a redeployment by default.

### Template syntax

Railway supports interpolation between services and shared variables:

```text
${{KEY}}                                         # same-service variable
${{shared.API_KEY}}                              # shared variable
${{postgres.DATABASE_URL}}                       # variable from another service
${{api.RAILWAY_PRIVATE_DOMAIN}}                  # another service's private domain
```

Wiring example — a frontend connecting to a backend over private networking:

```text
BACKEND_URL=http://${{api.RAILWAY_PRIVATE_DOMAIN}}:${{api.PORT}}
```

### Wiring services together

Each managed database creates connection variables automatically. Reference them from other services:

| Database | Variable reference |
|---|---|
| Postgres | `${{Postgres.DATABASE_URL}}` |
| Redis | `${{Redis.REDIS_URL}}` |
| MySQL | `${{MySQL.MYSQL_URL}}` |
| MongoDB | `${{MongoDB.MONGO_URL}}` |

Service names in references are case-sensitive and must match exactly.

**Public vs private networking decision:**

| Traffic path | Use |
|---|---|
| Browser → API | Public domain |
| Service → Service | Private domain (`RAILWAY_PRIVATE_DOMAIN`) |
| Service → Database | Private (automatic, uses internal DNS) |

**Frontend apps cannot use private networking.** Frontends run in the user's browser, not on Railway's network. Options:

1. **Backend proxy** (recommended): frontend calls a backend API on a public domain, backend connects to the database over the private network.
2. **Public database URL**: use the public connection variable (e.g. `${{Postgres.DATABASE_PUBLIC_URL}}`). Requires a TCP proxy and exposes the database to the internet — only appropriate for development.

### Railway-provided variables

These are set automatically at runtime:

**Networking:**

| Variable | Available when |
|---|---|
| `RAILWAY_PUBLIC_DOMAIN` | Public domain is configured |
| `RAILWAY_PRIVATE_DOMAIN` | Always (internal DNS for service-to-service) |
| `RAILWAY_TCP_PROXY_DOMAIN` | TCP proxy is enabled |
| `RAILWAY_TCP_PROXY_PORT` | TCP proxy is enabled |

**Context:**

| Variable | Available when |
|---|---|
| `RAILWAY_PROJECT_ID` | Always |
| `RAILWAY_ENVIRONMENT_ID` | Always |
| `RAILWAY_ENVIRONMENT_NAME` | Always |
| `RAILWAY_SERVICE_ID` | Always |
| `RAILWAY_SERVICE_NAME` | Always |
| `RAILWAY_DEPLOYMENT_ID` | Always |
| `RAILWAY_REPLICA_ID` | Replicas configured |
| `RAILWAY_REPLICA_REGION` | Multi-region configured |

**Git (present when deployed from a linked repo):**

| Variable | Description |
|---|---|
| `RAILWAY_GIT_COMMIT_SHA` | Full commit hash |
| `RAILWAY_GIT_AUTHOR` | Commit author name |
| `RAILWAY_GIT_COMMIT_MESSAGE` | First line of the commit message |
| `RAILWAY_GIT_BRANCH` | Branch that triggered the deploy |

**Storage (present when a volume is attached):**

| Variable | Description |
|---|---|
| `RAILWAY_VOLUME_MOUNT_PATH` | Filesystem path where the volume is mounted |
| `RAILWAY_VOLUME_NAME` | Name of the attached volume |

Sealed variables are write-only. Their values don't appear in CLI output.

## Service config

Service configuration controls source, build, deploy, and networking settings. Two mutation methods.

### Dot-path patch

For single-field changes:

```bash
railway environment edit --service-config <service> deploy.startCommand "npm start"
railway environment edit --service-config <service> build.buildCommand "npm run build"
railway environment edit --service-config <service> source.rootDirectory "/apps/api"
railway environment edit --service-config <service> deploy.numReplicas 2
```

### JSON patch

For multi-field changes or complex structures:

```bash
railway environment edit --json <<'JSON'
{"services":{"<service-id>":{"build":{"buildCommand":"npm run build"},"deploy":{"startCommand":"npm start"}}}}
JSON
```

Resolve exact service IDs from `railway status --json` before constructing JSON patches.

### Config schema (typed paths)

Include only keys you're changing. The full shape:

**Source**: `source.image` (string), `source.repo` (string), `source.branch` (string), `source.rootDirectory` (string), `source.checkSuites` (boolean), `source.commitSha` (string), `source.autoUpdates.type` (string: `disabled`, `patch`, `minor`)

**Build**: `build.builder` (string: `RAILPACK`, `NIXPACKS`, `DOCKERFILE`), `build.buildCommand` (string), `build.dockerfilePath` (string), `build.watchPatterns` (string array), `build.nixpacksConfigPath` (string)

**Deploy**: `deploy.startCommand` (string), `deploy.preDeployCommand` (string), `deploy.healthcheckPath` (string), `deploy.healthcheckTimeout` (integer), `deploy.numReplicas` (integer), `deploy.restartPolicyType` (string: `ON_FAILURE`, `ALWAYS`, `NEVER`), `deploy.restartPolicyMaxRetries` (integer), `deploy.sleepApplication` (boolean), `deploy.cronSchedule` (string), `deploy.multiRegionConfig` (object)

**Multi-region config** structure for `deploy.multiRegionConfig`:

```json
{ "us-west2": { "numReplicas": 2 }, "europe-west4-drams3a": { "numReplicas": 1 } }
```

| Region identifier | Location |
|---|---|
| `us-west2` | US West (Oregon) |
| `us-east4-eqdc4a` | US East (Virginia) |
| `europe-west4-drams3a` | Europe (Netherlands) |
| `asia-southeast1-eqsg3a` | Asia (Singapore) |

Natural language mapping: "add replicas in Europe" → `europe-west4-drams3a`, "US East" → `us-east4-eqdc4a`.

**Variables**: `variables.<KEY>.value` (string), `variables.<KEY>.isOptional` (boolean), `variables.<KEY>.isSealed` (boolean). Delete a variable by setting it to `null`.

**Lifecycle**: `isDeleted` (boolean) removes the service. `isCreated` (boolean) marks as new.

**Storage**: `volumeMounts.<volume-id>.mountPath` (string), `volumes.<volume-id>.isDeleted` (boolean)

**Buckets**: `buckets.<bucket-id>.region` (string: `sjc`, `iad`, `ams`, `sin`), `buckets.<bucket-id>.isCreated` (boolean), `buckets.<bucket-id>.isDeleted` (boolean)

### Shared variables and project-level config

```bash
railway environment edit --json <<'JSON'
{"sharedVariables":{"API_BASE":{"value":"https://example.com"}}}
JSON
```

Shared variables are accessible from any service via `${{shared.KEY}}`.

### Read config

Always inspect before mutating. Config patches merge:

```bash
railway environment config --json
```

Verify after mutation:

```bash
railway environment config --json
railway service status --all --json
```

## Domains

### Railway domain

One Railway-provided domain per service, generated automatically:

```bash
railway domain --service <service> --json
```

### Custom domain

```bash
railway domain example.com --service <service> --json
```

Returns the DNS records to configure at your DNS provider. Multiple custom domains per service are supported.

### Target port

If the service listens on a non-default port:

```bash
railway domain example.com --service <service> --port 8080 --json
```

### Private networking

For service-to-service traffic within a project, use private domain references:

```text
BACKEND_URL=http://${{api.RAILWAY_PRIVATE_DOMAIN}}:${{api.PORT}}
```

### TCP proxy

TCP proxies expose non-HTTP services (databases, game servers, custom protocols) to the public internet:

```bash
# Enable TCP proxy via JSON config — sets RAILWAY_TCP_PROXY_DOMAIN and RAILWAY_TCP_PROXY_PORT
railway environment edit --json <<'JSON'
{"services":{"<service-id>":{"networking":{"tcpProxies":{"<port>":{"applicationPort":<port>}}}}}}
JSON
```

### Read current domains

```bash
railway environment config --json
```

Domain configuration lives in `config.services.<service-id>.networking` under `serviceDomains` and `customDomains`.

### Remove a domain

Remove domains via JSON config patch by setting the domain ID to `null`:

```bash
# Remove a custom domain
railway environment edit --json <<'JSON'
{"services":{"<service-id>":{"networking":{"customDomains":{"<domain-id>":null}}}}}
JSON

# Remove a Railway-provided domain
railway environment edit --json <<'JSON'
{"services":{"<service-id>":{"networking":{"serviceDomains":{"<domain-id>":null}}}}}
JSON
```

Get domain IDs from `railway environment config --json` under the service's `networking` object.

## Troubleshoot configuration

- **Invalid dot-path**: check field names and types in the config schema section above
- **Wrong service key in JSON patch**: resolve service IDs from `railway status --json`
- **Variable change didn't take effect**: verify with `railway variable list`, changes trigger redeploy by default
- **Domain returns errors**: verify the service has a healthy deployment and the target port is correct
- **DNS propagation delay**: custom domains take time to propagate, this is normal
- **Cloudflare proxy issues**: align SSL/TLS mode per Railway's domain guidance
- **Private networking failing**: verify the service is listening on the referenced port
- **Multi-region patch ignored**: verify region names match the exact identifiers
- **TCP proxy not working**: ensure the application port matches what the service actually listens on
