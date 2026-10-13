# Demo runbook

Every command for the recorded walkthrough, in the order the submission guidelines ask for:
slides → codebase → CI/CD → Terraform → Argo CD → Kubernetes → Prometheus → Grafana.
Read [`VIDEO_SCRIPT.md`](VIDEO_SCRIPT.md) for what to say at each step.

## 0. Before you hit record (≈10 min)

```bash
cd ~/Desktop/DevOps_Capstone_Project
aws sts get-caller-identity                       # right AWS account
aws eks update-kubeconfig --region ap-south-1 --name medislot-dev-eks
kubectl get nodes                                  # 2 Ready nodes

# Terminal tabs to keep open (each one blocks, so give each its own tab):
kubectl -n argocd port-forward svc/argocd-server 8081:80
kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090
kubectl -n monitoring port-forward svc/monitoring-grafana 3001:80

# Passwords (copy somewhere off-screen):
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo
kubectl -n monitoring get secret grafana-admin -o jsonpath='{.data.admin-password}' | base64 -d; echo

# App URL (the AWS load balancer):
kubectl -n traefik get svc traefik -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'; echo
```

Browser tabs to pre-open:

| Tab | URL |
|-----|-----|
| App | `http://<load-balancer-hostname>/` |
| GitHub Actions | https://github.com/ayushsingh199/DevOps_Capstone_Project/actions |
| GHCR packages | https://github.com/ayushsingh199?tab=packages |
| AWS VPC | https://ap-south-1.console.aws.amazon.com/vpcconsole/home?region=ap-south-1#vpcs: |
| AWS EKS | https://ap-south-1.console.aws.amazon.com/eks/clusters?region=ap-south-1 |
| Argo CD | http://localhost:8081 (user `admin`) |
| Prometheus | http://localhost:9090/targets |
| Grafana | http://localhost:3001 → Dashboards → *MediSlot · Service Overview* |

Start some background traffic so the Grafana panels are alive:

```bash
./scripts/load-test.sh http://<load-balancer-hostname> 900 5 &
```

## 1. Slides (≈3 min)

Present `demo/MediSlot-Capstone.pdf` (or the `.pptx`) through the architecture slide.

## 2. Codebase (≈2 min)

Show in the editor: `backend/app/` (routers → services → models), `backend/alembic/versions/`,
`backend/tests/`, `frontend/src/`, the two Dockerfiles, `.github/workflows/ci-cd.yml`,
`terraform/`, `helm/medislot/`, `argocd/application.yaml`, `monitoring/`.

## 3. CI/CD: trigger a push (≈3 min)

Make a visible change, for example the subtitle in `frontend/src/App.jsx`
(`"Today's schedule and patient flow"` → `"Today's schedule, live from EKS"`):

```bash
git add frontend/src/App.jsx
git commit -m "feat(frontend): update dashboard subtitle for the live demo"
git push
gh run watch            # or watch it in the Actions tab
```

Talk through the jobs while they run: tests → frontend build → image builds → Trivy → push → deploy commit.
Then open the GHCR packages page and point at the new SHA tag.

## 4. Terraform + AWS Console (≈2 min)

```bash
cd terraform
terraform plan          # "No changes. Your infrastructure matches the configuration."
terraform output
cd ..
```

AWS Console: VPC → the `medislot-dev-vpc` with its 4 subnets; EKS → `medislot-dev-eks` → Compute → node group.

## 5. Argo CD (≈2 min)

Argo CD UI → `medislot` application: **Synced / Healthy**. After the CI deploy commit appears, click
**Refresh** (Argo CD polls every 1–2 minutes and caches Git lookups; Refresh syncs immediately), then
open *History and rollback* and show the new revision. Click the resource tree to show the
Deployments, the ReplicaSet with the new image and the rolling update.

## 6. Kubernetes (≈2 min)

```bash
kubectl get pods -n medislot -o wide
kubectl get svc -n medislot
kubectl get ingress -n medislot
kubectl get hpa -n medislot
helm list -A
kubectl -n medislot describe deploy medislot-backend | grep Image
```

Refresh the app in the browser: the sidebar **Build** now shows the new commit SHA, and the subtitle has changed.

## 7. Prometheus (≈1 min)

http://localhost:9090/targets → `serviceMonitor/medislot/medislot-backend` with 2/2 endpoints **UP**.
Optional: *Alerts* tab → the three `MediSlot*` rules.

## 8. Grafana (≈1 min)

Dashboard *MediSlot · Service Overview*: requests/s, p95 latency, error rate, bookings by visit type,
HPA replicas. Book an appointment in the app and watch *Appointments booked* tick up.

## 9. Optional extras if time allows

```bash
./scripts/hpa-stress.sh 180 4 && kubectl get hpa -n medislot -w      # autoscaling
kubectl apply -f troubleshooting/namespace.yaml -f troubleshooting/broken-service.yaml   # troubleshooting
```

## 10. After recording: stop the bill

```bash
./scripts/teardown.sh      # removes NLB + EBS, then terraform destroy
```

Screenshot the final `Destroy complete! Resources: N destroyed.` line for M7.
