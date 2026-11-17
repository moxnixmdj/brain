#!/usr/bin/env python3
"""Does experience buy anything later? The returns-to-experience curve of a memory-first learner.

WHY THIS EXISTS
---------------
The tree has measured what one demonstration determines *inside the commit it came from*
(`systematic_edit_supply_v1`: 16.0% of commits contain a sibling site; 54.9% of the inductive pairs
are reproduced, 21.4% of the value-bearing ones). That is the most generous possible reading of
"experience once", because the demonstration and the work are the same author's same batch.

"Learn it once and keep it forever" is a different claim: it says an edit seen at time t is still
worth something at time t + n, in this repository and in the *next* one. That claim has never been
measured here. It is measurable without any model: a memorised edit is useful later only if the same
edit *shape* occurs again, so count recurrences.

This instrument counts them, on the pinned 393-record corpus from five real repositories, in
chronological order, at the same three context rungs as the supply receipt so the two numbers can be
read side by side.

WHAT IT MEASURES
----------------
  recurrence      of every site, how many have an *earlier* site in the same repository with the same
                  signature (abstracted skeleton + the rung's context). This is the ceiling on what a
                  permanent memory can serve.
  curve           the recurrence rate by chronological quarter of each repository: rising means more
                  experience keeps paying, flat means the marginal demonstration is worth the same
                  fixed small amount forever, falling means the world moves away from what was stored.
  library         how many distinct signatures cover 50/80/90% of the recurrences -- the size of the
                  "skill library" a learner would actually need. Elon's law applied to memory: if a
                  handful of signatures carry the recurrences, the part that is worth keeping is tiny.
  cross_repo      leave-one-repository-out: memory built from the other four repositories, scored on
                  this one. This is the "give it a try in a brand-new environment" number. It is zero
                  when the edit vocabulary of one codebase does not transfer to another, and it is the
                  honest test of "instant learning in new arbitrary environments".
  triviality      the size distribution of what recurs, and how much of it recurs verbatim (no
                  abstraction at all), so a high recurrence rate cannot be mistaken for capability.

HONEST BOUNDS
-------------
The corpus is every sixth commit (sampled to 90 per repository), so an earlier occurrence that fell in
a skipped commit is invisible and recurrence is *under*-counted: these are lower bounds. Signatures are
lexical (identifiers, numbers and string literals become holes), which is the most abstract a
token-level learner can be without semantics.

Model dependency: 0. Network: 0. This counts strings in a pinned file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from collections import Counter
from typing import Any, Iterable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.systematic_edit_supply_v1 import (  # noqa: E402
    SOURCE_SUFFIXES,
    Site,
    induce,
    parse_commit,
    read_corpus,
)

SCHEMA = "BRAIN_SKILL_RECURRENCE_CURVE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
CORPUS_PATH = "canonical/tests/fixtures/systematic_edit_corpus_v1.jsonl"
RUNGS: dict[str, int] = {"shape_only": 0, "context_any": 1, "context_both": 1}


def _keys(site: Site, rung: str) -> tuple[Any, ...]:
    """The membership keys a site offers at one rung. Empty when the rung's context is missing."""
    if rung == "shape_only":
        return (site.skel,)
    before = site.ctx_before[-1:] if site.ctx_before else []
    after = site.ctx_after[:1] if site.ctx_after else []
    if rung == "context_any":
        out: list[Any] = []
        if before:
            out.append((site.skel, "B", before[0]))
        if after:
            out.append((site.skel, "A", after[0]))
        return tuple(out)
    if not (before and after):
        return ()
    return ((site.skel, "BA", before[0], after[0]),)


def _sites(records: Iterable[Mapping[str, Any]]) -> dict[str, list[tuple[str, Site]]]:
    """Sites per repository, in chronological order, with the supply receipt's own filter."""
    by_repo: dict[str, list[tuple[str, Site]]] = {}
    ordered = sorted(enumerate(records), key=lambda pair: (str(pair[1]["date"]), pair[0]))
    for _index, record in ordered:
        for site in parse_commit(str(record["diff"])):
            if not site.file.endswith(SOURCE_SUFFIXES) or not site.removed or not site.added:
                continue
            by_repo.setdefault(str(record["repo"]), []).append((str(record["date"]), site))
    return by_repo


def _share(part: int, whole: int) -> float:
    return round(part / whole, 4) if whole else 0.0


def _quartile_curve(pooled: Sequence[tuple[float, bool]]) -> list[float]:
    """Recurrence rate by relative chronological position: 0 is the repo's first commit, 1 the last."""
    out: list[float] = []
    for quarter in range(4):
        low, high = quarter / 4, (quarter + 1) / 4
        cell = [hit for position, hit in pooled
                if low <= position < high or (quarter == 3 and position == 1.0)]
        out.append(_share(sum(cell), len(cell)))
    return out


def _triviality(recurring: Sequence[Site]) -> dict[str, Any]:
    sizes = Counter(site.size for site in recurring)
    one_line = sizes.get(2, 0)
    substitution = sum(1 for site in recurring if site.skel[0] == site.skel[1])
    return {
        "recurring_sites": len(recurring),
        "one_line_replacements": one_line,
        "one_line_replacement_share": _share(one_line, len(recurring)),
        "pure_substitution_share": _share(substitution, len(recurring)),
        "pure_substitution_definition": "removed and added lines have the same abstract shape, so only a literal moved",
        "size_histogram": {str(size): count for size, count in sorted(sizes.items())[:8]},
        "median_size": sorted(sizes.elements())[len(recurring) // 2] if recurring else 0,
    }


def _replay(recurring: Sequence[tuple[Site, Site]]) -> dict[str, Any]:
    """Of what recurs, how much does replaying the earlier instance actually reproduce?

    Split by whether the change spans two lines on each side, because an advanced edit is exactly the
    one that does: a substitution of one literal is mechanically replayable and says nothing about
    capability.
    """
    def cell(pairs: Sequence[tuple[Site, Site]]) -> dict[str, Any]:
        outcomes: Counter[str] = Counter()
        for earlier, current in pairs:
            outcomes[induce(earlier, current)["verdict"]] += 1
        total = sum(outcomes.values())
        return {
            "pairs": total,
            "outcomes": dict(outcomes),
            "exact_share": _share(outcomes.get("exact", 0), total),
            "wrong_share": _share(sum(outcomes.get(name, 0) for name in
                                      ("rebound_wrong", "mismatch", "conflict")), total),
        }

    structured = [(a, b) for a, b in recurring if a.size >= 4 or b.size >= 4]
    return {
        "all": cell(recurring),
        "structured": cell(structured),
        "reading": "replay across time is weaker than replay inside the commit that taught it",
    }


def measure(*, corpus: pathlib.Path | None = None) -> dict[str, Any]:
    root = pathlib.Path(__file__).resolve().parents[2]
    corpus = corpus or (root / CORPUS_PATH)
    raw = corpus.read_bytes()
    records = read_corpus(corpus)
    by_repo = _sites(records)

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "network_calls": 0,
        "incremental_spend_usd": 0,
        "corpus": {
            "path": str(corpus.relative_to(root)) if corpus.is_relative_to(root) else str(corpus),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "records": len(records),
            "repos": sorted(by_repo),
        },
        "by_rung": {},
    }

    for rung in RUNGS:
        pooled: list[tuple[float, bool]] = []
        frequency: Counter[Any] = Counter()
        per_repo: dict[str, dict[str, Any]] = {}
        recurring_sites: list[Site] = []
        recurring_pairs: list[tuple[Site, Site]] = []
        structured_total = structured_hit = 0

        for repo, dated in by_repo.items():
            first_seen: dict[Any, Site] = {}
            repo_hit = 0
            for position, (_date, site) in enumerate(dated):
                keys = _keys(site, rung)
                if not keys:
                    continue
                matched = next((key for key in keys if key in first_seen), None)
                found = matched is not None
                repo_hit += 1 if found else 0
                if found:
                    frequency[matched] += 1
                    recurring_sites.append(site)
                    if rung == "context_both":
                        recurring_pairs.append((first_seen[matched], site))
                    if site.size >= 4:
                        structured_hit += 1
                if site.size >= 4:
                    structured_total += 1
                for key in keys:
                    first_seen.setdefault(key, site)
                pooled.append((position / max(1, len(dated) - 1), found))
            repo_sites = sum(1 for _date, site in dated if _keys(site, rung))
            per_repo[repo] = {
                "sites": repo_sites,
                "recurrent": repo_hit,
                "share": _share(repo_hit, repo_sites),
            }

        ranked = [count for _key, count in frequency.most_common()]
        cum: list[int] = []
        running = 0
        for count in ranked:
            running += count
            cum.append(running)
        total_hits = sum(ranked)
        library = {}
        for target in (0.5, 0.8, 0.9):
            need = next((i + 1 for i, value in enumerate(cum) if value >= target * total_hits), None)
            library[str(target)] = need

        cross: dict[str, Any] = {}
        for repo in by_repo:
            elsewhere: set[Any] = set()
            for other, dated in by_repo.items():
                if other == repo:
                    continue
                for _date, site in dated:
                    elsewhere.update(_keys(site, rung))
            scored = recurrent = 0
            structured_scored = structured_recurrent = 0
            for _date, site in by_repo[repo]:
                keys = _keys(site, rung)
                if not keys:
                    continue
                scored += 1
                found = any(key in elsewhere for key in keys)
                recurrent += 1 if found else 0
                if site.size >= 4:
                    structured_scored += 1
                    structured_recurrent += 1 if found else 0
            cross[repo] = {"sites": scored, "recurrent": recurrent,
                           "share": _share(recurrent, scored),
                           "structured_sites": structured_scored,
                           "structured_recurrent": structured_recurrent,
                           "structured_share": _share(structured_recurrent, structured_scored)}

        curve = _quartile_curve(pooled)
        report["by_rung"][rung] = {
            "sites": len(pooled),
            "recurrent": total_hits,
            "recurrence_share": _share(total_hits, len(pooled)),
            "structured_sites": {
                "definition": "sites changing at least two lines on each side (size >= 4)",
                "sites": structured_total,
                "recurrent": structured_hit,
                "share": _share(structured_hit, structured_total),
            },
            "distinct_signatures": len(frequency),
            "library_signatures_for": library,
            "curve_by_relative_chronological_quarter": curve,
            "curve_reading": _curve_reading(curve),
            "cross_repository": {
                "sites": sum(row["sites"] for row in cross.values()),
                "recurrent": sum(row["recurrent"] for row in cross.values()),
                "share": _share(sum(row["recurrent"] for row in cross.values()),
                                sum(row["sites"] for row in cross.values())),
                "structured_sites": sum(row["structured_sites"] for row in cross.values()),
                "structured_recurrent": sum(row["structured_recurrent"] for row in cross.values()),
                "structured_share": _share(sum(row["structured_recurrent"] for row in cross.values()),
                                           sum(row["structured_sites"] for row in cross.values())),
                "by_repo": cross,
            },
            "by_repo": per_repo,
            "triviality": _triviality(recurring_sites),
        }
        if rung == "context_both":
            report["by_rung"][rung]["replay"] = _replay(recurring_pairs)

    report["what_this_shows"] = _headline(report)
    return report


def _curve_reading(curve: Sequence[float]) -> str:
    if len(curve) < 3:
        return "insufficient data"
    first, last = curve[0], curve[-1]
    if last > first + 0.05:
        return "rising: later experience recurs more, so more experience keeps paying"
    if last < first - 0.05:
        return "falling: the codebase moves away from what was stored, so memory decays"
    return "flat: the marginal demonstration is worth the same small fixed amount forever"


def _headline(report: Mapping[str, Any]) -> str:
    loose = report["by_rung"]["shape_only"]
    strict = report["by_rung"]["context_both"]
    replay = strict.get("replay", {})
    return (
        "Across %d real changed sites from %s, %d (%s) are a recurrence of an earlier edit shape in "
        "the same repository at the loosest rung, %d (%s) when the neighbourhood must match on both "
        "sides, and only %d of %d (%s) recur once the change spans two lines. Those recurrences come "
        "from %d distinct signatures, of which %s carry 80%%. Memory built from the other four "
        "repositories covers %s of a held-out repository. The rate by chronological quarter is %s "
        "(%s), %s of the recurrences are one-line replacements, and replaying the earlier instance "
        "reproduces the later one exactly %s of the time."
        % (loose["sites"], ", ".join(report["corpus"]["repos"]), loose["recurrent"],
           loose["recurrence_share"], strict["recurrent"], strict["recurrence_share"],
           loose["structured_sites"]["recurrent"], loose["structured_sites"]["sites"],
           loose["structured_sites"]["share"], loose["distinct_signatures"],
           loose["library_signatures_for"]["0.8"], loose["cross_repository"]["share"],
           loose["curve_by_relative_chronological_quarter"], loose["curve_reading"],
           loose["triviality"]["one_line_replacement_share"],
           replay.get("all", {}).get("exact_share") or 0.0))


def summarize(report: Mapping[str, Any]) -> str:
    lines = ["corpus %s (%d records, sha256 %s)"
             % (", ".join(report["corpus"]["repos"]), report["corpus"]["records"],
                report["corpus"]["sha256"][:16])]
    for rung, row in report["by_rung"].items():
        lines.append("  rung %-12s sites %4d recurrent %4d (%s) | structured %3d/%3d (%s) | "
                     "signatures %4d library@50/80/90 %s"
                     % (rung, row["sites"], row["recurrent"], row["recurrence_share"],
                        row["structured_sites"]["recurrent"], row["structured_sites"]["sites"],
                        row["structured_sites"]["share"], row["distinct_signatures"],
                        [row["library_signatures_for"][k] for k in ("0.5", "0.8", "0.9")]))
        lines.append("    curve by chronological quarter %s -> %s"
                     % (row["curve_by_relative_chronological_quarter"], row["curve_reading"]))
        lines.append("    cross-repository %d/%d (%s)"
                     % (row["cross_repository"]["recurrent"], row["cross_repository"]["sites"],
                        row["cross_repository"]["share"]))
        for repo, cell in row["by_repo"].items():
            lines.append("    %-24s sites %3d recurrent %3d (%s)"
                         % (repo, cell["sites"], cell["recurrent"], cell["share"]))
        trivial = row["triviality"]
        lines.append("    what recurs: median size %d, one-line %d (%s), pure substitution %s"
                     % (trivial["median_size"], trivial["one_line_replacements"],
                        trivial["one_line_replacement_share"],
                        trivial["pure_substitution_share"]))
        if "replay" in row:
            lines.append("    replay across time: all %s | structured %s"
                         % (row["replay"]["all"]["outcomes"],
                            row["replay"]["structured"]["outcomes"]))
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    root = pathlib.Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Does an edit seen once still apply later, in this repository and the next one?")
    parser.add_argument("--corpus", default=str(root / CORPUS_PATH))
    parser.add_argument("--json", dest="json_path", default=None)
    ns = parser.parse_args(argv)
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
