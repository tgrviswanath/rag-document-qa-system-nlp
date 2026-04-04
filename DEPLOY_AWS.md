# AWS Deployment Guide — Project 12 RAG Document QA System

---

## AWS Services for RAG Document QA

### 1. Ready-to-Use AI (No Model Needed)

| Service                    | What it does                                                                 | When to use                                        |
|----------------------------|------------------------------------------------------------------------------|----------------------------------------------------|
| **Amazon Bedrock**         | Claude/Titan/Llama for LLM answer generation — replace Ollama llama3.2      | Replace your local Ollama LLM                      |
| **Amazon Bedrock KB**      | Managed RAG pipeline — ingest docs, embed, store in vector DB, query        | Replace your entire LangChain + FAISS pipeline     |
| **Amazon Kendra**          | Managed semantic search and document QA over uploaded documents              | When you need enterprise-grade document search     |

> **Amazon Bedrock Knowledge Bases** is the direct replacement for your LangChain + FAISS + Ollama pipeline. Upload PDFs → auto-chunked, embedded, stored in OpenSearch Serverless → query with Claude.

### 2. Host Your Own Model (Keep Current Stack)

| Service                    | What it does                                                        | When to use                                           |
|----------------------------|---------------------------------------------------------------------|-------------------------------------------------------|
| **AWS App Runner**         | Run backend container — simplest, no VPC or cluster needed          | Quickest path to production                           |
| **Amazon ECS Fargate**     | Run backend + nlp-service containers in a private VPC               | Best match for your current microservice architecture |
| **Amazon ECR**             | Store your Docker images                                            | Used with App Runner, ECS, or EKS                     |

### 3. Supporting Services

| Service                  | Purpose                                                                   |
|--------------------------|---------------------------------------------------------------------------|
| **Amazon S3**            | Store uploaded PDF/DOCX/TXT documents                                     |
| **Amazon OpenSearch**    | Persistent vector store — replace in-memory FAISS                        |
| **AWS Secrets Manager**  | Store API keys and connection strings instead of .env files               |
| **Amazon CloudWatch**    | Track QA latency, retrieval accuracy, request volume                      |

---

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  S3 + CloudFront — React Frontend                           │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS
┌──────────────────────▼──────────────────────────────────────┐
│  AWS App Runner / ECS Fargate — Backend (FastAPI :8000)     │
└──────────────────────┬──────────────────────────────────────┘
                       │ Internal
        ┌──────────────┴──────────────┐
        │ Option A                    │ Option B
        ▼                             ▼
┌───────────────────┐    ┌────────────────────────────────────┐
│ ECS Fargate       │    │ Amazon Bedrock Knowledge Bases     │
│ NLP Service :8001 │    │ Claude + OpenSearch Serverless     │
│ LangChain+FAISS   │    │ No infrastructure needed           │
│ + Ollama          │    │                                    │
└───────────────────┘    └────────────────────────────────────┘
```

---

## Prerequisites

```bash
aws configure
AWS_REGION=eu-west-2
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
```

---

## Step 1 — Create ECR and Push Images

```bash
aws ecr create-repository --repository-name ragqa/nlp-service --region $AWS_REGION
aws ecr create-repository --repository-name ragqa/backend --region $AWS_REGION
ECR=$AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR
docker build -f docker/Dockerfile.nlp-service -t $ECR/ragqa/nlp-service:latest ./nlp-service
docker push $ECR/ragqa/nlp-service:latest
docker build -f docker/Dockerfile.backend -t $ECR/ragqa/backend:latest ./backend
docker push $ECR/ragqa/backend:latest
```

---

## Step 2 — Create S3 Bucket for Documents

```bash
aws s3 mb s3://ragqa-docs-$AWS_ACCOUNT --region $AWS_REGION
```

---

## Step 3 — Deploy with App Runner

```bash
aws apprunner create-service \
  --service-name ragqa-backend \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "'$ECR'/ragqa/backend:latest",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "8000",
        "RuntimeEnvironmentVariables": {
          "NLP_SERVICE_URL": "http://nlp-service:8001"
        }
      }
    }
  }' \
  --instance-configuration '{"Cpu": "2 vCPU", "Memory": "4 GB"}' \
  --region $AWS_REGION
```

---

## Option B — Use Amazon Bedrock Knowledge Bases

```python
import boto3

bedrock_agent = boto3.client("bedrock-agent-runtime", region_name="eu-west-2")

def ask(question: str, kb_id: str) -> dict:
    response = bedrock_agent.retrieve_and_generate(
        input={"text": question},
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": kb_id,
                "modelArn": "arn:aws:bedrock:eu-west-2::foundation-model/anthropic.claude-v2"
            }
        }
    )
    return {
        "answer": response["output"]["text"],
        "citations": [c["retrievedReferences"] for c in response.get("citations", [])]
    }
```

Add to requirements.txt: `boto3>=1.34.0`

---

## CI/CD — GitHub Actions

```yaml
name: Deploy to AWS
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: eu-west-2
      - uses: aws-actions/amazon-ecr-login@v2
      - run: |
          docker build -f docker/Dockerfile.backend \
            -t ${{ secrets.ECR_REGISTRY }}/ragqa/backend:${{ github.sha }} ./backend
          docker push ${{ secrets.ECR_REGISTRY }}/ragqa/backend:${{ github.sha }}
```

---

## Estimated Monthly Cost

| Service                    | Tier              | Est. Cost          |
|----------------------------|-------------------|--------------------|
| App Runner (backend)       | 2 vCPU / 4 GB     | ~$30–40/month      |
| App Runner (nlp-service)   | 2 vCPU / 4 GB     | ~$30–40/month      |
| ECR + S3 + CloudFront      | Standard          | ~$3–7/month        |
| Bedrock Knowledge Bases    | Pay per query     | ~$5–15/month       |
| **Total (Option A)**       |                   | **~$63–87/month**  |
| **Total (Option B)**       |                   | **~$18–32/month**  |

For exact estimates → https://calculator.aws

---

## Teardown

```bash
aws ecr delete-repository --repository-name ragqa/backend --force
aws ecr delete-repository --repository-name ragqa/nlp-service --force
aws s3 rm s3://ragqa-docs-$AWS_ACCOUNT --recursive
aws s3 rb s3://ragqa-docs-$AWS_ACCOUNT
```
