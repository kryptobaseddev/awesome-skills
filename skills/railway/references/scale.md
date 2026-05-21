# Scale

Replicas, multi-region deployment, cron jobs, healthchecks, app sleeping, restart policies, and volumes.

## Replicas

### Set replica count

```bash
railway environment edit --service-config <service> deploy.numReplicas 3
```

Each replica on Pro plan gets up to 24 vCPU and 24 GB RAM. Maximum 42 replicas per service.

Railway automatically distributes public traffic randomly across replicas within each region. No load balancer configuration needed.

### Check current replicas

```bash
railway environment config --json
# Look for deploy.numReplicas in the service config
```

### Scale to zero

Setting `numReplicas` to 0 effectively stops the service. Use app sleeping instead for automatic scale-down (see below).

## Multi-region

### Deploy to multiple regions

```bash
railway environment edit --service-config <service> deploy.multiRegionConfig '{"us-west2":{"numReplicas":2},"europe-west4-drams3a":{"numReplicas":1}}'
```

Available Railway Metal regions:

| Region identifier | Location | Short name |
|---|---|---|
| `us-west2` | US West (Oregon) | US West |
| `us-east4-eqdc4a` | US East (Virginia) | US East |
| `europe-west4-drams3a` | Europe (Netherlands) | EU West |
| `asia-southeast1-eqsg3a` | Asia (Singapore) | APAC |

Railway automatically routes public traffic to the nearest region, then randomly distributes requests among replicas in that region.

### Natural language mapping

| User says | Region identifier |
|---|---|
| "US West", "California", "Oregon" | `us-west2` |
| "US East", "Virginia" | `us-east4-eqdc4a` |
| "Europe", "EU", "Netherlands" | `europe-west4-drams3a` |
| "Asia", "Singapore", "APAC" | `asia-southeast1-eqsg3a` |

When the user doesn't specify a region, query current config first to see existing assignments before modifying.

### Read current region config

```bash
railway environment config --json
# Look for deploy.multiRegionConfig in the service config
```

## Healthchecks

Healthchecks guarantee zero-downtime deployments. Railway checks the endpoint before shifting traffic to the new deployment.

### Configure healthcheck

```bash
railway environment edit --service-config <service> deploy.healthcheckPath "/health"
railway environment edit --service-config <service> deploy.healthcheckTimeout 300
```

- `healthcheckPath`: HTTP GET path that must return 200. Common paths: `/health`, `/healthz`, `/ready`, `/api/health`
- `healthcheckTimeout`: seconds to wait for a healthy response before marking the deployment as failed (default varies by plan)

### Healthcheck behavior

1. New deployment builds and starts
2. Railway sends GET requests to `healthcheckPath`
3. If 200 response within timeout → traffic shifts to new deployment, old is stopped
4. If no 200 within timeout → deployment marked FAILED, old deployment continues serving

### Best practices

- Return 200 only when the service is truly ready (database connected, caches warm)
- Keep the health endpoint lightweight — it's called frequently
- Set timeout higher than your startup time (database migrations, cache warming)

## App sleeping

When a service has no inbound requests for 10+ minutes, Railway automatically puts it to sleep. While asleep, the service incurs no compute charges. The first inbound request wakes it (cold start delay).

### Enable app sleeping

```bash
railway environment edit --service-config <service> deploy.sleepApplication true
```

### Disable app sleeping

```bash
railway environment edit --service-config <service> deploy.sleepApplication false
```

### When to use

- Development/staging environments with sporadic traffic
- Internal tools accessed occasionally
- Cost optimization for low-traffic services

### When NOT to use

- Production services requiring instant response times
- Services that maintain persistent connections (WebSocket servers)
- Databases (they have their own persistence model)

## Cron jobs

Schedule services to run on a recurring schedule. The service starts, executes, and stops — you pay only for execution time.

### Set a cron schedule

```bash
railway environment edit --service-config <service> deploy.cronSchedule "0 */6 * * *"
```

Common cron expressions:

| Expression | Schedule |
|---|---|
| `* * * * *` | Every minute |
| `*/5 * * * *` | Every 5 minutes |
| `0 * * * *` | Every hour |
| `0 */6 * * *` | Every 6 hours |
| `0 0 * * *` | Daily at midnight UTC |
| `0 0 * * 1` | Every Monday at midnight UTC |
| `0 0 1 * *` | First of every month |

### Remove cron schedule

```bash
railway environment edit --service-config <service> deploy.cronSchedule ""
```

### Cron + app sleeping

Cron services naturally benefit from app sleeping — the service wakes on schedule, runs, and sleeps until the next execution.

### Best practices

- Ensure the service exits cleanly after completing its task
- Set appropriate restart policy (usually `NEVER` for cron jobs)
- Monitor execution via logs: `railway logs --service <service> --lines 100 --json`

## Restart policies

Control what happens when a service process exits.

### Set restart policy

```bash
railway environment edit --service-config <service> deploy.restartPolicyType "ON_FAILURE"
railway environment edit --service-config <service> deploy.restartPolicyMaxRetries 5
```

| Policy | Behavior |
|---|---|
| `ON_FAILURE` | Restart only on non-zero exit (default for most services) |
| `ALWAYS` | Restart regardless of exit code |
| `NEVER` | Do not restart (appropriate for cron jobs and one-shot tasks) |

`restartPolicyMaxRetries` limits how many times Railway will restart the process before marking the deployment as crashed.

## Volumes

Persistent NVMe SSD storage that survives redeploys and restarts.

### Attach a volume

```bash
railway environment edit --json <<'JSON'
{"services":{"<service-id>":{"volumeMounts":{"<volume-id>":{"mountPath":"/data"}}}}}
JSON
```

For databases and templates, volumes are created automatically.

### Volume environment variables

When attached, Railway injects:

| Variable | Description |
|---|---|
| `RAILWAY_VOLUME_MOUNT_PATH` | Mount path |
| `RAILWAY_VOLUME_NAME` | Volume name |

### Remove a volume

```bash
railway environment edit --json <<'JSON'
{"services":{"<service-id>":{"volumes":{"<volume-id>":{"isDeleted":true}}}}}
JSON
```

### Volume considerations

- Volumes are tied to a single service in a single environment
- Data persists across deployments and restarts
- Volumes use NVMe SSDs on Railway Metal (fast I/O)
- No built-in backup — implement your own backup strategy for important data
- Volume size is not pre-allocated; it grows with usage and is billed per GB

## Resource limits

### Pro plan limits (per replica)

| Resource | Limit |
|---|---|
| CPU | 24 vCPU |
| Memory | 24 GB RAM |
| Max replicas | 42 |
| Network egress | Soft limit ~100 GB/month (throttled above) |

Railway uses vertical auto-scaling — services automatically get more CPU/memory as needed up to the limit. No manual instance size selection required.

### Business Class / Enterprise

Higher limits available on request. Contact Railway for custom resource allocations.

## Monitoring scaled services

After scaling, verify distribution:

```bash
# Check all services and replica status
railway service status --all --json

# Query metrics across replicas via GraphQL (see request.md)
# Use groupBy: ["DEPLOYMENT_INSTANCE_ID"] or ["REGION"] to see per-replica/per-region metrics
```

## Troubleshoot scaling

- **Replicas not distributing traffic**: verify the service has a public domain; private-only services don't load-balance
- **Multi-region patch ignored**: verify exact region identifiers (see table above)
- **Healthcheck timeout**: increase `healthcheckTimeout` if the service has slow startup
- **App sleeping causes cold start issues**: disable for latency-sensitive services
- **Cron job runs multiple times**: check for duplicate services with the same schedule
- **Volume data lost**: volumes persist across deploys but NOT across service deletion — deleting a service deletes its volumes
