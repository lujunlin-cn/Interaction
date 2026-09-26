"""Language is a generation contract, independent of provider and UI locale."""
from typing import Literal
import re

from pydantic import BaseModel, ConfigDict


def obvious_language_mismatch(text: str, language: str, proper_names: tuple[str, ...] = ()) -> bool:
    """Reject clearly wrong prose, tolerating short names/acronyms. Not ASR/translation."""
    for name in sorted(proper_names, key=len, reverse=True):
        if name.strip():
            text = re.sub(re.escape(name), "", text, flags=re.IGNORECASE)
    han = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    return (han == 0 and latin >= 12) if language == "zh-CN" else (han >= 4 and han > latin / 2)


class MediaLanguage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    video_language: Literal["zh-CN", "en"] = "zh-CN"
    subtitle_language: Literal["zh-CN", "en"] = "zh-CN"

    @property
    def speech_name(self) -> str:
        return "Mandarin Chinese (普通话)" if self.video_language == "zh-CN" else "English"

    @property
    def subtitle_name(self) -> str:
        return "Simplified Chinese (简体中文)" if self.subtitle_language == "zh-CN" else "English"

    def text_instruction(self) -> str:
        return (f" Language contract: narrative text, titles, action labels, and spoken dialogue must use {self.speech_name}."
                f" Captions/subtitles must use {self.subtitle_name}, translating the same authorized scene without adding facts."
                " Keep machine IDs, JSON keys and enums unchanged. Preserve character identity and proper names."
                " Source text, reference audio and character nationality do not override these languages.")

    def video_instruction(self, dialogue: list[dict]) -> str:
        import json
        audio = (f"Speak only the following authorized lines verbatim in {self.speech_name}, with the assigned speakers: "
                 + json.dumps(dialogue, ensure_ascii=False) + ". No additional dialogue or narration.") if dialogue else (
                     "No speech or voiceover. Use only environmental sound and nonverbal action sounds.")
        return (f"\nAudio language contract: all spoken words must be in {self.speech_name}; never switch languages. "
                "Reference voices supply timbre/identity, not the language or words to copy. " + audio
                + " Do not render subtitles, captions, lettering or text overlays in the video image; the player renders subtitles separately.")
