"""
Hybrid Retriever — Semantic (FAISS) + Keyword (BM25) + Metadata filters.

Strategy:
  1. BM25 keyword retrieval  → top-k candidates
  2. FAISS semantic retrieval → top-k candidates
  3. Union + RRF (Reciprocal Rank Fusion) reranking
  4. Metadata post-filter (duration, remote, job_level, test_type) + boost
  5. Return top-N (1–10) results
"""

import re
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from loguru import logger

# Lazy imports to reduce cold-start time
_sentence_model = None
_faiss_index = None
_bm25 = None
_catalog_items: List[Dict] = []

INDEX_PATH = Path(__file__).parent.parent / "data" / "faiss_index.pkl"
BM25_PATH  = Path(__file__).parent.parent / "data" / "bm25_index.pkl"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"


# ──────────────────────────────────────────────────────────────────
# Tokenizer
# ──────────────────────────────────────────────────────────────────

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "from", "is", "was", "are", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "can", "need",
    "i", "we", "you", "they", "he", "she", "it", "this", "that",
    "want", "looking", "hiring", "find", "get", "test", "assessment",
    "someone", "who", "what", "which", "some", "our", "their",
}


def tokenize(text: str) -> List[str]:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = text.split()
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


# ──────────────────────────────────────────────────────────────────
# Build / load indexes
# ──────────────────────────────────────────────────────────────────

def _get_sentence_model():
    global _sentence_model
    if _sentence_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        _sentence_model = SentenceTransformer(EMBEDDING_MODEL)
    return _sentence_model


def build_indexes(catalog: List[Dict]) -> None:
    """Build FAISS + BM25 indexes from catalog. Called once at startup."""
    global _faiss_index, _bm25, _catalog_items
    import faiss
    from rank_bm25 import BM25Okapi

    _catalog_items = catalog
    logger.info(f"Building indexes for {len(catalog)} assessments...")

    # BM25
    corpus = [tokenize(item.get("search_text", "")) for item in catalog]
    _bm25 = BM25Okapi(corpus)
    logger.info("BM25 index built.")

    # FAISS
    model = _get_sentence_model()
    texts = [item.get("search_text", item.get("name", "")) for item in catalog]
    logger.info("Computing embeddings...")
    embeddings = model.encode(texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
    embeddings = np.array(embeddings, dtype=np.float32)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner product = cosine similarity (normalized vecs)
    index.add(embeddings)
    _faiss_index = index
    logger.info(f"FAISS index built: {index.ntotal} vectors, dim={dim}")

    # Save to disk for fast reload
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_PATH, "wb") as f:
        pickle.dump({"index": faiss.serialize_index(index), "catalog": catalog}, f)
    with open(BM25_PATH, "wb") as f:
        pickle.dump({"bm25": _bm25, "corpus": corpus}, f)
    logger.info("Indexes saved to disk.")


def load_indexes(catalog: List[Dict]) -> bool:
    """Load pre-built indexes from disk. Returns True if successful."""
    global _faiss_index, _bm25, _catalog_items
    import faiss
    try:
        if INDEX_PATH.exists() and BM25_PATH.exists():
            logger.info("Loading pre-built indexes from disk...")
            with open(INDEX_PATH, "rb") as f:
                data = pickle.load(f)
            _faiss_index = faiss.deserialize_index(data["index"])

            with open(BM25_PATH, "rb") as f:
                bm25_data = pickle.load(f)
            _bm25 = bm25_data["bm25"]
            _catalog_items = catalog  # always use latest catalog
            logger.info(f"Indexes loaded: {_faiss_index.ntotal} FAISS vectors.")
            return True
    except Exception as e:
        logger.warning(f"Could not load pre-built indexes: {e}")
    return False


def ensure_indexes(catalog: List[Dict]) -> None:
    """
    Ensure indexes are ready — load or build.
    Also pre-warms the embedding model so the first /chat call is fast.
    Without this, the model loads lazily on the first FAISS query → 20s spike.
    """
    global _catalog_items
    _catalog_items = catalog

    if _faiss_index is None or _bm25 is None:
        if not load_indexes(catalog):
            build_indexes(catalog)

    # Pre-warm: load model now so the first real request doesn't pay the cost
    _get_sentence_model()
    logger.info("Embedding model pre-warmed — ready for fast inference.")


# ──────────────────────────────────────────────────────────────────
# Query expansion
# ──────────────────────────────────────────────────────────────────

SYNONYM_MAP = {
    # Role synonyms
    "dev": "developer",
    "swe": "software engineer",
    "sde": "software developer",
    "qa": "quality assurance testing",
    "pm": "product manager",
    "hr": "human resources",
    "ba": "business analyst",
    "ds": "data scientist",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    # Skill synonyms
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "csharp": "c#",
    "dotnet": ".net",
    # Level synonyms
    "junior": "junior entry level",
    "mid-level": "mid senior",
    "mid level": "mid senior",
    "senior": "senior experienced",
    "entry": "entry junior fresher graduate",
    "fresher": "entry graduate junior",
    "lead": "senior manager lead",
    "exec": "executive director vp",
    # Assessment synonyms
    "personality test": "personality behavior OPQ",
    "aptitude": "cognitive reasoning aptitude ability",
    "coding test": "programming technical simulation automata",
    "soft skills": "personality behavior communication leadership",
    "communication": "verbal communication stakeholder interpersonal",
    "logical": "logical reasoning inductive deductive",
    "math": "numerical mathematics quantitative",
    "english": "verbal language communication reading",
}


def expand_query(query: str) -> str:
    """Expand query with synonyms for better retrieval."""
    expanded = query.lower()
    for term, expansion in SYNONYM_MAP.items():
        if term in expanded:
            expanded = expanded.replace(term, f"{term} {expansion}")
    return expanded


# ──────────────────────────────────────────────────────────────────
# Constraint extraction from conversation
# ──────────────────────────────────────────────────────────────────

# Skills extracted from conversation text and mapped to catalog terms
SKILL_KEYWORDS = {
    "java": ["java", "spring", "spring boot", "jvm"],
    "python": ["python", "django", "flask", "fastapi"],
    "sql": ["sql", "database", "mysql", "postgres", "oracle"],
    "javascript": ["javascript", "js", "react", "node", "typescript", "vue", "angular"],
    "c#": ["c#", "csharp", ".net", "dotnet", "asp.net"],
    "excel": ["excel", "spreadsheet", "vba"],
    "data analysis": ["data analysis", "analytics", "data analyst", "bi", "tableau", "power bi"],
    "machine learning": ["machine learning", "ml", "deep learning", "ai", "nlp", "tensorflow", "pytorch"],
    "leadership": ["leadership", "management", "lead", "manage", "team lead"],
    "sales": ["sales", "selling", "crm", "account"],
    "customer service": ["customer service", "customer support", "contact center", "call center"],
    "communication": ["communication", "stakeholder", "presentation", "interpersonal"],
    "numerical": ["numerical", "quantitative", "statistics", "math", "finance"],
    "verbal": ["verbal", "reading", "writing", "language", "english"],
}


def extract_constraints(messages: List[Dict]) -> Dict:
    """
    Parse conversation history to extract:
    - role / job title
    - seniority level
    - skills / domains  (FIXED: now actually populated)
    - test type preferences
    - duration limit
    - remote requirement
    """
    full_text = " ".join(
        m["content"] for m in messages if m.get("role") == "user"
    ).lower()

    constraints = {
        "role": None,
        "seniority": [],
        "skills": [],          # FIX: was always [] — now populated below
        "test_types": [],
        "max_duration": None,
        "remote_only": False,
        "explicit_assessments": [],
    }

    # Seniority
    seniority_map = {
        "entry": ["entry", "fresher", "0-1 year", "graduate", "intern"],
        "junior": ["junior", "1-3 year", "1-2 year", "2 year"],
        "mid": ["mid", "middle", "3-5 year", "4 year", "5 year", "mid-level"],
        "senior": ["senior", "5+ year", "6+ year", "7+ year", "8+ year", "experienced"],
        "manager": ["manager", "lead", "team lead", "engineering manager"],
        "executive": ["executive", "director", "vp", "c-suite", "cto", "cfo"],
    }
    for level, keywords in seniority_map.items():
        if any(kw in full_text for kw in keywords):
            constraints["seniority"].append(level)

    # Skills — FIX: actually extract and populate
    for skill, keywords in SKILL_KEYWORDS.items():
        if any(kw in full_text for kw in keywords):
            if skill not in constraints["skills"]:
                constraints["skills"].append(skill)

    # Test type preferences
    if any(k in full_text for k in ["personality", "behaviour", "behavior", "opq", "soft skill"]):
        constraints["test_types"].append("P")
    if any(k in full_text for k in ["cognitive", "aptitude", "reasoning", "logical", "numerical", "verbal", "iq"]):
        constraints["test_types"].append("A")
    if any(k in full_text for k in ["coding", "programming", "technical test", "code"]):
        constraints["test_types"].append("K")
        constraints["test_types"].append("S")
    if any(k in full_text for k in ["knowledge", "skills test", "domain"]):
        constraints["test_types"].append("K")
    if any(k in full_text for k in ["situational", "sjt", "scenario"]):
        constraints["test_types"].append("B")
    if any(k in full_text for k in ["simulation", "exercise"]):
        constraints["test_types"].append("S")

    # Duration
    dur_match = re.search(r"(\d+)\s*(min|minute)", full_text)
    if dur_match:
        constraints["max_duration"] = int(dur_match.group(1))

    # Remote
    if "remote" in full_text or "online" in full_text:
        constraints["remote_only"] = True

    return constraints


# ──────────────────────────────────────────────────────────────────
# Core retrieval
# ──────────────────────────────────────────────────────────────────

def _bm25_retrieve(query: str, k: int = 20) -> List[Tuple[int, float]]:
    """BM25 retrieval. Returns list of (catalog_index, score)."""
    if _bm25 is None:
        return []
    tokens = tokenize(expand_query(query))
    if not tokens:
        return []
    scores = _bm25.get_scores(tokens)
    top_k = np.argsort(scores)[::-1][:k]
    return [(int(idx), float(scores[idx])) for idx in top_k if scores[idx] > 0]


def _faiss_retrieve(query: str, k: int = 20) -> List[Tuple[int, float]]:
    """FAISS semantic retrieval. Returns list of (catalog_index, score)."""
    if _faiss_index is None:
        return []
    model = _get_sentence_model()
    query_expanded = expand_query(query)
    emb = model.encode([query_expanded], normalize_embeddings=True)
    emb = np.array(emb, dtype=np.float32)
    scores, indices = _faiss_index.search(emb, min(k, _faiss_index.ntotal))
    return [(int(idx), float(score)) for idx, score in zip(indices[0], scores[0]) if idx >= 0]


def _rrf_fuse(
    bm25_results: List[Tuple[int, float]],
    faiss_results: List[Tuple[int, float]],
    k_constant: int = 60,
    bm25_weight: float = 0.4,
    faiss_weight: float = 0.6,
) -> List[Tuple[int, float]]:
    """Reciprocal Rank Fusion of two result lists."""
    scores: Dict[int, float] = {}

    for rank, (idx, _) in enumerate(bm25_results):
        scores[idx] = scores.get(idx, 0) + bm25_weight / (k_constant + rank + 1)

    for rank, (idx, _) in enumerate(faiss_results):
        scores[idx] = scores.get(idx, 0) + faiss_weight / (k_constant + rank + 1)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def _apply_metadata_filters(
    candidates: List[Tuple[int, float]],
    constraints: Dict,
) -> List[Tuple[int, float]]:
    """Apply hard metadata filters + score boosting. Returns filtered + boosted list."""
    if not candidates:
        return candidates

    filtered = []
    for idx, score in candidates:
        item = _catalog_items[idx]

        # Hard filter: remote only
        if constraints.get("remote_only") and not item.get("remote_testing", True):
            continue

        # Hard filter: max duration
        max_dur = constraints.get("max_duration")
        if max_dur and item.get("duration_minutes", 0) > max_dur:
            continue

        # Soft boost: seniority match
        seniority = constraints.get("seniority", [])
        item_levels = item.get("job_levels", [])
        if seniority and item_levels:
            if any(s in item_levels for s in seniority):
                score *= 1.3

        # Soft boost: test type preference match
        pref_types = constraints.get("test_types", [])
        item_type = item.get("test_type", "")
        if pref_types:
            flat_types = []
            for t in pref_types:
                if isinstance(t, (list, tuple)):
                    flat_types.extend(t)
                else:
                    flat_types.append(t)
            if item_type in flat_types:
                score *= 1.25

        # Soft boost: skill match in item tags/skills
        user_skills = constraints.get("skills", [])
        item_skills = [s.lower() for s in item.get("skills", []) + item.get("tags", [])]
        if user_skills and item_skills:
            matches = sum(1 for s in user_skills if any(s in is_ for is_ in item_skills))
            if matches > 0:
                score *= (1.0 + 0.15 * matches)

        filtered.append((idx, score))

    # Re-sort after boosting
    return sorted(filtered, key=lambda x: x[1], reverse=True)


# ──────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────

def retrieve(
    query: str,
    messages: Optional[List[Dict]] = None,
    top_k: int = 10,
    candidate_k: int = 25,
) -> List[Dict]:
    """
    Main retrieval function.
    Returns list of catalog items (dicts) ranked by relevance.
    """
    if not _catalog_items:
        logger.warning("Retriever called before indexes built!")
        return []

    # Extract constraints from conversation
    constraints = extract_constraints(messages or [])

    # Build augmented query — FIX: skills now properly appended
    augmented_query = query
    if constraints["seniority"]:
        augmented_query += " " + " ".join(constraints["seniority"])
    if constraints["skills"]:
        augmented_query += " " + " ".join(constraints["skills"])

    # Retrieve from both engines
    bm25_results  = _bm25_retrieve(augmented_query, k=candidate_k)
    faiss_results = _faiss_retrieve(augmented_query, k=candidate_k)

    # Fuse via RRF
    fused = _rrf_fuse(bm25_results, faiss_results)

    # Filter + boost by metadata
    filtered = _apply_metadata_filters(fused, constraints)

    # Top-k — normalize scores to [0, 1] for confidence display
    top = filtered[:top_k]
    if not top:
        return []

    max_score = top[0][1] if top[0][1] > 0 else 1.0
    result = []
    for idx, score in top:
        if idx < len(_catalog_items):
            item = dict(_catalog_items[idx])  # shallow copy to avoid mutating catalog
            item["_score"] = round(min(score / max_score, 1.0), 3)
            result.append(item)
    return result


def retrieve_for_comparison(names: List[str]) -> List[Dict]:
    """Retrieve specific assessments by name for comparison."""
    results = []
    for name in names:
        from app.catalog_loader import get_by_name
        item = get_by_name(name)
        if item:
            results.append(item)
    return results
