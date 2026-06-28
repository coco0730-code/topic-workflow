# 每日新媒体选题与内容生产工作流

## 目标
解决公司新媒体运营每天不知道发什么的问题。系统先采集行业热点，再结合公司知识库生成选题建议，由人工选择方向后进入写作、审核、视觉提示词和素材生成。

## 前置条件

如果这是一个空项目，先不要直接跑每日工作流，而是先用 `knowledge-bootstrap` 初始化：

- `knowledge/`
- `config/keywords.json`

知识库和关键词没有初始化完成前，热点采集和选题结果会明显偏空。

## 总流程

```text
Agent1 行业新闻与国内平台热点采集
  ├─ Tavily Search API：抓行业新闻、产品动态、融资/政策/研究报告等外部资讯
  ├─ Exa Search API：按关键词抓中文网页、行业媒体、竞品动态和内容线索
  ├─ DailyHotApi 兼容接口：抓抖音、百度、头条、知乎、36氪等国内热榜
  └─ 输出：news-source.md、china-web-search-source.md、china-hotspots-source.md、news.md
↓
Agent2 结合公司知识库做选题分析
  ├─ 判断热点与目标用户、产品能力、品牌语气和内容边界的匹配度
  └─ 输出 Top 5 选题、风险点、推荐平台和首推方向
↓
人工选择今日发文方向
↓
Agent3 写文章
  ├─ 生成标题、正文、配图建议、发布建议和评论区引导
  ├─ 使用 humanizer 技能处理，让文章更像真人写的
  └─ 保留事实来源、数据和链接
↓
Agent4 审核
  ├─ 审核事实准确性、来源完整性、业务相关性、用户价值、标题一致性
  ├─ 审核品牌语气、内容边界、合规风险和可发布性
  ├─ 不通过：返回 Agent3 重写，最多 3 轮
  ├─ 通过：进入人工复审
  └─ 输出 review-vN.md，给出通过/不通过和明确重写指令
↓
人工复审通过
↓
Agent5 生成配图/视频提示词
  ├─ 生成封面图、正文配图和短视频分镜提示词
  └─ 标注必须出现、不要出现、尺寸、风格和风险元素
↓
人工审核视觉提示词
↓
Agent6 调 `imagegen` 生图，或调 `agnes-video-v20` 生视频
  ├─ imagegen 用于静态图片
  └─ agnes-video-v20 仅在确认需要视频且配置 Agnes key 时使用
↓
人工最终确认发布
```

## 固定口令

### 开始每日选题
```text
跑今天的新媒体选题工作流
```

### 选题后写文章
```text
选第 X 个，写文章
```

### 自动审核并重写
```text
审核并自动改到通过，最多 3 轮
```

### 生成视觉提示词
```text
通过，生成配图提示词
```

### 生成素材
```text
用第 X 个提示词调用 imagegen 做图
```

## 每日输出目录

```text
outputs/YYYY-MM-DD/
├── news.md
├── news-source.md
├── china-web-search-source.md
├── china-hotspots-source.md
├── topic-options.md
├── selected-topic.md
├── article-draft-v1.md
├── review-v1.md
├── article-draft-v2.md
├── review-v2.md
├── article-final.md
├── visual-prompts.md
└── assets/
```

## 人工介入点
- 选择今日选题
- 复审文章最终稿
- 确认视觉提示词
- 确认最终素材

## Agent3 写作约束
- Agent3 输出 `article-draft-vN.md` 前，必须使用 `.agents/skills/humanizer/SKILL.md` 对文章做去 AI 味处理。
- 去 AI 味处理只影响标题、正文、评论区引导等对外文案，不改变事实来源、数据、链接和选题判断。
- 输出文件只保留处理后的最终稿，不保留 humanizer 的中间审稿过程。
