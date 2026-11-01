"""A refusal the adapter already named is not a controller crash.

Measured 2026-11-01 on main `6aa5dab`, 49-sentence advanced census: 13 refusals, and SEVEN of
them came back ``FAIL__LIVE_CONTROLLER_EXECUTION`` -- the status the door reserves for an adapter
that broke -- while the exception it discarded said exactly what had been read and refused:

    1 polyglot  RuntimeError:POLYGLOT_REFUSED:CPP_NO_APPLICABLE_TRANSFORM
    6 polyglot  RuntimeError:POLYGLOT_REFUSED:SQL_UNSUPPORTED_DDL_EDIT
    7 polyglot  RuntimeError:POLYGLOT_REFUSED:CPP_NO_APPLICABLE_TRANSFORM
   11 build     RuntimeError:POLYGLOT_REFUSED:PYPROJECT_ALREADY_PINNED_OR_EMPTY
   12 build     RuntimeError:POLYGLOT_REFUSED:NO_DECLARED_DEPENDENCY_TO_VENDOR
   16 ci        RuntimeError:POLYGLOT_REFUSED:NO_FLAKY_TEST_DETECTED
   33 refactor  RuntimeError:TARGET_SYMBOL_COLLISION:add

The same shape in the 18 ordinary sentences: ``DIAGNOSE_ARCHITECT_REFUSED:EXPLAIN_TARGET_FUNCTION_NOT_FOUND``
and ``NOT_A_GIT_REPOSITORY:.`` were both reported as controller executions.

The law pinned here: the door already classifies ONE spelling of an adapter refusal
(``SystemExit(json.dumps({"error": true, "reason": ...}))``); the other spelling -- the repository's
own SCREAMING_SNAKE guard key raised as ``RuntimeError`` -- is the same act and must be classified
the same way.  Nothing is invented: only a message that IS a key (optionally ``:detail``) qualifies,
so a traceback text or a free-form error keeps its crash classification, and the served count does
not move (36/49 before and after -- no pass is minted by a better failure name).
"""
from __future__ import annotations

import unittest

from canonical.runtime import live_brain_route_admission_v1 as door


class AGuardKeyIsARefusalV1(unittest.TestCase):
    def test_the_keys_the_census_measured_are_recognised(self) -> None:
        for message in (
            "POLYGLOT_REFUSED:CPP_NO_APPLICABLE_TRANSFORM",
            "POLYGLOT_REFUSED:NO_DECLARED_DEPENDENCY_TO_VENDOR",
            "TARGET_SYMBOL_COLLISION:add",
            "DIAGNOSE_ARCHITECT_REFUSED:EXPLAIN_TARGET_FUNCTION_NOT_FOUND",
            "NOT_A_GIT_REPOSITORY:.",
            "PATH_ESCAPE:../../etc/passwd",
        ):
            with self.subTest(message=message):
                self.assertTrue(door._ADAPTER_REFUSAL_KEY_RE.match(message), message)

    def test_a_crash_message_is_not_read_as_a_refusal(self) -> None:
        for message in (
            "list index out of range",
            "KeyError: 'x'",
            "Traceback (most recent call last):\n  File ...",
            "expecting property name enclosed in double quotes",
        ):
            with self.subTest(message=message):
                self.assertFalse(door._ADAPTER_REFUSAL_KEY_RE.match(message), message)

    def test_the_door_reports_a_guard_key_refusal_as_a_closed_refusal(self) -> None:
        # The one path every single-capability run passes through.  A tree with no `.git` is the
        # nearest world in which the git row refuses in this exact spelling.
        import pathlib
        import tempfile
        import shutil
        tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "pkg").mkdir()
        (tmp / "pkg" / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
        result = door.solve({"task_id": "GUARD_KEY_REFUSAL",
                             "goal": f"Show the last three git commits in {tmp}."})
        status = str(result.get("status") or "")
        self.assertFalse(status.startswith("FAIL__LIVE_CONTROLLER_EXECUTION"), status)
        if not result.get("pass"):
            self.assertTrue(status.startswith("FAIL_CLOSED__CAPABILITY_REFUSED_")
                            or status.startswith("FAIL_CLOSED__"), status)


if __name__ == "__main__":
    unittest.main()
