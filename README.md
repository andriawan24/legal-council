# Building an AI Legal Council: A Virtual Deliberation Room with Google Cloud and Vertex AI

Have you ever wondered how to build an AI system that simulates a complex decision-making process with multiple perspectives? In this guide, you'll learn how to build "Legal Council," a virtual deliberation room where three AI judges—Strict, Humanist, and Historian—debate legal cases to help achieve sentencing consistency.

**Tips**
*   **RAG (Retrieval-Augmented Generation)**: We use actual court verdicts to ground the AI's arguments.
*   **Multi-Agent Systems**: Learn how to orchestrate distinct AI personas.
*   **Serverless**: Deploy everything on Google Cloud Run for scalability.

## Introduction | Overview

**The Problem**: Inconsistency in judicial sentencing is a significant challenge. Two judges might give vastly different sentences for similar crimes based on their personal philosophies.

**The Solution**: This project provides an AI-powered deliberation system. It simulates a council of three AI judges, each with a distinct legal philosophy (Strict Constructionist, Rehabilitative Advocate, and Jurisprudence Historian). They debate cases in real-time, grounded in a database of Indonesian court verdicts, to provide a balanced legal opinion.

**Target Audience**: Developers interested in GenAI, Multi-Agent Systems, Legal Tech, and Google Cloud Platform.

**Outcome**: By the end of this guide, you will have deployed a full-stack application with:
*   A **Next.js** frontend for case input and deliberation.
*   A **FastAPI** backend orchestrating three AI agents.
*   A **PDF Ingestion Pipeline** using Cloud Functions and Vertex AI to process legal documents.
*   A **Vector Database** on Cloud SQL to find similar precedents.

## Design

The system is designed as a modular, event-driven architecture to handle both real-time user interactions and asynchronous document processing.

### High-Level Architecture

```mermaid
graph TD
    User[User] -->|Interacts| FE[Frontend Next.js]
    FE -->|REST/SSE| API[API Gateway FastAPI]
    
    subgraph "Backend Services (Cloud Run)"
        API -->|Orchestrates| Agent1[Strict Judge]
        API -->|Orchestrates| Agent2[Humanist Judge]
        API -->|Orchestrates| Agent3[Historian Judge]
    end

    subgraph "Data & AI Layer"
        Agent1 & Agent2 & Agent3 -->|Retrieved Context| VectorDB[Cloud SQL]
        Agent1 & Agent2 & Agent3 -->|Generate| VertexAI[Vertex AI - Gemini]
    end
    
    subgraph "Ingestion Pipeline"
        PDF[PDF Upload] -->|Trigger| GCS[Cloud Storage]
        GCS -->|Event| Ingestion[Extraction Job]
        Ingestion -->|Embed| VertexAI
        Ingestion -->|Store| VectorDB
    end
```

### Design Choices

1.  **Three-Agent System**: Instead of a single LLM response, we use three distinct personas to force a "debate." This mimics real judicial panels and reduces hallucination by requiring agents to critique each other.
2.  **Cloud Run**: We use Cloud Run for both the API and Frontend because it's serverless, scales to zero, and handles containerized applications easily.
3.  **Async Ingestion**: Processing legal PDFs is slow. We use GCS triggers and Cloud Functions to process files in the background without blocking the user interface.
4.  **Vertex AI**: We leverage Gemini models for high-quality reasoning and text embedding for semantic search.

## Prerequisites

Before you begin, ensure you have the following:

*   **Google Cloud Project**: With billing enabled.
*   **Google Cloud CLI**: Installed and authenticated (`gcloud auth login`).
*   **Docker**: Installed and running.
*   **Python 3.11+**: For backend services.
*   **Node.js 18+ & pnpm**: For the frontend.
*   **Make**: For running automation scripts.

## Step-by-step instructions

### 1. Setup Environment & Infrastructure

First, clone the repository and configure your Google Cloud environment.

```bash
# Set your Project ID
export PROJECT_ID=your-gcp-project-id
export REGION=asia-southeast2

# Enable required APIs
gcloud services enable run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    aiplatform.googleapis.com \
    sqladmin.googleapis.com \
    eventarc.googleapis.com
```

Create an Artifact Registry to store our Docker images:

```bash
make setup-registry
make auth-registry
```

### 2. Database Setup

Set up a Cloud SQL instance with `pgvector` support. (Detailed instructions for Cloud SQL creation are outside this scope, but ensure you have the connection string).

Update your `.env` or export the variable:

```bash
export DATABASE_URL=postgresql://user:pass@host:5432/legal_council
```

Initialize the database schema:

```bash
make db-schema
```

### 3. Deploy the Extraction Job

This service listens for PDF uploads, extracts text, generates embeddings, and stores them in the database.

```bash
# Create the GCS bucket for uploads
make create-bucket

# Deploy the Cloud Function
make deploy-extraction
```

### 4. Deploy the API Service

The API handles the deliberation logic and agent orchestration.

```bash
make deploy-api-full
```

### 5. Deploy the Frontend

The Next.js application provides the chat interface.

```bash
make deploy-frontend-full
```

### 6. Local Development (Optional)

If you want to test locally before deploying:

**Backend:**
```bash
# Install dependencies
make api-sync

# Run server
make api-dev
```

**Frontend:**
```bash
# Install dependencies
make frontend-install

# Run server
make frontend-dev
```

## Result / Demo

Once deployed, you will see a modern legal interface.

1.  **Case Input**: Enter a case summary or upload a PDF.
2.  **Deliberation Room**: Watch as three AI agents debate the case in real-time.
    *   **Judge Strict** will cite specific articles.
    *   **Judge Humanist** will argue for mitigating factors.
    *   **Judge Historian** will bring up similar past cases.
3.  **Legal Opinion**: At the end, generate a comprehensive PDF legal opinion summarizing the council's recommendation.

The system visualizes the "Debate Progress" and allows you to intervene or ask specific questions to specific judges.

## What’s next?

*   **Voice Input**: Add speech-to-text so judges can dictate their views.
*   **Multi-language Support**: Expand to support local Indonesian dialects.
*   **Mobile App**: Build a React Native version for judges on the go.

## Call to action

To learn more about Google Cloud services and to create impact for the work you do, get around to these steps right away:

*   Register for [Code Vipassana sessions](https://events.withgoogle.com/code-vipassana/)
*   Join the meetup group [Datapreneur Social](https://www.meetup.com/datapreneur-social-bangalore/)
*   Sign up to become [Google Cloud Innovator](https://cloud.google.com/innovators)
