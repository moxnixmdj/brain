"""Bounded TLAC/MREL identity discriminator V1.

This module closes one exact pairwise ambiguity only:
    {REGCAP::TLAC, REGCAP::MREL}

It authenticates two governing-framework marker bundles from primary sources:
- MREL: the BRRD minimum requirement for own funds and eligible liabilities is
  determined by the resolution authority under Article 45c.
- TLAC: the FSB Minimum External TLAC standard applies to G-SIBs.

The pair is complete only by construction for SCOPE_ID below. No open-world
regulatory-capital completeness, TLAC/MREL global disjointness, policy adequacy,
execution, acceptance, promotion, or terminal authority is granted.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from canonical.runtime.https_source_fragment_projection_authority_v2 import (
    verify_projection_pack,
)

SCHEMA = "PROJECT_BRAIN_TLAC_MREL_IDENTITY_DISCRIMINATOR_V1"
PACK_SCHEMA = "PROJECT_BRAIN_TLAC_MREL_IDENTITY_DISCRIMINATOR_SOURCE_PACK_V1"
PACK_PATH = "canonical/evidence/TLAC_MREL_IDENTITY_DISCRIMINATOR_SOURCE_PACK_V1.json"
PACK_GIT_BLOB_SHA = "5fee8efbd4ca57013400bfbc53051df292057cd4"
SCOPE_ID = "REGCAP_TLAC_MREL_BOUNDED_RIVAL_TASK_V1"

TLAC = "REGCAP::TLAC"
MREL = "REGCAP::MREL"
DOMAIN = (TLAC, MREL)

OBSERVATION_ID = "GOVERNING_REQUIREMENT_CLASS"
OUTCOMES = {
    TLAC: "FSB_MINIMUM_EXTERNAL_TLAC_FOR_GSIBS",
    MREL: "EU_BRRD_ARTICLE_45C_RESOLUTION_AUTHORITY_DETERMINED_MREL",
}

ROOT = Path(__file__).resolve().parents[2]
_WS = re.compile(r"\s+")

_MREL_NAME = re.compile(
    r"\bminimum\s+requirement\s+for\s+own\s+funds\s+and\s+eligible\s+liabilities\b",
    re.I,
)
_MREL_SETTER = re.compile(
    r"\b(?:is|shall\s+be|was|must\s+be)\s+determined\s+by\s+(?:the\s+)?resolution\s+authority\b",
    re.I,
)
_MREL_ARTICLE = re.compile(r"\barticle\s+45c\b", re.I)

_TLAC_MIN = re.compile(r"\bminimum\s+external\s+tlac\b", re.I)
_TLAC_GSIB = re.compile(
    r"\b(?:g[-\s]?sibs?|global\s+systemically\s+important\s+banks?)\b",
    re.I,
)
_TLAC_STANDARD = re.compile(r"\b(?:fsb\s+)?tlac\s+standard\b|\bfsb\s+standard\b", re.I)

_NEGATION = re.compile(
    r"\b(?:not|never|no)\b.{0,48}\b(?:determined|minimum\s+external\s+tlac|tlac\s+standard)\b",
    re.I,
)


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    if isinstance(value, str):
        return sha256(value.encode("utf-8")).hexdigest()
    return sha256(_canon(value)).hexdigest()


def _git_blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_truth_authority": False,
        "relative_selection_authority": False,
        "candidate_universe_complete": False,
        "open_world_ontology_complete": False,
        "concept_equivalence_authority": False,
        "concept_disjointness_authority": False,
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
    if not isinstance(sources, list) or len(sources) != 2:
        raise ValueError("PACK_SOURCE_COUNT_INVALID")
    by_id = {}
    for row in sources:
        if not isinstance(row, Mapping):
            raise ValueError("PACK_SOURCE_NOT_OBJECT")
        sid = str(row.get("source_id") or "").strip()
        if not sid or sid in by_id:
            raise ValueError("PACK_SOURCE_ID_INVALID_OR_DUPLICATE")
        by_id[sid] = dict(row)
    required = {
        "EBA_MREL_CASE_BY_CASE_2015",
        "FSB_TLAC_STANDARD_2015",
    }
    if set(by_id) != required:
        raise ValueError("PACK_SOURCE_SET_INVALID")
    return {
        "pack": dict(doc),
        "sources_by_id": by_id,
        "pack_git_blob_sha": blob,
    }


def verify_authority(
    *,
    repo_root: str | Path | None = None,
    projection_verifier=verify_projection_pack,
) -> dict[str, Any]:
    try:
        checked = load_pack(repo_root=repo_root)
        source_results = {}
        required_fragments = {
            "EURLEX_BRRD_2026_MREL_ARTICLE_45C": {
                "MREL_NOT_FIXED_FIGURE",
                "MREL_CASE_BY_CASE_RESOLUTION_AUTHORITY",
            },
            "FSB_TLAC_STANDARD_2015": {
                "TLAC_FSB_GSIB_SCOPE",
                "TLAC_MINIMUM_EXTERNAL_REQUIREMENT",
            },
        }
        for sid, pack in checked["sources_by_id"].items():
            result = projection_verifier(dict(pack))
            if not isinstance(result, Mapping) or result.get("pass") is not True:
                return _base(
                    "FAIL_CLOSED",
                    reason="PINNED_SOURCE_FRAGMENT_AUTHORITY_FAILED:" + sid,
                    source_result=result,
                )
            authenticated = set(
                str(x)
                for x in result.get("receipt", {}).get("fragment_ids", [])
            )
            missing = required_fragments[sid] - authenticated
            if missing:
                return _base(
                    "FAIL_CLOSED",
                    reason="REQUIRED_FRAGMENT_NOT_AUTHENTICATED:"
                    + sid
                    + ":"
                    + ",".join(sorted(missing)),
                )
            source_results[sid] = dict(result)

        material = {
            "scope_id": SCOPE_ID,
            "candidate_domain": list(DOMAIN),
            "observation_id": OBSERVATION_ID,
            "outcomes": dict(OUTCOMES),
            "pack_git_blob_sha": checked["pack_git_blob_sha"],
            "source_receipt_sha256": {
                sid: row["receipt"]["receipt_sha256"]
                for sid, row in source_results.items()
            },
        }
        return _base(
            "PASS__TLAC_MREL_IDENTITY_DISCRIMINATOR_AUTHENTICATED",
            passed=True,
            semantic_truth_authority=True,
            candidate_domain=list(DOMAIN),
            candidate_universe_complete=True,
            candidate_universe_complete_only_for_scope_id=SCOPE_ID,
            observation_id=OBSERVATION_ID,
            outcomes=dict(OUTCOMES),
            source_results=source_results,
            authority_sha256=_sha(material),
            boundary=(
                "PAIR_COMPLETENESS_ONLY_BY_DECLARED_TASK_SCOPE__"
                "NO_OPEN_WORLD_REGCAP_COMPLETENESS__"
                "NO_TLAC_MREL_GLOBAL_DISJOINTNESS_OR_EQUIVALENCE"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))


def _sentences(text: str):
    start = 0
    for match in re.finditer(r"[.!?](?:\s+|$)", text):
        end = match.start() + 1
        raw = text[start:end].strip()
        if raw:
            yield raw
        start = match.end()
    tail = text[start:].strip()
    if tail:
        yield tail


def compile_context(source_text: str, *, source_id: str) -> dict[str, Any]:
    try:
        if not isinstance(source_text, str) or not source_text.strip():
            return _base("FAIL_CLOSED", reason="SOURCE_TEXT_REQUIRED")
        source_id = str(source_id or "").strip()
        if not source_id:
            return _base("FAIL_CLOSED", reason="SOURCE_ID_REQUIRED")

        matches = []
        for sentence in _sentences(source_text):
            if len(sentence) > 1200:
                continue
            if _NEGATION.search(sentence):
                continue

            mrel = bool(
                _MREL_NAME.search(sentence)
                and _MREL_SETTER.search(sentence)
            )
            if mrel and _MREL_ARTICLE.search(sentence):
                matches.append({
                    "candidate_id": MREL,
                    "outcome": OUTCOMES[MREL],
                    "sentence": sentence,
                    "evidence": [
                        "MREL_OFFICIAL_NAME",
                        "MREL_RESOLUTION_AUTHORITY_SETTER",
                        "MREL_ARTICLE_45C",
                    ],
                })

            tlac = bool(
                _TLAC_MIN.search(sentence)
                and _TLAC_GSIB.search(sentence)
                and _TLAC_STANDARD.search(sentence)
            )
            if tlac:
                matches.append({
                    "candidate_id": TLAC,
                    "outcome": OUTCOMES[TLAC],
                    "sentence": sentence,
                    "evidence": [
                        "TLAC_MINIMUM_EXTERNAL",
                        "TLAC_GSIB_SCOPE",
                        "TLAC_STANDARD",
                    ],
                })

        candidate_ids = sorted({x["candidate_id"] for x in matches})
        if len(candidate_ids) > 1:
            return _base(
                "FAIL_CLOSED",
                reason="CONFLICTING_TLAC_MREL_CONTEXT_SIGNATURES",
                matches=matches,
            )
        if not matches:
            return _base(
                "OPEN__NO_BOUND_TLAC_MREL_IDENTITY_DISCRIMINATOR",
                source_id=source_id,
                source_text_sha256=_sha(source_text),
            )

        selected = candidate_ids[0]
        return _base(
            "PASS__BOUND_TLAC_MREL_CONTEXT_SIGNATURE",
            passed=True,
            semantic_truth_authority=True,
            relative_selection_authority=False,
            selected_candidate_hint=selected,
            observed_outcome=OUTCOMES[selected],
            matches=matches,
            source_id=source_id,
            source_text_sha256=_sha(source_text),
            boundary=(
                "EXACT_POSITIVE_SAME_SENTENCE_GOVERNING_FRAMEWORK_MARKERS_ONLY__"
                "CALLER_CANNOT_PROMOTE_HINT_WITHOUT_AUTHORITY_REPLAY"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))


def resolve_relative(
    source_text: str,
    *,
    source_id: str,
    candidate_concept_ids: Sequence[str],
    repo_root: str | Path | None = None,
    projection_verifier=verify_projection_pack,
) -> dict[str, Any]:
    compiled = compile_context(source_text, source_id=source_id)
    if compiled.get("pass") is not True:
        return compiled

    if (
        not isinstance(candidate_concept_ids, Sequence)
        or isinstance(candidate_concept_ids, (str, bytes))
    ):
        return _base("FAIL_CLOSED", reason="CANDIDATE_IDS_REQUIRED")
    candidates = [str(x) for x in candidate_concept_ids]
    if sorted(candidates) != sorted(DOMAIN):
        return _base(
            "FAIL_CLOSED",
            reason="CANDIDATE_SET_MUST_EQUAL_BOUND_TLAC_MREL_PAIR",
            supplied_candidate_ids=sorted(candidates),
        )

    authority = verify_authority(
        repo_root=repo_root,
        projection_verifier=projection_verifier,
    )
    if authority.get("pass") is not True:
        return _base(
            "FAIL_CLOSED",
            reason="TLAC_MREL_DISCRIMINATOR_AUTHORITY_FAILED",
            authority_result=authority,
        )

    selected = str(compiled["selected_candidate_hint"])
    outcome = str(compiled["observed_outcome"])
    if authority.get("outcomes", {}).get(selected) != outcome:
        return _base(
            "FAIL_CLOSED",
            reason="CONTEXT_OUTCOME_NOT_BOUND_TO_AUTHENTICATED_MATRIX",
        )

    return _base(
        "PASS__UNIQUE_TLAC_MREL_CONCEPT_IN_BOUND_PAIR_SCOPE",
        passed=True,
        semantic_truth_authority=True,
        relative_selection_authority=True,
        candidate_universe_complete=True,
        selected_concept_id=selected,
        surviving_candidate_ids=[selected],
        declared_candidate_ids=list(DOMAIN),
        observation_id=OBSERVATION_ID,
        observed_outcome=outcome,
        authority_sha256=authority.get("authority_sha256"),
        source_id=source_id,
        source_text_sha256=_sha(source_text),
        global_semantic_identity_authority=False,
        boundary=(
            "UNIQUE_ONLY_INSIDE_AUTHENTICATED_TLAC_MREL_PAIR_TASK_SCOPE__"
            "NO_OPEN_WORLD_OR_GLOBAL_CONCEPT_IDENTITY__NO_TERMINAL_AUTHORITY"
        ),
    )
