#!/usr/bin/env python3
"""Provenance for bound capability rows -- re-derivable, not asserted.

Eight rows entered the registry carrying ``VERIFIED_BOUND_CAPABILITY`` with a
``source`` block and NO ``verification`` block at all (measured 2026-10-31 on
origin/main: ``python.refactor.inline_helper.v1``, ``python.vcs.merge_conflict.
resolve.v1``, and six ``python.source.*`` analysis rows).  The only thing saying
they were verified was the status string, which is exactly the class of claim
``test_no_registry_entry_is_left_without_proof`` exists to stop; the honest fix
is not a string but evidence.

What makes this evidence rather than a second self-report:

* the check for each row is written HERE, against a world built HERE, and it
  recomputes the answer from the tree with the standard library only -- it never
  imports the adapter it is checking;
* what it compares is GROUND TRUTH BY CONSTRUCTION ("this world has exactly
  three functions and two classes"; "this key is planted at line 3 and this
  scanner must find it without ever echoing it"; "after the inline the helper's
  name must appear nowhere and the suite must be green when THIS process runs
  it"), not the adapter's own verdict text;
* ``--check`` re-runs every check with no adapter in the loop and compares the
  result to the receipt, so the ledger is falsifiable years later.

Every receipt also carries the adapter's sha256 and a replay command, so a
disagreement is resolvable rather than a matter of trust.

usage:
  verify_bound_capability_provenance_v1.py            # verify all eight, write receipts
  verify_bound_capability_provenance_v1.py --stamp    # ... and record them in the registry
  verify_bound_capability_provenance_v1.py --check    # re-check receipts, adapters not run
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REGISTRY = ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
EVIDENCE = ROOT / "canonical/astra_runtime/evidence"
STATE = ROOT / "canonical/astra_runtime/state"

SCHEMA = "PROJECT_BRAIN_BOUND_CAPABILITY_PROVENANCE_V1"
STATE_SCHEMA = "PROJECT_BRAIN_BOUND_CAPABILITY_PROVENANCE_STATE_V1"

# The planted credential is a *shape*, not a real key: AWS access key ids are
# AKIA + 16 uppercase base32 characters, and this one spells so in the alphabet
# to make the point that no issuer is being contacted.
PLANTED_KEY = "AKIA" + "QWERTYUIOPASDFGH"[:16]


# --------------------------------------------------------------------- plumbing
def _rel(path: pathlib.Path) -> str:
    return str(pathlib.Path(path).resolve().relative_to(ROOT)).replace("\\", "/")


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def _write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _adapter_path(cid: str) -> pathlib.Path:
    caps = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]
    entry = caps[cid]
    rel = str(((entry.get("source") or {}).get("adapter_path") or ""))
    if not rel:
        rel = "canonical/runtime/bound_capabilities/%s.py" % entry["adapter_module"]
    return (ROOT / rel).resolve()


def _run_adapter(cid: str, args: dict, world: pathlib.Path) -> dict:
    caps = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]
    module = importlib.import_module(
        "canonical.runtime.bound_capabilities." + str(caps[cid]["adapter_module"]))
    return module.run(args, str(ROOT))


def _python_ok(world: pathlib.Path, argv: list[str]) -> tuple[bool, str]:
    """Run a suite with THIS process's python, in the world, and report the truth."""
    from canonical.runtime.bound_capabilities._swe_static_soundness_v1 import universal_test_argv
    env = {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(world),
           "PATH": "/usr/local/bin:/usr/bin:/bin"}
    proc = subprocess.run(universal_test_argv(sys.executable, argv),
                          cwd=str(world), capture_output=True, text=True,
                          timeout=300, env=env)
    tail = "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-4:])
    return proc.returncode == 0, tail


# ------------------------------------------------------------------- fixtures
DEFS_MODULE = '''"""Shapes, for the counter."""


class Alpha:
    def method_one(self):
        return 1

    def method_two(self):
        return 2


def top():
    return 3


class Beta:
    pass
'''


COMPLEX_MODULE = '''"""Two functions, one flat and one not."""


def flat(values):
    return sum(values)


def nested(values):
    total = 0
    for value in values:
        if value > 0:
            for inner in range(value):
                if inner % 2:
                    total += inner
    return total
'''


DEAD_TOOLS = '''"""Helpers, only one of which is reached."""


def used_helper(value):
    return value * 2


def unused_helper(value):
    return value + 1
'''

DEAD_APP = '''"""The only caller in the tree."""

from tools import used_helper


def report(value):
    return used_helper(value)
'''

SECRET_CONFIG = '''"""Configuration, one line of which is a credential-shaped literal."""

DATABASE = "postgres://localhost/app"
AWS_ACCESS_KEY_ID = "%s"
REGION = "eu-west-1"
''' % PLANTED_KEY

TAINT_APP = '''"""Input boundary and a shell sink."""

import json
import os


def handle(raw):
    payload = json.loads(raw)
    name = payload["name"]
    os.system("echo " + name)
'''

TAINT_CLEAN = '''"""No external bytes reach a shell."""

import os


def handle():
    count = 3
    os.system("echo %d" % count)
'''

ADEQUACY_MODULE = '''"""Two functions: one the tests exercise, one they never touch."""


def covered(value):
    return value + 1


def never_called(value):
    return value - 1
'''

ADEQUACY_TESTS = '''import unittest

from app.mod import covered


class T(unittest.TestCase):
    def test_covered(self):
        self.assertEqual(covered(1), 2)
'''

INLINE_MODULE = '''"""Logic."""


def _price_with_tax(price_cents, rate):
    return price_cents + price_cents * rate // 100


def total(items, rate):
    return sum(_price_with_tax(i["price_cents"], rate) for i in items)
'''

INLINE_TESTS = '''import unittest

from app.service import total


class T(unittest.TestCase):
    def test_total(self):
        self.assertEqual(total([{"price_cents": 100}, {"price_cents": 50}], 10), 165)
'''

CONFLICTED_MODELS = '''"""Models."""

<<<<<<< HEAD
def line_total(item):
    return item.price_cents * item.qty
=======
class Item:
    def __init__(self, price_cents, qty=1):
        self.price_cents = price_cents
        self.qty = qty

    def total(self):
        return self.price_cents * self.qty
>>>>>>> feature/item-class
'''

CONFLICT_TESTS = '''import unittest

from app.models import Item


class T(unittest.TestCase):
    def test_total(self):
        self.assertEqual(Item(100, 2).total(), 200)
'''


def _world(mission: str) -> pathlib.Path:
    """The world lives WITH its receipt: a ledger that depends on `tmp/` is not a ledger.

    Everything a check reads is either the world snapshot under the evidence directory
    or an artifact beside it, so ``--check`` works from any checkout, years later, with
    no adapter and no scratch directory in the loop.
    """
    world = EVIDENCE / ("%s__WORLD" % mission)
    shutil.rmtree(world, ignore_errors=True)
    world.mkdir(parents=True)
    return world


# ------------------------------------------------------------------- the rows
def build_definition_count(world: pathlib.Path) -> dict:
    _write(world / "defs/mod.py", DEFS_MODULE)
    return {"source_root": _rel(world / "defs"), "output_path": _rel(world / "answer.json")}


def check_definition_count(world: pathlib.Path, report: dict) -> tuple[bool, dict]:
    # Ground truth by construction: three functions and two classes, counted here
    # from the source text with ast -- never from the adapter's own arithmetic.
    tree = ast.parse(DEFS_MODULE)
    funcs = sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                for n in ast.walk(tree))
    classes = sum(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
    ok = (report.get("function_count") == funcs == 3
          and report.get("class_count") == classes == 2
          and report.get("definition_count") == funcs + classes == 5)
    return ok, {"constructed_functions": funcs, "constructed_classes": classes,
                "reported": {k: report.get(k) for k in
                             ("function_count", "class_count", "definition_count")}}


def build_complexity(world: pathlib.Path) -> dict:
    _write(world / "complex/mod.py", COMPLEX_MODULE)
    return {"source_root": _rel(world / "complex"), "output_path": _rel(world / "answer.json")}


def check_complexity(world: pathlib.Path, report: dict) -> tuple[bool, dict]:
    tree = ast.parse(COMPLEX_MODULE)
    truth = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            # The row's published metric is LOOP-chain depth ("the deepest chain of
            # loops, not the count"), so the recomputation uses that definition and
            # only that one: an `if` is a decision, not an iteration.
            def depth(n, level=0):
                best = level
                for child in ast.iter_child_nodes(n):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef,
                                          ast.ClassDef, ast.Lambda)):
                        continue
                    step = level + 1 if isinstance(
                        child, (ast.For, ast.AsyncFor, ast.While)) else level
                    best = max(best, depth(child, step))
                return best
            # ... and McCabe's number, recomputed here from the decision nodes so the
            # check does not share a line of code with the adapter it is checking.
            decisions = 1
            for child in ast.walk(node):
                if child is node:
                    continue
                if isinstance(child, (ast.If, ast.For, ast.AsyncFor, ast.While,
                                      ast.ExceptHandler, ast.With, ast.AsyncWith,
                                      ast.Assert, ast.IfExp, ast.comprehension)):
                    decisions += 1
                elif isinstance(child, ast.BoolOp):
                    decisions += max(0, len(child.values) - 1)
            truth[node.name] = {"nesting": depth(node), "lineno": node.lineno,
                                "cyclomatic": decisions}
    measured = {row.get("name"): row for row in (report.get("functions") or [])}
    ok = (set(measured) == set(truth)
          and all(measured[name].get("nesting") == truth[name]["nesting"]
                  and measured[name].get("lineno") == truth[name]["lineno"]
                  and measured[name].get("cyclomatic_complexity") == truth[name]["cyclomatic"]
                  for name in truth)
          and report.get("cyclomatic_complexity") == max(
              row["cyclomatic"] for row in truth.values())
          and truth["nested"]["nesting"] > truth["flat"]["nesting"] == 0
          and report.get("answer") == "nested"
          and report.get("functions_measured") == len(truth) == 2)
    return ok, {"constructed": truth, "reported_worst": report.get("answer"),
                "reported_functions": len(measured)}


def build_dead_code(world: pathlib.Path) -> dict:
    # `dead_code` reads the subject PLUS its siblings (a caller can be beside it),
    # so the world's project directory is the isolated thing that gets planted.
    _write(world / "project/tools.py", DEAD_TOOLS)
    _write(world / "project/app.py", DEAD_APP)
    return {"source_root": _rel(world / "project"), "output_path": _rel(world / "answer.json")}


def _names_dead(report: dict) -> set[str]:
    out = set()
    for row in (report.get("dead_symbols") or []):
        text = row.get("symbol") if isinstance(row, dict) else str(row)
        text = str(text or "")
        out.add(text.rsplit(".", 1)[-1].rsplit("/", 1)[-1].replace(".py:", "").strip())
    return out


def check_dead_code(world: pathlib.Path, report: dict) -> tuple[bool, dict]:
    # Construction: `used_helper` has exactly one caller, `unused_helper` has none.
    tree = ast.parse(DEAD_APP)
    called = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    truth = {"unused_helper": "unused_helper" not in called,
             "used_helper": "used_helper" in called}
    dead = _names_dead(report)
    ok = (truth["unused_helper"] and truth["used_helper"]
          and any("unused_helper" in name for name in dead)
          and not any(re.fullmatch(r".*\bused_helper", name) for name in dead)
          and report.get("considered_count", 0) >= 2)
    return ok, {"constructed_dead": "unused_helper", "constructed_live": "used_helper",
                "reported_dead": sorted(dead), "considered_count": report.get("considered_count")}


def build_secret_scan(world: pathlib.Path) -> dict:
    _write(world / "secrets/config.py", SECRET_CONFIG)
    _write(world / "secrets/clean.py", '"""Nothing here."""\n\nTOKEN = "not-a-credential"\n')
    return {"source_root": _rel(world / "secrets"), "output_path": _rel(world / "answer.json")}


def check_secret_scan(world: pathlib.Path, report: dict) -> tuple[bool, dict]:
    # Construction: exactly ONE credential-shaped literal, on line 4 of config.py.
    planted_line = SECRET_CONFIG.splitlines().index(
        [ln for ln in SECRET_CONFIG.splitlines() if PLANTED_KEY in ln][0]) + 1
    findings = report.get("findings") or []
    echoed = PLANTED_KEY in json.dumps(report)
    ok = (len(findings) == 1 and report.get("finding_count") == 1
          and int(findings[0].get("line", 0)) == planted_line == 4
          and str(findings[0].get("path", "")).endswith("secrets/config.py")
          and findings[0].get("signature") == "aws_access_key_id"
          and not echoed)
    return ok, {"constructed_line": planted_line, "reported": findings[:1],
                "secret_echoed_in_report": echoed}


def build_taint_flow(world: pathlib.Path) -> dict:
    _write(world / "taint/app.py", TAINT_APP)
    _write(world / "clean/app.py", TAINT_CLEAN)
    # The clean world is the row's negative control, so its answer is produced here
    # and stored: --check then reads both artifacts and never starts the adapter.
    _run_adapter("python.source.taint_flow.v1",
                 {"source_root": _rel(world / "clean"),
                  "output_path": _rel(world / "clean_answer.json")}, world)
    return {"source_root": _rel(world / "taint"), "output_path": _rel(world / "answer.json")}


def check_taint_flow(world: pathlib.Path, report: dict) -> tuple[bool, dict]:
    # Ground truth: `int(sys.argv[1])` is the input boundary and the value reaches
    # `os.system`.  The clean world must come back "no" -- a scanner that says yes
    # to everything would pass the first half and fail this one.
    clean = json.loads((world / "clean_answer.json").read_text(encoding="utf-8"))
    # ... and the control is taint-free BY CONSTRUCTION, which is what makes its
    # "no" an answer rather than a coincidence.
    control_is_clean = not re.search(r"argv|json\.loads|\binput\(", TAINT_CLEAN)
    trace = report.get("trace") or []
    ok = (report.get("answer") == "yes" and report.get("reaches") is True
          and bool(trace) and "os.system" in str(trace[0].get("sink"))
          and trace[0].get("function") == "handle"
          and clean.get("answer") == "no" and clean.get("reaches") is False
          and control_is_clean)
    return ok, {"constructed_source": "json.loads(raw) on a parameter",
                "control_world_is_taint_free_by_construction": control_is_clean,
                "constructed_sink": "os.system",
                "reported_answer": report.get("answer"),
                "clean_world_answer": clean.get("answer")}


def build_test_adequacy(world: pathlib.Path) -> dict:
    _write(world / "project/app/__init__.py", "")
    _write(world / "project/tests/__init__.py", "")
    _write(world / "project/app/mod.py", ADEQUACY_MODULE)
    _write(world / "project/tests/test_mod.py", ADEQUACY_TESTS)
    return {"source_root": _rel(world / "project/app"), "output_path": _rel(world / "answer.json")}


def check_test_adequacy(world: pathlib.Path, report: dict) -> tuple[bool, dict]:
    # Construction: the suite calls `covered` and never calls `never_called`, so a
    # correct adequacy answer is "no" and it must name the uncovered line.
    tree = ast.parse(ADEQUACY_MODULE)
    lines = {node.name: node.body[0].lineno for node in tree.body
             if isinstance(node, ast.FunctionDef)}
    unexecuted = report.get("unexecuted_lines") or []
    ok = (report.get("answer") == "no"
          and lines["never_called"] in [int(x) for x in unexecuted]
          and lines["covered"] not in [int(x) for x in unexecuted]
          and report.get("declared_line_count") == (
              int(report.get("executed_line_count") or 0) + len(unexecuted))
          and report.get("unexecuted_count") == len(unexecuted))
    return ok, {"constructed_uncovered_line": lines["never_called"],
                "reported_answer": report.get("answer"),
                "reported_unexecuted": unexecuted}


def build_inline_helper(world: pathlib.Path) -> dict:
    _write(world / "project/app/__init__.py", "")
    _write(world / "project/app/service.py", INLINE_MODULE)
    _write(world / "project/tests/__init__.py", "")
    _write(world / "project/tests/test_service.py", INLINE_TESTS)
    return {"source_root": _rel(world / "project/app"),
            "output_path": _rel(world / "answer.json"), "helper_name": "_price_with_tax",
            "timeout_s": 120}


def check_inline_helper(world: pathlib.Path, report: dict) -> tuple[bool, dict]:
    # The two proofs, taken HERE: the name survives nowhere in the tree, the file
    # still parses, and THIS process runs the suite green.
    project = world / "project"
    text = (project / "app/service.py").read_text(encoding="utf-8")
    survived = [str(p.relative_to(world)) for p in project.rglob("*.py")
                if "_price_with_tax" in p.read_text(encoding="utf-8")]
    try:
        ast.parse(text)
        parses = True
    except SyntaxError:
        parses = False
    green, tail = _python_ok(project, ["tests"])
    ok = (not survived and parses and green
          and report.get("helper") == "_price_with_tax"
          and report.get("suite_passed") is True
          and "price_cents" in text)
    return ok, {"helper_name_survived": survived, "file_parses": parses,
                "suite_green_when_the_verifier_ran_it": green, "suite_tail": tail[-160:]}


def build_merge_resolve(world: pathlib.Path) -> dict:
    _write(world / "project/app/__init__.py", "")
    _write(world / "project/app/models.py", CONFLICTED_MODELS)
    _write(world / "project/tests/__init__.py", "")
    _write(world / "project/tests/test_models.py", CONFLICT_TESTS)
    return {"source_root": _rel(world / "project/app"),
            "output_path": _rel(world / "answer.json"), "timeout_s": 120}


def check_merge_resolve(world: pathlib.Path, report: dict) -> tuple[bool, dict]:
    project = world / "project"
    text = (project / "app/models.py").read_text(encoding="utf-8")
    markers = [m for m in ("<<<<<<<", "=======", ">>>>>>>") if m in text]
    try:
        ast.parse(text)
        parses = True
    except SyntaxError:
        parses = False
    # Both sides of the conflict survive, which is the resolution law the row
    # claims, and the suite is run by THIS process rather than by the adapter.
    both_sides = "def line_total" in text and "class Item" in text
    green, tail = _python_ok(project, ["tests"])
    ok = (not markers and parses and both_sides and green
          and report.get("suite_passed") is True
          and report.get("resolved_file_count") == 1)
    return ok, {"markers_left": markers, "file_parses": parses,
                "both_conflict_sides_kept": both_sides,
                "suite_green_when_the_verifier_ran_it": green, "suite_tail": tail[-160:]}


ROWS = {
    "python.source.definition_count.v1": {
        "mission": "ASTRA-VERIFY-DEFINITION-COUNT-001", "slug": "definition_count",
        "build": build_definition_count, "check": check_definition_count,
        "claim": "counts every function and class in a tree, by ast, exactly",
    },
    "python.source.complexity.v1": {
        "mission": "ASTRA-VERIFY-COMPLEXITY-001", "slug": "complexity",
        "build": build_complexity, "check": check_complexity,
        "claim": ("ranks functions by loop-nesting depth and by McCabe's cyclomatic number, "
                  "both recomputed from the tree"),
    },
    "python.source.dead_code.v1": {
        "mission": "ASTRA-VERIFY-DEAD-CODE-001", "slug": "dead_code",
        "build": build_dead_code, "check": check_dead_code,
        "claim": "separates a helper with no caller from one with a caller",
    },
    "python.source.secret_scan.v1": {
        "mission": "ASTRA-VERIFY-SECRET-SCAN-001", "slug": "secret_scan",
        "build": build_secret_scan, "check": check_secret_scan,
        "claim": "finds a published credential shape at its real line and never echoes it",
    },
    "python.source.taint_flow.v1": {
        "mission": "ASTRA-VERIFY-TAINT-FLOW-001", "slug": "taint_flow",
        "build": build_taint_flow, "check": check_taint_flow,
        "claim": "traces an input boundary to a shell sink, and says no when it does not",
    },
    "python.source.test_adequacy.v1": {
        "mission": "ASTRA-VERIFY-TEST-ADEQUACY-001", "slug": "test_adequacy",
        "build": build_test_adequacy, "check": check_test_adequacy,
        "claim": "names the executable line the suite never runs",
    },
    "python.refactor.inline_helper.v1": {
        "mission": "ASTRA-VERIFY-INLINE-HELPER-001", "slug": "inline_helper",
        "build": build_inline_helper, "check": check_inline_helper,
        "claim": "a single-use helper becomes its body; the name survives nowhere; the suite stays green",
    },
    "python.vcs.merge_conflict.resolve.v1": {
        "mission": "ASTRA-VERIFY-MERGE-RESOLVE-001", "slug": "merge_resolve",
        "build": build_merge_resolve, "check": check_merge_resolve,
        "claim": "a conflicted file keeps both sides, loses every marker, and the suite goes green",
    },
}


# ------------------------------------------------------------------ verify one
def verify(cid: str) -> dict:
    row = ROWS[cid]
    world = _world(row["mission"])
    args = row["build"](world)
    started = time.time()
    output = _run_adapter(cid, args, world)
    elapsed = round(time.time() - started, 3)
    report = json.loads((ROOT / str(output.get("output_path") or "")).read_text(encoding="utf-8"))
    ok, evidence = row["check"](world, report)
    adapter = _adapter_path(cid)
    receipt = {
        "schema": SCHEMA,
        "capability_id": cid,
        "claim": row["claim"],
        "mission_id": row["mission"],
        "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "adapter_path": _rel(adapter),
        "adapter_sha256": _sha256(adapter),
        "world": _rel(world),
        "inputs": args,
        "adapter_output_path": _rel(ROOT / str(output.get("output_path") or "")),
        "adapter_output_sha256": output.get("output_sha256"),
        "elapsed_s": elapsed,
        # `independent_verified` is true only when the check written in this file
        # reproduced the claim from the tree; the adapter's own `output_verified`
        # is recorded but never consulted.
        "independent_verified": bool(ok),
        "independence": ("the check recomputes the answer from the constructed world with the "
                         "standard library and never imports the adapter"),
        "checks": [{"name": row["claim"], "ok": bool(ok), "evidence": evidence}],
        "adapter_self_report": {"output_verified": output.get("output_verified"),
                                "verified": output.get("verified")},
        "replay": "python3 canonical/runtime/verify_bound_capability_provenance_v1.py --check",
    }
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    receipt_path = EVIDENCE / ("%s__RECEIPT.json" % row["mission"])
    receipt_path.write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n",
                            encoding="utf-8")
    state_path = STATE / ("%s.json" % row["mission"])
    _write(state_path, json.dumps({
        "schema": STATE_SCHEMA,
        "capability_id": cid,
        "mission_id": row["mission"],
        "receipt_path": _rel(receipt_path),
        "receipt_sha256": _sha256(receipt_path),
        "independent_verified": bool(ok),
        "verified_at": receipt["verified_at"],
    }, indent=1, sort_keys=True) + "\n")
    return receipt


def check(cid: str) -> dict:
    """Re-run one row's check from its receipt, with no adapter anywhere."""
    row = ROWS[cid]
    receipt_path = EVIDENCE / ("%s__RECEIPT.json" % row["mission"])
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    report = json.loads((ROOT / receipt["adapter_output_path"]).read_text(encoding="utf-8"))
    world = ROOT / receipt["world"]
    ok, evidence = row["check"](world, report)
    return {"capability_id": cid, "replayed_ok": bool(ok),
            "receipt_said": receipt["independent_verified"], "evidence": evidence}


# -------------------------------------------------------------- registry stamp
def _verification_block(cid: str, receipt: dict) -> str:
    block = {
        "independently_verified": bool(receipt["independent_verified"]),
        "mission_id": receipt["mission_id"],
        "observed_effect": {
            "claim": receipt["claim"],
            "checks": receipt["checks"][0]["evidence"],
            "verified": bool(receipt["independent_verified"]),
            "adapter_sha256": receipt["adapter_sha256"],
            "elapsed_s": receipt["elapsed_s"],
        },
        "provenance": ("canonical/runtime/verify_bound_capability_provenance_v1.py "
                       "--check re-derives the claim from a constructed world with no "
                       "adapter in the loop"),
        "receipt_path": "canonical/astra_runtime/evidence/%s__RECEIPT.json" % receipt["mission_id"],
        "state_path": "canonical/astra_runtime/state/%s.json" % receipt["mission_id"],
    }
    # Dump the wrapper and keep its INSIDE: the entry already supplies the braces.
    body = "\n".join(
        json.dumps({"verification": block}, indent=1, sort_keys=True).splitlines()[1:-1])
    # The entry's own keys sit at 3 spaces and its values at 4; dumping from column 0
    # and shifting the whole block by 3 reproduces the file's hand-shaped indentation.
    return "\n".join("   " + line for line in body.splitlines())


def stamp(receipts: dict[str, dict]) -> list[str]:
    raw = REGISTRY.read_text(encoding="utf-8")
    lines = raw.splitlines()
    stamped = []
    for cid, receipt in receipts.items():
        if not receipt["independent_verified"]:
            continue
        head = '  "%s": {' % cid
        if head not in lines:
            raise SystemExit("ENTRY_NOT_FOUND:" + cid)
        start = lines.index(head)
        end = start
        while lines[end] not in ("  }", "  },"):
            end += 1
        entry_text = "\n".join(lines[start:end])
        if '"verification"' in entry_text:
            continue
        block = _verification_block(cid, receipt)
        # the entry's last key has no trailing comma; the block becomes the last key,
        # so it inherits that shape and the old last line gains one.
        last = end - 1
        if not lines[last].rstrip().endswith(","):
            lines[last] = lines[last].rstrip() + ","
        lines[end:end] = block.splitlines()
        stamped.append(cid)
    text = "\n".join(lines) + ("\n" if raw.endswith("\n") else "")
    before = json.loads(raw)
    after = json.loads(text)
    # Only additions: every capability that existed still has exactly the keys it
    # had, plus `verification` on the stamped rows.
    for cid, entry in before["capabilities"].items():
        new = after["capabilities"][cid]
        added = set(new) - set(entry)
        if added - {"verification"}:
            raise SystemExit("STAMP_ADDED_UNEXPECTED_KEY:" + cid + ":" + ",".join(sorted(added)))
        if set(entry) - set(new):
            raise SystemExit("STAMP_DROPPED_KEY:" + cid)
    REGISTRY.write_text(text, encoding="utf-8")
    return stamped


def unproven() -> list[str]:
    caps = json.loads(REGISTRY.read_text(encoding="utf-8"))["capabilities"]
    return sorted(cid for cid, entry in caps.items()
                  if not (isinstance(entry.get("verification"), dict)
                          and entry.get("verification")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capability", action="append", default=[],
                        help="row to verify (default: every row with no verification block)")
    parser.add_argument("--check", action="store_true",
                        help="re-derive recorded receipts without running any adapter")
    parser.add_argument("--stamp", action="store_true",
                        help="write the verification blocks into the registry")
    parser.add_argument("--json", action="store_true")
    parsed = parser.parse_args(argv)

    targets = parsed.capability or (ROWS if parsed.check else unproven())
    missing = [cid for cid in targets if cid not in ROWS]
    if missing:
        raise SystemExit("NO_CONSTRUCTED_WORLD_FOR:" + ",".join(sorted(missing)))

    if parsed.check:
        results = [check(cid) for cid in targets]
        ok = all(row["replayed_ok"] for row in results)
        if parsed.json:
            print(json.dumps(results, indent=1, sort_keys=True))
        else:
            for row in results:
                print("%-45s %s" % (row["capability_id"],
                                    "REPLAYED" if row["replayed_ok"] else "DISAGREES"))
        return 0 if ok else 1

    receipts = {cid: verify(cid) for cid in targets}
    if parsed.stamp:
        stamped = stamp(receipts)
    else:
        stamped = []
    ok = all(row["independent_verified"] for row in receipts.values())
    if parsed.json:
        print(json.dumps(receipts, indent=1, sort_keys=True))
    else:
        for cid, row in receipts.items():
            print("%-45s %-10s %s" % (cid, "VERIFIED" if row["independent_verified"]
                                      else "DISAGREES", row["claim"]))
        if stamped:
            print("stamped into the registry: " + ", ".join(stamped))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
