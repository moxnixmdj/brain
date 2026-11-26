"""Tests for the domain atlas and the anatomy block it puts in the model.

The atlas exists to answer one question honestly: *does this repository implement the
five frontier functions, and can the shipped model reach what implements them?* Both
halves have to be checkable before either number means anything:

  1. a module must be anchored -- the function's word in its own name or in its own
     definitions -- so a docstring that merely mentions "memory" cannot rank as the
     memory subsystem;
  2. the model must expose the atlas without ever laundering navigation into admission.

The third property is the one that keeps the numbers comparable: the atlas is
deterministic, so a recall figure can be reproduced by anyone.
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import brain_unified_model_v1 as U  # noqa: E402
from canonical.tools import domain_atlas_v1 as A  # noqa: E402

FIXTURE = {
    "canonical/runtime/real_memory_recall_v1.py": (
        '"""Nothing much."""\n\n'
        "def recall_episode(query):\n"
        "    return query\n"
    ),
    "canonical/runtime/says_memory_a_lot_v1.py": (
        '"""A module about memory. It discusses memory, memory and more memory, at length.\n'
        'Memory is mentioned here because the docstring is long."""\n\n'
        "def compute(x):\n"
        "    return x\n"
    ),
    "canonical/runtime/gui_click_pointer_v1.py": (
        '"""Click a point on the screen."""\n\n'
        "def click(x, y):\n"
        "    return (x, y)\n"
    ),
}


def _tree(tmp: pathlib.Path) -> pathlib.Path:
    for rel, text in FIXTURE.items():
        path = tmp / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp


def test_anchored_module_ranks_and_docstring_noise_does_not(tmp_path=None):
    with tempfile.TemporaryDirectory() as tmp:
        root = _tree(pathlib.Path(tmp))
        atlas = A.build_atlas(root, None, per_domain=5)
    memory = [row["path"] for row in atlas["domains"]["memory"]["top"]]
    computer = [row["path"] for row in atlas["domains"]["computer_use"]["top"]]
    assert "canonical/runtime/real_memory_recall_v1.py" in memory
    # Mentions memory five times, defines nothing about it: not anchored, must not rank.
    assert "canonical/runtime/says_memory_a_lot_v1.py" not in memory
    assert "canonical/runtime/gui_click_pointer_v1.py" in computer


def test_atlas_is_deterministic():
    with tempfile.TemporaryDirectory() as tmp:
        root = _tree(pathlib.Path(tmp))
        first = json.dumps(A.build_atlas(root, None, per_domain=5), sort_keys=True)
        second = json.dumps(A.build_atlas(root, None, per_domain=5), sort_keys=True)
    assert first == second


def test_shipped_model_carries_anatomy_and_it_is_navigation_only():
    model = U.UnifiedModel(U.load_model())
    block = model.anatomy()
    assert block["schema"] == U.ANATOMY_SCHEMA
    assert block["capability"] is False and block["executable"] is False
    assert len(block["domains"]) == 7
    for name in ("instant_learning", "computer_use", "coding_agents", "memory",
                 "continual_learning", "verification_abstention", "world_model"):
        row = model.anatomy(name, top_k=3)
        assert row["operation"] == "ANATOMY"
        assert row["capability"] is False
        assert row["modules"], "a domain with no modules means the atlas is empty"
        for module in row["modules"]:
            assert module["capability"] is False
            assert module["path"].startswith("canonical/")


def test_unknown_domain_refuses_by_name():
    model = U.UnifiedModel(U.load_model())
    got = model.anatomy("no_such_function")
    assert got["domains"] == {}
    assert "UNKNOWN_DOMAIN" in got["reason"]
    assert "instant_learning" in got["reason"]


def test_reachability_reports_chance_baselines():
    """A recall without its chance baseline is a number without a denominator."""
    atlas = json.loads((A.ROOT / "canonical/unified_model/DOMAIN_ATLAS_V1.json")
                       .read_text(encoding="utf-8"))
    reach = atlas.get("reachability") or {}
    if not reach:  # atlas built with --no-reachability
        return
    for name, row in reach.items():
        assert row["chance_source_recall"] > 0.0, name
        assert row["chance_route_recall"] >= 0.0, name
        assert 0.0 <= row["frontier_source_hit_recall"] <= 1.0, name
