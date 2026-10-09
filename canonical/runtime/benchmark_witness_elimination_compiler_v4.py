"""Proof-carrying benchmark claim kernel v4.

This is a strict successor of benchmark_witness_elimination_compiler_v3.  V3
checks proof-carrying witness structure.  V4 adds the locks required before a
benchmark claim can become admissible evidence:

* exact claim/target/candidate/harness/resource/scoring identity
* frozen-before-evidence policy
* complete scope accounting or a proof-carrying stronger superset
* complete failure accounting and no undisclosed exclusions
* contamination/provenance gate
* evaluator-family robustness
* reproducible evidence capsule
* freshness against the current target identity

The kernel returns only PROVEN, DISPROVEN, UNKNOWN, or STALE.  It never grants
acceptance, family, ownership, capability, or terminal credit.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Mapping

from canonical.runtime.benchmark_witness_elimination_compiler_v3 import (
    evaluate_certificate as evaluate_v3_certificate,
)
from canonical.runtime.proof_carrying_scope_cover_v1 import (
    evaluate as evaluate_scope_cover,
)

SCHEMA = "PROJECT_BRAIN_BENCHMARK_CLAIM_KERNEL_V4"
TERMINAL_SCOPE_STATES = {"VALID_RESULT", "COUNTED_FAILURE", "BENCHMARK_INVALID"}
VALID_VERDICTS = {"PROVEN", "DISPROVEN", "UNKNOWN", "STALE"}
VALID_SCOPE_MODES = {
    "EXACT_TASK_SET",
    "BOUND_SCOPE_RECEIPT",
    "PROOF_CARRYING_SUPERSET",
}
VALID_EVALUATOR_MODES = {"NATIVE_SINGLE", "ROBUST_FAMILY", "OBJECTIVE"}

@dataclass(frozen=True)
class Verdict:
    predicate_id: str
    status: str
    reason: str
    locks: dict[str, str]
    v3_admissible: bool = False
    terminal_credit: int = 0
    acceptance_credit: int = 0
    family_credit: int = 0
    ownership_credit: int = 0
    promotion_authority: bool = False

def _hex40(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(ch in "0123456789abcdef" for ch in value)
    )

def _binding(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and isinstance(value.get("path"), str)
        and bool(value["path"].strip())
        and _hex40(value.get("git_blob_sha"))
    )

def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

def _identity_lock(policy: Mapping[str, Any], evidence: Mapping[str, Any]) -> tuple[str, str]:
    frozen = policy.get("frozen_identity")
    observed = evidence.get("observed_identity")
    if not isinstance(frozen, Mapping) or not frozen:
        return "UNKNOWN", "FROZEN_IDENTITY_MISSING"
    if not isinstance(observed, Mapping):
        return "UNKNOWN", "OBSERVED_IDENTITY_MISSING"
    required = policy.get("identity_keys")
    if not isinstance(required, list) or not required or not all(isinstance(x, str) for x in required):
        return "UNKNOWN", "IDENTITY_KEYS_INVALID"
    for key in required:
        if key not in frozen:
            return "UNKNOWN", f"FROZEN_IDENTITY_KEY_MISSING:{key}"
        if key not in observed:
            return "UNKNOWN", f"OBSERVED_IDENTITY_KEY_MISSING:{key}"
        if frozen[key] != observed[key]:
            return "UNKNOWN", f"IDENTITY_MISMATCH:{key}"
    return "PASS", "IDENTITY_EXACT"

def _freshness_lock(policy: Mapping[str, Any], current: Any) -> tuple[str, str]:
    frozen = policy.get("frozen_identity")
    if not isinstance(frozen, Mapping):
        return "UNKNOWN", "FROZEN_IDENTITY_MISSING"
    if not isinstance(current, Mapping):
        return "UNKNOWN", "CURRENT_IDENTITY_MISSING"
    keys = policy.get("freshness_keys")
    if not isinstance(keys, list) or not keys or not all(isinstance(x, str) for x in keys):
        return "UNKNOWN", "FRESHNESS_KEYS_INVALID"
    for key in keys:
        if key not in frozen or key not in current:
            return "UNKNOWN", f"FRESHNESS_KEY_MISSING:{key}"
        if frozen[key] != current[key]:
            return "STALE", f"CURRENT_IDENTITY_DRIFT:{key}"
    return "PASS", "FRESH"

def _policy_freeze_lock(policy: Mapping[str, Any], evidence: Mapping[str, Any]) -> tuple[str, str]:
    if not _binding(policy.get("policy_binding")):
        return "UNKNOWN", "POLICY_BINDING_INVALID"
    if policy.get("candidate_frozen") is not True:
        return "UNKNOWN", "CANDIDATE_NOT_FROZEN"
    if not _binding(policy.get("candidate_binding")):
        return "UNKNOWN", "CANDIDATE_BINDING_INVALID"
    frozen_at = _parse_time(policy.get("frozen_at"))
    observed_at = _parse_time(evidence.get("observed_at"))
    if frozen_at is None or observed_at is None:
        return "UNKNOWN", "POLICY_OR_EVIDENCE_TIME_INVALID"
    if frozen_at.tzinfo is None or observed_at.tzinfo is None:
        return "UNKNOWN", "POLICY_OR_EVIDENCE_TIMEZONE_MISSING"
    if observed_at < frozen_at:
        return "UNKNOWN", "EVIDENCE_PREDATES_FROZEN_POLICY"
    return "PASS", "POLICY_FROZEN_BEFORE_EVIDENCE"

def _scope_lock(policy: Mapping[str, Any], evidence: Mapping[str, Any]) -> tuple[str, str]:
    scope = policy.get("scope")
    if not isinstance(scope, Mapping):
        return "UNKNOWN", "SCOPE_POLICY_MISSING"
    mode = scope.get("mode")
    if mode not in VALID_SCOPE_MODES:
        return "UNKNOWN", "SCOPE_MODE_INVALID"

    if mode == "EXACT_TASK_SET":
        required = scope.get("task_ids")
        rows = evidence.get("scope_records")
        if not isinstance(required, list) or not required or not all(isinstance(x, str) and x for x in required):
            return "UNKNOWN", "REQUIRED_TASK_SET_INVALID"
        if len(required) != len(set(required)):
            return "UNKNOWN", "REQUIRED_TASK_SET_DUPLICATE"
        if not isinstance(rows, list):
            return "UNKNOWN", "SCOPE_RECORDS_MISSING"
        seen: dict[str, Mapping[str, Any]] = {}
        for row in rows:
            if not isinstance(row, Mapping):
                return "UNKNOWN", "SCOPE_RECORD_MALFORMED"
            task_id = row.get("task_id")
            if not isinstance(task_id, str) or not task_id:
                return "UNKNOWN", "SCOPE_RECORD_TASK_ID_INVALID"
            if task_id in seen:
                return "UNKNOWN", f"SCOPE_RECORD_DUPLICATE:{task_id}"
            if row.get("state") not in TERMINAL_SCOPE_STATES:
                return "UNKNOWN", f"SCOPE_RECORD_NONTERMINAL:{task_id}"
            seen[task_id] = row
        req = set(required)
        got = set(seen)
        if got != req:
            return "UNKNOWN", "CLAIM_SCOPE_EXCEEDS_OR_DIFFERS_FROM_EVIDENCE_SCOPE"
        return "PASS", "EXACT_SCOPE_COMPLETE"

    if mode == "BOUND_SCOPE_RECEIPT":
        receipt = evidence.get("scope_receipt")
        if not isinstance(receipt, Mapping):
            return "UNKNOWN", "SCOPE_RECEIPT_MISSING"
        if not _binding(receipt.get("binding")):
            return "UNKNOWN", "SCOPE_RECEIPT_BINDING_INVALID"
        if receipt.get("independent_verified") is not True:
            return "UNKNOWN", "SCOPE_RECEIPT_NOT_INDEPENDENTLY_VERIFIED"
        if receipt.get("scope_complete") is not True:
            return "UNKNOWN", "SCOPE_RECEIPT_NOT_COMPLETE"
        if receipt.get("scope_id") != scope.get("scope_id"):
            return "UNKNOWN", "SCOPE_RECEIPT_SCOPE_ID_MISMATCH"
        return "PASS", "BOUND_SCOPE_COMPLETE"

    cover = evidence.get("scope_cover")
    if not isinstance(cover, Mapping):
        return "UNKNOWN", "PROOF_CARRYING_SCOPE_COVER_MISSING"
    cover_result = evaluate_scope_cover(cover)
    if cover_result.get("pass") is not True:
        errors = cover_result.get("errors") or []
        suffix = errors[0] if errors else "UNSPECIFIED"
        return "UNKNOWN", f"SCOPE_COVER_NOT_PROVED:{suffix}"
    if cover_result.get("predicate_id") != policy.get("predicate_id"):
        return "UNKNOWN", "SCOPE_COVER_PREDICATE_MISMATCH"
    frozen_identity = policy.get("frozen_identity")
    frozen_benchmark = (
        frozen_identity.get("benchmark_id")
        if isinstance(frozen_identity, Mapping)
        else None
    )
    if cover_result.get("benchmark_id") != frozen_benchmark:
        return "UNKNOWN", "SCOPE_COVER_BENCHMARK_ID_MISMATCH"
    return "PASS", "PROOF_CARRYING_SCOPE_SUPERSET"

def _provenance_lock(policy: Mapping[str, Any], evidence: Mapping[str, Any]) -> tuple[str, str]:
    prov = evidence.get("provenance")
    if not isinstance(prov, Mapping):
        return "UNKNOWN", "PROVENANCE_MISSING"
    if not _binding(prov.get("binding")):
        return "UNKNOWN", "PROVENANCE_BINDING_INVALID"
    if prov.get("precommitment_frozen") is not True:
        return "UNKNOWN", "PRECOMMITMENT_NOT_FROZEN"
    if prov.get("target_outcome_not_used") is not True:
        return "UNKNOWN", "TARGET_OUTCOME_LEAKAGE_NOT_EXCLUDED"
    if policy.get("require_clean_provenance", True) and prov.get("status") != "CLEAN":
        return "UNKNOWN", "RUN_CONTAMINATED_OR_UNCLEARED"
    return "PASS", "PROVENANCE_CLEAN"

def _evaluator_lock(policy: Mapping[str, Any], evidence: Mapping[str, Any]) -> tuple[str, str]:
    ep = policy.get("evaluator")
    if not isinstance(ep, Mapping):
        return "UNKNOWN", "EVALUATOR_POLICY_MISSING"
    mode = ep.get("mode")
    if mode not in VALID_EVALUATOR_MODES:
        return "UNKNOWN", "EVALUATOR_MODE_INVALID"
    if mode == "OBJECTIVE":
        if ep.get("objective_validator") is not True:
            return "UNKNOWN", "OBJECTIVE_EVALUATOR_NOT_DECLARED"
        objective = evidence.get("objective_evaluator")
        if not isinstance(objective, Mapping):
            return "UNKNOWN", "OBJECTIVE_EVALUATOR_EVIDENCE_MISSING"
        if not _binding(objective.get("binding")):
            return "UNKNOWN", "OBJECTIVE_EVALUATOR_BINDING_INVALID"
        if objective.get("independent_verified") is not True:
            return "UNKNOWN", "OBJECTIVE_EVALUATOR_NOT_INDEPENDENTLY_VERIFIED"
        if objective.get("relation") == "TARGET_GT_BRAIN":
            return "DISPROVEN", "OBJECTIVE_EVALUATOR_FAVORS_TARGET"
        if objective.get("relation") not in {"BRAIN_GT_TARGET", "BRAIN_GE_TARGET"}:
            return "UNKNOWN", "OBJECTIVE_EVALUATOR_RELATION_INCONCLUSIVE"
        return "PASS", "OBJECTIVE_EVALUATOR"

    required = ep.get("required_evaluator_ids")
    rows = evidence.get("evaluator_records")
    if not isinstance(required, list) or not required or not all(isinstance(x, str) and x for x in required):
        return "UNKNOWN", "REQUIRED_EVALUATOR_SET_INVALID"
    if mode == "NATIVE_SINGLE" and len(required) != 1:
        return "UNKNOWN", "NATIVE_SINGLE_REQUIRES_ONE_EVALUATOR"
    if not isinstance(rows, list):
        return "UNKNOWN", "EVALUATOR_RECORDS_MISSING"

    by_id: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            return "UNKNOWN", "EVALUATOR_RECORD_MALFORMED"
        eid = row.get("evaluator_id")
        if not isinstance(eid, str) or not eid or eid in by_id:
            return "UNKNOWN", "EVALUATOR_ID_INVALID_OR_DUPLICATE"
        by_id[eid] = row

    if set(by_id) != set(required):
        return "UNKNOWN", "EVALUATOR_FAMILY_COVERAGE_MISMATCH"

    for eid in required:
        row = by_id[eid]
        if not _binding(row.get("binding")):
            return "UNKNOWN", f"EVALUATOR_BINDING_INVALID:{eid}"
        if row.get("calibration_pass") is not True:
            return "UNKNOWN", f"EVALUATOR_CALIBRATION_NOT_PASSED:{eid}"
        if row.get("stable_under_declared_perturbations") is not True:
            return "UNKNOWN", f"EVALUATOR_UNSTABLE:{eid}"
        relation = row.get("relation")
        if relation == "TARGET_GT_BRAIN":
            return "DISPROVEN", f"ADMISSIBLE_EVALUATOR_FAVORS_TARGET:{eid}"
        if relation not in {"BRAIN_GT_TARGET", "BRAIN_GE_TARGET"}:
            return "UNKNOWN", f"EVALUATOR_RELATION_INCONCLUSIVE:{eid}"
    return "PASS", "EVALUATOR_ROBUST"

def _evidence_completeness_lock(evidence: Mapping[str, Any]) -> tuple[str, str]:
    if evidence.get("failure_accounting_complete") is not True:
        return "UNKNOWN", "FAILURE_ACCOUNTING_INCOMPLETE"
    if evidence.get("undisclosed_exclusion_count") != 0:
        return "UNKNOWN", "UNDISCLOSED_EXCLUSIONS_PRESENT_OR_UNKNOWN"
    if evidence.get("reproducible") is not True:
        return "UNKNOWN", "REPRODUCIBILITY_NOT_PROVED"
    if not _binding(evidence.get("evidence_capsule_binding")):
        return "UNKNOWN", "EVIDENCE_CAPSULE_BINDING_INVALID"
    return "PASS", "EVIDENCE_COMPLETE"

def _v3_lock(policy: Mapping[str, Any], evidence: Mapping[str, Any]) -> tuple[str, str, bool]:
    cert = evidence.get("v3_certificate")
    if not isinstance(cert, Mapping):
        return "UNKNOWN", "V3_CERTIFICATE_MISSING", False
    if cert.get("predicate_id") != policy.get("predicate_id"):
        return "UNKNOWN", "V3_CERTIFICATE_PREDICATE_MISMATCH", False
    verdict = evaluate_v3_certificate(dict(cert))
    if verdict.admissible:
        return "PASS", verdict.reason, True
    if verdict.reason == "PROVED_LOWER_BOUND_BELOW_TARGET":
        return "DISPROVEN", verdict.reason, False
    return "UNKNOWN", "V3_NOT_ADMISSIBLE:" + verdict.reason, False

def evaluate_claim(spec: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, Mapping):
        return asdict(Verdict("UNKNOWN", "UNKNOWN", "INPUT_NOT_OBJECT", {})) | {"schema": SCHEMA}

    policy = spec.get("policy")
    evidence = spec.get("evidence")
    current = spec.get("current_identity")
    if not isinstance(policy, Mapping):
        return asdict(Verdict("UNKNOWN", "UNKNOWN", "POLICY_MISSING", {})) | {"schema": SCHEMA}
    pid = str(policy.get("predicate_id", "UNKNOWN"))
    if not isinstance(evidence, Mapping):
        return asdict(Verdict(pid, "UNKNOWN", "EVIDENCE_MISSING", {})) | {"schema": SCHEMA}

    locks: dict[str, str] = {}

    status, reason = _freshness_lock(policy, current)
    locks["freshness"] = status
    if status == "STALE":
        return asdict(Verdict(pid, "STALE", reason, locks)) | {"schema": SCHEMA}
    if status != "PASS":
        return asdict(Verdict(pid, "UNKNOWN", reason, locks)) | {"schema": SCHEMA}

    checks = (
        ("identity", _identity_lock(policy, evidence)),
        ("policy_freeze", _policy_freeze_lock(policy, evidence)),
        ("scope", _scope_lock(policy, evidence)),
        ("provenance", _provenance_lock(policy, evidence)),
        ("evaluator", _evaluator_lock(policy, evidence)),
        ("evidence", _evidence_completeness_lock(evidence)),
    )
    for name, (state, why) in checks:
        locks[name] = state
        if state == "DISPROVEN":
            return asdict(Verdict(pid, "DISPROVEN", why, locks)) | {"schema": SCHEMA}
        if state != "PASS":
            return asdict(Verdict(pid, "UNKNOWN", why, locks)) | {"schema": SCHEMA}

    v3_state, v3_reason, v3_ok = _v3_lock(policy, evidence)
    locks["proof_relation"] = v3_state
    if v3_state == "DISPROVEN":
        return asdict(Verdict(pid, "DISPROVEN", v3_reason, locks, False)) | {"schema": SCHEMA}
    if v3_state != "PASS":
        return asdict(Verdict(pid, "UNKNOWN", v3_reason, locks, False)) | {"schema": SCHEMA}

    return asdict(Verdict(
        pid,
        "PROVEN",
        "ALL_IDENTITY_EVIDENCE_SCOPE_PROVENANCE_EVALUATOR_FRESHNESS_LOCKS_PASS",
        locks,
        v3_ok,
    )) | {
        "schema": SCHEMA,
        "claim_scope": policy.get("claim_scope"),
        "hard_nonclaim": (
            "PROVEN_IS_ONLY_A_PROOF_KERNEL_RESULT__CANONICAL_ACCEPTANCE_REQUIRES_"
            "REGISTRY_BINDING_INDEPENDENT_VERIFICATION_AND_EXISTING_GOVERNANCE_PROMOTION"
        ),
    }

def compile_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    claims = manifest.get("claims") if isinstance(manifest, Mapping) else None
    if not isinstance(claims, list):
        claims = []
    verdicts = [evaluate_claim(x) for x in claims]
    return {
        "schema": "PROJECT_BRAIN_BENCHMARK_CLAIM_COMPILATION_V4",
        "claim_count": len(verdicts),
        "proved_count": sum(v.get("status") == "PROVEN" for v in verdicts),
        "disproved_count": sum(v.get("status") == "DISPROVEN" for v in verdicts),
        "unknown_count": sum(v.get("status") == "UNKNOWN" for v in verdicts),
        "stale_count": sum(v.get("status") == "STALE" for v in verdicts),
        "verdicts": verdicts,
        "promotion_authority": False,
        "terminal_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
