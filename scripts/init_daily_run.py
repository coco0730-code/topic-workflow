#!/usr/bin/env python3
"""初始化每日新媒体工作流输出目录。"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path


FILES = {
    "news.md": "# 今日行业新闻热点\n\n",
    "topic-options.md": "# 今日新媒体选题建议\n\n",
    "selected-topic.md": "# 人工选择的今日选题\n\n",
    "run-log.md": "# 工作流运行记录\n\n",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create daily workflow output folder.")
    parser.add_argument("--date", help="Date in YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--root", default="outputs", help="Output root folder.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    date = args.date or dt.datetime.now().astimezone().strftime("%Y-%m-%d")
    output_dir = Path(args.root) / date
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    for filename, content in FILES.items():
        path = output_dir / filename
        if not path.exists():
            path.write_text(content, encoding="utf-8")

    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

