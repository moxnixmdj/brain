"""THE DIRECTORY SURVEY: an adapter that was declared for weeks and never written.

`file.directory_listing.v1` was named in four runtime modules, and `live_brain_route_admission_v1`
cited it as the settled authority for a rule. Measured 2026-11-22 (A80): it was never in the
registry, because the adapter it declares raised `BOUND_CAPABILITY_ADAPTER_MISSING` -- the verifying
check could not pass, and nobody noticed, because nothing ran it.

These tests hold the adapter to the contract that verification function actually re-reads. They are
deliberately independent of it: the checks below recompute the listing from the filesystem rather than
calling the same verifying code, so a change that broke both together would still be caught here.

WHAT IS NOT CLAIMED, and is recorded here so it cannot be mistaken for done: the adapter is VERIFIED
but not yet REACHABLE. It is not in the bound registry, so no sentence routes to it -- "list the files
in this folder" still compiles to a source-code enumerator. Wiring it in needs a registry row whose
keywords are the words people use ("list the files", "what is in this folder"), and the
receipt-projection lane derives those from the module FILENAME, which would give "survey". That is
the next piece of work, and it is deliberately not faked here.
"""

import os
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.bound_capabilities import file_survey


@pytest.fixture()
def world(tmp_path):
    """A root with a named directory whose contents are known, built here, not inherited.

    The contents live in `listing/` because the adapter refuses to list its root itself -- a
    listing of everything is not an answer to a question about a folder, and that is tested below.
    """
    (tmp_path / "listing").mkdir()
    (tmp_path / "listing" / "a.txt").write_text("x", encoding="utf-8")
    (tmp_path / "listing" / "b.txt").write_text("yy", encoding="utf-8")
    (tmp_path / "listing" / "sub").mkdir()
    return tmp_path


def _run(path, root):
    return file_survey.run({"path": path, "command": "directory_list"}, root)


# --------------------------------------------------------------------------------------------
# It lists what is really there.
# --------------------------------------------------------------------------------------------
def test_it_names_every_entry_the_caller_created(world):
    out = _run("listing", world)
    assert sorted(out["names"]) == sorted(os.listdir(world / "listing"))


def test_it_lists_a_directory_it_is_pointed_at(world):
    (world / "other").mkdir(exist_ok=True)
    (world / "other" / "one.txt").write_text("1", encoding="utf-8")
    (world / "other" / "inner").mkdir(exist_ok=True)
    out = _run("other", world)
    assert sorted(out["names"]) == ["inner", "one.txt"]
    assert out["entry_count"] == 2


def test_it_distinguishes_directories_from_files(world):
    """The difference between "list the files" and "what is in here" is this flag."""
    out = _run("listing", world)
    dirs = sorted(entry["name"] for entry in out["entries"] if entry["is_dir"])
    files = sorted(entry["name"] for entry in out["entries"] if entry["is_file"])
    assert dirs == ["sub"]
    assert files == ["a.txt", "b.txt"]
    assert out["directory_count"] == 1
    assert out["file_count"] == 2


def test_files_and_names_agree_and_the_answer_is_the_listing(world):
    out = _run("listing", world)
    assert out["files"] == out["names"]
    assert out["answer"] == "\n".join(out["names"])


def test_the_answer_shape_gate_can_project_onto_files(world):
    """The gate looks for a field named `files`; the row declares it."""
    from canonical.runtime import answer_shape_v1 as shape
    out = _run("listing", world)
    hit = shape._project(out, shape.asked("list the files in this folder"))
    assert hit is not None and hit[0] == "files"


# --------------------------------------------------------------------------------------------
# It refuses rather than answering about the wrong thing.
# --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("path", ["/etc", "..", "../..", "/etc/passwd"])
def test_it_never_reads_outside_the_root_it_was_given(world, path):
    with pytest.raises(ValueError, match="PATH_OUTSIDE_ROOT"):
        _run(path, world)


def test_it_refuses_a_file_where_a_directory_is_required(world):
    with pytest.raises(ValueError, match="PATH_NOT_DIRECTORY"):
        _run("a.txt", world)


def test_the_root_is_refused_unless_it_was_named(world):
    """A81 refused the root outright. That was drawn in the wrong place, and this is the correction.

    The danger is SILENTLY defaulting to the root -- answering about a folder nobody named. The
    sentence "list the files in this folder" is not that: it points at the working folder, which IS
    the root, and refusing it made the plainest question about a directory unanswerable by the
    capability built for it. An explicit "." is the caller naming the root; an empty path is not.
    """
    # Named: answered.
    assert _run(".", world)["entry_count"] >= 0
    # Not named: refused.
    with pytest.raises(ValueError, match="PATH_REQUIRED"):
        _run("", world)


def test_a_deictic_phrase_is_answered_by_the_listing_row(world):
    """"this folder" names the place the request is served from -- a fact, not a guess."""
    out = _run(".", world)
    assert sorted(out["names"]) == sorted(os.listdir(world))


def test_it_refuses_a_command_it_does_not_implement(world):
    """A row wired to the wrong operation fails loudly instead of listing something and believing it."""
    with pytest.raises(ValueError, match="COMMAND_NOT_SUPPORTED"):
        file_survey.run({"path": ".", "command": "copy"}, world)


def test_a_missing_path_is_refused_not_reported_as_empty(world):
    """An empty folder and a folder that does not exist are different facts."""
    with pytest.raises((ValueError, OSError)):
        _run("not_here", world)


# --------------------------------------------------------------------------------------------
# The declared verification really runs and passes.
# --------------------------------------------------------------------------------------------
def test_the_declared_verification_check_passes():
    """This is the check that could not run before the adapter existed.

    It raised `BOUND_CAPABILITY_ADAPTER_MISSING` on 2026-11-22, which is how the missing adapter was
    found: a verification function that cannot get far enough to report a failure looks exactly like
    one that has not been run.
    """
    from canonical.runtime import verify_file_facts_provenance_v1 as verify
    pathlib.Path(verify.WORLD).mkdir(parents=True, exist_ok=True)
    ok, checks = verify._check_directory_listing()
    assert ok is True
    assert checks and all(check.get("ok") is True for check in checks)
    # The evidence is in the checks, not in the boolean: a check that silently skipped would pass
    # `ok` while proving nothing, so the names are asserted too.
    names = " ".join(str(check.get("name") or "") for check in checks)
    assert "names every entry" in names
    assert "distinguishes the directory" in names


# --------------------------------------------------------------------------------------------
# THE FRONTIER SENTENCE, ANSWERED.
#
# "list the files in this folder" names no program and no path. Three separate readers had to learn
# something before it could be routed, and each one is tested here because each was a real block:
#   * a BARE DIRECTORY NAME ("canonical") was not a path -- the reader wanted a "/";
#   * a DEICTIC PHRASE ("this folder", "here") names the root, which is a known fact, not a string;
#   * the row declared the DIRECTORY slot as `path`, which the machine reserves for FILES.
# --------------------------------------------------------------------------------------------
def test_a_bare_directory_name_is_read_as_a_path():
    from canonical.runtime import goal_compiler as compiler
    assert [c[0] for c in compiler._repo_paths("list the files in canonical", ROOT)] == ["canonical"]
    # ...and only when it really is a directory here: a word is not promoted to a path by hope.
    assert compiler._repo_paths("list the files in qqqnotafolder", ROOT) == []


@pytest.mark.parametrize("sentence", [
    "list the files in this folder",
    "show me the files here",
    "list the files in the current directory",
])
def test_a_deictic_phrase_names_the_root(sentence):
    """The reference is to the place the request is served from -- a fact this machine holds."""
    from canonical.runtime import goal_compiler as compiler
    assert [c[0] for c in compiler._repo_paths(sentence, ROOT)] == ["."]


def test_a_named_folder_is_not_read_as_deictic():
    from canonical.runtime import goal_compiler as compiler
    assert [c[0] for c in compiler._repo_paths("list the files in canonical", ROOT)] == ["canonical"]


def test_the_row_declares_the_DIRECTORY_slot_not_the_file_slot():
    """`path` is the machine's FILE slot; a directory declared as `path` can never bind."""
    from canonical.runtime import goal_front_compiler_v1 as compiler
    from canonical.runtime import live_integrated_brain_v1 as brain
    entry = brain.load_verified_registry()["file.directory_listing.v1"]
    keys = compiler.input_keys(entry)
    assert "source_root" in keys
    assert "path" not in keys
    # No whole-request slot: an input that takes the entire sentence is the catch-all shape, and it
    # would let this row "bind" any sentence at all, hiding whether the sentence was about a folder.
    assert "goal" not in keys


@pytest.mark.parametrize("sentence", [
    "list the files in this folder",
    "show me the files here",
    "list the files in the current directory",
])
def test_the_plainest_sentence_is_answered_with_the_real_listing(sentence):
    """End to end: prose in, the actual contents of the working folder out, and it is true.

    The expected answer is read from the filesystem AT TEST TIME rather than written down. A literal
    count here would be a fact about this checkout, and it would start failing the moment the
    repository gained a file -- a test that breaks on an unrelated change teaches nothing.
    """
    from canonical.runtime import live_brain_route_admission_v1 as door
    result = door.solve({"task_id": "deictic", "goal": sentence})
    assert result.get("pass") is True, result.get("status")
    answer = result.get("answer") or {}
    assert answer.get("noun") == "file"
    live = sorted(os.listdir(ROOT))
    # `count` is the true number of entries; `value` is deliberately BOUNDED to 50 and flagged
    # `truncated: true`, so the delivered page is asserted against the first 50 real entries.
    assert answer.get("count") == len(live)
    assert sorted(answer["value"]) == live[:50]
    assert answer.get("truncated") is (len(live) > 50)


@pytest.mark.parametrize("folder", ["canonical", "canonical/runtime/bound_capabilities"])
def test_a_named_directory_is_answered_with_its_own_contents(folder):
    """A single-segment folder name and a nested path both resolve to the same listing rule."""
    from canonical.runtime import live_brain_route_admission_v1 as door
    result = door.solve({"task_id": "named", "goal": "list the files in " + folder})
    assert result.get("pass") is True, result.get("status")
    answer = result.get("answer") or {}
    live = sorted(os.listdir(ROOT / folder))
    assert answer.get("count") == len(live)
    assert sorted(answer["value"]) == live[:50]


def test_a_folder_name_another_capability_owns_is_not_stolen():
    """`tests` is the test auditor's word, and honesty about scope beats coverage of a phrase.

    "list the files in tests" scores 11 for `python.tests.audit.unittest` and 4 for the listing row,
    so the auditor wins. It then cannot deliver a file listing, and the sentence fails. That is a
    RANKING outcome this row must not paper over by adding "tests" to its keywords -- a listing row
    that claims every folder name would take sentences from the rows that understand them.
    """
    from canonical.runtime import goal_front_compiler_v1 as compiler
    from canonical.runtime import live_integrated_brain_v1 as brain
    registry = brain.load_verified_registry()
    goal = "list the files in tests"
    listing, _t, _e = compiler.score_capability(goal, "file.directory_listing.v1",
                                                registry["file.directory_listing.v1"])
    auditor, _t2, _e2 = compiler.score_capability(goal, "python.tests.audit.unittest",
                                                  registry["python.tests.audit.unittest"])
    assert auditor > listing
