#!/usr/bin/env python3
"""使用 Exa Search API 抓取中文关键词网页搜索结果。"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import textwrap
import urllib.error
import urllib.request
from html.parser import HTMLParser
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
    parser.add_argument("--time-range", help="Logical recency window label, for logging only. Example: 48h, 7d, week.")
    parser.add_argument("--start-published-date", help="Filter Exa results published on/after this ISO-8601 datetime.")
    parser.add_argument("--end-published-date", help="Filter Exa results published on/before this ISO-8601 datetime.")
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
    verify_dates_setting = exa_config.get("verifyDates", True)
    verify_dates = bool(verify_dates_setting) if not isinstance(verify_dates_setting, str) else verify_dates_setting.strip().lower() not in {"false", "0", "no", "off"}
    verify_timeout = int(exa_config.get("verifyDateTimeoutSeconds") or 6)
    verify_max_bytes = int(exa_config.get("verifyDateMaxBytes") or 240_000)
    return {
        "enabled": bool(exa_config.get("enabled", True)),
        "queries": queries,
        "include_domains": [str(domain).strip() for domain in include_domains if str(domain).strip()],
        "max_results": max(1, max_results),
        "search_type": str(exa_config.get("type") or "auto"),
        "text_max_characters": int(exa_config.get("textMaxCharacters") or 900),
        "time_range": str(args.time_range or exa_config.get("timeRange") or config.get("timeRange") or "").strip(),
        "start_published_date": str(args.start_published_date or exa_config.get("startPublishedDate") or "").strip(),
        "end_published_date": str(args.end_published_date or exa_config.get("endPublishedDate") or "").strip(),
        "verify_dates": verify_dates,
        "verify_timeout": max(1, verify_timeout),
        "verify_max_bytes": max(8_000, verify_max_bytes),
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
    if settings["start_published_date"]:
        payload["startPublishedDate"] = settings["start_published_date"]
    if settings["end_published_date"]:
        payload["endPublishedDate"] = settings["end_published_date"]

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
        f"- 时间窗口：{settings['time_range'] or '未指定（默认近7天应由上游传入）'}",
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


META_DATE_KEYWORDS: tuple[str, ...] = (
    "article:published_time",
    "apub:time",
    "og:published_time",
    "pubdate",
    "datepublished",
    "date_published",
    "articlepublished",
    "weibo:article:create_at",
    "apubtime",
    "publish_time",
    "publish-time",
    "publishdate",
    "releasedate",
)


class _DateCandidateCollector(HTMLParser):
    """Collects possible publication-date signals from the article HTML head."""

    def __init__(self) -> None:
        super().__init__()
        self.meta_dates: list[tuple[str, str]] = []
        self.time_datetimes: list[str] = []
        self.kr_item_time_buffer: list[str] = []
        self._capture_kr = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_d = {key: (value or "") for key, value in attrs}
        if tag == "meta":
            prop = (attr_d.get("property") or attr_d.get("name") or attr_d.get("itemprop") or "").lower()
            content = (attr_d.get("content") or "").strip()
            if prop and content:
                self.meta_dates.append((prop, content))
        elif tag == "time":
            datetime_value = (attr_d.get("datetime") or "").strip()
            if datetime_value:
                self.time_datetimes.append(datetime_value)
        elif tag == "span":
            cls = attr_d.get("class", "")
            if "title-icon-item" in cls and "item-time" in cls:
                self._capture_kr = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "span" and self._capture_kr:
            self._capture_kr = False

    def handle_data(self, data: str) -> None:
        if self._capture_kr:
            self.kr_item_time_buffer.append(data)


def normalize_published_date(value: str | None) -> str | None:
    """Normalize assorted date strings to ``YYYY-MM-DD HH:MM`` Beijing-time string.

    Returns ``None`` if the value does not look like a usable date.
    """
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    match = re.match(
        r"^(\d{4})-(\d{1,2})-(\d{1,2})[T ](\d{1,2}):(\d{1,2})(?::(\d{1,2}))?(?:\.\d+)?(Z|[+-]\d{2}:?\d{2})?$",
        text,
    )
    if match:
        year, month, day, hour, minute, second, tz = match.groups()
        try:
            base = dt.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second or 0))
        except ValueError:
            return None
        offset = dt.timedelta(0)
        if tz == "Z":
            offset = dt.timedelta(hours=8)
        elif tz and (tz.startswith("+") or tz.startswith("-")):
            sign = 1 if tz[0] == "+" else -1
            digits = tz[1:].replace(":", "")
            try:
                oh = int(digits[0:2])
                om = int(digits[2:4]) if len(digits) >= 4 else 0
            except ValueError:
                return None
            offset = dt.timedelta(hours=8) - dt.timedelta(minutes=sign * (oh * 60 + om))
        return (base + offset).strftime("%Y-%m-%d %H:%M")
    match = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?:[ T](\d{1,2}):(\d{2})(?::\d{2})?)?$", text)
    if match:
        year, month, day, hour, minute = match.groups()
        try:
            base = dt.datetime(int(year), int(month), int(day))
        except ValueError:
            return None
        if hour is None:
            return base.strftime("%Y-%m-%d 00:00")
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d} {int(hour):02d}:{int(minute):02d}"
    match = re.match(
        r"^(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{1,2})(?::\d{1,2})?$",
        text,
    )
    if match:
        year, month, day, hour, minute = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d} {int(hour):02d}:{int(minute):02d}"
    match = re.match(r"^(\d{4})年(\d{1,2})月(\d{1,2})日$", text)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d} 00:00"
    return None


def fetch_real_publish_date(
    url: str,
    timeout: int = 6,
    max_bytes: int = 240_000,
) -> tuple[str | None, str, str]:
    """Try to recover the real publication date by fetching the page HTML.

    Returns ``(normalized_date, source_label, raw_value_or_error)``.
    ``source_label`` is one of:
      * ``"page"`` (visible text, e.g. 36kr ``title-icon-item item-time``),
      * ``"meta"`` (HTML ``<meta>`` tag),
      * ``"jsonld"`` (JSON-LD ``datePublished``),
      * ``"time"`` (``<time datetime>``),
      * ``""`` when nothing useful was found.

    The third tuple element is either the original raw date string on success or
    a short error description on failure.
    """
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(max_bytes).decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return None, "", f"fetch failed: {exc}"

    parser = _DateCandidateCollector()
    try:
        parser.feed(raw)
    except Exception:
        pass

    # 1) 36kr style: `<span class="title-icon-item item-time">·2026年06月25日 14:15</span>`
    kr_text = "".join(parser.kr_item_time_buffer)
    match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{1,2})(?::\d{1,2})?", kr_text)
    if match:
        raw_value = match.group(0)
        normalized = normalize_published_date(raw_value)
        if normalized:
            return normalized, "page", raw_value

    # 2) <meta> tags with date-like content. 36kr's `article:published_time` is a
    #    template default (today's crawl date), so we only trust it when the
    #    content clearly looks like a past date.
    today_prefix = dt.datetime.now().astimezone().strftime("%Y-%m-%d")
    for prop, content in parser.meta_dates:
        if not any(keyword in prop for keyword in META_DATE_KEYWORDS):
            continue
        candidate = content.strip()
        if not re.match(r"\d{4}-\d{1,2}-\d{1,2}", candidate) and not re.match(r"\d{4}/\d{1,2}/\d{1,2}", candidate):
            continue
        normalized = normalize_published_date(candidate)
        if normalized and not normalized.startswith(today_prefix):
            return normalized, "meta", candidate

    # 3) JSON-LD `datePublished`
    match = re.search(r'"datePublished"\s*:\s*"([^"]+)"', raw)
    if match:
        normalized = normalize_published_date(match.group(1))
        if normalized:
            return normalized, "jsonld", match.group(1)

    # 4) `<time datetime="...">`
    for value in parser.time_datetimes:
        normalized = normalize_published_date(value)
        if normalized:
            return normalized, "time", value

    return None, "", ""


class DateVerifier:
    """Per-run cache wrapper around ``fetch_real_publish_date``."""

    def __init__(self, enabled: bool, timeout: int = 6, max_bytes: int = 240_000) -> None:
        self.enabled = enabled
        self.timeout = timeout
        self.max_bytes = max_bytes
        self._cache: dict[str, tuple[str | None, str, str]] = {}

    def verify(self, url: str) -> tuple[str | None, str, str]:
        if not self.enabled:
            return None, "", "verifier disabled"
        if url in self._cache:
            return self._cache[url]
        result = fetch_real_publish_date(url, timeout=self.timeout, max_bytes=self.max_bytes)
        self._cache[url] = result
        return result


def render_markdown(
    results_by_query: list[tuple[str, dict[str, Any] | None, str]],
    settings: dict[str, Any],
    verifier: "DateVerifier | None" = None,
) -> str:
    now = dt.datetime.now().astimezone()
    source_count = 0
    lines = [
        f"# Exa 中文关键词搜索素材 - {now:%Y-%m-%d}",
        "",
        f"- 生成时间：{now:%Y-%m-%d %H:%M:%S %Z}",
        f"- 查询数：{len(results_by_query)}",
        "- 去重来源数：0",
        f"- 每个关键词上限：{settings['max_results']}",
        f"- 时间窗口：{settings['time_range'] or '未指定'}",
        "",
    ]
    if settings["start_published_date"] or settings["end_published_date"]:
        lines.append(
            f"- Exa 发布时间过滤：{settings['start_published_date'] or '无限制'} -> {settings['end_published_date'] or '无限制'}"
        )
        lines.append("")
    if settings["verify_dates"]:
        lines.append("- 二次核实：开启；每条结果抓一次原页面取真日期，Exa 估算日期作为对照保留。")
    else:
        lines.append("- 二次核实：关闭；发布时间直接采用 Exa 返回值，准确性较低。")
    lines.append("")
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
            exa_published_raw = str(item.get("publishedDate") or "").strip()
            exa_published_label = normalize_published_date(exa_published_raw) if exa_published_raw else None
            verified_date: str | None = None
            verified_source = ""
            verified_raw = ""
            if verifier is not None and settings["verify_dates"]:
                verified_date, verified_source, verified_raw = verifier.verify(url)
            summary = str(item.get("summary") or "").strip()
            highlights = item.get("highlights") if isinstance(item.get("highlights"), list) else []
            text = str(item.get("text") or "").strip()

            lines.append(f"- [{title}]({url})")
            if verified_date:
                source_text = {
                    "page": "页面正文",
                    "meta": "页面 <meta>",
                    "jsonld": "页面 JSON-LD",
                    "time": "页面 <time>",
                }.get(verified_source, "页面提取")
                lines.append(f"  - 发布时间：{verified_date}（{source_text}；请以原链接为准）")
                if exa_published_label and exa_published_label != verified_date:
                    lines.append(f"  - Exa 估算原值：{exa_published_label}（与实际不一致，仅供参考）")
            elif exa_published_label:
                lines.append(f"  - 发布时间：{exa_published_label}（Exa 估算，建议打开链接核实）")
            elif exa_published_raw:
                lines.append(f"  - 发布时间：{exa_published_raw or '未提供'}（Exa 原始字符串无法解析）")
            else:
                lines.append(f"  - 发布时间：未提供，建议打开链接核实")
            if verifier is not None and settings["verify_dates"] and not verified_date and verified_raw.startswith("fetch failed"):
                lines.append(f"  - 页面日期抓取失败：{verified_raw}")
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
            "- Exa 的 `publishedDate` 是估算值，常与原页面真实日期不一致；脚本默认会自动用页面真日期覆盖。",
            "- 标有 `Exa 估算` 或 `未提供` 的日期，正式发布前需要打开原链接核实。",
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
        print(f"time_range={settings['time_range']}")
        print(f"start_published_date={settings['start_published_date']}")
        print(f"end_published_date={settings['end_published_date']}")
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

    verifier = DateVerifier(
        enabled=settings["verify_dates"],
        timeout=settings["verify_timeout"],
        max_bytes=settings["verify_max_bytes"],
    )
    output.write_text(render_markdown(results_by_query, settings, verifier), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
