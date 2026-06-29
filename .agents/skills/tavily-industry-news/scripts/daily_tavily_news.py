#!/usr/bin/env python3
"""使用 Tavily 抓取行业资讯并生成 Markdown 素材文件。"""

# 启用延迟注解求值，兼容低版本 Python
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import textwrap
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


# Tavily Search API 端点
TAVILY_SEARCH_URL = "https://api.tavily.com/search"


def skill_root() -> Path:
    """返回技能根目录（当前脚本所在目录的父目录）。"""
    return Path(__file__).resolve().parents[1]


def project_root() -> Path:
    """返回项目根目录。"""
    return Path(__file__).resolve().parents[4]


def default_config_path() -> Path:
    """返回本地配置文件的默认路径。"""
    return project_root() / "config" / "api-keys.json"


def load_json_config(path: Path | None) -> dict[str, Any]:
    """读取 JSON 配置文件；文件不存在时返回空字典。"""
    config_path = path or default_config_path()
    if not config_path.exists():
        return {}
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON config: {config_path}\n{exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Invalid JSON config: {config_path}\nTop-level value must be an object.")
    return data


def find_api_key(config: dict[str, Any]) -> str:
    """从配置中提取 Tavily API key（兼容多种命名），未配置则报错退出。"""
    tavily_config = config.get("tavily") if isinstance(config.get("tavily"), dict) else {}
    # 兼容多种常见命名写法
    key = str(
        tavily_config.get("apiKey")
        or tavily_config.get("api_key")
        or config.get("apiKey")
        or config.get("api_key")
        or config.get("tavilyApiKey")
        or config.get("tavily_api_key")
        or ""
    ).strip()
    if not key:
        raise SystemExit(
            "Missing Tavily API key. Add it to config/api-keys.json under tavily.apiKey."
        )
    return key


def tavily_search(api_key: str, query: str, args: argparse.Namespace) -> dict[str, Any]:
    """调用 Tavily /search 接口，返回原始 JSON 响应。"""
    payload: dict[str, Any] = {
        "query": query,
        "topic": args.topic,
        "search_depth": args.search_depth,
        "max_results": args.max_results,
        "include_answer": True,
        "include_raw_content": args.include_raw_content,
    }
    if args.time_range:
        payload["time_range"] = args.time_range
    if args.start_date:
        payload["start_date"] = args.start_date
    if args.end_date:
        payload["end_date"] = args.end_date

    request = urllib.request.Request(
        TAVILY_SEARCH_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # 4xx/5xx 时把响应体一并抛出，便于排查
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Tavily HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Tavily request failed: {exc.reason}") from exc


def normalize_url(url: str) -> str:
    """去除首尾空白与尾部斜杠，用于跨查询去重比较。"""
    return url.strip().rstrip("/")


def render_markdown(results_by_query: list[tuple[str, dict[str, Any]]]) -> str:
    """把 Tavily 结果渲染为 Markdown 文本，含 AI 总结与去重后的来源链接。"""
    now = dt.datetime.now().astimezone()
    lines: list[str] = [
        f"# Tavily 行业资讯素材 - {now:%Y-%m-%d}",
        "",
        f"- 生成时间：{now:%Y-%m-%d %H:%M:%S %Z}",
        f"- 查询数：{len(results_by_query)}",
        "- 去重来源数：0",  # 占位行，渲染结束后回填真实数值
        "",
    ]

    seen: set[str] = set()
    source_count = 0

    for query, data in results_by_query:
        lines.extend([f"## {query}", ""])
        # 优先展示 Tavily 自带的 AI 总结（如有），便于快速浏览
        answer = (data.get("answer") or "").strip()
        if answer:
            lines.extend(["### Tavily Answer", "", answer, ""])

        lines.extend(["### Results", ""])
        query_results = data.get("results") or []
        if not query_results:
            lines.extend(["- 无结果", ""])
            continue

        for item in query_results:
            url = normalize_url(str(item.get("url") or ""))
            if not url or url in seen:
                # 空链接或已收录过的来源都跳过，避免重复
                continue
            seen.add(url)
            source_count += 1

            title = str(item.get("title") or "Untitled").strip()
            content = str(item.get("content") or "").strip()
            score = item.get("score")
            published_date = item.get("published_date")

            lines.append(f"- [{title}]({url})")
            meta = []
            if published_date:
                meta.append(f"published: {published_date}")
            if score is not None:
                meta.append(f"score: {score}")
            if meta:
                lines.append(f"  - {'; '.join(meta)}")
            # 摘要过长时压缩到 420 字符以内，避免单条信息占满屏
            if content:
                snippet = textwrap.shorten(" ".join(content.split()), width=420, placeholder="...")
                lines.append(f"  - {snippet}")
        lines.append("")

    # 回填去重后的实际来源数量
    lines[4] = f"- 去重来源数：{source_count}"
    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: list[str]) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="Collect Tavily search results and write Markdown source notes.",
    )
    parser.add_argument(
        "--query",
        action="append",
        dest="queries",
        help="Search query. Can be passed multiple times.",
    )
    parser.add_argument(
        "--queries-file",
        type=Path,
        help="UTF-8 text file with one query per line.",
    )
    parser.add_argument("--output", type=Path, help="Markdown output path.")
    parser.add_argument(
        "--config",
        type=Path,
        help="JSON config path. Defaults to project config/api-keys.json.",
    )
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--search-depth", choices=["basic", "advanced"], default="basic")
    parser.add_argument("--topic", choices=["general", "news"], default="general")
    parser.add_argument(
        "--time-range",
        choices=["day", "week", "month", "year", "d", "w", "m", "y"],
        help="Optional Tavily recency window.",
    )
    parser.add_argument("--start-date", help="Optional YYYY-MM-DD start date for Tavily search.")
    parser.add_argument("--end-date", help="Optional YYYY-MM-DD end date for Tavily search.")
    parser.add_argument("--include-raw-content", action="store_true")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved queries without calling Tavily.",
    )
    return parser.parse_args(argv)


def collect_queries(args: argparse.Namespace) -> list[str]:
    """从命令行参数或查询文件中读取关键词；没有关键词时直接提示用户。"""
    queries = list(args.queries or [])
    if args.queries_file:
        # 文件中以 # 开头的行视为注释
        lines = args.queries_file.read_text(encoding="utf-8").splitlines()
        queries.extend(line.strip() for line in lines if line.strip() and not line.startswith("#"))
    if not queries:
        raise SystemExit(
            "Missing search query. Please pass at least one keyword, for example:\n"
            "  python3 .agents/skills/tavily-industry-news/scripts/daily_tavily_news.py "
            '--query "epa鱼油"'
        )
    return queries


def main(argv: list[str]) -> int:
    """脚本入口：解析参数 -> 加载配置 -> 抓取 -> 输出 Markdown。"""
    args = parse_args(argv)
    config = load_json_config(args.config)
    queries = collect_queries(args)

    # dry-run 模式：仅打印将要使用的查询，不发起网络请求
    if args.dry_run:
        print("\n".join(queries))
        return 0

    api_key = find_api_key(config)
    results_by_query = []
    for query in queries:
        results_by_query.append((query, tavily_search(api_key, query, args)))

    markdown = render_markdown(results_by_query)
    # 未显式指定输出路径时，默认写到 outputs/<日期>/news-source.md
    output = args.output
    if output is None:
        date = dt.datetime.now().astimezone().strftime("%Y-%m-%d")
        output = Path("outputs") / date / "news-source.md"

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
