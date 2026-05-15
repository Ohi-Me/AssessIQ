#!/usr/bin/env python3
"""
SHL Product Catalog Scraper
Scrapes Individual Test Solutions from https://www.shl.com/solutions/products/product-catalog/
Saves to data/catalog.json

Usage:
    python scripts/scrape_catalog.py
    python scripts/scrape_catalog.py --use-playwright  # for JS-heavy pages
"""

import json
import time
import re
import argparse
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────

BASE_URL = "https://www.shl.com"
CATALOG_URL = "https://www.shl.com/solutions/products/product-catalog/"

# type=1 filters for Individual Test Solutions only (not pre-packaged job solutions)
CATALOG_PARAMS = {
    "type": "1",
    "action_doFilteringForm": "Search",
    "f": "1",
    "start": "0",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

PAGE_SIZE = 12  # SHL shows 12 items per page
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "catalog.json"

# Test type code mapping (from SHL documentation)
TEST_TYPE_MAP = {
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
# Fallback catalog — known SHL Individual Test Solutions
# Used when scraping fails / rate-limited
# ──────────────────────────────────────────────────────────────────

FALLBACK_CATALOG = [
    # Cognitive / Ability
    {
        "name": "Verify Numerical Reasoning",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/verify-numerical-reasoning/",
        "description": "Measures ability to make correct decisions or inferences from numerical or statistical data. Suitable for roles requiring data analysis, financial reasoning, and quantitative problem-solving.",
        "test_type": "A",
        "duration_minutes": 17,
        "remote_testing": True,
        "adaptive_irt": True,
        "job_levels": ["graduate", "professional", "manager", "senior"],
        "skills": ["numerical", "data analysis", "statistics", "mathematics", "quantitative"],
        "tags": ["numerical", "cognitive", "reasoning", "aptitude"],
        "languages": ["English", "Hindi", "French", "German", "Spanish"],
        "categories": ["cognitive", "ability"],
    },
    {
        "name": "Verify Verbal Reasoning",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/verify-verbal-reasoning/",
        "description": "Measures ability to understand and evaluate the logic of various kinds of arguments expressed in written form. Essential for roles requiring communication, analysis of written information, and verbal comprehension.",
        "test_type": "A",
        "duration_minutes": 17,
        "remote_testing": True,
        "adaptive_irt": True,
        "job_levels": ["graduate", "professional", "manager", "senior"],
        "skills": ["verbal", "communication", "reading comprehension", "language", "critical thinking"],
        "tags": ["verbal", "cognitive", "reasoning", "aptitude", "communication"],
        "languages": ["English", "French", "German", "Spanish"],
        "categories": ["cognitive", "ability"],
    },
    {
        "name": "Verify Inductive Reasoning",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/verify-inductive-reasoning/",
        "description": "Measures ability to identify rules, patterns, and logical sequences in abstract shapes and figures. Assesses general learning ability and fluid intelligence for a wide range of roles.",
        "test_type": "A",
        "duration_minutes": 25,
        "remote_testing": True,
        "adaptive_irt": True,
        "job_levels": ["graduate", "professional", "manager"],
        "skills": ["logical reasoning", "pattern recognition", "abstract thinking", "problem solving"],
        "tags": ["inductive", "logical", "abstract", "reasoning", "cognitive"],
        "languages": ["English"],
        "categories": ["cognitive", "ability"],
    },
    {
        "name": "Verify Deductive Reasoning",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/verify-deductive-reasoning/",
        "description": "Measures ability to draw logical conclusions from information provided. Tests systematic thinking and the ability to check whether conclusions follow from given premises.",
        "test_type": "A",
        "duration_minutes": 20,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["graduate", "professional", "manager"],
        "skills": ["logical reasoning", "deductive thinking", "analytical", "problem solving"],
        "tags": ["deductive", "logical", "reasoning", "cognitive"],
        "languages": ["English"],
        "categories": ["cognitive", "ability"],
    },
    {
        "name": "Verify Mechanical Comprehension",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/verify-mechanical-comprehension/",
        "description": "Measures understanding of mechanical principles and physical concepts. Suitable for engineering, manufacturing, and technical roles requiring mechanical knowledge.",
        "test_type": "A",
        "duration_minutes": 25,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["entry", "junior", "mid", "senior"],
        "skills": ["mechanical", "engineering", "physics", "technical", "manufacturing"],
        "tags": ["mechanical", "engineering", "technical", "physics"],
        "languages": ["English"],
        "categories": ["cognitive", "ability", "technical"],
    },
    {
        "name": "Verify Spatial Reasoning",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/verify-spatial-reasoning/",
        "description": "Measures ability to mentally manipulate shapes and objects in three dimensions. Important for design, engineering, architecture, and technical roles.",
        "test_type": "A",
        "duration_minutes": 25,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["entry", "junior", "mid"],
        "skills": ["spatial reasoning", "3D thinking", "design", "engineering", "architecture"],
        "tags": ["spatial", "reasoning", "design", "engineering"],
        "languages": ["English"],
        "categories": ["cognitive", "ability"],
    },
    {
        "name": "Verify Reading Comprehension",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/verify-reading-comprehension/",
        "description": "Measures ability to read and understand written information quickly and accurately. Suitable for customer service, administration, and roles requiring document processing.",
        "test_type": "A",
        "duration_minutes": 20,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["entry", "junior", "mid"],
        "skills": ["reading", "comprehension", "language", "administration", "customer service"],
        "tags": ["reading", "comprehension", "verbal", "administrative"],
        "languages": ["English"],
        "categories": ["cognitive", "ability"],
    },
    # Personality & Behavior
    {
        "name": "OPQ32r",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/opq32r/",
        "description": "Occupational Personality Questionnaire. Measures 32 personality characteristics that predict workplace performance. The gold standard for personality assessment in occupational settings. Covers relationships with people, thinking style, and feelings and emotions.",
        "test_type": "P",
        "duration_minutes": 25,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["entry", "junior", "mid", "senior", "manager", "executive", "graduate"],
        "skills": ["personality", "behavior", "leadership", "teamwork", "communication", "emotional intelligence"],
        "tags": ["personality", "OPQ", "behavior", "leadership", "soft skills"],
        "languages": ["English", "Hindi", "French", "German", "Spanish", "Chinese", "Japanese"],
        "categories": ["personality", "behavioral"],
    },
    {
        "name": "OPQ32",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/opq32/",
        "description": "Full version of the Occupational Personality Questionnaire. Comprehensive measure of 32 personality characteristics relevant to workplace behavior and performance. Provides in-depth personality profile for selection, development, and coaching.",
        "test_type": "P",
        "duration_minutes": 35,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["junior", "mid", "senior", "manager", "executive"],
        "skills": ["personality", "behavior", "leadership", "teamwork", "stakeholder management", "strategic thinking"],
        "tags": ["personality", "OPQ", "behavior", "leadership", "management", "comprehensive"],
        "languages": ["English", "French", "German", "Spanish"],
        "categories": ["personality", "behavioral"],
    },
    {
        "name": "Motivational Questionnaire (MQ)",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/motivational-questionnaire-mq/",
        "description": "Measures 18 motivational dimensions that drive performance. Identifies what energizes and motivates a candidate in the workplace. Useful for role fit, engagement, and retention predictions.",
        "test_type": "P",
        "duration_minutes": 25,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["junior", "mid", "senior", "manager", "executive"],
        "skills": ["motivation", "engagement", "values", "culture fit", "retention"],
        "tags": ["motivation", "MQ", "engagement", "values", "retention"],
        "languages": ["English"],
        "categories": ["personality", "behavioral"],
    },
    {
        "name": "RemoteWorkQ",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/remoteworkq/",
        "description": "Assesses personality characteristics important for effective remote working, including self-discipline, digital communication, and ability to work autonomously. Designed for remote and hybrid roles.",
        "test_type": "P",
        "duration_minutes": 10,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["entry", "junior", "mid", "senior"],
        "skills": ["remote work", "self-management", "digital communication", "autonomy", "productivity"],
        "tags": ["remote work", "WFH", "hybrid", "personality", "digital"],
        "languages": ["English"],
        "categories": ["personality", "behavioral"],
    },
    # Situational Judgement
    {
        "name": "Situational Judgement Test — Customer Service",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/situational-judgement-test-customer-service/",
        "description": "Measures judgment in customer service scenarios. Assesses how candidates handle customer interactions, complaints, and service situations. Suitable for frontline and contact center roles.",
        "test_type": "B",
        "duration_minutes": 30,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["entry", "junior"],
        "skills": ["customer service", "communication", "problem solving", "empathy", "conflict resolution"],
        "tags": ["SJT", "customer service", "situational judgement", "frontline"],
        "languages": ["English"],
        "categories": ["behavioral", "situational"],
    },
    {
        "name": "Situational Judgement Test — Management",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/situational-judgement-test-management/",
        "description": "Assesses managerial judgment in realistic workplace scenarios. Measures decision-making, team management, conflict resolution, and leadership effectiveness.",
        "test_type": "B",
        "duration_minutes": 35,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["manager", "senior", "executive"],
        "skills": ["management", "leadership", "decision making", "conflict resolution", "team management"],
        "tags": ["SJT", "management", "leadership", "situational judgement"],
        "languages": ["English"],
        "categories": ["behavioral", "situational", "leadership"],
    },
    # Knowledge & Skills — Technical
    {
        "name": "Java 8 (New)",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/java-8-new/",
        "description": "Tests knowledge of Java 8 programming language including object-oriented programming, streams, lambda expressions, collections, and core Java APIs. Suitable for backend developers and software engineers.",
        "test_type": "K",
        "duration_minutes": 30,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["junior", "mid", "senior"],
        "skills": ["java", "java 8", "OOP", "backend", "programming", "software development", "streams", "lambda"],
        "tags": ["java", "programming", "backend", "OOP", "developer", "software engineer"],
        "languages": ["English"],
        "categories": ["technical", "knowledge", "programming"],
    },
    {
        "name": "Python (New)",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/python-new/",
        "description": "Tests knowledge of Python programming including data structures, functions, OOP, standard library, and common patterns. Suitable for data scientists, backend developers, and automation engineers.",
        "test_type": "K",
        "duration_minutes": 30,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["junior", "mid", "senior"],
        "skills": ["python", "programming", "backend", "data science", "automation", "scripting"],
        "tags": ["python", "programming", "data science", "backend", "developer", "automation"],
        "languages": ["English"],
        "categories": ["technical", "knowledge", "programming"],
    },
    {
        "name": "SQL (New)",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/sql-new/",
        "description": "Tests SQL knowledge including queries, joins, aggregations, subqueries, stored procedures, and database design. Suitable for data analysts, data engineers, and backend developers.",
        "test_type": "K",
        "duration_minutes": 30,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["junior", "mid", "senior"],
        "skills": ["SQL", "database", "queries", "data analysis", "backend", "data engineering"],
        "tags": ["SQL", "database", "data", "analyst", "engineer", "queries"],
        "languages": ["English"],
        "categories": ["technical", "knowledge", "data"],
    },
    {
        "name": "JavaScript (New)",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/javascript-new/",
        "description": "Tests JavaScript knowledge including ES6+, DOM manipulation, async/await, closures, and modern frontend patterns. Suitable for frontend developers and full-stack engineers.",
        "test_type": "K",
        "duration_minutes": 30,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["junior", "mid", "senior"],
        "skills": ["javascript", "frontend", "web development", "ES6", "async", "DOM"],
        "tags": ["javascript", "JS", "frontend", "web", "developer", "full-stack"],
        "languages": ["English"],
        "categories": ["technical", "knowledge", "programming"],
    },
    {
        "name": "C# (New)",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/c-sharp-new/",
        "description": "Tests knowledge of C# language features, .NET framework, OOP principles, LINQ, async programming, and common patterns. Suitable for .NET developers and enterprise software engineers.",
        "test_type": "K",
        "duration_minutes": 30,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["junior", "mid", "senior"],
        "skills": ["C#", ".NET", "programming", "OOP", "enterprise", "LINQ", "backend"],
        "tags": ["C#", ".NET", "dotnet", "programming", "developer", "enterprise"],
        "languages": ["English"],
        "categories": ["technical", "knowledge", "programming"],
    },
    {
        "name": "Microsoft Excel (New)",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/microsoft-excel-new/",
        "description": "Tests Excel proficiency including formulas, pivot tables, data analysis, charts, and macros. Suitable for analysts, finance, operations, and administrative roles.",
        "test_type": "K",
        "duration_minutes": 30,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["entry", "junior", "mid"],
        "skills": ["Excel", "spreadsheets", "data analysis", "finance", "reporting", "formulas"],
        "tags": ["Excel", "Microsoft", "spreadsheet", "data", "finance", "analyst"],
        "languages": ["English"],
        "categories": ["technical", "knowledge", "office"],
    },
    {
        "name": "Core Java",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/core-java/",
        "description": "Tests fundamental Java concepts including OOP, data structures, algorithms, exception handling, threading, and collections. Suitable for entry to mid-level Java developers.",
        "test_type": "K",
        "duration_minutes": 25,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["entry", "junior", "mid"],
        "skills": ["java", "OOP", "programming", "backend", "algorithms", "data structures"],
        "tags": ["java", "core java", "programming", "OOP", "backend"],
        "languages": ["English"],
        "categories": ["technical", "knowledge", "programming"],
    },
    {
        "name": "Data Analysis",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/data-analysis/",
        "description": "Assesses ability to interpret, analyze, and draw conclusions from data using various analytical tools and methods. Covers statistics, data visualization, and business intelligence.",
        "test_type": "K",
        "duration_minutes": 30,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["junior", "mid", "senior"],
        "skills": ["data analysis", "statistics", "BI", "reporting", "analytics", "data science"],
        "tags": ["data", "analysis", "analytics", "statistics", "BI", "reporting"],
        "languages": ["English"],
        "categories": ["technical", "knowledge", "data"],
    },
    {
        "name": "Automata — Fix the Code",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/automata-fix-the-code/",
        "description": "Coding simulation where candidates debug and fix code snippets across multiple programming languages. Tests debugging skills, code comprehension, and problem-solving in realistic scenarios.",
        "test_type": "S",
        "duration_minutes": 45,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["junior", "mid", "senior"],
        "skills": ["debugging", "programming", "problem solving", "code review", "multiple languages"],
        "tags": ["coding", "debugging", "simulation", "programming", "developer"],
        "languages": ["English"],
        "categories": ["technical", "simulation", "programming"],
    },
    {
        "name": "Automata Pro",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/automata-pro/",
        "description": "Advanced coding assessment simulation testing ability to write, debug, and optimize code. Suitable for mid to senior software engineers. Covers algorithms, data structures, and software design patterns.",
        "test_type": "S",
        "duration_minutes": 60,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["mid", "senior"],
        "skills": ["coding", "algorithms", "data structures", "software design", "programming"],
        "tags": ["coding", "programming", "simulation", "algorithms", "senior developer"],
        "languages": ["English"],
        "categories": ["technical", "simulation", "programming"],
    },
    # Leadership & Management
    {
        "name": "Global Skills Assessment (GSA)",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/global-skills-assessment/",
        "description": "Measures 8 global competencies critical for success in international and cross-cultural roles. Assesses adaptability, cultural agility, communication, and global mindset.",
        "test_type": "C",
        "duration_minutes": 30,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["mid", "senior", "manager", "executive"],
        "skills": ["global mindset", "cultural agility", "leadership", "adaptability", "international", "communication"],
        "tags": ["GSA", "global", "leadership", "competency", "international", "cross-cultural"],
        "languages": ["English"],
        "categories": ["competency", "leadership"],
    },
    {
        "name": "Leadership Report",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/leadership-report/",
        "description": "Comprehensive leadership assessment combining personality, motivation, and competency measures. Predicts leadership effectiveness across key dimensions including strategy, execution, and people leadership.",
        "test_type": "P",
        "duration_minutes": 40,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["manager", "senior", "executive"],
        "skills": ["leadership", "strategy", "people management", "decision making", "executive presence"],
        "tags": ["leadership", "executive", "management", "strategy", "report"],
        "languages": ["English"],
        "categories": ["personality", "leadership", "competency"],
    },
    # Simulations
    {
        "name": "Contact Center Simulation",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/contact-center-simulation/",
        "description": "Realistic simulation of contact center work scenarios. Assesses multi-tasking, customer handling, data entry accuracy, and problem-solving in a simulated call center environment.",
        "test_type": "S",
        "duration_minutes": 45,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["entry", "junior"],
        "skills": ["customer service", "multitasking", "data entry", "communication", "problem solving"],
        "tags": ["contact center", "call center", "simulation", "customer service", "frontline"],
        "languages": ["English"],
        "categories": ["simulation", "customer service"],
    },
    {
        "name": "Financial Services Simulation",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/financial-services-simulation/",
        "description": "Simulates financial services work tasks including customer queries, compliance scenarios, and financial product knowledge. Suitable for banking, insurance, and financial advisory roles.",
        "test_type": "S",
        "duration_minutes": 45,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["entry", "junior", "mid"],
        "skills": ["finance", "banking", "compliance", "customer service", "financial products"],
        "tags": ["financial services", "banking", "simulation", "finance", "compliance"],
        "languages": ["English"],
        "categories": ["simulation", "finance"],
    },
    # Biodata & SJT additional
    {
        "name": "Graduate 8.0",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/graduate-8-0/",
        "description": "Comprehensive battery for graduate recruitment including verbal, numerical, and inductive reasoning. Norm-referenced for graduate population. The standard benchmark for graduate hiring.",
        "test_type": "A",
        "duration_minutes": 60,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["graduate", "entry"],
        "skills": ["verbal reasoning", "numerical reasoning", "inductive reasoning", "graduate", "cognitive ability"],
        "tags": ["graduate", "cognitive", "battery", "recruitment", "aptitude"],
        "languages": ["English"],
        "categories": ["cognitive", "ability", "graduate"],
    },
    {
        "name": "Workplace Personality Inventory II",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/workplace-personality-inventory-ii/",
        "description": "Personality inventory measuring 23 work-relevant traits organized into five broad factors. Predicts performance across a wide range of occupations with strong reliability and validity evidence.",
        "test_type": "P",
        "duration_minutes": 30,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["entry", "junior", "mid", "senior"],
        "skills": ["personality", "behavior", "work traits", "performance prediction"],
        "tags": ["personality", "WPI", "work traits", "behavior", "selection"],
        "languages": ["English"],
        "categories": ["personality", "behavioral"],
    },
    {
        "name": "Verbal Reasoning",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/verbal-reasoning/",
        "description": "Classic verbal reasoning test measuring ability to understand written arguments, draw conclusions, and evaluate information presented in text form. Widely used for professional and managerial selection.",
        "test_type": "A",
        "duration_minutes": 19,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["graduate", "junior", "mid", "professional"],
        "skills": ["verbal reasoning", "communication", "critical thinking", "reading", "language"],
        "tags": ["verbal", "reasoning", "cognitive", "aptitude"],
        "languages": ["English"],
        "categories": ["cognitive", "ability"],
    },
    {
        "name": "Numerical Reasoning",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/numerical-reasoning/",
        "description": "Classic numerical reasoning test measuring ability to work with numerical data, interpret tables and charts, and solve mathematical problems. Standard for professional and managerial selection.",
        "test_type": "A",
        "duration_minutes": 25,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["graduate", "junior", "mid", "professional"],
        "skills": ["numerical reasoning", "mathematics", "data interpretation", "finance", "analysis"],
        "tags": ["numerical", "reasoning", "cognitive", "aptitude", "mathematics"],
        "languages": ["English"],
        "categories": ["cognitive", "ability"],
    },
    {
        "name": "Customer Contact Styles Questionnaire",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/customer-contact-styles-questionnaire/",
        "description": "Personality-based questionnaire measuring traits critical for customer-facing roles. Covers interpersonal effectiveness, resilience, emotional control, and service orientation.",
        "test_type": "P",
        "duration_minutes": 20,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["entry", "junior"],
        "skills": ["customer service", "personality", "communication", "resilience", "empathy"],
        "tags": ["customer service", "personality", "frontline", "contact center", "service"],
        "languages": ["English"],
        "categories": ["personality", "customer service"],
    },
    {
        "name": "Verify G+",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/verify-g-plus/",
        "description": "Adaptive cognitive ability battery combining verbal, numerical, and inductive reasoning in a shorter adaptive format. Provides a general cognitive ability (g) score. Suitable for volume screening.",
        "test_type": "A",
        "duration_minutes": 36,
        "remote_testing": True,
        "adaptive_irt": True,
        "job_levels": ["entry", "junior", "mid", "graduate"],
        "skills": ["cognitive ability", "verbal", "numerical", "inductive", "general intelligence"],
        "tags": ["cognitive", "adaptive", "IRT", "battery", "screening", "g-factor"],
        "languages": ["English"],
        "categories": ["cognitive", "ability"],
    },
    {
        "name": "Entry Level Sales 7.1",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/entry-level-sales-7-1/",
        "description": "Pre-packaged battery for entry-level sales roles including cognitive ability and personality measures. Predicts sales performance for frontline and inside sales positions.",
        "test_type": "B",
        "duration_minutes": 35,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["entry", "junior"],
        "skills": ["sales", "communication", "persuasion", "resilience", "customer orientation"],
        "tags": ["sales", "entry level", "battery", "sales performance"],
        "languages": ["English"],
        "categories": ["behavioral", "sales"],
    },
    {
        "name": "Dependability and Safety Instrument",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/dependability-and-safety-instrument/",
        "description": "Measures safety-related attitudes, reliability, and dependability behaviors. Suitable for roles where safety compliance, rule-following, and reliability are critical.",
        "test_type": "P",
        "duration_minutes": 20,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["entry", "junior"],
        "skills": ["safety", "compliance", "reliability", "dependability", "manufacturing", "operations"],
        "tags": ["safety", "dependability", "compliance", "manufacturing", "operations"],
        "languages": ["English"],
        "categories": ["personality", "behavioral", "safety"],
    },
    {
        "name": "Technology Professional 8.0",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/technology-professional-8-0/",
        "description": "Assessment battery for technology professionals combining cognitive ability and personality. Designed for software developers, IT professionals, data scientists, and technology roles.",
        "test_type": "A",
        "duration_minutes": 50,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["junior", "mid", "senior"],
        "skills": ["technology", "programming", "cognitive ability", "problem solving", "IT", "software development"],
        "tags": ["technology", "IT", "developer", "software", "engineering", "battery"],
        "languages": ["English"],
        "categories": ["cognitive", "ability", "technical"],
    },
    {
        "name": "Administrative Professional 8.0",
        "url": "https://www.shl.com/solutions/products/product-catalog/view/administrative-professional-8-0/",
        "description": "Assessment battery for administrative and clerical roles. Tests verbal ability, numerical ability, and behavioral traits relevant to office and support functions.",
        "test_type": "A",
        "duration_minutes": 45,
        "remote_testing": True,
        "adaptive_irt": False,
        "job_levels": ["entry", "junior"],
        "skills": ["administration", "office", "verbal", "numerical", "organization", "clerical"],
        "tags": ["administrative", "clerical", "office", "support", "battery"],
        "languages": ["English"],
        "categories": ["cognitive", "ability", "administrative"],
    },
]


# ──────────────────────────────────────────────────────────────────
# Scraper functions
# ──────────────────────────────────────────────────────────────────

def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def get_catalog_page(session: requests.Session, start: int = 0) -> Optional[BeautifulSoup]:
    params = {**CATALOG_PARAMS, "start": str(start)}
    url = CATALOG_URL + "?" + urlencode(params)
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        log.error(f"Failed to fetch page start={start}: {e}")
        return None


def parse_product_list(soup: BeautifulSoup) -> list[dict]:
    """Parse product cards from catalog listing page."""
    products = []

    # SHL catalog uses table rows or product cards
    # Try multiple selectors
    rows = soup.select("tr.custom-table__body-row") or soup.select(".product-catalogue__row")

    for row in rows:
        try:
            # Name and URL
            link = row.select_one("a")
            if not link:
                continue
            name = link.get_text(strip=True)
            href = link.get("href", "")
            url = urljoin(BASE_URL, href) if href else ""

            # Remote testing badge
            remote_icon = row.select_one(".remote-testing") or row.select_one('[data-tooltip="Remote Testing"]')
            remote_testing = remote_icon is not None

            # Adaptive IRT badge
            adaptive_icon = row.select_one(".adaptive-irt") or row.select_one('[data-tooltip="Adaptive/IRT"]')
            adaptive_irt = adaptive_icon is not None

            # Test type icons (look for colored squares/badges)
            test_types = []
            type_icons = row.select(".product-catalogue__key-wrap span") or row.select(".assessment-type")
            for icon in type_icons:
                title = icon.get("title", "") or icon.get("data-tooltip", "") or icon.get_text(strip=True)
                for code, label in TEST_TYPE_MAP.items():
                    if code in title or label.lower() in title.lower():
                        test_types.append(code)

            # Duration — look for time text
            duration = 0
            time_cell = row.select_one(".duration") or row.select_one("td:last-child")
            if time_cell:
                text = time_cell.get_text()
                match = re.search(r"(\d+)", text)
                if match:
                    duration = int(match.group(1))

            products.append({
                "name": name,
                "url": url,
                "test_type": test_types[0] if test_types else "A",
                "duration_minutes": duration,
                "remote_testing": remote_testing,
                "adaptive_irt": adaptive_irt,
            })
        except Exception as e:
            log.warning(f"Error parsing row: {e}")
            continue

    return products


def get_total_count(soup: BeautifulSoup) -> int:
    """Extract total number of products from catalog page."""
    # Try different selectors for count
    count_el = (
        soup.select_one(".custom-select__count")
        or soup.select_one(".catalogue-count")
        or soup.select_one("[class*='count']")
    )
    if count_el:
        match = re.search(r"(\d+)", count_el.get_text())
        if match:
            return int(match.group(1))
    return 0


def scrape_product_detail(session: requests.Session, url: str) -> dict:
    """Scrape individual product page for description and metadata."""
    if not url:
        return {}
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Description
        desc_el = (
            soup.select_one(".product-intro__text")
            or soup.select_one(".module-overview__body")
            or soup.select_one("[class*='description']")
            or soup.select_one("main p")
        )
        description = desc_el.get_text(strip=True) if desc_el else ""

        # Job levels
        job_levels = []
        level_section = soup.find(text=re.compile("job level", re.I))
        if level_section:
            parent = level_section.parent
            text = parent.get_text().lower()
            for level in ["entry", "junior", "mid", "senior", "manager", "executive", "graduate"]:
                if level in text:
                    job_levels.append(level)

        return {
            "description": description[:800],  # cap at 800 chars
            "job_levels": job_levels,
        }
    except Exception as e:
        log.warning(f"Could not scrape {url}: {e}")
        return {}


def build_tags(item: dict) -> list[str]:
    """Generate tags from item data."""
    tags = []
    name_lower = item.get("name", "").lower()
    desc_lower = item.get("description", "").lower()

    # Extract keywords from name
    words = re.sub(r"[^\w\s]", " ", name_lower).split()
    tags.extend([w for w in words if len(w) > 2])

    # Common skill keywords to detect
    SKILL_KEYWORDS = [
        "java", "python", "sql", "javascript", "c#", "c++", "golang", "rust",
        "excel", "word", "powerpoint", "office",
        "numerical", "verbal", "inductive", "deductive", "spatial", "mechanical",
        "personality", "OPQ", "leadership", "management", "sales", "customer",
        "coding", "programming", "data", "analytics", "finance", "banking",
        "safety", "compliance", "administrative", "graduate",
    ]
    for kw in SKILL_KEYWORDS:
        if kw.lower() in name_lower or kw.lower() in desc_lower:
            if kw.lower() not in [t.lower() for t in tags]:
                tags.append(kw.lower())

    return list(set(tags))[:15]


def enrich_catalog(catalog: list[dict]) -> list[dict]:
    """Add derived fields and IDs to catalog items."""
    enriched = []
    for i, item in enumerate(catalog):
        item["id"] = re.sub(r"[^\w-]", "-", item["name"].lower()).strip("-")
        item.setdefault("skills", [])
        item.setdefault("job_levels", [])
        item.setdefault("languages", ["English"])
        item.setdefault("categories", [])
        item.setdefault("description", "")

        # Auto-build tags
        item["tags"] = build_tags(item)

        # Auto-populate categories from test_type
        type_category_map = {
            "A": ["cognitive", "ability"],
            "B": ["behavioral", "situational"],
            "C": ["competency", "leadership"],
            "D": ["development"],
            "E": ["exercises", "assessment"],
            "K": ["technical", "knowledge"],
            "P": ["personality", "behavioral"],
            "S": ["simulation", "technical"],
        }
        test_type = item.get("test_type", "A")
        for tt in (test_type if isinstance(test_type, list) else [test_type]):
            item["categories"].extend(type_category_map.get(tt, []))
        item["categories"] = list(set(item["categories"]))

        # Searchable text blob for embedding
        item["search_text"] = " ".join([
            item.get("name", ""),
            item.get("description", ""),
            " ".join(item.get("skills", [])),
            " ".join(item.get("tags", [])),
            " ".join(item.get("job_levels", [])),
            " ".join(item.get("categories", [])),
            TEST_TYPE_MAP.get(item.get("test_type", "A"), ""),
        ])

        enriched.append(item)
    return enriched


# ──────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────

def scrape_live(use_fallback_on_fail: bool = True) -> list[dict]:
    """Try to scrape live catalog; fall back to curated catalog if needed."""
    session = make_session()
    log.info("Attempting live scrape of SHL catalog...")

    # Get first page to determine total
    soup = get_catalog_page(session, start=0)
    if not soup:
        log.warning("Could not reach SHL catalog — using fallback catalog")
        return FALLBACK_CATALOG

    total = get_total_count(soup)
    products = parse_product_list(soup)
    log.info(f"Found {total} total products, got {len(products)} from page 1")

    if not products:
        log.warning("No products parsed from page — using fallback catalog")
        return FALLBACK_CATALOG

    # Paginate
    start = PAGE_SIZE
    while start < total and start < 500:  # safety cap
        time.sleep(1)  # be polite
        page_soup = get_catalog_page(session, start=start)
        if not page_soup:
            break
        page_products = parse_product_list(page_soup)
        if not page_products:
            break
        products.extend(page_products)
        log.info(f"  Scraped {len(products)} products so far (start={start})")
        start += PAGE_SIZE

    # Enrich with detail pages (selective — cap at 50 to avoid rate limiting)
    log.info(f"Enriching {min(len(products), 50)} products with detail pages...")
    for i, product in enumerate(products[:50]):
        time.sleep(0.5)
        detail = scrape_product_detail(session, product.get("url", ""))
        product.update(detail)
        if i % 10 == 0:
            log.info(f"  Enriched {i+1} products...")

    return products


def main():
    parser = argparse.ArgumentParser(description="Scrape SHL catalog")
    parser.add_argument("--use-fallback", action="store_true", help="Use fallback catalog only")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output path for catalog.json")
    args = parser.parse_args()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if args.use_fallback:
        log.info("Using curated fallback catalog...")
        catalog = FALLBACK_CATALOG
    else:
        catalog = scrape_live(use_fallback_on_fail=True)

    # Always merge with fallback to ensure key assessments are present
    existing_names = {p["name"] for p in catalog}
    for fb_item in FALLBACK_CATALOG:
        if fb_item["name"] not in existing_names:
            catalog.append(fb_item)

    # Enrich and finalize
    catalog = enrich_catalog(catalog)

    # Save
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    log.info(f"Saved {len(catalog)} assessments to {args.output}")

    # Print summary
    type_counts = {}
    for item in catalog:
        tt = item.get("test_type", "?")
        type_counts[tt] = type_counts.get(tt, 0) + 1
    log.info("Catalog summary by test type:")
    for tt, count in sorted(type_counts.items()):
        log.info(f"  {tt} ({TEST_TYPE_MAP.get(tt, '?')}): {count}")


if __name__ == "__main__":
    main()
