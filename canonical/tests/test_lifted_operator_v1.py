#!/usr/bin/env python3
"""Tests for the lifted operator: the durable unit is a contract, not a spelling.

The transfer tests use a real directory and a real gzip, because the claim under
test is that a program can be found and re-verified in a world that spells its
actions differently.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import effect_oracle_v1 as oracle
from canonical.runtime import lifted_operator_v1 as lifted

HAS_GZIP = shutil.which("gzip") is not None


class Env:
    """A directory with named actions -- the smallest thing a rule can bind to."""

    def __init__(self, root, vocabulary, program="gzip"):
        self.root = pathlib.Path(root)
        self._names = list(vocabulary)
        self._program = program

    @property
    def action_names(self):
        return list(self._names)

    def act(self, name):
        if name not in self._names:
            return False
        source = pathlib.Path(self.root) / "input.txt"
        done = subprocess.run([self._program, "-c", str(source)],
                              capture_output=True)
        if done.returncode != 0:
            return False
        (pathlib.Path(self.root) / "out.gz").write_bytes(done.stdout)
        return True

    def reset(self):
        pass

    def state(self):
        return ",".join(sorted(p.name for p in pathlib.Path(self.root).iterdir()))


def _rule(**over):
    base = dict(goal="compress the input into out.gz",
                goal_family="compress_to_named_file", env_kind="posix_dir",
                action="run_gzip", program=None, observation={},
                source_name="input.txt", output_name="out.gz")
    base.update(over)
    return lifted.lift(**base)


class NamingTests(unittest.TestCase):
    def test_the_program_is_derived_from_the_name_and_the_machine(self):
        self.assertEqual(lifted._program_of("run_gzip"), "gzip")
        self.assertEqual(lifted._program_of("pack_with_gzip"), "gzip")

    def test_a_name_that_resolves_to_no_program_yields_nothing(self):
        self.assertIsNone(lifted._program_of("alpha"))

    def test_a_rule_without_a_program_cannot_be_bound(self):
        rule = _rule(action="alpha")
        rule["program"] = None
        found = lifted.find_action(rule, ["alpha", "beta"])
        self.assertIsNone(found["action"])
        self.assertEqual(found["status"], lifted.REFUSED_NO_ACTION)


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="lift-test-"))

    def test_one_input_is_the_input(self):
        (self.root / "report.txt").write_bytes(b"x")
        bound = lifted.bind_source({"output_name": "out.gz"}, self.root)
        self.assertEqual(bound["bound"], "report.txt")

    def test_two_candidates_are_refused_rather_than_guessed(self):
        (self.root / "a.txt").write_bytes(b"x")
        (self.root / "b.txt").write_bytes(b"y")
        bound = lifted.bind_source({"output_name": "out.gz"}, self.root)
        self.assertIsNone(bound["bound"])
        self.assertEqual(bound["status"], lifted.REFUSED_AMBIGUOUS)

    def test_no_input_is_a_missing_precondition(self):
        bound = lifted.bind_source({"output_name": "out.gz"}, self.root)
        self.assertEqual(bound["status"], lifted.REFUSED_PRECONDITION)


class TransferTests(unittest.TestCase):
    def setUp(self):
        if not HAS_GZIP:
            self.skipTest("gzip is not on this machine")
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="lift-transfer-"))
        (self.root / "input.txt").write_bytes(b"transfer me\n")

    def test_a_renamed_vocabulary_is_bound_and_the_effect_re_verified_here(self):
        rule = _rule()
        self.assertEqual(rule["program"], "gzip")
        env = Env(self.root, ["pack_with_gzip", "pack_with_xz"])
        out = lifted.apply_rule(rule, env)
        self.assertTrue(out["applied"], out)
        self.assertEqual(out["action_used"], "pack_with_gzip")
        self.assertEqual(out["effect"]["verdict"], "EFFECT_VERIFIED")

    def test_a_vocabulary_that_names_nothing_refuses_honestly(self):
        rule = _rule()
        env = Env(self.root, ["alpha", "beta"])
        out = lifted.apply_rule(rule, env)
        self.assertFalse(out["applied"])
        self.assertEqual(out["status"], lifted.REFUSED_NO_ACTION)

    def test_a_rule_whose_program_writes_the_wrong_format_is_refuted(self):
        """The action exists, the file appears, and the effect is still wrong."""
        rule = _rule(program="xz")
        env = Env(self.root, ["run_xz"], program="xz")
        out = lifted.apply_rule(rule, env)
        self.assertFalse(out["applied"])
        self.assertEqual(out["status"], lifted.REFUTED)
        self.assertEqual(out["effect"]["verdict"], "WRONG_FORMAT__READER_REFUSED_THE_ARTIFACT")

    def test_a_refutation_is_recorded_and_the_rule_is_kept(self):
        rule = _rule()
        memory = {"schema": "x", "rules": [rule], "priors": {}}
        after = lifted.refute(memory, rule["rule_id"])
        self.assertEqual(len(after["rules"]), 1, "a refuted rule must not be deleted")
        self.assertEqual(after["rules"][0]["refutations"], 1)


if __name__ == "__main__":
    unittest.main()


class CompositionTests(unittest.TestCase):
    """Two proven contracts, one format neither of them makes."""

    class Env:
        def __init__(self, root):
            self.root = pathlib.Path(root)

        def reset(self):
            pass

    def setUp(self):
        if not (HAS_GZIP and shutil.which("tar")):
            self.skipTest("gzip and tar are both needed")
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="compose-test-"))
        (self.root / "input.txt").write_bytes(b"compose me\n" * 3)

    def _tar(self):
        return lifted.lift(goal="archive the input into out.tar", goal_family="archive",
                           env_kind="posix_dir", action="run_tar", program="tar",
                           observation={}, source_name="input.txt",
                           output_name="out.tar",
                           argv=["tar", "-cf", "{output}", "{source}"])

    def _gz(self, output="out.tar.gz"):
        return lifted.lift(goal="compress the input into %s" % output,
                           goal_family="compress", env_kind="posix_dir",
                           action="run_gzip", program="gzip", observation={},
                           source_name="input.txt", output_name=output,
                           argv=["gzip", "-c", "{source}"])

    def test_two_contracts_compose_into_a_verified_new_format(self):
        result = lifted.compose(self._tar(), self._gz(), env=self.Env(self.root),
                                intermediate="out.tar")
        self.assertTrue(result["applied"], result)
        self.assertEqual(result["status"], lifted.COMPOSED)
        self.assertEqual(result["effect"]["reader_chain"], ["gzip", "tar"])
        self.assertEqual(len(result["rule"]["composed_of"]), 2)

    def test_a_stream_program_is_carried_to_a_file_not_lost(self):
        result = lifted.compose(self._tar(), self._gz(), env=self.Env(self.root),
                                intermediate="out.tar")
        captured = [row for row in result["runs"] if row.get("captured_stdout")]
        self.assertEqual(len(captured), 1,
                         "the gzip step prints; without capture the second layer "
                         "would vanish and look like a format failure")

    def test_a_contract_without_a_shape_cannot_be_composed(self):
        bare = self._gz()
        bare["argv_shape"] = []
        result = lifted.compose(self._tar(), bare, env=self.Env(self.root))
        self.assertFalse(result["applied"])
        self.assertEqual(result["status"], lifted.COMPOSE_NO_SHAPES)

    def test_a_wrong_composition_is_refuted_by_the_chain_oracle(self):
        broken = self._tar()
        broken["argv_shape"] = ["gzip", "-c", "{source}"]  # gzip where tar belongs
        result = lifted.compose(broken, self._gz(), env=self.Env(self.root),
                                intermediate="out.tar")
        self.assertFalse(result["applied"])
        self.assertIn(result["status"], (lifted.COMPOSE_NO_EFFECT,))


class ChainCompositionTests(unittest.TestCase):
    """Any number of layers, in the order the name declares them."""

    class Env:
        def __init__(self, root):
            self.root = pathlib.Path(root)

        def reset(self):
            pass

    def setUp(self):
        if not all(shutil.which(p) for p in ("tar", "gzip", "xz")):
            self.skipTest("tar, gzip and xz are all needed")
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="chain3-test-"))
        (self.root / "input.txt").write_bytes(b"three layers deep\n" * 2)

    def _op(self, program, out, argv):
        return lifted.lift(goal="pack into %s" % out, goal_family="pack",
                           env_kind="posix_dir", action=program, program=program,
                           observation={}, source_name="input.txt",
                           output_name=out, argv=argv)

    def _three(self):
        return [self._op("tar", "out.tar", ["tar", "-c", "{source}"]),
                self._op("gzip", "out.tar.gz", ["gzip", "-c", "{source}"]),
                self._op("xz", "out.tar.gz.xz", ["xz", "-c", "{source}"])]

    def test_three_contracts_fold_into_the_format_the_name_claims(self):
        result = lifted.compose_chain(self._three(), env=self.Env(self.root),
                                      output="out.tar.gz.xz")
        self.assertTrue(result["applied"], result)
        self.assertEqual(result["effect"]["reader_chain"], ["xz", "gzip", "tar"])
        self.assertEqual(result["layers"], ["tar", "gzip", "xz"])
        self.assertEqual(len(result["rule"]["composed_of"]), 3)

    def test_the_middle_layers_are_real_files_not_placeholders(self):
        result = lifted.compose_chain(self._three(), env=self.Env(self.root),
                                      output="out.tar.gz.xz",
                                      intermediates=["out.tar", "out.tar.gz"])
        names = [row["argv"][-1] for row in result["runs"]]
        self.assertEqual(names, ["input.txt", "out.tar", "out.tar.gz"])
        self.assertTrue((self.root / "out.tar").is_file())

    def test_one_link_that_does_not_carry_the_format_refutes_the_chain(self):
        broken = self._three()
        broken[1]["argv_shape"] = ["tar", "-c", "{source}"]  # tar where gzip belongs
        result = lifted.compose_chain(broken, env=self.Env(self.root),
                                      output="out.tar.gz.xz")
        self.assertFalse(result["applied"])
        self.assertNotEqual(result["status"], lifted.COMPOSED)

    def test_a_layer_with_no_shape_stops_the_fold_before_it_runs(self):
        broken = self._three()
        broken[2]["argv_shape"] = []
        result = lifted.compose_chain(broken, env=self.Env(self.root),
                                      output="out.tar.gz.xz")
        self.assertEqual(result["status"], lifted.COMPOSE_NO_SHAPES)
        self.assertFalse((self.root / "out.tar").exists(),
                         "nothing may run when a layer has no shape")


class TheStoreSatisfiesANewNameTests(unittest.TestCase):
    """A stored contract is not tied to the file name it was taught with."""

    class Env:
        def __init__(self, root):
            self.root = pathlib.Path(root)

        def reset(self):
            pass

    def setUp(self):
        if not HAS_GZIP:
            self.skipTest("gzip is needed")
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="new-name-"))
        (self.root / "report.txt").write_bytes(b"a name never taught\n")

    def _store(self):
        operator = lifted.lift(goal="compress the input into out.gz",
                               goal_family="compress", env_kind="posix_dir",
                               action="run_gzip", program="gzip", observation={},
                               source_name="input.txt", output_name="out.gz",
                               argv=["gzip", "-c", "{source}"])
        return {"rules": [operator]}

    def test_a_single_contract_serves_an_output_name_it_never_saw(self):
        from canonical.swe_kernel import perfect_algorithm_v1 as pa

        result = pa._compose_from_store(
            self._store(), self.Env(self.root), "pack the input into backup.gz",
            contract=lambda env: {"source": "report.txt", "output": "backup.gz"})
        self.assertTrue(result.get("applied"), result)
        self.assertEqual(result["layers"], ["gzip"])
        self.assertEqual(result["runs"][0]["argv"], ["gzip", "-c", "report.txt"])

    def test_the_effect_is_verified_under_the_new_name(self):
        from canonical.swe_kernel import perfect_algorithm_v1 as pa

        pa._compose_from_store(
            self._store(), self.Env(self.root), "pack the input into backup.gz",
            contract=lambda env: {"source": "report.txt", "output": "backup.gz"})
        verdict = oracle.verify_roundtrip(self.root, "backup.gz", "report.txt")
        self.assertEqual(verdict["verdict"], oracle.EFFECT_VERIFIED, verdict)
