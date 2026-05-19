output "lake_bucket" {
  value       = google_storage_bucket.lake.name
  description = "GCS bucket holding bronze/silver/gold parquet."
}

output "bq_dataset" {
  value       = google_bigquery_dataset.warehouse.dataset_id
  description = "BigQuery dataset for silver and gold."
}

output "api_url" {
  value       = google_cloud_run_v2_service.api.uri
  description = "Public URL of the read API."
}

output "pubsub_topic" {
  value       = google_pubsub_topic.jobs_raw.name
  description = "Pub/Sub topic the ingester publishes to in cloud mode."
}
