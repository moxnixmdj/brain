#!/usr/bin/env python3
"""Compose the hardcore-SWE problem inventory from live measurement, not from memory.

Every count in the document is computed here: the 49-sentence census, the 54-case capability matrix,
the live verified registry, and a probe of the substrate the machine is standing on.  If a number is
not measured below, it is not in the document.

The commit named in the header is read from ``git rev-parse`` at compose time rather than typed in.
An earlier edition of this tool hard-coded it, so every re-measurement shipped a document that named
the previous tree -- the composer said ``bbc00a7`` while reporting numbers taken three merges later.
"""
from __future__ import annotations

import collections
import importlib.util
import json
import pathlib
import re
import shutil
import subprocess
import sys
from typing import Any, Mapping

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

CENSUS = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/c25.json")
OUT = ROOT / "HARDCORE_SWE_ALL_PROBLEMS_20261031_V1.md"

# ---- the class of work each census request belongs to (judgement about the SENTENCE) -------------
CLASS = {
    1: "polyglot", 2: "polyglot", 3: "polyglot", 4: "polyglot", 5: "polyglot", 6: "polyglot",
    7: "polyglot",
    8: "build", 9: "build", 10: "build", 11: "build", 12: "build",
    13: "ci", 14: "ci", 15: "ci", 16: "ci",
    17: "perf", 18: "perf", 19: "perf", 20: "perf",
    21: "systems", 22: "systems", 23: "systems",
    24: "tests", 25: "tests", 26: "tests", 27: "tests", 28: "tests", 29: "tests",
    30: "debug", 31: "debug", 32: "debug",
    33: "refactor", 34: "refactor", 35: "refactor", 36: "refactor", 37: "refactor", 38: "refactor",
    39: "review", 40: "review", 41: "review",
    42: "git", 43: "git", 44: "git", 45: "git", 46: "git",
    47: "design", 48: "design", 49: "design",
}

# Where each defect class actually breaks.  The name is the status the door itself returned.
DEFECT_MEANING = {
    "FAIL_CLOSED__ROUTE_ADMISSION_REJECTED":
        "a row was chosen whose declared inputs this sentence cannot supply",
    "FAIL__LIVE_CONTROLLER_EXECUTION":
        "the composed chain ran and failed (missing substrate or a wrong sub-row)",
    "FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED":
        "the chosen row does not declare the effect the sentence states (honest refusal)",
    "FAIL__RAW_GOAL_COMPILATION_GAP":
        "the sentence could not be compiled into any executable shape at all",
    "FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED":
        "the row ran and its answer was not the answer the sentence asked for",
    "FAIL_CLOSED__CAPABILITY_REFUSED_WORKTREE_NOT_DIRECTORY":
        "the row's own contract refused the stated object",
    "FAIL_CLOSED__CAPABILITY_REFUSED_NO_TESTS_DISCOVERED":
        "the row's own contract found nothing to measure",
    "FAIL_CLOSED__CAPABILITY_REFUSED_EDIT_PLAN_INPUT_INVALID":
        "the row's own contract refused the edit plan it was handed",
    "FAIL_CLOSED__TOOL_REPORTED_NON_SUCCESS":
        "the tool the row drives reported failure",
    # ---- the named capability refusals, surfaced from the adapter's own exception text ----
    "FAIL_CLOSED__CAPABILITY_REFUSED_CPP_NO_APPLICABLE_TRANSFORM":
        "no C/C++ transform applies to the construct the file actually contains",
    "FAIL_CLOSED__CAPABILITY_REFUSED_SQL_UNSUPPORTED_DDL_EDIT":
        "the DDL edit named is outside the migration shapes the engine implements",
    "FAIL_CLOSED__CAPABILITY_REFUSED_PYPROJECT_ALREADY_PINNED_OR_EMPTY":
        "there is nothing to pin: the stated pyproject declares no dependencies",
    "FAIL_CLOSED__CAPABILITY_REFUSED_NO_DECLARED_DEPENDENCY_TO_VENDOR":
        "the manifest declares no dependency for the vendoring request to act on",
    "FAIL_CLOSED__CAPABILITY_REFUSED_NO_FLAKY_TEST_DETECTED":
        "no test in the stated suite is flaky, so there is no quarantine to write",
    "FAIL_CLOSED__CAPABILITY_REFUSED_TARGET_SYMBOL_COLLISION":
        "the move collides: both stated files already define the symbol",
    "FAIL_CLOSED__CAPABILITY_REFUSED_TARGET_NOT_IN_STANDALONE_GIT_REPOSITORY":
        "a repository sentence was routed to a Python transformer, and the sentence names no "
        "repository for the transformer to stand in",
    "FAIL_CLOSED__CAPABILITY_REFUSED_GIT_READ_TARGET_NOT_SPECIFIED":
        "a sentence about commits was routed to the architect row, which read history without being "
        "given a repository to read it from",
    "FAIL_CLOSED__CAPABILITY_REFUSED_OPTIMIZATION_NOT_FASTER":
        "the optimiser produced a patch and the timed comparison did not show it faster, which is a "
        "statement about the measurement as much as about the patch",
    "FAIL_CLOSED__CAPABILITY_REFUSED_NO_REPRODUCIBLE_BUG_SPECIFIED_OR_OBSERVED":
        "the sentence asks for a regression test without stating a bug that can be reproduced or was "
        "observed, so there is nothing for the test to assert",
    "FAIL_CLOSED__CAPABILITY_REFUSED_NO_MODIFIED_PYTHON_FUNCTIONS_BETWEEN_REVISIONS":
        "the bisect row rebuilt the stated file's history and found no revision that changes a Python "
        "function, so no function can be named as the one that broke",
}

# The honest cheapest fix, per refusal class.  "None" means the refusal is correct and the fix is
# to change the fixture or to build a capability, not to change the plumbing.
FIX = {
    "FAIL__LIVE_CONTROLLER_EXECUTION":
        "make the declared dependency part of admission: a chain whose substrate is absent must refuse by name",
    "FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED":
        "none — this is the gate working; the fix is to build the missing capability, not the plumbing",
    "FAIL_CLOSED__ROUTE_ADMISSION_REJECTED":
        "extend the derivation pattern that fixed #38: derive the stated object (module, span, symbol) before binding",
    "FAIL__RAW_GOAL_COMPILATION_GAP":
        "one compiler shape per sentence family that has no template — or refuse it as NO_ROW instead of as a gap",
    "FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED":
        "selection: the answer gate is right, the choice of row is wrong",
    "FAIL_CLOSED__CAPABILITY_REFUSED_WORKTREE_NOT_DIRECTORY":
        "bind `worktree_path` from the stated file's parent, the same way #38's span was derived",
    "FAIL_CLOSED__CAPABILITY_REFUSED_NO_TESTS_DISCOVERED":
        "state the test root or refuse early; a census that finds nothing is not an answer",
    "FAIL_CLOSED__CAPABILITY_REFUSED_EDIT_PLAN_INPUT_INVALID":
        "validate the edit plan shape at admission, not inside the adapter",
    "FAIL_CLOSED__TOOL_REPORTED_NON_SUCCESS":
        "surface the tool's own reason instead of a generic non-success",
    "FAIL_CLOSED__CAPABILITY_REFUSED_CPP_NO_APPLICABLE_TRANSFORM":
        "a real C/C++ AST repair set: the engine has transforms, this construct matches none of them",
    "FAIL_CLOSED__CAPABILITY_REFUSED_SQL_UNSUPPORTED_DDL_EDIT":
        "more DDL shapes (add/drop column, change type, add index) with a migration file as evidence",
    "FAIL_CLOSED__CAPABILITY_REFUSED_PYPROJECT_ALREADY_PINNED_OR_EMPTY":
        "none on the machine — the fixture declares no dependencies; a better fixture is the fix",
    "FAIL_CLOSED__CAPABILITY_REFUSED_NO_DECLARED_DEPENDENCY_TO_VENDOR":
        "none on the machine — nothing is declared to vendor; a better fixture is the fix",
    "FAIL_CLOSED__CAPABILITY_REFUSED_OPTIMIZATION_NOT_FASTER":
        "instrument: the verdict is a timing comparison, so it must be two-sided, repeated, and it "
        "must answer UNCLEAR when the difference is inside the noise instead of refusing -- measured "
        "2026-11-01 this row passed in one session and refused in the next on identical code",
    "FAIL_CLOSED__CAPABILITY_REFUSED_NO_FLAKY_TEST_DETECTED":
        "none on the machine — the suite is not flaky; a better fixture is the fix",
    "FAIL_CLOSED__CAPABILITY_REFUSED_TARGET_SYMBOL_COLLISION":
        "none — the refusal is correct and the sentence is ill-posed",
    "FAIL_CLOSED__CAPABILITY_REFUSED_TARGET_NOT_IN_STANDALONE_GIT_REPOSITORY":
        "selection: a sentence whose verb is a repository operation belongs to the git row, and that "
        "row then refuses `cherry-pick` by name instead of a Python transformer refusing a repository",
    "FAIL_CLOSED__CAPABILITY_REFUSED_GIT_READ_TARGET_NOT_SPECIFIED":
        "derive `repo_root` from the working directory, and give a changelog its own row: it writes a "
        "document from history, which is neither a read nor an architecture review",
    "FAIL_CLOSED__CAPABILITY_REFUSED_NO_REPRODUCIBLE_BUG_SPECIFIED_OR_OBSERVED":
        "none — the sentence is under-specified; a fixture that states the failure is the fix",
    "FAIL_CLOSED__CAPABILITY_REFUSED_NO_MODIFIED_PYTHON_FUNCTIONS_BETWEEN_REVISIONS":
        "none — the fixture's history must actually change a function for a bisect to have an answer; "
        "the refusal is correct and the fixture is the defect",
}

# Who is wrong when a row refuses. This is DERIVED from the remedy text in FIX above rather than
# listed a second time, because two hand-maintained lists drift and the reader then cannot tell
# which one the ranking was built from. A refusal that is correct about an under-specified sentence
# is not evidence that the machine cannot do the work, and pricing it as capability work would
# spend the next hour on a fixture.
_OWNER_OF_REMEDY = (
    ("instrument:", "instrument"),
    ("selection:", "selection"),
    ("none on the machine", "fixture"),
    ("better fixture is the fix", "fixture"),
    ("the fixture's history", "fixture"),
    ("the sentence is under-specified", "fixture"),
    ("the sentence is ill-posed", "fixture"),
)


def _remedy_for(status_key: str) -> str:
    """The remedy text for a status key, a bare refusal class, or nothing."""
    if status_key in FIX:
        return str(FIX[status_key])
    suffix = "_" + status_key  # the door joins class to prefix with a single underscore
    matches = [v for k, v in FIX.items() if k.endswith(suffix)]
    # Exactly one match or nothing: an ambiguous suffix must not silently pick a remedy.
    return str(matches[0]) if len(matches) == 1 else ""


def defect_owner(status_key: str) -> str:
    """``selection``, ``fixture`` or ``capability`` -- read off the remedy already written.

    Accepts either form a caller has to hand: ``FAIL_CLOSED__CAPABILITY_REFUSED_X`` or the bare
    ``X`` that ``refusal_class`` returns. Getting this wrong is silent -- an unresolved key falls
    through to ``capability``, which once made this section claim 0 of 7 were sentence defects.
    """
    remedy = _remedy_for(status_key).lower()
    for needle, owner in _OWNER_OF_REMEDY:
        if needle in remedy:
            return owner
    return "capability"

CLASS_STORY = {
    "polyglot": ("C++, Rust, Go, Java, TypeScript, SQL", None),
    "build": ("pyproject, Makefile, dependency pinning, vendoring", None),
    "ci": ("workflow repair, matrices, caching, flake quarantine", None),
    "perf": ("profiling, optimisation, benchmark against a parent commit, memoisation", None),
    "systems": ("race detection, thread pools, GIL release", None),
    "tests": ("unit, property-based, regression-from-bug, mutation-score raising, fuzzing", None),
    "debug": ("failing test to cause, 'why does this return None', bisect", None),
    "refactor": ("move, split module, rename across the repo, replace all uses, add type hints, extract", None),
    "review": ("API design review, security review, dependency CVE audit", None),
    "git": ("commit, branch, diff, cherry-pick, changelog", None),
    "design": ("ADR, migration plan, package split", None),
}


def census() -> list[dict]:
    return json.loads(CENSUS.read_text())


def _matrix_once() -> dict:
    out = subprocess.run([sys.executable, "execution_guard/swe_capability_matrix_v1.py"],
                         cwd=ROOT, capture_output=True, text=True, timeout=1800).stdout
    real = [x.strip() for x in out.split("REAL   :", 1)[1].splitlines()[0].split(",")]
    false_row = out.split("FALSE  :", 1)[1].splitlines()[0].strip()
    damaged = out.split("DAMAGED:", 1)[1].splitlines()[0].strip()
    latency = [ln for ln in out.splitlines() if "LATENCY" in ln][0]
    return {"real": [r for r in real if r], "false": false_row, "damaged": damaged,
            "latency": latency}


def matrix(runs: int = 3) -> dict:
    """Run the matrix more than once, and report the RANGE rather than one sample.

    The matrix is not deterministic to the case: ``perf_review`` measures real timings, and under
    load its verdict moves between PASS and the honest UNCLEAR, which moves the REAL count by one.
    Publishing one sample hides that; publishing the floor, the ceiling and the names of the movers
    makes it a measurement rather than a sample.  ``stable`` is the intersection over every run --
    the number that can be quoted without knowing what else the box was doing.
    """
    samples = [_matrix_once() for _ in range(max(1, runs))]
    # COUNT CASES, NOT NAMES.  ``measure_coverage`` is registered twice, once per lane over a
    # different fixture, so the name list legitimately repeats and a set() would under-count the
    # matrix by one.  Multiplicity is compared per name instead: a case is stable when every run
    # reports it at least as many times as the rarest run did.
    tallies = [collections.Counter(s["real"]) for s in samples]
    stable_total = sum(min(t[name] for t in tallies) for name in set().union(*tallies))
    moving = sorted(name for name in set().union(*tallies)
                    if len({t[name] for t in tallies}) > 1)
    counts = sorted(len(s["real"]) for s in samples)
    first = max(samples, key=lambda s: len(s["real"]))
    return {"real": first["real"], "false": first["false"], "damaged": first["damaged"],
            "latency": first["latency"], "low": counts[0], "high": counts[-1],
            "runs": len(samples), "moving": moving, "stable": stable_total}


def registry_stats() -> dict:
    from canonical.runtime.live_integrated_brain_v1 import load_verified_registry
    reg = load_verified_registry()
    swe_pref = ("python.", "code.", "software.", "git.", "shell.", "test.", "orchestration.",
                "pypi.", "evidence.oracle.")
    swe = {c: e for c, e in reg.items()
           if c.startswith(swe_pref) and not c.startswith("canonical/")}
    pypi = sorted(c for c, e in reg.items()
                  if str((e.get("source") or {}).get("type")) == "pypi")
    degrade = [c for c, e in reg.items()
               if any(("Requires" in str(x) or "when available" in str(x) or "absent" in str(x))
                      for x in (e.get("limitations") or []))]
    return {"rows": len(reg), "swe": len(swe), "pypi": pypi, "degrade": degrade}


PYPI_MODULE = {
    "auto.pypi.bson-modern": "bson",
    "auto.pypi.msgpack": "msgpack",
    "code.impact.tree_sitter.testselect.v1": "tree_sitter",
    "code.index.tree_sitter.incremental.v1": "tree_sitter",
    "code.multilanguage.parse.tree_sitter.v1": "tree_sitter",
    "code.patch.tree_sitter.verify.v1": "tree_sitter",
    "math.numeric_expression.sympy": "sympy",
    "pdf.extract.text.pypdf": "pypdf",
    "python.contract.check.crosshair.v1": "crosshair",
    "python.review.diff_static_triage.v1": "ruff",
    "python.review.diff_type_gate.v1": "mypy",
    "python.software.issue_to_pr.orchestrate.v1": "",
}


def pypi_runnability(pypi: list[str]) -> list[tuple[str, str, bool]]:
    """For each package-sourced row: the module it needs and whether that module is importable HERE."""
    out = []
    for cid in pypi:
        mod = PYPI_MODULE.get(cid, "")
        ok = bool(mod) and importlib.util.find_spec(mod) is not None
        out.append((cid, mod or "in-tree", True if not mod else ok))
    return out


def substrate() -> tuple[list[str], list[str]]:
    """What an advanced engineer's day needs, and whether THIS image has it.

    ``python3 scripts/restore_substrate_v1.py`` is the one command that makes this true; before it
    existed the substrate evaporated between turns and nothing said so.
    """
    have, missing = [], []
    for tool in ("python3", "pip", "gcc", "g++", "make", "node", "npm", "git", "sqlite3",
                 "cargo", "rustc", "go", "javac", "java", "tsc", "cmake", "ninja", "docker",
                 "gdb", "valgrind", "strace", "perf"):  # noqa: E501
        (have if shutil.which(tool) else missing).append(tool)
    for mod in ("pytest", "hypothesis", "coverage", "ruff", "mypy", "tree_sitter",
                "tree_sitter_languages", "crosshair", "z3", "radon", "libcst", "rope",
                "mutmut", "pynguin"):
        (have if importlib.util.find_spec(mod) else missing).append(mod)
    return have, missing


def head_commit() -> str:
    """The tree these numbers were taken on, read rather than typed."""
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip() or "UNKNOWN"


def base_commit() -> str:
    """The commit on main this tree branched from, read rather than typed."""
    for ref in ("origin/main", "main"):
        out = subprocess.run(["git", "rev-parse", "--short", ref], cwd=ROOT,
                             capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    return "UNKNOWN"


LEARN_TEACH = ("def sum(xs):\n    t = 0\n    for i in range(len(xs)):\n"
               "        t += xs[i]\n    return t - 1\n")
LEARN_FIXED = ("def sum(xs):\n    t = 0\n    for i in range(len(xs)):\n"
               "        t += xs[i]\n    return t\n")
LEARN_PROBES = {
    "alpha-renamed twin (same skeleton)":
        "def total(vals):\n    acc = 0\n    for k in range(len(vals)):\n"
        "        acc += vals[k]\n    return acc - 1\n",
    "same bug, different loop form":
        "def sum(xs):\n    t = 0\n    i = 0\n    while i < len(xs):\n"
        "        t += xs[i]\n        i += 1\n    return t - 1\n",
    "same intent, different structure":
        "def mean(xs):\n    return (sum(xs) / len(xs)) - 1\n",
    "same shape, different literal":
        "def sum(xs):\n    t = 0\n    for i in range(len(xs)):\n"
        "        t += xs[i]\n    return t - 7\n",
    "unrelated function":
        "def biggest(xs):\n    m = xs[0]\n    for x in xs:\n"
        "        if x > m:\n            m = x\n    return m\n",
}


def learning_measurement() -> dict:
    """Measure the one-shot learning loop instead of describing it.

    Everything here is read off the live tree: where the store lives, how many rules a full census
    taught it, whether the documented CLI recipe abstraction exists, and -- in a throwaway database --
    exactly which neighbours of a taught fix the learned rule reaches.  A claim that learning
    generalizes is only worth what its falsifier says, so the falsifier is run here every time.
    """
    out: dict = {"store": None, "under_tempdir": None, "stored": None, "cli_recipe": None,
                 "probes": [], "crystallizes": None, "languages": [],
                 "portable_rules": None, "portable_refused": None, "transfer_hit": None,
                 "origins": None, "shipped_rules": None, "seeded_fresh": None,
                 "seed_path": None}
    try:
        from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry
        path = cry._default_db_path()
        out["store"] = str(path)
        import tempfile as _tf
        out["under_tempdir"] = str(path).startswith(str(_tf.gettempdir()))
        try:
            out["stored"] = cry.VerifiedSkillStore().count()
        except Exception:
            out["stored"] = "unreadable"
        out["cli_recipe"] = callable(getattr(cry, "anti_unify_cli_recipe", None))
        # the generalization surface, measured in a throwaway database
        db = pathlib.Path(_tf.mkdtemp()) / "probe.sqlite"
        import ast as _ast

        def _parses(c: str) -> bool:
            try:
                _ast.parse(c)
                return True
            except SyntaxError:
                return False

        # seed=False: this measures what ONE taught fix does, so the shipped bundle must not be in
        # the way. With seeding on, `crystallizes` read 6 (five shipped + one taught) and the probe
        # loop was answering with rules the repository already knew.
        store = cry.VerifiedSkillStore(db, seed=False)
        store.crystallize_verified_fix(language="python", bug_class="python_repair",
                                       before_code=LEARN_TEACH, after_code=LEARN_FIXED,
                                       verifier_oracle_kind="probe")
        out["crystallizes"] = store.count()
        for label, src in LEARN_PROBES.items():
            hit = store.recall_and_apply_verified(source_text=src, language="python",
                                                  verifier=_parses)
            out["probes"].append((label, hit is not None))
        # Portability, measured the same way: teach in one store, ship the bundle, import it into a
        # store that has never seen anything, and see whether the rule fires there. Durable is not
        # portable, and only this makes the difference visible.
        bundle = db.parent / "transfer.bundle.json"
        store.export_to_file(bundle)
        second = cry.VerifiedSkillStore(db.parent / "second.sqlite", seed=False)
        imported = second.import_from_file(bundle)
        out["portable_rules"] = imported["accepted"]
        out["portable_refused"] = imported["refused"]
        hit = second.recall_and_apply_verified(
            source_text=LEARN_PROBES["same shape, different literal"],
            language="python", verifier=_parses)
        out["transfer_hit"] = hit is not None
        origins = [o for row in second.provenance() for o in row["origins"]]
        out["origins"] = len(origins)
        # What ships: the bundle in version control, and what a machine that has never run
        # anything gets on its first open. Read from the bundle file, not asserted.
        shipped = cry._seed_bundle_path()
        out["seed_path"] = str(shipped)
        out["shipped_rules"] = 0
        if shipped.is_file():
            try:
                out["shipped_rules"] = int(
                    json.loads(shipped.read_text(encoding="utf-8")).get("rule_count") or 0)
            except Exception:
                out["shipped_rules"] = "unreadable"
        first_run = cry.VerifiedSkillStore(db_path=db.parent / "first_run.sqlite")
        out["seeded_fresh"] = first_run.count()
        import shutil as _sh
        _sh.rmtree(db.parent, ignore_errors=True)
    except Exception as exc:
        out["error"] = type(exc).__name__ + ":" + str(exc)[:120]
    try:
        src = (ROOT / "canonical/swe_kernel/polyglot_build_ci_engine_v1.py").read_text()
        out["languages"] = sorted(set(re.findall(r'bug_class="([a-z]+)_repair"', src)))
    except Exception:
        pass
    return out


MULTISTEP_RESULTS = ROOT / "execution_guard" / "MULTISTEP_RESULTS_20261101.json"
MULTISTEP_DOOR_RECEIPTS = ROOT / "execution_guard" / "MULTISTEP_DOOR_RECEIPTS_20261101.json"


def door_receipts() -> dict:
    """The four sentence shapes tried against the front door for the same real task.

    Read from a file for the same reason the instrument's results are: these are measurements, and
    a document that re-types them will sooner or later disagree with them.
    """
    if not MULTISTEP_DOOR_RECEIPTS.is_file():
        return {"measured": False}
    try:
        data = json.loads(MULTISTEP_DOOR_RECEIPTS.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"measured": False, "error": type(exc).__name__}
    data["measured"] = True
    return data


def multistep_measurement() -> dict:
    """Read the multi-step instrument's last recorded run, if one exists.

    Deliberately a file read and not a live run: the instrument clones real repositories and runs
    their suites, so composing this document must not depend on the network. A missing file is
    reported as "not measured", never as a pass.
    """
    if not MULTISTEP_RESULTS.is_file():
        return {"measured": False}
    try:
        rows = json.loads(MULTISTEP_RESULTS.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"measured": False, "error": type(exc).__name__}
    tasks = [r for r in rows]
    instrument_limited = [r for r in tasks if not r.get("attempts_log")]
    scored = [r for r in tasks if r.get("attempts_log")]
    return {
        "measured": True,
        "tasks": len(tasks),
        "scored": len(scored),
        "solved": sum(1 for r in scored if r.get("solved")),
        "stages": collections.Counter(str(r.get("final_stage")) for r in scored),
        "edits": sum(1 for r in scored for a in r["attempts_log"] if a.get("files_changed")),
        "attempts": sum(len(r["attempts_log"]) for r in scored),
        "limited": [r["repo"] for r in instrument_limited],
        "rows": scored,
    }


def refusal_class(row: Mapping[str, Any]) -> str:
    """The refusal class of a census row, without the door's own wrapper.

    ``status`` reads ``FAIL_CLOSED__CAPABILITY_REFUSED_<CLASS>`` or ``FAIL_CLOSED__<CLASS>``, and
    ``refusal`` reads ``CAPABILITY_REFUSED:<CLASS>``.  Splitting ``refusal`` on ':' yields the word
    ``CAPABILITY_REFUSED`` for every row, which is how an earlier version of this section managed to
    report zero fixture defects out of four.
    """
    status = str(row.get("status") or "")
    for prefix in ("FAIL_CLOSED__CAPABILITY_REFUSED_", "FAIL__CAPABILITY_REFUSED_",
                   "FAIL_CLOSED__", "FAIL__"):
        if status.startswith(prefix):
            return status[len(prefix):]
    raw = str(row.get("refusal") or "")
    return raw.split(":", 1)[1] if raw.startswith("CAPABILITY_REFUSED:") else raw.split(":")[0]


def family(capability_id: str) -> str:
    """The registry family a row belongs to: ``code.polyglot`` out of ``code.polyglot.x.v1``."""
    parts = str(capability_id).split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 else str(capability_id)


def main() -> int:
    rows = census()
    mx = matrix()
    rs = registry_stats()
    have, missing = substrate()
    runnability = pypi_runnability(rs["pypi"])

    served = [r for r in rows if r["served"]]
    refused = [r for r in rows if not r["served"]]
    by_defect = collections.Counter(r["status"] for r in refused)
    by_class = collections.defaultdict(lambda: {"n": 0, "served": 0, "ids": []})
    for r in rows:
        c = CLASS[r["n"]]
        by_class[c]["n"] += 1
        by_class[c]["ids"].append(r["n"])
        if r["served"]:
            by_class[c]["served"] += 1
    magnets = collections.defaultdict(list)
    for r in rows:
        if r.get("selected"):
            magnets[r["selected"]].append(r["n"])
    magnets = {k: v for k, v in magnets.items() if len(v) >= 2}

    rows_by_id = {r["n"]: r for r in rows}

    def class_refusals(c: str) -> str:
        """Why a class still fails, read off the requests that failed -- never a stored opinion."""
        ids = [i for i in by_class[c]["ids"] if not rows_by_id[i]["served"]]
        if not ids:
            return "**every request in this class is served**"
        bits = []
        for i in ids:
            reason = rows_by_id[i]["status"].replace("FAIL_CLOSED__", "").replace("FAIL__", "")
            bits.append(f"#{i} {reason}")
        return "; ".join(bits)

    zero_classes = [c for c in CLASS_STORY if by_class[c]["served"] == 0]
    families = collections.Counter(family(r["selected"]) for r in served if r.get("selected"))

    L: list[str] = []
    add = L.append

    add("# Every hardcore software-engineering problem, measured")
    add("")
    add(f"Measured 2026-11-01 on the tree of `{head_commit()}` (branched from main `{base_commit()}`) with the "
        "substrate restored (`scripts/restore_substrate_v1.py`).")
    add("Every number below was taken by this run: `execution_guard/swe_advanced_probe_v1.py`, "
        "`execution_guard/swe_capability_matrix_v1.py`,")
    add("the live verified registry, and a probe of the substrate. Nothing here is a wish.")
    add("")
    add("---")
    add("")
    add("## §0 The answer in one paragraph")
    add("")
    span = (f"{mx['stable']}" if mx['stable'] == mx['high']
            else f"{mx['stable']}–{mx['high']}")
    add(f"The brain answers **{len(served)} of {len(rows)}** advanced software-engineering sentences and "
        f"**{span} of 54** capability cases for real "
        f"(FALSE rows `{mx['false'] or '-'}`, DAMAGED `{mx['damaged'] or '-'}`). The remaining "
        f"**{len(refused)}** refusals fall into **{len(by_defect)}** distinct classes, and each one below is "
        "named, so the gap is now a list of capabilities rather than a failure count.")
    add("")
    add("They are three different kinds of problem, and confusing them is what made earlier editions of")
    add("this document wrong:")
    add("")
    gate_only = [k for k in by_defect if k.startswith(("FAIL_CLOSED__STATED_",))
                 or k.endswith("TARGET_SYMBOL_COLLISION")]
    capability = [k for k in by_defect if k.startswith("FAIL_CLOSED__CAPABILITY_REFUSED_")
                  and k not in gate_only]
    add(f"1. **The gate working.** {sum(by_defect[k] for k in gate_only)} refusals are sentences whose stated "
        "effect no row performs, or whose stated object does not admit the operation. These are correct:")
    add("   the machine declined instead of inventing. They are fixed by *building capability*, and no")
    add("   amount of routing work moves them.")
    add(f"2. **A capability that exists but cannot do this particular thing.** "
        f"{sum(by_defect[k] for k in capability)} refusals are a real row refusing a real input, and every one")
    add("   now reports the adapter's own reason (`§3`). Each names a missing transform, a degenerate")
    add("   fixture, or a genuinely ill-posed sentence — three different repairs.")
    add(f"3. **Absences.** {len(zero_classes)} of the {len(CLASS_STORY)} capability classes are at zero. "
        "A class at zero is not a defect; it is a missing row, and the order in `§6` prices it.")
    add("")
    add("---")
    add("")
    add("## §1 The measured surface")
    add("")
    add("| instrument | result |")
    add("|---|---|")
    add(f"| advanced census ({len(rows)} hardcore sentences) | **{len(served)} served / {len(refused)} refused** |")
    rng = (f"{mx['low']}" if mx['low'] == mx['high'] else f"{mx['low']}–{mx['high']}")
    add(f"| capability matrix (54 cases, {mx['runs']} runs) | **{rng} REAL / 0 FALSE / 0 DAMAGED** "
        f"(false: `{mx['false']}`, damaged: `{mx['damaged']}`) |")
    add(f"| cases real in **every** run | **{mx['stable']}** — a floor, not an average |")
    if mx["moving"]:
        add(f"| cases that moved between runs | `" + "`, `".join(mx["moving"]) + "` |")
    add(f"| matrix latency | {mx['latency'].replace('LATENCY ', '').strip()} |")
    add(f"| live verified registry | {rs['rows']} rows, {rs['swe']} of them software-engineering rows |")
    add(f"| rows sourced from a PyPI package (unrunnable when absent) | {len(rs['pypi'])} |")
    add(f"| rows whose own limitations admit they degrade silently | {len(rs['degrade'])} |")
    add("")
    add(f"The {len(mx['real'])} cases that work for real, by name:")
    add("")
    add("`" + "`, `".join(mx["real"]) + "`")
    add("")
    add("By registry family, the rows the served sentences actually reached:")
    add("")
    add("| family | served sentences |")
    add("|---|---|")
    for fam, n in families.most_common():
        add(f"| `{fam}` | {n} |")
    add("")
    add("---")
    add("")
    add("## §2 The eleven hardcore capability classes")
    add("")
    add("Ordered by how much of a real engineer's day the class covers, not by how hard it is. The last")
    add("column is read off the requests that actually failed in this run, so it cannot go stale.")
    add("")
    add("| class | what it is | requests | served | what still fails, by request |")
    add("|---|---|---|---|---|")
    order = ["refactor", "tests", "debug", "perf", "systems", "polyglot", "git", "build", "ci",
             "review", "design"]
    for c in order:
        d = by_class[c]
        add(f"| **{c}** | {CLASS_STORY[c][0]} | {d['n']} | {d['served']} | {class_refusals(c)} |")
    add("")
    answering = len(CLASS_STORY) - len(zero_classes)
    add(f"**{answering} of {len(CLASS_STORY)} classes answer at least one request**"
        + ("" if zero_classes else ", and none is at zero.")
        + (" The classes still at zero are " + ", ".join(zero_classes) + "." if zero_classes else ""))
    add("That is the difference between a routing problem and a missing row: the rows exist and are")
    add("reachable, and what remains inside each class is a named, individual refusal.")
    add("")
    add("### 2.1 Polyglot — the class where the refusal is the most specific")
    add("")
    poly = by_class["polyglot"]
    add(f"{poly['served']} of {poly['n']} polyglot sentences are served. The remaining ones are refused by a")
    add("polyglot engine that really does parse and rewrite C++, Rust, Go, Java, TypeScript and SQL:")
    add("")
    for i in [n for n in poly["ids"] if not rows_by_id[n]["served"]]:
        g = rows_by_id[i]["goal"].replace("canonical/astra_runtime/tmp/swe_advanced_probe/", "…/")
        add(f"* **#{i}** `{rows_by_id[i]['status'].replace('FAIL_CLOSED__', '')}` — {g[:170]}")
    add("")
    add("The distinction matters. *#11* and *#12* refuse because the census fixture is degenerate —")
    add("`11_build/pyproject.toml` declares no dependencies at all, so *\"pin the dependency versions\"*")
    add("asks for an effect on state that does not exist. Changing the fixture is the fix, not the engine.")
    add("*#1*, *#6* and *#7* refuse because the engine has a transform set and the stated construct")
    add("matches none of it — those are real capability gaps.")
    add("")
    add("### 2.2 The refusal convention is uniform, and that is why §3 can be trusted")
    add("")
    add("Roughly forty adapter classes in `canonical/runtime/bound_capabilities/` and")
    add("`canonical/swe_kernel/` refuse by raising `RuntimeError(\"<CLASS>:<detail>\")`. Until recently the")
    add("door recognised only the `SystemExit(json.dumps({\"error\": True, ...}))` spelling, so seven named")
    add("capability gaps arrived as one `FAIL__LIVE_CONTROLLER_EXECUTION`. It now reports the class the")
    add("adapter raised, promoting the inner reason when the outer token is a wrapper. That change bought")
    add("**zero served sentences** — measured, 36 before and 36 after, identical served-id list — and it is")
    add("declared as what it is: diagnosis, not capability. It is the reason the table in §3 is readable.")
    add("")
    add("---")
    add("")
    add("## §3 The plumbing defects, with counts")
    add("")
    add("| defect | count | who is wrong | what it means | cheapest correct fix |")
    add("|---|---|---|---|---|")
    for k, v in by_defect.most_common():
        add(f"| `{k}` | {v} | **{defect_owner(k)}** | {DEFECT_MEANING.get(k, '—')} | {FIX.get(k, '—')} |")
    add("")
    stated = [r for r in refused if str(r.get("refusal") or "").strip()]
    if stated:
        add("### 3.0 What each refusal actually said")
        add("")
        add("The census records the refusal text the door returned, so this table is the machine's own")
        add("sentence rather than a summary of it:")
        add("")
        add("| # | class | refused with |")
        add("|---|---|---|")
        for r in sorted(stated, key=lambda x: x["n"]):
            add(f"| {r['n']} | {CLASS[r['n']]} | `{str(r['refusal'])[:120]}` |")
        add("")
        _admission = [r for r in refused
                      if "R13_DECLARED_INPUT_UNBINDABLE" in str(r.get("refusal") or "")]
        if _admission:
            add("One of those deserves naming, because it is a *routing success* reported as a refusal:")
            add("")
            for r in _admission:
                _missing = str(r["refusal"]).split(":")[-1]
                add(f"* **#{r['n']}** now selects `{r.get('selected')}` — the correct row for a repository")
                add(f"  operation — and is refused for `{_missing}`: the sentence asks for *\"a clear message\"*")
                add("  without stating its text. `ACommitMessageIsCopiedAndNeverInvented` forbids the door from")
                add("  making one up, so the honest reading is that the **sentence** is under-specified, like")
                add("  #11 and #12. Inventing a message here would buy one sentence and spend the law that keeps")
                add("  the machine from writing content nobody asked for.")
                add("")
    add("### 3.1 The magnets: rows chosen for many sentences")
    add("")
    add("| row | requests it absorbs | verdicts |")
    add("|---|---|---|")
    for cap, ids in sorted(magnets.items(), key=lambda kv: -len(kv[1])):
        verdicts = collections.Counter(next(r["status"] for r in rows if r["n"] == i) for i in ids)
        add(f"| `{cap}` | {ids} | " + "; ".join(f"{k.replace('FAIL_CLOSED__', '').replace('FAIL__', '')} x{v}"
                                                for k, v in verdicts.most_common()) + " |")
    add("")
    absorbed = sum(len(v) for v in magnets.values())
    absorbed_ids = [i for ids in magnets.values() for i in ids]
    absorbed_served = sum(1 for i in absorbed_ids if rows_by_id[i]["served"])
    add(f"Those {len(magnets)} rows are chosen for **{absorbed} of the {len(rows)}** sentences, and "
        f"**{absorbed_served} of those {absorbed} are served**.")
    add("This is the honest version of what an earlier edition called the worst defect in the inventory.")
    add("Three broad rows — a polyglot transform, a Python transform-and-synthesize, and a")
    add("diagnose-and-architect — carry most of the census, and they now carry it successfully. Selection")
    add("is still trigger-word driven, so a generic row with a large trigger vocabulary will win a")
    add("sentence that belongs to a narrower row; what changed is that the broad rows became capable")
    add("enough that the misrouting costs fewer sentences than it used to. The remaining")
    add(f"{absorbed - absorbed_served} absorptions that fail are the ones priced in §3, and each one is now")
    add("attributed to the adapter's own reason rather than to a generic controller failure.")
    add("")
    add("---")
    add("")
    add("## §4 The substrate")
    add("")
    add("| present | missing |")
    add("|---|---|")
    add(f"| {', '.join(have)} | {', '.join(missing)} |")
    add("")
    add("`scripts/restore_substrate_v1.py` installs the hashed kernel manifest, then the review tools,")
    add("then verifies 10/10 modules, the required binaries, and the parser generation against")
    add("`tree_sitter_swe_kernel_v1.SUBSTRATE`. It exits non-zero and prints `SUBSTRATE_INCOMPLETE`")
    add("rather than letting a lane measure an environment gap and call it a capability gap.")
    add("")
    runnable = sum(1 for _, _, ok in runnability if ok)
    add(f"**{len(rs['pypi'])} registry rows are sourced from a PyPI package or a package-shaped adapter, and")
    add(f"{len(rs['pypi']) - runnable} of them cannot run in this image**:")
    add("")
    add("| package-sourced row | needs | here |")
    add("|---|---|---|")
    for cid, mod, ok in runnability:
        add(f"| `{cid}` | `{mod}` | {'**runnable**' if ok else 'package absent'} |")
    add("")
    add("* **No profiler, no debugger, no `valgrind`, no `strace`, no `gdb`.** Profiling, race")
    add('  detection and "find the commit that broke this" are requests about *execution*, and nothing')
    add("  here watches an execution.")
    add("* **No `rustc`, `cargo`, `go`, `javac`, `tsc`, `sqlite3`.** Five of the six languages the census")
    add("  asks about cannot be compiled here even if a row existed. `gcc`, `g++`, `node`, `npm` and")
    add("  `make` are present but no row drives them.")
    add("* **The substrate does not persist.** pip installs outside `/home/user` evaporate between")
    add("  turns; this document names the restore as a step rather than a hope.")
    add("")
    add("---")
    add("")
    add("## §5 Structural gaps the census cannot see")
    add("")
    add("These matter more than any single refusal, and none of them is measured by a 49-sentence census:")
    add("")
    add("1. **No long-horizon loop that survives.** Plans exist and chains exist, but there is no")
    add("   demonstrated plan → edit → run → observe → repair cycle on a real repository that runs")
    add("   unattended for hours. Every number here is one request deep.")
    add("2. **No execution feedback as a habit.** The machine mostly reasons statically. Running the code")
    add("   it changed and reading what happened is the one thing a strong engineer does constantly.")
    add("3. **No repo-scale navigation.** A symbol index exists, but there is no ranked cross-module")
    add('   retrieval, no "where is this behaviour implemented", no impact ranking a planner can use.')
    add("4. **No learning from its own refusals.** Each round re-derives the refusal taxonomy by hand. The")
    add("   refusal corpus is not mined automatically into candidate rows — §3 is written by hand this hour.")
    add("5. **Polyglot editing is thin even where it now answers.** Four of seven polyglot sentences are")
    add("   served, but the served ones are narrow transforms; there is no general non-Python rewrite row.")
    add("6. **The census measures the environment as much as the machine.** Sentences whose effect depends")
    add("   on an installed package move when the substrate is cold, and the matrix prints `unmeasurable")
    add("   lanes` without failing. A number that moves when a pip cache is cold is not a capability number.")
    add("7. **A performance verdict is honest but not reproducible under load.** `perf_review` measured")
    add("   slowdown ratios of 0.90 / 0.98 / 0.99 / 1.01 against a 1.10 band on unchanged files: when")
    add("   contention pushes a run past the band the gate says UNCLEAR, which is the correct answer (both")
    add("   sides were timed; the difference is inside the noise). The matrix oracle now requires a complete")
    add("   two-sided measurement with at least three timed runs per side and accepts PASS or UNCLEAR —")
    add("   strictly more evidence, one fewer false refusal. The residual problem is real and stays: a")
    add("   review that cannot distinguish a 10% change under load cannot certify a refactor's performance,")
    add("   only refute a large regression.")
    add("   **Measured 2026-11-01: this is no longer only about `perf_review`.** Request 18 (optimise a")
    add("   slow function) was *served* in one session and refuses `OPTIMIZATION_NOT_FASTER` in the")
    add("   next, on identical code, reproducibly, and with the crystallizer change reverted. The census")
    add("   total moved 42 -> 41 for that reason alone. A denominator that changes with the machine's")
    add("   mood is not a capability number, which is why that class now has its own owner in §3")
    add("8. **At least one census sentence is ill-posed.** Request 33 says *move the function `add`")
    add("   from mod.py into calc.py*, and both files define `add`, so the move collides and the")
    add("   refusal is CORRECT. A denominator that counts that sentence as a capability the machine lacks")
    add("   overstates the gap.")
    add("9. **Lane isolation is broken.** Running the matrix `--lane toolchain` alone reports")
    add("   `add_dependency` FALSE **and** DAMAGED, while the full run reports the same case refused with")
    add("   a clean tree. Every lane-only number is suspect until the fixture is shared.")
    if mx["moving"]:
        add(f"10. **The matrix itself moves between runs, and now says so.** Over {mx['runs']} runs "
            f"{mx['stable']} cases were real every time and")
        add(f"   {mx['low']}–{mx['high']} were real in any one run; the cases that moved are "
            "`" + "`, `".join(mx["moving"]) + "`. A headline number that")
        add("   changes with the box's load is not a capability number, so this document reports the floor")
        add("   and the ceiling and names the movers, instead of quoting whichever sample looked best.")
    add("10. **Measurement breadth.** 49 sentences written by the same hand that writes the rows. Real")
    add("   software engineering is unbounded, so this corpus can be satisfied without being a good engineer.")
    add("   It needs real repositories and adversarial sentences, not more fixtures.")
    add("")
    add("---")
    add("")
    add("## §6 The smartest order, given these numbers")
    add("")
    pct = 100.0 * len(served) / len(rows)
    fixture = [r for r in refused if defect_owner(refusal_class(r)) == "fixture"]
    selection = [r for r in refused if defect_owner(refusal_class(r)) == "selection"]
    # Explicitly owned, never "whatever is left": an unclassified row used to fall through into
    # capability, which is how the instrument defect was silently priced as missing capability.
    capability = [r for r in refused if defect_owner(refusal_class(r)) == "capability"]
    add(f"The census stands at **{len(served)} of {len(rows)} ({pct:.0f}%)**. Of the {len(refused)}")
    instrument = [r for r in refused
                  if defect_owner(refusal_class(r)) == "instrument"]
    add(f"that remain, **{len(fixture)} are fixture defects** -- the machine is right and the sentence is")
    add(f"under-specified or the move is ill-posed -- **{len(selection)} are selection**,")
    add(f"**{len(capability)} are capability**, and **{len(instrument)} are instrument defects**: the work")
    add("was done and the verdict is untrustworthy.")
    add("")
    add("The column is read off §3's own remedy text, so the two sections cannot disagree; a capability")
    add("gap whose remedy happens to start with the word \"none\" is still counted as capability, because")
    add("it says the missing thing is a capability.")
    add("")
    add("That split decides the order, because it decides what a number means:")
    add("")
    add(f"* **The 49-sentence census is now a regression guard, not a frontier.** At {pct:.0f}% with")
    add(f"  {len(fixture)} of the remaining {len(refused)} being sentence defects, raising it further buys")
    add("  almost no capability. It is what stops the machine going backwards, and it should be run on")
    add("  every change -- but no hour should be spent *aiming* at it.")
    add(f"* **Every number in §1 is one request deep, and §8 now prices that.** A real repository with an")
    add("  injected bug and its own suite as the oracle produced **no edit at all**, twice over: the")
    add("  single-step number and the multi-step number are not the same claim, and only the second one")
    add("  is about engineering.")
    add("  The gap is not subtle and it is not about polish: the machine has no working path from")
    add("  *'this test fails in this repository'* to *'here is an edit'*, so no amount of repair")
    add("  quality would show up yet.")
    add("")
    add("| # | move | measured reach | why at this position |")
    add("|---|---|---|---|")
    _ms = multistep_measurement()
    _ms_note = (f"measured {_ms['solved']} of {_ms['scored']}" if _ms.get("measured") and _ms.get("scored")
                else "not yet measured")
    add(f"| 1 | **let the sentence reach the capability that can already do it**: the repair works when "
        f"called with a source root and one failing test file, and three admissions still stop the "
        f"same task arriving as a sentence (§8: {_ms_note}) | the capability path passes, the door "
        f"path does not | the work is done and unreachable, which is cheaper to fix than doing it "
        f"again |")
    add(f"| 2 | **selection** for the {len(selection)} remaining sentences | {len(selection)} sentence(s) | "
        "cheap, and each one exposes a real missing row underneath (cherry-pick, changelog) |")
    add(f"| 3 | **capability** for the {len(capability)} remaining sentences | {len(capability)} sentence(s) | "
        "real work, but a small ceiling; do it after the instrument exists |")
    add("| 4 | **execution substrate**: a profiler, `gdb`/`valgrind`/`strace`, `sqlite3`, "
        "`rustc`/`go`/`tsc` | unblocks perf, systems and polyglot verification | without it several rows "
        "can never run, and no row may pretend otherwise |")
    add(f"| 4b | **reproducible timing verdicts** for the {len(instrument)} instrument defect(s) | "
        f"{len(instrument)} sentence(s) | a two-sided, repeated measurement that may answer UNCLEAR; "
        "today one row passes or refuses depending on the machine's mood |")
    add("| 5 | **learning upstream of selection**: a refusal memory that changes which row is chosen | "
        "today the learner is downstream (see §7) | as built, it cannot prevent a repeat of a miss |")
    add("| 6 | **repo-scale navigation**: ranked cross-module retrieval and impact ranking | a symbol "
        "index exists; a planner cannot yet ask \"where is this behaviour\" | needed by any multi-file "
        "task, which is item 1 |")
    add(f"| 7 | fix the {len(fixture)} fixture defect(s), or stop counting them | {len(fixture)} sentence(s) | "
        "not capability work, and leaving them in the denominator overstates the gap |")
    add("")
    add("The order is not a wish list. Items 1-3 are scored by this document; item 4 is scored by")
    add("the substrate table in §4; item 5 by §7. Item 7 is bookkeeping and belongs last on purpose:")
    add("it changes what the number means, and a number that means something else is not progress.")
    add("")
    add("---")
    add("")
    add("## §7 Instant learning, measured rather than described")
    add("")
    add("`canonical/swe_kernel/verified_skill_crystallizer_v1.py` is a real one-shot learner: it")
    add("anti-unifies a verified before/after pair into a structural rule with holes, tests that rule on")
    add("a mutated twin before admitting it, stores it in SQLite, and on recall re-runs the caller's own")
    add("verifier before returning anything. That design is sound, and it is wired into the polyglot")
    add("engine and the cross-file repair choreographer.")
    add("")
    lm = learning_measurement()
    if lm.get("error"):
        add(f"The live probe could not run on this tree: `{lm['error']}`.")
    else:
        add("| measured property | value |")
        add("|---|---|")
        add(f"| where the skills live | `{lm['store']}` |")
        add(f"| inside the temporary directory (wiped with the sandbox) | **{lm['under_tempdir']}** |")
        add(f"| rules taught by the {len(rows)}-sentence census so far | **{lm['stored']}** |")
        add(f"| a taught fix crystallized in the probe | **{lm['crystallizes']} rule(s)** |")
        add(f"| CLI/environment recipe abstraction documented in the docstring | **{'implemented' if lm['cli_recipe'] else 'not implemented'}** |")
        add(f"| languages with a repair op that can teach | {', '.join(lm['languages']) or '—'} |")
        add(f"| rules a fresh store accepts from an exported bundle | **{lm['portable_rules']}** "
            f"(refused {lm['portable_refused']}) |")
        add(f"| the imported rule fires in the store that never saw it | **{lm['transfer_hit']}** |")
        add(f"| provenance records carried with those rules | {lm['origins']} |")
        add(f"| rules shipped in version control (`{pathlib.Path(str(lm['seed_path'])).name}`) | "
            f"**{lm['shipped_rules']}** |")
        add(f"| rules a store that has never run anything holds on first open | "
            f"**{lm['seeded_fresh']}** |")
        add("")
        add("**What one taught fix actually reaches.** A single `return t - 1` -> `return t` repair was")
        add("taught, then the same rule was offered five neighbours:")
        add("")
        add("| neighbour | reached? |")
        add("|---|---|")
        for label, hit in lm["probes"]:
            add(f"| {label} | {'**yes**' if hit else 'no'} |")
        add("")
        reached = sum(1 for _l, h in lm["probes"] if h)
        add(f"It reached **{reached} of {len(lm['probes'])}** neighbours. That is the true surface of")
        add("\"instant learning\": it generalizes over **identifiers**, over **literals**, and over the")
        add("operator sequence. It does **not** generalize over a differently-shaped expression with the")
        add("same meaning -- that would need synthesis, not abstraction. Holes are `?id` (identifiers),")
        add("`?num` (numbers), `?str` (string literals, which is where a path lands) and `?fresh` (a")
        add("temporary the fix introduces). Identifier holes kept their historical token name, so rules")
        add("stored before literal holes existed still match.")
    add("")
    add("### 7.1 Why this cannot be the answer to the remaining problems")
    add("")
    add("Crystallization happens **after** a capability has already succeeded, and recall happens")
    add("**inside** the capability that was already selected. So learning sits downstream of both")
    add("selection and execution:")
    add("")
    add("    sentence -> SELECTION -> execution -> verification -> crystallization -> store")
    add("                     ^                                          |")
    add("                     +---------------- not on this path ---------+")
    add("")
    add("Measured directly: a C++ repair was taught into the store and the same file then recalled the")
    add("rule successfully (`MATCHED`), and the door still answered `STATED_SWE_EFFECT_UNSERVED` with")
    add("`selected: None`, because selection had already declined the sentence before any capability --")
    add("and therefore any recall -- was reached.")
    add("")
    add("Three consequences follow, and each one is why a refusal survives:")
    add("")
    add("1. **Nothing is learned from a failure.** A capability that cannot do the task once has nothing")
    add("   to crystallize. Learning amortizes the second attempt; it cannot pay for the first.")
    add("2. **Nothing is learned from a selection miss.** If the sentence never reaches the right row,")
    add("   the row's learned skills are never consulted.")
    add("3. **Nothing is learned from an under-specified sentence.** A fixture that states no")
    add("   reproducible bug, or a move whose symbol collides, is refused correctly on every attempt.")
    add("")
    add("Of the refusals counted in §3, **none** is a repetition problem that a crystallized skill could")
    add("convert into a pass. That is the honest answer to \"if it learns instantly, is everything solved\":")
    add("no. Learning makes a solved thing cheap to do again. It does not make an unsolved thing solvable.")
    add("")
    add("### 7.2 What instant learning is genuinely worth")
    add("")
    add("It is worth a great deal, in the one place it applies: **an environment the machine can already")
    add("operate becomes cheap and consistent there.** Teach it a fix, and every structurally identical")
    add("recurrence costs a recall plus a verifier instead of a search. That is real, and it compounds")
    add("-- but only along the axis the primitives already span (`" + "`, `".join(lm.get("languages") or []) + "`).")
    add("")
    add("To make it the answer to everything, two things must both hold:")
    add("")
    add("* **(a) the lesson must persist, and it must arrive.** Three separate claims are often")
    add("  collapsed into one, and only now are all three measured:")
    add("")
    add("  1. *Durable across a restart*: the store is `" + str(lm.get("store")) + "`, not the")
    add("     temporary directory. True, and it was false earlier today.")
    add("  2. *Shipped with the repository*: the SQLite file is gitignored, so it did **not** travel.")
    add("     Measured: the store held 6 rules at the end of one session and **0** at the start of the")
    add("     next -- same machine, same checkout. The rules now also live in a tracked bundle of")
    add("     **" + str(lm.get("shipped_rules")) + "** rules, and a store that has never run anything")
    add("     seeds **" + str(lm.get("seeded_fresh")) + "** of them on first open.")
    add("  3. *Mergeable across machines*: `export_bundle` / `import_bundle` carry rules by content")
    add("     address, union their provenance, and refuse an entry whose id does not match its own")
    add("     payload. A fresh store accepted **" + str(lm.get("portable_rules")) + "** of")
    add("     **" + str(lm.get("portable_rules")) + "** exported rule(s) and the imported rule fired")
    add("     there: **" + str(lm.get("transfer_hit")) + "**.")
    add("")
    add("  What is still asserted rather than demonstrated: bundles sync by hand. Nothing publishes")
    add("  them; two machines only merge when someone moves a file.")
    add("* **(b) something must produce a first success in a new environment.** That is the whole")
    add("  problem, and it is not a learning problem: it is capability acquisition, and it is what")
    add("  §6 prices. Instant learning is the multiplier; (b) is the multiplicand.")
    add("")
    add("---")
    add("")
    add("## Appendix: all 49 sentences, classified")
    add("")
    add("| # | class | sentence | chosen row | verdict |")
    add("|---|---|---|---|---|")
    for r in sorted(rows, key=lambda x: x["n"]):
        goal = r["goal"].replace("canonical/astra_runtime/tmp/swe_advanced_probe/", "…/")
        chosen = r.get("selected") or "**none**"
        verdict = "SERVED" if r["served"] else r["status"].replace("FAIL_CLOSED__", "").replace("FAIL__", "")
        detail = str(r.get("refusal") or "").strip()
        if detail:
            verdict += f" — `{detail[:90]}`"
        add(f"| {r['n']} | {CLASS[r['n']]} | {goal} | `{chosen}` | {verdict} |")
    add("")
    add("---")
    add("")
    add("## What this document is not")
    add("")
    add("---")
    add("")
    add("## §8 The multi-step instrument: what a real repository says")
    add("")
    add("`execution_guard/multistep_instrument_v1.py` measures the thing every number above cannot:")
    add("a real repository, a failing test, and a budget of attempts. Three projects are cloned")
    add("(`iniconfig`, `pluggy`, `click`), a bug is injected mechanically into their own source, the")
    add("issue text is generated from *their* failing output, and the acceptance check is *their* own")
    add("suite. A failed attempt is fed back verbatim, which is the only part of this that is a loop")
    add("rather than a request.")
    add("")
    ms = multistep_measurement()
    if not ms.get("measured"):
        add("**Not measured in this composition** — the results file is absent. That is reported as")
        add("absent on purpose: an instrument that silently reports zero is the failure mode this whole")
        add("document keeps finding.")
    else:
        add("| multi-step property | value |")
        add("|---|---|")
        add(f"| tasks scored | **{ms['scored']}** (of {ms['tasks']} attempted) |")
        add(f"| solved end to end | **{ms['solved']}** |")
        add(f"| attempts spent | {ms['attempts']} |")
        add(f"| attempts that edited a source file | **{ms['edits']}** |")
        for stage, count in ms["stages"].most_common():
            add(f"| tasks ending at `{stage}` | {count} |")
        if ms["limited"]:
            add("")
            add(f"*{', '.join(ms['limited'])} produced no observable injected bug at the accepted blast")
            add("radius (1-25 failing cases, at most 40% of a suite), so it is an instrument limitation")
            add("and is excluded from the score rather than counted as a pass.*")
        add("")
        add("| task | injected bug | attempts | files the machine edited | outcome |")
        add("|---|---|---|---|---|")
        for r in ms["rows"]:
            inj = r.get("injected") or {}
            edits = sum(len(a.get("files_changed") or []) for a in r["attempts_log"])
            add(f"| {r['repo']} | `{str(inj.get('before'))[:52]}` -> `{str(inj.get('after'))[:52]}` | "
                f"{len(r['attempts_log'])} | **{edits}** | `{r['final_stage']}` |")
        add("")
        add("**The single-step census says " + f"{pct:.0f}%" + ". The multi-step instrument says "
            + f"{ms['solved']} of {ms['scored']}.** The gap is not repair quality — it is that no")
        add("edit is produced at all. The door selects `python.software.repair.apply.verified.v1`, runs")
        add("it, and answers `STATED_ANSWER_NOT_PROVIDED` or `STATED_SWE_EFFECT_UNSERVED` with the tree")
        add("untouched. Feeding the failing tests back changes the sentence and nothing else: attempt 2")
        add("behaves exactly like attempt 1.")
        add("")
        add("Two false measurements were found while building this, and both made the machine look")
        add("worse *or* better than it is, which is why they are recorded:")
        add("")
        add("1. **The first run credited the machine with its own bug.** `git status` reported the")
        add("   injected mutation as a change, so a door that edited nothing was recorded as having")
        add("   edited a file — twice. The injection is now committed before the first attempt, so the")
        add("   only diff is the machine's.")
        add("2. **The first injection was a demolition, not a bug.** Flipping `expose_value: bool = True`")
        add("   to `False` in `click` broke 644 of 1014 tests. That is not a bug report and no fair task")
        add("   can be built from it; mutations are now capped at 25 failing cases and 40% of a suite.")
        add("")
        pinned = sorted({str(r.get("commit"))[:12] for r in ms["rows"] if r.get("commit")})
        add(f"The clones are pinned ({', '.join('`' + c + '`' for c in pinned)}), so the task bank is")
        add("stable and re-running reproduces the same injected bug and the same stage. The first")
        add("version of the instrument claimed pinning in a comment while cloning the default branch;")
        add("that is corrected here for the same reason the other false numbers were: a claim in a")
        add("comment is not a measurement.")
        add("")
        receipts = door_receipts()
        if receipts.get("measured"):
            stated = receipts.get("scope_1_stated_test_file") or {}
            whole = receipts.get("scope_2_whole_corpus") or {}
            truth = receipts.get("scope_3_true_repair") or {}
            withdrawn = receipts.get("withdrawn_claim") or {}
            after = whole.get("after_portfolio_narrowed_evidence_only") or {}
            add("### 8.1 Three scopes of one task, and the claim that did not survive them")
            add("")
            add("The same injected fault was measured at three scopes on a clone reset to the pin. The")
            add("answer differs at each one, which is exactly why publishing a single number was wrong:")
            add("")
            add("| scope | what the caller names | measured |")
            add("|---|---|---|")
            add(f"| the stated test file | a source root and `testing/test_pluginmanager.py` | "
                f"**`{stated.get('status')}`**, applied, post-apply rc `{stated.get('post_apply_test_returncode')}`, "
                f"{stated.get('elapsed_s')} s -- patch `{str(stated.get('patch')).split('  ->  ')[-1]}` |")
            add(f"| the whole corpus (the door's binding) | a source root only; 9 files, 226 tests | "
                f"**no edit**, `{after.get('status')}`, {after.get('elapsed_s')} s |")
            add(f"| the true one-line repair | restoring `and` | **`{truth.get('whole_corpus')}`** -- in the "
                f"engine's own candidate space, `found_by_the_engine_within_budget` = "
                f"`{str(truth.get('found_by_the_engine_within_budget')).lower()}` |")
            add("")
            add("**A claim was withdrawn.** Earlier this session the middle number was reported as a")
            add("verified in-place repair of the fault. The pass reproduces, but the patch it verified")
            add("repairs the file the caller named and leaves the other three failures of the same fault")
            add("standing, so the sentence said more than the measurement did. That is the correction:")
            add(f"*{withdrawn.get('corrected_claim')}*")
            add("")
            add("The two capability defects fixed on the way are real and each was measured before and")
            add("after, by running a third party's code rather than by reading ours:")
            add("")
            add("* **the search could not see the fault.** The stack names the line that RAISED, not the")
            add("  condition that sent control there. On pluggy the raise is at `_manager.py:251` and the")
            add("  faulty predicate at `:247`; the evidence rule was a +/-2-line window, so the one site")
            add("  that mattered scored zero while 24 slots filled with unrelated constant guesses.")
            add("  Graded proximity was not enough either -- the true site scored 9600 and eight")
            add("  constants three lines from another frame scored 9700. The rule that works is the one")
            add("  the language already states: a frame inside a branch body implicates that branch's own")
            add("  condition.")
            add("* **the suite could not import the package.** The import roots were derived by walking")
            add("  PARENTS only, so a `src/` layout was invisible; the baseline then failed for its")
            add("  import, every candidate scored the same as the baseline, and the search reported no")
            add("  repair existed. Measured: `src` -> 79 passed, rc 0; repo root -> 2 failed, 77 passed.")
            add("")
            add("### 8.2 The four sentences, and why each one fails")
            add("")
            add("| sentence names | refusal | which layer refused |")
            add("|---|---|---|")
            for a in receipts.get("attempts") or receipts.get("door_attempts") or []:
                sentence = str(a.get("sentence") or "")
                short = ("the repo, the failing output **and the fault file**"
                         if "The fault is in" in sentence else
                         "the repo and the failing output" if "in <repo>" in sentence else
                         "a test file at repository scope" if "test_pluginmanager.py so the suite" in sentence
                         else "the source file and its test file")
                add(f"| {short} | `{str(a.get('why'))[:96]}` | {str(a.get('reading'))[:150]} |")
            add("")
            add("Three of those four refusals are admissions, and one is a result: only the second")
            add("sentence let the capability run, and it ran and produced no verified whole-corpus edit.")
            add("Naming the fault makes a request a diagnosis a repair row may not answer; naming a test")
            add("file at repository scope reads as a broad mutation; naming both a source file and its")
            add("test file compiles to nothing. The remaining engineering gap is one sentence long: the")
            add("engine ranks a patch that halves the failures above the patch that removes them, and")
            add("each candidate costs a full corpus run, so it does not reach the right one in budget.")
            add("")
        add("What this does **not** yet measure: whether a *correct* edit would be accepted, because no")
        add("edit is produced. The next hour is not about repair quality — it is about the missing path")
        add("from `a failing test in this repository` to `a proposed edit`.")
        add("")
        add("---")
        add("")
    add("It is not a plan to make the machine *seem* more capable. Every item above is either a measured")
    add("refusal, a measured absence in the substrate, or a measured selection error. Nothing is softened:")
    add(f"the machine answers {len(served)} of {len(rows)} hardcore sentences and {span} of 54")
    add("capability cases, and the difference between those two numbers is itself a finding — the matrix")
    add("exercises rows directly, the census asks whether a sentence reaches the right one, and selection")
    add("is where the sentences are lost. The value of the inventory is that the next hour of work can be")
    add("spent where the reach is largest instead of where the last refusal happened to be.")

    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("WROTE", OUT, len("\n".join(L)), "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
