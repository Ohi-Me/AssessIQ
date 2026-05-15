# SHL Assessment Recommender

Conversational agent that recommends SHL assessments from the official product catalog. Built with FastAPI, hybrid retrieval (FAISS + BM25), and Groq LLM.

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set environment variables
```bash
cp .env.example .env
# Edit .env — add GROQ_API_KEY and/or GEMINI_API_KEY
```
Get keys free:
- Groq: https://console.groq.com (fast, recommended)
- Gemini: https://aistudio.google.com

### 3. Build indexes (optional — auto-built at startup)
```bash
python scripts/build_index.py
```

### 4. Run server
```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Test
```bash
# Health check
curl http://localhost:8000/health

# Chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "I need to hire a mid-level Java developer"}]}'

# Run test suite
pytest tests/ -v
```

## API Reference

### GET /health
```json
{"status": "ok"}
```

### POST /chat
**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "Hiring a Java developer who works with stakeholders"},
    {"role": "assistant", "content": "What seniority level?"},
    {"role": "user", "content": "Mid-level, around 4 years"}
  ]
}
```
**Response:**
```json
{
  "reply": "Here are 5 assessments that fit a mid-level Java developer...",
  "recommendations": [
    {
      "name": "Java 8 (New)",
      "url": "https://www.shl.com/...",
      "test_type": "K",
      "score": 0.97,
      "reason": null
    },
    {
      "name": "OPQ32r",
      "url": "https://www.shl.com/...",
      "test_type": "P",
      "score": 0.81,
      "reason": null
    }
  ],
  "end_of_conversation": true
}
```

> `score` is a normalized 0.0–1.0 relevance score from the hybrid retriever. `reason` is an optional field for future enrichment.

## Architecture

```
User Query
    ↓
[1] Guardrails (guardrails.py) — pre-LLM, deterministic
    ↓
┌──────────────────────────────────────┐
│ injection  → refuse immediately      │
│ hard off-topic → refuse (no bypass)  │
│ soft off-topic → refuse if no context│
│ comparison → grounded compare        │
│ refinement → update shortlist        │
│ vague      → ask ONE clarifying Q    │
│ ok         → recommend               │
└──────────────────────────────────────┘
    ↓
[2] Hybrid Retriever (retriever.py)
    ↓
[3] LLM (Groq / Gemini) — grounded generation
    ↓
[4] Validator (validator.py) — schema + URL check
    ↓
ChatResponse
```

## Hybrid Retrieval

The retriever combines two complementary strategies for strong recall:

```
Query
  ├── BM25 Lexical Search (rank-bm25)
  │     Exact keyword matching — great for assessment names,
  │     role titles, and technical terms (e.g. "Java", "SQL")
  │
  └── FAISS Semantic Search (sentence-transformers)
        all-MiniLM-L6-v2 embeddings — great for conceptual
        similarity (e.g. "problem solving" → Inductive Reasoning)
              ↓
        RRF Fusion (BM25 weight=0.4, FAISS weight=0.6)
              ↓
        Metadata Filter + Scoring Boosts
          · Seniority match  → ×1.3
          · Test type match  → ×1.25
          · Skill match      → ×1.15 per match
              ↓
        Top-10 results with normalized confidence scores (0.0–1.0)
```

## Guardrails

The system uses a two-tier guardrail approach for safety and quality:

### Hard Off-Topic (always refused, no bypass)
Salary/compensation, legal advice, lawsuits, employment law, HR actions (fire/terminate), weather, recipes, jokes, politics, religion.

> Even if the message contains a job role keyword (e.g. "salary for a Java developer"), it is refused.

### Soft Off-Topic (refused only if no assessment context)
Games, creative writing, competitor products (HackerRank, TestGorilla, Codility), competitor AI (ChatGPT, Gemini).

### Prompt Injection (always refused)
"Ignore instructions", "system prompt", "jailbreak", "DAN", "pretend to be", and similar patterns are detected pre-LLM and refused immediately.

### Schema Validation
Every recommendation passes through a validator that:
- Checks URLs against the scraped catalog whitelist
- Auto-corrects hallucinated URLs by matching assessment name
- Drops any recommendation whose URL cannot be verified
- Truncates to max 10 recommendations

### Timeout Protection
Each `/chat` call has a 25-second hard timeout (within the 30s spec limit).

### Turn Cap
Max 8 messages (user + assistant combined) per conversation. On hitting the cap, the agent returns a graceful close message with `end_of_conversation: true`.

## Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| Framework | FastAPI | Required by assignment |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 | Fast, free, good quality |
| Vector DB | FAISS | In-memory, no external service needed |
| Keyword | BM25 (rank-bm25) | Complements semantic for exact matches |
| LLM | Groq llama-3.3-70b-versatile | Free tier, fast (<5s), high quality |
| Fallback LLM | Google Gemini 2.0 Flash | Free tier backup |
| Deployment | Railway / Render | Easy FastAPI hosting |

## Sample Conversation

```
User: I need to assess candidates for a backend role
Agent: What seniority level are you targeting — entry, mid-level, or senior?

User: Senior, about 6+ years experience. They work with Java and also manage a small team.
Agent: Based on that, here are my recommendations:

  Java 8 (New) evaluates OOP, collections, concurrency, and Spring — essential for a
  senior Java backend engineer. OPQ32r measures personality traits including leadership
  and stakeholder management, relevant for someone managing a team. Verify Numerical
  Reasoning assesses analytical thinking for senior-level problem solving...

  [7 recommendations, end_of_conversation: true]
```

## Deploy to Docker

```bash
docker build -t shl-recommender .
docker run -p 8000:8000 \
  -e GROQ_API_KEY=your_key \
  -e GEMINI_API_KEY=your_key \
  shl-recommender
```

## Deploy to Railway

```bash
npm install -g @railway/cli
railway login
railway init
railway up
# Set env vars: GROQ_API_KEY, GEMINI_API_KEY
```

## Deploy to Render

1. Push to GitHub
2. Connect repo in Render dashboard
3. Use `render.yaml` config
4. Set `GROQ_API_KEY` and `GEMINI_API_KEY` in env vars

## Performance Notes

- **Cold start**: ~0.3s (indexes loaded from disk, model pre-warmed at startup)
- **First request**: ~3–5s (LLM call only — model already loaded)
- **Subsequent requests**: ~2–4s
- **Timeout budget**: 25s per call (hard limit)

> The embedding model (`all-MiniLM-L6-v2`) is pre-warmed during startup so the first `/chat` call does not incur the ~20s model load penalty.

## Running Tests

```bash
# All tests
pytest tests/ -v

# Guardrails only (no LLM needed, fast)
pytest tests/test_guardrails.py -v

# Retrieval quality
pytest tests/test_retriever.py -v

# Full API integration (requires running server)
pytest tests/test_api.py -v
```
