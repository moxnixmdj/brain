"""A declared kind is a WORD, not a substring.

Pins the round-4 finding: `world_probe_v1._kinds_of` matched kinds with a raw
substring test, so a capability id could announce a file kind nobody declared,
and `kind_contradiction` turned that accident into an outright ELIMINATION
before binding was ever attempted.

The measured case, on the live 145-capability registry:

    chart.raster.axis_title_unit_binding.v1   -> 'ast'   ("ch-art.r-ast-er")
    chart.raster.scene_graph.v1               -> 'ast'
    auto.npm.shelacek-ubjson                  -> 'json'  ("ub-json")
    terminal.kstar.root.assess.stdlib         -> 'tar'   ("ks-tar")

All six `chart.raster.*` capabilities declared themselves AST consumers while
their own registry rows say `requires: ['image.file.available']`. The result:
a goal naming a real PNG eliminated every one of them with
`INPUT_KIND_CONTRADICTS_GOAL_FILE`, and binding was never attempted.

Nothing here is a claim that the chart capabilities read a real chart. The
first test walks one as far as the world's answer; on a fabricated PNG the
honest outcome is a refusal (ACTION_FAILED), and a refusal reached after
selection is a different fact from an elimination reached before it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import grounded_action_v1 as GA
from canonical.runtime import world_probe_v1 as WP

REGISTRY = json.loads(
    (ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text()
)["capabilities"]

# The substring accidents measured on the live registry.
ACCIDENTS = {
    "chart.raster.axis_title_unit_binding.v1": "ast",
    "chart.raster.curve_value_query.v1": "ast",
    "chart.raster.curve_x_at_y_query.v1": "ast",
    "chart.raster.direct_curve_label_family_rank.v1": "ast",
    "chart.raster.legend_style_binding.v1": "ast",
    "chart.raster.scene_graph.v1": "ast",
    "auto.npm.shelacek-ubjson": "json",
    "terminal.kstar.root.assess.stdlib": "tar",
}


def test_a_kind_inside_an_unrelated_word_is_not_declared():
    for cid, phantom in ACCIDENTS.items():
        assert phantom not in WP._kinds_of(cid), (
            f"{cid} still declares {phantom!r} by substring accident"
        )


def test_a_kind_stated_as_a_whole_word_is_still_declared():
    # The repair must not blind the recogniser: real declarations still land.
    assert WP._kinds_of("pdf") == {"pdf"}
    assert "image" in WP._kinds_of("read an image file")
    assert "python" in WP._kinds_of("python.source")
    assert "ast" in WP._kinds_of("python ast audit")


def test_a_chart_capability_no_longer_contradicts_its_own_declared_input():
    # The registry row says image; kind_contradiction said ast. They must agree.
    cid = "chart.raster.axis_title_unit_binding.v1"
    assert "image.file.available" in REGISTRY[cid]["requires"]
    png = "canonical/astra/canary_frames/000-c-ferry-scan0.png"
    assert not WP.kind_contradiction(cid, ["path"], [png])


def test_an_unrecognised_extension_still_never_contradicts():
    # Not knowing is not contradicting: the invariant the docstring promises.
    assert not WP.kind_contradiction(
        "chart.raster.scene_graph.v1", ["path"], ["canonical/runtime/macro_v1"]
    )


def test_a_real_png_reaches_the_capability_instead_of_being_eliminated():
    """The end-to-end consequence, asserted at the front door.

    Before the repair this sentence produced `INPUT_KIND_CONTRADICTS_GOAL_FILE`
    -- the capability was not even a candidate. The minimum bar for a
    hypothesis space that can learn is that its members are reachable.
    """
    png = "canonical/astra/canary_frames/000-c-ferry-scan0.png"
    result = GA.act(
        f"read the axis title unit binding of the chart at {png}",
        memory=False,
        bridge=False,
        computer_use=False,
    )
    rejected = {
        str(r.get("capability_id")): r
        for r in (result.get("rejected") or [])
        if isinstance(r, dict)
    }
    why = (rejected.get("chart.raster.axis_title_unit_binding.v1") or {}).get("why")
    assert why != "INPUT_KIND_CONTRADICTS_GOAL_FILE", (
        "the capability whose row requires an image was eliminated by an "
        "image, again"
    )
    # And it is no longer reported as missing the one input the goal names.
    assert result.get("capability_id") == "chart.raster.axis_title_unit_binding.v1"


def test_the_binder_really_did_ground_the_named_path():
    # Guards the other half: the sentence named a path, so `path` is bindable.
    from canonical.runtime import world_binding_v1 as WB

    cid = "chart.raster.axis_title_unit_binding.v1"
    entry = dict(REGISTRY[cid], capability_id=cid)
    png = "canonical/astra/canary_frames/000-c-ferry-scan0.png"
    bound = WB.complete_inputs(f"read the axis title unit binding of the chart at {png}", ROOT, entry)
    assert bound["missing"] == []
    assert bound["inputs"]["path"] == png
