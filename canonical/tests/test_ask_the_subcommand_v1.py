"""Tests for asking a program the right question before calling it unbound.

Every test asserts a measurement taken from a real program on the host. Several exist
because a number was wrong first, and the docstring names the defect so it is not
re-litigated later.
"""

from __future__ import annotations

import shutil

import pytest

from canonical.runtime import ask_the_subcommand_before_you_call_it_unbound_v1 as A
from canonical.runtime import tool_census_v1 as C

HAVE = {n: shutil.which(n) for n in ("cp", "mv", "rm", "openssl", "tar", "grep")}


# --------------------------------------------------------------------------- #
# 1. a failed run is not a clean one
# --------------------------------------------------------------------------- #
def test_a_failed_run_is_not_reported_as_a_clean_one():
    """The defect that made 545 openssl operations look like sensors.

    `verdict = "NO_EFFECT"` was assigned to any run that left the tree alone, whatever
    its exit status. The census's own wording for that verdict says "exited cleanly and
    moved nothing", so a program that REFUSED the invocation was reported as having
    computed a value. Both are "no change"; only one is an answer.
    """
    if not HAVE["openssl"]:
        pytest.skip("needs openssl")
    census = C.census("openssl", depth=2, max_ops=40)
    contract = C.parse_contract(C._own_text("openssl"), "openssl")
    bound = [C.bind(op, contract=contract) for op in census["operations"]]
    graded = C.commit_check_many(bound, seed=C.trial_seeds(), preparation="PLAIN")
    rows = graded.get("rows") or []
    failed = [r for r in rows if r.get("verdict") == "FAILED_NO_EFFECT"]
    assert failed, "no run failed, so this test is not exercising the defect"
    assert all(r.get("exit") not in (0, None) for r in failed), \
        "a FAILED_NO_EFFECT row must carry a non-zero exit"
    clean = [r for r in rows if r.get("verdict") == "NO_EFFECT"]
    assert all(r.get("exit") in (0, None) for r in clean), \
        "a NO_EFFECT row must have exited cleanly"


def test_the_false_sentence_is_gone_for_failed_runs():
    """A receipt that says "exited cleanly" about a failed run is a lie with a schema."""
    if not HAVE["openssl"]:
        pytest.skip("needs openssl")
    census = C.census("openssl", depth=2, max_ops=40)
    contract = C.parse_contract(C._own_text("openssl"), "openssl")
    bound = [C.bind(op, contract=contract) for op in census["operations"]]
    graded = C.commit_check_many(bound, seed=C.trial_seeds(), preparation="PLAIN")
    split = C.classify(census["operations"], graded, contract=contract,
                       admitted=len(census["operations"]))
    for row in split["unbound"]:
        if "never ran as declared" in str(row.get("why")):
            assert "exited cleanly" not in str(row.get("why"))


# --------------------------------------------------------------------------- #
# 2. a subcommand has its own document
# --------------------------------------------------------------------------- #
def test_a_subcommand_is_asked_about_itself():
    """`openssl -h` describes no operation; `openssl asn1parse -h` describes nine."""
    if not HAVE["openssl"]:
        pytest.skip("needs openssl")
    parent = A.scope_text("openssl")
    child = A.scope_text("openssl", "asn1parse")
    assert parent["text"], "the parent must answer something"
    assert child["text"], "the child must answer something"
    assert child["has_usage"], "openssl asn1parse -h prints a Usage: line"
    assert child["asked_as"] == ["openssl", "asn1parse", "-h"]


def test_the_admitted_subcommands_come_from_the_census_not_a_second_probe():
    """Discovery was duplicated and the second copy was worse.

    The census already asked every candidate and recorded which words are doors plus how
    many operations each declares. Re-deriving them here produced ZERO admitted
    subcommands for a program that has 24, because the local `looks_like_help` gate
    rejected `openssl -h` -- a genuine subcommand table that the predicate does not
    recognise as a help page.
    """
    if not HAVE["openssl"]:
        pytest.skip("needs openssl")
    census = C.census("openssl", depth=2, max_ops=40)
    stored = [r["subcommand"] for r in (census.get("subcommands_admitted") or [])]
    assert stored, "the census must have admitted subcommands for openssl"
    run = A.classify_at_scope("openssl", max_ops=40)
    assert run["subcommands_admitted"] == stored


def test_each_scope_gets_its_own_contract():
    """One contract per program is the defect; a contract per scope is the fix."""
    if not HAVE["openssl"]:
        pytest.skip("needs openssl")
    scopes = A.contracts_by_scope("openssl", ["asn1parse", "x509"])
    assert set(scopes) == {"", "asn1parse", "x509"}
    parent_flags = len(scopes[""]["contract"].get("flags") or [])
    child_flags = len(scopes["asn1parse"]["contract"].get("flags") or [])
    assert child_flags > parent_flags, \
        "the child's own help lists flags the parent's does not"


# --------------------------------------------------------------------------- #
# 3. the kinds are decided by evidence, and there are few of them
# --------------------------------------------------------------------------- #
def test_every_unbound_operation_lands_in_exactly_one_kind():
    """A doubt that is in no bucket is a doubt nobody will act on."""
    if not HAVE["cp"]:
        pytest.skip("needs cp")
    run = A.classify_at_scope("cp", max_ops=40)
    kinds = A.kinds_of_ignorance(
        run["classified"],
        A.contracts_by_scope("cp", run["subcommands_admitted"]), run["rows"])
    assert kinds["total"] == run["classified"]["counts"]["UNBOUND"]
    assert all(k in A.KINDS for k in kinds["counts"])
    assert sum(kinds["counts"].values()) == kinds["total"]


def test_a_real_refusal_outranks_a_documentary_guess():
    """A run that refused the invocation is a FACT; a missing usage line is an inference.

    The kinds are evidence-ordered for that reason: `DROVE_IT_WRONG` is decided from a
    non-zero exit that actually happened, so no amount of help-text reasoning may
    outrank it.
    """
    if not HAVE["openssl"]:
        pytest.skip("needs openssl")
    run = A.classify_at_scope("openssl", max_ops=40)
    kinds = A.kinds_of_ignorance(
        run["classified"],
        A.contracts_by_scope("openssl", run["subcommands_admitted"]), run["rows"])
    assert kinds["counts"][A.DROVE_IT_WRONG] > 0
    for row in kinds["by_kind"][A.DROVE_IT_WRONG]:
        assert "refused" in row["evidence"] or "exited" in row["evidence"]


def test_the_questions_are_ranked_by_a_count_not_a_prior():
    """`ignorance_ledger` ranks by a beta prior; that cannot say which question settles most.

    An untried doubt and an untried doubt about anything else both score 0.5. Here the
    worth of asking is the number of verdicts the question decides, which is counted from
    the census's own rows and cannot flatter itself.
    """
    if not HAVE["openssl"]:
        pytest.skip("needs openssl")
    run = A.classify_at_scope("openssl", max_ops=40)
    questions = A.what_to_ask("openssl", run["subcommands_admitted"], run["classified"])
    assert questions
    decides = [q["decides"] for q in questions]
    assert decides == sorted(decides, reverse=True), "most doubt deleted first"
    assert sum(decides) == run["classified"]["counts"]["UNBOUND"]
    assert questions[0]["rank"] == 1


# --------------------------------------------------------------------------- #
# 4. the doubt must survive the process
# --------------------------------------------------------------------------- #
def test_a_doubt_reaches_the_ledger():
    """Nothing on the program path had ever written to the ledger.

    Measured before this round: 82 gaps on disk, 0 resolved, and every doubt about a
    program re-derived from nothing on the next run.
    """
    import os
    import tempfile
    from canonical.runtime import ignorance_ledger_v1 as L

    path = os.path.join(tempfile.mkdtemp(prefix="brain-ledger-test-"), "L.json")
    assert L.open_gaps(path) == 0
    result = A.note_to_ledger({"counts": {A.DROVE_IT_WRONG: 7}}, path=path)
    assert result["noted"], "the kind must be recorded"
    assert result["noted"][0]["operations"] == 7
    assert L.open_gaps(path) == 1, "the doubt must persist on disk"


# --------------------------------------------------------------------------- #
# 5. a rejected generalisation stays rejected
# --------------------------------------------------------------------------- #
def test_the_value_slot_rule_is_not_generalised_again():
    """A rule that looked principled cost a door and was reverted; this pins that.

    `_VALUE_SLOTS` is a hand-written name list, so generalising it is tempting: "a
    placeholder that is not a content slot is an option argument". Measured, it moved `cp`
    from 31 NO_EFFECT + 2 CHANGES to 30 FAILED_NO_EFFECT + 1 CHANGES -- real content
    placeholders are not all in `_CONTENT_SLOTS` either, so both directions of the guess
    lose doors. The doors are the control: they must survive any change to binding.
    """
    if not HAVE["cp"]:
        pytest.skip("needs cp")
    census = C.census("cp", depth=2, max_ops=40)
    contract = C.parse_contract(C._own_text("cp"), "cp")
    bound = [C.bind(op, contract=contract) for op in census["operations"]]
    graded = C.commit_check_many(bound, seed=C.trial_seeds(), preparation="PLAIN")
    doors = [r for r in graded["rows"] if r.get("verdict") in C.DOOR_VERDICTS]
    assert len(doors) >= 2, "the generalised rule dropped a cp door"


def test_every_unbound_operation_is_triaged_resolvable_or_exhausted():
    """The axis the five kinds were missing: can chasing this pay at all?

    LLM-IDEA names the failure exactly -- an agent that cannot tell "I have not looked
    yet" from "no further search will recover this" either refines against a target its
    data cannot constrain, or abandons something one more question would have settled.
    Here it is a property of the kind, so nothing is left in an untriaged state.
    """
    if not HAVE["cp"]:
        pytest.skip("needs cp")
    run = A.classify_at_scope("cp", max_ops=40)
    kinds = A.kinds_of_ignorance(
        run["classified"],
        A.contracts_by_scope("cp", run["subcommands_admitted"]), run["rows"])
    assert set(kinds["resolvability"]) <= {A.ASK, A.DRIVE, A.EXHAUSTED, A.UNDETERMINED}
    assert sum(kinds["resolvability"].values()) == kinds["total"]
    assert all(kinds["resolvability"][A.RESOLVABILITY[k]] > 0
               for k in kinds["counts"] if kinds["counts"][k] > 0)
