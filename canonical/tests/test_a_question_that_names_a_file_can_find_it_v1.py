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

import pathlib
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
        path = Path(root) / name
        # A nested name is a real path; the directory above it may not exist yet.
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
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
    # The file is there, so this is not "nothing found anywhere" -- it is "I looked in
    # the file you named and the words are not in it". Those are different facts, and
    # the verdict says which one happened rather than collapsing both.
    assert miss["answer"]["verdict"] == "NOT_IN_NAMED_FILE"
    assert set(miss["answer"]["unresolved_terms"]) == {"profit", "margin"}
    assert miss["verification"]["reason"] == "SUBJECT_ABSENT_FROM_NAMED_FILE"


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


# ---------------------------------------------------------------------------
# Found by pointing the door at THIS REPOSITORY, not at a fixture tree.
#
# A three-file fixture cannot show either defect. The first needs a tree big enough
# for the hit cap to fill before the named file is reached; the second needs a .git.
# ---------------------------------------------------------------------------

def _mini_repo(root):
    """A tree where a common word fills the hit cap before the named file is reached."""
    pathlib.Path(root, "canonical", "runtime").mkdir(parents=True)
    target = pathlib.Path(root, "canonical", "runtime", "mod.py")
    target.write_text("a = 1\nretries = 3\nc = 4\n")
    # Enough noise that a tree-wide search for `canonical`/`runtime` saturates first.
    for i in range(60):
        d = pathlib.Path(root, f"canonical/sibling_{i:02d}")
        d.mkdir()
        (d / "x.md").write_text("canonical runtime is mentioned here\n")
    return root


def test_a_path_is_one_name_not_a_pile_of_search_terms():
    """`canonical/runtime/mod.py` was split into three search terms.

    The fragments matched thousands of files in the real repository, the 40-hit cap
    filled with unrelated ones, and the file that actually contains the word was never
    opened -- so `retries` was reported absent from a file containing it.
    """
    root = _tree(**{"canonical/runtime/mod.py": "a = 1\nretries = 3\nc = 4\n"})
    answer = I.answer("what is retries in canonical/runtime/mod.py", root)
    assert answer["unresolved_terms"] == [], answer["unresolved_terms"]
    assert any(h["file"] == "canonical/runtime/mod.py" for h in answer["hits"])
    assert answer["answered"] is True


def test_the_named_file_is_searched_even_when_the_tree_is_loud():
    """The regression itself: a big tree must not hide the file the question named."""
    root = _mini_repo(tempfile.mkdtemp(prefix="loud-"))
    assert len(I.find(root, ["canonical"], limit=5)) == 5      # the noise is real
    answer = I.answer("what is retries in canonical/runtime/mod.py", root)
    assert answer["unresolved_terms"] == [], (answer["verdict"], answer["unresolved_terms"])
    assert answer["answered"] is True


def test_path_fragments_are_not_subject_terms():
    """`canonical` and `runtime` address the file; they are not things to look for.

    Only words the QUESTION contains are dropped, and only a final segment is matched by
    its whole name. A substring rule ("retry" appears in "retry.py") also drops, and it
    dropped `retry` from "what is retry in retry.py" on a file that never contains the
    word -- a false pass.
    """
    q = "what is hello in a/b/c.py"
    # Directory segments address the file; the final segment keeps the ".py" the
    # asker typed, so `c` on its own is not dropped.
    assert I._drop_path_fragments(["hello", "a", "b", "c.py"], "a/b/c.py", q) == ["hello", "c.py"]
    # A FILE called retry.py must not make `retry` disappear from a question asking
    # about it: the path containing a word is not the file containing it.
    assert I._drop_path_fragments(["retry", "retry.py"], "retry.py",
                                  "what is retry in retry.py") == ["retry", "retry.py"]
    root = _tree(**{"a/b/c.py": "hello\n"})
    answer = I.answer(q, root)
    assert answer["unresolved_terms"] == [], answer["unresolved_terms"]


def test_a_word_absent_from_the_named_file_is_not_satisfied_by_the_filename():
    """`retry` in `retry.py`: the path contains the word, the FILE does not.

    `find` matches terms against the path as well as the body, so a tree-wide fallback
    produced a name hit carrying `retry` as its term, and the question came back
    GROUNDED and answered. A question that names a file is about that file.
    """
    root = _tree(**{"retry.py": "nothing relevant here\n"})
    answer = I.answer("what is retry in retry.py", root)
    assert answer["answered"] is False
    assert answer["verdict"] != "GROUNDED"


def test_a_named_file_is_still_cited_when_the_answer_is_a_computation():
    """A count over a file has to say which file it counted."""
    root = _tree(**{"data.py": "a\nb\nc\n"})
    answer = I.answer("how many lines are in data.py", root)
    assert answer["verdict"] == "COMPUTED"
    assert answer["computation"]["value"] == 3
    assert answer["grounded"] > 0, answer["hits"]
    assert any(h["file"] == "data.py" for h in answer["hits"])


def test_counting_files_does_not_count_the_object_store():
    """`.git` is 220 files of object store and is not part of the project.

    The first version answered 20823 on a tree holding 20603 -- wrong in the one way a
    count must not be wrong. The detail string now states what was skipped, so the
    number reconciles against a plain `find` instead of silently differing from it.
    """
    root = tempfile.mkdtemp(prefix="cnt-")
    for i in range(3):
        pathlib.Path(root, f"f{i}.txt").write_text("x\n")
    git = pathlib.Path(root, ".git", "objects", "ab")
    git.mkdir(parents=True)
    for i in range(7):
        (git / f"obj{i}").write_text("y")

    answer = I.answer("how many files are in this directory", root)
    assert answer["computation"]["value"] == 3, answer["computation"]
    assert "skipped 7" in answer["computation"]["detail"], answer["computation"]["detail"]
    assert answer["unresolved_terms"] == [], answer["unresolved_terms"]


def test_the_count_is_rechecked_with_the_same_exclusion_it_reported():
    """Re-check must use one definition of 'the project's files', not two."""
    root = tempfile.mkdtemp(prefix="cnt2-")
    pathlib.Path(root, "a.txt").write_text("x")
    pathlib.Path(root, ".git").mkdir()
    pathlib.Path(root, ".git", "HEAD").write_text("ref")
    comp = {"operation": "count_files", "value": 1, "subject": "<the directory>", "claims": []}
    assert I._computation_holds(comp, root) is True
    wrong = dict(comp, value=2)
    assert I._computation_holds(wrong, root) is False


# ---------------------------------------------------------------------------
# Mutations that survived the first pass, pinned.
#
# Both of these were rules the code followed and the tests never checked. A mutation
# that restores the old behaviour and leaves every test green means the tests were
# exercising the code, not specifying it.
# ---------------------------------------------------------------------------

def test_a_filename_hit_does_not_resolve_the_word_it_is_spelled_with():
    """A name hit says the file is there; it must not say the word was found.

    With name hits counted as matches, `retry` in `retry.py` reads as resolved while
    the file never contains it. Asserted at the tally as well as the verdict, because
    the tally is what the verdict is computed from.
    """
    root = _tree(**{"retry.py": "nothing relevant here\n"})
    answer = I.answer("what is retry in retry.py", root)
    assert answer["answered"] is False
    assert answer["unresolved_terms"] == ["retry"], answer["unresolved_terms"]
    assert answer["verdict"] == "NOT_IN_NAMED_FILE"


def test_the_path_drop_cannot_take_a_word_the_question_is_about():
    """The substring rule dropped `retry` for `retry.py`. Exact basename does not.

    `mod.py` IS resolved by the named `canonical/runtime/mod.py` -- the asker typed the
    filename. `retry` is NOT resolved by `retry.py`, because asking about the word is
    asking about what is inside the file.
    """
    assert I._drop_path_fragments(["retry", "retry.py"], "retry.py",
                                  "what is retry in retry.py") == ["retry", "retry.py"]
    # basename equality resolves the filename term, and only that term
    root = _tree(**{"canonical/runtime/mod.py": "retries = 3\n"})
    got = I.answer("what is retries in canonical/runtime/mod.py", root)
    assert got["unresolved_terms"] == [], got["unresolved_terms"]

    # ...while a word the file does not contain stays unresolved even though the
    # filename contains it as a substring
    missing = I.answer("what is retry in retry.py", _tree(**{"retry.py": "x\n"}))
    assert missing["unresolved_terms"] == ["retry"], missing["unresolved_terms"]


def test_a_name_hit_beside_a_body_hit_does_not_cover_the_body_term():
    """The reachable form of the name-hit-as-match bug.

    One file matches by name for `notes`, another by body for `budget`. The name hit
    carries `notes` as its term; if name hits count as matches, `notes` reads as found
    even when nothing in any file discusses it -- the file is merely called that.
    """
    root = _tree(**{"notes.md": "unrelated content\n", "plan.txt": "the budget is 300\n"})
    answer = I.answer("what is the budget in notes", root)
    # `budget` is genuinely found; `notes` is only a filename fragment.
    assert "budget" not in answer["unresolved_terms"], answer["unresolved_terms"]
    assert answer["answered"] is False, answer["unresolved_terms"]
    named_hits = [h for h in answer["hits"]
                  if h.get("matched") in ("filename", "listing") and h.get("term") == "notes"]
    assert named_hits, "the fixture must produce a name hit carrying `notes`"


# ---------------------------------------------------------------------------
# A refusal must never be a confident claim about a file that was never opened.
# ---------------------------------------------------------------------------

def test_a_csv_is_text_and_can_be_searched():
    """`.csv` was not in the extension list, so the door skipped every CSV.

    It would answer "how many rows are in sales.csv" while refusing "what is amount in
    sales.csv" with NOT_IN_NAMED_FILE -- asserting a word absent from a file it never
    read. That is the worst shape of wrong: the refusal names a place it did not look.
    """
    root = _tree(**{"sales.csv": "region,amount\nnorth,100\nsouth,250\n"})
    answer = I.answer("what is amount in sales.csv", root)
    assert answer["verdict"] == "GROUNDED", answer["verdict"]
    assert answer["unresolved_terms"] == []
    assert answer["answered"] is True


def test_text_ness_is_decided_from_the_bytes_not_a_list():
    """The extension is a hint; the bytes are the fact."""
    root = _tree(**{"Makefile": "all:\n\techo build\n",  # no extension at all
                    "notes.rst": "# heading\n"})
    assert I._is_readable_text(Path(root) / "Makefile") is True
    assert I._is_readable_text(Path(root) / "notes.rst") is True

    binary = Path(root) / "blob.dat"
    binary.write_bytes(b"\x00\x01\x02binary")
    assert I._is_readable_text(binary) is False


def test_a_file_with_no_extension_can_be_named_and_read():
    """`Makefile` has no dot, so `_FILE_MENTION` never saw it and it fell through to a
    tree-wide search that reported the filename as an unresolved word."""
    root = _tree(**{"Makefile": "all:\n\techo build\n"})
    assert I._named_file("what does Makefile say", root) == "Makefile"
    answer = I.answer("what does Makefile say", root)
    assert answer["verdict"] == "READ", answer["verdict"]
    assert answer["unresolved_terms"] == []


def test_the_word_pass_does_not_invent_filenames():
    """Only a word that IS a file here becomes the named file."""
    root = _tree(**{"data.py": "x = 1\n"})
    assert I._named_file("what is the profit in data.py", root) == "data.py"
    assert I._named_file("what is the profit", root) is None


def test_a_word_absent_from_a_readable_csv_is_reported_as_absent():
    """The flip side: now that it CAN be searched, an absent word is a real refusal."""
    root = _tree(**{"sales.csv": "region,amount\nnorth,100\n"})
    answer = I.answer("what is zzz_absent in sales.csv", root)
    assert answer["verdict"] == "NOT_IN_NAMED_FILE"
    assert answer["unresolved_terms"] == ["zzz_absent"]
