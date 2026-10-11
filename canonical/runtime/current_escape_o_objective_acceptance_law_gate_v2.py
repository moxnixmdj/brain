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


def _git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _load(path: Path) -> Mapping[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping):
        raise ValueError("JSON_OBJECT_REQUIRED:" + str(path))
    return doc


def _current_projection(root: Path) -> tuple[set[str], set[str], set[str], Mapping[str, Any]]:
    cut = _load(root / CUT_PATH)
    if cut.get("schema") != CUT_SCHEMA:
        raise ValueError("CURRENT_CUT_SCHEMA_INVALID")

    bindings = cut.get("source_bindings")
    manifest_ref = bindings.get("manifest") if isinstance(bindings, Mapping) else None
    if (
        not isinstance(manifest_ref, list)
        or len(manifest_ref) != 2
        or not isinstance(manifest_ref[0], str)
        or not isinstance(manifest_ref[1], str)
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
    if not isinstance(rows, list):
        raise ValueError("CURRENT_MANIFEST_ROWS_INVALID")
    all_ids: set[str] = set()
    for row in rows:
        oid = row.get("obligation_id") if isinstance(row, Mapping) else None
        if not isinstance(oid, str) or not oid or oid in all_ids:
            raise ValueError("CURRENT_MANIFEST_ROW_ID_INVALID_OR_DUPLICATE")
        all_ids.add(oid)

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
    if part.get("total_escape_rows") != len(all_ids):
        raise ValueError("CURRENT_TOTAL_COUNT_MISMATCH")
    if part.get("active_o_rows") != len(o):
        raise ValueError("CURRENT_O_COUNT_MISMATCH")
    if part.get("active_q_rows") != len(q):
        raise ValueError("CURRENT_Q_COUNT_MISMATCH")
    if part.get("parked_rows") != len(parked):
        raise ValueError("CURRENT_PARKED_COUNT_MISMATCH")
    if part.get("active_rows") != len(o) + len(q):
        raise ValueError("CURRENT_ACTIVE_COUNT_MISMATCH")
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
