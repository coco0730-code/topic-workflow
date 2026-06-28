---
name: knowledge-bootstrap
description: 根据用户提供的文档、公司名、品牌名、产品名、官网链接、历史内容账号主页或已有公司介绍，初始化或补充项目 `knowledge/` 目录，并补全 `config/keywords.json` 中的行业关键词。适用于 Codex 需要自动完善 `company-profile.md`、`products.md`、`target-users.md`、`brand-voice.md`、`content-rules.md`、`competitors.md`、`past-content.md`、`source-notes.md`，以及在信息不足时主动追问用户品牌语气、竞品、行业关键词和重点平台等关键资料。
---

# 知识库补全器

## 概述

使用本技能把零散来源整理成当前项目可消费的 `knowledge/` 目录内容，并同步完善 `config/keywords.json`。它既支持第一次初始化，也支持在现有知识库上做增量补充。默认把用户提供的官网、文档、账号主页、竞品链接和明确文字资料视为已确认信息，知识库正文不要反复标注限制性状态。

## 适用输入

优先接受以下输入之一或组合：

- PDF、DOCX/Word、TXT、Markdown、PPT 等文档
- 公司官网、产品页、关于我们、案例页、定价页
- 小红书、公众号、抖音、视频号、B站、知乎、官网博客等历史内容主页或栏目链接
- 公司名、品牌名、产品名
- 用户直接粘贴的公司简介、产品介绍、服务说明

如果只有公司名或品牌名，也可以先做首轮整理；这类模型推断或公开搜索补充信息应写入 `knowledge/source-notes.md` 的“补充记录”，正文保持可直接使用。

## 文档解析原则

用户上传 PDF、Word/DOCX、PPT、TXT、Markdown 等文档时，默认只提取并使用文档内可读文字内容，包括标题、正文、表格文字、页眉页脚、批注或备注中的文字。不要解析、描述、OCR 或提取文档内嵌的图片、视频、音频、附件、图标、图表视觉样式、版式设计和截图内容，除非用户明确要求处理这些媒体内容。

如果文档里的关键信息只存在于图片、扫描页、视频帧或不可复制的视觉元素中，只在 `source-notes.md` 记录“该部分未解析，需用户补充文字版或明确要求 OCR/媒体解析”，不要基于视觉内容猜测事实。

## 必读文件

开始前读取：

- `knowledge/company-profile.md`
- `knowledge/products.md`
- `knowledge/target-users.md`
- `knowledge/brand-voice.md`
- `knowledge/content-rules.md`
- `knowledge/competitors.md`
- `knowledge/past-content.md`
- `knowledge/source-notes.md`
- `config/keywords.json`
- `references/knowledge-schema.md`
- `references/questioning-rules.md`

如果用户给了历史内容账号主页、内容列表页、合集页或要求补充历史内容，还要读取并使用：

- `.agents/skills/past-content-collector/SKILL.md`

只要输入里出现小红书、抖音、公众号、视频号、B站、知乎、官网博客等历史内容主页或栏目链接，就必须默认先执行历史内容采集；不需要用户额外说“使用 Chrome”或“采集历史内容”。默认假设用户 Chrome 已登录相关平台，直接使用 Chrome 插件打开页面并采集可见内容。只有当页面实际显示未登录、无权限、验证拦截或内容不可见时，才暂停并请用户处理登录/授权。采集失败不阻塞知识库初始化，但必须在 `past-content.md` 和 `source-notes.md` 写清失败原因、已尝试方式和后续待补充动作。

如需写入知识库，使用：

- `scripts/merge_knowledge.py`
- `scripts/update_keywords.py`

## 工作流程

1. 先检查用户给了什么输入：文档、官网、公司名，还是只说“完善知识库”。
2. 识别这次任务属于：
   - `bootstrap`：第一次初始化
   - `merge`：在现有知识库上补充
   - `refresh`：刷新某一类来源型信息，如官网介绍、产品信息、竞品信息
3. 读取现有 `knowledge/` 文件，判断哪些 section 已经比较完整，哪些仍是空白、模板或明显待补充状态。
4. 如果输入源包含历史内容主页、账号主页、内容列表页或合集页，先调用 `past-content-collector` 采集可见历史内容，并把结果合并到 facts 的 `past_content.by_platform`；不要仅登记主页链接后跳过采集。
5. 从输入源提取“事实层信息”，不要一上来直接写结论。对上传文档先按“文档解析原则”只抽取文字内容，再整理事实层。事实层至少包括：
   - 公司/品牌/产品基础信息
   - 核心业务
   - 用户类型与痛点
   - 产品与服务
   - 行业关键词候选
   - 公开背书与案例
   - 竞品或可疑竞品
   - 品牌语气线索
   - 内容边界线索
   - 历史内容数据：优先由 `past-content-collector` 按平台采集，写入 `past_content.by_platform`
   - 来源证据
6. 按 `references/knowledge-schema.md` 的映射，把事实分发到 `knowledge/` 各文件。
7. 同时整理行业关键词，区分：
   - `dailyQueries`
   - `exaWebSearch.queries`
   - 平台相关关键词
   - 竞品相关关键词
8. 默认用户提供的资料均按已确认信息写入；只有出现来源冲突、页面不可见、权限受限、明显缺少来源，或用户明确说“这个不确定/不要公开”时，才在 `source-notes.md` 写入补充说明。知识库正文避免使用限制性标签。
9. 用 `scripts/merge_knowledge.py` 安全写入知识库，用 `scripts/update_keywords.py` 安全更新 `config/keywords.json`。

## 追问规则

追问不是兜底补锅，而是本技能的核心能力。按 `references/questioning-rules.md` 执行，并遵守以下规则：

1. 如果用户没有提供公司名、品牌名、产品名、官网、文档中的任何一个，必须先追问，再继续。
2. 如果涉及客户案例、价格、合作背书、团队背景、未公开项目，必须先问是否可公开写入。
3. 品牌语气、竞品、重点平台、行业关键词侧重点、不能碰的话题，可以先给推荐选项让用户确认；不需要一上来卡死流程。
4. 每次追问最多 3-5 个问题，先确保能启动，再补细节。
5. 非阻塞问题如果用户暂时没答，先按默认策略生成可用知识库；缺口写进 `source-notes.md` 的“补充记录”，正文保持可直接使用。

## 推荐追问方式

当信息不足时，优先用可选项而不是纯开放问题。

对用户提问时使用用户能理解的业务语言，不要暴露内部文件名、字段名或 skill 名。比如不要说“补充 `past-content.md`”，而要说“补充历史数据并进行复盘”。

例如品牌语气：

```text
品牌语气我建议先定一个基线，你选最接近的：
1. 专业务实型（推荐）
2. 行业顾问型
3. 设计师沟通型
4. 科技先锋型

如果你不选，我先按“专业务实型”写。
```

例如竞品：

```text
竞品这块你可以直接给我：
1. 明确竞品名单
2. 你希望对标的账号或公司
3. 如果暂时没有，我先根据官网和行业信息初筛 3-5 个候选，再给你确认
```

例如历史内容：

```text
如果你有小红书、公众号、抖音等历史内容，可以发我主页链接；只要你给主页，我会默认使用你已登录的 Chrome 采集可见历史内容并进行复盘。只有页面实际显示未登录、无权限或内容不可见时，我才会提示你处理登录/授权。
```

例如行业关键词：

```text
行业关键词我建议先定一个抓取重心，你选最接近的：
1. 产品词优先（推荐）：适合抓直接相关工具/产品动态
2. 行业词优先：适合抓更大的行业趋势
3. 用户痛点词优先：适合找更贴近选题的信号
4. 竞品词优先：适合做对标和差异化内容

如果你不选，我先按“产品词 + 行业词混合”写入。
```

## 写入原则

- `company-profile.md`：只写公司定位、业务、传播主张、背书、公开边界。
- `products.md`：只写产品/服务、场景、价值、客户问题。
- `target-users.md`：写用户类型、痛点、关注点、转化触发点。
- `brand-voice.md`：写语气、表达风格、推荐/禁用表达。
- `content-rules.md`：写允许写什么、谨慎写什么、禁止写什么。
- `competitors.md`：写明确竞品和候选竞品，候选项必须标注依据。
- `past-content.md`：没有历史内容时不要编造，改写为“待补充字段 + 建议补充方式”；如果用户给了账号主页或内容列表页，必须先调用 `past-content-collector` 采集，再按平台写入。只有在页面不可访问、实际显示未登录/无权限、平台限制或采集失败时，才写“已尝试采集但未成功 + 待补充方式”。
- `source-notes.md`：记录来源、冲突、补充记录和本次补全说明。默认使用“补充记录”标题，不使用限制性清单标题。
- `config/keywords.json`：写热点采集会真正使用的搜索关键词和平台配置；未确认关键词可以先作为候选写入说明，但不要替换掉全部现有关键词。

## 更新策略

- 默认按 `merge` 处理，不要整体重写整个 `knowledge/` 目录。
- 如果现有 section 已经有明显人工加工内容，优先追加或保守替换。
- 如果发现冲突信息，不直接覆盖，写入 `source-notes.md` 的“冲突记录”，说明冲突来源和建议处理方式。
- 如果知识库明显仍是模板，可以更积极填充，但也要保留来源说明。

## 脚本使用

先准备一份事实 JSON，再交给脚本分发：

```bash
python3 .agents/skills/knowledge-bootstrap/scripts/merge_knowledge.py \
  --facts-file tmp/company-facts.json \
  --mode merge
```

脚本会更新：

- `knowledge/company-profile.md`
- `knowledge/products.md`
- `knowledge/target-users.md`
- `knowledge/brand-voice.md`
- `knowledge/content-rules.md`
- `knowledge/competitors.md`
- `knowledge/past-content.md`
- `knowledge/source-notes.md`

如需同时更新行业关键词：

```bash
python3 .agents/skills/knowledge-bootstrap/scripts/update_keywords.py \
  --facts-file tmp/company-facts.json \
  --mode merge
```

## 资源

- `references/knowledge-schema.md`：知识库字段映射与文件职责
- `references/questioning-rules.md`：追问优先级、问法和默认策略
- `scripts/merge_knowledge.py`：把结构化 facts 安全写入 `knowledge/`
- `scripts/update_keywords.py`：把结构化 facts 中的关键词候选安全写入 `config/keywords.json`
