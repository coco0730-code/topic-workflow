---
name: tavily-industry-news
description: 使用 Tavily Search 抓取、筛选并汇总行业资讯。适用于 Codex 制作每日或每周行业简报、追踪 AI/工具/产品关键词、抓取实时网页来源链接，或将 Tavily 搜索结果整理为简明的中文 Markdown 报告。
---

# Tavily 行业资讯

## 概述

使用本技能可以通过 Tavily 抓取最新行业信息，保留来源链接，去除明显重复内容，并整理为简短的中文简报。在搭建更重的爬虫、数据库或仪表盘之前，建议先用本技能做轻量级的每日监控。

## 工作流程

1. 明确用户需求中的主题、关键词、时间窗口和输出格式。
2. 使用 `scripts/daily_tavily_news.py` 抓取网页结果。API key 统一存放在项目根目录 `config/api-keys.json`。
3. 检查生成的 Markdown 文件和其中的来源链接。
4. 整理为中文简报，使用清晰的章节，例如 `今日重点`、`产品/技术`、`融资/公司`、`值得关注` 和 `来源`。
5. 如果用户希望自动化，建议先让一次性报告流程跑通，再考虑接入 cron、launchd、n8n、飞书 Webhook、邮件或 Notion 等方式。

## 快速开始

将 API key 写入项目根目录的 `config/api-keys.json`：

```json
{
  "tavily": {
    "apiKey": "..."
  }
}
```

运行时必须显式指定至少一个关键词：

```bash
python3 .agents/skills/tavily-industry-news/scripts/daily_tavily_news.py \
  --query "epa鱼油"
```

也可以指定多个关键词：

```bash
python3 .agents/skills/tavily-industry-news/scripts/daily_tavily_news.py \
  --query "AI video generation latest news" \
  --query "AI short drama tools latest news" \
  --max-results 5 \
  --output outputs/today.md
```

脚本会输出包含 Tavily AI 总结、标题、URL、摘要、相关度评分以及可选发布时间的 Markdown 文件。该文件仅作为原始素材，除非用户明确要求只保留原始搜索结果，否则最终的编辑与整合工作请在 Codex 中完成。

## 报告风格

中文行业简报应保持务实、不夸张的语调。开头先讲清楚：发生了什么、为何重要、下一步值得关注什么。

除非用户另有要求，建议使用以下简洁结构：

```markdown
# 行业资讯简报

## 今日重点
- ...

## 产品/技术
- ...

## 融资/公司
- ...

## 值得关注
- ...

## 来源
- [标题](URL)
```

## 资源

使用 `scripts/daily_tavily_news.py` 进行 Tavily 抓取。该脚本不依赖任何第三方 Python 包，API key 统一存放在项目根目录 `config/api-keys.json` 中。
