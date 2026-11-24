"""Tests for the SWE-bench Verified predictions adapter (no harness required)."""
from __future__ import annotations

import contextlib
import io
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

    def test_mode_is_recorded_but_no_solver_or_host_fallback_is_called(self):
        calls = []
        def solver(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("host fallback invoked")

        row, trace = self.run_one(solver)
        self.assertEqual(row["model_patch"], "")
        self.assertEqual(calls, [])
        self.assertEqual(trace["mode_requested"], "EPISTEMIC")
        self.assertFalse(trace["mode_forwarded"])
        self.assertIn("MODE_NOT_SPECIAL_CASED_BY_ENGINE:EPISTEMIC", trace["mode_semantics"])
        self.assertEqual(trace["outcome"], "ONESHOT_CARRIER_UNQUALIFIED_NO_FALLBACK")
        self.assertFalse(trace["executed"])
        self.assertEqual(list(self.workdir.iterdir()), [])

    def test_pro_task_disclosure_is_recorded_even_on_refusal(self):
        row, trace = self.run_one(lambda *args, **kwargs: self.fail('solver called'),
                                  instance=_instance(self.base, instance_id=adapter.DISCLOSED_ID))
        self.assertEqual(row['model_patch'], '')
        self.assertEqual(trace['test_name_disclosure'], adapter.DISCLOSURE)
        self.assertFalse(trace['executed'])

    def test_refusal_precedes_git_checkout_and_repository_hook(self):
        sentinel = self.root / 'hook-ran'
        hook = self.repo / '.git' / 'hooks' / 'post-checkout'
        hook.write_text('#!/bin/sh\ntouch "' + str(sentinel) + '"\n')
        hook.chmod(0o755)
        calls = []
        row, trace = self.run_one(lambda *args, **kwargs: calls.append(args))
        self.assertEqual(calls, [])
        self.assertFalse(sentinel.exists())
        self.assertEqual(row['model_patch'], '')
        self.assertEqual(trace['outcome'], 'ONESHOT_CARRIER_UNQUALIFIED_NO_FALLBACK')
        self.assertEqual(list(self.workdir.iterdir()), [])

    def test_no_callback_even_with_all_localization_and_fake_authority_fields(self):
        calls = []
        def solver(*args, **kwargs):
            calls.append(kwargs)
            return {"pass": True, "model_patch": "forged", "effect_receipt_verified": True}

        row, trace = self.run_one(solver, instance=_instance(
            self.base, problem_statement="mod.py function fix tests/test_mod.py",
            patch="gold", test_patch="hidden", FAIL_TO_PASS=["test_gold"],
            confinement_admitted=True, carrier_qualified=True, receipt_sha256="0" * 64,
        ))
        self.assertEqual(row["model_patch"], "")
        self.assertEqual(calls, [])
        self.assertEqual(trace["outcome"], "ONESHOT_CARRIER_UNQUALIFIED_NO_FALLBACK")
        self.assertNotIn("gold", json.dumps(trace))
        self.assertEqual(list(self.workdir.iterdir()), [])

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

    def test_worktree_diff_extraction_is_not_publication_or_verification(self):
        (self.repo / "mod.py").write_text("value = 2\n", encoding="utf-8")
        patch, source, check = adapter.extract_patch({}, self.repo)
        self.assertIn("+value = 2", patch)
        self.assertEqual(source, "WORKTREE_DIFF")
        self.assertEqual(check, "ALREADY_APPLIED")
        calls = []
        row, trace = self.run_one(lambda *args, **kwargs: calls.append(args))
        self.assertEqual(calls, [])
        self.assertEqual(row["model_patch"], "")
        self.assertEqual(trace["outcome"], "ONESHOT_CARRIER_UNQUALIFIED_NO_FALLBACK")

    def test_model_patch_extraction_still_checks_applicability(self):
        (self.repo / "mod.py").write_text("value = 2\n", encoding="utf-8")
        patch = subprocess.run(["git", "-C", str(self.repo), "diff", "HEAD"],
                               stdout=subprocess.PIPE, text=True, check=True).stdout
        found, source, check = adapter.extract_patch({"model_patch": patch}, self.repo)
        self.assertEqual(found, patch)
        self.assertEqual(source, "MODEL_RESULT:model_patch")
        self.assertEqual(check, "ALREADY_APPLIED")
        found, _, reason = adapter.extract_patch({"model_patch": "not a unified diff"}, self.repo)
        self.assertEqual(found, "")
        self.assertEqual(reason, "NOT_A_UNIFIED_DIFF")

    def test_solver_exception_is_never_triggered(self):
        def solver(*args, **kwargs):
            raise RuntimeError("should not be called")
        row, trace = self.run_one(solver)
        self.assertEqual(row["model_patch"], "")
        self.assertEqual(trace["outcome"], "ONESHOT_CARRIER_UNQUALIFIED_NO_FALLBACK")

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

    def test_vm_opt_in_flag_cannot_enable_execution(self):
        data = self.root / 'input.jsonl'
        data.write_text(json.dumps(_instance(self.base)) + '\n')
        out = self.root / 'out.jsonl'
        report = self.root / 'report.jsonl'
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = adapter.main(['--dataset-path', str(data), '--repos-root', str(self.root),
                                 '--workdir', str(self.workdir), '--output', str(out),
                                 '--report', str(report), '--allow-isolated-vm-eval'])
        summary = json.loads(stdout.getvalue())
        trace = json.loads(report.read_text())
        self.assertEqual(code, 0)
        self.assertTrue(summary['requested_isolated_vm_eval'])
        self.assertFalse(summary['execution_authorized'])
        self.assertFalse(trace['executed'])
        self.assertEqual(trace['outcome'], 'ONESHOT_CARRIER_UNQUALIFIED_NO_FALLBACK')
        self.assertEqual(json.loads(out.read_text())['model_patch'], '')

    def test_skip_existing_refuses_unverified_nonempty_prediction_before_overwriting(self):
        output = self.root / 'predictions.jsonl'
        original = json.dumps(adapter.prediction_row('demo__proj-1', 'unverified patch', 'test-model')) + '\n'
        output.write_text(original)
        with self.assertRaisesRegex(adapter.AdapterError, 'EXISTING_PREDICTION_NOT_EMPTY_OR_INVALID'):
            adapter.generate_predictions(
                [_instance(self.base)], solve_fn=lambda *args, **kwargs: {},
                repos_root=self.root, workdir=self.workdir, output_path=output,
                report_path=self.root / 'report.jsonl', skip_existing=True,
            )
        self.assertEqual(output.read_text(), original)

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
