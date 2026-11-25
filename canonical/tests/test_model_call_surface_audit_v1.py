#!/usr/bin/env python3
"""The audit must be able to say NO, and must be able to be wrong out loud.

Every test here builds a small synthetic repository under `tmp_path`, because the
point of the instrument is what it can prove about an import graph, not how large
this repository happens to be. The one test that runs against the real tree asserts
only the things that are stable: the entry set exists and the report carries its
limits.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOL = ROOT / "canonical" / "tools" / "model_call_surface_audit_v1.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("model_call_surface_audit_v1", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def git_init(path: pathlib.Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "a@b.c"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, check=True)


def write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture()
def repo(tmp_path):
    git_init(tmp_path)
    # A: entry -> B -> C(model). Static path.
    write(tmp_path / "pkg/__init__.py", "")
    write(tmp_path / "pkg/a.py", "from pkg import b\n")
    write(tmp_path / "pkg/b.py", "from pkg import c\n")
    write(tmp_path / "pkg/c.py", 'URL = "https://text.pollinations.ai/"\n')
    # D: model endpoint but nobody imports it.
    write(tmp_path / "pkg/orphan.py", 'URL = "http://127.0.0.1:8080/v1/chat/completions"\n')
    # E: loads its sibling by string, not by import.
    write(
        tmp_path / "pkg/dyn.py",
        "import importlib.util, pathlib\n"
        "p = pathlib.Path(__file__).resolve().with_name('hidden.py')\n"
        "s = importlib.util.spec_from_file_location('h', p)\n",
    )
    write(tmp_path / "pkg/hidden.py", 'URL = "https://api.openai.com/v1"\n')
    # F: model bytes, not an answer.
    write(tmp_path / "pkg/artifacts.py", 'HOST = "https://huggingface.co/x/model"\n')
    # G: builds a URL from parts, so no literal names an endpoint.
    write(tmp_path / "pkg/assembled.py", 'HOST = "text." + "pollinations" + ".ai"\n')
    (tmp_path / "missions").mkdir()
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "x"], cwd=tmp_path, check=True)
    return tmp_path


def test_static_path_to_a_model_endpoint_is_found(repo):
    tool = load_tool()
    report = tool.audit(repo, {"E": "pkg/a.py"})
    row = report["entries"]["E"]
    assert row["combined_inference_endpoint_files"] == ["pkg/c.py"], row
    # Four files, not three: a package's __init__ is imported by `from pkg import b`.
    assert row["static_closure_size"] == 4


def test_an_unimported_endpoint_is_not_charged_to_the_entry(repo):
    tool = load_tool()
    report = tool.audit(repo, {"E": "pkg/a.py"})
    assert "pkg/orphan.py" in report["inference_endpoint_files"]
    assert "pkg/orphan.py" not in report["entries"]["E"]["static_inference_endpoint_files"]


def test_dynamic_sibling_load_is_followed(repo):
    tool = load_tool()
    report = tool.audit(repo, {"E": "pkg/dyn.py"})
    row = report["entries"]["E"]
    assert "pkg/hidden.py" in row["dynamic_targets"], row
    assert row["combined_inference_endpoint_files"] == ["pkg/hidden.py"], row


def test_model_bytes_are_classified_apart_from_model_answers(repo):
    tool = load_tool()
    report = tool.audit(repo, {"E": "pkg/artifacts.py"})
    row = report["entries"]["E"]
    assert row["combined_model_artifact_files"] == ["pkg/artifacts.py"], row
    assert row["combined_inference_endpoint_files"] == [], "model bytes are not cognition"


def test_a_url_assembled_at_run_time_is_reported_as_a_limit_not_as_absence(repo):
    tool = load_tool()
    report = tool.audit(repo, {"E": "pkg/assembled.py"})
    assert report["entries"]["E"]["combined_inference_endpoint_files"] == []
    assert any("assembled from parts" in x for x in report["limits"])


def test_planner_switch_census_reads_missions_and_reports_its_own_enforcement(repo):
    tool = load_tool()
    missions = repo / "canonical/astra_runtime/missions"
    write(missions / "M1.json", json.dumps({"steps": [{"allow_optional_model_planner": True}]}))
    write(missions / "M2.json", json.dumps({"steps": [{"allow_optional_model_planner": False}]}))
    write(missions / "M3.json", json.dumps({"steps": [{"id": "x"}]}))
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "m"], cwd=repo, check=True)
    census = tool.audit(repo, {"E": "pkg/a.py"})["planner_flag_census"]
    assert census["missions"] == 3
    assert census["planner_flag_true"] == 1
    assert census["planner_flag_false"] == 1
    assert census["planner_flag_absent"] == 1
    assert census["missions_with_planner_flag_true"] == [
        "canonical/astra_runtime/missions/M1.json"
    ]
    # The synthetic tree has no guards, so enforcement must be reported as empty--
    # not silently as "enforced".
    assert all(not row["mentions"] for row in census["guard_mentions"])


def test_missing_entry_fails_closed(repo):
    tool = load_tool()
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--root", str(repo), "--entry", "E=pkg/nope.py"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 2, proc
    assert "MODEL_CALL_AUDIT_ENTRY_MISSING" in proc.stderr


def test_report_against_this_tree_names_its_limits_and_its_scope():
    tool = load_tool()
    report = tool.audit(ROOT, tool.DEFAULT_ENTRIES)
    assert report["schema"] == "BRAIN_MODEL_CALL_SURFACE_AUDIT_V1"
    assert report["authority"].startswith("NONE")
    assert report["counts"]["tracked_python_files"] > 1000
    for label in tool.DEFAULT_ENTRIES:
        assert label in report["entries"]
        assert report["entries"][label]["entry_exists"] is True
    assert len(report["limits"]) >= 5
    assert report["counts"]["files_with_inference_endpoint_literal"] >= 1
    # The audit names endpoint patterns in its own source, so it matches itself. The
    # requirement is that it SAYS so, not that it hides it.
    assert report["instrument_self_matches"] == [
        "canonical/tests/test_model_call_surface_audit_v1.py",
        "canonical/tools/model_call_surface_audit_v1.py",
    ], report["instrument_self_matches"]
    assert any("SELF_REFERENCE" in x for x in report["limits"])
    # No other file may be silently exempted.
    others = set(report["inference_endpoint_files"]) - set(report["instrument_self_matches"])
    assert others, "the audit must still find real endpoint-bearing files"
