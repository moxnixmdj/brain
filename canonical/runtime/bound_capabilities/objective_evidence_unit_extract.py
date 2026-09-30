#!/usr/bin/env python3
"""Fail-closed extraction of auditable evidence units from an admitted relevant source.

Required admission:
- live retrieval provenance for the candidate;
- an independently-qualified objective-relevance receipt for that same source;
- a fresh re-fetch that resolves to the exact admitted source URL.

Organization/ROR identity is deliberately not an admission prerequisite.

This capability proves only that returned units are verbatim normalized visible
text from the freshly retrieved page, bound by hashes/offsets and lexical
objective anchors. It does not prove support/contradiction, entailment, factual
correctness, causal direction, evidence quality, sufficiency, independence, or
parent completion.
"""
from __future__ import annotations

import hashlib
import html
import ipaddress
import json
import pathlib
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

SCHEMA = "PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2"
UA = "ProjectBrain-EvidenceUnitExtraction/2.0"

_BLOCK_TAGS = {
    "h1","h2","h3","h4","h5","h6",
    "p","li","dt","dd","blockquote","td","th","pre",
    "main","article","section","div",
}
_SUPPRESS = {"script","style","noscript","svg","nav","footer","header","form"}
_STOP = {
    "about","above","after","again","against","also","among","and","are","because",
    "been","being","between","both","can","could","determine","does","during","each",
    "evaluate","evidence","from","have","identify","into","investigate","more","most",
    "objective","provide","provides","published","research","source","sources","than",
    "that","the","their","then","there","these","this","those","through","under",
    "using","whether","which","while","with","would","assess","verify","verification",
    "result","results",
}

def _canon(value):
    return " ".join(str(value or "").split())

def _sha(value):
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()

def _norm_host(raw):
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        host = (urllib.parse.urlsplit(text).hostname or "") if "://" in text else text
    except Exception:
        return None
    host = host.lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
    if not host or "." not in host or host.endswith((".local", ".internal")):
        return None
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None and (
        ip.is_private or ip.is_loopback or ip.is_link_local or
        ip.is_reserved or ip.is_unspecified
    ):
        return None
    if not re.fullmatch(r"[a-z0-9.-]+", host):
        return None
    return host

def _safe_url(raw):
    try:
        parsed = urllib.parse.urlsplit(str(raw or "").strip())
    except Exception:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    if not _norm_host(parsed.hostname):
        return None
    return urllib.parse.urlunsplit((
        parsed.scheme.lower(),
        parsed.netloc,
        parsed.path or "/",
        parsed.query,
        "",
    ))

def _url_key(raw):
    safe = _safe_url(raw)
    if not safe:
        return None
    parsed = urllib.parse.urlsplit(safe)
    host = _norm_host(parsed.hostname)
    port = parsed.port
    if (parsed.scheme == "http" and port == 80) or (parsed.scheme == "https" and port == 443):
        port = None
    return (parsed.scheme, host, port, parsed.path or "/", parsed.query)

def _tokens(text):
    out = []
    for raw in re.findall(r"[a-z0-9][a-z0-9._+-]{1,}", str(text or "").lower()):
        token = raw.strip("._+-")
        if len(token) < 3 or token in _STOP:
            continue
        if token not in out:
            out.append(token)
    return out

class _Blocks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.suppress = 0
        self.stack = []
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        low = tag.lower()
        if low in _SUPPRESS:
            self.suppress += 1
        if self.suppress:
            return
        if low in _BLOCK_TAGS:
            self.stack.append([low, []])

    def handle_endtag(self, tag):
        low = tag.lower()
        if low in _SUPPRESS:
            if self.suppress:
                self.suppress -= 1
            return
        if self.suppress or low not in _BLOCK_TAGS or not self.stack:
            return
        idx = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == low:
                idx = i
                break
        if idx is None:
            return
        tag_name, parts = self.stack.pop(idx)
        text = _canon(" ".join(parts))
        if text:
            self.blocks.append((tag_name, text))

    def handle_data(self, data):
        if self.suppress or not self.stack:
            return
        text = _canon(data)
        if not text:
            return
        for frame in self.stack:
            frame[1].append(text)

def _split_long(text, max_chars=900):
    text = _canon(text)
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]
    sentences = [
        _canon(part)
        for part in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text)
        if _canon(part)
    ]
    if len(sentences) <= 1:
        return [
            text[i:i + max_chars].strip()
            for i in range(0, len(text), max_chars)
            if text[i:i + max_chars].strip()
        ]
    out = []
    buf = ""
    for sentence in sentences:
        candidate = (buf + " " + sentence).strip() if buf else sentence
        if buf and len(candidate) > max_chars:
            out.append(buf)
            buf = sentence
        else:
            buf = candidate
    if buf:
        out.append(buf)
    return out

def _extract_blocks(raw, content_type):
    decoded = raw.decode("utf-8", "replace")
    parser = _Blocks()
    if "html" in str(content_type or "").lower() or "<html" in decoded[:2000].lower():
        try:
            parser.feed(decoded)
        except Exception:
            pass
        rows = parser.blocks
    else:
        rows = [("text", part) for part in re.split(r"\n\s*\n", decoded)]
    out = []
    seen = set()
    for tag, value in rows:
        for unit in _split_long(html.unescape(value)):
            unit = _canon(unit)
            if len(unit) < 24:
                continue
            key = unit.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append((tag, unit))
    return out

def _fetch(url, timeout=20, max_bytes=2_000_000):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,text/plain,*/*;q=0.3",
        },
    )
    with urllib.request.urlopen(
        request,
        timeout=max(2, min(int(timeout), 30)),
    ) as response:
        raw = response.read(max_bytes)
        final_url = response.geturl()
        content_type = str(response.headers.get("Content-Type") or "")
        status = int(getattr(response, "status", 200))
    return raw, final_url, content_type, status

def _qualified_relevance_source(objective, candidate, provenance, relevance):
    """Return the admitted source URL or a fail-closed reason.

    Supports both qualified relevance routes already present in Brain:
    1. first-party fresh-page relevance verification; and
    2. generic deterministic BM25 relevance ranking selecting the candidate.

    Neither route requires ROR inside this extractor. ROR may have been used
    upstream by route (1), but it is not a universal extraction prerequisite.
    """
    objective = _canon(objective)
    candidate_url = _safe_url((candidate or {}).get("url"))
    provenance_final = _safe_url((provenance or {}).get("final_url"))
    if not candidate_url or not provenance_final:
        return None, "ADMITTED_SOURCE_URL_REQUIRED"

    status = relevance.get("status")
    if (
        status == "FIRST_PARTY_RELEVANT_SOURCE_VERIFIED"
        and relevance.get("objective_relevance_status") == "VERIFIED"
    ):
        fresh_url = _safe_url(relevance.get("fresh_url"))
        if not fresh_url:
            return None, "VERIFIED_OBJECTIVE_RELEVANCE_SOURCE_REQUIRED"
        if _url_key(fresh_url) != _url_key(provenance_final):
            return None, "ADMITTED_SOURCE_IDENTITY_MISMATCH"
        return fresh_url, None

    if (
        status == "LEXICAL_RELEVANCE_RANKED"
        and relevance.get("verification_method") == "DETERMINISTIC_BM25"
        and relevance.get("output_verified") is True
    ):
        receipt_objective = _canon(relevance.get("objective"))
        if receipt_objective and receipt_objective != objective:
            return None, "RELEVANCE_OBJECTIVE_MISMATCH"
        rows = relevance.get("ranked_candidates")
        top_index = relevance.get("top_candidate_original_index")
        if not isinstance(rows, list) or top_index is None:
            return None, "RELEVANCE_SELECTION_MISSING"
        selected = None
        for row in rows:
            if isinstance(row, dict) and row.get("original_index") == top_index:
                selected = row
                break
        if not selected:
            return None, "RELEVANCE_SELECTED_ROW_MISSING"
        selected_candidate = selected.get("candidate") or {}
        if _url_key(selected_candidate.get("url")) != _url_key(candidate_url):
            return None, "CANDIDATE_NOT_SELECTED_BY_RELEVANCE_RECEIPT"
        if float(selected.get("lexical_relevance_score") or 0.0) <= 0:
            return None, "NONPOSITIVE_RELEVANCE_SCORE"
        if not list(selected.get("matched_terms") or []):
            return None, "RELEVANCE_MATCH_TERMS_REQUIRED"
        admission=relevance.get("top_candidate_admission") or {}
        if admission.get("verified") is not True:
            return None, "RELEVANCE_SUBJECT_COVERAGE_ADMISSION_REQUIRED"
        if int(admission.get("matched_term_count") or 0) != len(list(selected.get("matched_terms") or [])):
            return None, "RELEVANCE_ADMISSION_MATCH_COUNT_MISMATCH"
        return provenance_final, None

    return None, "VERIFIED_OBJECTIVE_RELEVANCE_REQUIRED"

def extract(objective, candidate, provenance, relevance, timeout=20, max_units=10, fetch=None):
    objective = _canon(objective)
    candidate = dict(candidate or {})
    provenance = dict(provenance or {})
    relevance = dict(relevance or {})
    base = {
        "schema": SCHEMA,
        "objective": objective or None,
        "status": "UNVERIFIED",
        "evidence_extraction_status": "UNVERIFIED",
        "claim_relation_status": "UNVERIFIED",
        "semantic_entailment_status": "UNVERIFIED",
        "factual_correctness_status": "UNVERIFIED",
        "causal_direction_status": "UNVERIFIED",
        "evidence_quality_status": "UNVERIFIED",
        "evidence_sufficiency_status": "UNVERIFIED",
        "source_independence_status": "UNVERIFIED",
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "evidence_units": [],
    }
    if not objective:
        return {**base, "reason": "OBJECTIVE_REQUIRED"}
    if provenance.get("status") != "RETRIEVAL_PROVENANCE_VERIFIED":
        return {**base, "reason": "LIVE_RETRIEVAL_PROVENANCE_REQUIRED"}

    candidate_url = _safe_url(candidate.get("url"))
    provenance_candidate = _safe_url(provenance.get("candidate_url") or candidate_url)
    provenance_final = _safe_url(provenance.get("final_url"))
    if not candidate_url or _url_key(candidate_url) != _url_key(provenance_candidate):
        return {**base, "reason": "PROVENANCE_CANDIDATE_MISMATCH"}
    if not provenance_final:
        return {**base, "reason": "PROVENANCE_FINAL_URL_REQUIRED"}

    admitted_url, relevance_error = _qualified_relevance_source(
        objective, candidate, provenance, relevance
    )
    if relevance_error:
        return {**base, "reason": relevance_error}

    fetch = fetch or _fetch
    try:
        raw, observed_url, content_type, http_status = fetch(admitted_url, timeout)
    except Exception as exc:
        return {
            **base,
            "reason": "FRESH_EVIDENCE_FETCH_FAILED",
            "error_class": type(exc).__name__,
        }

    raw = bytes(raw)
    observed_safe = _safe_url(observed_url)
    if not observed_safe or _url_key(observed_safe) != _url_key(admitted_url):
        return {
            **base,
            "reason": "FRESH_EVIDENCE_SOURCE_IDENTITY_MISMATCH",
            "admitted_source_url": admitted_url,
            "fresh_source_url": observed_safe,
        }

    blocks = _extract_blocks(raw, content_type)
    objective_tokens = _tokens(objective)
    if not objective_tokens:
        return {**base, "reason": "NO_DISCRIMINATIVE_OBJECTIVE_TOKENS"}

    visible = "\n".join(text for _, text in blocks)
    page_raw_sha256 = _sha(raw)
    visible_text_sha256 = _sha(visible)
    required_unit_matches = 1 if len(objective_tokens) == 1 else 2

    rows = []
    cursor = 0
    for block_index, (tag, text) in enumerate(blocks):
        start = visible.find(text, cursor)
        if start < 0:
            start = visible.find(text)
        if start < 0:
            continue
        end = start + len(text)
        cursor = end
        words = set(_tokens(text))
        matched = [token for token in objective_tokens if token in words]
        if len(matched) < required_unit_matches:
            continue
        text_sha256 = _sha(text)
        evidence_unit_id = _sha(
            "{}:{}:{}:{}".format(page_raw_sha256, start, end, text_sha256)
        )
        rows.append({
            "_score": len(matched) * 10 + (2 if tag in {"h1","h2","h3","h4","h5","h6"} else 0),
            "evidence_unit_id": evidence_unit_id,
            "source_url": observed_safe,
            "page_raw_sha256": page_raw_sha256,
            "visible_text_sha256": visible_text_sha256,
            "block_index": block_index,
            "block_tag": tag,
            "text": text,
            "text_sha256": text_sha256,
            "matched_objective_tokens": matched,
            "matched_objective_token_count": len(matched),
            "visible_text_start": start,
            "visible_text_end": end,
        })

    rows.sort(key=lambda item: (-item["_score"], item["block_index"]))
    rows = rows[:max(1, min(int(max_units or 10), 20))]
    for row in rows:
        row.pop("_score", None)

    if not rows:
        return {
            **base,
            "reason": "NO_OBJECTIVE_GROUNDED_EVIDENCE_UNITS",
            "source_url": observed_safe,
            "objective_tokens": objective_tokens,
            "page_raw_sha256": page_raw_sha256,
            "visible_text_sha256": visible_text_sha256,
            "visible_block_count": len(blocks),
        }

    return {
        **base,
        "status": "OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
        "evidence_extraction_status": "VERIFIED",
        "verification_method": "VERIFIED_RELEVANCE_ADMISSION_PLUS_FRESH_EXACT_SOURCE_VISIBLE_BLOCK_EXTRACTION",
        "source_url": observed_safe,
        "source_host": _norm_host(observed_safe),
        "http_status": http_status,
        "content_type": content_type,
        "page_raw_sha256": page_raw_sha256,
        "visible_text_sha256": visible_text_sha256,
        "visible_text_length": len(visible),
        "visible_block_count": len(blocks),
        "objective_tokens": objective_tokens,
        "required_unit_match_count": required_unit_matches,
        "evidence_unit_count": len(rows),
        "evidence_units": rows,
        "scope_note": "Evidence units are verbatim normalized visible-text blocks from the exact freshly refetched admitted source. Organization/ROR identity is not an extraction prerequisite. Support, contradiction, entailment, correctness, causality, quality, sufficiency, and independence remain unverified.",
        "output_verified": True,
    }

def _safe_path(root, raw):
    root = pathlib.Path(root).resolve()
    path = (root / str(raw or "")).resolve()
    if path == root or root not in path.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return path

def run(args, root):
    args = dict(args or {})
    inp = _safe_path(root, args.get("input_path"))
    out = _safe_path(root, args.get("output_path"))
    if not inp.is_file():
        raise ValueError("EVIDENCE_EXTRACTION_INPUT_MISSING")
    data = json.loads(inp.read_text(encoding="utf-8"))
    result = extract(
        data.get("objective"),
        data.get("candidate"),
        data.get("provenance"),
        data.get("relevance"),
        timeout=args.get("timeout", 20),
        max_units=args.get("max_units", 10),
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result["output_path"] = str(
        out.relative_to(pathlib.Path(root).resolve())
    ).replace("\\", "/")
    result["output_verified"] = (
        result.get("status") == "OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED"
    )
    return result
