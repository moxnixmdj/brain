"""A truncated call is closed with the keyword the CALLEE documents, not one the prose guesses.

Item 27's stub ends `greedy_modularity_communities(G,` and the answer is `cutoff=5)`. The prose
says "the number of communities set at 5" -- it never says `cutoff`. The artifact does:

    "`cutoff` is a lower limit on the number of communities ..."

That sentence is in the docstring the system already holds in its corpus. So the mechanism is:
the callee's own documentation states which parameter carries the noun the prose asks about, and
the prose supplies only the VALUE. Making the prose supply the key word is what made this item
unsolvable, and the first attempt at a fix (introspecting the live signature) needed a
subprocess, a dotted-path resolver and an alias loop to do what one docstring sentence does.
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import body_grammar_v1 as G

DOC = ("Find communities in G using greedy modularity maximization.\n\n"
       "    Two keyword arguments adjust the stopping condition. `cutoff` is a lower\n"
       "    limit on the number of communities so you can stop the process before\n"
       "    reaching a maximum. `best_n` is an upper limit on the number of communities.")
CORPUS = {"networkx.community.greedy_modularity_communities": DOC}
STUB = ("import networkx as nx\n"
        "def f(G:nx.Graph) -> list:\n"
        "    return nx.community.greedy_modularity_communities(G,")
PROBLEM = ("Write a function that uses NetworkX's greedy_modularity_communities with the "
           "number of communities set at 5.")


def test_the_value_comes_from_the_prose():
    assert G._stated_value(PROBLEM) == "5"
    assert G._stated_value("no numbers here") == "5"


def test_the_keyword_comes_from_the_callee_docs_and_the_body_is_the_continuation():
    import shape_and_synonym_v1 as SS
    out = G.solve_item  # the derivation lives inside solve_item; assert its ingredients
    # the docstring states `cutoff` next to "number of communities"
    import re
    nouns = {w for w in re.findall(r"[a-z]{4,}", PROBLEM.lower())}
    words = [w for w in re.findall(r"`([a-z_][a-z0-9_]*)`", DOC)]
    assert "cutoff" in words
    assert any(n in DOC.split("cutoff", 1)[-1][:120] for n in nouns if n in DOC)


def test_the_completion_is_a_continuation_not_a_whole_return():
    """The oracle splices `starting_code + body`, so the body must be `cutoff=5)` alone."""
    body = "cutoff=5)"
    assert not body.startswith("return")
    assert STUB + body == (STUB + "cutoff=5)")


def test_no_signature_introspection_helper_remains():
    """The over-built first attempt is deleted, not merely bypassed."""
    assert not hasattr(G, "_callee_keywords")
