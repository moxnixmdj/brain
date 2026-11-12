"""Verified goal-variant generalization for compiled workflow memory.

The claim under test is narrow: a workflow qualified on one wording can recall a
*verified* second wording with new parameter values, while ambiguous, unsafe, or
untaught wordings still refuse.  This is not a claim of open-world semantic
understanding.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as C
from canonical.swe_kernel import workflow_goal_generalization_v1 as G


def _teach(db: pathlib.Path, heldout_goal: str, heldout_cwd: pathlib.Path | None = None) -> dict:
    return C.compile_and_qualify_skill(
        goal="Write 'alpha' to note.txt",
        trace=[{"layer": "python_file_op", "op": "write_text", "path": "note.txt", "content": "alpha"}],
        postcondition={"kind": "file_contains", "path": "note.txt", "contains": "alpha"},
        heldout_goal=heldout_goal,
        heldout_cwd=heldout_cwd,
        db_path=db,
    )


def test_verified_paraphrase_recalls_with_new_values(tmp_path: pathlib.Path) -> None:
    db = tmp_path / "w.sqlite"
    held = tmp_path / "held"
    held.mkdir()
    qualified = _teach(db, "Save 'beta' to other.txt", held)
    assert qualified["pass"] is True, qualified

    world = tmp_path / "world"
    world.mkdir()
    result = C.recall_and_execute_workflow("Save 'gamma' to third.txt", cwd=world, db_path=db)
    assert result is not None and result["pass"] is True
    assert result["bindings"] == {"?str0": "gamma", "?path0": "third.txt"}
    assert (world / "third.txt").read_text(encoding="utf-8") == "gamma"
    assert result["model_dependency_count"] == 0


def test_original_wording_still_recalls_after_variant_admission(tmp_path: pathlib.Path) -> None:
    db = tmp_path / "w.sqlite"
    assert _teach(db, "Save 'beta' to other.txt")["pass"] is True
    world = tmp_path / "world"
    world.mkdir()
    result = C.recall_and_execute_workflow("Write 'delta' to fourth.txt", cwd=world, db_path=db)
    assert result is not None and result["pass"] is True
    assert (world / "fourth.txt").read_text(encoding="utf-8") == "delta"


def test_argument_order_variant_is_admitted_when_typed_roles_are_unique(tmp_path: pathlib.Path) -> None:
    db = tmp_path / "w.sqlite"
    qualified = _teach(db, "Save to other.txt the text 'beta'")
    assert qualified["pass"] is True, qualified
    world = tmp_path / "world"
    world.mkdir()
    result = C.recall_and_execute_workflow("Save to third.txt the text 'gamma'", cwd=world, db_path=db)
    assert result is not None and result["pass"] is True
    assert (world / "third.txt").read_text(encoding="utf-8") == "gamma"


@pytest.mark.parametrize("goal", [
    "Delete 'gamma' from third.txt",
    "Append 'gamma' to third.txt",
    "Save 'gamma' to third.txt and delete note.txt",
    "Do not save 'gamma' to third.txt",
    "Paint the fence",
])
def test_untaught_or_unsafe_wordings_do_not_recall(tmp_path: pathlib.Path, goal: str) -> None:
    db = tmp_path / "w.sqlite"
    assert _teach(db, "Save 'beta' to other.txt")["pass"] is True
    world = tmp_path / "world"
    world.mkdir()
    assert C.recall_and_execute_workflow(goal, cwd=world, db_path=db) is None
    assert not list(world.iterdir())


def test_variant_survives_export_import_and_tamper_is_refused(tmp_path: pathlib.Path) -> None:
    db = tmp_path / "w.sqlite"
    assert _teach(db, "Save 'beta' to other.txt")["pass"] is True
    bundle = tmp_path / "bundle.json"
    exported = C.export_workflow_bundle(bundle, db_path=db)
    assert exported["ok"] is True

    db2 = tmp_path / "imported.sqlite"
    imported = C.import_workflow_bundle(bundle, db_path=db2)
    assert imported["ok"] is True and imported["accepted"] == 1
    world = tmp_path / "world"
    world.mkdir()
    assert C.recall_and_execute_workflow("Save 'gamma' to third.txt", cwd=world, db_path=db2)["pass"] is True

    doc = json.loads(bundle.read_text(encoding="utf-8"))
    doc["skills"][0]["goal_variants"][0]["goal_regex"] = "^Save anything$"
    bundle.write_text(json.dumps(doc), encoding="utf-8")
    db3 = tmp_path / "tampered.sqlite"
    refused = C.import_workflow_bundle(bundle, db_path=db3)
    assert refused["ok"] is False and refused["accepted"] == 0
    assert any(r["reason"] in {"TAMPERED_ARTIFACT_SHA256", "INVALID_GOAL_VARIANT"} for r in refused["refusals"])


def test_ambiguous_same_kind_holes_refuse_automatic_variant() -> None:
    generalized = C.anti_unify_workflow(
        "Set 'alpha' to 'beta' in config.txt",
        [{"layer": "python_file_op", "op": "write_text", "path": "config.txt", "content": "alpha=beta"}],
        {"kind": "file_contains", "path": "config.txt", "contains": "alpha=beta"},
    )
    assert generalized["param_order"].count("?str0") == 1
    assert any(h.startswith("?str") for h in generalized["param_order"])
    assert len([h for h in generalized["param_order"] if h.startswith("?str")]) == 2
    assert C.induce_goal_variant(generalized, "Store 'gamma' as 'delta' in config.txt") is None


def test_surface_guard_masks_user_data_but_refuses_control_language() -> None:
    assert G.surface_is_safe("Save 'do not delete' to note.txt") is True
    assert G.surface_is_safe("Save 'x' to note.txt and delete old.txt") is False
    assert G.surface_is_safe("Do not save 'x' to note.txt") is False


def test_variant_validator_requires_exact_hole_set() -> None:
    variant = {
        "goal_skeleton": "Save '?str0' to ?path0",
        "goal_regex": r"^\s*Save\s+'(?P<str0>.+?)'\s+to\s+(?P<path0>[^\s\"',;)]+?)\.?\s*$",
        "skeleton_tokens": ["save"],
    }
    assert G.validate_variant(variant, ["?str0", "?path0"]) is True
    assert G.validate_variant(variant, ["?str0"]) is False
    bad = dict(variant, goal_regex="(")
    assert G.validate_variant(bad, ["?str0", "?path0"]) is False
