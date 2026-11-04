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
