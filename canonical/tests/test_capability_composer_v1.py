"""Tests for PROJECT_BRAIN_CAPABILITY_COMPOSER_V1.

The composer claims one thing: that the 67 bound capabilities form one
connected, executable graph, and that a goal token can be turned into a valid
firing order.  These tests hold it to that.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))

import capability_composer_v1 as C

G = C.graph()
EXT = C.external_tokens(G)


# --------------------------------------------------------------------------- #
# graph shape
# --------------------------------------------------------------------------- #
def test_graph_covers_every_bound_capability():
    assert len(G) == 68


def test_external_prerequisites_are_never_produced():
    provided = {t for s in G.values() for t in s["provides"]}
    assert len(EXT) == 30
    assert set(EXT) & provided == set()


def test_capabilities_that_need_nothing_from_the_world():
    order, _ = C.forward_closure([], G)
    assert len(order) == 17


def test_producers_and_consumers_agree():
    for token in EXT:
        assert C.producers(token, G) == []
        assert C.consumers(token, G)
    for cid, spec in G.items():
        for token in spec["provides"]:
            assert cid in C.producers(token, G)


# --------------------------------------------------------------------------- #
# forward closure
# --------------------------------------------------------------------------- #
def test_full_closure_fires_every_capability():
    order, have = C.forward_closure(EXT, G)
    assert len(order) == 68
    assert len(have) == 121


def test_firing_order_is_topologically_valid():
    """Every capability fires only once everything it requires is available."""
    order, _ = C.forward_closure(EXT, G)
    have = set(EXT)
    for cid in order:
        assert not C.missing(cid, have, G), f"{cid} fired with requirements unmet"
        have |= set(G[cid]["provides"])


def test_nothing_is_unreachable_once_the_world_supplies_prerequisites():
    assert C.unreachable(EXT, G) == []


def test_starved_closure_leaves_the_rest_unreachable():
    order, _ = C.forward_closure([], G)
    assert len(C.unreachable([], G)) == 68 - 17


# --------------------------------------------------------------------------- #
# planning
# --------------------------------------------------------------------------- #
def test_plan_produces_the_four_step_evidence_chain():
    chain = C.plan(EXT, "evidence.claim.exact_quoted_bound", G)
    assert chain == [
        "source.objective_relevance.rank.bm25",
        "source.evidence.extract.objective_grounded.stdlib",
        "evidence.claim_relation.generic_units.stdlib",
        "evidence.claim_spec.bind.explicit_comparison.stdlib",
    ]


def test_planned_chain_is_itself_a_valid_firing_order():
    chain = C.plan(EXT, "evidence.claim.exact_quoted_bound", G)
    have = set(EXT)
    for cid in chain:
        assert not C.missing(cid, have, G), f"{cid} scheduled with requirements unmet"
        have |= set(G[cid]["provides"])


def test_plan_of_a_goal_already_held_needs_nothing():
    assert C.plan(EXT, EXT[0], G) == []


def test_plan_of_an_unproducible_goal_is_none():
    assert C.plan(EXT, "no.such.token.exists", G) is None


def test_blockers_name_the_world_supplies_that_are_absent():
    assert C.blockers(EXT, "pdf.extract.text", G) == []
    missing = C.blockers([], "pdf.extract.text", G)
    assert "pdf.file.available" in missing


# --------------------------------------------------------------------------- #
# typed call surface integration
# --------------------------------------------------------------------------- #
_SAMPLE = {
    "PATH_FILE": None,   # filled from a real file at call time
    "PATH_LIST": None,   # filled from a real file at call time
    "PATH_OUTPUT": "/tmp/out.bin",
    "PATH_DIR": "/tmp",
    "STRING": "x",
    "NUMBER": 1,
    "NUMBER_LIST": [1, 2],
    "PAIR_LIST": [[100, 0.0], [300, 2.0]],
    "BOOL": True,
    "ARGV": ["zbarimg", "--quiet", "--raw", "x"],
    "JSON_TEXT": '{"a": 1}',
    "KV": {"k": "v"},
}


def _valid_args(sig, real_path):
    """One well-typed value for every slot in `sig`."""
    out = {}
    for slot, ty in sig.items():
        if ty not in _SAMPLE:
            raise AssertionError(f"no sample value for type {ty}")
        out[slot] = _SAMPLE[ty]
        if out[slot] is None:
            out[slot] = real_path if ty == "PATH_FILE" else [real_path]
    return out


def test_call_errors_reject_a_number_where_a_file_path_is_required():
    registry = C.load_registry()
    for cid in sorted(registry):
        for slot, ty in C.signature(cid, registry).items():
            if ty == "PATH_FILE":
                assert C.call_errors(cid, {slot: 12345}, registry), (
                    f"{cid}.{slot} accepted a number as a file path"
                )
                return
    raise AssertionError("no PATH_FILE slot found in the registry")


def test_call_errors_accept_well_typed_arguments():
    registry = C.load_registry()
    real = str(Path(__file__).resolve())
    for cid in sorted(registry):
        sig = C.signature(cid, registry)
        if "PATH_FILE" not in sig.values():
            continue
        args = _valid_args(sig, real)
        assert C.call_errors(cid, args, registry) == [], f"{cid} <- {args}"
        return
    raise AssertionError("no PATH_FILE slot found in the registry")


def test_every_capability_signature_is_a_dict_with_no_unknown_types():
    registry = C.load_registry()
    for cid in registry:
        sig = C.signature(cid, registry)
        assert isinstance(sig, dict), cid
        assert "UNKNOWN" not in sig.values(), cid


def test_zero_slot_capabilities_are_named_not_hidden():
    """`() -> X` is a legitimate signature, but every one of them is named here.

    `image.code.decode.zbarimg` hides its input inside an argv template
    (`${input.path}`), so the typed surface sees no slot for it.  That is a
    real crack this integration exposed.  It is recorded, not papered over.
    """
    registry = C.load_registry()
    zero = sorted(c for c in registry if not C.signature(c, registry))
    assert zero == [
        "image.code.decode.zbarimg",
        "terminal.kstar.root.assess.stdlib",
    ]


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #
def test_report_is_internally_consistent():
    r = C.report(EXT, G)
    assert r["schema"] == C.SCHEMA
    assert r["capabilities_total"] == 68
    assert r["capabilities_fired"] == 68
    assert r["capabilities_unreachable"] == 0
    assert len(r["firing_order"]) == 68
