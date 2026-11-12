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
import os
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

#: Tokens that only a shell gives meaning to. Found INSIDE an argv list they are the
#: fragments of a command LINE that was split early, so what runs is not what was declared:
#: `["jq", "-r", ".capabilities", "|", "keys"]` hands `|` to jq as an argument and exits 2.
#: `predicate_of` already refuses these in a string `command` for exactly this reason; a
#: list is the same defect with the split already done.
SHELL_OPERATOR_TOKENS = frozenset({"|", "||", "&&", ";", ">", "<", ">>", "&", "2>&1"})

#: A leading `NAME=value` token is the environment a shell sets for the command that
#: follows it, not a binary. Measured 2026-11-12: reading it as argv[0] reported 30
#: runnable claims as BINARY_ABSENT -- the harness failing to read the declaration, not the
#: declaration being unrunnable.
ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

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


def _split_env_prefix(argv: list[str]) -> tuple[dict[str, str], list[str]]:
    """Peel leading `NAME=value` tokens off a command line. Returns (env, rest)."""
    env: dict[str, str] = {}
    index = 0
    while index < len(argv) and ENV_ASSIGNMENT.match(argv[index]):
        name, _, value = argv[index].partition("=")
        env[name] = value
        index += 1
    return env, argv[index:]


def _program_absence(program: str) -> str:
    """Name WHY a declared program that is not in the tree and not on PATH cannot run.

    A path-shaped program is a claim about THIS repository (or about a machine that no
    longer exists); a bare name is a claim about a provisioned tool. Those have different
    fixes, so they get different reasons.
    """
    if "/" in program or program.endswith((".py", ".sh")):
        return "DECLARED_PROGRAM_ABSENT:" + program
    return "BINARY_ABSENT:" + program


def run_predicate(spec: Mapping[str, Any], *, cwd: pathlib.Path | None = None,
                  timeout: float = 30.0) -> dict[str, Any]:
    """Execute `spec` and say what happened. FAIL is a real possibility, which is the point.

    Measured 2026-11-12 on this tree: 595 of the 605 discovered predicates declared NO
    expectation field, and 52 of those exited non-zero -- 37 at exit 1, 14 at exit 2, one
    `npm run gate` at 254 -- while being recorded as PASS. PASS therefore meant "a process
    started", not "the claim held", and FAIL was reachable only through the 10 specs (1.7%)
    that carried an expectation. That contradicts this module's own contract ("deliberately
    able to go red: a metric that cannot decrease is not a metric"), so an undeclared
    expectation is now treated as the strictest one: a verification command that does not
    exit 0 did not verify. A receipt that expects a non-zero exit says so with `expect_exit`
    -- that is what the field is for, and a negative control that does not declare itself is
    indistinguishable from a broken claim.

    FAIL here means "the declared verification does not hold on this tree". It does not
    claim to know why: `exit` and `stderr` are carried so the cause -- a falsified claim, a
    stale path, an unprovisioned sandbox -- can be triaged instead of guessed.
    """
    argv = [str(a) for a in (spec.get("argv") or [])]
    if not argv:
        return {"verdict": "FAIL", "reason": "EMPTY_ARGV", "expectations": []}
    expectations = [field for field in EXPECTATION_FIELDS if field in spec]
    if argv[0] in SHELL_PREFIXES:
        # `set -euo pipefail cmd` is a shell script prefix. Running argv[0] alone would test
        # `set`, which always succeeds -- a false PASS on a claim never exercised.
        return {"verdict": "UNRUNNABLE", "reason": "SHELL_SCRIPT_PREFIX:" + argv[0],
                "expectations": expectations}
    if any("${" in token for token in argv):
        # `argv: ["${input.argv}"]` is a template nobody filled in. Calling that an absent
        # binary hides the real fact, which is that no command was ever declared.
        return {"verdict": "UNRUNNABLE", "reason": "UNFILLED_TEMPLATE:" + argv[0][:80],
                "expectations": expectations}
    for token in argv[1:]:
        if token in SHELL_OPERATOR_TOKENS:
            return {"verdict": "UNRUNNABLE", "reason": "SHELL_OPERATORS_IN_ARGV:" + token,
                    "expectations": expectations}
    env_prefix, rest = _split_env_prefix(argv)
    if not rest:
        return {"verdict": "UNRUNNABLE",
                "reason": "ENV_ASSIGNMENT_WITHOUT_COMMAND:" + argv[0],
                "expectations": expectations}
    program = rest[0]
    try:
        on_path = shutil.which(program) is not None
    except (OSError, ValueError):
        on_path = False
    if not on_path:
        # Not on PATH. The tree may still contain it, and WHICH of these it is decides
        # whether the fix is a chmod, a `./`, a provisioned tool, or deleting a receipt that
        # points at a program nobody committed. One `BINARY_ABSENT` string for all four made
        # 110 unrunnable claims unactionable.
        candidate = pathlib.Path(program)
        if not candidate.is_absolute() and cwd is not None:
            candidate = cwd / program
        try:
            exists_here = candidate.exists()
        except (OSError, ValueError):
            exists_here = False
        if exists_here and not os.access(candidate, os.X_OK):
            # Present in the tree at mode 644. Running `python3 <it>` instead would test a
            # DIFFERENT command than the receipt declared, so this stays unrunnable rather
            # than borrowing a PASS from a command nobody claimed.
            return {"verdict": "UNRUNNABLE",
                    "reason": "DECLARED_PROGRAM_NOT_EXECUTABLE:" + program,
                    "expectations": expectations}
        if exists_here and "/" not in program:
            # Executable, but a bare filename is resolved through PATH by execvp -- and by a
            # shell -- never through the working directory, so the declared command genuinely
            # does not run. Rewriting it to `./x` would invent a command nobody declared.
            return {"verdict": "UNRUNNABLE",
                    "reason": "BARE_FILENAME_NOT_ON_PATH:" + program,
                    "expectations": expectations}
        if not exists_here:
            # An absent program is not a pass and not a failure of the claim: untestable here.
            return {"verdict": "UNRUNNABLE", "reason": _program_absence(program),
                    "expectations": expectations}
        # Otherwise it exists and is executable where the record says it is. `shutil.which`
        # missed it because which resolves a relative path against the AUDIT's own cwd, not
        # against the record's, and subprocess chdirs to `cwd` before exec, so the declared
        # command does run. Found by test_the_same_program_becomes_runnable_when_the_tree_
        # makes_it_executable, which failed until this branch existed.
    child_env = None
    if env_prefix:
        child_env = dict(os.environ)
        child_env.update(env_prefix)
    try:
        proc = subprocess.run(rest, capture_output=True, timeout=timeout, cwd=cwd,
                              env=child_env)
    except subprocess.TimeoutExpired:
        # Named with its budget, because "unmeasurable within 30s" is a fact about this
        # instrument, not about the claim. A bare exception class name reads as a crash and
        # hides that the fix is the budget. 19 of 605 predicates land here once env-prefixed
        # commands are actually run, including two that invoke the whole test suite.
        return {"verdict": "UNRUNNABLE", "reason": f"TIMEOUT_BUDGET_{timeout:g}s",
                "expectations": expectations}
    except (OSError, subprocess.SubprocessError) as exc:
        return {"verdict": "UNRUNNABLE", "reason": f"{type(exc).__name__}:{exc}"[:200],
                "expectations": expectations}
    # Tools do not all produce UTF-8. Replacing undecodable bytes keeps the expectation
    # checkable instead of turning a decode error into an exception inside the audit.
    proc.stdout = (proc.stdout or b"").decode("utf-8", "replace")
    proc.stderr = (proc.stderr or b"").decode("utf-8", "replace")

    # What actually ran, carried on every verdict so a PASS can be told apart from a
    # process that merely started. Without `expectations` the report cannot distinguish
    # "the claim was checked and held" from "nothing was checked and nothing failed".
    ran = {"exit": proc.returncode, "expectations": expectations,
           "env_prefix": sorted(env_prefix) or None}

    if "expect_exit" in spec and int(proc.returncode) != int(spec["expect_exit"]):
        return {"verdict": "FAIL",
                "reason": f"EXIT {proc.returncode} != {spec['expect_exit']}",
                "stdout": proc.stdout[:400], "stderr": proc.stderr[:400], **ran}
    if "expect_exit" not in spec and proc.returncode != 0:
        # THE FIX. Before this, 52 receipts whose declared verification exited non-zero
        # were recorded as PASS, because no expectation meant nothing could contradict them.
        return {"verdict": "FAIL",
                "reason": f"EXIT {proc.returncode} WITHOUT_EXPECTATION",
                "stdout": proc.stdout[:400], "stderr": proc.stderr[:400], **ran}
    needle = spec.get("expect_stdout_contains")
    if needle is not None and str(needle) not in proc.stdout:
        return {"verdict": "FAIL", "reason": f"STDOUT MISSING {needle!r}",
                "stdout": proc.stdout[:400], **ran}
    version = spec.get("expect_version")
    if version is not None and str(version) not in (proc.stdout + proc.stderr):
        return {"verdict": "FAIL", "reason": f"VERSION MISSING {version!r}",
                "stdout": proc.stdout[:400], "stderr": proc.stderr[:400], **ran}
    digest = spec.get("expect_stdout_sha256")
    if digest is not None and hashlib.sha256(proc.stdout.encode()).hexdigest() != str(digest):
        return {"verdict": "FAIL", "reason": "STDOUT SHA MISMATCH", **ran}
    for name, want in dict(spec.get("expect_file_sha256") or {}).items():
        got = _sha256_file(pathlib.Path(name))
        if got != want:
            return {"verdict": "FAIL", "reason": f"FILE SHA MISMATCH:{name}", **ran}
    return {"verdict": "PASS", "reason": None, "stdout": proc.stdout[:200], **ran}


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
    # A skill is checkable only if it can be RE-EXECUTED. Counting a stored
    # `twin_verification` record would be history: it says a check was once run, not that the
    # rule still holds. `skill_recheck_v1` re-applies the rule to the source it was taught on,
    # and reports ABSENT when the store kept only a hash of that source -- which is the real
    # state of every rule taught before 2026-11-12.
    # For those, `self_witness` re-applies the rule to the smallest text its OWN pattern
    # denotes and checks the rewrite it declares, plus a near-miss it must leave alone. That is
    # a weaker check than the demonstration and is counted in its own column: it shows a shipped
    # lesson still means what it says to the engine that applies it, not that it still fixes the
    # bug it was learned from.
    recheck = {"PASS": 0, "FAIL": 0, "ABSENT": 0}
    witness = {"PASS": 0, "FAIL": 0, "ABSENT": 0}
    recheckable_any = 0
    witness_only = 0
    stored_total = None
    detail = None
    try:
        from canonical.swe_kernel import skill_recheck_v1 as R  # local: avoid import cycles
        report = R.recheck_store(store.db_path)
        if report.get("error"):
            detail = report["error"]
        else:
            recheck = dict(report["counts"])
            witness = dict(report.get("self_witness_counts") or witness)
            recheckable_any = int(report.get("recheckable_any") or 0)
            witness_only = int(report.get("self_witness_only") or 0)
            stored_total = report.get("total")
    except Exception as exc:                      # a broken recheck must not read as a pass
        detail = f"{type(exc).__name__}:{exc}"[:120]

    # THE DENOMINATOR MUST BE THE POPULATION THE CHECK RAN OVER.
    #
    # `seen` is what the agent can RECALL (`_load_rules` reads one domain only); `recheck_store`
    # re-executes every stored row. Measured 2026-11-12 with the two mixed: a store holding one
    # recallable rule and one stored-but-unrecallable one reported `checkable 2` over `total 1`,
    # an auditability of 200%. A fraction above 1 is the instrument lying upward, which is the
    # one thing it must not do, so the denominator is the larger population and the difference
    # is reported as what it is: a lesson in memory that nothing can recall.
    total = len(seen)
    unreachable = 0
    if isinstance(stored_total, int):
        total = max(len(seen), stored_total)
        unreachable = max(0, stored_total - len(seen))

    # A rule checkable by BOTH mechanisms is one checkable rule, so the count comes from the
    # store's per-rule union and never from summing the two columns.
    checkable = recheckable_any or (recheck.get("PASS", 0) + recheck.get("FAIL", 0))
    checkable = min(checkable, total) if total else checkable
    taught = recheck.get("PASS", 0) + recheck.get("FAIL", 0)
    note = (f"re-executable {checkable} (taught source {taught}: PASS {recheck.get('PASS', 0)}, "
            f"FAIL {recheck.get('FAIL', 0)}; self-witness {witness.get('PASS', 0) + witness.get('FAIL', 0)}"
            f": PASS {witness.get('PASS', 0)}, FAIL {witness.get('FAIL', 0)}, "
            f"alone {witness_only}), no check {max(0, recheck.get('ABSENT', 0) - witness_only)}")
    if unreachable:
        note += f"; {unreachable} stored but not recallable by any lookup"
    if detail:
        note += f"; recheck unavailable: {detail}"
    return {"layer": "skills", "total": total, "checkable": checkable,
            "note": note, "recheck": recheck, "self_witness": witness,
            "self_witness_only": witness_only, "stored_not_recallable": unreachable,
            "recallable": len(seen),
            "fail": recheck.get("FAIL", 0) + witness.get("FAIL", 0)}


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
    try:
        proc = subprocess.run([sys.executable, "-m", "pytest", str(tests_dir),
                               "--collect-only", "-q"],
                              cwd=root, capture_output=True, text=True, timeout=1800)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"layer": "test_modules", "total": None, "checkable": None,
                "error": f"PYTEST_UNRUNNABLE:{type(exc).__name__}"}
    # MEASURED 2026-11-12: with no pytest installed, `python -m pytest` exits 1 and prints
    # nothing parseable, and this function used to report `total 0, checkable 0` -- a
    # confident zero where the truth was "could not measure". A missing measurement must
    # read as missing, or the number is worse than no number.
    if "No module named pytest" in (proc.stderr or "") or "No module named pytest" in (proc.stdout or ""):
        return {"layer": "test_modules", "total": None, "checkable": None,
                "error": "PYTEST_NOT_INSTALLED"}
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
    if not collected:
        return {"layer": "test_modules", "total": None, "checkable": None,
                "error": "COLLECTION_OUTPUT_UNPARSEABLE"}
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


def receipts(root: pathlib.Path) -> dict[str, Any]:
    """Receipts that name the program that measured them, and whether it still exists.

    Measured 2026-11-12: 67 receipts carry `measurement_program_sha256` and none names a
    locatable program, so the field is unfalsifiable in every instance. A layer that scores
    0 here is not "no receipts" -- it is "receipts that cannot be contradicted".
    """
    try:
        from canonical.tools import receipt_program_identity_v1 as R
    except Exception as exc:                      # pragma: no cover
        return {"layer": "receipts", "total": None, "checkable": None,
                "error": f"{type(exc).__name__}:{exc}"[:120]}
    report = R.scan(root)
    total = sum(report["counts"].values())
    checkable = report["checkable"]
    return {"layer": "receipts", "total": total, "checkable": checkable,
            "note": (f"MATCH {report['counts'].get('MATCH', 0)}, "
                     f"MISMATCH {report['counts'].get('MISMATCH', 0)}, "
                     f"no locatable program {report['counts'].get('NO_PROGRAM', 0)}"),
            "receipts": report["counts"]}


def rules_execute(root: pathlib.Path) -> dict[str, Any]:
    """Do stored rules survive being EXECUTED against a spec, or only re-checked structurally?

    The six other layers all verify consistency: a rule still applies, a hash still matches, a
    pin still resolves. Consistency is cheap. This layer asks whether applying the learned edit
    preserves the behaviour the program already had, on a victim the rule was never taught on.
    """
    try:
        from canonical.tools import rule_generalization_probe_v1 as P
    except Exception as exc:                      # pragma: no cover
        return {"layer": "rules_execute", "total": None, "checkable": None,
                "error": f"{type(exc).__name__}:{exc}"[:120]}

    demo = P.demonstrate()
    total = len(demo)
    checkable = sum(1 for v in demo.values() if v["verdict"] in (P.HOLDS, P.BREAKS))
    broken = [k for k, v in demo.items() if v["verdict"] == P.BREAKS]
    return {"layer": "rules_execute", "total": total, "checkable": checkable,
            "note": f"{checkable}/{total} executed against an oracle; "
                    f"{len(broken)} broke behaviour ({', '.join(broken) or 'none'})"}


def external_environment(root: pathlib.Path) -> dict[str, Any]:
    """The one layer measured on environments nobody in this repository wrote.

    Every other layer audits this tree's own claims about itself. This one reads the MiniWoB++
    runs: 130 pages, the page's own reward as the only judge, scored on instances nobody had
    looked at when the learner was written. It sat unread for five passes while the same
    question was argued from literature.
    """
    try:
        from canonical.tools import one_success_where_it_counts_v1 as L
    except Exception as exc:                      # pragma: no cover
        return {"layer": "external_environment", "total": None, "checkable": None,
                "error": f"{type(exc).__name__}:{exc}"[:120]}
    try:
        result = L.report()
    except FileNotFoundError:
        return {"layer": "external_environment", "total": 0, "checkable": 0,
                "note": "no recorded run; the claim is unmeasured here"}
    flat = result["where_replay_is_not_enough"]
    return {"layer": "external_environment", "total": len(result["ladder"]),
            "checkable": len([r for r in result["ladder"] if r["present"]]),
            "note": (f"{result['run']}: one success {flat['one_success']:.1%} vs replay "
                     f"{flat['replay']:.1%} where replay is not enough; denied the instruction "
                     f"{flat['denied_the_instruction']:.1%}"),
            "contradictions": result["contradictions"]}


def bottleneck(root: pathlib.Path) -> dict[str, Any]:
    """Which explanation of the external-environment result survives a confound check.

    The intuitive story -- "vague demonstrations transfer badly" -- is measured and rejected
    (r = +0.18, wrong sign; +0.12 once first-success cost is held fixed). What survives is
    whether a demonstration could be found at all. Reporting the rejected story as a bottleneck
    would send the next pass in the wrong direction, which is why it is a layer here.
    """
    try:
        from canonical.tools import what_a_demonstration_leaves_open_v1 as W
        result = W.report()
    except Exception as exc:                      # pragma: no cover
        return {"layer": "bottleneck", "total": None, "checkable": None,
                "error": f"{type(exc).__name__}:{exc}"[:120]}
    rel = result["relationships"]
    if rel.get("verdict") == "TOO_FEW_PAGES":
        return {"layer": "bottleneck", "total": rel["n"], "checkable": 0,
                "note": "too few pages to separate the explanations"}
    return {"layer": "bottleneck", "total": rel["n"], "checkable": 1,
            "note": (f"openness {rel['openness']['r_with_success']:+.2f} "
                     f"-> {rel['openness']['partial_r_controlling_for_cost']:+.2f} controlling for "
                     f"cost; cost {rel['cost']['r_with_success']:+.2f}; verdict {rel['verdict']}"),
            "rerun": result["feasibility"]["status"],
            "replication": _replication_note()}


def _replication_note() -> str:
    """Did the ordering reproduce on instances nobody had used? One line, or the reason not."""
    try:
        from canonical.tools import one_success_where_it_counts_v1 as L
        check = L.replication_check()
    except Exception as exc:                      # pragma: no cover
        return f"error:{type(exc).__name__}"
    if not check.get("available"):
        return "no replication on file"
    if check.get("ordering_reproduces"):
        return (f"ordering reproduces on {check['pages']} pages, seeds "
                f"{check['test_seeds'][0]}+ ({check['replication_run']})")
    return f"ORDERING DOES NOT REPRODUCE ({check['replication_run']})"


def audit(root: pathlib.Path = REPO_ROOT, *, run: bool = False) -> dict[str, Any]:
    layers = [capabilities(root), skills(root), process_sites(root), test_modules(root),
              binary_predicates(root), receipts(root), rules_execute(root),
              external_environment(root), bottleneck(root)]
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

    # A PASS is not one thing. Split it, because the difference is the whole measurement:
    # `pass_checked` is a claim somebody wrote a predicate for, `pass_started` is a process
    # that launched and exited 0 with nothing asserted about its output. Reporting only the
    # sum is how 10 checked claims were read as 495 verified ones.
    pass_checked = sum(1 for item in predicates
                       if item["verdict"] == "PASS" and item.get("expectations"))
    pass_started = counts.get("PASS", 0) - pass_checked
    declaring = sum(1 for item in predicates if item.get("expectations"))

    # A layer that re-executes its own records can contradict them, and a contradiction must be
    # able to gate the same way a predicate FAIL does -- otherwise the audit is green by
    # construction, which is the one property this instrument exists to not have.
    layer_failures = sum(int(layer.get("fail") or 0) for layer in layers)

    return {
        "schema": SCHEMA,
        "authority": "NONE",
        "layers": layers,
        "predicates_run": len(predicates),
        "predicate_verdicts": counts,
        "predicate_results": predicates,
        "predicates_declaring_an_expectation": declaring,
        "pass_checked": pass_checked,
        "pass_started": pass_started,
        "layer_failures": layer_failures,
        "red": bool(counts.get("FAIL")) or bool(layer_failures),
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
            print(f"  declaring an expectation: {report['predicates_declaring_an_expectation']}"
                  f" of {report['predicates_run']}")
            print(f"  PASS because it was CHECKED: {report['pass_checked']}")
            print(f"  PASS because it only STARTED (exit 0, nothing asserted):"
                  f" {report['pass_started']}")
            failures = [item for item in report["predicate_results"]
                        if item["verdict"] == "FAIL"]
            unrunnable = [item for item in report["predicate_results"]
                          if item["verdict"] == "UNRUNNABLE"]
            if failures:
                print(f"\n  FAIL -- the declared verification does not hold on this tree:")
                for item in failures:
                    print(f"    exit={str(item.get('exit')):>4} "
                          f"{' '.join(str(a) for a in item['argv'])[:64]:66} "
                          f"{item.get('reason')}")
            if unrunnable:
                print(f"\n  UNRUNNABLE -- grouped by cause, because the causes have "
                      f"different fixes:")
                grouped: dict[str, list[str]] = {}
                for item in unrunnable:
                    cause = str(item.get("reason") or "?").split(":")[0]
                    grouped.setdefault(cause, []).append(
                        " ".join(str(a) for a in item["argv"])[:70])
                for cause in sorted(grouped, key=lambda c: -len(grouped[c])):
                    examples = grouped[cause]
                    print(f"    {len(examples):4d}  {cause}")
                    for line in sorted(set(examples))[:3]:
                        print(f"          {line}")
        else:
            print("\n(run with --audit to execute the predicates that exist)")
    return 1 if report["red"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
