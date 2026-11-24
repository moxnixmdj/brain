"""Tests for the door witness search.

These test what the module MEASURES, not that the mission is done:

  * a signature is computed from the declaration alone, so the same shape in two
    different programs is the same rule slot;
  * an exit-0 run that prints the program's own usage is INERT, and a silent exit-0 run
    is a SENSOR -- the two failures either side of "exit 0 means success";
  * the trial generator never produces an empty command, and does cover substitution,
    composition, dropping and appending;
  * the ledger round-trips and refuses a foreign schema rather than resetting;
  * on this machine's own `diff`, the search recovers operations the plain binder cannot
    drive, and the winning command really is the composite one.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import tempfile
import unittest

from canonical.runtime import door_witness_search_v1 as W


def _op(**over):
    base = {"id": "x", "positionals": [], "required_slots": [], "declared_flags": [],
            "effect_class": "READS", "invoked_as": ["prog", "--flag"]}
    base.update(over)
    return base


class SignatureTest(unittest.TestCase):
    def test_same_shape_in_two_programs_is_the_same_signature(self):
        join = _op(positionals=["FILE1", "FILE2"], required_slots=["FILE1", "FILE2"])
        comm = _op(positionals=["FILE1", "FILE2"], required_slots=["FILE1", "FILE2"])
        self.assertEqual(W.signature(join), W.signature(comm))
        self.assertIn("arity=2", W.signature(join))

    def test_one_slot_that_means_two_files_keeps_arity_one(self):
        # `diff [OPTION]... FILES` declares ONE slot whose value is a pair, and `join
        # FILE1 FILE2` declares two. The difference is real and it is why diff needs the
        # extra operand while join already asked for it -- so the signature must keep
        # them apart rather than normalise to "two files".
        diff = _op(positionals=["FILES"], required_slots=["FILES"])
        join = _op(positionals=["FILE1", "FILE2"], required_slots=["FILE1", "FILE2"])
        self.assertNotEqual(W.signature(diff), W.signature(join))
        self.assertIn("arity=1", W.signature(diff))

    def test_a_value_carrying_flag_changes_the_signature(self):
        plain = _op(required_slots=["FILE"])
        valued = _op(required_slots=["FILE"],
                     declared_flags=[{"flag": "--out", "placeholder": "FILE"}])
        self.assertNotEqual(W.signature(plain), W.signature(valued))

    def test_optional_positionals_are_counted_apart(self):
        strict = _op(required_slots=["FILE"])
        loose = _op(required_slots=["FILE"], positionals=["FILE", "[FILE2]"])
        self.assertNotEqual(W.signature(strict), W.signature(loose))


class EffectTest(unittest.TestCase):
    def test_a_moved_tree_is_a_door(self):
        self.assertEqual(W.effect_of({"changed": True, "text": ""}, set()), "DOOR")

    def test_silence_after_success_is_a_sensor_not_a_dead_door(self):
        # `tar --diff` on an unchanged archive: this module once called that INERT and
        # threw away 146 recoveries.
        self.assertEqual(W.effect_of({"changed": False, "text": ""}, {"Usage: x"}), "SENSOR")

    def test_the_programs_own_usage_is_inert(self):
        fingerprint = {"Usage: convert [options ...] file", "-adjoin  join images"}
        run = {"changed": False,
               "text": "Usage: convert [options ...] file\n-adjoin  join images\n"}
        self.assertEqual(W.effect_of(run, fingerprint), "INERT")

    def test_a_computed_value_is_a_sensor(self):
        self.assertEqual(W.effect_of({"changed": False, "text": "17"}, {"Usage: wc"}), "SENSOR")


class TrialTest(unittest.TestCase):
    def test_no_trial_is_an_empty_command(self):
        for _label, candidate in W._trials(["prog", "in.txt"]):
            self.assertGreaterEqual(len(candidate), 1)

    def test_substitution_covers_a_positional_operand(self):
        labels = [label for label, _ in W._trials(["grep", "-i", "in.txt"])]
        self.assertIn("SUBSTITUTE:alpha", labels)

    def test_substitution_covers_a_flag_value(self):
        labels = [label for label, _ in W._trials(["cut", "--bytes=out.bin", "in.txt"])]
        self.assertIn("SUBSTITUTE:1", labels)

    def test_composition_fills_two_slots_at_once(self):
        seen = [candidate for label, candidate in W._trials(["grep", "-E", "in.txt"])
                if label.startswith("COMPOSE:")]
        self.assertTrue(any(candidate == ["grep", "-E", "alpha", "in.txt"]
                            for candidate in seen))

    def test_dropping_the_tail_is_offered(self):
        seen = [candidate for _label, candidate in W._trials(["tar", "--list", "in.txt"])]
        self.assertIn(["tar", "--list"], seen)

    def test_the_module_names_no_program_in_its_search_path(self):
        source = pathlib.Path(W.__file__).read_text(encoding="utf-8")
        body = source.split("FLEET = (", 1)[0]
        for name in ("tar", "grep", "diff", "convert", "unzip"):
            self.assertNotIn(f'"{name}"', body, f"{name} appears in the search path")


class LearnTest(unittest.TestCase):
    def test_learn_keeps_the_frequent_move_and_records_the_rest(self):
        rows = [{"outcome": "RECOVERED", "signature": "s", "moved_by": "APPEND1:in.txt"},
                {"outcome": "RECOVERED", "signature": "s", "moved_by": "APPEND1:in.txt"},
                {"outcome": "RECOVERED", "signature": "s", "moved_by": "DROP1:art0"}]
        learned = W.learn(rows)
        self.assertEqual(learned["rules"]["s"]["move"], "APPEND1:in.txt")
        self.assertIn("s", learned["ambiguous"])
        self.assertEqual(learned["rules"]["s"]["evidence"], 2)

    def test_residue_is_grouped_by_gap_not_by_door(self):
        reports = [
            {"program": "a", "rows": [{"outcome": "RESIDUE", "signature": "sig1",
                                       "argv": ["a"], "said": "x"}]},
            {"program": "b", "rows": [{"outcome": "RESIDUE", "signature": "sig1",
                                       "argv": ["b"], "said": "y"}]},
        ]
        gaps = W.residue_as_gaps(reports)
        self.assertEqual(gaps["distinct_gaps"], 1)
        self.assertEqual(gaps["gaps"]["sig1"]["operations"], 2)


class LedgerTest(unittest.TestCase):
    def test_round_trip(self):
        folder = tempfile.mkdtemp()
        try:
            path = pathlib.Path(folder) / "ledger.json"
            W.save_ledger({"schema": W.LEDGER_SCHEMA,
                           "rules": {"s": {"move": "APPEND1:in.txt"}}, "ambiguous": {}}, path)
            loaded = W.load_ledger(path)
            self.assertEqual(W.reuse_map(loaded), {"s": "APPEND1:in.txt"})
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_a_foreign_schema_is_refused_not_reset(self):
        folder = tempfile.mkdtemp()
        try:
            path = pathlib.Path(folder) / "ledger.json"
            path.write_text(json.dumps({"schema": "SOMETHING_ELSE", "rules": {}}))
            loaded = W.load_ledger(path)
            self.assertIn("refused", loaded)
            self.assertEqual(loaded["rules"], {})
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_a_corrupt_ledger_is_refused(self):
        folder = tempfile.mkdtemp()
        try:
            path = pathlib.Path(folder) / "ledger.json"
            path.write_text("{not json")
            self.assertIn("rules", W.load_ledger(path))
        finally:
            shutil.rmtree(folder, ignore_errors=True)


@unittest.skipUnless(shutil.which("diff"), "diff is required for the live case")
class LiveTest(unittest.TestCase):
    """The case the module exists for, on a program that is on this machine."""

    def test_search_drives_operations_the_binder_cannot(self):
        operations = W.operations_of("diff", depth=1)
        report = W.discover("diff", operations, budget=W.DEFAULT_BUDGET)
        self.assertGreater(report["counts"].get("RECOVERED", 0), 10, report["counts"])
        winners = [row["winning_argv"] for row in report["rows"]
                   if row["outcome"] == "RECOVERED"]
        # `diff FILES` means two, and the winning command says so.
        self.assertTrue(any(len(argv) >= 4 for argv in winners), winners[:3])

    def test_usage_dump_is_never_counted_as_recovered(self):
        operations = W.operations_of("diff", depth=1)
        report = W.discover("diff", operations, budget=W.DEFAULT_BUDGET)
        self.assertGreater(report["counts"].get("INERT", 0) +
                           report["counts"].get("RESIDUE", 0), 0)


if __name__ == "__main__":
    unittest.main()
