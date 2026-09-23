"""MockImageProvider —— mock 模式下的角色生图桩（不联网、确定性输出）。

生成内联 SVG data URL（含 prompt 摘要），让 v0.6 Character Asset System 的
生成→候选→Canonical→多视图链路在 PROVIDER_MODE=mock / 无 FAL_KEY 时也可测。
"""
from __future__ import annotations

import base64
import hashlib


class MockImageProvider:
    name = "nano_banana_2"          # 注册键与真实 provider 相同（router.registry 直取）

    def capabilities(self) -> dict:
        return {"image_generation": "mock", "image_edit": "mock",
                "num_images_max": 4, "edit_image_urls_max": 4,
                "note": "SVG placeholder; NOT a real generative model"}

    def _svg_url(self, seed: str, label: str) -> str:
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        hue = int(digest[:6], 16) % 360
        text = (label or "character")[:24].replace("<", "").replace("&", "")
        svg = (
            f"<svg xmlns='http://www.w3.org/2000/svg' width='512' height='640'>"
            f"<rect width='512' height='640' fill='hsl({hue},40%,28%)'/>"
            f"<circle cx='256' cy='220' r='110' fill='hsl({hue},55%,72%)'/>"
            f"<rect x='126' y='360' width='260' height='200' rx='40' "
            f"fill='hsl({hue},45%,55%)'/>"
            f"<text x='256' y='610' font-size='26' fill='#f0f2f4' "
            f"text-anchor='middle' font-family='sans-serif'>{text}</text></svg>")
        return "data:image/svg+xml;base64," + \
            base64.b64encode(svg.encode("utf-8")).decode("ascii")

    async def generate(self, request: dict) -> dict:
        prompt = request.get("prompt", "")
        n = max(1, min(int(request.get("num_images", 2)), 4))
        images = [{"url": self._svg_url(f"{prompt}#{i}", f"candidate {i+1}"),
                   "content_type": "image/svg+xml"} for i in range(n)]
        return {"images": images, "model": "mock_image",
                "raw": {"mock": True, "prompt_len": len(prompt)}}

    async def edit(self, request: dict) -> dict:
        image_urls = list(request.get("image_urls") or [])
        if not image_urls:
            raise RuntimeError("IMAGE_EDIT requires image_urls")
        prompt = request.get("prompt", "")
        images = [{"url": self._svg_url(f"{prompt}|{image_urls[0]}", "edited"),
                   "content_type": "image/svg+xml"}]
        return {"images": images, "model": "mock_image/edit",
                "raw": {"mock": True, "source_refs": len(image_urls)}}

    async def health(self) -> bool:
        return True
