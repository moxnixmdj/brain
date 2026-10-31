"""The answer is in the artifact. Deliver it, or refuse — never return a count in its place.

Measured 2026-10-31 on `main` f3d2e21, 62 human software-engineering sentences through
``live_brain_route_admission_v1.solve``: seven of the twelve PASSes were wrong answers, and
five of those seven share one skeleton -- an **inspector that counts** was chosen for a
request that asked to **extract**.

    "Find every caller of build_plan in .../swe_typed_plan_v1.py"
      result    : {"caller_index_size": 8, "call_edge_count": 236739, "symbol_count": 92726}
      artifact  : {"callers_of": {..., "build_plan": ["plan_report"],
                                  "_family_terms": ["_resolve_family", "build_plan", ...]}}
      verdict   : PASS__..._EXACT_SEMANTIC_ACCEPTANCE_VERIFIED

    "List the functions in .../swe_typed_plan_v1.py"
      result    : {"function_count": 10}
      artifact  : {"files": [{"functions": ["_effect_consistent", "_execution_template", ...]}]}

    "Show the imports of .../swe_typed_plan_v1.py"
      result    : {"distinct_imported_module_count": 5}
      artifact  : {"distinct_imported_modules": ["__future__", "canonical", "pathlib", ...]}

Three times the exact bytes the caller asked for were written to disk, hashed, verified, and
then thrown away in favour of a number that happens to be true.  This is the same defect as the
printed-verdict bug (`tool_truth_errors` reading the envelope instead of the stdout) one layer
deeper: the door's *result* is a summary, the *artifact* is the answer, and nothing reconciled
them.

This module is that reconciliation, and it has exactly two outcomes:

  * the artifact can answer the sentence -> the matching field is DELIVERED on the result as
    ``answer`` (bounded, with its count and its source field);
  * it cannot -> the run is refused with ``ANSWER_SHAPE_UNSERVED:<cid>:<noun>``, because a
    number is not a list and returning one is a lie the certificate cannot see.

What it deliberately does NOT do: invent, summarise, or re-rank.  Projection is by field name
from a declared vocabulary, the value is copied verbatim, and every alias that matched is
recorded so a reviewer can disagree with the match.

Scope is narrow on purpose.  A sentence is only judged when it asks to ENUMERATE -- an explicit
list/find-every verb, or a plural noun the table knows.  "Show the status of the working tree"
and "What changed in the last 5 commits" are not enumerations of a named collection and are
untouched.  A sentence that asks ``how many`` is the one case where a count IS the answer, and
it is explicitly allowed.

Authority: NONE.  Credit: 0.  Model dependency: 0.  Incremental spend: $0.
"""
from __future__ import annotations

import json
import pathlib
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_ANSWER_SHAPE_V1"

# An artifact bigger than this is not read to answer a sentence.  ``code.index`` writes 108 MB
# for this repository; loading it costs ~2 s and 1.5 GB of RSS to look for a field that is not
# there.  Over the cap the run is refused with its reason rather than paid for.
MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
# Projection never walks more than this many containers.  The shapes in this repository are
# three levels deep (files[].functions, modules[].calls, callers_of[k]); a deeper walk would be
# a search, and a search is not a projection.
MAX_NODES = 400

# Which field names may answer which asked noun.  Plural and singular spellings are listed
# because adapters are not consistent, and the ALIAS IS RECORDED when it matches so the choice
# is auditable rather than implicit.
_ALIASES: dict[str, tuple[str, ...]] = {
    "caller": ("callers_of", "callers", "call_sites", "call_edges", "callers"),
    "function": ("functions", "function_names", "defs", "definitions"),
    "class": ("classes", "class_names"),
    "import": ("imports", "distinct_imported_modules", "imported_modules", "modules"),
    "definition": ("definitions", "symbols", "functions"),
    "symbol": ("symbols", "definitions"),
    "reference": ("references", "reference_sites", "references_of"),
    "file": ("files", "paths"),
    "commit": ("rows", "commits"),
    "branch": ("rows", "branches"),
    "test": ("tests", "results", "rows", "failures", "failed_tests"),
    "duplicate": ("duplicates", "clones", "clone_pairs", "duplicate_groups"),
    "dead": ("dead_symbols", "dead_code"),
}

# The noun table.  ``pattern`` matches how a human names the thing; the key is the canonical
# noun used in messages and in the delivered answer.
_NOUNS: tuple[tuple[str, "re.Pattern[str]"], ...] = tuple(
    (name, re.compile(pattern, re.I)) for name, pattern in (
        ("caller", r"\b(callers?|call\s?sites?|who\s+calls)\b"),
        ("function", r"\b(functions?|methods?)\b"),
        ("class", r"\b(classes)\b"),
        ("import", r"\b(imports?|imported\s+modules?)\b"),
        ("definition", r"\b(definitions?)\b"),
        ("symbol", r"\b(symbols?)\b"),
        ("reference", r"\b(references?|usages?)\b"),
        ("file", r"\b(files?|paths?)\b"),
        ("commit", r"\b(commits?)\b"),
        ("branch", r"\b(branches?)\b"),
        ("test", r"\b(tests?)\b"),
        ("duplicate", r"\b(duplicat\w*|clones?|copy[- ]paste)\b"),
        ("dead", r"\b(dead\s+(?:code|symbols?)|unused|uncalled|never\s+called)\b"),
    )
)

# "list X" / "find every X" / "what are the X" / "name every X" -- the sentence is asking for
# the members, not for their number.
_ENUMERATE_VERB = re.compile(
    r"\b(list|enumerate|name|show|give\s+me|print|dump)\b|\bfind\s+(every|all)\b|"
    r"\bwhat\s+are\s+the\b|\bwhich\b|\bwho\b", re.I)
# "find <a thing you enumerate>" -- "find duplicated code", "find dead code", "find callers".
# Bare "find" is NOT generally an enumeration verb: "find the fault in X", "find the slow
# function" are lookups, and treating them as enumerations would refuse work that a real
# answer could serve.  The noun list after it is what makes it one.
_FIND_NOUN = re.compile(
    r"\bfind\b[^.]{0,32}\b(duplicat\w*|clones?|dead\s+(?:code|symbols?)|callers?|usages?)\b", re.I)

# "how many" is the one shape where the count is the answer.
_COUNT_ASK = re.compile(r"\bhow\s+many\b|\bcount\s+(?:the|of)\b|\bnumber\s+of\b", re.I)

_COUNT_FIELD = re.compile(r"(_count|_size|_total|_len|_n)$", re.I)
_NON_ANSWER_FIELDS = frozenset({
    "adapter", "schema", "capability_id", "capability", "output_path", "result_path",
    "report_path", "output_sha256", "output_verified", "verified", "dependency", "op",
    "repo_root", "totals", "unparseable", "unparseable_paths", "reason", "status", "gate",
    "complete", "observed_effect", "source_root", "analysis_context", "substrate", "modules",
})


def asked(goal: str) -> dict[str, Any] | None:
    """The shape this sentence asks its answer to have, or ``None`` if it states no shape.

    ``None`` is the common case and must stay cheap: one count-ask test and one verb test
    before any noun work.
    """
    text = str(goal or "")
    if not text.strip():
        return None
    if _COUNT_ASK.search(text):
        # A count IS the answer here.  The gate stays out of the way.
        return None
    verb = _ENUMERATE_VERB.search(text) or _FIND_NOUN.search(text)
    if verb is None:
        return None
    # The noun the sentence asks about is the FIRST one it names, not the first one this
    # table happens to list.  Read in table order, "Which commit broke the tests" answered
    # about *tests* -- and that sentence is one of the five answers that is already correct,
    # so a gate written that way would have broken working behaviour to fix broken behaviour.
    first: tuple[int, str, "re.Match[str]"] | None = None
    for noun, pattern in _NOUNS:
        hit = pattern.search(text)
        if hit is None:
            continue
        if first is None or hit.start() < first[0]:
            first = (hit.start(), noun, hit)
    if first is not None:
        _, noun, hit = first
        # A plural spelling, or an explicit list/find-every verb, is what makes this an
        # enumeration.  "Show the definition of X" is included on purpose: the definition is
        # a thing, and a count of definitions is not it.
        token = hit.group(1)
        plural = bool(re.search(r"(s|es)$", token, re.I)) or token.lower() in {
            "call", "call site", "dead code", "copy-paste"}
        # "WRITE ITS NAME TO <file>" IS NOT "NAME THEM".  The bare word `name` was read as an
        # imperative to enumerate, so "Which function in <d>/app is at fault? Write its name to
        # <d>/answer.json" was classified ENUMERATE (aliases functions/function_names/defs) while
        # the adapter answered with a single `answer` field.  The artifact was on disk and held the
        # right value; the gate refused it with ANSWER_SHAPE_UNSERVED:NO_MATCHING_FIELD.  Measured
        # 2026-10-31 on four ladder jobs (localize_fault, find_flaky_test, uncovered_function,
        # perf_regression): four correct answers reported as refusals.  An enumeration is asked for
        # by a PLURAL object ("write the names"), by "name them/each/all", or by an explicit
        # list/every verb -- never by the singular noun phrase "its name".
        explicit = bool(re.search(
            r"\b(?:list|enumerate|name\s+(?:them|each|all)|"
            r"(?:find|show|collect|write)\s+(?:every|all))\b", text, re.I))
        if plural or explicit or noun in {"caller", "duplicate", "dead", "definition"}:
            return {"schema": SCHEMA, "kind": "ENUMERATE", "noun": noun, "token": token,
                    "aliases": list(_ALIASES.get(noun, ())), "verb": verb.group(0).lower()}
    return None


def _is_answer_value(value: Any) -> bool:
    # Presence of the answering field, not positive cardinality, is evidence:
    # an analysis can legitimately find no callers/imports/functions.  A missing
    # field is still refused by _project; do not turn a present empty set into one.
    if isinstance(value, (Mapping, list, tuple)):
        return True
    if isinstance(value, str):
        return bool(value.strip())
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _project(payload: Mapping[str, Any], shape: Mapping[str, Any]) -> tuple[str, Any] | None:
    """The first (field, value) in ``payload`` whose field name answers ``shape``.

    Breadth-first over containers, so a top-level field always beats a nested one: the
    adapter's own summary is the most specific statement of what it produced.
    """
    aliases = {a.lower() for a in shape.get("aliases") or ()}
    if not aliases:
        return None
    queue: list[tuple[Any, str, int]] = [(payload, "", 0)]
    seen = 0
    while queue and seen < MAX_NODES:
        node, prefix, depth = queue.pop(0)
        items = node.items() if isinstance(node, Mapping) else enumerate(node)
        for key, value in items:
            seen += 1
            if seen > MAX_NODES:
                break
            name = str(key)
            low = name.lower()
            path = (prefix + "." + name) if prefix else name
            # A field under `totals` is a summary even when its name is the noun:
            # `totals.functions = 10` was answering "list the functions" before
            # `files[0].functions = [...]` was looked at.  The path decides, not the leaf.
            under_summary = any(seg in _NON_ANSWER_FIELDS for seg in path.split(".")[:-1])
            # AN ELEMENT OF A LIST IS NOT THE COLLECTION.  Measured 2026-10-31 (V4 §5):
            # "Which tests does <f> break" was delivered ``records.0.tests`` = 0 -- the test
            # count of the FIRST record of an audit, because the walk descended into the list
            # and matched the noun inside element 0.  A scalar under a numeric segment is one
            # item of an enumeration, never the enumeration itself; skipping it turns a
            # certified wrong number into a named refusal (ANSWER_SHAPE_UNSERVED).
            if (shape.get("kind") == "ENUMERATE"
                    and not isinstance(value, (Mapping, list, tuple))
                    and any(seg.isdigit() for seg in path.split(".")[:-1])):
                continue
            if (low in aliases and low not in _NON_ANSWER_FIELDS and not under_summary
                    and not _COUNT_FIELD.search(low) and _is_answer_value(value)):
                return path, value
            if depth < 2 and isinstance(value, (Mapping, list, tuple)):
                queue.append((value, path, depth + 1))
    return None


def _artifact_path(inner: Mapping[str, Any]) -> pathlib.Path | None:
    for key in ("output_path", "result_path", "report_path"):
        raw = inner.get(key)
        if isinstance(raw, str) and raw.strip():
            return pathlib.Path(raw)
    return None


def _read_artifact(path: pathlib.Path, root: pathlib.Path | None) -> tuple[Any, str | None]:
    """The parsed artifact, or a reason it could not be used."""
    try:
        resolved = path.resolve()
        if root is not None and resolved != root.resolve() and root.resolve() not in resolved.parents:
            return None, "ARTIFACT_OUTSIDE_REPOSITORY"
        if not resolved.is_file():
            return None, "ARTIFACT_MISSING"
        size = resolved.stat().st_size
        if size > MAX_ARTIFACT_BYTES:
            return None, "ARTIFACT_TOO_LARGE:%d" % size
        return json.loads(resolved.read_text(encoding="utf-8", errors="replace")), None
    except (OSError, ValueError) as exc:
        return None, "ARTIFACT_UNREADABLE:" + type(exc).__name__


def _narrow(value: Any, goal: str) -> Any:
    """If the sentence names a key of a mapping answer, deliver that entry, not the whole map.

    ``callers_of`` holds every callee in the file (42 here).  "every caller of build_plan"
    means one of them, and handing back the map would repeat the original mistake in a new
    shape -- a correct answer buried in data nobody asked for.
    """
    if not isinstance(value, Mapping):
        return value
    text = str(goal or "")
    for key in value:
        name = str(key)
        if len(name) >= 3 and re.search(r"(?<![A-Za-z0-9_])" + re.escape(name) + r"(?![A-Za-z0-9_])", text):
            return {name: value[key]}
    return value


def _bounded(value: Any, limit: int = 50) -> Any:
    if isinstance(value, Mapping):
        keys = list(value)[:limit]
        return {k: value[k] for k in keys}
    if isinstance(value, (list, tuple)):
        return list(value[:limit])
    return value


# A LOOKUP IS ANSWERED BY WHAT THE ROW OBSERVED.  ``asked()`` deliberately returns None for
# a state question -- "Show the status of the working tree" is not a collection, and the law
# ``test_a_lookup_and_a_count_are_not_enumerations`` pins that.  But returning None also meant
# returning nothing at all: measured 2026-10-31, that sentence PASSed on
# ``git.repository.operate.v1`` with ``answer: null`` while the row's ``observed_effect`` held
# ``{op: status, branch: ..., entry_count: 0, staged: 0}`` -- the answer was produced and then
# dropped on the floor.  That is the "correct but no answer" class (6 of 61 in the V4 baseline),
# and the fix is not a new taxonomy: every row already states what it observed, so a PASS that
# answered nothing hands over that statement.
_OBSERVATION_FIELDS: tuple[str, ...] = ("observed_effect", "observation", "state", "snapshot")


def _observation_hit(inner: Mapping[str, Any]) -> tuple[str, Mapping[str, Any]] | None:
    for field in _OBSERVATION_FIELDS:
        value = inner.get(field)
        if isinstance(value, Mapping) and value:
            return field, value
    return None


def deliver_observation(result: "dict[str, Any]") -> list[str]:
    """Hand over what a row observed when the sentence asked no collection.

    Only called when the result already PASSed and nothing has been delivered, so it can add
    an answer but never replace one, and it never changes a verdict.
    """
    if result.get("answer") is not None:
        return []
    rows: list[Mapping[str, Any]] = [r for r in (result.get("execution") or []) if isinstance(r, Mapping)]
    if not rows:
        for step in ((result.get("composer_execution") or {}).get("steps") or []):
            if isinstance(step, Mapping) and isinstance(step.get("result"), Mapping):
                rows.append({"capability_id": step.get("capability_id"), "result": step["result"]})
    for row in rows:
        inner = row.get("result") if isinstance(row.get("result"), Mapping) else None
        if inner is None:
            continue
        hit = _observation_hit(inner)
        if hit is None:
            continue
        field, value = hit
        count = len(value)
        shown = _bounded(dict(value))
        shown_len = len(shown) if isinstance(shown, (Mapping, list, tuple)) else 1
        result["answer"] = {
            "schema": SCHEMA,
            "noun": "observation",
            "field": field,
            "source": "result",
            "count": count,
            "value": shown,
            "truncated": shown_len < count,
        }
        return []
    return []


def deliver(goal: str, result: Mapping[str, Any], root: pathlib.Path | None = None) -> list[str]:
    """Deliver the answer the sentence asked for, or say why it cannot be delivered.

    Mutates ``result["answer"]`` when a projection succeeds -- the gate's job is not only to
    refuse, it is to hand over the bytes that were already produced.  Returns the refusal
    reasons; an empty list means the result is answerable as it stands.
    """
    shape = asked(goal)
    if shape is None:
        return deliver_observation(result)  # type: ignore[arg-type]
    rows: list[Mapping[str, Any]] = [r for r in (result.get("execution") or []) if isinstance(r, Mapping)]
    if not rows:
        for step in ((result.get("composer_execution") or {}).get("steps") or []):
            if isinstance(step, Mapping) and isinstance(step.get("result"), Mapping):
                rows.append({"capability_id": step.get("capability_id"), "result": step["result"]})
    if not rows:
        return []
    reasons: list[str] = []
    for row in rows:
        inner = row.get("result") if isinstance(row.get("result"), Mapping) else None
        if inner is None:
            continue
        cid = str(row.get("capability_id") or inner.get("capability_id") or "")
        hit = _project(inner, shape)
        source = "result"
        artifact_reason: str | None = None
        if hit is None:
            path = _artifact_path(inner)
            if path is not None:
                payload, artifact_reason = _read_artifact(path, root)
                if payload is not None and isinstance(payload, Mapping):
                    hit = _project(payload, shape)
                    source = str(path)
        if hit is None:
            detail = artifact_reason or "NO_MATCHING_FIELD"
            reasons.append("ANSWER_SHAPE_UNSERVED:%s:%s:%s" % (cid, shape["noun"], detail))
            continue
        field, value = hit
        value = _narrow(value, goal)
        count = len(value) if isinstance(value, (Mapping, list, tuple)) else 1
        shown = _bounded(value)
        shown_len = len(shown) if isinstance(shown, (Mapping, list, tuple)) else 1
        result["answer"] = {                      # type: ignore[index]
            "schema": SCHEMA,
            "noun": shape["noun"],
            "field": field,
            "source": source,
            "count": count,
            "value": shown,
            "truncated": shown_len < count,
        }
        return []
    return reasons or ["ANSWER_SHAPE_UNSERVED:%s" % shape["noun"]]


def main(argv: list[str] | None = None) -> int:
    """``python3 answer_shape_v1.py "<sentence>"`` -> the shape the sentence asks for."""
    import sys
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(__doc__)
        return 2
    print(json.dumps(asked(" ".join(args)), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
