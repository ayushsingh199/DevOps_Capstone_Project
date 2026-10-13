#!/usr/bin/env bash
# In-cluster CPU stress against the backend Service to demonstrate the HPA scaling out.
#   scripts/hpa-stress.sh [duration-seconds] [parallel-pods]
set -euo pipefail
DURATION="${1:-180}"
PODS="${2:-4}"
NS=medislot
TARGET="http://medislot-backend:8000/api/appointments/stats"

for i in $(seq 1 "$PODS"); do
  kubectl -n "$NS" run "load-$i" --labels=app=medislot-load --restart=Never --image=busybox:1.37 \
    --overrides='{"spec":{"securityContext":{"runAsNonRoot":true,"runAsUser":65534,"seccompProfile":{"type":"RuntimeDefault"}},"containers":[{"name":"load","image":"busybox:1.37","command":["sh","-c","end=$(( $(date +%s) + '"$DURATION"' )); while [ $(date +%s) -lt $end ]; do wget -q -O /dev/null '"$TARGET"'; done"],"securityContext":{"allowPrivilegeEscalation":false,"capabilities":{"drop":["ALL"]}},"resources":{"requests":{"cpu":"10m"},"limits":{"cpu":"200m","memory":"32Mi"}}}]}}' \
    >/dev/null
done
echo "Started $PODS load pods for ${DURATION}s. Watch scaling with:"
echo "  kubectl get hpa,pods -n $NS -w"
echo "Clean up afterwards with:"
echo "  kubectl -n $NS delete pod -l app=medislot-load"
