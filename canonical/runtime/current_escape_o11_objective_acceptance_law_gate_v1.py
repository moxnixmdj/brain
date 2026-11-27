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
CUT_SCHEMA = "PROJECT_BRAIN_CURRENT_ESCAPE_TWO_ENGINE_MINIMUM_DELTA_CUT_20261011_V1"
MANIFEST_SCHEMA = "PROJECT_BRAIN_ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_V2"


def _git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _load(path: Path) -> Mapping[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping):
        raise ValueError("JSON_OBJECT_REQUIRED:" + str(path))
    return doc


def _frontier(root: Path) -> tuple[set[str], set[str], set[str], Mapping[str, Any]]:
    cut_path = root / "canonical/governance/CURRENT_ESCAPE_TWO_ENGINE_MINIMUM_DELTA_CUT_20261011_V1.json"
    cut = _load(cut_path)
    if cut.get("schema") != CUT_SCHEMA:
        raise ValueError("CURRENT_TWO_ENGINE_CUT_SCHEMA_INVALID")

    source_bindings = cut.get("source_bindings")
    if not isinstance(source_bindings, Mapping):
        raise ValueError("CURRENT_TWO_ENGINE_SOURCE_BINDINGS_INVALID")
    manifest_ref = source_bindings.get("manifest")
    if (
        not isinstance(manifest_ref, list)
        or len(manifest_ref) != 2
        or not isinstance(manifest_ref[0], str)
        or not isinstance(manifest_ref[1], str)
    ):
        raise ValueError("CURRENT_TWO_ENGINE_MANIFEST_BINDING_INVALID")
    manifest_path = root / manifest_ref[0]
    if _git_blob(manifest_path) != manifest_ref[1]:
        raise ValueError("CURRENT_TWO_ENGINE_MANIFEST_BLOB_DRIFT")
    manifest = _load(manifest_path)
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("CURRENT_TWO_ENGINE_MANIFEST_SCHEMA_INVALID")
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

    partition = cut.get("current_partition")
    if not isinstance(partition, Mapping):
        raise ValueError("CURRENT_TWO_ENGINE_PARTITION_INVALID")
    o_rows = partition.get("active_o_obligation_ids")
    q_rows = partition.get("active_q_obligation_ids")
    parked_rows = partition.get("parked_obligation_ids")
    if not all(
        isinstance(x, list) and all(isinstance(v, str) and v for v in x)
        for x in (o_rows, q_rows, parked_rows)
    ):
        raise ValueError("CURRENT_TWO_ENGINE_PARTITION_LISTS_INVALID")
    o, q, parked = set(o_rows), set(q_rows), set(parked_rows)
    if o & q or o & parked or q & parked:
        raise ValueError("CURRENT_TWO_ENGINE_PARTITION_OVERLAP")
    if o | q | parked != all_ids:
        raise ValueError("CURRENT_TWO_ENGINE_PARTITION_NOT_SCOPE_COMPLETE")
    if (
        partition.get("total_escape_rows") != 13
        or partition.get("active_rows") != 12
        or partition.get("parked_rows") != 1
        or partition.get("active_o_rows") != 11
        or partition.get("active_q_rows") != 1
        or len(o) != 11
        or len(q) != 1
        or len(parked) != 1
    ):
        raise ValueError("CURRENT_TWO_ENGINE_COUNT_INVARIANT_FAILED")
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
        o_rows, q_rows, parked_rows, cut = _frontier(root)
        if obligation_id in q_rows:
            return {
                **base,
                "status": "NOT_APPLICABLE__CURRENT_Q_ROW",
                "reason": "QUALITATIVE_RELATIVE_ORDER_REQUIRES_Q_LAW",
                "obligation_id": obligation_id,
            }
        if obligation_id in parked_rows:
            return {
                **base,
                "status": "NOT_APPLICABLE__CURRENT_PARKED_ROW",
                "reason": "PARKED_ROW_REQUIRES_EXPLICIT_WAKE_AUTHORITY",
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
                "partition_status": cut.get("status"),
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
        }
    except Exception as exc:
        return {
            **base,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    return evaluate(args or {}, repo_root=root)
