"""Live capability ownership ontology verifier V1.

Defines the current live Brain as capabilities admitted by the authoritative
provider manifest. Repository code outside those providers is not live-owned
merely because it exists.

This module verifies structural R1 closure:
  live-owned capability -> discoverable carrier -> executable/composable fabric path

It does not claim arbitrary-language semantic routing completeness.
"""
from __future__ import annotations

import hashlib
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
AUTHORITY_PATH = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"

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


def _git_blob_sha(path: str | Path) -> str:
    p = Path(path)
    raw = p.read_bytes()
    prefix = ("blob " + str(len(raw)) + "\0").encode("ascii")
    return hashlib.sha1(prefix + raw).hexdigest()


def _authority_binding_check(
    *,
    repo_root: str | Path = ROOT,
    authority_path: str | Path = AUTHORITY_PATH,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    pointer_path = Path(authority_path)
    if not pointer_path.is_absolute():
        pointer_path = (root / pointer_path).resolve()
    doc = json.loads(pointer_path.read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping):
        raise LiveOwnershipError("CURRENT_TERMINAL_AUTHORITY_NOT_OBJECT")

    ownership = doc.get("live_capability_ownership_20261008_v1")
    invocation = doc.get("r1_universal_live_capability_invocation_20261008_v1")
    if not isinstance(ownership, Mapping):
        raise LiveOwnershipError("LIVE_OWNERSHIP_AUTHORITY_NODE_MISSING")
    if not isinstance(invocation, Mapping):
        raise LiveOwnershipError("LIVE_INVOCATION_AUTHORITY_NODE_MISSING")

    expected = (
        (ownership, "governance", "canonical/governance/LIVE_CAPABILITY_OWNERSHIP_MANIFEST_V1.json"),
        (ownership, "runtime", "canonical/runtime/live_capability_ownership_v1.py"),
        (ownership, "invoker", "canonical/runtime/live_capability_invoker_v1.py"),
        (ownership, "unified_fabric", "canonical/runtime/unified_cognitive_fabric_v1.py"),
        (ownership, "subordinate_runtime", "canonical/runtime/live_brain_runtime_v1.py"),
        (ownership, "activation", "canonical/governance/LIVE_BRAIN_RUNTIME_V1_ACTIVATION_20261008_V1.json"),
        (
            ownership,
            "verification",
            "canonical/verification/LIVE_CAPABILITY_OWNERSHIP_UNIVERSAL_INVOCATION_V1_SOURCE_REPLAY_20261008_V1.json",
        ),
        (invocation, "runtime", "canonical/runtime/live_capability_invoker_v1.py"),
        (invocation, "unified_fabric", "canonical/runtime/unified_cognitive_fabric_v1.py"),
        (invocation, "regression", "canonical/tests/test_live_capability_invoker_v1.py"),
        (invocation, "workflow", ".github/workflows/verify-unified-cognitive-fabric-v1.yml"),
        (
            invocation,
            "verification",
            "canonical/verification/LIVE_CAPABILITY_OWNERSHIP_UNIVERSAL_INVOCATION_V1_SOURCE_REPLAY_20261008_V1.json",
        ),
    )

    checked: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    for node, field, expected_path in expected:
        binding = node.get(field)
        if not isinstance(binding, Mapping):
            mismatches.append({"field": field, "reason": "BINDING_NOT_OBJECT"})
            continue
        path = str(binding.get("path") or "")
        declared = str(binding.get("git_blob_sha") or "")
        if path != expected_path:
            mismatches.append({
                "field": field,
                "reason": "PATH_MISMATCH",
                "expected_path": expected_path,
                "declared_path": path,
            })
            continue
        candidate = (root / path).resolve()
        if root not in candidate.parents or not candidate.is_file():
            mismatches.append({"field": field, "reason": "BOUND_FILE_MISSING", "path": path})
            continue
        actual = _git_blob_sha(candidate)
        row = {"field": field, "path": path, "declared_git_blob_sha": declared, "actual_git_blob_sha": actual}
        checked.append(row)
        if declared != actual:
            mismatches.append({**row, "reason": "GIT_BLOB_SHA_MISMATCH"})

    if ownership.get("canonical_public_entrypoint") != "canonical.runtime.unified_cognitive_fabric_v1.run":
        mismatches.append({"field": "canonical_public_entrypoint", "reason": "PUBLIC_ENTRYPOINT_DRIFT"})
    if ownership.get("subordinate_runtime_public_authority") is not False:
        mismatches.append({"field": "subordinate_runtime_public_authority", "reason": "SUBRUNTIME_AUTHORITY_DRIFT"})

    verification = ownership.get("verification")
    receipt_path = (
        str(verification.get("path") or "")
        if isinstance(verification, Mapping)
        else ""
    )
    receipt = None
    if receipt_path:
        rp = (root / receipt_path).resolve()
        if root in rp.parents and rp.is_file():
            raw_receipt = json.loads(rp.read_text(encoding="utf-8"))
            if isinstance(raw_receipt, Mapping):
                receipt = raw_receipt
    if not isinstance(receipt, Mapping):
        mismatches.append({"field": "verification.exact_blobs", "reason": "VERIFICATION_RECEIPT_INVALID"})
    else:
        exact = receipt.get("exact_blobs")
        if not isinstance(exact, Mapping):
            mismatches.append({"field": "verification.exact_blobs", "reason": "EXACT_BLOBS_NOT_OBJECT"})
        else:
            for name, binding in sorted(exact.items()):
                if not isinstance(binding, Mapping):
                    mismatches.append({"field": "receipt:" + str(name), "reason": "BINDING_NOT_OBJECT"})
                    continue
                path = str(binding.get("path") or "")
                declared = str(binding.get("git_blob_sha") or "")
                candidate = (root / path).resolve()
                if (
                    not path
                    or root not in candidate.parents
                    or not candidate.is_file()
                ):
                    mismatches.append({"field": "receipt:" + str(name), "reason": "BOUND_FILE_MISSING", "path": path})
                    continue
                actual = _git_blob_sha(candidate)
                row = {
                    "field": "receipt:" + str(name),
                    "path": path,
                    "declared_git_blob_sha": declared,
                    "actual_git_blob_sha": actual,
                }
                checked.append(row)
                if declared != actual:
                    mismatches.append({**row, "reason": "GIT_BLOB_SHA_MISMATCH"})

    passed = not mismatches
    return {
        "pass": passed,
        "status": (
            "PASS__R1_AUTHORITY_AND_RECEIPT_BINDINGS_CURRENT"
            if passed
            else "FAIL_CLOSED__R1_AUTHORITY_OR_RECEIPT_DRIFT"
        ),
        "checked_binding_count": len(checked),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }


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
    authority_path: str | Path = AUTHORITY_PATH,
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
    authority_binding = _authority_binding_check(
        repo_root=ROOT,
        authority_path=authority_path,
    )
    closure = equality and authority_binding["pass"] is True

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__LIVE_OWNED_EQUALS_FABRIC_REACHABLE__AUTHORITY_CURRENT"
            if closure
            else (
                "FAIL_CLOSED__R1_AUTHORITY_OR_RECEIPT_DRIFT"
                if equality
                else "FAIL_CLOSED__LIVE_OWNERSHIP_FABRIC_DIVERGENCE"
            )
        ),
        "pass": closure,
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
        "authority_binding": authority_binding,
        "authority_binding_current": authority_binding["pass"],
        "unregistered_repository_code_live_owned": False,
        "historical_repository_capability_completeness_proved": False,
        "arbitrary_raw_language_route_selection_proved": False,
        "r1_structural_closure": closure,
        "terminal_authority": False,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
