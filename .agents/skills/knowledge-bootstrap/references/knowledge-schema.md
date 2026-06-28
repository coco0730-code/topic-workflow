# Knowledge Schema

## 目标

把来源型资料映射为当前项目 `knowledge/` 目录的 8 个目标文件，避免不同来源内容直接混写。

同时把与热点采集有关的关键词写入 `config/keywords.json`。

## 文件职责

### `knowledge/company-profile.md`
- 公司名称
- 品牌/产品
- 官网
- 一句话介绍
- 核心定位
- 核心业务
- 商业目标
- 核心传播主张
- 不希望外界误解的点
- 可公开背书

### `knowledge/products.md`
- 产品/服务清单
- 产品能力
- 典型适用场景
- 客户收益
- 差异化
- 常见客户问题

### `knowledge/target-users.md`
- 用户类型
- 角色/岗位
- 行业
- 痛点
- 平时关注
- 决策动机
- 内容偏好
- 能触发咨询/转化的内容

### `knowledge/brand-voice.md`
- 整体风格
- 推荐表达气质
- 应该多用
- 应该少用
- 标题风格
- 正文风格
- 推荐表达
- 不推荐表达

### `knowledge/content-rules.md`
- 内容目标
- 可写方向
- 谨慎方向
- 禁止方向
- 禁用/慎用表达
- 审核红线
- 发布前检查

### `knowledge/competitors.md`
- 明确竞品
- 候选竞品
- 对标账号
- 差异化表达
- 可借鉴方向
- 不要模仿的方向

### `knowledge/past-content.md`
- 历史内容复盘
- 已经发布过的主题
- 按平台归档的历史内容列表
- 各平台账号/主页来源
- 表现较好的方向
- 表现一般的方向
- 后续选题建议

如果没有明确历史内容数据，不要编造，改写成待补充模板。
如果用户提供账号主页、栏目页或历史内容链接，先使用 `past-content-collector` 采集可见历史内容，再写入本文件。

### `knowledge/source-notes.md`
- 本次使用来源
- 事实证据
- 冲突记录
- 补充记录
- 用户提供资料的来源说明
- 仅在来源冲突、页面不可见、权限受限或用户明确表示不确定时记录限制说明
- 文档中未解析的非文字内容说明，如内嵌图片、视频、音频、附件、扫描页或图表视觉信息

### `config/keywords.json`
- `dailyQueries`
- `exaWebSearch.queries`
- 平台列表
- 热点采集配置
- 关键词侧重点说明

## 事实层字段建议

建议先整理为如下字段，再分发到各知识库文件：

```json
{
  "company": {
    "name": "",
    "brand": "",
    "website": "",
    "one_liner": "",
    "positioning": [],
    "businesses": [],
    "proof_points": [],
    "public_constraints": []
  },
  "products": [
    {
      "name": "",
      "audience": [],
      "pain_points": [],
      "features": [],
      "scenarios": [],
      "benefits": [],
      "differentiators": []
    }
  ],
  "users": [
    {
      "type": "",
      "roles": [],
      "industries": [],
      "pain_points": [],
      "interests": [],
      "decision_drivers": []
    }
  ],
  "brand_voice": {
    "style": [],
    "preferred_phrases": [],
    "avoid_phrases": [],
    "tone_guess": [],
    "status": "confirmed"
  },
  "content_rules": {
    "allowed": [],
    "caution": [],
    "forbidden": [],
    "red_lines": []
  },
  "keywords": {
    "focus": "product or industry or pain_point or competitor or mixed",
    "daily_queries": [],
    "exa_queries": [],
    "platforms": [],
    "notes": []
  },
  "competitors": {
    "confirmed": [],
    "candidates": [],
    "notes": []
  },
  "past_content": {
    "available": false,
    "by_platform": [
      {
        "platform": "",
        "account": "",
        "homepage_url": "",
        "collected_at": "",
        "items": [
          {
            "title": "",
            "url": "",
            "published_at": "",
            "content_type": "",
            "metrics": {
              "views": "",
              "likes": "",
              "comments": "",
              "favorites": "",
              "shares": ""
            },
            "angle": "",
            "topics": [],
            "performance_note": ""
          }
        ],
        "observations": []
      }
    ],
    "items": [],
    "notes": []
  },
  "sources": [
    {
      "type": "pdf or docx or ppt or txt or markdown or website or pasted_text",
      "label": "",
      "path_or_url": "",
      "notes": "文档来源默认只使用可读文字；未解析内嵌图片、视频、音频、附件和版式视觉信息"
    }
  ],
  "open_questions": []
}
```

## 分发规则

- 用户提供的官网、文档、账号主页、竞品链接和直接文字说明默认视为已确认信息，直接写入正式 section。
- `candidates`、`tone_guess`、`open_questions` 等仅作为内部组织字段；输出正文保持可直接使用。确实需要说明限制时，写入 `source-notes.md` 的“补充记录”或“冲突记录”。
- 涉及价格、客户、合作、市场数据时，如果来自用户提供资料或公开页面，可以写入；如果来源冲突或页面不可见，在 `source-notes.md` 记录限制说明。
- 关键词默认按用户资料和行业语境生成并写入 `dailyQueries` 和 `exaWebSearch.queries`，生成依据记录到 `source-notes.md`。
