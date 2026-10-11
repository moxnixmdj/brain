"""Current O11 objective-acceptance law gate.

This is a thin membership/currentness adapter over the existing proof-carrying
benchmark claim kernel V4. It does not define benchmark semantics, invent
thresholds, or grant acceptance. It only proves that one current O-row claim
satisfies the already verified generic objective-acceptance proof law.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.benchmark_witness_elimination_compiler_v4 import (
    evaluate_claim,
)

SCHEMA = "PROJECT_BRAIN_CURRENT_ESCAPE_O11_OBJECTIVE_ACCEPTANCE_LAW_GATE_V1"
OQ_SCHEMA = "PROJECT_BRAIN_CURRENT_ESCAPE_OQ_FRONTIER_REDUCTION_20261010_V1"
MANIFEST_SCHEMA = "PROJECT_BRAIN_ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_V2"
CURRENT_RESIDUAL_SCHEMA = "PROJECT_BRAIN_CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1"
ENGINE_CUT_SCHEMA = "PROJECT_BRAIN_CURRENT_ESCAPE_TWO_ENGINE_MINIMUM_DELTA_CUT_20261011_V1"
GDPVAL_RECLASS_SCHEMA = "PROJECT_BRAIN_GDPVAL_CURRENT_FIXED_BAR_ENGINE_RECLASSIFICATION_20261011_V1"
GDPVAL_VERIFY_SCHEMA = "PROJECT_BRAIN_GDPVAL_FIXED_BAR_OWNER_PAIRWISE_NONNECESSITY_VERIFICATION_20261009_V1"

OQ_PATH = "canonical/governance/CURRENT_ESCAPE_OQ_FRONTIER_REDUCTION_20261010_V1.json"
CURRENT_RESIDUAL_PATH = "canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json"
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


def _frontier(root: Path) -> tuple[set[str], set[str], Mapping[str, Any]]:
    """Resolve active O/Q membership through the current two-engine projection.

    The historical O/Q reduction remains the base acceptance-law classification.
    Current routing then applies the mutable residual pointer's exact two-engine cut,
    which may park rows or admit independently verified reclassifications. This
    prevents stale O11/Q2 snapshots from routing current work.
    """
    oq_path = root / OQ_PATH
    oq = _load(oq_path)
    if oq.get("schema") != OQ_SCHEMA:
        raise ValueError("OQ_SCHEMA_INVALID")
    source = oq.get("source_manifest")
    if not isinstance(source, Mapping):
        raise ValueError("OQ_SOURCE_MANIFEST_BINDING_MISSING")
    rel = source.get("path")
    expected_sha = source.get("git_blob_sha")
    if not isinstance(rel, str) or not rel:
        raise ValueError("OQ_SOURCE_MANIFEST_PATH_INVALID")
    if not isinstance(expected_sha, str) or len(expected_sha) != 40:
        raise ValueError("OQ_SOURCE_MANIFEST_SHA_INVALID")
    manifest_path = root / rel
    if _git_blob(manifest_path) != expected_sha:
        raise ValueError("OQ_SOURCE_MANIFEST_BLOB_DRIFT")
    manifest = _load(manifest_path)
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("OQ_SOURCE_MANIFEST_SCHEMA_INVALID")
    rows = manifest.get("rows")
    if not isinstance(rows, list) or len(rows) != 13:
        raise ValueError("CURRENT_ESCAPE_ROW_SET_INVALID")

    all_ids: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("CURRENT_ESCAPE_ROW_INVALID")
        oid = row.get("obligation_id")
        if not isinstance(oid, str) or not oid or oid in all_ids:
            raise ValueError("CURRENT_ESCAPE_OBLIGATION_ID_INVALID_OR_DUPLICATE")
        all_ids.add(oid)

    reduction = oq.get("reduction")
    if not isinstance(reduction, Mapping):
        raise ValueError("OQ_REDUCTION_INVALID")
    q_rows = reduction.get("Q_rows")
    if not isinstance(q_rows, list) or any(not isinstance(x, str) or not x for x in q_rows):
        raise ValueError("Q_ROWS_INVALID")
    base_q = set(q_rows)
    base_o = all_ids - base_q
    if (
        reduction.get("O_OBJECTIVE_ACCEPTANCE") != 11
        or reduction.get("Q_QUALITATIVE_RELATIVE_ORDER") != 2
        or len(base_o) != 11
        or base_q != {GDPVAL, AA_BRIEFCASE}
    ):
        raise ValueError("OQ_BASE_CLASSIFICATION_INVARIANT_FAILED")

    current_path = root / CURRENT_RESIDUAL_PATH
    current = _load(current_path)
    if current.get("schema") != CURRENT_RESIDUAL_SCHEMA:
        raise ValueError("CURRENT_RESIDUAL_SCHEMA_INVALID")

    topology = current.get("escape_current_topology")
    if not isinstance(topology, Mapping):
        raise ValueError("CURRENT_ESCAPE_TOPOLOGY_MISSING")
    parked_rows = topology.get("parked_obligation_ids")
    if (
        topology.get("frozen_obligation_count") != 13
        or topology.get("active_gap_a_acquisition_rows") != 12
        or topology.get("active_gap_b_strict_progress_rows") != 0
        or topology.get("parked_unresolved_rows") != 1
        or not isinstance(parked_rows, list)
        or any(not isinstance(x, str) or not x for x in parked_rows)
    ):
        raise ValueError("CURRENT_ESCAPE_TOPOLOGY_INVARIANT_FAILED")
    parked = set(parked_rows)
    if parked != {TB_SCIENCE}:
        raise ValueError("CURRENT_PARKED_SET_UNEXPECTED")

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
    if _git_blob(cut_path) != cut_sha:
        raise ValueError("CURRENT_TWO_ENGINE_CUT_BLOB_DRIFT")
    cut = _load(cut_path)
    if cut.get("schema") != ENGINE_CUT_SCHEMA:
        raise ValueError("CURRENT_TWO_ENGINE_CUT_SCHEMA_INVALID")
    if cut.get("status") != cut_ref.get("status"):
        raise ValueError("CURRENT_TWO_ENGINE_CUT_STATUS_MISMATCH")

    bindings = cut.get("source_bindings")
    if not isinstance(bindings, Mapping):
        raise ValueError("CURRENT_TWO_ENGINE_SOURCE_BINDINGS_MISSING")

    def _pair(name: str) -> tuple[str, str]:
        value = bindings.get(name)
        if (
            not isinstance(value, list)
            or len(value) != 2
            or not isinstance(value[0], str)
            or not value[0]
            or not isinstance(value[1], str)
            or len(value[1]) != 40
        ):
            raise ValueError("CURRENT_TWO_ENGINE_BINDING_INVALID:" + name)
        return value[0], value[1]

    manifest_rel, manifest_sha = _pair("manifest")
    if manifest_rel != rel or manifest_sha != expected_sha:
        raise ValueError("CURRENT_TWO_ENGINE_MANIFEST_BINDING_MISMATCH")
    oq_rel, oq_sha = _pair("oq")
    if oq_rel != OQ_PATH or _git_blob(oq_path) != oq_sha:
        raise ValueError("CURRENT_TWO_ENGINE_OQ_BINDING_MISMATCH")

    reclass_rel, reclass_sha = _pair("gdpval_fixed_bar_reclassification")
    reclass_path = root / reclass_rel
    if _git_blob(reclass_path) != reclass_sha:
        raise ValueError("GDPVAL_RECLASSIFICATION_BLOB_DRIFT")
    reclass = _load(reclass_path)
    if reclass.get("schema") != GDPVAL_RECLASS_SCHEMA:
        raise ValueError("GDPVAL_RECLASSIFICATION_SCHEMA_INVALID")
    if reclass.get("target_obligation") != GDPVAL:
        raise ValueError("GDPVAL_RECLASSIFICATION_TARGET_MISMATCH")
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

    verify_ref = (
        reclass.get("source_bindings", {}).get("fixed_bar_nonnecessity_verification")
        if isinstance(reclass.get("source_bindings"), Mapping)
        else None
    )
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

    partition = cut.get("current_partition")
    if not isinstance(partition, Mapping):
        raise ValueError("CURRENT_TWO_ENGINE_PARTITION_MISSING")
    o_rows = partition.get("active_o_obligation_ids")
    q_rows = partition.get("active_q_obligation_ids")
    cut_parked_rows = partition.get("parked_obligation_ids")
    for name, value in (
        ("ACTIVE_O_ROWS", o_rows),
        ("ACTIVE_Q_ROWS", q_rows),
        ("PARKED_ROWS", cut_parked_rows),
    ):
        if (
            not isinstance(value, list)
            or any(not isinstance(x, str) or not x for x in value)
            or len(value) != len(set(value))
        ):
            raise ValueError(name + "_INVALID")

    o = set(o_rows)
    q = set(q_rows)
    cut_parked = set(cut_parked_rows)
    if (
        partition.get("total_escape_rows") != 13
        or partition.get("active_rows") != 12
        or partition.get("parked_rows") != 1
        or partition.get("active_gap_b_rows") != 0
        or partition.get("active_o_rows") != 11
        or partition.get("active_q_rows") != 1
        or len(o) != 11
        or q != {AA_BRIEFCASE}
        or cut_parked != parked
        or (o & q)
        or (o & parked)
        or (q & parked)
        or (o | q | parked) != all_ids
    ):
        raise ValueError("CURRENT_TWO_ENGINE_PARTITION_INVARIANT_FAILED")

    expected_o = (base_o | {GDPVAL}) - parked
    expected_q = base_q - {GDPVAL}
    if o != expected_o or q != expected_q:
        raise ValueError("CURRENT_TWO_ENGINE_RECLASSIFICATION_DELTA_INVALID")

    return o, q, {
        "status": cut.get("status"),
        "historical_oq_status": oq.get("status"),
        "parked_obligation_ids": sorted(parked),
        "current_cut_path": cut_rel,
        "current_cut_git_blob_sha": cut_sha,
    }

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
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    try:
        if not isinstance(payload, Mapping):
            return {**base, "status": "FAIL_CLOSED", "reason": "PAYLOAD_MAPPING_REQUIRED"}
        allowed = {"obligation_id", "claim_spec"}
        extra = set(payload) - allowed
        if extra:
            return {
                **base,
                "status": "FAIL_CLOSED",
                "reason": "UNMODELED_FIELDS:" + ",".join(sorted(extra)),
            }
        obligation_id = payload.get("obligation_id")
        claim_spec = payload.get("claim_spec")
        if not isinstance(obligation_id, str) or not obligation_id:
            return {**base, "status": "FAIL_CLOSED", "reason": "OBLIGATION_ID_REQUIRED"}
        if not isinstance(claim_spec, Mapping):
            return {**base, "status": "FAIL_CLOSED", "reason": "CLAIM_SPEC_REQUIRED"}

        root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
        o_rows, q_rows, frontier = _frontier(root)
        parked_rows = set(frontier.get("parked_obligation_ids") or [])
        if obligation_id in parked_rows:
            return {
                **base,
                "status": "NOT_APPLICABLE__CURRENT_PARKED_ROW",
                "reason": "CURRENT_FRONTIER_EXPLICITLY_PARKED",
                "obligation_id": obligation_id,
            }
        if obligation_id in q_rows:
            return {
                **base,
                "status": "NOT_APPLICABLE__CURRENT_Q_ROW",
                "reason": "QUALITATIVE_RELATIVE_ORDER_REQUIRES_Q_LAW",
                "obligation_id": obligation_id,
            }
        if obligation_id not in o_rows:
            return {
                **base,
                "status": "FAIL_CLOSED",
                "reason": "OBLIGATION_NOT_CURRENT_O11",
                "obligation_id": obligation_id,
            }

        policy = claim_spec.get("policy")
        if not isinstance(policy, Mapping):
            return {**base, "status": "FAIL_CLOSED", "reason": "CLAIM_POLICY_REQUIRED"}
        if policy.get("predicate_id") != obligation_id:
            return {
                **base,
                "status": "FAIL_CLOSED",
                "reason": "CLAIM_PREDICATE_ID_MISMATCH",
                "obligation_id": obligation_id,
            }

        verdict = evaluate_claim(claim_spec)
        state = verdict.get("status")
        proof_type = None
        evidence = claim_spec.get("evidence")
        if isinstance(evidence, Mapping):
            cert = evidence.get("v3_certificate")
            if isinstance(cert, Mapping):
                inner = cert.get("certificate")
                if isinstance(inner, Mapping):
                    proof_type = inner.get("type")

        if state == "PROVEN":
            return {
                **base,
                "pass": True,
                "status": "PASS__CURRENT_O_OBJECTIVE_ACCEPTANCE_LAW_PROOF_READY",
                "objective_law_proof_ready": True,
                "obligation_id": obligation_id,
                "proof_mode": proof_type,
                "kernel_verdict": verdict,
                "current_o_count": len(o_rows),
                "current_q_count": len(q_rows),
                "oq_status": frontier.get("historical_oq_status"),
                "current_partition_status": frontier.get("status"),
                "rule": (
                    "CURRENT_O_MEMBERSHIP_PLUS_EXISTING_V4_KERNEL_PROVEN__"
                    "CURRENT_IDENTITY_SCOPE_PROVENANCE_EVALUATOR_FAILURE_ACCOUNTING_AND_"
                    "PROOF_RELATION_ALL_PASS__SEPARATE_GOVERNANCE_PROMOTION_REQUIRED"
                ),
            }

        return {
            **base,
            "status": (
                "DISPROVEN__CURRENT_O_OBJECTIVE_ACCEPTANCE"
                if state == "DISPROVEN"
                else (
                    "STALE__CURRENT_O_OBJECTIVE_ACCEPTANCE"
                    if state == "STALE"
                    else "OPEN__CURRENT_O_OBJECTIVE_ACCEPTANCE"
                )
            ),
            "reason": verdict.get("reason"),
            "obligation_id": obligation_id,
            "proof_mode": proof_type,
            "kernel_verdict": verdict,
            "current_o_count": len(o_rows),
            "current_q_count": len(q_rows),
            "oq_status": frontier.get("historical_oq_status"),
            "current_partition_status": frontier.get("status"),
        }
    except Exception as exc:
        return {
            **base,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    return evaluate(args or {}, repo_root=root)
