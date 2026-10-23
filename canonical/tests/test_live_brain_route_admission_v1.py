"""Fail-closed route admission in front of the live Brain.

Measured on 2026-10-15 (canonical/capabilities/true/LIVE_SOLVER_END_TO_END_MEASUREMENT_20261015_V1.json):
through ``run_raw_goal`` 100 of 100 fresh out-of-scope goals ("translate ...", "prove ...",
"summarize ...") came back PASS because a repository path token such as ``runtime`` matched a
keyword of a zero-input tool.  ``solve`` must refuse those before anything executes, and must
not refuse the goals the compiler really serves.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import goal_compiler  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as adm  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_live_brain_route_admission"
STATE = ROOT / "canonical/astra_runtime/state"


def _registry():
    return goal_compiler._platform_admissible_registry(dict(load_verified_registry()))


def _compile(goal: str):
    return goal_compiler.compile_goal(goal, _registry(), ROOT)


def _cleanup(task_id: str) -> None:
    for p in STATE.glob(task_id + "__*"):
        p.unlink()


def setup_module(_module=None):
    WORK.mkdir(parents=True, exist_ok=True)


def teardown_module(_module=None):
    if WORK.exists():
        shutil.rmtree(WORK)


# ----------------------------------------------------------------------------- pure rules

def test_path_token_only_match_is_rejected_before_execution():
    goal = "Translate the sentence 'good morning' into French and save it to canonical/astra_runtime/tmp/test_live_brain_route_admission/fr.txt."
    compiled = _compile(goal)
    # Nothing here can translate, so the compiler fails open and picks *something*; R1 must
    # catch it.  Which wrong capability wins is not the subject of this test, and it moves as
    # the corpus grows -- asserting the property keeps the test about the thing it is about.
    assert compiled.get("selected_capability"), "expected the compiler to fail open here"
    verdict = adm.route_admission(goal, compiled, _registry())
    assert verdict["admitted"] is False
    assert verdict["rule"] == "R1_PATH_TOKENS_ONLY"
    assert verdict["semantic_matched_tokens"] == []
    # The match came only out of a repository path, never from the goal's meaning.  Which token
    # it was ("runtime", "live") is a property of whichever capability the compiler happened to
    # pick, so pinning it re-introduces exactly the fragility removed two lines up.
    assert verdict["matched_from_paths_only"], verdict


def test_future_artifact_with_tool_that_cannot_write_is_rejected():
    goal = "Prove that the square root of 2 is irrational and save the proof to canonical/astra_runtime/tmp/test_live_brain_route_admission/proof.md."
    compiled = _compile(goal)
    verdict = adm.route_admission(goal, compiled, _registry())
    assert verdict["admitted"] is False
    assert verdict["rule"] == "R2_OUTPUT_ARTIFACT_UNSERVED"
    assert verdict["capability_output_keys"] == []
    assert verdict["goal_future_artifacts"]


def test_single_word_evidence_is_rejected():
    goal = "Write a Python tutorial for beginners and save it to canonical/astra_runtime/tmp/test_live_brain_route_admission/tut.md."
    compiled = _compile(goal)
    verdict = adm.route_admission(goal, compiled, _registry())
    assert verdict["admitted"] is False
    assert verdict["rule"] == "R3_WEAK_EVIDENCE"
    assert verdict["semantic_matched_tokens"] == ["python"]


def test_real_archive_goal_is_admitted_even_though_its_paths_share_tokens():
    manifest = WORK / "manifest.json"
    src = WORK / "src.txt"
    src.write_text("admitted", encoding="utf-8")
    manifest.write_text(json.dumps({"records": [{"verification_paths": ["canonical/astra_runtime/tmp/test_live_brain_route_admission/src.txt"]}]}), encoding="utf-8")
    goal = ("Create a tar.gz archive from the manifest canonical/astra_runtime/tmp/test_live_brain_route_admission/manifest.json "
            "and save it to canonical/astra_runtime/tmp/test_live_brain_route_admission/out.tar.gz.")
    compiled = _compile(goal)
    assert compiled.get("selected_capability") == "archive.tar_gz.create_from_manifest"
    verdict = adm.route_admission(goal, compiled, _registry())
    assert verdict["admitted"] is True, verdict
    assert {"archive", "tar", "gz"} <= set(verdict["semantic_matched_tokens"])


def test_controller_plans_without_a_selected_capability_are_not_judged_by_token_overlap():
    compiled = _compile('Respond with exactly "orientation 42".')
    verdict = adm.route_admission('Respond with exactly "orientation 42".', compiled, _registry())
    assert verdict["admitted"] is True
    assert verdict["selected_capability"] is None


def test_tool_truth_rule_catches_pass_false_and_non_success_status():
    result = {"execution": [{"capability_id": "x", "result": {"pass": False, "output_verified": True}}]}
    assert adm.tool_truth_errors(result) == ["TOOL_REPORTED_PASS_FALSE:x"]
    result = {"execution": [{"capability_id": "y", "result": {"status": "OPEN__SEMANTIC_RESIDUALS", "output_verified": True}}]}
    assert adm.tool_truth_errors(result) == ["TOOL_REPORTED_NON_SUCCESS_STATUS:y:OPEN__SEMANTIC_RESIDUALS"]
    result = {"execution": [{"capability_id": "z", "result": {"status": "UNRESOLVED", "outcome": "UNRESOLVED"}}]}
    assert adm.tool_truth_errors(result)[0].startswith("TOOL_REPORTED_NON_SUCCESS_STATUS:z:UNRESOLVED")
    assert adm.tool_truth_errors({"execution": [{"capability_id": "ok", "result": {"status": "PASS", "pass": True}}]}) == []


# ----------------------------------------------------------------------------- end to end

def test_solve_fails_closed_on_out_of_scope_goal_and_writes_nothing():
    out = WORK / "summary.txt"
    src = WORK / "notes.txt"
    src.write_text("alpha\nbeta\n", encoding="utf-8")
    task_id = "TEST_ROUTE_ADMISSION_OOS_%d" % os.getpid()
    try:
        result = adm.solve({"task_id": task_id, "goal": f"Summarize the file canonical/astra_runtime/tmp/test_live_brain_route_admission/notes.txt into three sentences and save the summary to canonical/astra_runtime/tmp/test_live_brain_route_admission/summary.txt."})
    finally:
        _cleanup(task_id)
    assert result["pass"] is False
    # with zero-input tools blocked from plain goals (F4) nothing can match; before F4 the same
    # goal reached admission and was rejected there - both are fail-closed with nothing written
    #
    # The comment above always described two acceptable outcomes but the assertion pinned one,
    # so the test went red the moment the goal moved to the other side of the same boundary.
    # What must hold is that it fails closed, executes nothing, spends nothing and writes
    # nothing -- the four assertions below that, not which gate caught it.
    assert result["status"] in {"FAIL__RAW_GOAL_COMPILATION_GAP",
                                "FAIL_CLOSED__ROUTE_ADMISSION_REJECTED"}, result["status"]
    assert result["executed"] is False
    assert result["incremental_spend_usd"] == 0
    assert not out.exists()


def test_a_manifest_not_named_manifest_now_binds_by_the_role_the_sentence_gives_it():
    """This used to assert a defect: a manifest not named *manifest* could not bind, so the
    compiler silently fell through to a zero-input catch-all and the guard had to refuse it.

    The defect is closed.  ``_bind_inputs`` now falls back to the role the sentence assigns --
    "the manifest X" names X as the manifest whatever X is called -- so this exact goal binds
    ``archive.tar_gz.create_from_manifest`` with the manifest and the output as two different
    paths.  Asserting the fixed behaviour turns a characterization of a known gap into a
    regression guard for the fix."""
    manifest = WORK / "m9.json"
    src = WORK / "s9.txt"
    src.write_bytes(b"fallback")
    manifest.write_text(json.dumps({"records": [{"verification_paths": ["canonical/astra_runtime/tmp/test_live_brain_route_admission/s9.txt"]}]}), encoding="utf-8")
    goal = ("Create a tar.gz archive from the manifest canonical/astra_runtime/tmp/test_live_brain_route_admission/m9.json, "
            "including all its verification_paths files, and save it to canonical/astra_runtime/tmp/test_live_brain_route_admission/bundle9.tar.gz.")
    compiled = _compile(goal)
    assert compiled.get("selected_capability") == "archive.tar_gz.create_from_manifest"
    inputs = compiled.get("inputs") or {}
    # the manifest and the archive are different files; binding both to the output was the bug
    assert inputs.get("manifest_path", "").endswith("/m9.json"), inputs
    assert inputs.get("output_path", "").endswith("/bundle9.tar.gz"), inputs
    assert inputs.get("manifest_path") != inputs.get("output_path"), inputs
    verdict = adm.route_admission(goal, compiled, _registry())
    assert verdict["admitted"] is True, verdict


def test_solve_still_executes_a_real_goal():
    manifest = WORK / "manifest2.json"
    src = WORK / "s2.txt"
    out = WORK / "bundle2.tar.gz"
    src.write_bytes(b"solve executes real goals\n")
    manifest.write_text(json.dumps({"records": [{"verification_paths": ["canonical/astra_runtime/tmp/test_live_brain_route_admission/s2.txt"]}]}), encoding="utf-8")
    if out.exists():
        out.unlink()
    task_id = "TEST_ROUTE_ADMISSION_ARCHIVE_%d" % os.getpid()
    try:
        result = adm.solve({"task_id": task_id, "goal": (
            "Create a tar.gz archive from the manifest canonical/astra_runtime/tmp/test_live_brain_route_admission/manifest2.json, "
            "including all its verification_paths files, and save it to canonical/astra_runtime/tmp/test_live_brain_route_admission/bundle2.tar.gz.")})
    finally:
        _cleanup(task_id)
    assert result["pass"] is True, result.get("status")
    assert result["route_admission"]["admitted"] is True
    assert result["model_dependency_count"] == 0
    with tarfile.open(out, "r:gz") as tf:
        names = [m.name for m in tf.getmembers() if m.isfile()]
        assert any(n.endswith("s2.txt") for n in names)
        member = next(m for m in tf.getmembers() if m.name.endswith("s2.txt"))
        assert tf.extractfile(member).read() == b"solve executes real goals\n"


def test_solve_compilation_gap_is_reported_as_before():
    task_id = "TEST_ROUTE_ADMISSION_GAP_%d" % os.getpid()
    try:
        result = adm.solve({"task_id": task_id, "goal": "Calibrate the neutrino interferometer phase drift."})
    finally:
        _cleanup(task_id)
    assert result["pass"] is False
    assert result["failure_class"] == "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP"


def _a_receipt_backed_capability_id() -> str:
    return next(c for c, e in sorted(load_verified_registry().items())
                if e.get("capability_source") == "receipt_projection")


def test_an_explicitly_named_capability_is_admitted_and_executed():
    """The other half of this file's contract: never refuse a goal the compiler really serves.

    Measured before: all 294 receipt-backed capabilities were selected by the front layer and
    then refused here with R1_PATH_TOKENS_ONLY, and the R6 gate then demanded the capability
    write a file named after itself.  None of the 294 could pass through this entry."""
    cid = _a_receipt_backed_capability_id()
    task_id = "TEST_NAMED_CAPABILITY_%d" % os.getpid()
    try:
        result = adm.solve({"task_id": task_id, "goal": f"run {cid}"})
    finally:
        _cleanup(task_id)
    assert result["status"] == (
        "PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED"
        "__RAW_ACCEPTANCE_RECEIPTS_STILL_REQUIRED"
    ), result.get("status")
    assert result["pass"] is True, result.get("status")
    assert result["compiled_capability_id"] == cid
    assert result["route_admission"]["admission_basis"] == "EXPLICIT_CAPABILITY_ID_IN_GOAL"
    # the R6 gate reports only what is missing; the capability's own id is not a promised file
    assert "promised_artifact_errors" not in result
    assert result["routing_success_authority"] is False
    assert result["model_dependency_count"] == 0


def test_both_live_doors_give_the_same_verdict_on_one_sentence():
    """Measured defect, asserted so it cannot come back: ONE sentence, TWO verdicts.

    On the same sentence - "Call the function classify_support ... with the payload ... and save the
    result to ..." - `solve()` answered `FAIL_CLOSED__ROUTE_ADMISSION_REJECTED` while
    `run_raw_goal` executed it and wrote the real result.  Root cause: a receipt-backed entry's
    executable template names only the capability itself, so every rule that reads the entry's
    argument contract (R2's artifact check, the renderer, the binder) saw a tool that takes no input.
    The loader now composes the DECLARED argument contract onto the derived entry (additively: the
    zero-input form stays), and both doors read the same entry.

    Both doors are run here and compared, because a statement about "the live Brain" that only holds
    for one of its doors is the defect this test exists for.
    """
    from canonical.runtime import live_integrated_brain_v1 as live_brain
    from canonical.runtime import capability_receipt_lane_v1 as lane

    WORK.mkdir(parents=True, exist_ok=True)
    payload = WORK / "door_agreement.json"
    payload.write_text(json.dumps({"claim_text": "Orion budget is 40.",
                                   "evidence_text": "The audited ledger reports that Orion budget is 40."}),
                       encoding="utf-8")
    out = WORK / "door_agreement_out.json"
    if out.is_file():
        out.unlink()
    rel = payload.relative_to(ROOT).as_posix()
    goal = (f"Call the function classify_support in canonical/runtime/bounded_claim_support.py with "
            f"the payload {rel} and save the result to {out.relative_to(ROOT).as_posix()}")
    before = lane._changed_paths(str(ROOT))
    try:
        first = adm.solve({"task_id": "TEST_DOOR_AGREEMENT_SOLVE", "goal": goal})
        written = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else None
        if out.is_file():
            out.unlink()
        second = live_brain.run_raw_goal({"task_id": "TEST_DOOR_AGREEMENT_RAW", "goal": goal})
        again = json.loads(out.read_text(encoding="utf-8")) if out.is_file() else None
    finally:
        for result in (locals().get("first"), locals().get("second")):
            checkpoint = ((result or {}).get("controller_checkpoint") or {}).get("path")
            nested = (((result or {}).get("controller_execution") or {}).get("controller_checkpoint") or {}).get("path")
            for path in (checkpoint, nested):
                if path and (ROOT / path).is_file():
                    (ROOT / path).unlink()
        if out.is_file():
            out.unlink()
        lane.restore_tree(str(ROOT), before, ())
    assert first["pass"] is True, first.get("status")
    assert second["pass"] is True, second.get("status")
    assert first["compiled_capability_id"] == second["compiled_capability_id"] == "brain.module.function.invoke"
    assert written and again and written["result"] == again["result"]
    assert written["result"]["relation"] == "SUPPORTS"
    # the door reports WHY it was admitted: the sentence states the capability's declared contract
    assert first["route_admission"]["admission_basis"] == "DECLARED_INPUT_CONTRACT_FULLY_STATED_IN_GOAL"


def test_a_capability_identity_is_never_a_promised_artifact():
    """F16's rule at the R6 gate: the id is an identity, and the artifact check still works."""
    cid = _a_receipt_backed_capability_id()
    assert adm._future_artifacts(f"run {cid}") == []
    assert adm._future_artifacts("save it to canonical/astra_runtime/tmp/real_future_artifact.md")


def test_a_ghost_capability_id_is_refused_before_anything_executes():
    cid = _a_receipt_backed_capability_id()
    ghost = cid.rsplit(".py.auto.v1", 1)[0] + "_renamed.py.auto.v1"
    result = adm.solve({"task_id": "TEST_GHOST_ID", "goal": f"run {ghost}"})
    assert result["status"] == "FAIL__RAW_GOAL_COMPILATION_GAP"
    assert result["compiler_code"] == "GOAL_NAMES_UNKNOWN_CAPABILITY"


# --------------------------------------------------------------------------- #
# R9: a capability that consumes a file must not be admitted for a fileless goal
# --------------------------------------------------------------------------- #
# Measured before R9: "extract text from a pdf file" selected pdf.extract.text.pypdf, whose only
# declared input is pdf_path, with goal_future_artifacts empty and no path token anywhere in the
# sentence.  This layer admitted it, so the front reported
# PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED with pass=True and
# executed=True while creating ZERO files.  Nothing was extracted because nothing was named to
# extract from.
#
# The asymmetry is the defect: the same capability, given a path that does not exist, already
# refuses with GOAL_INPUT_BINDING_REQUIRED.  Supplying LESS information was treated as MORE
# admissible.  An unbindable path fails, so no path at all must fail too.


def _admit(goal):
    r = adm.solve_or_learn({"task_id": "t", "goal": goal})
    return r, (r.get("route_admission") or {})


def test_file_capability_is_refused_when_the_goal_names_no_file():
    r, a = _admit("extract text from a pdf file")
    assert a.get("admitted") is False, a
    assert a.get("rule") == "R9_REQUIRED_FILE_INPUT_UNBOUND", a
    assert "pdf_path" in (a.get("unbound_file_inputs") or []), a
    assert not r.get("pass"), r.get("status")
    assert "EXECUTED_AND_VERIFIED" not in str(r.get("status")), r.get("status")


def test_naming_a_file_still_admits_the_same_capability():
    """R9 must refuse the empty case only, not the capability."""
    _, a = _admit("extract text from report.pdf")
    assert a.get("admitted") is True, a
    assert a.get("selected_capability") == "pdf.extract.text.pypdf", a


def test_an_absolute_path_still_admits():
    _, a = _admit("extract text from the pdf file /tmp/none.pdf")
    assert a.get("rule") != "R9_REQUIRED_FILE_INPUT_UNBOUND", a


def test_the_file_predicate_is_generous_so_r9_only_fires_on_truly_fileless_goals():
    for goal in ("read a.txt", "convert /abs/path/b.md", "use ~/c.json", "open file.tar.gz"):
        assert adm._goal_names_a_file(goal), goal
    for goal in ("extract text from a pdf file", "summarize this document", "translate the readme"):
        assert not adm._goal_names_a_file(goal), goal


def test_a_capability_with_no_file_input_is_untouched_by_r9():
    """R9 must not become a general refusal of goals that lack a filename."""
    _, a = _admit("compute the sum of 2 and 3")
    assert a.get("rule") != "R9_REQUIRED_FILE_INPUT_UNBOUND", a


def test_r9_does_not_move_the_compile_or_selection_rates():
    """Compile and correct-selection are the standing acceptance criteria."""
    from canonical.runtime import goal_compilation_benchmark_v1 as bench

    c = bench.run_all()["combined"]
    assert c["compiled"] == 23, c
    assert c["expected_first_selected"] == 22, c
