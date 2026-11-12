"""Two facts the machine could not decide, on machines that had them.

Pins round 7. Both defects were measured on 2026-11-12 and both were blindness,
not incapacity: the thing worked and the machine could not see it.

1. `network.http.available` returned UNDECIDABLE__NOT_ESTABLISHED in a sandbox
   where pypi.org, registry.npmjs.org and api.github.com all answered HTTP 200.
   `_subjects` stripped exactly one qualifier, so it asked about `network.http`
   -- not a subject -- and never reached `network`. The transport did not need
   to be part of the name to be checked.

2. A goal stating a URL, a json path and a destination bound neither the URL nor
   the path slot, so the only capability that fetches JSON over HTTP was refused
   NOT_CALLABLE_WITH_WHAT_GOAL_PROVIDES while the URL sat in the sentence.
   `goal_compiler._repo_paths_uncached` already strips URLs "because URL path
   components are not repository paths"; the binder had no counterpart rule, so
   a URL fell through every branch and was silently dropped.

WHAT THESE TESTS DO NOT ASSERT.

That the network is reachable. That is a fact about the machine running the
tests, not about the code, and asserting it would make the suite fail on an
offline box for a reason that is not a defect. What is asserted is that the
sensor ANSWERS -- reachable or not -- instead of returning "I don't know".
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import world_binding_v1 as WB
from canonical.runtime import world_probe_v1 as WP

ANSWERED = ("network_tcp_reachable", "network_tcp_unreachable")


# --------------------------------------------------------------------------------------------
# 1. The premise that could not be decided
# --------------------------------------------------------------------------------------------
def test_the_network_premise_is_answered_and_not_shrugged_at():
    got = WP.probe_effect("network.http.available", root=ROOT)
    assert got["how"] in ANSWERED, (
        "network.http.available is still undecidable, so a capability that needs "
        f"the network cannot be planned at all: {got['how']}"
    )


def test_the_subject_of_a_qualified_fact_is_reached():
    """The defect in one line: `network.http` is not a subject, `network` is."""
    assert WP._subjects("network.http.available") == ["network.http", "network"]


def test_an_unknown_subject_stays_undecided():
    """Not knowing must never become a yes, and must never become a no."""
    got = WP.probe_effect("definitely.not.a.runtime.available", root=ROOT)
    assert got["true"] is False
    assert got["how"] == "UNDECIDABLE__NOT_ESTABLISHED"


def test_an_absent_binary_is_still_reported_absent():
    """The sensor must not have been weakened into optimism by this change."""
    got = WP.probe_effect("qrencode.runtime.available", root=ROOT)
    assert got["how"] in ("path_executable", "executable_absent")
    if got["how"] == "executable_absent":
        assert got["true"] is False


# --------------------------------------------------------------------------------------------
# 2. The URL the binder threw away
# --------------------------------------------------------------------------------------------
def test_a_url_slot_is_told_apart_from_a_path_slot():
    assert WB._is_url_slot("url")
    assert WB._is_url_slot("source_url")
    assert WB._is_url_slot("href")
    assert not WB._is_url_slot("source_json_path")
    assert not WB._is_url_slot("output_path")


def test_a_lookup_key_is_not_an_address():
    """`url_key` means "the name of the key holding a URL", not a URL.

    This was the first version's bug: it bound the goal's URL into a slot that
    expects a lookup name, and the adapter failed with SOURCE_JSON_REQUIRED.
    """
    assert not WB._is_url_slot("url_key")
    assert not WB._is_url_slot("endpoint_name")


def test_the_goal_s_own_url_is_extracted_without_its_punctuation():
    goal = ("Using the authoritative JSON source "
            "https://api.worldbank.org/v2/country/FRA/indicator?format=json&date=2020, "
            "extract the value.")
    assert WB._url_named_in(goal) == (
        "https://api.worldbank.org/v2/country/FRA/indicator?format=json&date=2020")
    assert WB._url_named_in("(see https://example.org/report).") == "https://example.org/report"


def test_a_goal_naming_no_url_binds_no_url():
    assert WB._url_named_in("audit the python source canonical/runtime/macro_v1.py") is None


def test_the_url_slot_binds_the_url_and_the_path_slot_still_binds_the_file():
    """The whole point: one slot of each, not one value used for both."""
    entry = {
        "capability_id": "knowledge.json.fetch.external",
        "action_template": {"type": "x", "args": {
            "url": "${input.url}", "output_path": "${input.output_path}",
            "json_path": "${input.json_path}", "authoritative": "${input.authoritative}"}},
    }
    goal = ("extract JSON path 1.0.value from https://api.worldbank.org/v2/x?format=json "
            "and save it to canonical/astra_runtime/tmp/out.json")
    out = WB.complete_inputs(goal, ROOT, entry)
    inputs = out["inputs"]
    assert inputs.get("url") == "https://api.worldbank.org/v2/x?format=json"
    assert inputs.get("output_path") != inputs.get("url"), (
        "a URL became a file path, which is the substitution this rule exists to prevent"
    )
