"""Bridge source-aligned semantic proof v2 into monotone policy resolution.

Checked primitive and certified scope constraints are the only facts admitted into
the monotone semantic state.

IMPORTANT: source entailment is not policy adequacy. A caller-supplied
policy_conditions formula may be used to test logical entailment, but a policy is
returned as COMMON_POLICY_CERTIFIED only when a separate content-addressed
Brain adequacy certificate and an independent verification receipt authenticate
that exact policy/condition pair.

The bridge has no terminal authority.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v2 import verify_proof
from canonical.runtime.monotone_semantic_constraint_kernel_v1 import resolve_common_policy

SCHEMA = "BRAIN_PROOF_CARRYING_SEMANTIC_REFINEMENT_V2"
ROOT = Path(__file__).resolve().parents[2]

ADEQUACY_SCHEMA = "PROJECT_BRAIN_POLICY_ADEQUACY_CERTIFICATE_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_POLICY_ADEQUACY_INDEPENDENT_VERIFICATION_V1"


def _canon(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _condition_sha256(condition: Mapping[str, Any]) -> str:
    return sha256(_canon(condition).encode("utf-8")).hexdigest()


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _bound_path(raw: Any, *, prefixes: tuple[str, ...]) -> Path:
    value = str(raw or "").strip()
    p = Path(value)
    if not value or p.is_absolute() or ".." in p.parts:
        raise ValueError("NONCANONICAL_BINDING_PATH")
    if not any(value.startswith(prefix) for prefix in prefixes):
        raise ValueError("BINDING_PATH_OUTSIDE_ALLOWED_SCOPE")
    full = ROOT / p
    if not full.is_file():
        raise ValueError("BOUND_FILE_MISSING:" + value)
    return full


def _load_json(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("BOUND_JSON_NOT_OBJECT")
    return value


def _authenticate_policy_adequacy(
    policy_id: str,
    condition: Mapping[str, Any],
    binding: Mapping[str, Any] | None,
) -> tuple[bool, dict[str, Any]]:
    if not isinstance(binding, Mapping):
        return False, {"policy_id": policy_id, "reason": "ADEQUACY_BINDING_MISSING"}

    try:
        adequacy_path = _bound_path(
            binding.get("adequacy_certificate_path"),
            prefixes=("canonical/governance/", "canonical/verification/"),
        )
        verification_path = _bound_path(
            binding.get("independent_verification_path"),
            prefixes=("canonical/verification/",),
        )

        adequacy_blob = _git_blob_sha(adequacy_path)
        verification_blob = _git_blob_sha(verification_path)
        if binding.get("adequacy_certificate_blob_sha") != adequacy_blob:
            raise ValueError("ADEQUACY_CERTIFICATE_BLOB_DRIFT")
        if binding.get("independent_verification_blob_sha") != verification_blob:
            raise ValueError("ADEQUACY_VERIFICATION_BLOB_DRIFT")

        adequacy = _load_json(adequacy_path)
        verification = _load_json(verification_path)
        condition_sha = _condition_sha256(condition)

        if adequacy.get("schema") != ADEQUACY_SCHEMA:
            raise ValueError("ADEQUACY_CERTIFICATE_SCHEMA_INVALID")
        if adequacy.get("policy_id") != policy_id:
            raise ValueError("ADEQUACY_POLICY_ID_MISMATCH")
        if adequacy.get("policy_condition_sha256") != condition_sha:
            raise ValueError("ADEQUACY_CONDITION_MISMATCH")
        if adequacy.get("adequacy_proved") is not True:
            raise ValueError("ADEQUACY_NOT_PROVED")
        if adequacy.get("brain_owned") is not True:
            raise ValueError("POLICY_NOT_BRAIN_OWNED")
        if adequacy.get("load_bearing_constraints_preserved") is not True:
            raise ValueError("LOAD_BEARING_CONSTRAINTS_NOT_PRESERVED")

        if verification.get("schema") != VERIFY_SCHEMA:
            raise ValueError("ADEQUACY_VERIFICATION_SCHEMA_INVALID")
        if verification.get("policy_id") != policy_id:
            raise ValueError("ADEQUACY_VERIFICATION_POLICY_ID_MISMATCH")
        if verification.get("subject_git_blob_sha") != adequacy_blob:
            raise ValueError("ADEQUACY_VERIFICATION_SUBJECT_MISMATCH")
        if verification.get("pass") is not True:
            raise ValueError("ADEQUACY_INDEPENDENT_VERIFICATION_NOT_PASS")

        return True, {
            "policy_id": policy_id,
            "condition_sha256": condition_sha,
            "adequacy_certificate_path": str(adequacy_path.relative_to(ROOT)),
            "adequacy_certificate_blob_sha": adequacy_blob,
            "independent_verification_path": str(verification_path.relative_to(ROOT)),
            "independent_verification_blob_sha": verification_blob,
        }
    except Exception as exc:
        return False, {
            "policy_id": policy_id,
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def resolve_from_source_proof(
    source_text: str,
    *,
    source_id: str,
    claims: Sequence[Mapping[str, Any]],
    decision_basis: Sequence[str],
    policy_conditions: Mapping[str, Mapping[str, Any]],
    policy_adequacy_bindings: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    proof = verify_proof(source_text, source_id=source_id, claims=claims)
    if proof.get("status") == "FAIL_CLOSED":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": "SOURCE_PROOF_FAIL_CLOSED",
            "source_proof": proof,
            "terminal_authority": False,
        }

    proved = proof.get("proved_constraints") or []
    refinement = resolve_common_policy(
        decision_basis,
        policy_conditions,
        formal_source_constraints=proved,
        proposed_refinements=proved,
    )
    if refinement.get("status") == "FAIL_CLOSED":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": "SEMANTIC_REFINEMENT_FAIL_CLOSED",
            "source_proof": proof,
            "semantic_refinement": refinement,
            "terminal_authority": False,
        }

    entailed = list(refinement.get("certified_common_policies", []))
    bindings = policy_adequacy_bindings if isinstance(policy_adequacy_bindings, Mapping) else {}

    certified: list[str] = []
    auth_rows: list[dict[str, Any]] = []
    rejected_auth: list[dict[str, Any]] = []
    for pid in entailed:
        condition = policy_conditions.get(pid)
        if not isinstance(condition, Mapping):
            rejected_auth.append({"policy_id": pid, "reason": "POLICY_CONDITION_MISSING"})
            continue
        ok, row = _authenticate_policy_adequacy(pid, condition, bindings.get(pid))
        if ok:
            certified.append(pid)
            auth_rows.append(row)
        else:
            rejected_auth.append(row)

    if certified:
        status = "COMMON_POLICY_CERTIFIED"
    elif entailed:
        status = "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED"
    else:
        status = "UNRESOLVED"

    return {
        "schema": SCHEMA,
        "status": status,
        "source_proof": proof,
        "semantic_refinement": refinement,
        "entailed_policy_conditions": entailed,
        "certified_common_policies": sorted(certified),
        "authenticated_policy_adequacy": sorted(auth_rows, key=lambda x: x["policy_id"]),
        "rejected_policy_adequacy_bindings": sorted(rejected_auth, key=lambda x: x.get("policy_id", "")),
        "terminal_authority": False,
        "boundary": (
            "SOURCE_ALIGNED_V2_PROVES_ONLY_NARROW_PRIMITIVES_AND_CERTIFIED_SCOPE;"
            "CALLER_SUPPLIED_POLICY_CONDITIONS_ARE_ONLY_LOGICAL_QUERIES;"
            "COMMON_POLICY_CERTIFIED_REQUIRES_SEPARATE_CONTENT_ADDRESSED_BRAIN_OWNED_ADEQUACY"
            "_CERTIFICATE_PLUS_INDEPENDENT_VERIFICATION"
        ),
    }
