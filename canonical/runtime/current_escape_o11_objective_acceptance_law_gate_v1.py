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


def _git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _load(path: Path) -> Mapping[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping):
        raise ValueError("JSON_OBJECT_REQUIRED:" + str(path))
    return doc


def _frontier(root: Path) -> tuple[set[str], set[str], Mapping[str, Any]]:
    oq_path = root / "canonical/governance/CURRENT_ESCAPE_OQ_FRONTIER_REDUCTION_20261010_V1.json"
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
    q = set(q_rows)
    if not q.issubset(all_ids):
        raise ValueError("Q_ROWS_OUTSIDE_CURRENT_ESCAPE_SCOPE")
    o = all_ids - q
    if (
        reduction.get("O_OBJECTIVE_ACCEPTANCE") != 11
        or reduction.get("Q_QUALITATIVE_RELATIVE_ORDER") != 2
        or len(o) != 11
        or len(q) != 2
    ):
        raise ValueError("OQ_CURRENT_COUNT_INVARIANT_FAILED")
    return o, q, oq


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
        o_rows, q_rows, oq = _frontier(root)
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
                "oq_status": oq.get("status"),
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
