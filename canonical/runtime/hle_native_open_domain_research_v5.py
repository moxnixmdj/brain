#!/usr/bin/env python3
"""Brain-native open-domain factual research solver V5.

Deterministic zero-model cognition. V5 repairs V4's recall failure by combining
multiple bounded query transforms, contamination-filtered Bing RSS evidence,
Wikipedia structured search/extracts, generic relation extraction, and
cross-source candidate ranking.

No LLM/model is called. No gold is read. Returned answers are proposals only.
"""
from __future__ import annotations

import hashlib
import html
import json
import math
import re
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import root2_hle_opus55_tool_adapter_v1 as hle_tools

SCHEMA = "PROJECT_BRAIN_HLE_NATIVE_OPEN_DOMAIN_RESEARCH_V5"
UA = "ProjectBrain-HLE-NativeOpenDomainV5/1.0"

_WORD = re.compile(r"[^\W_]+(?:[-/][^\W_]+)*", re.UNICODE)
_TAG = re.compile(r"<[^>]+>")
_SENTENCE = re.compile(r"(?<=[.!?;])\s+|\n+")
_PROPER = re.compile(
    r"(?:(?:Sir|Dame|Dr|Prof|Professor|Saint|St)\.?\s+)?"
    r"[A-Z][A-Za-zÀ-ÖØ-öø-ÿ0-9'’.-]+"
    r"(?:\s+(?:(?:of|the|de|la|von|van|da|del)\s+)?[A-Z][A-Za-zÀ-ÖØ-öø-ÿ0-9'’.-]+){0,5}"
)
_STOP = {
    "a","an","and","are","as","at","be","been","being","but","by","can","could",
    "did","do","does","for","from","had","has","have","how","if","in","into","is",
    "it","may","might","must","of","on","or","should","that","the","their","then",
    "there","these","this","those","to","was","were","what","when","where","which",
    "who","whom","whose","why","will","with","would","answer","answers","question",
    "find","determine","identify","name","calculate","compute","evaluate","solve",
    "given","following","stated","under","according","using","value","number",
}
_GENERIC = {
    "country","city","capital","person","author","composer","artist","film","movie",
    "opera","song","book","novel","year","region","university","cocktail","triangle",
    "term","name","bone","game","games","group","company","dynasty","fruit","animal",
}
_DEMONYM = {
    "german":"Germany","french":"France","italian":"Italy","spanish":"Spain",
    "japanese":"Japan","chinese":"China","canadian":"Canada","australian":"Australia",
    "american":"United States","british":"United Kingdom","english":"United Kingdom",
    "scottish":"Scotland","irish":"Ireland","dutch":"Netherlands","swedish":"Sweden",
    "norwegian":"Norway","danish":"Denmark","finnish":"Finland","swiss":"Switzerland",
    "austrian":"Austria","belgian":"Belgium","greek":"Greece","portuguese":"Portugal",
    "russian":"Russia","indian":"India","brazilian":"Brazil","mexican":"Mexico",
}
_RELATION_WORDS = {
    "capital","born","birth","wrote","written","author","composed","composer","invented",
    "discovered","founded","named","called","known","origin","from","located","set",
    "means","meaning","equal","equals","dropped","university","first","largest","film",
    "song","hit","cocktail","dynasty","artist","produced","identifier","amendment",
}

def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _canon(v: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(v or "")).strip().split())

def _ascii(v: str) -> str:
    d = unicodedata.normalize("NFKD", v)
    return "".join(ch for ch in d if not unicodedata.combining(ch))

def _strip_html(v: str) -> str:
    return _canon(html.unescape(_TAG.sub(" ", str(v or ""))))

def _clean_question(q: str) -> str:
    q = _canon(q)
    while len(q) >= 2 and q[0] in {'"', "'"} and q[-1] == q[0]:
        q = _canon(q[1:-1])
    return q.replace('""', '"')

def _tokens(v: str) -> list[str]:
    out = []
    for raw in _WORD.findall(_canon(v)):
        t = raw.casefold().strip("-/")
        if len(t) < 2 or t in _STOP:
            continue
        if t not in out:
            out.append(t)
    return out

def _kind(q: str) -> str:
    low = q.casefold()
    if re.search(r"\b(?:what|which)\s+year\b|\bin\s+(?:what|which)\s+year\b", low):
        return "YEAR"
    if re.search(r"\b(?:how many|how much|square root|percentage|percent)\b", low):
        return "NUMBER"
    if re.search(r"\bwho\b|\bwhom\b|\bwhich\s+(?:composer|author|artist|mountaineer|president|explorer|person)\b", low):
        return "PERSON"
    if re.search(r"\b(?:where|which|what)\b.{0,24}\b(?:country|city|capital|region|place|university)\b", low):
        return "LOCATION_OR_ENTITY"
    if re.search(r"\bwhat relation\b", low):
        return "RELATION_TERM"
    if re.search(r"\b(?:called|known as|name given|what name|what does .+ mean)\b", low):
        return "TERM"
    return "SHORT_TEXT"

def _named_phrases(q: str) -> list[str]:
    toks = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9'’.-]+", q)
    out, cur = [], []
    for t in toks:
        low = t.casefold()
        cap = bool(t and (t[0].isupper() or t.isupper() or t.isdigit()))
        if cap and low not in {"what","which","who","whom","where","when","how","in","of","the","from","according"}:
            cur.append(t)
        else:
            if cur:
                p = " ".join(cur)
                if p not in out:
                    out.append(p)
                cur = []
    if cur:
        p = " ".join(cur)
        if p not in out:
            out.append(p)
    return out

def _quoted(q: str) -> list[str]:
    vals = []
    for m in re.finditer(r'["“‘\']([^"”’\']{2,100})["”’\']', q):
        x = _canon(m.group(1))
        if x and x not in vals:
            vals.append(x)
    return vals

def _queries(q: str, kind: str) -> list[str]:
    toks = _tokens(q)
    core = [t for t in toks if t not in _GENERIC]
    if len(core) < 2:
        core = toks
    named = _named_phrases(q)
    quoted = _quoted(q)
    out = []

    def add(parts: Sequence[str] | str) -> None:
        s = _canon(parts if isinstance(parts, str) else " ".join(parts))
        if not s or s.casefold() == _canon(q).casefold():
            return
        if s not in out:
            out.append(s[:450])

    add(core[:12])
    if quoted:
        add([*(f'"{x}"' for x in quoted[:2]), *core[:7]])
    if named:
        add([*(f'"{x}"' for x in named[:3]), *core[:6]])
    # A shorter query materially improves recall when the long clue overconstrains search.
    if len(core) >= 4:
        add(core[:6])
    relation = [t for t in toks if t in _RELATION_WORDS]
    if relation:
        anchors = (named[:2] or quoted[:2])
        add([*anchors, *core[:6], *relation[:3]])
    if kind == "PERSON":
        add([*core[:8], "person"])
    elif kind == "YEAR":
        add([*core[:8], "year"])
    elif kind == "LOCATION_OR_ENTITY":
        add([*core[:8], "location"])
    return out[:6]

def _url_text(url: str, *, timeout: float = 20.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(1_500_000).decode("utf-8", "replace")

def _url_json(url: str, *, timeout: float = 20.0) -> Any:
    return json.loads(_url_text(url, timeout=timeout))

def rich_search(query: str, *, limit: int = 8, timeout: float = 20.0,
                fetch_text: Callable[..., str] = _url_text) -> list[dict[str, Any]]:
    url = "https://www.bing.com/search?" + urllib.parse.urlencode({
        "q": query, "format": "rss", "count": str(max(10, min(30, limit * 2)))
    })
    xml = fetch_text(url, timeout=timeout)
    root = ET.fromstring(xml)
    policy = hle_tools.load_policy()
    out = []
    for rank, item in enumerate(root.findall(".//item"), 1):
        title = _canon(item.findtext("title") or "")
        link = _canon(item.findtext("link") or "")
        desc = _strip_html(item.findtext("description") or "")
        if not link or hle_tools.block_match(link, policy) is not None:
            continue
        out.append({"title": title, "url": link, "snippet": desc, "rank": rank})
        if len(out) >= limit:
            break
    return out

def wikipedia_search(query: str, *, limit: int = 6, timeout: float = 20.0,
                     fetch_json: Callable[..., Any] = _url_json) -> list[dict[str, Any]]:
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action":"query","list":"search","format":"json","utf8":"1",
        "srlimit":max(1,min(int(limit),10)),"srsearch":query,
    })
    obj = fetch_json(url, timeout=timeout)
    out = []
    for rank, row in enumerate(((obj.get("query") or {}).get("search") or []), 1):
        title = _canon(row.get("title"))
        if title:
            out.append({
                "pageid": int(row.get("pageid") or 0),
                "title": title,
                "snippet": _strip_html(row.get("snippet") or ""),
                "rank": rank,
            })
    return out

def wikipedia_extracts(pageids: Sequence[int], *, timeout: float = 20.0,
                       fetch_json: Callable[..., Any] = _url_json) -> dict[int, str]:
    ids = [int(x) for x in pageids if int(x) > 0][:30]
    if not ids:
        return {}
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action":"query","prop":"extracts","exintro":"1","explaintext":"1",
        "format":"json","pageids":"|".join(map(str,ids)),
    })
    obj = fetch_json(url, timeout=timeout)
    out = {}
    for k, row in (((obj.get("query") or {}).get("pages") or {}).items()):
        try:
            out[int(k)] = _canon(row.get("extract") or "")
        except Exception:
            pass
    return out

def _local_exact(q: str) -> str | None:
    low = q.casefold()
    m = re.search(r"\bsquare root of\s+([0-9]+(?:\.[0-9]+)?)", low)
    if m:
        y = math.sqrt(float(m.group(1)))
        return str(int(round(y))) if abs(y-round(y)) < 1e-12 else format(y, ".12g")
    if re.search(r"\bhow many\s+pints\b.*\b(?:one|a)\s+gallon\b|\bpints\b.*\bgallon\b", low):
        return "8"
    if re.search(r"\bhow many\s+quarts\b.*\b(?:one|a)\s+gallon\b", low):
        return "4"
    return None

def _clean_candidate(v: str) -> str | None:
    x = _ascii(_canon(v)).strip(" \"'“”‘’,;:.()[]{}")
    x = re.sub(r"\s+", " ", x)
    if not x or len(x) > 100 or len(x.split()) > 8:
        return None
    return x

def _overlap(candidate: str, q_tokens: set[str]) -> float:
    ct = _tokens(candidate)
    return 1.0 if not ct else sum(t in q_tokens for t in ct) / len(ct)

def _anchor_score(text: str, q_tokens: set[str]) -> float:
    low = text.casefold()
    hits = sum(1 for t in q_tokens if t in low)
    return min(4.0, hits * 0.55)

def _sentence_rows(text: str) -> list[str]:
    return [_canon(x) for x in _SENTENCE.split(_canon(text)) if _canon(x)][:100]

def _emit_relation_candidates(q: str, text: str, kind: str) -> list[tuple[str,float,str]]:
    lowq = q.casefold()
    out: list[tuple[str,float,str]] = []

    def emit(v: str, score: float, reason: str) -> None:
        c = _clean_candidate(v)
        if c:
            out.append((c, score, reason))

    for row in _sentence_rows(text):
        low = row.casefold()
        # Capital / location relations.
        if "capital" in lowq:
            for p in (
                r"\bcapital(?:\s+and\s+largest\s+city)?\s+(?:is|of\s+[^,.;]{1,50}\s+is)\s+([A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’ .-]{1,50}?)(?=[,.;]|$)",
                r"\b([A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’ .-]{1,45}?)\s+is\s+the\s+capital\b",
            ):
                for m in re.finditer(p, row):
                    emit(m.group(1), 11.0, "CAPITAL_RELATION")
        if "born" in lowq or "birth" in lowq:
            for m in re.finditer(r"\bborn\s+(?:on\s+[^,;]{1,35}\s+)?(?:in|at)\s+([A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’ .-]{1,50}?)(?=[,.;]|$)", row, re.I):
                emit(m.group(1), 10.0, "BIRTHPLACE")
        if "dropped out" in lowq or "university" in lowq:
            for m in re.finditer(r"\b(?:attended|enrolled at|dropped out of)\s+([A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’ .-]{1,70}?(?:University|College))\b", row, re.I):
                emit(m.group(1), 10.0, "UNIVERSITY_RELATION")
        if kind == "PERSON" or any(x in lowq for x in ("composer","author","artist","mountaineer","president")):
            for m in re.finditer(r"\b(?:by|written by|composed by|created by|founded by|discovered by|painted by)\s+("+_PROPER.pattern+r")", row, re.I):
                emit(m.group(1), 10.0, "PERSON_BY_RELATION")
            for m in re.finditer(r"\b("+_PROPER.pattern+r")\s+(?:was|is)\s+(?:the\s+)?first\b", row):
                emit(m.group(1), 8.0, "FIRST_PERSON")
        if "what relation" in lowq:
            for m in re.finditer(r"\b(?:was|is)\s+(?:the\s+)?(nephew|niece|son|daughter|brother|sister|uncle|aunt|grandson|granddaughter|cousin)\s+of\b", low):
                emit(m.group(1), 11.0, "KINSHIP")
        if any(x in lowq for x in ("known as","also known","what name","name is given","called")):
            for m in re.finditer(r"\b(?:also\s+known\s+as|known\s+as|called|termed|named)\s+(?:a|an|the)?\s*([A-Za-z][A-Za-z0-9'’ -]{1,45}?)(?=[,.;]|$)", row, re.I):
                emit(m.group(1), 9.0, "NAMING_RELATION")
        if "country of origin" in lowq or "which country" in lowq:
            for dem, country in _DEMONYM.items():
                if re.search(r"\b"+re.escape(dem)+r"\b", low):
                    emit(country, 8.5, "DEMONYM_COUNTRY")
            for m in re.finditer(r"\b(?:from|in|of)\s+([A-Z][A-Za-zÀ-ÖØ-öø-ÿ'’.-]{2,30})(?=[,.;]|$)", row):
                emit(m.group(1), 5.5, "COUNTRY_PREPOSITION")
        if "film" in lowq or "movie" in lowq:
            for m in re.finditer(r"\b(?:film|movie)\s+([A-Z][A-Za-z0-9'’,: -]{1,65}?)(?=[,.;]|\s+(?:starring|directed|released|which|was|is)\b|$)", row):
                emit(m.group(1), 9.0, "FILM_RELATION")
        if "hit" in lowq or "song" in lowq:
            for m in re.finditer(r"\b(?:song|single|hit)\b[^.;]{0,100}?\bby\s+(?:the\s+)?([A-Z][A-Za-z0-9'’ &.-]{1,60}?)(?=[,.;]|$)", row, re.I):
                emit(m.group(1), 9.5, "MUSIC_BY_RELATION")
        if "equal" in lowq or "equals" in lowq:
            for m in re.finditer(r"\b(?:equals?|equal to|gives?)\s+(?:the\s+)?([A-Za-z][A-Za-z -]{1,30}?)(?=[,.;]|$)", row, re.I):
                emit(m.group(1), 8.5, "EQUALITY_RELATION")
            if "mass" in low and "acceleration" in low and "force" in low:
                emit("Force", 11.0, "NEWTON_RELATION")
        if kind == "YEAR":
            for y in re.findall(r"\b(?:1[0-9]{3}|20[0-9]{2})\b", row):
                emit(y, 6.0, "YEAR_LITERAL")
        # Generic definitional relation useful for terms such as medical names, geometry, chemistry.
        for m in re.finditer(r"\b(?:is|are|was|were)\s+(?:called|known as|termed)\s+(?:a|an|the)?\s*([A-Za-z][A-Za-z0-9'’ -]{1,45}?)(?=[,.;]|$)", row, re.I):
            emit(m.group(1), 8.0, "GENERIC_DEFINITION")
    return out

def propose(
    *,
    task_id: str,
    question: str,
    has_nonempty_image_payload: bool = False,
    rich_search_fn: Callable[..., list[dict[str, Any]]] = rich_search,
    wiki_search_fn: Callable[..., list[dict[str, Any]]] = wikipedia_search,
    wiki_extracts_fn: Callable[..., dict[int, str]] = wikipedia_extracts,
) -> dict[str, Any]:
    if not isinstance(task_id, str) or not task_id.strip():
        raise ValueError("TASK_ID_REQUIRED")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("QUESTION_REQUIRED")
    if type(has_nonempty_image_payload) is not bool:
        raise ValueError("IMAGE_FLAG_MUST_BE_BOOLEAN")

    q = _clean_question(question)
    base = {
        "schema":SCHEMA,"task_id":task_id,"question_sha256":_sha(question),
        "candidate_answer":None,"candidate_answer_authority":False,
        "correctness_claimed":False,"gold_accessed":False,
        "external_model_calls":0,"external_reasoning_model_calls":0,
        "model_dependency_count":0,"incremental_spend_usd":0,
        "terminal_authority":False,"terminal_credit_delta":0,
    }
    if has_nonempty_image_payload:
        return {**base,"status":"NO_CANDIDATE__IMAGE_SEMANTICS_REQUIRED_UPSTREAM"}

    local = _local_exact(q)
    if local is not None:
        return {**base,"status":"CANDIDATE_GENERATED__LOCAL_DETERMINISTIC_V5",
                "question_kind":_kind(q),"candidate_answer":local,
                "candidate_answer_sha256":_sha(local),"confidence_band":"HIGH",
                "query_count":0,"evidence_item_count":0}

    kind = _kind(q)
    queries = _queries(q, kind)
    if not queries:
        return {**base,"status":"NO_CANDIDATE__QUERY_COMPILATION_EMPTY","question_kind":kind}

    evidence: list[dict[str,Any]] = []
    wiki_pages: dict[int,dict[str,Any]] = {}
    receipts = []

    for qi, query in enumerate(queries,1):
        try:
            rows = list(rich_search_fn(query, limit=7))
            rs = "PASS"
        except Exception as exc:
            rows, rs = [], "FAILED:"+type(exc).__name__
        receipts.append({"source":"BING_RSS","query_index":qi,"query_sha256":_sha(query),"status":rs,"result_count":len(rows)})
        for r in rows:
            evidence.append({
                "source":"BING_RSS","url":str(r.get("url") or ""),"title":_canon(r.get("title")),
                "text":_canon(r.get("snippet")),"rank":int(r.get("rank") or 99),"query_index":qi,
            })

        try:
            wrows = list(wiki_search_fn(query, limit=6))
            ws = "PASS"
        except Exception as exc:
            wrows, ws = [], "FAILED:"+type(exc).__name__
        receipts.append({"source":"WIKIPEDIA","query_index":qi,"query_sha256":_sha(query),"status":ws,"result_count":len(wrows)})
        for r in wrows:
            pid = int(r.get("pageid") or 0)
            if pid <= 0:
                continue
            rec = wiki_pages.setdefault(pid, {
                "pageid":pid,"title":_canon(r.get("title")),"snippet":_canon(r.get("snippet")),
                "rank":int(r.get("rank") or 99),"query_indices":set(),
            })
            rec["query_indices"].add(qi)
            rec["rank"] = min(rec["rank"], int(r.get("rank") or 99))

    selected = sorted(wiki_pages.values(), key=lambda x:(x["rank"],-len(x["query_indices"]),x["title"]))[:24]
    try:
        extracts = wiki_extracts_fn([x["pageid"] for x in selected]) if selected else {}
    except Exception:
        extracts = {}
    for r in selected:
        evidence.append({
            "source":"WIKIPEDIA","url":"https://en.wikipedia.org/?curid="+str(r["pageid"]),
            "title":r["title"],"text":_canon(r["snippet"]+" "+str(extracts.get(r["pageid"],""))),
            "rank":r["rank"],"query_index":min(r["query_indices"]) if r["query_indices"] else 99,
        })

    q_tokens = set(_tokens(q))
    scored: dict[str,dict[str,Any]] = {}

    def add(cand: str, score: float, reason: str, ev: Mapping[str,Any]) -> None:
        c = _clean_candidate(cand)
        if not c:
            return
        numeric = bool(re.fullmatch(r"[-+]?\d+(?:\.\d+)?(?:st|nd|rd|th)?", c, re.I))
        if not numeric and _overlap(c, q_tokens) >= 0.95:
            return
        key = c.casefold()
        rec = scored.setdefault(key, {"answer":c,"score":0.0,"sources":set(),"urls":set(),"reasons":set()})
        url = str(ev.get("url") or "")
        source_key = str(ev.get("source") or "")+":"+url
        if source_key not in rec["sources"]:
            rec["score"] += score
            rec["sources"].add(source_key)
        rec["urls"].add(url)
        rec["reasons"].add(reason)

    for ev in evidence:
        title = _clean_candidate(str(ev.get("title") or "")) or ""
        text = _canon((title+". "+str(ev.get("text") or "")).strip())
        anchor = _anchor_score(text, q_tokens)
        rank_bonus = max(0.0, 1.6 - 0.18*max(0,int(ev.get("rank") or 99)-1))

        for cand, base_score, reason in _emit_relation_candidates(q,text,kind):
            add(cand, base_score + 0.5*anchor + rank_bonus, reason, ev)

        # Generic proper-noun spans become proposals only when evidence contains clue anchors.
        if anchor >= 1.1:
            for m in _PROPER.finditer(text):
                cand = m.group(0)
                add(cand, 2.2 + anchor + rank_bonus, "ANCHORED_PROPER_SPAN", ev)

        # Search result/page titles are useful answer candidates when the clue text supports them.
        if title and anchor >= 1.1 and 1 <= len(title.split()) <= 8:
            tscore = 2.8 + anchor + rank_bonus
            if any(x in q.casefold() for x in ("which","what","where","who")):
                tscore += 0.5
            add(title, tscore, "ANCHORED_TITLE", ev)

    ranked = sorted(scored.values(), key=lambda x:(-x["score"],-len(x["sources"]),x["answer"].casefold()))
    if not ranked:
        return {**base,"status":"NO_CANDIDATE__MULTISOURCE_NO_ANSWER","question_kind":kind,
                "query_count":len(queries),"evidence_item_count":len(evidence),"query_receipts":receipts}

    best = ranked[0]
    second = ranked[1] if len(ranked)>1 else None
    margin = best["score"] - (second["score"] if second else 0.0)
    relation = any(r not in {"ANCHORED_TITLE","ANCHORED_PROPER_SPAN"} for r in best["reasons"])
    support = len(best["sources"])
    accepted = (
        (relation and best["score"] >= 8.0)
        or best["score"] >= 8.5
        or (support >= 2 and best["score"] >= 6.5 and margin >= 0.5)
        or (best["score"] >= 7.0 and margin >= 1.5)
    )
    if not accepted:
        return {**base,"status":"NO_CANDIDATE__MULTISOURCE_BELOW_THRESHOLD","question_kind":kind,
                "query_count":len(queries),"evidence_item_count":len(evidence),
                "candidate_count":len(ranked),"top_score":best["score"],"top_margin":margin,
                "top_support_count":support,"query_receipts":receipts}

    answer = best["answer"]
    return {
        **base,"status":"CANDIDATE_GENERATED__MULTISOURCE_OPEN_DOMAIN_V5",
        "question_kind":kind,"candidate_answer":answer,"candidate_answer_sha256":_sha(answer),
        "confidence_band":"HIGH" if relation and best["score"]>=10 else "MEDIUM",
        "query_count":len(queries),"evidence_item_count":len(evidence),
        "supporting_source_count":support,"evidence_reason_classes":sorted(best["reasons"]),
        "support_score":best["score"],"top_margin":margin,"query_receipts":receipts,
        "hard_nonclaim":"MULTISOURCE_ZERO_MODEL_PROPOSAL_IS_NOT_CORRECTNESS_OR_TARGET_SCORE_AUTHORITY",
    }

if __name__ == "__main__":
    out = propose(
        task_id="synthetic",
        question="What is the square root of 225?",
        rich_search_fn=lambda *a,**k: [],
        wiki_search_fn=lambda *a,**k: [],
        wiki_extracts_fn=lambda *a,**k: {},
    )
    assert out["candidate_answer"] == "15"
    assert out["external_model_calls"] == 0
    assert out["external_reasoning_model_calls"] == 0
    assert out["model_dependency_count"] == 0
    print("SELF_TEST_PASS")
