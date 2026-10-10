"""Bounded context-rich identity for two finance terms headed by "margin".

V1 binds exact occurrences of:
- net interest margin -> banking net interest margin
- initial margin -> derivatives/futures initial margin

Authority comes from pinned Federal Reserve and CFTC source fragments.  The
result is occurrence-local term identity.  It does NOT assign a global sense to
the bare word "margin", claim open-world finance sense completeness, or grant
policy/terminal authority.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime.https_source_fragment_projection_authority_v2 import (
    verify_projection_pack,
)

SCHEMA = "PROJECT_BRAIN_MARGIN_CONTEXTUAL_TERM_IDENTITY_V1"
PACK_SCHEMA = "PROJECT_BRAIN_MARGIN_CONTEXTUAL_TERM_SOURCE_PACK_V1"
PACK_PATH = "canonical/evidence/MARGIN_CONTEXTUAL_TERM_SOURCE_PACK_V1.json"
PACK_GIT_BLOB_SHA = "678bc914bda36d42ccdc5e65854347fbe28d3867"
SCOPE_ID = "FINANCE_MARGIN_CONTEXTUAL_TERM_IDENTITY_V1"

NET_INTEREST_MARGIN = "FINANCE::BANK_NET_INTEREST_MARGIN"
INITIAL_MARGIN = "FINANCE::DERIVATIVES_INITIAL_MARGIN"

_TERMS = {
    "net interest margin": {
        "concept_id": NET_INTEREST_MARGIN,
        "source_id": "FED_2026_NET_INTEREST_MARGIN_TERMS",
        "fragment_id": "FED_NET_INTEREST_MARGIN_DEFINITION",
    },
    "initial margin": {
        "concept_id": INITIAL_MARGIN,
        "source_id": "CFTC_FUTURES_GLOSSARY_INITIAL_MARGIN",
        "fragment_id": "CFTC_INITIAL_MARGIN_DEFINITION",
    },
}

_WS = re.compile(r"\s+")
ROOT = Path(__file__).resolve().parents[2]


def _norm(value: Any) -> str:
    return _WS.sub(" ", str(value or "").strip()).casefold()


def _sha(value: Any) -> str:
    if isinstance(value, str):
        return sha256(value.encode("utf-8")).hexdigest()
    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _git_blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "semantic_truth_authority": False,
        "occurrence_identity_authority": False,
        "bare_margin_sense_authority": False,
        "open_world_finance_semantics_complete": False,
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
    required = {x["source_id"] for x in _TERMS.values()}
    if set(by_id) != required:
        raise ValueError("PACK_SOURCE_SET_INVALID")
    return {
        "pack_git_blob_sha": blob,
        "sources_by_id": by_id,
    }


def resolve_span(
    source_text: str,
    *,
    start: int,
    end: int,
    repo_root: str | Path | None = None,
    projection_verifier=verify_projection_pack,
) -> dict[str, Any]:
    try:
        if not isinstance(source_text, str) or not source_text:
            return _base("FAIL_CLOSED", reason="SOURCE_TEXT_REQUIRED")
        if (
            isinstance(start, bool)
            or not isinstance(start, int)
            or isinstance(end, bool)
            or not isinstance(end, int)
            or start < 0
            or end <= start
            or end > len(source_text)
        ):
            return _base("FAIL_CLOSED", reason="SPAN_INVALID")

        surface = source_text[start:end]
        key = _norm(surface)
        spec = _TERMS.get(key)
        if spec is None:
            return _base(
                "UNRESOLVED__OUTSIDE_BOUND_CONTEXTUAL_MARGIN_TERMS",
                source_span=[start, end],
                source_surface=surface,
            )

        checked = load_pack(repo_root=repo_root)
        pack = checked["sources_by_id"][spec["source_id"]]
        source = projection_verifier(pack)
        if not isinstance(source, Mapping) or source.get("pass") is not True:
            return _base(
                "FAIL_CLOSED",
                reason="PINNED_TERM_SOURCE_AUTHORITY_FAILED",
                source_result=source,
            )
        ids = set(
            str(x)
            for x in source.get("receipt", {}).get("fragment_ids", [])
        )
        if spec["fragment_id"] not in ids:
            return _base(
                "FAIL_CLOSED",
                reason="REQUIRED_TERM_FRAGMENT_NOT_AUTHENTICATED",
                source_result=source,
            )

        head_start = end - len("margin")
        if source_text[head_start:end].casefold() != "margin":
            return _base("FAIL_CLOSED", reason="HEAD_MARGIN_SPAN_BINDING_INVALID")

        occurrence_id = "MARGIN_OCCURRENCE:" + _sha({
            "source_text_sha256": _sha(source_text),
            "term_span": [start, end],
            "head_span": [head_start, end],
            "concept_id": spec["concept_id"],
        })
        proof_material = {
            "concept_id": spec["concept_id"],
            "surface": surface,
            "source_span": [start, end],
            "head_span": [head_start, end],
            "source_text_sha256": _sha(source_text),
            "pack_git_blob_sha": checked["pack_git_blob_sha"],
            "source_receipt_sha256": source["receipt"]["receipt_sha256"],
            "fragment_id": spec["fragment_id"],
        }

        return _base(
            "PASS__CONTEXTUAL_MARGIN_TERM_IDENTITY_AUTHENTICATED",
            passed=True,
            semantic_truth_authority=True,
            occurrence_identity_authority=True,
            concept_id=spec["concept_id"],
            occurrence_id=occurrence_id,
            source_span=[start, end],
            margin_head_span=[head_start, end],
            source_surface=surface,
            source_text_sha256=_sha(source_text),
            proof_sha256=_sha(proof_material),
            source_result=source,
            bare_margin_sense_authority=False,
            boundary=(
                "EXACT_MULTIWORD_TERM_OCCURRENCE_ONLY__"
                "DOES_NOT_ASSIGN_A_GLOBAL_SENSE_TO_BARE_margin__"
                "NO_OPEN_WORLD_FINANCE_SENSE_COMPLETENESS_OR_TERMINAL_AUTHORITY"
            ),
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))
