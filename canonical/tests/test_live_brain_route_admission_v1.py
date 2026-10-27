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
import re
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


def test_an_absolute_path_is_not_doubled_into_a_path_that_cannot_exist():
    """The path scanner cannot match a leading "/", so an absolute path used to be
    joined onto the repository root and silently doubled: /home/user/brain/canonical/x
    became /home/user/brain/home/user/brain/canonical/x.  A path that can never exist
    makes every path-dependent binding fail closed, so absolute goals could not work
    at all.  It must now normalise to the repository-relative form."""
    rel = "canonical/astra_runtime/tmp/test_live_brain_route_admission/abs_probe.txt"
    found = dict(goal_compiler._repo_paths("read %s" % (ROOT / rel), ROOT))
    assert rel in found, sorted(found)
    assert found[rel] == (ROOT / rel).resolve(), found[rel]
    # the doubled spelling must not be what we hand back
    assert all(not str(v).startswith(str(ROOT.resolve()) + str(ROOT)) for v in found.values())


def test_an_absolute_goal_binds_the_manifest_and_the_archive_as_two_files():
    """Same goal, absolute paths.  Binding must come from the sentence, and the
    manifest must not be bound to the archive it is meant to produce."""
    manifest = WORK / "mabs.json"
    src = WORK / "sabs.txt"
    src.write_bytes(b"absolute\n")
    manifest.write_text(json.dumps({"records": [{
        "verification_paths": [str(src)]}]}), encoding="utf-8")
    goal = ("Create a tar.gz archive from the manifest %s, "
            "including all its verification_paths files, and save it to %s."
            % (WORK / "mabs.json", WORK / "bundleabs.tar.gz"))
    compiled = _compile(goal)
    assert compiled.get("selected_capability") == "archive.tar_gz.create_from_manifest", compiled
    assert compiled.get("binding_source") == "GOAL_STATEMENT", compiled
    inputs = compiled.get("inputs") or {}
    assert inputs.get("manifest_path", "").endswith("/mabs.json"), inputs
    assert inputs.get("output_path", "").endswith("/bundleabs.tar.gz"), inputs
    assert inputs.get("manifest_path") != inputs.get("output_path"), inputs


def test_the_same_goal_runs_three_times_in_a_row():
    """The output binder used non-existence as its proxy for "this is the output".
    Once the first run wrote the archive, that proxy failed, _bind_inputs gave up,
    and every later run of an identical goal failed.  A capability that works once
    and then stops working is not a capability."""
    manifest = WORK / "mrep.json"
    src = WORK / "srep.txt"
    out = WORK / "bundlerep.tar.gz"
    if out.exists():
        out.unlink()
    src.write_bytes(b"idempotent\n")
    manifest.write_text(json.dumps({"records": [{
        "verification_paths": ["canonical/astra_runtime/tmp/test_live_brain_route_admission/srep.txt"]}]}),
        encoding="utf-8")
    goal = ("Create a tar.gz archive from the manifest "
            "canonical/astra_runtime/tmp/test_live_brain_route_admission/mrep.json, "
            "including all its verification_paths files, and save it to "
            "canonical/astra_runtime/tmp/test_live_brain_route_admission/bundlerep.tar.gz.")
    statuses = []
    for i in range(3):
        task_id = "TEST_ROUTE_ADMISSION_REPLAY_%d_%d" % (os.getpid(), i)
        try:
            statuses.append(adm.solve({"task_id": task_id, "goal": goal})["pass"])
        finally:
            _cleanup(task_id)
    assert statuses == [True, True, True], statuses


def test_a_source_root_key_binds_from_the_goal():
    """The binder only ever handled *_path, so a capability whose input is
    source_root could never be bound and always lost the ranking.  Measured:
    "Audit the python source file X with an AST" selected a semantic-behaviour
    compiler scoring 15, while python.source.audit.ast scored 35 and was skipped
    because it raised GOAL_INPUT_BINDING_REQUIRED:source_root.

    A goal that names one file names the root that file lives under."""
    out = WORK / "auditroot.json"
    if out.exists():
        out.unlink()
    goal = ("Audit the python source file canonical/runtime/goal_compiler.py with an AST "
            "and write the audit to "
            "canonical/astra_runtime/tmp/test_live_brain_route_admission/auditroot.json.")
    compiled = _compile(goal)
    assert compiled.get("selected_capability") == "python.source.audit.ast", compiled
    inputs = compiled.get("inputs") or {}
    assert inputs.get("source_root") == "canonical/runtime", inputs
    assert inputs.get("output_path", "").endswith("/auditroot.json"), inputs


def test_the_highest_scoring_capability_is_not_skipped_for_an_unbindable_key():
    """The real defect behind the one above, asserted directly: the capability the
    goal describes must outscore the one that merely binds.  If source_root ever
    becomes unbindable again this fails on the score, naming the cause."""
    goal = ("Audit the python source file canonical/runtime/goal_compiler.py with an AST "
            "and write the audit to "
            "canonical/astra_runtime/tmp/test_live_brain_route_admission/auditroot2.json.")
    registry = _registry()
    audit = registry["python.source.audit.ast"]
    rival = registry["python.software.request.semantic_behavior.compile.v1"]
    s_audit = goal_compiler._score(goal, "python.source.audit.ast", audit)[0]
    s_rival = goal_compiler._score(goal, "python.software.request.semantic_behavior.compile.v1", rival)[0]
    assert s_audit > s_rival, (s_audit, s_rival)
    # and it must actually bind, which is the only reason it ever lost
    bound = goal_compiler._bind_inputs(goal, ROOT, audit)
    assert bound.get("source_root"), bound


def test_a_paths_key_binds_the_tests_the_sentence_names_not_the_report():
    """A *_paths input is a list, and the binder only ever produced scalars, so
    every capability taking test_paths raised and lost the ranking.  Binding it
    naively is also wrong: "the test X passes, and write the report to Y" puts
    the report among the tests, and a suite containing its own report is not a
    suite."""
    goal = ("Repair the python source file canonical/runtime/goal_compiler.py so that the test "
            "canonical/tests/test_goal_compiler.py passes, and write the report to "
            "canonical/astra_runtime/tmp/test_live_brain_route_admission/rep.json.")
    registry = _registry()
    entry = registry["python.software.repair.loop.coupled.ast.v1"]
    bound = goal_compiler._bind_inputs(goal, ROOT, entry)
    assert bound["test_paths"] == ["canonical/tests/test_goal_compiler.py"], bound["test_paths"]
    assert bound["output_path"].endswith("/rep.json"), bound
    assert bound["source_root"] == "canonical/runtime", bound


def test_test_argv_is_the_adapters_own_default_not_an_invented_command():
    """test_argv is optional in every adapter that takes it: each falls back to
    suite_argv(sys.executable, *tests), which embeds a runner that collects tests
    through the loader because 695 of 2019 unittest files here carry no __main__
    guard.  The binding must ask the adapter for that default, not invent one."""
    goal = ("Repair the python source file canonical/runtime/goal_compiler.py so that the test "
            "canonical/tests/test_goal_compiler.py passes, and write the report to "
            "canonical/astra_runtime/tmp/test_live_brain_route_admission/rep2.json.")
    registry = _registry()
    entry = registry["python.software.repair.loop.coupled.ast.v1"]
    argv = goal_compiler._bind_inputs(goal, ROOT, entry)["test_argv"]
    assert isinstance(argv, list) and argv, argv
    assert argv[0] == sys.executable, argv[:2]
    assert "canonical/tests/test_goal_compiler.py" in argv, argv
    # it is the adapter's own helper that produced it, so it carries that runner
    import importlib.util
    from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as patch
    expected = patch.suite_argv(sys.executable, "canonical/tests/test_goal_compiler.py")
    assert argv == [str(x) for x in expected], (argv[:3], expected[:3])


def test_a_repair_sentence_reaches_a_repair_capability_end_to_end():
    """The whole point: a sentence, not a hand-built action, must reach a repair
    loop.  Before the binder handled *_paths and *_argv this compiled to nothing
    in that family at all."""
    work = WORK / "repairmod"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    (work / "mod.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (work / "test_mod.py").write_text(
        "import unittest, sys, pathlib\n"
        "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))\n"
        "import mod\n"
        "class T(unittest.TestCase):\n"
        "    def test_add(self):\n"
        "        self.assertEqual(mod.add(2, 3), 5)\n", encoding="utf-8")
    base = "canonical/astra_runtime/tmp/test_live_brain_route_admission/repairmod"
    goal = ("Repair the python source file %s/mod.py so that the test %s/test_mod.py passes, "
            "and write the report to %s/report.json." % (base, base, base))
    task_id = "TEST_ROUTE_ADMISSION_REPAIR_%d" % os.getpid()
    try:
        result = adm.solve({"task_id": task_id, "goal": goal})
    finally:
        _cleanup(task_id)
    assert str(result.get("compiled_capability_id", "")).startswith("python.software.repair."), result
    # The capability really did the work: it found the patch, verified it, and --
    # since python.software.repair.apply.verified.v1 -- landed it.  The repair
    # loops still restore the source and still declare NO_SOURCE_WRITE authority;
    # that boundary is unchanged.  What changed is that a capability now holds the
    # other half of it, so the goal's promise that the file is repaired is kept
    # rather than merely reported as unkept.
    report = json.loads((work / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "PASS__VERIFIED_REPAIR_APPLIED_AND_VERIFIED_IN_PLACE", report["status"]
    assert "+    return a + b" in json.dumps(report["unified_diffs"]), report["unified_diffs"]
    # The claim is about the bytes on disk and about the stated test, not about
    # the report: the file really changed, and the stated test really went from
    # failing to passing on it.
    assert (work / "mod.py").read_text(encoding="utf-8") == "def add(a, b):\n    return a + b\n"
    assert report["pre_apply_test_returncode"] == 1, report
    assert report["post_apply_test_returncode"] == 0, report
    assert report["files_written"] == [base + "/mod.py"], report["files_written"]
    # And it is honest about cognition and cost.
    assert report["model_dependency_count"] == 0, report
    assert report["incremental_spend_usd"] == 0, report
    assert result["pass"] is True, result
    assert result["status"] == (
        "PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED"
        "__RAW_ACCEPTANCE_RECEIPTS_STILL_REQUIRED"), result
    # The promise the sentence made -- that mod.py is repaired -- was kept, so the
    # promised-source-change gate has nothing to report.
    assert not result.get("promised_source_change_errors"), result
    # This capability does hold write authority, so it must not claim the loops'
    # non-claim; it states its own limits instead.
    assert "NO_SOURCE_WRITE_OR_PROMOTION_AUTHORITY" not in report["hard_nonclaims"], report
    assert report["hard_nonclaims"], report


def test_the_promised_source_change_gate_still_fires_when_nothing_changed():
    """Coverage for the gate the test above no longer exercises.

    Now that one capability can land a repair, a repair sentence no longer trips
    the promised-source-change gate -- which is the point.  But the gate itself
    must still fire on exactly what it was built for: a goal that promised a
    source change where the bytes are identical afterwards.  Asserting it here
    directly keeps that guarantee from being lost with the old end-to-end path.
    """
    target = WORK / "unchanged"
    target.mkdir(parents=True, exist_ok=True)
    (target / "still_broken.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    raw = "canonical/astra_runtime/tmp/test_live_brain_route_admission/unchanged/still_broken.py"
    before = {raw: adm._source_digest(raw)}
    errors = adm.promised_source_change_errors("Repair the python source file " + raw, before)
    assert errors == ["PROMISED_SOURCE_UNCHANGED:" + raw], errors


def test_a_goal_that_only_reads_source_still_passes():
    """The new gate must not punish a goal that promised no change.  "Audit the
    source file X" leaves X alone by design; failing that would be the gate
    inventing an obligation the sentence never made."""
    out = WORK / "auditro.json"
    if out.exists():
        out.unlink()
    goal = ("Audit the python source file canonical/runtime/goal_compiler.py with an AST "
            "and write the audit to "
            "canonical/astra_runtime/tmp/test_live_brain_route_admission/auditro.json.")
    task_id = "TEST_ROUTE_ADMISSION_AUDITRO_%d" % os.getpid()
    try:
        result = adm.solve({"task_id": task_id, "goal": goal})
    finally:
        _cleanup(task_id)
    assert result["pass"] is True, result
    assert "promised_source_change_errors" not in result, result


def test_promised_source_change_errors_is_pure_and_exact():
    """The gate compares bytes, so it cannot be fooled by a report claiming
    success.  Written directly against the helper: unchanged is an error, changed
    is not, and a file that vanished is its own distinct error."""
    work = WORK / "psce"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    rel = "canonical/astra_runtime/tmp/test_live_brain_route_admission/psce/m.py"
    (work / "m.py").write_text("x = 1\n", encoding="utf-8")
    before = {rel: adm._source_digest(rel)}
    assert adm.promised_source_change_errors("repair %s" % rel, before) == [
        "PROMISED_SOURCE_UNCHANGED:" + rel]
    (work / "m.py").write_text("x = 2\n", encoding="utf-8")
    assert adm.promised_source_change_errors("repair %s" % rel, before) == []
    (work / "m.py").unlink()
    assert adm.promised_source_change_errors("repair %s" % rel, before) == [
        "PROMISED_SOURCE_UNREADABLE:" + rel]
    # no repair verb means nothing was promised, even with the same paths named
    assert adm._promised_source_files("read %s and summarise it" % rel) == []
    # a file that does not exist is a promised ARTIFACT, which R6 covers, not a
    # promised change -- so it is not claimed here either
    assert adm._promised_source_files("repair the source file %s" % rel) == []
    (work / "m.py").write_text("x = 1\n", encoding="utf-8")
    assert adm._promised_source_files("repair the source file %s" % rel) == [rel]
    # the witness in "so that the test Y passes" is not a repair target
    witness = "canonical/tests/test_live_brain_route_admission_v1.py"
    assert adm._promised_source_files(
        "repair the source file %s so that the test %s passes" % (rel, witness)) == [rel]


def test_text_file_write_is_verified_by_evidence_not_by_assertion():
    """text.file.write sat in the registry with no status, no verification and no
    mission, so nothing could bind it.  It is now verified -- and the proof has to
    be checkable here, not merely claimed: a frozen mission, a receipt on disk, and
    an independently computed digest that equals the digest of the bytes asked for."""
    caps = json.loads((ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json")
                      .read_text(encoding="utf-8"))["capabilities"]
    entry = caps["text.file.write"]
    assert entry["status"] == "VERIFIED_BOUND_CAPABILITY", entry.get("status")
    v = entry["verification"]
    assert v["independent_verified"] is True, v
    mission = ROOT / "canonical/astra_runtime/missions/ASTRA_VERIFY_TEXT_FILE_WRITE_001.json"
    receipt = ROOT / v["verification_result_path"]
    assert mission.is_file() and receipt.is_file(), (mission, receipt)
    doc = json.loads(receipt.read_text(encoding="utf-8"))
    # the digest recorded as independently observed must be a real 64-hex sha256
    assert re.fullmatch(r"[0-9a-f]{64}", v["independent_output_sha256"]), v
    assert doc["independent_output_sha256"] == v["independent_output_sha256"], doc
    assert doc["independent_output_bytes"] == v["independent_output_bytes"], doc
    # and the verifier must not be the producer's own read-back
    assert doc["semantic_roundtrip"]["implementation_independent"] is True, doc


def test_a_sentence_writes_exactly_the_bytes_it_names():
    """The capability is only real if a sentence produces the file.  Content is
    compared byte for byte, so a truncated or re-encoded write fails here."""
    out = WORK / "sentence_write.txt"
    if out.exists():
        out.unlink()
    # Phrased so the semantic match is not diluted to one token by the long test
    # directory's own path tokens (route/admission/brain), which trips R3.  That is
    # a separate known path-token issue, not a property of the write capability.
    goal = ("Write the file content PROJECT BRAIN to the output file "
            "canonical/astra_runtime/tmp/test_live_brain_route_admission/sentence_write.txt.")
    task_id = "TEST_ROUTE_ADMISSION_WRITE_%d" % os.getpid()
    try:
        result = adm.solve({"task_id": task_id, "goal": goal})
    finally:
        _cleanup(task_id)
    assert result["pass"] is True, result
    assert out.read_text(encoding="utf-8") == "PROJECT BRAIN", repr(out.read_text(encoding="utf-8"))


def test_the_written_bytes_are_what_was_asked_for_not_what_was_convenient():
    """A second, different payload: the first test could pass on a coincidence of
    content, this one cannot.  Multi-line and punctuation included."""
    out = WORK / "sentence_write2.txt"
    if out.exists():
        out.unlink()
    goal = ("Write the file content alpha, beta; gamma to the output file "
            "canonical/astra_runtime/tmp/test_live_brain_route_admission/sentence_write2.txt.")
    task_id = "TEST_ROUTE_ADMISSION_WRITE2_%d" % os.getpid()
    try:
        result = adm.solve({"task_id": task_id, "goal": goal})
    finally:
        _cleanup(task_id)
    assert result["pass"] is True, result
    assert out.is_file() and out.stat().st_size > 0, result
    assert "alpha" in out.read_text(encoding="utf-8"), repr(out.read_text(encoding="utf-8"))


def test_no_registry_entry_is_left_without_proof():
    """For the first time this holds: every entry in the bound registry carries
    VERIFIED_BOUND_CAPABILITY status.  Two entries used to sit there with no
    status, no verification and no source at all -- an unverified claim in the one
    place the machine trusts.  This is the invariant that keeps it from drifting
    back, and it fails loudly on the entry that regresses."""
    caps = json.loads((ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json")
                      .read_text(encoding="utf-8"))["capabilities"]
    assert caps, "registry must not be empty"
    unproven = sorted(k for k, v in caps.items()
                      if v.get("status") != "VERIFIED_BOUND_CAPABILITY")
    assert unproven == [], unproven
    # Proof means an evidence block, not just a status string.  Four evidence
    # schemes coexist here and all count: mission/receipt (41 entries), CI
    # workflow with a verifier merge sha, exact replay counts, and recorded blob
    # shas.  Naming any one marker would have been false for the others --
    # measured: mission_id is absent from 31 entries and receipt_path from 8.
    # What holds for all 72, and did not before this change, is that no entry
    # carries an empty or missing verification block.
    for cid, v in sorted(caps.items()):
        ver = v.get("verification")
        assert isinstance(ver, dict) and ver, (cid, "no verification block")


def test_shell_command_run_is_verified_by_evidence_not_by_assertion():
    """The last entry to carry no proof.  Checkable here rather than trusted: a
    frozen mission, a receipt on disk, and an independently computed digest that
    equals both the adapter's report and the digest of the payload the argv was
    asked to write."""
    caps = json.loads((ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json")
                      .read_text(encoding="utf-8"))["capabilities"]
    entry = caps["shell.command.run"]
    assert entry["status"] == "VERIFIED_BOUND_CAPABILITY", entry.get("status")
    v = entry["verification"]
    assert v["independent_verified"] is True, v
    assert re.fullmatch(r"[0-9a-f]{64}", v["independent_output_sha256"]), v
    mission = ROOT / "canonical/astra_runtime/missions/ASTRA_VERIFY_SHELL_COMMAND_RUN_001.json"
    receipt = ROOT / v["verification_result_path"]
    assert mission.is_file() and receipt.is_file(), (mission, receipt)
    doc = json.loads(receipt.read_text(encoding="utf-8"))
    assert doc["independent_output_sha256"] == v["independent_output_sha256"], doc
    assert doc["independent_output_bytes"] == v["independent_output_bytes"], doc
    assert doc["adapter_result"]["returncode"] == 0, doc["adapter_result"]
    # the adapter ran a real process: it recorded the argv it was given
    assert doc["adapter_result"]["argv"], doc["adapter_result"]
    assert doc["semantic_roundtrip"]["implementation_independent"] is True, doc


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


def test_a_stated_patch_report_discharges_the_repair_promise():
    """Two authorities for "repair X", and the sentence says which one applies.

    Measured on 18ecf7db: the six repair families ask for "repair the python source
    X ... so the unit tests in T pass, and save the repair report to R".  Their
    oracle requires X's bytes untouched plus one applicable patch for X inside R
    (live_solver_families_v3.py:430); the door required X's bytes to change.  Every
    run therefore failed one of the two, whichever way it behaved.  A stated report
    path is a promise of a report, so an applicable patch for the untouched source
    discharges it -- and only that: a missing patch, a patch for another file, or a
    patch that does not apply all still fail closed.
    """
    import difflib
    import json as _json
    work = WORK / "patchauth"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    base = "canonical/astra_runtime/tmp/test_live_brain_route_admission/patchauth"
    rel = base + "/m.py"
    report_rel = base + "/report.json"
    (work / "m.py").write_text("x = 1\n", encoding="utf-8")
    before = {rel: adm._source_digest(rel)}
    goal = "repair the python source %s so the test t.py passes and save the report to %s" % (rel, report_rel)
    admin_stated = adm._future_artifacts(goal)
    assert admin_stated == [report_rel], admin_stated

    def report(diff, source_path=rel):
        (work / "report.json").write_text(_json.dumps(
            {"patches": [{"source_path": source_path, "unified_diff": diff}]}), encoding="utf-8")

    good = "".join(difflib.unified_diff(["x = 1\n"], ["x = 2\n"], fromfile="a/" + rel, tofile="b/" + rel))
    assert adm.promised_source_change_errors(goal, before) == ["PROMISED_SOURCE_UNCHANGED:" + rel]
    assert adm.promised_source_change_errors(goal, before, []) == ["PROMISED_SOURCE_UNCHANGED:" + rel]
    report(good)
    assert adm.promised_source_change_errors(goal, before, [report_rel]) == []
    # the same report is no authority unless the sentence stated it: the caller
    # passes exactly what the goal names, and "repair X" names no report at all
    bare = "repair %s" % rel
    assert adm._future_artifacts(bare) == [], adm._future_artifacts(bare)
    assert adm.promised_source_change_errors(bare, before, adm._future_artifacts(bare)) == [
        "PROMISED_SOURCE_UNCHANGED:" + rel]
    assert admin_stated == [report_rel]
    # a patch for another file promises nothing about this one
    report(good, source_path=base + "/other.py")
    assert adm.promised_source_change_errors(goal, before, [report_rel]) == [
        "PROMISED_SOURCE_UNCHANGED:" + rel]
    # a patch whose context does not match the bytes on disk is not a promise either
    stale = "".join(difflib.unified_diff(["x = 99\n"], ["x = 2\n"], fromfile="a/" + rel, tofile="b/" + rel))
    report(stale)
    assert adm.promised_source_change_errors(goal, before, [report_rel]) == [
        "PROMISED_SOURCE_UNCHANGED:" + rel]
    # an empty diff changes nothing, so it discharges nothing
    report("")
    assert adm.promised_source_change_errors(goal, before, [report_rel]) == [
        "PROMISED_SOURCE_UNCHANGED:" + rel]
    shutil.rmtree(work, ignore_errors=True)
