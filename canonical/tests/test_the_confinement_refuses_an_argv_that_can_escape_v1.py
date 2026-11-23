"""A clone bounds relative work. It does not bound an absolute path.

The confinement's guarantee is that the capability runs in a disposable COPY of the host, so
everything it writes lands in the copy. That reasoning holds for a program that opens a relative
name -- `gzip -c input.txt > out.gz` writes `out.gz` inside the copy, whatever directory it is run
from. It does NOT hold for an argument that names an absolute path: `/tmp/x/proof.txt` resolves to
the same file inside the copy as outside it.

Measured before this was fixed:

    admit('/tmp/hole', ['bash', '-c', 'echo PWNED > /tmp/hole/proof.txt'])
    execute(...)  ->  exit 0, host_untouched: False, and /tmp/hole/proof.txt EXISTED ON THE HOST

The receipt reported the damage honestly, after it had been done. A receipt for harm already caused
is not a confinement.

The fix is a property, not a spelling: refuse any argument that can address a file outside the
worktree. A blocklist of dangerous words is the wrong shape -- ms-agent shipped six layers of regex
and was bypassed into a reverse shell (CVE-2026-2256), and its maintainers' fix was to remove the
shell tool entirely. So this does not ask whether a command looks dangerous; it asks whether an
argument can reach outside the copy.
"""
from __future__ import annotations

import pathlib

import pytest

from canonical.runtime import confinement_v1 as confinement


def test_a_shell_string_writing_an_absolute_path_is_refused(tmp_path):
    admitted = confinement.admit(str(tmp_path), ["bash", "-c", f"echo pwned > {tmp_path}/proof.txt"])
    assert isinstance(admitted, dict), "an escaping argv was admitted"
    assert admitted["refused"] == confinement.REFUSE_ARGV_ESCAPES_CONFINEMENT
    assert not (tmp_path / "proof.txt").exists(), "the host file was created"


def test_an_absolute_source_path_is_refused(tmp_path):
    admitted = confinement.admit(str(tmp_path), ["cp", "/etc/passwd", "copy"])
    assert isinstance(admitted, dict)
    assert admitted["refused"] == confinement.REFUSE_ARGV_ESCAPES_CONFINEMENT


@pytest.mark.parametrize("argv", [
    ["gzip", "-c", "input.txt"],
    ["sort", "input.txt"],
    ["cp", "AGENTS.md", "AGENTS_copy.md"],
    ["tar", "-cf", "out.tar", "input.txt"],
])
def test_well_formed_relative_work_is_still_admitted(tmp_path, argv):
    """The refusal must not cost the ordinary case, which is every real recipe."""
    (tmp_path / "input.txt").write_text("alpha\nbeta\n")
    (tmp_path / "AGENTS.md").write_text("# rules\n")
    admitted = confinement.admit(str(tmp_path), argv)
    assert not isinstance(admitted, dict), admitted


def test_dev_null_is_not_an_escape(tmp_path):
    """Every well-formed command uses /dev/null; it is a device, not a place to leave evidence."""
    (tmp_path / "input.txt").write_text("alpha\n")
    assert not confinement._names_absolute_path("/dev/null")


def test_the_ordinary_path_still_produces_a_verified_effect(tmp_path):
    """And the thing that made all this worth doing still works: a real file, verified."""
    (tmp_path / "input.txt").write_text("alpha\nbeta\ngamma\n")
    admitted = confinement.admit(str(tmp_path), ["gzip", "-c", "input.txt"],
                                 declared_effects=["out.gz"], stdout_to="out.gz")
    assert not isinstance(admitted, dict), admitted
    try:
        executed = confinement.execute(admitted)
        assert executed["exit_code"] == 0
        assert executed["declared_effects"]["out.gz"]["exists"] is True
        assert executed["declared_effects"]["out.gz"]["sha256"]
    finally:
        import shutil
        shutil.rmtree(str(admitted.worktree), ignore_errors=True)
