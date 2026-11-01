"""Nothing to do is an answer, and only with the proof.

Measured 2026-11-01, advanced census, the two sentences and the two verdicts:

    "Pin the dependency versions in <proj>/pyproject.toml."
      -> FAIL_CLOSED__CAPABILITY_REFUSED_POLYGLOT_REFUSED
         POLYGLOT_REFUSED:PYPROJECT_ALREADY_PINNED_OR_EMPTY

    "Vendor the single dependency of the project in <proj>/pkg."
      -> FAIL_CLOSED__CAPABILITY_REFUSED_POLYGLOT_REFUSED
         POLYGLOT_REFUSED:NO_DECLARED_DEPENDENCY_TO_VENDOR

Neither project declares a single dependency. Both requests are already true, vacuously, and the
machine reported them as missing capabilities -- two of the fourteen refusals in that census.

Why that is a lie and not a conservative choice: a refusal says "I cannot do this". A caller who
reads it goes looking for the capability, or works around it by hand. What actually happened is
that the engine rewrote the dependency array, saw its own output was identical to its input, and
called that failure. Its own rewrite is not evidence. The declaration is.

What is asserted, and how it is checked independently of the runtime's report:

* the request is answered ``PASS__REQUESTED_STATE_ALREADY_HOLDS`` with ``edited: false``, and the
  file on disk is **byte-identical** before and after -- read by this test, not by the door;
* the answer's evidence agrees with this test's OWN ``tomllib`` parse of the manifest: an empty
  declaration list is exactly why nothing was done;
* the negative controls are the ones that make ``already held`` mean something: an UNPINNED
  manifest must still be edited (bytes change, pins appear), a declared dependency must not be
  reported as ``already_satisfied``, and a manifest whose pins are all exact must be reported as
  already satisfied *with those pins named* -- not merely because nothing changed.

The engine is exercised through the front door, because the defect was in how the answer travelled.
"""
from __future__ import annotations

import pathlib
import shutil
import sys
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

SCRATCH = ROOT / "canonical" / "astra_runtime" / "tmp" / "already_satisfied_v1"


def _project(name: str, pyproject: str) -> pathlib.Path:
    base = SCRATCH / name
    if base.exists():
        shutil.rmtree(base)
    (base / "pkg").mkdir(parents=True)
    (base / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    (base / "pkg" / "mod.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    return base


NO_DEPS = '[project]\nname = "probe"\nversion = "0.1.0"\nrequires-python = ">=3.11"\n'
UNPINNED = '[project]\nname = "probe"\nversion = "0.1.0"\ndependencies = ["requests>=2.0"]\n'
PINNED = '[project]\nname = "probe"\nversion = "0.1.0"\ndependencies = ["requests==2.32.3"]\n'


class NothingToDoIsAnAnswerWithTheProof(unittest.TestCase):
    def tearDown(self) -> None:
        if SCRATCH.exists():
            shutil.rmtree(SCRATCH, ignore_errors=True)

    def _solve(self, goal: str) -> dict:
        return door.solve({"task_id": "ALREADY_SATISFIED_TEST", "goal": goal}) or {}

    def test_a_manifest_with_no_dependencies_is_already_pinned(self) -> None:
        base = _project("no_deps", NO_DEPS)
        before = (base / "pyproject.toml").read_bytes()
        result = self._solve(f"Pin the dependency versions in {base}/pyproject.toml.")
        after = (base / "pyproject.toml").read_bytes()

        self.assertEqual("PASS__REQUESTED_STATE_ALREADY_HOLDS", result.get("status"), result)
        self.assertIs(True, result.get("already_satisfied"))
        self.assertIs(False, result.get("edited"), "nothing was edited, and the answer must say so")
        self.assertEqual(before, after, "the manifest changed under an already-satisfied answer")

        # The oracle: this test's own parse of the manifest, not the artifact's claim.
        declared = tomllib.loads(after.decode("utf-8")).get("project", {}).get("dependencies", [])
        self.assertEqual([], declared)
        evidence = (result.get("answer_artifact") or {}).get("evidence") or {}
        self.assertEqual([], evidence.get("declared_dependencies"), evidence)
        self.assertEqual([], evidence.get("unpinned"), evidence)

    def test_a_project_with_no_declared_dependency_has_nothing_to_vendor(self) -> None:
        base = _project("vendor_none", NO_DEPS)
        before = (base / "pyproject.toml").read_bytes()
        result = self._solve(f"Vendor the single dependency of the project in {base}/pkg.")
        self.assertEqual("PASS__REQUESTED_STATE_ALREADY_HOLDS", result.get("status"), result)
        self.assertIs(False, result.get("edited"))
        self.assertEqual(before, (base / "pyproject.toml").read_bytes())
        self.assertFalse((base / "_vendor").exists(), "a vendor directory appeared for nothing")

    def test_an_unpinned_manifest_is_still_edited(self) -> None:
        base = _project("unpinned", UNPINNED)
        result = self._solve(f"Pin the dependency versions in {base}/pyproject.toml.")
        after = tomllib.loads((base / "pyproject.toml").read_text(encoding="utf-8"))
        deps = after.get("project", {}).get("dependencies", [])
        self.assertTrue(deps, result)
        self.assertTrue(all("==" in d for d in deps), deps)
        self.assertIsNot(True, result.get("already_satisfied"),
                         "work was done; that is not an already-satisfied answer")

    def test_exactly_pinned_manifest_reports_the_pins_it_read(self) -> None:
        base = _project("pinned", PINNED)
        before = (base / "pyproject.toml").read_bytes()
        result = self._solve(f"Pin the dependency versions in {base}/pyproject.toml.")
        self.assertEqual("PASS__REQUESTED_STATE_ALREADY_HOLDS", result.get("status"), result)
        self.assertEqual(before, (base / "pyproject.toml").read_bytes())
        evidence = (result.get("answer_artifact") or {}).get("evidence") or {}
        self.assertEqual(["requests==2.32.3"], evidence.get("declared_dependencies"), evidence)
        self.assertEqual("PYPROJECT_DEPENDENCIES_ALREADY_PINNED", evidence.get("reason"), evidence)

    def test_a_declared_dependency_is_not_silently_already_vendored(self) -> None:
        base = _project("vendor_required", PINNED)
        result = self._solve(f"Vendor the single dependency of the project in {base}/pkg.")
        self.assertIsNot(True, result.get("already_satisfied"),
                         "a declared dependency was reported as already vendored: " + str(result))


if __name__ == "__main__":
    unittest.main()
