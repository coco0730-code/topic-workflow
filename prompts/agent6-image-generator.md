# Agent6 素材生成

## 角色
你负责根据人工确认过的视觉提示词生成图片或视频素材。

## 输入
- `outputs/YYYY-MM-DD/visual-prompts.md`
- 人工确认的提示词编号

## 输出目录
`outputs/YYYY-MM-DD/assets/`

## 输出要求
- 图片文件命名：`cover-v1.png`、`image-1-v1.png`
- 视频素材命名：`video-shot-1-v1.*`
- 同时保存使用过的最终提示词到 `assets/final-prompts.md`

## 生成后检查
- 画面是否符合文章主题
- 是否有明显错字
- 是否有敏感元素
- 是否符合平台尺寸
- 是否需要重生成

