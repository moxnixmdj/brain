"""An unseen directory must be able to say what it can do.

THE OWNER'S IDEA, AND WHY IT NEEDED A NEW ORGAN.

    "All he should do is basically go into any new arbitrary environment in the computer and he
     doesn't know anything about anything... All he should do is scan everything in the environment
     and then retrieve from his memory what he knows and what he doesn't know."

Measured 2026-11-23, that did not happen. A directory with two honest callables, asked a question
they can answer, got `document.convert.markdown_pdf.pandoc_weasyprint` from the registry and
ACTION_FAILED. Every selector in the tree starts from a fixed registry, so a function the machine has
never met cannot even be a candidate -- which means "learn from one experience in a new environment"
had no first step.

`room_census_v1` is that step: a directory -> its callables, described by their own docstrings and
signatures, ranked by the BM25 scorer the tree already owns. It executes nothing and admits nothing.

These tests assert the properties that make it worth having, and nothing about a particular day's
score: that meaning comes from the docstring, that private functions are not offered, that an
unreadable file does not take the survey down, that a room with no vocabulary is UNRESOLVED rather
than a crash, and that the whole path -- survey, find the gap, forge, act -- lands on the right
function and returns the right numbers.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import uuid
import sys
import textwrap

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import room_census_v1 as RC  # noqa: E402


@pytest.fixture()
def room(tmp_path):
    """A directory nobody registered, holding a real csv tool and some noise."""
    (tmp_path / "census.py").write_text(textwrap.dedent('''
        """Summarise a csv by column."""
        import csv

        def profile(path):
            """Per-column fill rate and numeric rate for a csv file."""
            rows = list(csv.DictReader(open(path)))
            cols = {}
            for name in rows[0]:
                vals = [r.get(name, "") for r in rows]
                filled = sum(1 for v in vals if v.strip())
                cols[name] = {"fill_rate": round(filled / len(vals), 3)}
            return {"columns": cols, "rows": len(rows)}

        def _private(x):
            """Not offered: a leading underscore is not a callable a person means."""
            return x

        def trailing_comma(n, sep=","):
            """Format a number with a trailing separator."""
            return str(n) + sep
    '''), encoding="utf-8")
    (tmp_path / "broken.py").write_text("def oops(:\n  this is not python\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("not python at all\n", encoding="utf-8")
    return tmp_path


def test_a_room_is_read_as_callables_not_files(room):
    """The unit of a census is a FUNCTION, because a function is what can be called."""
    found = RC.survey(str(room))
    assert found["status"] == "SURVEYED"
    names = [f["function"] for f in found["functions"]]
    assert "profile" in names and "trailing_comma" in names, names
    # reading is bounded and honest about what it did
    assert found["files_read"] >= 1


def test_a_private_function_is_not_offered(room):
    """`_private` is the author saying "not for you". A census that lists it wastes a demonstration."""
    names = {f["function"] for f in RC.survey(str(room))["functions"]}
    assert "_private" not in names, names


def test_meaning_comes_from_the_docstring_not_the_name(room):
    """`profile` alone could be a profiler, a user profile, or this column report. The docstring says."""
    rows = {f["function"]: f for f in RC.survey(str(room))["functions"]}
    assert "fill rate" in rows["profile"]["doc"], rows["profile"]["doc"]
    # and the signature is read from source, never guessed
    assert rows["profile"]["params"] == ["path"], rows["profile"]
    # a defaulted parameter is recorded as optional, with its default
    assert rows["trailing_comma"]["params"] == ["n", "sep"]
    assert rows["trailing_comma"]["defaults"].get("sep") == "','", rows["trailing_comma"]


def test_an_unreadable_file_does_not_take_the_survey_down(room):
    """A census is the first thing to run in a place nobody has vouched for."""
    found = RC.survey(str(room))
    assert found["status"] == "SURVEYED"
    assert any(f["function"] == "profile" for f in found["functions"])
    # the syntax-error file contributed nothing and did not raise
    assert all(f["source_rel"].endswith(".py") for f in found["functions"])


def test_the_gap_is_what_the_room_offers_minus_what_is_already_known(room):
    """`unknown_functions` is the owner's "what I know and what I don't", asked about a PLACE."""
    found = RC.survey(str(room))
    everything = RC.unknown_functions(found, [])
    assert len(everything) == len(found["functions"])
    # once a capability names it, it is no longer a gap
    known = ["forged.census.profile::profile"]
    remaining = {f["function"] for f in RC.unknown_functions(found, known)}
    assert "profile" not in remaining, remaining


def test_a_room_with_no_shared_vocabulary_is_unresolved_not_a_crash(room):
    """THE SCORER'S OWN BUG, MADE A TEST.

    `_bm25_scores` returned bare floats when every candidate document was empty and
    (score, contributions) tuples otherwise, so `rank` -- which unpacks the pair -- raised
    "cannot unpack non-iterable float object". An objective that shares no word with a room took the
    whole survey down instead of reporting that it found no relevance.
    """
    blank = {"schema": RC.SCHEMA, "functions": [
        {"function": "aaa", "source_rel": "x.py", "params": [], "doc": "", "text": ""},
        {"function": "bbb", "source_rel": "y.py", "params": [], "doc": "", "text": ""},
    ]}
    out = RC.rank(blank, "zzz qqq vvv")
    assert out["status"] == "RELEVANCE_UNRESOLVED", out
    assert out["ranked"] == []


def test_the_relevance_it_reports_is_the_scorer_s_own(room):
    """A copy of a measurement under a new name reads like a second measurement."""
    found = RC.survey(str(room))
    out = RC.rank(found, "profile the columns of a csv", limit=3)
    assert out["relevance_scope"] == "LEXICAL_BM25_OBJECTIVE_RELEVANCE_ONLY", out
    # the scorer is explicit that lexical relevance is not semantic entailment, and that
    # qualification must survive the adapter
    assert out["semantic_entailment_status"] == "UNVERIFIED", out
    assert out["ranked"], out
    for row in out["ranked"]:
        assert row["score"] == row.get("score")
        assert isinstance(row["score"], (int, float))


def test_a_zero_scored_candidate_is_not_offered_as_a_match():
    """`rank` returns every candidate it scored, including those sharing no term with the objective.

    Passing those through presents "nothing here is about this" as a ranked shortlist -- and the
    first version did exactly that. This room is MIXED on purpose: one candidate is genuinely about
    the objective and one is not, so the filter has something to remove. (An all-zero room cannot
    observe the filter at all, which is how the first version of this test let the mutant live.)
    """
    mixed = {"schema": RC.SCHEMA, "functions": [
        {"function": "profile", "source_rel": "a.py", "params": ["path"],
         "doc": "Per-column fill rate and numeric rate for a csv file.", "text": ""},
        {"function": "zzz_unrelated", "source_rel": "b.py", "params": [],
         "doc": "Completely different subject matter entirely.", "text": ""},
    ]}
    out = RC.rank(mixed, "profile the columns of a csv", limit=5)
    kept = [r["function"] for r in out["ranked"]]
    assert "profile" in kept, out
    assert "zzz_unrelated" not in kept, kept


def test_an_unreadable_room_is_a_limit_not_a_fact(tmp_path):
    """THE DIFFERENCE THAT MATTERS MOST IN AN ARBITRARY ENVIRONMENT.

    The first census globbed `*.py` only, so a directory holding just `tools.js` reported
    status SURVEYED with 0 functions -- byte-identical to an EMPTY directory. An empty room is a
    fact about the world; a room full of code in a language this reader cannot parse is a limit of
    the reader. A machine that conflates them reports "nothing to learn here" about a place that is
    full of things to learn, which is the exact failure this whole round exists to remove.
    """
    empty = tmp_path / "empty"
    empty.mkdir()
    js = tmp_path / "js"
    js.mkdir()
    (js / "tools.js").write_text("function f(x){ return x; }\n", encoding="utf-8")
    (js / "run.sh").write_text("#!/bin/sh\necho hi\n", encoding="utf-8")

    assert RC.survey(str(empty))["status"] == "EMPTY"
    unread = RC.survey(str(js))
    assert unread["status"] == "NO_READABLE_SOURCE", unread
    # and it names what it saw, rather than saying nothing was there
    assert unread["unreadable_source"] == {".js": 1, ".sh": 1}, unread
    assert unread["files_read"] == 0
    assert unread["functions"] == []

    # a python room in the same tree is still SURVEYED -- the distinction does not cost the normal case
    (js / "tool.py").write_text("def g(y):\n    \"\"\"Return y.\"\"\"\n    return y\n", encoding="utf-8")
    mixed = RC.survey(str(js))
    assert mixed["status"] == "SURVEYED"
    assert [f["function"] for f in mixed["functions"]] == ["g"]
    assert mixed["unreadable_source"] == {".js": 1, ".sh": 1}


def test_the_two_paths_answer_two_different_questions(room):
    """A room-relative path is what a person there says; the forge needs a repository path.

    Handed the room-relative name, `forge_and_record` resolved nothing and refused with
    RESEARCH_TOOL_PATH_INVALID and `ran: 0/3` -- which reads like the function being broken. It was
    not: the same row admitted at 2/3 with 8/8 mutations killed once given the path the importer can
    actually open. The survey read both, so it records both rather than making a caller reconstruct
    one from the other.
    """
    root = pathlib.Path(__file__).resolve().parents[2]
    found = RC.survey(str(room))
    row = {f["function"]: f for f in found["functions"]}["profile"]
    # what someone standing in the room would say
    assert row["source_rel"] == "census.py", row
    # and where the file actually is; tmp_path is outside the repo, so the honest answer is the
    # room-relative path -- never a fabricated prefix
    assert row["source_path"], row
    assert pathlib.Path(row["source_path"]).name == "census.py"


def test_the_entry_is_spelled_the_way_the_forge_reads_it(room):
    """`module` is the bare stem; `source_rel` is a real path. Mixing them up fails confusingly."""
    found = RC.survey(str(room))
    row = {f["function"]: f for f in found["functions"]}["profile"]
    entry = RC.forge_entry(row)
    assert entry["module"] == "census", entry
    assert entry["function"] == "profile", entry
    assert entry["required"] == ["path"], entry
    assert entry["source_rel"].endswith("census.py"), entry
    # nothing invented: keywords come from the function's own name and docstring
    assert "profile" in entry["keywords"], entry
    assert any("fill" in k or "csv" in k for k in entry["keywords"]), entry

def test_the_whole_loop_on_a_room_nobody_registered(monkeypatch):
    """THE OWNER'S SENTENCE, AS ONE ASSERTION.

        "scan everything in the environment and then retrieve from his memory what he knows and
         what he doesn't know"

    A directory the machine has never seen, holding one honest callable and a csv. Survey it, find
    the gap, demonstrate the function once, then act on the objective WITHOUT NAMING THE FUNCTION --
    and get the right numbers back. This is the path that, before this module, ended at
    `document.convert.markdown_pdf.pandoc_weasyprint` and ACTION_FAILED.

    The function is named uniquely per run ON PURPOSE. The forge persists what it admits, so a fixed
    name is already known on the second run -- the machine remembering across runs is the feature,
    and a test that assumes amnesia would be testing the wrong thing. A fresh name is also the honest
    simulation: a new environment does not contain yesterday's function.
    """
    root = pathlib.Path(__file__).resolve().parents[2]
    room = root / "canonical" / "astra_runtime" / "tmp" / "test_room_census_loop"
    shutil.rmtree(room, ignore_errors=True)
    room.mkdir(parents=True, exist_ok=True)
    (room / "__init__.py").write_text("", encoding="utf-8")

    fname = "parcel_count_" + uuid.uuid4().hex[:8]
    (room / "columnar.py").write_text(
        '"""Summarise a csv by column."""\n'
        "import csv\n\n\n"
        "def %s(path):\n"
        '    """Count shipped parcels in a logistics manifest file."""\n'
        "    rows = list(csv.DictReader(open(path)))\n"
        "    cols = {}\n"
        "    for name in rows[0]:\n"
        '        vals = [r.get(name, "") for r in rows]\n'
        '        filled = sum(1 for v in vals if v.strip())\n'
        '        cols[name] = {"fill_rate": round(filled / len(vals), 3)}\n'
        '    return {"columns": cols, "rows": len(rows)}\n' % fname,
        encoding="utf-8")
    data = room / "sample.csv"
    data.write_text("city,q1\nA,1\nB,\n", encoding="utf-8")

    from canonical.runtime import capability_forge_v1 as F, grounded_action_v1 as GA
    monkeypatch.chdir(root)

    census = RC.survey(str(room))
    assert census["status"] == "SURVEYED", census
    assert [f["function"] for f in census["functions"]] == [fname], census

    plan = RC.closing_plan(census, "count shipped parcels in a logistics manifest", list(GA.load_registry()))
    assert plan["unknown"] >= 1, plan
    assert fname in [n["function"] for n in plan["need"]], plan

    admitted = F.forge_and_record(RC.forge_entry(census["functions"][0]), root=root,
                                  seed_cases=[{"path": str(data)}])
    assert admitted["admitted"] is True, admitted

    try:
        acted = GA.act("count shipped parcels in the logistics manifest %s" % data, root=str(root))
        assert acted.get("status") == "VERIFIED_ACTION", acted
        assert acted.get("capability_id") == admitted["capability_id"], acted
        cols = (acted.get("result") or {})["columns"]
        assert cols["city"]["fill_rate"] == 1.0 and cols["q1"]["fill_rate"] == 0.5, cols
    finally:
        # A TEST THAT LEARNS MUST ALSO FORGET, OR THE MACHINE ACCUMULATES A ROW PER RUN.
        # The forge persists admissions by design; each run uses a fresh name, so without this the
        # state file grows without bound and every later registry load carries dead rows. The system
        # tolerates them (`_still_real` drops them at load), but a test that leaves litter is a test
        # whose next run is measuring something slightly different.
        _drop_forged(admitted.get("capability_id"))
        shutil.rmtree(room, ignore_errors=True)


def _drop_forged(cid):
    """Remove one forged row from persistent state, if it is there."""
    state = ROOT / "canonical" / "runtime" / "state" / "forged_capabilities_v1.json"
    if not cid or not state.is_file():
        return
    data = json.loads(state.read_text(encoding="utf-8"))
    if data.get("forged", {}).pop(cid, None) is not None:
        state.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def test_the_docstring_survives_the_handoff(room):
    """The census reads what a function is FOR and must not drop it on the way to the forge.

    Measured 2026-11-23: `forge_entry` carried name, params and paths but not `doc`, so an admitted
    capability whose docstring read "Sum a numeric column and return the total" carried the keywords
    `['summarise']` -- the function's name and nothing else. It was then invisible to the one
    question it existed to answer. Reading meaning and then discarding it is the same as never having
    read it, and the forge already had a slot (`contract["doc"]`) waiting for it.
    """
    found = RC.survey(str(room))
    row = {f["function"]: f for f in found["functions"]}["profile"]
    entry = RC.forge_entry(row)
    assert entry.get("doc"), entry
    assert "fill rate" in entry["doc"], entry
    # and the words that describe the work reach the keywords, rather than only the name
    assert any(w in entry["keywords"] for w in ("csv", "fill", "column")), entry


def test_a_big_room_says_how_much_of_it_was_read(tmp_path):
    """A survey that silently reads a fraction of a room is reporting a fact it does not have.

    On an installed stdlib directory the budget cut 665 python files to 400 and `budget` stayed None
    -- indistinguishable from having read everything. Coverage is now always stated, and it says
    whether anything guided the choice.
    """
    for i in range(12):
        (tmp_path / ("mod%02d.py" % i)).write_text(
            "def fn_%d():\n    \"\"\"Doing thing %d.\"\"\"\n    return {}\n" % (i, i),
            encoding="utf-8")
    full = RC.survey(str(tmp_path))
    assert full["status"] == "SURVEYED"
    assert full["budget"] is None, full
    assert len(full["functions"]) == 12, full

    cut = RC.survey(str(tmp_path), max_files=5)
    assert cut["budget"], cut
    assert "5 of 12" in cut["budget"], cut["budget"]
    assert cut["files_read"] == 5, cut

    aimed = RC.survey(str(tmp_path), max_files=5, objective="doing thing 7")
    assert aimed["budget"], aimed
    # only the files bearing on the objective need be read; it must not silently fall back to all
    assert aimed["files_read"] <= 5, aimed


def test_the_path_index_lists_the_room_without_reading_it(tmp_path):
    """Listing costs nothing and covers everything; reading is the expensive, budgeted part."""
    (tmp_path / "a.py").write_text("def f():\n    return {}\n", encoding="utf-8")
    (tmp_path / "b.js").write_text("function g(){}\n", encoding="utf-8")
    index = RC.source_index(str(tmp_path))
    assert index["status"] == "INDEXED"
    assert index["readable"] == ["a.py"], index
    assert index["unreadable_source"] == {".js": 1}, index
    assert len(index["files"]) == 2, index


def test_methods_in_a_class_are_callables_too(tmp_path):
    """A room whose answers are all METHODS must not present as nearly empty.

    `ast.walk` returns methods and module functions alike with nothing to tell them apart, so a class
    was invisible as a unit. Measured on an installed stdlib directory: argparse's entire public
    surface is `ArgumentParser.add_argument` / `parse_args`, and none of it was offered. The census
    now walks the structure, records the owner, and gives each callable a name a caller can use.
    """
    (tmp_path / "cli.py").write_text(
        'class ArgumentParser:\n'
        '    """Parse command line arguments."""\n'
        '    def parse_args(self, argv):\n'
        '        """Parse the arguments and return a namespace."""\n'
        '        return {"argv": argv}\n'
        '    def _secret(self):\n'
        '        return None\n'
        '\n'
        'def main(argv):\n'
        '    """Entry point."""\n'
        '    return ArgumentParser().parse_args(argv)\n',
        encoding="utf-8")
    found = RC.survey(str(tmp_path))
    rows = {f["call"]: f for f in found["functions"]}
    assert "ArgumentParser.parse_args" in rows, sorted(rows)
    assert rows["ArgumentParser.parse_args"]["owner"] == "ArgumentParser"
    # a private method is not offered, exactly like a private function
    assert "ArgumentParser._secret" not in rows, sorted(rows)
    # module-level functions are unchanged
    assert "main" in rows and rows["main"]["owner"] == ""
    # the owner's name is part of what the thing is, so it reaches the text the scorer reads
    assert "ArgumentParser" in rows["ArgumentParser.parse_args"]["text"]


def test_a_room_whose_answer_is_a_method_can_be_ranked_to_it(tmp_path):
    """The structural fix has to pay off in ranking, not just in listing."""
    (tmp_path / "cli.py").write_text(
        'class ArgumentParser:\n'
        '    """Parse command line arguments for a script."""\n'
        '    def parse_args(self):\n'
        '        """Parse the command line arguments into a namespace."""\n'
        '        return {}\n'
        '    def format_usage(self):\n'
        '        """Render a usage line."""\n'
        '        return ""\n',
        encoding="utf-8")
    plan = RC.closing_plan(RC.survey(str(tmp_path)),
                           "parse command line arguments for a script", ())
    top = [n["function"] for n in plan["need"]]
    assert top and top[0] == "parse_args", plan


def test_a_concatenated_name_is_reachable_from_the_words_a_person_says(tmp_path):
    """`argparse` is `arg`+`parse`; `difflib` is `diff`+`lib`. BM25 reads each as one opaque token.

    Measured 2026-11-23 on a real stdlib directory: argparse.py was not in the top 30 paths for the
    question argparse exists to answer, and difflib.py was invisible to "diff two strings". The split
    table is deterministic -- no weights, no training -- and it is checkable by eye, which is the
    point. Without it the survey reads a fraction of the room and cannot find the answer inside it.
    """
    assert "arg" in RC._expand_name("argparse")
    assert "parse" in RC._expand_name("argparse")
    assert "diff" in RC._expand_name("difflib")
    assert "path" in RC._expand_name("pathlib")

    names = {"argparse", "difflib", "script_helper", "urllib_parse", "unrelated_thing"}
    # "arguments" is the case that matters: it matches NOTHING in "argparse" exactly. Only the
    # prefix relationship arg <-> arguments connects them, and an exact-token check would miss it.
    got = RC._prefix_related(["arguments", "command", "script"], names)
    assert "argparse" in got, got
    got2 = RC._prefix_related(["diff", "two", "strings"], names)
    assert "difflib" in got2, got2

    # it must not match everything: an unrelated name stays out
    assert "unrelated_thing" not in got and "unrelated_thing" not in got2, (got, got2)
    # short query tokens are refused, or every name would match every objective
    assert RC._prefix_related(["a", "b"], names) == set()


def test_a_concatenated_filename_reaches_the_top_of_a_real_budget(tmp_path):
    """The point is not the helper; it is that the file gets READ when the budget is small."""
    for i in range(30):
        (tmp_path / ("filler_%02d.py" % i)).write_text(
            "def filler_%d():\n    \"\"\"Unrelated.\"\"\"\n    return {}\n" % i, encoding="utf-8")
    (tmp_path / "difflib.py").write_text(
        'def unified_diff(a, b):\n'
        '    """Compare two sequences of lines and return the differences."""\n'
        '    return []\n',
        encoding="utf-8")
    found = RC.survey(str(tmp_path), max_files=5,
                      objective="diff two unified strings line by line")
    calls = [f["call"] for f in found["functions"]]
    assert "unified_diff" in calls, calls
    assert found["files_read"] <= 5, found
