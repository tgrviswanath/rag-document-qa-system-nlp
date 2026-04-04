# GCP Deployment Guide — Project 12 RAG Document QA System

---

## GCP Services for RAG Document QA

### 1. Ready-to-Use AI (No Model Needed)

| Service                              | What it does                                                                 | When to use                                        |
|--------------------------------------|------------------------------------------------------------------------------|----------------------------------------------------|
| **Vertex AI Gemini**                 | Gemini Pro for LLM answer generation — replace Ollama llama3.2               | Replace your local Ollama LLM                      |
| **Vertex AI Search**                 | Managed RAG pipeline — ingest docs, embed, store, query with Gemini          | Replace your entire LangChain + FAISS pipeline     |
| **Vertex AI Matching Engine**        | Vector store for document chunks — replace in-memory FAISS                  | Replace your FAISS index with persistent storage   |

> **Vertex AI Search (formerly Enterprise Search)** is the direct replacement for your LangChain + FAISS + Ollama pipeline. Upload PDFs → auto-chunked, embedded, stored → query with Gemini.

### 2. Host Your Own Model (Keep Current Stack)

| Service                    | What it does                                                        | When to use                                           |
|----------------------------|---------------------------------------------------------------------|-------------------------------------------------------|
| **Cloud Run**              | Run backend + nlp-service containers — serverless, scales to zero   | Best match for your current microservice architecture |
| **Artifact Registry**      | Store your Docker images                                            | Used with Cloud Run or GKE                            |

### 3. Supporting Services

| Service                        | Purpose                                                                   |
|--------------------------------|---------------------------------------------------------------------------|
| **Cloud Storage**              | Store uploaded PDF/DOCX/TXT documents                                     |
| **Secret Manager**             | Store API keys and connection strings instead of .env files               |
| **Cloud Monitoring + Logging** | Track QA latency, retrieval accuracy, request volume                      |

---

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Firebase Hosting — React Frontend                          │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────────────────────────┐
│  Cloud Run — Backend (FastAPI :8000)                        │
└──────────────────────┬──────────────────────────────────────┘
                       │ Internal HTTPS
        ┌──────────────┴──────────────┐
        │ Option A                    │ Option B
        ▼                             ▼
┌───────────────────┐    ┌────────────────────────────────────┐
│ Cloud Run         │    │ Vertex AI Search                   │
│ NLP Service :8001 │    │ + Vertex AI Gemini                 │
│ LangChain+FAISS   │    │ No infrastructure needed           │
│ + Ollama          │    │                                    │
└───────────────────┘    └────────────────────────────────────┘
```

---

## Prerequisites

```bash
gcloud auth login
gcloud projects create ragqa-project --name="RAG Document QA"
gcloud config set project ragqa-project
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com aiplatform.googleapis.com \
  storage.googleapis.com cloudbuild.googleapis.com
```

---

## Step 1 — Create Artifact Registry and Push Images

```bash
GCP_REGION=europe-west2
gcloud artifacts repositories create ragqa-repo \
  --repository-format=docker --location=$GCP_REGION
gcloud auth configure-docker $GCP_REGION-docker.pkg.dev
AR=$GCP_REGION-docker.pkg.dev/ragqa-project/ragqa-repo
docker build -f docker/Dockerfile.nlp-service -t $AR/nlp-service:latest ./nlp-service
docker push $AR/nlp-service:latest
docker build -f docker/Dockerfile.backend -t $AR/backend:latest ./backend
docker push $AR/backend:latest
```

---

## Step 2 — Create Cloud Storage for Documents

```bash
gsutil mb -l $GCP_REGION gs://ragqa-docs-ragqa-project
```

---

## Step 3 — Deploy to Cloud Run

```bash
gcloud run deploy nlp-service \
  --image $AR/nlp-service:latest --region $GCP_REGION \
  --port 8001 --no-allow-unauthenticated \
  --min-instances 1 --max-instances 3 --memory 4Gi --cpu 2

NLP_URL=$(gcloud run services describe nlp-service --region $GCP_REGION --format "value(status.url)")

gcloud run deploy backend \
  --image $AR/backend:latest --region $GCP_REGION \
  --port 8000 --allow-unauthenticated \
  --min-instances 1 --max-instances 5 --memory 1Gi --cpu 1 \
  --set-env-vars NLP_SERVICE_URL=$NLP_URL
```

---

## Option B — Use Vertex AI Search + Gemini

```python
from google.cloud import discoveryengine_v1 as discoveryengine

client = discoveryengine.SearchServiceClient()

def ask(question: str, data_store_id: str) -> dict:
    serving_config = (
        f"projects/ragqa-project/locations/global/collections/default_collection"
        f"/dataStores/{data_store_id}/servingConfigs/default_config"
    )
    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=question,
        page_size=5,
        content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
            summary_spec=discoveryengine.SearchRequest.ContentSearchSpec.SummarySpec(
                summary_result_count=5, include_citations=True
            )
        )
    )
    response = client.search(request)
    return {
        "answer": response.summary.summary_text,
        "results": [r.document.derived_struct_data for r in response.results]
    }
```

Add to requirements.txt: `google-cloud-discoveryengine>=0.11.0`

---

## CI/CD — GitHub Actions

```yaml
name: Deploy to GCP
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      - uses: google-github-actions/setup-gcloud@v2
      - run: gcloud auth configure-docker europe-west2-docker.pkg.dev
      - run: |
          docker build -f docker/Dockerfile.backend \
            -t europe-west2-docker.pkg.dev/${{ secrets.GCP_PROJECT }}/ragqa-repo/backend:${{ github.sha }} ./backend
          docker push europe-west2-docker.pkg.dev/${{ secrets.GCP_PROJECT }}/ragqa-repo/backend:${{ github.sha }}
          gcloud run deploy backend \
            --image europe-west2-docker.pkg.dev/${{ secrets.GCP_PROJECT }}/ragqa-repo/backend:${{ github.sha }} \
            --region europe-west2 --platform managed
```

---

## Estimated Monthly Cost

| Service                    | Tier                  | Est. Cost          |
|----------------------------|-----------------------|--------------------|
| Cloud Run (backend)        | 1 vCPU / 1 GB         | ~$10–15/month      |
| Cloud Run (nlp-service)    | 2 vCPU / 4 GB         | ~$20–30/month      |
| Artifact Registry          | Storage               | ~$1–2/month        |
| Firebase Hosting           | Free tier             | $0                 |
| Cloud Storage              | Standard              | ~$1/month          |
| Vertex AI Search           | Pay per query         | ~$5–15/month       |
| **Total (Option A)**       |                       | **~$32–48/month**  |
| **Total (Option B)**       |                       | **~$17–33/month**  |

For exact estimates → https://cloud.google.com/products/calculator

---

## Teardown

```bash
gcloud run services delete backend --region $GCP_REGION --quiet
gcloud run services delete nlp-service --region $GCP_REGION --quiet
gcloud artifacts repositories delete ragqa-repo --location=$GCP_REGION --quiet
gsutil rm -r gs://ragqa-docs-ragqa-project
gcloud projects delete ragqa-project
```
