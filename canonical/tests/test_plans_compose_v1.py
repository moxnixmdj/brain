"""Pins the composer: type schemes, a searched order, a searched inverse, honest refusals.

Every bug this file guards against was real and shipped in a draft: a visited set that
hid a valid route, an inverse that was not reversed, and a decompressor typed as a
widening to TEXT. Each is pinned here so it cannot come back silently.
"""
from __future__ import annotations

import pathlib
import sys

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import plans_compose_v1 as compose  # noqa: E402

TYPES = {
    "fmt": {"program": "fmt", "path": "/bin/false",
            "schemes": [{"from": "TEXT", "to": ["HTML", "ANSI"], "polymorphic": False,
                         "why": "formatter slot"}],
            "roles": [], "filter": True},
    "b64": {"program": "b64", "path": "/bin/false",
            "schemes": [{"from": "ANY", "to": "BASE64[_]", "polymorphic": True},
                        {"from": "BASE64", "to": "UNWRAP", "polymorphic": False}],
            "roles": ["decompress"], "filter": True},
    "zip": {"program": "zip", "path": "/bin/false",
            "schemes": [{"from": "ANY", "to": "GZIP[_]", "polymorphic": True},
                        {"from": "GZIP", "to": "UNWRAP", "polymorphic": False}],
            "roles": ["decompress"], "filter": True},
}


def test_a_polymorphic_filter_wraps_whatever_it_is_given() -> None:
    assert compose._apply(TYPES["zip"]["schemes"][0], "BASE64[TEXT]") == ["GZIP[BASE64[TEXT]]"]
    assert compose._apply(TYPES["b64"]["schemes"][0], "ANSI") == ["BASE64[ANSI]"]


def test_a_decompressor_unwraps_only_its_own_constructor() -> None:
    assert compose._apply(TYPES["zip"]["schemes"][1], "GZIP[BASE64[ANSI]]") == ["BASE64[ANSI]"]
    assert compose._apply(TYPES["zip"]["schemes"][1], "BASE64[TEXT]") == []
    assert compose._apply(TYPES["b64"]["schemes"][1], "GZIP[TEXT]") == []


def test_the_recoverable_goal_is_two_stages_and_the_inverse_reverses_it() -> None:
    forward = compose.find_path(TYPES, "TEXT", "GZIP[BASE64[TEXT]]")
    assert forward["found"] and forward["chain"] == ["b64", "zip"], forward
    back = compose.invert(forward["chain"], TYPES, "GZIP[BASE64[TEXT]]", "TEXT")
    assert back["found"] and back["chain"] == ["zip", "b64"], back


def test_the_inverse_is_not_reversed_into_the_wrong_order() -> None:
    """find_path from the sink already starts at the outermost constructor."""
    back = compose.find_path(TYPES, "GZIP[BASE64[TEXT]]", "TEXT")
    assert back["chain"] == ["zip", "b64"], back["chain"]
    inverted = compose.invert(["b64", "zip"], TYPES, "GZIP[BASE64[TEXT]]", "TEXT")
    assert inverted["chain"] == back["chain"]


def test_a_lossy_sink_has_a_forward_path_and_no_inverse() -> None:
    forward = compose.find_path(TYPES, "TEXT", "GZIP[BASE64[ANSI]]")
    assert forward["found"] and forward["chain"] == ["fmt", "b64", "zip"], forward
    back = compose.invert(forward["chain"], TYPES, "GZIP[BASE64[ANSI]]", "TEXT")
    assert not back["found"], "a formatter has no inverse; the search must say so"
    assert "no inverse chain" in back["reason"]


def test_an_unreachable_sink_is_refused_with_a_reason() -> None:
    result = compose.find_path(TYPES, "TEXT", "GZIP[PDF]")
    assert not result["found"]
    assert "PDF" in result["reason"]


def test_the_search_is_shortest_because_every_scheme_costs_the_same() -> None:
    """BFS depth order is cost order, so the found chain is a shortest one."""
    types = {
        "slow": {"program": "slow", "path": "/bin/false", "roles": [], "filter": True,
                 "schemes": [{"from": "ANY", "to": "A[_]", "polymorphic": True}]},
        "a2b": {"program": "a2b", "path": "/bin/false", "roles": [], "filter": True,
                "schemes": [{"from": "A", "to": "B", "polymorphic": False}]},
        "b2c": {"program": "b2c", "path": "/bin/false", "roles": [], "filter": True,
                "schemes": [{"from": "B", "to": "C", "polymorphic": False}]},
        "c2d": {"program": "c2d", "path": "/bin/false", "roles": [], "filter": True,
                "schemes": [{"from": "C", "to": "D", "polymorphic": False}]},
        "short": {"program": "short", "path": "/bin/false", "roles": [], "filter": True,
                  "schemes": [{"from": "A", "to": "D", "polymorphic": False}]},
    }
    found = compose.find_path(types, "A", "D")
    assert found["chain"] == ["short"], found


def test_the_visited_set_is_global_because_the_search_is_markovian() -> None:
    """Two routes into one type have identical futures, so pruning the second is sound.

    This is pinned because a global set was twice diagnosed as the bug. It is not:
    capability depends only on the type in hand. A counterexample would need two
    different routes to one type with different reachable futures, which the type
    algebra cannot express.
    """
    types = {
        "wrap": {"program": "wrap", "path": "/bin/false", "roles": [], "filter": True,
                 "schemes": [{"from": "ANY", "to": "BOX[_]", "polymorphic": True}]},
        "x_into_box": {"program": "x", "path": "/bin/false", "roles": [], "filter": True,
                       "schemes": [{"from": "X", "to": "BOX[Y]", "polymorphic": False}]},
        "open": {"program": "open", "path": "/bin/false", "roles": [], "filter": True,
                 "schemes": [{"from": "BOX", "to": "UNWRAP", "polymorphic": False}]},
        "finish": {"program": "finish", "path": "/bin/false", "roles": [], "filter": True,
                   "schemes": [{"from": "Y", "to": "DONE", "polymorphic": False}]},
    }
    found = compose.find_path(types, "X", "DONE")
    assert found["found"] and found["chain"] == ["x_into_box", "open", "finish"], found
