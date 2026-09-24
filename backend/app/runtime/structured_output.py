"""Lossless JSON envelope normalization. Never interpret reasoning or repair facts."""
import json

def decode_object(text: str) -> dict:
    raw = text.strip().lstrip("\ufeff")
    if raw.startswith("```") and raw.endswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("Expected a JSON object")
    return result
