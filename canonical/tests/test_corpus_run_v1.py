"""Local fixture exercises are replayable, but are not verified corpus admissions."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import corpus_run_20261112 as corpus  # noqa: E402


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    shutil.copytree(ROOT / corpus.FIXTURE, tmp_path / corpus.FIXTURE)
    monkeypatch.setattr(corpus, "REPO_ROOT", tmp_path)
    return tmp_path


@pytest.fixture
def exercise(workspace):
    report = corpus.run()
    records = [json.loads(path.read_text()) for path in sorted(
        (workspace / corpus.RECORD_DIR).glob("INSTANCE__*__RECORD.json"))]
    return report, records


def test_two_exercises_keep_pre_edit_inputs(workspace, exercise):
    report, records = exercise
    assert report["tasks"] == report["records_with_inputs"] == 2
    assert report["input_files_recorded"] == 8
    assert len(records) == 2
    for record in records:
        assert record["input_count"] == 4
        for name, digest in record["input_digests"].items():
            blob = (workspace / corpus.STORE / f"{digest}.bin").read_bytes()
            assert hashlib.sha256(blob).hexdigest() == digest
            assert blob == (workspace / corpus.FIXTURE / name).read_bytes()
        assert record["input_digests"] != record["output_digests"]
    assert len(list((workspace / corpus.STORE).glob("*.bin"))) == 4


def test_effect_and_red_baseline_are_measured_not_promoted(exercise):
    report, records = exercise
    assert report["postconditions_holding"] == report["baseline_preserved"] == 2
    assert report["independently_verified_instances"] == 0
    for record in records:
        assert record["observed"]["gate"] == "PASS_BLIND"
        assert record["postcondition"]["checked_by"] == "runner_ast_postcondition"
        assert record["postcondition"]["independent"] is False
        assert record["independently_verified"] is False
        assert record["independent_verifier"] is None
        assert record["baseline_tests"] == record["post_edit_tests"] == {
            "tests_run": 2, "failures": ["test_calc.CalcTests.test_twice_uses_add"],
            "errors": [], "skipped": []}


def test_replay_needs_no_original_fixture(workspace):
    task = corpus.TASKS[0]
    where = workspace / corpus.SCRATCH
    first = corpus.run_task(task, where)
    shutil.rmtree(where / task["id"])
    shutil.rmtree(workspace / corpus.FIXTURE)
    replay = corpus.run_task(task, where, saved_inputs=first["input_digests"])
    for key in ("input_digests", "output_digests", "result_sha256", "post_edit_tests"):
        assert replay[key] == first[key]


def test_replays_match_and_limits_are_explicit(exercise):
    report, records = exercise
    assert report["replayed_identically"] == 2
    for record in records:
        assert record["result_sha256"] == record["replay_result_sha256"]
    assert any("NOT_PRODUCTION_WORK" in limit for limit in report["what_this_is_not"])
    assert any("NOT_A_LEARNING_UPDATE" in limit for limit in report["what_this_is_not"])
    assert report["model_dependency_count"] == 0


def test_missing_or_corrupt_snapshot_fails_closed(workspace):
    task = corpus.TASKS[0]
    where = workspace / corpus.SCRATCH
    first = corpus.run_task(task, where)
    digest = first["input_digests"]["calc.py"]
    blob = workspace / corpus.STORE / f"{digest}.bin"
    blob.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="SNAPSHOT_DIGEST_MISMATCH"):
        corpus.run_task(task, where, saved_inputs=first["input_digests"])
    blob.unlink()
    with pytest.raises(FileNotFoundError):
        corpus.run_task(task, where, saved_inputs=first["input_digests"])


def test_postcondition_rejects_stale_import(workspace):
    task = corpus.TASKS[1]
    where = workspace / corpus.SCRATCH
    result = corpus.run_task(task, where)
    assert result["postcondition"]["holds"] is True
    scratch = where / task["id"]
    (scratch / "test_calc.py").write_text("from util import twice\n")
    assert corpus.postcondition(scratch, task)["holds"] is False


def test_snapshot_cannot_escape_workspace(workspace):
    with pytest.raises(ValueError, match="SNAPSHOT_PATH_ESCAPE"):
        corpus._restore_inputs(workspace / "scratch", {"../outside": "a" * 64})
