"""Verify the R3 V3 composition-compatibility successor without weakening V2."""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_r3_root_subject_binding_verify_v2 as v2

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_VERIFY_V3"
ROOT_ID = "R3_REALIZATION_OBSERVATION"
SUBJECT_KIND = "DECLARED_SYSTEM"
SUBJECT_ID = "PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SUBJECT_SHA = "d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
BINDING_PATH = "canonical/governance/PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_20261010_V3.json"
BINDING_BLOB = "4cd196b91613a8c0952ae0ad352d46c449b2c057"
PRIOR_PATH = "canonical/governance/PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_20261010_V2.json"
PRIOR_BLOB = "2fe91ecba3830641ed800d04b70279a3f84283bf"

SELF_AUTHORITY_FIELDS = (
    "root_subject_binding_authority",
    "real_task_render_step_receipt_bound",
    "semantic_truth_authority",
    "execution_authority",
    "quality_authority",
    "acceptance_authority",
    "promotion_authority",
    "terminal_authority",
)


def _blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _read(root: Path, rel: str, expected: str) -> dict[str, Any] | None:
    path = (root / rel).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return None
    if not path.is_file() or path.is_symlink() or _blob(path) != expected:
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return doc if isinstance(doc, dict) else None


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "root_id": ROOT_ID,
        "root_subject_binding_authority": False,
        "real_task_render_step_receipt_bound": False,
        "global_subject_identity_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def _validate_successor(binding: Mapping[str, Any], prior: Mapping[str, Any]) -> str | None:
    if binding.get("schema") != "PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1":
        return "V3_SCHEMA_INVALID"
    if binding.get("root_id") != ROOT_ID:
        return "V3_ROOT_ID_INVALID"
    if (
        binding.get("subject_kind"),
        binding.get("subject_id"),
        binding.get("subject_sha256"),
    ) != (SUBJECT_KIND, SUBJECT_ID, SUBJECT_SHA):
        return "V3_SUBJECT_IDENTITY_INVALID"

    supersedes = binding.get("supersedes")
    if not isinstance(supersedes, Mapping):
        return "V3_SUPERSEDES_MISSING"
    if (
        supersedes.get("path"),
        supersedes.get("git_blob_sha"),
    ) != (PRIOR_PATH, PRIOR_BLOB):
        return "V3_SUPERSEDES_INVALID"

    if binding.get("exact_instance") != prior.get("exact_instance"):
        return "V3_EXACT_INSTANCE_DRIFT"

    bscope = binding.get("binding_scope")
    pscope = prior.get("binding_scope")
    if not isinstance(bscope, Mapping) or not isinstance(pscope, Mapping):
        return "V3_SCOPE_INVALID"
    for key in ("behavior_id", "step_id", "claim"):
        if bscope.get(key) != pscope.get(key):
            return "V3_SCOPE_DRIFT:" + key

    prior_guarantees = set(pscope.get("guarantees") or [])
    successor_guarantees = set(bscope.get("guarantees") or [])
    if not prior_guarantees.issubset(successor_guarantees):
        return "V3_PRIOR_GUARANTEE_LOST"

    prior_limits = set(pscope.get("limitations") or [])
    successor_limits = set(bscope.get("limitations") or [])
    if not prior_limits.issubset(successor_limits):
        return "V3_PRIOR_LIMITATION_LOST"
    if "NO_GLOBAL_SUBJECT_IDENTITY_AUTHORITY" not in successor_limits:
        return "V3_GLOBAL_AUTHORITY_LIMITATION_MISSING"
    if "GLOBAL_SUBJECT_IDENTITY_SELF_AUTHORITY_EXPLICITLY_FORBIDDEN" not in successor_guarantees:
        return "V3_GLOBAL_AUTHORITY_GUARANTEE_MISSING"

    if binding.get("global_subject_identity_authority") is not False:
        return "V3_GLOBAL_SUBJECT_SELF_AUTHORITY_FORBIDDEN"
    for field in SELF_AUTHORITY_FIELDS:
        if binding.get(field) is not False:
            return "V3_SELF_AUTHORITY_FORBIDDEN:" + field
    return None


def verify(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]

    prior_result = v2.verify(repo_root=root)
    if prior_result.get("pass") is not True:
        return _fail("V2_PREDECESSOR_REPLAY_FAILED", predecessor=prior_result)
    if prior_result.get("root_subject_binding_authority") is not True:
        return _fail("V2_ROOT_AUTHORITY_MISSING")
    if prior_result.get("real_task_render_step_receipt_bound") is not True:
        return _fail("V2_REAL_TASK_RECEIPT_MISSING")
    if prior_result.get("global_r3_root_closed") is not False:
        return _fail("V2_GLOBAL_R3_BOUNDARY_DRIFT")

    prior = _read(root, PRIOR_PATH, PRIOR_BLOB)
    binding = _read(root, BINDING_PATH, BINDING_BLOB)
    if prior is None or binding is None:
        return _fail("V3_OR_PREDECESSOR_BYTES_INVALID")

    error = _validate_successor(binding, prior)
    if error is not None:
        return _fail(error)

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__R3_V3_EXPLICIT_NO_GLOBAL_SUBJECT_SELF_AUTHORITY__V2_EVIDENCE_PRESERVED",
        "root_id": ROOT_ID,
        "subject_kind": SUBJECT_KIND,
        "subject_id": SUBJECT_ID,
        "subject_sha256": SUBJECT_SHA,
        "subject_binding_git_blob_sha": BINDING_BLOB,
        "root_subject_binding_authority": True,
        "real_task_render_step_receipt_bound": True,
        "exact_real_task_receipt_count": prior_result.get("exact_real_task_receipt_count"),
        "global_subject_identity_authority": False,
        "global_r3_root_closed": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
