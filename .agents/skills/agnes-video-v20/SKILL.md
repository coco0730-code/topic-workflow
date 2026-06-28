---
name: agnes-video-v20
description: 使用 Agnes Video V2.0 调用 Agnes AI 视频生成 API。适用于用户要求文生视频、图生视频、多图视频生成、关键帧动画、轮询视频任务结果、下载最终视频 URL，或把 Agnes 生视频流程接入项目级内容生产工作流时。
---

# Agnes Video V2.0 生视频

## 概述

使用本技能通过 Agnes AI API 创建视频生成任务，并按需轮询结果。模型固定使用 `agnes-video-v2.0`，支持文生视频、图生视频、多图视频生成和关键帧动画。

## 使用前准备

1. API key 统一写在项目根目录 `config/api-keys.json`。
2. 配置结构如下：

```json
{
  "agnes": {
    "apiKey": "YOUR_API_KEY"
  }
}
```

## 工作流程

1. 明确用户要做的是文生视频、图生视频、多图视频，还是关键帧动画。
2. 将需求整理成视频提示词，包含主体动作、镜头运动、场景动态、风格、光照和需要避免的内容。
3. 创建任务：`POST https://apihub.agnes-ai.com/v1/videos`。
4. 保存响应中的 `video_id` 和 `task_id`。推荐使用 `video_id` 查询。
5. 轮询结果：`GET https://apihub.agnes-ai.com/agnesapi?video_id=<VIDEO_ID>`，建议间隔 5 秒。
6. 当 `status` 为 `completed` 时，从 `remixed_from_video_id` 读取最终视频 URL。

## 快速开始

文生视频，只创建任务：

```bash
python3 .agents/skills/agnes-video-v20/scripts/generate_video.py \
  --prompt "A cinematic shot of a cat walking on the beach at sunset, soft ocean waves, warm golden lighting" \
  --width 1152 \
  --height 768 \
  --num-frames 121 \
  --frame-rate 24
```

文生视频，并等待最终结果：

```bash
python3 .agents/skills/agnes-video-v20/scripts/generate_video.py \
  --prompt "A cinematic product reveal, slow camera dolly, soft studio light, realistic motion" \
  --wait \
  --poll-interval 5 \
  --download outputs/agnes-video.mp4
```

图生视频：

```bash
python3 .agents/skills/agnes-video-v20/scripts/generate_video.py \
  --prompt "The woman slowly turns around and looks back at the camera, natural facial expression" \
  --image https://example.com/image.png \
  --wait
```

关键帧动画：

```bash
python3 .agents/skills/agnes-video-v20/scripts/generate_video.py \
  --prompt "Generate a smooth cinematic transition between the keyframes, maintaining visual consistency" \
  --image https://example.com/keyframe1.png \
  --image https://example.com/keyframe2.png \
  --mode keyframes \
  --wait
```

查询已有任务：

```bash
python3 .agents/skills/agnes-video-v20/scripts/generate_video.py \
  --query-video-id video_xxxxxx
```

## 参数要点

- `model`：固定为 `agnes-video-v2.0`。
- `prompt`：视频内容描述，必填。
- `image`：图片 URL 或图片 URL 数组；单图用于图生视频，多图用于多图视频或关键帧。
- `mode`：可用于 `ti2vid` 或 `keyframes`。
- `width` / `height`：默认推荐 `1152x768`，接口可能会标准化到最接近的输出规格。
- `num_frames`：必须小于等于 `441`，且满足 `8n + 1`。
- `frame_rate`：支持 `1-60`。
- `negative_prompt`：描述需要避免的内容。

## 常用时长

| 目标时长 | 推荐参数 |
| --- | --- |
| 约 3 秒 | `num_frames: 81`, `frame_rate: 24` |
| 约 5 秒 | `num_frames: 121`, `frame_rate: 24` |
| 约 10 秒 | `num_frames: 241`, `frame_rate: 24` |
| 约 18 秒 | `num_frames: 441`, `frame_rate: 24` |

实际视频时长请以查询结果中的 `seconds` 字段为准。

## 状态与结果

- `queued`：任务排队中。
- `in_progress`：视频生成中。
- `completed`：视频已完成，读取 `remixed_from_video_id`。
- `failed`：生成失败，读取 `error`。

## 资源

使用 `scripts/generate_video.py` 创建 Agnes Video V2.0 任务、查询结果、轮询状态和下载最终视频。脚本只依赖 Python 标准库，默认读取项目根目录 `config/api-keys.json`。
