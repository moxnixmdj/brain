#!/usr/bin/env python3
"""A receipt that names the program that measured it must be checked against that program.

THE DEFECT THIS MEASURES
------------------------
`python_repository_acceptance_measurement_v1` writes
`measurement_program_sha256 = sha256(pathlib.Path(__file__).read_bytes())` into every
measurement receipt. Consumers copy that field forward:

    python_repair_measured_acceptance_controller_v1.py:465  "measurement_program_sha256": measurement.get(...)

Measured 2026-11-12: nothing anywhere compares the carried value to the program as it exists
now. `grep` for an equality test finds only a test that blanks the field. So a receipt keeps
asserting "the program that produced me is X" after X has changed, and no reader can tell.

That is the invariant this session keeps meeting, one layer out: the receipt is history, and
history cannot fail.

WHAT THIS MODULE DOES
---------------------
For every JSON receipt in the tree that carries `measurement_program_sha256`, it finds the
receipt's own program (recorded in the same document, or named on the command line), hashes
the file now, and reports:

    MATCH      the carried hash equals the program on disk
    MISMATCH   it does not -- the receipt describes a program that no longer exists
    NO_PROGRAM the receipt names a hash but no program can be located, so it is unfalsifiable
    ABSENT     the document carries no such field

A field that can only ever be MATCH is not evidence. MISMATCH has to be reachable, and the
tree should be able to show at least one of each.

Authority: NONE. A MATCH says the program file is unchanged; it says nothing about whether
the measurement was correct.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_RECEIPT_PROGRAM_IDENTITY_V1"

FIELD = "measurement_program_sha256"

MATCH = "MATCH"
MISMATCH = "MISMATCH"
NO_PROGRAM = "NO_PROGRAM"
ABSENT = "ABSENT"
INVALID = "INVALID"

#: Keys a receipt may use to name the program it was produced by. Ordered by trustworthiness:
#: an explicit path beats a module name beats a bare basename.
PROGRAM_KEYS = ("measurement_program_path", "measurement_program", "program_path",
                "measurement_program_module", "program")


def _sha_file(path: pathlib.Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _resolve_program(value: Any, root: pathlib.Path) -> pathlib.Path | None:
    """Turn whatever the receipt recorded into a file, or None. Never guesses silently."""
    if not isinstance(value, str) or not value.strip():
        return None
    name = value.strip()
    candidate = pathlib.Path(name)
    if candidate.is_absolute():
        return candidate if candidate.is_file() else None
    for base in (root, root / "canonical", root / "canonical" / "runtime"):
        direct = base / name
        if direct.is_file():
            return direct
    if name.endswith(".py"):
        matches = sorted(root.rglob(pathlib.PurePath(name).name))
        return matches[0] if matches else None
    dotted = name.replace(".", "/")
    for suffix in (".py", "/__init__.py"):
        found = sorted(root.rglob(dotted + suffix))
        if found:
            return found[0]
    return None


def check_record(record: Mapping[str, Any], root: pathlib.Path) -> dict[str, Any]:
    """One receipt. Returns a verdict, and the two hashes so the verdict can be audited."""
    carried = record.get(FIELD)
    if carried is None:
        return {"verdict": ABSENT, "reason": "FIELD_NOT_PRESENT"}
    if not isinstance(carried, str) or not carried.strip():
        return {"verdict": INVALID, "reason": "FIELD_EMPTY_OR_NOT_A_STRING",
                "carried": carried}

    program_value = None
    for key in PROGRAM_KEYS:
        if record.get(key):
            program_value = record[key]
            break
    if program_value is None:
        subject = record.get("subject")
        if isinstance(subject, Mapping):
            for key in PROGRAM_KEYS:
                if subject.get(key):
                    program_value = subject[key]
                    break
    if program_value is None:
        spec = record.get("measurement_spec")
        if isinstance(spec, Mapping):
            for key in PROGRAM_KEYS:
                if spec.get(key):
                    program_value = spec[key]
                    break

    if program_value is None:
        # The hash is present but the program is not identified anywhere in the document.
        # That is worse than absent: it looks checkable and is not.
        return {"verdict": NO_PROGRAM, "reason": "PROGRAM_NOT_IDENTIFIED", "carried": carried}

    program = _resolve_program(program_value, root)
    if program is None:
        return {"verdict": NO_PROGRAM, "reason": f"PROGRAM_NOT_FOUND:{str(program_value)[:80]}",
                "carried": carried}

    actual = _sha_file(program)
    if actual is None:
        return {"verdict": NO_PROGRAM, "reason": f"PROGRAM_UNREADABLE:{program}", "carried": carried}

    verdict = MATCH if actual == carried.strip() else MISMATCH
    return {"verdict": verdict,
            "reason": None if verdict == MATCH else "PROGRAM_CHANGED_SINCE_RECEIPT",
            "carried": carried, "actual": actual,
            "program": str(program.relative_to(root)) if program.is_relative_to(root) else str(program)}


def _iter_records(node: Any) -> Iterable[Mapping[str, Any]]:
    stack = [node]
    while stack:
        current = stack.pop()
        if isinstance(current, Mapping):
            if FIELD in current:
                yield current
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)


def scan(root: pathlib.Path, *, limit: int | None = None) -> dict[str, Any]:
    counts = {MATCH: 0, MISMATCH: 0, NO_PROGRAM: 0, ABSENT: 0, INVALID: 0}
    receipts: list[dict[str, Any]] = []
    files_with_field = 0

    for path in sorted(root.rglob("*.json")):
        if any(part in {".git", "__pycache__", "node_modules"} for part in path.parts):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except (OSError, ValueError):
            continue
        found = list(_iter_records(payload))
        if not found:
            continue
        files_with_field += 1
        for record in found:
            outcome = check_record(record, root)
            counts[outcome["verdict"]] = counts.get(outcome["verdict"], 0) + 1
            if outcome["verdict"] in (MISMATCH, NO_PROGRAM, INVALID):
                receipts.append({"source": str(path.relative_to(root)), **outcome})
            if limit is not None and len(receipts) >= limit:
                break

    return {"schema": SCHEMA, "authority": "NONE",
            "files_carrying_field": files_with_field,
            "counts": counts,
            "receipts": receipts,
            "checkable": counts[MATCH] + counts[MISMATCH],
            "red": bool(counts[MISMATCH] or counts[NO_PROGRAM] or counts[INVALID])}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(pathlib.Path(__file__).resolve().parents[2]))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = scan(pathlib.Path(args.root))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("receipt program identity: does the program a receipt names still exist?\n")
        print(f"  files carrying {FIELD}: {report['files_carrying_field']}")
        for verdict in (MATCH, MISMATCH, NO_PROGRAM, INVALID, ABSENT):
            print(f"    {verdict:11} {report['counts'].get(verdict, 0)}")
        print(f"\n  checkable: {report['checkable']}")
        for item in report["receipts"][:15]:
            print(f"    {item['verdict']:11} {item['source'][:64]:66} {item.get('reason')}")
    return 1 if report["red"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
