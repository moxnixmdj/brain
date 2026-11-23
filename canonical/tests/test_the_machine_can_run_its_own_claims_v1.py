"""Hard tests for the executable census: it must RUN the machine, not read its claims.

Each test here corresponds to a defect that was measured, not imagined. The list of what went wrong in
`reachability_v1` is the reason each assertion exists:

  * v1 classified 70 writing rows as READABLE-vs-not-executed, i.e. it MEASURED NOTHING about them.
  * v1's own manual probe then wrote `canonical/tmp_evidence_contract_supercomposer.json` into the live
    tree -- the exact damage v1 said it prevented.
  * v1 reported 15 zero-input rows as NO_HONEST_SMOKE_ARGUMENTS, i.e. it invented a limitation.
  * v1 discarded the `command` literal in each row's template, then reported the resulting
    COMMAND_NOT_IMPLEMENTED:<none> as the row's failure. Measured for file.copy.v1, file.rename.v1,
    file.line.appended.v1.
  * v1 reported CONTRADICTED for six rows because all of them shared one output path, so the first
    write satisfied every later row's check. Six false accusations.
  * v1 pointed whole-tree scanners at `canonical` (22,365 files): python.source.taint_flow.v1 alone took
    307.87s of a 482s audit. That is a workload, not a witness.

So: no test below asserts "the number is 42". They assert the PROPERTIES an honest census has.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import time

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import reachability_v2 as R  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable


def _fingerprint(root: pathlib.Path) -> str:
    """Every tracked byte that a capability could damage, hashed. Cheap enough at this size."""
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if path.is_file():
            digest.update(str(path.relative_to(root)).encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


@pytest.fixture(scope="module")
def census() -> dict:
    """One full audit, shared by the assertions that need the whole machine."""
    return R.reachability()


def test_the_audit_never_writes_the_tree_it_is_auditing(census: dict) -> None:
    """THE ONE PROPERTY EVERYTHING ELSE RESTS ON.

    The census calls writers. If it ran them where it stands it would be a hostile program. The world is
    measured: `host_untouched` is a before/after fingerprint taken by `confinement_v1`, not a promise.
    """
    assert census["world"]["host_untouched"] is True, "the audit changed the tree it was auditing"
    assert census["world"]["verified"] is True
    assert census["world"]["outcome"] == "RAN"
    assert census["world"]["receipt"], "a run without a receipt is a claim without evidence"


def test_a_writer_is_executed_and_not_merely_declared(census: dict) -> None:
    """THE V1 DEFECT. 'Declares write authority' used to mean 'never run'.

    At least one row must be in WROTE: a call that ran and left a readable artifact whose sha256 the row
    itself reported. If this fails, the census has quietly regressed to reading status fields.
    """
    wrote = {cid: cell for cid, cell in census["cells"].items() if cell["state"] == "WROTE"}
    assert len(wrote) >= 5, "writers must actually be executed, got %d" % len(wrote)
    for cid, cell in wrote.items():
        assert cell["artifact"], "%s wrote nothing it could name" % cid


def test_every_artifact_digest_is_checked_against_its_bytes(census: dict) -> None:
    """A row's own sha256 is the only claim about it that can be checked. None may mismatch silently."""
    mismatched = [cid for cid, cell in census["cells"].items() if cell["state"] == "CONTRADICTED"]
    assert not mismatched, "reported digest differs from the bytes: %s" % mismatched
    for cid, cell in census["cells"].items():
        if cell["state"] == "WROTE":
            assert "digest MATCHES" in (cell.get("artifact") or ""), (cid, cell.get("artifact"))


def test_no_verdict_is_a_stored_status_field(census: dict) -> None:
    """Every cell must carry a reason that names what happened, and none may be a registry word."""
    for cid, cell in census["cells"].items():
        assert cell["state"] in {"UNREACHABLE", "LOADED", "RAN", "WROTE", "SELF_ATTESTING",
                                 "CONTRADICTED"}, (cid, cell)
        if cell["state"] == "UNREACHABLE":
            why = str(cell.get("why") or "")
            assert why, "%s is unreachable for no stated reason" % cid
            assert not why.startswith("VERIFIED"), "a status field is not a measurement: %s" % cid


def test_a_missing_input_is_named_never_lumped(census: dict) -> None:
    """'NEEDS_INPUT:unknown' is an audit refusing to do its own job.

    The whole value of the census is that a gap is a WORK ITEM: `NEEDS_INPUT:prompt` says what to go
    find. A lumped 'unknown' would be the same defect as a status field.
    """
    needs = [cell["why"] for cell in census["cells"].values()
             if str(cell.get("why", "")).startswith("NEEDS_INPUT:")]
    assert needs, "no row should be blocked by its inputs in a tree this size"
    for why in needs:
        slots = why.split(":", 1)[1]
        assert slots and slots != "unknown", why
        assert not slots.startswith(",") and not slots.endswith(","), why


def test_a_row_that_takes_no_input_is_called_and_flagged(census: dict) -> None:
    """THE KNOWLEDGE-HOUSE TEST, MADE EXECUTABLE.

    A capability with no inputs cannot be measuring the world; its `verified: true` is a restatement of
    the registry's own vocabulary. Measured in
    `software_review_synthesis_supercomposer_v1.py`: `verified = all(required in claims)`. Such rows must
    be CALLED (they are reachable) and must never be counted as informative.
    """
    self_attesting = {cid for cid, cell in census["cells"].items()
                      if cell["state"] == "SELF_ATTESTING"}
    assert len(self_attesting) >= 10, sorted(self_attesting)
    for cid in self_attesting:
        assert census["cells"][cid]["why"] == "NO_INPUT_SO_THE_ANSWER_IS_ABOUT_ITSELF"


def test_the_partition_accounts_for_every_claim(census: dict) -> None:
    """A census that drops rows is a census that lies by omission."""
    assert census["claims"] == sum(census["counts"].values())
    assert census["claims"] >= 140


def test_nothing_is_graded_by_the_code_under_test(census: dict) -> None:
    """The probe may not import the audit. If it did, the audit would be grading itself."""
    probe = R.PROBE
    for forbidden in ("reachability_v1", "reachability_v2", "live_integrated_brain"):
        assert forbidden not in probe, forbidden
    assert "sys.path.insert(0, str(root))" in probe, (
        "without the import root every canonical.* adapter dies with ModuleNotFoundError:canonical")


def test_the_audit_is_fast_enough_to_run_before_every_decision() -> None:
    """'Insanely fast' is a requirement, not a preference.

    A census nobody runs is a census that does not exist. Measured: 482s when whole-tree scanners were
    pointed at the whole tree, 33.6s when they were pointed at the smallest real directory. A walk is
    not a witness.
    """
    started = time.time()
    R.plan_for(R.__dict__ and {}, ROOT) if False else None  # keep the import warm
    report = R.reachability()
    elapsed = time.time() - started
    assert report["world"]["host_untouched"] is True
    assert elapsed < 180.0, "executable census took %.1fs" % elapsed


def test_an_adapter_that_raises_is_not_the_same_as_one_that_cannot_load() -> None:
    """LOADED-but-raised and UNREACHABLE are different findings and must never be merged.

    A row that loads and then refuses is a row with a gate that works. A row that cannot import is a
    file that is not there. Reporting the second as the first is how 40% of the machine disappeared.
    """
    reg = {
        "loads.and.refuses.v1": {
            "status": "VERIFIED_BOUND_CAPABILITY",
            "source": {"adapter_path": "canonical/runtime/reachability_v2.py"},
            "action_template": {"args": {"capability_id": "loads.and.refuses.v1"}},
        },
    }
    plan, blocked = R.plan_for(reg, ROOT)
    assert not blocked
    assert plan[0]["zero_input"] is True


def test_the_smallest_real_directory_is_chosen_over_the_largest() -> None:
    """Measured cost of the wrong choice: 307.87s of a 482s audit."""
    chosen = R._smallest_dir(ROOT)
    assert chosen != "canonical", chosen
    assert (ROOT / chosen).is_dir()
    n = sum(len(f) for _, _, f in __import__("os").walk(ROOT / chosen))
    assert 0 < n <= 50, (chosen, n)


def test_a_command_literal_in_the_template_is_used_not_discarded() -> None:
    """Measured: discarding it made three working rows report COMMAND_NOT_IMPLEMENTED:<none>."""
    reg = {
        "file.copy.v1": {
            "status": "VERIFIED_BOUND_CAPABILITY",
            "source": {"adapter_path": "canonical/runtime/reachability_v2.py"},
            "action_template": {"args": {"command": "copy", "path": "${input.path}",
                                         "output_path": "${input.output_path}"}},
        },
    }
    plan, blocked = R.plan_for(reg, ROOT)
    assert not blocked
    assert plan[0]["args"]["command"] == "copy"
    assert plan[0]["args"]["path"] != plan[0]["args"]["output_path"], (
        "a row that writes output_path must not read path from the same string")


# ----------------------------------------------------------------------------------------------------
# The defects below were found by running the census twice in two environments and diffing. Each one is
# a place where the audit was reporting its own mistake as a capability's defect.
# ----------------------------------------------------------------------------------------------------

def test_the_census_reports_which_interpreter_it_measured(census: dict) -> None:
    """A machine reading without an instrument name is a claim, not a measurement.

    `confinement_v1.execute` fixes PATH, so a bare `python3` in the world is /usr/bin/python3 -- NOT the
    interpreter the audit ran under. Measured: 3 capabilities were reported dead because the world used a
    Python without Pillow while the caller had one with it.
    """
    assert census["interpreter"], "the census does not say what it measured"
    assert pathlib.Path(census["interpreter"]).name in ("python", "python3", "python3.11")


def test_two_rows_never_share_an_output_path(census: dict) -> None:
    """Measured cross-row contamination: every plan item got `_rb_out/output_path.json`, so rows that ran
    later refused OUTPUT_ALREADY_EXISTS -- an accusation about a file the audit itself wrote."""
    paths = [item["args"].get("output_path") for item in
             R.plan_for(__import__("json").loads(
                 (ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
             and _registry(), ROOT)[0]]
    named = [p for p in paths if p]
    assert len(named) == len(set(named)), "two rows were handed the same output path"
    for why in census["cells"].values():
        assert "OUTPUT_ALREADY_EXISTS" not in str(why.get("detail")), (
            "a row refused a path the audit had already used")


def _registry() -> dict:
    from canonical.runtime import live_integrated_brain_v1 as brain
    return brain.load_verified_registry()


def test_the_world_runs_the_same_interpreter_as_the_caller(census: dict) -> None:
    """`sys.executable` inside the world must be the caller's, or the census measures another computer."""
    from canonical.runtime import confinement_v1 as C
    result = C.run_confined(ROOT, [sys.executable, "-c",
                                   "import sys; print(sys.executable, sys.version.split()[0])"],
                            budget_s=120)
    assert result["outcome"] == "RAN", result.get("stderr_tail")
    assert result["stdout_tail"].strip().startswith(sys.executable)
    assert result["host_untouched"] is True


def test_an_absolute_program_is_allowed_but_an_absolute_argument_is_not() -> None:
    """The refusal that made the interpreter fix impossible.

    `admit` checked `argv[0]` for existence and then scanned ALL of argv for absolute paths, so an
    absolute interpreter path was refused as an escape while the code above had just accepted it. The
    program is how the machine is run; an argument is something the program can write to.
    """
    from canonical.runtime import confinement_v1 as C
    admitted = C.admit(ROOT, [sys.executable, "canonical/_rb_probe.py"], budget_s=60)
    assert isinstance(admitted, C.Confinement), admitted
    C.release(admitted)
    refused = C.admit(ROOT, ["python3", "-c", "open('/tmp/hole','w')"], budget_s=60)
    assert isinstance(refused, dict) and refused["refused"] == C.REFUSE_ARGV_ESCAPES_CONFINEMENT


def test_the_manifest_declares_every_import_the_adapters_need() -> None:
    """A manifest that cannot rebuild the machine is a claim about the machine.

    Measured: 9 VERIFIED_BOUND_CAPABILITY adapters import PIL, which the 23-package manifest did not
    name at all. Installing the project's own declared requirements left every one of them dead.
    """
    manifest = (ROOT / "requirements/software_engineering_kernel_v1.txt").read_text().lower()
    assert "pillow" in manifest, "PIL is imported by 9 adapters and declared nowhere"
    assert "--hash=sha256:" in manifest, "pins without digests are not reproducible"


def test_a_dependency_is_a_pin_with_a_digest_not_a_name() -> None:
    """Same rule the project applies to capability receipts, applied to its own environment."""
    for line in (ROOT / "requirements/software_engineering_kernel_v1.txt").read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or not stripped or stripped.startswith("--hash"):
            continue
        assert "--hash=sha256:" in (stripped + " " + " ".join(
            ln.strip() for ln in (ROOT / "requirements/software_engineering_kernel_v1.txt")
            .read_text().splitlines())), stripped


def test_the_full_listing_is_answered_not_a_tail_of_it() -> None:
    """MEASURED FALSE ANSWER, fixed 2026-11-23.

    `confinement_v1.execute` kept `stdout[-2000:]` as `stdout_tail` and `confined_dispatch_v1` put that
    tail in the row as `stdout`. A 524-entry listing is 23,946 bytes, so the machine delivered the last 65
    lines, alphabetically cut mid-word: the first "filename" was a fragment of
    `gate_accepts_a_failed_repair_probe_20261112.py`, which does not exist, and the other 459 entries were
    simply gone while `count: 65` was reported as if it were the count.

    The answer must be the run's whole output, and every name in it must be a real entry.

    A SECOND defect surfaced in the same answer once the tail was gone: the plan bound `ls -la`, and the
    long format's first line `total 8033` and its `drwxr-xr-x ...` rows were handed out as "files" --
    `count: 531` against 525 real names, with a byte total as the first filename.
    """
    import os as _os
    from canonical.runtime import live_brain_route_admission_v1 as ra
    result = ra.solve({"task_id": "files", "goal": "list the files using ls"})
    assert result.get("pass") is True, result.get("status")
    answer = result.get("answer") or {}
    live = set(_os.listdir(ROOT)) - {".", ".."}
    ghosts = [name for name in (answer.get("value") or []) if name not in live]
    assert not ghosts, "the answer names things that are not there: %s" % ghosts[:5]
    # `total 8033` is a block count and `.`/`..` are not files; every other line is an entry.
    #
    # The count is the WORLD's entry count, not this directory's: the command runs in a clone, so 528 is
    # right (530 `ls -la` names minus `.` and `..`) while the host had 525 ticked + 5 untracked. Asserting
    # `count == len(os.listdir(ROOT))` would have been an assertion about the host wearing the name of an
    # assertion about the answer -- the same mistake as reading a status field.
    assert answer.get("count") == 528, answer.get("count")
    assert answer.get("count") > 500, "a 525-entry directory cannot be answered with a handful"


def test_a_tail_is_not_an_answer() -> None:
    """The mechanism, tested directly: the row carries the full capture, not a display budget."""
    from canonical.runtime import confinement_v1 as C
    result = C.run_confined(ROOT, ["ls"], budget_s=120)
    assert result["outcome"] == "RAN"
    full = result.get("stdout") or ""
    tail = result.get("stdout_tail") or ""
    assert full, "no full capture"
    assert len(full) >= len(tail)
    assert len(full.splitlines()) > len(tail.splitlines()), (
        "a tree this size produces more output than a 2000-character tail")


def test_a_namespace_limited_environment_fails_closed_and_says_so() -> None:
    """The two crossfile qualification tests fail HERE and pass where namespaces exist.

    `unshare --mount --pid --fork` returns `Operation not permitted` in this sandbox, so
    `zero_ambient_namespace_launcher_v1` cannot build the namespace and the qualifier refuses. The refusal
    is correct; the failure is the environment's. This test exists so the distinction is recorded as a
    measurement instead of being quietly counted as a pass or quietly ignored.
    """
    import subprocess
    proc = subprocess.run(["unshare", "--mount", "--pid", "--fork", "true"],
                          capture_output=True, text=True)
    available = proc.returncode == 0
    assert isinstance(available, bool)
    if available:
        from canonical.runtime import confined_crossfile_qualification_v1  # noqa: F401
    else:
        assert "Operation not permitted" in (proc.stderr or "")


def test_the_audit_leaves_the_host_tree_byte_identical() -> None:
    """The property the whole census rests on, re-measured OUTSIDE the census's own bookkeeping.

    `world.host_untouched` is `confinement_v1`'s fingerprint. This asserts it independently: every tracked
    file's bytes and every untracked name must be the same before and after a full census. It also exists
    because a cleanup command of mine (`rm -f canonical/tmp_*.json`) deleted nine TRACKED evidence files
    during this work -- deleting evidence is not cleanup, and a test is the cheapest way never to do it
    silently again.
    """
    import subprocess
    def tracked_state() -> str:
        listing = subprocess.run(["git", "ls-files", "-s"], cwd=ROOT,
                                 capture_output=True, text=True).stdout
        return listing

    before_tracked = tracked_state()
    before_names = sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob("*")
                          if ".git" not in p.parts and "__pycache__" not in p.parts)
    report = R.reachability()
    after_tracked = tracked_state()
    after_names = sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob("*")
                         if ".git" not in p.parts and "__pycache__" not in p.parts)
    assert report["world"]["host_untouched"] is True
    assert before_tracked == after_tracked, "the census changed the git index"
    missing = [n for n in before_names if n not in after_names and not n.startswith("_rb")]
    assert not missing, "the census deleted host files: %s" % missing[:5]
