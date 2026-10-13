#!/usr/bin/env bash
# Remove everything Kubernetes created *outside* Terraform's state (load balancers,
# EBS volumes), then destroy the Terraform infrastructure. Skipping the first part
# leaves orphaned NLBs/ENIs that block VPC deletion and keep billing.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

log() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

if kubectl cluster-info >/dev/null 2>&1; then
  log "Removing Argo CD application (so it cannot re-create resources)"
  kubectl -n argocd delete application medislot --ignore-not-found --wait=true || true

  log "Deleting app namespace (PVC -> EBS volume is deleted with it)"
  kubectl delete namespace medislot --ignore-not-found --wait=true --timeout=5m || true

  log "Uninstalling Traefik (deletes the AWS Network Load Balancer)"
  helm uninstall traefik -n traefik --wait 2>/dev/null || true

  log "Waiting for LoadBalancer services to disappear"
  for _ in $(seq 1 30); do
    remaining=$(kubectl get svc -A -o jsonpath='{range .items[?(@.spec.type=="LoadBalancer")]}{.metadata.name}{"\n"}{end}' | grep -c . || true)
    [[ "$remaining" -eq 0 ]] && break
    sleep 10
  done
  helm uninstall argocd -n argocd 2>/dev/null || true
  helm uninstall monitoring -n monitoring 2>/dev/null || true
else
  echo "Cluster not reachable; skipping in-cluster cleanup."
fi

log "terraform destroy"
terraform -chdir="$ROOT/terraform" destroy -auto-approve
