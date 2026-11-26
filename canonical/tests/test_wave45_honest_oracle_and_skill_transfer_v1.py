#!/usr/bin/env python3
"""Wave 45 tests: honest oracle, repair admission, skill crystallisation and transfer.

These test the four defects found and fixed on 2026-11-26, each of which was
reproduced live before being fixed:

  1. `python -m unittest test_x.py` saw only `unittest.TestCase` subclasses, so a
     plain-function suite reported green while red -> false
     `PASS__BASELINE_ALREADY_GREEN`.
  2. A stale `.pyc` made the CoW runner re-execute the pre-patch module, so a
     verified patch could never be confirmed.
  3. `SkillStoreV2` persisted a memory address as a hole witness
     (`<ast.If object at 0x7f...>`), so no morphism could ever replay -- not
     even on its own witness -- and `learned_skill_id` was always `None` for
     multi-statement fixes.
  4. A suite-green patch that hardcoded a test literal (`and 'bob'`) was
     accepted as a repair.
"""
from __future__ import annotations

import ast
import pathlib
import tempfile
import unittest

from canonical.swe_kernel import repair_admission_v1 as admission
from canonical.swe_kernel.causal_nexus_v1 import SkillStoreV2
from canonical.swe_kernel.stdlib_cow_test_runner_v1 import run_targets_cow_fork

GUARD_SRC = 'def get_name(user):\n    if user is None:\n        return None\n    return user["name"]\n'
GUARD_FIX = 'def get_name(user):\n    return (user or {}).get("name", "")\n'
OVERFIT = 'def get_name(user):\n    return ((user or "") and "bob")\n'


class HonestOracleTest(unittest.TestCase):
    """The oracle must see plain `def test_*` functions and never cache stale bytecode."""

    def _repo(self) -> pathlib.Path:
        root = pathlib.Path(tempfile.mkdtemp(prefix="wave45_oracle_"))
        (root / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
        (root / "test_calc.py").write_text(
            "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n",
            encoding="utf-8",
        )
        return root

    def test_plain_function_tests_are_discovered(self):
        root = self._repo()
        res = run_targets_cow_fork(root, ["test_calc.py"], timeout_s=10)
        self.assertFalse(res["ok"], "a failing plain-function suite must not report green")
        self.assertEqual(res["failed_nodeids"], ["test_calc.py::test_add"])
        self.assertIn("assert -1 == 5", res["output"])

    def test_no_stale_bytecode_after_a_fix(self):
        root = self._repo()
        self.assertFalse(run_targets_cow_fork(root, ["test_calc.py"], timeout_s=10)["ok"])
        (root / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        self.assertTrue(
            run_targets_cow_fork(root, ["test_calc.py"], timeout_s=10)["ok"],
            "after a real fix the same directory must report green, not the cached old module",
        )


class AdmissionTest(unittest.TestCase):
    """A repair may not smuggle test data into the program."""

    def test_overfit_literal_is_refused(self):
        ok, reason, evidence = admission.admits_repair(OVERFIT, GUARD_SRC)
        self.assertFalse(ok)
        self.assertEqual(reason, "TEST_LITERAL_LEAK")
        self.assertEqual(evidence["leaked"][0]["value"], "'bob'")

    def test_real_fix_is_admitted(self):
        ok, reason, _ = admission.admits_repair(GUARD_FIX, GUARD_SRC)
        self.assertTrue(ok, reason)

    def test_canonical_defaults_are_admitted(self):
        # `"name"` is the source's own key and `""` is a canonical default, so nothing new is
        # introduced. (A brand-new key would be refused, which is the gate working.)
        ok, reason, _ = admission.admits_repair(
            'def get_name(user):\n    return (user or {}).get("name", "")\n', GUARD_SRC
        )
        self.assertTrue(ok, reason)

    def test_param_amnesia_is_refused(self):
        ok, reason, _ = admission.admits_repair(
            "def get_name(user):\n    return ''\n", GUARD_SRC
        )
        self.assertFalse(ok)
        self.assertIn(reason, {"PARAM_AMNESIA", "CONSTANT_BODY"})

    def test_filter_candidates_keeps_reasons(self):
        kept, refusals = admission.filter_candidates([OVERFIT, GUARD_FIX], GUARD_SRC)
        self.assertEqual(kept, [GUARD_FIX])
        self.assertEqual(refusals[0]["reason"], "TEST_LITERAL_LEAK")


class SkillTransferTest(unittest.TestCase):
    """A verified fix must crystallise, replay, and transfer to a renamed repo."""

    def test_morphism_replays_its_own_witness(self):
        store = SkillStoreV2(pathlib.Path(tempfile.mkdtemp()) / "s.json")
        morph = store.learn(GUARD_SRC, GUARD_FIX, origin="test")
        self.assertIsNotNone(morph)
        proposals = store.propose(GUARD_SRC)
        self.assertTrue(proposals, "a stored morphism must replay on the source it was learned from")
        self.assertIn(".get(", proposals[0][1])

    def test_morphism_transfers_to_renamed_vocabulary(self):
        store = SkillStoreV2(pathlib.Path(tempfile.mkdtemp()) / "s.json")
        store.learn(GUARD_SRC, GUARD_FIX, origin="test")
        held_out = (
            'def read_nickname(rec):\n    if rec is None:\n        return None\n'
            '    return rec["nick"]\n'
        )
        proposals = store.propose(held_out)
        self.assertTrue(proposals, "the law must fire on a renamed function, parameter and key")
        out = proposals[0][1]
        self.assertIn("read_nickname", out)
        self.assertIn("'nick'", out)
        ast.parse(out)  # must remain valid Python

    def test_morphism_refuses_unrelated_code(self):
        store = SkillStoreV2(pathlib.Path(tempfile.mkdtemp()) / "s.json")
        store.learn(GUARD_SRC, GUARD_FIX, origin="test")
        self.assertEqual(store.propose("def unrelated(x):\n    return x + 1\n"), [])

    def test_store_is_removable_without_retraining(self):
        store = SkillStoreV2(pathlib.Path(tempfile.mkdtemp()) / "s.json")
        morph = store.learn(GUARD_SRC, GUARD_FIX, origin="test")
        self.assertTrue(store.remove(morph.morphism_id))
        self.assertEqual(store.propose(GUARD_SRC), [])


class EndToEndSpineTest(unittest.TestCase):
    """The front door: an untrusted correct patch is admitted, verified and crystallised."""

    def setUp(self):
        # The shared default stores are real state used by the product. A test must not write into
        # them, and a stale entry from an earlier test must not change what this test measures.
        import os

        self._tmp_home = tempfile.mkdtemp(prefix="wave45_store_")
        self._prev = {
            k: os.environ.get(k) for k in ("BRAIN_SKILL_STORE_PATH", "BRAIN_LAW_STORE_PATH")
        }
        os.environ["BRAIN_SKILL_STORE_PATH"] = str(pathlib.Path(self._tmp_home) / "store.json")
        os.environ["BRAIN_LAW_STORE_PATH"] = str(pathlib.Path(self._tmp_home) / "laws.json")

    def tearDown(self):
        import os

        for k, v in self._prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_verified_patch_is_crystallised(self):
        from canonical.runtime.brain_unified_model_v1 import open_model

        model = open_model()
        base = pathlib.Path(tempfile.mkdtemp(prefix="wave45_spine_"))
        store = base / "store.json"
        repo = base / "repo"
        repo.mkdir()
        (repo / "mod.py").write_text(GUARD_SRC, encoding="utf-8")
        (repo / "test_mod.py").write_text(
            'from mod import get_name\n\n\ndef test_none():\n    assert get_name(None) == ""\n'
            '\n\ndef test_ok():\n    assert get_name({"name": "bob"}) == "bob"\n',
            encoding="utf-8",
        )
        res = model.solve_swe_repo_native(
            str(repo),
            test_targets=["test_mod.py"],
            candidate_files=["mod.py"],
            timeout_s=30.0,
            keep_patch_applied=True,
            residual_proposer=lambda packet: [{"mod.py": GUARD_FIX}],
            skill_store_path=str(store),
        )
        swe = res.get("swe_result") or {}
        self.assertTrue(res.get("pass"), res.get("status"))
        self.assertIsNotNone(swe.get("learned_skill_id"), "multi-statement fix must crystallise")
        self.assertTrue(store.exists(), "the external store must be written")
        self.assertIn(".get(", (repo / "mod.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()


class ColdStartAdapterTest(unittest.TestCase):
    """The front door: a sentence and a repository, no structured inputs."""

    def setUp(self):
        import os

        self._prev = {k: os.environ.get(k) for k in ("BRAIN_SKILL_STORE_PATH", "BRAIN_LAW_STORE_PATH")}
        import tempfile as _tf

        self._tmp = _tf.mkdtemp(prefix="wave45_cold_")
        os.environ["BRAIN_SKILL_STORE_PATH"] = f"{self._tmp}/store.json"
        os.environ["BRAIN_LAW_STORE_PATH"] = f"{self._tmp}/laws.json"

    def tearDown(self):
        import os

        for k, v in self._prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _repo(self, name: str, files: dict[str, str]) -> pathlib.Path:
        root = pathlib.Path(self._tmp) / name
        root.mkdir(parents=True, exist_ok=True)
        for rel, text in files.items():
            (root / rel).write_text(text, encoding="utf-8")
        return root

    def test_binds_targets_and_candidates_from_evidence(self):
        from canonical.swe_kernel.cold_start_swe_adapter_v1 import solve_from_issue

        root = self._repo("bind", {
            "calc.py": "def add(a, b):\n    return a - b\n",
            "test_calc.py": "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n",
            "unrelated.py": "def rain():\n    return 1\n",
        })
        res = solve_from_issue("the addition helper subtracts", root, keep_patch_applied=True)
        self.assertEqual(res["binding"]["test_targets"], ["test_calc.py"])
        self.assertIn("calc.py", res["binding"]["candidate_files"])
        self.assertNotIn("test_calc.py", res["binding"]["candidate_files"])

    def test_no_test_file_refuses_instead_of_guessing(self):
        from canonical.swe_kernel.cold_start_swe_adapter_v1 import solve_from_issue

        root = self._repo("nooracle", {"lib.py": "def f():\n    return 1\n"})
        res = solve_from_issue("f is wrong", root)
        self.assertFalse(res["pass"])
        self.assertEqual(res["reason"], "NO_ORACLE_TARGET__NO_TEST_FILE_IN_REPO")
        self.assertEqual(res["model_calls"], 0)

    def test_missing_repo_root_fails_closed(self):
        from canonical.swe_kernel.cold_start_swe_adapter_v1 import solve_from_issue

        res = solve_from_issue("anything", "/nonexistent/path/xyz")
        self.assertFalse(res["pass"])
        self.assertEqual(res["reason"], "REPO_ROOT_MISSING")

    def test_cold_start_solves_and_reports_zero_model_calls(self):
        from canonical.runtime.brain_unified_model_v1 import open_model

        model = open_model()
        root = self._repo("solve", {
            "calc.py": "def add(a, b):\n    return a - b\n",
            "test_calc.py": "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n",
        })
        res = model.solve_swe_cold_start("addition returns the wrong answer", root, keep_patch_applied=True)
        self.assertTrue(res["pass"], res.get("status"))
        payload = res["payload"]
        self.assertEqual((payload.get("swe_result") or {}).get("model_calls"), 0)
        self.assertIn("a + b", (root / "calc.py").read_text(encoding="utf-8"))
