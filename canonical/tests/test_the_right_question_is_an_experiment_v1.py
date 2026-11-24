"""The defects this round produced, held so they cannot come back.

Every test below is a failure that actually happened, in the order it happened. None of them is
a test of a design intention; each one is a test of a bug that produced a wrong admission or a
wrong refusal, and each one would pass on the day it was written only by re-introducing the bug.

  1. **A wrapped clause was read as a sentence.** `sort`'s help wrapped `-V, --version-sort
     natural sort of (version) numbers within text` across two lines, and the tail became a claim
     that `sort` sorts. Joining physical lines into the statement the author wrote removed it.

  2. **A program that merely appears near a relation word became the subject of it.** `The locale
     affects sort order` named sort and said nothing about what sort does. Requiring the program
     before the verb removed it.

  3. **An option table was read as prose about the program.** `@optItem{cat,-b,}` followed by
     `Number all nonempty output lines` was admitted as `cat counts lines`. Dropping the table
     removed it.

  4. **A witness with no object is true of nothing.** `unexpand` and `tar` ran bare, touched no
     file, and a predicate over an unread object was vacuously satisfied.

  5. **A witness that is true of the program that does nothing is not a witness.** `wc counts the
     lines` was true of `cat` too: the file has that many lines whoever reads it. The null-program
     gate refuses it.

  6. **Two relations with the same witness are one relation counted twice.** `computes` and
     `prints` both meant "stdout is not empty", so one sentence stored two relations.

  7. **The room was degenerate.** A body of repeated identical lines is trivially sorted, so
     `sort sorts the lines` could never be true of it; the claim was refused as false.

  8. **The action was built with another program's grammar.** `unzip extracts an archive` ran
     `unzip --extract -f archive` -- tar's operands -- and came back FALSE about unzip.

  9. **A help page is a table, not a list of lines.** `unzip`'s two-column page produced `-x` for
     "extract files into exdir" and `-Z` for "list".

 10. **A decompressor was handed a stream it does not speak.** `bzip2 decompresses` was given the
     gzip file the room always made, and refused for a reason about the room.

 11. **A binary stream was written as text.** `gzip -c` output was decoded and re-encoded, and
     `gzip -t` then said "not in gzip format" about a file gzip had just made.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
TOOLS = REPO / "canonical" / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import the_right_question_is_an_experiment_v1 as subject  # noqa: E402


# --------------------------------------------------------------------------- #
# 1. reading
# --------------------------------------------------------------------------- #

def test_a_wrapped_clause_is_one_statement_not_two_claims():
    """`sort`'s option row wrapped; its tail became a claim that sort sorts."""
    text = ("  -V, --version-sort  natural sort of (version) numbers within text\n"
            "  -r, --reverse       reverse the result of comparisons\n")
    claims = subject.extract_claims(text, programs=["sort"], subject="sort")
    assert claims == [], claims


def test_a_program_that_is_not_the_subject_of_the_verb_is_not_a_claim():
    """"sort order" is a noun phrase; the only program name in it is not a subject."""
    text = "The locale specified by the environment affects sort order.  Set LC_ALL=C."
    claims = subject.extract_claims(text, programs=["sort"], subject="sort")
    assert claims == [], claims


def test_the_document_owner_is_the_subject_of_its_imperatives():
    """`Compress or uncompress FILEs` is a claim about gzip, and gzip is named only above it."""
    claims = subject.extract_claims("Compress or uncompress FILEs (by default, in-place).",
                                    programs=["gzip"], subject="gzip")
    assert {c["relation"] for c in claims} >= {"compresses", "decompresses"}


def test_an_option_table_is_not_a_statement_about_the_program():
    """The whole point of the texinfo reader: a flag table is a catalogue, not prose."""
    texi = ("@node cat invocation\n"
            "@command{cat} copies each file to standard output.\n"
            "@table @samp\n"
            "@optItem{cat,-b,}\n"
            "@optItemx{cat,--number-nonblank,}\n"
            "Number all nonempty output lines, starting with 1.\n"
            "@end table\n")
    prose = subject.texinfo_prose(texi)["cat invocation"]
    assert "Number all nonempty" not in prose
    claims = subject.extract_claims(prose, programs=["cat"], subject="cat")
    assert all(c["relation"] != "counts" for c in claims), claims


# --------------------------------------------------------------------------- #
# 2. the vocabulary
# --------------------------------------------------------------------------- #

def test_no_two_relations_share_a_witness():
    """A name whose experiment is another name's experiment is a synonym, not a relation."""
    seen: dict[tuple[str, str], str] = {}
    for name, spec in subject.RELATIONS.items():
        key = (spec["observable"], spec["predicate"])
        assert key not in seen, f"{name} duplicates {seen.get(key)}"
        seen[key] = name


def test_the_relation_words_are_verb_forms():
    """"sort" is a noun in "sort order"; only a verb states a relation."""
    assert subject._is_verb_form("sort order", (0, 4), 5) is False
    assert subject._is_verb_form("sorts the lines", (0, 5), 0) is True
    assert subject._is_verb_form("gzip sorts the lines", (5, 10), 0) is True


# --------------------------------------------------------------------------- #
# 3. the witness
# --------------------------------------------------------------------------- #

def _claim(program: str, relation: str, kind: str, sentence: str) -> dict:
    return {"schema": subject.SCHEMA, "sentence": sentence, "line": 1, "program": program,
            "relation": relation, "observable": subject.RELATIONS[relation]["observable"],
            "object_kind": kind, "predicate": subject.RELATIONS[relation]["predicate"],
            "authority": "NONE"}


def _evaluate(program: str, relation: str, kind: str, sentence: str):
    return subject.evaluate_claim(_claim(program, relation, kind, sentence),
                                  actions=[program], programs=[program],
                                  help_text=subject._help_text(program))


def test_a_room_that_is_already_sorted_cannot_witness_sorting():
    """The body is unsorted by construction; if it ever becomes sorted, `sort sorts` is false."""
    body = subject._write_text(pathlib.Path("/tmp/never-written.txt"), 0)
    lines = body.splitlines()
    assert lines != sorted(lines), "the text object is sorted; the sorts witness cannot be true"


def test_a_witness_that_ignores_the_object_is_refused():
    """`tar` run bare touches nothing; a predicate over nothing is not a verdict."""
    result = _evaluate("tar", "runs", "file", "tar runs a file.")
    assert result.verdict == "REFUSED"
    assert result.reason == "WITNESS_IGNORES_THE_OBJECT"


def test_the_null_program_is_measured_on_the_same_object(tmp_path):
    """The gate exists because a predicate can be true of nothing.

    `_run_witness(..., null_program=...)` runs the program that does nothing to the object and
    returns the same readings. A discriminating predicate is FALSE there; a vacuous one is TRUE
    there, and that is exactly the case the gate refuses.
    """
    claim = _claim("tar", "checks", "archive", "tar checks an archive.")
    room = _evaluate("tar", "checks", "archive", "tar checks an archive.")
    assert room.verdict == "ADMIT"
    readings = subject._run_witness(claim, tmp_path, variant=0, null_program="true")["readings"]
    assert subject._predicate("distinguishes_valid_from_corrupt", readings) is False
    assert subject._predicate("content_equal", readings) is True, (
        "a vacuous predicate must be true of the null run, or the gate has nothing to refuse")


def test_a_predicate_that_is_true_of_nothing_is_refused(tmp_path):
    """The gate, end to end: a claim whose witness the null program also satisfies."""
    claim = _claim("cp", "copies", "directory", "cp copies a directory.")
    result = subject.evaluate_claim(claim, actions=["cp"], programs=["cp"],
                                    help_text=subject._help_text("cp"))
    assert result.verdict == "REFUSED"
    assert result.reason in ("WITNESS_IS_TRUE_OF_A_NULL_PROGRAM", "CLAIM_IS_FALSE")


def test_a_counting_claim_about_what_the_program_reports_is_admitted():
    """The same relation, about the program's own report rather than about the object."""
    result = _evaluate("wc", "counts", "text", "wc reports the number of lines of a file.")
    assert result.verdict == "ADMIT", (result.reason, result.readings)


@pytest.mark.parametrize("program,relation,kind,sentence", [
    ("sort", "sorts", "text", "sort sorts the lines of a text file."),
    ("gzip", "compresses", "file", "gzip compresses a file."),
    ("gzip", "decompresses", "compressed", "gzip decompresses a compressed file."),
    ("bzip2", "compresses", "file", "bzip2 compresses a file."),
    ("bzip2", "decompresses", "compressed", "bzip2 decompresses a compressed file."),
    ("xz", "compresses", "file", "xz compresses a file."),
    ("tar", "archives", "archive", "tar creates an archive."),
    ("tar", "lists", "archive", "tar lists an archive."),
    ("tar", "extracts", "archive", "tar extracts an archive."),
    ("zip", "archives", "zip", "zip archives a zip."),
    ("unzip", "extracts", "zip", "unzip extracts a zip archive."),
    ("unzip", "lists", "zip", "unzip lists a zip archive."),
    ("cp", "copies", "file", "cp copies a file."),
    ("mv", "renames", "file", "mv renames a file."),
    ("diff", "compares", "file", "diff compares two files."),
    ("patch", "applies", "patch", "patch applies a patch."),
    ("cat", "prints", "file", "cat prints a file."),
    ("grep", "searches", "file", "grep searches a file for a pattern."),
])
def test_the_core_operations_admit(program, relation, kind, sentence):
    """One claim per operation the fleet actually has, each built from its own help page.

    These are the doors the round is for: if any of them stops admitting, the vocabulary has
    lost an operation, and a vocabulary that cannot name `tar extracts` is not a vocabulary.
    """
    result = _evaluate(program, relation, kind, sentence)
    assert result.verdict == "ADMIT", (result.reason, result.readings)


@pytest.mark.parametrize("program,relation,kind,sentence", [
    ("sort", "reverses", "text", "sort reverses the lines."),
    ("gzip", "grows", "file", "gzip grows the size of a file."),
    ("cat", "sorts", "text", "cat sorts the lines of a file."),
    ("cp", "sorts", "file", "cp sorts a file."),
])
def test_a_false_prose_claim_is_refused_not_admitted(program, relation, kind, sentence):
    """The other half of the gate: prose that is wrong must come back wrong."""
    result = _evaluate(program, relation, kind, sentence)
    assert result.verdict != "ADMIT", (result.reason, result.readings)


def test_an_admitted_relation_survives_a_third_room():
    """A relation that only holds in the room it was verified in is about the room."""
    result = _evaluate("tar", "extracts", "archive", "tar extracts an archive.")
    assert result.verdict == "ADMIT"
    assert result.relation is not None
    claim = dict(result.relation)
    claim.update(schema=subject.SCHEMA, line=1, authority="NONE")
    import tempfile
    third = pathlib.Path(tempfile.mkdtemp(prefix="third-room-"))
    again = subject.evaluate_claim(claim, actions=["tar"], programs=["tar"], root=third)
    assert again.verdict == "ADMIT", (again.reason, again.readings)


# --------------------------------------------------------------------------- #
# 4. the store
# --------------------------------------------------------------------------- #

def test_the_relation_stores_no_prose_and_no_room(tmp_path):
    """What is saved is the relation; the sentence is a digest and a pointer, never the knowledge."""
    result = _evaluate("tar", "extracts", "archive", "tar extracts an archive.")
    relation = dict(result.relation)
    memory = subject.remember(subject.load_memory(str(tmp_path / "m.json")), relation)
    saved = memory["relations"][-1]
    assert saved["source"]["sentence"] == "tar extracts an archive."
    assert "room" not in json.dumps(saved)
    assert saved["witness"]["argv"][0] == "tar"
    assert saved["object_kind"] == "archive"


def test_a_stored_relation_plans_and_a_memory_without_one_refuses(tmp_path):
    result = _evaluate("tar", "extracts", "archive", "tar extracts an archive.")
    plan = subject.plan_from_relations([result.relation], ["tar"])
    assert plan["status"] == "PASS__PLAN_FROM_A_VERIFIED_CLAIM"
    assert plan["plan"] == ["tar --extract {object}"]
    empty = subject.plan_from_relations([], ["tar"])
    assert empty["status"] == "REFUSED__NO_ADMITTED_RELATION"


# --------------------------------------------------------------------------- #
# 5. the census is three corpora, not one number
# --------------------------------------------------------------------------- #

def test_the_corpora_are_reported_separately():
    """A `--help` page, a docstring and a manual are not interchangeable kinds of text."""
    report = subject.measure(budget=120, corpus="all")
    assert set(report["corpora"]) <= {"help", "stdlib", "prose"}
    for name, row in report["corpora"].items():
        assert row["sentences"] > 0, name
        assert row["admitted"] <= row["unique_claims"] <= row["claims"], name
        assert row["prose_yield"] == pytest.approx(
            row["admitted"] / row["sentences"], abs=1e-6), name
    assert report["cost"] == {"model_calls": 0, "parameters": 0,
                              "network_at_run_time": 0, "spend_usd": 0}


def test_the_prose_yield_is_small_and_not_zero():
    """The measurement this round exists to make, held so it cannot drift into a flattering form."""
    report = subject.measure(budget=120, corpus="all")
    if not report["prose_corpus_present"]:
        pytest.skip("the prose corpus is machine-local; fetch it with --fetch-prose")
    prose = report["corpora"]["prose"]
    assert 0 < prose["admitted"]
    assert prose["prose_yield"] < 0.05, prose


import json  # noqa: E402  (used by the store test above)


# --------------------------------------------------------------------------- #
# 6. the circuit this round was supposed to close
# --------------------------------------------------------------------------- #

class _Room:
    """The smallest environment `run()` accepts: a world with no plan in it."""

    kind = "grid_world"

    def __init__(self) -> None:
        self.p = (0, 0)

    def reset(self) -> None:
        self.p = (0, 0)

    def state(self):
        return self.p

    def act(self, action) -> None:
        self.p = (0, 0)

    def snapshot(self):
        return self.p

    def restore(self, state) -> None:
        self.p = state

    def is_goal(self, obs) -> bool:
        return False


def _run_with(readme: str, actions=("echo",)):
    from canonical.swe_kernel import perfect_algorithm_v1 as pa
    room = pathlib.Path(tempfile.mkdtemp(prefix="circuit-room-"))
    (room / "README.md").write_text(readme, encoding="utf-8")
    return pa.run(_Room(), "greet the user", list(actions),
                  goal_predicate=lambda obs: False, heuristic=lambda obs: 1,
                  goal_family="shell", env_kind="grid_world",
                  memory_path_=room / "memory.json", local_root=room,
                  budget=1, max_depth=1, seed=0)


def test_the_local_guide_returns_the_document_not_only_a_snippet():
    """The fetcher used to return a paragraph; the extractor needs the document."""
    from canonical.runtime import local_guide_v1 as local_guide
    room = pathlib.Path(tempfile.mkdtemp(prefix="guide-room-"))
    (room / "README.md").write_text(
        "# Guide\n\nTo greet the user, echo hello back to them.\n\n"
        "```console\n$ echo hello\nhello\n```\n", encoding="utf-8")
    found = local_guide.lookup("how to use grid world: greet the user", root=room)
    assert found["pass"] is True, found
    assert found["documents"][0]["text"].startswith("# Guide")


def test_a_paragraph_that_answers_in_its_specific_words_is_found():
    """The old gate asked for 60% of the query; this paragraph has 2 of 4 and is the answer."""
    from canonical.runtime import local_guide_v1 as local_guide
    room = pathlib.Path(tempfile.mkdtemp(prefix="guide-room-"))
    (room / "README.md").write_text(
        "# Guide\n\nTo greet the user, echo hello back to them.\n", encoding="utf-8")
    found = local_guide.lookup("how to use grid world: greet the user", root=room)
    assert found["pass"] is True, found


def test_run_hands_the_fetched_document_to_the_extractor():
    """THE DEFECT: `run()` read a key nothing set, so a replayable README still ended OPEN."""
    out = _run_with("# Guide\n\nTo greet the user, echo hello back to them.\n\n"
                    "```console\n$ echo hello\nhello\n```\n")
    instant = out["steps"]["instant_knowledge"]
    assert instant["status"] == "PASS__LOCAL_GUIDE_FOUND"
    assert instant["documents_with_text"] == 1
    assert instant["documents_returned"] == 1
    assert out["status"] == "PASS__PLAN_FROM_A_DOCUMENT"
    assert out["plan"] == ["echo hello"]


def test_a_shell_transcript_is_a_test_suite_too():
    """The pycon reader refused every shell guide at the first gate."""
    out = _run_with("# Guide\n\nTo greet the user, printf hi.\n\n"
                    "```bash\n$ printf hi\nhi\n```\n", actions=("printf",))
    assert out["status"] == "PASS__PLAN_FROM_A_DOCUMENT"
    assert out["plan"] == ["printf hi"]


def test_a_shell_command_outside_the_action_space_is_seen_not_planned():
    """A guide says what EXISTS on a machine, not what this call may DO."""
    out = _run_with("# Guide\n\nTo greet the user, remove the directory.\n\n"
                    "```bash\n$ rm -rf x\n```\n", actions=("echo",))
    assert out["status"] != "PASS__PLAN_FROM_A_DOCUMENT"
    assert out["steps"]["document_as_test_suite"]["status"] == (
        "REFUSED__COMMAND_SEEN_NOT_PERMITTED")


import tempfile  # noqa: E402
