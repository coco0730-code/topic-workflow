#!/usr/bin/env python3
"""把结构化 facts 中的关键词候选合并写入 config/keywords.json。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
KEYWORDS_PATH = ROOT / "config" / "keywords.json"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update config/keywords.json from structured facts.")
    parser.add_argument("--facts-file", type=Path, required=True, help="结构化 facts JSON 文件。")
    parser.add_argument("--mode", choices=["bootstrap", "merge", "refresh"], default="merge")
    parser.add_argument("--dry-run", action="store_true", help="只打印结果，不真正写入。")
    return parser.parse_args(argv)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("Top-level JSON value must be an object.")
    return data


def uniq(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def update_keywords(existing: dict[str, Any], facts: dict[str, Any], mode: str) -> dict[str, Any]:
    keyword_facts = facts.get("keywords") if isinstance(facts.get("keywords"), dict) else {}
    daily_queries = uniq(keyword_facts.get("daily_queries") or [])
    exa_queries = uniq(keyword_facts.get("exa_queries") or [])
    platforms = uniq(keyword_facts.get("platforms") or [])
    notes = uniq(keyword_facts.get("notes") or [])

    updated = json.loads(json.dumps(existing, ensure_ascii=False))

    if mode == "bootstrap":
        updated["dailyQueries"] = daily_queries or existing.get("dailyQueries") or []
    elif mode == "refresh":
        if daily_queries:
            updated["dailyQueries"] = daily_queries
    else:
        updated["dailyQueries"] = uniq((existing.get("dailyQueries") or []) + daily_queries)

    exa = updated.get("exaWebSearch") if isinstance(updated.get("exaWebSearch"), dict) else {}
    existing_exa_queries = exa.get("queries") if isinstance(exa.get("queries"), list) else []
    if mode == "bootstrap":
        exa["queries"] = exa_queries or existing_exa_queries
    elif mode == "refresh":
        if exa_queries:
            exa["queries"] = exa_queries
    else:
        exa["queries"] = uniq(existing_exa_queries + exa_queries)
    updated["exaWebSearch"] = exa

    existing_platforms = updated.get("platforms") if isinstance(updated.get("platforms"), list) else []
    if platforms:
        updated["platforms"] = uniq(existing_platforms + platforms)

    metadata = updated.get("knowledgeBootstrap") if isinstance(updated.get("knowledgeBootstrap"), dict) else {}
    if keyword_facts.get("focus"):
        metadata["keywordFocus"] = keyword_facts.get("focus")
    if notes:
        metadata["notes"] = uniq((metadata.get("notes") if isinstance(metadata.get("notes"), list) else []) + notes)
    if metadata:
        updated["knowledgeBootstrap"] = metadata

    return updated


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    facts = load_json(args.facts_file)
    existing = load_json(KEYWORDS_PATH)
    updated = update_keywords(existing, facts, args.mode)

    text = json.dumps(updated, ensure_ascii=False, indent=2) + "\n"
    if args.dry_run:
        print(text)
        return 0

    KEYWORDS_PATH.write_text(text, encoding="utf-8")
    print(KEYWORDS_PATH)
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
