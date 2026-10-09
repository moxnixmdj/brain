from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = {
    "canonical/governance/CURSORBENCH_TYPED_ACCEPTANCE_PLAN_POLICY_ADEQUACY_CERTIFICATE_20261009_V2.json":
        "bddb8f51f6dc91f98759c5c3b92c1257ca8b9577",
    "canonical/governance/CODING_FINITE_EXACT_ORACLE_POLICY_ADEQUACY_CERTIFICATE_20261009_V1.json":
        "458f7362ac3930ba62260585b323fb5c17ce2ff8",
    "canonical/governance/CODING_ROBUST_FINITE_MULTI_INTERPRETATION_POLICY_ADEQUACY_CERTIFICATE_20261009_V1.json":
        "7924c5a4d5e38e1d417d56c8be08575587ed66fd",
    "canonical/governance/CURSORBENCH_OWNER_ACCESS_BOUNDARY_V1.json":
        "d58c41a8e93fc95df6667e955e291b3f36c8942f",
    "canonical/governance/CURSORBENCH_4_0_SCOPE_COMPLETENESS_RECEIPT_V1.json":
        "7401589da3b30954104145dc4959e534ab8cd641",
}

def _blob(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()

def _load(rel: str) -> dict[str, Any]:
    value = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(rel + ":NOT_OBJECT")
    return value

def _atoms(condition: Mapping[str, Any]) -> list[str]:
    if condition.get("op") == "ATOM":
        atom = condition.get("id")
        if not isinstance(atom, str) or not atom:
            raise ValueError("ATOM_INVALID")
        return [atom]
    if condition.get("op") != "AND":
        raise ValueError("ONLY_CONJUNCTION_REGION_EXPECTED")
    rows = condition.get("args")
    if not isinstance(rows, list) or not rows:
        raise ValueError("AND_ARGS_INVALID")
    out: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("AND_ROW_INVALID")
        out.extend(_atoms(row))
    return out

def covered(valuation: Mapping[str, bool], regions: Sequence[Sequence[str]]) -> bool:
    return any(all(valuation.get(atom) is True for atom in region) for region in regions)

def verify() -> dict[str, Any]:
    errors: list[str] = []
    for rel, expected in EXPECTED.items():
        full = ROOT / rel
        if not full.is_file():
            errors.append("SOURCE_MISSING:" + rel)
        elif _blob(full) != expected:
            errors.append("SOURCE_DRIFT:" + rel)

    if errors:
        return {
            "schema":"PROJECT_BRAIN_CURSORBENCH_THREE_REGION_COMPLEMENT_NONIDENTIFIABILITY_VERIFIER_V1",
            "pass":False,"status":"FAIL_CLOSED","errors":errors,
            "terminal_authority":False,"terminal_credit_delta":0,
        }

    typed = _load("canonical/governance/CURSORBENCH_TYPED_ACCEPTANCE_PLAN_POLICY_ADEQUACY_CERTIFICATE_20261009_V2.json")
    finite = _load("canonical/governance/CODING_FINITE_EXACT_ORACLE_POLICY_ADEQUACY_CERTIFICATE_20261009_V1.json")
    robust = _load("canonical/governance/CODING_ROBUST_FINITE_MULTI_INTERPRETATION_POLICY_ADEQUACY_CERTIFICATE_20261009_V1.json")
    owner = _load("canonical/governance/CURSORBENCH_OWNER_ACCESS_BOUNDARY_V1.json")
    scope = _load("canonical/governance/CURSORBENCH_4_0_SCOPE_COMPLETENESS_RECEIPT_V1.json")

    regions = [
        _atoms(typed["policy_condition"]),
        _atoms(finite["policy_condition"]),
        _atoms(robust["policy_condition"]),
    ]
    expected_counts = [5,6,7]
    for idx,(atoms,count) in enumerate(zip(regions,expected_counts)):
        if len(atoms) != count or len(set(atoms)) != count:
            errors.append(f"REGION_{idx}_ATOM_SET_DRIFT")

    all_atoms = [a for region in regions for a in region]
    if len(set(all_atoms)) != len(all_atoms):
        errors.append("REGION_ATOM_SETS_UNEXPECTEDLY_OVERLAP")

    if typed.get("membership_self_certified") is not False:
        errors.append("TYPED_MEMBERSHIP_SELF_CERTIFICATION_DRIFT")
    if (typed.get("target_relevance") or {}).get("current_hidden_cursorbench_task_membership_proved") is not False:
        errors.append("TYPED_HIDDEN_MEMBERSHIP_ALREADY_PROVED")
    if finite.get("target_membership_proved") is not False:
        errors.append("FINITE_HIDDEN_MEMBERSHIP_ALREADY_PROVED")
    if robust.get("target_membership_proved") is not False:
        errors.append("ROBUST_HIDDEN_MEMBERSHIP_ALREADY_PROVED")
    if robust.get("interpretation_set_completeness_self_certified") is not False:
        errors.append("ROBUST_INTERPRETATION_COMPLETENESS_SELF_CERTIFICATION_DRIFT")
    if "PRIVATE_AND_HELDOUT_TASKS_STAY_PRIVATE" not in set(owner.get("owner_facts") or []):
        errors.append("OWNER_PRIVACY_BOUNDARY_DRIFT")
    if scope.get("scope_complete") is not True:
        errors.append("CURSORBENCH_SCOPE_NOT_CLOSED")
    if scope.get("positive_adequacy_cover_closed") is not False:
        errors.append("CURSORBENCH_COVER_ALREADY_CLOSED")

    world_cover = {a: True for a in all_atoms}
    world_escape = {a: True for a in all_atoms}
    for region in regions:
        world_escape[region[0]] = False

    cover_result = covered(world_cover, regions)
    escape_result = covered(world_escape, regions)
    if cover_result is not True:
        errors.append("COVER_WORLD_NOT_COVERED")
    if escape_result is not False:
        errors.append("ESCAPE_WORLD_NOT_IN_COMPLEMENT")

    passed = not errors
    return {
        "schema":"PROJECT_BRAIN_CURSORBENCH_THREE_REGION_COMPLEMENT_NONIDENTIFIABILITY_VERIFIER_V1",
        "pass":passed,
        "status":(
            "PASS__THREE_REGION_COMPLEMENT_EMPTINESS_NOT_IDENTIFIED_BY_CURRENT_EVIDENCE__ZERO_CREDIT"
            if passed else "FAIL_CLOSED"
        ),
        "errors":errors,
        "region_atom_counts":[len(x) for x in regions],
        "total_distinct_condition_atoms":len(set(all_atoms)),
        "world_cover_union_membership":cover_result,
        "world_escape_union_membership":escape_result,
        "actual_complement_empty_claimed":False,
        "actual_complement_nonempty_claimed":False,
        "current_evidence_identifies_complement_emptiness":False if passed else None,
        "promotion_authority":False,
        "acceptance_credit_delta":0,
        "terminal_credit_delta":0,
    }

if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
