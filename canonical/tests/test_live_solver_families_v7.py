#!/usr/bin/env python3
"""Wave 7: a receipt-backed capability asked for BY NAME must be the one that runs.

This file did not exist. `execution_guard/live_solver_families_v7.py` defines the
`RECEIPT_PROSE_EXECUTION` family with a strict oracle -- the compiled capability id
must equal the one the sentence named, and the tool result must reproduce a
verified sha256 -- and nothing in CI ever ran it. Every other wave (v2 through v6)
has a suite; v7 had an oracle and no test.

That gap hid a measured movement. `canonical/tests/test_capability_naming_rule_v1.py`
was fixed so that a sentence naming a receipt-projected capability consults F17,
which the pinned scorer structurally cannot see. Measured on this family, 3
instances, A/B by disabling that one hook:

    hook disabled:  1/3 pass, both failures "wrong capability ran:
                    python.task.acceptance.measured.objective.v1"
    hook enabled:   3/3 pass

Nothing asserted any of it. Over 12 instances the rate is 7/12, and all five
remaining failures are the same misroute on lexical siblings
(`bytes_characteristic_`, `bytes_discrete_sequence_`, `bytes_domain_free_`,
`bytes_hblind_` variants of `bytes_active_query_task_generator_v1`), where a k=3
retrieval shortlist cannot disambiguate. That residual is recorded here rather
than papered over: admitting the named entry directly was attempted and measured
as a REGRESSION -- it broke 7 tests in
`canonical/tests/test_live_brain_route_admission_v1.py`, including
`test_both_live_doors_give_the_same_verdict_on_one_sentence` -- so it was reverted.
"""
from __future__ import annotations

import random
import re
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import goal_compiler as gc  # noqa: E402
from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as adm  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry  # noqa: E402
import execution_guard.live_solver_families_v7 as v7  # noqa: E402


@pytest.fixture()
def work(tmp_path_factory):
    d = tmp_path_factory.mktemp("v7_receipt_prose")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _registry():
    return gc._platform_admissible_registry(dict(load_verified_registry()))


# --------------------------------------------------------------------- the generator's own contract


def test_there_are_receipt_backed_capabilities_to_ask_for_by_name():
    """The family is vacuous if the list is empty, and an empty list is silent."""
    targets = v7._receipt_backed()
    assert targets, "no independently verified receipt-backed capability: the family cannot run"
    for t in targets[:20]:
        assert t.get("capability_id"), t


def test_the_name_sentence_never_leaks_the_repository_path():
    """The generator's documented contract: the capability's own words, nothing else.

    A sentence containing the path or the `.py.auto.vN` suffix would make the test
    a lookup rather than a routing check -- the machine would be handed the answer.
    """
    for t in v7._receipt_backed()[:40]:
        cid = t["capability_id"]
        sentence = v7._name_sentence(cid)
        assert "/" not in sentence, (cid, sentence)
        assert ".py" not in sentence, (cid, sentence)
        assert ".auto." not in sentence, (cid, sentence)
        assert sentence.startswith("Run the ") and sentence.endswith("."), sentence


def test_every_target_is_named_by_its_own_sentence():
    """The rule the routing fix depends on, over a sample rather than one lucky case."""
    checked = 0
    for t in v7._receipt_backed()[:40]:
        cid = t["capability_id"]
        if "/" not in cid:
            # A dotted id has no module stem to judge a name against; the fix
            # deliberately refuses to treat one as named, so it is out of scope
            # here rather than silently passing.
            continue
        sentence = v7._name_sentence(cid)
        assert front.request_names_capability_id(sentence, cid), (cid, sentence)
        checked += 1
    assert checked >= 10, f"only {checked} targets exercised the naming rule"


# --------------------------------------------------------------------- the oracle itself


def test_the_oracle_rejects_a_result_from_the_wrong_capability(work):
    """The oracle must catch the exact misroute this family exists to measure."""
    case = v7.gen_receipt_prose_execution(random.Random(11), work, 0)
    assert case.family == "RECEIPT_PROSE_EXECUTION"
    ok, why = case.oracle({"compiled_capability_id": "python.task.acceptance.measured.objective.v1"})
    assert ok is False
    assert "wrong capability ran" in why, why


def test_the_oracle_rejects_a_correct_capability_that_returned_no_tool_result(work):
    case = v7.gen_receipt_prose_execution(random.Random(11), work, 0)
    cid = None
    for t in v7._receipt_backed():
        if v7._name_sentence(t["capability_id"]) == case.goal:
            cid = t["capability_id"]
            break
    assert cid, "the case goal must name one of the receipt-backed capabilities"
    ok, why = case.oracle({"compiled_capability_id": cid, "execution": []})
    assert ok is False
    assert "no tool result" in why, why


# --------------------------------------------------------------------- end to end, the real claim


def test_a_capability_asked_for_by_name_is_the_one_that_runs(work):
    """THE claim, end to end, through the one entry every caller uses.

    With the F17 naming hook disabled this returns
    `wrong capability ran: python.task.acceptance.measured.objective.v1`, which is
    what makes it a negative control and not a tautology.
    """
    case = v7.gen_receipt_prose_execution(random.Random(11), work, 0)
    result = adm.solve({"task_id": "TEST_V7_NAMED_ROUTE", "goal": case.goal})
    ran = str(result.get("compiled_capability_id") or "")
    named = None
    for t in v7._receipt_backed():
        if v7._name_sentence(t["capability_id"]) == case.goal:
            named = t["capability_id"]
            break
    assert named, case.goal
    assert ran == named, (
        f"the sentence named {named} but {ran or result.get('status')} ran; goal={case.goal!r}"
    )


# The residual that was pinned here is now CLEARED, and the history is kept because
# the number moved in three measured steps over the same 13 path-style targets:
#
#     6 of 13   before this change -- all 7 misroutes lost to
#               python.task.acceptance.measured.objective.v1
#    10 of 13   once taking over a route required the caller's whole name in order;
#               the 3 that remained lost to a SIBLING instead
#    13 of 13   once the most specific name stated wins
#
# The last step matters on its own: "Run the bytes characteristic active query task
# generator v10." also states the whole of bytes_active_query_task_generator_v1,
# because "characteristic" is only an extra word in the middle, so iteration order
# picked the less specific sibling. A caller who says the longer name means it.
KNOWN_MISROUTES: set[str] = set()


def test_the_compiler_alone_routes_a_named_capability_without_the_path_in_the_sentence():
    """Routing, isolated from execution: every named capability routes to itself.

    Measured over the first 13 path-style receipt-backed targets. The floor is 13
    because 13 is what it does; if a future change costs one of them its route this
    fails and says which.
    """
    reg = _registry()
    good, bad = [], []
    for t in v7._receipt_backed()[:14]:
        cid = t["capability_id"]
        if "/" not in cid:
            continue
        sentence = v7._name_sentence(cid)
        try:
            selected = front.compile_goal(sentence, reg, ROOT).get("selected_capability")
        except gc.GoalCompilationFailure as exc:
            selected = "<raised:" + str(getattr(exc, "code", "?")) + ">"
        (good if selected == cid else bad).append((cid.rsplit("/", 1)[-1], selected))
    assert len(good) >= 13, (
        f"only {len(good)} of {len(good) + len(bad)} named capabilities routed to themselves: {bad}"
    )
    assert not bad, f"misroutes: {bad}"


def test_a_capability_whose_name_is_only_part_of_the_sentence_is_not_taken_to_be_named():
    """The evidence needed to TAKE a route is stronger than the evidence to refuse one.

    Measured before this was tightened: judging a name against the raw sentence let a
    repository PATH do the naming -- one ordinary "Call the function classify_support
    in canonical/runtime/bounded_claim_support.py ..." sentence read as naming 16
    receipt projections, and admitting the first of them broke 4 tests in
    test_live_brain_route_admission_v1.py.  A path is not prose, an identifier is not
    prose, and one shared word is not a name.
    """
    ordinary = ("Call the function classify_support in canonical/runtime/bounded_claim_support.py "
                "with the payload canonical/astra_runtime/tmp/door_agreement.json and save the "
                "result to canonical/astra_runtime/tmp/door_agreement_out.json.")
    audit = ("Audit the python source file canonical/runtime/goal_compiler.py with an AST parser "
             "and save the report to canonical/astra_runtime/tmp/audit.json.")
    reg = _registry()
    for goal in (ordinary, audit):
        claimed = [cid for cid in reg
                   if (reg[cid] or {}).get("capability_source") == "receipt_projection"
                   and front.request_states_the_capability_name(goal, cid)]
        assert not claimed, (goal, claimed)


def test_a_stated_version_excludes_the_sibling_it_does_not_name():
    """A stronger guarantee than the one this test used to assert.

    It previously recorded that "Run the bytes characteristic active query task
    generator v10." ALSO states the whole of bytes_active_query_task_generator_v1,
    with "characteristic" as an extra word in the middle, so specificity had to
    decide.  Honouring a stated version removes the ambiguity outright: the sentence
    says v10, the sibling says v1, so the sibling is not named at all.
    """
    long_cid = "canonical/runtime/bytes_characteristic_active_query_task_generator_v10.py.auto.v1"
    short_cid = "canonical/runtime/bytes_active_query_task_generator_v1.py.auto.v1"
    reg = _registry()
    assert long_cid in reg and short_cid in reg
    sentence = v7._name_sentence(long_cid)
    assert front.request_states_the_capability_name(sentence, long_cid), sentence
    assert not front.request_states_the_capability_name(sentence, short_cid), sentence
    assert front._named_receipt_projection(sentence, reg, None,
                                           front.request_states_the_capability_name) == long_cid


def test_when_two_names_are_equally_stated_the_more_specific_one_wins():
    """The specificity tie-break on its own, on a synthetic pair with no versions.

    Kept as a unit check because the live corpus no longer contains a pair that
    reaches it -- versions now separate every sibling that used to.  Without it the
    tie-break would be untested code that only looks redundant.
    """
    reg = {
        "canonical/runtime/alpha_beta.py.auto.v1": {
            "capability_source": "receipt_projection"},
        "canonical/runtime/alpha_beta_gamma.py.auto.v1": {
            "capability_source": "receipt_projection"},
    }
    sentence = "Run the alpha beta gamma."
    names = front.request_states_the_capability_name
    assert names(sentence, "canonical/runtime/alpha_beta.py.auto.v1")
    assert names(sentence, "canonical/runtime/alpha_beta_gamma.py.auto.v1")
    assert front._named_receipt_projection(sentence, reg, None, names) == \
        "canonical/runtime/alpha_beta_gamma.py.auto.v1"


def test_every_path_style_receipt_backed_capability_routes_to_itself_when_named():
    """ALL of them, not a sample: 294 capabilities, each named by its own sentence.

    Measured in three steps over the same 294:

        270 of 294  before a stated version was honoured
        287 of 294  once a stated version had to match, reading the version only
                    from the END of the name -- which wrongly rejected
                    terminal_frontier_factorizer_v6_candidate, whose version sits
                    mid-name, and handed the route to ..._v6
        294 of 294  once the version is read from anywhere in the name and matched
                    as a set, so current_terminal_authority_v3_k6_v4_verifier works
                    too

    Every one of the 24 original failures was a VERSION SIBLING: "Run the
    composition cross step no bypass audit v2." matched _v1 and _v2 identically
    because the trailing version token was dropped, both tie-break on the same word
    count and the same stem length, and iteration order picked _v1.  The harness
    generator documents the rule this implements: "the version is part of the name,
    because the retrieval path separates a capability's version siblings only when
    the request states the version."
    """
    reg = _registry()
    targets = [t for t in v7._receipt_backed() if "/" in t["capability_id"]]
    assert len(targets) >= 200, f"only {len(targets)} targets: the corpus shrank"
    bad = []
    for t in targets:
        cid = t["capability_id"]
        sentence = v7._name_sentence(cid)
        try:
            selected = front.compile_goal(sentence, reg, ROOT).get("selected_capability")
        except gc.GoalCompilationFailure as exc:
            selected = "<raised:" + str(getattr(exc, "code", "?")) + ">"
        if selected != cid:
            bad.append((cid, selected))
    assert not bad, f"{len(bad)} of {len(targets)} misrouted; first few: {bad[:6]}"


def test_a_stated_version_selects_that_version_and_not_its_sibling():
    """The sibling rule as behaviour, on names that really exist in the registry."""
    v1 = "canonical/runtime/escape_progress_shared_gap_audit_v1.py.auto.v1"
    v2 = "canonical/runtime/escape_progress_shared_gap_audit_v2.py.auto.v1"
    v3 = "canonical/runtime/escape_progress_shared_gap_audit_v3.py.auto.v1"
    reg = _registry()
    for cid in (v1, v2, v3):
        assert cid in reg, cid
    # each sentence states exactly one version, and only that capability may claim it
    for want, others in ((v1, (v2, v3)), (v2, (v1, v3)), (v3, (v1, v2))):
        sentence = v7._name_sentence(want)
        assert front.request_states_the_capability_name(sentence, want), sentence
        for other in others:
            assert not front.request_states_the_capability_name(sentence, other), (sentence, other)
        assert front._named_receipt_projection(sentence, reg, None,
                                               front.request_states_the_capability_name) == want


def test_a_version_mid_name_is_still_part_of_the_name():
    """Reading only the trailing token rejected the right capability outright."""
    cid = "canonical/runtime/terminal_frontier_factorizer_v6_candidate.py.auto.v1"
    sibling = "canonical/runtime/terminal_frontier_factorizer_v6.py.auto.v1"
    reg = _registry()
    if cid not in reg or sibling not in reg:
        pytest.skip("the mid-name version pair is not in this registry")
    sentence = v7._name_sentence(cid)
    assert front.request_states_the_capability_name(sentence, cid), sentence
    assert front._named_receipt_projection(sentence, reg, None,
                                           front.request_states_the_capability_name) == cid


def test_a_name_with_no_version_still_matches_a_versioned_capability():
    """The reason the trailing token is dropped at all -- prose omits the version."""
    cid = "canonical/runtime/bytes_active_query_task_generator_v1.py.auto.v1"
    sentence = "Run the bytes active query task generator."
    assert "v1" not in sentence
    assert front.request_states_the_capability_name(sentence, cid), sentence


def test_a_target_that_routes_by_name_carries_the_rule_that_made_it_possible():
    """The mechanism is named in the evidence, so the win cannot become accidental."""
    reg = _registry()
    for t in v7._receipt_backed()[:14]:
        cid = t["capability_id"]
        if "/" not in cid or cid.rsplit("/", 1)[-1] in KNOWN_MISROUTES:
            continue
        sentence = v7._name_sentence(cid)
        compiled = front.compile_goal(sentence, reg, ROOT)
        if compiled.get("selected_capability") != cid:
            continue
        rules = " ".join((compiled.get("front_compiler") or {}).get("rules_applied") or [])
        assert re.search(r"F29_NAMED_RECEIPT_PROJECTION", rules), (cid, rules)
        return
    pytest.fail("no path-style target routed to itself, so the rule could not be evidenced")
