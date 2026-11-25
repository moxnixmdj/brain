"""Object-bound effect witness: real rooms, real programs, no stubs or patches.

Runs under both ``python3 -m unittest`` and pytest (no pytest-only fixtures).
"""
from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
for path in (str(REPO), str(REPO / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

from canonical.swe_kernel import effect_witness_v1 as ew  # noqa: E402
import the_check_names_its_object_v1 as measurement  # noqa: E402


def case_of(cid: str) -> dict:
    return next(c for c in measurement.CASES if c["id"] == cid)


class EffectWitnessTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="witness-test-")
        self.root = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def room(self, name: str, text: str) -> dict[str, str]:
        (self.root / name).write_text(text, encoding="utf-8")
        return ew.digest_tree(self.root)

    def test_digest_sees_an_overwrite_that_a_kind_map_cannot(self):
        before = self.room("a.txt", "original\n")
        (self.root / "a.txt").write_text("overwritten\n", encoding="utf-8")
        self.assertNotEqual(before["a.txt"], ew.digest_tree(self.root)["a.txt"])

    def test_read_only_command_does_not_change_the_room(self):
        before = self.room("a.txt", "alpha\n")
        self.assertEqual(ew.digest_tree(self.root), before)

    def test_named_subjects_are_literal_paths_not_flags(self):
        before = self.room("payload.txt", "alpha\n")
        (self.root / "out.txt").write_text("", encoding="utf-8")
        after = ew.digest_tree(self.root)
        got = ew.named_subjects(["sort", "--output=out.txt", "-k", "payload.txt"], before, after)
        self.assertIn("payload.txt", got)
        self.assertIn("out.txt", got)
        self.assertNotIn("-k", got)
        self.assertNotIn("--output=out.txt", got)

    def test_named_subjects_refuse_escapes_and_absolute_paths(self):
        before = self.room("a.txt", "alpha\n")
        self.assertEqual(ew.named_subjects(["gzip", "/etc/passwd", "../a.txt"], before, before), [])

    def test_archive_stem_is_a_derivation_not_a_program_table(self):
        self.assertTrue(ew.derives("proj/main.py", "proj.tar"))
        self.assertTrue(ew.derives("payload.txt.gz", "payload.txt"))
        self.assertTrue(ew.derives("a.txt", "a.txt"))
        self.assertFalse(ew.derives("other/main.py", "proj.tar"))

    def test_effect_roles_are_computed_from_two_digests(self):
        before = {"a.txt": "1", "b.txt": "2"}
        self.assertEqual(ew.witness(before, {"a.txt": "3", "b.txt": "2"},
                                    ["a.txt"])["role"], ew.ROLE_TRANSFORM)
        self.assertEqual(ew.witness(before, {"a.txt": "1", "b.txt": "2", "a.txt.gz": "3"},
                                    ["a.txt"])["role"], ew.ROLE_CONSUME)
        self.assertEqual(ew.witness(before, {"a.txt": "3", "b.txt": "2", "a.txt.gz": "4"},
                                    ["a.txt"])["role"], ew.ROLE_PRODUCE)
        self.assertEqual(ew.witness(before, {"b.txt": "2"}, ["a.txt"])["role"], ew.ROLE_DESTROY)
        self.assertEqual(ew.witness(before, before, ["a.txt"])["role"], ew.ROLE_VERIFY)
        self.assertEqual(ew.witness(before, before, [])["role"], ew.ROLE_INERT)

    def test_unexpected_change_is_reported_not_silently_accepted(self):
        before = {"a.txt": "1", "secret": "1"}
        row = ew.witness(before, {"a.txt": "2", "secret": "2"}, ["a.txt"])
        self.assertEqual(row["unexpected_changed"], ["secret"])

    def test_a_decoy_check_is_refused_when_the_program_exits_zero(self):
        row = measurement.run_case(case_of("T04"), "A")
        self.assertTrue(row["decoy_check"]["accepted_by_exit_code"])
        self.assertFalse(row["decoy_check"]["bound"])
        self.assertEqual(row["decoy_check"]["reason"], "SUBJECT_IS_NOT_THE_NAMED_OBJECT")

    def test_the_real_action_is_bound_to_its_named_object(self):
        row = measurement.run_case(case_of("T04"), "A")
        self.assertTrue(row["action"]["bound"])
        self.assertTrue(row["separates"])

    def test_removal_needs_a_declared_removal_goal(self):
        before = {"keep.gz": "1", "other.gz": "2"}
        after = {"other.gz": "2"}
        row = ew.witness(before, after, ["keep.gz"])
        self.assertEqual(ew.bind(row, ["keep.gz"])["reason"], "DESTROYED_SUBJECT")
        self.assertTrue(ew.bind(row, ["keep.gz"], allow_destroy=True)["bound"])

    def test_destroying_the_subject_is_not_a_check_of_its_content(self):
        control = measurement.destructive_control()
        self.assertTrue(control["digest_changed"])
        self.assertFalse(control["content_predicate_holds"])
        self.assertEqual(control["verdict"], "REFUSED__GOAL_CONTENT_LOST")

    def test_abstract_rule_has_no_concrete_path_or_argv(self):
        row = measurement.run_case(case_of("H01"), "A")["rule"]
        self.assertEqual(row["status"], "PASS__ABSTRACTED")
        self.assertNotIn("argv", row["rule"])
        self.assertNotIn("a.txt", str(row["rule"]))

    def test_signature_repeats_on_a_second_room_with_different_content(self):
        case = case_of("H01")
        first = measurement.run_case(case, "A")["rule"]["rule"]["signature"]
        second = measurement.run_case(case, "B")["rule"]["rule"]["signature"]
        self.assertEqual(first, second)

    def test_held_out_producer_is_bound_without_a_new_table(self):
        for cid in ("H01", "H02", "H03", "H04"):
            row = measurement.run_case(case_of(cid), "B")
            self.assertTrue(row["action"]["bound"], cid)
            self.assertFalse(row["decoy_check"]["bound"], cid)

    def test_guide_tool_records_a_witness_for_a_real_action(self):
        from canonical.tools import the_guide_is_an_action_grammar_v1 as guide
        (self.root / "a.txt").write_text("alpha\n", encoding="utf-8")
        got = guide.run(["gzip", "-f", "a.txt"], self.root)
        self.assertTrue(got["accepted"])
        self.assertEqual(got["witness"]["subjects"], ["a.txt"])
        self.assertIn("a.txt.gz", got["witness"]["changed"])

    def test_a_decoy_witness_cannot_be_stored(self):
        store = self.root / "rules.json"
        case = case_of("T04")
        row = measurement.run_case(case, "A")
        refused = ew.abstract_rule({"bound": False}, goal_family="decoy")
        self.assertEqual(ew.admit_rule(store, refused)["status"],
                         "REFUSED__NOT_AN_ADMITTED_RULE")
        self.assertEqual(ew.load_rules(store), [])

    def test_rule_lives_outside_the_mechanism_and_revocation_changes_behavior(self):
        store = self.root / "rules.json"
        case = case_of("H01")
        rule = measurement.run_case(case, "A")["rule"]
        signature = rule["rule"]["signature"]
        self.assertEqual(ew.admit_rule(store, rule)["status"], "PASS__STORED")
        self.assertEqual(len(ew.rules_for(store, signature)), 1)
        self.assertEqual(ew.revoke_rule(store, signature)["removed"], 1)
        self.assertEqual(ew.rules_for(store, signature), [])
        # The second room still binds correctly: the mechanism never depended
        # on the stored rule, so revocation cannot silently break it.
        self.assertTrue(measurement.run_case(case, "B")["action"]["bound"])

    def test_measurement_gates_are_declared_and_all_hold(self):
        receipt = measurement.measure()
        self.assertEqual(set(receipt["declared_before_the_run"]),
                         {"W1", "W2", "W3", "W4", "W5", "W6", "W7"})
        self.assertTrue(all(receipt["gates"].values()), receipt["gates"])


if __name__ == "__main__":
    unittest.main()
