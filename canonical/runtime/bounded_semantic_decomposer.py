"""Fail-closed dual-route semantic decomposer for a decidable source subset.

Purpose
-------
Reduce M0A without pretending arbitrary language understanding is solved.

Two structurally different deterministic routes independently:
1. segment raw text into sentence/line spans;
2. classify each span using disjoint implementations of the same frozen lexical
   contract;
3. reject compound/ambiguous spans instead of inventing semantics.

A PASS means only that this *bounded lexical subset* has an independently
reproducible decomposition. It is not a general natural-language semantic
parser and carries zero whole-family credit.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import re
from typing import Iterable

SCHEMA = "BRAIN_DUAL_ROUTE_BOUNDED_SEMANTIC_DECOMPOSER_V1"

# Frozen lexical contract. Multiple simultaneously matching semantic classes are
# deliberately rejected because lexical evidence is then insufficient to choose.
CLASS_PATTERNS = {
    "EVALUATION": re.compile(r"\b(verify|verification|test|tests|tested|pass|passes|fail|fails|score|benchmark|acceptance)\b", re.I),
    "RESOURCE": re.compile(r"\b(memory|cpu|gpu|storage|latency|throughput|time\s+limit|budget|cost|spend)\b", re.I),
    "SOURCE_BOUNDARY": re.compile(r"\b(source|sources|search|internet|web|hidden|verifier|external|leak|contaminat\w*)\b", re.I),
    "ENVIRONMENT": re.compile(r"\b(path|file|directory|folder|os|runtime|package|permission|network|container|environment)\b", re.I),
    "BEHAVIOR": re.compile(r"\b(must|shall|should|required|requires|need(?:s)?\s+to|ensure|produce|write|return|output|create|delete|reject|accept|validate|preserve|include|exclude|emit|raise|read|store|save|use)\b", re.I),
}

TOKEN_CLASS = {
    "verify": "EVALUATION", "verification": "EVALUATION", "test": "EVALUATION",
    "tests": "EVALUATION", "tested": "EVALUATION", "pass": "EVALUATION",
    "passes": "EVALUATION", "fail": "EVALUATION", "fails": "EVALUATION",
    "score": "EVALUATION", "benchmark": "EVALUATION", "acceptance": "EVALUATION",
    "memory": "RESOURCE", "cpu": "RESOURCE", "gpu": "RESOURCE",
    "storage": "RESOURCE", "latency": "RESOURCE", "throughput": "RESOURCE",
    "budget": "RESOURCE", "cost": "RESOURCE", "spend": "RESOURCE",
    "source": "SOURCE_BOUNDARY", "sources": "SOURCE_BOUNDARY",
    "search": "SOURCE_BOUNDARY", "internet": "SOURCE_BOUNDARY", "web": "SOURCE_BOUNDARY",
    "hidden": "SOURCE_BOUNDARY", "verifier": "SOURCE_BOUNDARY",
    "external": "SOURCE_BOUNDARY", "leak": "SOURCE_BOUNDARY",
    "path": "ENVIRONMENT", "file": "ENVIRONMENT", "directory": "ENVIRONMENT",
    "folder": "ENVIRONMENT", "os": "ENVIRONMENT", "runtime": "ENVIRONMENT",
    "package": "ENVIRONMENT", "permission": "ENVIRONMENT", "network": "ENVIRONMENT",
    "container": "ENVIRONMENT", "environment": "ENVIRONMENT",
    "must": "BEHAVIOR", "shall": "BEHAVIOR", "should": "BEHAVIOR",
    "required": "BEHAVIOR", "requires": "BEHAVIOR", "ensure": "BEHAVIOR",
    "produce": "BEHAVIOR", "write": "BEHAVIOR", "return": "BEHAVIOR",
    "output": "BEHAVIOR", "create": "BEHAVIOR", "delete": "BEHAVIOR",
    "reject": "BEHAVIOR", "accept": "BEHAVIOR", "validate": "BEHAVIOR",
    "preserve": "BEHAVIOR", "include": "BEHAVIOR", "exclude": "BEHAVIOR",
    "emit": "BEHAVIOR", "raise": "BEHAVIOR", "read": "BEHAVIOR",
    "store": "BEHAVIOR", "save": "BEHAVIOR", "use": "BEHAVIOR",
}

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_'-]*")
MODAL_OR_ACTION_RE = re.compile(
    r"\b(must(?:\s+not)?|shall(?:\s+not)?|should(?:\s+not)?|required|requires|"
    r"need(?:s)?\s+to|ensure|produce|write|return|output|create|delete|reject|"
    r"accept|validate|preserve|include|exclude|emit|raise|read|store|save|use)\b",
    re.I,
)
COMPOUND_RE = re.compile(r"\b(and|or|but|unless|except|while|whereas)\b", re.I)


@dataclass(frozen=True)
class Unit:
    start: int
    end: int
    text: str
    semantic_class: str
    fingerprint: str


def _fingerprint(text: str, semantic_class: str) -> str:
    canon = " ".join(text.lower().split())
    return hashlib.sha256((semantic_class + "\0" + canon).encode("utf-8")).hexdigest()


def _route_regex_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for m in re.finditer(r"[^.!?\n]+(?:[.!?]+|\n|$)", text):
        s, e = m.span()
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if s < e:
            spans.append((s, e))
    return spans


def _route_scanner_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    i = 0
    while i < len(text):
        if text[i] in ".!?\n":
            end = i + 1
            s, e = start, end
            while s < e and text[s].isspace():
                s += 1
            while e > s and text[e - 1].isspace():
                e -= 1
            if s < e:
                spans.append((s, e))
            start = end
        i += 1
    s, e = start, len(text)
    while s < e and text[s].isspace():
        s += 1
    while e > s and text[e - 1].isspace():
        e -= 1
    if s < e:
        spans.append((s, e))
    return spans


def _classify_regex(span: str) -> tuple[str, list[str]]:
    hits = [name for name, pat in CLASS_PATTERNS.items() if pat.search(span)]
    if not hits:
        return "INFORMATIVE", []
    if len(hits) > 1:
        return "AMBIGUOUS", sorted(hits)
    return hits[0], []


def _classify_tokens(span: str) -> tuple[str, list[str]]:
    hits: set[str] = set()
    words = [m.group(0).lower() for m in WORD_RE.finditer(span)]
    for word in words:
        cls = TOKEN_CLASS.get(word)
        if cls:
            hits.add(cls)
        elif word.startswith("contaminat"):
            hits.add("SOURCE_BOUNDARY")
    # Multi-token phrases intentionally handled independently from route A.
    low = " ".join(words)
    if "time limit" in low:
        hits.add("RESOURCE")
    if "needs to" in low or "need to" in low:
        hits.add("BEHAVIOR")
    if not hits:
        return "INFORMATIVE", []
    if len(hits) > 1:
        return "AMBIGUOUS", sorted(hits)
    return next(iter(hits)), []


def _compound_risk(span: str) -> bool:
    # One lexical obligation per unit is the decidable contract. Repeated action
    # markers or coordinating conjunctions around operative language fail closed.
    action_count = len(MODAL_OR_ACTION_RE.findall(span))
    return action_count > 1 or (action_count >= 1 and bool(COMPOUND_RE.search(span)))


def _units(text: str, spans: Iterable[tuple[int, int]], classifier) -> tuple[list[Unit], list[str]]:
    units: list[Unit] = []
    errors: list[str] = []
    for s, e in spans:
        raw = text[s:e]
        semantic_class, ambiguity = classifier(raw)
        if semantic_class == "AMBIGUOUS":
            errors.append(f"SEMANTIC_CLASS_AMBIGUOUS:{s}:{e}:{','.join(ambiguity)}")
            continue
        if semantic_class != "INFORMATIVE" and _compound_risk(raw):
            errors.append(f"COMPOUND_OPERATIVE_SPAN:{s}:{e}")
            continue
        units.append(Unit(s, e, raw, semantic_class, _fingerprint(raw, semantic_class)))
    return units, errors


def decompose(text: str) -> dict:
    if not isinstance(text, str) or not text.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["SOURCE_EMPTY"], "units": []}

    a_units, a_errors = _units(text, _route_regex_spans(text), _classify_regex)
    b_units, b_errors = _units(text, _route_scanner_spans(text), _classify_tokens)

    errors = sorted(set(a_errors + b_errors))
    a_sig = [(u.start, u.end, u.semantic_class, u.fingerprint) for u in a_units]
    b_sig = [(u.start, u.end, u.semantic_class, u.fingerprint) for u in b_units]
    if a_sig != b_sig:
        errors.append("INDEPENDENT_DECOMPOSITION_DISAGREEMENT")

    # Every non-whitespace source character must belong to exactly one returned
    # unit when we pass. This prevents silent deletion.
    if not errors:
        covered: set[int] = set()
        for u in a_units:
            covered.update(i for i in range(u.start, u.end) if not text[i].isspace())
        expected = {i for i, ch in enumerate(text) if not ch.isspace()}
        if covered != expected:
            errors.append("SOURCE_COVERAGE_MISMATCH")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "units": [],
            "terminal_authority": False,
        }

    return {
        "schema": SCHEMA,
        "status": "CONSENSUS",
        "unit_count": len(a_units),
        "units": [asdict(x) for x in a_units],
        "terminal_authority": False,
        "scope": "BOUNDED_SINGLE_OBLIGATION_LEXICAL_SOURCE_SUBSET_ONLY",
        "rule": "DISAGREEMENT_COMPOUND_OR_MULTI_CLASS_SOURCE_FAILS_CLOSED",
    }
