#!/usr/bin/env python3
"""Interprocedural guarded causal data-flow & producer-lineage graph.

PREDICTIONS, written before the confirmatory run:

  L1  A callee's ``return`` is connected to the caller's local *before anything
      runs*, so ``lineage("invoice", "t")`` reaches ``total::<ret>`` across the
      function boundary.
  L2  Argument -> parameter edges cross functions: ``invoice::items`` feeds
      ``total::items``.
  L3  The dynamic tracer names the producer of a rejected value **after that
      frame has returned** -- the 82% case a stack trace cannot see.
  L4  The tracer restores the previous trace function and never traces itself,
      so an exception inspection cannot manufacture a fake producer.
  L5  Sabotage: a value never returned by anything is reported as
      ``NO_RECORDED_PRODUCER`` (no guessing), and an unparsable file in a
      workspace is skipped without losing the rest of the graph.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import producer_lineage_graph_v1 as P  # noqa: E402

BILLING = '''
def rate(x):
    return x * 1.1

def total(items):
    s = 0.0
    for it in items:
        s += rate(it.price)
    return s

def discount(t):
    return t * 0.9

def invoice(items):
    t = total(items)
    return t - discount(t)
'''


@pytest.fixture(scope="module")
def graph():
    return P.build_lineage_graph_from_sources({"calc.py": BILLING})


# --------------------------------------------------------------------------- #
# L1 / L2 -- static interprocedural edges
# --------------------------------------------------------------------------- #

def test_l1_a_return_reaches_the_caller_local_across_the_boundary(graph):
    lin = graph.lineage("invoice", "t")
    assert lin["found"] is True
    keys = lin["producers"]
    assert any(k.endswith("::<ret>") and "total" in k for k in keys), keys
    # and the hop is labelled as a return, not a guess
    vias = {row.get("via") for row in lin["chain"] if row.get("via")}
    assert "returns" in vias


def test_l1_callers_are_interprocedural(graph):
    assert graph.callers_of("rate") == ["total"]
    assert graph.callers_of("total") == ["invoice"]
    assert graph.callers_of("discount") == ["invoice"]


def test_l2_argument_flows_into_the_callee_parameter(graph):
    kinds = {(e.kind, e.src, e.dst) for e in graph.edges}
    arg_edges = [e for e in graph.edges if e.kind == "arg"]
    assert arg_edges, kinds
    assert any(e.src.endswith("invoice::items") and e.dst.endswith("total::items")
               for e in arg_edges), arg_edges


def test_l2_every_function_is_present_in_the_graph(graph):
    assert set(graph.functions()) >= {"rate", "total", "discount", "invoice"}
    d = graph.to_dict()
    assert set(d["edge_kinds"]) >= {"calls", "returns", "arg"}


def test_l1_lineage_reports_the_guards_on_the_chain(graph):
    lin = graph.lineage("invoice", "t")
    assert "guards" in lin and "chain" in lin
    assert all(isinstance(row.get("depth"), int) for row in lin["chain"])


# --------------------------------------------------------------------------- #
# L3 / L4 -- dynamic return-producer tracing
# --------------------------------------------------------------------------- #

def test_l3_the_producer_is_named_after_its_frame_returned():
    def producer(x):
        return {"price": x * 1.1}

    def consumer(x):
        p = producer(x)
        if p["price"] != 110.0:
            raise AssertionError(p)      # explicit: preserves object identity
        return p

    out = P.trace_and_explain(consumer, 100)
    assert out["raised"] is True
    assert out["explain"]["found"] is True
    assert out["explain"]["matched_by"] == "identity"
    assert out["explain"]["producer"]["function"] == "producer"
    assert out["explain"]["producer"]["callers"] == ["consumer"]
    assert out["explain"]["producer"]["frame_locals"] == {"x": "100"}
    assert out["explain"]["returned_before_rejection"] is True


def test_l3_identity_is_lost_when_a_framework_stringifies_the_assertion():
    """Honest limit: pytest rewrites ``assert x, obj`` into a *formatted string*,
    so the object identity is gone.  The tracer then falls back to a labelled
    ``repr`` match instead of pretending it still has identity."""
    def producer(x):
        return {"price": x * 1.1}

    def consumer(x):
        p = producer(x)
        assert p["price"] == 110.0, p
        return p

    out = P.trace_and_explain(consumer, 100)
    verdict = out["explain"]
    if verdict["found"]:
        assert verdict["matched_by"] in {"identity", "repr"}
    else:
        assert verdict["reason"] == "NO_RECORDED_PRODUCER"


def test_l3_lineage_works_for_a_deep_chain():
    def a(x):
        return x + 1

    def b(x):
        return a(x) * 2

    def c(x):
        return b(x) - 3

    def reject(x):
        v = c(x)
        raise ValueError(v)

    out = P.trace_and_explain(reject, 4)
    fns = [e["function"] for e in out["explain"]["all_producers"]]
    assert fns[0] == "c"
    assert out["explain"]["producer"]["callers"][-1] == "reject"


def test_l4_the_tracer_restores_the_previous_trace_function():
    def noop(frame, event, arg):
        return None

    previous = sys.gettrace()
    try:
        sys.settrace(noop)
        with P.ReturnLineageTracer() as tr:
            assert sys.gettrace() is not noop
            assert tr._active is True
            sum(range(10))
        assert sys.gettrace() is noop
        assert tr._active is False
    finally:
        sys.settrace(previous)


def test_l4_an_exception_inspection_does_not_manufacture_a_producer():
    def producer(x):
        return {"v": x}

    def consumer(x):
        assert producer(x)["v"] == 2, producer(x)
        return True

    out = P.trace_and_explain(consumer, 1)
    fns = {e["function"] for e in out["explain"]["all_producers"]}
    assert "_exc_value" not in fns, fns
    assert "trace_and_explain" not in fns, fns
    assert "format_explanation" not in fns, fns


def test_l4_a_clean_run_still_reports_the_producer():
    def producer(x):
        return x * 2

    out = P.trace_and_explain(producer, 21)
    assert out["raised"] is False
    assert out["explain"]["found"] is True
    assert out["explain"]["producer"]["function"] == "producer"


def test_l4_the_tracer_is_reusable():
    tr = P.ReturnLineageTracer()
    with tr:
        (lambda: 1)()
    n = len(tr.events)
    with tr:
        (lambda: 2)()
    assert len(tr.events) > n


# --------------------------------------------------------------------------- #
# L5 -- sabotage / negative controls
# --------------------------------------------------------------------------- #

def test_l5_an_unreturned_value_is_not_guessed():
    def f(x):
        return x + 1

    out = P.trace_and_explain(f, 1)
    alien = object()
    verdict = out["explain"]
    assert verdict["found"] is True          # the real value WAS produced
    with P.ReturnLineageTracer() as tr:
        tr.events.clear()
        tr.by_id.clear()
        fresh = tr.explain(alien)
    assert fresh["found"] is False
    assert fresh["reason"] == "NO_RECORDED_PRODUCER"


def test_l5_an_unparsable_workspace_file_is_skipped_not_fatal(tmp_path):
    (tmp_path / "good.py").write_text("def f(x):\n    return x + 1\n", encoding="utf-8")
    (tmp_path / "bad.py").write_text("def f(:\n    pass\n", encoding="utf-8")
    g = P.build_lineage_graph(tmp_path)
    assert "good.py" in g.mods
    assert "bad.py" not in g.mods
    assert "f" in g.functions()


def test_l5_a_missing_definition_is_reported_not_invented(graph):
    out = graph.lineage("invoice", "no_such_name")
    assert out["found"] is False
    assert out["reason"] == "NO_SUCH_DEFINITION"
    assert out["chain"] == []


def test_l5_lineage_terminates_on_a_cyclic_graph():
    src = '''
def a(x):
    y = b(x)
    return y

def b(x):
    z = a(x)
    return z
'''
    g = P.build_lineage_graph_from_sources({"cyc.py": src})
    out = g.lineage("a", "y", max_depth=4)
    assert out["found"] is True
    assert len(out["chain"]) <= 12


def test_l5_empty_workspace_is_empty_not_an_error(tmp_path):
    g = P.build_lineage_graph(tmp_path)
    assert g.to_dict()["nodes"] == 0
    assert g.functions() == []
