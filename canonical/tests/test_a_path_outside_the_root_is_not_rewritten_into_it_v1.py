"""An absolute path outside the tree is not a repository path, and must not become one.

``goal_compiler._repo_paths`` matches a path with a pattern that cannot start at a
``/``, so ``/tmp/ws/calc.py`` is matched from ``tmp/`` and the leading separator is
reattached.  That reattachment was added for a real reason -- an absolute path
INSIDE the repository was being doubled into ``<repo>/home/user/brain/...`` -- but it
had no arm for an absolute path OUTSIDE the repository, so the token fell through and
was joined onto the root:

    "/tmp/ws_probe5/calc.py"   ->   ("tmp/ws_probe5/calc.py", "<repo>/tmp/ws_probe5/calc.py")

Measured 2026-11-01 on main ``c34c150``: ``Format /tmp/ws_probe5/calc.py.`` formatted
the caller's file and then reported ``FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED``,
because the declared output was the phantom ``<repo>/tmp/ws_probe5/calc.py`` that the
adapter could not find (``CLI_EXPECTED_OUTPUT_MISSING``).  The same alias is a
wrong-file hazard, not just a cosmetic one: had ``<repo>/tmp/ws_probe5/calc.py``
existed, the sentence about ``/tmp`` would have edited THAT file and reported success.

So the reading is: a relative path resolves against the root; an absolute path inside
the root keeps its repository-relative spelling; an absolute path outside the root is
not bound at all, and the door says so by name instead of blaming a capability.
"""
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import goal_compiler as gc  # noqa: E402
from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/path_outside_root_v1"
SOURCE = "def  f( x ):\n    return   x+1\n"


class APathOutsideTheRootIsNotRewrittenIntoIt(unittest.TestCase):

    def setUp(self) -> None:
        shutil.rmtree(WORK, ignore_errors=True)
        WORK.mkdir(parents=True, exist_ok=True)
        (WORK / "calc.py").write_text(SOURCE, encoding="utf-8")
        self.outside = pathlib.Path(tempfile.mkdtemp(prefix="brain-outside-root-"))
        (self.outside / "calc.py").write_text(SOURCE, encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(WORK, ignore_errors=True)
        shutil.rmtree(self.outside, ignore_errors=True)

    def test_an_absolute_path_outside_the_root_binds_no_repository_path(self) -> None:
        goal = f"Format {self.outside}/calc.py."
        self.assertEqual(gc._repo_paths(goal, ROOT), [],
                         "an absolute path outside the root was aliased into it")
        phantom = ROOT / str(self.outside).lstrip("/")
        self.assertFalse(phantom.exists(), "this test's own premise: no such file in the tree")
        self.assertEqual(front._future_artifacts(goal, ROOT), [],
                         "a promise was made about a file the sentence never named")

    def test_an_absolute_path_inside_the_root_keeps_its_repository_spelling(self) -> None:
        stated = gc._repo_paths(f"Format {WORK}/calc.py.", ROOT)
        self.assertEqual(len(stated), 1, stated)
        raw, resolved = stated[0]
        self.assertEqual(raw, str((WORK / "calc.py").relative_to(ROOT)))
        self.assertEqual(resolved.resolve(), (WORK / "calc.py").resolve())

    def test_the_door_names_the_scope_and_leaves_the_file_alone(self) -> None:
        goal = f"Format {self.outside}/calc.py."
        self.assertEqual(door._stated_paths_outside_the_root(goal, ROOT),
                         [f"{self.outside}/calc.py"])
        result = door.solve({"task_id": "OUTSIDE_ROOT", "goal": goal})
        self.assertEqual(result.get("status"), "FAIL_CLOSED__STATED_PATH_OUTSIDE_THE_WORKSPACE",
                         result.get("status"))
        self.assertIn("STATED_PATH_OUTSIDE_THE_WORKSPACE", str(result.get("reason") or ""))
        self.assertEqual((self.outside / "calc.py").read_text(encoding="utf-8"), SOURCE,
                         "the caller's file was changed by a request the door refused")

    def test_every_family_that_names_only_an_outside_path_is_refused_by_name(self) -> None:
        """The label must not depend on which capability the sentence resembles.

        Measured before the gate: the same shape reported STATED_SWE_EFFECT_UNSERVED
        for a format, GOAL_INPUT_BINDING_REQUIRED for a repair and
        GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH for a rename.  None of the three
        says the file is not in this workspace, and the first one ran the command
        anyway.
        """
        (self.outside / "mod.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
        (self.outside / "test_mod.py").write_text(
            "from mod import add\n\ndef test_add():\n    assert add(1, 2) == 3\n", encoding="utf-8")
        sentences = (
            f"Format {self.outside}/calc.py.",
            f"The tests in {self.outside}/test_mod.py are failing. Fix the code so they pass.",
            f"Rename old_name to new_name in {self.outside}/lib.py.",
            f"Add type hints to add in {self.outside}/mod.py.",
        )
        for index, goal in enumerate(sentences):
            with self.subTest(goal=goal):
                result = door.solve({"task_id": f"OUTSIDE_FAMILY_{index}", "goal": goal})
                self.assertEqual(result.get("status"),
                                 "FAIL_CLOSED__STATED_PATH_OUTSIDE_THE_WORKSPACE",
                                 (goal, result.get("status"), result.get("reason")))
                self.assertIn("STATED_PATH_OUTSIDE_THE_WORKSPACE",
                              str(result.get("reason") or ""))
                self.assertFalse(result.get("pass"))
        self.assertEqual((self.outside / "calc.py").read_text(encoding="utf-8"), SOURCE)
        self.assertEqual((self.outside / "mod.py").read_text(encoding="utf-8"),
                         "def add(a, b):\n    return a - b\n")

    def test_a_goal_that_names_an_in_scope_file_keeps_its_reading(self) -> None:
        """A passing mention of an outside path must not steal an in-scope goal."""
        self.assertEqual(
            door._stated_paths_outside_the_root(
                f"Copy {self.outside}/calc.py to {WORK}/copy.py.", ROOT), [])

    def test_a_path_inside_the_root_is_not_reported_as_outside(self) -> None:
        self.assertEqual(door._stated_paths_outside_the_root(f"Format {WORK}/calc.py.", ROOT), [])


if __name__ == "__main__":
    unittest.main()
