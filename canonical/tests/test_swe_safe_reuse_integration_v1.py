"""Disposable real-world controls for source preservation and trusted index reuse."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from canonical.runtime.bound_capabilities import python_source_symbol_index as index
from canonical.runtime.bound_capabilities import python_tests_generate_scaffold as scaffold

ROOT = Path(__file__).resolve().parents[2]


def project(tmp_path):
    source = tmp_path / "generated" / "source"
    source.mkdir(parents=True)
    module = source / "m.py"
    module.write_text("def actual(x: int):\n    return x + 1\n")
    sentinel = source.parent / "unrelated.txt"
    sentinel.write_bytes(b"preserve unrelated fixture data")
    return source, module, sentinel


@pytest.mark.parametrize("output", ["generated", "generated/source", "generated/source/tests", "."])
def test_overlapping_generation_refuses_before_any_source_write(tmp_path, output):
    source, module, sentinel = project(tmp_path)
    before = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(SystemExit, match="PATH_OVERLAPS_SOURCE_ROOT"):
        scaffold.run({"source_root": "generated/source", "generated_tests_root": output,
                      "output_path": "report.json"}, tmp_path)
    after = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert after == before
    assert module.exists() and sentinel.exists()


def test_symlink_alias_of_ancestor_refuses_without_deleting_source(tmp_path):
    source, module, sentinel = project(tmp_path)
    (tmp_path / "alias").symlink_to(source.parent, target_is_directory=True)
    with pytest.raises(SystemExit, match="PATH_OVERLAPS_SOURCE_ROOT"):
        scaffold.run({"source_root": "generated/source", "generated_tests_root": "alias",
                      "output_path": "report.json"}, tmp_path)
    assert module.exists() and sentinel.exists()


def test_positional_only_smoke_runs_through_actual_runner(tmp_path):
    source, module, _ = project(tmp_path)
    module.write_text("def actual(x: int, /, *, flag: bool = False):\n    return x + int(flag)\n")
    result = scaffold.run({"source_root": "generated/source", "generated_tests_root": "tests",
                           "output_path": "report.json"}, tmp_path)
    assert result["verified"] is True
    assert result["test_passed"] == 1
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["generated"][0]["call_expr"] == "actual(1, flag=True)"


def make_index(tmp_path, name="index.json"):
    source, _, _ = project(tmp_path)
    args = {"source_root": "generated/source", "output_path": name}
    result = index.run(args, tmp_path)
    return args, json.loads((tmp_path / name).read_text()), result


@pytest.mark.parametrize("rehash", [False, True])
def test_altered_semantic_rows_are_rederived_even_with_recomputed_row_hash(tmp_path, rehash):
    args, artifact, _ = make_index(tmp_path)
    row = artifact["modules"][0]
    row["definitions"][0]["name"] = "nonexistent"
    row["definitions"][0]["qualname"] = "nonexistent"
    if rehash:
        row["row_sha256"] = index._row_sha(row)
    (tmp_path / "index.json").write_text(json.dumps(artifact))
    result = index.run(args, tmp_path)
    rebuilt = json.loads((tmp_path / "index.json").read_text())
    assert rebuilt["modules"][0]["definitions"][0]["name"] == "actual"
    assert result["parsed_module_count"] == 1
    assert result["output_verified"] is True


def test_untouched_producer_output_is_reused(tmp_path):
    args, _, _ = make_index(tmp_path)
    before = (tmp_path / "index.json").read_bytes()
    result = index.run(args, tmp_path)
    assert result["parsed_module_count"] == 0
    assert result["reused_module_count"] == 1
    assert (tmp_path / "index.json").read_bytes() == before


def test_forged_sibling_does_not_supply_cache_rows(tmp_path):
    args, artifact, _ = make_index(tmp_path)
    artifact["modules"][0]["definitions"][0]["name"] = "nonexistent"
    (tmp_path / "index.json").write_text(json.dumps(artifact))
    args["output_path"] = "new-request.json"
    result = index.run(args, tmp_path)
    assert result["parsed_module_count"] == 1
    assert json.loads((tmp_path / "new-request.json").read_text())["modules"][0]["definitions"][0]["name"] == "actual"


def test_authentic_sibling_overwrites_an_existing_untrusted_output(tmp_path):
    args, _, _ = make_index(tmp_path)
    (tmp_path / "new-request.json").write_text('{"untrusted": true}')
    args["output_path"] = "new-request.json"
    result = index.run(args, tmp_path)
    assert result["reused_module_count"] == 1
    assert json.loads((tmp_path / "new-request.json").read_text())["schema"] == "PROJECT_BRAIN_PYTHON_SYMBOL_INDEX_V1"


@pytest.mark.parametrize("field", ["modules", "symbols", "callers_of", "totals"])
def test_external_cache_validator_rejects_forged_semantics(tmp_path, field):
    _, artifact, _ = make_index(tmp_path)
    artifact = copy.deepcopy(artifact)
    if field == "modules":
        artifact[field][0]["definitions"][0]["name"] = "nonexistent"
        artifact[field][0]["row_sha256"] = index._row_sha(artifact[field][0])
    elif field == "totals":
        artifact[field]["symbols"] = 900
    else:
        artifact[field] = {"nonexistent": []}
    with pytest.raises(RuntimeError, match="INDEX_CACHE_DERIVATION_UNTRUSTED"):
        index.validate_cached_index(tmp_path, tmp_path / "generated/source", artifact)


def test_new_process_rederives_persisted_output_instead_of_trusting_it(tmp_path):
    args, _, _ = make_index(tmp_path)
    script = ("import json, pathlib, sys; from canonical.runtime.bound_capabilities import "
              "python_source_symbol_index as i; print(json.dumps(i.run(" + repr(args) + ", pathlib.Path(sys.argv[1]))))")
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    proc = subprocess.run([sys.executable, "-c", script, str(tmp_path)], env=env,
                          capture_output=True, text=True, timeout=15, check=True)
    result = json.loads(proc.stdout)
    assert result["parsed_module_count"] == 1
    assert result["output_verified"] is True


def test_trusted_output_attestations_are_bounded(tmp_path):
    args, _, _ = make_index(tmp_path)
    for n in range(135):
        args["output_path"] = f"artifact-{n}.json"
        index.run(args, tmp_path)
    assert len(index._TRUSTED_OUTPUTS) <= 128
