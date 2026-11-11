"""A counting question about a file is now answered UNDER CONFINEMENT.

The engine that knew the answer (computer_env_v1.answer_query) ran host programs with
the caller's authority, which is what computer_execution_boundary_v1 refuses. The
carrier exists and works; this bridge is the routing that was missing.

Every test below runs a real subprocess under the real carrier. If the carrier is
missing on some host, these fail rather than skipping -- a skip would read as a pass.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import confined_query_bridge_v1 as bridge

BASE = ROOT / "canonical" / "astra_runtime" / "tmp"


def _file(name: str, rows: list[str]) -> Path:
    BASE.mkdir(parents=True, exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix="qb_", dir=str(BASE)))
    (d / name).write_text("\n".join(rows) + "\n")
    return d / name


def _dupes(distinct: int, each: int = 2) -> list[str]:
    return [f"row-{i}" for i in range(distinct) for _ in range(each)]


def test_unique_lines_is_the_distinct_count_not_the_total():
    f = _file("data.txt", _dupes(8))
    out = bridge.answer_confined("how many unique lines in data.txt", f)
    assert out["pass"] is True, out.get("reason")
    assert out["answer"] == "8", out
    assert out["confined"] is True


def test_plain_lines_is_the_total_count():
    f = _file("data.txt", _dupes(8))
    out = bridge.answer_confined("how many lines in data.txt", f)
    assert out["pass"] is True, out.get("reason")
    assert out["answer"] == "16", out


def test_a_different_file_and_a_different_size_still_answer():
    f = _file("pods.txt", _dupes(13, 3))
    out = bridge.answer_confined("how many unique lines in pods.txt", f)
    assert out["pass"] is True
    assert out["answer"] == "13", out
    tot = bridge.answer_confined("how many lines in pods.txt", f)
    assert tot["answer"] == "39", tot


def test_a_question_with_no_single_admitted_program_is_refused_not_guessed():
    f = _file("data.txt", _dupes(4))
    out = bridge.answer_confined("how many duplicate lines in data.txt", f)
    assert out["pass"] is False
    assert out["status"] == "REFUSED__QUERY_NOT_SERVABLE_UNDER_CONFINEMENT"
    assert "NO_SINGLE_ADMITTED_PROGRAM" in out["reason"] or out["reason"] == "NOT_A_COUNTABLE_QUESTION"


def test_a_missing_file_is_refused():
    out = bridge.answer_confined("how many lines in nope.txt", Path("/tmp/nope-not-here.txt"))
    assert out["pass"] is False
    assert out["reason"] == "NO_EXISTING_INPUT_FILE_IN_GOAL"


def test_the_bridge_never_claims_a_pass_without_confinement():
    f = _file("data.txt", _dupes(3))
    out = bridge.answer_confined("how many unique lines in data.txt", f)
    assert out["pass"] is True
    assert out["confined"] is True
    assert out["live_workspace_untouched"] is True
    # and it must be honest about the cross-check it does NOT do
    assert out["carrier_qualified"] is False
    assert "Not cross-checked" in out["honesty"]


def test_the_bridge_runs_no_pipeline_and_no_shell():
    """sort -u | wc -l is the obvious way and it is exactly what is not available."""
    f = _file("data.txt", _dupes(5))
    out = bridge.answer_confined("how many unique lines in data.txt", f)
    assert out["pass"] is True
    assert out["argv"] == ["sort", "-u", "data.txt"], out["argv"]
    assert all("|" not in str(a) for a in out["argv"])
