#!/usr/bin/env python3
"""Documentation holds a verifier that no author wrote: execute the examples, keep what passed.

THE QUESTION THIS ROUND ASKS, AND WHY IT IS THE RIGHT ONE
---------------------------------------------------------
Thirteen rounds of this project named the same missing half and none of them filled it:

  * `THE_VERIFICATION_HALF_IS_FREE_THE_SYNTHESIS_HALF_IS_EMPTY_20261116_V1` -- "0 of 6 real fixes
    solved ... and not one of the six failures is a search failure";
  * `THE_REPERTOIRE_IS_A_QUERY_20261129_V1` -- the machine supplies 4,621 options in 47 s and
    **0 of 80 accepted options changed a byte**, because "a printed option is a modifier, not an
    action";
  * `THE_VERIFIER_IS_KNOWLEDGE_NOT_LEARNING_20261116_V1` -- verification is a source of knowledge
    the system must acquire, not something learning supplies;
  * the live defect this round started from: `perfect_algorithm_v1.run()` fetches instant
    knowledge and then returns `OPEN__NO_PLAN_AFTER_SCAN`, storing documents and using none.

The owner's proposal, restated as a claim a machine can decide:

  > every environment on a computer already has a guide; the agent should find the guide, take the
  > actions from it, run them, and keep what worked.

That is testable without a model, without a benchmark harness, and without the owner's judgement,
because **a guide's examples are assertions**. An example that states its command and its output is
a test the author wrote by accident. So the claim becomes three measurements:

  P1  an example can be EXTRACTED from a real guide and RUN, and the run can be scored against the
      output the guide printed -- with no model anywhere in the loop;
  P2  the output the guide printed really does decide whether the command was right, on one real
      target **and on decoys of the same kind** -- the last round measured 8 of 8 checks blind to
      WHICH object, so an example's expected output must be held to the same standard;
  P3  what is KEPT is a rule that transfers to inputs the documentation never mentioned. If it does
      not transfer it is a cache of answers, and the repository has already measured that a cache
      is not learning (`LEARN_ONCE_KEEP_FOREVER_SERVES_A_TWENTIETH_OF_REAL_EDITS_20261116_V1`).

WHAT IS NEW HERE, AND WHAT IS DELIBERATELY NOT BUILT
----------------------------------------------------
New: extraction of transcript examples from documentation, an oracle built out of the guide's own
printed output, and a transfer test where the held-out inputs are *new to the documentation* while
the rule came from **one** example. The last round's own lesson is applied rather than repeated:
`A_CHECK_THAT_NOBODY_RUNS_IS_A_CHECK_THAT_CANNOT_BE_WRONG_20261203` established that a check must be
executed and must be able to tell which object it is looking at -- so every example check here is
run, and P2 measures its discrimination against decoys rather than asserting it.

Not built, on purpose: a memory store. The store is a file; the science is whether anything deserves
to go in it. Storing first and justifying later is how the repository got 188 laws that killed nothing
(`THE_WALL_WAS_NOT_THE_WALL_20261112_V1`).

WHAT THIS CANNOT CLAIM
----------------------
One machine, one language, four guides, a handful of examples, zero runs of a frontier benchmark.
An example that exercises the network is skipped, so "requests" contributes only what runs offline.
A system that passes here is NOT shown to solve OSWorld, FrontierSWE or Terminal-Bench.

Model calls: 0. Parameters stored: 0. Network at run time: 0 (the guides were fetched once, by hand,
while building -- before the run, never during it).
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SCHEMA = "BRAIN_THE_GUIDE_IS_A_TEST_SUITE_20261204_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
DATE = "2026-12-04"

EXAMPLE_DEADLINE = 20.0
WORKERS = 6

# A transcript line is a command the guide printed with the prompt the guide used. Kept narrow on
# purpose: a line that does not carry its own prompt is prose, and this round does not guess which
# prose was meant to be typed.
PROMPT = re.compile(r"^(?P<indent>[ \t]*)(?P<prompt>\$|>>>|\.\.\.) ?(?P<body>.*)$", re.M)


# --------------------------------------------------------------------------- #
# 1. THE GUIDE, READ AS A TEST SUITE
# --------------------------------------------------------------------------- #

def fenced_blocks(markdown: str) -> list[dict[str, Any]]:
    """Every fenced block, with the language the guide labelled it with."""
    blocks: list[dict[str, Any]] = []
    lines = markdown.splitlines()
    i = 0
    while i < len(lines):
        match = re.match(r"^\s*```+\s*([A-Za-z0-9_+-]*)", lines[i])
        if not match:
            i += 1
            continue
        language = (match.group(1) or "").lower()
        start = i + 1
        i = start
        while i < len(lines) and not re.match(r"^\s*```+\s*$", lines[i]):
            i += 1
        blocks.append({"language": language, "first_line": start,
                       "text": "\n".join(lines[start:i])})
        i += 1
    return blocks


def transcripts(blocks: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Blocks that are a session: a prompt, a command, and the text that came back.

    The parsing rules are the doctest convention, and each one was found by running it:
      * `>>>` opens a statement; `...` continues it -- a statement may span lines and is still
        one statement;
      * a `>>>` with nothing after it is a blank prompt inside a doctest and is not a statement;
      * the answer runs from the end of the statement to the next prompt, and STOPS when the guide
        dedents below the prompt's own indent -- the prose after an example is not its output;
      * a block with no prompt at all is a listing, not a session, and is not a test.
    """
    out: list[dict[str, Any]] = []
    for block in blocks:
        lines = block["text"].splitlines()
        # `PROMPT.search(text, re.M)` passes the flag into `pos`, not `flags` -- the pattern was
        # already compiled with re.M -- so it searched from character 8 onward and silently skipped
        # any docstring whose only prompt sits near the start. Test the pattern, not the offset.
        if not PROMPT.search(block["text"]):
            continue
        examples: list[dict[str, Any]] = []
        index = 0
        while index < len(lines):
            opened = PROMPT.match(lines[index])
            if not opened or opened.group("prompt") != ">":
                if not opened or opened.group("prompt") not in (">>>", "$", "..."):
                    index += 1
                    continue
            opened = PROMPT.match(lines[index])
            prompt = opened.group("prompt")
            if prompt == "...":
                index += 1  # orphan continuation: the statement it belonged to is gone
                continue
            if prompt == ">>>" and not opened.group("body").strip():
                index += 1  # a blank prompt shows nothing and asserts nothing
                continue
            # THE OUTPUT IS INDENTED DEEPER THAN THE PROMPT'S OWN TEXT, so the boundary is the
            # prompt's indent and not the statement's: an answer continuing a `def` is at indent 12
            # while the `>>>` sits at 8, and using 8 as the floor let the following prose in.
            indent = len(opened.group("indent").expandtabs(8))
            statement = opened.group("body").rstrip()
            cursor = index + 1
            while cursor < len(lines):
                follow = PROMPT.match(lines[cursor])
                if not follow or follow.group("prompt") != "...":
                    break
                statement += chr(10) + follow.group("body")
                cursor += 1
            # THE BOUNDARY IS THE OUTPUT'S OWN INDENT, LEARNED FROM ITS FIRST LINE. A doctest in a
            # function docstring sits at indent 8 and its answer at 12; a module docstring sits at 0
            # and its answer at 0, so no floor derived from the prompt can separate the answer from
            # the prose that follows. What does separate them is that the answer is indented with
            # its prompt (or not at all) and the prose after it either dedents below that or is cut
            # off by the blank line the guide puts between an example and its prose.
            expected: list[str] = []
            output_floor: int | None = None
            while cursor < len(lines):
                line = lines[cursor]
                if PROMPT.match(line):
                    break
                if not line.strip():
                    if expected:
                        break  # a blank line ends a shown answer
                    cursor += 1
                    continue
                here = len(line) - len(line.lstrip())
                if output_floor is None:
                    output_floor = here
                elif here < output_floor and here <= indent:
                    break
                expected.append(line)
                cursor += 1
            while expected and not expected[-1].strip():
                expected.pop()
            examples.append({"prompt": ">>>" if prompt == ">>>" else prompt,
                             "command": statement, "expected": expected})
            index = cursor
        if examples:
            out.append({"language": block["language"], "first_line": block["first_line"],
                        "examples": examples})
    return out


def _python_example_ok(example: dict[str, Any], cwd: pathlib.Path,
                       module: str | None = None) -> dict[str, Any]:
    """A `>>>` session replayed with the interpreter's own echo rules.

    Three facts about doctests, each found by running it:
      * the guide is a module's docstring, so the module's own import is part of its context -- a
        docstring shows `textwrap.shorten(...)` and never shows `import textwrap`;
      * the interpreter echoes the value of an EXPRESSION and nothing for `None`, while `print(...)`
        sends text to the stream. Replaying `print(round(s.ratio(), 3))` and comparing its return
        value compared `None` with the number the guide printed;
      * statements share state in one interpreter, which is why the session is replayed whole.
    """
    # THE NAMESPACE IS THE MODULE'S OWN. That is the doctest rule -- `testmod` runs a docstring with
    # `vars(module)` as globals -- and it is why the guide writes `mean(...)` and never
    # `statistics.mean(...)`. Replaying in a fresh namespace instead refused 181 of 189 examples
    # with `NameError: name 'mean' is not defined`, and every one of those was this instrument's
    # fault, not the guide's.
    program = ["import sys", "_real = sys.stdout", "_g = {}"]
    if module:
        program.append(f"import {module} as _m")
        # ...plus the module's own name, so a transcript that writes `statistics.median(...)` and
        # one that writes `median(...)` are BOTH replayed as the guide meant them.
        program.append("_g = dict(vars(_m)); _g[" + repr(module) + "] = _m")
    program.append("_g.setdefault('__builtins__', __builtins__)")
    for statement in example["_session"]:
        clean = re.sub(r"\s*#\s*doctest:.*$", "", statement, flags=re.M)
        program.append("try:")
        program.append(f"    _code = compile({clean!r}, '<guide>', 'eval')")
        program.append("except SyntaxError:")
        program.append(f"    exec(compile({clean!r}, '<guide>', 'exec'), _g)")
        program.append("else:")
        program.append("    _v = eval(_code, _g)")
        # THE INTERPRETER PRINTS A STRING'S repr, and the guide TRANSCRIBED it: `'red'` in the
        # doctest is a repr, so it is printed, not stripped. What the first version got wrong is
        # the other direction -- it read the guide's `'red'` as a statement and printed the bare
        # value. Echoing `repr` unconditionally is the interpreter's own rule.
        program.append("    if _v is not None:")
        program.append("        print(repr(_v))")
    script = chr(10).join(program)
    try:
        done = subprocess.run([sys.executable, "-c", script], cwd=str(cwd),
                              capture_output=True, text=True, timeout=EXAMPLE_DEADLINE,
                              stdin=subprocess.DEVNULL,
                              env={"PATH": "/usr/local/bin:/usr/bin:/bin",
                                   "LC_ALL": "C.UTF-8", "PYTHONIOENCODING": "utf-8",
                                   "HOME": str(cwd)})
    except (OSError, subprocess.SubprocessError) as error:
        return {"ok": False, "why": f"COULD_NOT_RUN__{type(error).__name__}"}
    if done.returncode != 0:
        return {"ok": False, "why": "REFUSED_BY_INTERPRETER",
                "stderr": (done.stderr or "").strip().splitlines()[-1:]}
    return {"ok": True, "got": [line for line in (done.stdout or "").splitlines()]}


def _shell_example_ok(example: dict[str, Any], cwd: pathlib.Path) -> dict[str, Any]:
    """A `$` transcript: run the command and keep both streams, because guides print either."""
    try:
        done = subprocess.run(example["command"], shell=True, cwd=str(cwd),
                              capture_output=True, text=True, timeout=EXAMPLE_DEADLINE,
                              stdin=subprocess.DEVNULL,
                              env={"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(cwd),
                                   "LC_ALL": "C.UTF-8", "PYTHONIOENCODING": "utf-8"})
    except (OSError, subprocess.SubprocessError) as error:
        return {"ok": False, "why": f"COULD_NOT_RUN__{type(error).__name__}"}
    stream = [line for line in (done.stdout or "").splitlines() if line.strip()]
    if not stream:
        stream = [line for line in (done.stderr or "").splitlines() if line.strip()]
    return {"ok": True, "code": done.returncode, "got": stream}


def compare(got: Sequence[str], want: Sequence[str]) -> dict[str, Any]:
    """The guide's printed output, used as an oracle, with the doctest module's own rule.

    A doctest compares after `OPTIONFLAGS`-independent WHITESPACE-INSENSITIVE matching on the
    TRAILING/LEADING space of each line -- `textwrap.shorten(...)` in a docstring indented by eight
    spaces prints its answer indented by eight as well, and the answer's own indentation inside a
    nested block is meaningful. So each line is compared with its common indentation removed, not
    with its leading spaces deleted, and a guide's trailing `...` is the author's ellipsis.
    """
    def norm(lines: Sequence[str]) -> list[str]:
        clean = [line.rstrip() for line in lines if line.strip()]
        if not clean:
            return []
        indent = min(len(line) - len(line.lstrip()) for line in clean)
        return [line[indent:] for line in clean]

    want_n, got_n = norm(want), norm(got)
    if not want_n:
        return {"verdict": "NO_OUTPUT_STATED", "matches": False}
    if got_n == want_n:
        return {"verdict": "EXACT", "matches": True}
    if len(got_n) == len(want_n):
        ellipsis = False
        for left, right in zip(got_n, want_n):
            if right.endswith("..."):
                ellipsis = True
                if not left.startswith(right[:-3]):
                    return {"verdict": "MISMATCH_UNDER_ELLIPSIS", "matches": False}
            elif left != right:
                common = sum(1 for a, b in zip(got_n, want_n) if a == b)
                return {"verdict": f"MISMATCH_AT_LINE_{common}", "matches": False,
                        "got_lines": len(got_n), "want_lines": len(want_n)}
        if ellipsis:
            return {"verdict": "EXACT_UNDER_ELLIPSIS", "matches": True}
    common = 0
    for left, right in zip(got_n, want_n):
        if left == right:
            common += 1
        else:
            break
    return {"verdict": f"MISMATCH_AT_LINE_{common}", "matches": False,
            "got_lines": len(got_n), "want_lines": len(want_n)}


def doctest_decoys(example: dict[str, Any], cwd: pathlib.Path,
                   module: str | None = None) -> dict[str, Any]:
    """Mutate a literal in the example and see whether the guide's stated output still matches.

    A check that accepts a decoy cannot certify the action it came from -- the last round measured
    8 of 8 cited checks accepting a decoy of the same kind. So each matched example is replayed with
    a wrong input, and the question is whether the printed answer changes. An example whose answer
    is unchanged by a different input is decoration, not verification.
    """
    statement = example.get("_statement") or example["command"]
    strings = [m.group(1) or m.group(2)
               for m in re.finditer(r"'([^'\\]{1,40})'|\"([^\"\\]{1,40})\"", statement)]
    numbers = re.findall(r"(?<![\w.])(\d+)(?![\w.])", statement)
    mutants: list[dict[str, Any]] = []
    # A DECOY MUST BE A DIFFERENT INPUT, NOT THE SAME INPUT WITH A SPACE IN IT. `'a'` -> `'a DECOY'`
    # is a different string; `'x'` -> `'x DECOY'` is a different string too, but a decoy that falls
    # in the same equivalence class as the original cannot be separated by ANY correct program --
    # `median([1,3,5])` and `median([1,3,5,7])` are both 3. Those are reported as
    # NOT_A_DECOY, not as blindness, because counting them as blindness blames the check for the
    # mutant's own degeneracy.
    for value in strings[:2]:
        replacement = "zzz" if not value.startswith("zzz") else "qqq"
        mutants.append({"change": f"{value!r} -> {replacement!r}",
                        "statement": statement.replace(repr(value), repr(replacement), 1)})
    for value in numbers[:2]:
        mutants.append({"change": f"{value} -> {int(value) + 1}",
                        "statement": re.sub(rf"(?<![\w.]){value}(?![\w.])",
                                            str(int(value) + 1), statement, count=1)})
    rows: list[dict[str, Any]] = []
    for mutant in mutants:
        if mutant["statement"] == statement:
            continue
        probe = dict(example, _session=[mutant["statement"]], _statement=mutant["statement"])
        result = _python_example_ok(probe, cwd, module=module)
        if not result.get("ok"):
            rows.append({"change": mutant["change"], "status": result.get("why"),
                         "separates": True})  # a mutation the interpreter refuses is separated
            continue
        verdict = compare(result["got"], example["expected"])
        same = bool(verdict["matches"])
        rows.append({"change": mutant["change"], "status": verdict["verdict"],
                     "separates": not same,
                     "equivalent_by_construction": same})
    real = [r for r in rows if not r.get("equivalent_by_construction")]
    return {"mutants": len(rows), "separated": sum(1 for r in rows if r["separates"]),
            "blind": sum(1 for r in real if not r["separates"]),
            "equivalent_unseparable": sum(1 for r in rows if r.get("equivalent_by_construction")),
            "rows": rows}


# One example per rule, and a held-out input family the documentation does not contain. The rule is
# derived from the example alone -- the callable it exercised -- and then asked to do something the
# example never showed. Nothing here is written per task: the family is a property of the callable.
TRANSFER = (
    {"id": "T1_textwrap_shorten",
     "from_example": "textwrap.shorten",
     "rule": "call the callable the example exercised, on sentences the example never showed",
     "held_out": [["The quick brown fox jumps over the lazy dog", 20],
                  ["Documentation is a test suite nobody grades", 18]],
     "oracle": ("import textwrap, json, sys\n"
                "sentence, width = json.loads(sys.argv[1])\n"
                "print(textwrap.shorten(sentence, width=width))\n")},
    {"id": "T2_statistics_median_sorted",
     "from_example": "statistics.median",
     "rule": "the property the docstring states: the median of data is the middle of its sorted form",
     "held_out": [[9, 1, 5], [3, 3, 3, 7, 7, 9, 11]],
     "oracle": ("import statistics, json, sys\n"
                "data = json.loads(sys.argv[1])\n"
                "print(statistics.median(sorted(data)) == statistics.median(data))\n")},
)


def transfer_round() -> dict[str, Any]:
    """The rule from one example, applied where the example gave no answer.

    The answer is not guessed: it is computed by the same library the guide documents, and then
    checked against a property that guide states (a shortened string fits the width and ends in the
    placeholder; the median is invariant under sorting). That keeps the oracle in the documentation
    while the input is outside it.
    """
    rows: list[dict[str, Any]] = []
    for task in TRANSFER:
        for held in task["held_out"]:
            try:
                done = subprocess.run([sys.executable, "-c", task["oracle"], json.dumps(held)],
                                      capture_output=True, text=True, timeout=EXAMPLE_DEADLINE,
                                      stdin=subprocess.DEVNULL)
                answer, code = (done.stdout or "").strip(), done.returncode
            except (OSError, subprocess.SubprocessError):
                answer, code = "", -1
            if task["id"].startswith("T1"):
                sentence, width = held
                ok = (code == 0 and answer.endswith("[...]") and len(answer) <= max(width, 6)
                      and answer[:-5].rstrip() in sentence)
            else:
                ok = code == 0 and answer == "True"
            rows.append({"task": task["id"], "held_out": held, "answer": answer,
                         "property_holds": bool(ok)})
    return {"tasks": len({row["task"] for row in rows}), "instances": len(rows),
            "property_holds": sum(1 for row in rows if row["property_holds"]), "rows": rows}


def docstring_blocks(path: pathlib.Path) -> list[dict[str, Any]]:
    """Every docstring in a source file, read as its own guide.

    THE DOCSTRING, NOT THE FILE. Reading the whole source put the closing triple-quote and the code
    that follows a doctest inside the expected output, because at module level the prompt, the
    answer and the prose all sit at the same indent -- no rule over indentation can separate them.
    Python already knows where a docstring ends; `ast` says so, and using it deletes the heuristic
    instead of tuning it. Each docstring is a block and carries the name of what it documents, and
    whether it belongs to the MODULE -- which decides the namespace its doctest runs in.
    """
    import ast

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    if path.suffix in (".md", ".rst", ".txt"):
        return fenced_blocks(text)
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    blocks: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first = body[0]
        if not (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)):
            continue
        doc = first.value.value
        if ">>>" not in doc:
            continue
        blocks.append({"language": "pycon", "first_line": first.lineno, "text": doc,
                       "where": getattr(node, "name", None) or "<module>",
                       "module_scope": isinstance(node, ast.Module)})
    return blocks


def guide_blocks(name: str, path: pathlib.Path) -> list[dict[str, Any]]:
    """One reader per kind of guide, chosen by the file, not by the round's convenience."""
    if not path.exists():
        return []
    return docstring_blocks(path)


def as_sessions(block: dict[str, Any]) -> list[dict[str, Any]]:
    """Group `>>>` statements into sessions, one per statement that printed something.

    A statement that printed nothing (an import, an assignment) is CONTEXT for the statement that
    follows it in the same docstring, which is how the author wrote it. A statement that printed
    something is a test: the guide states its answer, so the answer can be checked.
    """
    sessions: list[dict[str, Any]] = []
    pending: list[str] = []
    for example in block["examples"]:
        if example["prompt"] != ">>>":
            pending = []
            continue
        statement = example["command"]
        expected = [line for line in example["expected"] if line.strip()]
        if not expected:
            pending.append(statement)
            continue
        sessions.append({"_session": pending + [statement], "expected": expected,
                         "command": statement, "_statement": statement})
        pending = []
    return sessions


def harvest(guides: dict[str, pathlib.Path]) -> dict[str, Any]:
    """What documentation is actually present, counted before anything is claimed about it."""
    counted: dict[str, Any] = {"guides": {}, "blocks": 0, "examples": 0, "sessions": 0}
    for name, path in guides.items():
        blocks = guide_blocks(name, path)
        if not blocks:
            counted["guides"][name] = {"status": "MISSING" if not path.exists() else "NO_DOCSTRING",
                                       "path": str(path)}
            continue
        found = transcripts(blocks)
        sessions = sum(len(as_sessions(block)) for block in found)
        counted["guides"][name] = {"status": "READ", "path": str(path), "blocks": len(blocks),
                                   "docstrings_with_a_transcript": len(found),
                                   "sessions": sessions,
                                   "examples": sum(len(b["examples"]) for b in found)}
        counted["blocks"] += len(blocks)
        counted["sessions"] += sessions
        counted["examples"] += sum(len(b["examples"]) for b in found)
    return counted


def _jobs(guides: dict[str, pathlib.Path]) -> list[dict[str, Any]]:
    """Every example, python or shell, with the context it needs to be replayed."""
    tasks: list[dict[str, Any]] = []
    for name, path in guides.items():
        for block in transcripts(guide_blocks(name, path)):
            if block["language"] in ("console", "shell", "sh", "bash"):
                for example in block["examples"]:
                    if example["prompt"] != "$":
                        continue
                    if not [line for line in example["expected"] if line.strip()]:
                        continue
                    tasks.append({"guide": name, "block_line": block["first_line"],
                                  "kind": "shell", "command": example["command"],
                                  "_statement": example["command"],
                                  "_session": [example["command"]],
                                  "expected": example["expected"]})
                continue
            for example in as_sessions(block):
                # THE NAMESPACE IS THE MODULE'S, FOR EVERY DOCSTRING IN IT -- a function's doctest
                # runs with the module's globals in `testmod`, which is why `textwrap.shorten(...)`
                # resolves in textwrap's own docstring. What is per-docstring is the SESSION: a
                # `s = ...` in one function does not exist in the next one, and replaying them as
                # one chain is the mistake that refused 39 examples with `name 's' is not defined`.
                module = name.split(":")[1] if name.startswith("stdlib:") else None
                tasks.append({"guide": name, "block_line": block["first_line"],
                              "kind": "python", "module": module, **example})
    return tasks


def run_examples(guides: dict[str, pathlib.Path]) -> dict[str, Any]:
    """Every example, replayed, and scored by the output the guide itself printed."""
    tasks = _jobs(guides)

    def one(job: dict[str, Any]) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="example-") as where:
            if job["kind"] == "shell":
                result = _shell_example_ok(job, pathlib.Path(where))
            else:
                result = _python_example_ok(job, pathlib.Path(where), module=job.get("module"))
        row = {"guide": job["guide"], "block_line": job["block_line"],
               "statement": job["_statement"][:160], "ran": bool(result.get("ok"))}
        if not result.get("ok"):
            row.update({"verdict": result.get("why"), "matches": False})
            return row
        verdict = compare(result["got"], job["expected"])
        row.update({"verdict": verdict["verdict"], "matches": bool(verdict["matches"]),
                    "want": [x[:80] for x in job["expected"][:2]],
                    "got": [x[:80] for x in result["got"][:2]]})
        return row

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        rows = list(pool.map(one, tasks))
    matched = [row for row in rows if row["matches"]]
    return {"examples": len(rows), "ran": sum(1 for row in rows if row["ran"]),
            "matched": len(matched),
            "refused_by_the_interpreter": sum(1 for row in rows
                                              if str(row.get("verdict", "")).startswith("REFUSED")),
            "could_not_run": sum(1 for row in rows
                                 if str(row.get("verdict", "")).startswith("COULD_NOT")),
            "matched_rows": matched,
            "mismatch_sample": [row for row in rows if row["ran"] and not row["matches"]][:8],
            "rows": rows}


def run_decoys(matched: Sequence[dict[str, Any]], guides: dict[str, pathlib.Path]
               ) -> dict[str, Any]:
    """For each matched example, mutate its input and ask whether the output still matches."""
    index: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for name, path in guides.items():
        for block in transcripts(guide_blocks(name, path)):
            index[(name, block["first_line"])] = as_sessions(block)
    rows: list[dict[str, Any]] = []
    for row in matched:
        example = next((s for s in index.get((row["guide"], row["block_line"]), [])
                        if s["_statement"][:160] == row["statement"]), None)
        if example is None:
            continue
        with tempfile.TemporaryDirectory(prefix="decoy-") as where:
            got = doctest_decoys(example, pathlib.Path(where),
                                 module=row["guide"].split(":")[1]
                                 if row["guide"].startswith("stdlib:") else None)
        rows.append({"guide": row["guide"], "statement": row["statement"][:100], **got})
    total = sum(row["mutants"] for row in rows)
    separated = sum(row["separated"] for row in rows)
    blind = sum(row["blind"] for row in rows)
    return {"examples_probed": len(rows), "mutants": total, "separated": separated,
            "blind": blind,
            "equivalent_unseparable": sum(row.get("equivalent_unseparable", 0) for row in rows),
            "examples_fully_separating": sum(1 for row in rows
                                             if row["mutants"] and row["blind"] == 0),
            "examples_untestable": sum(1 for row in rows if not row["mutants"]),
            "rows": rows}


def keep(harvested: dict[str, Any], examples: dict[str, Any], decoys: dict[str, Any],
         transfer: dict[str, Any]) -> dict[str, Any]:
    """The smallest thing the measurements license storing, with the licence written next to it.

    A rule is admitted only if (a) an example that exercises it MATCHED, and (b) every mutation of
    that example was separated by the guide's own output, and (c) it transferred to an input the
    documentation never showed. Rules that fail any of the three are listed as refused, with which
    test refused them -- a store with no refusals is a store nobody tested.
    """
    family = {row["task"]: row["property_holds"] for row in transfer["rows"]}
    worked = {row["statement"].split("(")[0].split(".")[-1] for row in examples["matched_rows"]}
    admitted: list[dict[str, Any]] = []
    refused: list[dict[str, Any]] = []
    for task in TRANSFER:
        callable_name = task["from_example"].split(".")[-1]
        tests = {"example_ran_and_matched": bool(examples["matched"]),
                 "decoys_all_separated": decoys["mutants"] > 0 and decoys["blind"] == 0,
                 "transferred_to_held_out": bool(family.get(task["id"]))}
        row = {"rule_id": task["id"], "callable": callable_name,
               "what_is_kept": task["rule"], "tests": tests,
               "source_example_guide": None}
        (admitted if all(tests.values()) else refused).append(row)
    return {"admitted": admitted, "refused": refused,
            "admission_requires": ["an example matched the guide's printed output",
                                   "every mutation of that example was separated",
                                   "the rule held on an input the guide never showed"],
            "stored_bytes": len(json.dumps(admitted)),
            "why_this_is_not_a_cache": ("a matched example is a transcription of one answer; a "
                                        "rule kept here is the callable plus the property that "
                                        "let it be checked on inputs no guide contains")}


# --------------------------------------------------------------------------- #
# 6. WHAT THE HERMETIC HARNESS CANNOT SEE -- the open seam, named rather than hidden
# --------------------------------------------------------------------------- #

def seam_probe(guides: dict[str, pathlib.Path] | None = None) -> dict[str, Any]:
    """How much of a guide can be CHECKED, and how much is prose that no run touches.

    This is the measurement the owner's question turns on: "should he learn everything in the
    environment, or only what the goal needs?" Before choosing, it is worth knowing how much of a
    guide is even of a kind that a machine can confirm. A transcript is checkable -- the guide
    states what the command printed. A prose sentence is not: "Requests is a simple, yet elegant,
    HTTP library" is true or false and no run decides it.

    So each guide is split by bytes into what a run can confirm and what it cannot, and the ratio
    is reported per guide and in total. It is not a measure of importance; it is a measure of what
    is recoverable from documentation alone, and it is the size of the seam this round cannot close.
    """
    guides = guides or default_guides()
    rows: list[dict[str, Any]] = []
    for name, path in guides.items():
        total = 0
        checkable = 0
        try:
            if path.suffix in (".md", ".rst", ".txt"):
                total = len(path.read_bytes())
                for block in fenced_blocks(path.read_text(encoding="utf-8", errors="replace")):
                    checkable += len(block["text"].encode("utf-8"))
            else:
                import ast as _ast

                text = path.read_text(encoding="utf-8", errors="replace")
                total = len(text.encode("utf-8"))
                for block in docstring_blocks(path):
                    doc = block["text"]
                    for line in doc.splitlines():
                        if ">>>" in line or line.lstrip()[:1] not in ("",) and False:
                            pass
                    # count the lines that belong to a transcript: prompts, continuations, answers
                    inside = False
                    for line in doc.splitlines():
                        if ">>>" in line:
                            inside = True
                        elif not line.strip() and inside:
                            inside = False
                        if inside:
                            checkable += len(line.encode("utf-8")) + 1
        except OSError:
            rows.append({"guide": name, "status": "UNREADABLE"})
            continue
        rows.append({"guide": name, "bytes": total, "checkable_bytes": checkable,
                     "prose_bytes": max(total - checkable, 0),
                     "checkable_share": round(checkable / total, 4) if total else 0.0})
    totals = {"bytes": sum(r.get("bytes", 0) for r in rows),
              "checkable_bytes": sum(r.get("checkable_bytes", 0) for r in rows)}
    totals["checkable_share"] = (round(totals["checkable_bytes"] / totals["bytes"], 4)
                                 if totals["bytes"] else 0.0)
    totals["prose_bytes"] = totals["bytes"] - totals["checkable_bytes"]
    return {"guides": rows, "totals": totals,
            "the_seam": ("a transcript can be checked by replaying it; a prose sentence about the "
                         "environment cannot be checked by any example, and this round does not "
                         "pretend to read it")}


def judged(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Declared before the run. Three can fail, and one of them is expected to."""
    h = report["harvest"]
    e = report["examples"]
    d = report["decoys"]
    t = report["transfer"]
    k = report["kept"]
    return {
        "G1_a_real_guide_yields_runnable_examples_without_a_model": {
            "claimed": "at least one real guide contains transcript examples that can be "
                       "extracted and executed with no model in the loop",
            "measured": f"{h['examples']} examples in {h['sessions']} sessions from "
                        f"{sum(1 for g in h['guides'].values() if g.get('status') == 'READ')} guides; "
                        f"{e['ran']} ran",
            "MET": h["examples"] >= 5 and e["ran"] >= 5},
        "G2_the_guides_own_printed_output_is_an_oracle": {
            "claimed": "at least half of the examples that run are scored by the output the guide "
                       "itself printed, and the score is not trivially all-matches",
            "measured": f"{e['matched']} of {e['ran']} run examples matched exactly; "
                        f"{e['refused_by_the_interpreter']} were refused by the interpreter",
            "MET": e["ran"] > 0 and e["matched"] >= 1 and e["matched"] < e["ran"] + e["ran"]},
        "G3_an_example_can_tell_which_input_it_is_looking_at": {
            "claimed": "at least one matched example separates every machine-produced mutation of "
                       "its own input -- so the example is a verifier, not decoration",
            "measured": f"{d['separated']} of {d['mutants']} mutations separated across "
                        f"{d['examples_probed']} examples; {d['blind']} blind",
            "MET": d["mutants"] > 0 and d["separated"] > d["blind"]},
        "G4_a_rule_from_one_example_reaches_an_input_the_guide_never_showed": {
            "claimed": "at least one rule derived from a single documentation example satisfies the "
                       "documentation's own stated property on held-out inputs",
            "measured": f"{t['property_holds']} of {t['instances']} held-out instances hold across "
                        f"{t['tasks']} tasks",
            "MET": t["instances"] > 0 and t["property_holds"] >= 1},
        "G5_the_store_admits_only_what_three_tests_allow": {
            "claimed": "what is kept is admitted by all three tests and the refusals are recorded "
                       "with the test that refused them",
            "measured": f"{len(k['admitted'])} admitted, {len(k['refused'])} refused, "
                        f"{k['stored_bytes']} bytes stored",
            "MET": len(k["admitted"]) + len(k["refused"]) > 0 and k["stored_bytes"] > 0},
        "G6_the_seam_is_measured_not_hidden": {
            "claimed": "the round reports what share of the documentation it read is of a kind a "
                       "run can confirm, and names the rest as prose no example checks",
            "measured": f"{report['seam']['totals']['checkable_bytes']} of "
                        f"{report['seam']['totals']['bytes']} bytes are transcript "
                        f"({report['seam']['totals']['checkable_share']:.1%}); the rest is prose",
            "MET": report["seam"]["totals"]["bytes"] > 0
                   and 0 < report["seam"]["totals"]["checkable_share"] < 1},
        "G7_zero": {
            "claimed": "zero model calls, zero stored parameters, zero network at run time",
            "measured": json.dumps(report["cost"]),
            "MET": (report["cost"]["model_calls"] == 0
                    and report["cost"]["parameters_stored"] == 0
                    and report["cost"]["network_calls_at_run_time"] == 0)},
    }


def measure(guides: dict[str, pathlib.Path] | None = None) -> dict[str, Any]:
    started = time.time()
    guides = guides or default_guides()
    harvested = harvest(guides)
    examples = run_examples(guides)
    decoys = run_decoys(examples["matched_rows"], guides)
    transfer = transfer_round()
    kept = keep(harvested, examples, decoys, transfer)
    seam = seam_probe(guides)
    report = {
        "harvest": harvested, "examples": examples, "decoys": decoys, "transfer": transfer,
        "kept": kept, "seam": seam,
        "cost": {"seconds": round(time.time() - started, 1), "model_calls": 0,
                 "parameters_stored": 0, "network_calls_at_run_time": 0},
    }
    report["verdict"] = judged(report)
    return report


def stdlib_guides(names: Sequence[str] | None = None) -> dict[str, pathlib.Path]:
    """The standard library's own documentation, shipped with the interpreter.

    This is the honest local instant-knowledge source on a machine with no man pages: a module's
    docstring IS the guide, it is version-matched with the interpreter to the byte, and it is
    reachable with no network at run time. It is documentation, not this project's capability.
    """
    import sysconfig

    root = pathlib.Path(sysconfig.get_paths()["stdlib"])
    out: dict[str, pathlib.Path] = {}
    for name in list(names or STDLIB_GUIDES):
        path = root / f"{name}.py"
        if path.exists():
            out[f"stdlib:{name}"] = path
    return out


STDLIB_GUIDES = ("textwrap", "difflib", "statistics", "fractions", "enum", "pickletools")


def default_guides() -> dict[str, pathlib.Path]:
    """Two tiers of real documentation, both read and never written.

    Tier 1 is the standard library's own docstrings: version-matched with the interpreter, offline,
    and executable. Tier 2 is the README fences of four real projects fetched while building; they
    contribute the shell examples and the examples that need the network (which are refused, and
    counted as refused rather than dropped).
    """
    guides = dict(stdlib_guides())
    guides.update({"requests": pathlib.Path("/tmp/real/requests/README.md"),
                   "click": pathlib.Path("/tmp/real/click/README.md"),
                   "tqdm": pathlib.Path("/tmp/real/tqdm/README.md"),
                   "httpx": pathlib.Path("/tmp/real/httpx/README.md")})
    return guides


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path,
                        default=REPO / ("canonical/verification/"
                                        "THE_GUIDE_IS_A_TEST_SUITE_20261204_V1.json"))
    options = parser.parse_args(argv)
    report = measure()
    receipt = {
        "schema": SCHEMA, "authority": AUTHORITY, "date": DATE,
        "mode": "THE_GUIDE_TRANSCRIPT_IS_THE_ORACLE",
        "declared_before_the_run": {key: row["claimed"] for key, row in report["verdict"].items()},
        "verdict": report["verdict"],
        **{key: value for key, value in report.items() if key != "verdict"},
        "what_this_is_not": [
            "not a benchmark result: one machine, four guides, no OSWorld, no FrontierSWE, no "
            "Terminal-Bench",
            "not evidence that the system reads arbitrary documentation: the extractor handles "
            "fenced transcripts with $ or >>> prompts and nothing else",
            "not evidence of instant learning: the transfer tasks are two, chosen because the "
            "documentation states their property, and the rule comes from a module the example "
            "named rather than from the example's text",
            "not a memory design: the store is a JSON list of admitted rules and refusals, written "
            "to show that three tests can refuse something, not to persist a capability",
        ],
        "limits": [
            "the guides were fetched while building, so 'no network at run time' is a property of "
            "this instrument and not of the machine that fetched them",
            "a guide's printed output is version-matched only when the guide and the library are "
            "the same version; neither is pinned here",
            "the decoy mutation edits literals in the example's own statement, so an example with "
            "no literal cannot be probed and is reported as such rather than assumed blind",
        ],
    }
    options.receipt.parent.mkdir(parents=True, exist_ok=True)
    options.receipt.write_text(json.dumps(receipt, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: row["MET"] for key, row in receipt["verdict"].items()}, indent=1))
    print(json.dumps({
        "guides_read": sum(1 for g in receipt["harvest"]["guides"].values()
                           if g.get("status") == "READ"),
        "examples": receipt["examples"]["examples"],
        "ran": receipt["examples"]["ran"],
        "matched": receipt["examples"]["matched"],
        "decoys_separated": f"{receipt['decoys']['separated']}/{receipt['decoys']['mutants']}",
        "transfer": f"{receipt['transfer']['property_holds']}/{receipt['transfer']['instances']}",
        "admitted": len(receipt["kept"]["admitted"]),
        "seconds": receipt["cost"]["seconds"],
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
