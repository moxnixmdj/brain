"""A repair counts only when the failure stated it and the benchmark's own tests confirm it.

This file tests the mechanism that produced two green SWE-bench Pro instances on 2026-11-24,
and -- more importantly -- it tests the places where that mechanism must REFUSE. A repair engine
that patches everything it is shown is not a repair engine; it is a randomiser with good
publicity. Every refusal below is a case where the derived answer would have been a guess.

The law being enforced (`fix_from_the_failure_v1`, reused here rather than re-argued):

    THE FAILURE MUST STATE THE CORRECTION, AND THE WORLD MUST CONFIRM IT.

"The world" means the benchmark's own named tests, never this module's opinion. So `grade` is
tested too: a null (a test that never ran) must never be counted as a pass, because that is how
a harness reports a total failure as a success.
"""

from __future__ import annotations

import ast
import pathlib
import shutil
import sys
import tempfile
import textwrap
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import derive_from_the_failure_v1 as D  # noqa: E402


class TheFailureMustStateTheCorrection(unittest.TestCase):
    """What can be read out of an exception, and what cannot."""

    def test_an_instance_attribute_error_yields_the_class_and_the_name(self) -> None:
        out = ("E       AttributeError: 'LinuxNetwork' object has no attribute "
               "'get_locally_reachable_ips'\ntest/x.py:84: AttributeError")
        self.assertEqual(D.read_missing_member(out), ("LinuxNetwork", "get_locally_reachable_ips", False))

    def test_a_module_attribute_error_is_a_different_repair_and_is_marked_as_one(self) -> None:
        out = "AttributeError: module 'ansible.utils.vars' has no attribute 'combine_vars'"
        got = D.read_missing_member(out)
        self.assertEqual(got, ("ansible.utils.vars", "combine_vars", True))
        self.assertTrue(got[2], "a module-level name must not be written into a class")

    def test_a_failure_that_names_nothing_is_refused(self) -> None:
        """`DID NOT RAISE TypeError` states a requirement but names no symbol.

        This is the measured shape of the `check_type_dict` instance. It is derivable as an
        EDIT (a restriction of an existing body) but not as a new member, and a reader that
        returned some name here would be inventing one.
        """
        out = "E   Failed: DID NOT RAISE TypeError\ntest_x.py:35: Failed"
        self.assertIsNone(D.read_missing_member(out))

    def test_an_unrelated_traceback_is_refused(self) -> None:
        self.assertIsNone(D.read_missing_member("ValueError: something else entirely"))


class TheCallSiteIsTheInterfaceSpecification(unittest.TestCase):
    def test_parameter_names_come_from_the_call_the_test_makes(self) -> None:
        src = textwrap.dedent("""
            def test_x():
                path = 'p'
                net.get_locally_reachable_ips(path)
        """)
        self.assertEqual(D.call_signature_at(src, "get_locally_reachable_ips"), ["path"])

    def test_a_positional_literal_gets_a_neutral_name_rather_than_an_invented_one(self) -> None:
        src = "net.get_locally_reachable_ips('fake/ip')\n"
        self.assertEqual(D.call_signature_at(src, "get_locally_reachable_ips"), ["arg0"])

    def test_keyword_arguments_are_carried_as_names(self) -> None:
        self.assertEqual(D.call_signature_at("obj.f(a, sort=True)\n", "f"), ["a", "sort"])

    def test_a_bare_call_is_not_matched_because_it_names_no_owner(self) -> None:
        """`f(...)` alone cannot say which class owns `f`; matching it would write the member
        into an arbitrary class. The mechanism requires the attribute form, and this pins that."""
        self.assertIsNone(D.call_signature_at("f(a, sort=True)\n", "f"))

    def test_more_informative_call_wins_when_the_test_makes_several(self) -> None:
        """A mock setup and the real invocation both mention the name; the real one has arity."""
        src = textwrap.dedent("""
            net.get_locally_reachable_ips = Mock()
            res = net.get_locally_reachable_ips('x', 'y')
        """)
        self.assertEqual(D.call_signature_at(src, "get_locally_reachable_ips"), ["arg0", "arg1"])

    def test_an_unparsable_test_returns_none_instead_of_guessing(self) -> None:
        self.assertIsNone(D.call_signature_at("def broken(:\n", "f"))


class TheMemberLandsInTheClassTheFailureNamed(unittest.TestCase):
    def setUp(self) -> None:
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="derive_", dir=REPO / "canonical" / "astra_runtime" / "tmp"))
        self.mod = self.root / "lib" / "mod.py"
        self.mod.parent.mkdir(parents=True)
        self.mod.write_text(textwrap.dedent("""
            class Network:
                platform = 'Linux'

                def existing(self):
                    return 1


            class Other:
                def existing(self):
                    return 2
        """).lstrip(), encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_the_named_class_is_found_and_the_other_one_is_not_used(self) -> None:
        path, cls, indent, end = D.locate_class(self.root, "Network")
        self.assertEqual(path, self.mod)
        self.assertEqual(cls, "Network")
        self.assertEqual(indent, "    ")

    def test_appending_a_member_keeps_the_file_parsable_and_the_member_in_the_right_class(self) -> None:
        path, cls, indent, end = D.locate_class(self.root, "Network")
        ok = D.append_member(path, indent, end, "added", ["ip_path"], ["return ip_path"])
        self.assertTrue(ok)
        tree = ast.parse(self.mod.read_text(encoding="utf-8"))
        net = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Network")
        names = {m.name for m in net.body if isinstance(m, ast.FunctionDef)}
        self.assertIn("added", names)
        other = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Other")
        self.assertNotIn("added", {m.name for m in other.body if isinstance(m, ast.FunctionDef)})

    def test_the_derived_member_accepts_the_arguments_the_call_site_supplied(self) -> None:
        src = textwrap.dedent("""
            class Network:
                def existing(self):
                    return 1
        """).lstrip()
        self.mod.write_text(src, encoding="utf-8")
        path, _, indent, end = D.locate_class(self.root, "Network")
        D.append_member(path, indent, end, "get_locally_reachable_ips", ["arg0"],
                        ["return {'ipv4': [], 'ipv6': []}"])
        ns: dict = {}
        exec(compile(self.mod.read_text(encoding="utf-8"), "mod", "exec"), ns)  # noqa: S102
        got = ns["Network"]().get_locally_reachable_ips("fake/ip")
        self.assertEqual(got, {"ipv4": [], "ipv6": []})

    def test_a_missing_class_is_reported_rather_than_created(self) -> None:
        self.assertIsNone(D.locate_class(self.root, "DoesNotExist"))

    def test_an_edit_that_would_not_parse_is_refused_and_the_file_is_untouched(self) -> None:
        path, _, indent, end = D.locate_class(self.root, "Network")
        before = self.mod.read_text(encoding="utf-8")
        ok = D.append_member(path, indent, end, "bad", [], ["if True:  # no body"])
        self.assertFalse(ok)
        self.assertEqual(self.mod.read_text(encoding="utf-8"), before,
                         "a refused edit must not leave a half-written file")


class TheVerdictComesFromTheBenchmarkTests(unittest.TestCase):
    """`grade_named_tests` is the only authority. It must count what ran, and nothing else."""

    def setUp(self) -> None:
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="grade_", dir=REPO / "canonical" / "astra_runtime" / "tmp"))
        (self.root / "test_s.py").write_text(textwrap.dedent("""
            def test_good():
                assert True

            def test_bad():
                assert False
        """), encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_a_f2p_that_passes_and_a_p2p_that_passes_resolve(self) -> None:
        rep = D.grade_named_tests(self.root, ["test_s.py::test_good"], ["test_s.py::test_good"])
        self.assertTrue(rep["resolved"])
        self.assertEqual(rep["unseen"], [])

    def test_a_failing_p2p_blocks_resolution_even_when_f2p_passes(self) -> None:
        """The regression guard. An edit that fixes one test by breaking another is not a repair."""
        rep = D.grade_named_tests(self.root, ["test_s.py::test_good"], ["test_s.py::test_bad"])
        self.assertTrue(rep["f2p_passed"])
        self.assertFalse(rep["p2p_passed"])
        self.assertFalse(rep["resolved"])

    def test_a_test_that_never_ran_is_unseen_and_never_resolves(self) -> None:
        rep = D.grade_named_tests(self.root, ["test_s.py::test_absent"], [])
        self.assertFalse(rep["resolved"])
        self.assertEqual(rep["unseen"], ["test_s.py::test_absent"])

    def test_the_contract_is_read_with_literal_eval_so_quoted_names_survive(self) -> None:
        """Test ids contain apostrophes; string-replacing quotes corrupts them (measured)."""
        meta = self.root / "meta"
        meta.mkdir()
        # Written with json.dumps so this fixture cannot itself be the malformed thing it is
        # meant to test. The *stored value* is a python-repr list containing an apostrophe.
        import json as _json
        (meta / "config.json").write_text(
            _json.dumps({"fail_to_pass": "['a.py::T::test_it\\'s']", "pass_to_pass": "[]"}),
            encoding="utf-8")
        got = D.load_contract(meta)
        self.assertEqual(got["fail_to_pass"], ["a.py::T::test_it's"])


if __name__ == "__main__":
    unittest.main()
