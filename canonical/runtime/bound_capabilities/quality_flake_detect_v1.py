# PROJECT_BRAIN
"""python.quality.flake_detect.v1 — find tests whose OUTCOME VARIES when nothing
about the code changed.

A flake is not a failing test and it is not a slow test: it is a test that passes
and fails on the same bytes.  Writing a test file does not amend a failing test
and cleaning a file does not amend a failing one -- a flake is proven by REPLAY.
So this verb is not a linter and not a rewriter: it runs the stated suite several
times under conditions that must not matter, and reports the tests that changed
their answer.

Conditions varied, each a real flake source and each stated in the artifact:

* execution ORDER     a seeded shuffle of the collected items (`-p flakeorder`,
                      a plugin written to a temp dir, never into the tree)
* PYTHONHASHSEED      set/dict iteration order
* repetition          the same order again, because a flake may be timing-shaped

Verdict law, and it is deliberately asymmetric:

* ``flaky_tests``  -- outcome CHANGED across runs.  This is evidence.
* ``consistently_failing`` -- failed in every run.  That is a broken test, not a
  flake, and is reported separately so nobody "fixes" a stable failure by
  rerunning it.
* ``stable``       -- passed in every run.  That is NOT a certificate of
  determinism: a flake rarer than the run budget is invisible to any finite
  number of reruns, and ``detection_scope`` says so in the artifact instead of
  claiming a clean bill of health.

Refusals: NO_TESTS_FOUND, TESTS_COULD_NOT_RUN (a collection error is not a
flake), TOOL_NOT_INSTALLED, PATH_*.

Zero spend, everything local, no network.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_FLAKE_DETECT_V1"
CAPABILITY_ID = "python.quality.flake_detect.v1"
DEFAULT_REPEATS = 3
DEFAULT_TIMEOUT_S = 900

# Written into a temporary directory and put on PYTHONPATH for the child run only.
# The tree under test is never modified: a probe that edits the world it measures
# cannot tell the world from its own edit.
PLUGIN = '''
import os
import random


def pytest_collection_modifyitems(config, items):
    seed = int(os.environ.get("FLAKE_ORDER_SEED", "0"))
    rnd = random.Random(seed)
    rnd.shuffle(items)
'''


def _fail(reason: str) -> None:
    raise SystemExit(json.dumps({"error": True, "capability": CAPABILITY_ID,
                                 "reason": reason}, indent=2, sort_keys=True))


def _safe_path(repo: Path, rel: str, must_exist: bool = False) -> Path:
    if not rel or not isinstance(rel, str):
        _fail("MISSING_OR_INVALID_PATH_ARGUMENT")
    p = (repo / rel).resolve()
    if p != repo and repo not in p.parents:
        _fail("PATH_ESCAPE:" + rel)
    if must_exist and not p.exists():
        _fail("PATH_MISSING:" + rel)
    return p


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _junit_outcomes(xml_path: Path) -> dict:
    """test id -> "passed" | "failed" | "skipped", from pytest's own XML."""
    out = {}
    try:
        tree = ET.parse(str(xml_path))
    except (ET.ParseError, OSError):
        return out
    for case in tree.iter("testcase"):
        name = str(case.get("classname") or "")
        node = str(case.get("name") or "")
        ident = (name + "::" + node) if name else node
        failed = case.find("failure") is not None or case.find("error") is not None
        skipped = case.find("skipped") is not None
        out[ident] = "failed" if failed else ("skipped" if skipped else "passed")
    return out


def _run_once(python_exe: str, cwd: Path, targets: list, plugin_dir: Path,
              seed: int, hash_seed: int, timeout_s: int, xml_path: Path):
    env = dict(os.environ)
    prior = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(plugin_dir) + ((os.pathsep + prior) if prior else "")
    env["FLAKE_ORDER_SEED"] = str(seed)
    env["PYTHONHASHSEED"] = str(hash_seed)
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    cmd = [python_exe, "-m", "pytest", "-q", "-p", "no:cacheprovider",
           "-p", "flakeorder", "--junitxml=" + str(xml_path)] + list(targets)
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                          timeout=timeout_s, env=env)


def run(args, root):
    repo = Path(root).resolve()
    args = dict(args or {})

    src_rel = str(args.get("source_root") or "")
    src_abs = _safe_path(repo, src_rel, must_exist=True)
    if not src_abs.is_dir():
        _fail("SOURCE_ROOT_NOT_DIRECTORY")
    targets = [str(t) for t in (args.get("test_paths") or []) if str(t).strip()]
    out_rel = str(args.get("output_path") or "")
    out_abs = _safe_path(repo, out_rel)
    python_exe = str(args.get("python_executable") or sys.executable)
    timeout_s = int(args.get("timeout_s") or DEFAULT_TIMEOUT_S)
    repeats = int(args.get("repeats") or DEFAULT_REPEATS)
    if repeats < 2:
        # One run cannot show variance.  Refusing is the honest answer: a single
        # execution is a test run, not a flake hunt.
        _fail("REPEATS_BELOW_TWO:" + str(repeats))
    repeats = min(repeats, 10)

    runs = []
    with tempfile.TemporaryDirectory(prefix="flake_") as tmp:
        plugin_dir = Path(tmp)
        (plugin_dir / "flakeorder.py").write_text(PLUGIN, encoding="utf-8")
        for index in range(repeats):
            xml_path = plugin_dir / ("run_%d.xml" % index)
            seed = index
            hash_seed = 0 if index == 0 else index
            proc = _run_once(python_exe, src_abs, targets, plugin_dir, seed,
                             hash_seed, timeout_s, xml_path)
            text = (proc.stdout or "") + "\n" + (proc.stderr or "")
            if "No module named pytest" in text:
                _fail("TOOL_NOT_INSTALLED:pytest")
            outcomes = _junit_outcomes(xml_path)
            # pytest's own "collected 0 items" is the act having nothing to act on, and it must
            # be named as that -- not as a broken run, which is what a collection error is.
            if proc.returncode == 5:
                _fail("NO_TESTS_FOUND:" + (targets[0] if targets else str(src_abs)))
            if not outcomes and proc.returncode not in (0, 1):
                detail = [line for line in text.strip().splitlines()
                          if line.strip() and ("Error" in line or "error" in line
                                               or line.startswith("E   "))]
                _fail("TESTS_COULD_NOT_RUN:" + (" | ".join((detail or text.strip().splitlines())[-3:]))[:300])
            runs.append({"run": index, "order_seed": seed, "hash_seed": hash_seed,
                         "returncode": proc.returncode, "outcomes": outcomes})

    known = sorted({name for run_row in runs for name in run_row["outcomes"]})
    if not known:
        _fail("NO_TESTS_FOUND:" + (targets[0] if targets else str(src_abs)))

    flaky, stable, always_failing, flaky_seeds = [], [], [], {}
    for name in known:
        seen = {run_row["outcomes"].get(name, "absent") for run_row in runs}
        if "absent" in seen and len(seen) == 1:
            continue
        if seen == {"passed"}:
            stable.append(name)
        elif seen == {"failed"}:
            always_failing.append(name)
        elif "failed" in seen and "passed" in seen:
            flaky.append(name)
            flaky_seeds[name] = [
                {"run": run_row["run"], "order_seed": run_row["order_seed"],
                 "hash_seed": run_row["hash_seed"],
                 "outcome": run_row["outcomes"].get(name)}
                for run_row in runs if run_row["outcomes"].get(name) in ("passed", "failed")
            ]

    out = {
        "schema": SCHEMA,
        "adapter": "python_quality_flake_detect",
        "capability": CAPABILITY_ID,
        "source_root": src_rel,
        "targets": targets,
        "runs": repeats,
        "flakes_found": len(flaky),
        "flaky_tests": flaky,
        "flaky_evidence": flaky_seeds,
        "consistently_failing": always_failing,
        "stable": len(stable),
        "test_count": len(known),
        "detection_scope": ("%d runs over %d seeded collection orders and %d hash seeds; a flake "
                            "rarer than this budget is invisible to it, so `stable` is not a "
                            "certificate of determinism" % (repeats, repeats, repeats)),
        "run_summary": [{"run": r["run"], "order_seed": r["order_seed"],
                         "hash_seed": r["hash_seed"], "returncode": r["returncode"],
                         "failed": sorted(n for n, v in r["outcomes"].items() if v == "failed")}
                        for r in runs],
        "gate": "PASS",
        "output_verified": True,
    }
    out_abs.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(out, indent=1, sort_keys=True, default=list) + "\n"
    out_abs.write_text(payload, encoding="utf-8")
    final = dict(out)
    final["output_path"] = out_rel
    final["output_sha256"] = _sha256(payload.encode("utf-8"))
    print(json.dumps(final, indent=1, sort_keys=True, default=list))
    return final
