#!/usr/bin/env python3
"""Bounded SEC inline-XBRL source-native fact identity extraction.

V1 proves only an occurrence-local identity already declared by the source:
an inline XBRL fact element -> its exact QName (namespace URI + local name).
It does not infer nearby prose labels, custom-concept meaning, ontology class,
policy adequacy, or terminal truth.
"""
from __future__ import annotations

from html.parser import HTMLParser
import hashlib
import json
import pathlib
import re
import urllib.parse
import urllib.request
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_SEC_INLINE_XBRL_SOURCE_NATIVE_FACT_ANCHOR_V1"
_INLINE_NAMESPACES = {
    "http://www.xbrl.org/2013/inlineXBRL",
    "http://www.xbrl.org/2008/inlineXBRL",
}
_QNAME_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_.-]*):([A-Za-z_][A-Za-z0-9_.-]*)$")
_XMLNS_RE = re.compile(
    r"""\bxmlns:([A-Za-z_][A-Za-z0-9_.-]*)\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE,
)
_HTML_START_RE = re.compile(r"""<html\b[^<>]*>""", re.IGNORECASE | re.DOTALL)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_BYTES = 12_000_000
MAX_FACTS = 10_000


class InlineXbrlError(RuntimeError):
    pass


def _safe_path(root: pathlib.Path, raw: Any) -> pathlib.Path:
    root = pathlib.Path(root).resolve()
    path = (root / str(raw or "")).resolve()
    if path == root or root not in path.parents:
        raise InlineXbrlError("PATH_OUTSIDE_REPOSITORY")
    return path


def _user_agent(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 240:
        raise InlineXbrlError("SEC_USER_AGENT_REQUIRED")
    text = " ".join(value.strip().split())
    if len(text.split()) < 2 or not any(
        _EMAIL_RE.fullmatch(x.strip("<>()[]{};,") or "") for x in text.split()
    ):
        raise InlineXbrlError("SEC_USER_AGENT_DECLARED_CONTACT_REQUIRED")
    return text


def _filing_url(value: Any) -> str:
    text = str(value or "").strip()
    parsed = urllib.parse.urlsplit(text)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "www.sec.gov"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
        or parsed.query
        or parsed.fragment
        or not parsed.path.startswith("/Archives/edgar/data/")
        or not parsed.path.lower().endswith((".htm", ".html"))
    ):
        raise InlineXbrlError("SEC_ARCHIVE_INLINE_FILING_URL_REQUIRED")
    return urllib.parse.urlunsplit(("https", "www.sec.gov", parsed.path, "", ""))


def _fetch(url: str, user_agent: str, timeout: int, max_bytes: int):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Encoding": "identity",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = int(getattr(response, "status", 200))
        raw = response.read(max_bytes + 1)
        final_url = str(response.geturl())
        content_type = str(response.headers.get("Content-Type") or "")
    return raw, final_url, content_type, status


def _namespace_map(text: str) -> dict[str, str]:
    root_match = _HTML_START_RE.search(text)
    if root_match is None:
        raise InlineXbrlError("ROOT_HTML_START_TAG_REQUIRED")
    root_tag = root_match.group(0)
    out: dict[str, str] = {}
    for match in _XMLNS_RE.finditer(root_tag):
        prefix = match.group(1)
        uri = match.group(2).strip()
        prior = out.get(prefix)
        if prior is not None and prior != uri:
            raise InlineXbrlError("ROOT_NAMESPACE_PREFIX_REBOUND:" + prefix)
        out[prefix] = uri
    if not out:
        raise InlineXbrlError("ROOT_NAMESPACE_DECLARATIONS_REQUIRED")

    # V1 refuses scoped namespace mutation instead of applying declarations
    # outside their lexical scope. All QName prefixes must be root-declared.
    root_start, root_end = root_match.span()
    for match in _XMLNS_RE.finditer(text):
        if root_start <= match.start() and match.end() <= root_end:
            continue
        raise InlineXbrlError("NESTED_NAMESPACE_DECLARATION_OUTSIDE_V1:" + match.group(1))
    return out

class _FactParser(HTMLParser):
    def __init__(self, namespaces: Mapping[str, str], max_facts: int):
        super().__init__(convert_charrefs=False)
        self.namespaces = dict(namespaces)
        self.max_facts = max_facts
        self.facts: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs):
        self._handle(tag, attrs)

    def handle_startendtag(self, tag: str, attrs):
        self._handle(tag, attrs)

    def _handle(self, tag: str, attrs):
        if ":" not in tag:
            return
        tag_prefix, local = tag.split(":", 1)
        ix_uri = None
        for prefix, uri in self.namespaces.items():
            if prefix.casefold() == tag_prefix.casefold():
                ix_uri = uri
                break
        if ix_uri not in _INLINE_NAMESPACES or local.casefold() not in {
            "nonfraction",
            "nonnumeric",
        }:
            return
        if len(self.facts) >= self.max_facts:
            raise InlineXbrlError("INLINE_FACT_LIMIT_EXCEEDED")
        amap = {str(k).casefold(): v for k, v in attrs}
        lexical_qname = str(amap.get("name") or "").strip()
        match = _QNAME_RE.fullmatch(lexical_qname)
        if match is None:
            raise InlineXbrlError("INLINE_FACT_QNAME_INVALID")
        prefix, local_name = match.groups()
        namespace_uri = self.namespaces.get(prefix)
        if namespace_uri is None:
            raise InlineXbrlError("INLINE_FACT_QNAME_PREFIX_UNBOUND:" + prefix)
        context_ref = str(amap.get("contextref") or "").strip()
        if not context_ref:
            raise InlineXbrlError("INLINE_FACT_CONTEXTREF_REQUIRED")
        raw_start = self.get_starttag_text() or ""
        line, column = self.getpos()
        row = {
            "ordinal": len(self.facts),
            "ix_kind": local.casefold(),
            "lexical_qname": lexical_qname,
            "namespace_uri": namespace_uri,
            "local_name": local_name,
            "context_ref": context_ref,
            "source_line": int(line),
            "source_column": int(column),
            "start_tag_sha256": hashlib.sha256(raw_start.encode("utf-8")).hexdigest(),
        }
        for source_key, target_key in (
            ("id", "xml_id"),
            ("unitref", "unit_ref"),
            ("decimals", "decimals"),
            ("precision", "precision"),
            ("scale", "scale"),
            ("sign", "sign"),
            ("format", "format"),
        ):
            value = amap.get(source_key)
            if value is not None and str(value).strip():
                row[target_key] = str(value).strip()
        self.facts.append(row)


def _extract(raw: bytes, max_facts: int) -> tuple[dict[str, str], list[dict[str, Any]]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InlineXbrlError("INLINE_FILING_UTF8_REQUIRED") from exc
    namespaces = _namespace_map(text)
    if not any(uri in _INLINE_NAMESPACES for uri in namespaces.values()):
        raise InlineXbrlError("INLINE_XBRL_NAMESPACE_REQUIRED")
    parser = _FactParser(namespaces, max_facts)
    try:
        parser.feed(text)
        parser.close()
    except InlineXbrlError:
        raise
    except Exception as exc:
        raise InlineXbrlError("INLINE_XBRL_PARSE_FAILED") from exc
    if not parser.facts:
        raise InlineXbrlError("NO_SUPPORTED_INLINE_XBRL_FACTS")
    return namespaces, parser.facts


def _concept_id(row: Mapping[str, Any]) -> str:
    return "XBRL_CONCEPT:{" + str(row["namespace_uri"]) + "}" + str(row["local_name"])


def _semantic_contract(
    *,
    rows: list[dict[str, Any]],
    source_path: str,
    source_sha256: str,
    source_url: str,
) -> dict[str, Any]:
    base_source = {"path": source_path, "artifact": source_sha256, "uri": source_url}
    concept_rows: dict[str, dict[str, Any]] = {}
    entities: list[dict[str, Any]] = []
    facts: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    for row in rows:
        cid = _concept_id(row)
        if cid not in concept_rows:
            concept_rows[cid] = row
            entities.append({"id": cid, "type": "XBRL_CONCEPT_IDENTITY", "source": base_source})
            for predicate, value in (
                ("namespace_uri", row["namespace_uri"]),
                ("local_name", row["local_name"]),
            ):
                facts.append(
                    {"subject": cid, "predicate": predicate, "object": value, "source": base_source}
                )
        fid = "IX_FACT:" + str(row["ordinal"])
        source = {
            **base_source,
            "observation_id": fid,
            "span": [row["source_line"], row["source_column"]],
        }
        entities.append({"id": fid, "type": "INLINE_XBRL_FACT_OCCURRENCE", "source": source})
        relations.append(
            {
                "subject": fid,
                "predicate": "source_declares_xbrl_concept",
                "object": cid,
                "source": source,
            }
        )
        for key in (
            "lexical_qname",
            "context_ref",
            "ix_kind",
            "xml_id",
            "unit_ref",
            "decimals",
            "precision",
            "scale",
            "sign",
            "format",
            "start_tag_sha256",
        ):
            if key in row:
                facts.append(
                    {"subject": fid, "predicate": key, "object": row[key], "source": source}
                )
    return {
        "entities": entities,
        "facts": facts,
        "relations": relations,
        "templates": [],
        "ambiguities": [],
    }


def run(args: Mapping[str, Any], root: Any) -> dict[str, Any]:
    root = pathlib.Path(root).resolve()
    config_path = _safe_path(root, args.get("config_path"))
    raw_path = _safe_path(root, args.get("raw_output_path"))
    semantic_path = _safe_path(root, args.get("semantic_output_path"))
    if not config_path.is_file() or config_path.suffix.lower() != ".json":
        raise InlineXbrlError("CONFIG_JSON_REQUIRED")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    url = _filing_url(config.get("filing_url"))
    user_agent = _user_agent(config.get("sec_user_agent"))
    timeout = max(2, min(int(args.get("timeout_s", 30)), 60))
    max_bytes = max(4096, min(int(args.get("max_bytes", MAX_BYTES)), MAX_BYTES))
    max_facts = max(1, min(int(args.get("max_facts", MAX_FACTS)), MAX_FACTS))

    raw, final_url, content_type, status = _fetch(url, user_agent, timeout, max_bytes)
    if status != 200:
        raise InlineXbrlError("HTTP_STATUS:" + str(status))
    if final_url != url:
        raise InlineXbrlError("SEC_FINAL_URL_MISMATCH")
    if len(raw) > max_bytes:
        raise InlineXbrlError("HTTP_BODY_TOO_LARGE")
    ctype = content_type.casefold()
    if "html" not in ctype and "xhtml" not in ctype and "xml" not in ctype:
        raise InlineXbrlError("SEC_CONTENT_TYPE_NOT_INLINE_DOCUMENT")

    _, rows = _extract(raw, max_facts)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(raw)
    source_sha256 = hashlib.sha256(raw).hexdigest()
    source_path = str(raw_path.relative_to(root)).replace("\\", "/")
    semantic = {
        "schema": SCHEMA,
        "status": "PASS__INLINE_XBRL_FACT_QNAME_ANCHORS_EXTRACTED",
        "source_url": url,
        "source_path": source_path,
        "source_sha256": source_sha256,
        "http_status": status,
        "content_type": content_type,
        "fact_anchor_count": len(rows),
        "anchors": rows,
        "semantic_contract": _semantic_contract(
            rows=rows,
            source_path=source_path,
            source_sha256=source_sha256,
            source_url=url,
        ),
        "source_native_fact_identity_proved": True,
        "nearby_visible_label_semantics_claimed": False,
        "custom_concept_domain_semantics_claimed": False,
        "raw_prose_wsd_claimed": False,
        "policy_adequacy_authority": False,
        "semantic_truth_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    semantic_path.parent.mkdir(parents=True, exist_ok=True)
    semantic_path.write_text(
        json.dumps(semantic, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return semantic
