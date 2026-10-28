# Harness setup checklist

1. Create a Harness project and connect the source GitHub repository.
2. Create a Google Cloud connector with the least-privilege identity needed for GAR. Prefer Workload Identity Federation or an approved short-lived credential method where supported; avoid long-lived service-account keys.
3. Ensure the identity has `Artifact Registry Writer` on the target repository.
4. Create a CI pipeline in Pipeline Studio:
   - Clone Codebase
   - Run compile and unit tests
   - Add your approved dependency/image scanner and fail on policy violations
   - Build and push each image to GAR with a commit-SHA tag
   - Update the separate GitOps repository and push the manifest change
5. Configure a Git event trigger after manual runs work.
6. Keep deployment ownership with Argo CD; do not add direct `kubectl apply` deployment steps for the same resources.

The YAML in `pipeline-starter.yaml` is only a scaffold. Harness schema and available step types differ across account/project configuration. Build the final pipeline in the UI and export the resulting YAML.
