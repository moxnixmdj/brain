"""Attribution: pick the standing violation an issue is about, or abstain.

The measured cases are the two pluggy issues this was built against:

* #763 ("list_plugin_distinfo() keeps unregistered plugins") names `unregister()` and
  `list_plugin_distinfo()`, and must select the lifecycle violation over two unrelated
  `assert_validation` violations that sit in the *same* function.
* #762 ("unregister() argument validation relies on assert") names only `unregister()` and `assert`,
  and must select the assert violation, because the issue's own vocabulary ("assert") is evidence.

And the control: a werkzeug issue about `WWW-Authenticate` must not attribute anything to pluggy.
"""

from __future__ import annotations

from canonical.swe_kernel import violation_attribution_v1 as va

VIOLATIONS = [
    {"law": "assert_validation", "where": "pluggy._manager.unregister (line 292)",
     "detail": "argument validation by assert on ['plugin']"},
    {"law": "remove_argument_vanishes", "where": "PluginManager.unregister",
     "getter": "list_plugin_distinfo", "detail": "still yielded"},
    {"law": "assert_validation", "where": "pluggy._manager.unregister (line 294)",
     "detail": "argument validation by assert on ['name']"},
]

ISSUE_763 = """
`list_plugin_distinfo()` keeps unregistered plugins.

`load_setuptools_entrypoints()` appends to `_plugin_distinfo`, but `unregister()` never removes
those entries. After unregistering, `list_plugin_distinfo()` and `list_plugin_distributions()` still
list the plugin.
"""

ISSUE_762 = """
`unregister()` argument validation relies on `assert`.

`unregister()` checks "one of name or plugin" and "plugin is not registered" with `assert`.
Under `python -O`, `pm.unregister(unregistered_plugin)` silently returns the plugin.
"""

ISSUE_3127 = """
WWW-Authenticate trailing white-space with empty parameters

When a WWWAuthenticate header with no realm or other parameter is converted to a response header,
the header contains an invalid trailing white-space, and h11 rejects it.
"""


def test_the_issue_that_names_the_getter_selects_the_lifecycle_violation():
    ranked = va.rank_violations(VIOLATIONS, ISSUE_763)
    assert ranked[0]["law"] == "remove_argument_vanishes"
    assert "list_plugin_distinfo" in ranked[0]["evidence"]
    assert ranked[0]["score"] > ranked[1]["score"]


def test_the_issue_that_names_assert_selects_the_assert_violation():
    ranked = va.rank_violations(VIOLATIONS, ISSUE_762)
    assert ranked[0]["law"] == "assert_validation", "an issue whose only symbol is shared must be "
    "separated by the law's own vocabulary, or attribution there is a coin toss"


def test_an_unrelated_issue_abstains_rather_than_guessing():
    assert va.attributable(VIOLATIONS, ISSUE_3127) is False
    ranked = va.rank_violations(VIOLATIONS, ISSUE_3127)
    assert all(v["score"] == 0 for v in ranked)


def test_no_issue_text_means_no_attribution():
    assert va.attributable(VIOLATIONS, "") is False
    assert va.issue_signals("") == {}
