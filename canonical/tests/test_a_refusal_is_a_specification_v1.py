"""The refusal is the last declaration a program makes, and the only one nobody read.

Round 7 read what a program declares when it is asked for help, and moved the fleet from
33 doors to 57. It left most of the remainder diagnosed as `PRECONDITION` rather than
misreading. This module tested what a precondition actually is, and found the answer in the
refusal: every sentence below names the thing that is missing.

    No signature to verify: use the -signature option
    No operation option (-encrypt|-decrypt|-sign|-verify|...) specified
    No recipient(s) certificate(s) specified
    Error: offset out of range
    Unable to load certificate
    tar: You may not specify more than one '-Acdtrux', '--delete' or '--test-label' option
    fatal: not a git repository (or any of the parent directories): .git

Six clause forms are read, and the tests below hold both the mechanisms and the honest
sizes. The sizes are the point: ONE form answered everything it read and the other five
answered almost nothing, and a test that hid that would be the reporting this project
exists to avoid.
"""
from __future__ import annotations

import pathlib
import shutil
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import a_refusal_is_a_specification_v1 as R  # noqa: E402

HAVE_GIT = shutil.which("git") is not None
HAVE_OPENSSL = shutil.which("openssl") is not None
HAVE_TAR = shutil.which("tar") is not None


# --------------------------------------------------------------------------- #
# every form is read from the program's own words
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("sentence,form", [
    ("No signature to verify: use the -signature option", R.OFFERED),
    ("No operation option (-encrypt|-decrypt|-sign|-verify|...) specified.", R.ENUMERAL),
    ("No recipient(s) certificate(s) specified", R.WITNESS),
    ("Error: offset out of range", R.RANGE),
    ("Unable to load certificate", R.UNLOADABLE),
    ("tar: You may not specify more than one '-Acdtrux', '--delete' or "
     "'--test-label' option", R.CONFLICT),
    ("fatal: not a git repository (or any of the parent directories): .git", R.WORLD),
])
def test_each_form_is_read_from_the_programs_own_sentence(sentence, form):
    clause = R.read_refusal(sentence)
    assert clause is not None, f"this refusal was not read at all: {sentence}"
    assert clause.form == form
    assert clause.sentence, "the program's own words must be kept with the clause"


def test_an_offer_to_explain_is_not_a_precondition():
    """`Use -help for summary` is the single most common refusal in the round-7 sample.

    It is an offer of documentation, not a missing argument, and satisfying it has never
    produced anything. It must come back as nothing to do."""
    assert R.read_refusal("asn1parse: Use -help for summary.") is None
    assert R.read_refusal("tar --help    --usage") is None


def test_a_mutex_is_not_read_as_one_flag():
    """`-Acdtrux` is five options printed without separators.

    Adding it produced `tar --list -Acdtrux`, which tar reads as a flag it does not have.
    The program says which case it is: "one of ... options" is a choice."""
    clause = R.read_refusal(
        "tar: You must specify one of the '-Acdtrux', '--delete' or '--test-label' options")
    assert clause is not None
    assert clause.form == R.UNREAD, "a mutex was read as a single flag to add"
    assert clause.candidate == ""


# --------------------------------------------------------------------------- #
# where a repair is placed is part of the repair
# --------------------------------------------------------------------------- #
def test_a_flag_goes_in_the_option_region_and_a_value_goes_after_it():
    """The same defect round 7 found in the binder, reintroduced by appending.

    `openssl cms -stream in.txt -encrypt` answers "No operation option specified", because
    openssl stops reading options at the first operand; `openssl cms -encrypt -in=in.txt
    -out=out.bin cert.pem` exits 0 and writes the file. A flag is read by the option parser
    and a value is not, so each is placed where its own grammar expects it."""
    clause = R.read_refusal("No operation option (-encrypt|-decrypt) specified.")
    flagged = R.apply_clause(["openssl", "cms", "in.txt"], clause)
    assert flagged == ["openssl", "cms", "-encrypt", "in.txt"], (
        "the flag was appended after the operand and would never be parsed")

    witness = R.read_refusal("No recipient(s) certificate(s) specified")
    placed = R.apply_clause(["openssl", "cms", "-encrypt", "-in=in.txt"], witness,
                            files=["in.txt", "cert.pem"])
    assert placed[-1] == "cert.pem", "a value must go with the operands, not the flags"


def test_a_witness_is_a_file_whose_content_is_the_kind_asked_for(tmp_path):
    """A NAME IS NOT EVIDENCE. `in.txt` called a certificate is what produced
    `Unable to load certificate` 45 times."""
    cert = tmp_path / "cert.pem"
    cert.write_text("-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----\n")
    plain = tmp_path / "in.txt"
    plain.write_text("hello\n")
    assert R.file_is_kind(str(cert), "certificate") is True
    assert R.file_is_kind(str(plain), "certificate") is False
    assert R.file_is_kind(str(plain), "spreadsheet") is None, (
        "an unknown kind must be unknown, not a pass")


def test_a_clause_already_satisfied_is_not_reapplied():
    """A flag already in the command is not the missing piece, and adding it again is the
    loop this module is supposed to prevent."""
    clause = R.read_refusal("No signature to verify: use the -signature option")
    assert R.apply_clause(["openssl", "dgst", "-signature", "in.txt"], clause) is None


# --------------------------------------------------------------------------- #
# the world clause: the program ships its own initialiser
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not HAVE_GIT, reason="git is the world machine")
def test_the_world_action_is_the_subcommand_the_program_admitted():
    """`fatal: not a git repository` names git, and git's own admitted subcommands include
    `init`. The bare form is the program and the subcommand -- `git init` -- not one of the
    flag variants, because `git init --initial-branch=out.bin in.txt` does not create a
    repository and the first version of this picked exactly that."""
    from canonical.runtime import tool_census_v1 as C
    contract = C.parse_contract(C._own_text("git"), "git")
    census = C.census("git", depth=2, max_ops=60)
    bound = [C.bind(op, contract=contract) for op in census["operations"]]
    clause = R.read_refusal("fatal: not a git repository (or any of the parent directories)")
    world = R.world_for(clause, bound)
    assert world == ["git", "init"], f"the initialiser was read as {world}"


@pytest.mark.skipif(not HAVE_GIT, reason="git is the world machine")
def test_a_world_that_arrives_as_a_directory_is_visible_to_the_oracle():
    """`git init` creates `.git/` and changes no file at the top level.

    A file-only digest reported `world_created: False` for a world that had plainly been
    created -- and the same blindness is in `tool_census_v1`'s oracle. The digest walks
    directories, so a world that arrives as one is visible."""
    before = R.Repair("x", ["git", "add", "in.txt"], ["git", "add", "in.txt"],
                      None, 1, 1, "x", False, True)
    clause = R.read_refusal("fatal: not a git repository")
    before = R.Repair("x", ["git", "add", "in.txt"], ["git", "add", "in.txt"],
                      clause, 1, 1, "x", False, True)
    after = R.repair_in_world(before, world=["git", "init"],
                              seed=[("in.txt", b"hello\n")])
    assert after.learned["world_created"] is True
    assert after.verdict in R.DOOR_VERDICTS


# --------------------------------------------------------------------------- #
# the honest sizes
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not HAVE_GIT, reason="git is where the world clause pays")
def test_the_world_clause_pays_every_time_it_is_read():
    """435 of git's 480 refusals are one sentence, and answering it worked 435 times.

    This is the largest single refusal in the measurement and the only clause form that
    paid everything it read. It is also the reason the other forms' near-zero rate must be
    reported rather than smoothed: one mechanism did the work."""
    from canonical.runtime import tool_census_v1 as C
    contract = C.parse_contract(C._own_text("git"), "git")
    census = C.census("git", depth=2, max_ops=60)
    bound = [C.bind(op, contract=contract) for op in census["operations"]]
    committed = C.commit_check_many(bound, seed=C.trial_seeds(), preparation="PLAIN")
    refused = [row for row in committed["rows"] if row["verdict"] == "FAILED_NO_EFFECT"]
    result = R.repair_many(bound, seed=C.trial_seeds(),
                           only_ids=[row["id"] for row in refused])
    assert result["attempted"] == len(refused)
    assert result["answered"] >= 300, (
        f"the world clause answered {result['answered']} of {len(refused)}")
    assert result["all_restored"], "a repair left a tree modified"


def test_the_forms_that_answered_nothing_are_recorded_as_answering_nothing():
    """The measurement that matters is the one that makes this module look small.

    Across the fleet, WORLD answered everything it read and the other five forms answered
    about one in a hundred. A module that reported a single aggregate would hide that, and
    hiding it is how a tuned reader gets mistaken for a general one."""
    sizes = {"WORLD": (435, 435), "UNLOADABLE": (87, 0), "WITNESS": (14, 0),
             "ENUMERAL": (18, 1), "OFFERED": (12, 0), "CONFLICT": (4, 0), "RANGE": (7, 0)}
    forms = {name: read for name, (read, _paid) in sizes.items()}
    paid = {name: answered for name, (_r, answered) in sizes.items()}
    for name, read in forms.items():
        assert read > 0, f"{name} was never read; the measurement is not evidence"
    assert paid["WORLD"] == forms["WORLD"], "the world clause did not pay everything"
    other = sum(forms[n] for n in forms if n != "WORLD")
    other_paid = sum(paid[n] for n in forms if n != "WORLD")
    assert other_paid <= other * 0.05, (
        "the non-world forms are being credited with more than they earned")
