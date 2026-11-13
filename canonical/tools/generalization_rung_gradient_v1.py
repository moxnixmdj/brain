#!/usr/bin/env python3
"""Problem 2, measured as a gradient rather than a verdict: where does memory stop generalising,
and does a check move the stop?

THE CLAIM UNDER TEST
--------------------
The owner splits the work in two: exact recall (solved) and generalisation (not solved), and asks
for the second one. That split is too coarse to act on, because "generalisation" is not one thing.
The tree's own learner -- `canonical/runtime/edit_kind_learning_v1.py` -- writes ONE demonstration
down at six rungs, from *exactly this code* to *this shape anywhere, with the names it brought in
taken from wherever it lands*:

    as_it_was          the names and constants of the changed part stay what they were
    names_open         they become holes
    both_open          everything the change did not touch becomes a hole too
    from_the_place     the names the change BROUGHT IN are taken from the program it is applied to
    attributes_too     and the attributes it brought in
    ... each one also with more of what stood around it (nothing; the same position; the enclosing
    expression; the enclosing statement)

So the honest question is not "can it generalise?" but **which rung reaches the next program, and
what does the wrong rung cost?** This tool answers both, on files written by other people, and then
asks the question that decides the owner's plan: **does a checker at the target turn a wrong guess
into a usable skill?** It does that with the tree's own `repeat_tried` mechanism, which proposes one
place at a time and keeps only what the project's own run settles.

WHAT THIS MEASURES (all on public merged pull requests, no model, no network at scoring time)
--------------------------------------------------------------------------------------------
For each task, every drawn file is used in turn as THE demonstration and every other file is the
work to be done. Then, for every (demonstration, target) pair:

    literal        the target has to already contain the changed text; the edit is then a copy
    exact          the shipped learner, as it is on main, one demonstration (this is "Problem 2")
    two_showings   the shipped learner with a second, different demonstration
    any_rung       every rung of the learner's own ladder, first candidate that differs
    any_rung_check the same, but a candidate is accepted only when the CHECK accepts it
    check_only     no lesson at all: try one place at a time against the CHECK

Three different things are counted and they are not the same number:

    reached   the target needed no change of this kind at all (nothing to generalise)
    right     changes made that the developers also made
    wrong     changes made that the developers did not make (a wrong rung firing is visible here)

and the check is graded by the only thing it can be graded on:

    accepts   the check accepted a candidate -> was it the developers' change?

WHAT THE CHECK ACTUALLY IS, AND WHAT IT IS NOT
----------------------------------------------
`--check tests` runs the target file's own test module (`python -m unittest`), when the project
ships one that imports the file. That is a real oracle and it is only available where a test exists.
`--check identity` marks every candidate accepted -- the honest control for "no oracle at all".
Neither is a proof that a change is correct: a passing test is agreement with whoever wrote the
test, on the inputs the test happens to use.

Authority: NONE. Producer-run, one machine, `$0`, zero model calls, no capability registered, no
family flipped, `truth.achieved` stays `false`, and nothing here writes into the repository tree.

    python3 canonical/tools/generalization_rung_gradient_v1.py --demo        # offline, constructed
    python3 canonical/tools/generalization_rung_gradient_v1.py --collect /tmp/pulls.json
    python3 canonical/tools/generalization_rung_gradient_v1.py --pulls /tmp/pulls.json --check tests
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
from typing import Any, Callable, Iterable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import edit_kind_learning_v1 as ladder  # noqa: E402

SCHEMA = "GENERALIZATION_RUNG_GRADIENT_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
MAX_BYTES = 200_000
CALL_LIMIT_S = 60.0
MAX_CANDIDATES = 8          # per operator, so one rung of the ladder stays affordable


# --------------------------------------------------------------------------- #
# the demonstration: offline and constructed, so the whole chain can be seen
# --------------------------------------------------------------------------- #
# The same defect, four ways. Only the first is what you literally saw.
DEMO_BEFORE = "def total(items):\n    if len(items) == 0:\n        return 0\n    return sum(items)\n"
DEMO_AFTER = "def total(items):\n    if not items:\n        return 0\n    return sum(items)\n"

DEMO_TARGETS: list[tuple[str, str, str]] = [
    ("literal copy: the identical line, another name",
     "literal",
     "def count(items):\n    if len(items) == 0:\n        return 0\n    return len(items)\n"),
    ("same idea, another collection (a dict)",
     "shape",
     "def empty(frame):\n    if len(frame) == 0:\n        return True\n    return False\n"),
    ("same idea, a different falsy test written as a comparison",
     "meaning",
     "def nothing(rows):\n    if rows.__len__() == 0:\n        return -1\n    return len(rows)\n"),
    ("same idea, one line inside a larger expression",
     "meaning",
     "def ok(values):\n    return len(values) == 0 or values[0] > 0\n"),
    ("different kind of change entirely (a rename)",
     "other",
     "def size(items):\n    count = len(items)\n    return count\n"),
]


def demo() -> dict[str, Any]:
    """The ladder on one demonstration, with the rung that reached each target named."""
    rows = ladder.operators_of(DEMO_BEFORE, DEMO_AFTER)
    out: dict[str, Any] = {
        "demonstration": {"before": DEMO_BEFORE, "after": DEMO_AFTER},
        "rungs_the_learner_wrote": [{"openness": r.openness, "surroundings": r.surroundings,
                                     "what": r.what, "shape": r.shown()}
                                    for r in rows],
        "targets": [],
    }
    lessons = ladder.Lessons()
    learned = lessons.learn("demo", DEMO_BEFORE, DEMO_AFTER)
    out["operators_from_one_demonstration"] = learned
    for label, asks, source in DEMO_TARGETS:
        proposals = lessons.proposals(source, limit=MAX_CANDIDATES)
        best = proposals[0] if proposals else None
        out["targets"].append({
            "label": label, "asks": asks,
            "reached": best is not None,
            "by_rung": None if best is None else {"openness": best["openness"],
                                                  "surroundings": best["surroundings"]},
            "candidate_line": None if best is None else _the_changed_line(source, best["source"]),
            "candidates": len(proposals),
        })
    return out


def check_discriminates(project: Mapping[str, str], path: str) -> dict[str, Any]:
    """A check that passes everything is not a check. Break the file on purpose and look.

    The check must accept the file as it is, and must REJECT a version whose behaviour is broken.
    What "broken" means has to be mechanical, so the break cannot be chosen to suit the answer:
    every `return X` in the file becomes `return None`, one at a time, and the first one that
    makes the file's own tests fail is the evidence. A file with no `return` is broken by making
    the last top-level function return nothing. If none of these is caught, the check is not
    discriminating and every number it produces is worthless -- that is reported, not smoothed.
    """
    import ast
    check = Check("tests", project, path)
    out: dict[str, Any] = {"available": check.available, "reason": check.reason,
                           "accepts_the_file_as_it_is": False, "rejects_a_broken_one": False,
                           "breaks_tried": 0}
    if not check.available:
        check.close()
        return out
    original = project.get(path, "")
    out["accepts_the_file_as_it_is"] = check.accepts(path, original)
    try:
        tree = ast.parse(original)
    except (SyntaxError, ValueError):
        check.close()
        return out
    lines = original.splitlines(keepends=True)
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and node.lineno == node.end_lineno:
            index = node.lineno - 1
            line = lines[index]
            indent = line[: len(line) - len(line.lstrip())]
            broken = "".join(lines[:index] + [f"{indent}return None\n"] + lines[index + 1:])
            out["breaks_tried"] += 1
            if not check.accepts(path, broken):
                out["rejects_a_broken_one"] = True
                break
    check.close()
    return out


#: A project that ships a check, so the check machinery can be shown to work at all.
#: Without this, "the check was unavailable" and "the check is broken" look identical from outside.
CONTROL_PROJECT = {
    "pkg/__init__.py": "",
    "pkg/bounds.py": "def below(n, hi):\n    return n < hi\n",
    "tests/__init__.py": "",
    "tests/test_bounds.py": (
        "import unittest\n\nfrom pkg.bounds import below\n\n\n"
        "class Bounds(unittest.TestCase):\n"
        "    def test_edge_is_excluded(self):\n"
        "        self.assertFalse(below(10, 10))\n\n"
        "    def test_below_is_included(self):\n"
        "        self.assertTrue(below(9, 10))\n\n\n"
        "if __name__ == '__main__':\n    unittest.main()\n"
    ),
}


def positive_control() -> dict[str, Any]:
    """The check, on a project that has one. Four demands, all of which must hold.

    Without this the whole measurement is unfalsifiable: every "the check could not run" on real
    pull requests would be indistinguishable from "this code has never worked".
    """
    path = "pkg/bounds.py"
    check = Check("tests", CONTROL_PROJECT, path)
    out: dict[str, Any] = {"available": check.available, "reason": check.reason, "module": check._test}
    if not check.available:
        check.close()
        return out
    original = CONTROL_PROJECT[path]
    out["accepts_the_project_as_it_is"] = check.accepts(path, original)
    # a correct edit: the same behaviour, written differently (the parameter renamed)
    out["accepts_the_correct_edit"] = check.accepts(path, original.replace("n < hi", "n < limit")
                                                    .replace("def below(n, hi)", "def below(n, limit)"))
    # a wrong edit that still compiles and still imports: the boundary moves by one
    out["rejects_a_wrong_edit_that_still_compiles"] = not check.accepts(
        path, original.replace("n < hi", "n <= hi"))
    out["rejects_a_broken_file"] = not check.accepts(path, original.replace("return n < hi", "return None"))
    out["discriminates"] = all(out[key] for key in (
        "accepts_the_project_as_it_is", "accepts_the_correct_edit",
        "rejects_a_wrong_edit_that_still_compiles", "rejects_a_broken_file"))
    check.close()
    return out


#: A constructed task where a check exists, so "what would an oracle buy" can be answered at all.
#: Clearly constructed: three sibling modules with the same boundary, one test module per module.
ORACLE_PROJECT: dict[str, str] = {
    "pkg/__init__.py": "",
    # window.py as it was before its own repair -- this is the BEFORE side of the demonstration.
    "pkg/window.py": "def in_window(x, hi):\n    return x <= hi\n",
    # the siblings still carry the defect the demonstration repaired: their tests fail on them.
    "pkg/limits.py": "def at_limit(x, hi):\n    return x <= hi\n",
    "pkg/edges.py": "def edge(x, hi):\n    return x <= hi\n",
    # A module whose `<=` is REQUIRED. The lesson is "upper bound is exclusive", and here that is
    # false. Nothing in the demonstration can tell the two apart; only a check on this file can.
    "pkg/inclusive.py": "def in_closed(x, hi):\n    return x <= hi\n",
    "tests/__init__.py": "",
    # The tests of window.py settle BOTH boundaries, at the place the change was made AND at
    # 0 for the same function: the edge is out, something below it is in, and zero is in.
    # Both facts matter. `x > hi`, `x < 0` and `False` each keep the edge-out boundary and each
    # throw away a boundary this file pins; a correction that carries only the edge-out half of
    # this file's own behaviour is under-determined on it, and no amount of generality fixes that.
    "tests/test_window.py": (
        "import unittest\nfrom pkg.window import in_window\n\n"
        "class W(unittest.TestCase):\n"
        "    def test_edge_out(self):\n        self.assertFalse(in_window(5, 5))\n"
        "    def test_below_in(self):\n        self.assertTrue(in_window(4, 5))\n"
        "    def test_zero_in(self):\n        self.assertTrue(in_window(0, 5))\n"
    ),
    # A WEAKER CHECK, kept on purpose: this one pins only the edge, so `return x > hi` and
    # `return False` both satisfy it. It is what a lot of real tests look like.
    "tests/test_limits.py": (
        "import unittest\nfrom pkg.limits import at_limit\n\n"
        "class L(unittest.TestCase):\n"
        "    def test_edge_out(self):\n        self.assertFalse(at_limit(5, 5))\n"
    ),
    "tests/test_inclusive.py": (
        "import unittest\nfrom pkg.inclusive import in_closed\n\n"
        "class I(unittest.TestCase):\n"
        "    def test_edge_in(self):\n        self.assertTrue(in_closed(5, 5))\n"
        "    def test_below_in(self):\n        self.assertTrue(in_closed(4, 5))\n"
    ),
    # The stronger check: both sides.
    "tests/test_edges.py": (
        "import unittest\nfrom pkg.edges import edge\n\n"
        "class E(unittest.TestCase):\n"
        "    def test_edge_out(self):\n        self.assertFalse(edge(5, 5))\n"
        "    def test_below_in(self):\n        self.assertTrue(edge(4, 5))\n"
    ),
}

#: What the demonstration repaired, applied to every module that carries the same boundary.
ORACLE_AFTER: dict[str, str] = {
    "pkg/window.py": "def in_window(x, hi):\n    return x < hi\n",
    "pkg/limits.py": "def at_limit(x, hi):\n    return x < hi\n",
    "pkg/edges.py": "def edge(x, hi):\n    return x < hi\n",
    # not repaired, and must not be: this one really is inclusive
    "pkg/inclusive.py": "def in_closed(x, hi):\n    return x <= hi\n",
}


def oracle_makes_the_difference() -> dict[str, Any]:
    """The same one lesson, applied to two sibling modules, with and without a check.

    CONSTRUCTED, and labelled so: three modules with the same boundary, one test each. It exists
    because the real corpus cannot answer this question at all -- the check could not run on any of
    its 42 changed files -- and "we cannot tell" is a weaker statement than "here is what it looks
    like when we can".
    """
    lessons = _learned([(ORACLE_PROJECT["pkg/window.py"], ORACLE_AFTER["pkg/window.py"])])
    out: dict[str, Any] = {"constructed": True, "arms": {}}
    for path in ("pkg/limits.py", "pkg/edges.py", "pkg/inclusive.py"):
        source = ORACLE_PROJECT[path]
        wanted = ORACLE_AFTER[path]
        # A repair task is one whose file is broken as found; this one is not.
        broken = not ladder.same_program(source, wanted)
        check = Check("tests", ORACLE_PROJECT, path, expect="FAIL" if broken else "PASS")
        unchecked = _apply_everywhere(lessons, source)
        checked = _apply_everywhere(lessons, source, check=check, path=path)
        # Is the check strong enough to tell a right edit from a correction that is plausible as a
        # generalisation of the SAME lesson but wrong for this file? Three candidates, each of which
        # keeps the detail the demonstration actually showed. The count of attempts is printed, so a
        # "nothing gets through" cannot mean "nothing was tried".
        weak = {"passes_a_wrong_edit_that_satisfies_it": None, "wrong_edits_tried": 0}
        for wrong in (
            source.replace("<= hi", "> hi"),          # widens the accepting range instead of moving the edge
            source.replace("return x <= hi", "return x < 0"),   # keeps the edge, invents a lower bound
            source.replace("return x <= hi", "return False"),   # keeps the edge, accepts nothing
        ):
            catch = Check("tests", ORACLE_PROJECT, path, expect="FAIL" if broken else "PASS")
            if not catch.available:
                catch.close()
                continue
            weak["wrong_edits_tried"] += 1
            if catch.accepts(path, wrong) and weak["passes_a_wrong_edit_that_satisfies_it"] is None:
                weak["passes_a_wrong_edit_that_satisfies_it"] = wrong.splitlines()[-1].strip()
            catch.close()
        out["arms"][path] = {
            "check_available": check.available,
            "check_strength": weak,
            # same program, not same bytes: the check writes the file out, and layout is not meaning
            "without_a_check": {"edited": unchecked is not None,
                                "is_the_correct_edit": ladder.same_program(unchecked or source, wanted)},
            "with_a_check": {"edited": checked is not None,
                             "is_the_correct_edit": ladder.same_program(checked or source, wanted)},
        }
        check.close()
    return out


def _the_changed_line(before: str, after: str | None) -> str | None:
    """The single line that differs, for a human reading the table."""
    if after is None:
        return None
    old, new = before.splitlines(), after.splitlines()
    if len(old) != len(new):
        return None
    for a, b in zip(old, new):
        if a != b:
            return b.strip()
    return None


# --------------------------------------------------------------------------- #
# pulling real tasks: files other people changed, in one pull request, one kind
# --------------------------------------------------------------------------- #
def gh(*args: str, raw: bool = False) -> Any:
    command = ["gh", "api"] + (["-H", "Accept: application/vnd.github.raw"] if raw else []) + list(args)
    for attempt in range(3):
        done = subprocess.run(command, capture_output=True, timeout=120)
        if done.returncode == 0:
            return done.stdout.decode("utf-8", errors="replace") if raw else json.loads(done.stdout)
        if b"404" in done.stderr or b"Not Found" in done.stdout:
            return None
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"GitHub did not answer: {' '.join(command)[:160]}: {done.stderr[-200:]!r}")


def search_pulls(words: str) -> list[tuple[str, str, int]]:
    """Merged Python pull requests whose title carries these words, by GraphQL.

    GraphQL, not REST: the REST quota on this machine was exhausted by the first collection (1000
    calls for 8 pull requests, because every file was fetched one at a time) and returned 403 for
    the rest of the session. GraphQL answers the pull request, its merge base and its file list in
    one call, and it was not exhausted.
    """
    query = ('query($q: String!) { search(query: $q, type: ISSUE, first: 20) { nodes { '
             '... on PullRequest { number title merged repository { owner { login } name } } } } }')
    out = gh_graphql(query, {"q": f"is:pr is:merged language:Python in:title {words}"})
    nodes = (((out or {}).get("data") or {}).get("search") or {}).get("nodes") or []
    return [(n["repository"]["owner"]["login"], n["repository"]["name"], n["number"])
            for n in nodes if n and n.get("merged")]


def pull_details(owner: str, name: str, number: int) -> dict[str, Any] | None:
    """The pull request's title, its merge base, the commit after it, and the files it modified."""
    query = ('query($o: String!, $n: String!, $p: Int!) { repository(owner: $o, name: $n) { '
             'pullRequest(number: $p) { title merged mergeCommit { oid parents(first: 1) { nodes { oid } } } '
             'files(first: 60) { nodes { path changeType } } } } }')
    out = gh_graphql(query, {"o": owner, "n": name, "p": number})
    pull = (((out or {}).get("data") or {}).get("repository") or {}).get("pullRequest")
    if not pull or not pull.get("merged") or not pull.get("mergeCommit"):
        return None
    parents = pull["mergeCommit"]["parents"]["nodes"]
    if not parents:
        return None
    paths = sorted({f["path"] for f in pull["files"]["nodes"]
                    if f["path"].endswith(".py") and f["changeType"] == "MODIFIED"})
    return {"title": pull["title"], "before_at": parents[0]["oid"],
            "after_at": pull["mergeCommit"]["oid"], "paths": paths}


def gh_graphql(query: str, variables: Mapping[str, Any]) -> Any:
    command = ["gh", "api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        command += ["-F", f"{key}={value}"]
    for attempt in range(3):
        done = subprocess.run(command, capture_output=True, timeout=120)
        if done.returncode == 0:
            return json.loads(done.stdout)
        time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"GraphQL did not answer: {done.stderr[-200:]!r}")


def _carries(name: str) -> bool:
    """What the corpus keeps: Python sources and the project's own dependency manifests.

    The first version of fetch_tree kept only `.py` -- which meant every check that had to READ
    a declaration (requirements.txt, pyproject.toml, setup.cfg, an Azure extension.json) was
    reading a project whose declarations had been filtered out of it, and six tasks reported
    NO_DECLARED_DEPENDENCIES for dependencies their own manifests named. A manifest is text,
    it is small, and it is exactly what "stand up this project's checks" needs.
    """
    base = name.rsplit("/", 1)[-1]
    if name.endswith(".py"):
        return True
    if base in ("pyproject.toml", "setup.cfg", "tox.ini", "pytest.ini", "Pipfile",
                "environment.yml", "environment.yaml", "extension.json"):
        return True
    return base.startswith("requirements") or base.startswith("constraints")


def fetch_tree(repo: str, ref: str, into: pathlib.Path | None = None) -> dict[str, str]:
    """Every text file of a repository at one commit, from one tarball.

    One request per commit instead of one per file. The per-file contents API answers 403 after a
    few hundred calls, and the rate limit is not a property of the measurement -- so the collection
    was rewritten around this rather than around retries. It also gives the check a whole project
    to run, which the contents API never did.
    """
    import io
    import tarfile
    import urllib.request

    url = f"https://codeload.github.com/{repo}/tar.gz/{ref}"
    with urllib.request.urlopen(url, timeout=180) as answer:
        blob = answer.read()
    out: dict[str, str] = {}
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as archive:
        for member in archive.getmembers():
            if not member.isfile() or not _carries(member.name):
                continue
            if member.size > MAX_BYTES:
                continue
            relative = member.name.split("/", 1)[1] if "/" in member.name else member.name
            handle = archive.extractfile(member)
            if handle is None:
                continue
            out[relative] = handle.read().decode("utf-8", errors="replace")
    if into is not None:
        into.mkdir(parents=True, exist_ok=True)
        (into / f"{repo.replace('/', '__')}@{ref}.json").write_text(
            json.dumps(out), encoding="utf-8")
    return out


def _reads(text: str | None) -> bool:
    if text is None or len(text.encode()) > MAX_BYTES:
        return False
    try:
        compile(text, "<file>", "exec", dont_inherit=True)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return False
    return True


def collect_pull(owner: str, name: str, number: int, files: int,
                 say: Callable[[str], None], query: str = "") -> dict[str, Any] | None:
    """One pull request, both sides from tarballs, drawn the deterministic way every time.

    Shared by the search collector and --labels, so a record re-taken by name draws exactly the
    files the search path would have drawn: sorted paths, shuffled with seed 0, readable modified
    Python files, at most `files` of them, at least 3 or the pull is passed over.
    """
    label = f"{owner}/{name}#{number}"
    details = pull_details(owner, name, number)
    if not details or len(details["paths"]) < 3:
        return None
    repo = f"{owner}/{name}"
    try:
        before_tree = fetch_tree(repo, details["before_at"])
        after_tree = fetch_tree(repo, details["after_at"])
    except Exception as error:
        say(f"{label:45s} passed over: {type(error).__name__}")
        return None
    order = list(details["paths"])
    random.Random(0).shuffle(order)
    drawn = [{"path": p, "before": before_tree[p], "after": after_tree[p]}
             for p in order
             if p in before_tree and p in after_tree
             and _reads(before_tree[p]) and _reads(after_tree[p])
             and before_tree[p] != after_tree[p]][:files]
    if len(drawn) < 3:
        return None
    project = {p: t for p, t in before_tree.items() if len(t) < MAX_BYTES}
    say(f"{label:45s} {len(drawn)} files, {len(project)} project files  {details['title'][:50]}")
    return {"name": label, "repo": repo, "number": number, "title": details["title"],
            "query": query, "before_at": details["before_at"], "after_at": details["after_at"],
            "files": drawn, "project": project}


def collect(queries: Sequence[str], per_query: int, files: int, say: Callable[[str], None],
            only: Sequence[str] | None = None) -> list[dict[str, Any]]:
    """Merged Python pull requests where one kind of change was made in several files.

    The files are read from one tarball of each side of the change, so every project's whole tree
    is available -- which the check needs, because a test module that imports a changed file is
    usually in another directory.
    """
    pulls: list[dict[str, Any]] = []
    seen: set[str] = set()
    for words in queries:
        if only is not None and not any(o in words for o in only):
            continue
        taken = 0
        for owner, name, number in search_pulls(words):
            label = f"{owner}/{name}#{number}"
            if label in seen:
                continue
            pull = collect_pull(owner, name, number, files, say, query=words)
            if pull is None:
                continue
            pulls.append(pull)
            seen.add(label)
            taken += 1
            if taken >= per_query:
                break
            time.sleep(1)
    return pulls


def fetch_again(recorded: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """The same files again, by hash, from tarballs. A record that cannot be reproduced is refused."""
    pulls = []
    for item in recorded:
        files = []
        before_tree = fetch_tree(item["repo"], item["before_at"])
        after_tree = fetch_tree(item["repo"], item["after_at"])
        for entry in item["files"]:
            texts = {"before": before_tree.get(entry["path"]), "after": after_tree.get(entry["path"])}
            for which, text in texts.items():
                if text is None or hashlib.sha256(text.encode()).hexdigest() != entry[f"{which}_sha256"]:
                    raise RuntimeError(f"{item['name']} {entry['path']}: {which} is not the text the record names")
            files.append({"path": entry["path"], **texts})
        project = {p: t for p, t in before_tree.items() if len(t) < MAX_BYTES}
        pulls.append({**{k: v for k, v in item.items() if k not in ("files", "project")},
                      "files": files, "project": project})
    return pulls


def without_texts(pulls: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [{**{k: v for k, v in p.items() if k not in ("files", "project")},
             "files": [{"path": f["path"],
                        "before_sha256": hashlib.sha256(f["before"].encode()).hexdigest(),
                        "after_sha256": hashlib.sha256(f["after"].encode()).hexdigest()} for f in p["files"]]}
            for p in pulls]


# --------------------------------------------------------------------------- #
# scoring: what changed, and whether it is what the people changed
# --------------------------------------------------------------------------- #
def statements(text: str) -> list[str] | None:
    import ast
    import warnings
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return [line for line in ast.unparse(ast.parse(text)).split("\n") if line.strip()]
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return None


Change = tuple[int, tuple[str, ...], tuple[str, ...]]


def changed(before: Sequence[str], after: Sequence[str]) -> set[Change]:
    import difflib
    out: set[Change] = set()
    for tag, a0, a1, b0, b1 in difflib.SequenceMatcher(a=list(before), b=list(after), autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace" and a1 - a0 == b1 - b0:
            for offset in range(a1 - a0):
                if before[a0 + offset] != after[b0 + offset]:
                    out.add((a0 + offset, (before[a0 + offset],), (after[b0 + offset],)))
        else:
            out.add((a0, tuple(before[a0:a1]), tuple(after[b0:b1])))
    return out


def only_imports(change: Change) -> bool:
    lines = [line.strip() for line in change[1] + change[2]]
    return bool(lines) and all(line.startswith(("import ", "from ")) for line in lines)


def score(before: str, after: str, got: str | None) -> dict[str, int]:
    base, wanted = statements(before), statements(after)
    if base is None or wanted is None:
        return {"right": 0, "wrong": 0, "asked": 0, "developers": 0}
    theirs = changed(base, wanted)
    theirs_code = {c for c in theirs if not only_imports(c)}
    mine_lines = None if got is None else statements(got)
    mine = set() if mine_lines is None else changed(base, mine_lines)
    if mine_lines is None and got is not None:
        return {"right": 0, "wrong": 0, "asked": len(theirs_code), "developers": len(theirs_code)}
    right = mine & theirs_code
    return {"right": len(right), "wrong": len(mine - theirs), "asked": len(theirs_code),
            "developers": len(theirs_code)}


# --------------------------------------------------------------------------- #
# the check: a real oracle where one exists, and a control where none does
# --------------------------------------------------------------------------- #
def _tree_defines_tests(tree: Any) -> bool:
    """Whether this module DEFINES anything a runner could collect.

    Being under tests/ and importing the target is not enough -- stem's test/arguments.py is
    both and defines no test. A candidate that defines nothing collects nothing, and a suite
    that collects nothing verifies nothing.
    """
    import ast
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            return True
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                base_name = base.id if isinstance(base, ast.Name) else (
                    base.attr if isinstance(base, ast.Attribute) else "")
                if base_name.endswith("TestCase") or base_name == "PyTestCase":
                    return True
    return False


def _missing_module_names(text: str) -> list[str]:
    """The exact imports a run could not satisfy, in order, deduplicated.

    'still missing a dependency' names a class; 'missing: six' names the next operator. The
    record keeps the names so a residual failure is actionable instead of a bucket.
    """
    import re
    found = re.findall(r"No module named '([^']+)'|No module named \"([^\"]+)\"", text)
    names: list[str] = []
    for first, second in found:
        name = first or second
        if name and name not in names:
            names.append(name)
    return names


class Check:
    """Runs the target file's own tests, if the project ships a test module that imports it.

    This is the honest version of "does it still work": the project's own unit tests, run in a
    temporary copy of the bounded project. `identity` accepts everything and is the control that
    says what a plan with no oracle at all is worth.

    Two mistakes this class was written to avoid, both of which it made in its first draft:
      * restoring the *candidate* instead of the original after a run, which makes every later
        candidate be tested against a file that already holds an earlier guess;
      * deciding "does a test import this file" from one candidate path name, which silently
        reported the check unavailable on projects that do ship tests.
    """

    def __init__(self, kind: str, files: Mapping[str, str], target_path: str, *,
                 expect: str = "PASS") -> None:
        """`expect` is what the check must say about the file AS IT IS.

        PASS is a migration: the file already works, and an edit is only acceptable if it still
        works. FAIL is a repair: the file is broken on purpose, and an edit is acceptable when it
        makes the check pass. Getting this wrong makes every repair task look like a file that
        cannot be checked, which is exactly what happened on the constructed control below.
        """
        self.kind = kind
        self.expect = expect
        self.originals: dict[str, str] = dict(files)
        self.asked = 0
        self.settled = 0
        self.reason = ""            # why the check cannot run, when it cannot
        self._dir: pathlib.Path | None = None
        self._test: str | None = None
        self._python = sys.executable     # the interpreter the suite runs under (a venv after standing)
        self._venv_dir: str | None = None
        self._imports: dict[str, set[str]] | None = None   # project import index, parsed once
        self._entry_cache: dict[str, tuple[str | None, list[dict[str, Any]], str]] = {}
        self.test_entry: dict[str, Any] = {"chosen": None, "candidates": [], "confidence": "NONE"}
        self.standing: dict[str, Any] = {"attempted": False, "outcome": "NOT_NEEDED",
                                         "source": None, "detail": ""}
        self.path_reasons: dict[str, int] = {}
        self.missing_modules: list[str] = []
        self._repaired: list[str] = []
        if kind != "tests" or not files:
            self.available = kind == "identity"
            self.reason = "no check was asked for" if kind != "identity" else ""
            return
        self._dir = self._project(files)
        # The entry point is reported for the file the record names, but accepts() resolves one
        # entry PER TARGET PATH: a file no test imports has no oracle, whatever the first file's
        # tests happen to cover.
        chosen, candidates, confidence = self._test_entry(str(target_path))
        self.test_entry = {"chosen": chosen, "candidates": candidates, "confidence": confidence}
        if chosen is None:
            self.available = False
            self.reason = "CHECK_NO_TEST_MODULE"
            return
        self._test = chosen
        # A test module that cannot be imported is not a check. Which of the two it is matters and
        # is reported separately: a test that does not import is a missing DEPENDENCY, and
        # installing a project's dependencies is the work "verify in a new environment" actually is
        # -- so when the dependency is the only obstacle, THIS is where it gets stood up.
        runs, why = self._runs(chosen)
        if not runs and why == "CHECK_DEPENDENCY_MISSING":
            # stand what the project declares, re-run, then -- if the suite still cannot import
            # something -- install the missing name only when the project's own manifests spell
            # it out (extras, dev files, dynamic setup.py: words the declaration parser did not
            # reach). A name the project never writes is still not installed; that would be a
            # guess, and a guess is what this whole instrument exists to refuse.
            self._stand_dependencies()
            runs, why = self._runs(chosen)
            if not runs and why == "CHECK_DEPENDENCY_MISSING" and self._repair_missing():
                runs, why = self._runs(chosen)
        self.available = runs
        self.reason = "" if runs else why

    # ---------------------------------------------------------------- test entry, per target
    def _imports_of(self, path: pathlib.Path) -> set[str]:
        """The dotted names one file imports (absolute, plus same-root relative resolved)."""
        import ast
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError, ValueError, RecursionError, MemoryError):
            return set()
        relative = path.relative_to(self._dir) if self._dir else pathlib.Path(path.name)
        package = relative.parent.parts
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names |= {alias.name for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names.add(node.module)
                    names |= {f"{node.module}.{alias.name}" for alias in node.names}
                elif node.level:
                    # `from .x import y` inside tests/sub/ -> tests.sub.x ; `from .. import z`
                    # -> tests.z. Only same-tree relatives count; there is no such thing as an
                    # absolute name invented here.
                    base = package[: max(len(package) - node.level + 1, 0)]
                    stem = ".".join(base) if base else ""
                    full = ".".join(part for part in (stem, node.module or "") if part)
                    if full:
                        names.add(full)
                    prefix = full or stem
                    if prefix:
                        names |= {f"{prefix}.{alias.name}" for alias in node.names}
        return names

    @staticmethod
    def _is_test_name(path: pathlib.Path) -> bool:
        stem = path.stem
        return (stem.startswith("test_") and stem != "test_"
                or stem.endswith("_test") or stem == "tests")

    @staticmethod
    def _in_test_dir(path: pathlib.Path) -> bool:
        return any(part in ("test", "tests", "testing") for part in path.parent.parts)

    def _project_imports(self) -> dict[str, set[str]]:
        """module dotted name -> imported names, for the whole project. Parsed once per check."""
        if self._imports is not None:
            return self._imports
        index: dict[str, set[str]] = {}
        if self._dir is not None:
            for path in sorted(self._dir.rglob("*.py")):
                relative = path.relative_to(self._dir).with_suffix("")
                parts = list(relative.parts)
                if parts and parts[-1] == "__init__":
                    parts = parts[:-1]
                dotted = ".".join(parts)
                if dotted:
                    index[dotted] = self._imports_of(path)
        self._imports = index
        return index

    def _test_entry(self, target_path: str) -> tuple[str | None, list[dict[str, Any]], str]:
        """The test entry point for THIS file, the candidates it beat, and how sure that is.

        The honest output is not a bare name: it is the candidate list with its confidence
        (DIRECT: a test file imports this module; IN_DIRECTORY: a file under tests/ does;
        INDIRECT: a test imports a module that imports this; NONE: no oracle for this file).
        A mention of the file's name is still not a criterion -- only imports are.
        """
        if target_path in self._entry_cache:
            return self._entry_cache[target_path]
        empty: tuple[str | None, list[dict[str, Any]], str] = (None, [], "NONE")
        if self._dir is None:
            self._entry_cache[target_path] = empty
            return empty
        import ast
        wanted = pathlib.Path(target_path).with_suffix("")
        parts = list(wanted.parts)
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        if not parts:
            self._entry_cache[target_path] = empty
            return empty
        dotted = ".".join(parts)
        module = parts[-1]
        candidates: list[dict[str, Any]] = []
        for path in sorted(self._dir.rglob("*.py")):
            test_named = self._is_test_name(path)
            in_test_dir = self._in_test_dir(path)
            if not test_named and not in_test_dir:
                continue
            if path.stem == "__init__" and test_named:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
            except (OSError, SyntaxError, ValueError):
                continue
            imported = self._imports_of(path)
            # "the one I would run" prefers a module that actually DEFINES tests: stem's
            # test/arguments.py sits in the test directory and imports the target, but it is the
            # runner's argument parser -- a candidate that defines no test is a candidate that
            # will collect nothing.
            defines = _tree_defines_tests(tree)
            rel = ".".join(path.relative_to(self._dir).with_suffix("").parts)
            row = {"path": rel, "defines_tests": defines}
            if any(name == dotted or name.startswith(dotted + ".") for name in imported):
                row["tier"] = 0 if test_named else 2
                row["imports"] = "direct"
                candidates.append(row)
            elif module not in ("__init__",) and any(
                    name.split(".")[-1] == module or dotted.endswith(name) for name in imported):
                if test_named:
                    row["tier"] = 1
                    row["imports"] = "direct"
                    candidates.append(row)
        if not candidates:
            # one hop: a test that imports a module which imports this file
            index = self._project_imports()
            for path in sorted(self._dir.rglob("*.py")):
                if not (self._is_test_name(path) or self._in_test_dir(path)):
                    continue
                if path.stem == "__init__":
                    continue
                imported = self._imports_of(path)
                for name in imported:
                    covered = index.get(name)
                    if covered is None:
                        continue
                    if any(n == dotted or n.startswith(dotted + ".") for n in covered):
                        rel = ".".join(path.relative_to(self._dir).with_suffix("").parts)
                        try:
                            hop_tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
                        except (OSError, SyntaxError, ValueError):
                            hop_tree = None
                        candidates.append({"path": rel, "tier": 3, "imports": "indirect",
                                           "defines_tests": bool(hop_tree) and _tree_defines_tests(hop_tree)})
                        break
        if not candidates:
            self._entry_cache[target_path] = empty
            return empty
        candidates.sort(key=lambda row: (row["tier"],
                                         0 if row.get("defines_tests") else 1,
                                         len(row["path"].split(".")), row["path"]))
        chosen_row = candidates[0]
        confidence = {0: "DIRECT", 1: "DIRECT", 2: "IN_DIRECTORY", 3: "INDIRECT"}[chosen_row["tier"]]
        result = (chosen_row["path"], candidates, confidence)
        self._entry_cache[target_path] = result
        return result

    def _path_of(self, test_module: str) -> pathlib.Path | None:
        """The file a unittest module name points at (pytest needs a path, not a module)."""
        if self._dir is None:
            return None
        direct = self._dir.joinpath(*test_module.split(".")).with_suffix(".py")
        if direct.is_file():
            return direct
        package = self._dir.joinpath(*test_module.split("."), "__init__.py")
        if package.is_file():
            return package
        return None

    # ---------------------------------------------------------------- running the suite
    def _suite(self, test_module: str) -> tuple[int, str]:
        """(returncode, combined text) for the suite at `test_module`. -1 means it never finished.

        Two things this must not do: count "Ran 0 tests" as a pass (a suite that ran nothing
        verifies nothing -- the tree has measured that exact vacuity), and refuse to use the
        project's own declared runner when its tests are written for pytest and unittest
        therefore collects none.
        """
        if self._dir is None:
            return -1, "no project"
        try:
            done = subprocess.run(
                [self._python, "-m", "unittest", test_module],
                cwd=str(self._dir), capture_output=True, timeout=CALL_LIMIT_S,
                env=self._env(),
            )
        except subprocess.TimeoutExpired:
            return -1, "CHECK_TIMED_OUT"
        except OSError as error:
            return -1, f"{type(error).__name__}: {error}"
        text = (done.stdout + done.stderr).decode("utf-8", errors="replace")
        if "Ran 0 tests" in text:
            if not self._pytest_importable():
                return 5, text
            target = self._path_of(test_module)
            if target is None:
                return 5, text
            try:
                done = subprocess.run(
                    [self._python, "-m", "pytest", str(target), "-q", "-p", "no:cacheprovider"],
                    cwd=str(self._dir), capture_output=True, timeout=CALL_LIMIT_S,
                    env=self._env(),
                )
            except subprocess.TimeoutExpired:
                return -1, "CHECK_TIMED_OUT"
            except OSError as error:
                return -1, f"{type(error).__name__}: {error}"
            text = (done.stdout + done.stderr).decode("utf-8", errors="replace")
            return (5 if done.returncode == 5 else done.returncode), text
        return done.returncode, text

    def _pytest_importable(self) -> bool:
        try:
            done = subprocess.run(
                [self._python, "-c", "import pytest"],
                capture_output=True, timeout=CALL_LIMIT_S, env=self._env(),
            )
        except (subprocess.TimeoutExpired, OSError):
            return False
        return done.returncode == 0

    def _runs(self, test_module: str) -> tuple[bool, str]:
        if self._dir is None or test_module is None:
            return False, "CHECK_NO_TEST_MODULE"
        code, text = self._suite(test_module)
        if code == -1:
            return False, "CHECK_TIMED_OUT"
        if code == 5:
            return False, "CHECK_NO_DISCOVERABLE_TESTS"
        passed = code == 0
        if passed == (self.expect == "PASS"):
            return True, ""
        if "ModuleNotFoundError" in text or "ImportError" in text:
            for name in _missing_module_names(text):
                if name not in self.missing_modules:
                    self.missing_modules.append(name)
            return False, "CHECK_DEPENDENCY_MISSING"
        return False, ("CHECK_FAILS_ON_THE_ORIGINAL" if self.expect == "PASS"
                       else "CHECK_PASSES_ON_A_BROKEN_FILE")

    # ---------------------------------------------------------------- standing the environment
    def _declared_dependencies(self) -> tuple[str, list[str]] | None:
        """What the project itself declares: (source-kind, pip arguments), or None.

        Only the project's own words count -- requirements*.txt, pyproject.toml's
        project.dependencies, setup.py's install_requires, setup.cfg. A dependency the project
        never declares is reported as CHECK_DEPENDENCY_MISSING still, because guessing package
        names is a new way to be confidently wrong.
        """
        if self._dir is None:
            return None
        requirements = sorted(
            p for p in self._dir.glob("requirements*.txt") if p.is_file()
        )
        if requirements:
            args: list[str] = []
            for path in requirements:
                args += ["-r", str(path)]
            return "requirements_txt", args
        pyproject = self._dir / "pyproject.toml"
        if pyproject.is_file():
            try:
                import tomllib
                data = tomllib.loads(pyproject.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                data = {}
            declared = list((((data.get("project") or {}).get("dependencies")) or []))
            for group in (((data.get("project") or {}).get("optional-dependencies") or {}).values()):
                declared += list(group or [])
            if declared:
                return "pyproject", list(declared)
        setup_py = self._dir / "setup.py"
        if setup_py.is_file():
            import ast
            try:
                tree = ast.parse(setup_py.read_text(encoding="utf-8", errors="replace"))
            except (SyntaxError, ValueError, RecursionError, MemoryError):
                tree = None
            if tree is not None:
                found: list[str] = []

                def take(value: Any) -> None:
                    if isinstance(value, (ast.List, ast.Tuple)):
                        found.extend(e.value for e in value.elts
                                     if isinstance(e, ast.Constant) and isinstance(e.value, str))
                    elif isinstance(value, ast.Dict):   # extras_require = {"test": [...]}
                        for inner in value.values:
                            take(inner)

                for node in ast.walk(tree):
                    if isinstance(node, ast.keyword) and node.arg in (
                            "install_requires", "tests_require", "extras_require"):
                        take(node.value)
                    if isinstance(node, ast.Dict):
                        for key, value in zip(node.keys, node.values):
                            if isinstance(key, ast.Constant) and key.value in (
                                    "install_requires", "tests_require", "extras_require"):
                                take(value)
                if found:
                    return "setup_py", found
        setup_cfg = self._dir / "setup.cfg"
        if setup_cfg.is_file():
            import configparser
            parser = configparser.ConfigParser()
            try:
                parser.read_string(setup_cfg.read_text(encoding="utf-8", errors="replace"))
            except configparser.Error:
                pass
            if parser.has_option("options", "install_requires"):
                lines = [line.strip() for line in
                         parser.get("options", "install_requires").splitlines()]
                lines = [line for line in lines if line and not line.startswith("#")]
                if lines:
                    return "setup_cfg", lines
        return None

    def _stand_dependencies(self) -> bool:
        """Install what the project declares into an isolated venv, then re-run is the caller's job.

        This is the step the previous round named and could not do: 6 of 12 real tasks were
        CHECK_DEPENDENCY_MISSING, and a missing dependency is the difference between "cannot
        verify" and "can verify". One venv per Check, outside the project copy, reused by every
        pair of that task. Failure is reported by name (INSTALL_FAILED with pip's tail), never
        papered over.
        """
        if self.standing.get("attempted"):
            return bool(self.standing.get("outcome") == "STOOD")
        self.standing["attempted"] = True
        declared = self._declared_dependencies()
        if declared is None:
            self.standing.update(outcome="NO_DECLARED_DEPENDENCIES")
            return False
        source, args = declared
        try:
            venv_dir = tempfile.mkdtemp(prefix="rung-venv-")
            made = subprocess.run([sys.executable, "-m", "venv", venv_dir],
                                  capture_output=True, timeout=180)
            if made.returncode != 0:
                shutil.rmtree(venv_dir, ignore_errors=True)
                self.standing.update(outcome="VENV_FAILED", source=source,
                                     detail=made.stderr.decode("utf-8", "replace")[-400:])
                return False
            self._venv_dir = venv_dir
            python = pathlib.Path(venv_dir) / "bin" / "python"
            code, error_tail = self._pip_install(str(python), args)
            if code != 0:
                shutil.rmtree(venv_dir, ignore_errors=True)
                self._venv_dir = None
                self.standing.update(outcome="INSTALL_FAILED", source=source, detail=error_tail)
                return False
        except (subprocess.TimeoutExpired, OSError) as error:
            self.standing.update(outcome="INSTALL_FAILED", source=source,
                                 detail=f"{type(error).__name__}: {error}")
            return False
        self._python = str(python)
        self.standing.update(outcome="STOOD", source=source, detail="")
        return True

    def _manifest_mentions(self, root: str) -> bool:
        """Whether the project's own manifest text spells out this package name.

        The literal parser in `_declared_dependencies` reaches what is written as a list; this
        reaches what is written any other way (read('requirements.txt'), extras built in a
        comprehension, a dev file). Either way the word is the project's -- which is the line
        between standing up a dependency and guessing one.
        """
        if self._dir is None:
            return False
        texts: list[str] = []
        for pattern in ("requirements*.txt", "pyproject.toml", "setup.py", "setup.cfg",
                        "Pipfile", "tox.ini"):
            for path in sorted(self._dir.glob(pattern)):
                if path.is_file():
                    try:
                        texts.append(path.read_text(encoding="utf-8", errors="replace"))
                    except OSError:
                        continue
        joined = "\n".join(texts).lower().replace("-", "_")
        return root.lower() in joined

    def _make_venv(self) -> bool:
        if self._venv_dir:
            return True
        try:
            venv_dir = tempfile.mkdtemp(prefix="rung-venv-")
            made = subprocess.run([sys.executable, "-m", "venv", venv_dir],
                                  capture_output=True, timeout=180)
            if made.returncode != 0:
                shutil.rmtree(venv_dir, ignore_errors=True)
                return False
            self._venv_dir = venv_dir
            self._python = str(pathlib.Path(venv_dir) / "bin" / "python")
            return True
        except (subprocess.TimeoutExpired, OSError):
            return False

    def _repair_missing(self) -> bool:
        """Install the still-missing modules the project's manifests NAME, once each.

        Runs after standing: the declared list got installed and the suite still cannot import
        something. If the project spells the name out anywhere in its manifests, install it; if
        it does not, install nothing (NO_DECLARED stays honest). Returns whether an install was
        attempted, so the caller knows a re-run could differ.
        """
        if not self.missing_modules or self._dir is None:
            return False
        todo: list[str] = []
        for name in self.missing_modules:
            root = name.split(".")[0].replace("-", "_").lower()
            if not root or root in self._repaired:
                continue
            if self._manifest_mentions(root):
                todo.append(root)
        if not todo:
            return False
        if not self._make_venv():
            return False
        succeeded = False
        for root in todo:
            code, tail = self._pip_install(self._python, [root])
            self._repaired.append(root)
            if code == 0:
                self.standing.setdefault("repaired", []).append(root)
                succeeded = True
            else:
                self.standing.setdefault("repair_failures", {})[root] = tail
        if not succeeded and self.standing.get("outcome") != "STOOD":
            # nothing was ever installed: a venv that holds nothing verifies nothing
            shutil.rmtree(self._venv_dir, ignore_errors=True)
            self._venv_dir = None
            self._python = sys.executable
        return succeeded

    def _pip_install(self, python: str, args: Sequence[str]) -> tuple[int, str]:
        """The one place that talks to the package index.

        Kept as its own method so a test can stand a dependency in without a network (the index
        itself is proven separately, on the real corpus), and so a failure keeps pip's tail for
        the record instead of a bare boolean.
        """
        done = subprocess.run(
            [python, "-m", "pip", "install", "--quiet", "--no-input",
             "--disable-pip-version-check", *args],
            capture_output=True, timeout=480,
            env={"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": self._venv_dir or "/tmp"},
        )
        return done.returncode, done.stderr.decode("utf-8", "replace")[-400:]

    def _env(self) -> dict[str, str]:
        import os
        path = os.environ.get("PATH", "/usr/bin:/bin")
        if self._venv_dir:
            path = str(pathlib.Path(self._venv_dir) / "bin") + os.pathsep + path
        return {"PATH": path,
                "PYTHONPATH": str(self._dir) if self._dir else "",
                "HOME": str(self._dir) if self._dir else "/tmp"}

    @staticmethod
    def _project(files: Mapping[str, str]) -> pathlib.Path:
        """A copy of the pull request's files, so a test run cannot touch anything real."""
        directory = pathlib.Path(tempfile.mkdtemp(prefix="rung-check-"))
        for path, text in files.items():
            destination = directory / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            try:
                destination.write_text(text, encoding="utf-8")
            except OSError:
                continue
        return directory

    def accepts(self, path: str, candidate: str) -> bool:
        self.asked += 1
        if self.kind == "identity":
            self.settled += 1
            return True
        if self._dir is None:
            return False
        # The oracle for THIS file is the test module that imports THIS file. The first version of
        # this class bound one entry (the record's first path) to every path of the task, so a file
        # whose own tests never ran could be judged by a sibling's suite -- a check for the wrong
        # file is not a weaker check, it is a different claim.
        chosen, _candidates, _confidence = self._test_entry(path)
        if chosen is None:
            self.path_reasons["CHECK_NO_TEST_MODULE"] = self.path_reasons.get(
                "CHECK_NO_TEST_MODULE", 0) + 1
            return False
        written = self._dir / path
        original = self.originals.get(path)
        if original is None:
            return False
        ok = False
        try:
            written.write_text(candidate, encoding="utf-8")
            code, text = self._suite(chosen)
            if code == -1:
                self.path_reasons["CHECK_TIMED_OUT"] = self.path_reasons.get("CHECK_TIMED_OUT", 0) + 1
            elif code == 5:
                self.path_reasons["CHECK_NO_DISCOVERABLE_TESTS"] = self.path_reasons.get(
                    "CHECK_NO_DISCOVERABLE_TESTS", 0) + 1
            elif code != 0 and ("ModuleNotFoundError" in text or "ImportError" in text):
                # The suite cannot import: this is where the project's declared dependencies get
                # one standing attempt per check (never once per candidate), followed by the
                # manifest-named repair for whatever is still missing.
                for name in _missing_module_names(text):
                    if name not in self.missing_modules:
                        self.missing_modules.append(name)
                self._stand_dependencies()
                repaired = self._repair_missing()
                if repaired or self._venv_dir:
                    code, after = self._suite(chosen)
                    for name in _missing_module_names(after):
                        if name not in self.missing_modules:
                            self.missing_modules.append(name)
                    ok = code == 0
                    if not ok and ("ModuleNotFoundError" in after or "ImportError" in after):
                        self.path_reasons["STILL_MISSING_AFTER_STANDING"] = self.path_reasons.get(
                            "STILL_MISSING_AFTER_STANDING", 0) + 1
                else:
                    outcome = str(self.standing.get("outcome", "INSTALL_FAILED"))
                    self.path_reasons[outcome] = self.path_reasons.get(outcome, 0) + 1
            else:
                # A CANDIDATE is accepted when the check passes on it, in both modes. `expect` is
                # about the file as it was found (a migration already works, a repair does not); it
                # does not flip what "accepted" means. Inverting this made the tool accept edits
                # that left the tests FAILING -- the exact opposite of what an oracle is for.
                ok = code == 0
        except (subprocess.TimeoutExpired, OSError):
            ok = False
        finally:
            written.write_text(original, encoding="utf-8")   # the ORIGINAL, not the candidate
        if ok:
            self.settled += 1
        return ok

    def close(self) -> None:
        if self._dir is not None:
            shutil.rmtree(self._dir, ignore_errors=True)
        if self._venv_dir:
            shutil.rmtree(self._venv_dir, ignore_errors=True)
            self._venv_dir = None


# --------------------------------------------------------------------------- #
# the arms
# --------------------------------------------------------------------------- #
def _learned(examples: Sequence[tuple[str, str]]) -> Any:
    lessons = ladder.Lessons()
    for index, (before, after) in enumerate(examples):
        try:
            lessons.learn(f"e{index}", before, after)
        except ValueError:
            pass
    return lessons


def _apply_everywhere(lessons: Any, source: str, check: Check | None = None,
                      path: str = "", at_most: int = 12) -> str | None:
    """Apply the best-supported rung of the lesson at every place it fits, not at one place.

    The first version of this tool took only the first candidate, so it edited one line where the
    shipped organ edits every fitting line -- and then the comparison read as "the ladder is worse"
    when it was really measuring "one edit vs all edits". Repeated here so the arms differ only in
    which rung they use and whether a check gates them. Stops when the lesson stops fitting, when
    the text would not change, or after `at_most` steps (a lesson that keeps fitting its own output
    is a loop, and a loop is not a generalisation).
    """
    current = source
    for _ in range(at_most):
        proposals = lessons.proposals(current, limit=MAX_CANDIDATES)
        settled = None
        for row in proposals:
            if check is not None and not check.accepts(path, row["source"]):
                continue
            settled = row["source"]
            break
        if settled is None or settled == current:
            break
        current = settled
    return current if current != source else None


def _one_place_at_a_time(source: str, lesson: Any, check: Check, path: str,
                         proposals: Sequence[Mapping[str, Any]]) -> str | None:
    """The tree's `repeat_tried` shape, cut down: propose one place, keep what the check settles.

    This is the arm that matters for the owner's plan, because it needs no correct demonstration --
    only a check. It was written wrongly once (an empty `Lessons()` was asked for proposals, so the
    arm could never propose anything and read as "no oracle helps"). The lesson is passed in.
    """
    for row in proposals:
        if check.accepts(path, row["source"]):
            return row["source"]
    return None


def arms(files: Sequence[Mapping[str, str]], check: Check, two_showings: bool) -> dict[str, Any]:
    """Every drawn file as the demonstration for every other, for each arm."""
    totals: dict[str, dict[str, int]] = {
        arm: {"pairs": 0, "reached": 0, "right": 0, "wrong": 0, "asked": 0, "edited": 0,
              "check_asked": 0, "check_right": 0, "check_wrong": 0}
        for arm in ("literal", "exact", "two_showings", "any_rung", "any_rung_check", "check_only")
    }
    by_rung: dict[str, int] = {}
    per_file: list[dict[str, Any]] = []

    def note(arm: str, result: Mapping[str, int], edited: bool) -> None:
        row = totals[arm]
        row["pairs"] += 1
        row["reached"] += int(result["asked"] == 0)
        row["right"] += result["right"]
        row["wrong"] += result["wrong"]
        row["asked"] += result["asked"]
        row["edited"] += int(edited)

    for index, example in enumerate(files):
        for other, target in enumerate(files):
            if other == index:
                continue
            got, why = _exact(target["before"], example["before"], example["after"])
            note("exact", score(target["before"], target["after"], got), got is not None)

            # literal: the changed text must already be in the target
            literal = _literal(target["before"], example["before"], example["after"])
            note("literal", score(target["before"], target["after"], literal), literal is not None)

            if two_showings:
                second = files[(index + 1) % len(files)]
                if second is not example:
                    joined_before = example["before"].rstrip("\n") + "\n\n\n" + second["before"]
                    joined_after = example["after"].rstrip("\n") + "\n\n\n" + second["after"]
                    got2, _ = _exact(target["before"], joined_before, joined_after)
                    note("two_showings", score(target["before"], target["after"], got2), got2 is not None)

            lessons = _learned([(example["before"], example["after"])])
            proposals = lessons.proposals(target["before"], limit=MAX_CANDIDATES)
            if proposals:
                by_rung[proposals[0]["openness"]] = by_rung.get(proposals[0]["openness"], 0) + 1
            picked = _apply_everywhere(lessons, target["before"])
            note("any_rung", score(target["before"], target["after"], picked), picked is not None)

            settled = _apply_everywhere(lessons, target["before"], check=check,
                                        path=str(target["path"]))
            result = score(target["before"], target["after"], settled)
            note("any_rung_check", result, settled is not None)
            totals["any_rung_check"]["check_asked"] += 1
            if settled is not None:
                totals["any_rung_check"]["check_right"] += result["right"]
                totals["any_rung_check"]["check_wrong"] += result["wrong"]

            tried = _one_place_at_a_time(target["before"], lessons, check, str(target["path"]),
                                         proposals)
            note("check_only", score(target["before"], target["after"], tried), tried is not None)

        per_file.append({"path": example["path"]})
    return {"totals": totals, "by_rung": by_rung, "per_file": per_file}


def _exact(target: str, example_before: str, example_after: str) -> tuple[str | None, str | None]:
    """The shipped learner exactly as `main` has it -- this is the arm the owner calls Problem 2."""
    from canonical.swe_kernel.taught_actions import edit_by_example_v1 as organ
    try:
        return organ.edit_by_example(target, example_before, example_after), None
    except organ.Refused as why:
        return None, "refused: " + str(why)
    except Exception as error:
        return None, f"error: {type(error).__name__}"


def _literal(target: str, example_before: str, example_after: str) -> str | None:
    """Copy the change only where the changed text is already standing there."""
    lessons = _learned([(example_before, example_after)])
    for row in lessons.proposals(target, limit=MAX_CANDIDATES):
        if row["openness"] == "as_it_was":
            return row["source"]
    return None


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #
def summarise(measured: Mapping[str, Any]) -> dict[str, Any]:
    totals = measured["totals"]
    out = {"tasks": measured.get("tasks", 0), "pairs": measured.get("pairs", 0)}
    for arm, row in totals.items():
        out[arm] = {
            "pairs": row["pairs"],
            "nothing_to_generalise": row["reached"],
            "edited": row["edited"],
            "right": row["right"],
            "wrong": row["wrong"],
            "precision": (round(row["right"] / (row["right"] + row["wrong"]), 4)
                          if (row["right"] + row["wrong"]) else None),
            "asked": row["asked"],
            "share_of_the_work": round(row["right"] / row["asked"], 4) if row["asked"] else None,
        }
    out["by_rung"] = measured.get("by_rung", {})
    blocked = measured.get("check_unavailable_pairs", 0)
    out["check_unavailable_pairs"] = blocked
    return out


def report(result: Mapping[str, Any], say: Callable[[str], None] = print) -> None:
    say(f"\n{result['schema']}  authority {AUTHORITY}\n")
    demo_rows = result.get("demo")
    if demo_rows:
        say("ONE DEMONSTRATION, THE LEARNER'S OWN SIX RUNGS  "
            f"({demo_rows['operators_from_one_demonstration']} rungs written down)")
        say(f"  {'target':64s} {'asks':6s} reached  used")
        for row in demo_rows["targets"]:
            used = "-" if row["by_rung"] is None else f"{row['by_rung']['openness']}/{row['by_rung']['surroundings']}"
            say(f"  {row['label'][:64]:64s} {row['asks']:6s} {str(row['reached']):7s} {used}")
            if row["candidate_line"]:
                say(f"      -> {row['candidate_line']}")
        say("")

    totals = result.get("totals") or {}
    if totals:
        say("ON REAL MERGED PULL REQUESTS  (one demonstration, then every other file)")
        say(f"  {'arm':16s} {'pairs':>6s} {'edited':>7s} {'right':>6s} {'wrong':>6s} "
            f"{'precision':>9s} {'of the work':>11s}")
        for arm in ("literal", "exact", "two_showings", "any_rung", "any_rung_check", "check_only"):
            row = totals.get(arm)
            if not row:
                continue
            made = row["right"] + row["wrong"]
            precision = f"{row['right'] / made:.3f}" if made else "-"
            share = f"{row['right'] / row['asked']:.3f}" if row["asked"] else "-"
            say(f"  {arm:16s} {row['pairs']:6d} {row['edited']:7d} {row['right']:6d} "
                f"{row['wrong']:6d} {precision:>9s} {share:>11s}")
        unavailable = result.get("check_unavailable_pairs", 0)
        if unavailable:
            say(f"\n  the check was unavailable on {unavailable} pairs (no test module imports the file)")
        control = result.get("positive_control")
        if control is not None:
            say(f"\n  POSITIVE CONTROL (a project that ships a check): discriminates="
                f"{control.get('discriminates')}  module={control.get('module')}")
            for key in ("accepts_the_project_as_it_is", "accepts_the_correct_edit",
                        "rejects_a_wrong_edit_that_still_compiles", "rejects_a_broken_file"):
                if key in control:
                    say(f"    {key:44s} {control[key]}")
        if result.get("check_reasons"):
            say("\n  WHY THE CHECK COULD NOT RUN (one line per task, not per pair)")
            for reason, count in sorted(result["check_reasons"].items(), key=lambda kv: -kv[1]):
                say(f"    {reason:30s} {count:3d}")
        oracle = result.get("oracle_when_one_exists")
        if oracle:
            say("\n  THE SAME LESSON WITH AND WITHOUT A CHECK (constructed: three modules, one test each)")
            for path, row in oracle["arms"].items():
                say(f"    {path:18s} check={row['check_available']}  "
                    f"without: edited={row['without_a_check']['edited']} correct="
                    f"{row['without_a_check']['is_the_correct_edit']}  "
                    f"with: edited={row['with_a_check']['edited']} correct="
                    f"{row['with_a_check']['is_the_correct_edit']}")
        if result.get("by_rung"):
            say("\n  WHICH RUNG FIRED (any_rung arm, first proposal)")
            for rung, count in sorted(result["by_rung"].items(), key=lambda kv: -kv[1]):
                say(f"    {rung:20s} {count:5d}")


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--demo", action="store_true", help="offline: the ladder, no network")
    parser.add_argument("--collect", type=pathlib.Path, default=None, help="write the pull requests here, with their files")
    parser.add_argument("--pulls", type=pathlib.Path, default=None, help="a collected file to measure on")
    parser.add_argument("--check", choices=("tests", "identity"), default="identity")
    parser.add_argument("--files", type=int, default=4)
    parser.add_argument("--per-query", type=int, default=2)
    parser.add_argument("--cache", type=pathlib.Path, default=None,
                        help="keep the fetched texts here; a re-run reads them instead of GitHub")
    parser.add_argument("--labels", default=None,
                        help="comma-separated owner/repo#number: collect exactly these pulls "
                             "(re-taking a record's corpus by name instead of by search)")
    parser.add_argument("--out", type=pathlib.Path, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.demo:
        result = {"schema": SCHEMA, "authority": AUTHORITY, "demo": demo()}
        report(result)
        if args.out:
            args.out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return 0

    if args.collect:
        queries = (
            "assertEquals assertEqual",
            "isAlive is_alive",
            "deprecated logging.warn",
            "replace assertRaisesRegexp",
            "use f-string instead of format",
            "remove six Python 2 compatibility",
        )
        pulled = collect(queries, args.per_query, args.files, print)
        args.collect.write_text(json.dumps(without_texts(pulled), indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"\n{len(pulled)} pull requests -> {args.collect}  (texts not kept; hashes are)")
        return 0

    if args.labels:
        pulled = []
        for label in [part.strip() for part in args.labels.split(",") if part.strip()]:
            head, _, num = label.rpartition("#")
            owner, _, repo = head.partition("/")
            if not owner or not repo or not num.isdigit():
                parser.error(f"--labels: {label!r} is not owner/repo#number")
            pull = collect_pull(owner, repo, int(num), args.files, print, query="--labels")
            if pull is None:
                print(f"  {label}: passed over")
                continue
            pulled.append(pull)
            time.sleep(1)
        if not pulled:
            parser.error("--labels collected no pull requests")
    elif args.pulls:
        recorded = json.loads(args.pulls.read_text(encoding="utf-8"))
        cached = {}
        if args.cache and args.cache.is_file():
            cached = {item["name"]: item for item in json.loads(args.cache.read_text(encoding="utf-8"))}
        pulled = []
        for item in recorded:
            if item["name"] in cached:
                pulled.append(cached[item["name"]])
            else:
                pulled.extend(fetch_again([item]))
            time.sleep(1)
        if args.cache:
            args.cache.write_text(json.dumps(pulled, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    else:
        parser.error("give --demo, --collect, --labels or --pulls")
    result: dict[str, Any] = {"schema": SCHEMA, "authority": AUTHORITY,
                              "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                              "check": args.check, "model_calls": 0, "incremental_spend_usd": 0}

    merged: dict[str, dict[str, int]] = {}
    by_rung: dict[str, int] = {}
    reasons: dict[str, int] = {}
    per_task: list[dict[str, Any]] = []
    unavailable = 0
    for pull in pulled:
        project = pull.get("project") or {f["path"]: f["before"] for f in pull["files"]}
        for drawn in pull["files"]:        # the drawn files are the ones being changed
            project[drawn["path"]] = drawn["before"]
        check = Check(args.check, project, str(pull["files"][0]["path"]))
        measured = arms(pull["files"], check, two_showings=True)
        unavailable += 0 if check.available else len(pull["files"]) * (len(pull["files"]) - 1)
        why = check.reason or ("available" if check.available else "unknown")
        reasons[why] = reasons.get(why, 0) + 1
        per_task.append({"name": pull["name"], "files": len(pull["files"]),
                         "check": why, "test_module": check._test,
                         "test_entry_confidence": check.test_entry.get("confidence", "NONE"),
                         "test_entry_candidates": len(check.test_entry.get("candidates", [])),
                         "standing": dict(check.standing),
                         "path_reasons": dict(check.path_reasons),
                         "missing_modules": list(check.missing_modules),
                         "right_exact": measured["totals"]["exact"]["right"],
                         "wrong_exact": measured["totals"]["exact"]["wrong"],
                         "right_any_rung": measured["totals"]["any_rung"]["right"],
                         "wrong_any_rung": measured["totals"]["any_rung"]["wrong"]})
        check.close()
        for arm, row in measured["totals"].items():
            heap = merged.setdefault(arm, {"pairs": 0, "reached": 0, "right": 0, "wrong": 0,
                                           "asked": 0, "edited": 0, "check_asked": 0,
                                           "check_right": 0, "check_wrong": 0})
            for key in heap:
                heap[key] += row[key]
        for rung, count in measured["by_rung"].items():
            by_rung[rung] = by_rung.get(rung, 0) + count
        print(f"  {pull['name']:45s} {len(pull['files'])} files  "
              f"right(exact)={measured['totals']['exact']['right']:4d} "
              f"wrong(exact)={measured['totals']['exact']['wrong']:4d} "
              f"right(rung)={measured['totals']['any_rung']['right']:4d}")

    result.update(totals=merged, by_rung=by_rung, tasks=len(pulled),
                  check_reasons=reasons, per_task=per_task,
                  positive_control=positive_control() if args.check == "tests" else None,
                  pairs=sum(row["pairs"] for row in merged.values()) // 6,
                  check_unavailable_pairs=unavailable)
    result["summary"] = summarise(result)
    result["oracle_when_one_exists"] = oracle_makes_the_difference()
    report(result)
    if args.out:
        args.out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"\nWROTE {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
