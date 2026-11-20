"""Tests for discovering damaged origins by executing generic actions."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import discover_origins_from_actions_v1 as D  # noqa: E402
from canonical.tools import goal_closure_v1 as GC  # noqa: E402
from canonical.tools import the_branch_is_the_model_v1 as BM  # noqa: E402
from canonical.tests.test_one_origin_derives_the_judge_v1 import repo  # noqa: E402


def test_discovery_finds_three_defect_families_without_a_damage_class(tmp_path: Path) -> None:
    base = repo(tmp_path)
    target = BM.MACHINE.git(base, "rev-parse", "HEAD")[1].strip()
    reference = GC.reference_tree(base, target)
    origins, edges = D.discover(base, target, tmp_path / "discover", reference)
    families = {defect for origin in origins for defect in origin["defects"]}
    assert edges > 0
    assert {"stash", "untracked", "wrong_branch"}.issubset(families)
    assert all(origin["path"].is_dir() for origin in origins)
    assert all(name not in ("stashed_wrong_branch", "side_untracked", "conflict_and_stash")
               for origin in origins for name in origin["plan"])


def test_discovered_origins_yield_a_closure(tmp_path: Path) -> None:
    base = repo(tmp_path)
    target = BM.MACHINE.git(base, "rev-parse", "HEAD")[1].strip()
    reference = GC.reference_tree(base, target)
    origins, _edges = D.discover(base, target, tmp_path / "discover", reference)
    rows, summaries = D.judge_rows(origins, target, reference, tmp_path, "test")
    assert all(s["holes"] and s["legitimate"] for s in summaries)
    selection = GC.select_closure(rows, target)
    assert selection["status"] == "CLOSURE_FOUND"
    evaluation = GC.evaluate(selection["closures"][0], rows, target)
    assert evaluation["false_accepts"] == [] and evaluation["false_rejects"] == []
