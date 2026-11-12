"""Tests for `canonical/swe_kernel/swe_self_improvement_bridge_v1.py`."""
from __future__ import annotations

import json
import pathlib
import tempfile

from canonical.runtime import autonomous_verified_self_improvement_v1 as self_improvement
from canonical.swe_kernel.swe_self_improvement_bridge_v1 import (
    SCHEMA,
    execute_swe_coding_episode,
    main,
    make_python_unittest_verifier,
    run_swe_bridge_experiment,
)


def test_swe_bridge_experiment_all_checks_pass() -> None:
    report = run_swe_bridge_experiment()
    assert report["schema"] == SCHEMA
    assert report["all_ok"] is True, report
    assert all(report["checks"].values()), report["checks"]
    assert report["truth"] == {"achieved": False}
    admitted = report["episodes"]["ep_swe_2"]["admitted_skill_id"]
    reused = report["episodes"]["ep_swe_3"]["reused_skill_id"]
    assert isinstance(admitted, str) and admitted.startswith("skill:")
    assert admitted == reused


def test_unittest_verifier_distinguishes_failing_and_passing_candidates() -> None:
    v = make_python_unittest_verifier(
        "import unittest\nfrom target_mod import inc\n"
        "class T(unittest.TestCase):\n"
        "    def test_inc(self): self.assertEqual(inc(3), 4)\n",
        scope_id="unit_scope",
    )
    bad = v("def inc(x):\n    return x - 1\n")
    assert bad.passed is False
    assert bad.evidence["test_count"] == 1
    assert bad.evidence["returncode"] != 0

    good = v("def inc(x):\n    return x + 1\n")
    assert good.passed is True
    assert good.evidence["test_count"] == 1
    assert good.evidence["returncode"] == 0


def test_end_to_end_teaching_induction_and_unseen_transfer() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        state_path = root / "state.json"
        db_path = root / "skills.sqlite"

        ep1 = execute_swe_coding_episode(
            workspace_root=root,
            state_path=state_path,
            skill_db_path=db_path,
            episode_id="ep_1",
            scope_id="scope_1",
            before_code="def add_tax(val):\n    return val - val // 5\n",
            candidate_after_code="def add_tax(val):\n    return val + val // 5\n",
            test_code=(
                "import unittest\nfrom target_mod import add_tax\n"
                "class T(unittest.TestCase):\n"
                "    def test_a(self): self.assertEqual(add_tax(100), 120)\n"
                "    def test_b(self): self.assertEqual(add_tax(0), 0)\n"
            ),
        )
        assert ep1["pass"] is True

        ep2 = execute_swe_coding_episode(
            workspace_root=root,
            state_path=state_path,
            skill_db_path=db_path,
            episode_id="ep_2",
            scope_id="scope_2",
            before_code="def add_surcharge(base):\n    return base - base // 5\n",
            candidate_after_code=None,
            test_code=(
                "import unittest\nfrom target_mod import add_surcharge\n"
                "class T(unittest.TestCase):\n"
                "    def test_a(self): self.assertEqual(add_surcharge(50), 60)\n"
                "    def test_b(self): self.assertEqual(add_surcharge(25), 30)\n"
            ),
        )
        assert ep2["pass"] is True
        admitted_sid = ep2["self_improvement_output"]["learning"]["active_skill_id"]
        assert isinstance(admitted_sid, str) and admitted_sid.startswith("skill:")

        ep3 = execute_swe_coding_episode(
            workspace_root=root,
            state_path=state_path,
            skill_db_path=db_path,
            episode_id="ep_3",
            scope_id="scope_3",
            before_code="def gross_up(amount):\n    return amount - amount // 5\n",
            candidate_after_code=None,
            test_code=(
                "import unittest\nfrom target_mod import gross_up\n"
                "class T(unittest.TestCase):\n"
                "    def test_a(self): self.assertEqual(gross_up(200), 240)\n"
                "    def test_b(self): self.assertEqual(gross_up(15), 18)\n"
            ),
        )
        assert ep3["pass"] is True
        assert ep3["reuse_first"] is True
        assert ep3["reused_skill_id"] == admitted_sid
        assert ep3["fallback_used"] is False

        state = self_improvement.load_state(state_path)
        assert state["stats"]["verified_episode_count"] == 3
        assert state["stats"]["active_skill_count"] == 1
        assert state["reuse"][admitted_sid]["successes"] == 1


def test_cli_json_entrypoint(capsys) -> None:
    rc = main(["--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["all_ok"] is True
