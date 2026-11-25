"""Line-level localisation, and the three rankers that were tried and deleted.

The point of keeping the deletions in the receipt: a number means nothing unless the alternatives that were
rejected on measurement are also on the record.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from canonical.tools import line_localisation_v1 as locate  # noqa: E402

RECEIPT = REPO / "canonical" / "corpus" / "line_localisation_20261124_V1.json"


def test_changed_lines_reads_the_parent_side_of_a_hunk(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    run = lambda argv: subprocess.run(["git", *argv], cwd=repo, capture_output=True, text=True)
    run(["init", "-q"])
    run(["config", "user.email", "b@l"])
    run(["config", "user.name", "b"])
    (repo / "src" / "pkg").mkdir(parents=True)
    module = repo / "src" / "pkg" / "m.py"
    module.write_text("\n".join(f"line{i}" for i in range(1, 21)) + "\n")
    run(["add", "-A"])
    run(["commit", "-qm", "one"])
    module.write_text("\n".join(f"line{i}" for i in range(1, 21)).replace("line10", "changed") + "\n")
    run(["add", "-A"])
    run(["commit", "-qm", "two"])
    sha = run(["rev-parse", "HEAD"]).stdout.strip()
    parent = run(["rev-parse", "HEAD~1"]).stdout.strip()
    truth = locate.changed_lines(repo, parent, sha)
    assert truth.get("src/pkg/m.py")
    assert 10 in truth["src/pkg/m.py"]


def test_fusion_needs_no_weights():
    left = [(10, 1.0), (20, 2.0)]
    right = [(20, 1.0), (30, 1.0)]
    fused = locate.fuse({"a": left, "b": right})
    assert fused[0] == 20
    assert set(fused) == {10, 20, 30}


def test_generic_exceptions_are_not_a_location():
    """TypeError appears on hundreds of lines; treating it as a signal is noise."""
    assert "TypeError" in locate.GENERIC_EXCEPTIONS
    assert locate.exception_lines(pathlib.Path("/nonexistent"), "TypeError") == []


def test_the_receipt_records_the_gap_between_file_and_line():
    receipt = json.loads(RECEIPT.read_text())
    gap = receipt["the_gap_that_explains_everything"]
    assert gap["right_file_at_rank_1"] == 16
    assert gap["of_those_line_reached_at_1"] == 0
    assert gap["of_those_line_reached_within_25"] == 5


def test_the_deleted_rankers_are_on_the_record():
    receipt = json.loads(RECEIPT.read_text())
    deleted = {item["name"] for item in receipt["rankers_that_were_tried_and_deleted"]}
    assert "SHAPE" in deleted
    assert len(deleted) == 3


def test_line_localisation_is_not_claimed_as_solved():
    receipt = json.loads(RECEIPT.read_text())
    assert receipt["measured"]["line_top1"] <= 2
    assert "not a solved problem" in receipt["what_this_establishes"]
