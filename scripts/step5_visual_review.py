"""Review existing CharacterAssets with Step 5. Never generates media.

Run from backend with PYTHONPATH=.: .venv/bin/python ../scripts/step5_visual_review.py
  --characters ID [ID ...] --output PATH [--separation]
QA-only dependency: Pillow (pip install Pillow).
Credentials come only from the backend Settings environment.
"""
import argparse
import asyncio
import base64
import hashlib
import io
import json
import time
from pathlib import Path

import httpx
from PIL import Image
from app.config import settings
from app.runtime.structured_output import decode_object


async def run(args):
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise SystemExit("Review already recorded; choose a new explicit output for another call")
    contract = {
        "same_identity": "boolean", "identity_confidence": "0..1", "face_consistency": "0..1",
        "age_consistency": "0..1", "hair_consistency": "0..1", "body_consistency": "0..1",
        "outfit_correct": "boolean", "viewpoint_correct": "boolean", "prompt_adherence": "0..1",
        "major_artifact": "boolean", "issues": ["string"], "recommendation": "accept|retry|inspect",
    }
    instruction = (
        "你是视觉 QA。只判断提供的图片，不决定剧情事实或 Runtime 状态。输出严格 JSON。"
        "只有明显身份错误、混脸、严重人体畸变、完全错误服装或视角才是 Major Failure。"
        "普通光线、构图、锐度或服装小细节不构成重生成理由。候选可能是不同身份，不能预设相同。"
        "每个 asset 返回 {asset_id, qa, major_failure, reason}，qa contract 为 " + json.dumps(contract) +
        "。如主图可接受，不因为其他候选更漂亮而替换。返回 canonical_acceptable（角色ID到布尔映射）。"
        "顶层另给 recommendation。证据不足使用 inspect，不编造。"
    )
    if args.separation:
        instruction += "本次重点三角色两两身份区分，返回 pairs:[{characters,characters_separable,identity_swap,face_mix,identity_confusion,issues}]。"
    manifest = []
    content = [{"type": "text", "text": instruction}]
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        characters = (await client.get(args.base + "/api/characters?include_archived=true")).json()["items"]
        for cid in args.characters:
            character = next(c for c in characters if c["id"] == cid)
            assets = (await client.get(args.base + f"/api/characters/{cid}/character-assets")).json()["items"]
            assets = [a for a in assets if a["status"] != "ARCHIVED"]
            if args.separation:
                assets = [a for a in assets if a["status"] == "CANONICAL" and a["role"] == "front"]
            if args.assets:
                assets = [a for a in assets if a["id"] in args.assets]
            content.append({"type": "text", "text": json.dumps({"character_id": cid, "name": character["name"], "appearance": character.get("appearance"), "canonical": [a["id"] for a in assets if a["status"] == "CANONICAL"]}, ensure_ascii=False)})
            for asset in assets:
                source = asset["url"]
                response = await client.get(args.base + source if source.startswith("/") else source)
                response.raise_for_status()
                image = Image.open(io.BytesIO(response.content)); original = image.size
                image.thumbnail((2048, 2048))
                buf = io.BytesIO(); image.convert("RGB").save(buf, "JPEG", quality=90)
                manifest.append({"character": cid, "asset": asset["id"], "role": asset["role"], "status": asset["status"], "source_sha256": hashlib.sha256(response.content).hexdigest(), "original_dimensions": original, "review_dimensions": image.size})
                content.extend([{"type": "text", "text": f"Asset {asset['id']}, role {asset['role']}, status {asset['status']}; expected edit: {asset.get('provenance', {}).get('instruction', '')}; expected view: {asset.get('provenance', {}).get('standard_view', '')}"},
                                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()}}])
    evidence = {"provider": "step_5", "requested_model": settings.step5_model, "reasoning_effort": "high", "max_tokens": 32768, "started_at_ms": int(time.time()*1000), "assets": manifest, "instruction": instruction, "status": "SUBMITTING", "step_chat_attempts": 1, "new_media_generation_requests": 0}
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2))
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(settings.step_base_url.rstrip("/") + "/chat/completions",
                headers={"Authorization": f"Bearer {settings.step_api_key}"},
                json={"model": settings.step5_model, "messages": [{"role": "user", "content": content}], "reasoning_effort": "high", "max_tokens": 32768, "temperature": 0.1})
        evidence["http_status"] = response.status_code
        response.raise_for_status()
        data = response.json()
        evidence.update(status="SUCCEEDED", actual_model=data.get("model"), request_id=response.headers.get("x-request-id"), completion_id=data.get("id"), usage=data.get("usage"), result=decode_object(data["choices"][0]["message"]["content"]))
    except Exception as exc:
        evidence.update(status="FAILED", error_type=type(exc).__name__)
        raise
    finally:
        evidence["latency_ms"] = round((time.monotonic()-t0)*1000)
        output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2))
        print(json.dumps({"output": str(output), "status": evidence["status"], "latency_ms": evidence["latency_ms"], "result": evidence.get("result")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--characters", nargs="+", required=True)
    parser.add_argument("--assets", nargs="*")
    parser.add_argument("--output", required=True)
    parser.add_argument("--base", default="http://127.0.0.1:9000")
    parser.add_argument("--separation", action="store_true")
    asyncio.run(run(parser.parse_args()))
