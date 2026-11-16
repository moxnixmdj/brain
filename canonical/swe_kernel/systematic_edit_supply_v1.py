#!/usr/bin/env python3
"""How much of real engineering is a repeat a single demonstration could determine?

THE CLAIM UNDER TEST
--------------------
"Give the model the most advanced coding actions, let it do each one once, and it has learned them
permanently; do that everywhere and advanced software engineering is solved."

For that to be true of a change, three things must hold, and the claim is usually argued without
measuring any of them:

  1. SUPPLY       real work contains siblings -- another site where the same edit belongs -- so a
                  demonstration has somewhere to generalise TO;
  2. DETERMINACY  one demonstration determines the transformation, rather than merely resembling it,
                  so the sibling can be produced rather than guessed;
  3. PERMANENCE   the induced transformation survives the file moving under it (measured elsewhere:
                  `action_replay_under_change_v1`, 53.5% stale and 31.1% silently corrupt over 228
                  real compositions).

This module measures 1 and 2 against ground truth: the text the developer actually committed.

THE PROTOCOL
------------
SyDIT (Meng et al., PLDI 2011) made the same bet -- one example, applied to the other places a
systematic edit belongs -- and reported reproducing the human's edit exactly on 70% (39/56) of
systematic edits. Nguyen et al. (ASE 2013) measured the supply across 2,841 projects: repetitiveness
is 70-100% at the smallest sizes and decays exponentially with size. Both are the external anchors.

For each real commit that touched sibling sites, take ONE site as the demonstration, apply its edit
to the sibling's concrete tokens, and compare with what the developer wrote. Three outcomes, and the
first two are not the same thing:

  DETERMINED  the prediction matched and every token in it came from the target -- the demonstration
              forced the edit, so a learner may trust it;
  LUCKY       the prediction matched only because a token the demonstration could not derive was
              copied across and happened to be right;
  WRONG       it did not reproduce the edit, and the diagnosis says why: a token that the
              demonstration DID bind was used differently by the developer (`rebound_wrong`), a value
              the demonstration had to invent was different (`constant_differs`), the same demo token
              had to mean two different things (`conflict`), or the edit is not a substitution at all
              (`mismatch`).

Two strictness rungs are reported because "the same systematic edit" is a judgement: one shared line
of context on each side (`context1`) and two (`context2`). A conclusion that flips between them is
not a conclusion, so both are printed.

WHAT THIS DOES NOT CLAIM
------------------------
No capability credit, no benchmark rank, no independent verification. The corpus is real history from
three public repositories, sampled deterministically and pinned by sha256, so the numbers are
reproducible offline; the abstraction is lexical (identifiers, numbers and literals become holes),
so "exact" means "reproduces the bytes", never "means the same thing". This measures what a
*demonstration-determined substitution learner* can do. A richer inducer is a different experiment,
and the published ceiling for one with full AST and context machinery is the 70% above, not 100%.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "systematic_edit_supply_v1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
CORPUS_SCHEMA = "systematic_edit_corpus_v1"
CORPUS_PATH = "canonical/tests/fixtures/systematic_edit_corpus_v1.jsonl"
DIFF_CAP = 12000
RUNGS = {"shape_only": (0, False), "context_any": (1, False), "context_both": (1, True)}

TOKEN = re.compile(r"[A-Za-z_][A-Za-z_0-9]*|\d+(?:\.\d+)?|'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"")
HOLE = re.compile(r"\x00([A-Z]+)(\d+)")
SOURCE_SUFFIXES = (".py", ".md", ".json", ".yml", ".yaml", ".toml", ".sh", ".txt")
VERDICTS = ("verbatim", "exact", "constant_differs", "rebound_wrong", "conflict", "mismatch")


def _run(*argv: str) -> str:
    """Git output as text. Diffs are bytes, not UTF-8: one legacy file must not abort a crawl."""
    done = subprocess.run(list(argv), capture_output=True, timeout=300)
    body = (done.stdout or b"")
    if done.returncode != 0:
        body += done.stderr or b""
    return body.decode("utf-8", errors="replace")


def abstract(line: str) -> tuple[str, tuple[tuple[str, str], ...]]:
    """A line as a template plus its holes: identifiers, numbers and literals become positions."""
    pieces: list[str] = []
    holes: list[tuple[str, str]] = []
    start = 0
    for match in TOKEN.finditer(line):
        pieces.append(line[start:match.start()])
        text = match.group()
        kind = "ID" if text[0].isalpha() or text[0] == "_" else ("NUM" if text[0].isdigit() else "STR")
        pieces.append("\x00" + kind + str(len(holes)))
        holes.append((kind, text))
        start = match.end()
    pieces.append(line[start:])
    return "".join(pieces), tuple(holes)


class Site:
    """One hunk of one file in one commit: what the developer removed, added, and around what."""

    __slots__ = ("file", "removed", "added", "before", "after", "skel", "holes_removed",
                 "holes_added", "ctx_before", "ctx_after")

    def __init__(self, file: str, removed: Sequence[str], added: Sequence[str],
                 before: Sequence[str] = (), after: Sequence[str] = ()) -> None:
        self.file = file
        self.removed = tuple(removed)
        self.added = tuple(added)
        self.before = tuple(before)
        self.after = tuple(after)
        removed_parts = [abstract(line) for line in self.removed]
        added_parts = [abstract(line) for line in self.added]
        self.skel = (tuple(part[0] for part in removed_parts),
                     tuple(part[0] for part in added_parts))
        self.holes_removed = tuple(hole for part in removed_parts for hole in part[1])
        self.holes_added = tuple(hole for part in added_parts for hole in part[1])
        self.ctx_before = tuple(abstract(line)[0] for line in self.before)
        self.ctx_after = tuple(abstract(line)[0] for line in self.after)

    @property
    def size(self) -> int:
        return len(self.removed) + len(self.added)

    def tokens(self) -> list[str]:
        return [text for _kind, text in self.holes_removed] + \
               [text for _kind, text in self.holes_added]


def parse_commit(text: str, *, context_lines: int = 2) -> list[Site]:
    """Read a diff into sites: one per hunk, with the lines around the change as its context."""
    sites: list[Site] = []
    file = ""
    rows: list[tuple[str, str]] = []

    def flush() -> None:
        nonlocal rows
        if file and rows:
            first = next((i for i, (kind, _t) in enumerate(rows) if kind != " "), None)
            last = next((i for i in range(len(rows) - 1, -1, -1) if rows[i][0] != " "), None)
            if first is not None and last is not None:
                before = [t for k, t in rows[:first] if k == " "][-context_lines:]
                after = [t for k, t in rows[last + 1:] if k == " "][:context_lines]
                removed = [t for k, t in rows if k == "-"]
                added = [t for k, t in rows if k == "+"]
                if removed or added:
                    sites.append(Site(file, removed, added, before, after))
        rows = []

    for line in text.splitlines():
        if line.startswith("diff --git "):
            flush()
            file = ""
            continue
        if line.startswith("+++ "):
            path = line[4:].strip()
            file = path[2:] if path.startswith("b/") else path
            continue
        if line.startswith("--- ") or line.startswith("index ") or line.startswith("new file mode") \
                or line.startswith("deleted file mode") or line.startswith("similarity index") \
                or line.startswith("rename ") or line.startswith("\\"):
            continue
        if line.startswith("@@"):
            flush()
            continue
        if line.startswith("+"):
            rows.append(("+", line[1:]))
        elif line.startswith("-"):
            rows.append(("-", line[1:]))
        elif line.startswith(" "):
            rows.append((" ", line[1:]))
    flush()
    return sites


def siblings(a: Site, b: Site, context_lines: int, both: bool = True) -> bool:
    """Two sites are siblings when the same edit sits in the same context and differs concretely.

    Context is what separates a systematic edit from a coincidence: two one-line changes that merely
    share a token pattern are not one operation applied twice.
    """
    if a.skel != b.skel or not a.removed or not a.added:
        return False
    if context_lines:
        before = (len(a.ctx_before) >= context_lines and len(b.ctx_before) >= context_lines
                  and a.ctx_before[-context_lines:] == b.ctx_before[-context_lines:])
        after = (len(a.ctx_after) >= context_lines and len(b.ctx_after) >= context_lines
                 and a.ctx_after[:context_lines] == b.ctx_after[:context_lines])
        if both and not (before and after):
            return False
        if not both and not (before or after):
            return False
    return True


def induce(demo: Site, target: Site) -> dict[str, Any]:
    """Apply the demonstration's edit to the target's tokens and say what happened.

    Every token in the output is marked with where it came from: bound from the target, or copied
    verbatim from the demonstration because nothing in the target determined it. That marking is what
    makes "it matched" different from "the demonstration forced it".
    """
    mapping: dict[str, str] = {}
    for demo_hole, target_hole in zip(demo.holes_removed, target.holes_removed):
        if demo_hole[0] != target_hole[0]:
            return {"verdict": "mismatch", "lines": [], "copied": []}
        if demo_hole[1] in mapping and mapping[demo_hole[1]] != target_hole[1]:
            return {"verdict": "conflict", "lines": [], "copied": []}
        mapping[demo_hole[1]] = target_hole[1]

    lines: list[str] = []
    copied_flags: list[list[bool]] = []
    for template in demo.skel[1]:
        pieces: list[str] = []
        flags: list[bool] = []
        cursor = 0
        for match in HOLE.finditer(template):
            pieces.append(template[cursor:match.start()])
            index = int(match.group(2))
            if index >= len(demo.holes_added):
                return {"verdict": "mismatch", "lines": [], "copied": []}
            _kind, source = demo.holes_added[index]
            if source in mapping:
                pieces.append(mapping[source])
                flags.append(False)
            else:
                pieces.append(source)
                flags.append(True)
            cursor = match.end()
        pieces.append(template[cursor:])
        lines.append("".join(pieces))
        copied_flags.append(flags)

    verdict = "exact"
    for produced, actual, flags in zip(lines, target.added, copied_flags):
        if produced == actual:
            continue
        produced_template, produced_holes = abstract(produced)
        actual_template, actual_holes = abstract(actual)
        if produced_template != actual_template:
            return {"verdict": "mismatch", "lines": lines, "copied": copied_flags}
        for index, (mine, theirs) in enumerate(zip(produced_holes, actual_holes)):
            if mine[1] == theirs[1]:
                continue
            was_copied = flags[index] if index < len(flags) else False
            if verdict == "exact":
                verdict = "constant_differs" if was_copied else "rebound_wrong"
            elif verdict == "constant_differs" and not was_copied:
                verdict = "rebound_wrong"
    return {"verdict": verdict, "lines": lines, "copied": copied_flags}


def read_corpus(path: pathlib.Path) -> list[dict[str, Any]]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def extract(repo: pathlib.Path, name: str, *, stride: int = 8, keep: int = 70,
            cap: int = DIFF_CAP) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Sample a real repository's history into a pinned corpus, deterministically.

    Every `stride`-th non-merge commit is kept; commits whose diff is empty or larger than `cap` are
    skipped and counted, never silently dropped, so the sample's bias is visible.
    """
    raw = _run("git", "-C", str(repo), "rev-list", "--no-merges", "--reverse", "HEAD")
    shas = [line.strip() for line in raw.splitlines() if line.strip()]
    records: list[dict[str, Any]] = []
    skipped_large = skipped_empty = 0
    for sha in shas[::stride]:
        if len(records) >= keep:
            break
        text = _run("git", "-C", str(repo), "show", sha, "--format=", "--unified=2", "--no-color")
        if not text.strip():
            skipped_empty += 1
            continue
        if len(text) > cap:
            skipped_large += 1
            continue
        meta = _run("git", "-C", str(repo), "show", "-s", "--format=%cI%x09%s", sha).strip()
        date, _sep, subject = meta.partition("\t")
        records.append({"repo": name, "sha": sha, "date": date, "subject": subject[:120],
                        "diff": text})
    return records, {"repo": name, "commits_in_history": len(shas), "stride": stride,
                     "kept": len(records), "skipped_large": skipped_large,
                     "skipped_empty": skipped_empty}


def _score(pairs: Iterable[tuple[str, Site, Site]]) -> dict[str, Any]:
    outcomes = {name: 0 for name in VERDICTS}
    pairs_count = 0
    determined = lucky = 0
    per_size: dict[int, dict[str, int]] = {}
    examples: list[dict[str, Any]] = []
    for _repo, demo, target in pairs:
        if set(demo.tokens()) == set(target.tokens()):
            # A verbatim repeat: the same edit text belongs here too, so copying the demonstration
            # is correct and nothing has to be induced. Counted as determined, never as a guess.
            verdict = "verbatim" if demo.added == target.added else "constant_differs"
            result = {"verdict": verdict, "lines": list(demo.added), "copied": [[False] * len(demo.added)]}
        else:
            result = induce(demo, target)
            verdict = result["verdict"]
        pairs_count += 1
        outcomes[verdict] += 1
        bucket = min(demo.size, 6)
        row = per_size.setdefault(bucket, {"pairs": 0, "determined": 0, "lucky": 0, "wrong": 0})
        row["pairs"] += 1
        if verdict in ("verbatim", "exact") and not any(any(flags) for flags in result["copied"]):
            determined += 1
            row["determined"] += 1
        elif verdict in ("verbatim", "exact"):
            lucky += 1
            row["lucky"] += 1
        else:
            row["wrong"] += 1
            if len(examples) < 5 and verdict in ("constant_differs", "rebound_wrong"):
                examples.append({"demo": demo.file, "target": target.file,
                                 "verdict": verdict, "demo_lines": list(demo.removed[:2]),
                                 "demo_added": list(demo.added[:2]),
                                 "target_lines": list(target.removed[:2]),
                                 "target_added": list(target.added[:2]),
                                 "predicted": list(result["lines"][:2])})
    return {"pairs": pairs_count, "outcomes": outcomes, "determined": determined,
            "lucky": lucky, "wrong": pairs_count - determined - lucky,
            "determined_share": round(determined / pairs_count, 4) if pairs_count else 0.0,
            "lucky_share": round(lucky / pairs_count, 4) if pairs_count else 0.0,
            "wrong_share": round((pairs_count - determined - lucky) / pairs_count, 4)
            if pairs_count else 0.0,
            "by_demonstration_size": {str(key): per_size[key] for key in sorted(per_size)},
            "examples": examples}


def evaluate(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Score one demonstration per commit, at each strictness rung, against real sibling edits."""
    sites_by_commit: list[tuple[str, str, list[Site]]] = []
    for record in records:
        sites = [site for site in parse_commit(str(record["diff"]))
                 if site.file.endswith(SOURCE_SUFFIXES) and site.removed and site.added]
        if sites:
            sites_by_commit.append((str(record["repo"]), str(record["sha"]), sites))

    by_rung: dict[str, Any] = {}
    for rung, (context_lines, both) in RUNGS.items():
        pairs: list[tuple[str, Site, Site]] = []
        multi_site = 0
        determined_commits = 0
        by_repo: dict[str, dict[str, int]] = {}
        for repo, _sha, sites in sites_by_commit:
            row = by_repo.setdefault(repo, {"commits": 0, "with_siblings": 0})
            row["commits"] += 1
            if len(sites) < 2:
                continue
            commit_pairs = [(repo, sites[i], sites[j])
                            for i in range(len(sites)) for j in range(len(sites))
                            if i < j and siblings(sites[i], sites[j], context_lines, both)]
            if not commit_pairs:
                continue
            multi_site += 1
            row["with_siblings"] += 1
            pairs.extend(commit_pairs)
        scored = _score(pairs)
        determined_commits = _determined_commits(sites_by_commit, context_lines, both)
        scored.update({
            "context_lines": context_lines,
            "context_both_sides": both,
            "commits_scanned": len(sites_by_commit),
            "commits_with_sibling_sites": multi_site,
            "commits_where_the_demonstration_forced_the_edit": determined_commits,
            "determined_commit_share": round(determined_commits / multi_site, 4)
            if multi_site else 0.0,
            "supply_share": round(multi_site / len(sites_by_commit), 4)
            if sites_by_commit else 0.0,
            "by_repo": by_repo,
        })
        by_rung[rung] = scored
    return {"commits_in_corpus": len(records), "scanned": len(sites_by_commit),
            "by_rung": by_rung}


def _determined_commits(sites_by_commit: Sequence[tuple[str, str, list[Site]]],
                        context_lines: int, both: bool = True) -> int:
    total = 0
    for _repo, _sha, sites in sites_by_commit:
        forced = False
        for i in range(len(sites)):
            for j in range(len(sites)):
                if i >= j or not siblings(sites[i], sites[j], context_lines, both):
                    continue
                result = induce(sites[i], sites[j])
                if result["verdict"] == "exact" and not any(any(flags) for flags in result["copied"]):
                    forced = True
        total += 1 if forced else 0
    return total


def measure(*, corpus: pathlib.Path | None = None) -> dict[str, Any]:
    root = pathlib.Path(__file__).resolve().parents[2]
    corpus = corpus or (root / CORPUS_PATH)
    raw = corpus.read_bytes()
    records = read_corpus(corpus)
    report = evaluate(records)
    report.update({
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "network_calls": 0,
        "incremental_spend_usd": 0,
        "corpus": {
            "path": str(corpus.relative_to(root)) if corpus.is_relative_to(root) else str(corpus),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "records": len(records),
            "repos": sorted({str(record["repo"]) for record in records}),
            "schema": CORPUS_SCHEMA,
        },
    })
    report["what_this_shows"] = _headline(report)
    return report


def _headline(report: Mapping[str, Any]) -> str:
    loose = report["by_rung"]["shape_only"]
    middle = report["by_rung"]["context_any"]
    strict = report["by_rung"]["context_both"]
    return (
        "Of %d real commits from %s, %d (%s) contain sibling sites at one shared line of context; "
        "across %d sibling pairs the demonstrated edit was DETERMINED by the demonstration in %d "
        "(%s), matched only by luck in %d (%s), and failed in %d (%s). %d of the %d multi-site "
        "commits (%s) had a sibling the demonstration forced. Requiring a shared context line on "
        "either side leaves %d commits and %d pairs, and on both sides %d commits and %d pairs. The %d commits with no sibling at all have nothing "
        "for a demonstration to amortise: 'do it once' is one acquisition per instance for them."
        % (loose["commits_scanned"], ", ".join(report["corpus"]["repos"]),
           loose["commits_with_sibling_sites"], loose["supply_share"], loose["pairs"],
           loose["determined"], loose["determined_share"], loose["lucky"], loose["lucky_share"],
           loose["wrong"], loose["wrong_share"], loose["determined_commit_share"].__int__()
           if False else loose["commits_where_the_demonstration_forced_the_edit"],
           loose["commits_with_sibling_sites"],
           round(loose["commits_where_the_demonstration_forced_the_edit"]
                 / loose["commits_with_sibling_sites"], 4)
           if loose["commits_with_sibling_sites"] else 0.0,
           middle["commits_with_sibling_sites"], middle["pairs"],
           strict["commits_with_sibling_sites"], strict["pairs"],
           loose["commits_scanned"] - loose["commits_with_sibling_sites"]))


def summarize(report: Mapping[str, Any]) -> str:
    lines = ["corpus %s (%d records, sha256 %s)"
             % (", ".join(report["corpus"]["repos"]), report["corpus"]["records"],
                report["corpus"]["sha256"][:16]),
             "commits scanned %d" % report["scanned"]]
    for rung, row in report["by_rung"].items():
        lines.append("  rung %s (%d context lines): commits with siblings %d (%s) | pairs %d -> "
                     "determined %d (%s) lucky %d (%s) wrong %d (%s)"
                     % (rung, row["context_lines"], row["commits_with_sibling_sites"],
                        row["supply_share"], row["pairs"], row["determined"],
                        row["determined_share"], row["lucky"], row["lucky_share"],
                        row["wrong"], row["wrong_share"]))
        lines.append("    raw outcomes: " + ", ".join("%s %d" % (name, row["outcomes"][name])
                                                      for name in VERDICTS))
        for size, bucket in row["by_demonstration_size"].items():
            lines.append("    demo size %-2s pairs %3d determined %3d lucky %3d wrong %3d"
                         % (size, bucket["pairs"], bucket["determined"], bucket["lucky"],
                            bucket["wrong"]))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    root = pathlib.Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="How much of real engineering can one demonstration determine?")
    parser.add_argument("--corpus", default=str(root / CORPUS_PATH))
    parser.add_argument("--json", dest="json_path", default=None)
    parser.add_argument("--extract", default=None,
                        help="comma separated name=path pairs; writes a fresh corpus")
    parser.add_argument("--out-corpus", default=str(root / CORPUS_PATH))
    parser.add_argument("--stride", type=int, default=8)
    parser.add_argument("--keep", type=int, default=70)
    ns = parser.parse_args(argv)

    if ns.extract:
        records: list[dict[str, Any]] = []
        provenance = []
        for pair in ns.extract.split(","):
            name, _sep, path = pair.partition("=")
            rows, meta = extract(pathlib.Path(path), name.strip(), stride=ns.stride, keep=ns.keep)
            records.extend(rows)
            provenance.append(meta)
        out = pathlib.Path(ns.out_corpus)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in records),
                       encoding="utf-8")
        print(json.dumps({"provenance": provenance, "records": len(records)}, indent=2))
        return 0

    report = measure(corpus=pathlib.Path(ns.corpus))
    print(summarize(report))
    if ns.json_path:
        target = pathlib.Path(ns.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("\nwritten:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
