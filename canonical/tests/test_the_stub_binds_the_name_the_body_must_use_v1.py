"""The body must spell the name the way the STUB bound it, not the way the corpus found it.

Measured failure this test pins. The corpus records a name's DEFINING module: `prod` lives in
`numpy`, `expm` in `scipy.linalg`. So the grammar emitted `numpy.prod(arr)`. The stub's own
line is `import numpy as np`, which binds the identifier `np` and NOT `numpy`, so the correct
answer in corpus spelling raised NameError and the item failed with the right answer in hand.

40 of the 59 recalled-but-unsolved items failed exactly this way. The stub's import lines are
the only authority on which spelling exists in the namespace, so they decide the body.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import body_grammar_v1 as G  # noqa: E402


def test_alias_map_reads_all_three_import_shapes():
    a = G.alias_map(["import numpy as np"])
    assert a["numpy"] == "np"
    a = G.alias_map(["from scipy import linalg"])
    assert a["scipy.linalg"] == "linalg"
    a = G.alias_map(["from scipy.spatial import distance"])
    assert a["scipy.spatial.distance"] == "distance"
    a = G.alias_map(["import numpy"])
    assert a["numpy"] == "numpy"


def test_bound_spelling_never_emits_a_name_the_stub_did_not_bind():
    a = G.alias_map(["import networkx as nx"])
    assert G.bound_spelling("networkx.algorithms.bellman_ford", a) \
        == "nx.algorithms.bellman_ford"
    # a module the stub never imported has NO legal spelling, and guessing one is the bug
    assert G.bound_spelling("scipy.linalg.expm", a) is None


def test_respell_rewrites_the_root_and_leaves_bare_parameters_alone():
    a = G.alias_map(["import numpy as np"])
    assert G.respell("numpy.prod(arr)", a) == "np.prod(arr)"
    assert G.respell("np.prod(arr)", a) == "np.prod(arr)"
    assert G.respell("arr", a) == "arr"


def test_qualified_spelling_joins_the_module_then_applies_the_alias():
    mods = {"prod": "numpy", "expm": "scipy.linalg", "combine_pvalues": "scipy.stats"}
    a = G.alias_map(["import numpy as np", "from scipy import linalg",
                     "import scipy.stats as st"])
    got = G.qualified_spellings(["prod", "expm", "combine_pvalues"], mods, a)
    assert got == ["np.prod", "linalg.expm", "st.combine_pvalues"]


def test_a_stated_bare_name_is_qualified_when_the_corpus_gives_its_module():
    """The case that actually cost the items: `any(arr)` was in the space, `np.any(arr)` was not.

    `respell` can only rewrite a name that is ALREADY dotted, so a bare stated name came back
    untouched and the only legal spelling was never built.
    """
    cands = G.compositions(
        ["arr"], {}, problem="checks if any elements in an array are true",
        stated_symbols=["any", "array"], imported_names=["np"],
        stub_imports=["import numpy as np"],
        modules_in_scope={"any": "numpy", "array": "numpy"},
    )
    bodies = [c["body"] for c in cands]
    assert "np.any(arr)" in bodies, bodies[:12]


def test_no_module_in_scope_means_no_qualification_is_invented():
    """Without the corpus's module there is nothing to qualify from, and guessing one is worse
    than emitting the bare name the stub may well have bound with `from x import *`."""
    cands = G.compositions(["arr"], {}, problem="checks if any elements are true",
                           stated_symbols=["any"], imported_names=["np"],
                           stub_imports=["import numpy as np"], modules_in_scope={})
    bodies = [c["body"] for c in cands]
    assert any(b.startswith("np.") for b in bodies) is False
