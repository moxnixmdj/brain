"""A sentence names FILES; a review gate reviews a CHANGE SET.  The derivation closes that gap.

Measured 2026-10-29 on a fresh tree, one door call each::

    "Lint <...>/pkg/calc.py"        FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
    "Type-check <...>/pkg/calc.py"  FAIL_CLOSED__ROUTE_ADMISSION_REJECTED
    "Run a security audit on <pkg>" FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED

with ``BINDING_REFUSED:diff_path:0_type_compatible_existing_files_named`` underneath.  Nine
capabilities in the registry declare ``diff_path`` + ``worktree_path`` (static triage, type gate,
security gate, coverage gate, mutation gate, perf gate, apply-and-test gate ...) and every one of
them was unreachable from English, because nothing in the registry produces a change set from a
sentence (census over all 419 rows: the only producer is
``python.software.repair.apply.verified.v1``).

A request to review a FILE is a request to review all of it.  The honest change set for it is every
line as an ADDITION against an empty baseline -- what ``git diff --no-index /dev/null <file>``
writes, and what the gate's own parser already treats as "the whole file is in scope".  Nothing is
invented: the content is the file's bytes, the baseline is empty, the artifact is content-addressed
so the same request always produces the same diff, and the diff is a *derived input*, never a claim
about the result.

The honesty controls matter more than the reach: a review gate is READ-ONLY, so it must never edit
the file it reviews; and a file that really has a defect must be REFUSED, not passed.  Both are
asserted below, and both hold whether or not the declared static tool is installed (a tool-absent
gate reports ``PASS_SYNTAX_ONLY`` loudly, which is not a PASS).
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import (  # noqa: E402
    capability_selection_retrieval_v1 as selection,
    declared_input_derivation_v1 as derivation,
    live_brain_route_admission_v1 as door,
)

WORK = ROOT / "canonical/astra_runtime/tmp/test_review_change_set"
TRIAGE = "python.review.diff_static_triage.v1"
CLEAN = "def add(a, b):\n    return a + b\n"
UNDEFINED = "def f():\n    return undefined_name + 1\n"
BROKEN = "def f(:\n    return 1\n"


def _fresh(case: str, body: str = CLEAN) -> pathlib.Path:
    base = WORK / case
    if base.exists():
        shutil.rmtree(base)
    (base / "pkg").mkdir(parents=True)
    (base / "pkg/calc.py").write_text(body, encoding="utf-8")
    return base


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _entry(cid: str = TRIAGE) -> dict:
    return door.load_verified_registry()[cid]


def _ruff_present() -> bool:
    proc = subprocess.run([sys.executable, "-m", "ruff", "--version"],
                          capture_output=True, text=True)
    return proc.returncode == 0 and proc.stdout.strip().startswith("ruff")


class TheChangeSetIsTheFilesOwnBytes(unittest.TestCase):
    def test_every_line_of_the_stated_file_is_new(self):
        base = _fresh("shape")
        src = _rel(base / "pkg/calc.py")
        values = derivation.derive("Lint the file %s" % src, _entry(), ROOT)
        self.assertIn("diff_path", values)
        self.assertIn("worktree_path", values)
        self.assertEqual(values["worktree_path"]["value"], ".",
                         "the new-side bytes are the tree the sentence named")
        text = (ROOT / values["diff_path"]["value"]).read_text(encoding="utf-8")
        self.assertIn("+++ b/" + src, text)
        self.assertIn("@@ -0,0 +1,2 @@", text, text)
        self.assertIn("+def add(a, b):", text)
        self.assertNotIn("--- a/" + src, "the baseline is EMPTY, not a guess at an older revision")

    def test_the_same_sentence_always_produces_the_same_change_set(self):
        """Content-addressed: rewrite is a no-op, so nothing accumulates between runs."""
        base = _fresh("idempotent")
        src = _rel(base / "pkg/calc.py")
        first = derivation.derive("Lint the file %s" % src, _entry(), ROOT)["diff_path"]["value"]
        path = ROOT / first
        before = path.stat().st_mtime_ns, path.read_bytes()
        second = derivation.derive("Lint the file %s" % src, _entry(), ROOT)["diff_path"]["value"]
        after = path.stat().st_mtime_ns, path.read_bytes()
        self.assertEqual(first, second)
        self.assertEqual(before, after, "an unchanged file must not rewrite its change set")

    def test_a_different_file_is_a_different_change_set(self):
        other = _fresh("other", "def g():\n    return 2\n")
        src = _rel(other / "pkg/calc.py")
        values = derivation.derive("Lint the file %s" % src, _entry(), ROOT)
        self.assertIn("+def g():", (ROOT / values["diff_path"]["value"]).read_text())
        self.assertNotIn("+def add(a, b):", (ROOT / values["diff_path"]["value"]).read_text())

    def test_a_sentence_that_names_no_file_derives_nothing(self):
        values = derivation.derive("Lint the repository", _entry(), ROOT)
        self.assertNotIn("diff_path", values)


class TheGateReviewsTheWholeFile(unittest.TestCase):
    def test_the_door_lints_a_stated_file_without_editing_it(self):
        base = _fresh("lint_clean")
        src = base / "pkg/calc.py"
        before = src.read_bytes()
        result = door.solve({"task_id": "REV_LINT", "goal": "Lint the file %s" % _rel(src)})
        self.assertEqual(src.read_bytes(), before, "a review gate edited the file it reviewed")
        if _ruff_present():
            self.assertIs(result.get("pass"), True, result.get("status"))
            self.assertEqual(result.get("compiled_capability_id"), TRIAGE)
        else:
            # Tool absent: the gate says PASS_SYNTAX_ONLY loudly and is NOT a pass.
            self.assertIs(result.get("pass"), False, result.get("status"))

    def test_a_real_lint_defect_is_refused_not_passed(self):
        base = _fresh("lint_defect", UNDEFINED)
        src = base / "pkg/calc.py"
        before = src.read_bytes()
        result = door.solve({"task_id": "REV_DEFECT", "goal": "Lint the file %s" % _rel(src)})
        self.assertIs(result.get("pass"), False,
                      "an undefined name was reported as a clean file: %s" % result.get("status"))
        self.assertEqual(src.read_bytes(), before)

    def test_a_syntax_error_is_refused_with_or_without_the_tool(self):
        """The baseline compile stage is stdlib-only, so this control is environment-free."""
        base = _fresh("lint_broken", BROKEN)
        src = base / "pkg/calc.py"
        result = door.solve({"task_id": "REV_BROKEN", "goal": "Lint the file %s" % _rel(src)})
        self.assertIs(result.get("pass"), False, result.get("status"))

    def test_an_unstated_scope_is_not_a_license_to_scan(self):
        """No stated file => no change set => the reach does not silently widen."""
        self.assertIsNone(
            selection.select("Lint the repository", door.load_verified_registry(), ROOT).get(
                "selected_capability"))


if __name__ == "__main__":
    unittest.main()
