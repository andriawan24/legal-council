# =============================================================================
# Legal Council - Deployment Makefile
# =============================================================================

# Project Configuration (override with environment variables or .env)
PROJECT_ID ?= your-gcp-project
REGION ?= us-central1
PDF_BUCKET ?= your-pdf-bucket
DATABASE_URL ?= postgresql://user:pass@localhost:5432/legal_council

# Cloud SQL Configuration (for Cloud Functions)
CLOUDSQL_INSTANCE ?= $(PROJECT_ID):$(REGION):legal-council-db

# =============================================================================
# Extraction Job Deployment
# =============================================================================

.PHONY: deploy-extraction
deploy-extraction: ## Deploy extraction job as Cloud Function (triggered by GCS upload)
	@echo "Deploying extraction-job to Cloud Functions (2nd gen)..."
	cd extraction-job && gcloud functions deploy extraction-job \
		--gen2 \
		--runtime=python312 \
		--region=$(REGION) \
		--source=. \
		--entry-point=process_pdf_event \
		--trigger-bucket=$(PDF_BUCKET) \
		--memory=2Gi \
		--timeout=540s \
		--set-env-vars="GCP_PROJECT=$(PROJECT_ID),GCP_REGION=$(REGION),DATABASE_URL=$(DATABASE_URL)" \
		--set-env-vars="ENABLE_EMBEDDINGS=true,ENABLE_DATABASE_STORAGE=true"
	@echo "Done! Function will trigger on PDF uploads to gs://$(PDF_BUCKET)"

.PHONY: deploy-extraction-http
deploy-extraction-http: ## Deploy extraction job with HTTP trigger (for manual testing)
	@echo "Deploying extraction-job with HTTP trigger..."
	cd extraction-job && gcloud functions deploy extraction-job-http \
		--gen2 \
		--runtime=python312 \
		--region=$(REGION) \
		--source=. \
		--entry-point=process_pdf_http \
		--trigger-http \
		--allow-unauthenticated \
		--memory=2Gi \
		--timeout=540s \
		--set-env-vars="GCP_PROJECT=$(PROJECT_ID),GCP_REGION=$(REGION),DATABASE_URL=$(DATABASE_URL)" \
		--set-env-vars="ENABLE_EMBEDDINGS=true,ENABLE_DATABASE_STORAGE=true"
	@echo "Done! Use HTTP POST to trigger extraction manually"

# =============================================================================
# Database Setup
# =============================================================================

.PHONY: db-schema
db-schema: ## Apply database schema to Cloud SQL
	@echo "Applying schema to database..."
	psql "$(DATABASE_URL)" -f extraction-job/schema.sql
	@echo "Schema applied successfully"

.PHONY: db-connect
db-connect: ## Connect to database via psql
	psql "$(DATABASE_URL)"

# =============================================================================
# Local Development
# =============================================================================

.PHONY: extraction-dev
extraction-dev: ## Run extraction job locally for development
	cd extraction-job && uv run functions-framework --target=process_pdf_http --port=8080 --debug

.PHONY: extraction-lock
extraction-lock: ## Regenerate uv.lock for extraction job
	cd extraction-job && uv lock

.PHONY: extraction-sync
extraction-sync: ## Install extraction job dependencies locally
	cd extraction-job && uv sync

# =============================================================================
# GCS Bucket Setup
# =============================================================================

.PHONY: create-bucket
create-bucket: ## Create GCS bucket for PDF uploads
	gsutil mb -p $(PROJECT_ID) -l $(REGION) gs://$(PDF_BUCKET)
	@echo "Created bucket: gs://$(PDF_BUCKET)"

.PHONY: upload-pdf
upload-pdf: ## Upload a test PDF (usage: make upload-pdf FILE=path/to/file.pdf)
	@if [ -z "$(FILE)" ]; then echo "Usage: make upload-pdf FILE=path/to/file.pdf"; exit 1; fi
	gsutil cp $(FILE) gs://$(PDF_BUCKET)/
	@echo "Uploaded $(FILE) to gs://$(PDF_BUCKET)/"

# =============================================================================
# Logs & Monitoring
# =============================================================================

.PHONY: logs-extraction
logs-extraction: ## View extraction job logs
	gcloud functions logs read extraction-job --region=$(REGION) --gen2 --limit=50

.PHONY: logs-tail
logs-tail: ## Tail extraction job logs in real-time
	gcloud beta run services logs tail extraction-job --region=$(REGION)

# =============================================================================
# Cleanup
# =============================================================================

.PHONY: delete-extraction
delete-extraction: ## Delete extraction job Cloud Function
	gcloud functions delete extraction-job --region=$(REGION) --gen2 --quiet

# =============================================================================
# Help
# =============================================================================

.PHONY: help
help: ## Show this help message
	@echo "Legal Council - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Configuration (set via environment or override):"
	@echo "  PROJECT_ID     = $(PROJECT_ID)"
	@echo "  REGION         = $(REGION)"
	@echo "  PDF_BUCKET     = $(PDF_BUCKET)"

.DEFAULT_GOAL := help
