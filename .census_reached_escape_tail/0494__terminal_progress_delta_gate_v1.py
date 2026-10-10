from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

INPUT_SCHEMA = "PROJECT_BRAIN_TERMINAL_PROGRESS_DELTA_INPUT_V1"
OUTPUT_SCHEMA = "PROJECT_BRAIN_TERMINAL_PROGRESS_DELTA_OUTPUT_V1"
STATE_SCHEMA = "PROJECT_BRAIN_TERMINAL_PROGRESS_STATE_V1"

class ProgressGateError(ValueError):
    pass

@dataclass(frozen=True)
class GateResult:
    status: str
    admitted: bool
    counts_as_progress: bool
    recompute_required: bool
    before_potential: tuple[int, int, int, int, int]
    after_potential: tuple[int, int, int, int, int]
    closed_truth_obligations: tuple[str, ...]
    introduced_truth_obligations: tuple[str, ...]
    reason: str
    acceptance_credit_delta: int = 0
    family_credit_delta: int = 0
    capability_credit_delta: int = 0
    ownership_credit_delta: int = 0

def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")

def sha256_json(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()

def _sha1(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(c in "0123456789abcdef" for c in value)

def _sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)

def _binding(row: Any) -> bool:
    return (
        isinstance(row, Mapping)
        and isinstance(row.get("path"), str)
        and bool(row["path"].strip())
        and _sha1(row.get("git_blob_sha"))
    )

def _ids(value: Any, name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ProgressGateError(name + "_NOT_LIST")
    if not allow_empty and not value:
        raise ProgressGateError(name + "_EMPTY")
    if any(not isinstance(x, str) or not x.strip() for x in value):
        raise ProgressGateError(name + "_INVALID_ITEM")
    out = tuple(x.strip() for x in value)
    if len(set(out)) != len(out):
        raise ProgressGateError(name + "_DUPLICATE")
    return out

def _state(doc: Any) -> dict[str, Any]:
    if not isinstance(doc, Mapping) or doc.get("schema") != STATE_SCHEMA:
        raise ProgressGateError("STATE_SCHEMA_INVALID")
    truth = _ids(doc.get("open_truth_obligations"), "OPEN_TRUTH")
    interfaces = _ids(doc.get("active_causal_interfaces"), "ACTIVE_INTERFACES")
    prereqs = _ids(doc.get("open_prerequisites"), "OPEN_PREREQUISITES")
    depth = doc.get("max_open_causal_depth")
    nodes = doc.get("open_proof_node_count")
    if not isinstance(depth, int) or isinstance(depth, bool) or depth < 0:
        raise ProgressGateError("MAX_OPEN_CAUSAL_DEPTH_INVALID")
    if not isinstance(nodes, int) or isinstance(nodes, bool) or nodes < 0:
        raise ProgressGateError("OPEN_PROOF_NODE_COUNT_INVALID")
    normalized = {
        "schema": STATE_SCHEMA,
        "open_truth_obligations": list(truth),
        "active_causal_interfaces": list(interfaces),
        "open_prerequisites": list(prereqs),
        "max_open_causal_depth": depth,
        "open_proof_node_count": nodes,
    }
    declared = doc.get("state_sha256")
    computed = sha256_json(normalized)
    if declared is not None and (not _sha256(declared) or declared != computed):
        raise ProgressGateError("STATE_SHA256_MISMATCH")
    normalized["state_sha256"] = computed
    return normalized

def potential(state: Mapping[str, Any]) -> tuple[int, int, int, int, int]:
    s = _state(state)
    return (
        len(s["open_truth_obligations"]),
        len(s["active_causal_interfaces"]),
        s["max_open_causal_depth"],
        len(s["open_prerequisites"]),
        s["open_proof_node_count"],
    )

def _target_digest(targets: Sequence[str]) -> str:
    return sha256_json(sorted(targets))

def _dominant_effect(before_p: tuple[int, int, int, int, int], after_p: tuple[int, int, int, int, int]) -> str:
    labels = (
        "TRUTH_CLOSURE",
        "INTERFACE_CONTRACTION",
        "DEPTH_CONTRACTION",
        "PREREQUISITE_CONTRACTION",
        "PROOF_NODE_CONTRACTION",
    )
    for index, (before_value, after_value) in enumerate(zip(before_p, after_p)):
        if after_value < before_value:
            return labels[index]
        if after_value > before_value:
            raise ProgressGateError("POTENTIAL_NOT_LEXICOGRAPHICALLY_CONTRACTING")
    raise ProgressGateError("POTENTIAL_UNCHANGED")

def _receipts(
    value: Any,
    name: str,
    *,
    required: bool,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    targets: Sequence[str],
    effect_kind: str,
) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, list):
        raise ProgressGateError(name + "_NOT_LIST")
    if required and not value:
        raise ProgressGateError(name + "_EMPTY")
    if not all(_binding(x) for x in value):
        raise ProgressGateError(name + "_INVALID_BINDING")
    paths = [x["path"] for x in value]
    if len(paths) != len(set(paths)):
        raise ProgressGateError(name + "_DUPLICATE_PATH")
    target_sha = _target_digest(targets)
    for row in value:
        if row.get("before_state_sha256") != before["state_sha256"]:
            raise ProgressGateError(name + "_BEFORE_STATE_BINDING_MISMATCH")
        if row.get("after_state_sha256") != after["state_sha256"]:
            raise ProgressGateError(name + "_AFTER_STATE_BINDING_MISMATCH")
        if row.get("target_truth_obligations_sha256") != target_sha:
            raise ProgressGateError(name + "_TARGET_BINDING_MISMATCH")
        if row.get("effect_kind") != effect_kind:
            raise ProgressGateError(name + "_EFFECT_KIND_MISMATCH")
    return tuple(value)

def evaluate(doc: Mapping[str, Any]) -> GateResult:
    if not isinstance(doc, Mapping) or doc.get("schema") != INPUT_SCHEMA:
        raise ProgressGateError("INPUT_SCHEMA_INVALID")
    kind = doc.get("kind")
    if kind not in {"PROGRESS", "TRUTH_REPAIR"}:
        raise ProgressGateError("KIND_INVALID")

    before = _state(doc.get("before"))
    after = _state(doc.get("after"))
    targets = set(_ids(doc.get("target_truth_obligations"), "TARGET_TRUTH", allow_empty=False))
    before_truth = set(before["open_truth_obligations"])
    after_truth = set(after["open_truth_obligations"])
    if not targets.issubset(before_truth):
        raise ProgressGateError("TARGET_OUTSIDE_BEFORE_OPEN_TRUTH")

    before_p = potential(before)
    after_p = potential(after)
    closed = tuple(sorted(before_truth - after_truth))
    introduced = tuple(sorted(after_truth - before_truth))

    if kind == "TRUTH_REPAIR":
        _receipts(
            doc.get("countermodel_receipts"),
            "COUNTERMODEL_RECEIPTS",
            required=True,
            before=before,
            after=after,
            targets=tuple(sorted(targets)),
            effect_kind="TRUTH_REPAIR",
        )
        return GateResult(
            status="ADMIT_TRUTH_REPAIR_NOT_PROGRESS",
            admitted=True,
            counts_as_progress=False,
            recompute_required=True,
            before_potential=before_p,
            after_potential=after_p,
            closed_truth_obligations=closed,
            introduced_truth_obligations=introduced,
            reason="CONSTRUCTIVE_COUNTERMODEL_ADMITTED_FOR_CORRECTNESS__ZERO_PROGRESS_CREDIT__GLOBAL_RECOMPUTE_REQUIRED",
        )

    if introduced:
        return GateResult(
            status="REJECT_NONCONTRACTING_PROGRESS",
            admitted=False,
            counts_as_progress=False,
            recompute_required=False,
            before_potential=before_p,
            after_potential=after_p,
            closed_truth_obligations=closed,
            introduced_truth_obligations=introduced,
            reason="PROGRESS_ACTION_INTRODUCES_NEW_OPEN_TRUTH_OBLIGATIONS",
        )
    if not after_truth.issubset(before_truth):
        raise ProgressGateError("AFTER_TRUTH_NOT_SUBSET")
    if not (after_p < before_p):
        return GateResult(
            status="REJECT_NONCONTRACTING_PROGRESS",
            admitted=False,
            counts_as_progress=False,
            recompute_required=False,
            before_potential=before_p,
            after_potential=after_p,
            closed_truth_obligations=closed,
            introduced_truth_obligations=introduced,
            reason="LEXICOGRAPHIC_TERMINAL_PROGRESS_POTENTIAL_DID_NOT_STRICTLY_DECREASE",
        )
    effect_kind = _dominant_effect(before_p, after_p)
    _receipts(
        doc.get("evidence_receipts"),
        "EVIDENCE_RECEIPTS",
        required=True,
        before=before,
        after=after,
        targets=tuple(sorted(targets)),
        effect_kind=effect_kind,
    )
    return GateResult(
        status="ADMIT_TERMINAL_CONTRACTING_PROGRESS",
        admitted=True,
        counts_as_progress=True,
        recompute_required=True,
        before_potential=before_p,
        after_potential=after_p,
        closed_truth_obligations=closed,
        introduced_truth_obligations=introduced,
        reason="STRICT_TERMINAL_OR_CAUSAL_CONTRACTION_WITH_CONTENT_ADDRESSED_EVIDENCE",
    )

def compile_result(doc: Mapping[str, Any]) -> dict[str, Any]:
    try:
        result = evaluate(doc)
        out = asdict(result)
        out["schema"] = OUTPUT_SCHEMA
        out["before_potential"] = list(result.before_potential)
        out["after_potential"] = list(result.after_potential)
        out["closed_truth_obligations"] = list(result.closed_truth_obligations)
        out["introduced_truth_obligations"] = list(result.introduced_truth_obligations)
        out["execution_authority"] = False
        out["promotion_authority"] = False
        out["fresh_reality_authority"] = False
        return out
    except ProgressGateError as exc:
        return {
            "schema": OUTPUT_SCHEMA,
            "status": "FAIL_CLOSED",
            "admitted": False,
            "counts_as_progress": False,
            "recompute_required": False,
            "errors": [str(exc)],
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }
