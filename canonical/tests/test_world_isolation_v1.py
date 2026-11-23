"""A probe cannot be trusted to measure a mechanism that changes the world.

FIVE PROBES IN §A111 WERE INVALID and every one of them for the same reason: the mechanism under test changed
the world, and the probe then measured it again. One of those misreadings was expensive -- it produced the
belief that `repair_v1` could not classify `ModuleNotFoundError`, which was false, and chasing it cost more
probes, each of which changed the world again.

These tests check the three separate claims this module makes, and they check the one it explicitly does NOT
make: that a copied directory isolates the machine. It cannot, so the module records what changed instead of
denying it.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

import pytest

from canonical.runtime import world_isolation_v1 as W


def _world(files: dict[str, str]) -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp(prefix="iso_src_"))
    for name, body in files.items():
        (root / name).write_text(body)
    return root


def test_a_probe_that_edits_its_world_leaves_the_original_byte_identical() -> None:
    """The core promise: the copy absorbs the damage.

    Without this, round 2 of any repair loop measures a world round 1 already repaired -- which is precisely
    how five probes produced five wrong answers.
    """
    source = _world({"app.py": "import nope\nprint(totl)\n"})
    before = W.fingerprint(source)

    with W.isolated(source, label="edit") as record:
        copy = pathlib.Path(record["world"])
        assert (copy / "app.py").read_text() == "import nope\nprint(totl)\n"
        (copy / "app.py").write_text("print(6)\n")
        (copy / "extra.txt").write_text("written inside the copy")
        (copy / "app.py").chmod(0o600)

    assert W.fingerprint(source)["sha256"] == before["sha256"]
    assert not (source / "extra.txt").exists()
    verdict = W.report(record)["verdict"]
    assert verdict in ("THE_ORIGINAL_WORLD_AND_THE_MACHINE_ARE_BOTH_UNCHANGED",
                       "THE_WORLD_WAS_PROTECTED_BUT_THE_MACHINE_CHANGED"), verdict
    assert W.report(record)["source_unchanged"] is True


def test_a_world_that_is_edited_directly_is_reported_as_having_changed() -> None:
    """The negative case, and the reason `source_unchanged` exists.

    A result is only meaningful if the same check would have caught the failure. Here the probe edits the
    ORIGINAL rather than the copy, which is the mistake isolation is meant to prevent, and the record must say
    so instead of reporting success.
    """
    source = _world({"app.py": "print(1)\n"})
    with W.isolated(source, label="tamper") as record:
        (source / "app.py").write_text("print(2)\n")   # wrong world, deliberately

    reported = W.report(record)
    assert reported["source_unchanged"] is False
    assert reported["verdict"] == "THE_PROBE_CHANGED_THE_WORLD_IT_WAS_MEANT_TO_LEAVE_ALONE"


def test_an_install_is_detected_even_though_a_directory_copy_cannot_undo_it() -> None:
    """THE CLAIM THIS MODULE DOES NOT MAKE.

    A `pip install` is a machine-wide fact. A copied directory cannot restore it, so pretending to isolate the
    machine would be a false claim -- and a caller would build a conclusion on it. What the module does instead
    is enumerate the installed package set before and after, so an install of ANY package is visible,
    including one nobody thought to look for.

    That last part is the bug this test was written after: the first version probed a fixed list of module
    names, so a real install went unreported. A snapshot of the names I thought to check is a snapshot of my
    imagination, not of the machine.
    """
    source = _world({"app.py": "print(1)\n"})
    before = W.machine_state()
    assert before["package_count"] > 0, "the interpreter must have packages, or this test proves nothing"

    installed = False
    with W.isolated(source, label="install") as record:
        attempt = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                                  "tabulate"], capture_output=True, text=True, timeout=300)
        installed = attempt.returncode == 0
    reported = W.report(record)

    assert reported["source_unchanged"] is True, "installing must not touch the world"
    after = W.machine_state()
    if after["packages_sha256"] == before["packages_sha256"]:
        # nothing was installed, so there is no drift to detect and no honest claim to make either way
        assert reported["machine_changed"] is False
        return
    # a real change happened: it MUST be reported, and the verdict must not claim a clean machine
    assert reported["machine_changed"] is True, reported
    assert reported["verdict"] == "THE_WORLD_WAS_PROTECTED_BUT_THE_MACHINE_CHANGED"
    assert reported["machine_drift"]["packages_sha256_changed"] is True


def test_a_source_that_contains_the_workspace_is_refused() -> None:
    """§A101 filled the disk by copying a directory into a temp dir inside itself.

    Copying a world into a workspace that the world contains is not a slow probe, it is an unbounded one, and
    the guard must be a refusal rather than a hope that it terminates.
    """
    with pytest.raises(ValueError, match="THE_SOURCE_CONTAINS_THE_ISOLATION_WORKSPACE"):
        with W.isolated(tempfile.gettempdir(), label="self"):
            pass


def test_isolation_reports_what_it_did_not_isolate() -> None:
    """A caller deciding how much to trust a measurement needs the limits stated, not implied."""
    source = _world({"app.py": "print(1)\n"})
    with W.isolated(source, label="limits") as record:
        pass
    reported = W.report(record)
    assert reported["isolated"] == ["the_world_directory"]
    assert set(reported["not_isolated"]) == {
        "the_process_environment", "installed_packages", "anything_outside_the_world"}


def test_the_repair_loop_runs_inside_isolation_and_does_not_leak() -> None:
    """THE POINT OF THE HARNESS: the measurement that failed five times, now trustworthy.

    A world holding a misspelling is repaired by a loop that offers the failure to the environment repairer
    first and the code repairer second. The loop runs against a COPY, so the world it started from is still
    broken afterwards -- which is the only way round 2 can be a question about the same world round 1 saw.
    """
    from canonical.runtime import fix_from_the_failure_v1 as F
    from canonical.runtime import repair_v1 as R

    body = "total=0\nfor n in [1,2,3]:\n    total=total+n\nprint(totl)\n"
    source = _world({"app.py": body})
    before = W.fingerprint(source)

    with W.isolated(source, label="loop") as record:
        world = pathlib.Path(record["world"])
        run = subprocess.run([sys.executable, "app.py"], cwd=world, capture_output=True, text=True)
        assert run.returncode != 0
        output = (run.stdout or "") + (run.stderr or "")

        environment = R.attempt("%s app.py" % sys.executable, str(world), timeout=180, max_attempts=1)
        assert not environment.get("ok"), "a misspelling is not an environment fault"

        code = F.repair_from_failure(world / "app.py", output)
        assert code["repaired"] is True, code
        assert (code["bad"], code["good"]) == ("totl", "total")

        final = subprocess.run([sys.executable, "app.py"], cwd=world, capture_output=True, text=True)
        assert final.returncode == 0, final.stderr
        assert (final.stdout or "").strip() == "6"

    assert W.fingerprint(source)["sha256"] == before["sha256"], "the source world must be untouched"
    assert W.report(record)["source_unchanged"] is True
