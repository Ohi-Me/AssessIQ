# SHL Assessment Recommender — REFERENCE.md
**Project memory doc. Always read this at the start of every new session.**

---

## Project Goal
Build a conversational FastAPI agent that recommends SHL assessments from the official catalog.
- Deadline: 17 May 2026, 6 PM
- Submission: Deployed public API URL + 2-page approach document

---

## Deliverables Checklist
- [ ] `GET /health` → `{"status": "ok"}` (HTTP 200, cold start ≤2 min)
- [ ] `POST /chat` → strict JSON schema (see below)
- [ ] Deployed public URL (Railway or Render)
- [ ] 2-page approach document (PDF)
- [ ] All catalog URLs must be scraped — no hallucinated URLs

---

## API Schema (NON-NEGOTIABLE)

### Request
```json
{
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

### Response
```json
{
  "reply": "string",
  "recommendations": [
    {"name": "string", "url": "string", "test_type": "string"}
  ],
  "end_of_conversation": false
}
```

Rules:
- `recommendations` = [] when clarifying or refusing
- `recommendations` = 1–10 items when committed to a shortlist
- `end_of_conversation` = true when agent commits to a shortlist OR user says done
- Every URL must come from scraped catalog — NEVER hallucinate
- Max 8 messages per conversation (user + assistant combined)
- 30 second per-call timeout

---

## Architecture (3-Layer Pipeline)

```
User Message
    ↓
[1] Guardrails (guardrails.py) — pre-LLM, deterministic
    - Injection → refuse immediately
    - HARD off-topic (salary/legal/HR/weather) → refuse, NO bypass
    - SOFT off-topic → refuse only if no assessment context
    - Comparison → route to compare handler
    - Refinement → route to refine handler (only if prior recs exist)
    - Vague → route to clarify handler
    - OK → route to recommend handler
    ↓
[2] Retriever (retriever.py) — Hybrid FAISS + BM25
    - extract_constraints() → role, seniority, skills (now properly populated), test_types, duration, remote
    - build augmented query with constraints
    - BM25 keyword retrieval + FAISS semantic retrieval
    - RRF fusion (BM25 weight=0.4, FAISS weight=0.6)
    - Metadata filter + scoring boosts (seniority, test_type, skill match)
    - k=25 candidates → rerank → top 10
    ↓
[3] Response Generator (agent.py + prompts.py + llm_client.py)
    - clarify → ask ONE question, no recs, end_of_conversation=False
    - off-topic/injection → static refusal, no recs
    - recommend → LLM grounded reply, extract recs, end_of_conversation=True when shortlist committed
    - refine → same as recommend but preserves prior constraints
    - compare → grounded comparison from catalog data only, no recs
    - max_turns → graceful close message, end_of_conversation=True
    ↓
[4] Validator (validator.py)
    - URL whitelist check against catalog_urls
    - Auto-correct URL from catalog if LLM hallucinated
    - Truncate to max 10 recommendations
    - Drop recs with no valid URL
```

---

## Catalog Schema (per item)
```json
{
  "id": "unique-slug",
  "name": "Java 8 (New)",
  "url": "https://www.shl.com/solutions/products/product-catalog/...",
  "description": "...",
  "job_levels": ["entry", "junior", "mid", "senior", "manager", "executive"],
  "test_type": "K",
  "test_type_label": "Knowledge & Skills",
  "duration_minutes": 30,
  "remote_testing": true,
  "adaptive_irt": false,
  "languages": ["English"],
  "skills": ["java", "backend", "oop", "programming"],
  "categories": ["technical", "cognitive"],
  "tags": ["java", "developer", "programming"]
}
```

### Test Type Codes (SHL)
- A = Ability / Cognitive
- B = Biodata & Situational Judgement
- C = Competency
- D = Development & 360
- E = Assessment Exercises
- K = Knowledge & Skills
- P = Personality & Behavior
- S = Simulations

### Current Catalog (37 assessments)
| Type | Assessments |
|------|-------------|
| A (Ability) | Verify Numerical/Verbal/Inductive/Deductive/Mechanical/Spatial/Reading, Verify G+, Graduate 8.0, Technology Professional 8.0, Administrative Professional 8.0, Numerical Reasoning, Verbal Reasoning |
| P (Personality) | OPQ32r, OPQ32, Motivational Questionnaire (MQ), RemoteWorkQ, Leadership Report, Workplace Personality Inventory II, Customer Contact Styles Questionnaire, Dependability and Safety Instrument |
| K (Knowledge) | Java 8 (New), Python (New), SQL (New), JavaScript (New), C# (New), Microsoft Excel (New), Core Java, Data Analysis |
| S (Simulation) | Automata — Fix the Code, Automata Pro, Contact Center Simulation, Financial Services Simulation |
| B (SJT) | Situational Judgement Test — Customer Service, Situational Judgement Test — Management, Entry Level Sales 7.1 |
| C (Competency) | Global Skills Assessment (GSA) |

---

## File Structure
```
shl-recommender/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── schemas.py           # Pydantic models
│   ├── retriever.py         # Hybrid retrieval (FAISS + BM25)
│   ├── agent.py             # Conversation orchestration + routing
│   ├── prompts.py           # All LLM prompt templates
│   ├── guardrails.py        # Off-topic / injection detection
│   ├── validator.py         # Response schema validator
│   └── catalog_loader.py   # Load and index catalog
├── data/
│   ├── catalog.json         # Scraped SHL catalog (source of truth, 37 items)
│   └── embeddings.pkl       # Precomputed FAISS index (generated at startup)
├── scripts/
│   ├── scrape_catalog.py    # Scraper for SHL product catalog
│   └── build_index.py       # Build FAISS index from catalog
├── tests/
│   ├── test_api.py          # API endpoint integration tests
│   ├── test_guardrails.py   # Guardrails unit tests (28 cases, no LLM needed)
│   ├── test_retriever.py    # Retrieval quality tests
│   └── conversations/
│       └── sample_traces.json  # 10 conversation traces (all key personas)
├── Dockerfile
├── railway.toml             # Railway deployment config
├── render.yaml              # Render deployment config
├── requirements.txt
├── .env.example
├── README.md
└── REFERENCE.md             # THIS FILE
```

---

## Tech Stack Decisions

| Component | Choice | Reason |
|-----------|--------|--------|
| Framework | FastAPI | Required by assignment |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 | Fast, free, good quality |
| Vector DB | FAISS | In-memory, no external service needed |
| Keyword | BM25 (rank-bm25) | Complements semantic for exact matches |
| LLM | Groq (llama-3.3-70b-versatile) | Free tier, fast (<5s), high quality |
| Fallback LLM | Google Gemini 2.0 Flash | Free tier backup (upgraded from 1.5-flash) |
| Deployment | Railway | Smooth FastAPI, easy env vars |

---

## Scoring Priorities (in order)
1. **Hard evals** (must pass): schema compliance, catalog-only URLs, ≤8 messages
2. **Recall@10**: fraction of relevant assessments appearing in recommendations
3. **Behavior probes**: vague→clarify, off-topic→refuse, injection→refuse, refinement→update, no hallucinations

---

## Conversational Behavior Rules

### Clarification threshold
```
if JD provided → recommend immediately
if role AND (seniority OR skill) → recommend
if context_score >= 2 → recommend
if turns >= 4 AND context_score >= 1 → recommend (avoid loop)
else → clarify
```

### What to ask when vague
1. What role/job are they hiring for? (most important)
2. What seniority level?
3. Technical test, personality/behavioral, or both?

### Refinement handling
- Only triggers when prior recommendations exist in history
- Preserves all prior constraints
- Augments query, does NOT restart
- Re-runs retrieval with combined constraints
- end_of_conversation=True on new shortlist

### Comparison handling
- Extracts assessment names from query using KNOWN_ASSESSMENT_NAMES list
- Falls back to semantic search if names not recognized
- Only compares using scraped catalog descriptions
- end_of_conversation=False (user may follow up)

### Refusal triggers (guardrails)
**HARD (always refuse — no bypass):**
- Salary, compensation, negotiation
- Legal advice, lawsuits, discrimination, wrongful termination
- HR actions (fire/terminate employee)
- Weather, recipes, jokes, politics, religion

**SOFT (refuse only if no assessment context):**
- Games, creative writing, competitor products, competitor AI

**INJECTION (always refuse):**
- Ignore instructions, system prompt, jailbreak, DAN, pretend to be

### Turn cap
- Max 8 messages (user + assistant combined)
- On reaching cap: return MAX_TURNS_REPLY with end_of_conversation=True

---

## end_of_conversation Logic
```
True when:
  - handle_recommend() returns recs (len >= 1)
  - handle_refine() returns recs (len >= 1)
  - handle_max_turns() called (messages >= 8)
  - is_end_of_conversation() detects user saying thanks/done AFTER recs were given

False always:
  - handle_clarify()
  - handle_off_topic()
  - handle_injection()
  - handle_compare()
```

---

## Guardrail Patterns (keyword-based, pre-LLM)

### HARD_OFF_TOPIC_PATTERNS — always refuse, no role/skill bypass
Salary, negotiation, compensation, legal advice, lawsuits, discrimination,
wrongful termination, HR actions (fire/terminate), weather, recipes, jokes,
politics, religion.

**Critical bug fixed (Session 2)**: these refuse even when the message also
contains role/skill keywords (e.g. "salary for a finance manager" → off_topic).

### SOFT_OFF_TOPIC_PATTERNS — refuse only if no assessment context
Games, creative writing (poem/story/essay/song/code), meaning of life,
competitor products (HireQuest, HackerRank, Codility, TestGorilla, etc.),
personal advice, competitor AI (ChatGPT, Gemini, etc.).

### Bug: turn count (Session 2)
`_conversation_turn_count()` was counting total messages (user+assistant).
Fixed to count only user messages (true turn count).

---

## Bugs Fixed (Sessions 1–2)

### Bug 1: OFF_TOPIC bypass logic (Session 2)
**Root cause**: single `OFF_TOPIC_PATTERNS` list with blanket bypass — if role/skill keyword present, don't refuse. Salary+role queries slipped through.
**Fix**: Split into `HARD_OFF_TOPIC_PATTERNS` (unconditional) and `SOFT_OFF_TOPIC_PATTERNS` (bypass-allowed).

### Bug 2: skills never populated in extract_constraints (Session 2)
**Root cause**: `extract_constraints()` had a `skills` key in the return dict but no code ever populated it. `build_retrieval_query()` appended `constraints["skills"]` which was always [].
**Fix**: Added `SKILL_KEYWORDS` dict and extraction loop that populates skills from conversation text.

### Bug 3: turn count counted messages not turns (Session 2)
**Root cause**: `_conversation_turn_count()` returned `len(messages)` — includes both user and assistant messages. Guardrail threshold `turns >= 5` was effectively `messages >= 5`.
**Fix**: Changed to count only messages with `role == "user"`.

### Bug 4: end_of_conversation never set True on shortlist (Session 2)
**Root cause**: `handle_recommend()` always returned `end_of_conversation=False`. The field was only set by `is_end_of_conversation()` which checks for user thanks — but spec says it should be True when agent commits to shortlist.
**Fix**: `handle_recommend()` and `handle_refine()` set `end_of_conversation=True` when `len(recs) >= 1`.

### Bug 5: max turns silently sliced messages (Session 2)
**Root cause**: `main.py` sliced `messages = messages[-8:]` on overflow, continuing the conversation silently.
**Fix**: `agent.py` checks `len(messages) >= MAX_MESSAGES` and calls `handle_max_turns()` which returns a graceful close message with `end_of_conversation=True`.

### Bug 6: Gemini using deprecated model (Session 2)
**Root cause**: `llm_client.py` used `gemini-1.5-flash` which is being deprecated.
**Fix**: Updated to `gemini-2.0-flash`.

---

## Evaluation Notes

### Recall@10 Formula
```
Recall@10 = (# relevant assessments in top 10) / (total relevant for query)
Mean Recall@10 = average across all traces
```

### Key behaviors tested by evaluator
- Turn 1 vague → must clarify, NOT recommend
- Mid-conversation change → update shortlist without restart
- Off-topic → refuse with no recommendations
- Salary+role keyword → still refuse (HARD off-topic)
- JD provided → skip clarification, recommend directly
- Comparison → grounded from catalog only
- No hallucinated assessment names or URLs

---

## Known SHL Assessment Categories (from catalog)

### Cognitive / Ability (A)
- Verify Numerical/Verbal/Inductive/Deductive/Mechanical/Spatial/Reading Reasoning
- Verify G+, Graduate 8.0, Technology Professional 8.0, Administrative Professional 8.0
- Numerical Reasoning, Verbal Reasoning

### Personality / Behavioral (P)
- OPQ32r, OPQ32, Motivational Questionnaire (MQ)
- RemoteWorkQ, Leadership Report
- Workplace Personality Inventory II
- Customer Contact Styles Questionnaire
- Dependability and Safety Instrument

### Knowledge & Skills (K)
- Java 8 (New), Python (New), SQL (New), JavaScript (New), C# (New)
- Microsoft Excel (New), Core Java, Data Analysis

### Simulations (S)
- Automata — Fix the Code, Automata Pro
- Contact Center Simulation, Financial Services Simulation

### Situational Judgement (B)
- Situational Judgement Test — Customer Service
- Situational Judgement Test — Management
- Entry Level Sales 7.1

### Competency (C)
- Global Skills Assessment (GSA)

---

## Build Log

### Session 1 — Foundation
- [x] Project structure created
- [x] REFERENCE.md written
- [x] Scraper script (scrape_catalog.py)
- [x] Catalog schema defined (37 assessments in catalog.json)
- [x] FastAPI skeleton (main.py, schemas.py)
- [x] Retriever foundation (retriever.py with FAISS + BM25)
- [x] Agent, prompts, guardrails, validator, llm_client
- [x] Requirements.txt, Dockerfile, Railway/Render configs
- [x] Test suite (test_api.py, test_retriever.py)
- [x] 5 sample conversation traces

### Session 2 — Bug Fixes (Assignment Spec Alignment)
- [x] Bug 1: HARD/SOFT off-topic split in guardrails.py (salary+role bypass fixed)
- [x] Bug 2: skills extraction fixed in retriever.py extract_constraints()
- [x] Bug 3: turn count fixed to count user messages only
- [x] Bug 4: end_of_conversation=True set on shortlist commit
- [x] Bug 5: turn cap now returns graceful MAX_TURNS_REPLY + end_of_conversation=True
- [x] Bug 6: Gemini updated from gemini-1.5-flash to gemini-2.0-flash
- [x] Skills-based score boost added to _apply_metadata_filters()
- [x] KNOWN_ASSESSMENT_NAMES in agent.py updated to match all 37 catalog items
- [x] prompts.py: explicit names list in recommendation prompt (anti-hallucination)
- [x] prompts.py: MAX_TURNS_REPLY added
- [x] Sample traces expanded from 5 to 10 (all key personas covered)
- [x] New test file: test_guardrails.py (28 unit tests, 28/28 passing, no LLM needed)

### Session 3 — Performance & Quality Improvements
- [x] Fix 1: Pre-warm embedding model at startup (22s → ~3s first request)
- [x] Fix 2: retrieve() now returns normalized _score (0.0–1.0) on each item
- [x] Fix 3: schemas.py — optional `reason` and `score` fields on Recommendation
- [x] Fix 4: validator.py — passes through `reason` and `score` fields
- [x] Fix 5: extract_recommendations_from_llm_reply attaches _score from retriever
- [x] Fix 6: recommendation_prompt now asks LLM for explicit reason per assessment
- [x] Fix 7: clarification_prompt now picks single most-important missing signal
- [x] README: added Guardrails section, Hybrid Retrieval diagram, Docker, perf notes
- [ ] Deploy to Railway or Render
- [ ] Run full test_api.py against live endpoint
- [ ] Verify Recall@10 on all 10 traces
- [ ] 2-page approach document (PDF)
- [ ] Final submission

---

## Deployment Notes

### Railway
```bash
railway login
railway init
railway up
```
- Set env vars: GROQ_API_KEY, GEMINI_API_KEY
- Port: $PORT (auto-detected by Railway)
- Health check: /health

### Render
- Connect GitHub repo
- Build command: `pip install -r requirements.txt && python scripts/scrape_catalog.py --use-fallback`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check path: /health

---

## Environment Variables
```
GROQ_API_KEY=          # Primary LLM (Groq, free) — https://console.groq.com
GEMINI_API_KEY=        # Fallback LLM (Google, free) — https://aistudio.google.com
CATALOG_PATH=data/catalog.json
LOG_LEVEL=INFO
```

---

*Last updated: Session 3 — Performance & quality improvements (22s latency fix, scores, reasons, better clarification)*
