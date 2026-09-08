"""
Builds data/catalog.json — the assessment catalog the retriever indexes.

The catalog is vendor-neutral: entries describe standard, widely-used categories
of hiring assessment rather than any one provider's branded products, so the
project can be run and demonstrated without depending on an external vendor.
Swap this file's ASSESSMENTS list to point the agent at a different catalog;
nothing else in the system needs to change.

Run:  python scripts/build_catalog.py
"""

import json
import re
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "catalog.json"

TEST_TYPE_LABELS = {
    "A": "Ability & Aptitude",
    "B": "Biodata & Situational Judgement",
    "C": "Competency Based",
    "D": "Development & 360",
    "K": "Knowledge & Skills",
    "P": "Personality & Behavior",
    "S": "Simulations",
}

ASSESSMENTS = [
    # ── Knowledge & Skills ────────────────────────────────────────────
    {
        "name": "Java Programming Test",
        "description": "Assesses core Java: object-oriented design, collections, exception handling and data structures. Suited to backend and platform engineering roles.",
        "test_type": "K", "duration_minutes": 30,
        "job_levels": ["entry", "junior", "mid", "senior"],
        "skills": ["java", "OOP", "collections", "backend", "programming", "data structures", "algorithms"],
        "tags": ["programming", "java", "backend"],
    },
    {
        "name": "Python Programming Test",
        "description": "Covers Python fundamentals, data structures, scripting and standard library use. Common for backend, data engineering and machine learning roles.",
        "test_type": "K", "duration_minutes": 30,
        "job_levels": ["entry", "junior", "mid", "senior"],
        "skills": ["python", "programming", "scripting", "backend", "data science", "automation"],
        "tags": ["programming", "python", "data"],
    },
    {
        "name": "SQL and Database Test",
        "description": "Evaluates query writing, joins, aggregation, indexing and schema design. Central to data engineering, analytics and backend work.",
        "test_type": "K", "duration_minutes": 25,
        "job_levels": ["entry", "junior", "mid", "senior"],
        "skills": ["sql", "database", "queries", "data engineering", "data analysis", "backend"],
        "tags": ["sql", "data", "database"],
    },
    {
        "name": "JavaScript and Web Development Test",
        "description": "Tests JavaScript language fundamentals, asynchronous behaviour, the DOM and modern front-end patterns.",
        "test_type": "K", "duration_minutes": 30,
        "job_levels": ["entry", "junior", "mid", "senior"],
        "skills": ["javascript", "frontend", "web", "programming", "react"],
        "tags": ["programming", "javascript", "frontend"],
    },
    {
        "name": "C# and .NET Test",
        "description": "Assesses C# language features, object-oriented design and the .NET ecosystem for enterprise backend development.",
        "test_type": "K", "duration_minutes": 30,
        "job_levels": ["junior", "mid", "senior"],
        "skills": ["c#", ".net", "programming", "OOP", "backend", "enterprise"],
        "tags": ["programming", "c#", "backend"],
    },
    {
        "name": "Machine Learning Foundations Test",
        "description": "Covers supervised and unsupervised learning, feature engineering, model evaluation and overfitting. Aimed at machine learning and applied AI roles.",
        "test_type": "K", "duration_minutes": 35,
        "job_levels": ["entry", "junior", "mid", "senior"],
        "skills": ["machine learning", "data science", "model evaluation", "python", "statistics", "ai"],
        "tags": ["machine learning", "ai", "data"],
    },
    {
        "name": "Data Analysis Test",
        "description": "Measures the ability to summarise data, apply descriptive statistics, and draw defensible conclusions from tables and charts.",
        "test_type": "K", "duration_minutes": 30,
        "job_levels": ["entry", "junior", "mid", "senior"],
        "skills": ["data analysis", "statistics", "analytics", "reporting", "data science"],
        "tags": ["data", "analysis", "analytics"],
    },
    {
        "name": "Spreadsheet Skills Test",
        "description": "Assesses formulas, lookups, pivot tables and data cleaning in spreadsheet software, for analyst and operations roles.",
        "test_type": "K", "duration_minutes": 25,
        "job_levels": ["entry", "junior", "mid"],
        "skills": ["excel", "spreadsheets", "formulas", "reporting", "data analysis"],
        "tags": ["excel", "data", "administrative"],
    },
    {
        "name": "Cloud and DevOps Fundamentals Test",
        "description": "Covers containers, CI/CD pipelines, infrastructure as code and basic cloud service models.",
        "test_type": "K", "duration_minutes": 30,
        "job_levels": ["junior", "mid", "senior"],
        "skills": ["devops", "cloud", "ci/cd", "containers", "infrastructure", "programming"],
        "tags": ["devops", "cloud", "infrastructure"],
    },

    # ── Simulations ───────────────────────────────────────────────────
    {
        "name": "Debugging Simulation",
        "description": "Candidates are given failing code and must diagnose and repair it under time pressure. Measures real debugging and problem solving rather than recall.",
        "test_type": "S", "duration_minutes": 45,
        "job_levels": ["entry", "junior", "mid", "senior"],
        "skills": ["debugging", "programming", "problem solving", "code review", "algorithms"],
        "tags": ["coding", "simulation", "debugging"],
    },
    {
        "name": "Algorithmic Coding Challenge",
        "description": "A timed coding exercise covering algorithms, data structures and complexity trade-offs, scored on correctness and efficiency.",
        "test_type": "S", "duration_minutes": 60,
        "job_levels": ["entry", "junior", "mid", "senior"],
        "skills": ["algorithms", "data structures", "coding", "programming", "problem solving"],
        "tags": ["coding", "simulation", "algorithms"],
    },
    {
        "name": "Data Pipeline Exercise",
        "description": "A practical task building a small extract-transform-load flow, covering data modelling, validation and error handling.",
        "test_type": "S", "duration_minutes": 50,
        "job_levels": ["junior", "mid", "senior"],
        "skills": ["data engineering", "etl", "sql", "python", "data pipeline", "problem solving"],
        "tags": ["data", "simulation", "engineering"],
    },
    {
        "name": "Customer Support Simulation",
        "description": "A role-play style exercise measuring multitasking, written communication and issue resolution in a support setting.",
        "test_type": "S", "duration_minutes": 40,
        "job_levels": ["entry", "junior"],
        "skills": ["customer service", "communication", "multitasking", "problem solving"],
        "tags": ["simulation", "customer", "support"],
    },

    # ── Ability & Aptitude ────────────────────────────────────────────
    {
        "name": "Graduate Aptitude Battery",
        "description": "A combined verbal, numerical and inductive reasoning battery designed for campus and graduate hiring where candidates have little work history.",
        "test_type": "A", "duration_minutes": 45,
        "job_levels": ["graduate", "entry"],
        "skills": ["verbal reasoning", "numerical reasoning", "inductive reasoning", "cognitive ability", "aptitude", "graduate"],
        "tags": ["graduate", "aptitude", "campus"],
    },
    {
        "name": "General Cognitive Ability Test",
        "description": "A short general mental ability measure combining numerical, verbal and logical items. A broad predictor across role types.",
        "test_type": "A", "duration_minutes": 30,
        "job_levels": ["entry", "junior", "mid", "graduate"],
        "skills": ["cognitive ability", "reasoning", "aptitude", "problem solving"],
        "tags": ["aptitude", "cognitive", "general"],
    },
    {
        "name": "Numerical Reasoning Test",
        "description": "Measures interpretation of tables, charts and ratios, and the ability to reason with quantitative information.",
        "test_type": "A", "duration_minutes": 25,
        "job_levels": ["graduate", "junior", "mid", "senior"],
        "skills": ["numerical", "quantitative", "statistics", "data analysis", "reasoning"],
        "tags": ["numerical", "aptitude", "reasoning"],
    },
    {
        "name": "Verbal Reasoning Test",
        "description": "Assesses comprehension of written passages and the ability to evaluate arguments and draw valid conclusions.",
        "test_type": "A", "duration_minutes": 25,
        "job_levels": ["graduate", "junior", "mid", "senior"],
        "skills": ["verbal", "reading", "comprehension", "communication", "reasoning"],
        "tags": ["verbal", "aptitude", "reasoning"],
    },
    {
        "name": "Logical Reasoning Test",
        "description": "Measures pattern recognition and rule inference from abstract sequences, independent of language or domain knowledge.",
        "test_type": "A", "duration_minutes": 25,
        "job_levels": ["graduate", "entry", "junior", "mid"],
        "skills": ["inductive reasoning", "logic", "pattern recognition", "problem solving", "aptitude"],
        "tags": ["logical", "aptitude", "reasoning"],
    },
    {
        "name": "Technology Aptitude Test",
        "description": "Combines logical reasoning with technical problem solving, aimed at screening candidates for engineering and IT roles.",
        "test_type": "A", "duration_minutes": 35,
        "job_levels": ["entry", "junior", "mid", "graduate"],
        "skills": ["technology", "programming", "problem solving", "cognitive ability", "software development"],
        "tags": ["technology", "aptitude", "engineering"],
    },
    {
        "name": "Reading Comprehension Test",
        "description": "Assesses accurate understanding of workplace documents and instructions.",
        "test_type": "A", "duration_minutes": 20,
        "job_levels": ["entry", "junior", "mid"],
        "skills": ["reading", "comprehension", "verbal", "communication"],
        "tags": ["reading", "verbal", "aptitude"],
    },

    # ── Personality & Behaviour ───────────────────────────────────────
    {
        "name": "Work Personality Questionnaire",
        "description": "A broad work-relevant personality measure covering how a candidate approaches tasks, people and pressure.",
        "test_type": "P", "duration_minutes": 25,
        "job_levels": ["entry", "junior", "mid", "senior", "manager", "graduate"],
        "skills": ["personality", "behavior", "teamwork", "communication", "work style"],
        "tags": ["personality", "behavior", "general"],
    },
    {
        "name": "Team Collaboration Styles Questionnaire",
        "description": "Profiles how someone works with others: communication preferences, handling disagreement, and working with stakeholders.",
        "test_type": "P", "duration_minutes": 20,
        "job_levels": ["entry", "junior", "mid", "senior"],
        "skills": ["teamwork", "communication", "collaboration", "stakeholder", "interpersonal"],
        "tags": ["personality", "teamwork", "communication"],
    },
    {
        "name": "Remote Work Readiness Questionnaire",
        "description": "Assesses self-management, written communication and autonomy for distributed and hybrid teams.",
        "test_type": "P", "duration_minutes": 15,
        "job_levels": ["entry", "junior", "mid", "senior"],
        "skills": ["remote", "self management", "communication", "autonomy", "personality"],
        "tags": ["personality", "remote", "work style"],
    },
    {
        "name": "Motivation and Drivers Questionnaire",
        "description": "Identifies what energises or drains a candidate at work, useful for retention and role fit decisions.",
        "test_type": "P", "duration_minutes": 20,
        "job_levels": ["junior", "mid", "senior", "manager"],
        "skills": ["motivation", "engagement", "personality", "work style"],
        "tags": ["personality", "motivation"],
    },
    {
        "name": "Dependability and Safety Inventory",
        "description": "Measures reliability, rule-following and safety awareness for operational and field roles.",
        "test_type": "P", "duration_minutes": 20,
        "job_levels": ["entry", "junior"],
        "skills": ["dependability", "safety", "reliability", "personality"],
        "tags": ["personality", "safety", "entry"],
    },
    {
        "name": "Leadership Potential Report",
        "description": "Assesses people leadership, strategic thinking and decision making for management and senior roles.",
        "test_type": "P", "duration_minutes": 30,
        "job_levels": ["manager", "senior", "executive"],
        "skills": ["leadership", "management", "strategy", "decision making"],
        "tags": ["leadership", "management", "senior"],
    },

    # ── Situational Judgement ─────────────────────────────────────────
    {
        "name": "Situational Judgement: Customer Service",
        "description": "Presents realistic customer scenarios and scores the judgement shown in choosing a response.",
        "test_type": "B", "duration_minutes": 25,
        "job_levels": ["entry", "junior"],
        "skills": ["customer service", "judgement", "communication", "situational"],
        "tags": ["situational", "customer", "entry"],
    },
    {
        "name": "Situational Judgement: Management",
        "description": "Scenario-based measure of people management decisions, prioritisation and handling conflict.",
        "test_type": "B", "duration_minutes": 30,
        "job_levels": ["manager", "senior", "executive"],
        "skills": ["management", "leadership", "judgement", "conflict", "situational"],
        "tags": ["situational", "management", "senior"],
    },
    {
        "name": "Sales Aptitude Assessment",
        "description": "Combines behavioural and situational items covering persuasion, resilience and customer orientation for early-career sales roles.",
        "test_type": "B", "duration_minutes": 25,
        "job_levels": ["entry", "junior"],
        "skills": ["sales", "persuasion", "resilience", "customer orientation", "communication"],
        "tags": ["sales", "situational", "entry"],
    },

    # ── Competency & Development ──────────────────────────────────────
    {
        "name": "Global Competency Assessment",
        "description": "Evaluates cross-cultural working, adaptability and communication for international and distributed teams.",
        "test_type": "C", "duration_minutes": 35,
        "job_levels": ["mid", "senior", "manager", "executive"],
        "skills": ["global mindset", "adaptability", "cultural agility", "communication", "leadership"],
        "tags": ["competency", "global", "leadership"],
    },
    {
        "name": "360 Development Review",
        "description": "Collects structured feedback from peers, reports and managers to support development planning.",
        "test_type": "D", "duration_minutes": 40,
        "job_levels": ["mid", "senior", "manager", "executive"],
        "skills": ["development", "feedback", "leadership", "self awareness"],
        "tags": ["development", "360", "feedback"],
    },
]


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def build() -> list:
    catalog = []
    for item in ASSESSMENTS:
        entry = dict(item)
        entry["id"] = slugify(item["name"])
        entry["url"] = ""
        entry["remote_testing"] = True
        entry["adaptive_irt"] = False
        entry["languages"] = ["English"]
        entry["categories"] = list(item.get("tags", []))
        # search_text is what BM25 tokenizes and FAISS embeds.
        entry["search_text"] = " ".join([
            item["name"],
            item["description"],
            " ".join(item.get("skills", [])),
            " ".join(item.get("tags", [])),
            " ".join(item.get("job_levels", [])),
            TEST_TYPE_LABELS.get(item["test_type"], ""),
        ])
        catalog.append(entry)
    return catalog


def main():
    catalog = build()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(catalog)} assessments to {OUTPUT_PATH}")
    by_type = {}
    for a in catalog:
        by_type[a["test_type"]] = by_type.get(a["test_type"], 0) + 1
    print("By test type:", dict(sorted(by_type.items())))


if __name__ == "__main__":
    main()
