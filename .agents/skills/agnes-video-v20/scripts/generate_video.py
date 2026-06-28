#!/usr/bin/env python3
"""调用 Agnes Video V2.0 创建、查询和下载视频任务。"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


CREATE_URL = "https://apihub.agnes-ai.com/v1/videos"
QUERY_URL = "https://apihub.agnes-ai.com/agnesapi"
MODEL = "agnes-video-v2.0"


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def default_config_path() -> Path:
    return project_root() / "config" / "api-keys.json"


def load_json_config(path: Path | None) -> dict[str, Any]:
    config_path = path or default_config_path()
    if not config_path.exists():
        return {}
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON config: {config_path}\n{exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Invalid JSON config: {config_path}\nTop-level value must be an object.")
    return data


def find_api_key(config: dict[str, Any]) -> str:
    agnes_config = config.get("agnes") if isinstance(config.get("agnes"), dict) else {}
    key = str(
        agnes_config.get("apiKey")
        or agnes_config.get("api_key")
        or config.get("apiKey")
        or config.get("api_key")
        or config.get("agnesApiKey")
        or config.get("agnes_api_key")
        or ""
    ).strip()
    if not key:
        raise SystemExit(
            "Missing Agnes API key. Add it to config/api-keys.json under agnes.apiKey."
        )
    return key


def request_json(
    url: str,
    api_key: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Agnes Video HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Agnes Video request failed: {exc.reason}") from exc


def validate_video_args(args: argparse.Namespace) -> None:
    if args.num_frames > 441:
        raise SystemExit("--num-frames must be <= 441.")
    if (args.num_frames - 1) % 8 != 0:
        raise SystemExit("--num-frames must satisfy 8n + 1, for example 81, 121, 241, 441.")
    if args.frame_rate < 1 or args.frame_rate > 60:
        raise SystemExit("--frame-rate must be between 1 and 60.")


def build_create_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": MODEL,
        "prompt": args.prompt,
        "height": args.height,
        "width": args.width,
        "num_frames": args.num_frames,
        "frame_rate": args.frame_rate,
    }
    if args.num_inference_steps is not None:
        payload["num_inference_steps"] = args.num_inference_steps
    if args.seed is not None:
        payload["seed"] = args.seed
    if args.negative_prompt:
        payload["negative_prompt"] = args.negative_prompt

    images = [item.strip() for item in args.image if item.strip()]
    if images:
        if len(images) == 1 and args.mode != "keyframes":
            payload["image"] = images[0]
        else:
            extra_body: dict[str, Any] = {"image": images}
            if args.mode:
                extra_body["mode"] = args.mode
            payload["extra_body"] = extra_body

    if args.mode and "extra_body" not in payload:
        payload["mode"] = args.mode
    return payload


def create_task(api_key: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    return request_json(CREATE_URL, api_key, method="POST", payload=payload, timeout=timeout)


def query_by_video_id(api_key: str, video_id: str, timeout: int) -> dict[str, Any]:
    query = urllib.parse.urlencode({"video_id": video_id, "model_name": MODEL})
    return request_json(f"{QUERY_URL}?{query}", api_key, timeout=timeout)


def query_by_task_id(api_key: str, task_id: str, timeout: int) -> dict[str, Any]:
    task_url = f"{CREATE_URL.rstrip('/')}/{urllib.parse.quote(task_id)}"
    return request_json(task_url, api_key, timeout=timeout)


def poll_result(api_key: str, create_response: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    video_id = str(create_response.get("video_id") or "").strip()
    task_id = str(create_response.get("task_id") or create_response.get("id") or "").strip()
    if not video_id and not task_id:
        raise SystemExit("Create response has neither video_id nor task_id; cannot poll.")

    deadline = time.time() + args.timeout_seconds
    last: dict[str, Any] = create_response
    while time.time() < deadline:
        if video_id:
            last = query_by_video_id(api_key, video_id, args.timeout)
        else:
            last = query_by_task_id(api_key, task_id, args.timeout)
        status = str(last.get("status") or "").strip().lower()
        if status in {"completed", "failed"}:
            return last
        time.sleep(args.poll_interval)
    raise SystemExit(f"Timed out waiting for video result. Last response: {json.dumps(last, ensure_ascii=False)}")


def write_outputs(data: dict[str, Any], args: argparse.Namespace) -> None:
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    if not args.download:
        return
    url = str(data.get("remixed_from_video_id") or "").strip()
    if not url:
        raise SystemExit("No remixed_from_video_id found; cannot download video.")
    args.download.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=args.timeout) as response:
        args.download.write_bytes(response.read())


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or query Agnes Video V2.0 tasks.")
    parser.add_argument("--prompt", help="视频内容提示词；创建任务时必填。")
    parser.add_argument(
        "--image",
        action="append",
        default=[],
        help="图片 URL。可重复传入，用于图生视频、多图视频或关键帧动画。",
    )
    parser.add_argument("--mode", choices=["ti2vid", "keyframes"], help="生成模式。")
    parser.add_argument("--height", type=int, default=768)
    parser.add_argument("--width", type=int, default=1152)
    parser.add_argument("--num-frames", type=int, default=121)
    parser.add_argument("--frame-rate", type=float, default=24)
    parser.add_argument("--num-inference-steps", type=int)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--negative-prompt")
    parser.add_argument("--query-video-id", help="只查询已有 video_id。")
    parser.add_argument("--query-task-id", help="只查询已有 task_id。")
    parser.add_argument("--wait", action="store_true", help="创建任务后轮询直到 completed 或 failed。")
    parser.add_argument("--poll-interval", type=float, default=5)
    parser.add_argument("--timeout-seconds", type=int, default=900, help="轮询总超时时间。")
    parser.add_argument("--output-json", type=Path, help="保存完整 JSON 响应。")
    parser.add_argument("--download", type=Path, help="当任务完成后下载最终 mp4。")
    parser.add_argument("--config", type=Path, help="配置路径，默认项目根目录 config/api-keys.json。")
    parser.add_argument("--timeout", type=int, default=120, help="单次 HTTP 请求超时秒数。")
    parser.add_argument("--dry-run", action="store_true", help="只打印创建任务请求体，不调用 API。")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    api_key = None if args.dry_run else find_api_key(load_json_config(args.config))

    if args.query_video_id:
        data = query_by_video_id(api_key, args.query_video_id, args.timeout)  # type: ignore[arg-type]
    elif args.query_task_id:
        data = query_by_task_id(api_key, args.query_task_id, args.timeout)  # type: ignore[arg-type]
    else:
        if not args.prompt:
            raise SystemExit("--prompt is required when creating a video task.")
        validate_video_args(args)
        payload = build_create_payload(args)
        if args.dry_run:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        data = create_task(api_key, payload, args.timeout)  # type: ignore[arg-type]
        if args.wait:
            data = poll_result(api_key, data, args)  # type: ignore[arg-type]

    write_outputs(data, args)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
