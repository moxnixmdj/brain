"""Claim-instance assurance binder V1.

This is the bridge from open domain-level assurance graphs to sound bounded
claim certificates. It deliberately does NOT close a whole domain or the
open-ended mission. It binds a frozen claim to content-addressed verifier
receipts through explicit adapter contracts.

Current V1 adapter support is intentionally narrow:
* exact professional-quality R7 single-edit causal instance receipts.

More adapters must be added explicitly and tested; arbitrary JSON cannot
self-certify semantic or execution closure.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from canonical.runtime.coverage_claim_scope_guard_v1 import validate_claim

SCHEMA = "PROJECT_BRAIN_CLAIM_INSTANCE_ASSURANCE_BINDER_V1"
BUNDLE_SCHEMA = "PROJECT_BRAIN_CLAIM_INSTANCE_ASSURANCE_BUNDLE_V1"

R7_ROOT = "R7_CAUSAL_PRESCRIPTIVE"
R7_RECEIPT_SCHEMA = (
    "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R7_SINGLE_EDIT_CAUSAL_INSTANCE_VERIFY_V1"
)
R7_DEFEATERS = frozenset({
    "C28_PREDICTIVE_PRESCRIPTIVE_GAP",
    "C29_COMPOUND_EDIT_ATTRIBUTION",
    "C30_TREATMENT_VERSION_NONINVARIANCE",
    "C31_EDIT_SEQUENCE_INTERACTION",
})
R7_ALLOWED_DISPOSITIONS = frozenset({
    "DISCHARGED_FOR_THIS_EXACT_INSTANCE",
    "PROVEN_IRRELEVANT_TO_THIS_CLAIM_SCOPE",
})


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return sha1(header + data).hexdigest()


def _base(status: str, *, passed: bool) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "claim_soundness_only": True,
        "global_domain_closure": False,
        "global_mission_completion_derivable": False,
        "live_default": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {**_base("FAIL_CLOSED", passed=False), "reason": reason, **extra}


def _safe_path(repo_root: str | Path, relative_path: str) -> Path | None:
    if not isinstance(relative_path, str) or not relative_path:
        return None
    root = Path(repo_root).resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _load_receipt(
    *,
    repo_root: str | Path,
    relative_path: str,
    expected_git_blob_sha: str,
) -> tuple[dict[str, Any] | None, str | None]:
    path = _safe_path(repo_root, relative_path)
    if path is None:
        return None, "EVIDENCE_PATH_INVALID"
    if not path.is_file():
        return None, "EVIDENCE_FILE_MISSING"
    raw = path.read_bytes()
    actual_sha = git_blob_sha(raw)
    if actual_sha != expected_git_blob_sha:
        return None, "EVIDENCE_GIT_BLOB_SHA_MISMATCH"
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except Exception:
        return None, "EVIDENCE_JSON_INVALID"
    if not isinstance(parsed, dict):
        return None, "EVIDENCE_RECEIPT_NOT_OBJECT"
    return parsed, None


def _adapt_r7_single_edit(receipt: Mapping[str, Any]) -> dict[str, Any]:
    if receipt.get("schema") != R7_RECEIPT_SCHEMA:
        return {"pass": False, "reason": "R7_RECEIPT_SCHEMA_INVALID"}
    status = str(receipt.get("status") or "")
    if not status.startswith(
        "PASS__REAL_PROFESSIONAL_CODE_EDIT_AB__OLD_FAIL_NEW_PASS__"
    ):
        return {"pass": False, "reason": "R7_RECEIPT_STATUS_NOT_ACCEPTED"}
    if receipt.get("root_id") != R7_ROOT:
        return {"pass": False, "reason": "R7_ROOT_ID_MISMATCH"}
    if receipt.get("terminal_authority") is not False:
        return {"pass": False, "reason": "R7_TERMINAL_AUTHORITY_FORBIDDEN"}
    if receipt.get("terminal_credit_delta", 0) != 0:
        return {"pass": False, "reason": "R7_NONZERO_TERMINAL_CREDIT_FORBIDDEN"}

    claim_scope = receipt.get("claim_scope")
    if not isinstance(claim_scope, Mapping):
        return {"pass": False, "reason": "R7_CLAIM_SCOPE_MISSING"}
    if claim_scope.get("kind") != "EXACT_SINGLE_EDIT_PROFESSIONAL_CODE_INTERVENTION_INSTANCE":
        return {"pass": False, "reason": "R7_CLAIM_SCOPE_KIND_INVALID"}
    claimed_effect = claim_scope.get("claimed_effect")
    if not isinstance(claimed_effect, str) or not claimed_effect:
        return {"pass": False, "reason": "R7_CLAIMED_EFFECT_MISSING"}

    conclusions = receipt.get("conclusions")
    if not isinstance(conclusions, Mapping):
        return {"pass": False, "reason": "R7_CONCLUSIONS_MISSING"}
    if conclusions.get("exact_claim_scoped_professional_edit_causality_proved") is not True:
        return {"pass": False, "reason": "R7_CLAIM_SCOPED_CAUSALITY_NOT_PROVED"}
    if conclusions.get("r7_global_root_closed") is not False:
        return {"pass": False, "reason": "R7_GLOBAL_ROOT_OVERCLAIM"}

    dispositions = receipt.get("r7_defeater_disposition")
    if not isinstance(dispositions, Mapping):
        return {"pass": False, "reason": "R7_DEFEATER_DISPOSITION_MISSING"}
    if set(dispositions) != set(R7_DEFEATERS):
        return {
            "pass": False,
            "reason": "R7_DEFEATER_SET_INCOMPLETE_OR_EXTRA",
            "expected": sorted(R7_DEFEATERS),
            "observed": sorted(dispositions),
        }
    for defeater_id in sorted(R7_DEFEATERS):
        row = dispositions.get(defeater_id)
        if not isinstance(row, Mapping):
            return {"pass": False, "reason": "R7_DEFEATER_ROW_INVALID:" + defeater_id}
        if row.get("claim_scoped_state") not in R7_ALLOWED_DISPOSITIONS:
            return {
                "pass": False,
                "reason": "R7_DEFEATER_NOT_CLOSED_FOR_CLAIM:" + defeater_id,
            }

    return {
        "pass": True,
        "root_id": R7_ROOT,
        "scope_sha256": sha256_value(dict(claim_scope)),
        "target_predicate_sha256": sha256_value(claimed_effect),
        "semantics_sha256": sha256_value(dict(dispositions)),
        "evidence_kind": "EXACT_SINGLE_EDIT_R7_CAUSAL_EXECUTION",
        "claim_scoped_defeaters_closed": sorted(R7_DEFEATERS),
        "claim_scoped_adversarial_closure": True,
    }


Adapter = Callable[[Mapping[str, Any]], dict[str, Any]]
ADAPTERS: dict[str, Adapter] = {
    "PROFESSIONAL_QUALITY_R7_SINGLE_EDIT_CAUSAL_INSTANCE_V1": _adapt_r7_single_edit,
}


def evaluate(
    bundle: Mapping[str, Any],
    *,
    current_mission_blob_sha: str,
    repo_root: str | Path,
) -> dict[str, Any]:
    if not isinstance(bundle, Mapping):
        return _fail("BUNDLE_NOT_OBJECT")
    if bundle.get("schema") != BUNDLE_SCHEMA:
        return _fail("BUNDLE_SCHEMA_INVALID")

    claim = bundle.get("claim")
    if not isinstance(claim, Mapping):
        return _fail("CLAIM_NOT_OBJECT")
    claim_check = validate_claim(
        claim,
        current_mission_blob_sha=current_mission_blob_sha,
    )
    if claim_check.get("pass") is not True:
        return _fail(
            "CLAIM_SCOPE_INVALID",
            claim_errors=list(claim_check.get("errors") or []),
        )

    required_roots = bundle.get("required_root_ids")
    if (
        not isinstance(required_roots, list)
        or not required_roots
        or not all(isinstance(x, str) and x for x in required_roots)
        or len(required_roots) != len(set(required_roots))
    ):
        return _fail("REQUIRED_ROOT_IDS_INVALID")

    evidence = bundle.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        return _fail("EVIDENCE_LIST_REQUIRED")

    accepted: list[dict[str, Any]] = []
    for index, entry in enumerate(evidence):
        if not isinstance(entry, Mapping):
            return _fail("EVIDENCE_ENTRY_NOT_OBJECT", evidence_index=index)
        adapter_id = entry.get("adapter_id")
        adapter = ADAPTERS.get(adapter_id)
        if adapter is None:
            return _fail(
                "EVIDENCE_ADAPTER_UNREGISTERED",
                evidence_index=index,
                adapter_id=adapter_id,
            )
        path = entry.get("path")
        expected_sha = entry.get("git_blob_sha")
        if not isinstance(path, str) or not isinstance(expected_sha, str):
            return _fail("EVIDENCE_REFERENCE_INVALID", evidence_index=index)
        receipt, error = _load_receipt(
            repo_root=repo_root,
            relative_path=path,
            expected_git_blob_sha=expected_sha,
        )
        if error is not None or receipt is None:
            return _fail(
                error or "EVIDENCE_LOAD_FAILED",
                evidence_index=index,
                path=path,
            )
        adapted = adapter(receipt)
        if adapted.get("pass") is not True:
            return _fail(
                "EVIDENCE_ADAPTER_REJECTED",
                evidence_index=index,
                path=path,
                adapter_reason=adapted.get("reason"),
            )
        accepted.append({
            "adapter_id": adapter_id,
            "path": path,
            "git_blob_sha": expected_sha,
            **adapted,
        })

    if not all(row.get("claim_scoped_adversarial_closure") is True for row in accepted):
        return _fail("CLAIM_SCOPED_ADVERSARIAL_CLOSURE_UNPROVED")

    covered_roots = {row["root_id"] for row in accepted}
    missing_roots = sorted(set(required_roots) - covered_roots)
    extra_roots = sorted(covered_roots - set(required_roots))
    if missing_roots:
        return _fail("REQUIRED_ROOT_EVIDENCE_MISSING", missing_root_ids=missing_roots)
    if extra_roots:
        return _fail("UNDECLARED_ROOT_EVIDENCE", extra_root_ids=extra_roots)

    scope_digests = {row["scope_sha256"] for row in accepted}
    target_digests = {row["target_predicate_sha256"] for row in accepted}
    semantics_digests = {row["semantics_sha256"] for row in accepted}
    if len(scope_digests) != 1 or claim.get("scope_sha256") not in scope_digests:
        return _fail("CLAIM_SCOPE_NOT_BOUND_TO_EVIDENCE")
    if len(target_digests) != 1 or claim.get("target_predicate_sha256") not in target_digests:
        return _fail("CLAIM_TARGET_NOT_BOUND_TO_EVIDENCE")
    if len(semantics_digests) != 1 or claim.get("semantics_sha256") not in semantics_digests:
        return _fail("CLAIM_SEMANTICS_NOT_BOUND_TO_EVIDENCE")

    return {
        **_base("PASS__CLAIM_INSTANCE_ASSURANCE_CLOSED", passed=True),
        "claim_id": claim_check.get("claim_id"),
        "claim_kind": claim.get("claim_kind"),
        "required_root_ids": list(required_roots),
        "covered_root_ids": sorted(covered_roots),
        "accepted_evidence": accepted,
        "domain_semantic_closure": True,
        "domain_execution_closure": True,
        "claim_scoped_adversarial_closure": True,
        "closure_scope": "FROZEN_CLAIM_INSTANCE_ONLY",
    }
