#!/usr/bin/env bash
# Deploy and wait for healthy status
# Usage: railway-deploy-wait.sh <service> <environment> "<deploy message>" [timeout_seconds]
#
# Deploys the current directory to the specified service/environment,
# then polls deployment status until SUCCESS, FAILED, or timeout.
#
# Exit codes:
#   0 — deployment succeeded (SUCCESS)
#   1 — deployment failed (FAILED or CRASHED)
#   2 — timeout waiting for deployment
#   3 — missing arguments
#   4 — deploy command failed

set -e

SERVICE="${1:?Usage: railway-deploy-wait.sh <service> <environment> '<message>' [timeout_seconds]}"
ENVIRONMENT="${2:?Usage: railway-deploy-wait.sh <service> <environment> '<message>' [timeout_seconds]}"
MESSAGE="${3:?Usage: railway-deploy-wait.sh <service> <environment> '<message>' [timeout_seconds]}"
TIMEOUT="${4:-300}"

echo "Deploying to $SERVICE in $ENVIRONMENT..."

# Deploy
if ! railway up --service "$SERVICE" --environment "$ENVIRONMENT" --detach -m "$MESSAGE"; then
  echo "ERROR: Deploy command failed"
  exit 4
fi

echo "Deploy initiated. Waiting up to ${TIMEOUT}s for healthy status..."

ELAPSED=0
POLL_INTERVAL=10

while [[ $ELAPSED -lt $TIMEOUT ]]; do
  sleep $POLL_INTERVAL
  ELAPSED=$((ELAPSED + POLL_INTERVAL))

  # Get latest deployment status
  STATUS=$(railway deployment list --service "$SERVICE" --environment "$ENVIRONMENT" --limit 1 --json 2>/dev/null \
    | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4)

  case "$STATUS" in
    SUCCESS)
      echo "Deployment succeeded after ${ELAPSED}s"
      # Verify with logs
      railway logs --service "$SERVICE" --environment "$ENVIRONMENT" --lines 10 --json 2>/dev/null | head -20
      exit 0
      ;;
    FAILED|CRASHED)
      echo "ERROR: Deployment $STATUS after ${ELAPSED}s"
      echo "Recent logs:"
      railway logs --service "$SERVICE" --environment "$ENVIRONMENT" --lines 50 --json 2>/dev/null | tail -30
      exit 1
      ;;
    BUILDING|DEPLOYING)
      echo "  Status: $STATUS (${ELAPSED}s elapsed)"
      ;;
    *)
      echo "  Status: ${STATUS:-unknown} (${ELAPSED}s elapsed)"
      ;;
  esac
done

echo "ERROR: Timeout after ${TIMEOUT}s. Last status: ${STATUS:-unknown}"
echo "Check status manually: railway service status --service $SERVICE --json"
exit 2
