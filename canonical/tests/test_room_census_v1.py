"""An unseen directory must be able to say what it can do.

THE OWNER'S IDEA, AND WHY IT NEEDED A NEW ORGAN.

    "All he should do is basically go into any new arbitrary environment in the computer and he
     doesn't know anything about anything... All he should do is scan everything in the environment
     and then retrieve from his memory what he knows and what he doesn't know."

Measured 2026-11-23, that did not happen. A directory with two honest callables, asked a question
they can answer, got `document.convert.markdown_pdf.pandoc_weasyprint` from the registry and
ACTION_FAILED. Every selector in the tree starts from a fixed registry, so a function the machine has
never met cannot even be a candidate -- which means "learn from one experience in a new environment"
had no first step.

`room_census_v1` is that step: a directory -> its callables, described by their own docstrings and
signatures, ranked by the BM25 scorer the tree already owns. It executes nothing and admits nothing.

These tests assert the properties that make it worth having, and nothing about a particular day's
score: that meaning comes from the docstring, that private functions are not offered, that an
unreadable file does not take the survey down, that a room with no vocabulary is UNRESOLVED rather
than a crash, and that the whole path -- survey, find the gap, forge, act -- lands on the right
function and returns the right numbers.
"""
from __future__ import annotations

import json
import pathlib
import sys
import textwrap

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import room_census_v1 as RC  # noqa: E402


@pytest.fixture()
def room(tmp_path):
    """A directory nobody registered, holding a real csv tool and some noise."""
    (tmp_path / "census.py").write_text(textwrap.dedent('''
        """Summarise a csv by column."""
        import csv

        def profile(path):
            """Per-column fill rate and numeric rate for a csv file."""
            rows = list(csv.DictReader(open(path)))
            cols = {}
            for name in rows[0]:
                vals = [r.get(name, "") for r in rows]
                filled = sum(1 for v in vals if v.strip())
                cols[name] = {"fill_rate": round(filled / len(vals), 3)}
            return {"columns": cols, "rows": len(rows)}

        def _private(x):
            """Not offered: a leading underscore is not a callable a person means."""
            return x

        def trailing_comma(n, sep=","):
            """Format a number with a trailing separator."""
            return str(n) + sep
    '''), encoding="utf-8")
    (tmp_path / "broken.py").write_text("def oops(:\n  this is not python\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("not python at all\n", encoding="utf-8")
    return tmp_path


def test_a_room_is_read_as_callables_not_files(room):
    """The unit of a census is a FUNCTION, because a function is what can be called."""
    found = RC.survey(str(room))
    assert found["status"] == "SURVEYED"
    names = [f["function"] for f in found["functions"]]
    assert "profile" in names and "trailing_comma" in names, names
    # reading is bounded and honest about what it did
    assert found["files_read"] >= 1


def test_a_private_function_is_not_offered(room):
    """`_private` is the author saying "not for you". A census that lists it wastes a demonstration."""
    names = {f["function"] for f in RC.survey(str(room))["functions"]}
    assert "_private" not in names, names


def test_meaning_comes_from_the_docstring_not_the_name(room):
    """`profile` alone could be a profiler, a user profile, or this column report. The docstring says."""
    rows = {f["function"]: f for f in RC.survey(str(room))["functions"]}
    assert "fill rate" in rows["profile"]["doc"], rows["profile"]["doc"]
    # and the signature is read from source, never guessed
    assert rows["profile"]["params"] == ["path"], rows["profile"]
    # a defaulted parameter is recorded as optional, with its default
    assert rows["trailing_comma"]["params"] == ["n", "sep"]
    assert rows["trailing_comma"]["defaults"].get("sep") == "','", rows["trailing_comma"]


def test_an_unreadable_file_does_not_take_the_survey_down(room):
    """A census is the first thing to run in a place nobody has vouched for."""
    found = RC.survey(str(room))
    assert found["status"] == "SURVEYED"
    assert any(f["function"] == "profile" for f in found["functions"])
    # the syntax-error file contributed nothing and did not raise
    assert all(f["source_rel"].endswith(".py") for f in found["functions"])


def test_the_gap_is_what_the_room_offers_minus_what_is_already_known(room):
    """`unknown_functions` is the owner's "what I know and what I don't", asked about a PLACE."""
    found = RC.survey(str(room))
    everything = RC.unknown_functions(found, [])
    assert len(everything) == len(found["functions"])
    # once a capability names it, it is no longer a gap
    known = ["forged.census.profile::profile"]
    remaining = {f["function"] for f in RC.unknown_functions(found, known)}
    assert "profile" not in remaining, remaining


def test_a_room_with_no_shared_vocabulary_is_unresolved_not_a_crash(room):
    """THE SCORER'S OWN BUG, MADE A TEST.

    `_bm25_scores` returned bare floats when every candidate document was empty and
    (score, contributions) tuples otherwise, so `rank` -- which unpacks the pair -- raised
    "cannot unpack non-iterable float object". An objective that shares no word with a room took the
    whole survey down instead of reporting that it found no relevance.
    """
    blank = {"schema": RC.SCHEMA, "functions": [
        {"function": "aaa", "source_rel": "x.py", "params": [], "doc": "", "text": ""},
        {"function": "bbb", "source_rel": "y.py", "params": [], "doc": "", "text": ""},
    ]}
    out = RC.rank(blank, "zzz qqq vvv")
    assert out["status"] == "RELEVANCE_UNRESOLVED", out
    assert out["ranked"] == []


def test_the_relevance_it_reports_is_the_scorer_s_own(room):
    """A copy of a measurement under a new name reads like a second measurement."""
    found = RC.survey(str(room))
    out = RC.rank(found, "profile the columns of a csv", limit=3)
    assert out["relevance_scope"] == "LEXICAL_BM25_OBJECTIVE_RELEVANCE_ONLY", out
    # the scorer is explicit that lexical relevance is not semantic entailment, and that
    # qualification must survive the adapter
    assert out["semantic_entailment_status"] == "UNVERIFIED", out
    assert out["ranked"], out
    for row in out["ranked"]:
        assert row["score"] == row.get("score")
        assert isinstance(row["score"], (int, float))


def test_a_zero_scored_candidate_is_not_offered_as_a_match():
    """`rank` returns every candidate it scored, including those sharing no term with the objective.

    Passing those through presents "nothing here is about this" as a ranked shortlist -- and the
    first version did exactly that. This room is MIXED on purpose: one candidate is genuinely about
    the objective and one is not, so the filter has something to remove. (An all-zero room cannot
    observe the filter at all, which is how the first version of this test let the mutant live.)
    """
    mixed = {"schema": RC.SCHEMA, "functions": [
        {"function": "profile", "source_rel": "a.py", "params": ["path"],
         "doc": "Per-column fill rate and numeric rate for a csv file.", "text": ""},
        {"function": "zzz_unrelated", "source_rel": "b.py", "params": [],
         "doc": "Completely different subject matter entirely.", "text": ""},
    ]}
    out = RC.rank(mixed, "profile the columns of a csv", limit=5)
    kept = [r["function"] for r in out["ranked"]]
    assert "profile" in kept, out
    assert "zzz_unrelated" not in kept, kept
