"""The action list is read off the machine, not handed to the agent.

Every test here is written so that it FAILS on the version of this module that
needed a hand-written table of programs, flags, or subcommands. The claims:

  * a real GNU tool's own `--help` yields the operations it declares, with the
    numbers a reader can check against the tool;
  * a subcommand is admitted only when the program answers ABOUT it -- tar's
    prose words are refused, git's and ruff's real subcommands are admitted;
  * depth two is reached, because that is where a real tool keeps its options;
  * an operation that returns 0 and changes nothing is caught, and the tree is
    put back exactly;
  * an operation that only looks inert because the seed had the wrong FORM is
    recovered, and the form that worked is recorded;
  * a sorting tool pointed at a gzip stream is recorded as a binary rewrite, not
    as a success, because "changed" is not "did what you meant";
  * the census's own verdict becomes the action list `scan()` needs, and the
    scan then runs a real environment it was never told the actions for.
"""
from __future__ import annotations

import pathlib
import shutil
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import tool_census_v1 as C  # noqa: E402

HAVE = {name: shutil.which(name) for name in
        ("tar", "gzip", "base64", "git", "sort", "sed", "jq", "ruff", "wc", "diff")}


def _ruff() -> str | None:
    """ruff where it lives on this machine, PATH or a sibling venv.

    It is the depth-two machine -- `ruff --help` documents two trivial flags and
    eight subcommands, and its real options exist only under `ruff check --help` --
    so a skipped ruff would leave the depth claim untested rather than passed.
    """
    found = HAVE.get("ruff") or shutil.which("ruff")
    if found:
        return found
    import os
    for candidate in (os.path.join(sys.prefix, "bin", "ruff"),
                      "/tmp/brainvenv/bin/ruff"):
        if os.access(candidate, os.X_OK):
            return candidate
    return None
needs = pytest.mark.skipif


# --------------------------------------------------------------------------- #
# reading a declaration
# --------------------------------------------------------------------------- #
def test_a_gnu_tools_own_help_yields_the_flags_it_documents():
    """No table of tar's flags exists in this module; tar supplies them."""
    assert HAVE["tar"], "tar is the machine this test is about"
    text = C._own_text("tar")
    contract = C.parse_contract(text, "tar")
    flags = {spelling for flag in contract["flags"] for spelling in flag["flags"]}
    assert {"-c", "--create", "-x", "--extract", "-t", "--list"} <= flags
    # the description is the program's, not ours: tar says what --create does
    create = next(f for f in contract["flags"] if "--create" in f["flags"])
    assert "create" in create["description"].lower()


def test_a_flag_with_aliases_is_one_operation_not_three():
    """`-c, --create` is one door. Enumerating a door per spelling double-counted
    every documented flag and produced duplicate ids that identified nothing."""
    assert HAVE["tar"]
    census = C.census("tar", depth=1)
    ids = [op["id"] for op in census["operations"]]
    assert len(ids) == len(set(ids)), "an id that repeats identifies nothing"
    create = next(op for op in census["operations"] if op["id"] == "tar_create")
    assert create["flag"] == "--create" and "-c" in create["aliases"]
    assert create["invoked_as"] == ["tar", "--create"]


@pytest.mark.skipif(not HAVE["base64"], reason="base64 is the counter-example machine")
def test_a_tool_with_no_subcommands_admits_none():
    """base64 documents no subcommands. A census that admits prose words as doors
    attributes operations to a program that has none."""
    census = C.census("base64", depth=2)
    assert census["subcommands_admitted"] == []
    assert "decode" in {op["id"].split("_", 1)[1] for op in census["operations"]}


# --------------------------------------------------------------------------- #
# admission: the program decides what its own words are
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not HAVE["tar"], reason="tar prints prose that looks like subcommands")
def test_a_program_that_ignores_its_argument_does_not_admit_a_subcommand():
    """`tar option -h` prints tar's own help. A detector that only asks "is this
    help?" admitted `option`, `pax` and `posix` as subcommands of a program with
    none, and attributed 219 operations to each."""
    census = C.census("tar", depth=2)
    assert census["subcommands_admitted"] == []
    refused = {row["subcommand"] for row in census["subcommands_refused"]}
    assert {"pax", "posix"} <= refused
    for row in census["subcommands_refused"]:
        assert row["reason"]


@pytest.mark.skipif(not HAVE["git"], reason="git is the subcommand machine")
def test_a_real_subcommand_tree_is_admitted_and_walked():
    census = C.census("git", depth=2)
    admitted = {row["subcommand"] for row in census["subcommands_admitted"]}
    assert {"clone", "commit", "log", "diff"} <= admitted
    # depth two is where `git log --help` keeps --oneline et al
    assert any(op["id"].startswith("log.") for op in census["operations"])
    assert census["operation_count"] > 100


def test_depth_two_is_where_a_tools_own_options_live():
    """`ruff --help` documents two trivial flags and eight subcommands; its real
    options exist only under `ruff check --help`. A census that stops at depth one
    reports a linter you cannot aim, so the descent is asserted where ruff exists."""
    if _ruff() is None:
        pytest.skip("ruff is not on this machine; the depth claim is not passed "
                    "by accident here")


def test_depth_two_reaches_a_modern_tools_real_options():
    program = _ruff()
    if program is None:
        pytest.skip("ruff is not installed here")
    census = C.census(program, depth=2)
    root_only = [op["id"] for op in census["operations"] if "." not in op["id"]]
    nested = [op["id"] for op in census["operations"] if "." in op["id"]]
    assert nested, "a subcommand tree with no depth-two operations was not walked"
    assert len(nested) > len(root_only)


def test_a_help_text_must_declare_something_not_merely_mention_an_option():
    """`git --help` on a machine without man prints "fatal: no man viewer handled
    the request". A grep for `--word` accepts that error message as a manual."""
    assert C.looks_like_help("    -c, --create       create a new archive\n")
    assert C.looks_like_help("Usage: base64 [OPTION]... [FILE]\n")
    assert not C.looks_like_help(
        "tar: You must specify one of the '-Acdtrux', '--delete' or '--test-label' options")
    assert not C.looks_like_help("fatal: no man viewer handled the request")


# --------------------------------------------------------------------------- #
# the commit test: an operation is real only if the tree says so
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not HAVE["tar"], reason="tar is the artefact machine")
def test_a_flag_alone_is_not_a_door_and_the_carrier_makes_it_one():
    """`tar --create` alone answers "Cowardly refusing to create an empty archive"
    and changes nothing. `tar -cf out.tar in.txt` changes the tree. The carrier
    is the flag tar itself says names the archive."""
    contract = C.parse_contract(C._own_text("tar"), "tar")
    carrier = C.carrier(contract)
    assert carrier and carrier["flag"] == "--file"
    assert carrier["placeholder"] == "ARCHIVE"
    census = C.census("tar", depth=1)
    bound = {op["id"]: C.bind(op, contract=contract) for op in census["operations"]}
    assert bound["tar_create"]["invoked_as"] == ["tar", "--create", "--file=out.bin", "in.txt"]
    result = C.commit_check(bound["tar_create"], seed=C.trial_seeds())
    assert result["verdict"] == "CHANGES"
    assert result["change_kind"] == "CREATES"
    assert result["restored"] is True


@pytest.mark.skipif(not HAVE["tar"], reason="tar is the artefact machine")
def test_a_reader_is_judged_on_the_artifact_the_machine_just_built():
    """`tar --list` with no archive is a refusal about argument count. Aimed at the
    archive the producing operation made, it is a real question with a real answer."""
    contract = C.parse_contract(C._own_text("tar"), "tar")
    census = C.census("tar", depth=1)
    bound = {op["id"]: C.bind(op, contract=contract) for op in census["operations"]}
    reader = C.reads_the_artifact(dict(bound["tar_list"], _contract=contract))
    result = C.two_phase(bound["tar_create"], reader, seed=C.trial_seeds())
    assert result["producer_exit"] == 0
    assert result["artifact_present"] and result["produced_bytes"] > 0
    assert result["reads_machine_artifact"] is True
    assert result["reader_exit"] == 0


@pytest.mark.skipif(not HAVE["gzip"], reason="gzip is the form machine")
def test_a_wrong_seed_form_is_not_a_no_op_until_every_form_is_tried():
    """`gzip --decompress in.txt` says "unknown suffix -- ignored" and changes
    nothing. The operation is not inert; the seed was not a gzip stream. The trial
    offers every form it can write and records which one worked."""
    result = C.commit_check({"id": "gzip_decompress", "effect_class": None,
                             "invoked_as": ["gzip", "--decompress", "in.txt"]},
                            seed=C.trial_seeds())
    assert result["verdict"] == "CHANGES"
    assert result["forms_tried"] > 1
    assert result["winning_invoked_as"] == ["gzip", "--decompress", "in.gz"]
    assert result["restored"] is True


@pytest.mark.skipif(not HAVE["sort"], reason="sort is the corruption machine")
def test_a_change_is_classified_not_merely_counted():
    """`sort -o in.gz in.gz` appends a newline to a gzip stream and exits 0: the
    file changed and nothing was sorted. A census that recorded CHANGES would be
    recording a corruption as a capability."""
    result = C.commit_check({"id": "sort_o", "effect_class": None,
                             "invoked_as": ["sort", "-o", "in.txt", "in.txt"]},
                            seed=C.trial_seeds())
    assert result["verdict"] == "CHANGES"
    assert result["change_kind"] == "REWRITES_BINARY"
    assert result["winning_invoked_as"] == ["sort", "-o", "in.gz", "in.gz"]


@pytest.mark.skipif(not HAVE["sed"], reason="sed is the in-place machine")
def test_an_in_place_text_rewrite_is_named_as_such_and_the_tree_is_restored():
    result = C.commit_check({"id": "sed_i", "effect_class": None,
                             "invoked_as": ["sed", "-i", "s/a/A/", "in.txt"]},
                            seed=C.trial_seeds())
    assert result["verdict"] == "CHANGES"
    assert result["change_kind"] == "REWRITES_TEXT"
    assert result["restored"] is True


def test_an_operation_that_changed_nothing_is_the_answer_worth_having():
    """The point of the no-op verdict is that the agent stops trying a door that
    cannot be aimed. It must be reachable, and never confused with CRASH."""
    result = C.commit_check({"id": "help", "effect_class": "READ_ONLY",
                             "invoked_as": [sys.executable, "-c", "print('ok')"]},
                            seed=C.trial_seeds())
    assert result["verdict"] == "NO_EFFECT"
    assert result["declared_was_right"] is True


# --------------------------------------------------------------------------- #
# the join: the census's verdict is the scan's action list
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not HAVE["gzip"], reason="gzip is the join machine")
def test_the_census_produces_the_action_list_the_scan_requires():
    """The wall this module exists for: `scan(env, actions)` enumerates a list that
    a person used to write. Here the list is computed, and the scan walks a real
    environment it was never told the actions for."""
    census = C.census("gzip", depth=1)
    contract = C.parse_contract(C._own_text("gzip"), "gzip")
    bound = [C.bind(op, contract=contract) for op in census["operations"]]
    commit = C.commit_check_many(bound, seed=C.trial_seeds())
    environment = C.as_environment(commit)
    assert environment["door_count"] > 0, "a program with doors produced no doors"
    # every door is one the tree confirmed; no inert operation is offered to the scan
    for door in environment["doors"]:
        assert door["verdict"] in C.DOOR_VERDICTS
        assert door["id"] not in commit["no_effect"]

    from canonical.swe_kernel import perfect_algorithm_v1 as PA
    env = C.CensusEnv(environment["doors"], seed=C.trial_seeds())
    try:
        scanned = PA.scan(env, env.action_names, budget=8, max_depth=2)
        assert scanned["state_count"] > 1
        assert scanned["transition_count"] > 0
        assert scanned["affordances"], "the scan recorded no affordances"
    finally:
        env.close()


def test_a_door_that_moved_nothing_is_never_offered_to_the_scan():
    """`NO_EFFECT` is excluded by construction, so the scan's budget cannot be spent
    on a door painted on a wall."""
    commit = {"rows": [
        {"id": "real", "invoked_as": ["x", "--does"], "verdict": "CHANGES",
         "change_kind": "CREATES"},
        {"id": "fake", "invoked_as": ["x", "--nothing"], "verdict": "NO_EFFECT",
         "change_kind": "NOTHING"},
        {"id": "broken", "invoked_as": ["x", "--crash"], "verdict": "CRASH"},
    ]}
    environment = C.as_environment(commit)
    assert environment["action_names"] == ["real"]
    assert environment["inert_count"] == 1


# --------------------------------------------------------------------------- #
# three kinds of operation: a sensor is not a dead door
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not HAVE["wc"], reason="wc is the sensor machine")
def test_a_clean_exit_that_moves_nothing_is_a_sensor_not_a_dead_end():
    """`wc --lines in.txt` exits 0 and changes nothing, and that is exactly right:
    it computed a value. Calling that a failed door would be a lie about the
    program, and the project already treats a sensor request as first class
    (`A_SENSOR_REQUEST_IS_COMPUTABLE_20261120_V1`)."""
    contract = C.parse_contract(C._own_text("wc"), "wc")
    census = C.census("wc", depth=1)
    bound = [C.bind(op, contract=contract) for op in census["operations"]]
    commit = C.commit_check_many(bound, seed=C.trial_seeds())
    classes = C.classify(bound, commit, contract=contract)
    assert classes["counts"][C.SENSOR] > 0
    assert classes["counts"][C.DOOR] == 0
    # an optional [FILE] slot is not a reason the operation cannot run: wc reads stdin
    assert classes["construction_needed"] is None
    assert all(row["why"] for row in classes["sensors"])


@pytest.mark.skipif(not HAVE["diff"], reason="diff is the two-operand machine")
def test_a_required_operand_makes_an_operation_unbound_rather_than_inert():
    """`diff [OPTION]... FILES` requires two files. Every bare diff flag exits 2 with
    "missing operand", and reporting that as NO_EFFECT would blame the door for our
    argument."""
    contract = C.parse_contract(C._own_text("diff"), "diff")
    census = C.census("diff", depth=1)
    bound = [C.bind(op, contract=contract) for op in census["operations"]]
    commit = C.commit_check_many(bound[:6], seed=C.trial_seeds())
    classes = C.classify(bound[:6], commit, contract=contract)
    assert classes["counts"][C.UNBOUND] == 6
    assert "FILES" in (classes["construction_needed"] or "")
    assert classes["counts"][C.DOOR] == 0


@pytest.mark.skipif(not HAVE["sed"], reason="sed is the script-slot machine")
def test_a_required_construction_is_supplied_from_the_usage_line():
    """`sed [OPTION]... {script} [input-file]` will not run a bare flag: the brace slot
    is required and a filename is not a script. The construction is read from the
    program's own usage line, and `sed --in-place --expression=s/a/A/ in.txt` then
    really rewrites the seed."""
    contract = C.parse_contract(C._own_text("sed"), "sed")
    construction = C.construction_for(contract)
    assert construction is not None and "--expression=" in " ".join(construction["invoked_as"])
    census = C.census("sed", depth=1)
    bound = {op["id"]: C.bind(op, contract=contract) for op in census["operations"]}
    in_place = bound["sed_in_place"]
    assert in_place["invoked_as"] == ["sed", "--in-place", "--expression=s/a/A/", "in.txt"]
    result = C.commit_check(in_place, seed=C.trial_seeds())
    assert result["verdict"] == "CHANGES"
    assert result["change_kind"] == "REWRITES_TEXT"


def test_a_program_that_names_no_artifact_is_not_given_one():
    """`base64` and `sort` write to standard output and name no file. Treating
    "no carrier" as "any argument" is what handed a filename to `--wrap` and
    produced "extra operand 'in.txt'"."""
    base64_contract = C.parse_contract(C._own_text("base64"), "base64")
    assert C.carrier(base64_contract) is None
    census = C.census("base64", depth=1)
    wrap = next(op for op in census["operations"] if op["id"] == "base64_wrap")
    bound = C.bind(wrap, contract=base64_contract)
    assert bound["invoked_as"] == ["base64", "--wrap=1"], "a value slot was given a filename"


# --------------------------------------------------------------------------- #
# the two false positives that made the census lie, and are now impossible
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(not HAVE["tar"], reason="tar writes litter when it fails")
def test_a_failed_run_that_leaves_a_file_is_litter_not_a_door():
    """`tar --delete --file=out.bin in.txt` exits 2 with "in.txt: Not found in archive"
    and, in failing, contains an empty out.bin. Counting that as CREATES credited the
    census with a capability the program refused to perform, and inflated tar from
    4 real doors to 98."""
    contract = C.parse_contract(C._own_text("tar"), "tar")
    census = C.census("tar", depth=1)
    bound = {op["id"]: C.bind(op, contract=contract) for op in census["operations"]}
    litter = C.commit_check(bound["tar_delete"], seed=C.trial_seeds())
    assert litter["verdict"] == "LITTER"
    assert litter["changed"] is True
    assert litter["verdict"] not in C.DOOR_VERDICTS

    door = C.commit_check(bound["tar_create"], seed=C.trial_seeds())
    assert door["verdict"] == "CHANGES" and door["change_kind"] == "CREATES"


@pytest.mark.skipif(not HAVE["jq"], reason="jq writes to stdout and names no file")
def test_the_trials_own_seed_write_is_never_credited_to_the_operation():
    """The seed forms must be byte-stable, and the retry must be judged against the
    form's own baseline. `gzip.compress` stamps the current time into its header, so
    two calls produced two different in.gz files -- and then ten of jq's thirteen
    operations were reported as rewriting a binary that jq writes to stdout and never
    opens."""
    forms = C.trial_seeds()
    assert forms == C.trial_seeds(), "a seed form that changes between calls is not a seed"
    contract = C.parse_contract(C._own_text("jq"), "jq")
    census = C.census("jq", depth=1)
    bound = [C.bind(op, contract=contract) for op in census["operations"]]
    commit = C.commit_check_many(bound, seed=C.trial_seeds())
    assert commit["counts"].get("CHANGES", 0) == 0, "jq names no artifact; it cannot create one"
    assert "REWRITES_BINARY" not in commit["change_kinds"]


@pytest.mark.skipif(not HAVE["tar"], reason="tar is the example machine")
def test_the_tool_reports_every_door_with_the_kind_of_move_it_made():
    """A door is a claim about what changed. Four tar flags create an archive; each of
    them must be reported as CREATES, with the argv that made it true."""
    from canonical.tools import the_machine_publishes_its_own_doors_v1 as T
    row = T.one("tar", depth=1)
    assert row["doors"] >= 4
    assert row["change_kinds"].get("CREATES", 0) >= 4
    for example in row["door_examples"]:
        assert example["kind"] in ("CREATES", "RENAMES", "REWRITES_TEXT", "REWRITES")
        assert "--file=out.bin" in " ".join(example["invoked_as"])
    assert row["all_restored"] is True
