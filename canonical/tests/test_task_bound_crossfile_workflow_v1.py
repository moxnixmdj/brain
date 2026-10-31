"""Execute the real kernels; no producer/tool mocking or historical fixtures."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from canonical.runtime.bound_capabilities import software_repair_crossfile_choreograph_v1 as crossfile
from canonical.runtime.bound_capabilities import software_patch_cegis_z3_v1 as architecture
from canonical.runtime.bound_capabilities import software_hardcore_swe_supercomposer_v1 as declarations
from canonical.runtime.swe_task_artifacts_v1 import fresh_output, publish_report

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "src/pkg").mkdir(parents=True)
    (tmp_path / "src/tests").mkdir()
    (tmp_path / "src/pkg/__init__.py").write_text("")
    (tmp_path / "src/pkg/core.py").write_text(
        "def helper(x):\n    return len(str(x).strip()) + 1\n")
    (tmp_path / "src/pkg/util.py").write_text(
        "from pkg.core import helper\n\ndef twice(x):\n    return helper(x) * 2\n")
    (tmp_path / "src/tests/test_core.py").write_text(
        "import sys, pathlib\n"
        "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))\n"
        "from pkg.core import helper\nfrom pkg.util import twice\n\n"
        "def test_behavior():\n    assert helper(' A ') == 2\n    assert twice(' A ') == 4\n")
    (tmp_path / "issue.json").write_text(json.dumps({
        "issue_id": "RENAME-1", "title": "Rename helper to compute in pkg/core.py"}))
    (tmp_path / "task.json").write_text(json.dumps({
        "issue_id": "RENAME-1", "edits": [{"op": "rename_symbol", "module": "pkg/core.py",
                                              "name": "helper", "new_name": "compute"}]}))
    return tmp_path


def run(repo, **extra):
    args = {"source_root": "src", "issue_path": "issue.json", "output_path": "out/report.json"}
    args.update(extra)
    return crossfile.run(args, repo)


def contents(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_natural_issue_executes_real_crossfile_change_and_regressions(repo):
    before = contents(repo / "src")
    result = run(repo)
    assert result["pass"] is True, result
    assert result["choreography_verified"] is True
    assert result["source_unchanged"] is True
    assert result["candidate_unchanged_during_regression"] is True
    assert result["regression"]["completed"] == 1
    assert result["regression"]["returncode"] == 0
    assert result["stages"]["test_passed_count"] == 1
    assert result["issue_binding"]["complete"] is True
    assert set(result["changed_files"]) == {"pkg/core.py", "pkg/util.py", "tests/test_core.py"}
    assert result["planned_edits"][0]["new_name"] == "compute"
    assert contents(repo / "src") == before
    report_bytes = (repo / "out/report.json").read_bytes()
    assert result["output_sha256"] == hashlib.sha256(report_bytes).hexdigest()
    assert json.loads(report_bytes)["pass"] is True
    assert result["independent_semantic_oracle_credit"] is False
    assert not list((repo / "out").glob(".crossfile-*"))
    # Separate consumer: apply the emitted diff to the untouched original and
    # execute its tests. Do not trust the wrapper's own candidate/test flags.
    proc = subprocess.run(["git", "apply", "-p1"], input=result["unified_diff"].encode(),
                          cwd=repo / "src", capture_output=True)
    assert proc.returncode == 0, proc.stderr
    assert "def compute(" in (repo / "src/pkg/core.py").read_text()
    assert "from pkg.core import compute" in (repo / "src/pkg/util.py").read_text()
    import sys
    tested = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                            cwd=repo / "src", capture_output=True)
    assert tested.returncode == 0, tested.stdout + tested.stderr


def test_explicit_task_reuses_same_execution_pipeline(repo):
    result = run(repo, issue_path=None, task_path="task.json")
    assert result["pass"] is True, result
    assert result["issue_binding"] is None


def test_move_to_new_module_is_a_real_tested_diff(repo):
    (repo / "issue.json").write_text(json.dumps({
        "issue_id": "MOVE-1", "title": "Move helper from pkg/core.py to pkg/ops.py"}))
    result = run(repo)
    assert result["pass"] is True, result
    assert "pkg/ops.py" in result["changed_files"]
    assert "--- /dev/null" in result["unified_diff"]
    assert result["regression"]["completed"] == 1


def test_missing_task_cannot_succeed_from_imports(repo):
    with pytest.raises(ValueError, match="EXACTLY_ONE_ISSUE_OR_TASK_REQUIRED"):
        run(repo, issue_path=None)
    assert not (repo / "out").exists()


def test_missing_source_is_rejected_before_artifacts(repo):
    with pytest.raises(ValueError, match="SOURCE_ROOT_NOT_DIRECTORY"):
        run(repo, source_root="missing")
    assert not (repo / "out").exists()


def test_existing_report_and_source_probe_are_preserved(repo):
    probe = repo / "src/.nl_intent_probe_index.json"
    probe.write_bytes(b"user-owned bytes")
    result = run(repo)
    assert result["pass"] is True, result
    assert probe.read_bytes() == b"user-owned bytes"
    original = (repo / "out/report.json").read_bytes()
    with pytest.raises(ValueError, match="OUTPUT_ALREADY_EXISTS"):
        run(repo)
    assert (repo / "out/report.json").read_bytes() == original


def test_source_output_overlap_refused_without_writes(repo):
    before = contents(repo / "src")
    with pytest.raises(ValueError, match="OUTPUT_OVERLAPS_SOURCE"):
        run(repo, output_path="src/new/report.json")
    assert contents(repo / "src") == before


def test_source_symlink_refused_before_copy(repo):
    (repo / "src/linked.py").symlink_to(repo / "src/pkg/core.py")
    with pytest.raises(ValueError, match="UNSUPPORTED_SOURCE_TREE_ENTRY"):
        run(repo)
    assert not (repo / "out").exists()


@pytest.mark.parametrize("edit", [
    {"op": "move_symbol", "module": "pkg/core.py", "qualname": "helper", "to_module": "../escape.py"},
    {"op": "rename_symbol", "module": "pkg/core.py", "name": "helper", "new_name": "class"},
    {"op": "delete_module", "module": "pkg/core.py"},
])
def test_unsafe_or_unsupported_tasks_refused_before_scratch(repo, edit):
    (repo / "task.json").write_text(json.dumps({"issue_id": "BAD", "edits": [edit]}))
    before = contents(repo)
    with pytest.raises(ValueError):
        run(repo, issue_path=None, task_path="task.json")
    assert contents(repo) == before


@pytest.mark.parametrize("issue", [
    {"issue_id": "BAD", "title": "Extract normalize from helper"},
    {"issue_id": "BAD", "title": "Rename helper to compute in pkg/core.py",
     "body": "Preserve every secret file and improve every API."},
    {"issue_id": "BAD", "title": "Rename parameter x to count in pkg/core.py:helper"},
])
def test_unsupported_issue_requirements_are_not_dropped(repo, issue):
    (repo / "issue.json").write_text(json.dumps(issue))
    before = contents(repo / "src")
    result = run(repo)
    assert result["pass"] is False
    assert result["output_verified"] is False
    assert result["regression"]["completed"] == 0
    assert result["reason"]
    assert contents(repo / "src") == before


def test_ambiguous_symbol_refuses_instead_of_choosing(repo):
    (repo / "src/pkg/other.py").write_text("def helper(x):\n    return x\n")
    (repo / "issue.json").write_text(json.dumps({"issue_id": "AMB", "title": "Rename helper to compute"}))
    result = run(repo)
    assert result["pass"] is False
    assert result["issue_binding"]["complete"] is False
    assert result["stages"] == {}


def test_full_regression_catches_failure_outside_selected_slice(repo):
    (repo / "src/tests/test_unrelated.py").write_text("def test_unrelated():\n    assert 1 == 2\n")
    result = run(repo)
    assert result["stages"]["verified"] is True
    assert result["stages"]["test_passed_count"] == 1
    assert result["regression"]["failed"] == 1
    assert result["pass"] is False
    assert result["source_unchanged"] is True


def test_zero_test_execution_cannot_be_accepted(repo):
    (repo / "src/tests/test_core.py").unlink()
    result = run(repo)
    assert result["pass"] is False
    assert result["regression"]["completed"] == 0


def test_all_skipped_is_not_successful_verification(repo):
    test = repo / "src/tests/test_core.py"
    test.write_text(test.read_text().replace("def test_behavior():", "import pytest\n@pytest.mark.skip\ndef test_behavior():"))
    result = run(repo)
    assert result["pass"] is False
    assert result["regression"]["completed"] == 0


def test_selected_tests_cannot_mutate_candidate_outside_emitted_diff(repo):
    test = repo / "src/tests/test_core.py"
    test.write_text(test.read_text() + "\npathlib.Path('config.json').write_text('unreported change')\n")
    result = run(repo)
    assert result["pass"] is False
    assert "TESTED_TREE_DIFF_MISMATCH" in result["reason"]
    assert not (repo / "src/config.json").exists()


def test_diagnostic_architecture_exhaustion_is_not_patch_success(tmp_path):
    result = architecture.run({"output_path": "report.json"}, tmp_path)
    assert result["architecture_search_completed"] is True
    assert result["classification"] == "NEW_PRIMITIVE_REQUIRED"
    assert result["patch_synthesized"] is False
    assert result["pass"] is False
    assert result["verified"] is False
    assert result["output_verified"] is False
    assert result["artifact_integrity_verified"] is True


def test_even_successful_component_plan_is_not_executed_source_patch(tmp_path):
    manifest = {"components": [{"id": "available", "requires": [], "provides": ["target"],
                                "verified": True, "brain_owned": True, "donor_independent": True}],
                "initial_facts": [], "target": {"required_effects": ["target"],
                                                "forbidden_effects": [], "max_components": 1}}
    result = architecture.run({"manifest": manifest, "output_path": "plan.json"}, tmp_path)
    assert result["architecture_search_pass"] is True
    assert result["patch_synthesized"] is False
    assert result["verified"] is False


def test_registry_presence_cannot_credit_fullstack_delivery(tmp_path):
    registry_path = tmp_path / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_bytes((ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_bytes())
    result = declarations.run({"output_path": "report.json"}, tmp_path)
    assert result["declarations_resolve"] is True
    assert result["workflow_executed"] is False
    assert result["fullstack_verified"] is False
    assert result["output_verified"] is False
    assert result["artifact_integrity_verified"] is True


@pytest.mark.parametrize("adapter", [architecture, declarations])
def test_diagnostics_never_overwrite_existing_report(tmp_path, adapter):
    (tmp_path / "report.json").write_bytes(b"user report")
    with pytest.raises(ValueError, match="OUTPUT_ALREADY_EXISTS"):
        adapter.run({"output_path": "report.json"}, tmp_path)
    assert (tmp_path / "report.json").read_bytes() == b"user report"


def test_report_publish_is_atomic_no_replace_even_after_preflight(tmp_path):
    destination = fresh_output(tmp_path, "out/report.json", "unused.json")
    def write(value):
        try:
            return publish_report(tmp_path, destination, {"value": value, "verified": False})
        except FileExistsError:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, [1, 2]))
    winners = [r for r in results if r is not None]
    assert len(winners) == 1
    assert json.loads(destination.read_bytes())["value"] == winners[0]["value"]
    assert not list(destination.parent.glob(".swe-report-*"))


def test_pure_index_builder_matches_existing_adapter_without_source_writes(repo):
    from canonical.runtime.bound_capabilities import python_source_symbol_index as indexer
    before = contents(repo / "src")
    built = indexer.build_index(".", repo / "src")
    assert contents(repo / "src") == before
    indexer.run({"source_root": "src", "output_path": "index.json"}, repo)
    emitted = json.loads((repo / "index.json").read_bytes())
    assert indexer.build_index("src", repo) == emitted
    assert built["totals"] == emitted["totals"]
    assert {"src/" + m["path"]: m["sha256"] for m in built["modules"]} == {
        m["path"]: m["sha256"] for m in emitted["modules"]}
    assert built["modules"][0]["definitions"] == emitted["modules"][0]["definitions"]


def test_concurrent_tasks_share_no_probe_or_candidate_paths(repo):
    before = contents(repo / "src")
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run, repo, output_path=f"out/report-{i}.json") for i in range(2)]
        results = [f.result() for f in futures]
    assert all(r["pass"] is True for r in results), results
    assert results[0]["diff_sha256"] == results[1]["diff_sha256"]
    assert contents(repo / "src") == before
    assert not list((repo / "out").glob(".crossfile-*"))


@pytest.mark.parametrize("timeout", [0, False, 121, "10"])
def test_invalid_timeout_refused_before_scratch(repo, timeout):
    with pytest.raises(ValueError, match="TIMEOUT_MUST_BE_BOUNDED_INTEGER"):
        run(repo, timeout_s=timeout)
    assert not (repo / "out").exists()


def test_reserved_staging_file_is_not_overwritten_in_candidate(repo):
    (repo / "src/.orchestrate_plan.json").write_text("pre-existing user file")
    before = contents(repo / "src")
    with pytest.raises(ValueError, match="SOURCE_RESERVED_STAGE_FILE"):
        run(repo)
    assert contents(repo / "src") == before


def test_full_regression_mutation_cannot_change_the_accepted_candidate(repo):
    (repo / "src/tests/test_unrelated.py").write_text(
        "from pathlib import Path\ndef test_unrelated():\n    Path('cfg.json').write_text('side effect')\n")
    result = run(repo)
    assert result["regression"]["pass"] is True
    assert result["candidate_unchanged_during_regression"] is False
    assert result["pass"] is False
    assert not (repo / "src/cfg.json").exists()
