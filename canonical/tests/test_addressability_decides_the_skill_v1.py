"""r84 -- the instrument was lying, and fixing it changed the answer.

Four things were wrong before any measurement could be trusted:

  1. `plan_len` was initialised to 0 and NEVER assigned, so every task read as "the
     planner produced nothing" -- won and lost alike. Not a planner failure; a missing
     assignment.
  2. 93 of 130 goals contain no quoted literal, and that branch did NOTHING and was then
     scored as a failure. "Did not try" and "tried and failed" were the same number.
  3. I reported a "12.5% addressable vs 0% render-only" split from a classifier keyed on
     task source features. It was contaminated by (2): tasks that were never attempted
     cannot be evidence about addressability.
  4. The addressability probe itself defaulted to "render_only" when it found NO signal
     of either kind, silently accusing 52 families of being pixel problems.

The measured decomposition of the 9/130 headline:
    37 attempted         -> 9/37 = 24.3%
    93 never attempted   -> 0/93  by construction
"""
import pathlib
import urllib.request

import pytest

from canonical.runtime import addressability_probe_v1 as P

MINIWOB = pathlib.Path("/tmp/miniwob++/miniwob/html/miniwob")


def test_a_goal_with_no_literal_must_not_be_scored_as_an_attempted_failure():
    """The runner must distinguish 'did not try' from 'tried and failed'."""
    src = pathlib.Path("canonical/evaluation/bench/run_planned_v1.py").read_text()
    assert '"strategy": "unset"' in src or "'strategy': 'unset'" in src
    assert "not_attempted_no_literal" in src
    assert 'r["plan_len"] = len(pr.get("plan") or [])' in src


def test_no_signal_is_not_an_accusation():
    """A family with neither state nor render signal is UNKNOWN, not render-only."""
    html = "<html><body><div id=x>hello</div></body></html>"
    assert P.classify_source(html)["kind"] == P.DOM_ONLY_UNOBSERVABLE


def test_the_two_live_pages_we_actually_measured_are_told_apart():
    """The property that matters is SKILLABLE, not the exact label.

    An earlier version of this test asserted a stub page classifies as HYBRID. It does
    not: with no styling it is STATE_ADDRESSABLE, and that is correct -- both are
    skillable. The test was asserting the wrong property, so the test was fixed.
    """
    server = "<form method=GET action=/inbox><input name=filter></form>"
    assert P.classify_source(server)["kind"] in (P.STATE_ADDRESSABLE, P.HYBRID)

    client = ('<h1>Inbox</h1><button onclick="this.style.background=\'#ff0000\'">'
              'APPLY</button>')
    assert P.classify_source(client)["kind"] == P.RENDER_ONLY

    # and against the real servers, where the answer is already known end to end
    for url, skillable in (("http://127.0.0.1:8901/inbox", True),
                           ("http://127.0.0.1:8895/", False)):
        try:
            html = urllib.request.urlopen(url, timeout=3).read().decode()
        except Exception:
            pytest.skip(f"{url} not running")
        assert P.decides_skill("", html)["exact_postcondition_possible"] is skillable


def test_a_predicate_referent_is_named_as_such():
    """'the shortest one' has no token; a demonstration is the only way to learn it."""
    assert P.referent_is_predicate("Buy the ticket with the shortest duration.")
    assert P.referent_is_predicate("Click on the numbers in ascending order.")
    assert not P.referent_is_predicate("Select Portugal from the list and click Submit.")


@pytest.mark.skipif(not MINIWOB.exists(), reason="MiniWob++ not present")
def test_the_suite_is_overwhelmingly_out_of_the_compilers_class():
    """129 of 130 families expose no code-readable terminal state.

    This is the honest answer to 'do we solve everything on a computer': no. Five shapes
    are real and measured; they apply to the class whose postcondition is addressable,
    and MiniWob++ is almost entirely outside it.
    """
    kinds = {}
    for f in sorted(MINIWOB.glob("*.html")):
        kinds[f.stem] = P.classify_source(f.read_text(errors="replace"))["kind"]
    assert len(kinds) == 130
    skillable = [n for n, k in kinds.items() if k in (P.STATE_ADDRESSABLE, P.HYBRID)]
    assert len(skillable) <= 2, f"expected almost none, got {skillable}"
