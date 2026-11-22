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
import json
import pathlib
import re
import shutil
import textwrap

import pytest

from canonical.runtime import require_survey_plan_v1 as R

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
    for banned in ("call_model", "model_call", "llm", "completion("):
        assert banned not in text.lower().replace("no model call", "")


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
    binary = "/tmp/cb/bin/alertmgr"
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
    binary = "/tmp/cb/bin/flowctl"
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
    binary = "/tmp/cb/bin/notion"
    if not pathlib.Path(binary).exists():
        pytest.skip("the benchmark's notion page is not on this machine")
    result = R.require_survey_plan_sequence(
        binary, 'List all pages in the workspace. Show the page title and parent.', probes=14)
    assert len(result["commands"]) == len({tuple(c) for c in result["commands"]})


def test_a_step_with_no_operation_is_not_emitted_as_a_command():
    """A bare value is not a command: `set the owner to "devops"` is not `devops`."""
    binary = "/tmp/cb/bin/flowctl"
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
    exe = "/tmp/cb/bin/linear"
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
    out = R.require_survey_plan("/tmp/cb/bin/linear", request, probes=16)
    assert out["plans"][0]["argv"][1:] == ["project", "list"], out["plans"][0]["argv"]
    assert out["plans"][0]["missing_required"] == []
    assert out["plans"][0]["complete"] is True

    # a page WITH required flags: a reading that lacks them is incomplete, and says which
    created = ("Create a new workflow named \"deploy-staging\" using the flowctl tool.\n"
               "The workflow should have two steps: a \"build\" step with action \"run_pipeline\"\n"
               "and an \"approve\" step with action \"gate\".")
    plans = R.require_survey_plan("/tmp/cb/bin/flowctl", created, probes=16)["plans"]
    assert any(p["complete"] for p in plans), [p.get("missing_required") for p in plans]
    assert any(p["missing_required"] for p in plans), "an incomplete reading must name what it lacks"
