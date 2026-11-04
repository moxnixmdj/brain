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
    assert answer.get("verdict") in ("COMPUTED", "READ", "GROUNDED"), answer
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
        # ANSWERED, not merely grounded. The earlier version of this test accepted
        # GROUNDED, and "how many lines are in data.py" passed it with no number in
        # the answer -- the test was asserting the weaker claim the bug relied on.
        assert answer.get("answered") is True, (q, answer.get("verdict"), answer.get("computation"))
        assert out["verification"]["verified"] is True, (q, out["verification"])


# ---------------------------------------------------------------------------
# A question that asks for a COUNT must come back with the count in it.
#
# The worst defect found in this module was not a miss. "how many lines are in
# data.py" returned verdict GROUNDED, verified=True, one hit -- the file, found by
# name -- and NO NUMBER. It never counted. The verdict vocabulary had one word for
# two different claims, so "the evidence is real" was read as "the question is
# answered", and nothing downstream could tell them apart.
# ---------------------------------------------------------------------------

def test_a_counting_question_returns_the_number_it_counted():
    root = _tree(**{"data.py": "a\nb\nc\nd\n"})
    answer = I.answer("how many lines are in data.py", root)
    assert answer["verdict"] == "COMPUTED"
    assert answer["computation"]["value"] == 4
    assert answer["answered"] is True


def test_a_count_is_recomputed_and_a_wrong_one_does_not_verify():
    """Nothing is taken on trust, including our own arithmetic."""
    root = _tree(**{"data.py": "a\nb\nc\nd\n"})
    lying = {"operation": "count_lines", "value": 99, "subject": "data.py", "claims": []}
    truthful = {"operation": "count_lines", "value": 4, "subject": "data.py", "claims": []}
    assert I._computation_holds(lying, root) is False
    assert I._computation_holds(truthful, root) is True


def test_csv_rows_do_not_silently_count_the_header():
    root = _tree(**{"sales.csv": "region,amount\nnorth,100\nsouth,250\neast,50\n"})
    answer = I.answer("how many rows are in sales.csv", root)
    assert answer["computation"]["value"] == 3
    assert "header" in answer["computation"]["detail"]


def test_asking_what_a_file_says_shows_what_it_says():
    """A name hit proves the file exists. It does not answer 'what does it say'."""
    root = _tree(**{"notes.md": "# Plan\n- first\n- second\n"})
    answer = I.answer("what does notes.md say", root)
    assert answer["verdict"] == "READ"
    assert answer["computation"]["body"] == ["# Plan", "- first", "- second"]


def test_a_fabricated_read_does_not_verify():
    root = _tree(**{"data.py": "a\nb\n"})
    fake = {"operation": "read_content", "subject": "data.py",
            "body": ["a", "b", "a line that is not in the file"], "claims": []}
    assert I._computation_holds(fake, root) is False


def test_the_door_does_not_report_a_counting_question_as_answered_without_a_count():
    """The exact shape of the original defect, asserted from the outside."""
    from canonical.runtime import autonomous_v1 as A

    root = _tree(**{"data.py": "a\nb\nc\nd\n"})
    out = A.run(goal="how many lines are in data.py", root=root)
    # The strong claim: the number reached the rendered output a person reads.
    assert "= 4" in out["rendered"], out["rendered"]
    assert out["verification"]["verified"] is True

    # And the honest-refusal half still holds: a question whose answer is genuinely
    # absent must not be reported as answered.
    miss = A.run(goal="what is the profit margin in data.py", root=root)
    assert miss["verification"]["verified"] is False
    # The file is there, so this is not "nothing found" -- it is "the file is there and
    # what you asked about is not in it". Those are different facts and the verdict
    # says which one this is.
    assert miss["answer"]["verdict"] == "PARTIALLY_GROUNDED"
    assert set(miss["answer"]["unresolved_terms"]) == {"profit", "margin"}


# ---------------------------------------------------------------------------
# Two defects that made the module report the opposite of the truth.
# ---------------------------------------------------------------------------

def test_a_file_matched_by_name_is_still_searched_for_content():
    """The body scan was skipped whenever the filename matched.

    "what is retries in conf.json" recorded the filename hit and then `continue`d past
    the file, so `retries` was reported as missing from a file containing it. The
    per-term dedup above that loop already prevented double counting; the skip guarded
    against a duplicate that could not happen and discarded every other term.
    """
    root = _tree(**{"conf.json": '{"retries": 3}\n'})
    answer = I.answer("what is retries in conf.json", root)
    assert answer["unresolved_terms"] == []
    assert any(h.get("term") == "retries" for h in answer["hits"])


def test_terms_that_matched_nothing_are_reported_not_dropped():
    """The pointer to a file is not an answer about what is inside it."""
    root = _tree(**{"data.py": "a\nb\n"})
    answer = I.answer("what is the profit margin in data.py", root)
    assert set(answer["unresolved_terms"]) == {"profit", "margin"}
    assert answer["answered"] is False


def test_the_grounder_loads_both_ways_or_the_module_refuses():
    """A silently absent verifier reports exactly like a working one.

    `import grounding_v1` only resolved when canonical/runtime was already on sys.path,
    which is true through autonomous_v1 and false for a package import. The failure
    path set G = None and turned every content hit UNVERIFIABLE while verdicts still
    read as confident. This asserts the result is identical from both entry points,
    which it can only be if the grounder actually loaded.
    """
    import pathlib, subprocess, sys as _sys, textwrap

    script = textwrap.dedent("""
        import sys, tempfile, pathlib
        sys.path.insert(0, {root!r})
        from canonical.runtime import inspect_v1 as I
        root = pathlib.Path(tempfile.mkdtemp())
        (root / 'conf.json').write_text('{{"retries": 3}}\\n')
        d = I.answer('what is retries in conf.json', str(root))
        assert d['grounding_summary'] is not None, 'grounder did not load'
        # One file, reported once, with real grounding behind it. Before the grounder
        # was resolved both ways this summary was None and the hit was UNVERIFIABLE.
        assert d['verdict'] == 'GROUNDED' and d['grounded'] == 1, d
        assert d['hits'][0]['verdict'] == 'GROUNDED', d
    """).format(root=str(pathlib.Path(__file__).resolve().parents[2]))

    proc = subprocess.run([_sys.executable, "-c", script], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr


def test_answer_actually_re_checks_the_computation_it_reports(monkeypatch):
    """A verifier nothing calls is not a verifier.

    The previous test proved `_computation_holds` can reject a wrong count. It did not
    prove `answer()` consults it -- and mutating the re-check to `verified = True` left
    every test green. So: make the computation LIE, and check that the answer catches
    it. Without the call site wired up, this returns a confident COMPUTED with 99.
    """
    root = _tree(**{"data.py": "a\nb\nc\nd\n"})

    def lying(question, path):
        return {"operation": "count_lines", "value": 99, "subject": "data.py",
                "detail": "9,999 line(s)", "claims": []}

    monkeypatch.setattr(I, "compute", lying)
    answer = I.answer("how many lines are in data.py", root)
    assert answer["computation"]["verified"] is False
    assert answer["verdict"] != "COMPUTED"
    assert answer["answered"] is False
