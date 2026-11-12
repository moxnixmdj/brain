"""One environment's failures may not delete another environment's knowledge.

Pins the round-5 finding. `macro_v1.signature` is deliberately invariant to
everything except the verbs and the file kinds — that is the whole design, and
it is right. The consequence, measured on this module before the repair:

    machine A has the binaries, proves the job once      -> successes = 1
    machine B, same platform, lacks the binary           -> lookup returns A's plan
    B calls note_failure twice                           -> the macro is gone
    A looks it up                                        -> None, and A was right

So the coarse unit of memory that macro_v1's own docstring names as its
recurring bug ("a goal-relative file kind became a permanent ban, a
precondition became one, eight audits of one bad directory disabled auditing
everywhere") had one more level left in it: THE ENVIRONMENT.

The repair does not narrow the key again — that is the move that produced every
previous sighting. It lets a caller who knows where it ran say so, and counts
evidence per environment. Nothing is generalised by assumption, and an
unaddressed call behaves exactly as it always did.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from canonical.runtime import macro_v1 as MC

JOB = ["extract the text from report.pdf", "verify the docx output.docx"]
STEPS = [{"capability_id": "pdf.extract.text.pypdf", "verified": True},
         {"capability_id": "docx.document.verify.ooxml", "verified": True}]


@pytest.fixture()
def store(tmp_path, monkeypatch):
    p = tmp_path / "macros.json"
    monkeypatch.setattr(MC, "STATE", p)
    monkeypatch.setattr(MC, "_state_path", lambda: p)
    return p


# --------------------------------------------------------------------------------------------
# The defect
# --------------------------------------------------------------------------------------------
def test_the_key_is_invisible_to_the_environment(store):
    """The premise, not a complaint: the signature carries no environment."""
    same_root_a = ["extract the text from /home/a/report.pdf",
                   "verify the docx /home/a/output.docx"]
    same_root_b = ["extract the text from /srv/b/report.pdf",
                   "verify the docx /srv/b/output.docx"]
    assert MC.signature(same_root_a) == MC.signature(same_root_b)


def test_one_environments_failures_used_to_destroy_anothers_plan(store):
    """The measured failure, asserted as the reason the parameter exists.

    With no address given, behaviour is unchanged: two failures outweigh one
    success and the macro is dropped. That is correct WITHIN an environment and
    was wrong ACROSS one.
    """
    MC.record(JOB, STEPS)
    key = MC.signature(JOB)
    MC.note_failure(key)
    assert MC.lookup(JOB) is not None            # one failure is not a verdict
    MC.note_failure(key)
    assert MC.lookup(JOB) is None                # two outweigh one


# --------------------------------------------------------------------------------------------
# The repair
# --------------------------------------------------------------------------------------------
def test_a_failure_observed_elsewhere_does_not_delete_the_plan(store):
    MC.record(JOB, STEPS, where="a.example")
    key = MC.signature(JOB)
    for _ in range(5):
        MC.note_failure(key, where="b.example")
    assert MC.lookup(JOB) is not None, "B destroyed A's plan"
    entry = MC._load()["macros"][key]
    assert entry["proved_where"] == "a.example"
    assert entry["failures_by_environment"] == {"b.example": 5}
    # The evidence is not discarded, it is ADDRESSED. It is still counted.
    assert entry["failures"] == 5


def test_a_failure_at_the_same_address_still_refutes(store):
    """The repair must not make a plan immortal where it demonstrably fails."""
    MC.record(JOB, STEPS, where="a.example")
    key = MC.signature(JOB)
    MC.note_failure(key, where="a.example")
    MC.note_failure(key, where="a.example")
    assert MC.lookup(JOB) is None


def test_an_unaddressed_record_cannot_be_defended(store):
    """Unknown provenance is fail-safe: the old behaviour, not a shield."""
    MC.record(JOB, STEPS)                        # no `where` -> unaddressed
    key = MC.signature(JOB)
    MC.note_failure(key, where="b.example")
    MC.note_failure(key, where="b.example")
    assert MC.lookup(JOB) is None


def test_environment_names_are_normalised(store):
    MC.record(JOB, STEPS, where="A.Example")
    key = MC.signature(JOB)
    for _ in range(3):
        MC.note_failure(key, where="  a.EXAMPLE  ")
    assert MC.lookup(JOB) is None, "case/whitespace made the same box look like two"


def test_successes_are_never_counted_across_environments(store):
    """A success on B must not silently promote a plan proved on A."""
    MC.record(JOB, STEPS, where="a.example")
    key = MC.signature(JOB)
    MC.record(JOB, STEPS, where="b.example")
    entry = MC._load()["macros"][key]
    assert entry["proved_where"] == "a.example", "the proving environment silently moved"
    assert entry["successes"] == 2
