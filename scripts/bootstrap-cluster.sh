#!/usr/bin/env bash
# Install the platform (ingress, monitoring, Argo CD) and the MediSlot app on a cluster.
#
#   scripts/bootstrap-cluster.sh eks     # AWS EKS created by terraform/
#   scripts/bootstrap-cluster.sh local   # local k3s / kind with images from docker compose
#
# Idempotent: safe to re-run. Secrets are generated here and never written to Git.
set -euo pipefail

TARGET="${1:-eks}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NS=medislot

log() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
need() { command -v "$1" >/dev/null || { echo "missing required tool: $1" >&2; exit 1; }; }
need kubectl
need helm
need openssl

case "$TARGET" in
  eks)   APP_VALUES="$ROOT/helm/medislot/values-eks.yaml" ;;
  local) APP_VALUES="$ROOT/helm/medislot/values-dev.yaml" ;;
  *) echo "usage: $0 [eks|local]" >&2; exit 1 ;;
esac

log "Cluster: $(kubectl config current-context)"
kubectl get nodes -o wide

log "Helm repositories"
helm repo add traefik https://traefik.github.io/charts >/dev/null 2>&1 || true
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null 2>&1 || true
helm repo add argo https://argoproj.github.io/argo-helm >/dev/null 2>&1 || true
helm repo update >/dev/null

log "Namespaces and storage"
kubectl apply -f "$ROOT/k8s/namespace.yaml"
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -
if [[ "$TARGET" == "eks" ]]; then
  kubectl apply -f "$ROOT/k8s/storageclass-gp3.yaml"
  # Only one default StorageClass: demote EKS's legacy gp2 if it is marked default.
  kubectl annotate storageclass gp2 storageclass.kubernetes.io/is-default-class=false --overwrite 2>/dev/null || true
fi

log "Secrets (generated once, kept only in the cluster)"
if ! kubectl -n "$NS" get secret medislot-db >/dev/null 2>&1; then
  kubectl -n "$NS" create secret generic medislot-db \
    --from-literal=username=medislot \
    --from-literal=password="$(openssl rand -hex 24)"
fi
if ! kubectl -n monitoring get secret grafana-admin >/dev/null 2>&1; then
  kubectl -n monitoring create secret generic grafana-admin \
    --from-literal=admin-user=admin \
    --from-literal=admin-password="$(openssl rand -base64 18 | tr -d '/+=')"
fi

log "Ingress controller (Traefik)"
helm upgrade --install traefik traefik/traefik -n traefik --create-namespace \
  -f "$ROOT/k8s/traefik-values.yaml" --wait --timeout 10m

log "Monitoring (Prometheus + Grafana)"
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack -n monitoring \
  -f "$ROOT/monitoring/prometheus-values.yaml" -f "$ROOT/monitoring/grafana-values.yaml" \
  --wait --timeout 15m

log "MediSlot application (Helm)"
if [[ "$TARGET" == "local" ]]; then
  # Local clusters reuse the medislot DB secret too, instead of the throwaway values password.
  EXTRA=(--set postgresql.auth.existingSecret=medislot-db)
else
  EXTRA=()
fi
helm upgrade --install medislot "$ROOT/helm/medislot" -n "$NS" \
  -f "$APP_VALUES" ${EXTRA[@]+"${EXTRA[@]}"} --wait --timeout 10m

if [[ "$TARGET" == "eks" ]]; then
  log "Argo CD (GitOps) — takes over the medislot release from here on"
  helm upgrade --install argocd argo/argo-cd -n argocd --create-namespace \
    -f "$ROOT/argocd/argocd-values.yaml" --wait --timeout 10m
  kubectl apply -f "$ROOT/argocd/application.yaml"
fi

log "Done"
kubectl get pods,svc,ingress,hpa -n "$NS"
cat <<MSG

Grafana password : kubectl -n monitoring get secret grafana-admin -o jsonpath='{.data.admin-password}' | base64 -d
Grafana UI       : kubectl -n monitoring port-forward svc/monitoring-grafana 3001:80
Prometheus UI    : kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090
App URL          : kubectl -n traefik get svc traefik -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
MSG
if [[ "$TARGET" == "eks" ]]; then
  cat <<MSG
Argo CD password : kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
Argo CD UI       : kubectl -n argocd port-forward svc/argocd-server 8081:80
MSG
fi
