# Azure Deployment Guide — Project 12 RAG Document QA System

---

## Azure Services for RAG Document QA

### 1. Ready-to-Use AI (No Model Needed)

| Service                              | What it does                                                                 | When to use                                        |
|--------------------------------------|------------------------------------------------------------------------------|----------------------------------------------------|
| **Azure OpenAI Service**             | GPT-4/GPT-3.5 for LLM answer generation — replace Ollama llama3.2           | Replace your local Ollama LLM                      |
| **Azure AI Search**                  | Vector store for document chunks — replace in-memory FAISS                  | Replace your FAISS index with persistent storage   |
| **Azure AI Document Intelligence**   | Extract text from PDF/DOCX before chunking                                   | Replace PyMuPDF + python-docx                      |

> **Azure OpenAI + Azure AI Search** together replace your LangChain + FAISS + Ollama pipeline. Azure AI Search handles chunking, embedding, and retrieval natively via its integrated vectorization feature.

### 2. Host Your Own Model (Keep Current Stack)

| Service                        | What it does                                                        | When to use                                           |
|--------------------------------|---------------------------------------------------------------------|-------------------------------------------------------|
| **Azure Container Apps**       | Run your 3 Docker containers (frontend, backend, nlp-service)       | Best match for your current microservice architecture |
| **Azure Container Registry**   | Store your Docker images                                            | Used with Container Apps or AKS                       |

### 3. Supporting Services

| Service                       | Purpose                                                                  |
|-------------------------------|--------------------------------------------------------------------------|
| **Azure Blob Storage**        | Store uploaded PDF/DOCX/TXT documents                                    |
| **Azure Key Vault**           | Store API keys and connection strings instead of .env files              |
| **Azure Monitor + App Insights** | Track QA latency, retrieval accuracy, request volume                 |

---

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Azure Static Web Apps — React Frontend                     │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────────────────────────┐
│  Azure Container Apps — Backend (FastAPI :8000)             │
└──────────────────────┬──────────────────────────────────────┘
                       │ Internal
        ┌──────────────┴──────────────┐
        │ Option A                    │ Option B
        ▼                             ▼
┌───────────────────┐    ┌────────────────────────────────────┐
│ Container Apps    │    │ Azure OpenAI (GPT-4)               │
│ NLP Service :8001 │    │ + Azure AI Search (vector)         │
│ LangChain+FAISS   │    │ No infrastructure needed           │
│ + Ollama          │    │                                    │
└───────────────────┘    └────────────────────────────────────┘
```

---

## Prerequisites

```bash
az login
az group create --name rg-rag-qa --location uksouth
az extension add --name containerapp --upgrade
```

---

## Step 1 — Create Container Registry and Push Images

```bash
az acr create --resource-group rg-rag-qa --name ragqaacr --sku Basic --admin-enabled true
az acr login --name ragqaacr
ACR=ragqaacr.azurecr.io
docker build -f docker/Dockerfile.nlp-service -t $ACR/nlp-service:latest ./nlp-service
docker push $ACR/nlp-service:latest
docker build -f docker/Dockerfile.backend -t $ACR/backend:latest ./backend
docker push $ACR/backend:latest
```

---

## Step 2 — Create Blob Storage for Documents

```bash
az storage account create --name ragqadocs --resource-group rg-rag-qa --sku Standard_LRS
az storage container create --name documents --account-name ragqadocs
```

---

## Step 3 — Deploy Container Apps

```bash
az containerapp env create --name ragqa-env --resource-group rg-rag-qa --location uksouth

az containerapp create \
  --name nlp-service --resource-group rg-rag-qa \
  --environment ragqa-env --image $ACR/nlp-service:latest \
  --registry-server $ACR --target-port 8001 --ingress internal \
  --min-replicas 1 --max-replicas 3 --cpu 2 --memory 4.0Gi

az containerapp create \
  --name backend --resource-group rg-rag-qa \
  --environment ragqa-env --image $ACR/backend:latest \
  --registry-server $ACR --target-port 8000 --ingress external \
  --min-replicas 1 --max-replicas 5 --cpu 0.5 --memory 1.0Gi \
  --env-vars NLP_SERVICE_URL=http://nlp-service:8001
```

---

## Option B — Use Azure OpenAI + Azure AI Search

```python
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential

openai_client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-02-01"
)
search_client = SearchClient(
    endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
    index_name="documents",
    credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY"))
)

def ask(question: str) -> dict:
    # Embed question
    q_embedding = openai_client.embeddings.create(input=question, model="text-embedding-ada-002").data[0].embedding
    # Retrieve top chunks
    vq = VectorizedQuery(vector=q_embedding, k_nearest_neighbors=4, fields="embedding")
    chunks = [r["content"] for r in search_client.search(search_text=None, vector_queries=[vq])]
    context = "\n\n".join(chunks)
    # Generate answer
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Answer using only the provided context."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        ]
    )
    return {"answer": response.choices[0].message.content, "sources": chunks}
```

Add to requirements.txt: `openai>=1.12.0 azure-search-documents>=11.4.0`

---

## CI/CD — GitHub Actions

```yaml
name: Deploy to Azure
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      - run: az acr login --name ragqaacr
      - run: |
          docker build -f docker/Dockerfile.backend -t ragqaacr.azurecr.io/backend:${{ github.sha }} ./backend
          docker push ragqaacr.azurecr.io/backend:${{ github.sha }}
          az containerapp update --name backend --resource-group rg-rag-qa \
            --image ragqaacr.azurecr.io/backend:${{ github.sha }}
```

---

## Estimated Monthly Cost

| Service                  | Tier      | Est. Cost         |
|--------------------------|-----------|-------------------|
| Container Apps (backend) | 0.5 vCPU  | ~$10–15/month     |
| Container Apps (nlp-svc) | 2 vCPU    | ~$25–35/month     |
| Container Registry       | Basic     | ~$5/month         |
| Static Web Apps          | Free      | $0                |
| Azure OpenAI (GPT-4)     | Pay per token | ~$10–30/month |
| Azure AI Search          | Basic     | ~$75/month        |
| **Total (Option A)**     |           | **~$40–55/month** |
| **Total (Option B)**     |           | **~$100–130/month**|

For exact estimates → https://calculator.azure.com

---

## Teardown

```bash
az group delete --name rg-rag-qa --yes --no-wait
```
