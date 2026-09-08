"""
Guardrails — pre-LLM rule-based checks.
Runs BEFORE any LLM call. Fast, deterministic, no tokens spent.

Returns:
  "ok"          → proceed normally
  "vague"       → need clarification
  "off_topic"   → refuse
  "injection"   → refuse (prompt injection attempt)
  "comparison"  → comparison request detected
  "refinement"  → user is refining previous recommendation
"""

import re
from typing import List, Dict, Tuple

# ──────────────────────────────────────────────────────────────────
# Pattern lists
# ──────────────────────────────────────────────────────────────────

INJECTION_PATTERNS = [
    r"ignore.{0,20}(instructions?|prompts?|rules?|guidelines?)",
    r"forget.{0,20}(instructions?|everything|all your)",
    r"you are now",
    r"act as (a |an )?(different|new|another|unrestricted|evil|helpful|jailbreak)",
    r"pretend (you|to be)",
    r"jailbreak",
    r"\bDAN\b",
    r"override (your )?(instructions?|safety|rules?|filters?)",
    r"system prompt",
    r"disregard (your )?(previous|prior|all)",
    r"new (persona|personality|role|character)",
    r"(reveal|show|print|output|expose) (your )?(system |initial |full )?(prompt|instructions?)",
    r"from now on (you are|act|respond|behave)",
    r"(stop|don't) being (an? )?(AI|assistant|chatbot)",
    r"hypothetically (if you were|speaking|say|assume)",
    r"what would you say if (you had no|there were no) (restrictions?|rules?|guidelines?)",
]

# HARD_OFF_TOPIC_PATTERNS — always refuse, no role/skill bypass.
# Salary, legal, HR actions, and other universally non-assessment topics
# must be refused even when the message contains role or skill keywords
# (e.g. "what salary for a finance manager?" hits finance+manager but is
# still off-topic and must be blocked).
HARD_OFF_TOPIC_PATTERNS = [
    # Finance / negotiation
    r"\bsalar(y|ies)\b", r"\bnegotiat(e|ion)\b", r"\bcompensation\b",
    # Legal
    r"\blawsuit\b", r"\blegal advice\b", r"\bsue\b", r"\bliabilit(y|ies)\b",
    r"\bdiscriminat(e|ion)\b", r"\bwrongful termination\b",
    # HR actions
    r"\bfire (an? )?(employee|person|worker)\b", r"\bterminate (an? )?(employee|contract)\b",
    # Completely unrelated
    r"\bweather\b", r"\brecipe(s)?\b", r"\bjoke(s)?\b",
    r"\bpolitics\b", r"\breligion\b",
]

# SOFT_OFF_TOPIC_PATTERNS — refuse only when message has NO assessment context.
# e.g. "write code" alone → off-topic; "write a coding test for Python developer" → OK.
SOFT_OFF_TOPIC_PATTERNS = [
    r"\bgames?\b",
    r"\bwrite (an? )?(poem|story|essay|song|code)\b",
    r"\bwhat is (the )?(meaning|purpose) of life\b",
    # Competitor products / AI (no bypass — they're never assessment-related)
    r"\b(hirequest|hackerrank|codility|testgorilla|criteria corp|wonderlic)\b",
    # Personal advice
    r"\bmy relationship\b", r"\bmy personal\b",
    # Competitor AI
    r"\b(chatgpt|gpt-4|gpt4|openai|gemini|claude)\b",
]

COMPARISON_PATTERNS = [
    r"\b(difference|differ(ence)?|vs|versus|compare|comparison|contrast)\b",
    r"(which is better|how do .+ differ|what.?s the difference between)",
    r"\bboth\b.{0,30}\b(test|assessment)\b",
    r"(OPQ|MQ|GSA|SJT|Verify|Automata).{0,30}(vs|versus|or|compared to|difference)",
]

REFINEMENT_PATTERNS = [
    r"\b(also|add|include|plus|additionally|and also)\b.{0,30}(test|assessment|personalit|cogniti)",
    r"\b(instead|rather|change|switch|replace|update|modify)\b",
    r"\bactually\b",
    r"\bmore (focused|specific|narrow|relevant)\b",
    r"\b(remove|exclude|without|not?)\b.{0,30}(test|assessment)",
    r"\b(only|just)\b.{0,30}(personality|cognitive|technical|knowledge)\b",
    r"(what about|how about).{0,30}(adding|including|with)",
]

# What makes a query have "enough context" to recommend
HAS_ROLE_PATTERNS = [
    # Trailing "s?" so plurals match; "engineering" needs its own entry because
    # \bengineer\b does not match it.
    r"\b(developer|engineer|engineering|programmer|coder|manager|analyst|designer|"
    r"sales|marketing|hr|recruiter|accountant|finance|operations|admin|support|"
    r"executive|director|lead|architect|scientist|researcher|consultant|specialist|"
    r"coordinator|associate|officer|technician|tester)s?\b",
    r"\b(sde|swe|sdet|devops|qa)\b",
    r"\b(hiring|recruit(ing)?|screen(ing)?|assess(ing)?|evaluat(ing)?)\b.{0,30}\b(for|a|an)\b",
]

HAS_SENIORITY_PATTERNS = [
    r"\b(entry|junior|mid(-level)?|senior|lead|manager|executive|director|"
    r"graduate|fresher|intern|experienced|\d+\s*year)\b",
]

HAS_SKILL_PATTERNS = [
    r"\b(java|python|sql|javascript|c#|excel|data|analytics?|leadership|"
    r"sales|customer|communication|coding|programming|technical|cognitive|"
    r"personality|verbal|numerical|reasoning|management|finance|banking|"
    r"ml|ai|algorithms?|dsa|debugging|backend|frontend|software|"
    r"problem[ -]solving|aptitude)\b",
]

JOB_DESCRIPTION_PATTERNS = [
    r"\bjob description\b", r"\bJD\b", r"\brole description\b",
    r"responsibilities include", r"requirements?:", r"qualifications?:",
]


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

def _matches_any(text: str, patterns: List[str]) -> bool:
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in patterns)


def _last_user_message(messages: List[Dict]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content", "")
    return ""


def _all_user_text(messages: List[Dict]) -> str:
    return " ".join(m.get("content", "") for m in messages if m.get("role") == "user")


def _conversation_turn_count(messages: List[Dict]) -> int:
    """
    Count conversation turns (user+assistant pairs), not raw message count.
    A 'turn' = one user message + optional assistant reply.
    FIX: was counting raw messages; now counts user messages as turn proxy.
    """
    return sum(1 for m in messages if m.get("role") == "user")


def _has_prior_recommendations(messages: List[Dict]) -> bool:
    for m in messages:
        if m.get("role") == "assistant":
            content = m.get("content", "").lower()
            if any(kw in content for kw in ["recommend", "suggest", "here are", "assessment"]):
                return True
    return False


# ──────────────────────────────────────────────────────────────────
# Signal scoring for "enough context"
# ──────────────────────────────────────────────────────────────────

def _context_signal_score(messages: List[Dict]) -> Tuple[int, Dict]:
    """
    Score 0-4 representing how much hiring context we have.
    0 = nothing, 1 = partial, 2 = enough to recommend, 3+ = very detailed.
    """
    all_text = _all_user_text(messages)
    signals = {
        "has_role": _matches_any(all_text, HAS_ROLE_PATTERNS),
        "has_seniority": _matches_any(all_text, HAS_SENIORITY_PATTERNS),
        "has_skill": _matches_any(all_text, HAS_SKILL_PATTERNS),
        "has_jd": _matches_any(all_text, JOB_DESCRIPTION_PATTERNS),
    }
    score = sum(signals.values())
    return score, signals


# ──────────────────────────────────────────────────────────────────
# Public classifier
# ──────────────────────────────────────────────────────────────────

def classify(messages: List[Dict]) -> Dict:
    """
    Classify the conversation state.
    Returns dict with keys:
      - intent: "ok" | "vague" | "off_topic" | "injection" | "comparison" | "refinement"
      - reason: str (human-readable reason)
      - context_score: int (0–4)
      - signals: dict of detected signals
      - last_user_msg: str
      - has_prior_recommendations: bool
    """
    last_msg = _last_user_message(messages)
    context_score, signals = _context_signal_score(messages)
    has_prior = _has_prior_recommendations(messages)
    turns = _conversation_turn_count(messages)

    result = {
        "last_user_msg": last_msg,
        "context_score": context_score,
        "signals": signals,
        "has_prior_recommendations": has_prior,
        "turn_count": turns,
    }

    # 1. Injection check (highest priority)
    if _matches_any(last_msg, INJECTION_PATTERNS):
        return {**result, "intent": "injection", "reason": "Prompt injection attempt detected."}

    # 2. Off-topic check
    # HARD: always refuse — no role/skill bypass. Salary, legal, HR actions, etc.
    # must be refused even when the message contains role/skill keywords.
    if _matches_any(last_msg, HARD_OFF_TOPIC_PATTERNS):
        return {**result, "intent": "off_topic", "reason": "Query is not about talent assessments."}

    # SOFT: refuse only if message has no assessment-related context.
    if _matches_any(last_msg, SOFT_OFF_TOPIC_PATTERNS):
        if not _matches_any(last_msg, HAS_ROLE_PATTERNS + HAS_SKILL_PATTERNS):
            return {**result, "intent": "off_topic", "reason": "Query is not about talent assessments."}

    # 3. Comparison check
    if _matches_any(last_msg, COMPARISON_PATTERNS):
        return {**result, "intent": "comparison", "reason": "User is asking for a comparison."}

    # 4. Refinement check (must have prior recommendations)
    if has_prior and _matches_any(last_msg, REFINEMENT_PATTERNS):
        return {**result, "intent": "refinement", "reason": "User is refining previous recommendations."}

    # 5. Context check — do we have enough to recommend?
    # JD alone is always enough
    if signals.get("has_jd"):
        return {**result, "intent": "ok", "reason": "Job description provided."}

    # Role + at least one other signal (seniority or skill) → recommend
    if signals.get("has_role") and (signals.get("has_seniority") or signals.get("has_skill")):
        return {**result, "intent": "ok", "reason": "Sufficient context to recommend."}

    # General score-based threshold
    if context_score >= 2:
        return {**result, "intent": "ok", "reason": "Sufficient context to recommend."}

    # On turn 1 with very minimal info, always clarify
    if turns <= 1:
        return {**result, "intent": "vague", "reason": "First message — insufficient context."}

    # After 4+ turns, proceed with what we have rather than keep asking
    if turns >= 4 and context_score >= 1:
        return {**result, "intent": "ok", "reason": "Enough turns — proceeding with available context."}

    # Still vague
    return {**result, "intent": "vague", "reason": "Insufficient context to recommend."}


def is_end_of_conversation(messages: List[Dict], reply: str) -> bool:
    """
    Detect if conversation should be marked complete.
    True when:
    - User says thanks/done after recommendations were given, OR
    - Agent just committed to a shortlist and user acknowledged positively.
    """
    last_msg = _last_user_message(messages).lower()

    thanks_patterns = [
        r"\b(thank(s| you)|that.?s (all|it|perfect|great)|perfect|great|no (more|other)|done|bye)\b"
    ]
    if _matches_any(last_msg, thanks_patterns):
        return True

    # Agent just gave recommendations and user acknowledged
    reply_has_recs = _matches_any(
        reply.lower(),
        [r"\b(here are|here is|recommended|these assessments|shortlist)\b"]
    )
    user_acknowledged = _matches_any(
        last_msg,
        [r"\b(ok|okay|sure|sounds good|looks good|perfect|great|that.?s (it|all))\b"]
    )
    if reply_has_recs and user_acknowledged:
        return True

    return False
