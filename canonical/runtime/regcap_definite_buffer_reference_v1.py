"""Bounded definite-description reference for regulatory-capital buffers.

V1 resolves only the exact reference form "the buffer" and only when, within the
current sentence prefix plus at most one preceding sentence, there is exactly one
distinct authenticated buffer concept antecedent among CCoB and CCyB.

Multiple mentions of the same concept are fine. Mentions of both CCoB and CCyB
preserve ambiguity. No nearest-mention heuristic is allowed.

The result is occurrence-local reference identity only, never a global alias
"buffer = concept".
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from canonical.runtime import regcap_bounded_rival_registry_authority_v1 as registry
from canonical.runtime import regcap_necessary_property_authority_v1 as regcap

SCHEMA = "PROJECT_BRAIN_REGCAP_DEFINITE_BUFFER_REFERENCE_V1"
REFERENCE_SURFACE = "the buffer"

EXPECTED_SURFACES = {
    regcap.CCOB: {"capital conservation buffer", "ccob"},
    regcap.CCYB: {"countercyclical capital buffer", "ccyb"},
}

_WORD = re.compile(r"[A-Za-z0-9_]")


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "reference_identity_authority": False,
        "semantic_truth_authority": False,
        "global_alias_authority": False,
        "candidate_universe_complete": False,
        "open_world_coreference_complete": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _sha(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _context_start(text: str, reference_start: int) -> int:
    prior = text[:reference_start]
    last = max(prior.rfind("."), prior.rfind("!"), prior.rfind("?"))
    if last < 0:
        return 0

    before_current = prior[:last]
    previous = max(
        before_current.rfind("."),
        before_current.rfind("!"),
        before_current.rfind("?"),
    )
    return 0 if previous < 0 else previous + 1


def _surface_pattern(surface: str) -> re.Pattern[str]:
    parts = [re.escape(x) for x in surface.split()]
    body = r"\s+".join(parts)
    return re.compile(r"(?<![A-Za-z0-9_])" + body + r"(?![A-Za-z0-9_])", re.I)


def _registry_surface_check(
    *,
    repo_root: Any,
    projection_verifier: Any,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]:
    request = {
        "schema": registry.REQUEST_SCHEMA,
        "registry_id": registry.REGISTRY_ID,
        "scope_id": registry.SCOPE_ID,
    }
    authority = registry.verify_authority_request(
        request,
        repo_root=repo_root,
        projection_verifier=projection_verifier,
    )
    if not isinstance(authority, Mapping) or authority.get("pass") is not True:
        return None, dict(authority or {}), "REGCAP_REGISTRY_AUTHORITY_FAILED"

    checked = registry.load_registry(repo_root=repo_root)
    rows = {
        str(row.get("concept_id") or ""): row
        for row in checked["normalized_registry"].get("concepts", [])
        if isinstance(row, Mapping)
    }
    for concept_id, expected in EXPECTED_SURFACES.items():
        row = rows.get(concept_id)
        if not isinstance(row, Mapping):
            return None, dict(authority), "BUFFER_CONCEPT_MISSING_FROM_REGISTRY:" + concept_id
        observed = {
            str(x).casefold()
            for x in (row.get("surfaces") or [])
            if isinstance(x, str)
        }
        if not expected.issubset(observed):
            return None, dict(authority), "BUFFER_SURFACE_SET_MISMATCH:" + concept_id

    return checked, dict(authority), None


def resolve_reference(
    source_text: str,
    *,
    source_id: str,
    start: int,
    end: int,
    repo_root: Any = None,
    projection_verifier=registry.matrix.verify_projection_pack,
) -> dict[str, Any]:
    try:
        if not isinstance(source_text, str) or not source_text:
            return _base("FAIL_CLOSED", reason="SOURCE_TEXT_REQUIRED")
        if not isinstance(source_id, str) or not source_id.strip():
            return _base("FAIL_CLOSED", reason="SOURCE_ID_REQUIRED")
        if (
            isinstance(start, bool)
            or not isinstance(start, int)
            or isinstance(end, bool)
            or not isinstance(end, int)
            or start < 0
            or end <= start
            or end > len(source_text)
        ):
            return _base("FAIL_CLOSED", reason="REFERENCE_SPAN_INVALID")
        if " ".join(source_text[start:end].split()).casefold() != REFERENCE_SURFACE:
            return _base(
                "UNRESOLVED__REFERENCE_FORM_OUTSIDE_BOUND_SCOPE",
                reference_span=[start, end],
                reference_surface=source_text[start:end],
            )

        checked, authority, error = _registry_surface_check(
            repo_root=repo_root,
            projection_verifier=projection_verifier,
        )
        if error is not None or checked is None:
            return _base(
                "FAIL_CLOSED",
                reason=str(error),
                registry_authority=authority or {},
            )

        ctx_start = _context_start(source_text, start)
        prior_text = source_text[ctx_start:start]
        mentions: list[dict[str, Any]] = []

        for concept_id, surfaces in EXPECTED_SURFACES.items():
            for surface in sorted(surfaces, key=lambda x: (-len(x), x)):
                pattern = _surface_pattern(surface)
                for match in pattern.finditer(prior_text):
                    mentions.append({
                        "concept_id": concept_id,
                        "surface": match.group(0),
                        "span": [
                            ctx_start + match.start(),
                            ctx_start + match.end(),
                        ],
                    })

        concept_ids = sorted({row["concept_id"] for row in mentions})
        common = {
            "source_id": source_id.strip(),
            "source_text_sha256": sha256(source_text.encode("utf-8")).hexdigest(),
            "reference_span": [start, end],
            "reference_surface": source_text[start:end],
            "context_span": [ctx_start, start],
            "candidate_mentions": sorted(
                mentions,
                key=lambda x: (x["span"][0], x["span"][1], x["concept_id"]),
            ),
            "candidate_concept_ids": concept_ids,
            "registry_scope_id": registry.SCOPE_ID,
            "registry_authority_receipt_sha256": authority.get("receipt_sha256"),
            "candidate_universe_complete": False,
            "open_world_coreference_complete": False,
        }

        if not concept_ids:
            return _base(
                "UNRESOLVED__NO_AUTHENTICATED_PRIOR_BUFFER_ANTECEDENT",
                **common,
            )
        if len(concept_ids) > 1:
            return _base(
                "UNRESOLVED__MULTIPLE_AUTHENTICATED_BUFFER_ANTECEDENTS",
                ambiguity_preserved=True,
                **common,
            )

        selected = concept_ids[0]
        material = {
            "source_id": source_id.strip(),
            "source_text_sha256": common["source_text_sha256"],
            "reference_span": [start, end],
            "context_span": [ctx_start, start],
            "selected_concept_id": selected,
            "candidate_mentions": common["candidate_mentions"],
            "registry_authority_receipt_sha256": authority.get("receipt_sha256"),
        }
        return _base(
            "PASS__UNIQUE_LOCAL_BUFFER_REFERENCE_IDENTITY",
            passed=True,
            reference_identity_authority=True,
            semantic_truth_authority=True,
            selected_concept_id=selected,
            reference_id="REGCAP_BUFFER_REFERENCE:" + _sha(material),
            ambiguity_preserved=False,
            **common,
            global_alias_authority=False,
            boundary=(
                "EXACT_the_buffer_REFERENCE_ONLY__AT_MOST_ONE_PRECEDING_SENTENCE__"
                "UNIQUE_DISTINCT_AUTHENTICATED_CCOB_OR_CCYB_ANTECEDENT_REQUIRED__"
                "MULTIPLE_CONCEPTS_PRESERVE_AMBIGUITY__NO_GLOBAL_BUFFER_ALIAS"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))
