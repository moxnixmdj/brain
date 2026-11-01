"""A refusal that names its own reason is reported as that reason.

Measured on main at ``6aa5dab``: seven of the thirteen unserved sentences in the 49-request census
reported ``FAIL__LIVE_CONTROLLER_EXECUTION``, which reads as the runtime falling over.  Calling each
adapter directly showed seven deliberate refusals and zero exceptions from the engine.  The reason
was in the exception text the whole time, in the convention roughly forty adapter classes already
use -- ``RuntimeError("<CLASS>:<detail>")`` -- and the door discarded it because it only recognised
the ``SystemExit(json.dumps({"error": True, ...}))`` spelling.

These tests pin the classifier from both sides: every row that accepts a refusal is paired with the
nearest world in which it must stay a crash.  A classifier that returns a refusal for everything
would pass the first four assertions and fail the last three.
"""
from __future__ import annotations

import pytest

from canonical.runtime.live_brain_route_admission_v1 import (
    _ALREADY_SATISFIED_RE,
    _REFUSAL_CLASS_EXCLUDED,
    _refusal_status_and_payload,
)


def _classify(message: str):
    return _refusal_status_and_payload(RuntimeError(message), "some.capability.v1")


# --------------------------------------------------------------------------------------
# The reason inside a wrapper is the class, because it is the thing with its own fix.
# --------------------------------------------------------------------------------------

def test_a_wrapped_refusal_reports_the_inner_class_and_not_the_wrapper():
    """``POLYGLOT_REFUSED:CPP_NO_APPLICABLE_TRANSFORM`` names a family and then a cause."""
    status, reason, payload = _classify("POLYGLOT_REFUSED:CPP_NO_APPLICABLE_TRANSFORM")
    assert status == "FAIL_CLOSED__CAPABILITY_REFUSED_CPP_NO_APPLICABLE_TRANSFORM"
    assert payload["class"] == "CPP_NO_APPLICABLE_TRANSFORM"
    assert "CPP_NO_APPLICABLE_TRANSFORM" in reason


def test_the_six_polyglot_refusals_are_six_different_statuses():
    """The whole point: six problems that shared one label must not share it any more.

    This is the falsifier for "just report the outer family": every message below wraps the same
    ``POLYGLOT_REFUSED`` family, so a classifier that stops at the wrapper returns one status for
    all six and this assertion fails.
    """
    messages = [
        "POLYGLOT_REFUSED:CPP_NO_APPLICABLE_TRANSFORM",
        "POLYGLOT_REFUSED:SQL_UNSUPPORTED_DDL_EDIT",
        "POLYGLOT_REFUSED:PYPROJECT_ALREADY_PINNED_OR_EMPTY",
        "POLYGLOT_REFUSED:NO_DECLARED_DEPENDENCY_TO_VENDOR",
        "POLYGLOT_REFUSED:NO_FLAKY_TEST_DETECTED",
        "POLYGLOT_REFUSED:TARGET_SYMBOL_COLLISION",
    ]
    statuses = {_classify(m)[0] for m in messages}
    assert len(statuses) == len(messages)
    assert "FAIL_CLOSED__CAPABILITY_REFUSED_POLYGLOT_REFUSED" not in statuses


def test_a_chain_deeper_than_two_still_ends_at_the_reason():
    """The door wraps what the adapter raised, so the chain grows from the outside.

    Measured on main at 85e2b81: once the door began keeping the adapter's key, the same refusal
    arrived as ``CAPABILITY_REFUSED:POLYGLOT_REFUSED:CPP_NO_APPLICABLE_TRANSFORM``. A single
    unwrap reported the middle token, and six distinct refusals collapsed onto one class again --
    5 distinct classes where there had been 9. The reason is the last token, however deep it is.
    """
    status, _reason, payload = _classify(
        "CAPABILITY_REFUSED:POLYGLOT_REFUSED:CPP_NO_APPLICABLE_TRANSFORM")
    assert status == "FAIL_CLOSED__CAPABILITY_REFUSED_CPP_NO_APPLICABLE_TRANSFORM"
    assert payload["class"] == "CPP_NO_APPLICABLE_TRANSFORM"


def test_unwrapping_stops_at_the_last_token_and_keeps_the_payload():
    """A chain that ends in ``TOKEN:detail`` keeps the detail and stops unwrapping."""
    status, _reason, payload = _classify(
        "CAPABILITY_REFUSED:POLYGLOT_REFUSED:NO_FLAKY_TEST_DETECTED:suite.txt")
    assert status == "FAIL_CLOSED__CAPABILITY_REFUSED_NO_FLAKY_TEST_DETECTED"
    assert payload["class"] == "NO_FLAKY_TEST_DETECTED"


def test_a_two_level_class_promotes_the_inner_token():
    """``OUTER:INNER:detail`` -- the middle token is the class, the rest is the detail."""
    status, _reason, payload = _classify("OUTER_REFUSED:INNER_TOKEN_REASON:the detail b")
    assert status == "FAIL_CLOSED__CAPABILITY_REFUSED_INNER_TOKEN_REASON"
    assert payload["class"] == "INNER_TOKEN_REASON"


def test_a_flat_class_keeps_its_own_name_and_its_detail():
    """``TARGET_SYMBOL_COLLISION:add`` is one class with a detail, not a wrapper."""
    status, reason, payload = _classify("TARGET_SYMBOL_COLLISION:add")
    assert status == "FAIL_CLOSED__CAPABILITY_REFUSED_TARGET_SYMBOL_COLLISION"
    assert payload["reason"] == "add"
    assert reason == "CAPABILITY_REFUSED:add"


def test_the_payload_carries_the_capability_that_refused():
    """A caller must be able to tell *which* capability said no without re-running it."""
    _status, _reason, payload = _classify("PATH_MISSING:/nope")
    assert payload["capability"] == "some.capability.v1"
    assert payload["error"] is True


# --------------------------------------------------------------------------------------
# ...and the nearest worlds in which it must NOT be called a capability refusal.
# --------------------------------------------------------------------------------------

def test_a_bare_compound_refusal_key_is_a_refusal():
    """A refusal key does not have to carry a detail.

    ``NO_MODIFIED_PYTHON_FUNCTIONS_BETWEEN_REVISIONS`` is one of the repository's own keys and says
    everything it has to say, but it has no colon, so it was reported as a controller crash.
    Measured on main at 29ada61: census request 32, the last unexplained row in the inventory.
    """
    status, reason, payload = _classify("NO_MODIFIED_PYTHON_FUNCTIONS_BETWEEN_REVISIONS")
    assert status == "FAIL_CLOSED__CAPABILITY_REFUSED_NO_MODIFIED_PYTHON_FUNCTIONS_BETWEEN_REVISIONS"
    assert payload["class"] == "NO_MODIFIED_PYTHON_FUNCTIONS_BETWEEN_REVISIONS"
    assert reason == "CAPABILITY_REFUSED:NO_MODIFIED_PYTHON_FUNCTIONS_BETWEEN_REVISIONS"


@pytest.mark.parametrize("message", ["SEGFAULT", "Timeout", "KeyError", "CRASHED"])
def test_a_single_shouting_word_is_still_a_crash(message):
    """The rule is structural, not "anything in capitals is a refusal".

    A refusal key is a snake-case condition name -- a compound of words. A crash label is one word.
    This is the nearest world in which the bare-key rule must not fire, and it is what keeps the
    rule honest rather than a blanket ``[A-Z]+`` match.
    """
    assert _classify(message) is None


@pytest.mark.parametrize(
    "message",
    [
        "FileNotFoundError raised while importing the module",
        "Traceback: KeyError('targets')",
        "the controller crashed for no stated reason",
        "",
    ],
)
def test_a_message_with_no_class_token_is_still_a_crash(message):
    """A generic failure must stay ``FAIL__LIVE_CONTROLLER_EXECUTION``.

    Without this the previous five tests are satisfied by a classifier that calls everything a
    refusal, and every real crash would be filed as a missing capability.
    """
    assert _classify(message) is None


def test_a_bare_class_token_with_no_detail_is_not_treated_as_a_refusal():
    """Adapters always spell ``CLASS:detail``; a bare caps word is not evidence of a refusal."""
    assert _classify("SEGFAULT") is None


def test_an_already_satisfied_answer_outranks_a_refusal():
    """``BASELINE_ALREADY_PASSES:test_x`` matches the class convention exactly.

    The requested post-state is *true* there, so reporting it as a capability refusal would turn a
    success into a failure.  This is the falsifier for the ordering hazard the first draft had: the
    refusal branch was inserted before the already-satisfied branch and stole the answer.
    """
    assert _ALREADY_SATISFIED_RE.search("BASELINE_ALREADY_PASSES:test_the_thing_works")
    assert _classify("BASELINE_ALREADY_PASSES:test_the_thing_works") is None
    assert _classify("ALREADY_SATISFIED:x") is None
    assert _classify("NOTHING_TO_DO:x") is None


def test_the_excluded_control_flow_signals_stay_excluded():
    """``ACTION_EXPECTATION_FAILED`` is a retry signal the caller may still recover from."""
    assert "ACTION_EXPECTATION_FAILED" in _REFUSAL_CLASS_EXCLUDED
    assert _classify("ACTION_EXPECTATION_FAILED:the attempt did not match the plan") is None
