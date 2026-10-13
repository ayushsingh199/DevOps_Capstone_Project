# Troubleshooting lab

Three deliberately broken workloads in an isolated `medislot-lab` namespace, each showing a
failure mode that comes up constantly in real clusters. The production `medislot` namespace is never touched.

```bash
kubectl apply -f troubleshooting/namespace.yaml
kubectl apply -f troubleshooting/broken-image.yaml -f troubleshooting/broken-service.yaml -f troubleshooting/broken-probe.yaml
kubectl -n medislot-lab get pods,svc
```

## 1. `ImagePullBackOff` — wrong image tag

| Step | Command | What you see |
|------|---------|--------------|
| Spot it | `kubectl -n medislot-lab get pods` | `lab-api-…  0/1  ImagePullBackOff` |
| Explain it | `kubectl -n medislot-lab describe pod -l app=lab-api` | Events: `Failed to pull image … manifest unknown` |
| Timeline | `kubectl -n medislot-lab get events --sort-by=.lastTimestamp` | `Pulling` → `Failed` → `BackOff` |

**Fix:** point at a tag that exists. CI only ever pushes commit-SHA tags:

```bash
kubectl -n medislot-lab set image deploy/lab-api api=ghcr.io/ayushsingh199/medislot-backend:<git-sha>
```

## 2. Service with no endpoints — label/selector mismatch

| Step | Command | What you see |
|------|---------|--------------|
| Service exists | `kubectl -n medislot-lab get svc lab-web` | ClusterIP assigned, looks fine |
| No backends | `kubectl -n medislot-lab get endpointslices -l kubernetes.io/service-name=lab-web` | `ENDPOINTS <unset>` |
| Compare labels | `kubectl -n medislot-lab get pods --show-labels` | pods carry `app=lab-frontend`, Service selects `app=lab-web` |

**Lesson:** a Service finds Pods *only* through labels. No match → no endpoints → connection refused / 503.

```bash
kubectl -n medislot-lab patch svc lab-web -p '{"spec":{"selector":{"app":"lab-frontend"}}}'
```

## 3. Running but not Ready — failing readiness probe

| Step | Command | What you see |
|------|---------|--------------|
| Spot it | `kubectl -n medislot-lab get pods -l app=lab-probe` | `Running` but `0/1` READY |
| Explain it | `kubectl -n medislot-lab describe pod -l app=lab-probe` | `Readiness probe failed: … statuscode: 404` |

**Lesson:** readiness gates traffic; an unready Pod is removed from Service endpoints but *not* restarted
(that is what liveness does). MediSlot uses `/health` for liveness and `/ready` (checks the database) for readiness.

```bash
kubectl -n medislot-lab patch deploy lab-probe --type=json \
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/httpGet/path","value":"/"}]'
```

## Clean up

```bash
kubectl delete namespace medislot-lab
```
