from __future__ import annotations

import hashlib
import json
from pathlib import Path

from canonical.runtime.terminal_frontier_factorizer_v2 import (
    ATOMIC,
    META,
    EXTERNAL_RESULT_ATOMS,
)

ROOT = Path(__file__).resolve().parents[2]

SOURCES = {
    "factorizer": (
        "canonical/runtime/terminal_frontier_factorizer_v2.py",
        "7bf57811d1b745cc2b92596f6c1c87ff5693aa1c",
    ),
    "normal_form": (
        "canonical/governance/OPUS55_PROTOCOL_TO_TASK_ACCEPTANCE_QUOTIENT_NORMAL_FORM_20261005_V1.json",
        "f99773af55e434f8f5b3753261b51d90d6c13213",
    ),
    "top_support": (
        "canonical/governance/HIDDEN_EVALUATOR_TARGET_FREE_TOP_SUPPORT_DOMINANCE_V1.json",
        "69e3ac04f0158bd2309c926d606d798449633f25",
    ),
    "domain_activation": (
        "canonical/governance/DOMAIN_KNOWLEDGE_QUOTIENT_THEOREM_ACTIVATION_20261005_V1.json",
        "8552ef9113c03d8a249c1c41f50e6a7e7ee10da3",
    ),
    "domain_mapping": (
        "canonical/governance/OPUS55_DOMAIN_BEHAVIORAL_QUOTIENT_MAPPING_V3.json",
        "2c40a1e326e6f7162e362ae0ceba0026e2e92ba5",
    ),
    "condition_factoring": (
        "canonical/governance/CROSS_CUTTING_CONDITION_FACTORING_THEOREM_20261005_V2.json",
        "81bbaac7b6255833fb304c7b3f457760cba51c8f",
    ),
    "creative_activation": (
        "canonical/governance/CREATIVE_DIAGRAM_TERMINAL_ACCEPTANCE_BASIS_ACTIVATION_20261005_V1.json",
        "7a88a686bde231d2570dafc5bdb07a034a0a149c",
    ),
}


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"OBJECT_REQUIRED:{path}")
    return value


def verify() -> dict:
    errors: list[str] = []

    for key, (rel, expected) in SOURCES.items():
        path = ROOT / rel
        if not path.is_file():
            errors.append(f"MISSING:{key}")
        elif git_blob_sha(path) != expected:
            errors.append(f"DRIFT:{key}")

    cut_path = ROOT / "canonical/governance/TERMINAL_BSTAR_INFORMATION_CUT_20261007_V1.json"
    if not cut_path.is_file():
        errors.append("MISSING:cut")
        return {"pass": False, "errors": errors, "terminal": False}

    cut = load_json(cut_path)
    partition = cut.get("exact_partition", {})

    obligations = set(ATOMIC) | set(META)
    external = set(EXTERNAL_RESULT_ATOMS)
    nonexternal = obligations - external

    if len(obligations) != 29:
        errors.append("CANONICAL_TRUTH_COUNT")
    if len(external) != 15:
        errors.append("CANONICAL_EXTERNAL_COUNT")
    if len(nonexternal) != 14:
        errors.append("CANONICAL_NONEXTERNAL_COUNT")

    if set(partition.get("target_specific_coordinates", [])) != external:
        errors.append("TARGET_SPECIFIC_SET")
    if set(partition.get("nonexternal_truths", [])) != nonexternal:
        errors.append("NONEXTERNAL_SET")

    programs = cut.get("zero_target_information_programs", [])
    covered: list[str] = []
    for program in programs:
        covered.extend(program.get("covers", []))

    if len(programs) != 4:
        errors.append("PROGRAM_COUNT")
    if len(covered) != len(set(covered)):
        errors.append("PROGRAM_DUPLICATE_COVERAGE")
    if set(covered) != nonexternal:
        errors.append("PROGRAM_COVERAGE")

    info = cut.get("target_specific_information_cut", {})
    if info.get("current_upper_bound_coordinates") != 15:
        errors.append("UPPER_BOUND")
    if info.get("irreducible_count") != (
        "UNKNOWN_UNTIL_EACH_COORDINATE_SURVIVES_J_G_T_OR_STRONGER_PROOF_FALSIFICATION"
    ):
        errors.append("IRREDUCIBLE_GUARD")

    required_nonclaims = {
        "NO_CLAIM_ANY_OF_THE_14_NONEXTERNAL_TRUTHS_IS_CLOSED",
        "NO_CLAIM_ALL_15_TARGET_SPECIFIC_COORDINATES_REQUIRE_FRESH_OPUS_INFORMATION",
        "NO_TRUTH_VARIABLE_DELETED_BY_THIS_SCHEDULING_REDUCTION",
        "NO_TERMINAL_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
    }
    if not required_nonclaims.issubset(set(cut.get("hard_nonclaims", []))):
        errors.append("NONCLAIM_GUARD")

    return {
        "pass": not errors,
        "errors": errors,
        "truths": 29 if not errors else None,
        "target_specific_upper_bound": 15 if not errors else None,
        "zero_target_truths": 14 if not errors else None,
        "zero_target_programs": 4 if not errors else None,
        "irreducible_target_specific_count": None,
        "truths_deleted": 0,
        "terminal": False,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    result = verify()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["pass"] else 1)
