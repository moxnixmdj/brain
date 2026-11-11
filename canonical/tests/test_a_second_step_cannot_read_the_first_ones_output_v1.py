"""The composition ceiling, measured 2026-11-09.

THE FINDING
-----------
r41 measured 23/33 single-step read verbs passing. The obvious next question is
"then chain two of them and you can do anything." You cannot, and the failure was
SILENT -- the worst kind.

Every cli_exec step is launched INDEPENDENTLY through the carrier
(`execute_compiled_steps`, L960-L1040). No step receives the previous step's stdout,
and `cli_pipeline` is refused at the boundary (L962). So a two-step skill
    ['sort','-u',f]  then  ['wc','-l',f]
does not count the unique lines. `wc` re-reads the whole file.

Worse, `stdout_line_count` took the LAST receipt's stdout and counted its lines, so
the answer to "count the unique lines" was the number of lines `wc` itself printed:
**1**. It returned 1 where the truth was 3, and it QUALIFIED -- held-out, sabotage
control and all -- because the postcondition could not tell the difference.

FIXED IN THIS ROUND: a multi-step sequence now fails closed with
POSTCONDITION_STDOUT_LINE_COUNT_UNDEFINED_FOR_MULTI_STEP rather than reporting a
number that describes the procedure instead of the file.

WHY THIS IS THE ANSWER TO "ONE DEMONSTRATION => ANYTHING ON A COMPUTER"
-----------------------------------------------------------------------
Composition is the multiplier the thesis needs. 23 verbs, single-step, in parallel,
means 23 capabilities. 23 verbs that can be sequenced means thousands. The ceiling
is therefore not 23 -- it is 23 and not one more, because the chain does not exist.
"""
from __future__ import annotations

import pathlib
import tempfile

import pytest

from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as K

FIXTURE = "zebra\napple\nzebra\nmango\napple\n"


def _db(tmp: pathlib.Path) -> str:
    return str(tmp / "skills.sqlite")


def _stage(tmp: pathlib.Path, name: str):
    p = tmp / name
    p.write_text(FIXTURE, encoding="utf-8")
    return p


def test_a_two_step_skill_fails_closed_instead_of_answering_wrongly():
    """The regression this test exists for: a two-step count once returned 1 for 3."""
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        t = _stage(tmp, "t.txt")
        h = _stage(tmp, "h.txt")
        s = _stage(tmp, "s.txt")
        r = K.compile_and_qualify_skill(
            goal=f"count the unique lines of {t}",
            trace=[{"kind": "cli_exec", "layer": "cli_exec", "argv": ["sort", "-u", str(t)]},
                   {"kind": "cli_exec", "layer": "cli_exec", "argv": ["wc", "-l", str(t)]}],
            postcondition={"kind": "stdout_line_count"},
            heldout_goal=f"count the unique lines of {h}",
            heldout_cwd=tmp,
            sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                     "contains": "__nope__"},
            db_path=_db(tmp),
        )
        assert not r.get("pass"), (
            "a multi-step stdout_line_count must not qualify: no step receives the "
            "previous step's stdout, so the count describes the last program's own output"
        )


def test_the_single_step_case_still_works():
    """The fix must not disable the one shape that is sound."""
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        t = _stage(tmp, "t.txt")
        h = _stage(tmp, "h.txt")
        s = _stage(tmp, "s.txt")
        r = K.compile_and_qualify_skill(
            goal=f"unique lines of {t}",
            trace=[{"kind": "cli_exec", "layer": "cli_exec", "argv": ["sort", "-u", str(t)]}],
            postcondition={"kind": "stdout_line_count"},
            heldout_goal=f"unique lines of {h}",
            heldout_cwd=tmp,
            sabotaged_postcondition={"kind": "file_contains", "path": str(s),
                                     "contains": "__nope__"},
            db_path=_db(tmp),
        )
        assert r.get("pass"), r.get("status")


def test_a_pipeline_layer_is_refused_at_the_boundary():
    """`cli_pipeline` is in the layer table but refused, so a genuine shell pipe can never
    be taught. This is the structural reason two skills cannot compose."""
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        t = _stage(tmp, "t.txt")
        r = K.compile_and_qualify_skill(
            goal=f"count unique lines of {t}",
            trace=[{"kind": "cli_pipeline", "layer": "cli_pipeline",
                    "stages": [["sort", "-u", str(t)], ["wc", "-l"]]}],
            postcondition={"kind": "stdout_line_count"},
            heldout_goal=f"count unique lines of {t}",
            heldout_cwd=tmp,
            sabotaged_postcondition={"kind": "file_contains", "path": str(t),
                                     "contains": "__nope__"},
            db_path=_db(tmp),
        )
        assert not r.get("pass")
