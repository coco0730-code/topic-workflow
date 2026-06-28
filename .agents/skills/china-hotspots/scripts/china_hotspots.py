#!/usr/bin/env python3
"""抓取国内平台热榜并生成 Markdown 素材。"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
KEYWORDS_PATH = ROOT / "config" / "keywords.json"
DEFAULT_API_BASE_URL = "https://api-hot.imsyy.top"
DEFAULT_PLATFORM_IDS = ["douyin", "weibo", "baidu", "toutiao", "zhihu", "36kr", "juejin"]
PLATFORM_LABELS = {
    "douyin": "抖音",
    "weibo": "微博",
    "baidu": "百度",
    "toutiao": "今日头条",
    "zhihu": "知乎",
    "36kr": "36氪",
    "juejin": "掘金",
    "bilibili": "哔哩哔哩",
    "ithome": "IT之家",
    "thepaper": "澎湃新闻",
}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect China platform hot lists.")
    parser.add_argument("--config", type=Path, default=KEYWORDS_PATH)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--date", help="Date in YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--api-base-url", help="DailyHotApi-compatible base URL.")
    parser.add_argument("--platform", action="append", dest="platforms", help="Platform id, e.g. douyin.")
    parser.add_argument("--max-items", type=int, help="Max items per platform.")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON config: {path}\n{exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Invalid JSON config: {path}\nTop-level value must be an object.")
    return data


def resolve_settings(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    china_config = config.get("chinaHotspots") if isinstance(config.get("chinaHotspots"), dict) else {}
    platforms = args.platforms or china_config.get("platforms") or DEFAULT_PLATFORM_IDS
    platforms = [str(platform).strip() for platform in platforms if str(platform).strip()]
    api_base_url = str(args.api_base_url or china_config.get("apiBaseUrl") or DEFAULT_API_BASE_URL).strip()
    max_items = args.max_items or int(china_config.get("maxItemsPerPlatform") or 20)
    manual_sources = china_config.get("manualSources") if isinstance(china_config.get("manualSources"), list) else []
    return {
        "enabled": bool(china_config.get("enabled", True)),
        "api_base_url": api_base_url.rstrip("/"),
        "platforms": platforms,
        "max_items": max(1, max_items),
        "manual_sources": manual_sources,
        "daily_queries": config.get("dailyQueries") if isinstance(config.get("dailyQueries"), list) else [],
    }


def request_json(url: str, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "topic-workflow/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
    return json.loads(body)


def normalize_item(item: Any, index: int) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    title = str(
        item.get("title")
        or item.get("name")
        or item.get("word")
        or item.get("keyword")
        or item.get("desc")
        or ""
    ).strip()
    if not title:
        return None
    url = str(
        item.get("url")
        or item.get("link")
        or item.get("mobileUrl")
        or item.get("mobile_url")
        or item.get("shareUrl")
        or ""
    ).strip()
    hot = item.get("hot") or item.get("hotValue") or item.get("heat") or item.get("views") or item.get("score")
    desc = str(item.get("desc") or item.get("summary") or item.get("content") or "").strip()
    return {
        "rank": item.get("rank") or item.get("index") or index,
        "title": title,
        "url": url,
        "hot": hot,
        "desc": desc,
    }


def extract_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    raw_items = data.get("data")
    if isinstance(raw_items, dict):
        raw_items = raw_items.get("list") or raw_items.get("items") or raw_items.get("data")
    if not isinstance(raw_items, list):
        raw_items = data.get("list") or data.get("items") or data.get("results")
    if not isinstance(raw_items, list):
        return []
    items = []
    for index, raw_item in enumerate(raw_items, start=1):
        item = normalize_item(raw_item, index)
        if item:
            items.append(item)
    return items


def collect_platform(platform: str, settings: dict[str, Any], timeout: int) -> dict[str, Any]:
    url = f"{settings['api_base_url']}/{urllib.parse.quote(platform)}"
    try:
        data = request_json(url, timeout)
        items = extract_items(data)[: settings["max_items"]]
        return {
            "platform": platform,
            "label": PLATFORM_LABELS.get(platform, platform),
            "url": url,
            "ok": True,
            "items": items,
            "updated_at": data.get("updateTime") or data.get("updated_at") or data.get("time") or "",
            "error": "",
        }
    except (json.JSONDecodeError, urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        return {
            "platform": platform,
            "label": PLATFORM_LABELS.get(platform, platform),
            "url": url,
            "ok": False,
            "items": [],
            "updated_at": "",
            "error": str(exc),
        }


def keyword_terms(daily_queries: list[Any]) -> list[str]:
    text = " ".join(str(query) for query in daily_queries)
    candidates = re.split(r"[\s,，、/|()（）]+", text)
    stopwords = {"最新", "资讯", "latest", "news", "trend", "trends", "工具", "平台"}
    terms = []
    for candidate in candidates:
        token = candidate.strip().lower()
        if len(token) < 2 or token in stopwords:
            continue
        if token not in terms:
            terms.append(token)
    return terms


def relevance_hits(item: dict[str, Any], terms: list[str]) -> list[str]:
    haystack = f"{item.get('title', '')} {item.get('desc', '')}".lower()
    return [term for term in terms if term in haystack]


def render_markdown(results: list[dict[str, Any]], settings: dict[str, Any]) -> str:
    now = dt.datetime.now().astimezone()
    terms = keyword_terms(settings["daily_queries"])
    total_items = sum(len(result["items"]) for result in results)
    failed = [result for result in results if not result["ok"]]
    relevant: list[tuple[str, dict[str, Any], list[str]]] = []
    for result in results:
        for item in result["items"]:
            hits = relevance_hits(item, terms)
            if hits:
                relevant.append((result["label"], item, hits))

    lines = [
        f"# 国内平台热点素材 - {now:%Y-%m-%d}",
        "",
        f"- 生成时间：{now:%Y-%m-%d %H:%M:%S %Z}",
        f"- 平台数：{len(results)}",
        f"- 热点条目：{total_items}",
        f"- 相关候选：{len(relevant)}",
        f"- API 基址：{settings['api_base_url']}",
        "",
    ]

    if failed:
        lines.extend(["## 采集提醒", ""])
        for result in failed:
            lines.append(f"- {result['label']} 请求失败：{result['error']}（{result['url']}）")
        lines.append("")

    if relevant:
        lines.extend(["## 与业务关键词相关的候选", ""])
        for label, item, hits in relevant[:20]:
            title = item["title"]
            url = item.get("url") or ""
            hot = item.get("hot")
            suffix = f"；热度：{hot}" if hot else ""
            hit_text = "、".join(hits[:5])
            if url:
                lines.append(f"- [{title}]({url})（{label}；命中：{hit_text}{suffix}）")
            else:
                lines.append(f"- {title}（{label}；命中：{hit_text}{suffix}）")
        lines.append("")

    lines.extend(["## 平台热榜", ""])
    for result in results:
        lines.extend([f"### {result['label']}", ""])
        if result["updated_at"]:
            lines.append(f"- 更新时间：{result['updated_at']}")
        lines.append(f"- 来源：{result['url']}")
        if not result["items"]:
            lines.extend(["- 暂无可用条目", ""])
            continue
        lines.append("")
        for item in result["items"]:
            title = item["title"]
            url = item.get("url") or ""
            rank = item.get("rank") or ""
            hot = item.get("hot")
            desc = item.get("desc") or ""
            prefix = f"{rank}. " if rank else "- "
            if url:
                lines.append(f"{prefix}[{title}]({url})")
            else:
                lines.append(f"{prefix}{title}")
            meta = []
            if hot:
                meta.append(f"热度：{hot}")
            hits = relevance_hits(item, terms)
            if hits:
                meta.append(f"命中关键词：{'、'.join(hits[:5])}")
            if meta:
                lines.append(f"   - {'；'.join(meta)}")
            if desc:
                snippet = textwrap.shorten(" ".join(desc.split()), width=160, placeholder="...")
                lines.append(f"   - {snippet}")
        lines.append("")

    manual_sources = settings.get("manual_sources") or []
    if manual_sources:
        lines.extend(["## 小红书/公众号等人工补充源", ""])
        for source in manual_sources:
            if isinstance(source, dict):
                platform = source.get("platform") or "人工源"
                note = source.get("note") or source.get("query") or ""
                url = source.get("url")
                if url:
                    lines.append(f"- {platform}：[{note or url}]({url})")
                else:
                    lines.append(f"- {platform}：{note}")
            else:
                lines.append(f"- {source}")
        lines.append("")

    lines.extend(
        [
            "## 使用说明",
            "",
            "- 本文件是选题素材，不等同于事实确认。",
            "- 热榜标题、热度和链接需要在正式发布前二次核实。",
            "- 小红书若无接口数据，优先补充行业关键词搜索结果、对标账号爆款笔记、评论区高频问题。",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    config = load_config(args.config)
    settings = resolve_settings(args, config)
    date = args.date or dt.datetime.now().astimezone().strftime("%Y-%m-%d")
    output = args.output or ROOT / "outputs" / date / "china-hotspots-source.md"

    if args.dry_run:
        print(f"enabled={settings['enabled']}")
        print(f"api_base_url={settings['api_base_url']}")
        print("platforms=" + ",".join(settings["platforms"]))
        print(f"max_items={settings['max_items']}")
        return 0

    if not settings["enabled"]:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("# 国内平台热点素材\n\n- 已在配置中关闭 `chinaHotspots.enabled`。\n", encoding="utf-8")
        print(output)
        return 0

    results = [collect_platform(platform, settings, args.timeout) for platform in settings["platforms"]]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(results, settings), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
