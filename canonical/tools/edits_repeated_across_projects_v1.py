#!/usr/bin/env python3
"""A change one project made, shown once, repeated on other projects -- compared with what the people there did.

    python3 canonical/tools/edits_repeated_across_projects_v1.py collect SET     # find the commits (uses `gh`)
    python3 canonical/tools/edits_repeated_across_projects_v1.py fetch [SET]     # download their files
    python3 canonical/tools/edits_repeated_across_projects_v1.py measure [SET]   # run the engine, print the table

The question this answers is narrow: when ``edit_by_example_v1`` is shown a change in one project and asked
to make it in a file of another project, does it write what the person there wrote?

Which commits.  ``KINDS`` names kinds of change (``yaml.load`` -> ``yaml.safe_load``), each with two search
words and a marker, a piece of text the old code holds.  For a kind, GitHub's commit search is asked for the
two words, and its answers are taken in the order given.  A commit is kept when its project was not yet
taken for this kind, it has one parent, it changes at most 40 files of which at most 10 are Python files
that existed before, and at least one of those files parses before and after and holds the marker more
often before than after.  Four commits are kept per kind; looking stops after twelve.  Nothing is chosen by
hand, and the kinds of a set are written here before its commits are looked at.

What is stored.  ``edits_repeated_across_projects_commits_v1.json`` holds, per kind, the project, the commit,
its parent and the file names.  Other people's code is not stored; ``fetch`` downloads it again into a
directory outside the repository.

How it is measured.  The first commit of a kind is the showing: its first kept file, before and after.
Every kept file of the kind's other commits is a file to edit, as it was before the person there changed
it.  What the engine writes is compared with what that person wrote, one statement at a time (a statement
with a block under it counts by its first line): the statements holding the marker that the person changed
one for one are the questions.  For each: the engine wrote the same, wrote something else, or left it; and,
apart from those, statements the engine changed that the person did not (`extra`), which are wrong edits.

Three ways of using the lesson are measured: `strict` is the `repeat` action, which refuses the whole file
when any fitting place is used a way the example did not show; `shown` is `repeat_shown`, which changes
the shown uses and leaves the rest; `tried` is `repeat_tried` with a check that settles every try -- the
most such a check can give, counting its `same` (tries a sufficient check keeps, rightly) and its `extra`
(tries only a sufficient check would catch; an insufficient one lets them through).

This measures agreement with people on changes of one kind.  It runs no test and solves no task.
Zero model calls.  Nothing here gives authority to anything.
"""
from __future__ import annotations

import argparse
import ast
import difflib
import json
import pathlib
import subprocess
import sys
import time
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMMITS = pathlib.Path(__file__).with_name("edits_repeated_across_projects_commits_v1.json")
CACHE = pathlib.Path("/tmp/edits_repeated_across_projects")
KEPT_PER_KIND, LOOKED_AT_PER_KIND, MOST_FILES, MOST_PYTHON_FILES = 4, 12, 40, 10

# (name, the two search words, the marker).  A set's kinds are fixed before its commits are collected.
KINDS = {
    # Kinds of the earlier measurements (2026-11-12, pull requests 6665 and 6686), as far as they were
    # written down, and others of the same sort.  The engine was designed while looking at such commits.
    "seen": [
        ("yaml_safe_load", "yaml.load safe_load", "yaml.load("),
        ("is_alive", "isAlive is_alive", ".isAlive("),
        ("encodebytes", "encodestring encodebytes", "encodestring("),
        ("read_file", "readfp read_file", ".readfp("),
        ("model_validate", "parse_obj model_validate", ".parse_obj("),
        ("tobytes", "tostring tobytes", ".tostring("),
        ("has_key", "has_key python3", ".has_key("),
        ("is_none", "\"== None\" \"is None\"", "== None"),
        ("logger_warning", "logger.warn logger.warning", ".warn("),
        ("assert_equal", "assertEquals assertEqual", "assertEquals("),
        ("utcnow", "utcnow timezone.utc", "utcnow()"),
        ("perf_counter", "time.clock perf_counter", "time.clock()"),
        ("getfullargspec", "getargspec getfullargspec", "getargspec("),
        ("model_dump", ".dict() model_dump", ".dict()"),
        ("iteritems", "iteritems items python3", ".iteritems()"),
        ("np_float", "np.float deprecated", "np.float"),
    ],
    # Written down on 2026-11-12 before any of their commits was collected, and run once.
    "held_out": [
        ("decodebytes", "decodestring decodebytes", "decodestring("),
        ("html_escape", "cgi.escape html.escape", "cgi.escape("),
        ("assert_regex", "assertRegexpMatches assertRegex", "assertRegexpMatches("),
        ("assert_count_equal", "assertItemsEqual assertCountEqual", "assertItemsEqual("),
        ("assert_not_equal", "assertNotEquals assertNotEqual", "assertNotEquals("),
        ("assert_almost_equal", "assertAlmostEquals assertAlmostEqual", "assertAlmostEquals("),
        ("assert_raises_regex", "assertRaisesRegexp assertRaisesRegex", "assertRaisesRegexp("),
        ("current_thread", "currentThread current_thread", "currentThread("),
        ("set_daemon", "setDaemon daemon", ".setDaemon("),
        ("notify_all", "notifyAll notify_all", ".notifyAll("),
        ("is_set", "isSet is_set", ".isSet("),
        ("frombytes", "fromstring frombytes", ".fromstring("),
        ("getchildren", "getchildren deprecated", ".getchildren()"),
        ("math_gcd", "fractions.gcd math.gcd", "fractions.gcd("),
        ("maxsize", "sys.maxint sys.maxsize", "sys.maxint"),
        ("izip", "izip zip python3", "izip("),
        ("force_str", "force_text force_str", "force_text("),
        ("gettext", "ugettext gettext django", "ugettext("),
        ("gettext_lazy", "ugettext_lazy gettext_lazy", "ugettext_lazy"),
        ("np_int", "np.int deprecated", "np.int"),
        ("np_bool", "np.bool deprecated", "np.bool"),
        ("np_item", "asscalar item", "asscalar("),
        ("isin", "in1d isin", "in1d("),
        ("np_prod", "np.product np.prod", "np.product("),
        ("as_matrix", "as_matrix values", ".as_matrix()"),
        ("df_loc", "ix loc pandas", ".ix["),
        ("torch_item", "data[0] item()", ".data[0]"),
        ("torch_sigmoid", "F.sigmoid torch.sigmoid", "F.sigmoid("),
        ("running_loop", "get_event_loop get_running_loop", "get_event_loop()"),
        ("fromtimestamp", "utcfromtimestamp fromtimestamp", "utcfromtimestamp("),
        ("yield_fixture", "yield_fixture fixture", "yield_fixture"),
        ("format_string", "locale.format format_string", "locale.format("),
        ("getcwd", "getcwdu getcwd", "getcwdu()"),
        ("ascii_letters", "string.letters ascii_letters", "string.letters"),
        ("itervalues", "itervalues values python3", ".itervalues()"),
        ("exception_message", "e.message str(e)", "e.message"),
        ("collections_abc", "collections.Mapping collections.abc", "collections.Mapping"),
        ("tf_cast", "to_float tf.cast", "tf.to_float("),
        ("text_mode", "universal_newlines text=True", "universal_newlines="),
        ("open_mode", "rU mode open", "'rU'"),
    ],
}


# ----------------------------------------------------------------------------- GitHub, through `gh`


def gh(arguments, raw=False, tries=4):
    """The answer of one `gh` call, parsed unless `raw`; None when GitHub has no such thing."""
    for attempt in range(tries):
        done = subprocess.run(["gh"] + arguments, capture_output=True)
        if done.returncode == 0:
            return done.stdout if raw else json.loads(done.stdout.decode("utf-8") or "null")
        problem = done.stderr.decode("utf-8", "replace")
        if "404" in problem or "Not Found" in problem or "No commit found" in problem:
            return None
        if "403" in problem or "rate limit" in problem.lower() or "secondary" in problem.lower():
            time.sleep(75)
        else:
            time.sleep(5)
    return None


def file_at(project, commit, path):
    """The bytes of one file of a project at a commit, from the cache or from GitHub; None when it is not there."""
    kept = CACHE / project.replace("/", "__") / commit / path.replace("/", "__")
    if kept.is_file():
        return kept.read_bytes()
    found = gh(["api", "-H", "Accept: application/vnd.github.raw",
                "repos/%s/contents/%s?ref=%s" % (project, urllib.parse.quote(path), commit)], raw=True)
    time.sleep(0.2)
    if found is not None:
        kept.parent.mkdir(parents=True, exist_ok=True)
        kept.write_bytes(found)
    return found


def parses(data):
    try:
        ast.parse(data.decode("utf-8"))
        return True
    except (SyntaxError, ValueError, UnicodeDecodeError, RecursionError):
        return False


def kept_files(project, commit, parent, names, marker):
    """The files of a commit that parse before and after and hold the marker more often before."""
    kept = []
    for name in names:
        before, after = file_at(project, parent, name), file_at(project, commit, name)
        if (before is not None and after is not None and parses(before) and parses(after)
                and before.count(marker.encode("utf-8")) > after.count(marker.encode("utf-8"))):
            kept.append(name)
    return kept


def collect(which):
    """Find the commits of every kind of a set and write them to the commits file."""
    held = json.loads(COMMITS.read_text()) if COMMITS.is_file() else {"sets": {}}
    if which in held["sets"]:
        raise SystemExit("the set %r is already collected; its commits are not collected a second time" % which)
    kinds = []
    for name, words, marker in KINDS[which]:
        found = gh(["search", "commits", words, "--limit", "30", "--json", "repository,sha"]) or []
        time.sleep(6)
        commits, projects, looked_at = [], set(), 0
        for answer in found:
            project = answer["repository"]["fullName"]
            if project in projects or len(commits) == KEPT_PER_KIND or looked_at == LOOKED_AT_PER_KIND:
                continue
            looked_at += 1
            detail = gh(["api", "repos/%s/commits/%s" % (project, answer["sha"])])
            time.sleep(0.2)
            if not detail or len(detail.get("parents") or []) != 1:
                continue
            files = detail.get("files") or []
            python = [one["filename"] for one in files if one.get("status") == "modified"
                      and one["filename"].endswith(".py")]
            if len(files) > MOST_FILES or not 0 < len(python) <= MOST_PYTHON_FILES:
                continue
            parent = detail["parents"][0]["sha"]
            names = kept_files(project, answer["sha"], parent, python, marker)
            if names:
                projects.add(project)
                commits.append({"project": project, "commit": answer["sha"], "parent": parent, "files": names})
        kinds.append({"kind": name, "searched for": words, "marker": marker, "answers": len(found),
                      "looked at": looked_at, "commits": commits})
        print("%-22s answers %2d  looked at %2d  kept %d" % (name, len(found), looked_at, len(commits)), flush=True)
    held["sets"][which] = {"collected": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "kinds": kinds}
    COMMITS.write_text(json.dumps(held, indent=1) + "\n")


def fetch(which):
    """Download every stored file, before and after.  Returns how many could not be had."""
    missing = 0
    for name, chosen in json.loads(COMMITS.read_text())["sets"].items():
        if which in (None, name):
            for kind in chosen["kinds"]:
                for commit in kind["commits"]:
                    for path in commit["files"]:
                        for at in (commit["parent"], commit["commit"]):
                            missing += file_at(commit["project"], at, path) is None
    return missing


# ----------------------------------------------------------------------------- one statement at a time


def statements(text):
    """Every statement of a file in source order, each as its own text without the statements under it."""
    found = []

    def own(node):
        fields = {}
        for name in ("body", "orelse", "finalbody", "handlers"):
            if isinstance(getattr(node, name, None), list) and getattr(node, name) \
                    and all(isinstance(one, (ast.stmt, ast.ExceptHandler)) for one in getattr(node, name)):
                fields[name] = getattr(node, name)
                setattr(node, name, [ast.Pass()] if name == "body" else [])
        for case in getattr(node, "cases", []) or []:
            fields.setdefault("cases", node.cases)
        if "cases" in fields:
            node.cases = []
        try:
            written = ast.unparse(node)
        except Exception:  # noqa: BLE001 - a node that cannot be written alone is compared by its dump
            written = ast.dump(node)
        for name, value in fields.items():
            setattr(node, name, value)
        return written

    def walk(node):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.stmt):
                found.append(own(child))
            walk(child)

    walk(ast.parse(text))
    return found


def answers(before, person, engine, marker):
    """Compare what the engine wrote with what the person wrote, per statement of `before`.

    Returns the counts: questions (marker statements the person changed one for one), same, different,
    left, and extra (statements the engine changed, or added, that the person did not).  A statement the
    engine adds (an import it brings) that the person also added is counted neither way.
    """
    was, became = statements(before), statements(person)
    by_person, person_added = {}, []
    for tag, a, b, c, d in difflib.SequenceMatcher(None, was, became, autojunk=False).get_opcodes():
        if tag == "replace" and b - a == d - c:
            by_person.update({a + step: became[c + step] for step in range(b - a)})
        elif tag in ("replace", "delete"):
            by_person.update({index: None for index in range(a, b)})      # reshaped or taken out
        elif tag == "insert":
            person_added += became[c:d]
    wrote = statements(engine) if engine is not None else list(was)
    by_engine, engine_added = {}, []
    for tag, a, b, c, d in difflib.SequenceMatcher(None, was, wrote, autojunk=False).get_opcodes():
        if tag == "equal" or (tag == "replace" and b - a == d - c):
            by_engine.update({a + step: wrote[c + step] for step in range(b - a)})
        elif tag == "insert":
            engine_added += wrote[c:d]
        else:                            # the engine never takes a statement out; read it as left + additions
            by_engine.update({index: was[index] for index in range(a, b)})
            engine_added += wrote[c:d]
    count = dict.fromkeys(("questions", "same", "different", "left", "extra"), 0)
    for statement in engine_added:
        if statement in person_added:
            person_added.remove(statement)
        else:
            count["extra"] += 1
    for index, old in enumerate(was):
        new, made = by_person.get(index), by_engine.get(index, old)
        if new is not None and marker in old:
            count["questions"] += 1
            count["same" if made == new else "left" if made == old else "different"] += 1
        elif made != old and index not in by_person:
            count["extra"] += 1
    return count


# ----------------------------------------------------------------------------- the three ways of repeating


def engine():
    import sys as _sys
    _sys.path.insert(0, str(ROOT))
    from canonical.swe_kernel.taught_actions import edit_by_example_v1
    return edit_by_example_v1


def repeated(by_example, rules, readings, text, way):
    """The engine's text for one file, or None where it refuses.  `way` is strict, shown or tried."""
    try:
        if way in ("strict", "shown"):
            return by_example.rewrite(rules, text, leave_unshown=way == "shown")[0]
        held = by_example.Text(text, "the file")
        found = by_example.fitting(rules, held, "the file")
        places = [place[:4] for place in found]                        # every fit, shown or not: all are tried
        taken = {id(place[1]) for place in found}
        places += [place[:4] for place in by_example.fitting(readings, held, "the file",
                                                             lambda node: id(node) in taken, torn=False)]
        return by_example.written(held, places) if places else text
    except (by_example.Refused, RecursionError):
        return None


def measure(which, out):
    by_example = engine()
    sets = json.loads(COMMITS.read_text())["sets"]
    report = {}
    for name, chosen in sets.items():
        if which not in (None, name):
            continue
        ways = {way: dict.fromkeys(("questions", "same", "different", "left", "extra", "refused files"), 0)
                for way in ("strict", "shown", "tried")}
        totals = {"kinds": 0, "kinds unlearned": 0, "files": 0, "files unreadable": 0}
        for kind in chosen["kinds"]:
            if len(kind["commits"]) < 2:
                continue
            totals["kinds"] += 1
            teacher = kind["commits"][0]
            shown_before = file_at(teacher["project"], teacher["parent"], teacher["files"][0])
            shown_after = file_at(teacher["project"], teacher["commit"], teacher["files"][0])
            try:
                rules, readings = by_example.learn_all(
                    [(shown_before.decode("utf-8"), shown_after.decode("utf-8"))], wide=True)
            except (by_example.Refused, RecursionError) as why:
                totals["kinds unlearned"] += 1
                print("%-22s not learned: %s" % (kind["kind"], str(why)[:90]), flush=True)
                continue
            for commit in kind["commits"][1:]:
                for path in commit["files"]:
                    before = file_at(commit["project"], commit["parent"], path).decode("utf-8")
                    person = file_at(commit["project"], commit["commit"], path).decode("utf-8")
                    try:
                        statements(before), statements(person)
                    except (RecursionError, ValueError):
                        totals["files unreadable"] += 1
                        continue
                    totals["files"] += 1
                    for way in ways:
                        wrote = repeated(by_example, rules, readings, before, way)
                        try:
                            count = answers(before, person, wrote, kind["marker"])
                        except (ValueError, RecursionError):
                            totals["files unreadable"] += 1
                            continue
                        ways[way]["refused files"] += wrote is None
                        for key, value in count.items():
                            ways[way][key] += value
        report[name] = {"totals": totals, "ways": ways}
        print("\n== %s: %d kinds (%d not learned), %d files" % (name, totals["kinds"], totals["kinds unlearned"],
                                                                totals["files"]))
        for way, count in ways.items():
            print("%-7s questions %3d  same %3d  different %2d  left %3d  extra %2d  refused files %2d"
                  % (way, count["questions"], count["same"], count["different"], count["left"], count["extra"],
                     count["refused files"]), flush=True)
    if out:
        pathlib.Path(out).write_text(json.dumps(report, indent=1) + "\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=("collect", "fetch", "measure"))
    parser.add_argument("which", nargs="?")
    parser.add_argument("--json")
    options = parser.parse_args(argv)
    if options.command == "collect":
        if options.which not in KINDS:
            raise SystemExit("name the set to collect: %s" % ", ".join(KINDS))
        collect(options.which)
        return 0
    if options.command == "fetch":
        missing = fetch(options.which)
        print("files that could not be had: %d" % missing)
        return 1 if missing else 0
    measure(options.which, options.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
