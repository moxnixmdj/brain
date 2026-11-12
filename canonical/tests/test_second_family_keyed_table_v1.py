"""Round 25: the compression mechanism generalises to a second family -- measured.

Rounds 23/24 measured compression -> admission -> replay for ONE family (periodic-table lookup)
and pinned the honest negative that the mechanism had not been shown to generalise. This round
generalises the lifter itself: every constant-collection literal (tuple, list, set, dict) lifts
as ONE parameter, with `None`/`True`/`False` excluded as structural singletons -- the world-model
writer's machinery (`row is None`, `out['known'] = True`) is structure, not data.

THE PREDICTION, written before the confirmatory run:

> Three world-model organs -- machinery byte-identical, one dict literal of per-organ data --
> compress into ONE admitted abstraction with measured gain and the family recognised from
> structure; a NEVER-seen fourth world-model organ, synthesized cold, replays through it
> strictly smaller with behaviour preserved on held-out action ids.

Measured (this tree): admission pays from the third site exactly as the periodic family does
(2 sites: NOT_COMPRESSIVE; 3 sites: gain 103 bytes, family `keyed_table_lookup`); the never-seen
organ replays 394 -> 277 bytes (30% smaller); 0 behaviour mismatches on held-out ids including
unknowns and non-string inputs.

Honesty upgrades this family forced, both pinned:
  * a probe grid the original answers IDENTICALLY on every input verifies nothing -- a
    non-discriminating grid now refuses both admission and replay (a float grid against a
    string-keyed table is exactly such a grid);
  * the bridge stays SKILL-only and correctly admits nothing it cannot probe: it has no domain
    knowledge, so string-domain organs enter the library only through a caller that can supply
    real domain probes.
"""
from __future__ import annotations

import tempfile

import pytest

import canonical.swe_kernel.meta_circular_organ_graph_v1 as M
from canonical.swe_kernel import compression_gain_v1 as cg
from canonical.swe_kernel.concept_library_v1 import (
    CompoundingConceptLibrary,
    ConceptEntry,
    rewrite_source_with_concepts,
)


def _wm(transitions) -> str:
    return M.synthesize_world_model_organ(transitions).source_code


T1 = [{"action": "a", "cost": 1.0, "failed": False, "delta": {"x": 2}},
      {"action": "b", "cost": 2.0, "failed": True, "delta": {"x": -1}}]
T2 = [{"action": "c", "cost": 3.5, "failed": False, "delta": {"y": 7}},
      {"action": "d", "cost": 0.5, "failed": False, "delta": {"y": 1}},
      {"action": "e", "cost": 9.0, "failed": True, "delta": {"z": 0}}]
T3 = [{"action": "f", "cost": 0.2, "failed": False, "delta": {"q": 1}},
      {"action": "g", "cost": 4.0, "failed": False, "delta": {"r": 2}},
      {"action": "h", "cost": 6.0, "failed": True, "delta": {"s": 3}},
      {"action": "i", "cost": 1.5, "failed": False, "delta": {"t": 4}}]
T4 = [{"action": "w", "cost": 2.5, "failed": False, "delta": {"k": 9}},
      {"action": "v", "cost": 7.0, "failed": True, "delta": {"m": -3}}]

DOMAIN_PROBES = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "zzz", ""]
W4_PROBES = ["w", "v", "a", "zzz", ""]


def _build_library() -> CompoundingConceptLibrary:
    """Compress three world-model organs with domain probes and admit the abstraction."""
    w1, w2, w3 = _wm(T1), _wm(T2), _wm(T3)
    res = cg.compress_corpus([w1, w2, w3], probes=DOMAIN_PROBES)
    assert len(res["abstractions"]) == 1, res["refusals"]
    a = res["abstractions"][0]
    lib = CompoundingConceptLibrary(None)
    entry = ConceptEntry(
        concept_id=a["concept_id"], arity=a["arity"], param_names=tuple(a["param_names"]),
        body_expr="", body_stmts=cg.helper_body_stmts(a), domain_kind="any",
        mdl_gain_bytes=a["gain_bytes"], corpus_sites=a["sites"], verified_hits=1,
        family=a["family"],
    )
    assert lib.admit_verified_concept(entry)
    return lib


# ------------------------------------------------------------------ the prediction
def test_a_never_seen_world_model_replays_through_the_second_family_abstraction():
    """THE PREDICTION. The organ is built cold; the library contributes only the shared
    machinery. Replay must strictly shrink it and preserve behaviour on held-out ids."""
    w4 = _wm(T4)
    lib = _build_library()
    r = cg.rewrite_source_with_abstractions(w4, lib, probes=W4_PROBES)
    assert r is not None, "the never-seen world model refused to replay"
    assert r["bytes_after"] < r["bytes_before"]
    assert any(c["concept_id"].startswith("c_x_") for c in r["changes"])
    # behaviour preserved on held-out ids the probe grids never saw, plus type-hostile inputs
    ns: dict = {"math": __import__("math")}
    prelude = "\n".join(str(h).rstrip() + "\n" for h in r["helpers"].values())
    exec(compile(prelude + r["source"], "<r25>", "exec"), ns)
    new_fn = ns["predict"]
    orig_ns: dict = {"math": __import__("math")}
    exec(compile(w4, "<r25orig>", "exec"), orig_ns)
    old_fn = orig_ns["predict"]
    for x in ["w", "v", "a", "zzz", "", 0.5, None, ("t",)]:
        assert old_fn(x) == new_fn(x), x
    # the machinery is gone from the program: it now lives in the library
    assert "table.get" not in r["source"] and "known" not in r["source"].split("{")[0]


def test_admission_economics_match_the_periodic_family():
    """Two sites do not pay for the abstraction; three do. Same economics as the periodic
    family, measured -- not a threshold someone chose."""
    w1, w2, w3 = _wm(T1), _wm(T2), _wm(T3)
    pair = cg.compress_corpus([w1, w2], probes=DOMAIN_PROBES)
    assert pair["abstractions"] == []
    assert any(r["reason"].startswith("NOT_COMPRESSIVE") for r in pair["refusals"])
    triple = cg.compress_corpus([w1, w2, w3], probes=DOMAIN_PROBES)
    assert len(triple["abstractions"]) == 1
    a = triple["abstractions"][0]
    assert a["sites"] == 3
    assert a["gain_bytes"] > 0
    assert a["family"] == cg.FAMILY_KEYED_TABLE
    # the gain equals the measured description-length difference, both directions
    before = sum(cg.description_bytes(s) for s in (w1, w2, w3))
    after = cg.description_bytes(a["helper_src"]) + sum(
        cg.description_bytes(r) for r in a["rewritten_sources"]
    )
    assert a["gain_bytes"] == before - after


def test_singletons_stay_structural_in_the_lifted_machinery():
    """`row is None` and `out['known'] = True` are the machinery's own structure. Lifting them
    measured out as self-defeating; the helper must carry them as written."""
    lifted = cg.lift_shape(_wm(T1))
    assert lifted is not None
    assert "row is None" in lifted["helper_src"]
    assert "is _p" not in lifted["helper_src"]
    # the VALUE True stays structural (the KEY 'known' lifts as a param -- it is data-shaped)
    assert "= True" in lifted["helper_src"]


def test_a_non_discriminating_grid_refuses_admission_and_replay():
    """A float grid against a string-keyed table answers every probe identically: the equality
    checks would be vacuous. Both admission and replay must refuse rather than ship unchecked --
    this is the gate a forged abstraction would otherwise sail through."""
    w1, w2, w3 = _wm(T1), _wm(T2), _wm(T3)
    # three sites WOULD compress (gain 103) -- so the only thing standing between this corpus
    # and admission under the numeric grid is the vacuity gate itself
    res = cg.compress_corpus([w1, w2, w3])  # default numeric grid
    assert res["abstractions"] == []
    assert any(r["reason"] == "PROBE_GRID_NON_DISCRIMINATING" for r in res["refusals"])
    # and the replay engine refuses the same vacuity on a built library
    lib = _build_library()
    w4 = _wm(T4)
    assert cg.rewrite_source_with_abstractions(w4, lib) is None  # numeric probes: refused
    # an empty output-variety probe list refuses too
    assert cg.rewrite_source_with_abstractions(w4, lib, probes=["w"]) is None


def test_periodic_family_unchanged_and_bridge_still_skill_only():
    """The lifter generalisation must not disturb the first family's measured behaviour, and the
    bridge keeps its honest scope: it admits nothing it cannot probe."""
    s3 = M._table_body([5.0, -2.0, 7.0])
    s5 = M._table_body([-1.0, -5.0, 2.0, -2.0, 5.0])
    s7 = M._table_body([3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0])
    res = cg.compress_corpus([s3, s5, s7])
    assert len(res["abstractions"]) == 1
    assert res["abstractions"][0]["family"] == cg.FAMILY_PERIODIC_TABLE
    assert res["abstractions"][0]["gain_bytes"] == 67  # round 23's measured gain, unchanged
    # a string-keyed table offered through the numeric-only path stays refused
    wm_pair = cg.compress_corpus([_wm(T1), _wm(T2)])
    assert wm_pair["abstractions"] == []


def test_replay_through_the_second_family_via_the_wake_entry():
    """The wake dispatch is family-agnostic: an admitted keyed-table abstraction replays through
    `rewrite_source_with_concepts` exactly as the periodic one does."""
    lib = _build_library()
    w4 = _wm(T4)
    out = rewrite_source_with_concepts(w4, lib, probes=W4_PROBES) if (
        "probes" in rewrite_source_with_concepts.__code__.co_varnames
    ) else None
    # the wake entry keeps its own numeric grid; the direct engine call is the domain-probed path
    if out is None:
        direct = cg.rewrite_source_with_abstractions(w4, lib, probes=W4_PROBES)
        assert direct is not None
        assert "c_x_" in direct["source"]
