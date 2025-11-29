# =============================================================================
# Legal Council - Deployment Makefile
# =============================================================================

# Project Configuration (override with environment variables or .env)
PROJECT_ID ?= cloud-run-marathon-479703
REGION ?= asia-southeast2
PDF_BUCKET ?= legal-council
DATABASE_URL ?= postgresql://user:pass@localhost:5432/legal_council

# Cloud SQL Configuration (for Cloud Functions)
CLOUDSQL_INSTANCE ?= $(PROJECT_ID):$(REGION):legal-council-db

# Service Names
API_SERVICE ?= legal-council-api
FRONTEND_SERVICE ?= legal-council-fe

# Container Registry
REGISTRY ?= $(REGION)-docker.pkg.dev/$(PROJECT_ID)/legal-council

# API Configuration
API_PORT ?= 8080
API_MEMORY ?= 1Gi
API_CPU ?= 1
API_MIN_INSTANCES ?= 0
API_MAX_INSTANCES ?= 10

# API Environment Defaults
API_TITLE ?= legal-council-api
API_VERSION ?= 1.0.0
DEBUG ?= false
DATABASE_POOL_MIN_SIZE ?= 1
DATABASE_POOL_MAX_SIZE ?= 10
DATABASE_COMMAND_TIMEOUT ?= 60
VERTEX_AI_MODEL ?= gemini-2.5-flash
VERTEX_AI_EMBEDDING_MODEL ?= gemini-embedding-001
EMBEDDING_DIMENSION ?= 768
RATE_LIMIT_REQUESTS ?= 100
RATE_LIMIT_WINDOW_SECONDS ?= 60
SESSION_MAX_MESSAGES ?= 100
SESSION_TIMEOUT_HOURS ?= 24
VECTOR_SEARCH_LIMIT ?= 10
VECTOR_SEARCH_MIN_SIMILARITY ?= 0.5

# Frontend Configuration
FRONTEND_PORT ?= 3000
FRONTEND_MEMORY ?= 512Mi
FRONTEND_CPU ?= 1
FRONTEND_MIN_INSTANCES ?= 0
FRONTEND_MAX_INSTANCES ?= 10

# =============================================================================
# Extraction Job Deployment
# =============================================================================

.PHONY: extraction-build
extraction-build: ## Build extraction job Docker image on GCP (Cloud Build)
	@echo "Building extraction job Docker image on GCP..."
	gcloud builds submit ./extraction-job --tag $(REGISTRY)/extraction-job:latest --project $(PROJECT_ID)
	@echo "Done! Image built and pushed to: $(REGISTRY)/extraction-job:latest"

.PHONY: extraction-push
extraction-push: extraction-build ## Build and push extraction job image to Artifact Registry (Alias for extraction-build)

.PHONY: deploy-extraction
deploy-extraction: ## Deploy extraction job as Cloud Function (triggered by GCS upload)
	@echo "Deploying extraction-job to Cloud Functions (2nd gen)..."
	cd extraction-job && gcloud functions deploy extraction-job \
		--gen2 \
		--runtime=python314 \
		--region=$(REGION) \
		--source=. \
		--entry-point=process_pdf_event \
		--trigger-bucket=$(PDF_BUCKET) \
		--cpu 4 \
		--memory=4Gi \
		--timeout=540s \
		--set-env-vars="GCP_PROJECT=$(PROJECT_ID),GCP_REGION=$(REGION),DATABASE_URL=$(DATABASE_URL)" \
		--set-env-vars="ENABLE_EMBEDDINGS=true,ENABLE_DATABASE_STORAGE=true"
	@echo "Done! Function will trigger on PDF uploads to gs://$(PDF_BUCKET)"

.PHONY: deploy-extraction-container
deploy-extraction-container: ## Deploy extraction job using the pre-built container image (requires extraction-push)
	@echo "Deploying extraction-job container to Cloud Run..."
	gcloud run deploy extraction-job \
		--image $(REGISTRY)/extraction-job:latest \
		--region $(REGION) \
		--memory 2Gi \
		--timeout 540s \
		--set-env-vars="GCP_PROJECT=$(PROJECT_ID),GCP_REGION=$(REGION),DATABASE_URL=$(DATABASE_URL)" \
		--set-env-vars="ENABLE_EMBEDDINGS=true,ENABLE_DATABASE_STORAGE=true" \
		--no-allow-unauthenticated
	@echo "------------------------------------------------------------------------"
	@echo "NOTE: Service deployed, but to match 'deploy-extraction' functionality,"
	@echo "you need to create an Eventarc trigger for GCS bucket events:"
	@echo ""
	@echo "  gcloud eventarc triggers create extraction-job-gcs-trigger \\"
	@echo "    --location=$(REGION) \\"
	@echo "    --destination-run-service=extraction-job \\"
	@echo "    --destination-run-region=$(REGION) \\"
	@echo "    --event-filters=\"type=google.cloud.storage.object.v1.finalized\" \\"
	@echo "    --event-filters=\"bucket=$(PDF_BUCKET)\" \\"
	@echo "    --service-account=$$(gcloud projects describe $(PROJECT_ID) --format='value(projectNumber)')-compute@developer.gserviceaccount.com"
	@echo "------------------------------------------------------------------------"

.PHONY: deploy-extraction-http
deploy-extraction-http: ## Deploy extraction job with HTTP trigger (for manual testing)
	@echo "Deploying extraction-job with HTTP trigger..."
	cd extraction-job && gcloud functions deploy extraction-job-http \
		--gen2 \
		--runtime=python314 \
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
# API Deployment (Cloud Run)
# =============================================================================

.PHONY: api-build
api-build: ## Build API Docker image locally
	@echo "Building API Docker image..."
	docker build -t $(API_SERVICE):latest ./api
	@echo "Done! Image: $(API_SERVICE):latest"

.PHONY: api-push
api-push: ## Build and push API image to Artifact Registry
	@echo "Building and pushing API image to $(REGISTRY)/$(API_SERVICE)..."
	docker build --platform linux/amd64 -t $(REGISTRY)/$(API_SERVICE):latest ./api
	docker push $(REGISTRY)/$(API_SERVICE):latest
	@echo "Done! Image pushed to $(REGISTRY)/$(API_SERVICE):latest"

.PHONY: deploy-api
deploy-api: ## Deploy API to Cloud Run from source
	@echo "Deploying API to Cloud Run from source..."
	cd api && gcloud run deploy $(API_SERVICE) \
		--source . \
		--region=$(REGION) \
		--memory=$(API_MEMORY) \
		--cpu=$(API_CPU) \
		--port=8080 \
		--min-instances=$(API_MIN_INSTANCES) \
		--max-instances=$(API_MAX_INSTANCES) \
		--set-env-vars="API_TITLE=$(API_TITLE)" \
		--set-env-vars="API_VERSION=$(API_VERSION)" \
		--set-env-vars="DEBUG=$(DEBUG)" \
		--set-env-vars="DATABASE_URL=$(DATABASE_URL)" \
		--set-env-vars="DATABASE_POOL_MIN_SIZE=$(DATABASE_POOL_MIN_SIZE)" \
		--set-env-vars="DATABASE_POOL_MAX_SIZE=$(DATABASE_POOL_MAX_SIZE)" \
		--set-env-vars="DATABASE_COMMAND_TIMEOUT=$(DATABASE_COMMAND_TIMEOUT)" \
		--set-env-vars="GCP_PROJECT=$(PROJECT_ID)" \
		--set-env-vars="GCP_REGION=$(REGION)" \
		--set-env-vars="VERTEX_AI_MODEL=$(VERTEX_AI_MODEL)" \
		--set-env-vars="VERTEX_AI_EMBEDDING_MODEL=$(VERTEX_AI_EMBEDDING_MODEL)" \
		--set-env-vars="EMBEDDING_DIMENSION=$(EMBEDDING_DIMENSION)" \
		--set-env-vars="RATE_LIMIT_REQUESTS=$(RATE_LIMIT_REQUESTS)" \
		--set-env-vars="RATE_LIMIT_WINDOW_SECONDS=$(RATE_LIMIT_WINDOW_SECONDS)" \
		--set-env-vars="SESSION_MAX_MESSAGES=$(SESSION_MAX_MESSAGES)" \
		--set-env-vars="SESSION_TIMEOUT_HOURS=$(SESSION_TIMEOUT_HOURS)" \
		--set-env-vars="VECTOR_SEARCH_LIMIT=$(VECTOR_SEARCH_LIMIT)" \
		--set-env-vars="VECTOR_SEARCH_MIN_SIMILARITY=$(VECTOR_SEARCH_MIN_SIMILARITY)" \
		--allow-unauthenticated
	@echo "Done! API deployed to Cloud Run"

.PHONY: deploy-api-full
deploy-api-full: api-push deploy-api ## Build, push, and deploy API to Cloud Run

# =============================================================================
# Frontend Deployment (Cloud Run)
# =============================================================================

.PHONY: frontend-build
frontend-build: ## Build Frontend Docker image locally
	@echo "Building Frontend Docker image..."
	docker build -t $(FRONTEND_SERVICE):latest ./legal-council-fe
	@echo "Done! Image: $(FRONTEND_SERVICE):latest"

.PHONY: frontend-push
frontend-push: ## Build and push Frontend image to Artifact Registry
	@echo "Building and pushing Frontend image to $(REGISTRY)/$(FRONTEND_SERVICE)..."
	docker build --platform linux/amd64 -t $(REGISTRY)/$(FRONTEND_SERVICE):latest ./legal-council-fe
	docker push $(REGISTRY)/$(FRONTEND_SERVICE):latest
	@echo "Done! Image pushed to $(REGISTRY)/$(FRONTEND_SERVICE):latest"

.PHONY: deploy-frontend
deploy-frontend: ## Deploy Frontend to Cloud Run
	@echo "Deploying Frontend to Cloud Run..."
	gcloud run deploy $(FRONTEND_SERVICE) \
		--image=$(REGISTRY)/$(FRONTEND_SERVICE):latest \
		--region=$(REGION) \
		--platform=managed \
		--port=$(FRONTEND_PORT) \
		--memory=$(FRONTEND_MEMORY) \
		--cpu=$(FRONTEND_CPU) \
		--min-instances=$(FRONTEND_MIN_INSTANCES) \
		--max-instances=$(FRONTEND_MAX_INSTANCES) \
		--allow-unauthenticated
	@echo "Done! Frontend deployed to Cloud Run"

.PHONY: deploy-frontend-full
deploy-frontend-full: frontend-push deploy-frontend ## Build, push, and deploy Frontend to Cloud Run

# =============================================================================
# Deploy All Services
# =============================================================================

.PHONY: deploy-all
deploy-all: deploy-api-full deploy-frontend-full ## Deploy both API and Frontend to Cloud Run
	@echo "All services deployed successfully!"

.PHONY: build-all
build-all: api-build frontend-build extraction-build ## Build all Docker images locally

# =============================================================================
# Local Development
# =============================================================================

.PHONY: api-dev
api-dev: ## Run API locally for development
	cd api && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8080

.PHONY: api-sync
api-sync: ## Install API dependencies locally
	cd api && uv sync

.PHONY: frontend-dev
frontend-dev: ## Run Frontend locally for development
	cd legal-council-fe && pnpm dev

.PHONY: frontend-install
frontend-install: ## Install Frontend dependencies locally
	cd legal-council-fe && pnpm install

.PHONY: dev
dev: ## Run both API and Frontend locally (requires tmux or run in separate terminals)
	@echo "Starting API and Frontend..."
	@echo "Run 'make api-dev' in one terminal and 'make frontend-dev' in another"

# =============================================================================
# Logs & Monitoring
# =============================================================================

.PHONY: logs-api
logs-api: ## View API logs from Cloud Run
	gcloud run services logs read $(API_SERVICE) --region=$(REGION) --limit=50

.PHONY: logs-api-tail
logs-api-tail: ## Tail API logs in real-time
	gcloud beta run services logs tail $(API_SERVICE) --region=$(REGION)

.PHONY: logs-frontend
logs-frontend: ## View Frontend logs from Cloud Run
	gcloud run services logs read $(FRONTEND_SERVICE) --region=$(REGION) --limit=50

.PHONY: logs-frontend-tail
logs-frontend-tail: ## Tail Frontend logs in real-time
	gcloud beta run services logs tail $(FRONTEND_SERVICE) --region=$(REGION)

# =============================================================================
# Cleanup
# =============================================================================

.PHONY: delete-extraction
delete-extraction: ## Delete extraction job Cloud Function
	gcloud functions delete extraction-job --region=$(REGION) --gen2 --quiet

.PHONY: delete-api
delete-api: ## Delete API Cloud Run service
	gcloud run services delete $(API_SERVICE) --region=$(REGION) --quiet

.PHONY: delete-frontend
delete-frontend: ## Delete Frontend Cloud Run service
	gcloud run services delete $(FRONTEND_SERVICE) --region=$(REGION) --quiet

.PHONY: delete-all
delete-all: delete-api delete-frontend delete-extraction ## Delete all deployed services

# =============================================================================
# Artifact Registry Setup
# =============================================================================

.PHONY: setup-registry
setup-registry: ## Create Artifact Registry repository for Docker images
	gcloud artifacts repositories create legal-council \
		--repository-format=docker \
		--location=$(REGION) \
		--description="Legal Council Docker images"
	@echo "Created Artifact Registry: $(REGISTRY)"

.PHONY: auth-registry
auth-registry: ## Configure Docker to authenticate with Artifact Registry
	gcloud auth configure-docker $(REGION)-docker.pkg.dev
	@echo "Docker configured for $(REGION)-docker.pkg.dev"

# =============================================================================
# Help
# =============================================================================

.PHONY: help
help: ## Show this help message
	@echo "Legal Council - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Configuration (set via environment or override):"
	@echo "  PROJECT_ID       = $(PROJECT_ID)"
	@echo "  REGION           = $(REGION)"
	@echo "  PDF_BUCKET       = $(PDF_BUCKET)"
	@echo "  API_SERVICE      = $(API_SERVICE)"
	@echo "  FRONTEND_SERVICE = $(FRONTEND_SERVICE)"
	@echo "  REGISTRY         = $(REGISTRY)"
	@echo ""
	@echo "Quick Start:"
	@echo "  1. Set PROJECT_ID:  export PROJECT_ID=your-gcp-project"
	@echo "  2. Setup registry:  make setup-registry && make auth-registry"
	@echo "  3. Deploy all:      make deploy-all"

.DEFAULT_GOAL := help
