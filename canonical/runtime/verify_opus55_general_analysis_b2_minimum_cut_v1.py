"""Fail-closed verifier for the generic Opus 5.5 B2 analysis minimum cut."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = "canonical/governance/OPUS55_GENERAL_ANALYSIS_B2_MINIMUM_CUT_20261005_V1.json"
ENVELOPE = "canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json"
BASIS = "canonical/governance/OPUS55_OBSERVABLE_BEHAVIOR_FUNCTIONAL_BASIS_CHARACTERIZATION_20261005_V1.json"

EXPECTED_BLOBS = {
    ENVELOPE: "661a57f839101fbf54c7e4edc76166c65ce9327d",
    BASIS: "62c0e207ce935a02611700a69e0917f938792b11",
}


class VerificationError(RuntimeError):
    pass


def _raw(path: str, root: Path = ROOT) -> bytes:
    p = root / path
    if not p.is_file():
        raise VerificationError("MISSING:" + path)
    return p.read_bytes()


def _load(path: str, root: Path = ROOT) -> dict[str, Any]:
    try:
        obj = json.loads(_raw(path, root))
    except Exception as exc:
        raise VerificationError("INVALID_JSON:" + path + ":" + str(exc)) from exc
    if not isinstance(obj, dict):
        raise VerificationError("NOT_OBJECT:" + path)
    return obj


def _git_blob_sha(path: str, root: Path = ROOT) -> str:
    payload = _raw(path, root)
    return hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()


def _must(ok: bool, code: str) -> None:
    if not ok:
        raise VerificationError(code)


def verify(root: Path = ROOT) -> dict[str, Any]:
    for path, expected in EXPECTED_BLOBS.items():
        _must(_git_blob_sha(path, root) == expected, "BOUND_BLOB_DRIFT:" + path)

    c = _load(CANDIDATE, root)
    e = _load(ENVELOPE, root)
    b = _load(BASIS, root)

    _must(c.get("schema") == "PROJECT_BRAIN_OPUS55_GENERAL_ANALYSIS_B2_MINIMUM_CUT_20261005_V1", "SCHEMA")
    _must(c.get("independent_verification_required") is True, "INDEPENDENCE")
    for key in ("scheduling_authority", "execution_authority", "promotion_authority", "fresh_reality_authority"):
        _must(c.get(key) is False, "AUTHORITY_LEAK:" + key)

    acct = c.get("accounting")
    _must(isinstance(acct, dict), "ACCOUNTING")
    for key in ("incremental_spend_usd", "new_reality_units_consumed", "terminal_cases_consumed",
                "acceptance_credit_delta", "family_credit_delta", "capability_credit_delta", "ownership_credit_delta"):
        _must(acct.get(key) == 0, "CREDIT_OR_SPEND_LEAK:" + key)

    fam = next((x for x in e.get("families", []) if x.get("id") == "MULTIDISCIPLINARY_TOOL_AUGMENTED_REASONING"), None)
    _must(isinstance(fam, dict), "TARGET_FAMILY_MISSING")
    _must(fam.get("useful_behavior") == "Solve difficult expert-level questions across domains with search/code/tools.",
          "TARGET_FAMILY_WORDING_DRIFT")

    b2 = next((x for x in b.get("functional_basis", []) if x.get("id") == "B2_INFORMATION_TRANSFORMATION_REASONING_AND_PROBLEM_SOLVING"), None)
    _must(isinstance(b2, dict), "B2_MISSING")
    _must("MULTIDISCIPLINARY_TOOL_AUGMENTED_REASONING" in b2.get("families", []), "B2_PARENT_MAPPING_MISSING")

    part = c.get("breakthrough_partition")
    _must(isinstance(part, dict), "PARTITION_MISSING")
    cells = part.get("cells")
    _must(isinstance(cells, list) and len(cells) == 2, "PARTITION_CARDINALITY")
    by_id = {x.get("id"): x for x in cells if isinstance(x, dict)}
    _must(set(by_id) == {"B2A_ABSOLUTE_CEILING_ANALYSIS", "B2B_OPEN_QUALITY_ANALYSIS"}, "PARTITION_IDS")

    a = by_id["B2A_ABSOLUTE_CEILING_ANALYSIS"]
    _must(a.get("new_target_comparator_required_if_ceiling_proved") is False, "B2A_COMPARATOR_LEAK")
    _must(a.get("new_learned_primitive_required") is False, "B2A_PRIMITIVE_LEAK")
    _must(a.get("credit_now") is False, "B2A_CREDIT_LEAK")

    q = by_id["B2B_OPEN_QUALITY_ANALYSIS"]
    _must(q.get("minimum_new_acceptance_obligation_if_no_stronger_proof_exists") ==
          "GENERAL_ANALYSIS_OPEN_QUALITY_NONINFERIOR", "B2B_ATOM")
    _must(q.get("new_broad_primitive_required_by_this_partition") is False, "B2B_PRIMITIVE_LEAK")
    _must(q.get("credit_now") is False, "B2B_CREDIT_LEAK")

    repair = c.get("candidate_target_envelope_repair", {}).get("preferred_no_new_family_route", {})
    _must(repair.get("family") == "MULTIDISCIPLINARY_TOOL_AUGMENTED_REASONING", "REPAIR_FAMILY")
    wording = repair.get("successor_useful_behavior", "")
    _must("ordinary non-specialized analysis" in wording and "optionally using search" in wording, "REPAIR_NOT_ACTUALLY_WIDENED")
    _must(repair.get("requires_independent_review_before_canonical_mutation") is True, "MUTATION_GUARD")

    atom = c.get("acceptance_reduction", {}).get("new_atom_candidate", {})
    _must(atom.get("id") == "GENERAL_ANALYSIS_OPEN_QUALITY_NONINFERIOR", "ATOM_ID")
    _must(atom.get("fresh_reality_authority") is False, "ATOM_REALITY_LEAK")
    dims = atom.get("minimum_quality_dimensions")
    _must(isinstance(dims, list) and len(dims) >= 6, "ATOM_DIMENSIONS_TOO_WEAK")

    term = c.get("terminal_effect", {})
    _must(term.get("literal_terminal") is False, "FALSE_FINALITY")
    _must(term.get("root1_positive_new_primitive_gap_delta") == 0, "UNPROVED_PRIMITIVE_GAP")

    return {
        "schema": "PROJECT_BRAIN_OPUS55_GENERAL_ANALYSIS_B2_MINIMUM_CUT_VERIFICATION_V1",
        "status": "PASS",
        "partition": ["B2A_ABSOLUTE_CEILING_ANALYSIS", "B2B_OPEN_QUALITY_ANALYSIS"],
        "new_broad_primitive_claimed": False,
        "maximum_new_open_quality_atom_after_ceiling_reuse": 1,
        "acceptance_credit_delta": 0,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
