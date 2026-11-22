"""The stub's incomplete last line is a STATEMENT, not a hole.

Every item in this file failed before the mechanism below existed, and every one of them
failed for a reason that had nothing to do with vocabulary:

  35   `return nx.`                        -> parameters() silently returned []
  31   `return nx.community.`              -> same
  186  `    from sympy.`                   -> same
  200  `    from sympy.tensor.array...`    -> same

`_repaired_source` appended `pass`, but the truncated expression was still a SyntaxError, so
`ast.parse` failed, `parameters()` returned `[]`, and NO candidate could ever be built. That is
a fail-closed instrument masquerading as a capability limit, and it hid five items.
"""
from __future__ import annotations

import ast
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import hole_filler_v1 as HF
import body_grammar_v1 as G

STUBS = {
    "return_dotted": "import networkx as nx\ndef f(G:nx.Graph, source:int) -> list:\n    return nx.",
    "return_reexport": "import networkx as nx\ndef f(G:nx.Graph) -> list:\n    return nx.community.",
    "from_partial": "from sympy import symbols\nimport sympy\n\ndef f(N: sympy.Symbol) -> sympy.Symbol:\n    from sympy.",
    "from_deep": "from sympy import Matrix\nimport sympy\n\ndef f(array: sympy.Array) -> sympy.Matrix:\n    from sympy.tensor.array.expressions.",
    "open_call": "import networkx as nx\ndef f(G:nx.Graph) -> list:\n    return nx.community.greedy_modularity_communities(G,",
}


def test_every_truncated_stub_parses_after_repair():
    for name, stub in STUBS.items():
        repaired = HF._repaired_source(stub)
        try:
            ast.parse(repaired)
        except SyntaxError as exc:          # pragma: no cover - the bug being guarded
            raise AssertionError(f"{name} still does not parse: {exc}") from exc


def test_arguments_are_recovered_from_a_truncated_stub():
    # The whole point of the repair: the signature is readable, so the parameters exist.
    assert G.parameters(STUBS["return_dotted"]) == ["G", "source"]
    assert G.parameters(STUBS["return_reexport"]) == ["G"]
    assert G.parameters(STUBS["from_partial"]) == ["N"]
    assert G.parameters(STUBS["from_deep"]) == ["array"]
    assert G.parameters(STUBS["open_call"]) == ["G"]


def test_from_continuation_is_valid_python():
    # A bare `from sympy` on its own line is ALWAYS a SyntaxError (no module, no names), so
    # the repair has to substitute a placeholder rather than merely drop the dot.
    repaired = HF._repaired_source(STUBS["from_partial"])
    body = [l for l in repaired.splitlines() if "from sympy" in l][-1].strip()
    assert body != "from sympy"
    ast.parse(repaired)


def test_compositions_emit_a_return_annotation_constructor_first():
    # Item 178's stub declares `-> sympy.physics.quantum.trace.Tr` and its reference is
    # exactly that call. An unimported intermediate module raises AttributeError on sympy,
    # so the QUALIFIED spelling is the one that works and it must not be truncated away.
    cands = G.compositions(["n"], {}, return_annotations=["sympy.physics.quantum.trace.Tr"])
    bodies = [c["body"] for c in cands]
    assert bodies[0] == "sympy.physics.quantum.trace.Tr(n)"
    assert cands[0]["kind"] == "RETANN"


def test_a_prose_stated_member_wins_over_a_grid():
    # "all the free symbols present" -> `free_symbols`. A plain membership test on the prose
    # vocabulary cannot match one token with an underscore, so every part must be checked.
    paths = {"index": ["base", "free_symbols", "canonical_variables", "indices"]}
    cands = G.compositions(["index"], paths,
                           problem="extract all the free symbols present in the expression")
    bodies = [c["body"] for c in cands]
    assert bodies.index("index.free_symbols") < 5
    # and the un-stated members must still be present, just later
    assert "index.canonical_variables" in bodies


def test_stub_prefixes_are_emitted_before_every_grid():
    cands = G.compositions(["G"], {}, problem="shortest path lengths and predecessors",
                           stub_prefixes=[("", ["bellman_ford_predecessor_and_distance(G)"])])
    assert cands[0]["kind"] == "PREFIX"
    assert cands[0]["body"] == "bellman_ford_predecessor_and_distance(G)"
