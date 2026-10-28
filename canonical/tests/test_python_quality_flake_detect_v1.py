# PROJECT_BRAIN
"""Pins for python.quality.flake_detect.v1 — a flake is proven by REPLAY.

The pins exist to nail the asymmetry the adapter is built on:

* outcome VARIANCE is evidence and is reported with the seeds that produced it;
* a test that fails in every run is a broken test and is reported separately, so
  it is never "fixed" by rerunning;
* `stable` is a statement about this budget only, and the artifact says so;
* the tree being measured is never modified by the measuring.

Run: python -m pytest canonical/tests/test_python_quality_flake_detect_v1.py -q
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.bound_capabilities import quality_flake_detect_v1 as fd

PY = sys.executable

ORDER_DEPENDENT = '''STATE = []


def test_a_expects_a_clean_slate():
    STATE.append(1)
    assert STATE == [1]


def test_b_pollutes():
    STATE.append(2)
    assert 2 in STATE
'''

STABLE = '''def test_one():
    assert 1 + 1 == 2


def test_two():
    assert "a".upper() == "A"
'''

ALWAYS_RED = '''def test_broken():
    assert 1 == 2
'''


def _build(root: Path, files: dict) -> Path:
    src = root / "src"
    (src / "pkg").mkdir(parents=True, exist_ok=True)
    (src / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    for rel, body in files.items():
        f = src / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body, encoding="utf-8")
    return src


def _run(root: Path, **kw):
    args = {"source_root": "src", "output_path": "_out/flakes.json",
            "python_executable": PY, "timeout_s": 300}
    args.update(kw)
    return fd.run(args, root), json.loads((root / "_out/flakes.json").read_text())


def _snapshot(src: Path) -> dict:
    return {p.relative_to(src).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(src.rglob("*.py"))}


class TestFlakeDetect(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="flakedetect_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_order_dependent_test_is_reported_with_its_evidence(self):
        _build(self.tmp, {"pkg/test_order.py": ORDER_DEPENDENT})
        res, art = _run(self.tmp, repeats=4)
        self.assertEqual(art["gate"], "PASS")
        self.assertEqual(art["runs"], 4)
        self.assertEqual(art["flakes_found"], 1)
        self.assertTrue(any("test_a_expects_a_clean_slate" in name
                            for name in art["flaky_tests"]))
        evidence = art["flaky_evidence"][
            next(iter(art["flaky_evidence"]))] if art["flaky_evidence"] else []
        self.assertEqual({row["outcome"] for row in evidence}, {"passed", "failed"})
        # the order-independent test in the same file is not called flaky
        self.assertFalse(any("test_b_pollutes" in name for name in art["flaky_tests"]))

    def test_a_stable_suite_reports_no_flake_and_says_what_it_cannot_see(self):
        _build(self.tmp, {"pkg/test_stable.py": STABLE})
        res, art = _run(self.tmp, repeats=3)
        self.assertEqual(art["flakes_found"], 0)
        self.assertEqual(art["stable"], 2)
        self.assertIn("not a certificate of determinism", art["detection_scope"])

    def test_a_test_that_fails_every_time_is_not_a_flake(self):
        _build(self.tmp, {"pkg/test_red.py": ALWAYS_RED})
        res, art = _run(self.tmp, repeats=2)
        self.assertEqual(art["flakes_found"], 0)
        self.assertEqual(len(art["consistently_failing"]), 1)
        self.assertIn("test_broken", art["consistently_failing"][0])

    def test_one_run_is_not_a_flake_hunt(self):
        _build(self.tmp, {"pkg/test_stable.py": STABLE})
        with self.assertRaises(SystemExit) as raised:
            _run(self.tmp, repeats=1)
        self.assertIn("REPEATS_BELOW_TWO", str(raised.exception))

    def test_no_tests_refuses_instead_of_reporting_zero_flakes(self):
        src = _build(self.tmp, {})
        with self.assertRaises(SystemExit) as raised:
            _run(self.tmp)
        self.assertIn("NO_TESTS_FOUND", str(raised.exception))

    def test_the_measured_tree_is_never_modified(self):
        src = _build(self.tmp, {"pkg/test_order.py": ORDER_DEPENDENT})
        before = _snapshot(src)
        _run(self.tmp, repeats=3)
        self.assertEqual(before, _snapshot(src))

    def test_determinism_same_tree_same_verdict(self):
        _build(self.tmp, {"pkg/test_order.py": ORDER_DEPENDENT})
        _, first = _run(self.tmp, repeats=4)
        _, second = _run(self.tmp, repeats=4)
        self.assertEqual(first["flaky_tests"], second["flaky_tests"])
        self.assertEqual(first["flakes_found"], second["flakes_found"])


if __name__ == "__main__":
    unittest.main()
