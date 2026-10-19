#!/usr/bin/env python3
"""F29: the request must NAME the capability - and the catch-all must survive it.

Why this file exists, and why it is NEW rather than an addition to an existing test file.
The module-invocation evidence (`canonical/runtime/MODULE_INVOCATION_EVIDENCE_V1.json`) pins
the sha256 of every test file that holds passing evidence for an inventory module, and
`brain_module_invoke_v1` re-checks those pins on every call.  Editing a pinned test file
makes the evidence stale, and the module-invocation capability then refuses to run the
functions that file evidenced - measured here: editing
`canonical/tests/test_capability_selection_retrieval_v1.py` made
`brain.module.function.invoke` answer `TEST_EVIDENCE_STALE` for the module
`canonical/runtime/bounded_claim_support.py`, and the live doors then disagreed about the
verdict of one sentence.  A new file is not pinned by anything, so the rule below can be
asserted without making any other capability's evidence stale.

THE DEFECT.  Measured: "Run the thing." selected `run_long_horizon_continuity_v1`.  "run" is
the only capability name in the whole registry that contains it, so the ranker found NO
competitor, the margin was 1.0, and the machine reported success on a request that described
no task at all.  The score had matched a VERB.  A request that names nothing must fail
closed, and it must fail closed AT THE MOUTH - through the one entry every caller uses - not
only inside the compiler.

THE EXEMPTION.  A capability whose declared contract takes the WHOLE REQUEST makes no claim to
have been named: it exists to serve any sentence, and it can never be selected anyway, because
a candidate with no specific input is not evidence that the sentence asked for it.  Refusing it
would delete the fallback and replace the true diagnosis - "the request named nothing, so
nothing specific was found" - with a refusal that names a capability the request never
mentioned.  The diagnosis must stay `CATCH_ALL_ONLY__NO_STRUCTURAL_MATCH`.

THE CONTRACT.  A capability whose declared contract names real inputs does not need its name in
the request: the typed binder refuses every candidate whose contract the sentence did not
state, so a bound contract is STRONGER evidence than a name word.  Measured: "Call the function
classify_support in canonical/runtime/bounded_claim_support.py with the payload .../x.json and
save the result to .../y.json" names no word of `brain.module.function.invoke` and is still
exactly that capability's route.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import capability_selection_retrieval_v1 as sel  # noqa: E402
from canonical.runtime import goal_compiler as gc  # noqa: E402
from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as adm  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_capability_naming_rule"
STATE = ROOT / "canonical/astra_runtime/state"


def _registry():
    return gc._platform_admissible_registry(dict(load_verified_registry()))


def _cleanup(task_id: str) -> None:
    for p in STATE.glob(task_id + "__*"):
        p.unlink()


def _entry(cid: str, contract: dict, keywords: list[str]) -> dict:
    return {"capability_id": cid, "status": "VERIFIED_BOUND_CAPABILITY", "incremental_spend_usd": 0,
            "entrypoint": "run", "provides": ["x.y"], "keywords": keywords,
            "action_template": {"type": "invoke_capability", "args": contract,
                                "expect": {"type": "field_equals", "field": "status", "value": "OK"}}}


# ------------------------------------------------------------------ the naming rule itself


def test_f29_a_request_that_names_nothing_fails_closed():
    """The compiler must refuse a request that names no capability."""
    reg = _registry()
    try:
        compiled = front.compile_goal("Run the thing.", reg, ROOT)
    except gc.GoalCompilationFailure as exc:
        assert exc.code == "GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH", exc.detail
    else:
        raise AssertionError("a request that names no capability must fail closed, got %r"
                             % compiled.get("selected_capability"))


def test_f29_the_one_entry_does_not_report_success_for_a_request_that_names_nothing():
    """The refusal must be real at the mouth.

    Measured through `solve()` - the ONE entry every caller uses - "Run the thing." returned a
    successful result for `run_long_horizon_continuity_v1`.  The machine claimed to have done
    work it was never asked for.  It must refuse instead.
    """
    task_id = "TEST_F29_NAMED_NOTHING_%d" % os.getpid()
    try:
        result = adm.solve({"task_id": task_id, "goal": "Run the thing."})
    finally:
        _cleanup(task_id)
    assert result["pass"] is False, result
    assert not str(result.get("status", "")).startswith("PASS"), result
    assert "run_long_horizon_continuity" not in json.dumps(result), result


def test_f29_a_named_capability_is_still_selected():
    """F29 must not cost a capability its route: a request that NAMES it still selects it."""
    reg = _registry()
    compiled = front.compile_goal("Run the bytes active query task generator.", reg, ROOT)
    assert compiled.get("selected_capability") == \
        "canonical/runtime/bytes_active_query_task_generator_v1.py.auto.v1"


def test_f29_a_request_that_names_nothing_is_refused_by_typed_admission():
    """The refusal must be a REFUSAL with a reason, not a wrong answer."""
    registry = {"run.long_horizon.continuity.stdlib": _entry("run.long_horizon.continuity.stdlib",
                                                              {}, ["run", "continuity"])}
    decision = sel.select("Run the thing.", registry, ROOT)
    assert decision["status"] == "NOT_SELECTED"
    assert decision["selected_capability"] is None
    reasons = [str(row.get("reason", "")) for row in decision["admissions"]]
    assert "REQUEST_DOES_NOT_NAME_CAPABILITY" in reasons, decision["admissions"]


def test_f29_does_not_delete_the_catch_all_fallback():
    """A catch-all makes no claim to have been named, and the diagnosis must survive.

    A capability that takes the whole request exists to serve ANY sentence, and it can never
    be selected anyway (it has no specific input, so binding it is not evidence).  Refusing it
    under F29 would replace the true diagnosis - "the request named nothing, so nothing
    specific was found" - with a refusal that names a capability the request never mentioned.
    """
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / "any.json").write_text("{}", encoding="utf-8")
    rel = (WORK / "any.json").relative_to(ROOT).as_posix()
    out = (WORK / "any_out.json").relative_to(ROOT).as_posix()
    registry = {"absorb.everything.stdlib": _entry("absorb.everything.stdlib",
                                                   {"goal": "${input.goal}",
                                                    "output_path": "${input.output_path}"},
                                                   ["summarise", "file", "save", "output"])}
    decision = sel.select(f"Summarise {rel} and save it to {out}", registry, ROOT)
    assert decision["status"] == "NOT_SELECTED"
    assert "CATCH_ALL_ONLY" in str(decision["reason"]), decision
    reasons = [str(row.get("reason", "")) for row in decision["admissions"]]
    assert "REQUEST_DOES_NOT_NAME_CAPABILITY" not in reasons, decision["admissions"]


def test_f29_the_rule_has_exactly_three_ways_to_be_earned():
    """The rule itself, stated as behaviour rather than as prose.

    1. the request NAMES the capability (a non-verb word of its name appears in the request);
    2. the request STATED the contract (a specific contract, which the binder checks);
    3. the capability TAKES THE WHOLE REQUEST (the catch-all, which claims nothing).
    A contract that states no task at all is NOT one of them: the name is then the only link
    between the request and the capability, so the request must use it.
    """
    # 1. the name
    assert sel.request_names_capability("Run the bytes active query task generator.",
                                         "bytes_active_query_task_generator_v1")
    # a VERB is not a name
    assert not sel.request_names_capability("Run the thing.", "run_long_horizon_continuity_v1")
    # 2. the contract
    assert sel.request_may_select("Summarise the file and save it.",
                                   "absorb.everything.stdlib", ["source_path", "output_path"])
    # 3. the whole request
    assert sel.request_may_select("Summarise the file and save it.",
                                   "absorb.everything.stdlib", ["goal", "output_path"])
    # and NOT a contract that states no task: the name is then the only link
    assert not sel.request_may_select("Summarise the file and save it.",
                                      "absorb.everything.stdlib", ["output_path"])
    assert not sel.request_may_select("Run the thing.",
                                      "run_long_horizon_continuity_v1", [])


def test_f29_the_catch_all_is_exempt_because_it_claims_nothing():
    """The exemption is a property of the CONTRACT, not of the entry."""
    # a whole-request capability is exempt even when the request shares no word of its name
    assert sel.request_may_select("Do the needful thing.", "absorb.everything.stdlib",
                                   ["goal", "output_path"])
    # the same capability with a contract that states a task is judged on that contract
    assert sel.request_may_select("Do the needful thing.", "absorb.everything.stdlib",
                                   ["source_path", "output_path"])


def teardown_module(_module=None) -> None:
    shutil.rmtree(WORK, ignore_errors=True)
