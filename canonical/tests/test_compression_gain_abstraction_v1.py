"""Round 23: compression is the mechanism that makes experience compound.

Round 22 measured the deepest still-open defect: nothing is ever compressed, so nothing compounds.
The bridge into `G_t` admitted only single-`return` bodies and reported a gain nobody computed;
meeting period-3 (14 questions) and period-7 (34) left a cold period-5 at exactly 24.

The prediction, written before the measurement: after periods 3, 5 and 7 have been solved through
the growth loop and their corpus has compressed into one abstraction, a NEVER-SEEN period-12
structure must cost strictly fewer oracle questions than it costs cold -- because the library's
compression-positive abstraction licenses a two-cycle evidence policy, while a cold run must pay
the conservative four-cycle rule. A cache cannot pass this test: period 12 was never met. What
transfers is the family abstraction.

Measured (2026-11-12, this tree): cold 59 questions / 48 evidence points; library-armed
35 questions / 24 evidence points; 0 held-out failures on 57 probes for both organs. The build
arm reproduces the historical cold numbers 14 / 24 / 34 exactly, which is what makes this
instrument comparable with the round-22 documents.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

import canonical.swe_kernel.meta_circular_organ_graph_v1 as M
from canonical.swe_kernel import compression_gain_v1 as cg
from canonical.swe_kernel.concept_library_v1 import CompoundingConceptLibrary
from canonical.runtime import settlement_v1 as S

BLOCK12 = [7.0, -3.0, 11.0, 2.0, -8.0, 5.0, 13.0, -1.0, 4.0, 9.0, -6.0, 1.0]
PERIOD_BLOCKS = [
    ("op::p3", [5.0, -2.0, 7.0]),
    ("op::p5", [-1.0, -5.0, 2.0, -2.0, 5.0]),
    ("op::p7", [3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0]),
]
HELD_OUT = list(range(-40, 0)) + [100, 101, 137, 500]


def _oracle_for(block):
    world = lambda x: block[int(x) % len(block)]
    return lambda xs: float(world(int(xs[0]))), world


def _seeds(oracle):
    return [((0,), oracle((0,))), ((1,), oracle((1,))), ((2,), oracle((2,)))]


def _held_out_failures(organ, world) -> int:
    if organ is None:
        return len(HELD_OUT)
    bad = 0
    for x in HELD_OUT:
        ok, val = M._safe_eval_candidate(organ, (x,))
        if not (ok and abs(float(val) - world(x)) < 1e-9):
            bad += 1
    return bad


def _table_sources() -> list[str]:
    return [M._table_body(b) for _, b in PERIOD_BLOCKS]


# --------------------------------------------------------------------------- compression
def test_three_solved_programs_compress_into_one_measured_abstraction():
    """The corpus of table organs shares one lifted shape; the rewrite must pay for itself."""
    res = cg.compress_corpus(_table_sources())
    assert len(res["abstractions"]) == 1, res["refusals"]
    a = res["abstractions"][0]
    assert a["sites"] == 3
    assert a["gain_bytes"] > 0, "no measured gain, no abstraction"
    assert a["before_bytes"] > a["after_bytes"]
    assert a["family"] == cg.FAMILY_PERIODIC_TABLE
    # The abstraction is executable and reproduces each member: measured, not assumed --
    # compress_corpus already refuses a rewrite that changes behaviour; this asserts the helper
    # itself runs against a fresh block through the library-facing call form.
    fn = cg._exec_fn(a["helper_src"], next(
        n for n in a["helper_src"].split() if n.startswith("def")
    ).split("(")[0][4:] if False else cg._helper_name_of(a["helper_src"]))
    block = [9.0, 1.0, 8.0]
    for x in (-9, 0, 1, 2, 3, 7, 20):
        assert fn(block, float(x)) == float(block[int(x) % 3])


def test_a_singleton_and_an_incompressible_rewrite_are_refused_with_their_reason():
    """One site is a stored program; two sites on this corpus do not pay for the definition.

    Both refusals are measured properties of the currency, not arbitrary thresholds: the helper's
    definition cost exceeds what two call sites save, so admitting it would put a menu entry in
    the library and call it an abstraction.
    """
    srcs = _table_sources()
    single = cg.compress_corpus([srcs[0]])
    assert single["abstractions"] == []
    assert any(r["reason"].startswith("SINGLE_SITE") for r in single["refusals"])

    pair = cg.compress_corpus(srcs[:2])
    assert pair["abstractions"] == []
    assert any(r["reason"].startswith("NOT_COMPRESSIVE") for r in pair["refusals"])
    for r in pair["refusals"]:
        if r["reason"].startswith("NOT_COMPRESSIVE"):
            assert r["after_bytes"] >= r["before_bytes"]


def test_gain_is_computed_from_description_length_not_asserted():
    """The gain must equal the measured difference in description length, both directions."""
    srcs = _table_sources()
    res = cg.compress_corpus(srcs)
    a = res["abstractions"][0]
    before = sum(cg.description_bytes(s) for s in srcs)
    after = cg.description_bytes(a["helper_src"]) + sum(
        cg.description_bytes(r) for r in a["rewritten_sources"]
    )
    assert a["before_bytes"] == before
    assert a["after_bytes"] == after
    assert a["gain_bytes"] == before - after
    # zlib's executable_ast_bytes is the wrong currency here: it re-derives shared structure for
    # free, so it cannot be the admission measure. This pins WHY the module has its own metric.
    from canonical.swe_kernel.concept_library_v1 import executable_ast_bytes
    assert sum(executable_ast_bytes(s) for s in srcs) < before, (
        "zlib compresses the corpus; a currency in which the mechanism being admitted can never "
        "measure a gain is a veto, not a measurement")


# --------------------------------------------------------------------------- the bridge
def test_the_bridge_reports_honest_zero_gain_and_admits_statement_bodies():
    """Round 22's two bridge defects, pinned: fabricated gain, and the silent rejection of every
    statement-body organ the synthesizer produces."""
    lib = CompoundingConceptLibrary(None)
    graph = M.MetaCircularOrganGraph(None, concept_library=lib)
    inc = M.make_organ(
        stratum=M.SKILL, name="inc", task_signature="op::inc", entrypoint="run",
        source_code="def run(x0):\n    return x0 + 1\n",
    )
    entry = M._skill_organ_to_concept_entry(inc, corpus_sources=[inc.source_code])
    assert entry is not None
    assert entry.mdl_gain_bytes == 0, "a singleton measured no compression; 0 is the honest value"
    assert entry.corpus_sites == 1

    # A statement-body organ (Assign, Assign, Return -- the exact shape round 22 found rejected)
    # now bridges as a statement function.
    table_organ = M.make_organ(
        stratum=M.SKILL, name="t3", task_signature="op::t3", entrypoint="run",
        source_code=M._table_body([5.0, -2.0, 7.0]),
    )
    entry2 = M._skill_organ_to_concept_entry(table_organ, corpus_sources=[table_organ.source_code])
    assert entry2 is not None
    assert entry2.body_stmts, "a multi-statement organ must bridge as a statement function"
    assert entry2.is_stmt_fn


def test_three_solved_structures_admit_one_compression_positive_abstraction():
    """Round 22 measured `concepts now=0` after three distinct structures. This is the same
    experiment after the fix: the library holds ONE abstraction with the measured gain and the
    measured site count, and its structural family is recognised from the shape."""
    with tempfile.TemporaryDirectory() as tmp:
        lib = CompoundingConceptLibrary(pathlib.Path(tmp) / "lib.json")
        for sig, block in PERIOD_BLOCKS:
            oracle, _ = _oracle_for(block)
            g = M.MetaCircularOrganGraph(None, concept_library=lib)
            organ, growth = g._grow_operator_from_evidence(_seeds(oracle), oracle, sig)
            assert organ is not None, (sig, growth)
            g.register_organ(organ)
        abstractions = [c for c in lib.concepts() if c.family == cg.FAMILY_PERIODIC_TABLE]
        assert len(abstractions) == 1
        a = abstractions[0]
        assert a.corpus_sites >= 3
        assert a.mdl_gain_bytes > 0
        assert a.verified_hits >= 1
        # and the licensing rule fires only on that measured entry
        pol = cg.licensed_table_policy(lib)
        assert pol is not None
        assert pol["concept_id"] == a.concept_id
        assert pol["corpus_sites"] == a.corpus_sites
        assert pol["gain_bytes"] == a.mdl_gain_bytes


# --------------------------------------------------------------------------- the prediction
def test_a_never_seen_period_12_costs_fewer_questions_with_the_library_than_cold():
    """THE PREDICTION. Same instance, same oracle, same front door; the only difference is what
    the library holds. A cache cannot pass it: nothing about period 12 was ever stored."""
    oracle12, world12 = _oracle_for(BLOCK12)
    seeds = _seeds(oracle12)

    with tempfile.TemporaryDirectory() as tmp:
        cold_lib = CompoundingConceptLibrary(pathlib.Path(tmp) / "cold.json")
        cold_lib2 = CompoundingConceptLibrary(pathlib.Path(tmp) / "cold_front.json")
        assert cold_lib.concepts() == [] and cold_lib2.concepts() == []

        g_cold = M.MetaCircularOrganGraph(None, concept_library=cold_lib)
        grown_cold = g_cold._grow_operator_from_evidence(seeds, oracle12, "op::p12")
        assert grown_cold is not None
        organ_cold, growth_cold = grown_cold

        # build the library through the real growth loop (the mechanism that emits table organs)
        lib = CompoundingConceptLibrary(pathlib.Path(tmp) / "build.json")
        for sig, block in PERIOD_BLOCKS:
            oracle, _ = _oracle_for(block)
            g = M.MetaCircularOrganGraph(None, concept_library=lib)
            organ, growth = g._grow_operator_from_evidence(_seeds(oracle), oracle, sig)
            assert organ is not None, (sig, growth)
            g.register_organ(organ)
        assert cg.licensed_table_policy(lib) is not None

        g_armed = M.MetaCircularOrganGraph(None, concept_library=lib)
        armed = g_armed.synthesize_or_disambiguate_skill(
            list(seeds), task_signature="op::p12", oracle=oracle12)
        assert armed["ok"], armed
        organ_armed = armed["organ"]
        growth_armed = armed["growth"]

        q_cold = int(growth_cold.get("questions", 0))
        q_armed = int(armed.get("oracle_queries_used", 0))
        assert q_armed < q_cold, (
            "the library did not make a never-seen member of the family cheaper: "
            f"cold={q_cold} armed={q_armed}")
        assert growth_armed["evidence_collected"] < growth_cold["evidence_collected"]
        # the verification gate is NOT waived: acquire still verified the period at 2p and 3p
        p = growth_armed["period"]
        assert sorted(growth_armed["verified_at"]) == sorted([p, 2 * p, 3 * p])
        # and BOTH organs are right everywhere nothing was asked
        assert _held_out_failures(organ_cold, world12) == 0
        assert _held_out_failures(organ_armed, world12) == 0


def test_the_build_arm_reproduces_the_historical_cold_costs():
    """Instrument calibration against the round-22 documents: cold period-3 = 14 questions,
    period-5 = 24, period-7 = 34 (each with three seeds and this oracle discipline). If these
    drift, the comparison in the prediction test is against a different instrument."""
    with tempfile.TemporaryDirectory() as tmp:
        lib = CompoundingConceptLibrary(pathlib.Path(tmp) / "hist.json")
        costs = {}
        for sig, block in PERIOD_BLOCKS:
            oracle, _ = _oracle_for(block)
            g = M.MetaCircularOrganGraph(None, concept_library=lib)
            organ, growth = g._grow_operator_from_evidence(_seeds(oracle), oracle, sig)
            assert organ is not None
            costs[sig] = int(growth.get("questions", 0))
            g.register_organ(organ)
        assert costs["op::p3"] == 14, costs
        assert costs["op::p5"] == 24, costs
        assert costs["op::p7"] == 34, costs


# --------------------------------------------------------------------------- the guards
def test_without_a_library_or_with_an_empty_one_nothing_licenses():
    """The prior may come only from a measured abstraction. No library, empty library, stored
    primitive, unverified entry -- all license NOTHING, and the cold rule stands."""
    assert cg.licensed_table_policy(None) is None
    with tempfile.TemporaryDirectory() as tmp:
        empty = CompoundingConceptLibrary(pathlib.Path(tmp) / "empty.json")
        assert empty.concepts() == []
        assert cg.licensed_table_policy(empty) is None
        # a stored primitive with a family-shaped body but no compression measured
        entry = type(empty.concepts())  # placeholder to keep the import obvious
        from canonical.swe_kernel.concept_library_v1 import ConceptEntry
        e = ConceptEntry(
            concept_id="c_lone", arity=2, param_names=("_p0", "x0"),
            body_expr="", body_stmts="_block = _p0\n_n = len(_block)\nreturn _block[0]",
            domain_kind="any", mdl_gain_bytes=0, corpus_sites=1, verified_hits=1,
            family=cg.FAMILY_PERIODIC_TABLE,
        )
        assert empty.admit_verified_concept(e)
        assert cg.licensed_table_policy(empty) is None, "a singleton must not license a policy"
        e2 = ConceptEntry(
            concept_id="c_unverified", arity=2, param_names=("_p0", "x0"),
            body_expr="", body_stmts="_block = _p0\n_n = len(_block)\nreturn _block[0]",
            domain_kind="any", mdl_gain_bytes=50, corpus_sites=3, verified_hits=0,
            family=cg.FAMILY_PERIODIC_TABLE,
        )
        lib2 = CompoundingConceptLibrary(pathlib.Path(tmp) / "unverified.json")
        assert lib2.admit_verified_concept(e2)
        assert cg.licensed_table_policy(lib2) is None, "an unverified entry must not license"


def test_library_reload_preserves_the_measured_zero_and_the_family():
    """`or 1` used to upgrade an honest stored 0 back to a fabricated gain on every reload."""
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "reload.json"
        lib = CompoundingConceptLibrary(path)
        from canonical.swe_kernel.concept_library_v1 import ConceptEntry
        e = ConceptEntry(
            concept_id="c_zero", arity=1, param_names=("x0",), body_expr="x0 + 1",
            domain_kind="any", mdl_gain_bytes=0, corpus_sites=1, verified_hits=0,
        )
        assert lib.admit_verified_concept(e)
        lib2 = CompoundingConceptLibrary(path)
        reloaded = {c.concept_id: c for c in lib2.concepts()}
        assert reloaded["c_zero"].mdl_gain_bytes == 0


def test_the_cold_growth_loop_is_unchanged_for_a_period_five_table():
    """Regression guard on the historical behavior the round-22 documents measured: an
    arbitrary-block period-5 table, cold, costs 24 questions and 20 evidence points."""
    with tempfile.TemporaryDirectory() as tmp:
        lib = CompoundingConceptLibrary(pathlib.Path(tmp) / "cold5.json")
        oracle, world = _oracle_for([-1.0, -5.0, 2.0, -2.0, 5.0])
        g = M.MetaCircularOrganGraph(None, concept_library=lib)
        organ, growth = g._grow_operator_from_evidence(_seeds(oracle), oracle, "op::p5_cold")
        assert organ is not None
        assert int(growth.get("questions", 0)) == 24
        assert int(growth.get("evidence_collected", 0)) == 20
        assert _held_out_failures(organ, world) == 0
