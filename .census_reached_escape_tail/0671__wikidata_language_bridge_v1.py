#!/usr/bin/env python3
"""Zero-cost Wikidata multilingual language bridge for retrieval query expansion.

This module treats Wikidata labels and aliases as external knowledge used to
produce candidate query variants. It is not a translator, semantic oracle, or
completeness proof. Failures remain UNKNOWN to the caller.

The capability is internal: deterministic request construction, normalization,
provenance capture, dedupe, and authority boundaries live here. Knowledge
(labels/aliases) remains external JIT.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
import unicodedata
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_WIKIDATA_LANGUAGE_BRIDGE_V1"
API = "https://www.wikidata.org/w/api.php"
USER_AGENT = "ProjectBrain-RetrievalLanguageBridge/1.0"
DEFAULT_LANGUAGES = ("zh", "ja", "ko", "ru", "ar", "es", "fr", "de", "pt")


class LanguageBridgeError(RuntimeError):
    pass


def _canon(value: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).strip().split())


def _request_json(params: Mapping[str, Any], *, opener=None, timeout: int = 20) -> Mapping[str, Any]:
    payload = {
        "format": "json",
        "formatversion": "2",
        "origin": "*",
        **{str(k): str(v) for k, v in params.items() if v is not None},
    }
    url = API + "?" + urllib.parse.urlencode(payload)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    opener = opener or urllib.request.urlopen
    try:
        with opener(req, timeout=max(2, min(int(timeout), 30))) as resp:
            raw = resp.read(5_000_000)
    except urllib.error.HTTPError as exc:
        raise LanguageBridgeError(f"WIKIDATA_HTTP_{getattr(exc,'code','ERROR')}") from exc
    except Exception as exc:
        raise LanguageBridgeError("WIKIDATA_REQUEST_FAILED:" + type(exc).__name__) from exc
    try:
        data = json.loads(raw.decode("utf-8", "replace"))
    except Exception as exc:
        raise LanguageBridgeError("WIKIDATA_JSON_INVALID") from exc
    if not isinstance(data, Mapping):
        raise LanguageBridgeError("WIKIDATA_RESPONSE_MAPPING_REQUIRED")
    if data.get("error"):
        raise LanguageBridgeError("WIKIDATA_API_ERROR:" + _canon(data.get("error")))
    return data


def _search_ids(anchor: str, *, opener=None, limit: int = 3) -> list[str]:
    data = _request_json({
        "action": "wbsearchentities",
        "search": anchor,
        "language": "en",
        "uselang": "en",
        "type": "item",
        "limit": max(1, min(int(limit), 10)),
    }, opener=opener)
    rows = data.get("search") or []
    out: list[str] = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            qid = _canon(row.get("id"))
            if qid.startswith("Q") and qid[1:].isdigit() and qid not in out:
                out.append(qid)
    return out


def expand(
    anchors: Sequence[str],
    *,
    languages: Sequence[str] = DEFAULT_LANGUAGES,
    per_anchor_entities: int = 3,
    opener=None,
) -> dict[str, Any]:
    clean_anchors: list[str] = []
    for raw in anchors:
        a = _canon(raw)
        if a and a.casefold() not in {x.casefold() for x in clean_anchors}:
            clean_anchors.append(a)
    if not clean_anchors:
        raise ValueError("AT_LEAST_ONE_ANCHOR_REQUIRED")

    langs = []
    for raw in languages:
        lang = _canon(raw).lower()
        if lang and lang not in langs:
            langs.append(lang)
    if not langs:
        raise ValueError("AT_LEAST_ONE_LANGUAGE_REQUIRED")

    qids_by_anchor: dict[str, list[str]] = {}
    all_qids: list[str] = []
    for anchor in clean_anchors:
        ids = _search_ids(anchor, opener=opener, limit=per_anchor_entities)
        qids_by_anchor[anchor] = ids
        for qid in ids:
            if qid not in all_qids:
                all_qids.append(qid)

    if not all_qids:
        return {
            "schema": SCHEMA,
            "status": "NO_ENTITY_MATCH__UNKNOWN_NOT_NONEXISTENCE",
            "anchors": clean_anchors,
            "languages": langs,
            "variants": [],
            "complete": False,
            "semantic_equivalence_verified": False,
            "incremental_spend_usd": 0,
            "authority": "CANDIDATE_QUERY_EXPANSION_ONLY",
        }

    data = _request_json({
        "action": "wbgetentities",
        "ids": "|".join(all_qids),
        "props": "labels|aliases",
        "languages": "|".join(langs),
        "languagefallback": "0",
    }, opener=opener)

    entities = data.get("entities") or {}
    if not isinstance(entities, Mapping):
        raise LanguageBridgeError("WIKIDATA_ENTITIES_MAPPING_REQUIRED")

    variants: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for qid in all_qids:
        ent = entities.get(qid)
        if not isinstance(ent, Mapping):
            continue
        labels = ent.get("labels") or {}
        aliases = ent.get("aliases") or {}
        if not isinstance(labels, Mapping):
            labels = {}
        if not isinstance(aliases, Mapping):
            aliases = {}
        for lang in langs:
            values: list[tuple[str, str]] = []
            row = labels.get(lang)
            if isinstance(row, Mapping):
                values.append((_canon(row.get("value")), "LABEL"))
            arows = aliases.get(lang) or []
            if isinstance(arows, list):
                for arow in arows:
                    if isinstance(arow, Mapping):
                        values.append((_canon(arow.get("value")), "ALIAS"))
            for value, kind in values:
                if not value:
                    continue
                key = (lang, value.casefold())
                if key in seen:
                    continue
                seen.add(key)
                variants.append({
                    "text": value,
                    "language": lang,
                    "kind": kind,
                    "qid": qid,
                    "source": "WIKIDATA",
                    "semantic_equivalence_verified": False,
                })

    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_VARIANTS_GENERATED",
        "anchors": clean_anchors,
        "languages": langs,
        "entities_by_anchor": qids_by_anchor,
        "variants": variants,
        "complete": False,
        "semantic_equivalence_verified": False,
        "incremental_spend_usd": 0,
        "authority": "CANDIDATE_QUERY_EXPANSION_ONLY",
        "hard_rules": [
            "WIKIDATA_LABEL_OR_ALIAS_IS_NOT_ACCEPTANCE_EVIDENCE",
            "NO_ENTITY_MATCH_IS_UNKNOWN_NOT_NONEXISTENCE",
            "NO_ALL_LANGUAGE_OR_ALL_SYNONYM_COMPLETENESS_CLAIM",
            "DOWNSTREAM_WITNESS_MUST_BE_INDEPENDENTLY_VERIFIED",
        ],
    }
