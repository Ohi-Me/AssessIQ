"""
All LLM prompt templates.
Keep prompts tight — we're under a 30-second response budget.
"""

from typing import List, Dict

TEST_TYPE_LABELS = {
    "A": "Ability & Aptitude",
    "B": "Biodata & Situational Judgement",
    "C": "Competency Based",
    "D": "Development & 360",
    "E": "Assessment Exercises",
    "K": "Knowledge & Skills",
    "P": "Personality & Behavior",
    "S": "Simulations",
}

# ──────────────────────────────────────────────────────────────────
# System prompt (shared base)
# ──────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a talent assessment recommendation assistant. Your job is to help hiring managers and recruiters find the right assessments from the product catalog you are given.

STRICT RULES — follow these without exception:
1. Only recommend assessments from the catalog provided to you. Never invent or hallucinate assessment names or URLs.
2. Only discuss assessments from that catalog. Refuse general hiring advice, legal questions, salary questions, and off-topic requests politely.
3. Clarify vague queries before recommending. Do not recommend on the first message if the user hasn't provided a role and at least one other signal (seniority, skills, or test type preference).
4. Never recommend more than 10 assessments in a single response.
5. Keep responses concise and professional.
6. When recommending, always mention the assessment name exactly as it appears in the catalog provided.

Your response tone: professional, helpful, efficient. No fluff.
"""

# ──────────────────────────────────────────────────────────────────
# Static reply constants
# ──────────────────────────────────────────────────────────────────

OFF_TOPIC_REFUSAL = """I'm specialized in helping you find the right assessments for your hiring needs. I can't help with that particular question.

If you're looking for assessments to evaluate candidates — whether cognitive, personality, technical skills, or situational judgment — I'd be happy to help. What role are you hiring for?"""

INJECTION_REFUSAL = """I'm here to help you find assessments for your hiring needs. I can't process that type of request.

Is there a specific role or skill set you'd like to assess? I can recommend assessments from the catalog."""

MAX_TURNS_REPLY = """We've reached the end of our conversation session. I hope I was able to help you find the right assessments for your needs. Please start a new conversation if you have further questions."""


# ──────────────────────────────────────────────────────────────────
# Clarification prompt
# ──────────────────────────────────────────────────────────────────

def clarification_prompt(messages: List[Dict], signals: Dict) -> str:
    # Prioritize the single most important missing signal
    if not signals.get("has_role"):
        focus = "what role or position they are hiring for (e.g., Java Developer, Sales Manager, Data Analyst)"
        example = "e.g. 'What role are you assessing candidates for?'"

    elif not signals.get("has_seniority"):
        focus = "the seniority or experience level (entry, junior, mid-level, senior, manager, or executive)"
        example = "e.g. 'What seniority level is this role - entry, mid-level, or senior?'"

    elif not signals.get("has_skill"):
        focus = "the key skills or competencies to assess (technical skills, personality/behavior, leadership, cognitive reasoning, or situational judgement)"
        example = "e.g. 'Should I focus on technical skills, behavioral traits, or a mix of both?'"

    else:
        focus = "any additional requirements such as test duration limits or remote-testing preference"
        example = "e.g. 'Do you have any constraints on test duration or format?'"

    history = _format_history(messages)
    return f"""{SYSTEM_PROMPT}

Conversation so far:
{history}

The user's request needs one more piece of information: {focus}.

Ask ONE clear, specific question to get this. Be warm and efficient.
Good question format: {example}
Do NOT list multiple questions. Do NOT recommend anything yet.
"""


# ──────────────────────────────────────────────────────────────────
# Recommendation prompt
# ──────────────────────────────────────────────────────────────────

def recommendation_prompt(messages: List[Dict], retrieved_docs: List[Dict]) -> str:
    history = _format_history(messages)
    catalog_context = _format_catalog_docs(retrieved_docs)

    # Extract assessment names for explicit mention instruction
    names_list = "\n".join(f"- {doc['name']}" for doc in retrieved_docs)

    return f"""{SYSTEM_PROMPT}

Conversation so far:
{history}

AVAILABLE ASSESSMENTS FROM THE CATALOG (use ONLY these — do NOT invent others):
{catalog_context}

ASSESSMENT NAMES YOU MAY RECOMMEND (copy exactly as shown):
{names_list}

Based on the conversation, select the 1–10 most relevant assessments from the list above.

IMPORTANT OUTPUT FORMAT:
- Write your reply in natural prose (not a bullet list).
- Mention each chosen assessment by its EXACT name as shown above.
- For each, give ONE specific sentence explaining why it fits this role/seniority/skill.
  Example: "Java 8 (New) evaluates OOP, collections, and backend Java fundamentals — ideal for mid-level developers."
- Do NOT add URLs in your text — URLs are added automatically by the system.
- End with a brief offer to refine or compare.
- Keep under 250 words.
"""


# ──────────────────────────────────────────────────────────────────
# Refinement prompt
# ──────────────────────────────────────────────────────────────────

def refinement_prompt(messages: List[Dict], retrieved_docs: List[Dict]) -> str:
    history = _format_history(messages)
    catalog_context = _format_catalog_docs(retrieved_docs)
    names_list = "\n".join(f"- {doc['name']}" for doc in retrieved_docs)

    return f"""{SYSTEM_PROMPT}

Conversation so far:
{history}

AVAILABLE ASSESSMENTS FROM THE CATALOG (use ONLY these):
{catalog_context}

ASSESSMENT NAMES YOU MAY RECOMMEND (copy exactly as shown):
{names_list}

The user is refining their previous request. Update the shortlist while:
1. Preserving any constraints from earlier in the conversation.
2. Adding or removing assessments based on the new request.
3. Do NOT start over — build on what was already established.

Mention each chosen assessment by its EXACT name. No URLs in text. Keep under 150 words.
"""


# ──────────────────────────────────────────────────────────────────
# Comparison prompt
# ──────────────────────────────────────────────────────────────────

def comparison_prompt(messages: List[Dict], comparison_items: List[Dict]) -> str:
    history = _format_history(messages)

    if not comparison_items:
        return f"""{SYSTEM_PROMPT}

Conversation so far:
{history}

The user asked for a comparison but the specific assessments could not be identified in the catalog.
Politely ask which specific assessments they'd like to compare, and list a few examples from the catalog.
"""

    items_text = "\n\n".join([
        f"**{item['name']}** (Type: {TEST_TYPE_LABELS.get(item.get('test_type', 'A'), item.get('test_type', 'A'))})\n"
        f"Description: {item.get('description', 'No description available.')}\n"
        f"Duration: {item.get('duration_minutes', 'N/A')} minutes\n"
        f"Suitable for: {', '.join(item.get('job_levels', ['all levels']))}\n"
        f"Measures: {', '.join(item.get('skills', []))}"
        for item in comparison_items
    ])

    return f"""{SYSTEM_PROMPT}

Conversation so far:
{history}

ASSESSMENTS TO COMPARE (from the catalog only — do NOT use outside knowledge):
{items_text}

Compare these assessments based ONLY on the information above. Do NOT add information from your general knowledge.
Structure your comparison as:
1. What each measures (1-2 sentences each)
2. Key differences
3. When to use each

Keep under 250 words. Be factual and grounded in the catalog data only.
"""


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

def _format_history(messages: List[Dict]) -> str:
    lines = []
    for m in messages:
        role = "User" if m.get("role") == "user" else "Assistant"
        content = m.get("content", "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "(no prior conversation)"


def _format_catalog_docs(docs: List[Dict]) -> str:
    if not docs:
        return "(no matching assessments found)"
    lines = []
    for i, doc in enumerate(docs, 1):
        name = doc.get("name", "Unknown")
        desc = doc.get("description", "No description.")[:200]
        test_type = doc.get("test_type", "A")
        type_label = TEST_TYPE_LABELS.get(test_type, test_type)
        duration = doc.get("duration_minutes", "N/A")
        levels = ", ".join(doc.get("job_levels", ["all levels"])) or "all levels"
        skills = ", ".join(doc.get("skills", [])[:6]) or "various"
        lines.append(
            f"{i}. {name} [{type_label}, {duration} min, levels: {levels}]\n"
            f"   Measures: {skills}\n"
            f"   {desc}"
        )
    return "\n\n".join(lines)
