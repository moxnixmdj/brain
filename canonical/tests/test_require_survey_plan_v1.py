"""The document is the plan: what is enforced, and what is measured.

Three kinds of test here, deliberately separated:

* **static** -- the mechanism names no tool, flag, or answer (A1), calls no model and opens no
  socket (A6). Enforced by reading this module's own source, so a future edit cannot quietly
  reintroduce a table.
* **behavioural** -- routing, requiring, refusing and the copy doctrine, on documents the tests
  write themselves. These use no real program, so they hold on any host.
* **measured** -- a small arm over real programs on this host, reported as numbers. A refusal here
  is a sound refusal (A2), never a silent wrong action.
"""
from __future__ import annotations

import ast
import base64
import json
import pathlib
import re
import shutil
import textwrap

import pytest

from canonical.runtime import require_survey_plan_v1 as R

# The bench programs live in this repository, under `programs/`. They are the documents these
# tests read, and a test that cannot be re-run on a clean checkout is not evidence: before this,
# eight of them read a scratch directory and silently skipped -- or failed -- anywhere else.
_HERE = pathlib.Path(__file__).resolve()
CB_BIN = _HERE.parent / "programs" / "bin"
CB_BIN3 = _HERE.parent / "programs" / "bin3"

MODULE = pathlib.Path(R.__file__)

# Tool and flag names that must never appear as data in the mechanism. This is the A1 list,
# written once, used by the static test: the mechanism may *read* such words from a document,
# and may never *carry* one.
FORBIDDEN_LITERALS = {
    "gzip", "gunzip", "tar", "zip", "unzip", "base64", "sort", "cut", "cp", "mv", "rm", "ls",
    "git", "jq", "sed", "awk", "grep", "find", "identify", "convert", "ffmpeg", "pandoc",
    "gh", "curl", "wget", "docker", "kubectl",
    "--output", "-o", "--file", "-f", "--directory", "-d", "--create", "-c", "--extract",
    "--decode", "--encode", "--list", "-l", "--suffix", "-S", "--verbose", "-v",
}


def _module_literals(include_cli: bool = False) -> set[str]:
    """Every string literal in the module except the module's own prose (docstrings).

    The docstring is allowed to name what the module is about -- it is the one place a human
    reads the design; the executable body is not allowed to carry a tool or a flag. `main` is
    excluded by default for one honest reason: a command-line interface to this module must
    spell its own switches, and those switches are arguments to *this file*, not knowledge
    about any other program. The test that cares (A1) reads the mechanism without them.
    """
    tree = ast.parse(MODULE.read_text())
    if not include_cli:
        for node in list(ast.walk(tree)):
            if isinstance(node, ast.FunctionDef) and node.name == "main":
                tree.body = [n for n in tree.body if n is not node]
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                and body and isinstance(body[0], ast.Expr) \
                and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            docstrings.add(id(body[0].value))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and id(node) not in docstrings:
            out.add(node.value)
    return out


def test_a1_the_mechanism_carries_no_tool_name_and_no_flag_name():
    """A1: a tool, a binary, or an option may be read from a document, never written into code."""
    literals = _module_literals()
    offenders = sorted(
        literal for literal in literals
        if literal.strip().lower() in FORBIDDEN_LITERALS)
    assert offenders == [], f"tool/flag literals in the mechanism: {offenders}"


def test_a1_the_mechanism_reads_no_table_of_answers():
    """A1: no dictionary or tuple keyed by a program name may exist in the module."""
    tree = ast.parse(MODULE.read_text())
    named = {"META_KINDS", "PRODUCT_META", "STOP", "ACTS", "DEST_MARKERS", "SOURCE_MARKERS",
             "NOT_A_DOCUMENT", "INVERSE_PREFIXES", "FORBIDDEN"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key in node.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    assert key.value.lower() not in FORBIDDEN_LITERALS, key.value
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.startswith("TOOL"):
                    assert target.id in named
    # A flag-shaped literal is allowed only if it is the asking convention itself: the protocol
    # by which this module addresses *any* program's document. Nothing else about any program.
    asking = set(R.ASK_CONVENTION[0]) | {part for rung in R.ASK_CONVENTION for part in rung}
    flags = {literal for literal in _module_literals() if re.match(r"^--?[a-z]", literal)}
    assert flags <= asking, f"flag-shaped knowledge outside the asking convention: {flags - asking}"
    assert asking, "the asking convention must be non-empty, or nothing could be read at all"
    assert any(literal.startswith("--") for literal in _module_literals(include_cli=True)), \
        "the module does expose a CLI, so the exclusion above must be doing real work"


def test_a6_no_model_call_and_no_network_client_in_the_mechanism():
    """A6: zero model calls, zero parameters, zero network -- by import and by name."""
    text = MODULE.read_text()
    tree = ast.parse(text)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    for banned in ("socket", "urllib", "http", "requests", "httpx", "openai", "anthropic",
                   "torch", "transformers"):
        assert banned not in imported, banned
    # The banned names are checked as *identifiers*, not as substrings anywhere in the source.
    # `llm` as a bare substring matches the character class `[a-zA-Z0-9]` -- the ranges of A-Z and
    # a-z spell `...zA-Z...`, which contains `llm`. A guard that fires on a regex character class is
    # not measuring what it claims to measure, and a guard nobody trusts is worse than none.
    lowered = text.lower().replace("no model call", "")
    for banned in ("call_model", "model_call", "completion("):
        assert banned not in lowered, banned
    assert not re.search(r"\bllms?\b", lowered), "llm identifier"
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            assert "llm" not in node.id.lower(), node.id
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            assert "llm" not in node.name.lower(), node.name


# --------------------------------------------------------------------------- documents written
#                                                                            by the test itself

PY = "python3"
DOC = {
    "shrink": {
        "root": """\
Usage: shrink [OPTION]... [FILE]...
Reduce the size of FILE, writing the result to standard output.

  -r, --ratio=NUM       reduce by a factor of NUM
      --help            display this help and exit
""",
    },
    "flow": {
        "root": """\
Usage: flow [OPTION]... [FILE]...
Gather lines from FILE(s) to standard output.

  -f, --fold[=NUM]      join lines after NUM characters
  -w, --width=NUM       set the width of a folded line
  -o, --out=FILE        write the result to FILE instead of standard output
      --help            display this help and exit
""",
    },
    "box": {
        "root": """\
Usage: box [OPTION]... COMMAND [ARG]...

Commands:
  pack      Put files into a single box file
  unpack    Take files back out of a box file
  verify    Check a box file without opening it

Run 'box COMMAND --help' for details.
""",
        "pack": """\
Usage: box pack [OPTION]... BOXNAME [FILE]...
Put files into a single box file.

  -c, --compress=NUM    compress with strength NUM
  -m, --mode=MODE       set the entry mode to MODE
""",
    },
}


@pytest.fixture()
def fake_host(tmp_path: pathlib.Path) -> pathlib.Path:
    """Two programs whose only documentation is what this test wrote."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, pages in DOC.items():
        root = pages["root"]
        pages_code = {key: value for key, value in pages.items() if key != "root"}
        script = f"""#!{shutil.which(PY)}
import sys
PAGES = {json.dumps(pages_code)}
ROOT = {root!r}
args = sys.argv[1:]
if args and args[0] in PAGES and any(a in ("--help", "-h") for a in args[1:]):
    sys.stdout.write(PAGES[args[0]])
elif any(a in ("--help", "-h") for a in args) or not args:
    sys.stdout.write(ROOT)
else:
    sys.exit(0)
"""
        path = bin_dir / name
        path.write_text(textwrap.dedent(script))
        path.chmod(0o755)
    return bin_dir


def test_the_program_is_routed_to_the_subcommand_the_request_is_about(fake_host, monkeypatch):
    tool = str(fake_host / "box")
    tree = R.survey(tool, want=sorted(R.words_of("put my files into a box file")))
    # this fake answers its root page for the subcommands it does not know, so a survey that
    # reported three children would be inventing pages out of an echo
    assert [c["title"] for c in tree["root"]["children"]] == ["pack"]
    assert tree["root"]["children"][0]["options"], "the pack page's own options were not read"
    routed = R.route(tree, R.words_of("put my files into a box file"),
                     [("put", "put")])
    assert routed["path"] == ["pack"]


def test_the_destination_takes_the_slot_that_means_a_place(fake_host):
    tool = str(fake_host / "flow")
    result = R.require_survey_plan(tool, "write /tmp/source.txt to /tmp/report.txt")
    product = [p for p in result["plans"] if p["reason"].startswith("PLANNED_INTO")]
    assert product, result["plans"]
    argv = product[0]["argv"]
    assert argv[0] == tool and "--out" in argv
    assert argv[argv.index("--out") + 1] == "/tmp/report.txt"
    assert "/tmp/source.txt" in argv


def test_a_destination_no_slot_carries_is_planned_as_a_redirect(fake_host, tmp_path):
    """A named destination with no slot to live in is the shell's job, and is planned as one.

    The document here declares one option that takes a number and no place at all, so the only
    way a result reaches the requested file is the redirect the request itself implies.
    """
    tool = str(fake_host / "shrink")
    report = tmp_path / "report.txt"
    result = R.require_survey_plan(tool, f"reduce {tmp_path}/source.txt to {report}")
    redirected = [p for p in result["plans"] if p.get("stdout_to")]
    assert redirected, [p["reason"] for p in result["plans"]]
    assert redirected[0]["stdout_to"] == str(report)
    assert str(report) not in redirected[0]["argv"]


def test_the_document_is_free_no_store_no_cache_and_nothing_written(fake_host, tmp_path):
    """A3: reading a document re-derives it and stores zero bytes, and probing writes nothing."""
    tool = str(fake_host / "flow")
    before = sorted(p.name for p in tmp_path.iterdir())
    tree = R.survey(tool)
    after = sorted(p.name for p in tmp_path.iterdir())
    assert tree["stored_bytes"] == 0
    assert tree["document_bytes"] > 0 and tree["documents_ok"] >= 1
    assert before == after, "probing a document must not write into the caller's world"


def test_an_act_outside_the_closed_class_is_refused_by_name(fake_host):
    result = R.require_survey_plan(str(fake_host / "flow"), "zorbulate the /tmp/thing.txt")
    assert result["complete"] is False
    assert result["reason"] == "NO_ACT_THE_REQUEST_NAMES"
    assert result["refusals"][0]["reason"] == "NO_ACT_IN_THE_CLOSED_CLASS"


def test_a_value_of_no_accepted_kind_is_refused_naming_its_own_word(fake_host):
    """A2: the refusal names the requirement word it could not bind, not a generic failure."""
    result = R.require_survey_plan(str(fake_host / "flow"), "fold the file /tmp/x.txt")
    # nothing to refuse here: a path and an act the document carries
    assert result["complete"] is True
    # and a refusal is refused by the name of the word it could not bind
    outside = R.require("zorbulate /tmp/x.txt")
    assert outside["reasons"] == ["NO_ACT_IN_THE_CLOSED_CLASS"]
    refusal = R.require_survey_plan(str(fake_host / "flow"), "zorbulate /tmp/x.txt")
    assert refusal["refusals"][0]["reason"] == "NO_ACT_IN_THE_CLOSED_CLASS"


def test_verification_acts_in_a_copy_and_never_on_the_named_world(tmp_path):
    """The copy doctrine: the plan names the real path, the execution touches the copy only."""
    world = tmp_path / "world"
    world.mkdir()
    (world / "source.txt").write_text("alpha\n")
    plan = {"argv": ["cp", str(world / "source.txt"), str(world / "copy.txt")]}
    seen: dict[str, object] = {}

    def judge(status):
        copied = pathlib.Path(status["world"]) / "copy.txt"
        seen["copy"] = copied.exists()
        seen["original_untouched"] = not (world / "copy.txt").exists()
        return copied.exists()

    got = R.verify_plans([plan], workdir=str(world), is_success=judge)
    assert got["success"] is True
    assert seen["copy"] is True and seen["original_untouched"] is True
    assert got["chosen"][0] == "cp"
    assert "verify-" in got["chosen"][1]
    assert got["chosen_planned"] == plan["argv"]
    assert not (world / "copy.txt").exists()


def test_a_failing_predicate_tries_the_next_reading_and_reports_every_attempt(tmp_path):
    world = tmp_path / "w"
    world.mkdir()
    (world / "a.txt").write_text("alpha\n")
    plans = [{"argv": ["true"]}, {"argv": ["true"]}]
    plans[0]["argv"] = ["false"]
    got = R.verify_plans(plans, workdir=str(world), is_success=lambda st: st["exit"] == 0)
    assert got["success"] is True and got["tried"] == 2
    assert [a["exit"] for a in got["attempts"]] == [1, 0]


# --------------------------------------------------------------------------- measured, not enforced

MEASURED = [
    ("gzip", "Compress the file {w}/notes.txt", "notes.txt.gz"),
    ("zip", "Compress {w}/notes.txt into {w}/bundle.zip", "bundle.zip"),
    ("tar", "Create {w}/bundle.tar from the file {w}/notes.txt", "bundle.tar"),
    ("sort", "Sort {w}/words.txt into {w}/sorted.txt", "sorted.txt"),
    ("cp", "Copy {w}/notes.txt to {w}/copy.txt", "copy.txt"),
    ("base64", "Encode {w}/notes.txt into {w}/notes.b64", "notes.b64"),
]


@pytest.mark.parametrize("tool,instruction,expected", MEASURED)
def test_measured_on_this_host_the_effect_is_produced_or_the_plan_is_refused(
        tool, instruction, expected, tmp_path):
    """Measured arm: the goal is reached by acting in a copy, or the plan is refused by name.

    A host without the program skips, and a host where the tool's own document differs is a
    measurement, not a failure: the assertion is that the loop never claims success it did
    not observe and never leaves a wrong action behind in the world.
    """
    if shutil.which(tool) is None:
        pytest.skip(f"{tool} not on this host")
    world = tmp_path / tool
    world.mkdir()
    (world / "notes.txt").write_text("alpha one\nbeta two\ngamma three\n")
    (world / "words.txt").write_text("pear,3\napple,1\nfig,2\n")
    result = R.require_survey_plan(tool, instruction.format(w=world), probes=12)
    target = world / expected

    def judge(status):
        """Success is the artifact, read in the copy -- never the planner's own confidence."""
        artifact = pathlib.Path(status["world"]) / expected
        if not artifact.exists() or not artifact.is_file() or artifact.stat().st_size == 0:
            return False
        return status["exit"] == 0

    verdict = R.verify_plans(result["plans"], workdir=str(world), is_success=judge) \
        if result["plans"] else {"success": False, "attempts": []}
    if verdict["success"]:
        assert verdict["chosen"] is not None
        # the action ran in a copy, so the copy's own paths are what the verifier saw
        assert "verify-" in " ".join(verdict["chosen"])
        assert str(tmp_path) not in " ".join(verdict["chosen"])
    else:
        assert result["complete"] is False or verdict["attempts"], result
        assert not target.exists(), "a failed verification must not have touched the world"


def test_the_survey_budget_is_never_exceeded(tmp_path):
    world = tmp_path / "w"
    world.mkdir()
    result = R.require_survey_plan("git", "Show the status of the repository", probes=3)
    assert len(result["documents_asked"]) <= 3
    assert result["survey"]["document_bytes"] >= 0


# --------------------------------------------------------------------------- the composed reading
#                                                                            in the document's own
#                                                                            grammar

def _box_pack_reading(values_text: str):
    """A reading of a `stitch`-shaped document: one named place for the product, one repeatable."""
    usage = {"usage": "quilt stitch [OPTION]... OUTFILE [PATCH]...",
             "variants": [{"usage": "quilt stitch [OPTION]... OUTFILE [PATCH]...",
                           "commands": ["quilt", "stitch"],
                           "positional": ["[OPTION]...", "OUTFILE", "[PATCH]..."]}]}
    usage["options"] = []
    return usage


def test_a_repeatable_place_takes_every_leftover_and_a_single_place_takes_one():
    """`[PATCH]...` is repeatable and `FILE` is not; the ellipsis is the only thing that says so."""
    repeatable = R.repeatable_places(_box_pack_reading(""))
    assert repeatable == {"option", "patch"}
    usage = _box_pack_reading("")
    picture = R.positional_grammar(usage)
    assert picture == ["option", "outfile", "patch"]


def test_the_place_named_for_the_product_is_claimed_before_any_other_object():
    """`OUTFILE` belongs to the thing made, or a patch would be written over instead of read."""
    usage = _box_pack_reading("")
    requirement = R.require(
        "Join /tmp/a/one.diff and /tmp/a/two.diff into /tmp/a/all.diff")
    readings = R._composed_readings(requirement, usage, R.positional_grammar(usage))
    assert readings, "the document states every place this request needs"
    bound, reason = readings[0]
    assert reason == "PLANNED_BY_A_COMPOSED_READING"
    means = {item["value"]: item.get("means") for item in bound}
    assert means["/tmp/a/all.diff"] == "outfile"
    assert means["/tmp/a/one.diff"] == "patch" and means["/tmp/a/two.diff"] == "patch"


def test_a_grammar_with_no_place_for_the_product_uses_the_shell():
    """No place named for the result does not mean no result: the request's own shape says how.

    `quilt measure [FILE]...` has nowhere but its argument list, and the request says `into
    report.txt`. The shell carries the result, exactly as the request states, and the reading is
    complete -- two objects placed, one stream carrying the product.
    """
    usage = {"usage": "quilt measure [FILE]...",
             "variants": [{"usage": "quilt measure [FILE]...", "commands": ["quilt", "measure"],
                           "positional": ["[FILE]..."]}], "options": []}
    requirement = R.require("Measure /tmp/a/one.diff and /tmp/a/two.diff into /tmp/a/report.txt")
    readings = R._composed_readings(requirement, usage, R.positional_grammar(usage))
    assert len(readings) == 1
    bound, _ = readings[0]
    sinks = [item for item in bound if item["role"] == "redirect"]
    assert [item["value"] for item in sinks] == ["/tmp/a/report.txt"]
    placed = sorted(item["value"] for item in bound if item["role"] == "positional")
    assert placed == ["/tmp/a/one.diff", "/tmp/a/two.diff"]


def test_the_made_thing_is_written_in_the_place_the_grammar_gives_it():
    """Positionals are ordered by their place in the grammar, not by the order they were named."""
    argv = R._render("quilt", ["stitch"], None, [
        {"role": "positional", "value": "one.diff", "means": "patch", "place_index": 2},
        {"role": "positional", "value": "all.diff", "means": "outfile", "place_index": 1},
        {"role": "positional", "value": "two.diff", "means": "patch", "place_index": 2},
    ])
    assert argv == ["quilt", "stitch", "all.diff", "one.diff", "two.diff"]


def test_the_same_request_plans_the_same_way_twice():
    """A plan is a reading of the request, not a sample from it.

    Every value this planner assigns is fixed by stated evidence. The failure this pins was
    real: `--severity`'s description names both `severity` and `incident`, so two of the
    request's values matched it equally well, and which one won came from the iteration order of
    a `set` of words -- that is, from the process's hash seed. Measured across twelve seeds, five
    produced `--severity P1` and seven produced `--severity "Payment Service Degradation"`. The
    same request and the same document gave different answers because a tie was broken by memory
    layout. The fix is stated evidence: a value belongs to the word it follows in the request,
    which is `with severity "P1"` at ten characters against `incident` at a hundred and sixty.

    The page is a program's own, read the way the planner reads every page -- a fixture cannot
    state the parent pages a demonstration is looked up through, and a test that rebuilds the
    path by hand tests the fixture instead of the planner.
    """
    binary = str(CB_BIN / "alertmgr")
    if not pathlib.Path(binary).exists():
        pytest.skip("the benchmark's alertmgr page is not on this machine")
    requirement = R.require(
        'Handle a production incident. Create a new incident titled '
        '"Payment Service Degradation" with severity "P1" and link the '
        'acknowledged alerts to it.')
    tree = R.survey(binary, want=sorted(R.words_of(requirement["instruction"])), probes=14)
    once, twice = [], []
    for target in (once, twice):
        target.extend(p["argv"] for p in R.plan(requirement, tree, ask_program=False,
                                                read_manual=False)["plans"])
    assert once == twice

    # the value binds to the word it follows, not to the nearest word that fits at all
    assert any("P1" in argv for argv in once), once


def test_a_request_written_as_steps_is_read_as_steps():
    """The sentence is the boundary the request states, and only where a new act appears.

    A task that names several acts is several acts; reading it as one is how a later step's
    value ends up in an earlier step's flag. But a sentence that names no act continues the
    sentence before it -- `Create a workflow named "x". Set the owner to "y".` is one create with
    two of its own fields, and splitting it cuts `--name` off the command it belongs to.
    """
    # a sentence that opens with an act is a step of its own
    assert R.sentences_of('Create a workflow named "deploy". Approve the gate.') == [
        'Create a workflow named "deploy".', 'Approve the gate.']
    # a sentence that names no act continues the step before it
    assert R.sentences_of(
        'Create a workflow named "deploy". The workflow should have two steps: '
        'a "build" step.') == [
        'Create a workflow named "deploy". The workflow should have two steps: a "build" step.']
    # guidance about the exercise is not a step of it
    assert R.sentences_of(
        'Approve the gate. You are not provided with documentation -- discover the tool.') == [
        'Approve the gate.']

    numbered = R.sentences_of(
        'Using the tool:\n1. Get workflow "wf-1".\n2. Approve gate "g-1".\n'
        'You are not provided with documentation.')
    assert numbered == ['Get workflow "wf-1".', 'Approve gate "g-1".']


def test_a_flag_the_document_calls_required_is_the_reason_to_prefer_a_reading():
    """`(required)` is the document's own statement, and it decides between readings.

    `flowctl gate approve` marks `--id` required. The flagless reading is available and looks
    complete, and the document says it is not this command. Before this, the flagless reading
    was emitted and the world refused it.
    """
    binary = str(CB_BIN / "flowctl")
    if not pathlib.Path(binary).exists():
        pytest.skip("the benchmark's flowctl page is not on this machine")
    result = R.require_survey_plan(
        binary, 'Approve gate "gate-001" with comment "LGTM, deploys to production".', probes=14)
    top = result["plans"][0]["argv"]
    assert "--id" in top, top
    assert result["complete"] is True


def test_the_required_marker_is_read_from_the_document_and_not_dropped():
    """The parser matched `(required)` and then discarded it; the planner could not see it."""
    required = R._option_cell("  --id <string> (required)\tGate ID", "FLAGS")
    optional = R._option_cell("  --comment <string>\tApproval comment", "FLAGS")
    assert required["required"] is True
    assert optional["required"] is None


def test_a_sequence_never_runs_the_same_command_twice():
    """Two steps that plan to one argv said one thing twice; running it twice does nothing."""
    binary = str(CB_BIN / "notion")
    if not pathlib.Path(binary).exists():
        pytest.skip("the benchmark's notion page is not on this machine")
    result = R.require_survey_plan_sequence(
        binary, 'List all pages in the workspace. Show the page title and parent.', probes=14)
    assert len(result["commands"]) == len({tuple(c) for c in result["commands"]})


def test_a_step_with_no_operation_is_not_emitted_as_a_command():
    """A bare value is not a command: `set the owner to "devops"` is not `devops`."""
    binary = str(CB_BIN / "flowctl")
    if not pathlib.Path(binary).exists():
        pytest.skip("the benchmark's flowctl page is not on this machine")
    result = R.require_survey_plan_sequence(
        binary, 'Create a workflow named "deploy". Set the owner to "devops-team".', probes=14)
    for command in result["commands"]:
        assert len(command) > 1, command


def test_a_possessive_apostrophe_does_not_open_a_quoted_value():
    """`the project's target date` contains one quote, and it is not a quotation mark.

    Reading it as one made `s target date to match the milestone` a value of the request, which
    the planner then filled into a flag and the world refused. A straight quote opens a value only
    where it is not preceded by a letter; the closing side needs no condition, because a
    possessive has no partner and the two plain quotes of a real quotation balance each other.
    """
    possessives = R.require("Update the Linear project's target date to match the milestone")
    assert [v["value"] for v in possessives["values"]] == []

    quoted = R.require('Create a page titled "Project Tracking" here')
    assert [v["value"] for v in quoted["values"]] == ["Project Tracking"]

    single = R.require("Set the label 'bug' on the issue")
    assert [v["value"] for v in single["values"]] == ["bug"]


def test_naming_a_thing_outranks_mentioning_it():
    """A page's path names what it is; its summary says what it can be told about.

    Probed on the real `linear` document: `issue list` summarises itself "List issues with
    optional filtering by project, assignee, or status", so the word `project` -- a filter this
    command accepts -- scored as highly as the title of `project list`, and "list all projects"
    routed to `issue list`. A parameter is not the subject. The fix weights the path above the
    summary, and breaks ties by the shorter path, because a longer path is named by words the
    request did not ask for.
    """
    import shutil
    exe = str(CB_BIN / "linear")
    if not shutil.which(exe) and not pathlib.Path(exe).exists():
        pytest.skip("the linear program is not on this host")
    request = "List all projects in the Linear workspace."
    tree = R.survey(exe, want=sorted(R.words_of(request)), probes=16)
    routed = R.route(tree, R.words_of(request), [("list", "list")])
    assert routed["path"] == ["project", "list"], routed["path"]


def test_completeness_is_decided_both_ways_and_means_the_pages_own_requirements():
    """A reading is complete exactly when it satisfies every flag its page marks required.

    The census used to only ever CLEAR this flag, so a candidate from a route that never set it
    stayed incomplete forever: `linear project list` declares no required flags and was reported
    incomplete, and 59 of 60 real tasks reported incomplete -- including ones that scored 0.9.
    A flag that is always false carries no information, and this one is the system's only means
    of saying what it does not know.
    """
    # a page with no required flags: a command that names the page is complete
    request = "List all projects in the Linear workspace."
    out = R.require_survey_plan(str(CB_BIN / "linear"), request, probes=16)
    assert out["plans"][0]["argv"][1:] == ["project", "list"], out["plans"][0]["argv"]
    assert out["plans"][0]["missing_required"] == []
    assert out["plans"][0]["complete"] is True

    # a page WITH required flags: a reading that lacks them is incomplete, and says which
    created = ("Create a new workflow named \"deploy-staging\" using the flowctl tool.\n"
               "The workflow should have two steps: a \"build\" step with action \"run_pipeline\"\n"
               "and an \"approve\" step with action \"gate\".")
    plans = R.require_survey_plan(str(CB_BIN / "flowctl"), created, probes=16)["plans"]
    assert any(p["complete"] for p in plans), [p.get("missing_required") for p in plans]
    assert any(p["missing_required"] for p in plans), "an incomplete reading must name what it lacks"


def test_the_scan_is_not_steered_by_the_guess_it_is_meant_to_test():
    """A survey spent along the route the request already suggests cannot refute that route.

    `want` ranks pages by the request's words and spends the probe budget depth-first along that
    ranking, so the survey reaches exactly the pages the guess points at. "Send a direct message
    to the Slack user alice" was steered into `message send`, and `dm send` -- whose own summary
    is "Send a direct message to a user" and which declares the `--user` flag the request needs
    -- was never fetched, although the whole help is ten pages and 0.17 seconds. The plan that
    came back named `--channel alice`, a flag the request never mentions.
    """
    request = ('Send a direct message to the Slack user "alice" with the text: "on my way".')
    out = R.require_survey_plan(str(CB_BIN / "slack"), request, probes=14)
    assert out["path"] == ["dm", "send"], out["path"]
    # The route is what this test is about. Binding `alice` to `--user` is a separate matter --
    # the flag/value pairing -- and ordering demonstrations by how much shape they state was
    # measured separately and lost (0.4291, three tasks unable to run), so it is not assumed here.
    assert "--user" in " ".join(str(t) for p in out["plans"] for t in p["argv"]), \
        [p["argv"] for p in out["plans"]]

    # and the sequence path -- what the agent actually runs -- agrees with the single one
    seq = R.require_survey_plan_sequence(str(CB_BIN / "slack"), request, probes=14)
    assert seq["commands"], seq["steps"]
    assert seq["commands"][0][1:3] == ["dm", "send"], seq["commands"][0]


# A cache-cluster manager written for the two tests below: no tuning against it, a domain no other
# measurement used (clusters, node counts, key patterns), and every command shape it exercises also
# appears in the eight measured programs. It exists so that "the document is enough for a new
# program" can be checked rather than asserted. Base64 so the help text, which is mostly quotes,
# needs no escaping here.
LATTICE_PROGRAM = base64.b64decode(
    "IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwoiIiJBIHByb2dyYW0gdGhhdCBoYXMgbmV2ZXIgZXhpc3Rl"
    "ZDogbGF0dGljZSAtLSBhIGNhY2hlLXNlcnZpY2UgbWFuYWdlci4iIiIKaW1wb3J0IHN5cwpQQUdF"
    "UyA9IHsKInJvb3QiOiAiIiJsYXR0aWNlIC0gTGF0dGljZSBDTEkgZm9yIG1hbmFnaW5nIGRpc3Ry"
    "aWJ1dGVkIGNhY2hlIGNsdXN0ZXJzCgpVU0FHRToKICBsYXR0aWNlIDxjb21tYW5kPiBbZmxhZ3Nd"
    "CgpBVkFJTEFCTEUgQ09NTUFORFM6CiAgY2x1c3RlciAgICAgICAgICAgICBNYW5hZ2UgY2x1c3Rl"
    "cgogIGVudHJ5ICAgICAgICAgICAgICAgTWFuYWdlIGNhY2hlIGVudHJ5CgpGTEFHUzoKICAtaCwg"
    "LS1oZWxwICAgICAgICAgIFNob3cgaGVscCBmb3IgYSBjb21tYW5kIiIiLAoKImNsdXN0ZXIiOiAi"
    "IiJNYW5hZ2UgY2x1c3RlcgoKVVNBR0U6CiAgbGF0dGljZSBjbHVzdGVyIDxjb21tYW5kPiBbZmxh"
    "Z3NdCgpBVkFJTEFCTEUgQ09NTUFORFM6CiAgY3JlYXRlICAgICAgICAgICAgICBDcmVhdGUgYSBj"
    "bHVzdGVyCiAgc2NhbGUgICAgICAgICAgICAgICBDaGFuZ2UgdGhlIG5vZGUgY291bnQgb2YgYSBj"
    "bHVzdGVyCiAgaW5zcGVjdCAgICAgICAgICAgICBTaG93IG9uZSBjbHVzdGVyJ3Mgc3RhdHVzCgpG"
    "TEFHUzoKICAtaCwgLS1oZWxwICAgICAgICAgIFNob3cgaGVscCBmb3IgYSBjb21tYW5kIiIiLAoK"
    "ImNsdXN0ZXIgY3JlYXRlIjogIiIiQ3JlYXRlIGEgY2x1c3RlcgoKVVNBR0U6CiAgbGF0dGljZSBj"
    "bHVzdGVyIGNyZWF0ZSBbZmxhZ3NdCgpGTEFHUzoKICAtLW5hbWUgPHN0cmluZz4gKHJlcXVpcmVk"
    "KQlDbHVzdGVyIG5hbWUKICAtLW5vZGVzIDxpbnQ+IChyZXF1aXJlZCkJTnVtYmVyIG9mIG5vZGVz"
    "IHRvIHN0YXJ0CiAgLS1yZWdpb24gPHN0cmluZz4JUmVnaW9uIHRvIHBsYWNlIHRoZSBjbHVzdGVy"
    "IGluCgogIC1oLCAtLWhlbHAJU2hvdyBoZWxwIGZvciB0aGlzIGNvbW1hbmQKCkVYQU1QTEVTOgog"
    "IGxhdHRpY2UgY2x1c3RlciBjcmVhdGUgLS1uYW1lIGVkZ2UtY2FjaGUgLS1ub2RlcyAzIC0tcmVn"
    "aW9uIGV1LXdlc3QtMSIiIiwKCiJjbHVzdGVyIHNjYWxlIjogIiIiQ2hhbmdlIHRoZSBub2RlIGNv"
    "dW50IG9mIGEgY2x1c3RlcgoKVVNBR0U6CiAgbGF0dGljZSBjbHVzdGVyIHNjYWxlIFtmbGFnc10K"
    "CkZMQUdTOgogIC0tbmFtZSA8c3RyaW5nPiAocmVxdWlyZWQpCUNsdXN0ZXIgbmFtZQogIC0tbm9k"
    "ZXMgPGludD4gKHJlcXVpcmVkKQlOZXcgbnVtYmVyIG9mIG5vZGVzCgogIC1oLCAtLWhlbHAJU2hv"
    "dyBoZWxwIGZvciB0aGlzIGNvbW1hbmQKCkVYQU1QTEVTOgogIGxhdHRpY2UgY2x1c3RlciBzY2Fs"
    "ZSAtLW5hbWUgZWRnZS1jYWNoZSAtLW5vZGVzIDYiIiIsCgoiY2x1c3RlciBpbnNwZWN0IjogIiIi"
    "U2hvdyBvbmUgY2x1c3RlcidzIHN0YXR1cwoKVVNBR0U6CiAgbGF0dGljZSBjbHVzdGVyIGluc3Bl"
    "Y3QgW2ZsYWdzXQoKRkxBR1M6CiAgLS1uYW1lIDxzdHJpbmc+IChyZXF1aXJlZCkJQ2x1c3RlciBu"
    "YW1lCgogIC1oLCAtLWhlbHAJU2hvdyBoZWxwIGZvciB0aGlzIGNvbW1hbmQKCkVYQU1QTEVTOgog"
    "IGxhdHRpY2UgY2x1c3RlciBpbnNwZWN0IC0tbmFtZSBlZGdlLWNhY2hlIiIiLAoKImVudHJ5Ijog"
    "IiIiTWFuYWdlIGNhY2hlIGVudHJ5CgpVU0FHRToKICBsYXR0aWNlIGVudHJ5IDxjb21tYW5kPiBb"
    "ZmxhZ3NdCgpBVkFJTEFCTEUgQ09NTUFORFM6CiAgcHVyZ2UgICAgICAgICAgICAgICBEZWxldGUg"
    "ZW50cmllcyBtYXRjaGluZyBhIHBhdHRlcm4KICBsaXN0ICAgICAgICAgICAgICAgIExpc3QgZW50"
    "cmllcyBpbiBhIGNsdXN0ZXIKCkZMQUdTOgogIC1oLCAtLWhlbHAgICAgICAgICAgU2hvdyBoZWxw"
    "IGZvciBhIGNvbW1hbmQiIiIsCgoiZW50cnkgcHVyZ2UiOiAiIiJEZWxldGUgZW50cmllcyBtYXRj"
    "aGluZyBhIHBhdHRlcm4KClVTQUdFOgogIGxhdHRpY2UgZW50cnkgcHVyZ2UgW2ZsYWdzXQoKRkxB"
    "R1M6CiAgLS1jbHVzdGVyIDxzdHJpbmc+IChyZXF1aXJlZCkJQ2x1c3RlciB0byBwdXJnZQogIC0t"
    "cGF0dGVybiA8c3RyaW5nPiAocmVxdWlyZWQpCUtleSBwYXR0ZXJuIHRvIG1hdGNoCgogIC1oLCAt"
    "LWhlbHAJU2hvdyBoZWxwIGZvciB0aGlzIGNvbW1hbmQKCkVYQU1QTEVTOgogIGxhdHRpY2UgZW50"
    "cnkgcHVyZ2UgLS1jbHVzdGVyIGVkZ2UtY2FjaGUgLS1wYXR0ZXJuICdzZXNzaW9uOionIiIiLAoK"
    "ImVudHJ5IGxpc3QiOiAiIiJMaXN0IGVudHJpZXMgaW4gYSBjbHVzdGVyCgpVU0FHRToKICBsYXR0"
    "aWNlIGVudHJ5IGxpc3QgW2ZsYWdzXQoKRkxBR1M6CiAgLS1jbHVzdGVyIDxzdHJpbmc+IChyZXF1"
    "aXJlZCkJQ2x1c3RlciB0byBsaXN0CiAgLS1saW1pdCA8aW50PglNYXhpbXVtIGVudHJpZXMgdG8g"
    "cmV0dXJuCgogIC1oLCAtLWhlbHAJU2hvdyBoZWxwIGZvciB0aGlzIGNvbW1hbmQKCkVYQU1QTEVT"
    "OgogIGxhdHRpY2UgZW50cnkgbGlzdCAtLWNsdXN0ZXIgZWRnZS1jYWNoZSAtLWxpbWl0IDIwIiIi"
    "LAp9CmFyZ3MgPSBbeCBmb3IgeCBpbiBzeXMuYXJndlsxOl0gaWYgeCBub3QgaW4gKCctLWhlbHAn"
    "LCctaCcpXQprZXkgPSAnICcuam9pbihhcmdzKQpzeXMuc3Rkb3V0LndyaXRlKFBBR0VTLmdldChr"
    "ZXkpIG9yIFBBR0VTWydyb290J10pCg=="
).decode()


@pytest.fixture(scope="module")
def lattice(tmp_path_factory):
    path = tmp_path_factory.mktemp("lattice") / "lattice"
    path.write_text(LATTICE_PROGRAM)
    path.chmod(0o755)
    return str(path)


def test_a_flag_the_request_cannot_fill_does_not_cancel_the_flags_it_can(lattice):
    """An unfilled optional flag is omitted; it is not a reason to discard the whole reading.

    `lattice entry list` demonstrates `--cluster <x> --limit 20`. The request "List the entries in
    the cluster session-store" supplies a cluster and nothing for `--limit`, and the planner used
    to throw the demonstration away at that point -- losing the `--cluster session-store` it had
    already bound and falling back to a positional `entry list session-store`. The census still
    reports a *required* flag left empty, so dropping an option cannot hide a contradiction.
    """
    out = R.require_survey_plan(lattice,
                                'List the entries in the cluster "session-store".', probes=20)
    assert out["plans"][0]["argv"][1:] == ["entry", "list", "--cluster", "session-store"], \
        out["plans"][0]["argv"]
    assert not out["plans"][0]["missing_required"], out["plans"][0]["missing_required"]


def test_a_program_that_has_never_existed_is_planned_with_no_new_machinery(lattice):
    """The claim is not "it does well on the bench" but "the document is enough for a new program".

    `lattice` is a cache-cluster manager written for this test: no tuning against it, a domain no
    other measurement used (clusters, node counts, key patterns), and bare numbers, quoted values
    containing `*`, and three required flags in one call. Every shape it exercises already appears
    in the eight programs measured, so this is a test that the *mechanism* is general, not that it
    generalises by memorising.
    """
    cases = [
        ('Create a new cluster named "edge-cache" with 3 nodes in the "eu-west-1" region.',
         ["cluster", "create", "--name", "edge-cache", "--nodes", "3", "--region", "eu-west-1"]),
        ('Scale the cluster "market-cache" to 6 nodes.',
         ["cluster", "scale", "--name", "market-cache", "--nodes", "6"]),
        ('Show the status of the cluster "edge-cache".',
         ["cluster", "inspect", "--name", "edge-cache"]),
        ('Delete all entries in the cluster "edge-cache" matching the pattern "session:*".',
         ["entry", "purge", "--cluster", "edge-cache", "--pattern", "session:*"]),
        ('List the entries in the cluster "session-store".',
         ["entry", "list", "--cluster", "session-store"]),
    ]
    for instruction, want in cases:
        out = R.require_survey_plan(lattice, instruction, probes=20)
        assert out["plans"], instruction
        assert out["plans"][0]["argv"][1:] == want, (instruction, out["plans"][0]["argv"])


# A second program from an unrelated domain, in a help style no measured program uses: GNU
# `--flag=VALUE` spellings, an `Options:` heading, no `USAGE:` line, and `[required]` as a
# trailing marker. Written to test whether the mechanism reads a document or a dialect.
ZONECTL_PROGRAM = base64.b64decode(
    "IyEvdXNyL2Jpbi9lbnYgcHl0aG9uMwoiIiJ6b25lY3RsIC0tIEROUyB6b25lIGFkbWluaXN0cmF0"
    "aW9uLiBEZWxpYmVyYXRlbHkgYSBkaWZmZXJlbnQgaGVscCBzdHlsZToKR05VIGAtLWZsYWc9VkFM"
    "VUVgIHNwZWxsaW5ncywgYE9wdGlvbnM6YCBsb3dlcmNhc2UgaGVhZGluZywgbm8gVVNBR0UgbGlu"
    "ZS4iIiIKaW1wb3J0IHN5cwoKUEFHRVMgPSB7CiIiOiAiIiJ6b25lY3RsIC0gYWRtaW5pc3RlciBE"
    "TlMgem9uZXMKClVzYWdlIHN1bW1hcnkgaXMgaW50ZW50aW9uYWxseSBzdHlsZWQgZGlmZmVyZW50"
    "bHkgZnJvbSBvdGhlciBwcm9ncmFtcy4KCkNvbW1hbmRzCiAgICB6b25lICAgICAgICB3b3JrIHdp"
    "dGggYSB6b25lCiAgICByZWNvcmQgICAgICB3b3JrIHdpdGggYSByZWNvcmQKCk9wdGlvbnM6CiAg"
    "ICAtaCwgLS1oZWxwICBwcmludCBoZWxwCiIiIiwKCiJ6b25lIjogIiIid29yayB3aXRoIGEgem9u"
    "ZQoKQ29tbWFuZHMKICAgIGFkZCAgICAgICAgIGNyZWF0ZSBhIHpvbmUKICAgIGRlbGVnYXRlICAg"
    "IGhhbmQgYSB6b25lIHRvIGFub3RoZXIgbmFtZXNlcnZlcgoKT3B0aW9uczoKICAgIC1oLCAtLWhl"
    "bHAgIHByaW50IGhlbHAKIiIiLAoKInpvbmUgYWRkIjogIiIiY3JlYXRlIGEgem9uZQoKQ3JlYXRl"
    "cyBhIG5ldyBhdXRob3JpdGF0aXZlIHpvbmUuCgpPcHRpb25zOgogICAgLS1vcmlnaW49VEVYVCAg"
    "ICB6b25lIG9yaWdpbiwgZS5nLiBleGFtcGxlLm9yZyAgICAgIFtyZXF1aXJlZF0KICAgIC0tdHRs"
    "PUlOVCAgICAgICAgZGVmYXVsdCBUVEwgaW4gc2Vjb25kcwogICAgLWgsIC0taGVscCAgICAgICBw"
    "cmludCBoZWxwCgpFeGFtcGxlczoKICAgIHpvbmVjdGwgem9uZSBhZGQgLS1vcmlnaW49ZXhhbXBs"
    "ZS5vcmcgLS10dGw9MzYwMAoiIiIsCgoiem9uZSBkZWxlZ2F0ZSI6ICIiImhhbmQgYSB6b25lIHRv"
    "IGFub3RoZXIgbmFtZXNlcnZlcgoKT3B0aW9uczoKICAgIC0tb3JpZ2luPVRFWFQgICAgem9uZSBv"
    "cmlnaW4gICAgICAgICAgICAgICAgICAgICAgICAgW3JlcXVpcmVkXQogICAgLS10bz1URVhUICAg"
    "ICAgICBuYW1lc2VydmVyIHRvIGRlbGVnYXRlIHRvICAgICAgICAgICAgW3JlcXVpcmVkXQogICAg"
    "LWgsIC0taGVscCAgICAgICBwcmludCBoZWxwCgpFeGFtcGxlczoKICAgIHpvbmVjdGwgem9uZSBk"
    "ZWxlZ2F0ZSAtLW9yaWdpbj1leGFtcGxlLm9yZyAtLXRvPW5zMS5leGFtcGxlLm5ldAoiIiIsCgoi"
    "cmVjb3JkIjogIiIid29yayB3aXRoIGEgcmVjb3JkCgpDb21tYW5kcwogICAgYWRkICAgICAgICAg"
    "Y3JlYXRlIGEgcmVjb3JkCiAgICByZW1vdmUgICAgICBkZWxldGUgYSByZWNvcmQKCk9wdGlvbnM6"
    "CiAgICAtaCwgLS1oZWxwICBwcmludCBoZWxwCiIiIiwKCiJyZWNvcmQgYWRkIjogIiIiY3JlYXRl"
    "IGEgcmVjb3JkCgpPcHRpb25zOgogICAgLS1vcmlnaW49VEVYVCAgICB6b25lIHRoZSByZWNvcmQg"
    "bGl2ZXMgaW4gICAgICAgICAgICAgIFtyZXF1aXJlZF0KICAgIC0tbmFtZT1URVhUICAgICAgcmVj"
    "b3JkIGxhYmVsCiAgICAtLXR5cGU9VEVYVCAgICAgIHJlY29yZCB0eXBlLCBvbmUgb2YgQSwgQUFB"
    "QSwgQ05BTUUsIE1YCiAgICAtLXZhbHVlPVRFWFQgICAgIHJlY29yZCBkYXRhICAgICAgICAgICAg"
    "ICAgICAgICAgICAgICAgW3JlcXVpcmVkXQogICAgLWgsIC0taGVscCAgICAgICBwcmludCBoZWxw"
    "CgpFeGFtcGxlczoKICAgIHpvbmVjdGwgcmVjb3JkIGFkZCAtLW9yaWdpbj1leGFtcGxlLm9yZyAt"
    "LW5hbWU9d3d3IC0tdHlwZT1DTkFNRSAtLXZhbHVlPWV4YW1wbGUub3JnCiIiIiwKCiJyZWNvcmQg"
    "cmVtb3ZlIjogIiIiZGVsZXRlIGEgcmVjb3JkCgpPcHRpb25zOgogICAgLS1vcmlnaW49VEVYVCAg"
    "ICB6b25lIHRoZSByZWNvcmQgbGl2ZXMgaW4gICAgICAgICAgICAgIFtyZXF1aXJlZF0KICAgIC0t"
    "bmFtZT1URVhUICAgICAgcmVjb3JkIGxhYmVsICAgICAgICAgICAgICAgICAgICAgICAgICBbcmVx"
    "dWlyZWRdCiAgICAtaCwgLS1oZWxwICAgICAgIHByaW50IGhlbHAKCkV4YW1wbGVzOgogICAgem9u"
    "ZWN0bCByZWNvcmQgcmVtb3ZlIC0tb3JpZ2luPWV4YW1wbGUub3JnIC0tbmFtZT13d3cKIiIiLAp9"
    "CmFyZ3YgPSBbYSBmb3IgYSBpbiBzeXMuYXJndlsxOl0gaWYgYSBub3QgaW4gKCItaCIsICItLWhl"
    "bHAiKV0Ka2V5ID0gIiAiLmpvaW4oYXJndikKc3lzLnN0ZG91dC53cml0ZShQQUdFUy5nZXQoa2V5"
    "LCBQQUdFU1siIl0pKQo="
).decode()


@pytest.fixture(scope="module")
def zonectl(tmp_path_factory):
    path = tmp_path_factory.mktemp("zonectl") / "zonectl"
    path.write_text(ZONECTL_PROGRAM)
    path.chmod(0o755)
    return str(path)


def test_a_documents_choice_list_is_applied_before_any_word_matching(zonectl):
    """The document writes a flag's vocabulary itself, and that is the strongest evidence.

    `zonectl record add` documents `--type` as "record type, one of A, AAAA, CNAME, MX" and the
    request says "of type CNAME". Applied as a pass over every flag first, because the reading
    used to end at the first flag with nothing to take -- which dropped `--value` along with
    any flag after the gap.
    """
    out = R.require_survey_plan(
        zonectl,
        'Add a record "www" of type CNAME with value "example.org" in the zone "example.org".',
        probes=20)
    argv = out["plans"][0]["argv"][1:]
    assert argv[:2] == ["record", "add"], argv
    assert "--type" in argv and argv[argv.index("--type") + 1] == "CNAME", argv
    assert argv[argv.index("--name") + 1] == "www", argv
    assert argv[argv.index("--origin") + 1] == "example.org", argv


def test_a_choice_whose_flag_takes_a_number_is_sent_its_number_not_its_label():
    """`--priority <int>` documents `(0=none, 1=urgent, 2=high, ...)`; the request says "urgent".

    The label is what the request writes and the number is what the flag accepts. Sending the
    word raised inside the program -- cb-006 stopped running entirely -- so the enum is kept as a
    label/value pair and the flag's own documented type decides which spelling goes on the line.
    """
    option = {"flag": "--priority", "meta": "<int>",
              "words": "Priority level (0=none, 1=urgent, 2=high, 3=medium, 4=low)"}
    assert R.slot_kind(option) == "number", R.slot_kind(option)
    assert dict(R.enum_pairs(option))["urgent"] == "1", R.enum_pairs(option)
    assert R.enum_choices(option)[:2] == ["none", "urgent"], R.enum_choices(option)


def test_one_spelling_may_fill_two_slots_when_the_document_and_the_request_both_say_so(zonectl):
    """A value is spent once -- except where both sides independently write it twice.

    `zonectl record add` demonstrates `--origin=example.org --name=www --type=CNAME
    --value=example.org`, because a record's data is very often its own zone, and the request says
    "value example.org in the zone example.org". Two independent statements agreeing on a second
    occurrence is the licence. A document repeating a placeholder is not enough by itself, so both
    sides must show it -- which is why the check is the count in the instruction, not in the demo.
    """
    out = R.require_survey_plan(
        zonectl,
        'Add a record "www" of type CNAME with value "example.org" in the zone "example.org".',
        probes=20)
    argv = out["plans"][0]["argv"][1:]
    assert argv[:2] == ["record", "add"], argv
    got = dict(zip(argv[2::2], argv[3::2]))
    assert got == {"--type": "CNAME", "--origin": "example.org", "--name": "www",
                   "--value": "example.org"}, argv


@pytest.mark.parametrize("instruction,want", [
    ("Create an empty git repository in the directory /tmp/h/repo.",
     ["init", "/tmp/h/repo"]),
    ("Add the file /tmp/h/a.txt to the git staging area.",
     ["add", "/tmp/h/a.txt"]),
    ("Clone the repository https://example.com/x.git into /tmp/h/cl",
     ["clone", "https://example.com/x.git", "/tmp/h/cl"]),
    ("Rename the file /tmp/h/a.txt to /tmp/h/c.txt in the git repository.",
     ["mv", "/tmp/h/a.txt", "/tmp/h/c.txt"]),
])
def test_gits_own_help_is_enough_for_gits_own_commands(instruction, want):
    """Real help text from a program nobody here wrote, on a machine, read as a document.

    Each of these was executed against the real `git` afterwards. Four separate defects in reading
    a document came out of them and each is represented here: `git init -h` writes `[<directory>]`
    on the fifth line of a wrapped usage statement; `git clone` writes one positional bracketed and
    one bare; `[<options>]` appears in every git usage line and is not an operand; and `git mv`
    states its act as "Move or rename", so only checking a summary's *first* act misses the request
    that says "rename".
    """
    out = R.require_survey_plan("git", instruction, probes=24)
    assert out["plans"], instruction
    assert out["plans"][0]["argv"][1:] == want, out["plans"][0]["argv"]


@pytest.mark.parametrize("instruction,want", [
    ("Create an archive file /tmp/h/out.tar containing the files /tmp/h/a.txt and /tmp/h/b.txt.",
     ["-cf", "/tmp/h/out.tar", "/tmp/h/a.txt", "/tmp/h/b.txt"]),
    ("List the contents of the archive /tmp/h/out.tar.", ["-tvf", "/tmp/h/out.tar"]),
    ("Extract all files from the archive /tmp/h/out.tar into the directory /tmp/h/dest.",
     ["-xf", "/tmp/h/out.tar", "/tmp/h/dest"]),
])
def test_one_page_with_a_hundred_and_sixty_options_and_no_command_tree(instruction, want):
    """GNU tar: a single page, 162 option lines, no subcommands, an `Examples:` block.

    Nothing about this shape was designed for, and every command below came from tar's own examples
    and was executed against the real binary.
    """
    out = R.require_survey_plan("tar", instruction, probes=24)
    assert out["plans"], instruction
    assert out["plans"][0]["argv"][1:] == want, out["plans"][0]["argv"]


def test_a_wrapped_usage_statement_is_one_grammar():
    """`git init -h` puts `[<directory>]`, its only positional, on the fifth line."""
    out = R.survey("git", want=[], probes=24)
    init = next(n for n in R.every_page(out)
                if "git init" in str((n.get("usage") or {}).get("usage") or "")[:20])
    picture = R.positional_grammar(init["usage"])
    assert "option" in picture, picture
    assert any("directory" in str(p) for p in picture), picture


def test_a_structured_argument_is_filled_from_prose_inside_the_documents_own_shape():
    """The hardest binding there is: one argument that is a JSON object, values stated in prose.

    `datapipe source connect --config` documents itself as `Connection configuration as JSON
    (e.g. {"host": ..., "port": 5432, "database": "analytics"})`, and the request states a host, a
    port and a database as an English list. The document supplies the *structure* and the request
    supplies every value -- nothing here is invented, and the keys are the document's.
    """
    request = ('Using the datapipe tool, register a new PostgreSQL data source named "analytics-db" '
               'with the connection config: host "db.analytics.internal", port 5432, '
               'database "analytics".')
    out = R.require_survey_plan(str(CB_BIN / "datapipe"), request, probes=14)
    argv = out["plans"][0]["argv"][1:]
    assert argv[:2] == ["source", "connect"], argv
    config = argv[argv.index("--config") + 1]
    assert '"host": "db.analytics.internal"' in config, config
    assert '"port": 5432' in config, config
    assert '"database": "analytics"' in config, config
    assert argv[argv.index("--name") + 1] == "analytics-db", argv
    # the flag documents its vocabulary as `postgres, mysql, s3, ...` and the request names the
    # choice by its full name; the document's spelling is what the flag accepts
    assert argv[argv.index("--type") + 1] == "postgres", argv


def test_completeness_and_coverage_are_two_different_statements():
    """`complete` says the command meets its own page's requirements; `covered` says every object
    the request named reached the line. They fail differently and both are reported.

    Measured over the sixty: complete-and-covered n=41 mean 0.5131, the rest n=16 mean 0.4076 --
    +0.106 with no reward and no answer key. `complete` alone certifies 54 of 57 and so separates
    almost nothing, which is why the second statement earns its place.
    """
    out = R.require_survey_plan(
        str(CB_BIN / "meshctl"),
        'Using the meshctl tool, configure a canary deployment for "user-service": '
        'Route 90% of traffic to v1 and 10% to v2.', probes=14)
    candidate = out["plans"][0]
    assert candidate["complete"] is True
    assert candidate["covered"] is True
    assert candidate["values_unplaced"] == []

    # cb-016's shape: a request naming an object this command has no place for is covered=False
    # and *says which object* -- the report is the point, not just the flag
    dropped = R.require_survey_plan(
        str(CB_BIN / "jira"),
        """Create a new Jira issue in the "INFRA" project with summary "Set up
centralized log aggregation with Loki", type "Task", priority "High",
and assign it to "ops-bob".
""",
        probes=14)
    assert dropped["plans"], dropped.get("reason")
    assert dropped["plans"][0]["covered"] is False
    assert "ops-bob" in dropped["plans"][0]["values_unplaced"], dropped["plans"][0]


def test_an_ordinal_that_opens_a_clause_is_not_a_count():
    """Never invent a value. The first law, and a mechanism broke it silently.

    `First, list available artifacts to find the most recent successful build` contains no number.
    The extractor read `First` as the ordinal `1`, and that `1` was seated in a required flag:

        kforge artifact list --namespace 1

    An invented value looks exactly like an extracted one, which is what made this dangerous. The
    rule that distinguishes them is local: a clause-opening ordinal is followed by a comma, or
    stands at the start of the text. `the first 5 files` is not a clause opener and still counts.
    """
    opener = R.require("First, list available artifacts to find the most recent build.")
    assert opener["values"] == [], opener["values"]

    opener_no_comma = R.require("First list the files in the directory.")
    assert opener_no_comma["values"] == [], opener_no_comma["values"]

    counted = R.require("Delete the first 5 files in the directory.")
    assert [v["value"] for v in counted["values"]] == ["5"], counted["values"]

    # and the task that exposed it no longer manufactures a namespace
    plan = R.require_survey_plan_sequence(
        str(CB_BIN / "kforge"),
        'Using the kforge CLI, deploy the latest build artifact for the "web-platform" service to'
        ' the staging environment. First, list available artifacts to find the most recent'
        ' successful build. Then trigger a deployment pipeline for staging using that artifact.',
        probes=14)
    joined = " ".join(" ".join(c) for c in plan["commands"])
    assert "--namespace 1" not in joined, joined


def test_a_second_value_of_one_field_repeats_its_flag():
    """A demonstration shows a flag once; a request may name several values for it.

    `have the label "priority:critical" or "priority:high"` names two labels while the example
    shows `--label bug` once. The second value then trailed the command as a bare operand, where
    the program reads it as a positional and refuses. Repeating the flag is the idiom every
    list-valued option uses, and it invents nothing -- the flag is on the page and each value is in
    the request.

    The two limits are measured, not guessed: a *path* never repeats (tar's `--catenate` is
    described with the word "files", and repeating a path there turned a correct
    `tar -cf out.tar a.txt b.txt` into `-cf out.tar --catenate a.txt`), and a flag the
    demonstration fills with a *structure* never repeats (it came out as the same JSON argument
    written four times wrong).
    """
    plan = R.require_survey_plan_sequence(
        str(CB_BIN / "gh"),
        'Find all open GitHub issues in "acme-corp/web-platform" that have the label'
        ' "priority:critical" or "priority:high".',
        probes=14)
    argv = plan["commands"][0]
    assert argv.count("--label") == 2, argv
    assert "priority:critical" in argv and "priority:high" in argv, argv
    assert argv.count("--repo") == 1, argv

    # a coordinated value inherits the naming words of the value it is coordinated with
    req = R.require('have the label "priority:critical" or "priority:high"')
    assert len(req["values"]) == 2
    assert "label" in R.words_of(req["values"][1]["context"]) | set(
        req["values"][1]["words"]), req["values"][1]


def test_a_request_that_states_a_structure_names_that_argument():
    """The document's example and the request can carry the *same* structure.

    `datapipe sink create --help` demonstrates

        --config '{"bucket": "analytics-output", "prefix": "daily/"}'

    and the request says `with config {"bucket": "analytics-output", "prefix": "daily/"}`. The
    extractor had also found `bucket`, `analytics-output`, `prefix`, `daily/` as four separate
    literals, and because every shape token looked "already used" the shape contributed nothing:

        sink create --name analytics-lake --type S3 bucket analytics-output prefix daily/

    The JSON then trailed the command as four operands. A request that spells out every key of the
    shape has named that argument; emitting it supplies nothing the request did not state.
    """
    plan = R.require_survey_plan_sequence(
        str(CB_BIN / "datapipe"),
        'Using the datapipe tool, build a data pipeline:'
        ' 1. Create an S3 sink named "analytics-lake" with config'
        ' {"bucket": "analytics-output", "prefix": "daily/"}.',
        probes=14)
    argv = plan["commands"][0]
    assert "--config" in argv, argv
    config = argv[argv.index("--config") + 1]
    assert config.startswith("{") and '"bucket"' in config and '"prefix"' in config, argv
    # every stray literal is inside the JSON, not trailing beside it
    assert "bucket" not in argv, argv
    assert "daily/" not in argv, argv


def test_a_bracketed_required_marker_is_read_like_a_parenthesised_one():
    """Two spellings of the same statement, and only one was read.

    `zonectl record remove --help` writes its options as

        --origin=TEXT    zone the record lives in              [required]
        --name=TEXT      record label                          [required]

    The parser matched `(required)` where a description begins and had no rule for `[required]`
    where one ends, so both flags came back `required: None` and a command missing `--name` was
    reported `complete: True`. **The verifier lying is worse than the command being wrong**: a
    caller who trusts `complete` ships a malformed command with a certificate.

    The marker is the document's own word in either position, and reading it is not an inference.
    """
    # A request that names only the zone cannot form the command: `--name` is required and the
    # request supplies no label, so the best plan must say so rather than certify it.
    partial = R.require_survey_plan(
        str(CB_BIN3 / "zonectl"),
        'Remove the record from the zone example.org', probes=14)
    first = partial["plans"][0]
    assert first["complete"] is False, first
    assert "--name" in first["missing_required"], first

    # and the flags themselves are known to be required
    import subprocess
    page = subprocess.run([str(CB_BIN3 / "zonectl"), "record", "remove", "--help"],
                          capture_output=True, text=True).stdout
    options = {o["flag"]: o for o in R.parse_options(page)}
    assert options["--name"]["required"] is True, options["--name"]
    assert options["--origin"]["required"] is True, options["--origin"]
    # the marker is not part of the description
    assert "required" not in str(options["--name"]["words"]).lower(), options["--name"]


def test_a_bare_word_the_example_also_writes_is_that_flags_value():
    """The strongest licence a document can offer, and it costs no inference.

    `zonectl record remove --help` demonstrates `--origin=example.org --name=www`, and the request
    says "Remove the record www from the zone example.org". `www` is neither quoted, nor a path, nor
    a number, so the extractor never saw it; `--name` stayed empty and a *required* flag was left
    off the command.

    The licence is not "a bare word might be a value" -- that would invent values everywhere. It is
    that the request and the document's own example write the same word, and the example states
    which flag takes it. Nothing is inferred from the word's shape or meaning; both statements are
    on the page and in the request already.
    """
    out = R.require_survey_plan(
        str(CB_BIN3 / "zonectl"),
        'Remove the record www from the zone example.org', probes=14)
    argv = out["plans"][0]["argv"]
    assert "--name" in argv, argv
    assert argv[argv.index("--name") + 1] == "www", argv
    assert "--origin" in argv and argv[argv.index("--origin") + 1] == "example.org", argv
    assert out["plans"][0]["complete"] is True, out["plans"][0]





# A pipeline program in the dialect the measured bench uses (`USAGE:` / `FLAGS:`, `(required)`),
# so this test exercises the same reading path rather than a convenience format the planner never
# meets in the field. The pages live in base64 for the same reason ZONECTL_PROGRAM's do: the
# program's own quoting must not have to survive the test file's.
PIPELINE_PAGES = {
    "": """pipelinectl - build data pipelines

USAGE:
  pipelinectl <command> [flags]

AVAILABLE COMMANDS:
  sink                Manage sink
  transform           Manage transform
  pipeline            Manage pipeline
""",
    "sink": """Manage sink

USAGE:
  pipelinectl sink <command> [flags]

AVAILABLE COMMANDS:
  create              Create a sink
""",
    "sink create": """Create a sink

USAGE:
  pipelinectl sink create [flags]

FLAGS:
  --name <string> (required)\tSink name (unique identifier)
  --type <enum> (required)\tSink type (values: s3, bigquery, postgres)
  --config <json> (required)\tSink configuration as JSON

EXAMPLES:
  pipelinectl sink create --name analytics-lake --type s3 --config '{"bucket": "out", "prefix": "daily/"}'
""",
    "transform": """Manage transform

USAGE:
  pipelinectl transform <command> [flags]

AVAILABLE COMMANDS:
  create              Create a transform
""",
    "transform create": """Create a transform

USAGE:
  pipelinectl transform create [flags]

FLAGS:
  --name <string> (required)\tTransform name (unique identifier)
  --sql <string> (required)\tSQL transformation query
  --source <string> (required)\tSource name to read data from

EXAMPLES:
  pipelinectl transform create --name daily-revenue --sql 'SELECT 1' --source prod-db
""",
    "pipeline": """Manage pipeline

USAGE:
  pipelinectl pipeline <command> [flags]

AVAILABLE COMMANDS:
  create              Create a pipeline
""",
    "pipeline create": """Create a pipeline

USAGE:
  pipelinectl pipeline create [flags]

FLAGS:
  --name <string> (required)\tPipeline name (unique identifier)
  --source <string> (required)\tSource name
  --transforms <string> (required)\tComma-separated list of transform names
  --sink <string> (required)\tSink name
  --schedule <string> (required)\tCron expression
""",
}


def _pipeline_program() -> str:
    pages = "".join(f"    {json.dumps(k)}: {json.dumps(v)},\n" for k, v in PIPELINE_PAGES.items())
    return (
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "PAGES = {\n" + pages + "}\n"
        "args = [x for x in sys.argv[1:] if x not in ('--help', '-h')]\n"
        "print(PAGES.get(' '.join(args)) or PAGES.get(args[0] if args else '', PAGES['']))\n"
    )


@pytest.fixture(scope="module")
def pipelinectl(tmp_path_factory):
    path = tmp_path_factory.mktemp("pipelinectl") / "pipelinectl"
    path.write_text(_pipeline_program())
    path.chmod(0o755)
    return str(path)


def test_the_verdict_is_for_the_whole_plan_not_its_first_command(pipelinectl):
    """The verdict is the conjunction over the commands, not a copy of the first one's.

    Measured over the sixty, judging every command separates good plans from bad at AUC 0.740
    (0.5096 vs 0.3677) where the single-command `complete` -- true for 57 of 60 -- gives 0.599.
    Both are reported; `satisfies_every_page` is the one worth reading.

    Asserted by construction rather than by expecting a particular reading: whatever commands
    were planned, the verdict is False exactly when some command cannot name a required flag,
    and every failing command is named with what it could not supply.
    """
    asked = (
        "Build a complete data pipeline:\n"
        '1. Create a transform named "daily-revenue" with SQL "SELECT 1" using source "prod-db".\n'
        '2. Create an S3 sink named "analytics-lake" with config {"bucket": "out", "prefix": "daily/"}.\n'
        '3. Create a pipeline named "daily-etl" with a schedule of "0 2 * * *".\n'
    )
    out = R.require_survey_plan_sequence(pipelinectl, asked, probes=12)
    assert out["commands"], "the request did produce commands"

    flagged = [s for s in out["steps"] if s.get("argv")]
    assert flagged, "steps carry their commands"
    any_missing = any((s.get("alternatives") or [{}])[0].get("missing_required") for s in flagged)

    # the verdict is the conjunction over the commands
    assert out["satisfies_every_page"] is (not any_missing)
    assert out["unsatisfied"] != [] if any_missing else out["unsatisfied"] == []
    for gap in out["unsatisfied"]:
        assert gap["missing"] and gap["command"], "a failing command is named with its gap"
    # a command that satisfies its page is never reported as failing
    for step in flagged:
        alt = (step.get("alternatives") or [{}])[0]
        if not alt.get("missing_required"):
            assert " ".join(step["argv"]) not in {g["command"] for g in out["unsatisfied"]}


ISSUECTL_PAGES = {
    "": """issuectl - track issues in a repository

USAGE:
  issuectl <command> [flags]

AVAILABLE COMMANDS:
  issue               Manage issue
""",
    "issue": """Manage issue

USAGE:
  issuectl issue <command> [flags]

AVAILABLE COMMANDS:
  create              Create a new issue in a repository
""",
    "issue create": """Create a new issue in a repository

USAGE:
  issuectl issue create [flags]

FLAGS:
  --repo <string> (required)\tRepository in owner/repo format
  --title <string> (required)\tIssue title
  --body <string>\tIssue body text
  --label <string>\tLabel to apply (can be repeated)

EXAMPLES:
  issuectl issue create --repo owner/repo --title 'Bug report' --body 'Details here'
""",
}


@pytest.fixture(scope="module")
def issuectl(tmp_path_factory):
    pages = "".join(f"    {json.dumps(k)}: {json.dumps(v)},\n" for k, v in ISSUECTL_PAGES.items())
    program = (
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "PAGES = {\n" + pages + "}\n"
        "args = [x for x in sys.argv[1:] if x not in ('--help', '-h')]\n"
        "print(PAGES.get(' '.join(args)) or PAGES.get(args[0] if args else '', PAGES['']))\n"
    )
    path = tmp_path_factory.mktemp("issuectl") / "issuectl"
    path.write_text(program)
    path.chmod(0o755)
    return str(path)


def test_prose_the_request_labels_with_an_option_name_becomes_that_option(issuectl):
    """`... with a body that describes the need to prevent abuse` binds --body.

    The request names the option and then says what goes in it, in a clause rather than a quote.
    The clause is prose, so it stayed in `unclaimed` and `--body` was dropped from a command the
    page says takes one -- the issue was created with no body at all (cb-002, outcome 0.000).
    """
    asked = ('Create a new issue in the repository "acme-corp/web-platform" with the title '
             '"Add rate limiting to public API endpoints" and a body that describes the need '
             'to prevent abuse on unauthenticated routes.')
    out = R.require_survey_plan(issuectl, asked, probes=12)
    argv = out["plans"][0]["argv"]
    assert "--body" in argv, argv
    body = argv[argv.index("--body") + 1]
    # what goes in the body is the clause the request wrote after the name, and no more
    assert body.startswith("that describes the need"), body
    assert "prevent abuse" in body, body
    assert "unauthenticated" in body, body
    # and the title is still exactly the quoted one
    assert argv[argv.index("--title") + 1].startswith("Add rate limiting"), argv


def test_a_field_list_after_an_option_name_is_not_its_content(pipelinectl):
    """`Show the project name, status, lead, and target date` names fields, not a value.

    Binding that list as a value turned the display sentence into a command made of its own
    field names (`linear project lead, and target date`), which ran nothing and cost cb-009
    0.20 and cb-013 0.10. A comma list is a form; a clause is prose.
    """
    asked = ("List all projects in the workspace. Show the project name, status, lead, and "
             "target date for each project.")
    out = R.require_survey_plan(pipelinectl, asked, probes=12)
    for plan in out["plans"][:3]:
        argv = " ".join(plan["argv"])
        assert "target date" not in argv, argv
        assert "lead," not in argv, argv


def test_a_value_the_page_has_no_slot_for_is_reported_rather_than_forced_into_one():
    """A value's label is the request saying what kind of thing it is.

    `issue list` documents `--team` and `--project`; it has no `--title`. A request that names a
    project, a team *and* a title therefore states something this page cannot carry. The reading
    that puts the title in `--assignee` is not "the best available slot" -- it silently changes the
    request's meaning to "filter by an assigned person called Fix login", and reports complete.

    The correct reading places what the page documents and reports the rest by its own word.
    """
    out = R.require_survey_plan(
        str(CB_BIN / "linear"),
        'Add an issue to the project "Engineering" for the team "Platform" titled "Fix login".',
        probes=16)
    assert out["plans"], out.get("reason")
    # No reading may put the title in a flag that means a person or a project.
    for candidate in out["plans"]:
        argv = candidate["argv"]
        assert "--assignee" not in argv, f"a title was read as a person: {argv}"
        if "Fix login" in argv:
            assert argv[argv.index("Fix login") - 1] == "--title", argv
    # At least one reading places both labelled values the page does document.
    assert any("Engineering" in p["argv"] and "Platform" in p["argv"] for p in out["plans"]), \
        [p["argv"] for p in out["plans"]]
    # And the value with no home is reported by its own word rather than silently dropped --
    # in whichever of the two fields the plan carries it: `unbound` (a slot was wanted and refused)
    # or `values_unplaced` (the reading never found a slot to want).
    reported = [p for p in out["plans"]
                for item in (p.get("unbound") or []) + (p.get("values_unplaced") or [])
                if "Fix login" in str(item.get("value") if isinstance(item, dict) else item)]
    assert reported, "the unplaceable value must be reported, not silently dropped"


def test_a_labelled_value_lands_in_the_flag_that_names_it_not_the_first_free_one():
    """`--team` is declared first; the request says "the **title**".

    Binding by declaration order puts whatever comes first in the document into whichever value
    comes first in the request. The page prints the word that decides it.
    """
    out = R.require_survey_plan(
        str(CB_BIN / "linear"),
        'Create an issue titled "Fix login" in the team "Platform".', probes=16)
    argv = out["plans"][0]["argv"]
    assert argv[argv.index("--title") + 1] == "Fix login", argv
    assert argv[argv.index("--team") + 1] == "Platform", argv


def test_complete_means_the_request_was_answered_not_merely_runnable():
    """A plan that discards part of the request is not an answer, however well it runs.

    `Add an issue to the project "Engineering" for the team "Platform" titled "Fix login"` has no
    single reading here: `issue list` houses the project and the team but has no `--title`, and
    `issue create` houses the title but documents no `--project`. The reading offered is
    `issue list --team Platform`, which reports `complete` at both levels and quietly drops two of
    the three values -- a caller reading only the top flag would run it and believe the request
    was carried out.

    The plans stay: a partial reading is a real next step. What must not stand is the claim.
    """
    out = R.require_survey_plan(
        str(CB_BIN / "linear"),
        'Add an issue to the project "Engineering" for the team "Platform" titled "Fix login".',
        probes=16)
    assert out["plans"], out.get("reason")
    assert out["complete"] is False, "a reading that discards the request must not claim completeness"
    reasons = [r["reason"] for r in out["refusals"]]
    assert "NO_SINGLE_READING_ACCOUNTS_FOR_THE_WHOLE_REQUEST" in reasons, reasons

    # The same shape where the program does have one command for it stays complete.
    ok = R.require_survey_plan(
        str(CB_BIN / "linear"),
        'Create an issue titled "Fix login" in the team "Platform".', probes=16)
    assert ok["complete"] is True, ok.get("refusals")


def test_a_program_with_no_command_for_the_act_says_so_instead_of_improvising():
    """"This program has no command for that" is an answer, and it is decidable without a weight.

    `/usr/bin/tar` has no copy operation. A request to copy one file to another has no reading in
    its help -- the old behaviour planned `tar --block-number /tmp/b.txt /tmp/a.txt`, which has both
    paths in it and means something else entirely, and called it complete because every value
    appeared somewhere in the argument list.

    The test uses the real program, because that is where the failure was found: `tar`'s help is
    a dense wall of option prose, and copying is never stated as an operation. The word appears
    once, inside `-u, --update  only append files newer than copy in archive`.

    The same program's real operations must still plan, so the rule cannot be "refuse when the help
    is hard to read".
    """
    import shutil
    if shutil.which("tar") is None:
        import pytest
        pytest.skip("no tar on this host")

    missing = R.require_survey_plan(
        "tar", "Copy /tmp/a.txt to /tmp/b.txt.", probes=10)
    assert missing["complete"] is False, missing["plans"][:1]
    assert "NO_COMMAND_OF_THIS_PROGRAM_IS_ABOUT_THE_REQUEST" in [
        r["reason"] for r in missing["refusals"]], missing["refusals"]

    for request in ("Create a gzipped archive named backup.tgz from the directory /tmp/data.",
                    "Extract the archive backup.tgz into /tmp/out.",
                    "List the contents of the archive backup.tgz."):
        plan = R.require_survey_plan("tar", request, probes=10)
        assert plan["complete"] is True, (request, plan["refusals"])
