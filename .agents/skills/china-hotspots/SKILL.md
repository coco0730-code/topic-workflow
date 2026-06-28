---
name: china-hotspots
description: 抓取和整理国内平台热点信号，适用于新媒体选题前采集抖音、微博、百度、头条、知乎、36氪、掘金等国内热榜，以及补充小红书、公众号、对标账号观察记录。
---

# China Hotspots

## 概述

使用本技能采集国内平台的实时热点和用户讨论信号，作为 Tavily 行业新闻之外的选题素材。它适合新媒体日更选题、内容角度判断、平台语境观察，以及把国外行业新闻转成国内用户更关心的话题。

## 工作流程

1. 读取 `config/keywords.json` 中的 `dailyQueries`、`platforms` 和 `chinaHotspots` 配置。
2. 运行 `scripts/china_hotspots.py` 生成 `outputs/YYYY-MM-DD/china-hotspots-source.md`。
3. 将该文件与 Tavily 的 `news-source.md` 一起交给 Agent1 做热点归纳。
4. 选题时优先寻找三类信号：
   - 国内用户已经在讨论的痛点、情绪、误区和高频问题。
   - 能和公司业务结合的行业新闻、工具更新、竞品动态。
   - 小红书、抖音、公众号适合展开的表达角度。

## 数据源策略

默认使用 DailyHotApi 兼容接口，基址从 `config/keywords.json` 的 `chinaHotspots.apiBaseUrl` 读取。推荐自建或部署一份 DailyHotApi，避免公开示例站不稳定。

适合直接接入的热榜源：

- 抖音：`douyin`
- 微博：`weibo`
- 百度：`baidu`
- 今日头条：`toutiao`
- 知乎：`zhihu`
- 36 氪：`36kr`
- 掘金：`juejin`
- B 站：`bilibili`
- IT之家：`ithome`
- 澎湃：`thepaper`

小红书没有稳定公开热榜接口时，不要硬编造数据。可以在 `manualSources` 中记录人工补充方式，例如行业关键词搜索、对标账号爆款笔记、品牌账号评论区问题，再由 Agent1 合并分析。

## 命令

```bash
python3 .agents/skills/china-hotspots/scripts/china_hotspots.py \
  --output outputs/$(date +%F)/china-hotspots-source.md
```

只检查配置和将要抓取的平台：

```bash
python3 .agents/skills/china-hotspots/scripts/china_hotspots.py --dry-run
```

## 输出原则

- 保留平台、标题、链接、热度、排名和更新时间。
- API 不可用时生成可读的降级文件，并提示需要配置的内容，不中断整体工作流。
- 对小红书、公众号等非公开热榜源，只记录“待人工补充”或用户提供的链接，不编造热度。
- Agent1 后续必须对事实和数据标注“待核实”，不要把热榜标题直接当作事实结论。
