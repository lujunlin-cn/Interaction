"""Promote only actual Scenario overrides, preserving newer inherited library data."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.domain.character_overlay import promotion_patch
from app.domain.schemas import CharacterVersion


def test_voice_only_promote_does_not_revert_newer_library_identity():
    pinned = CharacterVersion(id="v3", character_id="c", version=3,
        identity_spec={"name": "Alice", "personality": "old", "default_desire": "old goal", "appearance": "old look"})
    current = {"name": "Alice", "personality": "new", "default_desire": "new goal", "appearance": "new look", "ref_voice_asset": "a"}
    overlay = {"identity": "Alice", "personality": "old", "desire": "old goal", "visual_state": "old look", "voice_id": "b",
               "overlay_sources": {"identity": "INHERIT", "personality": "INHERIT", "desire": "INHERIT", "appearance": "INHERIT", "voice": "OVERRIDE"}}
    patch = promotion_patch(current, pinned, overlay)
    assert set(patch) == {"ref_voice_asset", "alternate_voice_assets"}
    assert patch["ref_voice_asset"] == "b"
    assert patch["alternate_voice_assets"] == ["a"]
    assert current["personality"] == "new" and pinned.identity_spec["personality"] == "old"


def test_legacy_unchanged_fields_inherit_while_explicit_empty_override_promotes():
    pinned = CharacterVersion(id="v3", character_id="c", version=3,
        identity_spec={"personality": "old", "default_desire": "goal", "appearance": "coat"})
    current = {"personality": "new", "default_desire": "new goal", "appearance": "new coat"}
    patch = promotion_patch(current, pinned, {"personality": "old", "desire": "changed goal", "visual_state": "coat"})
    assert patch == {"default_desire": "changed goal"}
    patch = promotion_patch(current, pinned, {"desire": "", "overlay_sources": {"desire": "OVERRIDE"}})
    assert patch == {"default_desire": ""}


def test_explicit_story_identity_override_promotes_as_name():
    pinned = CharacterVersion(id="v3", character_id="c", version=3, identity_spec={"name": "Alice"})
    assert promotion_patch({"name": "Alice"}, pinned, {
        "identity": "Alicia", "overlay_sources": {"identity": "OVERRIDE"}}) == {"name": "Alicia"}
