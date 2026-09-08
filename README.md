# AssessIQ

[![CI](https://github.com/Ohi-Me/AssessIQ/actions/workflows/ci.yml/badge.svg)](https://github.com/Ohi-Me/AssessIQ/actions/workflows/ci.yml)

A conversational AI agent that recommends the right talent assessment for a role from a plain-English hiring need — grounded in a real catalog of published assessments, so it can only suggest tests that actually exist.

Ask it something like *"Hiring an SDE intern to test coding and problem solving"* and it clarifies what it's missing, then returns ranked assessment recommendations with a reason for each.

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
  "reply": "For an SDE intern, the Java Programming Test covers OOP and data structures, while the Debugging Simulation tests real debugging under time pressure.",
  "recommendations": [
    {
      "name": "Java Programming Test",
      "test_type": "K",
      "score": 1.0,
      "reason": "Assesses object-oriented design, collections and data structures."
    },
    {
      "name": "Debugging Simulation",
      "test_type": "S",
      "score": 0.896,
      "reason": "Candidates diagnose and repair failing code under time pressure."
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

## Evaluation

Retrieval is scored against a hand-labelled set of 20 queries in
`evals/retrieval_set.json`, covering the role families the catalog serves.
Relevance is binary; a label naming an assessment that no longer exists fails
the run rather than silently deflating the score.

```bash
python scripts/evaluate.py
```

| metric | value |
| ------------ | ----- |
| Recall@5     | 0.87  |
| Recall@10    | 0.99  |
| MRR          | 0.89  |
| nDCG@10      | 0.88  |
| Precision@5  | 0.41  |

Precision@5 is low by construction: most queries have two or three relevant
assessments, so five slots cannot all be correct. Recall and MRR are the
metrics that matter here — nearly everything relevant reaches the top ten, and
the first hit is usually first or second.

Only retrieval is evaluated. Generation is excluded on purpose: it is
non-deterministic and needs API keys, which would make the numbers
unrepeatable and stop this running in CI.

CI enforces a floor:

```bash
python scripts/evaluate.py --min-recall-at-5 0.75
```

## Performance

Every request is timed per stage — guardrails, retrieval, generation,
validation — and the breakdown is returned on the response as `timings` and
written to the logs, so it is clear which stage owns a given latency.

The breakdown showed retrieval was dominated by query embedding; the searches
themselves are microseconds against 31 vectors. Embeddings are now memoized on
the exact query text, and successful LLM completions are cached on a hash of
the prompt (failures are never cached — caching one rate-limited response would
pin the error in place).

Retrieval latency, measured with `python scripts/benchmark.py`
(8 queries × 5 repeats, local CPU):

| | cold cache | warm cache |
| ------ | ---------- | ---------- |
| p50    | 21.4 ms    | 0.9 ms     |
| p95    | 31.9 ms    | 1.7 ms     |
| mean   | 24.4 ms    | 1.0 ms     |

**23.8× faster at p50.** Generation is excluded from the benchmark on purpose:
it is a call to a third-party API, so its latency measures the provider rather
than this system. Live cache counters are exposed at `GET /stats`.

End-to-end latency is dominated by generation (seconds, provider-bound), not by
anything in this service. The embedding model is loaded at startup rather than
on first query, and requests are capped at 25s.

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

## Data

The catalog is vendor-neutral: 31 entries describing standard categories of
hiring assessment — programming and knowledge tests, coding simulations,
aptitude batteries, personality questionnaires and situational judgement —
rather than any single provider's branded products.

It is defined in `scripts/build_catalog.py` and compiled to
`data/catalog.json`:

```bash
python scripts/build_catalog.py
```

The retrieval and agent layers are catalog-agnostic. To point the system at a
different catalog, replace the `ASSESSMENTS` list, then regenerate both the
catalog and the search indexes:

```bash
python scripts/build_catalog.py
python -c "from app.catalog_loader import load_catalog; from app.retriever import build_indexes; build_indexes(load_catalog())"
```

Commit the resulting `data/*.pkl` files. They are checked in deliberately:
building an index holds the embedding model and the encode batch in memory at
the same time, which exceeds a 512Mi instance, whereas loading a prebuilt one
does not.

## Author

Built by [Rohit Kumar](https://github.com/Ohi-Me).

<!-- Updated -->
