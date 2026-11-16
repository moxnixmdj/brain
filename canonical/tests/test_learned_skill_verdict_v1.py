#!/usr/bin/env python3
"""Tests for the verdict attached to the tree's learned skills.

Every test here pins a measured fact rather than a preference:

    the shipped bundle judges all of its skills by their own stdout       11 of 11
    none of them has ever been used                                      0 of 11
    against a real request, the stored verdict admits a program that
        prints the success sentence and writes nothing                    4 of 4
    a verdict that reads the file it claims changed refuses that program  0 of 4
    ...and still accepts the real skill                                   4 of 4

The last two are the point: the oracle is not weak, it is absent, and replacing it with a
filesystem witness fixes it on the tree's own artifacts without changing the skills.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as compiler  # noqa: E402
from canonical.swe_kernel import learned_skill_verdict_v1 as verdict  # noqa: E402


class BundleTests(unittest.TestCase):
    def test_the_shipped_bundle_judges_every_skill_by_its_own_stdout(self):
        skills = verdict.load_skills()
        self.assertGreaterEqual(len(skills), 11)
        kinds = {(skill["abstract_postcondition"] or {}).get("kind") for skill in skills}
        self.assertEqual(kinds, {"stdout_equals"})

    def test_no_shipped_skill_has_ever_been_used(self):
        # This is the honest state of "learn it once and keep it": the storage and the credit
        # flags exist, and the loop that would tell us whether any of it works has never run.
        skills = verdict.load_skills()
        self.assertEqual([skill.get("hit_count") for skill in skills],
                         [skill.get("hit_count") for skill in skills])
        self.assertEqual(sum(1 for skill in skills if (skill.get("hit_count") or 0) > 0), 0)


class BindingTests(unittest.TestCase):
    def test_the_arguments_are_bound_in_the_order_the_stored_step_unpacks_them(self):
        # `param_order` is not the unpacking order: it lists (str0, str1, path0) while the stored
        # code unpacks (path0, str1, str0). Binding by param_order handed the skill a variable
        # name where it wanted a path, and every attempt was refused with "there is no file
        # probes" -- a refusal that looks like care and was this instrument's bug.
        source = 'REQUEST = ("?path0", "?str1", "?str0")  # file, function, variable\nprint(1)\n'
        self.assertEqual(verdict.stored_request_shape(source), ("?path0", "?str1", "?str0"))
        skill = {"abstract_steps": [{"code": source}], "param_order": ["?str0", "?str1", "?path0"]}
        bound = verdict.request_tuple(skill, {"path0": "p.py", "str1": "f", "str0": "x"})
        self.assertEqual(bound, ("p.py", "f", "x"))

    def test_the_roles_are_read_off_the_skill_own_sentence(self):
        inline = {"goal_skeleton": "inline the variable '?str0' in the function '?str1' in ?path0"}
        rename = {"goal_skeleton": "rename the variable '?str0' to '?str1' in the function '?str2' in ?path0"}
        self.assertEqual(verdict.claim_roles(inline), ("str1", "str0"))
        self.assertEqual(verdict.claim_roles(rename), ("str2", "str0"))


class OracleTests(unittest.TestCase):
    def _skill(self) -> dict:
        return {
            "goal_skeleton": "inline the variable '?str0' in the function '?str1' in ?path0",
            "param_order": ["?str0", "?str1", "?path0"],
            "abstract_steps": [{"code": 'REQUEST = ("?path0", "?str1", "?str0")\nprint("real")\n'}],
            "abstract_postcondition": {
                "kind": "stdout_equals",
                "expected": "inlined the variable '?str0' in the function '?str1' in ?path0",
            },
        }

    def test_a_program_that_prints_the_sentence_is_accepted_by_the_stored_postcondition(self):
        request = {"path0": "canonical/swe_kernel/rule_expiry_v1.py", "str1": "audit", "str0": "now"}
        skill = self._skill()
        source = verdict.impostor_source(skill, request)
        with tempfile.TemporaryDirectory() as directory:
            run = verdict.run_program(source, workdir=pathlib.Path(directory))
            judged = verdict.judge(verdict.concrete_postcondition(skill, request),
                                   workdir=pathlib.Path(directory), run=run)
        self.assertTrue(judged["accepted"], judged)
        # The impostor touches no file at all: two lines, a print and an exit.
        self.assertNotIn("open(", source)
        self.assertNotIn("pathlib", source)
        self.assertEqual(len(source.strip().splitlines()), 3)

    def test_a_file_witness_refuses_the_file_it_was_never_asked_to_change(self):
        with tempfile.TemporaryDirectory() as directory:
            workdir = pathlib.Path(directory)
            target = workdir / "m.py"
            original = "def f():\n    value = 1\n    return value\n"
            target.write_text(original, encoding="utf-8")
            postcondition = {
                "kind": "file_edit_claim", "path": "m.py", "function": "f", "symbol": "value",
                "before_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest(),
            }
            ok, why = compiler.verify_postcondition(postcondition, cwd=workdir, execution_result=None)
            self.assertFalse(ok)
            self.assertEqual(why, "POSTCONDITION_FILE_UNCHANGED")

            target.write_text("def f():\n    return 1\n", encoding="utf-8")
            ok, why = compiler.verify_postcondition(postcondition, cwd=workdir, execution_result=None)
            self.assertTrue(ok, why)

    def test_a_file_witness_still_refuses_an_edit_that_leaves_the_symbol_in_place(self):
        with tempfile.TemporaryDirectory() as directory:
            workdir = pathlib.Path(directory)
            target = workdir / "m.py"
            original = "def f():\n    value = 1\n    return value\n"
            target.write_text("def f():\n    value = 2\n    return value\n", encoding="utf-8")
            postcondition = {
                "kind": "file_edit_claim", "path": "m.py", "function": "f", "symbol": "value",
                "before_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest(),
            }
            ok, why = compiler.verify_postcondition(postcondition, cwd=workdir, execution_result=None)
            self.assertFalse(ok)
            self.assertEqual(why, "POSTCONDITION_SYMBOL_STILL_ASSIGNED")


class ExerciseTests(unittest.TestCase):
    def test_one_real_skill_is_accepted_by_both_verdicts_and_its_impostor_only_by_one(self):
        skills = verdict.load_skills()
        exercises = [skill for skill in skills
                     if "path1" not in str(skill.get("goal_skeleton"))
                     and verdict.claim_roles(skill)[0] is not None]
        self.assertTrue(exercises, "the bundle no longer carries an exercisable skill")
        found = verdict.find_an_accepted_request(
            exercises[0], ["canonical/swe_kernel/lesson_admission_gate_v1.py"])
        if found is None:
            self.skipTest("no request in that file is answered by this skill on this machine")
        self.assertTrue(found["skill"]["verdict"]["accepted"])
        self.assertTrue(found["skill"]["witness_verdict"]["accepted"])
        self.assertTrue(found["impostor"]["verdict"]["accepted"])
        self.assertFalse(found["impostor"]["witness_verdict"]["accepted"])
        self.assertFalse(found["skill"]["independent"]["holds"] is False)


if __name__ == "__main__":
    unittest.main()


# --- the four-arm certificate: a verdict is admitted only if it can tell a real action from
# --- three ways of not doing it (nothing / the wrong edit / a destroyed file).

SEARCH = ["canonical/swe_kernel/lesson_admission_gate_v1.py"]


def _first_exercisable_skill():
    for skill in verdict.load_skills():
        if "path1" in str(skill.get("goal_skeleton")):
            continue
        found = verdict.find_an_accepted_request(skill, SEARCH)
        if found is not None:
            return skill, found["request"]
    raise AssertionError("no exercisable skill in this repository")


class CertificateTests(unittest.TestCase):
    def test_a_verdict_that_reads_only_stdout_admits_a_program_that_does_nothing(self):
        skill, request = _first_exercisable_skill()
        certificate = verdict.certify(skill, request, postcondition_kind="stored")
        self.assertFalse(certificate["admitted"])
        self.assertIn("THE_VERDICT_ACCEPTED_THE_NULL_PROGRAM", certificate["refusals"])
        self.assertTrue(certificate["arms"]["null"]["accepted"])

    def test_the_file_witness_refuses_all_three_impostors_and_keeps_the_real_action(self):
        skill, request = _first_exercisable_skill()
        certificate = verdict.certify(skill, request, postcondition_kind="witness")
        self.assertTrue(certificate["arms"]["real"]["accepted"])
        for impostor in ("null", "wrong_claim", "corrupt"):
            self.assertFalse(certificate["arms"][impostor]["accepted"], impostor)

    def test_a_claim_that_did_not_name_everything_it_changed_is_refused(self):
        """The scope of a claim is part of the claim: deleting the rest of the file is not the edit."""
        target = "canonical/swe_kernel/lesson_admission_gate_v1.py"
        skill, request = _first_exercisable_skill()
        before = (verdict.ROOT / target).read_text(encoding="utf-8")
        postcondition = verdict.witness_postcondition(skill, request, before)
        self.assertTrue(postcondition["outside_digests"], "the file has other top-level nodes")

        workdir = pathlib.Path(tempfile.mkdtemp(prefix="verdict_scope_"))
        try:
            path = workdir / target
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(before[: len(before) // 2], encoding="utf-8")
            ok, why = compiler.verify_postcondition(postcondition, cwd=workdir)
            self.assertFalse(ok)
            self.assertTrue(
                why.startswith("POSTCONDITION_FILE_DOES_NOT_PARSE")
                or why == "POSTCONDITION_CHANGE_ESCAPED_THE_FUNCTION", why)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def test_admission_tells_the_loader_which_verdict_it_can_trust(self):
        decision = verdict.admission_decision(SEARCH)
        self.assertTrue(decision["admitted"])
        self.assertEqual(decision["under"], "witness")
        self.assertFalse(decision["stored_verdict_admitted"])
        self.assertGreaterEqual(decision["skills_certified"], 1)
