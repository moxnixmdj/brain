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


def test_it_refuses_the_root_itself(world):
    """A listing of everything is not an answer to a question about a folder."""
    with pytest.raises(ValueError, match="REFUSES_THE_REPOSITORY_ROOT"):
        _run(".", world)


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
