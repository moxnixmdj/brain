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


# ---------------------------------------------------------------------------
# The return type selects which member's guide applies.
# ---------------------------------------------------------------------------
def test_guide_ranking_prefers_the_declared_direction():
    """188: prose and name share no word; the member's own guide does the matching."""
    import the_return_type_selects_the_guide_v1 as RTG

    guides = [
        ("poly.rep.to_list()",
         "Convert ``f`` to a list representation with native coefficients. "),
        ("poly.rep.from_list()",
         "Convert a list representation to a polynomial with native coefficients."),
        ("poly.rep.to_sympy_list()", "Convert ``f`` to a list representation."),
    ]
    bodies = RTG.guide_bodies(
        "returns a list of its coefficients based on its internal representation",
        "list[int]", ["poly"], guides)
    assert bodies[0] == "poly.rep.to_list()", bodies


def test_guide_ranking_uses_the_first_sentence_not_the_examples():
    """194: doctest examples made `tolist` outrank `todok` on incidental overlap."""
    import the_return_type_selects_the_guide_v1 as RTG

    guides = [
        ("matrix.todok()",
         "Return the matrix as dictionary of keys.\n\n        Examples\n"
         "        ========\n\n        >>> from sympy import Matrix\n"),
        ("matrix.tolist()",
         "Return the Matrix as a nested Python list.\n\n        Examples\n"
         "        ========\n\n        >>> from sympy import Matrix\n"),
    ]
    bodies = RTG.guide_bodies(
        "accepts a Sympy SparseMatrix and returns its dictionary-of-keys representation",
        "list[int]", ["matrix"], guides)
    assert bodies[0] == "matrix.todok()", bodies


def test_no_type_specific_word_is_a_stopword():
    # "representation" is the word 194 depends on; a stoplist containing it silently made the
    # item unsolvable. Structural English only.
    import the_return_type_selects_the_guide_v1 as RTG

    for w in ("representation", "dictionary", "keys", "coefficient", "list"):
        assert w not in RTG._STOP, w


def test_declared_return_type_outranks_prose_overlap():
    """185: prose mentions both 'SymPy' and 'integer', so `from_sympy` scored 3 overlap hits
    against `to_int`'s 1 -- but the declared type is `int` and `to_int` spells it. The type is
    the least noisy statement available and must win."""
    import the_return_type_selects_the_guide_v1 as RTG

    guides = [
        ("K.from_sympy()", "Convert SymPy's Integer to SymPy's ``Integer``. "),
        ("K.to_int()", "Convert ``val`` to a Python ``int`` object. "),
        ("K.to_sympy()", "Convert ``a`` to a SymPy object. "),
    ]
    bodies = RTG.guide_bodies(
        "takes a finite field K created using the GF class from Sympy and an element a of that "
        "field, converts the field element into its corresponding integer representation",
        "int", ["K", "a"], guides)
    assert bodies[0] == "K.to_int()", bodies


def test_guide_bodies_are_emitted_with_and_without_arguments():
    """`todok` takes nothing, `to_int` takes the element. The signature says how many
    parameters exist to supply; which shape is right is decidable, so both are emitted."""
    cands = G.compositions(["K", "a"], {},
                           guide_bodies=["K.to_int()", "matrix.todok()"])
    bodies = [c["body"] for c in cands]
    assert bodies[0] == "K.to_int()"
    assert "K.to_int(a)" in bodies
    assert "matrix.todok(a)" in bodies


# ---------------------------------------------------------------------------
# A nested read is stated by a live instance.
# ---------------------------------------------------------------------------
def test_kwctor_body_is_the_exact_reference_shape():
    """181/182: one constructor call, keywords from the artifact's signature, values read
    two levels deep because `Body.frame` is a property and `dir(cls)` cannot see inside it."""
    target = ("PinJoint('pin', parent, child, parent_point=parent.frame.x, "
              "child_point=-child.frame.x)")
    cands = G.compositions(
        ["parent", "child"], {},
        problem=("creates a pin joint connecting two bodies, positioned at parent.frame.x "
                 "with respect to the mass center, and in the child at -child.frame.x. "
                 "using the specified points. Create a function called custom_pinJoint"),
        stub_imports=["Body", "PinJoint"],
        return_annotations=["sympy.physics.mechanics.PinJoint"],
        func_name="custom_pinJoint",
        nested_short={"parent": ["frame.x", "frame.u"], "child": ["frame.x", "frame.u"]},
        kwarg_names=["parent", "child", "parent_point", "child_point", "parent_axis"])
    bodies = [c["body"] for c in cands]
    assert target in bodies, bodies[:5]


def test_keyword_must_not_be_a_parameter_name():
    """`PinJoint(parent=..., child=...)` is a different call. `parent`/`child` are the
    PARAMETERS and the prose names them constantly, so they must not win the keyword slot."""
    cands = G.compositions(
        ["parent", "child"], {},
        problem=("a parent and a child, positioned at parent.frame.x, at -child.frame.x, "
                 "using the specified points"),
        stub_imports=["PinJoint"],
        return_annotations=["sympy.physics.mechanics.PinJoint"],
        nested_short={"parent": ["frame.x"], "child": ["frame.x"]},
        kwarg_names=["parent", "child", "parent_point", "child_point"])
    bodies = [c["body"] for c in cands if c["kind"] == "KWCTOR"]
    assert bodies, "no keyword-constructor bodies"
    assert "parent=" not in bodies[0]
    assert "child=" not in bodies[0]


def test_open_import_stub_parses_and_recovers_arguments():
    """189's stub ends `from sympy.physics.mechanics import ` with the cursor before the name.
    Unrepaired it kept parameters() empty, so its three-statement body could never be built."""
    stub = ("from sympy import symbols\nfrom sympy.physics.mechanics import (\n"
            "Particle, PinJoint, PrismaticJoint, RigidBody)\nimport sympy\n\n"
            "def custom_motion(wall: sympy.physics.mechanics.RigidBody, "
            "slider: sympy.physics.mechanics.PrismaticJoint, "
            "pin: sympy.physics.mechanics.PinJoint) -> sympy.Matrix:\n"
            "    from sympy.physics.mechanics import ")
    repaired = HF._repaired_source(stub)
    ast.parse(repaired)
    assert G.parameters(stub) == ["wall", "slider", "pin"]


def test_lambda_rewrite_shape_is_generated():
    """180: prose says 'every occurrence ... is REPLACED' and 'the product of the maximum and
    the minimum of those arguments'. The member comes from the inflected verb, the lambda's two
    names from the stated symbols, and the rewritten symbol from the prose's own `symbol F`."""
    target = ("parse_mathematica(expr).replace(Function('F'), "
              "lambda *x: Max(*x)*Min(*x))")
    cands = G.compositions(
        ["expr"], {},
        problem=("modify the resulting expression so that every occurrence of the function "
                 "symbol F is replaced by a new function that, when evaluated with one or "
                 "more arguments, returns the product of the maximum and the minimum of "
                 "those arguments"),
        stated_symbols=["parse_mathematica", "Function", "Max", "Min"])
    bodies = [c["body"] for c in cands]
    assert target in bodies, bodies[:6]


def test_multi_statement_chain_is_generated():
    """189: construct, add the joints, return the equations of motion -- three statements on
    one object, which the grammar previously emitted only as single calls."""
    cands = G.compositions(
        ["wall", "slider", "pin"], {},
        problem=("sets up this system using the Newtonian formulation, adds the slider and "
                 "pin joints, and returns the system's equations of motion"),
        stub_prefixes=[("", ["System", "Inertia"])])
    bodies = [c["body"] for c in cands]
    target = ("System\n    system = System.from_newtonian(wall)\n"
              "    system.add_joints(slider, pin)\n    return system.form_eoms()")
    assert target in bodies
