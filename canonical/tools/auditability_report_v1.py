#!/usr/bin/env python3
"""How much of what this tree calls verified can still be shown true?

THE DISTINCTION THIS MEASURES
-----------------------------
Every record here that says `VERIFIED_...` is one of two things:

    HISTORY   "this worked once; here is the sha of the output"
              -> cannot fail, so it can never tell you it stopped working
    ABILITY   "here is a predicate; run it"
              -> can fail, so it is a claim you can lose

Permanence turns history into the appearance of ability: nothing in the schema expires, so
nothing is ever found expired. Five separate audits of this tree found the same fraction at
four different layers, which is why this module exists as one measurement instead of four
anecdotes.

WHAT A PREDICATE IS, HERE
-------------------------
Deliberately narrow and executable, so that "verified" means something a machine can
disagree with:

    {"argv": ["tar", "--version"],
     "expect_exit": 0,
     "expect_stdout_contains": "GNU tar",
     "expect_version": "1.34"}

A record carrying a spec like that is CHECKABLE. A record carrying only `receipt_path`,
`observed_effect`, `independently_verified` and a hash is HISTORY, and is counted as
UNCHECKABLE -- not as a pass.

WHAT THIS MODULE DOES NOT DO
----------------------------
It does not verify anything. It reports how much CAN be verified, and in `--audit` mode it
runs the predicates it finds and reports what currently holds. Authority: NONE. A result here
is a measurement, not a receipt, and it is not independent verification of anything.

Exit status is 1 when any predicate that was run FAILED, so this can gate a pipeline. It is
deliberately able to go red: a metric that cannot decrease is not a metric.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import pathlib
import shlex
import shutil
import subprocess
import sys
from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_AUDITABILITY_REPORT_V1"

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: Fields that make a record a predicate rather than a photograph. `argv` is required;
#: the rest narrow what counts as success.
PREDICATE_FIELDS = ("argv", "command")
SHELL_PREFIXES = frozenset({"set", "export", "cd", "source", ".", "env", "if", "for", "while", "(", "{", "echo"})

EXPECTATION_FIELDS = (
    "expect_exit",
    "expect_stdout_contains",
    "expect_stdout_sha256",
    "expect_version",
    "expect_file_sha256",
)


# ---------------------------------------------------------------------------
# what counts as a predicate
# ---------------------------------------------------------------------------
def predicate_of(record: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return the executable check carried by `record`, or None if it carries only history.

    Search is shallow-but-explicit: the spec may sit on the record, or under `verification`
    / `verification.predicate`. Anything else is not recognised, and not recognised means
    UNCHECKABLE -- the safe direction, since an unrecognised predicate must never be counted
    as evidence.
    """
    if not isinstance(record, Mapping):
        return None
    seen_ids: set[int] = set()
    for holder in (record, record.get("verification")):
        if not isinstance(holder, Mapping):
            continue
        for nested in (holder, holder.get("predicate")):
            if not isinstance(nested, Mapping) or id(nested) in seen_ids:
                continue
            seen_ids.add(id(nested))
            argv = nested.get("argv") or nested.get("arg") or nested.get("command")
            if not argv:
                continue
            if isinstance(argv, str):
                # A `command` field holds a command LINE, not a binary named after the whole
                # line. A program with newlines or shell operators is not something we can
                # re-run faithfully, and a partial run would be a lie.
                if "\n" in argv or any(tok in argv for tok in
                                        ("&&", "||", ";", "|", ">", "<", "`", "$(")):
                    continue
                try:
                    argv = shlex.split(argv)
                except ValueError:
                    continue
            if not isinstance(argv, (list, tuple)) or not argv:
                continue
            if not all(isinstance(a, str) and a.strip() for a in argv):
                continue
            spec: dict[str, Any] = {"argv": list(argv)}
            for field in EXPECTATION_FIELDS:
                if field in nested:
                    spec[field] = nested[field]
            return spec
    return None


def _sha256_file(path: pathlib.Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def run_predicate(spec: Mapping[str, Any], *, cwd: pathlib.Path | None = None,
                  timeout: float = 30.0) -> dict[str, Any]:
    """Execute `spec` and say what happened. FAIL is a real possibility, which is the point."""
    argv = [str(a) for a in (spec.get("argv") or [])]
    if not argv:
        return {"verdict": "FAIL", "reason": "EMPTY_ARGV"}
    if argv[0] in SHELL_PREFIXES:
        # `set -euo pipefail cmd` is a shell script prefix. Running argv[0] alone would test
        # `set`, which always succeeds -- a false PASS on a claim never exercised.
        return {"verdict": "UNRUNNABLE", "reason": "SHELL_SCRIPT_PREFIX:" + argv[0]}
    try:
        present = shutil.which(argv[0]) is not None or pathlib.Path(argv[0]).exists()
    except (OSError, ValueError):
        present = False
    if not present:
        # An absent binary is not a pass and not a failure of the claim: it is untestable here.
        return {"verdict": "UNRUNNABLE", "reason": "BINARY_ABSENT:" + argv[0]}
    try:
        proc = subprocess.run(argv, capture_output=True, timeout=timeout, cwd=cwd)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"verdict": "UNRUNNABLE", "reason": f"{type(exc).__name__}:{exc}"[:200]}
    # Tools do not all produce UTF-8. Replacing undecodable bytes keeps the expectation
    # checkable instead of turning a decode error into an exception inside the audit.
    proc.stdout = (proc.stdout or b"").decode("utf-8", "replace")
    proc.stderr = (proc.stderr or b"").decode("utf-8", "replace")

    if "expect_exit" in spec and int(proc.returncode) != int(spec["expect_exit"]):
        return {"verdict": "FAIL",
                "reason": f"EXIT {proc.returncode} != {spec['expect_exit']}",
                "stdout": proc.stdout[:400], "stderr": proc.stderr[:400]}
    needle = spec.get("expect_stdout_contains")
    if needle is not None and str(needle) not in proc.stdout:
        return {"verdict": "FAIL", "reason": f"STDOUT MISSING {needle!r}",
                "stdout": proc.stdout[:400]}
    version = spec.get("expect_version")
    if version is not None and str(version) not in (proc.stdout + proc.stderr):
        return {"verdict": "FAIL", "reason": f"VERSION MISSING {version!r}",
                "stdout": proc.stdout[:400], "stderr": proc.stderr[:400]}
    digest = spec.get("expect_stdout_sha256")
    if digest is not None and hashlib.sha256(proc.stdout.encode()).hexdigest() != str(digest):
        return {"verdict": "FAIL", "reason": "STDOUT SHA MISMATCH"}
    for name, want in dict(spec.get("expect_file_sha256") or {}).items():
        got = _sha256_file(pathlib.Path(name))
        if got != want:
            return {"verdict": "FAIL", "reason": f"FILE SHA MISMATCH:{name}"}
    return {"verdict": "PASS", "reason": None, "stdout": proc.stdout[:200]}


# ---------------------------------------------------------------------------
# the four layers
# ---------------------------------------------------------------------------
def _iter_json(root: pathlib.Path) -> Iterable[tuple[pathlib.Path, Any]]:
    for path in root.rglob("*.json"):
        if any(part in {".git", "__pycache__", "node_modules"} for part in path.parts):
            continue
        try:
            yield path, json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except (OSError, ValueError):
            continue


def capabilities(root: pathlib.Path) -> dict[str, Any]:
    """Records claiming a verified bound capability, and how many carry a predicate."""
    total = 0
    checkable = 0
    sample: list[str] = []

    def walk(node: Any) -> None:
        nonlocal total, checkable
        if isinstance(node, dict):
            if str(node.get("status") or "").startswith("VERIFIED_BOUND_CAPABILITY"):
                total += 1
                if predicate_of(node) is not None:
                    checkable += 1
                    if len(sample) < 3:
                        sample.append(str(node.get("adapter_module") or "?")[:60])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    for _, payload in _iter_json(root / "canonical"):
        walk(payload)
    return {"layer": "capabilities", "total": total, "checkable": checkable,
            "checkable_examples": sample}


def skills(root: pathlib.Path) -> dict[str, Any]:
    """Stored skills, and how many carry a check that would fail if the rule stopped holding."""
    sys.path.insert(0, str(root))
    try:
        from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
    except Exception as exc:                      # pragma: no cover - environment specific
        return {"layer": "skills", "total": None, "checkable": None,
                "error": f"{type(exc).__name__}:{exc}"[:160]}
    try:
        store = VerifiedSkillStore()
    except Exception as exc:                      # pragma: no cover
        return {"layer": "skills", "total": None, "checkable": None,
                "error": f"{type(exc).__name__}:{exc}"[:160]}

    # Iterate the languages actually present in the store, not a guessed list: a fixed list
    # silently omits whatever it did not think of, and an omitted lesson reads as a pass.
    languages = {"python"}
    try:
        import sqlite3
        conn = sqlite3.connect(str(store.db_path))
        try:
            languages |= {str(r[0]) for r in
                          conn.execute("SELECT DISTINCT language FROM crystallized_skills")
                          if r and r[0]}
        finally:
            conn.close()
    except Exception:
        pass

    seen: dict[str, dict] = {}
    for language in sorted(languages):
        try:
            rows = store.lookup_rules(language) or []
        except Exception:
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            key = str(row.get("skill_id") or row.get("id") or
                      hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest())
            seen.setdefault(key, row)

    # A skill is checkable only if it names a verifier that is not the demonstration that
    # taught it. `twin_verification` is the only stored field that does that; a rule that
    # carries neither it nor an executable predicate is history.
    checkable = sum(1 for row in seen.values()
                    if row.get("twin_verification") or predicate_of(row) is not None)
    with_any_evidence = sum(
        1 for row in seen.values()
        if any(k for k in row if "verification" in k or "verified" in k))
    return {"layer": "skills", "total": len(seen), "checkable": checkable,
            "note": f"{with_any_evidence} of {len(seen)} carry any verification field at all"}


def process_sites(root: pathlib.Path) -> dict[str, Any]:
    """Registered process call sites: identified by position (history) or by content (identity)."""
    registry = root / "canonical" / "runtime" / "root3_subprocess_effect_class_registry_v1.py"
    if not registry.exists():
        return {"layer": "process_sites", "total": None, "checkable": None,
                "error": "REGISTRY_ABSENT"}
    text = registry.read_text(encoding="utf-8", errors="ignore")
    # Keys are (module_path, lineno, process_api). A lineno is a POSITION: it identifies the
    # site by where it happened to be, not by what it is, so it is history. A key carrying a
    # content digest instead identifies the site by what it is, and survives an edit above it.
    line_pins = 0
    content_pins = 0
    for match in re.finditer(r'\(\s*"([^"]+\.py)"\s*,\s*([^,]+),\s*"([^"]+)"\s*\)', text):
        where = match.group(2).strip()
        if where.isdigit():
            line_pins += 1
        elif len(where.strip('"')) >= 16:
            content_pins += 1
    total = line_pins + content_pins
    if not total:
        return {"layer": "process_sites", "total": None, "checkable": None,
                "error": "NO_PINS_PARSED"}
    return {"layer": "process_sites", "total": total, "checkable": content_pins,
            "note": f"{line_pins} pinned by line number (history), "
                    f"{content_pins} by content (identity)"}


def test_modules(root: pathlib.Path) -> dict[str, Any]:
    """Modules that never start, so their claims are neither true nor false."""
    tests_dir = root / "canonical" / "tests"
    if not tests_dir.exists():
        return {"layer": "test_modules", "total": None, "checkable": None, "error": "NO_TESTS_DIR"}
    proc = subprocess.run([sys.executable, "-m", "pytest", str(tests_dir), "--collect-only", "-q"],
                          cwd=root, capture_output=True, text=True, timeout=1800)
    # `-q` prints one "ERROR path - reason" line per module that failed to import, plus a
    # final "Interrupted: N errors during collection". Count the module lines: each one is a
    # module whose tests never ran, so its claims are neither true nor false.
    errors = sum(1 for line in proc.stdout.splitlines() if line.startswith("ERROR "))
    collected = 0
    for line in proc.stdout.splitlines():
        if "tests collected" in line:
            head = line.split("tests collected")[0].strip().split()[-1]
            if head.isdigit():
                collected = int(head)
    return {"layer": "test_modules", "total": collected,
            "checkable": max(collected - errors, 0),
            "note": f"{errors} collection errors (modules that never ran)"}


# ---------------------------------------------------------------------------
# the report
# ---------------------------------------------------------------------------
def binary_predicates(root: pathlib.Path) -> dict[str, Any]:
    """Named binary identities, each an executable check that can be contradicted.

    This is the one layer that is fully checkable by construction, so it is the reference
    point: 100% here and 0% elsewhere is the gap this instrument exists to make visible.
    """
    corpus = (root / "canonical" / "tools" / "predicates"
              / "binary_identity_predicates_20261112_v1.json")
    if not corpus.exists():
        return {"layer": "binary_identity", "total": 0, "checkable": 0,
                "error": "CORPUS_ABSENT"}
    try:
        payload = json.loads(corpus.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"layer": "binary_identity", "total": 0, "checkable": 0,
                "error": f"{type(exc).__name__}:{exc}"[:120]}
    entries = [e for e in (payload.get("predicates") or []) if isinstance(e, dict)]
    checkable = sum(1 for entry in entries if predicate_of(entry) is not None)
    total = len(entries)
    return {"layer": "binary_identity", "total": total, "checkable": checkable,
            "auditability": round(checkable / total, 4) if total else None}


def audit(root: pathlib.Path = REPO_ROOT, *, run: bool = False) -> dict[str, Any]:
    layers = [capabilities(root), skills(root), process_sites(root), test_modules(root),
              binary_predicates(root)]
    for layer in layers:
        total, checkable = layer.get("total"), layer.get("checkable")
        layer["auditability"] = (round(checkable / total, 4)
                                 if isinstance(total, int) and total and isinstance(checkable, int)
                                 else None)

    predicates: list[dict[str, Any]] = []
    if run:
        corpus = (root / "canonical" / "tools" / "predicates"
                  / "binary_identity_predicates_20261112_v1.json")
        if corpus.exists():
            try:
                entries = (json.loads(corpus.read_text(encoding="utf-8")) or {}).get("predicates") or []
            except (OSError, ValueError):
                entries = []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                spec = predicate_of({"argv": entry.get("arg") or entry.get("argv"),
                                     **{k: v for k, v in entry.items() if k.startswith("expect_")}})
                if spec is None:
                    continue
                result = run_predicate(spec, cwd=root)
                predicates.append({"source": "canonical/tools/predicates/"
                                             "binary_identity_predicates_20261112_v1.json",
                                   "name": entry.get("name"), "argv": spec["argv"], **result})
        for path, payload in _iter_json(root / "canonical"):
            # One check per RECORD, not per dict. A record's `verification` block is part of
            # the record; walking into it visits the same predicate twice and inflates the
            # count, which would make the instrument report more evidence than exists.
            stack = [payload]
            while stack:
                node = stack.pop()
                if isinstance(node, dict):
                    spec = predicate_of(node)
                    if spec is not None:
                        result = run_predicate(spec, cwd=root)
                        predicates.append({"source": str(path.relative_to(root)),
                                           "argv": spec["argv"], **result})
                        continue                      # a predicate is a leaf: do not descend
                    stack.extend(node.values())
                elif isinstance(node, list):
                    stack.extend(node)

    counts = {"PASS": 0, "FAIL": 0, "UNRUNNABLE": 0}
    for item in predicates:
        counts[item["verdict"]] = counts.get(item["verdict"], 0) + 1

    return {
        "schema": SCHEMA,
        "authority": "NONE",
        "layers": layers,
        "predicates_run": len(predicates),
        "predicate_verdicts": counts,
        "predicate_results": predicates,
        "red": bool(counts.get("FAIL")),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", action="store_true",
                        help="also RUN every checkable predicate and report what currently holds")
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = audit(pathlib.Path(args.root), run=args.audit)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("auditability: how much of 'verified' can still be shown true\n")
        print(f"{'layer':16}{'records':>9}{'checkable':>11}{'auditability':>14}")
        print("-" * 52)
        for layer in report["layers"]:
            frac = layer.get("auditability")
            print(f"{layer['layer']:16}{str(layer.get('total')):>9}"
                  f"{str(layer.get('checkable')):>11}"
                  f"{(str(round(frac * 100, 1)) + '%') if frac is not None else '?':>14}")
            if layer.get("note"):
                print(f"{'':16}{layer['note']}")
            if layer.get("error"):
                print(f"{'':16}error: {layer['error']}")
        if args.audit:
            print(f"\npredicates run: {report['predicates_run']}  {report['predicate_verdicts']}")
            for item in report["predicate_results"]:
                if item["verdict"] != "PASS":
                    print(f"  {item['verdict']:11} {' '.join(item['argv'])[:50]:52} {item.get('reason')}")
        else:
            print("\n(run with --audit to execute the predicates that exist)")
    return 1 if report["red"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
