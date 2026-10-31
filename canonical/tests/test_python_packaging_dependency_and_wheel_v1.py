# PROJECT_BRAIN
"""Pins for python.packaging.dependency_add.v1 and python.packaging.build_package.v1.

The two acts that open the pypi lane.  What is pinned is not the happy path -- it is the four
things that make an edit of somebody else's manifest safe, and the one thing that makes a build
real:

* the manifest is SPLICED, never re-serialised: every existing line survives, and exactly one line
  appears (a one-line array and a multi-line array are both handled);
* asking twice is answered, not applied twice (`already_present`, one entry, not two);
* the edit is verified by RE-READING the file -- it still parses and the dependency is there once;
* a refusal names the reason and writes a FAIL artifact instead of an empty success;
* a build is verified by READING the artifact: a wheel must carry `.dist-info/METADATA` and
  `RECORD`, and its name/version must come back out of it.

Run: python -m pytest canonical/tests/test_python_packaging_dependency_and_wheel_v1.py -q
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.bound_capabilities import packaging_v1 as P

DEP = "python.packaging.dependency_add.v1"
BUILD = "python.packaging.build_package.v1"

PYPROJECT = '''[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "demo-pkg"
version = "0.1.0"
dependencies = [
    "packaging>=23",
]
'''

PYPROJECT_ONE_LINE = '''[project]
name = "demo-pkg"
version = "0.1.0"
dependencies = ["packaging>=23"]
'''

REQUIREMENTS = '''# runtime
packaging>=23
'''


class _Project(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="packaging_pin_"))
        self.project = self.tmp / "project"
        (self.project / "demo").mkdir(parents=True)
        (self.project / "demo" / "__init__.py").write_text("x = 1\n", encoding="utf-8")

    def _manifest(self, text: str, name: str = "pyproject.toml") -> Path:
        path = self.project / name
        path.write_text(text, encoding="utf-8")
        return path

    def _add(self, dependency: str) -> dict:
        return P.run({"act_verb": "dependency_add", "capability_id": DEP,
                      "source_root": str(self.project), "dependency": dependency,
                      "output_path": str(self.tmp / "add.json")}, self.tmp)


class DependencyAddTests(_Project):

    def test_a_multi_line_array_gains_exactly_one_line_and_keeps_every_other(self):
        path = self._manifest(PYPROJECT)
        payload = self._add("requests>=2")
        after = path.read_text(encoding="utf-8")
        self.assertTrue(payload["verified"])
        self.assertEqual(payload["lines_added"], ['    "requests>=2",'])
        for line in PYPROJECT.splitlines():
            self.assertIn(line, after, "an existing line was rewritten")
        self.assertEqual(payload["other_lines_changed"], 0)
        self.assertEqual(payload["dependencies"], ["packaging>=23", "requests>=2"])

    def test_a_one_line_array_is_spliced_not_reflowed(self):
        path = self._manifest(PYPROJECT_ONE_LINE)
        payload = self._add("requests")
        text = path.read_text(encoding="utf-8")
        self.assertTrue(payload["verified"])
        self.assertIn('dependencies = ["packaging>=23", "requests"]', text)
        self.assertIn('version = "0.1.0"', text)

    def test_asking_twice_is_answered_not_applied_twice(self):
        path = self._manifest(PYPROJECT)
        self._add("requests>=2")
        once = path.read_text(encoding="utf-8")
        payload = self._add("requests>=2")
        self.assertTrue(payload["already_present"])
        self.assertTrue(payload["verified"])
        self.assertEqual(path.read_text(encoding="utf-8"), once)
        self.assertEqual(sum(1 for d in payload["dependencies"] if "requests" in d), 1)

    def test_a_requirements_file_is_appended_to(self):
        path = self._manifest(REQUIREMENTS, "requirements.txt")
        payload = self._add("requests>=2")
        self.assertEqual(payload["manifest_kind"], "requirements")
        self.assertIn("requests>=2", path.read_text(encoding="utf-8").splitlines())
        self.assertIn("packaging>=23", payload["dependencies"])

    def test_a_project_without_a_manifest_is_refused_in_words(self):
        (self.project / "pyproject.toml").unlink(missing_ok=True)
        with self.assertRaises(Exception) as caught:
            self._add("requests")
        self.assertIn("NO_MANIFEST", str(caught.exception))

    def test_an_option_is_not_a_requirement(self):
        self._manifest(PYPROJECT)
        with self.assertRaises(Exception) as caught:
            self._add("--index-url=https://example.invalid/simple")
        self.assertIn("DEPENDENCY_NOT_A_REQUIREMENT", str(caught.exception))
        # ...and the refusal wrote a FAIL artifact rather than an empty success
        artifact = json.loads((self.tmp / "add.json").read_text(encoding="utf-8"))
        self.assertEqual(artifact["gate"], "FAIL")
        self.assertIn("DEPENDENCY_NOT_A_REQUIREMENT", artifact["reason"])

    def test_a_two_line_value_is_refused(self):
        self._manifest(PYPROJECT)
        with self.assertRaises(Exception) as caught:
            self._add("requests\nmalicious")
        self.assertIn("DEPENDENCY_NOT_A_REQUIREMENT", str(caught.exception))


class BuildPackageTests(_Project):

    def test_a_wheel_is_built_and_verified_by_reading_it(self):
        self._manifest(PYPROJECT)
        payload = P.run({"act_verb": "build_package", "capability_id": BUILD,
                         "source_root": str(self.project),
                         "output_path": str(self.tmp / "build.json")}, self.tmp)
        self.assertTrue(payload["verified"])
        self.assertEqual(payload["name"], "demo-pkg")
        self.assertEqual(payload["version"], "0.1.0")
        self.assertTrue(payload["has_record"])
        self.assertIn("demo", payload["top_level"])
        kept = Path(payload["wheel"])
        self.assertTrue(kept.is_file())
        self.assertEqual(kept.name, payload["wheel_name"])
        self.assertTrue(kept.name.startswith("demo_pkg-0.1.0"))

    def test_the_artifact_is_digest_verified_like_every_other_verb(self):
        self._manifest(PYPROJECT)
        P.run({"act_verb": "build_package", "capability_id": BUILD,
               "source_root": str(self.project), "output_path": str(self.tmp / "b.json")},
              self.tmp)
        from canonical.runtime.bound_capabilities.quality_v1 import verify_artifact
        self.assertTrue(verify_artifact(self.tmp / "b.json"))

    def test_a_project_that_cannot_build_refuses_with_the_builders_own_words(self):
        self._manifest('[project]\nname = "demo-pkg"\nversion = "0.1.0"\n', "pyproject.toml")
        (self.project / "pyproject.toml").write_text(
            '[build-system]\nrequires = ["no-such-backend-xyz"]\n'
            'build-backend = "no_such_backend_xyz"\n\n[project]\nname = "d"\nversion = "0.1.0"\n',
            encoding="utf-8")
        with self.assertRaises(Exception) as caught:
            P.run({"act_verb": "build_package", "capability_id": BUILD,
                   "source_root": str(self.project), "output_path": str(self.tmp / "c.json"),
                   "timeout_s": 120}, self.tmp)
        self.assertIn("BUILD_FAILED", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
