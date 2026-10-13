# MediSlot — Clinic Appointment Platform on AWS EKS

[![CI/CD](https://github.com/ayushsingh199/DevOps_Capstone_Project/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/ayushsingh199/DevOps_Capstone_Project/actions/workflows/ci-cd.yml)

**MediSlot** is a scheduling platform for outpatient clinics. Front-desk staff book patients with
doctors, check them in when they arrive and close the visit when it's done, while the dashboard
shows the day's load at a glance. The system refuses double-bookings: a doctor can't have two
overlapping active appointments.

This repository takes MediSlot from a developer laptop to a monitored, autoscaled, GitOps-managed
Kubernetes deployment on AWS:

```
React + FastAPI + PostgreSQL → pytest → Docker → GitHub Actions → Trivy → GHCR
  → Terraform (VPC + EKS) → Helm → Argo CD → Ingress → HPA → Prometheus + Grafana
```

---

## Contents

1. [Architecture](#1-architecture)
2. [Tech stack](#2-tech-stack)
3. [Repository layout](#3-repository-layout)
4. [The application](#4-the-application)
5. [Run locally (Docker Compose)](#5-run-locally-docker-compose)
6. [Testing and code quality](#6-testing-and-code-quality)
7. [Docker images](#7-docker-images)
8. [CI/CD pipeline](#8-cicd-pipeline)
9. [DevSecOps: Trivy](#9-devsecops-trivy)
10. [Terraform: AWS VPC + EKS](#10-terraform-aws-vpc--eks)
11. [Kubernetes + Helm](#11-kubernetes--helm)
12. [GitOps with Argo CD](#12-gitops-with-argo-cd)
13. [Autoscaling (HPA)](#13-autoscaling-hpa)
14. [Observability: Prometheus + Grafana](#14-observability-prometheus--grafana)
15. [Troubleshooting lab](#15-troubleshooting-lab)
16. [Tear down (cost control)](#16-tear-down-cost-control)
    - [Evidence](#evidence-captured-from-the-live-eks-deployment)
17. [Rubric map](#17-rubric-map)
18. [Design decisions](#18-design-decisions)

---

## 1. Architecture

```mermaid
flowchart LR
  dev([Developer]) -- git push --> gh[(GitHub<br/>main)]
  gh --> ci{{GitHub Actions}}
  subgraph CI[CI/CD pipeline]
    direction TB
    t1[ruff + pytest<br/>+ Alembic on Postgres] --> b[docker build]
    t2[eslint + vite build] --> b
    b --> tr[Trivy scan<br/>HIGH/CRITICAL gate]
    tr --> push[push :git-sha]
    push --> bump[bump image tag<br/>values-eks.yaml]
  end
  ci --> CI
  push --> ghcr[(GHCR)]
  bump --> gh
  subgraph AWS[AWS ap-south-1 · provisioned by Terraform]
    subgraph VPC[VPC 10.20.0.0/16 · 2 public + 2 private subnets]
      nlb[Network Load Balancer] --> trf[Traefik Ingress]
      subgraph EKS[EKS · managed node group]
        argo[Argo CD] -. syncs .-> app
        trf -- "/" --> fe[frontend ×2<br/>React on Nginx]
        trf -- "/api" --> be[backend ×2..6<br/>FastAPI + HPA]
        fe -- /api --> be
        be --> pg[(PostgreSQL<br/>StatefulSet + EBS gp3)]
        prom[Prometheus] -- scrape /metrics --> be
        graf[Grafana] --> prom
        app((medislot<br/>namespace))
      end
    end
  end
  argo -- watches --> gh
  EKS -- pulls images --> ghcr
  user([Clinic staff]) --> nlb
```

**Request path:** browser → AWS NLB → Traefik Ingress → `/` frontend Service or `/api` backend
Service → Pods. The frontend Nginx also proxies `/api`, so the same image works behind Docker
Compose, an Ingress or a plain port-forward. The browser only ever calls relative URLs.

**Delivery path (pull-based GitOps):** CI never holds cluster credentials. It publishes an image and
commits the new tag to Git; Argo CD, running inside the cluster, pulls that change and rolls it out.

## 2. Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, Vite 6, plain CSS (responsive), Nginx (unprivileged) |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic 2, Alembic, Uvicorn |
| Database | PostgreSQL 16 |
| Quality | pytest + coverage, ruff (lint + format), ESLint, Prettier |
| Containers | Docker multi-stage builds, Docker Compose |
| CI/CD | GitHub Actions, GitHub Container Registry (GHCR) |
| Security | Trivy image scanning (gate + SARIF), SHA-pinned actions, non-root images, Pod Security "restricted", NetworkPolicy |
| Infrastructure | Terraform, AWS VPC, EKS 1.36 (terraform-aws-modules), EBS CSI via Pod Identity |
| Kubernetes | Helm 3/4 chart, Traefik Ingress, HPA, PDB, StatefulSet |
| GitOps | Argo CD |
| Observability | kube-prometheus-stack (Prometheus Operator, Grafana), ServiceMonitor, PrometheusRule |

## 3. Repository layout

```text
.
├── backend/                  FastAPI service
│   ├── app/                  config, database, models, schemas, routers/, services/
│   ├── alembic/versions/     0001 schema, 0002 doctor roster seed
│   ├── tests/                pytest suite (+ conftest.py) on isolated SQLite
│   ├── Dockerfile            multi-stage, non-root (UID 10001)
│   ├── pytest.ini · pyproject.toml (ruff) · requirements*.txt
├── frontend/                 React + Vite dashboard
│   ├── src/                  App.jsx, components/, api.js, styles.css
│   ├── Dockerfile            multi-stage: node build → nginx-unprivileged (UID 101)
│   └── nginx.conf.template   SPA routing + /api reverse proxy
├── docker-compose.yml        postgres + backend + frontend
├── .github/workflows/        ci-cd.yml
├── terraform/                VPC + EKS (+ terraform.tfvars.example)
├── k8s/                      namespace (restricted PSA), gp3 StorageClass, Traefik values
├── helm/medislot/            Helm chart + values-dev.yaml / values-eks.yaml + Grafana dashboard
├── argocd/                   Argo CD values + Application manifest
├── monitoring/               Prometheus and Grafana Helm values
├── scripts/                  bootstrap, teardown, load-test, HPA stress
├── troubleshooting/          deliberately broken manifests + investigation guide
└── demo/                     presentation slides, video script and demo runbook
```

## 4. The application

### Domain model

| Table | Key columns |
|-------|-------------|
| `doctors` | `full_name`, `specialty`, `room` |
| `appointments` | `patient_name`, `patient_phone`, `doctor_id → doctors`, `scheduled_at`, `duration_minutes` (10–240), `visit_type`, `status` (`scheduled → checked_in → completed`, or `cancelled` / `no_show`), `reason` |

Both tables are created by Alembic migrations (`backend/alembic/versions/`). Migrations run under a
Postgres advisory lock, so several replicas can start at once without racing.

### REST API

Interactive docs: **`/docs`** (Swagger UI).

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness: the process is up (no DB call) |
| GET | `/ready` | Readiness: returns 503 unless PostgreSQL answers |
| GET | `/metrics` | Prometheus metrics |
| GET | `/api/info` | Running version (git SHA) and environment |
| GET | `/api/appointments` | List; filters `status`, `doctor_id`, `date`, `q` |
| GET | `/api/appointments/stats` | Dashboard KPIs |
| GET | `/api/appointments/{id}` | Fetch one |
| POST | `/api/appointments` | Book (**409** if the doctor is already booked for that slot) |
| PUT | `/api/appointments/{id}` | Reschedule / reassign / change status |
| DELETE | `/api/appointments/{id}` | Delete |
| GET · POST | `/api/doctors` | List / register doctors |
| GET · DELETE | `/api/doctors/{id}` | Fetch / remove (409 if they have appointments) |

### UI

A dashboard with KPI cards (visits today, upcoming, checked in, completion rate), today's
schedule with one-click **Check in → Complete**, doctor load bars, a full appointment table with
status chips, doctor filter and search, a booking/edit modal and doctor management. The sidebar
card shows API health and the **build SHA served by the running backend**, so you can see a
deployment change in the browser. The layout collapses to a single column with card-style rows on
phones.

## 5. Run locally (Docker Compose)

Requires Docker with the Compose plugin.

```bash
docker compose up --build
```

| URL | What |
|-----|------|
| http://localhost:3000 | MediSlot UI |
| http://localhost:8000/docs | Swagger |
| http://localhost:8000/health · /ready · /metrics | Probes and metrics |

On first start the backend applies migrations and seeds a few demo appointments (`SEED_DEMO_DATA=true`).

```bash
docker compose down        # stop
docker compose down -v     # stop and delete the database volume
```

<details><summary>Run without Docker</summary>

```bash
cd backend && python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL='postgresql+psycopg://medislot:medislot-local@localhost:5432/medislot'
alembic upgrade head && python -m app.seed
uvicorn app.main:app --reload --port 8000

cd ../frontend && npm ci && npm run dev    # http://localhost:5173 (proxies /api to :8000)
```
</details>

## 6. Testing and code quality

```bash
cd backend
pip install -r requirements-dev.txt
pytest -v --cov            # 23 tests, ~97% line coverage
ruff check . && ruff format --check .
cd ../frontend && npm run lint && npm run format:check
```

- **Isolation:** `tests/conftest.py` gives every test a fresh in-memory SQLite database through
  FastAPI's dependency override. The production PostgreSQL database is never touched.
- **Coverage:** every endpoint group (health, doctors, appointments, stats, metrics) plus
  validation errors (422), not-found (404), double-booking (409), status transitions, filters and a
  full upgrade/downgrade round-trip of the Alembic chain.
- **In CI** the migrations are additionally run against a real PostgreSQL 16 service container.

## 7. Docker images

| Image | Build | Runtime user | Notes |
|-------|-------|--------------|-------|
| `medislot-backend` | `python:3.12-slim` builder (wheels) → slim runtime | `app` (UID 10001) | OS packages upgraded, pip/setuptools removed, HEALTHCHECK on `/health` |
| `medislot-frontend` | `node:22-alpine` (npm ci + vite build) → `nginx-unprivileged:1.29-alpine` | `nginx` (UID 101), port 8080 | No Node toolchain in the final image; security headers; `/healthz` |

```bash
docker build -t medislot-backend:local ./backend
docker build -t medislot-frontend:local ./frontend
docker run --rm --entrypoint id medislot-backend:local   # uid=10001(app)
```

## 8. CI/CD pipeline

[`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml) runs on every push and pull request to `main`.

```mermaid
flowchart LR
  A[Backend: ruff + pytest<br/>+ Alembic on Postgres] --> C
  B[Frontend: eslint + build] --> C
  C[Build image<br/>backend / frontend] --> D[Trivy gate]
  D -->|clean| E[Push ghcr.io/…:git-sha]
  E --> F[GitOps: commit new tag<br/>to values-eks.yaml]
  F -.-> G[Argo CD syncs EKS]
```

| Stage | What happens | Fails the build when |
|-------|--------------|----------------------|
| `backend-test` | ruff lint/format, `pytest` with coverage + JUnit report, Alembic up/down/up on Postgres 16 | any lint error, test failure or migration error |
| `frontend-build` | `npm ci`, ESLint, `vite build` (artifact uploaded) | lint error or build error |
| `build-scan-push` (matrix) | Buildx build with GHA cache → Trivy SARIF to the Security tab → Trivy gate → push | fixable HIGH/CRITICAL CVE |
| `deploy` | `yq` sets both image tags to the commit SHA and pushes `deploy: release …` (`[skip ci]`) | push conflict after 3 retries |

- **Images are tagged only with the full Git commit SHA**, never `latest`:
  `ghcr.io/ayushsingh199/medislot-backend:<sha>`. Every running Pod traces back to one commit, and
  `/api/info` reports it.
- Only images that pass the scan are pushed; pull requests build and scan but never publish.
- Every third-party action is **pinned to a commit SHA** (with the version in a comment). A tag can
  be moved by an attacker; a SHA cannot.

## 9. DevSecOps: Trivy

Each image is scanned twice in the pipeline: once to produce a SARIF report for GitHub's
**Security → Code scanning** tab, and once as a gate with `severity: HIGH,CRITICAL`,
`ignore-unfixed: true` and `exit-code: 1`.

**What Trivy scanned and what the result means.** Trivy inspects the OS packages (Debian 13 for
the backend, Alpine 3.23 for the frontend) and the language dependencies inside each image
(Python wheels in `site-packages`, the Nginx build) against vulnerability databases. Both images
pass the gate: **no HIGH or CRITICAL vulnerability that has a fix available**. The backend
image still contains HIGH-rated CVEs that the gate deliberately tolerates because no patched
package exists yet. One example is **CVE-2026-76642** in Debian's `util-linux` packages
(`bsdutils`, `libblkid1`), marked *affected / no fix* by Debian. Failing the build on those would
block every release with nothing the team can do about it. The packages are only in the image as
base-OS dependencies: the API never invokes those utilities, and it runs as a non-root user with a
read-only root filesystem and all Linux capabilities dropped, which limits the exposure. The
`apt-get upgrade` in the Dockerfile means a fix is picked up on the next build once Debian ships it.

Other security layers in the project:

| Layer | Control |
|-------|---------|
| Supply chain | SHA-pinned actions, pinned Python deps, `npm ci` from a lockfile |
| Secrets | `.gitignore` for `.env` / tfvars / state; DB and Grafana passwords generated in-cluster by the bootstrap script; AWS credentials only in the local AWS CLI profile |
| Container | non-root users, multi-stage builds, minimal runtime images |
| Kubernetes | namespace enforces Pod Security **restricted**; `readOnlyRootFilesystem`, `drop: [ALL]`, `RuntimeDefault` seccomp; NetworkPolicy lets only backend Pods reach Postgres |
| AWS | worker nodes in private subnets, EBS volumes encrypted, EBS CSI permissions scoped to its own service account via Pod Identity |

## 10. Terraform: AWS VPC + EKS

```text
terraform/
├── versions.tf        Terraform + AWS provider constraints
├── providers.tf       provider, default tags, AZ lookup
├── variables.tf       region, CIDR, k8s version, node sizing (with validation)
├── vpc.tf             VPC: 2 public + 2 private subnets, IGW, NAT gateway, LB subnet tags
├── eks.tf             EKS cluster, core add-ons, managed node group
├── iam.tf             EBS CSI driver role (Pod Identity)
├── outputs.tf         cluster name/endpoint, subnet IDs, kubeconfig command
└── terraform.tfvars.example
```

| Resource | Configuration |
|----------|---------------|
| VPC | `10.20.0.0/16`, DNS hostnames on |
| Public subnets | `10.20.0.0/24`, `10.20.1.0/24` (2 AZs), tagged `kubernetes.io/role/elb` |
| Private subnets | `10.20.10.0/24`, `10.20.11.0/24`, tagged `kubernetes.io/role/internal-elb` |
| NAT | one shared NAT gateway (`single_nat_gateway = true` keeps cost down) |
| EKS | `medislot-dev-eks`, Kubernetes 1.36, public + private endpoint, creator gets admin via access entry |
| Add-ons | vpc-cni, kube-proxy, coredns, eks-pod-identity-agent, aws-ebs-csi-driver, metrics-server |
| Node group | `medislot-dev-general`: 2 × t3.large (min 2, max 3), AL2023, private subnets. New AWS accounts start with a 5-vCPU On-Demand quota, and 2 × t3.large (4 vCPU, 35 pods per node) fits it |

```bash
aws configure                                # credentials stay in ~/.aws, never in this repo
cd terraform
cp terraform.tfvars.example terraform.tfvars # optional overrides
terraform init
terraform plan -out tfplan
terraform apply tfplan                       # ~15 minutes
$(terraform output -raw configure_kubectl)   # aws eks update-kubeconfig …
```

## 11. Kubernetes + Helm

```bash
./scripts/bootstrap-cluster.sh eks    # or: local  (k3s / kind with compose-built images)
```

The script is idempotent. It applies `k8s/namespace.yaml` and the gp3 StorageClass, generates the
DB and Grafana secrets inside the cluster, installs Traefik, kube-prometheus-stack and the app
(`helm upgrade --install`), then hands the app over to Argo CD.

Manual equivalent for the application:

```bash
kubectl apply -f k8s/namespace.yaml
helm upgrade --install medislot ./helm/medislot -n medislot -f helm/medislot/values-eks.yaml
kubectl get pods,svc,ingress,hpa -n medislot
helm list -n medislot
```

What the chart creates in the `medislot` namespace:

| Kind | Name | Notes |
|------|------|-------|
| Deployment | `medislot-backend` | 2–6 replicas (HPA); initContainers `wait-for-db` + `migrate`; startup/liveness (`/health`) and readiness (`/ready`) probes |
| Deployment | `medislot-frontend` | 2 replicas; read-only FS with emptyDirs for Nginx |
| StatefulSet | `medislot-postgres` | 1 replica, 2 Gi gp3 PVC |
| Service (ClusterIP) | `medislot-backend:8000`, `medislot-frontend:80`, `medislot-postgres:5432` | |
| Ingress | `medislot` | `/api` → backend, `/` → frontend (class `traefik`) |
| HPA | `medislot-backend` | CPU 60% target |
| PDB | backend, frontend | `minAvailable: 1` keeps the app up during node drains |
| NetworkPolicy | `medislot-postgres` | ingress only from backend Pods |
| ServiceMonitor / PrometheusRule / ConfigMap | | scrape config, alerts, Grafana dashboard |

Values overlays: `values.yaml` (defaults), `values-dev.yaml` (local cluster, compose-built images),
`values-eks.yaml` (GHCR images; tags managed by CI).

**Why Traefik?** An Ingress resource is only configuration; a controller has to implement it. The
community `ingress-nginx` controller was retired in March 2026, so this project uses Traefik with a
standard `networking.k8s.io/v1` Ingress. On EKS its Service gets an AWS Network Load Balancer.

## 12. GitOps with Argo CD

[`argocd/application.yaml`](argocd/application.yaml) points Argo CD at `helm/medislot` on `main`
with `values-eks.yaml`, using automated sync, `prune` and `selfHeal`.

```text
git push → CI builds + scans + pushes :<sha> → CI commits "deploy: release <sha>"
        → Argo CD detects the diff (≤ 60 s) → rolling update (maxUnavailable 0)
        → UI sidebar shows the new build SHA
```

```bash
kubectl -n argocd port-forward svc/argocd-server 8081:80
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
```

Rollback means reverting the deploy commit in Git: Argo CD converges the cluster back.
`selfHeal` also reverts manual `kubectl edit` drift.

Argo CD polls Git every 60 s (plus jitter), and its repo-server caches Git lookups, so a release can
take a couple of minutes to appear. Press **Refresh** in the Argo CD UI to sync immediately. A GitHub
webhook to Argo CD would make this instant, but it needs a public Argo CD endpoint.

The deploy job is serialized (`concurrency: deploy-eks`) and skips commits that a newer commit has
already superseded, so two pipelines finishing together can never roll production backwards.

## 13. Autoscaling (HPA)

The backend HPA (`autoscaling/v2`) scales from 2 to 6 replicas at 60% average CPU of the requested
100m, using metrics from the metrics-server EKS add-on.

```bash
./scripts/hpa-stress.sh 180 4          # 4 in-cluster load pods for 3 minutes
kubectl get hpa,pods -n medislot -w    # watch REPLICAS climb, then settle after ~2 min
kubectl -n medislot delete pod -l app=medislot-load
```

## 14. Observability: Prometheus + Grafana

- **Instrumentation:** `prometheus-fastapi-instrumentator` exports `http_requests_total` and
  `http_request_duration_seconds`. The domain counters are `medislot_appointments_booked_total{visit_type}`,
  `medislot_appointment_status_changes_total{status}` and `medislot_booking_conflicts_total`.
- **Collection:** kube-prometheus-stack (values in [`monitoring/`](monitoring/)). The chart's
  **ServiceMonitor** makes the operator scrape every backend Pod's `/metrics` every 15 s.
- **Dashboard:** *MediSlot · Service Overview* is provisioned automatically from a ConfigMap. It
  shows requests/s, p50/p95/p99 latency, 5xx error rate, pods up, bookings by visit type, blocked
  double-bookings, CPU and memory per pod, and HPA current vs desired replicas.
- **Alerts:** `MediSlotBackendDown`, `MediSlotHighErrorRate` (> 5% 5xx) and `MediSlotSlowRequests` (p95 > 500 ms).

```bash
kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090   # /targets
kubectl -n monitoring port-forward svc/monitoring-grafana 3001:80
kubectl -n monitoring get secret grafana-admin -o jsonpath='{.data.admin-password}' | base64 -d
./scripts/load-test.sh http://<ingress-host> 120 10   # traffic for the panels
```

## 15. Troubleshooting lab

[`troubleshooting/`](troubleshooting/README.md) contains three broken workloads in an isolated
namespace, each with symptoms, diagnosis commands and the fix:

1. `ImagePullBackOff` from a non-existent image tag
2. A Service with no endpoints because of a label/selector mismatch
3. A Pod that is Running but never Ready because of a wrong readiness-probe path

## 16. Tear down (cost control)

```bash
./scripts/teardown.sh
```

Kubernetes creates AWS resources that Terraform doesn't know about: the NLB from the Traefik
Service and the EBS volume behind the Postgres PVC. The script deletes those first (Argo CD app →
namespace → Traefik → wait for the load balancer to disappear), then runs `terraform destroy`.
Destroying the VPC while the NLB still exists fails on dependent network interfaces.

Approximate running cost in ap-south-1: EKS control plane $0.10/h + 2 × t3.large ≈ $0.18/h +
NAT gateway ≈ $0.06/h + NLB ≈ $0.03/h, so **about $0.37 per hour**.

## Evidence (captured from the live EKS deployment)

Raw command output is in [`docs/evidence/`](docs/evidence/); images are in [`docs/screenshots/`](docs/screenshots/).

| What | Screenshot |
|------|-----------|
| App on EKS through the Ingress / AWS NLB (build SHA + `eks-dev` in the sidebar) | ![app](docs/screenshots/app-dashboard.png) |
| Appointments view · booking modal · mobile layout | [appointments](docs/screenshots/app-appointments.png) · [modal](docs/screenshots/app-booking-modal.png) · [mobile](docs/screenshots/app-mobile.png) |
| `pytest -v`: 23 passed, 97% coverage (M2) | ![pytest](docs/screenshots/pytest.png) |
| `docker compose up --build` + non-root `id` (M4) | [terminal](docs/screenshots/docker-compose.png) · [browser at localhost:3000](docs/screenshots/compose-localhost-3000.png) |
| GitHub Actions run, all jobs green (M5) | ![actions](docs/screenshots/github-actions-run.png) |
| GHCR package with commit-SHA tags only (M5) | [ghcr](docs/screenshots/ghcr-backend-package.png) |
| Trivy gate output from the pipeline (M6) | [trivy](docs/screenshots/trivy-ci.png) |
| `terraform plan` (60 to add) and `apply` (M7) | [plan](docs/screenshots/terraform-plan-summary.png) · [apply](docs/screenshots/terraform-apply-summary.png) |
| AWS Console (ap-south-1): `medislot-dev-vpc` with 4 subnets, EKS `medislot-dev-eks` Active on 1.36 (M7) | [VPC list](docs/screenshots/aws-vpc-list.png) · ![vpc](docs/screenshots/aws-vpc-details.png) · ![eks](docs/screenshots/aws-eks-cluster.png) |
| `kubectl get pods/svc/ingress/hpa`, `helm list`, Argo CD app (M8) | ![k8s](docs/screenshots/k8s-status.png) |
| `curl` of the backend `/metrics` (M9) | [metrics](docs/screenshots/metrics.png) |
| Prometheus targets: `serviceMonitor/medislot/medislot-backend` 2/2 UP (M9) | ![targets](docs/screenshots/prometheus-targets.png) |
| Grafana *MediSlot · Service Overview* with live traffic and HPA scaling (M9) | ![grafana](docs/screenshots/grafana-dashboard.png) |
| Argo CD: Synced + Healthy on the CI release commit | ![argocd](docs/screenshots/argocd-app.png) |
| Commit history | [commits](docs/screenshots/github-commits.png) |

## 17. Rubric map

| Module | Requirement | Where |
|--------|-------------|-------|
| M1 | `/health`, ≥ 4 REST endpoints (GET/POST/PUT/DELETE) | `backend/app/routers/` |
| M1 | PostgreSQL + Alembic migration | `backend/alembic/versions/` |
| M1 | Frontend calling the API, responsive UI | `frontend/src/` |
| M2 | pytest, ≥ 5 tests over ≥ 3 endpoints, test DB, config | `backend/tests/` (23 tests), `backend/pytest.ini`, `tests/conftest.py` |
| M3 | `.gitignore` (`.env`, `__pycache__`, `node_modules`, `.venv`), meaningful commits | `.gitignore`, `git log` |
| M4 | Backend Dockerfile, multi-stage frontend, non-root, compose | `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml` |
| M5 | Workflow on push to main, pytest gate, frontend build, both images, GHCR, SHA tags | `.github/workflows/ci-cd.yml` |
| M6 | Trivy on both images, fails on HIGH/CRITICAL, explanation | `build-scan-push` job, [§9](#9-devsecops-trivy) |
| M7 | VPC with 2 public subnets, EKS + node group, tfvars example | `terraform/` |
| M8 | Namespace, Helm chart, ≥ 2 replicas, ClusterIP, Ingress `/` + `/api` | `k8s/namespace.yaml`, `helm/medislot/` |
| M9 | `/metrics`, Prometheus scraping, Grafana dashboard | `backend/app/main.py`, `monitoring/`, chart ServiceMonitor + dashboard |
| M10 | README, presentation video + slides | this file, [`demo/MediSlot-Capstone-Demo.mp4`](demo/MediSlot-Capstone-Demo.mp4) (10 min, narrated), [`demo/MediSlot-Capstone.pdf`](demo/MediSlot-Capstone.pdf) / `.pptx` |

## 18. Design decisions

- **Pull-based GitOps instead of `kubectl` from CI.** CI needs no AWS or cluster credentials, Git
  is the audit log of every release, and drift is self-healed.
- **Migrations in an initContainer with an advisory lock.** Schema changes land before the new
  code serves traffic, and parallel replicas can't run the same migration twice.
- **Separate liveness and readiness.** A database outage makes Pods *unready*, so they're taken out
  of rotation, but it doesn't make Kubernetes restart healthy processes in a loop.
- **PostgreSQL in-cluster (StatefulSet + EBS).** Keeps the capstone self-contained and cheap. For
  production, Amazon RDS (Multi-AZ, automated backups, point-in-time recovery) is the better
  trade-off; only `DATABASE_URL` would change.
- **Single NAT gateway and local Terraform state.** These are cost and simplicity choices for one
  operator. A team setup would use one NAT per AZ and an S3 backend with state locking.
