---
name: social-media-workflow
description: 运行公司新媒体选题与内容生产工作流。适用于用户要求“跑今天的新媒体选题工作流”、根据行业热点生成选题、结合公司知识库提出发文方向、写文章、审核、生成配图或视频提示词，以及串联 Agent1 到 Agent6 的日常运营流程。
---

# Social Media Workflow

## 入口

当用户说“跑今天的新媒体选题工作流”或类似表达时，按 `workflows/daily-social-media-workflow.md` 执行。

如果当前项目还是空模板，或 `knowledge/` 与 `config/keywords.json` 仍是待初始化状态，不要直接开始每日流程，先引导用户调用 `.agents/skills/knowledge-bootstrap/SKILL.md` 初始化项目知识库和搜索关键词。

## 必读文件

开始前读取：

- `workflows/daily-social-media-workflow.md`
- `config/keywords.json`
- `config/workflow.json`
- `knowledge/company-profile.md`
- `knowledge/products.md`
- `knowledge/target-users.md`
- `knowledge/brand-voice.md`
- `knowledge/content-rules.md`
- `knowledge/competitors.md`
- `knowledge/past-content.md`

按阶段读取：

- Agent1：`prompts/agent1-news-search.md`，并读取 `.agents/skills/china-hotspots/SKILL.md`
- Agent2：`prompts/agent2-topic-analysis.md`
- Agent3：`prompts/agent3-article-writer.md`，并读取 `.agents/skills/humanizer/SKILL.md` 做去 AI 味处理
- Agent4：`prompts/agent4-reviewer.md`
- Agent5：`prompts/agent5-visual-prompt.md`
- Agent6：`prompts/agent6-image-generator.md`

## 执行规则

1. 每次运行先创建当天目录：`outputs/YYYY-MM-DD/`。
2. Agent1 使用 `scripts/run_daily_news.py` 生成 `news-source.md` 和 `china-hotspots-source.md`，再结合两类素材整理 `news.md`。
3. Agent2 必须结合 `knowledge/` 内容生成 `topic-options.md`，并等待人工选择。
4. 人工选定后，Agent3 写 `article-draft-v1.md`，写完后必须按 `.agents/skills/humanizer/SKILL.md` 处理标题、正文和评论区引导，让文章更自然、更像真人写的；输出文件只保留处理后的最终稿。
5. Agent4 审核；不通过则按审核意见让 Agent3 重写，最多 `config/workflow.json` 中的 `maxRewriteRounds` 轮。
6. Agent4 通过后，等待人工复审。
7. 人工复审通过后，Agent5 生成 `visual-prompts.md`。
8. 必须等待人工审核视觉提示词。
9. Agent6 只在人工确认视觉提示词后执行；做图时优先调用 `imagegen`，做视频时调用 `.agents/skills/agnes-video-v20/SKILL.md`。

## 输出原则

- 所有阶段产物都写入 `outputs/YYYY-MM-DD/`。
- 不要覆盖历史版本，草稿和审核文件按 `v1`、`v2`、`v3` 编号。
- 如果知识库仍是 TODO 模板，必须在选题建议里标注“知识库待补充”，但仍然给出可执行的下一步。
- 涉及事实、数据、新闻来源时保留链接。
