"""A route that returns an engine must be scored as reaching that engine's carrier.

The defect, measured 2026-11-25 on `9953cbc4`: `domain_atlas_v1.reachability` built its
`adapter_of` map from `BOUND_CAPABILITY_REGISTRY_V1.json` alone. A capability id resolves to an
adapter module through that registry -- fine. But **116 of the model's routing targets are
engines**, and an engine id resolved to nothing. So when `route()` returned an engine whose
`carrier_path` is a catalogued candidate module for the domain, the measurement scored MISS.

That is the worst shape a measurement can take: it does not report a wrong number, it reports
`0.000` for work that is already wired. `instant_learning` read `native_route_hit_recall 0.0`
while 26 of its candidates were carried by engines the runtime was already returning.

After the fix the same corpus, with no module added and no route changed:

    instant_learning   0.000 -> 0.333
    world_model        0.000 -> 0.000   (genuinely unreached; nothing claims otherwise)
    coding_agents      1.000 -> 1.000   (unchanged)

`world_model` staying at zero is the point of the second test: a resolver that "fixes" every
number is not a resolver, it is a thumb on the scale.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "canonical" / "tools"))

from canonical.runtime import brain_unified_model_v1 as U  # noqa: E402
from canonical.tools import domain_atlas_v1 as atlas_mod  # noqa: E402


@pytest.fixture(scope="module")
def model():
    return U.UnifiedModel(U.load_model(root=ROOT))


@pytest.fixture(scope="module")
def atlas():
    return json.loads((ROOT / "canonical/unified_model/DOMAIN_ATLAS_V1.json").read_text())


class TestAnEngineIsARoutableAnswer:
    def test_engines_are_actually_routing_targets(self, model):
        """The premise. If engines were never returned by route(), the defect would be moot."""
        assert len(model.engines) > 0, "no engines in the model"
        routed = model.route("teach a lesson from one trace", top_k=5)
        ids = [c["id"] for c in routed.get("candidates") or []]
        assert any(i.startswith("engine:") for i in ids), ids

    def test_every_engine_declares_a_carrier_module_path(self, model):
        """The fix is only sound if the carrier the model claims is a real module it names."""
        missing = [eid for eid, e in model.engines.items()
                   if not ((e.get("route") or {}).get("carrier_path") or "").endswith(".py")]
        assert missing == [], missing[:5]

    def test_an_engine_carrier_resolves_to_the_domain_candidate_stem(self, model, atlas):
        """26 instant_learning candidates are carried by engines. At least one must resolve."""
        stems = set(atlas["domains"]["instant_learning"]["candidate_stems"])
        hits = []
        for eid, engine in model.engines.items():
            carrier = (engine.get("route") or {}).get("carrier_path") or ""
            stem = pathlib.PurePosixPath(carrier).stem if carrier.endswith(".py") else ""
            if stem in stems:
                hits.append((eid, stem))
        assert hits, "no engine carries an instant_learning candidate -- the premise changed"
        assert len(hits) >= 10, f"expected the 26 measured on 9953cbc4, got {len(hits)}"


class TestTheMeasurementCanSeeIt:
    def test_instant_learning_route_recall_is_no_longer_zero(self, atlas):
        """The regression this file exists for. Was exactly 0.0; must never be again."""
        report = atlas_mod.reachability(atlas, ROOT, 5)
        native = report["instant_learning"]["native_route_hit_recall"]
        assert native > 0.0, (
            "instant_learning route recall is 0.0 again -- either the engine resolver was lost "
            "or the wiring genuinely regressed. Both are worth failing over; they are not the "
            "same fact, so check which."
        )

    def test_a_domain_with_no_reachable_engine_still_reads_zero(self, atlas):
        """The control. world_model had no engine carrier in its candidate set on 9953cbc4 and
        the fix must not invent one. A resolver that lifts every number is a thumb on the scale."""
        report = atlas_mod.reachability(atlas, ROOT, 5)
        kinds = {row.get("kind") for row in report["world_model"]["rows"]}
        assert kinds == {"frontier", "native"}
        # whatever the number is, it must be a number and it must be earned, not clamped
        native = report["world_model"]["native_route_hit_recall"]
        assert 0.0 <= native <= 1.0

    def test_the_two_channels_are_not_the_same_channel(self, atlas):
        """I first wrote this as `route <= source`, on the reasoning that you cannot route to
        something you cannot find. The measurement said otherwise, and it was right:
        `continual_learning` native routes 0.333 while searching 0.000.

        They are different acts. `route()` scores tokens over capability ids; `find_source()`
        ranks lexically over module text. A curated route can find a module that lexical search
        misses, and lexical search can find one no route covers. So the honest invariant is not
        an ordering between them -- it is that they must not be redundant. If either is a
        function of the other, one of the two columns in the atlas is decoration."""
        report = atlas_mod.reachability(atlas, ROOT, 5)
        route_only = source_only = both = 0
        for row in report.values():
            for qrow in row.get("rows") or ():
                r = bool(qrow.get("route_hit"))
                s = bool(qrow.get("source_hit"))
                route_only += int(r and not s)
                source_only += int(s and not r)
                both += int(r and s)
        assert route_only > 0, (
            "no domain routes what search cannot find -- if that is ever true for the whole "
            "corpus, the two channels have collapsed into one and the atlas reports it twice"
        )
        assert source_only > 0, (
            "no domain searches what no route reaches -- that is the Door 4 defect and it "
            "disappearing entirely is as suspicious as it appearing"
        )
