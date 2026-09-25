"""Resolve the existing ScenarioCharacter overlay against its pinned version.

This module has no I/O. Published snapshots, promotion and production share the
same explicit inheritance rules; an empty OVERRIDE must never become INHERIT.
"""
from copy import deepcopy

from .schemas import CharacterOutfit, CharacterVersion

REFERENCE_KEYS = {
    "front": "ref_front_asset", "three_quarter": "ref_three_quarter_asset",
    "side": "ref_side_asset", "full_front": "ref_full_front_asset",
    "full_side": "ref_full_side_asset", "back": "ref_back_asset",
    "other": "ref_other_assets",
}


def is_override(overlay: dict, module: str, field: str) -> bool:
    source = overlay.get("overlay_sources", {}).get(module)
    if source is not None:
        return source == "OVERRIDE"
    return bool(overlay.get(field))  # compatibility for pre-source overlays


def outfit_refs(outfit: dict) -> list[str]:
    slots = outfit.get("reference_slots") or {}
    if not slots:
        return list(dict.fromkeys(outfit.get("reference_assets") or []))
    if set(slots) - {"front", "side", "back", "full_body", "additional"}:
        raise ValueError("unknown outfit reference slot")
    refs = []
    for name in ("front", "side", "back", "full_body"):
        value = slots.get(name)
        if value is not None and not isinstance(value, str):
            raise ValueError("outfit reference slot must be an asset")
        if value:
            refs.append(value)
    additional = slots.get("additional") or []
    if not isinstance(additional, list) or not all(isinstance(v, str) for v in additional):
        raise ValueError("additional references must be a list")
    return list(dict.fromkeys([*refs, *additional]))


def resolve_overlay(version: CharacterVersion, overlay: dict) -> dict:
    frozen = deepcopy(version.canonical_asset_refs)
    frozen["other"] = list(version.other_refs)
    if is_override(overlay, "reference", "reference_overrides"):
        for role, value in (overlay.get("reference_overrides") or {}).items():
            if role not in REFERENCE_KEYS:
                raise ValueError("unknown identity reference slot")
            if role == "other":
                if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                    raise ValueError("other references must be a list")
            elif value is not None and not isinstance(value, str):
                raise ValueError("identity reference must be an asset")
            frozen[role] = deepcopy(value)
    outfits = {o.id: o.model_dump(mode="json") for o in version.outfits}
    for raw in overlay.get("local_outfits") or []:
        outfit = CharacterOutfit.model_validate(raw).model_dump(mode="json")
        outfit_refs(outfit)
        outfits[outfit["id"]] = outfit
    if is_override(overlay, "outfit", "outfit_id"):
        selected_id = overlay.get("outfit_id")
        if selected_id and selected_id not in outfits:
            raise ValueError("selected outfit is not in the pinned version or scenario")
        selected = outfits.get(selected_id)
    else:
        selected = next((o.model_dump(mode="json") for o in version.outfits if o.is_default), None)
    frozen["outfit"] = outfit_refs(selected) if selected else []
    frozen["pose"] = list(overlay.get("pose_refs") or []) if is_override(overlay, "pose", "pose_refs") else list(version.pose_refs)
    frozen["motion"] = list(overlay.get("motion_refs") or []) if is_override(overlay, "motion", "motion_refs") else list(version.motion_refs)
    frozen["voice"] = overlay.get("voice_id") if is_override(overlay, "voice", "voice_id") else version.canonical_voice_ref
    return frozen


def promotion_patch(current: dict, version: CharacterVersion, overlay: dict) -> dict:
    resolved = resolve_overlay(version, overlay)
    patch = {}
    # A pinned story often contains copies of inherited identity fields. Promoting
    # one local voice/outfit must not roll back newer library identity to that pin.
    identity_fields = [(key, key, key) for key in ("name", "bio", "personality", "appearance", "tags")]
    identity_fields += [(key, "default_" + key, key) for key in ("desire", "fear", "secrets", "knowledge", "relationship")]
    identity_fields += [("identity", "name", "identity"), ("visual_state", "appearance", "appearance")]
    for field, destination, source in identity_fields:
        if field not in overlay:
            continue
        origin = overlay.get("overlay_sources", {}).get(source)
        inherited = version.identity_spec.get(destination, [] if destination == "tags" else "")
        if origin == "OVERRIDE" or (origin is None and overlay[field] != inherited):
            patch[destination] = deepcopy(overlay[field])
    for module, field, destination in (("pose", "pose_refs", "ref_pose_assets"),
                                       ("motion", "motion_refs", "ref_motion_assets")):
        if is_override(overlay, module, field):
            patch[destination] = resolved[module]
            if module == "motion":
                patch["ref_motion_asset"] = None  # do not resurrect legacy fallback
    if is_override(overlay, "voice", "voice_id"):
        voice = resolved["voice"]
        patch["ref_voice_asset"] = voice
        alternatives = [*current.get("alternate_voice_assets", [])]
        if current.get("ref_voice_asset"):
            alternatives.append(current["ref_voice_asset"])
        patch["alternate_voice_assets"] = list(dict.fromkeys(v for v in alternatives if v != voice))
    if is_override(overlay, "reference", "reference_overrides"):
        for role in overlay.get("reference_overrides", {}):
            patch[REFERENCE_KEYS[role]] = resolved[role]
    if overlay.get("local_outfits") or is_override(overlay, "outfit", "outfit_id"):
        outfits = {o["id"]: deepcopy(o) for o in current.get("outfits", [])}
        pinned = {o.id: o.model_dump(mode="json") for o in version.outfits}
        local = {o["id"]: deepcopy(o) for o in overlay.get("local_outfits", [])}
        outfits.update(local)
        selected = overlay.get("outfit_id")
        if is_override(overlay, "outfit", "outfit_id"):
            if selected and selected not in outfits:
                outfits[selected] = pinned[selected]
            for oid, outfit in outfits.items():
                outfit["is_default"] = oid == selected
        for outfit in outfits.values():
            outfit["reference_assets"] = outfit_refs(outfit)
        patch["outfits"] = list(outfits.values())
    return patch
