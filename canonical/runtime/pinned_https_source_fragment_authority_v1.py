"""Pinned HTTPS source-fragment authority V1.

Fetches one exact HTTPS resource, requires exact raw-byte SHA-256 and byte count,
deterministically reduces HTML to normalized visible text, and authenticates only
the explicitly listed source fragments that are actually present.

This module grants source-fragment authority only. It does not infer the meaning
of a fragment, does not map it to ontology concepts, and grants no semantic,
policy, execution, acceptance, promotion, or terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
import json
import re
import urllib.request
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_PINNED_HTTPS_SOURCE_FRAGMENT_AUTHORITY_V1"
PACK_SCHEMA = "PROJECT_BRAIN_PINNED_HTTPS_SOURCE_FRAGMENT_PACK_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_PINNED_HTTPS_SOURCE_FRAGMENT_RECEIPT_V1"

_WS = re.compile(r"\s+")
_SHA = re.compile(r"^[0-9a-f]{64}$")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _norm(text: Any) -> str:
    return _WS.sub(" ", unescape(str(text or "")).strip()).casefold()


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    if isinstance(value, (bytes, bytearray)):
        return sha256(bytes(value)).hexdigest()
    return sha256(_canon(value)).hexdigest()


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
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
    decoded = raw.decode("utf-8", "replace")
    if "html" not in content_type.casefold():
        return _norm(decoded)
    parser = _TextExtractor()
    parser.feed(decoded)
    parser.close()
    return _norm(" ".join(parser.parts))


def verify_pack(
    pack: Mapping[str, Any],
    *,
    timeout_seconds: int = 30,
    opener: Any = None,
) -> dict[str, Any]:
    try:
        if not isinstance(pack, Mapping) or pack.get("schema") != PACK_SCHEMA:
            return _fail("PACK_SCHEMA_INVALID")

        allowed = {
            "schema",
            "source_id",
            "url",
            "expected_raw_sha256",
            "expected_byte_count",
            "fragments",
            "retrieval_user_agent",
        }
        extra = set(pack) - allowed
        if extra:
            return _fail(
                "UNMODELED_PACK_FIELDS:"
                + ",".join(sorted(str(x) for x in extra))
            )

        source_id = str(pack.get("source_id") or "").strip()
        url = str(pack.get("url") or "").strip()
        expected_sha = str(pack.get("expected_raw_sha256") or "").lower()
        byte_count = pack.get("expected_byte_count")
        user_agent = str(
            pack.get("retrieval_user_agent")
            or "ProjectBrainPinnedSourceVerifier/1.0"
        ).strip()

        if not source_id:
            return _fail("SOURCE_ID_REQUIRED")
        if not url.startswith("https://"):
            return _fail("HTTPS_URL_REQUIRED")
        if _SHA.fullmatch(expected_sha) is None:
            return _fail("EXPECTED_RAW_SHA256_INVALID")
        if (
            isinstance(byte_count, bool)
            or not isinstance(byte_count, int)
            or byte_count <= 0
        ):
            return _fail("EXPECTED_BYTE_COUNT_INVALID")
        if not user_agent:
            return _fail("RETRIEVAL_USER_AGENT_INVALID")

        fragments = pack.get("fragments")
        if (
            not isinstance(fragments, Sequence)
            or isinstance(fragments, (str, bytes))
            or not fragments
        ):
            return _fail("FRAGMENTS_REQUIRED")

        normalized_rows = []
        ids = set()
        for i, raw_row in enumerate(fragments):
            if not isinstance(raw_row, Mapping):
                return _fail(f"FRAGMENT_NOT_OBJECT:{i}")
            if set(raw_row) != {"fragment_id", "text"}:
                return _fail(f"FRAGMENT_FIELD_SET_INVALID:{i}")
            fid = str(raw_row.get("fragment_id") or "").strip()
            text = str(raw_row.get("text") or "").strip()
            if not fid or fid in ids:
                return _fail(f"FRAGMENT_ID_INVALID_OR_DUPLICATE:{i}")
            ids.add(fid)
            norm = _norm(text)
            if not norm:
                return _fail(f"FRAGMENT_TEXT_INVALID:{fid}")
            normalized_rows.append({
                "fragment_id": fid,
                "text": text,
                "normalized_text": norm,
            })

        client = opener if opener is not None else urllib.request.urlopen
        request = urllib.request.Request(
            url,
            headers={"User-Agent": user_agent},
        )
        response = client(request, timeout=timeout_seconds)
        raw = response.read()
        observed_url = (
            response.geturl()
            if hasattr(response, "geturl")
            else url
        )
        content_type = ""
        headers = getattr(response, "headers", None)
        if headers is not None:
            content_type = str(headers.get("Content-Type") or "")

        observed_sha = sha256(raw).hexdigest()
        if observed_sha != expected_sha:
            return _fail(
                "RAW_SOURCE_SHA256_MISMATCH",
                observed_raw_sha256=observed_sha,
                expected_raw_sha256=expected_sha,
                observed_byte_count=len(raw),
            )
        if len(raw) != byte_count:
            return _fail(
                "RAW_SOURCE_BYTE_COUNT_MISMATCH",
                observed_byte_count=len(raw),
                expected_byte_count=byte_count,
            )

        visible = _visible_text(raw, content_type or "text/html")
        missing = [
            row["fragment_id"]
            for row in normalized_rows
            if row["normalized_text"] not in visible
        ]
        if missing:
            return _fail(
                "PINNED_FRAGMENT_NOT_FOUND_IN_SOURCE",
                missing_fragment_ids=sorted(missing),
            )

        receipt_core = {
            "schema": RECEIPT_SCHEMA,
            "pass": True,
            "source_id": source_id,
            "url": url,
            "observed_url": observed_url,
            "raw_sha256": observed_sha,
            "raw_byte_count": len(raw),
            "fragment_ids": sorted(ids),
            "fragment_set_sha256": _sha(normalized_rows),
            "source_bytes_authenticated": True,
            "fragment_presence_authenticated": True,
            "verification_authority_mutated": False,
        }
        receipt = dict(receipt_core)
        receipt["receipt_sha256"] = _sha(receipt_core)

        return {
            "schema": SCHEMA,
            "status": "PASS__PINNED_HTTPS_SOURCE_FRAGMENTS_AUTHENTICATED",
            "pass": True,
            "source_id": source_id,
            "url": url,
            "raw_sha256": observed_sha,
            "raw_byte_count": len(raw),
            "fragments": deepcopy(normalized_rows),
            "receipt": receipt,
            "source_fragment_authority": True,
            "semantic_truth_authority": False,
            "policy_adequacy_authority": False,
            "execution_authority": False,
            "acceptance_authority": False,
            "promotion_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "boundary": (
                "EXACT_HTTPS_RAW_BYTES_AND_FRAGMENT_PRESENCE_ONLY__"
                "NO_SEMANTIC_INTERPRETATION_ONTOLOGY_MAPPING_POLICY_OR_TERMINAL_AUTHORITY"
            ),
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))
