"""Three mechanisms that each turned a measured zero into passes, and their reasons.

All three are the same idea: the environment is asked a question it can answer about itself,
and the answer is not stored anywhere.

1. KEYWORD FORM. scipy's 22 reference-solvable items: 15 pass a stub parameter as a keyword
   (`gaussian_filter1d(x, radius=radius, sigma=sigma)`). The grammar emitted the positional
   `gaussian_filter1d(x, radius, sigma)` -- the right name, the wrong calling convention -- and
   the artifact rejected it. Positional ORDER is not derivable from a docstring; "a parameter of
   mine named `radius` goes into the slot named `radius`" is, once the artifact is asked for its
   own signature.

2. RETURN PREFIX. A stub that ends `def f(x):` and gets a bare expression appended evaluates
   the expression and returns None. The stub's own last character decides, so nothing is assumed.

3. FROM-IMPORT CALLABLES. `from scipy.ndimage import gaussian_filter1d` names the answer in the
   stub's first line while the prose says only "a 1D gaussian filter". The prose states the
   concept, the import states the symbol, and neither alone is the body.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import body_grammar_v1 as G  # noqa: E402


def test_a_parameter_whose_slot_is_not_its_position_becomes_a_keyword():
    # gaussian_filter1d's real signature: input, sigma, axis, ..., radius. The stub parameter
    # `radius` sits in POSITION 1 and the slot of that name is 8th, so arg 1 must be renamed.
    sig = ["input", "sigma", "axis", "order", "output", "mode", "cval", "truncate", "radius"]
    assert G.keyword_call("gaussian_filter1d(x, radius, sigma)", sig) \
        == "gaussian_filter1d(x, radius=radius, sigma=sigma)"


def test_a_parameter_already_in_its_own_slot_is_not_renamed():
    """`rank_filter(A, rank, size)` already fills (input, rank, size) in order; rewriting it to
    `rank=rank, size=size` is noise the oracle would spend trials on."""
    assert G.keyword_call("rank_filter(A, rank, size)",
                          ["input", "rank", "size"]) is None


def test_a_literal_or_expression_is_never_renamed_into_a_slot():
    """A literal cannot become a keyword, and `a` is already in slot 0, so there is no rewrite
    to make. Returning None is the correct answer: emitting `f(a, 5=5)` would be a SyntaxError
    that costs a trial and teaches nothing."""
    assert G.keyword_call("f(a, 5)", ["a", "b"]) is None
    # but a name that belongs in a DIFFERENT slot still gets renamed, alongside a literal
    assert G.keyword_call("f(a, 5)", ["b", "a"]) == "f(a=a, 5)"


def test_a_stub_ending_in_a_colon_needs_return_and_an_assignment_does_not_get_one():
    assert G._looks_expression("gaussian_filter1d(x, radius=radius)")
    assert not G._looks_expression("output = f(x)")
    assert not G._looks_expression("return f(x)")
    assert not G._looks_expression("for i in x")


def test_a_callable_imported_from_a_submodule_is_offered_as_a_candidate():
    """The stub's own import line states the symbol; the prose only states the concept."""
    cands = G.compositions(
        ["x", "radius", "sigma"], {}, problem="apply a 1D gaussian filter",
        stated_symbols=["gaussian"], imported_names=["gaussian_filter1d"],
        stub_imports=["from scipy.ndimage import gaussian_filter1d", "import numpy as np"],
        modules_in_scope={"gaussian_filter1d": "scipy.ndimage"},
        stub_source="from scipy.ndimage import gaussian_filter1d\nimport numpy as np\n"
                    "def f(x, radius, sigma):",
    )
    bodies = [c["body"] for c in cands]
    assert "return gaussian_filter1d(x, radius, sigma)" in bodies, bodies[:10]


def test_from_import_binding_resolves_to_the_bound_name_not_the_module_path():
    """`from scipy.ndimage import gaussian_filter1d` binds the name ITSELF; appending anything
    to it would emit `gaussian_filter1d.gaussian_filter1d`."""
    a = G.alias_map(["from scipy.ndimage import gaussian_filter1d"])
    assert G.bound_spelling("scipy.ndimage.gaussian_filter1d", a) == "gaussian_filter1d"
    a = G.alias_map(["import numpy as np"])
    assert G.bound_spelling("numpy.prod", a) == "np.prod"
