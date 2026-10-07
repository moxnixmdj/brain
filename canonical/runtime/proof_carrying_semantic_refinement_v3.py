"""Proof-carrying semantic refinement with closed policy-adequacy trust roots.

Content-addressing proves byte identity, not independent verification. A caller
must not be able to create an adequacy JSON plus a second pass=true JSON and
silently promote a policy. Generic adequacy therefore accepts only exact
code-registered roots and revalidates their evidence closure.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v3 import verify_proof
from canonical.runtime.monotone_semantic_constraint_kernel_v1 import resolve_common_policy

SCHEMA = "BRAIN_PROOF_CARRYING_SEMANTIC_REFINEMENT_V3"
ROOT = Path(__file__).resolve().parents[2]
ADEQUACY_SCHEMA = "PROJECT_BRAIN_POLICY_ADEQUACY_CERTIFICATE_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_POLICY_ADEQUACY_INDEPENDENT_VERIFICATION_V1"

TRUSTED_ADEQUACY_ROOTS: dict[str, dict[str, Any]] = {
    "SYNTHESIS_CERTIFIED_VISIBLE_SUPPORT_POLICY_V1": {
        "condition_sha256": "f25ad4ccc7958b9255c3f7fa69ffdf69abd946acd3ef48c38fa82d4df42e430f",
        "adequacy_certificate_path": "canonical/governance/SYNTHESIS_VISIBLE_SUPPORT_POLICY_ADEQUACY_CERTIFICATE_20261007_V1.json",
        "adequacy_certificate_blob_sha": "0e7fb524a83d97d85523c6c818af803608b72e81",
        "independent_verification_path": "canonical/verification/SYNTHESIS_VISIBLE_SUPPORT_POLICY_ADEQUACY_INDEPENDENT_VERIFICATION_20261007_V1.json",
        "independent_verification_blob_sha": "c8615927bd08bcc7daf79c419d3c5eb204a19bdd",
        "closure": {
            "policy": {
                "path": "canonical/runtime/synthesis_certified_visible_support_policy_v1.py",
                "git_blob_sha": "dcef050165201d506f66c86854cb30bcb7637b42",
            },
            "top_law": {
                "path": "canonical/governance/SYNTHESIS_CERTIFIED_VISIBLE_SUPPORT_TOP_LAW_CELL_20261007_V1.json",
                "git_blob_sha": "042d89d354a6d10f97a4ac45d45825d1673247ec",
            },
            "common_policy_cover": {
                "path": "canonical/governance/SYNTHESIS_COMMON_POLICY_COVER_20261007_V1.json",
                "git_blob_sha": "bca081880b4f90fc98b6be41c5f6b9a18192b39b",
            },
            "independent_replay": {
                "path": "canonical/verification/SYNTHESIS_COMMON_POLICY_C2_INDEPENDENT_REPLAY_20261007_V1.json",
                "git_blob_sha": "d038e5ca79286b7d69aa9ff8da8c18173569fc88",
            },
        },
    },
}


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


def _binding_matches(value: Any, expected: Mapping[str, Any]) -> bool:
    return (
        isinstance(value, Mapping)
        and value.get("path") == expected.get("path")
        and value.get("git_blob_sha") == expected.get("git_blob_sha")
    )


def _trusted_root(policy_id: str, condition_sha: str, binding: Mapping[str, Any]) -> Mapping[str, Any]:
    root = TRUSTED_ADEQUACY_ROOTS.get(policy_id)
    if not isinstance(root, Mapping):
        raise ValueError("POLICY_ADEQUACY_ROOT_UNREGISTERED")
    if root.get("condition_sha256") != condition_sha:
        raise ValueError("TRUSTED_ROOT_CONDITION_MISMATCH")
    for key in (
        "adequacy_certificate_path",
        "adequacy_certificate_blob_sha",
        "independent_verification_path",
        "independent_verification_blob_sha",
    ):
        if binding.get(key) != root.get(key):
            raise ValueError("ADEQUACY_BINDING_NOT_TRUSTED_ROOT:" + key)
    return root


def _validate_registered_synthesis_root(
    adequacy: Mapping[str, Any],
    verification: Mapping[str, Any],
    root: Mapping[str, Any],
) -> list[dict[str, str]]:
    closure = root.get("closure")
    if not isinstance(closure, Mapping):
        raise ValueError("TRUSTED_ROOT_CLOSURE_MISSING")

    docs: dict[str, Mapping[str, Any] | None] = {}
    rows: list[dict[str, str]] = []
    for name in ("policy", "top_law", "common_policy_cover", "independent_replay"):
        expected = closure.get(name)
        if not isinstance(expected, Mapping):
            raise ValueError("TRUSTED_ROOT_CLOSURE_ENTRY_MISSING:" + name)
        path = _bound_path(
            expected.get("path"),
            prefixes=("canonical/runtime/", "canonical/governance/", "canonical/verification/"),
        )
        if _git_blob_sha(path) != expected.get("git_blob_sha"):
            raise ValueError("TRUSTED_ROOT_CLOSURE_BLOB_DRIFT:" + name)
        docs[name] = _load_json(path) if str(expected.get("path")).endswith(".json") else None
        rows.append({
            "role": name,
            "path": str(expected["path"]),
            "git_blob_sha": str(expected["git_blob_sha"]),
        })

    policy = closure["policy"]
    top_ref = closure["top_law"]
    cover_ref = closure["common_policy_cover"]
    replay_ref = closure["independent_replay"]
    top = docs["top_law"]
    cover = docs["common_policy_cover"]
    replay = docs["independent_replay"]
    assert top is not None and cover is not None and replay is not None

    if not _binding_matches(adequacy.get("exact_policy"), policy):
        raise ValueError("ADEQUACY_TRUSTED_POLICY_BINDING_MISMATCH")
    if not _binding_matches(adequacy.get("adequacy_authority"), top_ref):
        raise ValueError("ADEQUACY_TRUSTED_TOP_LAW_BINDING_MISMATCH")
    if not _binding_matches(adequacy.get("common_policy_cover"), cover_ref):
        raise ValueError("ADEQUACY_TRUSTED_COVER_BINDING_MISMATCH")
    if not _binding_matches(adequacy.get("independent_replay_source"), replay_ref):
        raise ValueError("ADEQUACY_TRUSTED_REPLAY_BINDING_MISMATCH")

    evidence = verification.get("evidence")
    if not isinstance(evidence, Mapping):
        raise ValueError("ADEQUACY_VERIFICATION_EVIDENCE_MISSING")
    if not _binding_matches(evidence.get("exact_policy"), policy):
        raise ValueError("VERIFICATION_TRUSTED_POLICY_BINDING_MISMATCH")
    if not _binding_matches(evidence.get("top_law"), top_ref):
        raise ValueError("VERIFICATION_TRUSTED_TOP_LAW_BINDING_MISMATCH")
    if not _binding_matches(evidence.get("common_policy_cover"), cover_ref):
        raise ValueError("VERIFICATION_TRUSTED_COVER_BINDING_MISMATCH")
    if not _binding_matches(evidence.get("independent_policy_replay"), replay_ref):
        raise ValueError("VERIFICATION_TRUSTED_REPLAY_BINDING_MISMATCH")

    if top.get("schema") != "PROJECT_BRAIN_SYNTHESIS_CERTIFIED_VISIBLE_SUPPORT_TOP_LAW_CELL_V1":
        raise ValueError("TRUSTED_TOP_LAW_SCHEMA_INVALID")
    conditional = top.get("conditional_top_law")
    if not isinstance(conditional, Mapping) or conditional.get("matched_quality") != 1:
        raise ValueError("TRUSTED_TOP_LAW_NOT_OBJECTIVE_CEILING")
    components = conditional.get("component_values")
    if not isinstance(components, Mapping):
        raise ValueError("TRUSTED_TOP_LAW_COMPONENTS_MISSING")
    for key in (
        "claim_to_source_fidelity",
        "uncertainty_and_disagreement_preservation",
        "audience_adaptation",
        "format_and_style_constraints",
        "compression_without_decision_relevant_loss",
        "required_claim_coverage",
    ):
        if components.get(key) != 1:
            raise ValueError("TRUSTED_TOP_LAW_COMPONENT_NOT_CEILING:" + key)
    if components.get("unsupported_material_claims") != 0:
        raise ValueError("TRUSTED_TOP_LAW_UNSUPPORTED_CLAIMS_NONZERO")

    if cover.get("schema") != "PROJECT_BRAIN_SYNTHESIS_COMMON_POLICY_COVER_V1":
        raise ValueError("TRUSTED_COVER_SCHEMA_INVALID")
    if not _binding_matches(cover.get("policy"), policy):
        raise ValueError("TRUSTED_COVER_POLICY_BINDING_MISMATCH")
    if not _binding_matches(cover.get("adequacy"), top_ref):
        raise ValueError("TRUSTED_COVER_TOP_LAW_BINDING_MISMATCH")
    result = cover.get("result")
    if not isinstance(result, Mapping) or result.get("type") != "COMMON_POLICY_CERTIFICATE":
        raise ValueError("TRUSTED_COVER_NOT_COMMON_POLICY")

    if replay.get("schema") != "PROJECT_BRAIN_SYNTHESIS_COMMON_POLICY_C2_INDEPENDENT_REPLAY_V1":
        raise ValueError("TRUSTED_REPLAY_SCHEMA_INVALID")
    if not str(replay.get("status") or "").startswith("INDEPENDENT_EXACT_BLOB_REPLAY_PASS"):
        raise ValueError("TRUSTED_REPLAY_NOT_PASS")
    carrier = replay.get("carrier")
    if not isinstance(carrier, Mapping) or carrier.get("provider") != "SPRITES":
        raise ValueError("TRUSTED_REPLAY_CARRIER_INVALID")
    exact = replay.get("exact_blobs")
    if not isinstance(exact, Mapping):
        raise ValueError("TRUSTED_REPLAY_EXACT_BLOBS_MISSING")
    for key in ("policy", "top_law", "common_policy_cover"):
        if not _binding_matches(exact.get(key), closure[key]):
            raise ValueError("TRUSTED_REPLAY_EXACT_BLOB_MISMATCH:" + key)
    replay_body = replay.get("replay")
    if not isinstance(replay_body, Mapping):
        raise ValueError("TRUSTED_REPLAY_BODY_MISSING")
    if replay_body.get("test_count") != 7 or replay_body.get("pass_count") != 7 or replay_body.get("fail_count") != 0:
        raise ValueError("TRUSTED_REPLAY_COUNTS_INVALID")
    return rows


def _authenticate_policy_adequacy(
    policy_id: str,
    condition: Mapping[str, Any],
    binding: Mapping[str, Any] | None,
) -> tuple[bool, dict[str, Any]]:
    if not isinstance(binding, Mapping):
        return False, {"policy_id": policy_id, "reason": "ADEQUACY_BINDING_MISSING"}
    try:
        condition_sha = _condition_sha256(condition)
        root = _trusted_root(policy_id, condition_sha, binding)
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

        if policy_id != "SYNTHESIS_CERTIFIED_VISIBLE_SUPPORT_POLICY_V1":
            raise ValueError("TRUSTED_ROOT_VALIDATOR_MISSING")
        closure_rows = _validate_registered_synthesis_root(adequacy, verification, root)
        return True, {
            "policy_id": policy_id,
            "condition_sha256": condition_sha,
            "adequacy_certificate_path": str(adequacy_path.relative_to(ROOT)),
            "adequacy_certificate_blob_sha": adequacy_blob,
            "independent_verification_path": str(verification_path.relative_to(ROOT)),
            "independent_verification_blob_sha": verification_blob,
            "trust_root_registered": True,
            "validated_evidence_closure": closure_rows,
        }
    except Exception as exc:
        return False, {"policy_id": policy_id, "reason": type(exc).__name__ + ":" + str(exc)}


def resolve_from_source_proof(
    source_text: str,
    *,
    source_id: str,
    claims: Sequence[Mapping[str, Any]],
    decision_basis: Sequence[str],
    policy_conditions: Mapping[str, Mapping[str, Any]],
    typed_context: Mapping[str, Any] | None = None,
    expected_typed_context_sha256: str | None = None,
    policy_adequacy_bindings: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    proof = verify_proof(
        source_text,
        source_id=source_id,
        claims=claims,
        typed_context=typed_context,
        expected_typed_context_sha256=expected_typed_context_sha256,
    )
    if proof.get("status") == "FAIL_CLOSED":
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "SOURCE_PROOF_FAIL_CLOSED", "source_proof": proof, "terminal_authority": False}

    proved = proof.get("proved_constraints") or []
    refinement = resolve_common_policy(
        decision_basis,
        policy_conditions,
        formal_source_constraints=proved,
        proposed_refinements=proved,
    )
    if refinement.get("status") == "FAIL_CLOSED":
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "SEMANTIC_REFINEMENT_FAIL_CLOSED", "source_proof": proof, "semantic_refinement": refinement, "terminal_authority": False}

    entailed = list(refinement.get("certified_common_policies", []))
    bindings = policy_adequacy_bindings if isinstance(policy_adequacy_bindings, Mapping) else {}
    certified: list[str] = []
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for pid in entailed:
        condition = policy_conditions.get(pid)
        if not isinstance(condition, Mapping):
            rejected.append({"policy_id": pid, "reason": "POLICY_CONDITION_MISSING"})
            continue
        ok, row = _authenticate_policy_adequacy(pid, condition, bindings.get(pid))
        if ok:
            certified.append(pid)
            accepted.append(row)
        else:
            rejected.append(row)

    status = (
        "COMMON_POLICY_CERTIFIED" if certified else
        "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED" if entailed else
        "UNRESOLVED"
    )
    return {
        "schema": SCHEMA,
        "status": status,
        "source_proof": proof,
        "semantic_refinement": refinement,
        "entailed_policy_conditions": entailed,
        "certified_common_policies": sorted(certified),
        "authenticated_policy_adequacy": sorted(accepted, key=lambda x: x["policy_id"]),
        "rejected_policy_adequacy_bindings": sorted(rejected, key=lambda x: x.get("policy_id", "")),
        "terminal_authority": False,
        "boundary": (
            "SOURCE_FACTS_ONLY_ENTAIL_DECLARED_POLICY_CONDITIONS;"
            "GENERIC_POLICY_ADEQUACY_REQUIRES_AN_EXACT_REGISTERED_TRUST_ROOT_AND_REVALIDATED_EVIDENCE_CLOSURE;"
            "UNREGISTERED_REPOSITORY_CERTIFICATE_PAIRS_CANNOT_SELF_PROMOTE"
        ),
    }
