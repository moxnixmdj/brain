#!/usr/bin/env python3
"""One example of a change a project made in many files: how much of the rest does it give?

The claim under test is "done once, learned". This measures it where it can be true on real
projects: a pull request that makes one kind of change in many files. One changed file is the
example. The other changed files, as they were before, are the files to edit. What the developers
did to them is the answer.

The organ measured is canonical/swe_kernel/taught_actions/edit_by_example_v1.py, as it stands in
the tree. It is not edited and nothing is taught to it beyond the one example.

Where the pull requests come from. GitHub's search, by title, for kinds of change that projects
make in many places (the phrases are QUERIES below, fixed before any pull request was put to the
organ). For each phrase the results are taken in the order GitHub gives them, and the first
PER_QUERY pull requests that change at least MIN_FILES Python files in a way Python 3.11 can read
are used. From each, FILES changed files are drawn by a seed.

Three questions are asked of every pull request:

  one example    each drawn file in turn is the example; every other drawn file is edited.
  two examples   two drawn files, one after the other in one text, are the example.
  elsewhere      the example comes from a pull request found by ANOTHER phrase. Whatever the organ
                 changes then is not what the developers did there: a count of changes made where
                 the example did not belong.

What is counted. Both texts are written out one statement a line (ast.unparse), so layout and
comments do not count. A change is a line, or a run of lines, that the developers replaced. The
organ's changes are found the same way. A change of the organ is right when the developers made
that very change at that very line. Lines that only import are counted apart, because the organ
by its own rule does not repeat an added or removed import.

No test is run. Agreement with the developers is the measure; a change the developers did not make
may still be harmless, and one they made may still be wrong.

This is the best case by construction: the pull requests were looked for because they repeat one
change. It says how far one example reaches inside such a change. It does not say how much of
software work is of this kind.
"""
from __future__ import annotations

import argparse
import ast
import collections
import difflib
import hashlib
import itertools
import json
import pathlib
import random
import signal
import subprocess
import sys
import time
import urllib.parse
import warnings
from typing import Any, Callable, Iterable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "BRAIN_REPEATED_CHANGE_ONE_EXAMPLE_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
ORGAN = "canonical/swe_kernel/taught_actions/edit_by_example_v1.py"

# kinds of change projects make in many places: the words looked for in pull-request titles
QUERIES = (
    ("an old name of a test method", "assertEquals assertEqual"),
    ("an old name of a test method, second", "assertRaisesRegexp assertRaisesRegex"),
    ("an old name of a logging method", "logger.warn logger.warning"),
    ("a call written the old way", "super() without arguments"),
    ("a library taken out", "Remove six"),
    ("text put together another way", "Use f-strings"),
    ("types written another way", "PEP 585 generics"),
    ("a call that is no longer to be used", "datetime.utcnow"),
)
PER_QUERY = 2            # pull requests used per phrase
RESULTS_READ = 12        # search results looked through per phrase, at most
MIN_FILES = 6            # changed Python files a pull request must have to be looked at
MAX_FILES_IN_ALL = 300   # a pull request that changes more files than this is passed over
FILES = 6                # changed files drawn from one pull request
FEWEST_FILES = 4         # a pull request with fewer usable files than this is passed over
MAX_BYTES = 100_000      # a file longer than this is passed over
SEED = 20261112
CALL_LIMIT_S = 30        # one call of the organ


# --------------------------------------------------------------------------- #
# what changed, one statement a line
# --------------------------------------------------------------------------- #
def statement_lines(text: str) -> list[str] | None:
    """The program one statement a line, without the empty lines, or None when Python 3.11 cannot
    read it."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return [line for line in ast.unparse(ast.parse(text)).split("\n") if line.strip()]
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return None


Change = tuple[int, tuple[str, ...], tuple[str, ...]]     # (first line, the lines that were there, the lines put there)


def changes(before: Sequence[str], after: Sequence[str]) -> set[Change]:
    """What was replaced, as (line, old lines, new lines). A run replaced by a run of the same
    length is taken line by line, so one right line inside a run still counts."""
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


def score(before: str, after: str, got: str | None) -> dict[str, Any]:
    """The organ's text against the developers'. `got` None: the organ made nothing."""
    base, wanted = statement_lines(before), statement_lines(after)
    if base is None or wanted is None:
        raise ValueError("a file that cannot be read cannot be scored")
    theirs = changes(base, wanted)
    made_lines = None if got is None else statement_lines(got)
    mine = set() if made_lines is None else changes(base, made_lines)
    theirs_code = {change for change in theirs if not only_imports(change)}
    right = mine & theirs
    return {"developers_changes": len(theirs), "developers_changes_not_imports": len(theirs_code), "organ_changes": len(mine),
            "right": len(right), "right_not_imports": len(right & theirs_code), "not_what_the_developers_did": len(mine - theirs),
            "organ_text_cannot_be_read": bool(got is not None and made_lines is None),
            "the_whole_file_as_the_developers_left_it": bool(made_lines is not None and made_lines == wanted),
            "all_but_imports_as_the_developers_left_it": bool(mine and theirs_code <= mine and not (mine - theirs))}


def put_together(first: str, second: str) -> str | None:
    """Two files as one text, or None when Python cannot read the result."""
    joined = first.rstrip("\n") + "\n\n\n" + second
    return joined if statement_lines(joined) is not None else None


# --------------------------------------------------------------------------- #
# the organ
# --------------------------------------------------------------------------- #
class TookTooLong(Exception):
    pass


def _alarm(signum, frame):
    raise TookTooLong()


def the_organ(target: str, example_before: str, example_after: str) -> tuple[str | None, str | None]:
    """(the edited text, None) or (None, why not). The organ's own refusal is given in its words."""
    return _asked(lambda organ: organ.edit_by_example(target, example_before, example_after))


def the_organ_leaving_the_rest(target: str, example_before: str, example_after: str) -> tuple[str | None, str | None]:
    """The organ's other way of repeating (its `repeat_shown`): code that is used a way the example
    did not show is left as it is, and the rest is changed. Added after the first two runs had
    been seen, when another session had changed the organ so that it refuses such a file whole."""
    return _asked(lambda organ: organ.repeated(organ.learn(example_before, example_after), target, "the example", leave_unshown=True))


def _asked(ask: Callable[[Any], str]) -> tuple[str | None, str | None]:
    from canonical.swe_kernel.taught_actions import edit_by_example_v1 as organ
    previous = signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(CALL_LIMIT_S)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return ask(organ), None
    except organ.Refused as why:
        return None, "refused: " + str(why)
    except TookTooLong:
        return None, f"stopped: more than {CALL_LIMIT_S} s"
    except RecursionError:
        return None, "refused: the code is nested too deeply to compare"
    except Exception as error:      # the organ failed: counted apart, never as a refusal
        return None, f"error: {type(error).__name__}"
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def reason_class(why: str | None) -> str:
    """A refusal without its line numbers and names, so that like refusals are counted together."""
    if why is None:
        return "edited"
    import re
    head = why.split("(")[0]
    head = re.sub(r"'[^']*'", "'…'", head)
    head = re.sub(r"\d+", "N", head)
    return " ".join(head.split())[:110]


# --------------------------------------------------------------------------- #
# one pull request
# --------------------------------------------------------------------------- #
def _add(total: dict[str, Any], one: Mapping[str, Any], why: str | None) -> None:
    total["asked"] += 1
    total["edited"] += why is None
    for key in ("developers_changes", "developers_changes_not_imports", "organ_changes", "right", "right_not_imports", "not_what_the_developers_did"):
        total[key] += one[key]
    for key in ("the_whole_file_as_the_developers_left_it", "all_but_imports_as_the_developers_left_it", "organ_text_cannot_be_read"):
        total[key] += bool(one[key])
    total["edited_and_every_change_right"] += bool(why is None and one["organ_changes"] and not one["not_what_the_developers_did"])
    total["why_not"][reason_class(why)] += 1


def _empty() -> dict[str, Any]:
    out: dict[str, Any] = {key: 0 for key in (
        "asked", "edited", "developers_changes", "developers_changes_not_imports", "organ_changes", "right", "right_not_imports",
        "not_what_the_developers_did", "the_whole_file_as_the_developers_left_it", "all_but_imports_as_the_developers_left_it",
        "organ_text_cannot_be_read", "edited_and_every_change_right")}
    out["why_not"] = collections.Counter()
    return out


def rates(total: Mapping[str, Any]) -> dict[str, Any]:
    out = {key: value for key, value in total.items() if key != "why_not"}
    out["why_not"] = dict(sorted(total["why_not"].items(), key=lambda item: (-item[1], item[0])))
    out["of_the_developers_changes_made"] = _share(total["right_not_imports"], total["developers_changes_not_imports"])
    out["of_the_organs_changes_right"] = _share(total["right"], total["organ_changes"])
    out["share_edited"] = _share(total["edited"], total["asked"])
    out["share_all_but_imports_as_the_developers_left_it"] = _share(total["all_but_imports_as_the_developers_left_it"], total["asked"])
    return out


def _share(part: int, whole: int) -> float | None:
    return None if not whole else round(part / whole, 4)


def one_pull_request(files: Sequence[Mapping[str, str]], *, organ: Callable[[str, str, str], tuple[str | None, str | None]] = the_organ,
                     two_examples: bool = True) -> dict[str, Any]:
    """Every drawn file as the example for every other; then every two files as the example."""
    out: dict[str, Any] = {"files": len(files), "itself": _empty(), "one_example": _empty(), "two_examples": _empty(),
                           "two_examples_could_not_be_put_together": 0, "per_file_as_the_example": []}
    for index, example in enumerate(files):
        got, why = organ(example["before"], example["before"], example["after"])
        _add(out["itself"], score(example["before"], example["after"], got), why)
        as_example = _empty()
        for other, target in enumerate(files):
            if other == index:
                continue
            got, why = organ(target["before"], example["before"], example["after"])
            one = score(target["before"], target["after"], got)
            _add(out["one_example"], one, why)
            _add(as_example, one, why)
        out["per_file_as_the_example"].append({"path": example["path"], **{key: as_example[key] for key in ("asked", "edited", "right_not_imports", "developers_changes_not_imports", "not_what_the_developers_did")}})
    if two_examples:
        for first, second in itertools.combinations(range(len(files)), 2):
            before = put_together(files[first]["before"], files[second]["before"])
            after = put_together(files[first]["after"], files[second]["after"])
            for other, target in enumerate(files):
                if other in (first, second):
                    continue
                if before is None or after is None:
                    out["two_examples_could_not_be_put_together"] += 1
                    _add(out["two_examples"], score(target["before"], target["after"], None), "refused: the two examples could not be put together as one text")
                    continue
                got, why = organ(target["before"], before, after)
                _add(out["two_examples"], score(target["before"], target["after"], got), why)
    return out


def elsewhere(files: Sequence[Mapping[str, str]], foreign: Sequence[Mapping[str, str]], *,
              organ: Callable[[str, str, str], tuple[str | None, str | None]] = the_organ) -> dict[str, Any]:
    """Examples of another kind of change put to these files."""
    total = _empty()
    for example in foreign:
        for target in files:
            got, why = organ(target["before"], example["before"], example["after"])
            _add(total, score(target["before"], target["after"], got), why)
    return total


def measure(pulls: Sequence[Mapping[str, Any]], *, organ: Callable[[str, str, str], tuple[str | None, str | None]] = the_organ,
            two_examples: bool = True, say: Callable[[str], None] = lambda line: None) -> dict[str, Any]:
    per_pull: dict[str, Any] = {}
    for pull in pulls:
        started = time.time()
        row = one_pull_request(pull["files"], organ=organ, two_examples=two_examples)
        foreign = [other["files"][0] for other in pulls if other["query"] != pull["query"] and other["files"]]
        row["elsewhere"] = elsewhere(pull["files"], foreign, organ=organ)
        row.update(kind=pull["kind"], query=pull["query"], title=pull["title"], seconds=round(time.time() - started, 1))
        per_pull[pull["name"]] = row
        one = rates(row["one_example"])
        say(f"{pull['name']:45s} files {row['files']}  one example: edited {one['edited']}/{one['asked']}  "
            f"made {one['right_not_imports']}/{one['developers_changes_not_imports']}  not theirs {one['not_what_the_developers_did']}  {row['seconds']} s")
    return per_pull


def summarise(per_pull: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"pull_requests": len(per_pull), "files": sum(row["files"] for row in per_pull.values())}
    for question in ("itself", "one_example", "two_examples", "elsewhere"):
        total = _empty()
        for row in per_pull.values():
            for key, value in row[question].items():
                if key == "why_not":
                    total["why_not"].update(value)
                else:
                    total[key] += value
        out[question] = rates(total)
    out["two_examples_could_not_be_put_together"] = sum(row["two_examples_could_not_be_put_together"] for row in per_pull.values())
    by_kind: dict[str, Any] = {}
    for kind in dict.fromkeys(row["kind"] for row in per_pull.values()):
        rows = [row for row in per_pull.values() if row["kind"] == kind]
        by_kind[kind] = {}
        for question in ("one_example", "two_examples"):
            total = _empty()
            for row in rows:
                for key, value in row[question].items():
                    if key == "why_not":
                        total["why_not"].update(value)
                    else:
                        total[key] += value
            made = rates(total)
            by_kind[kind][question] = {key: made[key] for key in ("asked", "edited", "of_the_developers_changes_made", "of_the_organs_changes_right",
                                                                 "share_all_but_imports_as_the_developers_left_it", "not_what_the_developers_did")}
        by_kind[kind]["pull_requests"] = len(rows)
    out["by_kind_of_change"] = by_kind
    reached = [name for name, row in per_pull.items() if row["one_example"]["right_not_imports"]]
    out["pull_requests_where_one_example_made_any_of_the_developers_changes"] = len(reached)
    return out


# --------------------------------------------------------------------------- #
# the pull requests, from GitHub
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
    raise RuntimeError(f"GitHub did not answer: {' '.join(command)[:200]}: {done.stderr[-200:]!r}")


def usable(before: str | None, after: str | None) -> bool:
    """A changed file that Python 3.11 reads before and after, not too long, changed in its code."""
    if before is None or after is None or len(before.encode()) > MAX_BYTES or len(after.encode()) > MAX_BYTES:
        return False
    was, now = statement_lines(before), statement_lines(after)
    return was is not None and now is not None and was != now


def draw(paths: Iterable[str], seed: int = SEED) -> list[str]:
    """The changed Python files in the order they are tried."""
    order = sorted(paths)
    random.Random(seed).shuffle(order)
    return order


def one_pull(repo: str, number: int) -> dict[str, Any] | None:
    pull = gh(f"repos/{repo}/pulls/{number}")
    if not pull or not pull.get("merged_at") or pull.get("changed_files", 0) > MAX_FILES_IN_ALL:
        return None
    listed: list[dict[str, Any]] = []
    for page in range(1, 5):
        part = gh(f"repos/{repo}/pulls/{number}/files?per_page=100&page={page}") or []
        listed += part
        if len(part) < 100:
            break
    paths = [item["filename"] for item in listed if item["filename"].endswith(".py") and item["status"] == "modified"]
    if len(paths) < MIN_FILES:
        return None
    compared = gh(f"repos/{repo}/compare/{pull['base']['sha']}...{pull['head']['sha']}")
    if not compared:
        return None
    before_at, after_at = compared["merge_base_commit"]["sha"], pull["head"]["sha"]
    files = []
    for path in draw(paths):
        quoted = urllib.parse.quote(path)
        before = gh(f"repos/{repo}/contents/{quoted}?ref={before_at}", raw=True)
        after = gh(f"repos/{repo}/contents/{quoted}?ref={after_at}", raw=True)
        if usable(before, after):
            files.append({"path": path, "before": before, "after": after})
        if len(files) >= FILES:
            break
    if len(files) < FEWEST_FILES:
        return None
    return {"name": f"{repo}#{number}", "repo": repo, "number": number, "title": pull["title"], "before_at": before_at, "after_at": after_at,
            "changed_python_files": len(paths), "files": files}


def collect(say: Callable[[str], None] = print) -> list[dict[str, Any]]:
    pulls = []
    for kind, words in QUERIES:
        found = gh("-X", "GET", "search/issues", "-f", f"q=is:pr is:merged language:Python in:title {words}", "-f", f"per_page={RESULTS_READ}") or {}
        taken = 0
        for item in found.get("items", []):
            repo = item["repository_url"].split("/repos/")[1]
            pull = one_pull(repo, item["number"])
            say(f"{kind:40s} {repo}#{item['number']:<6d} {'USED' if pull else 'passed over'}  {item['title'][:60]}")
            if pull:
                pulls.append(dict(pull, kind=kind, query=words))
                taken += 1
                if taken >= PER_QUERY:
                    break
            time.sleep(1)
    return pulls


def without_texts(pulls: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """What was used, without the files' text: enough for anyone to fetch the same files again."""
    return [{**{key: value for key, value in pull.items() if key != "files"},
             "files": [{"path": item["path"], "before_sha256": hashlib.sha256(item["before"].encode()).hexdigest(),
                        "after_sha256": hashlib.sha256(item["after"].encode()).hexdigest()} for item in pull["files"]]} for pull in pulls]


def code_sha256() -> dict[str, str]:
    names = ("canonical/tools/repeated_change_one_example_measure_v1.py", ORGAN)
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--collect", type=pathlib.Path, default=None, help="look the pull requests up and write them, with the files' text, here")
    parser.add_argument("--pulls", type=pathlib.Path, default=None, help="the file --collect wrote")
    parser.add_argument("--out", type=pathlib.Path, default=None)
    parser.add_argument("--no-two-examples", action="store_true")
    parser.add_argument("--leave-unshown", action="store_true", help="the organ's other way of repeating: code used a way the example did not show is left as it is")
    args = parser.parse_args(argv)
    if args.collect is not None:
        pulls = collect()
        args.collect.write_text(json.dumps(pulls), encoding="utf-8")
        print(f"{len(pulls)} pull requests, {sum(len(pull['files']) for pull in pulls)} files -> {args.collect}")
        return 0
    if args.pulls is None or args.out is None:
        parser.error("--pulls and --out, or --collect")
    pulls = json.loads(args.pulls.read_text(encoding="utf-8"))
    started = time.time()
    per_pull = measure(pulls, organ=the_organ_leaving_the_rest if args.leave_unshown else the_organ,
                       two_examples=not args.no_two_examples, say=lambda line: print(line, flush=True))
    summary = summarise(per_pull)
    for row in per_pull.values():
        for question in ("itself", "one_example", "two_examples", "elsewhere"):
            row[question] = rates(row[question])
    record = {"schema": SCHEMA, "authority": AUTHORITY, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "organ": ORGAN, "queries": [list(query) for query in QUERIES],
              "way_of_repeating": "what the example did not show is left as it is" if args.leave_unshown else "the whole file or nothing",
              "parameters": {"per_query": PER_QUERY, "results_read": RESULTS_READ, "min_files": MIN_FILES, "max_files_in_all": MAX_FILES_IN_ALL,
                             "files": FILES, "fewest_files": FEWEST_FILES, "max_bytes": MAX_BYTES, "seed": SEED, "call_limit_s": CALL_LIMIT_S},
              "code_sha256": code_sha256(), "pulls_sha256": hashlib.sha256(args.pulls.read_bytes()).hexdigest(),
              "pull_requests": without_texts(pulls), "summary": summary, "per_pull_request": per_pull,
              "seconds": round(time.time() - started, 1), "model_calls": 0, "tests_run": 0}
    args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in record["summary"].items() if key != "by_kind_of_change"}, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
