#!/usr/bin/env python3
"""Review existing media with configured Step vision; never generate media.

Example (run from repository root):
  python -m pip install -r tools/visual_qa_requirements.txt
  python tools/visual_qa.py --mode candidates \
      --assets evidence/assets.json --canonical-id ca_example \
      --context evidence/expected.json --output evidence/review_step5.json

For video, add --video existing.mp4. Frames are extracted beside the report;
--assets then supplies the character reference images used by that shot.
Each invocation performs at most one Step chat request, with no automatic retry.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

IMAGE_CONTRACT = {
    "same_identity": "boolean", "identity_confidence": "0..1", "face_consistency": "0..1",
    "age_consistency": "0..1", "hair_consistency": "0..1", "body_consistency": "0..1",
    "outfit_correct": "boolean", "viewpoint_correct": "boolean", "prompt_adherence": "0..1",
    "major_artifact": "boolean", "issues": ["string"], "recommendation": "accept|retry|inspect",
}
VIDEO_CONTRACT = {
    "scene_semantics_match": "0..1", "character_identity_consistent": "boolean",
    "multi_character_identity_swap": "boolean", "motion_coherence": "0..1",
    "shot_continuity": "0..1", "story_action_visible": "boolean", "major_visual_artifact": "boolean",
    "issues": ["string"], "recommendation": "accept|retry|inspect",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("candidates", "reference", "edit", "separation", "video"), required=True)
    parser.add_argument("--assets", type=Path, required=True, help="Existing CharacterAsset items or list of images")
    parser.add_argument("--canonical-id", default="")
    parser.add_argument("--video", type=Path)
    parser.add_argument("--context", type=Path, help="JSON with narrative/prompt/expected characters/action")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-tokens", type=int, default=32768)
    parser.add_argument("--timeout", type=float, default=300)
    return parser.parse_args()


def asset_items(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    items = data.get("items") or data.get("images") or data.get("assets", {}).get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("Asset input must contain existing items/images")
    return items


def frame_times(duration: float) -> list[float]:
    if duration <= 0:
        raise ValueError("Video duration must be positive")
    if duration <= 6:
        return sorted(set(round(t, 3) for t in (min(.5, duration / 4), duration / 2, max(duration - .5, duration * .75))))
    return [round(t, 3) for t in (.5, duration * .25, duration * .5, duration * .75, duration - .5)]


def extract_frames(video: Path, folder: Path) -> tuple[list[dict], dict]:
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height,codec_type",
                            "-of", "json", str(video)], capture_output=True, text=True, check=True, timeout=30)
    metadata = json.loads(probe.stdout)
    duration = float(metadata["format"]["duration"])
    folder.mkdir(parents=True, exist_ok=True)
    frames = []
    for index, position in enumerate(frame_times(duration)):
        path = folder / f"frame_{index + 1:02d}_{position:.3f}s.jpg"
        if path.exists():
            raise FileExistsError(f"Frame already exists: {path}")
        subprocess.run(["ffmpeg", "-v", "error", "-ss", str(position), "-i", str(video), "-frames:v", "1",
                        "-q:v", "2", str(path)], capture_output=True, check=True, timeout=60)
        frames.append({"id": f"video_frame_{index + 1}", "path": str(path), "role": "video_frame", "position_seconds": position})
    return frames, {"file": str(video), "duration": duration, "probe": metadata}


def prepare_image(item: dict, client: httpx.Client) -> tuple[dict, str]:
    source = item.get("url") or item.get("path")
    if not source:
        raise ValueError("Existing image requires url or path")
    if str(source).startswith(("http://", "https://")):
        response = client.get(source, headers={"User-Agent": "Mozilla/5.0", "Accept": "image/*"})
        response.raise_for_status()
        data = response.content
    else:
        data = Path(source).read_bytes()
    image = Image.open(io.BytesIO(data))
    dimensions = list(image.size)
    image = image.convert("RGB")
    image.thumbnail((2048, 2048))
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=91)
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    summary = {"asset_id": item.get("id"), "role": item.get("role"), "status": item.get("status"),
               "source": source, "source_sha256": hashlib.sha256(data).hexdigest(),
               "original_dimensions": dimensions, "qa_dimensions": list(image.size),
               "position_seconds": item.get("position_seconds")}
    return summary, f"data:image/jpeg;base64,{encoded}"


def review_prompt(mode: str, canonical_id: str, context: dict) -> str:
    contract = VIDEO_CONTRACT if mode == "video" else IMAGE_CONTRACT
    additional = ""
    if mode == "candidates":
        additional = (
            "候选是独立生成，不能预设所有候选已经是同一身份。逐张判断身份特征、年龄、脸、发型、体型、服装、姿势与重大畸形。"
            "返回 candidates:[{asset_id,qa:(上方完整图片contract),major_failure:boolean,major_failure_reason:string}]，"
            "selected_candidate_id、selection_reason、canonical_asset_id、canonical_acceptable:boolean、canonical_reason。"
            "如果已选主图本身可接受，不因其他候选更漂亮而建议重生成；可与其他图不同而独立作为身份基准。"
        )
    if mode == "separation":
        additional = "额外返回 characters_separable:boolean、identity_swap:boolean、face_mix:boolean，以及可区分依据。"
    return (
        "你是视觉QA评审。只检查提供的真实图片或从同一真实视频抽取的帧，不推断没有观察到的结果。"
        "你不决定剧情事实、角色关系分数、分支状态、物品、线索或结局。输出严格JSON对象，不用markdown。"
        "只有明显换脸/身份交换/混脸、严重人体畸变、完全错误服装或视角、动作/场景完全不符才是Major Failure。"
        "普通光线、构图、锐度、服装小细节不构成重生成理由。证据不足时inspect并说明，不假装看清。"
        "所有数值在0到1；recommendation仅accept/retry/inspect。单任务最多一次Major质量Retry，评审本身不触发生图。"
        "返回顶层 qa 使用此contract：" + json.dumps(contract, ensure_ascii=False) + additional +
        "当前主图ID：" + (canonical_id or "未指定") + "。创作上下文：" + json.dumps(context, ensure_ascii=False)
    )


def validate_review(parsed: dict, mode: str, asset_ids: list[str], canonical_id: str = "") -> None:
    def check_qa(qa: dict, contract: dict):
        if not isinstance(qa, dict):
            raise ValueError("Visual QA contract is missing")
        for field, kind in contract.items():
            value = qa.get(field)
            if kind == "boolean" and not isinstance(value, bool):
                raise ValueError(f"QA field {field} must be boolean")
            if kind == "0..1" and (isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1):
                raise ValueError(f"QA field {field} must be in [0,1]")
            if kind == "accept|retry|inspect" and value not in {"accept", "retry", "inspect"}:
                raise ValueError(f"QA field {field} has an invalid recommendation")
            if isinstance(kind, list) and (not isinstance(value, list) or any(not isinstance(v, str) for v in value)):
                raise ValueError(f"QA field {field} must be a string array")
    # Candidate adjudication may return complete per-candidate QA without a
    # redundant aggregate whose identity comparison would be ambiguous.
    if mode != "candidates" or "qa" in parsed:
        check_qa(parsed.get("qa"), VIDEO_CONTRACT if mode == "video" else IMAGE_CONTRACT)
    if mode == "candidates":
        candidates = parsed.get("candidates")
        if not isinstance(candidates, list) or {v.get("asset_id") for v in candidates} != set(asset_ids):
            raise ValueError("QA must review every supplied candidate exactly once")
        if len(candidates) != len(asset_ids):
            raise ValueError("QA returned duplicate candidate IDs")
        for candidate in candidates:
            check_qa(candidate.get("qa"), IMAGE_CONTRACT)
            if not isinstance(candidate.get("major_failure"), bool):
                raise ValueError("Candidate major_failure must be boolean")
        if parsed.get("selected_candidate_id") not in asset_ids:
            raise ValueError("Selected candidate does not exist in review input")
        if canonical_id and (parsed.get("canonical_asset_id") != canonical_id or not isinstance(parsed.get("canonical_acceptable"), bool)):
            raise ValueError("QA omitted the requested canonical assessment")
    if mode == "separation":
        for field in ("characters_separable", "identity_swap", "face_mix"):
            if not isinstance(parsed.get(field), bool):
                raise ValueError(f"Separation QA requires {field}")


def sanitize(value, secrets: list[str]):
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[REDACTED_SECRET]")
        return value
    if isinstance(value, dict):
        return {key: sanitize(item, secrets) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item, secrets) for item in value]
    return value


def run(args: argparse.Namespace) -> dict:
    from app.config import Settings
    from app.runtime.structured_output import decode_object
    settings = Settings(_env_file=ROOT / "backend" / ".env")
    if args.output.exists():
        raise FileExistsError("Review output exists; choose another output to preserve prior evidence")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    request_path = args.output.with_name(args.output.stem + "_request_summary.json")
    if request_path.exists():
        raise FileExistsError("Request summary exists; choose another output")
    secrets = [settings.step_api_key, settings.image_provider_api_key, settings.fal_key, settings.fal_key_secondary]
    report = {"review_type": args.mode, "provider": "step_5", "requested_model": settings.step5_model,
              "actual_model": None, "request_id": None, "completion_id": None,
              "step_chat_attempts": 0, "new_media_generation_requests": 0,
              "started_at": datetime.now(timezone.utc).isoformat(), "status": "PREPARING"}
    summary = {"mode": args.mode, "model": settings.step5_model, "reasoning_effort": "high",
               "max_tokens": args.max_tokens, "timeout_seconds": args.timeout,
               "canonical_asset_id": args.canonical_id, "assets": []}
    started = time.monotonic()
    try:
        if not settings.step_api_key:
            raise RuntimeError("Configured Step API key is unavailable")
        items = asset_items(args.assets)
        context = json.loads(args.context.read_text(encoding="utf-8")) if args.context else {}
        content = []
        if args.mode == "video":
            if not args.video:
                raise ValueError("--video is required for video QA")
            frames, video_metadata = extract_frames(args.video, args.output.with_name(args.output.stem + "_frames"))
            items += frames
            summary["video"] = video_metadata
        with httpx.Client(timeout=90, follow_redirects=True) as download:
            for item in items:
                item_summary, data_url = prepare_image(item, download)
                summary["assets"].append(item_summary)
                content.append({"type": "text", "text": "Visual input: " + json.dumps(item_summary, ensure_ascii=False)})
                content.append({"type": "image_url", "image_url": {"url": data_url, "detail": "high"}})
        prompt = review_prompt(args.mode, args.canonical_id, context)
        summary["context"] = context
        summary["instruction"] = prompt
        payload = {"model": settings.step5_model, "reasoning_effort": "high", "max_tokens": args.max_tokens,
                   "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": content}]}
        request_path.write_text(json.dumps(sanitize(summary, secrets), ensure_ascii=False, indent=2), encoding="utf-8")
        report["step_chat_attempts"] = 1
        report["status"] = "SUBMITTED"
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        with httpx.Client(timeout=args.timeout) as client:
            response = client.post(settings.step_base_url.rstrip("/") + "/chat/completions", json=payload,
                                   headers={"Authorization": f"Bearer {settings.step_api_key}", "Content-Type": "application/json"})
        report["http_status"] = response.status_code
        report["header_request_id"] = response.headers.get("x-request-id") or response.headers.get("request-id")
        try:
            raw = response.json()
        except ValueError:
            raw = {"unparsed_body": response.text}
        report["raw"] = raw
        report["request_id"] = raw.get("request_id") or report["header_request_id"]
        report["completion_id"] = raw.get("id")
        report["actual_model"] = raw.get("model")
        report["usage"] = raw.get("usage")
        response.raise_for_status()
        choice = raw["choices"][0]
        report["finish_reason"] = choice.get("finish_reason")
        report["parsed"] = decode_object(choice["message"]["content"])
        if choice.get("finish_reason") == "length":
            raise ValueError("Vision QA response hit output token limit")
        validate_review(report["parsed"], args.mode, [item.get("id") for item in items], args.canonical_id)
        report["status"] = "SUCCEEDED"
    except Exception as exc:
        report["status"] = "FAILED"
        report["error_type"] = type(exc).__name__
        report["error"] = sanitize(str(exc), secrets)
    finally:
        report["completed_at"] = datetime.now(timezone.utc).isoformat()
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        args.output.write_text(json.dumps(sanitize(report, secrets), ensure_ascii=False, indent=2), encoding="utf-8")
        if not request_path.exists():
            request_path.write_text(json.dumps(sanitize(summary, secrets), ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    arguments = parse_args()
    result = run(arguments)
    print(json.dumps({"status": result["status"], "step_chat_attempts": result["step_chat_attempts"],
                      "new_media_generation_requests": 0, "output": str(arguments.output)}, ensure_ascii=False))
    sys.exit(0 if result["status"] == "SUCCEEDED" else 1)
