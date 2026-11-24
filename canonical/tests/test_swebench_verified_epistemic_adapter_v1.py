"""Tests for the SWE-bench Verified predictions adapter (no harness required)."""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from canonical.tools import swebench_verified_epistemic_adapter_v1 as adapter


def _git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(cwd), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _make_repo(root: Path) -> tuple[Path, str]:
    repo = root / "demo__proj"
    repo.mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test")
    (repo / "mod.py").write_text("value = 1\n", encoding="utf-8")
    _git(repo, "add", "mod.py")
    _git(repo, "commit", "-qm", "base")
    return repo, _git(repo, "rev-parse", "HEAD")


def _instance(base: str, **extra: object) -> dict[str, object]:
    row: dict[str, object] = {
        "instance_id": "demo__proj-1",
        "repo": "demo/proj",
        "base_commit": base,
        "problem_statement": "value must be 2",
    }
    row.update(extra)
    return row


class SwebenchVerifiedEpistemicAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo, self.base = _make_repo(self.root)
        self.workdir = self.root / "work"
        self.workdir.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_one(self, solve_fn, instance=None, **kwargs):
        return adapter.solve_one(
            instance or _instance(self.base),
            solve_fn=solve_fn,
            repos_root=self.root,
            workdir=self.workdir,
            model_name="test-model",
            mode="EPISTEMIC",
            **kwargs,
        )

    def test_prediction_row_has_exactly_official_fields(self):
        row = adapter.prediction_row("django__django-11099", "diff --git a/x b/x\n", "m")
        self.assertEqual(
            row,
            {
                "instance_id": "django__django-11099",
                "model_name_or_path": "m",
                "model_patch": "diff --git a/x b/x\n",
            },
        )

    def test_mode_string_is_forwarded_and_semantics_are_stated(self):
        seen = {}

        def solver(goal, **kwargs):
            seen.update(kwargs)
            return {"pass": False, "status": "FAIL_CLOSED", "reason": "GOAL_NOT_REPRESENTED"}

        row, trace = self.run_one(solver)
        self.assertEqual(row["model_patch"], "")
        self.assertEqual(seen["mode"], "EPISTEMIC")
        self.assertEqual(trace["mode_requested"], "EPISTEMIC")
        self.assertIn("MODE_NOT_SPECIAL_CASED_BY_ENGINE:EPISTEMIC", trace["mode_semantics"])
        self.assertEqual(trace["outcome"], "NO_SOURCE_CHANGE")

    def test_adapter_never_self_grants_confinement_admission(self):
        seen = {}

        def solver(goal, **kwargs):
            seen.update(kwargs)
            return {"pass": False, "status": "FAIL_CLOSED"}

        self.run_one(solver)
        inputs = seen["inputs"]
        self.assertNotIn("confinement_admitted", inputs)
        self.assertIsNot(inputs.get("confinement_admitted"), True)

    def test_localization_is_advisory_and_ignores_answer_fields(self):
        (self.repo / "mod.py").write_text("def fix():\n    pass\n", encoding="utf-8")
        _git(self.repo, "add", "mod.py")
        _git(self.repo, "commit", "-qm", "source")
        base = _git(self.repo, "rev-parse", "HEAD")
        seen = {}

        def solver(goal, **kwargs):
            seen.update(kwargs)
            return {"pass": False, "status": "FAIL_CLOSED"}

        row, trace = self.run_one(solver, instance=_instance(
            base, problem_statement="mod.py function fix fails",
            patch="tests/answer.py gold()", test_patch="hidden.py",
            FAIL_TO_PASS=["test_gold"], hints_text="unused.py function gold",
        ))
        loc = trace["issue_localization"]
        self.assertEqual(loc["target_path"]["value"], "mod.py")
        self.assertEqual(loc["symbol"]["value"], "fix")
        self.assertEqual(loc["test_target"]["status"], "MISSING")
        self.assertNotIn("gold", json.dumps(loc))
        self.assertNotIn("target_path", seen["inputs"])
        self.assertNotIn("symbol", seen["inputs"])
        self.assertNotIn("test_target", seen["inputs"])
        self.assertNotIn("operation", seen["inputs"])
        self.assertEqual(row["model_patch"], "")

    def test_goal_does_not_contain_answer_fields(self):
        goal = adapter.render_goal(
            _instance(
                self.base,
                hints_text="public hint",
                patch="diff --git gold",
                test_patch="diff --git test",
                FAIL_TO_PASS=["test_gold"],
            ),
            include_hints=True,
        )
        self.assertIn("value must be 2", goal)
        self.assertIn("public hint", goal)
        for forbidden in ("diff --git gold", "diff --git test", "test_gold"):
            self.assertNotIn(forbidden, goal)

    def test_worktree_diff_becomes_patch_and_worktree_is_removed(self):
        def solver(goal, **kwargs):
            source = Path(kwargs["inputs"]["source_root"])
            (source / "mod.py").write_text("value = 2\n", encoding="utf-8")
            return {"pass": True, "status": "PASS__TEST", "reason": None}

        row, trace = self.run_one(solver)
        self.assertIn("diff --git", row["model_patch"])
        self.assertIn("+value = 2", row["model_patch"])
        self.assertEqual(trace["patch_source"], "WORKTREE_DIFF")
        self.assertEqual(trace["patch_check"], "ALREADY_APPLIED")
        self.assertEqual(trace["outcome"], "PATCH_EMITTED")
        self.assertEqual(list(self.workdir.glob("*__worktree")), [])

    def test_model_result_patch_is_preferred_and_verified(self):
        def solver(goal, **kwargs):
            source = Path(kwargs["inputs"]["source_root"])
            (source / "mod.py").write_text("value = 2\n", encoding="utf-8")
            patch = subprocess.run(
                ["git", "-C", str(source), "diff", "HEAD"],
                stdout=subprocess.PIPE,
                text=True,
                check=True,
            ).stdout
            return {"pass": True, "model_patch": patch}

        row, trace = self.run_one(solver)
        self.assertTrue(row["model_patch"].startswith("diff --git"))
        self.assertEqual(trace["patch_source"], "MODEL_RESULT:model_patch")
        self.assertEqual(trace["patch_check"], "ALREADY_APPLIED")

    def test_invalid_model_patch_is_rejected(self):
        def solver(goal, **kwargs):
            return {"pass": True, "model_patch": "not a unified diff"}

        row, trace = self.run_one(solver)
        self.assertEqual(row["model_patch"], "")
        self.assertEqual(trace["outcome"], "NOT_A_UNIFIED_DIFF")

    def test_solver_exception_yields_empty_patch_and_named_reason(self):
        def solver(goal, **kwargs):
            raise RuntimeError("boom")

        row, trace = self.run_one(solver)
        self.assertEqual(row["model_patch"], "")
        self.assertIn("ADAPTER_EXCEPTION:RuntimeError:boom", trace["outcome"])

    def test_bad_base_commit_fails_closed_without_calling_model(self):
        calls = []

        def solver(goal, **kwargs):
            calls.append(goal)
            return {}

        row, trace = self.run_one(solver, instance=_instance("not-a-commit"))
        self.assertEqual(row["model_patch"], "")
        self.assertEqual(calls, [])
        self.assertIn("BASE_COMMIT_INVALID", trace["outcome"])

    def test_generate_predictions_writes_every_instance(self):
        rows = [
            _instance(self.base),
            dict(_instance(self.base), instance_id="demo__proj-2"),
        ]

        def solver(goal, **kwargs):
            return {"pass": False, "status": "FAIL_CLOSED"}

        output = self.root / "predictions.jsonl"
        report = self.root / "report.jsonl"
        summary = adapter.generate_predictions(
            rows,
            solve_fn=solver,
            repos_root=self.root,
            workdir=self.workdir,
            output_path=output,
            report_path=report,
            mode="EPISTEMIC",
        )
        predictions = [json.loads(line) for line in output.read_text().splitlines()]
        traces = [json.loads(line) for line in report.read_text().splitlines()]
        self.assertEqual([row["instance_id"] for row in predictions], ["demo__proj-1", "demo__proj-2"])
        self.assertTrue(all(row["model_patch"] == "" for row in predictions))
        self.assertEqual(len(traces), 2)
        self.assertEqual(summary["counts"], {"total": 2, "skipped": 0, "patched": 0, "empty": 2})
        self.assertIn("REQUIRES_OFFICIAL_HARNESS", summary["claim"])

    def test_dataset_loader_drops_answer_fields(self):
        dataset = self.root / "dataset.jsonl"
        dataset.write_text(
            json.dumps(
                {
                    **_instance(self.base),
                    "patch": "GOLD PATCH",
                    "test_patch": "TEST PATCH",
                    "FAIL_TO_PASS": '["hidden_test"]',
                }
            )
            + "\n",
            encoding="utf-8",
        )
        rows = adapter.load_instances(dataset_path=dataset)
        self.assertEqual(
            set(rows[0]),
            {"instance_id", "problem_statement", "repo", "base_commit", "hints_text"},
        )
        self.assertNotIn("patch", json.dumps(rows))

    def test_filter_instances_smoke_test(self):
        rows = [{"instance_id": f"demo__proj-{n}"} for n in range(1, 60)]
        self.assertEqual(len(adapter.filter_instances(rows, limit=50)), 50)
        selected = adapter.filter_instances(rows, instance_ids=["demo__proj-3"])
        self.assertEqual(selected, [{"instance_id": "demo__proj-3"}])
        with self.assertRaises(adapter.AdapterError):
            adapter.filter_instances(rows, instance_ids=["missing__proj-1"])


if __name__ == "__main__":
    unittest.main()
