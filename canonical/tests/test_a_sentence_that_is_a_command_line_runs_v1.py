"""A SENTENCE THAT IS A COMMAND LINE IS A REQUEST TO RUN IT.

The most ordinary thing a person can type at a computer is the command itself -- `ls -la`,
`df -h`, `git log`. Measured 2026-11-22, every one of those was unreachable: `extract_argv`
required the sentence to FRAME its command (the word "command", the word "argv", a quoting, or
English prose like "Copy the file a to b"), so a bare command line returned None and the request
died at GOAL_COMPILATION_BEST_MATCH_UNBINDABLE while `shell.command.run` sat verified with nothing
to bind.

THE DISTINCTION THAT MAKES THIS SAFE is not "does it start with a program name" -- `sort` and
`find` are programs, and "sort the lines of a file" and "find all files larger than one megabyte"
both start with one. A command line contains NO ENGLISH FUNCTION WORDS. A person writing prose
needs "the", "of", "all", "larger than"; a person writing a command line does not, because the
program's own flags carry the grammar.

BOTH HALVES ARE TESTED HERE, because a rule that read "sort the lines of a file" as a `sort`
command line would be an invention executed on a claim nobody made.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from canonical.runtime import composer_route_v1 as composer


# --------------------------------------------------------------------------------------------
# WHAT IS A COMMAND LINE.
# --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("sentence,argv", [
    ("ls -la", ["ls", "-la"]),
    ("ls", ["ls"]),
    ("df -h", ["df", "-h"]),
    ("git log", ["git", "log"]),
    ("python3 --version", ["python3", "--version"]),
    ("grep TODO src", ["grep", "TODO", "src"]),
    ("du -sh .", ["du", "-sh", "."]),
    ("du -sh src/.", ["du", "-sh", "src/."]),
])
def test_a_bare_command_line_is_read_as_one(sentence, argv):
    assert composer._is_a_bare_command_line(sentence) == argv


# --------------------------------------------------------------------------------------------
# AND WHAT IS NOT. THESE ARE THE CASES THAT WOULD MAKE THE RULE AN INVENTION.
# --------------------------------------------------------------------------------------------
@pytest.mark.parametrize("sentence", [
    # BOTH BEGIN WITH A REAL PROGRAM ON THIS MACHINE. Only the function words tell them apart.
    "sort the lines of a file",
    "find all files larger than one megabyte",
    "count the lines in README.md",
    "show me the last five git commits",
    # Names no program at all.
    "Fix it.",
    "Run the thing.",
    "what version of python is this",
    # A pipeline is a command this machine cannot honour: the adapter runs argv with no shell.
    "ls | head -5",
    "cat a > b",
])
def test_a_sentence_that_is_not_a_command_line_is_not_read_as_one(sentence):
    assert composer._is_a_bare_command_line(sentence) is None


def test_a_trailing_stop_is_removed_from_a_sentence_but_never_from_an_operand():
    """`.` is the current directory; stripping it turned "du -sh ." into "du -sh", which runs and
    answers about the wrong thing. Sentence punctuation is still removed."""
    assert composer._is_a_bare_command_line("ls -la.") == ["ls", "-la"]
    assert composer._is_a_bare_command_line("du -sh .") == ["du", "-sh", "."]
    assert composer._is_a_bare_command_line("du -sh ./") == ["du", "-sh", "./"]


def test_the_program_must_exist_on_this_machine():
    assert composer._is_a_bare_command_line("definitelynotaprogram_zz9 --help") is None


# --------------------------------------------------------------------------------------------
# THE END OF THE ROAD: IT RAN, IT WAS VERIFIED, AND THE ANSWER CAME BACK.
# --------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def listing():
    from canonical.runtime import live_brain_route_admission_v1 as ra
    return ra.solve({"task_id": "bare-ls", "goal": "ls -la"})


def test_a_bare_command_line_executes_and_verifies(listing):
    assert listing["pass"] is True, listing.get("status")
    assert "PASS__" in str(listing["status"])
    execution = listing["execution"]
    step = execution[0] if isinstance(execution, list) else execution
    assert step["capability_id"] == "shell.command.run"
    assert step["argv"] == ["ls", "-la"]
    assert step["confinement"]["exit_code"] == 0
    assert step["confinement"]["host_untouched"] is True
    assert step["confinement"]["receipt_sha256"]


def test_the_answer_is_what_the_command_printed(listing):
    """A pass with no output would be the machine doing the work and throwing it away."""
    execution = listing["execution"]
    step = execution[0] if isinstance(execution, list) else execution
    assert step.get("stdout", "").strip(), "ls -la passed and returned nothing"
    assert "shell.command.run" in str(step)


# --------------------------------------------------------------------------------------------
# A COMMAND THAT PROVES NOTHING IS STILL REFUSED. THE RECEIPT IS THE EVIDENCE.
# --------------------------------------------------------------------------------------------
def test_a_command_that_prints_nothing_is_not_a_verifiable_effect():
    """`true` exits 0 and does nothing. There is no receipt to read, so it is refused.

    This is the property the deleted `stdout_effect_argv` whitelist was guarding, kept without a
    list of pre-approved commands: the whitelist decided whether someone had ANTICIPATED the
    command, and this decides whether the run LEFT ANYTHING BEHIND.
    """
    from canonical.runtime import confined_dispatch_v1 as confined
    from canonical.runtime import live_integrated_brain_v1 as live
    entry = live.load_verified_registry()["shell.command.run"]
    routed = confined.run_confined_capability(
        "shell.command.run", entry, {"args": {"argv": ["true"]}}, host_root=str(ROOT))
    assert routed is None or routed.get("pass") is not True, routed
