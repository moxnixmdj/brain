#!/usr/bin/env python3
"""Compute the preservation algebra from readings; do not supply its law names.

WHAT THIS REMOVES
-----------------
Every closure experiment so far used five named laws written by the experimenter. The selections
were real, but the vocabulary they could state was not. This module derives candidate laws from the
key/value structure of the readings themselves: preserve a prefix, forbid new keys in a prefix,
clear a prefix, restore a suffix from one prefix to another, or hold a low-cardinality flag. No law
name, task name, file name, commit digest or judge answer is passed to the selector.

The selector keeps the smallest conjunction that accepts every LEGITIMATE row and refuses every
HOLE row, deduplicates laws by their truth vector on training rows, and reports the selected
templates beside the old named closure for comparison only. Evaluation uses judged rows produced
by the existing one-origin judge on a different repository.

This is a bounded git experiment, not general computer use. The template grammar is supplied; the
names of its instances are not. No runtime model call, no stored parameter, no capability credit.

Authority: NONE__PRODUCER_RUN_SANDBOX.
"""
from __future__ import annotations

import argparse
import itertools
import json
import pathlib
import sys
import time
from typing import Any, Iterable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import goal_closure_v1 as GC  # noqa: E402
from canonical.tools import one_origin_derives_the_judge_v1 as O  # noqa: E402

SCHEMA = "BRAIN_COMPUTED_LAW_ALGEBRA_V1"
MAX_LAW_SIZE = 4


def _prefix(key: str) -> str:
    return key.split(".", 1)[0] if "." in key else key


def _suffix(key: str) -> str:
    return key.split(".", 1)[1] if "." in key else ""


def candidate_laws(rows: Sequence[GC.Judgment]) -> list[dict[str, Any]]:
    """Enumerate relation templates over the facts that actually occurred."""
    readings: list[GC.Reading] = [r for row in rows for r in (row.origin, row.post)]
    prefixes = sorted({_prefix(k) for r in readings for k in r.facts})
    laws: list[dict[str, Any]] = []
    for p in prefixes:
        laws.append({"kind": "preserve", "prefix": p})
        laws.append({"kind": "no_new", "prefix": p})
        laws.append({"kind": "clear", "prefix": p})
    for p in prefixes:
        for q in prefixes:
            evidenced = any(
                f"{p}.{s}" in before.facts and f"{q}.{s}" in after.facts
                for before, after in zip((r.origin for r in rows), (r.post for r in rows))
                for s in {_suffix(k) for k in before.facts if k.startswith(p + ".")}
            )
            if evidenced:
                laws.append({"kind": "restore", "from": p, "to": q})
    values: dict[str, set[str]] = {}
    for r in readings:
        for key, value in r.facts.items():
            if key.startswith("target."):
                continue
            values.setdefault(key, set()).add(value)
    for key, seen in values.items():
        # A flag about a path name or a digest is memorized world knowledge, not a mechanism.
        # Structural flags have short non-hex values and no path in the key suffix.
        if _prefix(key) not in ("head", "history", "stash") or _suffix(key).count(".") > 0:
            continue
        if not 1 < len(seen) <= 3 or any(len(v) > 12 or all(c in "0123456789abcdef" for c in v)
                                        for v in seen):
            continue
        for value in sorted(seen):
            laws.append({"kind": "flag", "key": key, "value": value})
    return conditional_laws(rows, prefixes, laws)


def conditional_laws(rows: Sequence[GC.Judgment], prefixes: Sequence[str],
                     base: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Induce generic exceptions from the keys that actually broke a preservation rule."""
    out = list(base)
    seen = {json.dumps(law, sort_keys=True) for law in out}
    prefixes = list(prefixes)

    def add(law: dict[str, Any]) -> None:
        token = json.dumps(law, sort_keys=True)
        if token not in seen:
            seen.add(token)
            out.append(law)

    for kind in ("preserve", "no_new"):
        for p in prefixes:
            base_law = {"kind": kind, "prefix": p}
            for row in rows:
                before, after = row.origin, row.post
                if kind == "preserve":
                    broken = [k for k, v in before.facts.items()
                              if k.startswith(p + ".") and after.get(k) != v]
                else:
                    broken = [k for k in after.facts
                              if k.startswith(p + ".") and k not in before.facts]
                for key in broken:
                    suffix = _suffix(key)
                    for q in prefixes:
                        if q != p and f"{q}.{suffix}" in before.facts:
                            add({"kind": kind + "_except_prefix", "prefix": p, "witness": q})
                    for scope, reading in (("before", before), ("after", after)):
                        for other, value in reading.facts.items():
                            if other != key and value == suffix and _prefix(other) != p:
                                add({"kind": kind + "_except_value", "prefix": p,
                                     "key": other, "scope": scope})
    return out


def law_holds(law: Mapping[str, Any], before: GC.Reading, after: GC.Reading) -> bool:
    kind = law["kind"]
    if kind == "preserve":
        prefix = str(law["prefix"]) + "."
        return all(after.get(k) == v for k, v in before.facts.items() if k.startswith(prefix))
    if kind == "no_new":
        prefix = str(law["prefix"]) + "."
        return not any(k.startswith(prefix) and k not in before.facts for k in after.facts)
    if kind == "clear":
        prefix = str(law["prefix"]) + "."
        return not any(k.startswith(prefix) for k in after.facts)
    if kind == "restore":
        src, dst = str(law["from"]) + ".", str(law["to"]) + "."
        for key, value in before.facts.items():
            if key.startswith(src):
                target_key = dst + key[len(src):]
                if after.get(target_key) != value:
                    return False
        return True
    if kind == "preserve_except_prefix":
        prefix, witness = str(law["prefix"]) + ".", str(law["witness"]) + "."
        for key, value in before.facts.items():
            if not key.startswith(prefix) or after.get(key) == value:
                continue
            if f"{witness}{key[len(prefix):]}" not in before.facts:
                return False
        return True
    if kind == "preserve_except_value":
        prefix, key, scope = str(law["prefix"]) + ".", str(law["key"]), str(law["scope"])
        reading = before if scope == "before" else after
        allowed = reading.get(key)
        for k, v in before.facts.items():
            if k.startswith(prefix) and after.get(k) != v and _suffix(k) != allowed:
                return False
        return True
    if kind == "no_new_except_prefix":
        prefix, witness = str(law["prefix"]) + ".", str(law["witness"]) + "."
        for key in after.facts:
            if key.startswith(prefix) and key not in before.facts:
                if f"{witness}{key[len(prefix):]}" not in before.facts:
                    return False
        return True
    if kind == "no_new_except_value":
        prefix, key, scope = str(law["prefix"]) + ".", str(law["key"]), str(law["scope"])
        reading = before if scope == "before" else after
        allowed = reading.get(key)
        for k in after.facts:
            if k.startswith(prefix) and k not in before.facts and _suffix(k) != allowed:
                return False
        return True
    if kind == "flag":
        return after.get(str(law["key"])) == law["value"]
    raise ValueError("unknown computed law kind: " + str(kind))


def closure_holds(laws: Sequence[Mapping[str, Any]], row: GC.Reading | GC.Judgment) -> bool:
    if isinstance(row, GC.Judgment):
        return all(law_holds(law, row.origin, row.post) for law in laws)
    raise TypeError("closure_holds needs a Judgment")


def _vector(law: Mapping[str, Any], rows: Sequence[GC.Judgment]) -> tuple[bool, ...]:
    return tuple(law_holds(law, r.origin, r.post) for r in rows)


def select(rows: Sequence[GC.Judgment]) -> dict[str, Any]:
    """Smallest conjunction over computed laws; ties are kept, not hidden."""
    unique: dict[tuple[bool, ...], dict[str, Any]] = {}
    for law in candidate_laws(rows):
        vec = _vector(law, rows)
        if not any(vec) or all(vec):
            continue
        unique.setdefault(vec, law)
    vectors = sorted(unique)
    for size in range(1, min(MAX_LAW_SIZE, len(vectors)) + 1):
        winners = []
        for group in itertools.combinations(range(len(vectors)), size):
            ok = True
            for i, row in enumerate(rows):
                conjunction = all(vectors[j][i] for j in group)
                if conjunction != (row.verdict == "LEGITIMATE"):
                    ok = False
                    break
            if ok:
                winners.append([unique[vectors[j]] for j in group])
        if winners:
            return {"status": "CLOSURE_FOUND", "closures": winners, "minimal_size": size,
                    "nonconstant_vectors": len(vectors)}
    return {"status": "NO_CLOSURE_IN_COMPUTED_ALGEBRA", "closures": [],
            "minimal_size": None, "nonconstant_vectors": len(vectors)}


def evaluate(laws: Sequence[Mapping[str, Any]], rows: Sequence[GC.Judgment]) -> dict[str, Any]:
    return {
        "laws": list(laws),
        "holes_seen": sum(r.verdict == "HOLE" for r in rows),
        "legitimate_seen": sum(r.verdict == "LEGITIMATE" for r in rows),
        "false_accepts": [list(r.plan) for r in rows
                          if r.verdict == "HOLE" and closure_holds(laws, r)],
        "false_rejects": [list(r.plan) for r in rows
                          if r.verdict == "LEGITIMATE" and not closure_holds(laws, r)],
    }


def _rows(repo: str, root: pathlib.Path, label: str, base_url: str) -> tuple[list[GC.Judgment], str]:
    host = root / label
    host.mkdir(parents=True, exist_ok=True)
    base = GC.BM.MACHINE.build_base(host, base_url, None)
    target = GC.BM.MACHINE.git(base, "rev-parse", "HEAD")[1].strip()
    reference = GC.reference_tree(base, target)
    rows: list[GC.Judgment] = []
    for kind in O.C.SETUP:
        start = GC.damage_extra(root / f"{label}-{kind}", base, kind)
        rows.extend(O._origin_rows(start, target, root / f"ws-{label}-{kind}", reference)["rows"])
    return rows, target


def measure(root: pathlib.Path, train_repo: str, held_repo: str, *,
            receipt: pathlib.Path | None = None) -> dict[str, Any]:
    begun = time.time()
    root.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "claim": "The preservation vocabulary is computed from readings; the smallest separator "
                 "transfers to judged rows from a different repository.",
        "declared_before_the_run": [
            "F1 the selector receives no named law, file name or commit digest",
            "F2 the computed algebra selects a closure from training rows",
            "F3 the selected closure has zero false accepts and zero false rejects on held rows",
            "F4 no false accept/reject under the old named closure is hidden by this comparison",
            "F5 zero model calls and zero stored parameters",
        ],
        "limits": ["template grammar, damage classes, target commits and bounds are supplied",
                   "git only; not a GUI, browser or open benchmark score",
                   "producer-run; no independent verification"],
    }
    train_rows, train_target = _rows(train_repo, root, "train", train_repo)
    held_rows, held_target = _rows(held_repo, root, "held_out", held_repo)
    vectors: dict[tuple[bool, ...], dict[str, Any]] = {}
    for law in candidate_laws(train_rows):
        vec = _vector(law, train_rows)
        if any(vec) and not all(vec):
            vectors.setdefault(vec, law)
    report["computed_candidates"] = [
        {"true_rows": sum(vec), "law": law} for vec, law in
        sorted(vectors.items(), key=lambda item: -sum(item[0]))]
    selection = select(train_rows)
    report["selection"] = selection
    laws = selection["closures"][0] if selection["closures"] else []
    report["computed_laws"] = laws
    report["train_evaluation"] = [evaluate(c, train_rows) for c in ([laws] if laws else [])]
    report["held_evaluation"] = [evaluate(c, held_rows) for c in ([laws] if laws else [])]
    named = ["ref_preserve", "tracking_preserve", "stash_restore"]
    report["named_baseline"] = {
        "laws": named,
        "train": {"false_accepts": sum(
            r.verdict == "HOLE" and GC.closure_holds(named, r.origin, r.post, train_target, r.path)
            for r in train_rows),
            "false_rejects": sum(
                r.verdict == "LEGITIMATE" and not GC.closure_holds(named, r.origin, r.post, train_target, r.path)
                for r in train_rows)},
        "held": {"false_accepts": sum(
            r.verdict == "HOLE" and GC.closure_holds(named, r.origin, r.post, held_target, r.path)
            for r in held_rows),
            "false_rejects": sum(
                r.verdict == "LEGITIMATE" and not GC.closure_holds(named, r.origin, r.post, held_target, r.path)
                for r in held_rows)},
    }
    report["judged_rows"] = {"train": len(train_rows), "held": len(held_rows)}
    criteria = {
        "F1_no_named_law_input": (
            not any(name in json.dumps(laws) for name in GC.LAW_IDS)
            and not any(len(str(v)) > 12 for law in laws for k, v in law.items()
                        if k == "value")
            and "local edit" not in json.dumps(laws)),
        "F2_closure_found": selection["status"] == "CLOSURE_FOUND",
        "F3_transfer_zero_errors": bool(report["held_evaluation"])
        and report["held_evaluation"][0]["false_accepts"] == []
        and report["held_evaluation"][0]["false_rejects"] == [],
        "F4_named_baseline_zero_errors": (report["named_baseline"]["train"]["false_accepts"] == 0
                                          and report["named_baseline"]["train"]["false_rejects"] == 0
                                          and report["named_baseline"]["held"]["false_accepts"] == 0
                                          and report["named_baseline"]["held"]["false_rejects"] == 0),
        "F5_zero_model_calls_and_parameters": True,
    }
    report["criteria"] = criteria
    report["met"] = all(criteria.values())
    report["model_calls"] = 0
    report["parameters_stored"] = 0
    report["seconds"] = round(time.time() - begun, 1)
    if receipt is not None:
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    return report


def write_store(report: Mapping[str, Any], path: pathlib.Path) -> dict[str, Any]:
    """Write the computed closure as editable, deletable external knowledge."""
    store = {
        "schema": "BRAIN_COMPUTED_LAW_STORE_V1",
        "laws": list(report.get("computed_laws") or []),
        "derived_from": report.get("selection", {}),
        "parameters": 0,
        "model_calls": 0,
        "removable": True,
        "note": "Delete this file to remove the learned closure; the selector is unchanged.",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(store, indent=1) + "\n", encoding="utf-8")
    return store


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default="/tmp/computed-law-algebra")
    ap.add_argument("--train-repo", default="https://github.com/pypa/packaging.git")
    ap.add_argument("--held-repo", default="https://github.com/pypa/pyproject-hooks.git")
    ap.add_argument("--receipt", default=None)
    ap.add_argument("--store", default=None)
    args = ap.parse_args(argv)
    r = measure(pathlib.Path(args.root), args.train_repo, args.held_repo,
                receipt=pathlib.Path(args.receipt) if args.receipt else None)
    if args.store:
        write_store(r, pathlib.Path(args.store))
    print(json.dumps({"computed_laws": r.get("computed_laws"),
                      "selection": r.get("selection"),
                      "held": r.get("held_evaluation"),
                      "criteria": r.get("criteria"), "met": r.get("met")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
