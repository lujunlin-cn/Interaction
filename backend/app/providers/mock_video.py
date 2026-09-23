"""MockVideoProvider —— 用 FFmpeg 真实生成占位视频（主题化字幕卡）。

这是「正式 MockProvider」：实现 VideoProvider 接口，产出真实可解码播放的 mp4，
但不调用任何外部付费 API。业务 Runtime（调度、装配、提交）完全不感知它是 Mock。
"""
from __future__ import annotations

import asyncio
import re
import subprocess
from pathlib import Path

from ..config import settings
from .base import VideoJobHandle, VideoJobResult


def _escape_drawtext(text: str) -> str:
    return re.sub(r"([\\':%,\[\]=])", r"\\\1", text)


class MockVideoProvider:
    name = "mock_video"
    healthy = True

    def capabilities(self) -> dict:
        return {
            "text_to_video": "mock", "reference_image": "mock",
            "reference_audio": "unsupported", "reference_video": "unsupported",
            "durations": [5], "resolutions": ["768p"],
            "note": "FFmpeg slate placeholder; NOT a real generative model",
        }

    async def submit(self, request: dict) -> VideoJobHandle:
        job_id = request.get("job_id") or f"mockvid_{id(request):x}"
        shots = request.get("shots") or []
        # 记录完整请求工件（含素材 references）——FR-005~008 的可审计证据
        job_dir = settings.media_path / "clips" / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        import json
        (job_dir / "request.json").write_text(
            json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
        # 异步执行 FFmpeg 渲染，避免阻塞事件循环
        asyncio.get_running_loop().create_task(self._render(job_id, shots))
        return VideoJobHandle(provider_job_id=job_id, provider=self.name)

    async def _render(self, job_id: str, shots: list[dict]) -> None:
        out_dir = settings.media_path / "clips" / job_id
        out_dir.mkdir(parents=True, exist_ok=True)
        status_file = out_dir / "status.json"
        try:
            for shot in shots:
                clip = out_dir / f"{shot['id']}.mp4"
                await asyncio.get_running_loop().run_in_executor(
                    None, self._render_one, shot, clip)
            status_file.write_text('{"status": "READY"}', encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            status_file.write_text(
                '{"status": "FAILED", "error": %s}' % _json_str(str(e)), encoding="utf-8")

    @staticmethod
    def _render_one(shot: dict, clip: Path) -> None:
        duration = max(1.0, float(shot.get("duration", 5)))
        title = _escape_drawtext(shot.get("title", "镜头"))[:60]
        subtitle = _escape_drawtext(shot.get("subtitle", ""))[:80]
        # 1280x720 深色背景 + 标题 + 字幕条
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=0x15191e:s=1280x720:d={duration}:r=24",
            "-f", "lavfi", "-i", "anoisesrc=color=brown:amplitude=0.015:seed=7",
            "-vf",
            "drawtext=text='%s':fontcolor=0xf0f2f4:fontsize=44:x=(w-text_w)/2:y=(h/2)-60,"
            "drawtext=text='%s':fontcolor=0xd2d7df:fontsize=30:x=(w-text_w)/2:y=h-120" % (title, subtitle),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", str(duration),
            "-c:a", "aac", "-shortest", "-loglevel", "error", str(clip),
        ]
        subprocess.run(cmd, check=True, timeout=120, capture_output=True)

    async def status(self, handle: VideoJobHandle) -> VideoJobResult:
        out_dir = settings.media_path / "clips" / handle.provider_job_id
        status_file = out_dir / "status.json"
        if not status_file.exists():
            return VideoJobResult(status="GENERATING")
        import json
        data = json.loads(status_file.read_text(encoding="utf-8"))
        if data.get("status") == "READY":
            clips = sorted(out_dir.glob("*.mp4"))
            return VideoJobResult(
                status="READY",
                video_path=str(out_dir),
                timings={"mock": True},
                raw={"clips": [str(c) for c in clips]},
            )
        return VideoJobResult(status="FAILED", error=data.get("error", "unknown"))

    async def cancel_if_supported(self, handle: VideoJobHandle) -> bool:
        return False  # FFmpeg 本地任务不支持中途取消；迟到结果会被丢弃记账

    async def health(self) -> bool:
        try:
            proc = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
            return proc.returncode == 0
        except Exception:
            return False


def _json_str(s: str) -> str:
    import json
    return json.dumps(s, ensure_ascii=False)
