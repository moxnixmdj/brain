"""Round 24: wake replay closes the library loop -- admitted abstractions become programs.

Round 23 measured the compounding half (cold 59 vs armed 35 questions on a never-seen period-12)
but left the loop open at the program layer: `rewrite_source_with_concepts` handled single-
expression concepts only and silently skipped statement-function abstractions -- the ONLY entries
the library admits by compression. Admission without replay is an append-only log, not a memory.

EXPLORATION FINDINGS this round (measured before the prediction, reported honestly):
  * ramp bodies (`x - floor(x/p)*p`) do NOT compress: the abstraction's definition costs more
    than the call sites save. The family is already minimal.
  * world-model organs do not lift (dict-table bodies are outside the lifter's plain-function
    scope). Both negatives are pinned below, so no later session can claim generalization
    without new machinery.

THE PREDICTION, written before the confirmatory run:

> After periods 3, 5 and 7 are solved through the growth loop and their corpus has compressed
> into one admitted abstraction, a NEVER-SEEN period-12 organ -- synthesized through the COLD
> path with a fresh library, so it owes nothing to the library -- is rewritten by the wake pass
> into a form that CALLS the admitted abstraction, preserving behaviour on held-out inputs and
> strictly reducing description length.

A cache cannot satisfy this either: the period-12 block was never met; what the library
contributes is the shared shape. What the measurement decides is whether the library's content
is USABLE, not merely stored.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

import canonical.swe_kernel.meta_circular_organ_graph_v1 as M
from canonical.swe_kernel import compression_gain_v1 as cg
from canonical.swe_kernel.concept_library_v1 import (
    CompoundingConceptLibrary,
    ConceptEntry,
    rewrite_source_with_concepts,
)

BLOCK12 = [7.0, -3.0, 11.0, 2.0, -8.0, 5.0, 13.0, -1.0, 4.0, 9.0, -6.0, 1.0]
PERIOD_BLOCKS = [
    ("op::p3", [5.0, -2.0, 7.0]),
    ("op::p5", [-1.0, -5.0, 2.0, -2.0, 5.0]),
    ("op::p7", [3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0]),
]
HELD_OUT = list(range(-60, 0)) + [60, 61, 137, 500, -500]


def _oracle_for(block):
    world = lambda x: block[int(x) % len(block)]
    return lambda xs: float(world(int(xs[0]))), world


def _seeds(oracle):
    return [((0,), oracle((0,))), ((1,), oracle((1,))), ((2,), oracle((2,)))]


def _build_library(tmp: str) -> CompoundingConceptLibrary:
    lib = CompoundingConceptLibrary(pathlib.Path(tmp) / "build.json")
    for sig, block in PERIOD_BLOCKS:
        oracle, _ = _oracle_for(block)
        g = M.MetaCircularOrganGraph(None, concept_library=lib)
        organ, growth = g._grow_operator_from_evidence(_seeds(oracle), oracle, sig)
        assert organ is not None, (sig, growth)
        g.register_organ(organ)
    return lib


def _world(organ, block) -> int:
    bad = 0
    for x in HELD_OUT:
        ok, val = M._safe_eval_candidate(organ, (x,))
        if not (ok and abs(float(val) - block[int(x) % len(block)]) < 1e-9):
            bad += 1
    return bad


# ------------------------------------------------------------------ the prediction
def test_a_never_seen_organ_replays_through_the_admitted_abstraction():
    """THE PREDICTION. The organ is synthesized COLD (fresh library, no license) so it owes the
    library nothing; the wake pass must rewrite it to call the abstraction, preserve behaviour on
    held-out inputs, and strictly shrink the program."""
    oracle12, world12 = _oracle_for(BLOCK12)
    with tempfile.TemporaryDirectory() as tmp:
        # the cold organ: synthesized with an EMPTY library, on its own
        cold_lib = CompoundingConceptLibrary(pathlib.Path(tmp) / "cold.json")
        assert cold_lib.concepts() == []
        g = M.MetaCircularOrganGraph(None, concept_library=cold_lib)
        grown = g._grow_operator_from_evidence(_seeds(oracle12), oracle12, "op::p12")
        assert grown is not None
        organ, growth = grown
        cold_src = organ.source_code
        assert "_block" in cold_src and "_n" in cold_src

        lib = _build_library(tmp)
        # The wake entry returns SOURCE TEXT -- one return type on every path. It used to hand
        # back the replay engine's report dict on the abstraction branch, so a caller that exec'd
        # the result exec'd a dict; the report itself is asserted directly against the engine.
        direct = cg.rewrite_source_with_abstractions(cold_src, lib)
        assert direct is not None, "the replay engine refused an admitted abstraction"
        report = direct
        assert any(
            c["concept_id"].startswith("c_x_") for c in report["changes"]
        ), report
        # the rewritten program CALLS the abstraction and no longer carries the block inline
        rewritten = str(report["source"])
        entry_return = rewrite_source_with_concepts(cold_src, lib)
        assert isinstance(entry_return, str), entry_return
        # the entry returns the abstraction helper AND the module that calls it, so `_block`
        # survives inside the helper -- it is the machinery, stored once, which is the point.
        assert "c_x_" in entry_return
        assert entry_return.rstrip().endswith("x0)")
        assert "_block" not in entry_return.rsplit("def run(", 1)[-1]
        assert "c_x_" in rewritten
        assert "_block" not in rewritten
        # measured: strictly fewer description bytes, computed not asserted
        assert cg.description_bytes(rewritten) < cg.description_bytes(cold_src)
        assert report["bytes_after"] < report["bytes_before"]
        # behaviour preserved on inputs the probe grid never saw
        exec_ns: dict = {"math": __import__("math")}
        prelude = "\n".join(str(h).rstrip() + "\n" for h in report["helpers"].values())
        exec(compile(prelude + rewritten, "<replay_test>", "exec"), exec_ns)
        fn = exec_ns["run"]
        for x in HELD_OUT:
            assert abs(float(fn(float(x))) - world12(x)) < 1e-9, x
        # and the COLD organ itself was right too: the replay changed cost, not correctness
        assert _world(organ, BLOCK12) == 0


# ------------------------------------------------------------------ the guards
def test_replay_refuses_when_the_library_holds_no_abstraction():
    """No admitted abstraction, no replay: an empty or singleton library is not a memory."""
    oracle12, _ = _oracle_for(BLOCK12)
    with tempfile.TemporaryDirectory() as tmp:
        empty = CompoundingConceptLibrary(pathlib.Path(tmp) / "empty.json")
        assert empty.concepts() == []
        g = M.MetaCircularOrganGraph(None, concept_library=empty)
        grown = g._grow_operator_from_evidence(_seeds(oracle12), oracle12, "op::p12")
        assert grown is not None
        organ, _ = grown
        assert rewrite_source_with_concepts(organ.source_code, empty) is None
        # a singleton primitive (gain 0, sites 1) must not license a replay either
        single = CompoundingConceptLibrary(pathlib.Path(tmp) / "single.json")
        e = ConceptEntry(
            concept_id="c_solo", arity=1, param_names=("x0",), body_expr="x0 + 1",
            domain_kind="any", mdl_gain_bytes=0, corpus_sites=1, verified_hits=1,
        )
        assert single.admit_verified_concept(e)
        assert rewrite_source_with_concepts(organ.source_code, single) is None


def test_replay_refuses_a_library_entry_that_would_change_behaviour():
    """Fail-closed against a corrupted library: a shape-matching entry whose body computes
    something else must be caught by the probe grid, never shipped as a 'reuse'."""
    oracle12, _ = _oracle_for(BLOCK12)
    with tempfile.TemporaryDirectory() as tmp:
        lib = _build_library(tmp)
        # forge a same-shape but WRONG abstraction (off-by-one modulus length) with a fresh id
        wrong = (
            "def c_wrong(_p0, x0):\n"
            "    _block = _p0\n"
            "    _n = len(_block) + 1\n"
            "    return _block[int(math.floor(x0) - math.floor(x0 / _n) * _n)]\n"
        )
        lifted = cg.lift_shape(wrong)
        # sanity: the forged body really does differ on the probe grid
        good_helper = next(
            c for c in lib.concepts() if c.family == cg.FAMILY_PERIODIC_TABLE
        ).render_helper_def()
        f_good = cg._exec_fn(good_helper, cg._helper_name_of(good_helper))
        f_wrong = cg._exec_fn(wrong, "c_wrong")
        assert any(f_good(BLOCK12, float(x)) != f_wrong(BLOCK12, float(x)) for x in cg._PROBE_INPUTS)
        e = ConceptEntry(
            concept_id="c_wrong", arity=2, param_names=("_p0", "x0"), body_expr="",
            body_stmts=lifted["helper_src"].split("\n", 1)[1],
            domain_kind="any", mdl_gain_bytes=50, corpus_sites=3, verified_hits=1,
            family=cg.FAMILY_PERIODIC_TABLE,
        )
        lib.admit_verified_concept(e)
        g = M.MetaCircularOrganGraph(None, concept_library=lib)
        grown = g._grow_operator_from_evidence(_seeds(oracle12), oracle12, "op::p12_probe")
        assert grown is not None
        organ, _ = grown
        rewritten = rewrite_source_with_concepts(organ.source_code, lib)
        if rewritten is not None:
            # if anything is returned, it must be the GOOD abstraction's rewrite, never c_wrong
            assert "c_wrong" not in str(rewritten), rewritten
        # and a direct replay against ONLY the forged entry must refuse outright
        forged_only = CompoundingConceptLibrary(pathlib.Path(tmp) / "forged.json")
        forged_only.admit_verified_concept(e)
        assert rewrite_source_with_concepts(organ.source_code, forged_only) is None


def test_the_exploration_negatives_are_pinned():
    """Ramps do not compress; a singleton cannot replay. Pinning the negatives so a later
    session cannot claim the mechanism generalised without new machinery."""
    r3 = M._periodic_body(3, floor_convention=True)
    r7 = M._periodic_body(7, floor_convention=True)
    res = cg.compress_corpus([r3, r7])
    assert res["abstractions"] == []
    assert any(r["reason"].startswith("NOT_COMPRESSIVE") for r in res["refusals"])
    with tempfile.TemporaryDirectory() as tmp:
        empty = CompoundingConceptLibrary(pathlib.Path(tmp) / "e.json")
        assert rewrite_source_with_concepts(r3, empty) is None


def test_expression_concepts_and_abstractions_coexist_in_one_library():
    """The dispatch ordering: the expression pass runs first and the abstraction replay is only
    consulted when it produces nothing. The positive expression path is pinned by the creature
    suite (`test_sleep_admits_policy_concepts_and_wake_rewrites_the_organ`) on factory-shaped
    sources; this pins the COEXISTENCE case -- a library holding both kinds, where the replay
    must still fire despite the expression concept present."""
    with tempfile.TemporaryDirectory() as tmp:
        lib = _build_library(tmp)
        e = ConceptEntry(
            concept_id="c_never_matches", arity=1, param_names=("x0",), body_expr="x0 * 999",
            domain_kind="any", mdl_gain_bytes=4, corpus_sites=2, verified_hits=1,
        )
        assert lib.admit_verified_concept(e)
        oracle12, _ = _oracle_for(BLOCK12)
        g = M.MetaCircularOrganGraph(None, concept_library=lib)
        grown = g._grow_operator_from_evidence(_seeds(oracle12), oracle12, "op::p12")
        assert grown is not None
        organ, _ = grown
        rewritten = rewrite_source_with_concepts(organ.source_code, lib)
        assert rewritten is not None
        # the wake entry returns the rewritten SOURCE; the expression concept must not appear,
        # the abstraction call must
        assert "c_never_matches" not in rewritten
        assert "c_x_" in rewritten
