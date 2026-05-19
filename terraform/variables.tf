variable "project_id" {
  description = "GCP project id."
  type        = string
}

variable "region" {
  description = "Default region for all regional resources."
  type        = string
  default     = "europe-west3"   # Frankfurt — closest free-tier region to DACH
}

variable "api_image" {
  description = "Fully-qualified image for the Cloud Run API."
  type        = string
  default     = "europe-west3-docker.pkg.dev/REPLACE/dach-jobs-api/api:latest"
}

variable "api_public" {
  description = "Allow unauthenticated invocation of the Cloud Run API."
  type        = bool
  default     = true
}
