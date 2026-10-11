"""Fail-closed O10 minimum-delta family projection.

This is scheduling compression only. It reuses the current two-engine Escape cut
and row-level reuse specialization, and groups the ten active objective rows by
the structural shape of the first decision-changing missing premise.

It grants no acceptance, capability, execution, promotion, ownership, or
terminal authority.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_ESCAPE_O10_MINIMUM_DELTA_FAMILY_PROJECTION_V1"
TWO_ENGINE_SCHEMA = "PROJECT_BRAIN_CURRENT_ESCAPE_TWO_ENGINE_MINIMUM_DELTA_CUT_20261011_V1"
SPECIALIZATION_SCHEMA = "PROJECT_BRAIN_CURRENT_FRONTIER_REUSE_SPECIALIZATION_20261011_V1"

TWO_ENGINE_PATH = "canonical/governance/CURRENT_ESCAPE_TWO_ENGINE_MINIMUM_DELTA_CUT_20261011_V1.json"
SPECIALIZATION_PATH = "canonical/governance/CURRENT_FRONTIER_REUSE_SPECIALIZATION_20261011_V1.json"

FAMILY_RULES = {
    "THRESHOLD_OR_DECOMPOSITION_EVIDENCE": {
        "rows": {
            "CODING_TB4_GE_66_4": ("DISTINGUISHING_TB4_PREMISE",),
            "CODING_CURSORBENCH_GE_57_8": ("SCORE_CONTRIBUTION", "AGGREGATION_AUTHORITY"),
            "FINANCE_ACCOUNTING_INDEX_GE_61": ("NORMALIZED_COMPONENT_LOWER_BOUND", "NORMALIZATION_BINDINGS"),
        },
        "v4_first_route": "THRESHOLD_LOWER_BOUND",
        "existing_machinery": [
            "canonical/runtime/benchmark_witness_elimination_compiler_v4.py",
            "canonical/runtime/current_escape_o11_objective_acceptance_law_gate_v1.py",
        ],
        "acquisition_rule": "ACQUIRE_ONLY_A_CONTENT_ADDRESSED_SCORE_OR_DECOMPOSITION_FACT_CAPABLE_OF_CHANGING_THE_PROVED_LOWER_BOUND_OR_A_STRONGER_SCOPE_COMPLETE_CERTIFICATE",
    },
    "SCOPE_COMPLETENESS": {
        "rows": {
            "AUTOMATIONBENCH_GE_40": ("PRIVATE_TASK_SCOPE",),
            "OSWORLD_2_1_PARTIAL_GE_81_8": ("PINNED_TASK_SEMANTICS",),
            "FINANCE_AGENT_V2_GE_58_59": ("PRIVATE_SCOPE_BIND",),
            "MYSTERYMECHANISM_INTRINSIC_OPUS55_NONINFERIORITY_OR_STRONGER": ("FINITE_COVERAGE",),
        },
        "v4_first_route": "SCOPE_SUPERSET",
        "existing_machinery": [
            "canonical/runtime/proof_carrying_scope_cover_v1.py",
            "canonical/runtime/benchmark_witness_elimination_compiler_v4.py",
            "canonical/runtime/current_escape_o11_objective_acceptance_law_gate_v1.py",
        ],
        "acquisition_rule": "ACQUIRE_ONLY_SCOPE_SEMANTICS_OR_A_FORMAL_SUPERSET_FACT_THAT_CAN_CHANGE_SCOPE_COMPLETENESS__DO_NOT_ACQUIRE_SCORE_DATA_BEFORE_SCOPE_IS_SOUND",
    },
    "OWNER_OR_EVALUATOR_INTERFACE": {
        "rows": {
            "CODING_FRONTIERCODE_GE_54_4": ("OWNER_INTAKE", "HARNESS_ADMISSIBILITY"),
            "HLE_TOOLS_GE_67_7": ("COMPARABLE_GRADER_RELATION",),
            "CHARTOGRAPHY_TOOLS_GE_89": ("JUDGE_CAPACITY", "ADAPTER_BINDING"),
        },
        "v4_first_route": "EVALUATOR_OR_IDENTITY_LOCK_THEN_OBJECTIVE_ROUTE",
        "existing_machinery": [
            "canonical/runtime/benchmark_witness_elimination_compiler_v4.py",
            "canonical/runtime/current_escape_o11_objective_acceptance_law_gate_v1.py",
        ],
        "acquisition_rule": "ACQUIRE_ONLY_OWNER_OR_EVALUATOR_INTERFACE_FACTS_NEEDED_TO_BIND_CURRENT_IDENTITY_EVALUATOR_RELATION_AND_RESOURCE_ADMISSIBLE_EXECUTION__NO_SCORE_BEARING_RUN_BEFORE_THOSE_LOCKS",
    },
}


class ProjectionError(ValueError):
    pass


def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _load(root: Path, rel: str) -> Mapping[str, Any]:
    p = (root / rel).resolve(strict=True)
    p.relative_to(root)
    doc = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping):
        raise ProjectionError("JSON_OBJECT_REQUIRED:" + rel)
    return doc


def compile_projection(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve(strict=True) if repo_root is not None else Path(__file__).resolve().parents[2]
    two = _load(root, TWO_ENGINE_PATH)
    spec = _load(root, SPECIALIZATION_PATH)
    if two.get("schema") != TWO_ENGINE_SCHEMA:
        raise ProjectionError("TWO_ENGINE_SCHEMA_MISMATCH")
    if spec.get("schema") != SPECIALIZATION_SCHEMA:
        raise ProjectionError("SPECIALIZATION_SCHEMA_MISMATCH")

    part = two.get("current_partition")
    if not isinstance(part, Mapping):
        raise ProjectionError("CURRENT_PARTITION_MISSING")
    active_o = part.get("active_o_obligation_ids")
    if not isinstance(active_o, list) or len(active_o) != 10 or len(set(active_o)) != 10:
        raise ProjectionError("ACTIVE_O10_SET_INVALID")
    if part.get("active_o_rows") != 10 or part.get("active_q_rows") != 2 or part.get("parked_rows") != 1:
        raise ProjectionError("TWO_ENGINE_COUNT_INVARIANT_FAILED")

    rows = spec.get("active_rows")
    if not isinstance(rows, list) or len(rows) != 12:
        raise ProjectionError("SPECIALIZATION_ACTIVE_ROWS_INVALID")
    row_by_id = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ProjectionError("SPECIALIZATION_ROW_INVALID")
        rid = row.get("id")
        if not isinstance(rid, str) or not rid or rid in row_by_id:
            raise ProjectionError("SPECIALIZATION_ROW_ID_INVALID_OR_DUPLICATE")
        row_by_id[rid] = row

    expected = set()
    families = []
    for family_id, rule in FAMILY_RULES.items():
        frows = []
        for rid, required_tokens in rule["rows"].items():
            expected.add(rid)
            if rid not in active_o:
                raise ProjectionError("FAMILY_ROW_NOT_ACTIVE_O10:" + rid)
            row = row_by_id.get(rid)
            if row is None:
                raise ProjectionError("SPECIALIZATION_ROW_MISSING:" + rid)
            delta = row.get("delta")
            if not isinstance(delta, str) or not delta:
                raise ProjectionError("DELTA_MISSING:" + rid)
            for token in required_tokens:
                if token not in delta:
                    raise ProjectionError("DELTA_RULE_DRIFT:" + rid + ":" + token)
            frows.append({
                "obligation_id": rid,
                "reuse": row.get("reuse"),
                "exact_delta": delta,
                "mode": row.get("mode"),
            })
        families.append({
            "family_id": family_id,
            "row_count": len(frows),
            "rows": sorted(frows, key=lambda x: x["obligation_id"]),
            "v4_first_route": rule["v4_first_route"],
            "existing_machinery": list(rule["existing_machinery"]),
            "acquisition_rule": rule["acquisition_rule"],
        })

    if set(active_o) != expected:
        raise ProjectionError("O10_FAMILY_PARTITION_NOT_EXACT")

    family_rows = [r["obligation_id"] for f in families for r in f["rows"]]
    if len(family_rows) != len(set(family_rows)) or set(family_rows) != set(active_o):
        raise ProjectionError("O10_FAMILY_PARTITION_OVERLAP_OR_GAP")

    return {
        "schema": SCHEMA,
        "status": "PASS__O10_COMPRESSED_TO_3_MINIMUM_DELTA_FAMILIES__ZERO_CREDIT",
        "source_bindings": {
            "two_engine": {"path": TWO_ENGINE_PATH, "git_blob_sha": _blob(root / TWO_ENGINE_PATH)},
            "row_specialization": {"path": SPECIALIZATION_PATH, "git_blob_sha": _blob(root / SPECIALIZATION_PATH)},
        },
        "active_o_row_count": 10,
        "minimum_delta_family_count": 3,
        "families": sorted(families, key=lambda x: x["family_id"]),
        "scheduler_rule": [
            "RUN_FAMILIES_AS_SHARED_ACQUISITION_OR_PROOF_SHAPES__NOT_TEN_BESPOKE_RESEARCH_PROGRAMS",
            "WITHIN_EACH_ROW_TRY_STRONGER_SCOPE_COMPLETE_OR_OBJECTIVE_PROOF_BEFORE_ACQUIRING_NEW_REALITY",
            "AFTER_EACH_NEW_FACT_REENTER_EXISTING_V4_O_GATE_AND_STOP_ACQUISITION_AS_SOON_AS_THE_ROW_VERDICT_CHANGES",
            "A_SHARED_FAMILY_DOES_NOT_IMPLY_ONE_FACT_CLOSES_EVERY_ROW_IN_THE_FAMILY",
        ],
        "new_primitive_required": False,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "ownership_authority": False,
        "terminal_authority": False,
        "accounting": {
            "incremental_spend_usd": 0,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "terminal_credit_delta": 0,
        },
        "hard_nonclaims": [
            "NO_O_ROW_ACCEPTANCE_CLOSED",
            "NO_CLAIM_ONE_FACT_PER_FAMILY_IS_SUFFICIENT",
            "NO_Q2_RESULT",
            "NO_CC_R3_OR_U_EMPTY",
        ],
    }


def run(args=None, root=None):
    return compile_projection(repo_root=root)


if __name__ == "__main__":
    print(json.dumps(compile_projection(), indent=2, sort_keys=True))
