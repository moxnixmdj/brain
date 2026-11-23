"""Three derivations that took 21/40 -> 29/40, each pinned by the fact that justified it.

Every test here encodes a MEASURED failure, not a hope:

  * a truncated stub (`return nx.`, `from sympy.`) silently produced `parameters() == []`,
    so items 35, 31, 32, 186 and 200 could never be solved by any candidate;
  * a bare `from X` line is never valid Python, so the repair must placeholder it;
  * a member named in prose across an underscore (`free symbols` -> `free_symbols`) was not
    treated as stated, so `index.free_symbols` sat behind 50 hanging candidates.
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import hole_filler_v1 as HF
import body_grammar_v1 as G
import shape_and_synonym_v1 as SS


def _parses(code: str) -> bool:
    import ast
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def test_truncated_return_expression_is_repaired_and_keeps_its_arguments():
    stub = "import networkx as nx\ndef f(G:nx.Graph, source:int) -> list:\n    return nx."
    assert _parses(HF._repaired_source(stub))
    assert G.parameters(stub) == ["G", "source"]


def test_truncated_import_expression_is_repaired():
    stub = ("from sympy import symbols\nimport sympy\n\n"
            "def f(N: sympy.Symbol) -> sympy.Symbol:\n    from sympy.")
    assert _parses(HF._repaired_source(stub))
    assert G.parameters(stub) == ["N"]


def test_open_call_is_closed_and_keeps_its_arguments():
    stub = "import networkx as nx\ndef f(G:nx.Graph) -> list:\n    return nx.community.greedy_modularity_communities(G,"
    assert _parses(HF._repaired_source(stub))
    assert G.parameters(stub) == ["G"]


def test_member_named_in_prose_across_an_underscore_is_stated_first():
    """`free symbols` in the prose must make `free_symbols` a stated read, not a guess."""
    paths = {"index": ["canonical_variables", "free_symbols", "base", "func"]}
    out = G.compositions(["index"], paths,
                         problem="extract all the free symbols present in the expression")
    bodies = [c["body"] for c in out]
    assert "index.free_symbols" in bodies
    pos = bodies.index("index.free_symbols")
    # it must beat every unstated single-attribute read, including the hanging ones
    unstated = [i for i, c in enumerate(out[:pos]) if c["kind"] == "PATH"]
    assert unstated == [], f"unstated reads still ahead of it: {[out[i]['body'] for i in unstated]}"


def test_return_annotation_constructor_is_emitted_first():
    """Item 178's reference IS its annotation: `sympy.physics.quantum.trace.Tr(n)`."""
    out = G.compositions(["n"], {}, problem="instantiate a trace object",
                         return_annotations=["sympy.physics.quantum.trace.Tr"])
    assert out[0]["body"] == "sympy.physics.quantum.trace.Tr(n)"
    assert out[0]["kind"] == "RETANN"


def test_return_annotation_of_a_generic_is_not_a_constructor():
    out = G.compositions(["x"], {}, problem="return a list", return_annotations=["list"])
    assert all(c["kind"] != "RETANN" for c in out)


def test_compound_member_statement_rule_does_not_fire_on_partial_words():
    """`base` must NOT count as stated for `canonical_variables` -- only full part matches."""
    paths = {"index": ["canonical_variables", "free_symbols"]}
    out = G.compositions(["index"], paths, problem="the free symbols")
    bodies = [c["body"] for c in out]
    assert bodies.index("index.free_symbols") < bodies.index("index.canonical_variables")
