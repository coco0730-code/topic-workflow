#!/usr/bin/env python3
"""根据 config/keywords.json 调用 Tavily、Exa 和国内热榜采集，生成当天素材。"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
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
    parser.add_argument(
        "--time-range",
        help="采集时间窗口，例如 48h、7d、day、week、最近48小时、近7天。未指定时默认近7天。",
    )
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


def _utc_iso(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_time_window(raw_value: str | None, fallback_value: str | None = None) -> dict[str, str | None]:
    """Normalize a user/config time window to values usable by Tavily and Exa.

    Supported examples:
    - `48h`, `24h`, `7d`, `2w`, `1m`
    - `day`, `week`, `month`, `year`
    - `最近48小时`, `近7天`, `最近2周`, `近1个月`
    """
    default_value = str(raw_value or fallback_value or "7d").strip()
    text = default_value.lower().strip()
    compact = re.sub(r"\s+", "", text)
    alias_map = {
        "day": ("day", dt.timedelta(days=1), "近24小时"),
        "d": ("day", dt.timedelta(days=1), "近24小时"),
        "today": ("day", dt.timedelta(days=1), "近24小时"),
        "24h": ("day", dt.timedelta(hours=24), "近24小时"),
        "1d": ("day", dt.timedelta(days=1), "近24小时"),
        "近24小时": ("day", dt.timedelta(hours=24), "近24小时"),
        "最近24小时": ("day", dt.timedelta(hours=24), "近24小时"),
        "一天": ("day", dt.timedelta(days=1), "近24小时"),
        "1天": ("day", dt.timedelta(days=1), "近24小时"),
        "week": ("week", dt.timedelta(days=7), "近7天"),
        "w": ("week", dt.timedelta(days=7), "近7天"),
        "7d": ("week", dt.timedelta(days=7), "近7天"),
        "1w": ("week", dt.timedelta(days=7), "近7天"),
        "近7天": ("week", dt.timedelta(days=7), "近7天"),
        "最近7天": ("week", dt.timedelta(days=7), "近7天"),
        "一周": ("week", dt.timedelta(days=7), "近7天"),
        "month": ("month", dt.timedelta(days=30), "近30天"),
        "m": ("month", dt.timedelta(days=30), "近30天"),
        "30d": ("month", dt.timedelta(days=30), "近30天"),
        "1m": ("month", dt.timedelta(days=30), "近30天"),
        "近30天": ("month", dt.timedelta(days=30), "近30天"),
        "最近30天": ("month", dt.timedelta(days=30), "近30天"),
        "一个月": ("month", dt.timedelta(days=30), "近30天"),
        "year": ("year", dt.timedelta(days=365), "近365天"),
        "y": ("year", dt.timedelta(days=365), "近365天"),
        "365d": ("year", dt.timedelta(days=365), "近365天"),
        "1y": ("year", dt.timedelta(days=365), "近365天"),
        "近365天": ("year", dt.timedelta(days=365), "近365天"),
        "最近365天": ("year", dt.timedelta(days=365), "近365天"),
        "一年": ("year", dt.timedelta(days=365), "近365天"),
    }
    if compact in alias_map:
        tavily_time_range, delta, label = alias_map[compact]
    else:
        match = re.fullmatch(r"(?:近|最近)?(\d+)(小时|小時|h|hr|hrs|hour|hours|天|日|d|day|days|周|w|week|weeks|个月|個月|月|m|month|months)", compact)
        if not match:
            raise SystemExit(
                "Unsupported time window. Try values like 48h, 7d, week, 最近48小时, 近7天."
            )
        amount = int(match.group(1))
        unit = match.group(2)
        if amount <= 0:
            raise SystemExit("Time window must be greater than 0.")
        if unit in {"小时", "小時", "h", "hr", "hrs", "hour", "hours"}:
            tavily_time_range = "day" if amount <= 24 else None
            delta = dt.timedelta(hours=amount)
            label = f"近{amount}小时"
        elif unit in {"天", "日", "d", "day", "days"}:
            tavily_time_range = {1: "day", 7: "week", 30: "month", 365: "year"}.get(amount)
            delta = dt.timedelta(days=amount)
            label = f"近{amount}天"
        elif unit in {"周", "w", "week", "weeks"}:
            tavily_time_range = "week" if amount == 1 else None
            delta = dt.timedelta(days=amount * 7)
            label = f"近{amount}周"
        else:
            tavily_time_range = "month" if amount == 1 else None
            delta = dt.timedelta(days=amount * 30)
            label = f"近{amount}个月"

    now = dt.datetime.now().astimezone()
    start = now - delta
    return {
        "requested": default_value,
        "label": label,
        "tavily_time_range": tavily_time_range,
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": now.strftime("%Y-%m-%d"),
        "start_published_date": _utc_iso(start),
        "end_published_date": _utc_iso(now),
    }


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
    time_window = resolve_time_window(args.time_range, str(config.get("timeRange") or "7d"))
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
    if time_window["tavily_time_range"]:
        tavily_cmd.extend(["--time-range", str(time_window["tavily_time_range"])])
    else:
        tavily_cmd.extend(["--start-date", str(time_window["start_date"]), "--end-date", str(time_window["end_date"])])
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
        "--time-range",
        str(time_window["requested"]),
        "--start-published-date",
        str(time_window["start_published_date"]),
        "--end-published-date",
        str(time_window["end_published_date"]),
        "--output",
        str(exa_output),
    ]

    if args.dry_run:
        print("Resolved time window:")
        print(
            f"{time_window['label']} | request={time_window['requested']} | "
            f"Tavily={time_window['tavily_time_range'] or (str(time_window['start_date']) + ' -> ' + str(time_window['end_date']))} | "
            f"Exa={time_window['start_published_date']} -> {time_window['end_published_date']}"
        )
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
