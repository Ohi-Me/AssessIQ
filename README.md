# AssessIQ

A conversational AI agent that recommends the right talent assessment for a role from a plain-English hiring need — grounded in SHL's real, public assessment catalog.

Ask it something like *"Hiring a Java developer who works with stakeholders"* and it clarifies what it's missing, then returns ranked, cited assessment recommendations with a reason for each.

**Why:** Hiring managers picking an assessment usually have to browse a large product catalog by hand. This turns that into a short conversation — the agent asks for the one missing signal it needs (role, seniority, skill focus) instead of dumping a list, then grounds every recommendation in retrieved catalog entries so it never invents an assessment.

---

## Architecture

```text
User Query
    ↓
Guardrails            (blocks prompt injection, off-topic requests)
    ↓
Hybrid Retrieval       (BM25 + FAISS, fused with RRF, boosted by seniority/skill/test-type match)
    ↓
LLM Recommendation Generation
    ↓
Validator Layer        (catalog-URL verification, schema enforcement, max 10 results)
    ↓
Final Response
```

**Hybrid retrieval** combines BM25 lexical search with FAISS semantic search via Reciprocal Rank Fusion, then boosts results on seniority, skill, and test-type match — so results are both keyword-precise and semantically relevant.

**Guardrails** classify intent per turn (clarify / recommend / refine / compare / refuse), block prompt-injection and off-topic queries, and support multi-turn refinement and side-by-side comparisons.

**Validator** is the last layer before a response leaves the service: every recommended assessment is checked against real catalog URLs, invalid entries are dropped, and results are capped at 10.

---

## Stack

| Component      | Choice                       |
| -------------- | ----------------------------- |
| Framework      | FastAPI                       |
| Embeddings     | all-MiniLM-L6-v2              |
| Vector Search  | FAISS                         |
| Keyword Search | BM25                          |
| LLM            | Groq `openai/gpt-oss-120b`    |
| Fallback LLM   | Gemini 2.5 Flash              |

---

## Quick Start

```bash
pip install -r requirements.txt
```

Set environment variables:

```bash
cp .env.example .env
```

Add API keys inside `.env`:

```env
GROQ_API_KEY=your_key
GEMINI_API_KEY=your_key
```

Get free API keys: [Groq](https://console.groq.com) · [Gemini](https://aistudio.google.com)

Build the retrieval indexes:

```bash
python scripts/build_index.py
```

Run the server:

```bash
uvicorn app.main:app --reload --port 8000
```

Try it:

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"messages\": [{\"role\": \"user\", \"content\": \"Hiring a Java developer who works with stakeholders\"}]}"
```

Run tests:

```bash
pytest tests/ -v
```

Swagger docs: `http://127.0.0.1:8000/docs`

---

## API Reference

### `GET /health`

```json
{ "status": "ok" }
```

### `POST /chat`

**Request**

```json
{
  "messages": [
    { "role": "user", "content": "Hiring a Java developer who works with stakeholders" },
    { "role": "assistant", "content": "What seniority level?" },
    { "role": "user", "content": "Mid-level, around 4 years" }
  ]
}
```

**Response**

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

| Field                 | Meaning                                                      |
| --------------------- | -------------------------------------------------------------|
| `score`                | Normalized relevance score (0.0–1.0)                         |
| `reason`               | Explanation of why the assessment fits                       |
| `test_type`            | `K` Knowledge · `A` Ability · `P` Personality · `C` Competency |
| `end_of_conversation`  | `true` when the recommendation flow is complete              |

---

## Performance

- Cold start: ~0.3s
- Typical latency: ~2–5s
- Hard timeout: 25s per request
- Embedding model preloaded at startup

---

## Deployment

**Docker**

```bash
docker build -t assessiq .
docker run -p 8000:8000 -e GROQ_API_KEY=your_key -e GEMINI_API_KEY=your_key assessiq
```

**Railway**

```bash
railway login
railway init
railway up
```

**Render** — push to GitHub, connect the repo in Render, add env vars, deploy via `render.yaml`.

---

## Author

Built by [Rohit Kumar](https://github.com/Ohi-Me).

<!-- Updated -->
