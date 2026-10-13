#!/usr/bin/env bash
# Generate realistic API traffic so Grafana panels populate and the HPA has CPU to react to.
#
#   scripts/load-test.sh http://<ingress-host> [duration-seconds] [concurrency]
#   scripts/load-test.sh http://localhost:3000 120 20
set -euo pipefail

BASE="${1:?usage: $0 <base-url> [duration] [concurrency]}"
DURATION="${2:-120}"
CONCURRENCY="${3:-10}"
END=$(( $(date +%s) + DURATION ))

worker() {
  local paths=("/api/appointments" "/api/appointments/stats" "/api/doctors" "/api/info"
               "/api/appointments?status=scheduled" "/api/appointments/999999")
  while (( $(date +%s) < END )); do
    curl -s -o /dev/null "$BASE${paths[RANDOM % ${#paths[@]}]}" || true
  done
}

echo "Hitting $BASE for ${DURATION}s with $CONCURRENCY workers..."
for _ in $(seq 1 "$CONCURRENCY"); do worker & done
wait
echo "Done. Watch: kubectl get hpa -n medislot -w"
