"""The LIVE loop: experience -> library -> reuse, measured where the creature actually runs.

Rounds 23-25 measured compress -> admit -> replay by calling `compression_gain_v1` directly and
supplying the probe domain from the test. That measured the DECOMPRESSOR. The owner's question is
about the live path, and the live path is `MetaCircularOrganGraph.register_organ` feeding
`CompoundingConceptLibrary` feeding `rewrite_source_with_concepts` with nobody naming a domain.

Measured on that path, before this change:

    live curve (world-model organs, one family, no caller probes)
      organs  library  abstractions  never-seen replay
           1        0              0  REFUSED
           2        0              0  REFUSED
           3        0              0  REFUSED
    identifier: 3 organs offered -> 1 distinct id -> 1 slot

Four defects, each one measured and each one a place where "learn it once and keep it" failed on
the CREATURE rather than in a test:

  1. **No probe domain at the live entry.** `_skill_organ_to_concept_entry` called
     `compress_corpus(corpus)` with no `probes`, so the numeric default grid ran against a
     string-keyed table; every probe answered identically and the (correct) vacuity gate refused.
     Fixed by `compress_corpus`'s new sibling `admit_corpus_abstraction`, which derives the domain
     from the corpus literals instead of requiring a human to name it. No gate was loosened: the
     same behaviour-preservation and discrimination checks run, on a domain that exists.
  2. **A comparator that assumed total functions.** Both gates read ANY exception as a
     disagreement, so "identical except where the table does not cover the input" -- which is what
     every keyed lookup is -- was reported as changed behaviour and refused. Now both compare
     partial functions: agreement wherever either form is defined, an exception is an outcome.
  3. **One identifier for every organ.** The bridge built `"c_" + organ_id.replace(
     "organ_skill_", "")[:18]`, which leaves `c_organ_skill_` for every SKILL organ: the library
     could hold exactly one stored program. Now the id is a hash of the source
     (`cg.concept_id_for_source`).
  4. **A gate that excluded the family the loop was built for.** Admission fired only for
     `organ.stratum == SKILL`, but the second family is emitted by `synthesize_world_model_organ`,
     a WORLD_MODEL organ -- so the live writer for that family did not exist. Admission now covers
     SKILL and WORLD_MODEL (`_ADMISSIBLE_STRATA`); PERCEPTOR and VERIFIER stay out because lifting
     a parser's literals probes it with tokens it was never written to accept.

One contract defect fell out while wiring it: `rewrite_source_with_concepts` returned the replay
engine's REPORT DICT on the abstraction branch and source text everywhere else, so a caller that
exec'd a successful replay exec'd a dict (`TypeError`). It now returns source text on every path.

What this does NOT claim: nothing here is a new mechanism, no capability is registered, no family
flips, `truth.achieved` stays false, and no external oracle judged anything. The live curve below
is producer-run on one machine, $0, zero model dependency.
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

#: Four organs of ONE structural family: byte-identical machinery, one dict literal of per-organ
#: data. T4 is never registered -- it is the never-seen member the prediction is about.
T1 = [{"action": "a", "cost": 1.0, "failed": False, "delta": {"x": 2}},
      {"action": "b", "cost": 2.0, "failed": True, "delta": {"x": -1}}]
T2 = [{"action": "c", "cost": 3.5, "failed": False, "delta": {"y": 7}},
      {"action": "d", "cost": 0.5, "failed": False, "delta": {"y": 1}}]
T3 = [{"action": "f", "cost": 0.2, "failed": False, "delta": {"q": 1}},
      {"action": "g", "cost": 4.0, "failed": False, "delta": {"r": 2}}]
T4 = [{"action": "w", "cost": 2.5, "failed": False, "delta": {"k": 9}},
      {"action": "v", "cost": 7.0, "failed": True, "delta": {"m": -3}}]

HELD_OUT = ["w", "v", "nope", "", "W", "a"]


def _html(transitions):
    organ = M.synthesize_world_model_organ(transitions)
    assert organ is not None
    return organ


def _live(tmp: str, tables):
    lib = CompoundingConceptLibrary(pathlib.Path(tmp) / "lib.json")
    graph = M.MetaCircularOrganGraph(pathlib.Path(tmp) / "graph.json", concept_library=lib)
    for i, table in enumerate(tables):
        graph.register_organ(M.synthesize_world_model_organ(table, name=f"wm{i}"))
    return graph, lib


def _behaviour(source: str, entry: str, values):
    ns: dict = {}
    exec(compile(source, "<live_replay>", "exec"), ns)
    fn = ns[entry]
    return [fn(v) for v in values]


# --------------------------------------------------------------- the prediction
def test_the_live_path_learns_from_experience_and_the_library_shows_the_curve():
    """THE PREDICTION: after three organs of one family are experienced through the LIVE entry
    point, a never-seen fourth replays strictly smaller with behaviour preserved -- and the curve
    shows the abstraction arriving at the third site, not at the first.

    A cache cannot pass this: T4's action ids never appear in any registered organ.
    """
    unseen = _html(T4).source_code
    with tempfile.TemporaryDirectory() as tmp:
        graph, lib = _live(tmp, [T1, T2, T3])
        entries = lib.concepts()
        assert len(entries) == 3, entries
        abstractions = [c for c in entries if c.family]
        assert len(abstractions) == 1
        a = abstractions[0]
        assert a.family == cg.FAMILY_KEYED_TABLE
        assert a.mdl_gain_bytes > 0 and a.corpus_sites >= 3

        rewritten = rewrite_source_with_concepts(unseen, lib)
        assert isinstance(rewritten, str), rewritten
        assert a.concept_id in rewritten
        # The PROGRAM shrank; the helper is stored once and shared by the whole family, which is
        # where the win amortises (round 25's economics). Counting the helper into one program
        # would make reuse look like a loss, so both numbers are stated, neither hidden.
        program = rewritten.rsplit("def predict(", 1)[-1]
        cold_program = unseen.rsplit("def predict(", 1)[-1]
        assert cg.description_bytes("def predict(" + program) < cg.description_bytes(unseen)
        assert len("def predict(" + program) < len(cold_program)
        # the engine's own default is the numeric grid, which this domain cannot see: it is the
        # WAKE ENTRY that derives a domain, and the derived one is what a caller would pass.
        report = cg.rewrite_source_with_abstractions(
            unseen, lib, probes=cg.derive_probe_domain([unseen])
        )
        assert report is not None
        # and with the numeric grid it refuses, which is the vacuity gate doing its job
        assert cg.rewrite_source_with_abstractions(unseen, lib) is None
        assert report["bytes_after"] < report["bytes_before"]
        # behaviour preserved on inputs no organ in the corpus contains
        assert _behaviour(rewritten, "predict", HELD_OUT) == _behaviour(unseen, "predict", HELD_OUT)

        # the library itself is what replayed: re-entering the wake pass from a FRESH library
        # object on the same file finds the abstraction again (it is stored, not memoised)
        reloaded = CompoundingConceptLibrary(pathlib.Path(tmp) / "lib.json")
        again = rewrite_source_with_concepts(unseen, reloaded)
        assert isinstance(again, str) and a.concept_id in again


def test_the_curve_is_one_store_at_one_two_and_an_abstraction_at_three():
    """The shape of "learn once": a single experience is a STORED PROGRAM (gain 0), never a rule.
    The abstraction appears at the third site, which is the measured economics from round 23 --
    pinned here on the live path so a future change cannot move it silently."""
    with tempfile.TemporaryDirectory() as tmp:
        rows = []
        lib = CompoundingConceptLibrary(pathlib.Path(tmp) / "curve.json")
        graph = M.MetaCircularOrganGraph(pathlib.Path(tmp) / "g.json", concept_library=lib)
        for i, table in enumerate((T1, T2, T3), start=1):
            graph.register_organ(M.synthesize_world_model_organ(table, name=f"c{i}"))
            entries = lib.concepts()
            rows.append((i, len(entries), sum(1 for c in entries if c.family)))
        assert rows[0][1:] == (1, 0), rows
        assert rows[1][1:] == (2, 0), rows
        assert rows[2][1:] == (3, 1), rows


# --------------------------------------------------------------- the gates, unchanged
def test_a_domain_the_corpus_does_not_supply_still_refuses():
    """The derived domain is a PRIOR, not a permission slip. One site is a stored program, and a
    corpus that cannot compress is refused with its reason -- exactly as before."""
    single = cg.admit_corpus_abstraction([_html(T1).source_code])
    assert single["abstractions"] == []
    assert single["probe_domain"] == "DERIVED_FROM_CORPUS"
    assert any("SINGLE_SITE" in r["reason"] for r in single["refusals"])

    # a corpus with no liftable literals at all has no domain to derive: refuse by name
    empty = cg.admit_corpus_abstraction(["def run(x):\n    return None\n"])
    assert empty["abstractions"] == []


def test_a_non_discriminating_domain_is_still_refused():
    """The vacuity gate is the one a forged abstraction sails through. It must still fire when the
    caller supplies a grid that answers identically -- a supplied domain is not automatically a
    good one."""
    sources = [_html(t).source_code for t in (T1, T2, T3)]
    res = cg.compress_corpus(sources, probes=[0, 1, 2])  # numeric grid, string-keyed table
    assert res["abstractions"] == []
    assert any(r["reason"] == "PROBE_GRID_NON_DISCRIMINATING" for r in res["refusals"])


def test_two_different_organs_do_not_share_one_library_slot():
    """The bridge's old id was `"c_" + organ_id.replace("organ_skill_", "")[:18]` -- eighteen
    characters of a twenty-character hash after a ten-character prefix leaves `organ_skill`, so
    EVERY skill organ mapped to `c_organ_skill_`. Measured: three organs, one id, one slot."""
    with tempfile.TemporaryDirectory() as tmp:
        lib = CompoundingConceptLibrary(pathlib.Path(tmp) / "ids.json")
        ids = []
        for i, table in enumerate((T1, T2, T3)):
            organ = M.make_organ(
                stratum=M.SKILL, name=f"o{i}", task_signature="world_model::action_delta",
                entrypoint="predict", source_code=_html(table).source_code,
            )
            entry = M._skill_organ_to_concept_entry(organ, corpus_sources=[organ.source_code])
            assert entry is not None
            ids.append(entry.concept_id)
            assert lib.admit_verified_concept(entry)
        assert len(set(ids)) == 3, ids
        assert len(lib.concepts()) == 3


def test_the_same_source_always_gets_the_same_id():
    """A replay that names a concept has to find it after a restart: the id is a function of the
    bytes and of nothing else."""
    src = _html(T1).source_code
    assert cg.concept_id_for_source(src) == cg.concept_id_for_source(src)
    assert cg.concept_id_for_source(src) != cg.concept_id_for_source(_html(T2).source_code)
    assert cg.concept_id_for_source(src).isidentifier()


def test_the_writer_of_the_second_family_can_actually_reach_the_library():
    """The stratum gate admitted SKILL organs only, while the second family is emitted by
    `synthesize_world_model_organ` (a WORLD_MODEL organ). The live writer for the family the
    mechanism was measured on did not exist."""
    assert M.WORLD_MODEL in M._ADMISSIBLE_STRATA
    assert M.SKILL in M._ADMISSIBLE_STRATA
    assert M.PERCEPTOR not in M._ADMISSIBLE_STRATA
    assert M.VERIFIER not in M._ADMISSIBLE_STRATA


def test_the_wake_entry_returns_source_text_on_every_path():
    """It returned the replay engine's report dict on the abstraction branch and source text
    everywhere else, so three live registrations produced a library that replayed, and the replay
    raised `TypeError: compile() arg 1 must be a string` at the first use."""
    unseen = _html(T4).source_code
    with tempfile.TemporaryDirectory() as tmp:
        _, lib = _live(tmp, [T1, T2, T3])
        out = rewrite_source_with_concepts(unseen, lib)
        assert isinstance(out, str)
        compile(out, "<replay>", "exec")  # the artifact a caller execs is a program


def test_the_supplied_domain_still_wins_when_a_caller_has_one():
    """A caller with real domain knowledge must be able to say so, and the report must say which
    domain was used, so no measurement conflates the derived path with the supplied one."""
    sources = [_html(t).source_code for t in (T1, T2, T3)]
    supplied = cg.admit_corpus_abstraction(sources, probes=["a", "c", "f", "zzz"])
    derived = cg.admit_corpus_abstraction(sources)
    assert supplied["probe_domain"] == "SUPPLIED"
    assert derived["probe_domain"] == "DERIVED_FROM_CORPUS"
    # both admit the same family; the derived path simply did not need the human
    assert [a["family"] for a in supplied["abstractions"]] == [
        a["family"] for a in derived["abstractions"]
    ] == [cg.FAMILY_KEYED_TABLE]
