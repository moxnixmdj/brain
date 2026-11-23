"""THE MACHINE ANSWERS BY ASKING ITSELF, OR IT REFUSES. IT NEVER PREDICTS.

`machine_purpose_index_v1.derive_argv` turns a sentence that names a GOAL but no COMMAND into a
command this machine actually answers. The property under test is not accuracy -- it is that no
result can be wrong, because nothing is predicted:

  * WHAT TO ASK: `shutil.which` decides which word in the sentence is a program on THIS machine.
  * WHAT TO ASK IT: the sentence's own words pick a UNIVERSAL query (`--version`, `--help`) that
    every program answers the same way, plus the closed English idioms for asking for instructions
    ("how to use tar").
  * WHETHER THAT WORKED: the argv is RUN before it is returned. `ok` is true only because the
    program exited 0 and printed something here, now. Its first line comes back as `answer`.

The A71 version of this idea had `_flag_for` read an individual program's manual and match the
sentence's words against flag glosses. That was measured wrong three times in one round and every
failure was an invention that would have executed:

    "audit python source structure ..."      -> python -I   (gloss: "isolate ... environment")
    "check the python version and write ..." -> python -B   (gloss: "don't write .pyc files")
    "check the python version"               -> python -q   (gloss: "don't print version ...")

A gloss is one clause; a sentence is long; matching words between them finds coincidences. The
rewrite deleted the prediction entirely, which is why the tests below pin REFUSALS as hard as they
pin answers. A refusal is visible; an invention is not.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from canonical.runtime import machine_purpose_index_v1 as machine


# --------------------------------------------------------------------------------------------
# THE ANSWER IS THE PROGRAM'S, AND IT WAS OBTAINED BY RUNNING IT.
# --------------------------------------------------------------------------------------------
def test_a_version_question_is_answered_by_the_program_itself():
    derived = machine.derive_argv("Check the python version and write it to v.txt.")
    assert derived["ok"] is True, derived
    assert derived["argv"] == ["python", "--version"], derived["argv"]
    # The answer is the program's own output, not a stored fact about Python.
    assert derived["answer"].startswith("Python "), derived["answer"]
    assert derived["verified_by_running"] is True
    assert derived["stored_world_facts"] == 0
    assert derived["network_used"] is False


def test_a_second_program_answers_the_same_question_in_its_own_words():
    """The mechanism is `--version`, not knowledge about python. git answers differently."""
    derived = machine.derive_argv("check the git version")
    assert derived["ok"] is True, derived
    assert derived["argv"] == ["git", "--version"]
    assert "git version" in derived["answer"]


def test_a_question_about_how_to_use_something_is_a_help_request():
    """No word in "how to use tar" says "help"; the IDIOM does, and tar --help answers it."""
    derived = machine.derive_argv("show me how to use tar")
    assert derived["ok"] is True, derived
    assert derived["argv"] == ["tar", "--help"]
    assert "Usage" in derived["answer"] or "usage" in derived["answer"]


# --------------------------------------------------------------------------------------------
# WHAT IT CANNOT ANSWER IT REFUSES -- AND THE THREE INVENTIONS ARE GONE.
# --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("sentence,reason", [
    # Names a program, asks nothing a universal query answers. The old reader invented `python -I`
    # here by matching "source" against a gloss about isolating the environment.
    ("Audit python source structure and write the audit to a JSON file.",
     "NO_UNIVERSAL_QUERY_ANSWERS_THE_WORDS"),
    # Names no program at all.
    ("Fix it.", "NO_PROGRAM_NAMED_IN_THE_SENTENCE"),
    ("Run the thing.", "NO_PROGRAM_NAMED_IN_THE_SENTENCE"),
    ("count the words in README.md", "NO_PROGRAM_NAMED_IN_THE_SENTENCE"),
    # A real question, but not one `--version`/`--help` answers.
    ("how many files are in this folder", "NO_PROGRAM_NAMED_IN_THE_SENTENCE"),
])
def test_a_sentence_it_cannot_answer_is_refused_with_a_reason(sentence, reason):
    derived = machine.derive_argv(sentence)
    assert derived["ok"] is False, derived
    assert derived["reason"] == reason, derived
    assert "argv" not in derived


def test_the_three_measured_inventions_can_never_be_returned():
    """`-I`, `-B` and `-q` answered different questions. Nothing may derive a bare short flag."""
    for sentence in ("Audit python source structure and write the audit to a JSON file.",
                     "Check the python version and write it to v.txt.",
                     "check the python version"):
        derived = machine.derive_argv(sentence)
        if not derived.get("ok"):
            continue
        argv = derived["argv"]
        assert len(argv) == 2, argv
        assert argv[1] in ("--version", "--help"), argv


# --------------------------------------------------------------------------------------------
# THE PROGRAM MUST BE ON THIS MACHINE. NOTHING IS ASSUMED PRESENT.
# --------------------------------------------------------------------------------------------
def test_a_word_that_is_not_a_program_on_this_machine_is_not_a_program():
    derived = machine.derive_argv("check the version of definitelynotaprogram_zz9")
    assert derived["ok"] is False
    assert derived["reason"] == "NO_PROGRAM_NAMED_IN_THE_SENTENCE"


def test_the_authority_is_recorded_and_is_the_machine():
    derived = machine.derive_argv("check the python version")
    assert derived["authority"] == "THE_PROGRAM_ON_THIS_MACHINE_ANSWERED_WHEN_ASKED"
