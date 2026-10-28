# Digital Loan Processing Platform (Sample)

A learning/demo repository for a cloud-native personal-loan workflow. It is intentionally a **non-production sample**:
- Python/FastAPI microservices: frontend API, loan, customer, document, notification
- PostgreSQL for demo persistence (compose locally; Kubernetes manifest is a demo starter)
- Dockerfiles and local Docker Compose
- Kubernetes manifests and Istio 90/10 canary example
- Harness CI pipeline starter and Argo CD Application example
- Dynatrace setup checklist

## Architecture

`frontend -> loan-service -> customer-service + document-service + notification-service -> PostgreSQL`

This sample uses simulated eligibility rules and notification logging. It does not implement real banking, credit-bureau, KYC, authentication, encryption/key management, or regulatory controls. Never use real customer data or credentials.

## Repository layout

```text
services/
  frontend/              Customer portal API
  loan-service/          Loan application and demo eligibility logic
  customer-service/       Customer profile API
  document-service/      Document metadata API (does not store file bytes)
  notification-service/  Logs demo notification requests
deploy/k8s/               Kubernetes Deployments, Services, PostgreSQL
deploy/istio/             Gateway/VirtualService/DestinationRule canary sample
deploy/argocd/             Argo CD Application
harness/                   Harness pipeline starter notes/YAML
```

## 1. Run locally with Docker Compose

Prerequisites: Docker Desktop or Docker Engine + Compose.

```bash
docker compose up --build
```

Check endpoints:
```bash
curl http://localhost:8080/health
curl http://localhost:8081/health
curl http://localhost:8082/health
curl http://localhost:8083/health
curl http://localhost:8084/health
```

Submit a demo loan:
```bash
curl -X POST http://localhost:8081/loans \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":"C1001","amount":50000,"annual_income":900000,"employment_type":"salaried","document_ids":["DOC-1"]}'
```

List applications:
```bash
curl http://localhost:8081/loans
```

Eligibility is a simplified educational rule only. A result is `eligible_for_review`, `rejected_demo_rule`, or `pending_documents`; it is not a real credit decision.

## 2. GCP/GKE deployment plan

Set your values first:
```bash
export PROJECT_ID="YOUR_GCP_PROJECT_ID"
export REGION="us-central1"
export CLUSTER_NAME="loan-platform-gke"
export REPOSITORY="loan-platform"
gcloud config set project "$PROJECT_ID"
gcloud services enable container.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com
```

Create an Artifact Registry Docker repository:
```bash
gcloud artifacts repositories create "$REPOSITORY" \
  --repository-format=docker --location="$REGION" \
  --description="Personal loan demo images"
```

Create or use a GKE cluster. For a learning lab, use a small Standard cluster or Autopilot, after reviewing estimated costs:
```bash
gcloud container clusters create-auto "$CLUSTER_NAME" --region "$REGION"
gcloud container clusters get-credentials "$CLUSTER_NAME" --region "$REGION"
kubectl get nodes
```
If you already have a GKE cluster, use it rather than creating another.

## 3. Build and push images

From the repository root, authenticate Docker:
```bash
gcloud auth configure-docker "${REGION}-docker.pkg.dev"
```

Example for the loan service:
```bash
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/loan-service:1.0.0"
docker build -t "$IMAGE" services/loan-service
docker push "$IMAGE"
```
Repeat for `frontend`, `customer-service`, `document-service`, and `notification-service`.

## 4. Deploy to Kubernetes

Before applying manifests, replace `PROJECT_ID` and `REGION` placeholders in the workload image references with your actual values. The manifests are examples and should be reviewed before use.

```bash
kubectl create namespace loan-platform
kubectl apply -n loan-platform -f deploy/k8s/postgres.yaml
kubectl apply -n loan-platform -f deploy/k8s/services.yaml
kubectl apply -n loan-platform -f deploy/k8s/deployments.yaml
kubectl get pods -n loan-platform
kubectl get svc -n loan-platform
```

For a real environment, do not use a containerized in-cluster PostgreSQL instance as a durable database without a proper storage, backup, HA, upgrade, access-control, and recovery design. Prefer a managed database such as Cloud SQL for PostgreSQL with private connectivity and Secret Manager integration.

## 5. Harness CI

Create a Harness CI pipeline connected to this source repository. Suggested stages:
1. Clone Codebase
2. Run `python -m compileall services`
3. Run unit tests (`pytest`)
4. Run a vulnerability/dependency scan (for example, your organization's approved scanner)
5. Build and push each image to GAR with an immutable tag such as the Git commit SHA
6. Update the separate GitOps repository with the new image tag and commit/push the manifest change

The YAML in `harness/pipeline-starter.yaml` is a **starter sketch**, not guaranteed to import unchanged into every Harness account. Harness step types and connector identifiers vary by account; configure connectors and step types in Pipeline Studio.

Use a GAR service account with least-privilege `Artifact Registry Writer` scoped to the target repository. Store credentials in Harness secrets/connectors; never hard-code keys in Git.

## 6. GitOps with Argo CD

Recommended: create a separate `loan-platform-gitops` repository and copy `deploy/k8s` and `deploy/istio` into it. Update image tags there. Install Argo CD into the cluster, then update `deploy/argocd/application.yaml` with your GitOps repository URL and path.

Argo CD can automatically sync desired state from Git. For production, enable pruning and self-heal only after reviewing deletion impact and access controls. The sample is illustrative.

## 7. Istio

Install Istio using the supported installation method/version for your cluster and inject sidecars into the application namespace. Then apply the DestinationRule and VirtualService examples from `deploy/istio/`.

The canary example expects two versions of `loan-service` to be deployed and labelled `version: v1` and `version: v2`. The VirtualService routes 90% to v1 and 10% to v2. Validate using repeated test requests and telemetry; traffic weights are probabilistic, not an exact count for a small number of requests.

mTLS policy should be tested against all callers before enforcing STRICT mode. Avoid applying a broad STRICT policy before all workloads are correctly enrolled in the mesh.

## 8. Dynatrace

1. In Dynatrace, create/identify your environment and an access token with the minimum required Kubernetes Operator permissions.
2. Follow the current Dynatrace Kubernetes deployment guide for your GKE mode and Kubernetes version.
3. Install the Dynatrace Operator and create the appropriate DynaKube resource using the exact API URL and secret name for your environment.
4. Verify cluster, namespace, pod, and service visibility.
5. Ensure application tracing is supported for the selected instrumentation mode/runtime. Add OpenTelemetry instrumentation if required by your chosen setup.
6. Create a dashboard for request count, p95 latency, error rate, CPU/memory, pod restarts, and loan endpoint latency.
7. Configure alerts such as 5xx rate > 5% for 5 minutes or p95 latency > 3 seconds for 5 minutes. Tune thresholds to baseline and route notifications to your approved channel.

See the official Dynatrace Kubernetes documentation before installing: https://docs.dynatrace.com/docs/ingest-from/setup-on-k8s/deployment/application-observability

## 9. Canary validation and rollback

1. Deploy v1 and confirm health.
2. Deploy v2 with a changed demo eligibility response and `version: v2`.
3. Apply the Istio 90/10 route.
4. Send repeated synthetic requests and inspect error rate, latency, and traces in Dynatrace.
5. If unhealthy, change the VirtualService to 100% v1 and commit the change to GitOps. Argo CD will reconcile it.
6. Keep the previous image tag and manifest commit available for a controlled rollback.

For GitOps-managed resources, prefer reverting the Git commit/image tag rather than manually changing the live Deployment, because Argo CD may reconcile manual changes back to Git.

## Security and production gaps

This is a demo scaffold, not a deployable banking product. Before any real use, add authentication/authorization, API gateway/rate limits, input validation, idempotency, audit trail, secrets management, encrypted document storage, malware scanning, retention controls, database migrations/backups, policy-approved credit decisioning, PII redaction, network policies, image signing/SBOM, vulnerability gates, and compliance review.
