"""Read-only history audit. Run from backend with .venv/bin/python ../scripts/audit_media_language.py."""
import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from sqlalchemy import select
from app.db import SessionLocal
from app.db_models import SessionRow
from app.providers.real import usage_ledger


def script_hint(text):
    # Script heuristic is NOT audio language detection or transcription.
    han = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    return "zh-dominant" if han > latin / 2 else "latin-dominant" if latin else "empty"


async def main():
    counts = {}
    examples = {}
    mismatches = []
    shot_count = 0
    async with SessionLocal() as db:
        rows = (await db.execute(select(SessionRow).order_by(SessionRow.updated_at.desc()).limit(50))).scalars().all()
        for row in rows:
            branches = row.state.get("branches", [])
            if isinstance(branches, dict):
                branches = list(branches.values())
            for branch in branches:
                for shot in branch.get("shots", []):
                    shot_count += 1
                    prompt = shot.get("prompt", "").split("\nPinned cast appearance")[0]
                    kind = script_hint(prompt)
                    counts[kind] = counts.get(kind, 0) + 1
                    sample = {"session_id": row.id, "branch_id": branch.get("id"), "shot_id": shot.get("id"),
                              "prompt_excerpt": prompt[:600], "player_caption": branch.get("caption", "")[:240],
                              "shot_subtitle": shot.get("subtitle", "")[:240],
                              "media_language": branch.get("media_language"),
                              "has_persisted_dialogue": "dialogue" in branch,
                              "submitted_jobs": branch.get("jobs", [])}
                    examples.setdefault(kind, sample)
                    if kind == "latin-dominant" and script_hint(branch.get("caption", "")) == "zh-dominant" and len(mismatches) < 3:
                        mismatches.append(sample)
    ledger = usage_ledger(5000)
    print(json.dumps({"at_utc": datetime.now(timezone.utc).isoformat(), "read_only": True,
                      "sessions_scanned": len(rows), "shots_scanned": shot_count, "prompt_script_counts": counts,
                      "method": "Inspect persisted prompt/caption/subtitle only; no audio transcription, no paid generation.",
                      "examples": examples, "mixed_prompt_caption_examples": mismatches,
                      "usage_total_records": len(ledger),
                      "usage_http_attempts": sum(x.get("external_http_attempts", 0) for x in ledger)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
