"""The carrier's verb set is the capability ceiling, and it must be TRUE.

Every round since r34 I have called the carrier "the real ceiling" without counting it.
This pins the count and the honesty of the table.

MEASURED 2026-11-09
-------------------
READ_ONLY_PROGRAMS holds 38 entries: 37 real verbs plus one inert sentinel
(`tee_never_admitted`, deliberately in the set so the table is auditable, refused because
it is also in _WRITER_PROGRAMS).

Of the 37, FOUR ARE NOT INSTALLED on this host: column, hexdump, look, xxd. Before this
test existed, `admission_verdict(["xxd","d.txt"])` returned `admitted: True` and the
execution then raised FileNotFoundError out of the carrier. An admission table that admits
a program the host cannot run is a promise the system cannot keep, and a skill learned on
top of it can never execute.

WHAT THIS DOES NOT CLAIM
------------------------
That 37 verbs is the right number. It is far too small to be a general computer user and it
is not presented as one. What it is: the exact, finite list that every learned skill must
live inside, which makes "nothing learned can exceed the carrier" a checkable statement
rather than a metaphor.
"""
from __future__ import annotations

import shutil

from canonical.runtime import admitted_confinement_execution_v1 as A


def _real_verbs() -> list[str]:
    return [p for p in A.READ_ONLY_PROGRAMS if "never" not in p]


def test_the_ceiling_has_a_finite_count():
    """If this number changes, every claim about the ceiling in the governance reports
    must be re-derived. Pinned so it cannot drift silently."""
    assert len(_real_verbs()) == 37, sorted(_real_verbs())


def test_the_inert_sentinel_is_present_and_never_runs():
    assert "tee_never_admitted" in A.READ_ONLY_PROGRAMS
    assert A.admission_verdict(["tee_never_admitted"]).get("admitted") is False


def test_an_admitted_verb_the_host_lacks_is_refused_by_name():
    """The defect: the table promised a verb the machine did not have."""
    missing = [p for p in _real_verbs() if shutil.which(p) is None]
    for prog in missing:
        verdict = A.admission_verdict([prog, "x.txt"])
        assert verdict.get("admitted") is False, f"{prog} was admitted but is not installed"
        assert verdict.get("reason") == "PROGRAM_NOT_INSTALLED:" + prog


def test_an_installed_admitted_verb_is_still_admitted():
    """The nearest world in which the new check must NOT refuse."""
    assert A.admission_verdict(["sort", "-u", "d.txt"]).get("admitted") is True


def test_everything_outside_the_table_is_refused():
    """The verbs that would make this a general computer user, all refused."""
    for argv in (["python3", "-c", "print(1)"], ["make"], ["pip", "install", "x"],
                 ["curl", "https://example.com"], ["git", "log"], ["jq", ".x", "f"]):
        assert A.admission_verdict(argv).get("admitted") is False, argv
