#!/usr/bin/env python3
"""根据 config/keywords.json 调用 Tavily、Exa 和国内热榜采集，生成当天素材。"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TAVILY_SCRIPT = ROOT / ".agents" / "skills" / "tavily-industry-news" / "scripts" / "daily_tavily_news.py"
CHINA_HOTSPOTS_SCRIPT = ROOT / ".agents" / "skills" / "china-hotspots" / "scripts" / "china_hotspots.py"
EXA_SCRIPT = ROOT / "scripts" / "exa_china_web_search.py"
KEYWORDS_PATH = ROOT / "config" / "keywords.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Tavily news collection from config/keywords.json.")
    parser.add_argument("--date", help="Date in YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_keywords() -> dict:
    data = json.loads(KEYWORDS_PATH.read_text(encoding="utf-8"))
    queries = data.get("dailyQueries")
    if not isinstance(queries, list) or not [q for q in queries if str(q).strip()]:
        raise SystemExit("config/keywords.json must contain non-empty dailyQueries.")
    if any(str(q).startswith("TODO:") for q in queries):
        raise SystemExit("Please replace TODO entries in config/keywords.json before running news collection.")
    return data


def write_failure_note(path: Path, title: str, command: list[str], result: subprocess.CompletedProcess[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    output = "\n".join(part for part in [result.stdout, result.stderr] if part)
    path.write_text(
        "\n".join(
            [
                f"# {title}",
                "",
                "- 状态：采集失败",
                f"- 退出码：{result.returncode}",
                "",
                "## 命令",
                "",
                "```bash",
                " ".join(command),
                "```",
                "",
                "## 错误输出",
                "",
                "```text",
                output.strip() or "无输出",
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )


def run_source(name: str, command: list[str], output: Path) -> bool:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    if result.returncode == 0:
        if result.stdout.strip():
            print(result.stdout.strip())
        return True
    print(f"{name} failed; wrote fallback note to {output}", file=sys.stderr)
    write_failure_note(output, f"{name} 采集失败", command, result)
    return False


def main() -> int:
    args = parse_args()
    date = args.date or dt.datetime.now().astimezone().strftime("%Y-%m-%d")
    config = load_keywords()
    output_dir = ROOT / "outputs" / date
    tavily_output = output_dir / "news-source.md"
    exa_output = output_dir / "china-web-search-source.md"
    china_output = output_dir / "china-hotspots-source.md"
    output_dir.mkdir(parents=True, exist_ok=True)

    tavily_cmd = [sys.executable, str(TAVILY_SCRIPT)]
    for query in config["dailyQueries"]:
        query = str(query).strip()
        if query:
            tavily_cmd.extend(["--query", query])
    tavily_cmd.extend(["--max-results", str(config.get("maxResultsPerQuery", 5))])
    if config.get("timeRange"):
        tavily_cmd.extend(["--time-range", str(config["timeRange"])])
    tavily_cmd.extend(["--output", str(tavily_output)])

    china_cmd = [
        sys.executable,
        str(CHINA_HOTSPOTS_SCRIPT),
        "--date",
        date,
        "--output",
        str(china_output),
    ]
    exa_cmd = [
        sys.executable,
        str(EXA_SCRIPT),
        "--date",
        date,
        "--output",
        str(exa_output),
    ]

    if args.dry_run:
        print("Tavily:")
        print(" ".join(tavily_cmd))
        print("Exa China web search:")
        print(" ".join(exa_cmd + ["--dry-run"]))
        print("China hotspots:")
        print(" ".join(china_cmd + ["--dry-run"]))
        return 0

    results = [
        run_source("Tavily", tavily_cmd, tavily_output),
        run_source("Exa China web search", exa_cmd, exa_output),
        run_source("China hotspots", china_cmd, china_output),
    ]
    print(tavily_output)
    print(exa_output)
    print(china_output)
    return 0 if any(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
