# GCP free-tier deployment of the DACH Jobs pipeline.
#
# What this provisions:
#   - GCS bucket for the lake (replaces MinIO in cloud)
#   - BigQuery dataset for the warehouse (replaces local DuckDB)
#   - Cloud Run service for the FastAPI read API
#   - Artifact Registry repo for the API image
#   - Pub/Sub topic for the ingestion stream (replaces Redpanda)
#   - Service account with the minimum IAM the pipeline actually uses
#
# Everything sits inside the always-free quotas (5GB GCS Standard,
# 10GB BigQuery storage + 1TB queries/mo, 2M Cloud Run requests/mo,
# 10GB Pub/Sub/mo). Demo cost: typically $0/mo, max single-digit cents.

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ------------------------------------------------------------------ buckets
resource "google_storage_bucket" "lake" {
  name                        = "${var.project_id}-dach-lake"
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  force_destroy               = true

  lifecycle_rule {
    action { type = "Delete" }
    condition { age = 90 }   # bronze retention: 90d
  }
}

# ------------------------------------------------------------- warehouse
resource "google_bigquery_dataset" "warehouse" {
  dataset_id                 = "dach_jobs"
  location                   = var.region
  delete_contents_on_destroy = true
}

# ------------------------------------------------------------------- pubsub
resource "google_pubsub_topic" "jobs_raw" {
  name = "jobs-raw"
}

# ------------------------------------------------------------------- api
resource "google_artifact_registry_repository" "api" {
  location      = var.region
  repository_id = "dach-jobs-api"
  format        = "DOCKER"
}

resource "google_service_account" "api" {
  account_id   = "dach-jobs-api"
  display_name = "DACH Jobs FastAPI service account"
}

resource "google_project_iam_member" "api_bq_reader" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_project_iam_member" "api_bq_jobuser" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_cloud_run_v2_service" "api" {
  name     = "dach-jobs-api"
  location = var.region

  template {
    service_account = google_service_account.api.email
    scaling { max_instance_count = 2 }
    containers {
      image = var.api_image
      ports { container_port = 8000 }
      resources {
        limits = { memory = "512Mi", cpu = "1" }
      }
      env {
        name  = "BQ_DATASET"
        value = google_bigquery_dataset.warehouse.dataset_id
      }
    }
  }

  deletion_protection = false
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  count    = var.api_public ? 1 : 0
  project  = var.project_id
  location = google_cloud_run_v2_service.api.location
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
