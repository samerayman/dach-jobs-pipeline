# Cloud deployment (GCP free tier)

Mirror of the local stack, sized to fit the always-free quotas.

| Local         | Cloud                 |
| ------------- | --------------------- |
| MinIO         | GCS (Standard, 5GB)   |
| Redpanda      | Pub/Sub (10GB/mo)     |
| DuckDB        | BigQuery (10GB)       |
| FastAPI local | Cloud Run             |
| Streamlit     | Cloud Run (or local)  |

## One-time

```bash
gcloud auth application-default login
gcloud config set project <YOUR_PROJECT>

terraform init
terraform plan  -var "project_id=<YOUR_PROJECT>"
terraform apply -var "project_id=<YOUR_PROJECT>"
```

## Cost note

Region is `europe-west3` (Frankfurt) — closest to DACH for latency, and inside
the GCP free-tier eligible set for these services. With the demo dataset
(~50k postings) the entire stack runs $0/mo. The 90-day lifecycle rule on the
lake bucket keeps GCS comfortably under 5GB.

## Teardown

```bash
terraform destroy -var "project_id=<YOUR_PROJECT>"
```
