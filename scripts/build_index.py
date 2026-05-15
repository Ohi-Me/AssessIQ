#!/usr/bin/env python3
"""
Pre-build FAISS + BM25 indexes from catalog.json.
Run this after scraping to avoid cold-start index building.

Usage:
    python scripts/build_index.py
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.catalog_loader import load_catalog
from app.retriever import build_indexes
from loguru import logger


def main():
    logger.info("Loading catalog...")
    catalog = load_catalog()
    logger.info(f"Loaded {len(catalog)} assessments.")

    logger.info("Building indexes...")
    build_indexes(catalog)
    logger.info("Done! Indexes saved to data/")


if __name__ == "__main__":
    main()
