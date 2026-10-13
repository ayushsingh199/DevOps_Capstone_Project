# Presentation video script (≈15 minutes)

Talking points to read in your own words while recording. Pair it with [`RUNBOOK.md`](RUNBOOK.md),
which has every command. Record with QuickTime (File → New Screen Recording, choose your
microphone) and export as MP4 to `demo/MediSlot-Capstone-Demo.mp4`.

---

## Part 1: Slides

**Slide 1, title.**
"Hi, I'm Ayush Singh. My capstone is MediSlot, a clinic appointment platform, and in this video I'll
show how it goes from my laptop to a monitored, autoscaled Kubernetes deployment on AWS, delivered
through a GitOps pipeline."

**Slide 2, the application.**
"Front-desk staff book patients with doctors, check them in and close the visit. The dashboard shows
today's load. The important business rule is that a doctor can never be double-booked: the API
returns 409 Conflict for an overlapping slot."

**Slide 3, architecture.**
"Two flows. The *request* flow: the browser hits an AWS Network Load Balancer, then the Traefik
ingress controller, which routes `/api` to FastAPI and everything else to the React frontend, with
PostgreSQL behind the API. The *delivery* flow: a push to main runs GitHub Actions, which tests,
builds, scans and pushes images, then commits the new image tag to Git. Argo CD inside the cluster
sees that commit and deploys it. CI never gets cluster credentials. That's pull-based GitOps."

**Slide 4, stack.** Read the table quickly; mention Terraform, Helm, Argo CD and Prometheus/Grafana.

**Slides 5–6, app and tests.**
"Four resource groups of REST endpoints plus health, readiness and metrics. Two tables managed by
Alembic migrations, which run in an init container under a Postgres advisory lock so two replicas
can't migrate at the same time. 23 pytest tests at 97% coverage, each on its own in-memory SQLite
database, so tests never touch the real database."

**Slide 7, Docker.**
"Both images are multi-stage and run as non-root: UID 10001 for the API, UID 101 for Nginx. The
frontend image doesn't contain Node at all, only the built static files."

**Slide 8, CI/CD.**
"Every image is tagged with the full Git commit SHA, never `latest`, so any pod can be traced back
to the exact commit. All third-party actions are pinned to commit SHAs, because a tag can be
re-pointed by an attacker. That actually happened to a popular security action earlier this year."

**Slide 9, DevSecOps.**
"Trivy scans both images. The gate fails the pipeline on any HIGH or CRITICAL vulnerability that has
a fix available. Both images pass. The backend still has HIGH CVEs with no fix yet, for example
CVE-2026-76642 in Debian's util-linux packages. Blocking on those would block every release with
nothing we can do, so we track them in GitHub's Security tab instead. The API never runs those
utilities, and runs non-root with a read-only filesystem and no Linux capabilities."

**Slide 10, Terraform.**
"Terraform builds a VPC with two public and two private subnets across two availability zones, a NAT
gateway, and an EKS cluster with a managed node group in the private subnets. No AWS keys are in
the repo; Terraform reads them from my local AWS CLI profile."

**Slides 11–13, Kubernetes, GitOps and observability.**
"The Helm chart runs two replicas of each tier behind ClusterIP services, an Ingress with the two
routes, an autoscaler for the backend, disruption budgets, and a network policy so only the backend
can reach Postgres. The namespace enforces the restricted Pod Security standard. Prometheus scrapes
the API through a ServiceMonitor, and Grafana loads my dashboard automatically."

**Slide 14, challenges.**
Pick two or three from the slide, for example: "My first AWS account was inside an organization whose
service control policy denied EC2 and EKS, so no IAM permission could fix it. I moved to a
standalone account, where the 5-vCPU quota made me resize the node group to two t3.large nodes."

## Part 2: Live walkthrough

Follow [`RUNBOOK.md`](RUNBOOK.md) sections 2–8. Things worth saying out loud:

- **Codebase:** "Routers only handle HTTP; business rules such as double-booking live in `services/`."
- **CI/CD:** while the pipeline runs: "The test job also runs migrations against a real Postgres
  container; the image job won't push anything that fails Trivy."
- **Terraform:** `terraform plan` showing *No changes*: "The real infrastructure matches the code. There's no drift."
- **Argo CD:** "This is the commit CI just made. Argo CD synced it, and the rolling update kept
  `maxUnavailable` at zero, so no downtime."
- **Kubernetes:** point at the 2/2 READY backend and frontend pods and the two Ingress paths.
- **Browser:** "The build SHA in the sidebar is now the commit I pushed a few minutes ago."
- **Prometheus:** "Both backend pods are UP; Prometheus scrapes them every 15 seconds."
- **Grafana:** book an appointment and show the counter increase.

## Closing (20 seconds)

"To recap: tests, image scanning, SHA-tagged images, infrastructure as code, GitOps delivery,
autoscaling and monitoring, all automated from a single git push. After recording I tear everything
down with the teardown script so nothing keeps billing. Thank you."
