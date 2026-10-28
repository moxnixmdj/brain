"""Repair-depth ladder: MEASURED repair rate by bug class, not green-on-toy.

The sweep proved the repair loops EXECUTE (63/63 clean). Green-on-miniature is
not senior-engineer depth: the number that defines the model is the repair rate
as the bug class gets harder. This mission grades seeded bugs into five classes
and measures every real repair loop against each class:

  L1 literal        single operator flip, test sits directly on the function
  L2 boundary       off-by-one comparison; only the boundary point distinguishes
  L3 interprocess   defect in a callee 3 frames deep; tests only call the caller
  L4 stateful       defect in accumulated state (RunningMean denominator)
  L5 coupled        two independent defects + one test spanning both (v6 generator)

Verdict per run is INDEPENDENT: after the capability returns, the ladder itself
re-runs the fixture's unittest suite and requires exit 0. A capability that
returns verified=True without making the suite green is scored NOT repaired.
That is the check that caught the cegis_hypothesis loop: its per-round engine
calls carry no source/test paths at all, so it verifies nothing about the repo.

Model dependency: 0. Spend: $0. Network: none.
"""
from __future__ import annotations

import importlib.util
import json
import random
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

WORK = ROOT / "canonical/astra_runtime/tmp/bug_ladder"
EVIDENCE = ROOT / "canonical/astra_runtime/evidence"
SCHEMA = "PROJECT_BRAIN_REPAIR_DEPTH_LADDER_V1"
SEED = 20261029
INSTANCES_PER_TIER = 2

# No custom budgets: tightened knobs would let the instrument strawman the
# capabilities (a 0% that is the harness's fault, not the loop's). Every loop
# runs on its own published defaults; only the wall clock is bounded.
LOOP_BUDGET = {"timeout_s": 20}

from execution_guard.typed_capability_sweep_v1 import _swe_unittest_fixture  # noqa: E402
from execution_guard import live_solver_families_v6_coupled as v6  # noqa: E402

CAPS = {
    # The composed repair agent: search + verify + WRITE + replay. The search
    # loops below publish patch reports and restore the source by contract
    # (hard_nonclaims: NO_SOURCE_WRITE_OR_PROMOTION_AUTHORITY), so the honest
    # repair number belongs to apply.verified; search loops are scored on
    # whether their report contains a patch at all.
    "python.software.repair.loop.test_guided.ast.v1":
        "python_software_repair_loop_v1",
    "python.software.repair.loop.strict_progress.ast.v1":
        "python_iterative_software_repair_loop_v1",
    "python.software.repair.loop.coupled.ast.v1":
        "python_coupled_software_repair_loop_v1",
    "software.repair.loop.cegis_hypothesis.v1":
        "software_repair_loop_cegis_hypothesis_v1",
    # The composed agent runs LAST: the search loops publish patch reports and
    # restore the source by contract, but apply.verified WRITES. Running the
    # writer first left the searchers a green baseline and an honest
    # BASELINE_ALREADY_PASSES refusal -- an instrument ordering artifact, not
    # a capability result. Writer last = every row sees the same red fixture.
    "python.software.repair.apply.verified.v1":
        "python_repair_apply_verified_v1",
}


def _load(cid: str, module: str):
    path = ROOT / "canonical/runtime/bound_capabilities" / f"{module}.py"
    spec = importlib.util.spec_from_file_location("ladder_" + module, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return cid, mod.run


def _unittest_test(src: Path, mod: str, body: str, head: str = "") -> Path:
    t = src / f"test_{mod}.py"
    t.write_text(
        "import unittest\n"
        + head
        + f"from {mod} import *\n\n\n"
        + "class TestLadder(unittest.TestCase):\n"
        + body
        + '\n\nif __name__ == "__main__":\n    unittest.main()\n',
        encoding="utf-8")
    return t


# ---------------------------------------------------------------- tier fixtures
def tier_L1_literal(base: Path, rng: random.Random) -> dict:
    """Harvested straight from the sweep instrument (red polarity)."""
    fx = _swe_unittest_fixture(base)
    return {"src": fx["src"], "tests": [fx["test"]],
            "module": fx["test"].stem, "sources": [fx["module"],
                                                   fx["src"] / "user_mod.py"]}


def tier_L2_boundary(base: Path, rng: random.Random) -> dict:
    """Threshold off-by-one: ONLY the boundary point distinguishes.

    clamp() cannot carry this class: at v == lo both '<' and '<=' return lo,
    so the mutation is value-identical on the boundary. A threshold that maps
    the boundary point to a DIFFERENT value is the real thing: grade(60) is
    'pass' under >= and 'fail' under >.
    """
    k = rng.randint(2, 9)
    src = base / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "threshold_mod.py").write_text(
        "PASS_MARK = 60\n"
        "\n\n"
        "def grade(score):\n"
        "    return 'pass' if score >= PASS_MARK else 'fail'\n"   # BUG: '>' below
        "\n\n"
        f"def batch_pass(scores):\n"
        "    return sum(1 for s in scores if grade(s) == 'pass') * " + str(k) + "\n",
        encoding="utf-8")
    p = src / "threshold_mod.py"
    p.write_text(p.read_text(encoding="utf-8").replace("score >= PASS_MARK",
                                                       "score > PASS_MARK"),
                 encoding="utf-8")
    t = _unittest_test(
        src, "threshold_mod",
        "    def test_at_mark(self):\n"
        "        self.assertEqual(grade(60), 'pass')\n"
        "    def test_below(self):\n"
        "        self.assertEqual(grade(59), 'fail')\n"
        "    def test_above(self):\n"
        "        self.assertEqual(grade(61), 'pass')\n"
        "    def test_batch(self):\n"
        f"        self.assertEqual(batch_pass([59, 60, 61]), 2 * {k})\n")
    return {"src": src, "tests": [t], "module": t.stem,
            "sources": [p]}


def tier_L3_interproc(base: Path, rng: random.Random) -> dict:
    """Three-frame call chain; the defect lives at the bottom, tests touch only the top."""
    # k>=3: at k==2 the buggy program (6+3k) coincides with the correct one
    # (6k) and the fixture would not be red.
    k = rng.randint(3, 9)
    src = base / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "pricing.py").write_text(
        "def unit_price(q):\n"
        "    return q * " + str(k) + "\n"   # BUG below: applied after tier build
        "\n\n"
        "def line_sum(qs):\n"
        "    return sum(unit_price(q) for q in qs)\n"
        "\n\n"
        "def invoice_total(lines):\n"
        "    return sum(line_sum(qs) for qs in lines)\n",
        encoding="utf-8")
    bug = "q * " + str(k)
    bad = "q + " + str(k)
    p = src / "pricing.py"
    p.write_text(p.read_text(encoding="utf-8").replace(bug, bad, 1),
                 encoding="utf-8")
    t = _unittest_test(
        src, "pricing",
        f"    def test_total(self):\n"
        f"        self.assertEqual(invoice_total([[1, 2], [3]]), {6 * k})\n")
    return {"src": src, "tests": [t], "module": t.stem,
            "sources": [p]}


def tier_L4_stateful(base: Path, rng: random.Random) -> dict:
    """RunningMean divides by n+1 after n records: only accumulated state exposes it."""
    src = base / "src"
    src.mkdir(parents=True, exist_ok=True)
    (src / "running_mean.py").write_text(
        "class RunningMean:\n"
        "    def __init__(self):\n"
        "        self.total = 0\n"
        "        self.n = 0\n"
        "\n"
        "    def add(self, x):\n"
        "        self.total += x\n"
        "        self.n += 1\n"
        "        return self\n"
        "\n"
        "    def mean(self):\n"
        "        return self.total / (self.n + 1)\n"   # BUG: must be self.n
        "\n\n"
        "def mean_of(xs):\n"
        "    m = RunningMean()\n"
        "    for x in xs:\n"
        "        m.add(x)\n"
        "    return m.mean()\n",
        encoding="utf-8")
    t = _unittest_test(
        src, "running_mean",
        "    def test_mean_stateful(self):\n"
        "        self.assertEqual(mean_of([2, 4, 6]), 4.0)\n"
        "    def test_single(self):\n"
        "        self.assertEqual(mean_of([10]), 10.0)\n")
    return {"src": src, "tests": [t], "module": t.stem,
            "sources": [src / "running_mean.py"]}


def tier_L5_coupled(base: Path, rng: random.Random) -> dict:
    """Harvested v6 generator: two independent defects, one test spanning both."""
    bug = v6.fresh_coupled_bug(rng, base, rng.randrange(1 << 20))
    return {"src": bug.src.parent, "tests": sorted(bug.tests),
            "module": sorted(bug.tests)[0].stem,
            "sources": [bug.src]}


TIERS = [
    ("L1_literal", tier_L1_literal),
    ("L2_boundary", tier_L2_boundary),
    ("L3_interproc", tier_L3_interproc),
    ("L4_stateful", tier_L4_stateful),
    ("L5_coupled", tier_L5_coupled),
]

# ---------------------------------------------------------------------- running
def suite_green(fixture: dict) -> bool:
    proc = subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "-v", fixture["module"]],
        cwd=str(fixture["src"]), text=True, capture_output=True, timeout=30)
    return proc.returncode == 0


def ground_args(cid: str, fixture: dict, tag: str = "run") -> dict:
    rel = lambda p: str(Path(p).resolve().relative_to(ROOT))  # noqa: E731
    tests = [rel(t) for t in fixture["tests"]]
    out = WORK / f"out_{tag}_{cid.replace('.', '_')}.json"
    args = {
        "output_path": str(out.relative_to(ROOT)),
        "test_paths": tests,
        "test_argv": [sys.executable, "-B", "-m", "unittest", "-v",
                      fixture["module"]],
        "timeout_s": LOOP_BUDGET["timeout_s"],
    }
    if "cegis_hypothesis" in cid:
        args["source_root"] = rel(fixture["src"])
    elif "apply.verified" in cid:
        args["source_root"] = rel(fixture["src"])
    elif "strict_progress" in cid:
        args["source_root"] = rel(fixture["src"])
    elif "coupled" in cid:
        args["source_root"] = rel(fixture["src"])
    else:  # test_guided + cegis_hypothesis family
        args["source_paths"] = [rel(s) for s in fixture["sources"]]
    return args


def run_ladder() -> dict:
    import shutil
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True, exist_ok=True)
    rows = []
    for tier_idx, (tier_name, maker) in enumerate(TIERS):
        for i in range(INSTANCES_PER_TIER):
            # Fixture-state protocol: agents include WRITERS (strict, coupled,
            # cegis, apply all realize bytes). One shared fixture let a writer
            # repair the tree out from under the agents after it -- measured
            # artifact: cegis honest-refused off strict's repair, apply took
            # credit via ALREADY_PASSES. Every agent gets its OWN pristine red
            # copy, rebuilt from the same per-instance seed.
            instance_seed = SEED * 1000 + tier_idx * 10 + i
            for cid, fn in (_load(cid, mod) for cid, mod in CAPS.items()):
                base = WORK / f"{tier_name}_{i}_{cid.rsplit('.', 2)[-2]}"
                base.mkdir(parents=True, exist_ok=True)
                fixture = maker(base, random.Random(instance_seed))
                baseline_green = suite_green(fixture)
                row = {"tier": tier_name, "instance": i, "capability_id": cid,
                       "baseline_green": baseline_green}
                if baseline_green:
                    row["verdict"] = "FIXTURE_BROKEN_NOT_RED"
                    rows.append(row)
                    continue
                args = ground_args(cid, fixture, f'{tier_name}_{i}')
                report = None
                t0 = time.monotonic()
                try:
                    report = fn(dict(args), str(ROOT))
                    claimed = True
                except SystemExit as exc:
                    claimed = False
                    row["refusal"] = str(exc.code).split("\n")[0][:160]
                except Exception as exc:
                    claimed = False
                    row["refusal"] = type(exc).__name__ + ":" + str(exc)[:160]
                seconds = time.monotonic() - t0
                green = suite_green(fixture)
                row["seconds"] = round(seconds, 2)
                row["claimed_verified"] = claimed
                row["independent_green"] = green
                # Verdict law: REPAIRED == independent green, PERIOD. The
                # writer/searcher name table lied (a repair loop whose
                # patches live in its artifact, not its return, got labelled
                # "searcher" and its real green was hidden behind a tag).
                found = bool(report and report.get("patches"))
                row["patch_reported"] = found
                if green:
                    row["verdict"] = "REPAIRED"
                elif claimed:
                    row["verdict"] = "NOT_REPAIRED_claimed_but_red"
                else:
                    row["verdict"] = "NOT_REPAIRED_refused"
                rows.append(row)
                print(f"{tier_name:13s} i{i} {cid.split('repair.')[-1]:28s} "
                      f"{row['verdict']:28s} {row['seconds']:>6}s")
    return {"schema": SCHEMA, "seed": SEED,
            "instances_per_tier": INSTANCES_PER_TIER,
            "tiers": [t for t, _ in TIERS], "rows": rows}


def summarize(doc: dict) -> dict:
    per: dict[str, dict[str, dict[str, int]]] = {}
    for r in doc["rows"]:
        cell = per.setdefault(r["tier"], {}).setdefault(
            r["capability_id"], {"repaired": 0, "patched": 0,
                                 "runs": 0, "seconds": 0})
        cell["runs"] += 1
        cell["seconds"] += r.get("seconds", 0)
        if r["verdict"] == "REPAIRED":
            cell["repaired"] += 1
        if r.get("patch_reported"):
            cell["patched"] += 1
    table = {t: {cid: {"repair_rate": c["repaired"] / c["runs"],
                       "patch_reported_rate": c["patched"] / c["runs"],
                       "repaired": c["repaired"], "patched": c["patched"],
                       "runs": c["runs"],
                       "mean_s": round(c["seconds"] / c["runs"], 1)}
                 for cid, c in sorted(caps.items())}
             for t, caps in per.items()}
    return {"schema": SCHEMA + "_SUMMARY", "per_tier_per_capability": table}


def main() -> int:
    doc = run_ladder()
    doc["summary"] = summarize(doc)["per_tier_per_capability"]
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE / "REPAIR_DEPTH_LADDER_20261029.json"
    out.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    print("\n== repair depth ladder ==")
    for tier, caps in doc["summary"].items():
        line = " ".join(
            f"{cid.split('repair.')[-1].split('.ast')[0].split('.v1')[0]}"
            f"={c['repair_rate']:.0%}/P{c['patch_reported_rate']:.0%}"
            f"({c['mean_s']}s)"
            for cid, c in caps.items())
        print(f"{tier:13s} {line}")
    print("receipt:", out.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
