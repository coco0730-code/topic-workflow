#!/usr/bin/env python3
"""把结构化 facts 合并写入 knowledge/ 目录。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
KNOWLEDGE_DIR = ROOT / "knowledge"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge structured facts into project knowledge files.")
    parser.add_argument("--facts-file", type=Path, required=True, help="结构化 facts JSON 文件。")
    parser.add_argument("--mode", choices=["bootstrap", "merge", "refresh"], default="merge")
    parser.add_argument("--dry-run", action="store_true", help="只打印将写入的文件，不真正落盘。")
    return parser.parse_args(argv)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("facts file top-level value must be an object.")
    return data


def write_text(path: Path, text: str, dry_run: bool) -> None:
    if dry_run:
        print(f"=== {path} ===")
        print(text)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def is_placeholder(content: str) -> bool:
    lowered = content.lower()
    signals = ["待补充", "当前状态", "暂无可直接使用", "建议补充"]
    return any(signal in content for signal in signals) or len(lowered.strip()) < 80


def bullets(items: list[str], fallback: str = "- 待补充") -> str:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    if not cleaned:
        return fallback
    return "\n".join(f"- {item}" for item in cleaned)


def render_company_profile(facts: dict[str, Any]) -> str:
    company = facts.get("company") if isinstance(facts.get("company"), dict) else {}
    return f"""# 公司画像

## 公司名称
{company.get("name") or "待补充"}

## 品牌/产品
{company.get("brand") or "待补充"}

## 官网
{company.get("website") or "待补充"}

## 公司一句话介绍
{company.get("one_liner") or "待补充"}

## 核心定位
{bullets(company.get("positioning") or [])}

## 核心业务
{bullets(company.get("businesses") or [])}

## 核心团队与能力背书
{bullets(company.get("proof_points") or [])}

## 不希望外界误解的点
{bullets(company.get("public_constraints") or [], "- 待补充")}
"""


def render_products(facts: dict[str, Any]) -> str:
    products = facts.get("products") if isinstance(facts.get("products"), list) else []
    if not products:
        return "# 产品与服务资料\n\n## 当前状态\n- 待补充\n"

    sections = ["# 产品与服务资料", "", "## 产品/服务清单", ""]
    for product in products:
        if not isinstance(product, dict):
            continue
        name = product.get("name") or "未命名产品"
        sections.extend(
            [
                f"### {name}",
                f"- 面向用户：{', '.join(product.get('audience') or []) or '待补充'}",
                "- 核心痛点：",
                bullets(product.get("pain_points") or []),
                "- 核心功能：",
                bullets(product.get("features") or []),
                "- 典型适用场景：",
                bullets(product.get("scenarios") or []),
                "- 客户收益：",
                bullets(product.get("benefits") or []),
                "- 差异化：",
                bullets(product.get("differentiators") or []),
                "",
            ]
        )
    return "\n".join(sections).rstrip() + "\n"


def render_target_users(facts: dict[str, Any]) -> str:
    users = facts.get("users") if isinstance(facts.get("users"), list) else []
    if not users:
        return "# 目标用户\n\n## 当前状态\n- 待补充\n"

    sections = ["# 目标用户", "", "## 核心用户画像", ""]
    for idx, user in enumerate(users, start=1):
        if not isinstance(user, dict):
            continue
        sections.extend(
            [
                f"### 用户类型 {idx}：{user.get('type') or '待命名'}",
                f"- 身份/岗位：{', '.join(user.get('roles') or []) or '待补充'}",
                f"- 所在行业：{', '.join(user.get('industries') or []) or '待补充'}",
                "- 主要痛点：",
                bullets(user.get("pain_points") or []),
                "- 平时关注：",
                bullets(user.get("interests") or []),
                "- 决策动机：",
                bullets(user.get("decision_drivers") or []),
                "",
            ]
        )
    return "\n".join(sections).rstrip() + "\n"


def render_brand_voice(facts: dict[str, Any]) -> str:
    voice = facts.get("brand_voice") if isinstance(facts.get("brand_voice"), dict) else {}
    tone_guess = voice.get("tone_guess") or []
    status = voice.get("status") or "confirmed"
    return f"""# 品牌语气

## 整体风格
{bullets(voice.get("style") or [])}

## 推荐表达
{bullets(voice.get("preferred_phrases") or [], "- 待补充")}

## 不推荐表达
{bullets(voice.get("avoid_phrases") or [], "- 待补充")}

## 表达补充
{bullets(tone_guess, "- 暂无")}

## 状态
- 当前状态：{status}
"""


def render_content_rules(facts: dict[str, Any]) -> str:
    rules = facts.get("content_rules") if isinstance(facts.get("content_rules"), dict) else {}
    return f"""# 内容规则

## 可写方向
{bullets(rules.get("allowed") or [])}

## 谨慎方向
{bullets(rules.get("caution") or [], "- 待补充")}

## 禁止方向
{bullets(rules.get("forbidden") or [], "- 待补充")}

## 审核红线
{bullets(rules.get("red_lines") or [], "- 待补充")}
"""


def render_competitors(facts: dict[str, Any]) -> str:
    competitors = facts.get("competitors") if isinstance(facts.get("competitors"), dict) else {}
    confirmed = competitors.get("confirmed") or []
    candidates = competitors.get("candidates") or []
    notes = competitors.get("notes") or []
    return f"""# 竞品与对标账号

## 已确认竞品
{bullets(confirmed, "- 暂无")}

## 候选竞品
{bullets(candidates, "- 暂无候选")}

## 补充说明
{bullets(notes, "- 待补充")}
"""


def render_past_content(facts: dict[str, Any]) -> str:
    past = facts.get("past_content") if isinstance(facts.get("past_content"), dict) else {}
    available = bool(past.get("available"))
    by_platform = past.get("by_platform") if isinstance(past.get("by_platform"), list) else []
    items = past.get("items") if isinstance(past.get("items"), list) else []
    notes = past.get("notes") or []
    if not available:
        return f"""# 历史内容复盘

## 当前状态
- 暂无可直接使用的历史内容数据

## 按平台归档
- 待补充账号主页或内容列表链接

## 建议补充
{bullets(notes or ['按平台补充近 20-30 条历史内容标题、链接、发布时间和互动数据'])}
"""

    lines = ["# 历史内容复盘", "", "## 按平台归档", ""]
    if by_platform:
        for platform_data in by_platform:
            if not isinstance(platform_data, dict):
                continue
            platform = platform_data.get("platform") or "平台未标注"
            account = platform_data.get("account") or "待补充"
            homepage_url = platform_data.get("homepage_url") or "待补充"
            collected_at = platform_data.get("collected_at") or "待补充"
            platform_items = platform_data.get("items") if isinstance(platform_data.get("items"), list) else []
            observations = platform_data.get("observations") if isinstance(platform_data.get("observations"), list) else []

            lines.extend(
                [
                    f"### {platform}",
                    f"- 账号/栏目：{account}",
                    f"- 主页/列表链接：{homepage_url}",
                    f"- 采集时间：{collected_at}",
                    "",
                    "#### 已采集内容",
                    "",
                ]
            )
            if platform_items:
                for idx, item in enumerate(platform_items, start=1):
                    if isinstance(item, dict):
                        title = item.get("title") or "未命名内容"
                        url = item.get("url") or "待补充"
                        published_at = item.get("published_at") or "待补充"
                        content_type = item.get("content_type") or "未显示"
                        angle = item.get("angle") or "待分析"
                        performance_note = item.get("performance_note") or "待观察"
                        topics = item.get("topics") if isinstance(item.get("topics"), list) else []
                        metrics = item.get("metrics") if isinstance(item.get("metrics"), dict) else {}
                        metric_parts = [
                            f"{label}：{metrics.get(key)}"
                            for key, label in [
                                ("views", "阅读/播放"),
                                ("likes", "点赞"),
                                ("comments", "评论"),
                                ("favorites", "收藏"),
                                ("shares", "转发"),
                            ]
                            if metrics.get(key)
                        ]
                        lines.extend(
                            [
                                f"{idx}. {title}",
                                f"   - 链接：{url}",
                                f"   - 发布时间：{published_at}",
                                f"   - 内容类型：{content_type}",
                                f"   - 互动数据：{'; '.join(metric_parts) if metric_parts else '未显示'}",
                                f"   - 内容角度：{angle}",
                                f"   - 主题标签：{', '.join(str(topic) for topic in topics) if topics else '待补充'}",
                                f"   - 初步表现判断：{performance_note}",
                            ]
                        )
                    else:
                        lines.append(f"{idx}. {item}")
            else:
                lines.append("- 暂无采集内容")

            lines.extend(["", "#### 初步观察", "", bullets(observations, "- 待补充"), ""])
    else:
        lines.append("- 暂无按平台归档数据")

    if items:
        lines.extend(["", "## 未分平台内容", ""])
        for idx, item in enumerate(items, start=1):
            lines.append(f"{idx}. {item}")
    lines.extend(["", "## 补充说明", "", bullets(notes, "- 暂无")])
    return "\n".join(lines).rstrip() + "\n"


def render_source_notes(facts: dict[str, Any], mode: str) -> str:
    sources = facts.get("sources") if isinstance(facts.get("sources"), list) else []
    questions = facts.get("open_questions") if isinstance(facts.get("open_questions"), list) else []
    lines = ["# 知识库来源记录", "", "## 本次更新模式", f"- {mode}", "", "## 已使用来源", ""]
    if sources:
        for item in sources:
            if not isinstance(item, dict):
                continue
            label = item.get("label") or item.get("type") or "未命名来源"
            ref = item.get("path_or_url") or "待补充"
            note = item.get("notes") or ""
            lines.append(f"- {label}：`{ref}`" + (f" - {note}" if note else ""))
    else:
        lines.append("- 待补充")

    lines.extend(["", "## 补充记录", ""])
    if questions:
        lines.extend(f"- {str(question).strip()}" for question in questions if str(question).strip())
    else:
        lines.append("- 暂无")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    facts = load_json(args.facts_file)

    outputs = {
        KNOWLEDGE_DIR / "company-profile.md": render_company_profile(facts),
        KNOWLEDGE_DIR / "products.md": render_products(facts),
        KNOWLEDGE_DIR / "target-users.md": render_target_users(facts),
        KNOWLEDGE_DIR / "brand-voice.md": render_brand_voice(facts),
        KNOWLEDGE_DIR / "content-rules.md": render_content_rules(facts),
        KNOWLEDGE_DIR / "competitors.md": render_competitors(facts),
        KNOWLEDGE_DIR / "past-content.md": render_past_content(facts),
        KNOWLEDGE_DIR / "source-notes.md": render_source_notes(facts, args.mode),
    }

    for path, text in outputs.items():
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        final_text = text
        if args.mode == "merge" and current.strip() and not is_placeholder(current):
            final_text = current.rstrip() + "\n\n## 本次补充\n" + text.strip() + "\n"
        write_text(path, final_text, args.dry_run)

    if not args.dry_run:
        print("Updated knowledge files:")
        for path in outputs:
            print(path)
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
