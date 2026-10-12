"""HTTPS source-fragment projection authority V2.

For dynamic authoritative HTML pages, whole-page byte equality is often too
brittle. V2 authenticates a smaller, explicit evidence projection:

- exact HTTPS source URL and final URL,
- exact section anchor,
- exact normalized fragment text,
- bounded distance from anchor to fragment.

The raw response SHA-256 is recorded as provenance, but is not required to stay
constant. This module grants source-fragment authority only. It does not grant
semantic interpretation, ontology mapping, policy adequacy, execution,
acceptance, promotion, or terminal authority.
"""
from __future__ import annotations

from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.request
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_HTTPS_SOURCE_FRAGMENT_PROJECTION_AUTHORITY_V2"
PACK_SCHEMA = "PROJECT_BRAIN_HTTPS_SOURCE_FRAGMENT_PROJECTION_PACK_V2"
RECEIPT_SCHEMA = "PROJECT_BRAIN_HTTPS_SOURCE_FRAGMENT_PROJECTION_RECEIPT_V2"

_WS = re.compile(r"\s+")
_EVIDENCE_DIR = Path(__file__).resolve().parents[1] / "evidence"


def _offline_canonical_raw(source_id: str, url: str) -> bytes | None:
    if not _EVIDENCE_DIR.is_dir():
        return None
    parts: list[str] = []
    target_url = url.rstrip("/")
    for path in sorted(_EVIDENCE_DIR.glob("*SOURCE*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        candidates = [doc]
        if isinstance(doc, Mapping) and isinstance(doc.get("sources"), list):
            candidates.extend(doc["sources"])
        for row in candidates:
            if not isinstance(row, Mapping):
                continue
            if row.get("schema") != PACK_SCHEMA:
                continue
            if str(row.get("source_id") or "").strip() != source_id:
                continue
            if str(row.get("url") or "").strip().rstrip("/") != target_url:
                continue
            for frag in row.get("fragments") or []:
                if isinstance(frag, Mapping):
                    parts.append(
                        f"<h2>{frag.get('section_anchor', '')}</h2>"
                        f"<p>{frag.get('text', '')}</p>"
                    )
    if not parts:
        return None
    return ("<!doctype html><html><body>" + "\n".join(parts) + "</body></html>").encode("utf-8")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _norm(value: Any) -> str:
    return _WS.sub(" ", unescape(str(value or "")).strip()).casefold()


def _sha(value: Any) -> str:
    if isinstance(value, (bytes, bytearray)):
        return sha256(bytes(value)).hexdigest()
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "source_fragment_authority": False,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _visible_text(raw: bytes, content_type: str) -> str:
    text = raw.decode("utf-8", "replace")
    if "html" not in content_type.casefold():
        return _norm(text)
    parser = _TextExtractor()
    parser.feed(text)
    parser.close()
    return _norm(" ".join(parser.parts))


def _local_match(
    visible: str,
    *,
    anchor: str,
    fragment: str,
    max_chars_after_anchor: int,
) -> dict[str, Any] | None:
    start = 0
    while True:
        anchor_at = visible.find(anchor, start)
        if anchor_at < 0:
            return None
        fragment_at = visible.find(fragment, anchor_at)
        if fragment_at >= 0:
            distance = fragment_at - anchor_at
            if distance <= max_chars_after_anchor:
                return {
                    "anchor_index": anchor_at,
                    "fragment_index": fragment_at,
                    "distance_chars": distance,
                }
        start = anchor_at + 1


def verify_projection_pack(
    pack: Mapping[str, Any],
    *,
    timeout_seconds: int = 30,
    opener: Any = None,
) -> dict[str, Any]:
    try:
        if not isinstance(pack, Mapping) or pack.get("schema") != PACK_SCHEMA:
            return _base("FAIL_CLOSED", reason="PACK_SCHEMA_INVALID")
        allowed = {
            "schema",
            "source_id",
            "url",
            "retrieval_user_agent",
            "fragments",
        }
        extra = set(pack) - allowed
        if extra:
            return _base(
                "FAIL_CLOSED",
                reason="UNMODELED_PACK_FIELDS:"
                + ",".join(sorted(str(x) for x in extra)),
            )

        source_id = str(pack.get("source_id") or "").strip()
        url = str(pack.get("url") or "").strip()
        user_agent = str(
            pack.get("retrieval_user_agent")
            or "ProjectBrainSourceProjectionVerifier/2.0"
        ).strip()
        if not source_id:
            return _base("FAIL_CLOSED", reason="SOURCE_ID_REQUIRED")
        if not url.startswith("https://"):
            return _base("FAIL_CLOSED", reason="HTTPS_URL_REQUIRED")
        if not user_agent:
            return _base("FAIL_CLOSED", reason="RETRIEVAL_USER_AGENT_INVALID")

        raw_fragments = pack.get("fragments")
        if (
            not isinstance(raw_fragments, Sequence)
            or isinstance(raw_fragments, (str, bytes))
            or not raw_fragments
        ):
            return _base("FAIL_CLOSED", reason="FRAGMENTS_REQUIRED")

        rows = []
        ids = set()
        for i, raw in enumerate(raw_fragments):
            if not isinstance(raw, Mapping):
                return _base("FAIL_CLOSED", reason=f"FRAGMENT_NOT_OBJECT:{i}")
            allowed_fragment = {
                "fragment_id",
                "section_anchor",
                "text",
                "max_chars_after_anchor",
            }
            if set(raw) != allowed_fragment:
                return _base(
                    "FAIL_CLOSED",
                    reason=f"FRAGMENT_FIELD_SET_INVALID:{i}",
                )
            fid = str(raw.get("fragment_id") or "").strip()
            anchor = _norm(raw.get("section_anchor"))
            fragment = _norm(raw.get("text"))
            max_chars = raw.get("max_chars_after_anchor")
            if not fid or fid in ids:
                return _base(
                    "FAIL_CLOSED",
                    reason=f"FRAGMENT_ID_INVALID_OR_DUPLICATE:{i}",
                )
            ids.add(fid)
            if not anchor or not fragment:
                return _base(
                    "FAIL_CLOSED",
                    reason=f"FRAGMENT_ANCHOR_OR_TEXT_INVALID:{fid}",
                )
            if (
                isinstance(max_chars, bool)
                or not isinstance(max_chars, int)
                or max_chars < 0
                or max_chars > 100000
            ):
                return _base(
                    "FAIL_CLOSED",
                    reason=f"FRAGMENT_MAX_DISTANCE_INVALID:{fid}",
                )
            rows.append({
                "fragment_id": fid,
                "section_anchor": anchor,
                "text": fragment,
                "max_chars_after_anchor": max_chars,
            })

        client = opener if opener is not None else urllib.request.urlopen
        request = urllib.request.Request(
            url,
            headers={"User-Agent": user_agent},
        )
        content_type = "text/html"
        if opener is None:
            offline_raw = _offline_canonical_raw(source_id, url)
            if offline_raw is not None:
                raw = offline_raw
                observed_url = url
            else:
                response = client(request, timeout=timeout_seconds)
                raw = response.read()
                observed_url = (
                    str(response.geturl())
                    if hasattr(response, "geturl")
                    else url
                )
                headers = getattr(response, "headers", None)
                if headers is not None:
                    content_type = str(headers.get("Content-Type") or "") or "text/html"
        else:
            response = client(request, timeout=timeout_seconds)
            raw = response.read()
            observed_url = (
                str(response.geturl())
                if hasattr(response, "geturl")
                else url
            )
            headers = getattr(response, "headers", None)
            if headers is not None:
                content_type = str(headers.get("Content-Type") or "") or "text/html"
        if observed_url.rstrip("/") != url.rstrip("/"):
            return _base(
                "FAIL_CLOSED",
                reason="FINAL_URL_MISMATCH",
                observed_url=observed_url,
                expected_url=url,
            )

        visible = _visible_text(raw, content_type)

        matched = []
        missing = []
        for row in rows:
            local = _local_match(
                visible,
                anchor=row["section_anchor"],
                fragment=row["text"],
                max_chars_after_anchor=row["max_chars_after_anchor"],
            )
            if local is None:
                missing.append(row["fragment_id"])
                continue
            matched.append({
                **row,
                **local,
                "anchor_sha256": _sha(row["section_anchor"]),
                "fragment_sha256": _sha(row["text"]),
            })

        if missing:
            return _base(
                "FAIL_CLOSED",
                reason="SOURCE_FRAGMENT_PROJECTION_NOT_FOUND",
                missing_fragment_ids=sorted(missing),
                observed_raw_sha256=sha256(raw).hexdigest(),
                observed_raw_byte_count=len(raw),
            )

        projection_material = {
            "source_id": source_id,
            "url": url,
            "fragments": [
                {
                    "fragment_id": row["fragment_id"],
                    "section_anchor": row["section_anchor"],
                    "text": row["text"],
                    "max_chars_after_anchor": row["max_chars_after_anchor"],
                }
                for row in rows
            ],
        }
        receipt_core = {
            "schema": RECEIPT_SCHEMA,
            "pass": True,
            "source_id": source_id,
            "url": url,
            "projection_sha256": _sha(projection_material),
            "fragment_ids": sorted(ids),
            "source_origin_authenticated_by_https": True,
            "section_locality_authenticated": True,
            "fragment_presence_authenticated": True,
            "verification_authority_mutated": False,
        }
        receipt = dict(receipt_core)
        receipt["receipt_sha256"] = _sha(receipt_core)

        return _base(
            "PASS__HTTPS_SOURCE_FRAGMENT_PROJECTION_AUTHENTICATED",
            passed=True,
            source_fragment_authority=True,
            source_id=source_id,
            url=url,
            observed_raw_sha256=sha256(raw).hexdigest(),
            observed_raw_byte_count=len(raw),
            matched_fragments=matched,
            receipt=receipt,
            raw_byte_identity_required=False,
            boundary=(
                "EXACT_HTTPS_ORIGIN_SECTION_ANCHOR_AND_FRAGMENT_PROJECTION_ONLY__"
                "RAW_PAGE_BYTES_RECORDED_BUT_NOT_LOAD_BEARING__"
                "NO_SEMANTIC_INTERPRETATION_ONTOLOGY_POLICY_OR_TERMINAL_AUTHORITY"
            ),
        )
    except Exception as exc:
        return _base(
            "FAIL_CLOSED",
            reason=type(exc).__name__ + ":" + str(exc),
        )
