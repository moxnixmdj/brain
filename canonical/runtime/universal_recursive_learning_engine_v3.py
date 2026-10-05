"""Universal Recursive Learning Engine V3.

V3 adds only structural guarantees that can be proved without claiming semantic
success in arbitrary new domains:
- cross-domain transfer requires verified structural, never label-only, mappings;
- irrelevant/distractor mappings cannot reduce the target novelty set;
- the smallest safe finite probe set that distinguishes every pair of live
  hypotheses requiring different actions is selected exactly;
- if such a discriminator is unavailable, the engine abstains rather than
  inventing identifiability;
- skills may be compressed only across an exact shared structural signature and
  independently verified, exact-byte-bound proof receipts.

No function here grants acceptance, family, capability, ownership, execution,
or promotion authority.
"""
from __future__ import annotations

from math import isfinite
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_RECURSIVE_LEARNING_ENGINE_V3"
STRUCTURAL_BASES = {
    "CAUSAL_INVARIANT",
    "ALGEBRAIC_INVARIANT",
    "STATE_TRANSITION_INVARIANT",
    "PROTOCOL_INVARIANT",
    "CONSTRAINT_INVARIANT",
}
MAX_ACTION_RELEVANT_PAIRS = 24
MAX_SAFE_PROBES = 64


class RecursiveLearningEngineError(ValueError):
    pass


def _norm_set(values: Iterable[Any]) -> set[str]:
    out: set[str] = set()
    for value in values:
        item = str(value).strip()
        if item:
            out.add(item)
    return out


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise RecursiveLearningEngineError(f"{field.upper()}_INVALID")
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise RecursiveLearningEngineError(f"{field.upper()}_INVALID") from exc
    if not isfinite(x) or x < 0:
        raise RecursiveLearningEngineError(f"{field.upper()}_INVALID")
    return x


def _verify_receipt(receipt: Any) -> str:
    if not isinstance(receipt, Mapping):
        raise RecursiveLearningEngineError("VERIFICATION_RECEIPT_INVALID")
    rid = str(receipt.get("receipt_id") or "").strip()
    if not rid:
        raise RecursiveLearningEngineError("VERIFICATION_RECEIPT_ID_REQUIRED")
    if receipt.get("independent_verified") is not True:
        raise RecursiveLearningEngineError("VERIFICATION_RECEIPT_NOT_INDEPENDENT")
    if receipt.get("exact_byte_bound") is not True:
        raise RecursiveLearningEngineError("VERIFICATION_RECEIPT_NOT_EXACT_BYTE_BOUND")
    if receipt.get("conclusion") != "success":
        raise RecursiveLearningEngineError("VERIFICATION_RECEIPT_NOT_SUCCESS")
    return rid


def structural_transfer_plan(
    *,
    target_requirements: Iterable[Any],
    mappings: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    targets = _norm_set(target_requirements)
    covered: set[str] = set()
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []

    for raw in mappings:
        if not isinstance(raw, Mapping):
            raise RecursiveLearningEngineError("TRANSFER_MAPPING_INVALID")
        source = str(raw.get("source_primitive_id") or "").strip()
        target = str(raw.get("target_requirement_id") or "").strip()
        basis = str(raw.get("mapping_basis") or "").strip()
        if not source or not target:
            raise RecursiveLearningEngineError("TRANSFER_MAPPING_ENDPOINT_REQUIRED")

        if target not in targets:
            rejected.append({
                "source_primitive_id": source,
                "target_requirement_id": target,
                "reason": "TARGET_REQUIREMENT_OUTSIDE_SCOPE",
            })
            continue
        if raw.get("label_only") is not False or basis not in STRUCTURAL_BASES:
            rejected.append({
                "source_primitive_id": source,
                "target_requirement_id": target,
                "reason": "LABEL_ONLY_OR_NONSTRUCTURAL_MAPPING",
            })
            continue

        source_receipt_id = _verify_receipt(raw.get("source_verification_receipt"))
        mapping_receipt_id = _verify_receipt(raw.get("mapping_verification_receipt"))
        covered.add(target)
        accepted.append({
            "source_primitive_id": source,
            "target_requirement_id": target,
            "mapping_basis": basis,
            "source_verification_receipt_id": source_receipt_id,
            "mapping_verification_receipt_id": mapping_receipt_id,
        })

    return {
        "schema": SCHEMA,
        "status": "STRUCTURAL_TRANSFER_AVAILABLE" if covered else "NO_VERIFIED_STRUCTURAL_TRANSFER",
        "target_requirements": sorted(targets),
        "covered": sorted(covered),
        "missing": sorted(targets - covered),
        "accepted_mappings": sorted(
            accepted,
            key=lambda x: (x["target_requirement_id"], x["source_primitive_id"]),
        ),
        "rejected_mappings": sorted(
            rejected,
            key=lambda x: (x["target_requirement_id"], x["source_primitive_id"], x["reason"]),
        ),
        "label_only_credit_allowed": False,
        "acceptance_credit_delta": 0,
        "ownership_credit_delta": 0,
        "promotion_authorized": False,
    }


def _live_hypotheses(hypotheses: Sequence[Mapping[str, Any]]) -> list[tuple[str, str]]:
    live: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw in hypotheses:
        hid = str(raw.get("id") or "").strip()
        if not hid:
            raise RecursiveLearningEngineError("HYPOTHESIS_ID_REQUIRED")
        if hid in seen:
            raise RecursiveLearningEngineError("HYPOTHESIS_ID_DUPLICATE")
        seen.add(hid)
        if raw.get("plausible") is True:
            action = str(raw.get("best_action") or "").strip()
            if not action:
                raise RecursiveLearningEngineError("LIVE_HYPOTHESIS_ACTION_REQUIRED")
            live.append((hid, action))
    return live


def minimum_action_discriminator(
    *,
    hypotheses: Sequence[Mapping[str, Any]],
    probes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    live = _live_hypotheses(hypotheses)
    if not live:
        return {
            "schema": SCHEMA,
            "identifiable": False,
            "route": "ABSTAIN",
            "reason": "NO_LIVE_HYPOTHESES",
            "probe_ids": [],
            "total_cost": 0.0,
            "promotion_authorized": False,
        }

    action_pairs: list[tuple[str, str]] = []
    for i, (h1, a1) in enumerate(live):
        for h2, a2 in live[i + 1 :]:
            if a1 != a2:
                action_pairs.append((h1, h2))

    if not action_pairs:
        return {
            "schema": SCHEMA,
            "identifiable": True,
            "route": "DECISION_SUFFICIENT",
            "reason": "ALL_LIVE_HYPOTHESES_IMPLY_SAME_ACTION",
            "probe_ids": [],
            "total_cost": 0.0,
            "promotion_authorized": False,
        }
    if len(action_pairs) > MAX_ACTION_RELEVANT_PAIRS:
        raise RecursiveLearningEngineError("DISCRIMINATOR_PAIR_BOUND_EXCEEDED")

    live_ids = {hid for hid, _ in live}
    candidates: list[tuple[str, float, int]] = []
    seen_probe_ids: set[str] = set()
    for raw in probes:
        if not isinstance(raw, Mapping):
            raise RecursiveLearningEngineError("PROBE_INVALID")
        pid = str(raw.get("id") or "").strip()
        if not pid:
            raise RecursiveLearningEngineError("PROBE_ID_REQUIRED")
        if pid in seen_probe_ids:
            raise RecursiveLearningEngineError("PROBE_ID_DUPLICATE")
        seen_probe_ids.add(pid)
        if raw.get("safe") is not True:
            continue
        outcomes = raw.get("outcomes")
        if not isinstance(outcomes, Mapping):
            raise RecursiveLearningEngineError("SAFE_PROBE_OUTCOMES_REQUIRED")
        if not live_ids.issubset({str(k) for k in outcomes.keys()}):
            raise RecursiveLearningEngineError("SAFE_PROBE_LIVE_HYPOTHESIS_OUTCOME_MISSING")
        total_cost = (
            _number(raw.get("time", 0), "time")
            + _number(raw.get("cost", 0), "cost")
            + _number(raw.get("risk", 0), "risk")
        )
        if total_cost <= 0:
            raise RecursiveLearningEngineError("SAFE_PROBE_TOTAL_COST_MUST_BE_POSITIVE")
        mask = 0
        for idx, (h1, h2) in enumerate(action_pairs):
            if outcomes[h1] != outcomes[h2]:
                mask |= 1 << idx
        if mask:
            candidates.append((pid, total_cost, mask))

    if len(candidates) > MAX_SAFE_PROBES:
        raise RecursiveLearningEngineError("DISCRIMINATOR_PROBE_BOUND_EXCEEDED")

    target_mask = (1 << len(action_pairs)) - 1
    dp: dict[int, tuple[float, tuple[str, ...]]] = {0: (0.0, ())}
    for pid, pcost, pmask in sorted(candidates, key=lambda x: x[0]):
        snapshot = list(dp.items())
        for mask, (cost, ids) in snapshot:
            new_mask = mask | pmask
            candidate = (cost + pcost, tuple(sorted(ids + (pid,))))
            current = dp.get(new_mask)
            if current is None or (candidate[0], len(candidate[1]), candidate[1]) < (
                current[0], len(current[1]), current[1]
            ):
                dp[new_mask] = candidate

    solution = dp.get(target_mask)
    if solution is None:
        return {
            "schema": SCHEMA,
            "identifiable": False,
            "route": "ABSTAIN",
            "reason": "NO_SAFE_PROBE_SET_SEPARATES_ALL_ACTION_RELEVANT_HYPOTHESES",
            "probe_ids": [],
            "total_cost": 0.0,
            "action_relevant_pair_count": len(action_pairs),
            "promotion_authorized": False,
        }

    return {
        "schema": SCHEMA,
        "identifiable": True,
        "route": "PROBE",
        "reason": "EXACT_MINIMUM_COST_SAFE_DISCRIMINATOR_FOUND",
        "probe_ids": list(solution[1]),
        "total_cost": solution[0],
        "action_relevant_pair_count": len(action_pairs),
        "promotion_authorized": False,
        "acceptance_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


def merge_structurally_equivalent_skills(skills: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not isinstance(skills, Sequence) or isinstance(skills, (str, bytes)) or len(skills) < 2:
        raise RecursiveLearningEngineError("AT_LEAST_TWO_SKILLS_REQUIRED")
    signatures: set[str] = set()
    applicability: set[str] = set()
    receipt_ids: set[str] = set()
    skill_ids: set[str] = set()

    for skill in skills:
        if not isinstance(skill, Mapping):
            raise RecursiveLearningEngineError("SKILL_INVALID")
        sid = str(skill.get("skill_id") or "").strip()
        signature = str(skill.get("structural_signature") or "").strip()
        if not sid or not signature:
            raise RecursiveLearningEngineError("SKILL_ID_AND_SIGNATURE_REQUIRED")
        if sid in skill_ids:
            raise RecursiveLearningEngineError("SKILL_ID_DUPLICATE")
        skill_ids.add(sid)
        signatures.add(signature)
        applicability.update(_norm_set(skill.get("applicability") or ()))
        receipts = skill.get("verification_receipts")
        if not isinstance(receipts, Sequence) or isinstance(receipts, (str, bytes)) or not receipts:
            raise RecursiveLearningEngineError("SKILL_VERIFICATION_RECEIPT_REQUIRED")
        for receipt in receipts:
            receipt_ids.add(_verify_receipt(receipt))

    if len(signatures) != 1:
        raise RecursiveLearningEngineError("STRUCTURAL_SIGNATURE_MISMATCH")
    signature = next(iter(signatures))
    return {
        "schema": SCHEMA,
        "status": "VERIFIED_ABSTRACTION_CANDIDATE",
        "structural_signature": signature,
        "source_skill_ids": sorted(skill_ids),
        "applicability": sorted(applicability),
        "verification_receipt_ids": sorted(receipt_ids),
        "trusted_source_evidence": True,
        "promotion_authorized": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
