"""Tests for a law vocabulary computed from readings rather than supplied by name."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import computed_law_algebra_v1 as L  # noqa: E402
from canonical.tools import goal_closure_v1 as GC  # noqa: E402
from canonical.tools import one_origin_derives_the_judge_v1 as O  # noqa: E402
from canonical.tests.test_one_origin_derives_the_judge_v1 import repo  # noqa: E402


def _rows(tmp_path: Path) -> tuple[list[GC.Judgment], str]:
    base = repo(tmp_path)
    target = GC.BM.MACHINE.git(base, "rev-parse", "HEAD")[1].strip()
    reference = GC.reference_tree(base, target)
    start = GC.damage_extra(tmp_path / "task", base, "stashed_wrong_branch")
    rows = O._origin_rows(start, target, tmp_path / "ws", reference)["rows"]
    return rows, target


def test_candidates_contain_no_named_law_and_no_observation_text(tmp_path: Path) -> None:
    rows, _target = _rows(tmp_path)
    laws = L.candidate_laws(rows)
    encoded = json.dumps(laws)
    assert laws
    assert not any(name in encoded for name in GC.LAW_IDS)
    assert "local edit" not in encoded
    assert any(law.get("kind") in ("preserve", "no_new", "restore", "flag", "clear")
               for law in laws)


def test_computed_selection_has_zero_errors_on_observed_rows(tmp_path: Path) -> None:
    rows, _target = _rows(tmp_path)
    selection = L.select(rows)
    assert selection["status"] == "CLOSURE_FOUND"
    evaluation = L.evaluate(selection["closures"][0], rows)
    assert evaluation["false_accepts"] == [] and evaluation["false_rejects"] == []
