#!/usr/bin/env python3
"""Historical-envelope compiler for the exact frozen legacy LiveBench prompt grammar.

The historical generator inserts source article text between two literal
"-------" separators and appends all IFEval descriptions after the closing
separator. V4 parses only that visible suffix, eliminating false recognizer hits
inside arbitrary article text while preserving full-prompt recovery for
combination:repeat_prompt.

No hidden IDs, kwargs, question IDs, terminal responses, scores, or case
metadata are read.
"""
from __future__ import annotations

import re
from typing import Any

from canonical.runtime import livebench_legacy_visible_constraint_compiler_v1 as v1

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_VISIBLE_CONSTRAINT_COMPILER_V4"
HISTORICAL_GENERATOR_COMMIT = "686be1e78a0ba8036d7e355bc406e1a265da5292"
HISTORICAL_GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"
_ENVELOPE_SEPARATOR = "\n-------\n"
_REPEAT_MARKER = (
    "First repeat the request word for word without change,"
    " then give your answer (1. do not say any words or characters"
    " before repeating the request; 2. the request you need to repeat"
    " does not include this sentence)"
)
_POSTSCRIPT_RE = re.compile(
    r"At the end of your response, please explicitly add a postscript "
    r"starting with (?P<postscript_marker>P\.P\.S|P\.S\.)"
)


def _offset_constraint(c: dict[str, Any], offset: int) -> dict[str, Any]:
    out = dict(c)
    out["start"] = int(out.get("start", 0)) + offset
    out["end"] = int(out.get("end", 0)) + offset
    return out


def compile_visible_constraints(prompt: str) -> dict[str, Any]:
    text = str(prompt or "")
    boundary = text.rfind(_ENVELOPE_SEPARATOR)
    if boundary < 0:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "HISTORICAL_ENVELOPE_SEPARATOR_NOT_FOUND",
            "constraints": [],
            "terminal_data_used": False,
            "hidden_instruction_ids_used": False,
            "hidden_kwargs_used": False,
        }

    suffix_start = boundary + len(_ENVELOPE_SEPARATOR)
    suffix = text[suffix_start:]
    base = v1.compile_visible_constraints(suffix)
    constraints = [_offset_constraint(c, suffix_start) for c in base.get("constraints") or []]

    # Recover the only historically non-rendered parameter from the exact public
    # generator rule, using the full visible prompt prefix.
    repeat_positions = [m.start() for m in re.finditer(re.escape(_REPEAT_MARKER), suffix)]
    repeats = [c for c in constraints if c.get("instruction_id") == "combination:repeat_prompt"]
    if len(repeats) == 1 and len(repeat_positions) == 1:
        absolute = suffix_start + repeat_positions[0]
        prefix = text[:absolute].strip()
        if prefix:
            repeats[0]["slots"] = dict(repeats[0].get("slots") or {})
            repeats[0]["slots"]["prompt_to_repeat"] = prefix
            repeats[0]["parameter_complete"] = True
            repeats[0]["unresolved_parameters"] = []

    # Bound postscript marker parsing to the generated suffix so article text
    # cannot create a false repair match.
    post_matches = list(_POSTSCRIPT_RE.finditer(suffix))
    posts = [c for c in constraints if c.get("instruction_id") == "detectable_content:postscript"]
    if len(posts) == 1 and len(post_matches) == 1:
        m = post_matches[0]
        posts[0]["start"] = suffix_start + m.start()
        posts[0]["end"] = suffix_start + m.end()
        posts[0]["matched_text"] = m.group(0)
        posts[0]["slots"] = {"postscript_marker": m.group("postscript_marker")}
        posts[0]["parameter_complete"] = True
        posts[0]["unresolved_parameters"] = []

    ids = [str(c.get("instruction_id")) for c in constraints]
    duplicates = sorted({iid for iid in ids if ids.count(iid) > 1})
    incomplete = [
        {"instruction_id": c.get("instruction_id"), "unresolved_parameters": list(c.get("unresolved_parameters") or [])}
        for c in constraints
        if not c.get("parameter_complete")
    ]
    parse_errors = list(base.get("parse_errors") or [])

    ok = not parse_errors and not duplicates and not incomplete
    return {
        "schema": SCHEMA,
        "status": "PASS" if ok else "FAIL_CLOSED",
        "constraints": constraints,
        "recognized_instruction_instance_count": len(constraints),
        "recognized_instruction_type_count": len(set(ids)),
        "parameter_complete_count": sum(1 for c in constraints if c.get("parameter_complete")),
        "parameter_incomplete": incomplete,
        "duplicate_instruction_ids": duplicates,
        "parse_errors": parse_errors,
        "suffix_start": suffix_start,
        "historical_envelope_isolation": True,
        "article_region_scanned_for_constraints": False,
        "historical_generator_commit": HISTORICAL_GENERATOR_COMMIT,
        "historical_generator_blob": HISTORICAL_GENERATOR_BLOB,
        "terminal_data_used": False,
        "hidden_instruction_ids_used": False,
        "hidden_kwargs_used": False,
        "terminal_case_metadata_used": False,
        "terminal_case_content_used": False,
        "model_dependency_count": 0,
        "network_used": False,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return compile_visible_constraints(str((args or {}).get("prompt") or (args or {}).get("text") or ""))


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ns = ap.parse_args()
    print(json.dumps(compile_visible_constraints(ns.prompt), ensure_ascii=False, indent=2, sort_keys=True))
