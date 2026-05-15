# SHL Assessment Recommender

Conversational agent that recommends SHL assessments from the official product catalog.

Built with FastAPI, hybrid retrieval (FAISS + BM25), and LLM-grounded recommendation generation.

---

# Quick Start

## Install dependencies

```bash
pip install -r requirements.txt
```

---

## Set environment variables

```bash
cp .env.example .env
```

Add API keys inside `.env`

```env
GROQ_API_KEY=your_key
GEMINI_API_KEY=your_key
```

Get free API keys:

* Groq: https://console.groq.com
* Gemini: https://aistudio.google.com

---

## Build indexes

```bash
python scripts/build_index.py
```

---

## Run server

```bash
uvicorn app.main:app --reload --port 8000
```

---

## Test API

```bash
curl http://localhost:8000/health
```

---

## Test Chat Endpoint

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"messages\": [{\"role\": \"user\", \"content\": \"Hiring a Java developer who works with stakeholders\"}]}"
```

---

## Run tests

```bash
pytest tests/ -v
```

---

# Swagger Docs

```text
http://127.0.0.1:8000/docs
```

---

# API Reference

## GET /health

```json
{
  "status": "ok"
}
```

---

## GET /

```json
{
  "service": "SHL Assessment Recommender",
  "version": "1.0.0",
  "endpoints": {
    "health": "GET /health",
    "chat": "POST /chat",
    "docs": "GET /docs"
  }
}
```

---

## POST /chat

### Request

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Hiring a Java developer who works with stakeholders"
    },
    {
      "role": "assistant",
      "content": "What seniority level?"
    },
    {
      "role": "user",
      "content": "Mid-level, around 4 years"
    }
  ]
}
```

### Response

```json
{
  "reply": "For a mid-level Java developer who works with stakeholders, Java 8 (New) evaluates OOP, collections, and backend Java fundamentals.",

  "recommendations": [
    {
      "name": "Java 8 (New)",
      "url": "https://www.shl.com/solutions/products/product-catalog/view/java-8-new/",
      "test_type": "K",
      "score": 1.0,
      "reason": "Assesses modern Java 8 concepts relevant for backend development."
    },
    {
      "name": "Core Java",
      "url": "https://www.shl.com/solutions/products/product-catalog/view/core-java/",
      "test_type": "K",
      "score": 0.997,
      "reason": "Evaluates Java fundamentals, OOP, collections, and backend programming skills."
    },
    {
      "name": "OPQ32r",
      "url": "https://www.shl.com/solutions/products/product-catalog/view/opq32r/",
      "test_type": "P",
      "score": 0.896,
      "reason": "Evaluates workplace personality traits, teamwork, and communication style."
    }
  ],

  "end_of_conversation": true
}
```

---

# Field Explanations

| Field               | Meaning                                                     |
| ------------------- | ----------------------------------------------------------- |
| score               | Normalized relevance score (0.0–1.0)                        |
| reason              | Explanation of why assessment fits                          |
| test_type           | K = Knowledge, A = Ability, P = Personality, C = Competency |
| end_of_conversation | True when recommendation flow is complete                   |

---

# Architecture

```text
User Query
    ↓
Guardrails
    ↓
Hybrid Retrieval (BM25 + FAISS)
    ↓
LLM Recommendation Generation
    ↓
Validator Layer
    ↓
Final Response
```

---

# Hybrid Retrieval

The system combines:

* BM25 lexical search
* FAISS semantic search
* Reciprocal Rank Fusion (RRF)
* Metadata scoring boosts

Boosts include:

* Seniority match
* Skill match
* Test-type match

Returns:

* Top ranked assessments
* Confidence scores
* Grounded recommendations

---

# Guardrails

The system blocks:

* Prompt injection attempts
* Hard off-topic queries
* Unsafe instructions

Supports:

* Clarification questions
* Multi-turn conversations
* Refinement requests
* Assessment comparisons

---

# Validator

Every recommendation passes validation that:

* Verifies SHL URLs
* Removes invalid recommendations
* Enriches reason fields
* Enforces schema consistency
* Limits responses to max 10 recommendations

---

# Stack

| Component      | Choice                       |
| -------------- | ---------------------------- |
| Framework      | FastAPI                      |
| Embeddings     | all-MiniLM-L6-v2             |
| Vector Search  | FAISS                        |
| Keyword Search | BM25                         |
| LLM            | Groq llama-3.3-70b-versatile |
| Fallback LLM   | Gemini 2.0 Flash             |

---

# Performance

* Cold start: ~0.3s
* Typical latency: ~2–5s
* Hard timeout: 25s per request
* Embedding model preloaded during startup

---

# Deployment

## Docker

```bash
docker build -t shl-recommender .

docker run -p 8000:8000 \
  -e GROQ_API_KEY=your_key \
  -e GEMINI_API_KEY=your_key \
  shl-recommender
```

---

## Railway

```bash
railway login
railway init
railway up
```

---

## Render

* Push repository to GitHub
* Connect repository in Render
* Add environment variables
* Deploy using `render.yaml`

---

# Author

Built for the SHL AI Research Intern Assignment.
