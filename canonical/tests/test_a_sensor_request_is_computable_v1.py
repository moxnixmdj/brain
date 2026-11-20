"""The sensor request is computed from a refusal and closed on an unseen tree."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import a_sensor_request_is_computable_v1 as S  # noqa: E402


def test_old_reader_is_blind_but_the_effect_is_real(tmp_path: Path) -> None:
    base = S.build(tmp_path / "base", S.TRAIN_FILES)
    row = S.run_action(base, tmp_path / "copy", "mkdir")
    assert row["returncode"] == 0
    assert S.old_sees_change(row) is False
    assert "new_directory" in S.new_paths(row["before"], row["after"])
    assert (Path(row["cwd"]) / "new_directory").is_dir()


def test_request_closes_the_hole_on_a_different_tree(tmp_path: Path) -> None:
    receipt = S.measure(tmp_path / "run",
                        receipt=tmp_path / "receipt.json",
                        store=tmp_path / "store.json")
    assert receipt["met"] is True
    assert receipt["sensor_request"]["field"] in receipt["selection_diagnostics"]["minimal_tie_fields"]
    assert receipt["selected_train"]["false_accepts"] == []
    assert receipt["selected_train"]["false_rejects"] == []
    assert receipt["selected_held"]["false_accepts"] == []
    assert receipt["selected_held"]["false_rejects"] == []
    assert receipt["naive_held"]["false_accepts"] == ["touch", "write_file", "symlink"]
    store = json.loads((tmp_path / "store.json").read_text())
    assert store["removable"] is True and store["parameters"] == 0 and store["model_calls"] == 0
