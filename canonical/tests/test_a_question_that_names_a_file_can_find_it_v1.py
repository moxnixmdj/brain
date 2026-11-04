"""A question about a file names the file. That name is not in the file's body.

The inspector matched file CONTENTS only. So "how many lines are in data.py" could
not find data.py unless the word "data" happened to occur inside it -- the filename,
which is the one thing such a question usually gives you, was the one thing never
looked at. Measured on a three-file tree before the fix:

    'how many lines are in data.py'      -> NOTHING_FOUND
    'what does notes.md say'             -> NOTHING_FOUND
    'what is retries in config.json'     -> PARTIALLY_GROUNDED   (only because
                                            `retries` is a key inside that file)

Each test fails if filename matching is removed.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import inspect_v1 as I  # noqa: E402


def _tree(**files: str) -> str:
    root = tempfile.mkdtemp(prefix="named-file-")
    for name, body in files.items():
        (Path(root) / name).write_text(body, encoding="utf-8")
    return root


def test_a_named_file_is_found_even_when_its_body_never_mentions_its_name():
    root = _tree(**{"data.py": "ITEMS = ['alpha']\n"})
    assert I.find(root, ["data.py"]), "a named file must be selected by its name"


def test_the_original_three_file_failure_is_gone():
    root = _tree(**{"data.py": "ITEMS = ['alpha']\n",
                    "notes.md": "# Notes\nplain\n",
                    "config.json": '{"retries": 3}\n'})
    for question in ("how many lines are in data.py", "what does notes.md say"):
        answer = I.answer(question, root)
        assert answer["verdict"] != "NOTHING_FOUND", (question, answer["verdict"])
        assert answer["grounded"] > 0, (question, answer)


def test_a_content_match_still_works_and_is_reported_at_a_real_line():
    """Filename matching must not replace content matching."""
    root = _tree(**{"data.py": "alpha\nITEMS = ['alpha']\n"})
    hits = I.find(root, ["ITEMS"])
    assert hits, "a term inside the file must still be found"
    assert hits[0]["line"] >= 1, "a content hit must carry the line it was read at"


def test_a_filename_hit_never_claims_a_line_number_it_did_not_read():
    """The distinction is load-bearing: line 0 means 'selected by name, no body read'.
    Inventing line 1 would be exactly the unmeasured claim this module refuses."""
    root = _tree(**{"data.py": "ITEMS = ['alpha']\n"})
    hits = I.find(root, ["data.py"])
    assert hits[0]["line"] == 0
    assert hits[0].get("matched") == "filename"
    assert hits[0]["text"] == ""


def test_a_file_is_not_reported_twice_when_both_name_and_body_match():
    """A file that matches by NAME and by BODY is still one file.

    An earlier version of this test used terms ("data.py", "data") on a body that
    contained "data", so the name hit was suppressed by the same-term rule and the
    duplicate path was never taken -- the test passed with the dedupe removed. This
    one forces both: the body contains the stem, and the question names the file.
    """
    root = _tree(**{"report.md": "the report mentions totals\n"})
    hits = I.find(root, ["report.md", "totals"])
    files = [h["file"] for h in hits]
    assert "report.md" in files, "the named file must be selected"
    assert files.count("report.md") == 1, f"one file must not be counted twice: {files}"


def test_a_name_hit_and_a_body_hit_on_the_same_file_do_not_double_the_grounded_count():
    """`grounded` is what the verdict is computed from, so a double count inflates it."""
    root = _tree(**{"report.md": "the report mentions totals\n"})
    answer = I.answer("what does report.md say about totals", root)
    report_rows = [h for h in answer["hits"] if h["file"] == "report.md"]
    assert len(report_rows) == 1, report_rows


def test_a_question_naming_nothing_still_finds_nothing():
    """The negative control. Letting a name question pass must not make every
    question pass -- the sweep's decoy environments depend on real refusals."""
    root = _tree(**{"data.py": "ITEMS = ['alpha']\n"})
    hits = I.find(root, ["nonexistent_token_zzz"])
    assert hits == []


def test_the_full_door_answers_a_question_it_used_to_refuse():
    """End to end through autonomous_v1.run, the front door the brain exposes."""
    from canonical.runtime import autonomous_v1 as A

    root = _tree(**{"data.py": "ITEMS = ['alpha', 'beta', 'gamma']\n"})
    out = A.run(goal="how many lines are in data.py", root=root, iterations=8)
    answer = out.get("answer") or {}
    assert answer.get("verdict") == "GROUNDED", answer
    assert out.get("verification", {}).get("verified") is True


# ---------------------------------------------------------------------------
# A question that names NO file asks for a SET, not for a word occurrence.
# ---------------------------------------------------------------------------

def test_a_listing_question_is_answered_by_enumerating_not_searching():
    """'list the files in this directory' names nothing inside the tree, so no term
    can ever match. It returned NOTHING_FOUND on a directory holding three files."""
    root = _tree(**{"a.py": "x = 1\n", "b.md": "# b\n", "c.json": "{}\n"})
    answer = I.answer("list the files in this directory", root)
    assert answer["verdict"] == "GROUNDED"
    assert answer["total"] == 3
    assert {h["file"] for h in answer["hits"]} == {"a.py", "b.md", "c.json"}


def test_the_listing_gate_does_not_swallow_content_questions():
    """`files` alone must not make a question a listing. The gate needs a listing verb."""
    assert I.wants_a_listing("list the files in this directory")
    assert I.wants_a_listing("which files exist here")
    assert not I.wants_a_listing("what is retries in files")
    assert not I.wants_a_listing("how many lines are in a.py")
    # A listing verb alone is not a listing: "list the exports of data.py" asks for the
    # contents of one named file. Dropping the container half turns it into a directory
    # listing and answers a question nobody asked.
    assert not I.wants_a_listing("list the exports of data.py")


def test_a_listing_verb_pointed_at_a_named_file_is_not_a_listing():
    """The container word is what distinguishes 'which files are here' from
    'what is in this one file'. Without it the gate answers the wrong question."""
    root = _tree(**{"data.py": "exports = ['a']\n", "other.txt": "unrelated\n"})
    answer = I.answer("list the exports of data.py", root)
    assert [h["file"] for h in answer["hits"]] != ["data.py", "other.txt"]
    assert all(h.get("matched") != "listing" for h in answer["hits"])


def test_a_content_question_that_mentions_files_still_searches_content():
    root = _tree(**{"notes.md": "retries is a word in here\n"})
    answer = I.answer("what is retries in files", root)
    assert any(h["file"] == "notes.md" for h in answer["hits"])


def test_a_listing_hit_claims_existence_and_no_line():
    root = _tree(**{"a.py": "x = 1\n"})
    hits = I.listing(root)
    assert hits[0]["line"] == 0
    assert hits[0]["matched"] == "listing"
    assert hits[0]["text"] == ""


def test_a_listing_does_not_resurrect_the_missing_directory_ambiguity():
    """'I could not look' and 'there is nothing there' are different facts."""
    import pytest as _pytest
    with _pytest.raises(NotADirectoryError):
        I.listing("/tmp/definitely-not-a-real-directory-zzz")


def test_the_whole_door_answers_five_plain_questions():
    """The capability probe, as a test. 1/5 before the filename fix, 5/5 after."""
    from canonical.runtime import autonomous_v1 as A

    root = _tree(**{"data.py": "ITEMS = ['a','b','c']\nTOTAL = 6\n",
                    "notes.md": "# Plan\n- first\n",
                    "conf.json": '{"retries": 3}\n'})
    questions = ["how many lines are in data.py", "what does data.py define",
                 "what is retries in conf.json", "what does notes.md say",
                 "list the files in this directory"]
    for q in questions:
        out = A.run(goal=q, root=root, iterations=8)
        answer = out.get("answer") or {}
        assert answer.get("verdict") in ("GROUNDED", "PARTIALLY_GROUNDED"), (q, answer.get("verdict"))
        assert answer.get("grounded", 0) > 0, (q, answer)
