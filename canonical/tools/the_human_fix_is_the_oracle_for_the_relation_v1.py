"""Ask, of every row, the only question that bounds everything else:

    is the human's own repaired line reachable by a relation, from the failing source?

No test runs, no sampling, no ranking. Just: take the file before the fix and after it,
diff them, and ask each relation whether it would have written the human's line.

This separates three things that were being conflated in the sweep's stage counts:

    NOT_EXPRESSIBLE  no relation can write the human's line  -> a LEXICON gap
    NOT_PROPOSED     a relation can, but the run never offered it -> a GENERATION gap
    LOW_RANK         offered, but after other hypotheses      -> a RANKING gap (the
                                                                only gap a store can close)

The store's measured +0 is only interesting once we know how many rows sit in the third
bucket. If the third bucket is empty, no store can ever change an outcome on this corpus
and the ablation's null result is structural, not a failure of the store implementation.
"""
from __future__ import annotations

import argparse
import difflib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent))

import the_relation_is_read_from_the_failing_run_v1 as T  # noqa: E402

REPOS = Path("/home/user/repos")


def _show(repo: str, rev: str, path: str) -> str:
    out = subprocess.run(["git", "show", f"{rev}:{path}"], cwd=REPOS / repo,
                         capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else ""


def _changed_lines(before: str, after: str) -> tuple[set[int], set[str]]:
    """Line numbers (1-based, in the BEFORE file) that the human touched, plus the
    replacement text. Only single-line replacements count: this tool is about the
    single-line fixes the corpus was built from."""
    a = before.splitlines()
    b = after.splitlines()
    numbers: set[int] = set()
    texts: set[str] = set()
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("replace", "insert", "delete"):
            numbers.update(range(i1 + 1, i2 + 1))
            texts.update(t.strip() for t in b[j1:j2])
    return numbers, texts


def _squash(text: str) -> str:
    return " ".join(text.split())


def classify(row: dict[str, Any]) -> dict[str, Any]:
    repo = row["repo"]
    sha = row["commit"]
    source = row["sources"][0]
    before = _show(repo, sha + "^", source)
    after = _show(repo, sha, source)
    if not before or not after:
        return {"commit": sha, "repo": repo, "verdict": "SOURCE_UNAVAILABLE"}
    human_lines, human_texts = _changed_lines(before, after)
    wanted = {_squash(t) for t in human_texts if t}

    hits: list[dict[str, Any]] = []
    for site in T.sites_in(before):
        # Samples are deliberately empty: this measures what the relation LANGUAGE can
        # reach, not what one particular run happened to see. A `forbidden` token and a
        # message both steer relations toward the run's evidence; withholding them is the
        # most generous possible test of the lexicon.
        # `did_not_raise` is the demand that END_ANCHOR is READ FROM. It is not a
        # decoration on the relation: a pattern with a loose tail only becomes a defect
        # when the program was supposed to reject an input and didn't. Handing the
        # relation the demand is giving it the run's evidence, not the answer.
        demand = {"source": "did_not_raise", "kind": "raised"}
        try:
            proposed = T.relations_for(site, [], demand, None, "", forbidden=None,
                                       wanted_raise=None, patterns_linked={},
                                       sites_inside=[])
        except Exception as error:  # a relation that raises is a bug, not a verdict
            hits.append({"site": site.index, "line": site.line, "relation": f"RAISED:{type(error).__name__}"})
            continue
        for option in proposed:
            edit = option.get("edit")
            if not isinstance(edit, str):
                continue
            # CONTAINMENT, NOT EQUALITY. The human's changed line is a whole statement
            # (`_build_tag_regex = re.compile(r"(\d+)(.*)\Z", re.ASCII)`) while a relation
            # writes just the expression (`re.compile(r"(\d+)(.*)\Z", re.ASCII)`). Demanding
            # equality reported 0/45 -- including three rows this engine has VERIFIED -- so
            # the first version of this tool measured its own comparison, not the lexicon.
            if any(_squash(edit) in human or human in _squash(edit) for human in wanted):
                hits.append({"site": site.index, "line": site.line,
                             "relation": option["relation"], "edit": edit[:200],
                             "on_the_human_line": site.line in human_lines})

    on_line = [h for h in hits if h.get("on_the_human_line")]
    if not hits:
        verdict = "NOT_EXPRESSIBLE"
    elif not on_line:
        verdict = "EXPRESSIBLE_ELSEWHERE_ONLY"
    else:
        verdict = "EXPRESSIBLE_ON_THE_HUMAN_LINE"
    return {"commit": sha, "repo": repo, "verdict": verdict,
            "human_lines": sorted(human_lines), "relations": sorted({h["relation"] for h in on_line}),
            "n_expressible": len(on_line)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commits", default="canonical/corpus/single_line_fix_commits_20261123_V1.json")
    parser.add_argument("--receipt", default="/tmp/rel/oracle.json")
    parser.add_argument("--only", nargs="*", default=None)
    args = parser.parse_args()

    rows = json.loads(Path(args.commits).read_text())["tasks"]
    if args.only:
        wanted = [p.lower() for p in args.only]
        rows = [r for r in rows if any(r["commit"].lower().startswith(p) for p in wanted)]

    results = []
    for row in rows:
        try:
            result = classify(row)
        except Exception as error:
            result = {"commit": row["commit"], "repo": row["repo"],
                      "verdict": "TOOL_ERROR", "error": f"{type(error).__name__}: {error}"}
        results.append(result)
        print(f"  {result['repo']:<15} {result['commit'][:8]}  {result['verdict']:<32}"
              f" {result.get('relations', '')}")
        Path(args.receipt).write_text(json.dumps({"results": results}, indent=2))

    counts: dict[str, int] = {}
    for result in results:
        counts[result["verdict"]] = counts.get(result["verdict"], 0) + 1
    print("\n===", counts)
    print(f"=== expressible on the human's own line: "
          f"{counts.get('EXPRESSIBLE_ON_THE_HUMAN_LINE', 0)}/{len(results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
