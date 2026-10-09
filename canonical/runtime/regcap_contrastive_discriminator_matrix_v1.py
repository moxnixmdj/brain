"""Bounded CCoB/CCyB/TLAC contrastive discriminator matrix V1.

This authority authenticates a tiny source-backed outcome table for exactly three
named regulatory-capital rivals.  It does NOT claim these three concepts exhaust
all possible meanings of arbitrary language.

The matrix is useful only relative to a separately justified candidate set.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.https_source_fragment_projection_authority_v2 import (
    verify_projection_pack,
)
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap

SCHEMA = "PROJECT_BRAIN_REGCAP_CONTRASTIVE_DISCRIMINATOR_MATRIX_V1"
PACK_SCHEMA = "PROJECT_BRAIN_REGCAP_CONTRASTIVE_DISCRIMINATOR_SOURCE_PACK_V1"
PACK_PATH = "canonical/evidence/REGCAP_CONTRASTIVE_DISCRIMINATOR_SOURCE_PACK_V1.json"
PACK_GIT_BLOB_SHA = "3b8d85d5e25baa907846617ad704414e891b682b"
SCOPE_ID = "REGCAP_CCOB_CCYB_TLAC_CONTRASTIVE_MATRIX_V1"

DOMAIN = (regcap.CCOB, regcap.CCYB, regcap.TLAC)

OBSERVATIONS = {
    "FRAMEWORK_CLASS": {
        regcap.CCOB: "BASEL_CAPITAL_BUFFER_ABOVE_REGULATORY_MINIMUM",
        regcap.CCYB: "BASEL_CAPITAL_BUFFER_ABOVE_REGULATORY_MINIMUM",
        regcap.TLAC: "SEPARATE_MINIMUM_TLAC_REQUIREMENT",
    },
    "RELEASABILITY_CLASS": {
        regcap.CCOB: "BASEL_BUFFER_NOT_DESIGNATED_RELEASABLE",
        regcap.CCYB: "BASEL_DESIGNATED_RELEASABLE_BUFFER",
        regcap.TLAC: "OUTSIDE_BASEL_CAPITAL_BUFFER_FRAMEWORK",
    },
    "FUNCTIONAL_SIGNATURE_CLASS": {
        regcap.CCOB: "DRAWDOWN_AS_LOSSES_ARE_INCURRED",
        regcap.CCYB: "RELEASE_WHEN_SYSTEM_WIDE_RISK_CRYSTALLISES_OR_DISSIPATES",
        regcap.TLAC: "G_SIB_LOSS_ABSORPTION_RECAPITALISATION_IN_RESOLUTION",
    },
    "STRUCTURAL_SIGNATURE_CLASS": {
        regcap.CCOB: "TWO_POINT_FIVE_PERCENT_CET1_ABOVE_REGULATORY_MINIMUM",
        regcap.CCYB: "EXTENDS_CCOB_AND_MET_WITH_CET1",
        regcap.TLAC: "SEPARATE_MINIMUM_TLAC_REQUIREMENT",
    },
}

SOURCE_REQUIREMENTS = {
    "FRAMEWORK_CLASS": {
        "BIS_CAD20_2026_COUNTERCYCLICAL_CAPITAL_BUFFERS": (
            "BASEL_BUFFER_FRAMEWORK_MEMBERS",
            "BASEL_BUFFERS_ABOVE_MINIMUM_CET1",
        ),
        "FSB_TLAC_STANDARD_2015_11_09": (
            "TLAC_SEPARATE_MINIMUM_REQUIREMENT",
        ),
    },
    "RELEASABILITY_CLASS": {
        "BIS_CAD20_2026_COUNTERCYCLICAL_CAPITAL_BUFFERS": (
            "BASEL_BUFFER_FRAMEWORK_MEMBERS",
            "CCYB_ONLY_DESIGNATED_RELEASABLE_BUFFER",
        ),
        "FSB_TLAC_STANDARD_2015_11_09": (
            "TLAC_SEPARATE_MINIMUM_REQUIREMENT",
        ),
    },
    "FUNCTIONAL_SIGNATURE_CLASS": {
        "BIS_BASEL_RBC30_2023_11_08_EFFECTIVE_2027_01_01": (
            "CCOB_LOSS_DRAWDOWN",
            "CCYB_RELEASE",
        ),
        "FSB_TLAC_2015_11_09": (
            "TLAC_LOSS_RECAP_RESOLUTION",
        ),
    },
    "STRUCTURAL_SIGNATURE_CLASS": {
        "BIS_BASEL_RBC30_2023_11_08_EFFECTIVE_2027_01_01": (
            "CCOB_CET1_ABOVE_MINIMUM",
            "CCYB_CET1",
            "CCYB_EXTENDS_CCOB",
        ),
        "FSB_TLAC_STANDARD_2015_11_09": (
            "TLAC_SEPARATE_MINIMUM_REQUIREMENT",
        ),
    },
}

ROOT = Path(__file__).resolve().parents[2]


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _git_blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "source_authority": False,
        "semantic_truth_authority": False,
        "candidate_universe_complete": False,
        "open_world_ontology_complete": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def load_pack(*, repo_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve() if repo_root is not None else ROOT
    path = (root / PACK_PATH).resolve(strict=True)
    path.relative_to(root)
    if not path.is_file() or path.is_symlink():
        raise ValueError("PACK_FILE_INVALID")
    raw = path.read_bytes()
    blob = _git_blob(raw)
    if blob != PACK_GIT_BLOB_SHA:
        raise ValueError("PACK_GIT_BLOB_DRIFT:" + blob)
    doc = json.loads(raw.decode("utf-8"))
    if not isinstance(doc, Mapping) or doc.get("schema") != PACK_SCHEMA:
        raise ValueError("PACK_SCHEMA_INVALID")
    if doc.get("scope_id") != SCOPE_ID:
        raise ValueError("PACK_SCOPE_INVALID")
    sources = doc.get("sources")
    if not isinstance(sources, Sequence) or isinstance(sources, (str, bytes)):
        raise ValueError("PACK_SOURCES_INVALID")
    by_id = {}
    for raw_source in sources:
        if not isinstance(raw_source, Mapping):
            raise ValueError("PACK_SOURCE_NOT_OBJECT")
        sid = str(raw_source.get("source_id") or "").strip()
        if not sid or sid in by_id:
            raise ValueError("PACK_SOURCE_ID_INVALID_OR_DUPLICATE")
        by_id[sid] = dict(raw_source)
    required = set().union(*[set(x) for x in SOURCE_REQUIREMENTS.values()])
    if not required.issubset(by_id):
        raise ValueError("PACK_REQUIRED_SOURCE_MISSING")
    return {
        "pack": dict(doc),
        "sources_by_id": by_id,
        "pack_git_blob_sha": blob,
    }


def verify_matrix(
    *,
    repo_root: str | Path | None = None,
    projection_verifier=verify_projection_pack,
) -> dict[str, Any]:
    try:
        checked = load_pack(repo_root=repo_root)
        source_results = {}
        for source_id, source_pack in checked["sources_by_id"].items():
            result = projection_verifier(dict(source_pack))
            if not isinstance(result, Mapping) or result.get("pass") is not True:
                return _base(
                    "FAIL_CLOSED",
                    reason="PINNED_SOURCE_FRAGMENT_AUTHORITY_FAILED:" + source_id,
                    source_result=result,
                )
            source_results[source_id] = dict(result)

        for observation_id, requirements in SOURCE_REQUIREMENTS.items():
            for source_id, fragment_ids in requirements.items():
                authenticated = set(
                    source_results[source_id]
                    .get("receipt", {})
                    .get("fragment_ids", [])
                )
                missing = set(fragment_ids) - authenticated
                if missing:
                    return _base(
                        "FAIL_CLOSED",
                        reason="REQUIRED_FRAGMENT_NOT_AUTHENTICATED:"
                        + observation_id
                        + ":"
                        + source_id
                        + ":"
                        + ",".join(sorted(missing)),
                    )

        observations = []
        for observation_id in sorted(OBSERVATIONS):
            outcomes = dict(OBSERVATIONS[observation_id])
            if set(outcomes) != set(DOMAIN):
                return _base(
                    "FAIL_CLOSED",
                    reason="MATRIX_DOMAIN_COVERAGE_INCOMPLETE:" + observation_id,
                )
            observations.append({
                "observation_id": observation_id,
                "outcome_map_complete_relative_to_matrix_domain": True,
                "outcomes": outcomes,
                "source_requirements": {
                    sid: list(ids)
                    for sid, ids in SOURCE_REQUIREMENTS[observation_id].items()
                },
            })

        matrix_core = {
            "scope_id": SCOPE_ID,
            "candidate_domain": list(DOMAIN),
            "observations": observations,
            "pack_git_blob_sha": checked["pack_git_blob_sha"],
            "source_receipt_sha256": {
                sid: result["receipt"]["receipt_sha256"]
                for sid, result in source_results.items()
            },
        }
        return _base(
            "PASS__REGCAP_CONTRASTIVE_DISCRIMINATOR_MATRIX_AUTHENTICATED",
            passed=True,
            source_authority=True,
            semantic_truth_authority=True,
            candidate_domain=list(DOMAIN),
            outcome_maps_complete_relative_to_matrix_domain=True,
            candidate_universe_complete=False,
            observations=observations,
            matrix_sha256=_sha(matrix_core),
            source_results=source_results,
            theorem_boundary=(
                "COMPLETE_ONLY_FOR_THE_FOUR_DECLARED_OBSERVATIONS_OVER_THE_THREE_"
                "NAMED_MATRIX_CONCEPTS__DOES_NOT_PROVE_THOSE_CONCEPTS_EXHAUST_"
                "ARBITRARY_LANGUAGE_MEANINGS_OR_THE_OPEN_WORLD_REGCAP_ONTOLOGY"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))


def relative_one_step_discriminators(
    candidate_concept_ids: Sequence[str],
    *,
    repo_root: str | Path | None = None,
    projection_verifier=verify_projection_pack,
) -> dict[str, Any]:
    """Find one-step separators relative to a declared subset only.

    This function never upgrades the declared subset to a complete hypothesis
    universe.  It answers only whether an authenticated matrix observation has a
    unique outcome for every concept in the supplied subset.
    """
    matrix = verify_matrix(
        repo_root=repo_root,
        projection_verifier=projection_verifier,
    )
    if matrix.get("pass") is not True:
        return matrix

    if (
        not isinstance(candidate_concept_ids, Sequence)
        or isinstance(candidate_concept_ids, (str, bytes))
        or not candidate_concept_ids
    ):
        return _base("FAIL_CLOSED", reason="CANDIDATE_IDS_REQUIRED")
    candidates = [str(x) for x in candidate_concept_ids]
    if len(candidates) != len(set(candidates)):
        return _base("FAIL_CLOSED", reason="CANDIDATE_IDS_DUPLICATE")
    if not set(candidates).issubset(set(DOMAIN)):
        return _base("FAIL_CLOSED", reason="CANDIDATE_OUTSIDE_MATRIX_DOMAIN")

    separators = []
    for row in matrix["observations"]:
        outcomes = {cid: row["outcomes"][cid] for cid in candidates}
        if len(set(outcomes.values())) == len(candidates):
            separators.append({
                "observation_id": row["observation_id"],
                "outcomes": outcomes,
            })

    return _base(
        "PASS__RELATIVE_ONE_STEP_DISCRIMINATORS_COMPUTED",
        passed=True,
        source_authority=True,
        semantic_truth_authority=True,
        declared_candidate_ids=candidates,
        candidate_universe_complete=False,
        one_step_discriminators=separators,
        matrix_sha256=matrix["matrix_sha256"],
        relative_only=True,
        theorem_boundary=(
            "SEPARATION_IS_ONLY_RELATIVE_TO_CALLER_DECLARED_CANDIDATES__"
            "NO_HYPOTHESIS_SET_COMPLETENESS_OR_GLOBAL_MAPPING_AUTHORITY"
        ),
    )
