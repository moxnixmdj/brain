"""A computed relation for a reader field the old grammar could not name: file mode."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import permissions_are_a_relation_too_v1 as P  # noqa: E402


def test_reader_reports_modes_and_discovery_finds_the_mode_family(tmp_path: Path) -> None:
    tree = P.Tree(tmp_path / "base", P.TRAIN_FILES)
    target = tree.read()
    assert target.by_prefix("targetmode.")
    origins, edges = P.discover(tree, target, tmp_path / "discover")
    families = {defect for origin in origins for defect in origin["defects"]}
    assert edges > 0
    assert {"content_mismatch", "extra_path", "mode_mismatch"}.issubset(families)


def test_computed_closure_states_mode_and_transfers(tmp_path: Path) -> None:
    receipt = P.measure(tmp_path / "run",
                        receipt=tmp_path / "receipt.json",
                        store=tmp_path / "store.json")
    assert receipt["met"] is True
    assert any("mode" in json.dumps(law) for law in receipt["computed_laws"])
    assert all(not name in json.dumps(receipt["computed_laws"]) for name in P.TRAIN_FILES)
    assert receipt["held_evaluation"][0]["false_accepts"] == []
    assert receipt["held_evaluation"][0]["false_rejects"] == []
    store = json.loads((tmp_path / "store.json").read_text())
    assert store["removable"] is True and store["parameters"] == 0 and store["model_calls"] == 0
