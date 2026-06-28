# topic-workflow

这是一个给 Codex 使用的新媒体内容工作流模板。

它不是全自动发稿工具，而是把“公司知识库 -> 热点采集 -> 选题 -> 写稿 -> 审核 -> 配图/视频提示词”这条内容生产链路整理成可复用的项目结构，适合公司新媒体、品牌内容、行业账号和产品内容运营。

## 使用顺序

### 1. 配置 key

先填写本地 API 配置：

```text
config/api-keys.json
```

这个文件用于统一管理项目里会用到的 API key。开源使用时，建议每个项目单独维护自己的本地配置。

当前项目会读取这些 key：

- `tavily.apiKey`：用于 Agent1 抓取行业资讯。脚本会调用 Tavily Search API，把行业新闻、产品动态和趋势素材整理到每日输出里。
- `exa.apiKey`：用于补充中文网页关键词搜索。脚本会按 `config/keywords.json` 里的关键词和优先站点抓取网页结果，补充到每日热点素材里。
- `agnes.apiKey`：只在需要调用 Agnes Video V2.0 生成视频时使用。如果你暂时不生成视频，可以留空。

配置格式参考：

```json
{
  "tavily": {
    "apiKey": "你的 Tavily API key"
  },
  "exa": {
    "apiKey": "你的 Exa API key"
  },
  "agnes": {
    "apiKey": "你的 Agnes API key，可选"
  }
}
```

密钥文件是：

```text
config/api-keys.json
```

`config/api-keys.json` 已写入 `.gitignore`，后续你更新真实 key 不会被提交到 git。提交前也可以用下面命令确认：

```bash
git check-ignore -v config/api-keys.json
git status --short
```

申请与费用概览：

- Tavily：到 [Tavily Pricing](https://www.tavily.com/pricing) 注册并创建 API key。官方当前展示有免费额度，适合先跑通流程；超出免费额度后按套餐或按量计费，具体以 Tavily 官网为准。
- Exa：到 [Exa](https://exa.ai/) 注册并在 dashboard/API 页面创建 API key。Exa 用于搜索和网页内容抓取，通常有试用额度或按量计费，具体价格以 Exa 官方 pricing 页面为准。
- Agnes：到 [Agnes AI Docs](https://agnes-ai.com/doc) 或 Agnes 平台创建 API key。当前项目只在生成视频时用它；不做视频时可以不填。Agnes 官方 FAQ 提到核心模型可免费使用，但额度、限制和政策可能调整，实际以 Agnes 官方页面为准。

### 2. 初始化知识库

第一次使用时，先在 Codex 里说：

```text
根据我提供的文档、官网和公司介绍，初始化这个项目的知识库和搜索关键词
```

你可以提供：

- 公司/品牌/产品名
- 官网、产品页、案例页
- 公司介绍、产品资料、PDF、Word、PPT、TXT、Markdown 等文档
- 小红书、公众号、抖音等历史内容主页链接

上传 PDF、Word、PPT 等文档时，知识库初始化默认只提取文档里的文字内容；不会解析文档内嵌图片、视频、音频、附件、版式视觉信息或截图内容。若关键信息只在图片/扫描页里，需要你补充文字版，或明确要求 Codex 进行 OCR/媒体解析。

如果你提供小红书、抖音、公众号、视频号、B站、知乎、官网博客等历史内容主页或栏目链接，Codex 会默认使用你已登录的 Chrome 采集页面可见的已发布内容，再写入历史内容复盘；不需要额外说明“使用 Chrome”。只有页面实际显示未登录、无权限或内容不可见时，Codex 才会提示你处理登录/授权后继续。

如果信息不够，Codex 会继续追问。比如品牌语气、重点平台、竞品、行业关键词方向、历史内容链接等。

### 3. 运行工作流

知识库初始化完成后，在 Codex 里说：

```text
跑今天的新媒体选题工作流
```

工作流会依次完成热点采集、选题分析、文章草稿、审核、视觉提示词等步骤。中间需要人工选择选题、确认终稿和审核视觉提示词。

## 工作流介绍

```text
项目初始化阶段
↓
knowledge-bootstrap 初始化/补全知识库与搜索关键词
  ├─ 输入：官网、PDF/Word/PPT 等文档文字、公司介绍、产品页、历史内容主页、竞品链接
  ├─ 采集：社媒主页默认用已登录 Chrome 采集可见历史内容
  ├─ 输出：knowledge/ 下的公司画像、产品、用户、语气、内容规则、竞品、历史内容、来源记录
  └─ 同步：更新 config/keywords.json，作为后续热点采集关键词
↓
日常内容生产阶段
↓
Agent1 行业新闻与国内平台热点采集
  ├─ Tavily Search API：抓行业新闻、产品动态、融资/政策/研究报告等外部资讯
  ├─ Exa Search API：按关键词抓中文网页、行业媒体、竞品动态和内容线索
  ├─ DailyHotApi 兼容接口：抓抖音、百度、头条、知乎、36氪等国内热榜
  ├─ 人工来源：小红书、公众号、对标账号链接等非公开热榜来源可补充
  └─ 输出：news-source.md、china-web-search-source.md、china-hotspots-source.md、news.md
↓
Agent2 结合公司知识库做选题分析
  ├─ 输入：news.md + knowledge/ 公司知识库
  ├─ 判断：热点是否贴合目标用户痛点、产品能力、平台语境和内容边界
  └─ 输出：topic-options.md，包含推荐平台、内容形式、业务关联、风险点和 Top 5 选题
↓
人工选择今日发文方向
  └─ 输出：selected-topic.md，锁定今天要写的选题、平台和目标
↓
Agent3 写文章
  ├─ 输入：selected-topic.md、topic-options.md、knowledge/、事实来源
  ├─ 写作：生成标题、正文、配图建议、发布建议、评论区引导
  ├─ humanizer：去掉空泛 AI 味、套路化表达和机械总结，保留事实、链接和品牌语气
  └─ 输出：article-draft-v1.md
↓
Agent4 审核
  ├─ 审核项：事实准确性、来源完整性、业务相关性、用户价值、标题一致性、品牌语气、内容边界、合规风险、可发布性
  ├─ 不通过：写清必须修改的问题和给 Agent3 的重写指令，最多按 config/workflow.json 重写轮数执行
  ├─ 通过：进入人工复审
  └─ 输出：review-vN.md；通过后整理 article-final.md 或等待人工确认
↓
人工复审通过
↓
Agent5 生成配图/视频提示词
  ├─ 输入：通过审核的文章、品牌语气、内容规则
  ├─ 输出：visual-prompts.md，含封面、正文配图、短视频分镜、字幕和不要出现的元素
  └─ 注意：不使用未授权 logo、客户名、敏感数据或无法证实的画面
↓
人工审核视觉提示词
↓
Agent6 调 imagegen 生图，或调 agnes-video-v20 生视频
  ├─ imagegen：生成封面图、正文配图等静态素材
  ├─ agnes-video-v20：只在确认需要视频且配置了 agnes.apiKey 时生成视频
  └─ 输出：outputs/YYYY-MM-DD/assets/ 和 assets/final-prompts.md
↓
人工最终确认发布
```

## 配置说明

### `config/api-keys.json`

本地 API key 配置入口。

### `config/keywords.json`

热点采集关键词配置。初始化知识库后会根据公司、产品、行业和重点平台补充。

### `config/workflow.json`

工作流行为配置，例如最大重写轮数、默认平台、是否需要人工确认等。

## 输出目录

日常运行产物会写到：

```text
outputs/YYYY-MM-DD/                 # 当天内容生产输出目录
├── news.md                         # 汇总后的今日热点素材
├── news-source.md                  # 原始行业新闻来源
├── china-web-search-source.md      # 国内网页搜索来源
├── china-hotspots-source.md        # 国内平台热榜来源
├── topic-options.md                # 今日候选选题
├── selected-topic.md               # 人工选中的发文方向
├── article-draft-v1.md             # 第一版文章草稿
├── review-v1.md                    # 第一轮审核意见
├── article-final.md                # 最终文章稿
├── visual-prompts.md               # 配图/视频提示词
└── assets/                         # 图片、视频等视觉素材
```

## 项目目录

```text
topic-workflow
├── README.md                       # 项目说明
├── AGENTS.md                       # Codex 项目协作规则
├── .agents/                        # Codex 可调用的技能目录
│   └── skills/
│       ├── social-media-workflow/  # 串联每日新媒体内容工作流
│       ├── knowledge-bootstrap/    # 初始化/补全知识库与搜索关键词
│       ├── past-content-collector/ # 从账号主页采集历史内容并复盘
│       ├── tavily-industry-news/   # 抓取行业资讯
│       ├── china-hotspots/         # 抓取国内平台热点
│       ├── humanizer/              # 文章去 AI 味润色
│       └── agnes-video-v20/        # 调用 Agnes 生成视频
├── config/                         # 项目配置
│   ├── api-keys.json               # 本地 API key
│   ├── keywords.json               # 热点采集关键词
│   └── workflow.json               # 工作流规则配置
├── knowledge/                      # 公司/品牌知识库
│   ├── brand-voice.md              # 品牌语气
│   ├── company-profile.md          # 公司画像
│   ├── competitors.md              # 竞品与对标账号
│   ├── content-rules.md            # 内容边界与审核规则
│   ├── past-content.md             # 历史内容复盘
│   ├── products.md                 # 产品与服务资料
│   ├── source-notes.md             # 来源记录、冲突记录与补充说明
│   └── target-users.md             # 目标用户画像
├── prompts/                        # 各阶段 Agent 提示词
│   ├── agent1-news-search.md       # 热点采集提示词
│   ├── agent2-topic-analysis.md    # 选题分析提示词
│   ├── agent3-article-writer.md    # 文章写作提示词
│   ├── agent4-reviewer.md          # 审核提示词
│   ├── agent5-visual-prompt.md     # 视觉提示词生成提示词
│   └── agent6-image-generator.md   # 生图/视频提示词
├── scripts/                        # 可直接运行的辅助脚本
│   ├── exa_china_web_search.py     # 国内网页搜索脚本
│   ├── init_daily_run.py           # 初始化当天输出目录
│   └── run_daily_news.py           # 运行每日新闻/热点采集
├── workflows/                      # 工作流说明
│   └── daily-social-media-workflow.md # 每日新媒体工作流
└── outputs/                        # 每日运行输出
    └── YYYY-MM-DD/                 # 按日期归档的内容产物
```
