#!/usr/bin/env python3
"""使用 Exa Search API 抓取中文关键词网页搜索结果。"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import textwrap
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
KEYWORDS_PATH = ROOT / "config" / "keywords.json"
API_KEYS_PATH = ROOT / "config" / "api-keys.json"
EXA_SEARCH_URL = "https://api.exa.ai/search"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Chinese web search results with Exa.")
    parser.add_argument("--date", help="Date in YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--config", type=Path, default=KEYWORDS_PATH)
    parser.add_argument("--api-keys", type=Path, default=API_KEYS_PATH)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--query", action="append", dest="queries")
    parser.add_argument("--max-results", type=int)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON config: {path}\n{exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Invalid JSON config: {path}\nTop-level value must be an object.")
    return data


def find_api_key(path: Path) -> str:
    config = load_json(path)
    exa_config = config.get("exa") if isinstance(config.get("exa"), dict) else {}
    key = str(
        exa_config.get("apiKey")
        or exa_config.get("api_key")
        or config.get("exaApiKey")
        or config.get("exa_api_key")
        or os.environ.get("EXA_API_KEY")
        or ""
    ).strip()
    return key


def exa_settings(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    exa_config = config.get("exaWebSearch") if isinstance(config.get("exaWebSearch"), dict) else {}
    queries = args.queries or exa_config.get("queries") or config.get("dailyQueries") or []
    queries = [str(query).strip() for query in queries if str(query).strip()]
    include_domains = exa_config.get("includeDomains") if isinstance(exa_config.get("includeDomains"), list) else []
    max_results = args.max_results or int(exa_config.get("maxResultsPerQuery") or 5)
    return {
        "enabled": bool(exa_config.get("enabled", True)),
        "queries": queries,
        "include_domains": [str(domain).strip() for domain in include_domains if str(domain).strip()],
        "max_results": max(1, max_results),
        "search_type": str(exa_config.get("type") or "auto"),
        "text_max_characters": int(exa_config.get("textMaxCharacters") or 900),
    }


def exa_search(api_key: str, query: str, settings: dict[str, Any], timeout: int) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "query": query,
        "type": settings["search_type"],
        "numResults": settings["max_results"],
        "contents": {
            "text": {"maxCharacters": settings["text_max_characters"]},
            "highlights": {"numSentences": 2, "highlightsPerUrl": 2},
            "summary": {"query": "用中文概括这个结果与工业设计、产品设计、AI工具或制造业设计工作流的关系。"},
        },
    }
    if settings["include_domains"]:
        payload["includeDomains"] = settings["include_domains"]

    request = urllib.request.Request(
        EXA_SEARCH_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def render_missing_key(settings: dict[str, Any]) -> str:
    now = dt.datetime.now().astimezone()
    lines = [
        f"# Exa 中文关键词搜索素材 - {now:%Y-%m-%d}",
        "",
        f"- 生成时间：{now:%Y-%m-%d %H:%M:%S %Z}",
        "- 状态：未执行，缺少 Exa API key",
        "",
        "## 配置方式",
        "",
        "在 `config/api-keys.json` 中加入：",
        "",
        "```json",
        '{',
        '  "exa": {',
        '    "apiKey": "你的 Exa API key"',
        '  }',
        '}',
        "```",
        "",
        "## 将要搜索的关键词",
        "",
    ]
    lines.extend(f"- {query}" for query in settings["queries"])
    return "\n".join(lines).rstrip() + "\n"


def render_markdown(results_by_query: list[tuple[str, dict[str, Any] | None, str]], settings: dict[str, Any]) -> str:
    now = dt.datetime.now().astimezone()
    source_count = 0
    lines = [
        f"# Exa 中文关键词搜索素材 - {now:%Y-%m-%d}",
        "",
        f"- 生成时间：{now:%Y-%m-%d %H:%M:%S %Z}",
        f"- 查询数：{len(results_by_query)}",
        "- 去重来源数：0",
        f"- 每个关键词上限：{settings['max_results']}",
        "",
    ]
    if settings["include_domains"]:
        lines.extend(["## 优先检索域名", ""])
        lines.extend(f"- {domain}" for domain in settings["include_domains"])
        lines.append("")

    seen_urls: set[str] = set()
    for query, data, error in results_by_query:
        lines.extend([f"## {query}", ""])
        if error:
            lines.extend([f"- 请求失败：{error}", ""])
            continue

        items = data.get("results") if isinstance(data, dict) else []
        if not isinstance(items, list) or not items:
            lines.extend(["- 无结果", ""])
            continue

        for item in items:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            source_count += 1

            title = str(item.get("title") or "Untitled").strip()
            published_date = item.get("publishedDate")
            summary = str(item.get("summary") or "").strip()
            highlights = item.get("highlights") if isinstance(item.get("highlights"), list) else []
            text = str(item.get("text") or "").strip()

            lines.append(f"- [{title}]({url})")
            if published_date:
                lines.append(f"  - 发布时间：{published_date}")
            if summary:
                lines.append(f"  - 摘要：{textwrap.shorten(' '.join(summary.split()), width=260, placeholder='...')}")
            if highlights:
                highlight_text = " / ".join(str(value).strip() for value in highlights if str(value).strip())
                if highlight_text:
                    lines.append(f"  - 命中片段：{textwrap.shorten(' '.join(highlight_text.split()), width=260, placeholder='...')}")
            elif text:
                lines.append(f"  - 正文片段：{textwrap.shorten(' '.join(text.split()), width=260, placeholder='...')}")
        lines.append("")

    lines[4] = f"- 去重来源数：{source_count}"
    lines.extend(
        [
            "## 使用说明",
            "",
            "- 本文件用于补充中文网页关键词搜索，不等同于事实确认。",
            "- 正式发布前需要打开原链接核实发布时间、主体和上下文。",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    config = load_json(args.config)
    settings = exa_settings(args, config)
    date = args.date or dt.datetime.now().astimezone().strftime("%Y-%m-%d")
    output = args.output or ROOT / "outputs" / date / "china-web-search-source.md"

    if args.dry_run:
        print(f"enabled={settings['enabled']}")
        print("queries=" + "|".join(settings["queries"]))
        print("include_domains=" + ",".join(settings["include_domains"]))
        print(f"max_results={settings['max_results']}")
        return 0

    output.parent.mkdir(parents=True, exist_ok=True)
    if not settings["enabled"]:
        output.write_text("# Exa 中文关键词搜索素材\n\n- 已在配置中关闭 `exaWebSearch.enabled`。\n", encoding="utf-8")
        print(output)
        return 0

    api_key = find_api_key(args.api_keys)
    if not api_key:
        output.write_text(render_missing_key(settings), encoding="utf-8")
        print(output)
        return 0

    results_by_query: list[tuple[str, dict[str, Any] | None, str]] = []
    for query in settings["queries"]:
        try:
            results_by_query.append((query, exa_search(api_key, query, settings, args.timeout), ""))
        except (json.JSONDecodeError, urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
            results_by_query.append((query, None, str(exc)))

    output.write_text(render_markdown(results_by_query, settings), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
