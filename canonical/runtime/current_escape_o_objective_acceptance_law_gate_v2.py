"""Current-projection-aware objective acceptance gate.

Successor to current_escape_o11_objective_acceptance_law_gate_v1. The proof
kernel is unchanged; only current O/Q/parked membership is resolved from the
canonical two-engine current cut so scheduler and executor cannot disagree.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.benchmark_witness_elimination_compiler_v4 import evaluate_claim

SCHEMA = "PROJECT_BRAIN_CURRENT_ESCAPE_O_OBJECTIVE_ACCEPTANCE_LAW_GATE_V2"
CUT_SCHEMA = "PROJECT_BRAIN_CURRENT_ESCAPE_TWO_ENGINE_MINIMUM_DELTA_CUT_20261011_V1"
MANIFEST_SCHEMA = "PROJECT_BRAIN_ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_V2"
CUT_PATH = Path("canonical/governance/CURRENT_ESCAPE_TWO_ENGINE_MINIMUM_DELTA_CUT_20261011_V1.json")
CURRENT_RESIDUAL_PATH = Path("canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json")
CURRENT_RESIDUAL_SCHEMA = "PROJECT_BRAIN_CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1"
GDPVAL_RECLASS_SCHEMA = "PROJECT_BRAIN_GDPVAL_CURRENT_FIXED_BAR_ENGINE_RECLASSIFICATION_20261011_V1"
GDPVAL_VERIFY_SCHEMA = "PROJECT_BRAIN_GDPVAL_FIXED_BAR_OWNER_PAIRWISE_NONNECESSITY_VERIFICATION_20261009_V1"
GDPVAL = "PROWORK_GDPVAL_GE_1846"
AA_BRIEFCASE = "PROWORK_AA_BRIEFCASE_GE_1822__SHARED_MEASUREMENT_WITH_ARTIFACT"
TB_SCIENCE = "TB_SCIENCE_GE_58_7"


def _git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _load(path: Path) -> Mapping[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping):
        raise ValueError("JSON_OBJECT_REQUIRED:" + str(path))
    return doc


def _current_projection(root: Path) -> tuple[set[str], set[str], set[str], Mapping[str, Any]]:
    """Resolve O/Q/parked membership through the mutable current residual authority."""
    current = _load(root / CURRENT_RESIDUAL_PATH)
    if current.get("schema") != CURRENT_RESIDUAL_SCHEMA:
        raise ValueError("CURRENT_RESIDUAL_SCHEMA_INVALID")

    topology = current.get("escape_current_topology")
    if not isinstance(topology, Mapping):
        raise ValueError("CURRENT_ESCAPE_TOPOLOGY_MISSING")
    parked_ids = topology.get("parked_obligation_ids")
    if (
        topology.get("frozen_obligation_count") != 13
        or topology.get("active_gap_a_acquisition_rows") != 12
        or topology.get("active_gap_b_strict_progress_rows") != 0
        or topology.get("parked_unresolved_rows") != 1
        or not isinstance(parked_ids, list)
        or any(not isinstance(x, str) or not x for x in parked_ids)
        or set(parked_ids) != {TB_SCIENCE}
    ):
        raise ValueError("CURRENT_ESCAPE_TOPOLOGY_INVARIANT_FAILED")

    cut_ref = current.get("current_escape_two_engine_minimum_delta_cut")
    if not isinstance(cut_ref, Mapping):
        raise ValueError("CURRENT_TWO_ENGINE_CUT_REFERENCE_MISSING")
    cut_rel = cut_ref.get("path")
    cut_sha = cut_ref.get("git_blob_sha")
    if not isinstance(cut_rel, str) or not cut_rel:
        raise ValueError("CURRENT_TWO_ENGINE_CUT_PATH_INVALID")
    if not isinstance(cut_sha, str) or len(cut_sha) != 40:
        raise ValueError("CURRENT_TWO_ENGINE_CUT_SHA_INVALID")
    cut_path = root / cut_rel
    if not cut_path.is_file():
        raise ValueError("CURRENT_TWO_ENGINE_CUT_MISSING")
    if _git_blob(cut_path) != cut_sha:
        raise ValueError("CURRENT_TWO_ENGINE_CUT_BLOB_DRIFT")
    cut = _load(cut_path)
    if cut.get("schema") != CUT_SCHEMA:
        raise ValueError("CURRENT_CUT_SCHEMA_INVALID")
    if cut.get("status") != cut_ref.get("status"):
        raise ValueError("CURRENT_TWO_ENGINE_CUT_STATUS_MISMATCH")

    bindings = cut.get("source_bindings")
    if not isinstance(bindings, Mapping):
        raise ValueError("CURRENT_CUT_SOURCE_BINDINGS_INVALID")
    manifest_ref = bindings.get("manifest")
    if (
        not isinstance(manifest_ref, list)
        or len(manifest_ref) != 2
        or not isinstance(manifest_ref[0], str)
        or not isinstance(manifest_ref[1], str)
        or len(manifest_ref[1]) != 40
    ):
        raise ValueError("CURRENT_CUT_MANIFEST_BINDING_INVALID")
    manifest_path = root / manifest_ref[0]
    if not manifest_path.is_file():
        raise ValueError("CURRENT_CUT_MANIFEST_MISSING")
    if _git_blob(manifest_path) != manifest_ref[1]:
        raise ValueError("CURRENT_CUT_MANIFEST_BLOB_DRIFT")
    manifest = _load(manifest_path)
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("CURRENT_CUT_MANIFEST_SCHEMA_INVALID")

    rows = manifest.get("rows")
    if not isinstance(rows, list) or len(rows) != 13:
        raise ValueError("CURRENT_MANIFEST_ROWS_INVALID")
    all_ids: set[str] = set()
    for row in rows:
        oid = row.get("obligation_id") if isinstance(row, Mapping) else None
        if not isinstance(oid, str) or not oid or oid in all_ids:
            raise ValueError("CURRENT_MANIFEST_ROW_ID_INVALID_OR_DUPLICATE")
        all_ids.add(oid)

    reclass_ref = bindings.get("gdpval_fixed_bar_reclassification")
    if (
        not isinstance(reclass_ref, list)
        or len(reclass_ref) != 2
        or not isinstance(reclass_ref[0], str)
        or not reclass_ref[0]
        or not isinstance(reclass_ref[1], str)
        or len(reclass_ref[1]) != 40
    ):
        raise ValueError("GDPVAL_RECLASSIFICATION_BINDING_INVALID")
    reclass_path = root / reclass_ref[0]
    if _git_blob(reclass_path) != reclass_ref[1]:
        raise ValueError("GDPVAL_RECLASSIFICATION_BLOB_DRIFT")
    reclass = _load(reclass_path)
    if reclass.get("schema") != GDPVAL_RECLASS_SCHEMA or reclass.get("target_obligation") != GDPVAL:
        raise ValueError("GDPVAL_RECLASSIFICATION_IDENTITY_INVALID")
    shape = reclass.get("current_acceptance_shape")
    effect = reclass.get("engine_effect")
    if (
        not isinstance(shape, Mapping)
        or shape.get("acceptance_relation_class") != "OBJECTIVE_FIXED_BAR"
        or shape.get("hidden_owner_pairwise_relation_is_free_variable_of_decision") is not False
        or not isinstance(effect, Mapping)
        or effect.get("previous") != "Q_ACCEPTANCE_RELATION_ROBUST_COMMON_POLICY"
        or effect.get("current") != "O_OBJECTIVE_ACCEPTANCE_INSTANTIATION"
        or effect.get("new_primitive_required") is not False
    ):
        raise ValueError("GDPVAL_RECLASSIFICATION_SEMANTICS_INVALID")

    source_bindings = reclass.get("source_bindings")
    verify_ref = source_bindings.get("fixed_bar_nonnecessity_verification") if isinstance(source_bindings, Mapping) else None
    if not isinstance(verify_ref, Mapping):
        raise ValueError("GDPVAL_RECLASSIFICATION_VERIFICATION_BINDING_MISSING")
    verify_rel = verify_ref.get("path")
    verify_sha = verify_ref.get("git_blob_sha")
    if not isinstance(verify_rel, str) or not verify_rel:
        raise ValueError("GDPVAL_RECLASSIFICATION_VERIFICATION_PATH_INVALID")
    if not isinstance(verify_sha, str) or len(verify_sha) != 40:
        raise ValueError("GDPVAL_RECLASSIFICATION_VERIFICATION_SHA_INVALID")
    verify_path = root / verify_rel
    if _git_blob(verify_path) != verify_sha:
        raise ValueError("GDPVAL_RECLASSIFICATION_VERIFICATION_BLOB_DRIFT")
    verify = _load(verify_path)
    if (
        verify.get("schema") != GDPVAL_VERIFY_SCHEMA
        or not str(verify.get("status") or "").startswith("PASS__")
        or "NOT_NECESSARY" not in str(verify.get("conclusion") or "")
    ):
        raise ValueError("GDPVAL_RECLASSIFICATION_VERIFICATION_INVALID")

    part = cut.get("current_partition")
    if not isinstance(part, Mapping):
        raise ValueError("CURRENT_PARTITION_INVALID")

    def idset(key: str) -> set[str]:
        values = part.get(key)
        if not isinstance(values, list) or any(not isinstance(x, str) or not x for x in values):
            raise ValueError("CURRENT_PARTITION_SET_INVALID:" + key)
        if len(values) != len(set(values)):
            raise ValueError("CURRENT_PARTITION_SET_DUPLICATE:" + key)
        return set(values)

    o = idset("active_o_obligation_ids")
    q = idset("active_q_obligation_ids")
    parked = idset("parked_obligation_ids")

    if o & q or o & parked or q & parked:
        raise ValueError("CURRENT_PARTITION_OVERLAP")
    if o | q | parked != all_ids:
        raise ValueError("CURRENT_PARTITION_NOT_EXHAUSTIVE")
    if part.get("total_escape_rows") != 13:
        raise ValueError("CURRENT_TOTAL_COUNT_MISMATCH")
    if part.get("active_rows") != 12:
        raise ValueError("CURRENT_ACTIVE_COUNT_MISMATCH")
    if part.get("active_o_rows") != 11 or len(o) != 11:
        raise ValueError("CURRENT_O_COUNT_MISMATCH")
    if part.get("active_q_rows") != 1 or len(q) != 1:
        raise ValueError("CURRENT_Q_COUNT_MISMATCH")
    if part.get("parked_rows") != 1 or len(parked) != 1:
        raise ValueError("CURRENT_PARKED_COUNT_MISMATCH")
    if part.get("active_gap_b_rows") != 0:
        raise ValueError("CURRENT_GAP_B_COUNT_MISMATCH")
    if q != {AA_BRIEFCASE}:
        raise ValueError("CURRENT_Q_IDENTITY_MISMATCH")
    if parked != set(parked_ids) or parked != {TB_SCIENCE}:
        raise ValueError("CURRENT_PARKED_IDENTITY_MISMATCH")
    if GDPVAL not in o:
        raise ValueError("GDPVAL_CURRENT_O_MEMBERSHIP_MISSING")
    return o, q, parked, cut

def evaluate(
    payload: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    base = {
        "schema": SCHEMA,
        "pass": False,
        "objective_law_proof_ready": False,
        "acceptance_authority": False,
        "capability_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "ownership_credit_delta": 0,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    try:
        if not isinstance(payload, Mapping):
            return {**base, "status": "FAIL_CLOSED", "reason": "PAYLOAD_MAPPING_REQUIRED"}
        extra = set(payload) - {"obligation_id", "claim_spec"}
        if extra:
            return {
                **base,
                "status": "FAIL_CLOSED",
                "reason": "UNMODELED_FIELDS:" + ",".join(sorted(extra)),
            }
        oid = payload.get("obligation_id")
        claim = payload.get("claim_spec")
        if not isinstance(oid, str) or not oid:
            return {**base, "status": "FAIL_CLOSED", "reason": "OBLIGATION_ID_REQUIRED"}
        if not isinstance(claim, Mapping):
            return {**base, "status": "FAIL_CLOSED", "reason": "CLAIM_SPEC_REQUIRED"}

        root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
        o, q, parked, cut = _current_projection(root)
        if oid in parked:
            return {
                **base,
                "status": "NOT_APPLICABLE__CURRENT_PARKED_ROW",
                "reason": "CURRENT_ROW_PARKED_BY_CANONICAL_PROJECTION",
                "obligation_id": oid,
            }
        if oid in q:
            return {
                **base,
                "status": "NOT_APPLICABLE__CURRENT_Q_ROW",
                "reason": "CURRENT_QUALITATIVE_ROW_REQUIRES_Q_LAW",
                "obligation_id": oid,
            }
        if oid not in o:
            return {
                **base,
                "status": "FAIL_CLOSED",
                "reason": "OBLIGATION_NOT_CURRENT_ACTIVE_O",
                "obligation_id": oid,
            }

        policy = claim.get("policy")
        if not isinstance(policy, Mapping):
            return {**base, "status": "FAIL_CLOSED", "reason": "CLAIM_POLICY_REQUIRED"}
        if policy.get("predicate_id") != oid:
            return {
                **base,
                "status": "FAIL_CLOSED",
                "reason": "CLAIM_PREDICATE_ID_MISMATCH",
                "obligation_id": oid,
            }

        verdict = evaluate_claim(claim)
        state = verdict.get("status")
        proof_type = None
        evidence = claim.get("evidence")
        if isinstance(evidence, Mapping):
            cert = evidence.get("v3_certificate")
            if isinstance(cert, Mapping):
                inner = cert.get("certificate")
                if isinstance(inner, Mapping):
                    proof_type = inner.get("type")

        detail = {
            "obligation_id": oid,
            "proof_mode": proof_type,
            "kernel_verdict": verdict,
            "current_o_count": len(o),
            "current_q_count": len(q),
            "current_parked_count": len(parked),
            "current_cut_status": cut.get("status"),
        }
        if state == "PROVEN":
            return {
                **base,
                **detail,
                "pass": True,
                "status": "PASS__CURRENT_O_OBJECTIVE_ACCEPTANCE_LAW_PROOF_READY",
                "objective_law_proof_ready": True,
                "rule": (
                    "CURRENT_PROJECTION_MEMBERSHIP_PLUS_EXISTING_V4_KERNEL_PROVEN__"
                    "SEPARATE_CANONICAL_ROW_PROOF_AND_PROMOTION_REQUIRED"
                ),
            }

        status = {
            "DISPROVEN": "DISPROVEN__CURRENT_O_OBJECTIVE_ACCEPTANCE",
            "STALE": "STALE__CURRENT_O_OBJECTIVE_ACCEPTANCE",
        }.get(state, "OPEN__CURRENT_O_OBJECTIVE_ACCEPTANCE")
        return {**base, **detail, "status": status, "reason": verdict.get("reason")}
    except Exception as exc:
        return {
            **base,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    return evaluate(args or {}, repo_root=root)
