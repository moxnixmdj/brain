"""Live capability ownership ontology verifier V1.

Defines the current live Brain as capabilities admitted by the authoritative
provider manifest. Repository code outside those providers is not live-owned
merely because it exists.

This module verifies structural R1 closure:
  live-owned capability -> discoverable carrier -> executable/composable fabric path

It does not claim arbitrary-language semantic routing completeness.
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import live_integrated_brain_v1 as live_brain
from canonical.runtime import autonomous_verified_self_improvement_v1 as self_improvement
from canonical.runtime import h100_verified_capability_registry_v8 as h100_registry
from canonical.runtime import certificate_gated_selected_route_runtime_entrypoint_v2 as certified_route

SCHEMA = "PROJECT_BRAIN_LIVE_CAPABILITY_OWNERSHIP_V1"
MANIFEST_SCHEMA = "PROJECT_BRAIN_LIVE_CAPABILITY_OWNERSHIP_MANIFEST_V1"
ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "canonical/governance/LIVE_CAPABILITY_OWNERSHIP_MANIFEST_V1.json"

EXPECTED_PROVIDERS = (
    "FABRIC_ENGINES",
    "VERIFIED_BOUND_CAPABILITIES",
    "ACTIVE_VERIFIED_LEARNED_SKILLS",
    "H100_VERIFIED_CAPABILITIES",
    "CERTIFICATE_GATED_SELECTED_ROUTES",
)


class LiveOwnershipError(ValueError):
    pass


def _load_manifest(path: str | Path = MANIFEST_PATH) -> dict[str, Any]:
    p = Path(path)
    doc = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping):
        raise LiveOwnershipError("OWNERSHIP_MANIFEST_NOT_OBJECT")
    if doc.get("schema") != MANIFEST_SCHEMA:
        raise LiveOwnershipError("OWNERSHIP_MANIFEST_SCHEMA_INVALID")
    if doc.get("status") != "ACTIVE_AUTHORITATIVE_LIVE_OWNERSHIP_ONTOLOGY":
        raise LiveOwnershipError("OWNERSHIP_MANIFEST_NOT_ACTIVE")
    if doc.get("default") != "NOT_LIVE_OWNED_UNLESS_ADMITTED_BY_ONE_PROVIDER":
        raise LiveOwnershipError("OWNERSHIP_DEFAULT_NOT_FAIL_CLOSED")
    providers = doc.get("providers")
    if not isinstance(providers, Mapping):
        raise LiveOwnershipError("OWNERSHIP_PROVIDERS_NOT_OBJECT")
    if tuple(sorted(providers)) != tuple(sorted(EXPECTED_PROVIDERS)):
        raise LiveOwnershipError("OWNERSHIP_PROVIDER_SET_DRIFT")
    return deepcopy(dict(doc))


def _h100_owned_ids(entries: list[Mapping[str, Any]]) -> tuple[list[str], list[dict[str, Any]]]:
    """Return stable ownership identities while preserving historical capability IDs.

    Some independently verified H100 mechanisms intentionally share a historical
    capability_id. When that occurs, route identity disambiguates the live-owned
    mechanisms without mutating historical verification artifacts.
    """
    by_id: dict[str, list[Mapping[str, Any]]] = {}
    for row in entries:
        if not isinstance(row, Mapping):
            raise LiveOwnershipError("H100_REGISTRY_ROW_NOT_OBJECT")
        cid = str(row.get("capability_id") or "").strip()
        if not cid:
            raise LiveOwnershipError("H100_CAPABILITY_ID_INVALID")
        by_id.setdefault(cid, []).append(row)

    owned_ids: list[str] = []
    collisions: list[dict[str, Any]] = []
    for cid in sorted(by_id):
        rows = by_id[cid]
        if len(rows) == 1:
            owned_ids.append("h100:" + cid)
            continue
        routes = [str(row.get("route") or "").strip() for row in rows]
        if any(not route for route in routes) or len(set(routes)) != len(routes):
            raise LiveOwnershipError("H100_CAPABILITY_COLLISION_NOT_DISAMBIGUATED:" + cid)
        identities = ["h100:" + cid + "@" + route for route in sorted(routes)]
        owned_ids.extend(identities)
        collisions.append({
            "capability_id": cid,
            "row_count": len(rows),
            "routes": sorted(routes),
            "ownership_ids": identities,
        })
    return sorted(owned_ids), collisions


def _active_skill_ids(state: Mapping[str, Any]) -> list[str]:
    out: list[str] = []
    skills = state.get("skills")
    if not isinstance(skills, Mapping):
        raise LiveOwnershipError("SELF_IMPROVEMENT_SKILLS_NOT_OBJECT")
    for sid, record in skills.items():
        if not isinstance(record, Mapping) or record.get("active") is not True:
            continue
        skill = record.get("skill")
        if not isinstance(skill, Mapping):
            raise LiveOwnershipError("ACTIVE_SKILL_RECORD_INVALID:" + str(sid))
        if skill.get("verified_skill") is not True:
            raise LiveOwnershipError("ACTIVE_SKILL_NOT_VERIFIED:" + str(sid))
        if skill.get("reuse_authorized") is not True:
            raise LiveOwnershipError("ACTIVE_SKILL_REUSE_NOT_AUTHORIZED:" + str(sid))
        out.append(str(sid))
    return sorted(out)


def evaluate(
    engine_descriptors: Mapping[str, str],
    *,
    manifest_path: str | Path = MANIFEST_PATH,
    self_improvement_state_path: str | Path = self_improvement.DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    if not isinstance(engine_descriptors, Mapping) or not engine_descriptors:
        raise LiveOwnershipError("ENGINE_DESCRIPTORS_REQUIRED")
    manifest = _load_manifest(manifest_path)
    providers = manifest["providers"]

    modes = {str(k) for k in engine_descriptors}
    provider_rows: dict[str, dict[str, Any]] = {}
    owned: list[dict[str, Any]] = []

    # Direct fabric engines are themselves live-owned entry capabilities.
    engine_ids = ["engine:" + mode for mode in sorted(modes)]
    for mode in sorted(modes):
        owned.append({
            "capability_id": "engine:" + mode,
            "provider": "FABRIC_ENGINES",
            "carrier_mode": mode,
            "carrier_kind": "DIRECT_ENGINE_MODE",
        })
    provider_rows["FABRIC_ENGINES"] = {
        "count": len(engine_ids),
        "capability_ids": engine_ids,
        "carrier_modes": sorted(modes),
    }

    # load_verified_registry is already the promoted-registry authority gate.
    bound = live_brain.load_verified_registry()
    bound_ids = sorted(str(x) for x in bound)
    for cid in bound_ids:
        owned.append({
            "capability_id": "bound:" + cid,
            "provider": "VERIFIED_BOUND_CAPABILITIES",
            "carrier_mode": str(providers["VERIFIED_BOUND_CAPABILITIES"]["fabric_carrier"]),
            "carrier_kind": "VERIFIED_BOUND_REGISTRY",
        })
    provider_rows["VERIFIED_BOUND_CAPABILITIES"] = {
        "count": len(bound_ids),
        "capability_ids": ["bound:" + x for x in bound_ids],
        "carrier_modes": [str(providers["VERIFIED_BOUND_CAPABILITIES"]["fabric_carrier"])],
    }

    state = self_improvement.load_state(self_improvement_state_path)
    skill_ids = _active_skill_ids(state)
    for sid in skill_ids:
        owned.append({
            "capability_id": sid,
            "provider": "ACTIVE_VERIFIED_LEARNED_SKILLS",
            "carrier_mode": str(providers["ACTIVE_VERIFIED_LEARNED_SKILLS"]["fabric_carrier"]),
            "carrier_kind": "VERIFIED_DYNAMIC_SKILL_STATE",
        })
    provider_rows["ACTIVE_VERIFIED_LEARNED_SKILLS"] = {
        "count": len(skill_ids),
        "capability_ids": skill_ids,
        "carrier_modes": [str(providers["ACTIVE_VERIFIED_LEARNED_SKILLS"]["fabric_carrier"])],
    }

    h100_entries = list(h100_registry.REGISTRY)
    h100_ids, h100_collisions = _h100_owned_ids(h100_entries)
    for ownership_id in h100_ids:
        owned.append({
            "capability_id": ownership_id,
            "provider": "H100_VERIFIED_CAPABILITIES",
            "carrier_mode": str(providers["H100_VERIFIED_CAPABILITIES"]["fabric_carrier"]),
            "carrier_kind": "VERIFIED_INFERENCE_REGISTRY",
        })
    provider_rows["H100_VERIFIED_CAPABILITIES"] = {
        "count": len(h100_ids),
        "registry_row_count": len(h100_entries),
        "capability_ids": h100_ids,
        "historical_id_collision_count": len(h100_collisions),
        "historical_id_collisions": h100_collisions,
        "carrier_modes": [str(providers["H100_VERIFIED_CAPABILITIES"]["fabric_carrier"])],
    }

    certified_registry = certified_route.load_registry()
    receipts, _rows = certified_route._verified_rows(certified_registry)
    route_ids = sorted({
        "certified_route:" + r.route_id
        for r in receipts
        if r.admitted is True
    })
    for cid in route_ids:
        owned.append({
            "capability_id": cid,
            "provider": "CERTIFICATE_GATED_SELECTED_ROUTES",
            "carrier_mode": str(providers["CERTIFICATE_GATED_SELECTED_ROUTES"]["fabric_carrier"]),
            "carrier_kind": "CONTENT_ADDRESSED_ROUTE_REGISTRY",
        })
    provider_rows["CERTIFICATE_GATED_SELECTED_ROUTES"] = {
        "count": len(route_ids),
        "capability_ids": route_ids,
        "carrier_modes": [str(providers["CERTIFICATE_GATED_SELECTED_ROUTES"]["fabric_carrier"])],
    }

    ids = [row["capability_id"] for row in owned]
    duplicates = sorted({cid for cid in ids if ids.count(cid) > 1})
    if duplicates:
        raise LiveOwnershipError("LIVE_OWNERSHIP_ID_COLLISION:" + ",".join(duplicates))

    missing_carriers = sorted({
        str(row["carrier_mode"])
        for row in owned
        if str(row["carrier_mode"]) not in modes
    })
    discoverable = sorted(
        row["capability_id"]
        for row in owned
        if str(row["carrier_mode"]) in modes
    )
    owned_ids = sorted(ids)
    equality = not missing_carriers and discoverable == owned_ids

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__LIVE_OWNED_EQUALS_FABRIC_REACHABLE"
            if equality
            else "FAIL_CLOSED__LIVE_OWNERSHIP_FABRIC_DIVERGENCE"
        ),
        "pass": equality,
        "manifest_status": manifest["status"],
        "ownership_default": manifest["default"],
        "provider_count": len(EXPECTED_PROVIDERS),
        "providers": provider_rows,
        "live_owned_capability_count": len(owned_ids),
        "live_owned_capability_ids": owned_ids,
        "fabric_reachable_capability_count": len(discoverable),
        "fabric_reachable_capability_ids": discoverable,
        "missing_carrier_modes": missing_carriers,
        "live_owned_equals_fabric_reachable": equality,
        "provider_coverage_complete": equality,
        "unregistered_repository_code_live_owned": False,
        "historical_repository_capability_completeness_proved": False,
        "arbitrary_raw_language_route_selection_proved": False,
        "r1_structural_closure": equality,
        "terminal_authority": False,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
