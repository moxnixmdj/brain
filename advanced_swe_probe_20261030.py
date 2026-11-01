#!/usr/bin/env python3
"""Which TIER of software engineering is reachable, measured by independent oracles.

The 97-sentence battery answered "how often does a sentence pass".  That is a
dispatch measurement dressed up as a capability measurement, and it says nothing
about the ceiling: a system can pass 90% of trivial sentences and still be unable
to find a race condition, bisect a regression, or prove a refactor is behaviour-
preserving.

This probe asks the other question.  Ten tasks, each one a thing a strong
software engineer does and a weak one cannot, each graded by an oracle that does
not consult the runtime's own report:

  T1 LOCAL TRANSFORMATION     one file, one symbol
  T2 CROSS-FILE SEMANTICS     a change that must be consistent across callers
  T3 BEHAVIOURAL VERIFICATION  the code must still DO the same thing
  T4 DIAGNOSIS                find the cause, not the symptom
  T5 CONCURRENCY              a defect that only appears sometimes
  T6 ATTRIBUTION              which change cost the time
  T7 ASSURANCE                is the test suite actually strong
  TX TAINT                    does untrusted input reach a sink
  TF FEATURE                  new behaviour, wired and tested
  TS SCALE                    the same question on a 5000-file tree

Every oracle is machine-checkable: a grep, a real test run, a behavioural value
table, or a file the goal was told to write.  Where the answer has to be a
judgement ("which function got slower"), the goal is required to write it to a
path this probe named, and the probe reads that file -- so the oracle never has
to interpret prose.

Authority: NONE.  Credit: 0.  Model dependency: 0.  Spend: $0.

Usage:
    python3 advanced_swe_probe_20261030.py [--jobs N] [--only TAG,TAG] [--json OUT]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
WORK = "canonical/astra_runtime/tmp/advanced_probe_20261030"
BUDGET_S = 150


def rel(p: pathlib.Path) -> str:
    return str(p.relative_to(ROOT))


def sh(argv, cwd, timeout=60):
    # AN ORACLE MUST NOT BE FOOLED BY A FILE IT DID NOT ASK FOR.  Several oracles here
    # measure a claim by reverting a source file and re-running the suite; a bytecode cache
    # left by any earlier run of the same tree can answer for the reverted source, because a
    # same-size edit inside one timestamp tick still matches the pyc header (measured
    # 2026-11-01: `fix_then_regression_test` read 1/4 instead of 4/4 for exactly this
    # reason).  The tree the oracle reasons about is the source tree, never a compiled copy.
    env = dict(os.environ, PYTHONPATH=str(cwd), PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True,
                          timeout=timeout, env=env)


def git(cwd, *args):
    return sh(["git", *args], cwd)


# --------------------------------------------------------------------- fixtures

# One name, one symbol: the method is `subtotal`, never a second `line_total`,
# so "rename the function line_total" has exactly one correct answer and the
# oracle below can be absolute without being unfair.
MODELS = '''"""Models."""


class Item:
    def __init__(self, name, price_cents, qty=1):
        self.name = name
        self.price_cents = price_cents
        self.qty = qty

    def subtotal(self):
        return self.price_cents * self.qty


def line_total(item):
    return item.price_cents * item.qty
'''

SERVICE = '''"""Logic."""
from app.models import Item, line_total


def cart_total(items):
    return sum(line_total(i) for i in items)


def apply_discount(subtotal_cents, percent):
    if percent < 0:
        return subtotal_cents
    cut = subtotal_cents * percent // 100
    if cut > subtotal_cents:
        cut = subtotal_cents
    if percent > 100:
        percent = 100
    taxed = subtotal_cents - cut
    return taxed if taxed > 0 else 0
'''

TEST_SERVICE = '''import unittest

from app.models import Item
from app.service import cart_total


class CartTests(unittest.TestCase):
    def test_cart_total(self):
        items = [Item("a", 100, 2), Item("b", 250, 1)]
        self.assertEqual(cart_total(items), 450)


if __name__ == "__main__":
    unittest.main()
'''


def _fresh(tag):
    base = ROOT / WORK / tag
    if base.exists():
        shutil.rmtree(base)
    (base / "app").mkdir(parents=True)
    (base / "tests").mkdir(parents=True)
    (base / "app/__init__.py").write_text("", encoding="utf-8")
    (base / "app/models.py").write_text(MODELS, encoding="utf-8")
    (base / "app/service.py").write_text(SERVICE, encoding="utf-8")
    (base / "tests/__init__.py").write_text("", encoding="utf-8")
    (base / "tests/test_service.py").write_text(TEST_SERVICE, encoding="utf-8")
    _commit(base, "initial cart service")
    return base


def _commit(base, msg):
    git(base, "init", "-q", "-b", "main")
    git(base, "add", "-A")
    git(base, "-c", "user.email=a@b.c", "-c", "user.name=probe", "commit", "-qm", msg)


def _commit_more(base, msg):
    git(base, "add", "-A")
    git(base, "-c", "user.email=a@b.c", "-c", "user.name=probe", "commit", "-qm", msg)


def _suite_ok(base, pattern="tests"):
    cp = sh([sys.executable, "-m", "unittest", "discover", "-s", pattern, "-t", "."], base, 120)
    return cp.returncode == 0, (cp.stdout + cp.stderr)[-400:]


# ---------------------------------------------------------------------- oracles


def oracle_rename(base, result):
    """Nothing anywhere may still say line_total, and the package must import."""
    hits = []
    for p in base.rglob("*.py"):
        if ".git" in p.parts:
            continue
        if "line_total" in p.read_text(encoding="utf-8"):
            hits.append(str(p.relative_to(base)))
    renamed = any("item_total" in p.read_text(encoding="utf-8")
                  for p in base.rglob("*.py") if ".git" not in p.parts)
    imp = sh([sys.executable, "-c", "import app.service, app.models"], base, 60)
    ok, tail = _suite_ok(base)
    return (not hits) and renamed and imp.returncode == 0 and ok, {
        "stale_refs": hits, "renamed": renamed, "imports": imp.returncode == 0, "suite": ok,
        "tail": tail if not ok else "", "status": str(result.get("status"))[:80]}


def oracle_extract(base, result):
    """The module must import, expose a new function, and answer identically."""
    # Values computed by hand from the fixture's own arithmetic, not read back
    # from whatever the edit produced: (500, 250) clamps the cut to the subtotal
    # and returns 0, which is the branch an extractor most often breaks.
    table = [(1000, 10), (1000, 0), (500, 250), (500, -5), (0, 50), (999, 100)]
    code = (
        "import json,sys\n"
        "from app.service import apply_discount\n"
        f"print(json.dumps([apply_discount(a,b) for a,b in {table}]))\n"
    )
    cp = sh([sys.executable, "-c", code], base, 60)
    if cp.returncode != 0:
        return False, {"behaviour": "IMPORT_OR_CALL_FAILED", "tail": (cp.stderr or "")[-300:],
                       "status": str(result.get("status"))[:80]}
    got = json.loads(cp.stdout.strip().splitlines()[-1])
    want = [900, 1000, 0, 500, 0, 0]
    src = (base / "app/service.py").read_text(encoding="utf-8")
    n_defs = src.count("\ndef ")
    return got == want and n_defs >= 3, {
        "behaviour_equal": got == want, "got": got, "want": want,
        "defs_in_service": n_defs, "status": str(result.get("status"))[:80]}


def oracle_fix_bug(base, result):
    """A green suite is not the oracle on its own: the code must also be right.

    `_suite_ok` runs the fixture's own test file, and a repair is free to rewrite
    that file, so a passing run proves nothing unless the behaviour is checked
    independently.  The value table below is computed from the fixture's own
    specification, not from whatever the runtime left behind.
    """
    ok, tail = _suite_ok(base)
    code = (
        "import json\n"
        "from app.models import Item\n"
        "from app.service import cart_total, apply_discount\n"
        "items=[Item('a',100,2),Item('b',250,1)]\n"
        "print(json.dumps([cart_total(items), apply_discount(1000,10), apply_discount(1000,0)]))\n"
    )
    cp = sh([sys.executable, "-c", code], base, 60)
    want = [450, 900, 1000]
    got = None
    if cp.returncode == 0 and cp.stdout.strip():
        try:
            got = json.loads(cp.stdout.strip().splitlines()[-1])
        except Exception:  # noqa: BLE001
            got = None
    return ok and got == want, {"suite": ok, "behaviour_equal": got == want, "got": got,
                                "want": want, "tail": tail if not ok else "",
                                "status": str(result.get("status"))[:80]}


TRUE_BREAKER = None


def fixture_bisect(tag):
    base = _fresh(tag)
    (base / "app/calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (base / "tests/test_calc.py").write_text(
        "import unittest\n\nfrom app.calc import add\n\n\n"
        "class CalcTests(unittest.TestCase):\n"
        "    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n\n\n"
        'if __name__ == "__main__":\n    unittest.main()\n', encoding="utf-8")
    _commit_more(base, "add calc")
    (base / "CHANGELOG.md").write_text("v2\n", encoding="utf-8")
    _commit_more(base, "docs: changelog")
    (base / "app/calc.py").write_text(
        "def add(a, b):\n    return a - b\n\ndef mul(a, b):\n    return a * b\n", encoding="utf-8")
    _commit_more(base, "refactor: simplify add")
    (base / "app/extra.py").write_text("VALUE = 1\n", encoding="utf-8")
    _commit_more(base, "feat: extra")
    (base / "tests/test_more.py").write_text(
        "import unittest\n\nfrom app.calc import mul\n\n\n"
        "class MulTests(unittest.TestCase):\n"
        "    def test_mul(self):\n        self.assertEqual(mul(2, 3), 6)\n\n\n"
        'if __name__ == "__main__":\n    unittest.main()\n', encoding="utf-8")
    _commit_more(base, "test: mul")
    sha = git(base, "log", "--format=%H", "--reverse").stdout.split()[-3]
    return base, sha


def oracle_answer_contains(base, result, needle, what):
    f = base / "answer.json"
    if not f.is_file():
        return False, {"answer_file": False, "status": str(result.get("status"))[:80]}
    raw = f.read_text(encoding="utf-8", errors="replace")
    hit = needle.lower() in raw.lower()
    return hit, {"answer_file": True, "contains_" + what: hit,
                 "bytes": len(raw), "status": str(result.get("status"))[:80]}


RACE = '''import threading
import time


class Counter:
    def __init__(self):
        self.n = 0

    def add(self):
        current = self.n
        # A real interleaving window.  A busy-wait does NOT reliably yield the
        # GIL between the read and the write, and a "flaky" fixture that never
        # actually fails makes every oracle scored against it meaningless
        # (measured: 10/10 green with no lock present).
        time.sleep(0.0002)
        self.n = current + 1


def run(threads=8, per=50):
    c = Counter()
    ts = [threading.Thread(target=lambda: [c.add() for _ in range(per)]) for _ in range(threads)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return c.n
'''

RACE_TEST = '''import unittest

from app.counter import run


class RaceTests(unittest.TestCase):
    def test_concurrent_counter_loses_no_increment(self):
        self.assertEqual(run(), 400)


if __name__ == "__main__":
    unittest.main()
'''


def fixture_race(tag):
    base = _fresh(tag)
    (base / "app/counter.py").write_text(RACE, encoding="utf-8")
    (base / "tests/test_counter.py").write_text(RACE_TEST, encoding="utf-8")
    _commit_more(base, "feat: counter with a test")
    return base


def oracle_race(base, result):
    """Ten real runs: a fix that holds once and fails once more is not a fix."""
    runs, ok = 0, 0
    for _ in range(10):
        cp = sh([sys.executable, "tests/test_counter.py"], base, 60)
        runs += 1
        ok += 1 if cp.returncode == 0 else 0
    src = (base / "app/counter.py").read_text(encoding="utf-8")
    # A substring test for "lock" is a tautology: the fixture's own comment
    # contains the word, so this oracle scored the *unmodified* file as fixed
    # (measured: lock_present True over a file whose git diff was empty).  The
    # oracle has to look for the construct, not the word.
    import re as _re
    guarded = bool(_re.search(r"\b(?:threading\.)?(?:R?Lock|Semaphore|Condition)\s*\(", src))
    return ok == runs and guarded, {"runs": runs, "passing": ok, "lock_present": guarded,
                                    "status": str(result.get("status"))[:80]}


SLOW = '''"""Reporting."""


def dedupe(rows):
    out = []
    for r in rows:
        if r not in out:
            out.append(r)
    return out


def fast_path(rows):
    return len(set(rows))
'''


def fixture_perf(tag):
    base = _fresh(tag)
    (base / "app/report.py").write_text(
        '"""Reporting."""\n\n\ndef dedupe(rows):\n    return list(dict.fromkeys(rows))\n\n\n'
        "def fast_path(rows):\n    return len(set(rows))\n", encoding="utf-8")
    _commit_more(base, "perf: dedupe via dict")
    (base / "app/report.py").write_text(SLOW, encoding="utf-8")
    _commit_more(base, "refactor: dedupe for readability")
    return base


MUTANT_APP = '''"""Prices."""


def clamp(v, low, high):
    if v < low:
        return low
    if v > high:
        return high
    return v


def is_adult(age):
    return age >= 18
'''

MUTANT_TEST = '''import unittest

from app.prices import clamp


class ClampTests(unittest.TestCase):
    def test_below(self):
        self.assertEqual(clamp(-5, 0, 10), 0)

    def test_above(self):
        self.assertEqual(clamp(50, 0, 10), 10)

    def test_inside(self):
        self.assertEqual(clamp(5, 0, 10), 5)


if __name__ == "__main__":
    unittest.main()
'''


def fixture_mutation(tag):
    base = _fresh(tag)
    (base / "app/prices.py").write_text(MUTANT_APP, encoding="utf-8")
    (base / "tests/test_prices.py").write_text(MUTANT_TEST, encoding="utf-8")
    _commit_more(base, "feat: prices")
    return base


HANDLER = '''"""HTTP entry."""
import json


def parse_request(raw):
    return json.loads(raw or "{}")


def handle(raw):
    payload = parse_request(raw)
    code = payload.get("code", "")
    result = exec(code)  # noqa: S102 - the sink under test
    return result
'''


def fixture_taint(tag):
    base = _fresh(tag)
    (base / "app/handler.py").write_text(HANDLER, encoding="utf-8")
    _commit_more(base, "feat: handler")
    return base


def fixture_feature(tag):
    base = _fresh(tag)
    return base


BUGGY_SERVICE = SERVICE.replace(
    "    return sum(line_total(i) for i in items)",
    "    return sum(i.price_cents for i in items)")
BUGGY_TEST = TEST_SERVICE.replace("self.assertEqual(cart_total(items), 450)",
                                  "self.assertEqual(cart_total(items), 450)")


def fixture_fixbug(tag):
    """A genuine red suite: cart_total ignores quantity, the test says it must not."""
    base = _fresh(tag)
    (base / "app/service.py").write_text(BUGGY_SERVICE, encoding="utf-8")
    _commit_more(base, "refactor: inline the line total")
    return base


# ---------------------------------------------------------------------- the list
# Each row: (tier, tag, goal template, fixture maker, oracle maker, extra)

PROBES = []


def probe(tier, tag, goal, fixture, oracle, **kw):
    PROBES.append({"tier": tier, "tag": tag, "goal": goal,
                   "fixture": fixture, "oracle": oracle, **kw})


def _fx_simple(tag):
    return _fresh(tag), None


probe("T1_LOCAL", "rename_symbol",
      "Rename the function line_total to item_total in {b}/app and update every caller.",
      _fx_simple, oracle_rename)
probe("T2_CROSSFILE", "extract_function",
      "Extract the discount arithmetic from apply_discount in {b}/app/service.py into a new function.",
      _fx_simple, oracle_extract)
probe("T3_BEHAVIOUR", "fix_failing_test",
      "The tests in {b}/tests are failing. Fix the code so they pass.",
      fixture_fixbug, oracle_fix_bug)
probe("T4_DIAGNOSIS", "bisect_regression",
      "Find the commit in {b} that broke tests/test_calc.py and write its commit id to {b}/answer.json",
      fixture_bisect, "BISECT")
probe("T5_CONCURRENCY", "fix_race",
      "The test tests/test_counter.py in {b} is flaky. Fix the race condition in {b}/app/counter.py.",
      fixture_race, oracle_race)
probe("T6_ATTRIBUTION", "perf_regression",
      "Between HEAD~1 and HEAD in {b}, one function got much slower. Find it and write its name to {b}/answer.json",
      fixture_perf, "SLOWFUNC")
probe("T7_ASSURANCE", "mutation_score",
      "Measure how strong the tests in {b}/tests are against the code in {b}/app and write the mutation score (0 to 1) to {b}/answer.json",
      fixture_mutation, "MUTATION")
probe("TX_TAINT", "taint_reaches_exec",
      "Does untrusted input from parse_request in {b}/app/handler.py reach exec? Write yes or no to {b}/answer.json",
      fixture_taint, "TAINT")
probe("TF_FEATURE", "add_total_function",
      "Add a function total_cents(item) to {b}/app/models.py that returns price_cents * qty, "
      "export it from {b}/app/__init__.py, and add a test for it in {b}/tests/test_total.py",
      fixture_feature, "FEATURE")
probe("TS_SCALE", "index_whole_runtime",
      "Index the symbols in canonical/runtime and save the index to " + WORK + "/scale_index.json",
      lambda tag: (ROOT, None), "SCALE")


def run_probe(index):
    from canonical.runtime import live_brain_route_admission_v1 as door
    row = PROBES[index]
    made = row["fixture"](row["tag"])
    base, extra = made if isinstance(made, tuple) else (made, None)
    goal = row["goal"].format(b=rel(base))
    t0 = time.perf_counter()
    err = None
    try:
        result = door.solve({"task_id": "ADV_" + row["tag"], "goal": goal})
    except BaseException as exc:  # noqa: BLE001 - an adapter must not be able to end the probe
        result, err = {}, f"{type(exc).__name__}: {str(exc)[:140]}"
    ms = (time.perf_counter() - t0) * 1000
    try:
        if row["oracle"] == "BISECT":
            ok, detail = oracle_answer_contains(base, result, extra, "commit")
        elif row["oracle"] == "SLOWFUNC":
            ok, detail = oracle_answer_contains(base, result, "dedupe", "function_name")
        elif row["oracle"] == "TAINT":
            ok, detail = oracle_answer_contains(base, result, "yes", "answer")
        elif row["oracle"] == "MUTATION":
            f = base / "answer.json"
            ok, detail = False, {"answer_file": f.is_file(),
                                 "status": str(result.get("status"))[:80]}
            if f.is_file():
                raw = f.read_text(encoding="utf-8", errors="replace")
                import re
                m = re.search(r"(0?\.\d+|1\.0+|0|1)", raw)
                score = float(m.group(1)) if m else None
                ok = score is not None and 0.0 < score < 1.0
                detail.update({"score": score, "in_open_interval": ok})
        elif row["oracle"] == "FEATURE":
            mod = sh([sys.executable, "-c",
                      "from app.models import total_cents\nprint(total_cents(type('I',(),{'price_cents':3,'qty':4})()))"],
                     base, 60)
            tf = base / "tests/test_total.py"
            suite_ok = sh([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                          base, 120).returncode == 0
            ok = mod.returncode == 0 and mod.stdout.strip().endswith("12") and tf.is_file() and suite_ok
            detail = {"module_answer": mod.stdout.strip()[-6:], "has_test_file": tf.is_file(),
                      "suite": suite_ok, "status": str(result.get("status"))[:80]}
        elif row["oracle"] == "SCALE":
            f = ROOT / WORK / "scale_index.json"
            ok, detail = f.is_file(), {"file": f.is_file(),
                                       "status": str(result.get("status"))[:80]}
            if f.is_file():
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    detail["symbols"] = data.get("totals", {}).get("symbols") or data.get("symbol_count")
                    detail["files"] = data.get("totals", {}).get("files") or data.get("file_count")
                    ok = bool(detail["symbols"])
                except Exception as exc:  # noqa: BLE001
                    detail["parse_error"] = type(exc).__name__
                    ok = False
        else:
            ok, detail = _safe_oracle(row["oracle"], base, result)
    except BaseException as exc:  # noqa: BLE001
        ok, detail = False, {"oracle_raised": f"{type(exc).__name__}: {str(exc)[:140]}"}
    return {"tier": row["tier"], "tag": row["tag"], "goal": goal, "ok": bool(ok),
            "reached": str(result.get("compiled_capability_id") or result.get("capability_id")),
            "status": str(result.get("status"))[:90], "pass_flag": result.get("pass"),
            "ms": round(ms, 1), "error": err, "detail": detail}


def _safe_oracle(fn, base, result):
    return fn(base, result)


# ------------------------------------------------------------------ the parent


def parent(jobs, only):
    sel = [i for i, p in enumerate(PROBES) if not only or p["tag"] in only]
    rows = []
    with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
        futs = {ex.submit(_sub, i): i for i in sel}
        for fut in cf.as_completed(futs):
            rows.append(fut.result())
    rows.sort(key=lambda r: [p["tag"] for p in PROBES].index(r["tag"]))
    return rows


def _sub(index):
    cmd = [sys.executable, str(pathlib.Path(__file__).resolve()), "--worker", str(index)]
    t0 = time.perf_counter()
    try:
        cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=BUDGET_S)
    except subprocess.TimeoutExpired:
        row = PROBES[index]
        return {"tier": row["tier"], "tag": row["tag"], "goal": row["goal"].format(b=""),
                "ok": False, "reached": None, "status": f"TIMEOUT_>{BUDGET_S}s",
                "pass_flag": None, "ms": round((time.perf_counter() - t0) * 1000, 1),
                "error": None, "detail": {}}
    for line in reversed(cp.stdout.strip().splitlines()):
        try:
            return json.loads(line)
        except Exception:  # noqa: BLE001
            continue
    row = PROBES[index]
    return {"tier": row["tier"], "tag": row["tag"], "goal": row["goal"].format(b=""),
            "ok": False, "reached": None, "status": "PROCESS_DIED:" + (cp.stderr or "")[-160:],
            "pass_flag": None, "ms": round((time.perf_counter() - t0) * 1000, 1),
            "error": None, "detail": {}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", type=int)
    ap.add_argument("--jobs", type=int, default=5)
    ap.add_argument("--only", default="")
    ap.add_argument("--json", default="")
    ns = ap.parse_args()
    if ns.worker is not None:
        print(json.dumps(run_probe(ns.worker)))
        return 0
    only = {t for t in ns.only.split(",") if t.strip()}
    rows = parent(ns.jobs, only)
    if ns.json:
        pathlib.Path(ns.json).write_text(json.dumps({"probes": rows}, indent=1), encoding="utf-8")
    width = max(len(r["tag"]) for r in rows) + 2
    print(f"{'tier':<16}{'probe':<{width}}{'ok':<4}{'ms':>9}  reached")
    print("-" * 96)
    for r in rows:
        print(f"{r['tier']:<16}{r['tag']:<{width}}{('YES' if r['ok'] else 'no'):<4}"
              f"{r['ms']:>9.0f}  {str(r['reached'])[:34]}")
    n = sum(1 for r in rows if r["ok"])
    print("-" * 96)
    print(f"TIERS REACHED {n}/{len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
