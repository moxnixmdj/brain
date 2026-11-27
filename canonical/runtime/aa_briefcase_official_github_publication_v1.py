from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_OFFICIAL_GITHUB_PUBLICATION_V1"
STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
PREDICATE_TYPE = "https://project-brain.local/attestation/aa-briefcase-current-epoch-noninferiority/v2"
EXPECTED_BENCHMARK = "AA-Briefcase v1.1"
EXPECTED_MODEL = "Claude Opus 5.5 (Max, Default Fallback)"
EXPECTED_TASK_COUNT = 91
EXPECTED_OWNER_LOGIN = "ArtificialAnalysis"
EXPECTED_OWNER_TYPE = "Organization"
EXPECTED_GRADING_PROTOCOL_BLOB_SHA = "5c77f294e09d4933e3a3175c46af225b414f4702"
EXPECTED_OWNER_ANCHOR_BLOB_SHA = "672877a30053a33e3589fde5214e2c61f9ea5e74"


class OfficialPublicationError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _hex(value: Any, n: int, label: str) -> str:
    if not isinstance(value, str) or len(value) != n or any(c not in "0123456789abcdef" for c in value):
        raise OfficialPublicationError(label + "_INVALID")
    return value


def git_blob_sha1(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


def verify_official_github_publication(
    current_target: Mapping[str, Any],
    publication: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(current_target, Mapping):
        raise OfficialPublicationError("TARGET_INVALID")
    target = current_target.get("target")
    epoch = current_target.get("epoch_rule")
    if not isinstance(target, Mapping) or not isinstance(epoch, Mapping):
        raise OfficialPublicationError("TARGET_BINDING_MISSING")
    if target.get("benchmark") != EXPECTED_BENCHMARK:
        raise OfficialPublicationError("TARGET_BENCHMARK_MISMATCH")
    if target.get("model") != EXPECTED_MODEL:
        raise OfficialPublicationError("TARGET_MODEL_MISMATCH")
    if epoch.get("current_epoch_minimum_opus55_target_elo") != target.get("current_owner_elo"):
        raise OfficialPublicationError("TARGET_REFERENCE_DRIFT")

    if not isinstance(publication, Mapping):
        raise OfficialPublicationError("PUBLICATION_RECEIPT_INVALID")
    if publication.get("retrieval_method") != "GITHUB_CONNECTOR_FETCH_FILE_AT_EXACT_COMMIT":
        raise OfficialPublicationError("RETRIEVAL_METHOD_INVALID")
    if publication.get("owner_identity_anchor_git_blob_sha") != EXPECTED_OWNER_ANCHOR_BLOB_SHA:
        raise OfficialPublicationError("OWNER_IDENTITY_ANCHOR_DRIFT")

    repository_full_name = publication.get("repository_full_name")
    owner_login = publication.get("owner_login")
    owner_type = publication.get("owner_type")
    visibility = publication.get("visibility")
    if not isinstance(repository_full_name, str) or not repository_full_name.startswith(EXPECTED_OWNER_LOGIN + "/"):
        raise OfficialPublicationError("REPOSITORY_OWNER_NAMESPACE_MISMATCH")
    if owner_login != EXPECTED_OWNER_LOGIN:
        raise OfficialPublicationError("OWNER_LOGIN_MISMATCH")
    if owner_type != EXPECTED_OWNER_TYPE:
        raise OfficialPublicationError("OWNER_TYPE_MISMATCH")
    if visibility != "public":
        raise OfficialPublicationError("PUBLICATION_NOT_PUBLIC")

    commit_sha = _hex(publication.get("commit_sha"), 40, "COMMIT_SHA")
    git_blob_sha = _hex(publication.get("git_blob_sha"), 40, "GIT_BLOB_SHA")
    path = publication.get("path")
    if not isinstance(path, str) or not path.endswith(".json") or path.startswith("/"):
        raise OfficialPublicationError("PUBLICATION_PATH_INVALID")

    file_content_utf8 = publication.get("file_content_utf8")
    if not isinstance(file_content_utf8, str) or not file_content_utf8:
        raise OfficialPublicationError("PUBLICATION_CONTENT_INVALID")
    content_bytes = file_content_utf8.encode("utf-8")
    if git_blob_sha1(content_bytes) != git_blob_sha:
        raise OfficialPublicationError("GIT_BLOB_SHA_MISMATCH")

    try:
        statement = json.loads(file_content_utf8)
    except json.JSONDecodeError as exc:
        raise OfficialPublicationError("PUBLICATION_JSON_INVALID") from exc
    if not isinstance(statement, Mapping):
        raise OfficialPublicationError("STATEMENT_INVALID")
    if statement.get("_type") != STATEMENT_TYPE:
        raise OfficialPublicationError("STATEMENT_TYPE_MISMATCH")
    if statement.get("predicateType") != PREDICATE_TYPE:
        raise OfficialPublicationError("PREDICATE_TYPE_MISMATCH")

    subjects = statement.get("subject")
    if not isinstance(subjects, list) or len(subjects) != 1 or not isinstance(subjects[0], Mapping):
        raise OfficialPublicationError("EXACTLY_ONE_SUBJECT_REQUIRED")
    digest = subjects[0].get("digest")
    if not isinstance(digest, Mapping):
        raise OfficialPublicationError("SUBJECT_DIGEST_INVALID")
    subject_sha = _hex(digest.get("sha256"), 64, "SUBJECT_SHA256")

    predicate = statement.get("predicate")
    if not isinstance(predicate, Mapping):
        raise OfficialPublicationError("PREDICATE_INVALID")
    if predicate.get("benchmark") != EXPECTED_BENCHMARK:
        raise OfficialPublicationError("PREDICATE_BENCHMARK_MISMATCH")
    if predicate.get("target_model") != EXPECTED_MODEL:
        raise OfficialPublicationError("PREDICATE_TARGET_MODEL_MISMATCH")
    if predicate.get("target_observed_date") != target.get("observed_date"):
        raise OfficialPublicationError("PREDICATE_EPOCH_MISMATCH")
    if predicate.get("grading_protocol_manifest_git_blob_sha") != EXPECTED_GRADING_PROTOCOL_BLOB_SHA:
        raise OfficialPublicationError("GRADING_PROTOCOL_DRIFT")
    if predicate.get("task_count") != EXPECTED_TASK_COUNT:
        raise OfficialPublicationError("TASK_COUNT_MISMATCH")
    if predicate.get("complete_current_scored_private_scope_used") is not True:
        raise OfficialPublicationError("PRIVATE_SCOPE_NOT_COMPLETE")
    if predicate.get("all_load_bearing_grading_relations_included") is not True:
        raise OfficialPublicationError("GRADING_RELATION_SCOPE_NOT_COMPLETE")
    if predicate.get("brain_weakly_dominates_current_opus55") is not True:
        raise OfficialPublicationError("NONINFERIORITY_NOT_ATTESTED")
    if predicate.get("official_owner_elo_claimed") is not False:
        raise OfficialPublicationError("DIRECT_PUBLICATION_MUST_NOT_CLAIM_OFFICIAL_ELO")
    if predicate.get("historical_1822_epoch_rewritten") is not False:
        raise OfficialPublicationError("HISTORICAL_EPOCH_REWRITE_FORBIDDEN")

    material = {
        "schema": SCHEMA,
        "status": "PASS_OFFICIAL_GITHUB_PUBLICATION",
        "repository_full_name": repository_full_name,
        "commit_sha": commit_sha,
        "git_blob_sha": git_blob_sha,
        "path": path,
        "subject_sha256": subject_sha,
        "statement_sha256": _sha256_bytes(content_bytes),
        "target_observed_date": target["observed_date"],
        "current_owner_reference_elo_context_only": target["current_owner_elo"],
        "scope_complete_current_epoch_noninferiority": True,
        "signature_required": False,
        "private_benchmark_content_required": False,
        "numeric_elo_reconstruction_required": False,
        "official_owner_elo_claimed": False,
        "historical_1822_epoch_rewritten": False,
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
    }
    return {
        **material,
        "verdict_sha256": _sha256_bytes(_canon(material)),
    }
