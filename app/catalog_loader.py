"""
Catalog loader — reads catalog.json, validates, exposes as singleton.
Generates catalog at startup if missing (uses fallback).
"""

import json
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Set
from loguru import logger

_CATALOG: List[Dict] = []
_CATALOG_URLS: Set[str] = set()
_LOADED = False

CATALOG_PATH = Path(__file__).parent.parent / "data" / "catalog.json"


def _generate_catalog():
    """Run scraper to generate catalog if missing."""
    logger.info("catalog.json not found — generating from fallback catalog...")
    script = Path(__file__).parent.parent / "scripts" / "scrape_catalog.py"
    result = subprocess.run(
        [sys.executable, str(script), "--use-fallback"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        logger.error(f"Scraper failed: {result.stderr}")
    else:
        logger.info("Catalog generated successfully.")


def load_catalog(path: Path = CATALOG_PATH) -> List[Dict]:
    global _CATALOG, _CATALOG_URLS, _LOADED
    if _LOADED:
        return _CATALOG

    if not path.exists():
        _generate_catalog()

    if not path.exists():
        logger.error("Could not load or generate catalog.json!")
        _CATALOG = []
        _CATALOG_URLS = set()
        _LOADED = True
        return _CATALOG

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Validate and filter
    valid = []
    for item in data:
        if not item.get("name") or not item.get("url"):
            continue
        # Ensure required fields
        item.setdefault("test_type", "A")
        item.setdefault("description", "")
        item.setdefault("duration_minutes", 0)
        item.setdefault("remote_testing", True)
        item.setdefault("adaptive_irt", False)
        item.setdefault("job_levels", [])
        item.setdefault("skills", [])
        item.setdefault("tags", [])
        item.setdefault("categories", [])
        item.setdefault("languages", ["English"])
        item.setdefault("search_text", " ".join([
            item["name"], item["description"],
            " ".join(item["skills"]), " ".join(item["tags"])
        ]))
        valid.append(item)

    _CATALOG = valid
    _CATALOG_URLS = {item["url"] for item in valid}
    _LOADED = True
    logger.info(f"Loaded {len(_CATALOG)} assessments from catalog.")
    return _CATALOG


def get_catalog() -> List[Dict]:
    return load_catalog()


def get_catalog_urls() -> Set[str]:
    load_catalog()
    return _CATALOG_URLS


def get_by_name(name: str) -> Dict | None:
    catalog = get_catalog()
    name_lower = name.lower()
    for item in catalog:
        if item["name"].lower() == name_lower:
            return item
    # Partial match
    for item in catalog:
        if name_lower in item["name"].lower():
            return item
    return None
