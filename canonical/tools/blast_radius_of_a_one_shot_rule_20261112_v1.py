#!/usr/bin/env python3
"""What ONE demonstration buys, and what the SECOND one buys, 2026-11-12. Measurements only. Authority: NONE.

The owner's claim is: show the machine the most advanced coding action ONCE, and it has that
capability permanently.  This tool measures that on the tree's own mechanism for it,
`canonical/swe_kernel/taught_actions/edit_by_example_v1`, over the project's own test files.

The learner's documented rule is: "one changed place gives a rule about exactly that code, and a
second, different place is what makes it general."  That sentence is the whole answer to the
claim, and it is checkable:

  * ONE showing  -- replay the lesson over every file in the tree.  A rule with no blank can
    only match the exact code of the demonstration, so it is expected to rewrite nothing.  A
    capability that rewrites nothing outside the sentence that taught it is not a capability.
  * TWO showings -- the same change shown twice, differing only in the names it touches.  Blanks
    appear, the rule generalises, and now it rewrites real files -- with no check that the
    change is right at any of those places.  That is the blast radius a "permanent" lesson has.

The second half is why the same module also ships `repeat_tried`, which keeps a repeated change
only when a check the project already runs is broken by making that change wrong, place by
place.  The ungated path is measured here; the gated path's cost (a check run per file) is not.

Nothing is written: every rewrite happens on text held in memory.  No network, no model, no
capability registration, no governance file read or changed.  `truth.achieved` stays false.

Run from anywhere:

    python3 canonical/tools/blast_radius_of_a_one_shot_rule_20261112_v1.py
    python3 canonical/tools/blast_radius_of_a_one_shot_rule_20261112_v1.py --json
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import Counter
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as ebe  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
CORPUS_DIR = ROOT / "canonical" / "runtime"

# Each entry: the change shown ONCE, then the same change shown a SECOND time with different
# names, which is the smallest thing that tells the learner what may vary.  `marker` picks the
# files where the general form can actually bite, so the replay is measured where it matters.
DEMOS: tuple[dict[str, Any], ...] = (
    {"name": "?1 == None -> ?1 is None",
     "once": ("def f(a):\n    return a == None\n",
              "def f(a):\n    return a is None\n"),
     "twice": ("def f(a, b):\n    if a == None:\n        return 0\n    return b.x == None\n",
               "def f(a, b):\n    if a is None:\n        return 0\n    return b.x is None\n"),
     "marker": "None"},
    {"name": "pow(?1, 2) -> ?1 ** 2",
     "once": ("a = pow(x, 2)\n", "a = x ** 2\n"),
     "twice": ("a = pow(x, 2)\nb = pow(y.z, 2)\n", "a = x ** 2\nb = y.z ** 2\n"),
     "marker": "pow("},
    {"name": "?1.has_key(?2) -> ?2 in ?1",
     "once": ("a = d.has_key(k)\n", "a = k in d\n"),
     "twice": ("a = d.has_key(k)\nb = e.f.has_key('x')\n", "a = k in d\nb = 'x' in e.f\n"),
     "marker": "has_key"},
    {"name": "?1.assertEquals -> ?1.assertEqual",
     "once": ("class T:\n    def test_a(self):\n        self.assertEquals(add(1, 2), 3)\n",
              "class T:\n    def test_a(self):\n        self.assertEqual(add(1, 2), 3)\n"),
     "twice": ("class T:\n    def test_a(self):\n        self.assertEquals(add(1, 2), 3)\n\n"
               "class U:\n    def test_b(self):\n        box.assertEquals(name, 'x')\n",
               "class T:\n    def test_a(self):\n        self.assertEqual(add(1, 2), 3)\n\n"
               "class U:\n    def test_b(self):\n        box.assertEqual(name, 'x')\n"),
     "marker": "assertEquals"},
)

MOST_MATCHING = 600
MOST_OTHER = 200


def corpus(marker: str) -> tuple[list[pathlib.Path], int]:
    """Files that contain the demonstrated form (all of them, capped), plus a sample of files that do not.

    The second group is there so "nothing else changed" is a measurement and not an assumption: a
    lesson that fires on files with no trace of the form it learned would be matching something
    else entirely.  The marker is a text hint, not the match: rules match syntax trees, so
    ``x==None`` without spaces is the same place as ``x == None`` with them.
    """
    matching: list[pathlib.Path] = []
    other: list[pathlib.Path] = []
    for path in sorted(CORPUS_DIR.rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if marker in text:
            if len(matching) < MOST_MATCHING:
                matching.append(path)
        elif len(other) < MOST_OTHER:
            other.append(path)
    return matching + other, len(matching)


def replay(before: str, after: str, files: list[pathlib.Path]) -> dict[str, Any]:
    rules = ebe.learn(before, after)
    sites = 0
    touched = 0
    refused: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        try:
            edited, count = ebe.rewrite(rules, text, what=str(path.relative_to(ROOT)))
        except ebe.Refused as refusal:
            refused[_reason(str(refusal))] += 1
            continue
        except Exception as problem:  # noqa: BLE001 - a file the learner cannot read proves nothing
            refused[f"unparsed: {type(problem).__name__}"] += 1
            continue
        if count:
            touched += 1
            sites += count
            if len(examples) < 2:
                examples.append({"file": str(path.relative_to(ROOT)), "sites": count,
                                 "sample": _first_change(text, edited)})
    return {"rules": [str(rule) for rule in rules], "sites": sites, "files_rewritten": touched,
            "refused": sum(refused.values()), "refusals": dict(refused.most_common(4)),
            "examples": examples}


def measure() -> dict[str, Any]:
    rows = []
    for demo in DEMOS:
        files, matching = corpus(str(demo["marker"]))
        once = replay(demo["once"][0], demo["once"][1], files)
        twice = replay(demo["twice"][0], demo["twice"][1], files)
        rows.append({"demo": demo["name"], "files_with_the_form": matching,
                     "files_replayed": len(files),
                     "one_showing": once, "two_showings": twice})
    return {
        "schema": "blast_radius_of_a_one_shot_rule/2026-11-12/v3",
        "authority": "NONE",
        "truth_achieved": False,
        "claim": "MEASUREMENTS_ONLY__NO_CAPABILITY_OR_TERMINAL_CREDIT",
        "corpus": {"root": "canonical/runtime",
                   "files_in_corpus": len(list(CORPUS_DIR.rglob("*.py"))),
                   "matching_files_cap": MOST_MATCHING,
                   "other_files_sampled": MOST_OTHER},
        "lessons": rows,
        "what_this_says": (
            "One showing is not a capability with a scope: a single changed place leaves no blank, "
            "so the lesson is about exactly that code and rewrites nothing elsewhere. The second "
            "showing is what makes it general -- and then it rewrites places no check has looked "
            "at. 'Learn it once, then it is permanent' is really 'learn it twice, then gate every "
            "use', which is what `repeat_tried` does at the cost of a check run per file."
        ),
        "what_this_does_not_say": (
            "It does not measure the gated path (`repeat_tried`) and does not score whether any "
            "rewritten site is semantically right; it measures reach, not correctness."
        ),
    }


def _first_change(before: str, after: str) -> dict[str, str] | None:
    old, new = before.splitlines(), after.splitlines()
    for left, right in zip(old, new):
        if left != right:
            return {"before": left.strip()[:90], "after": right.strip()[:90]}
    return None


def _reason(text: str) -> str:
    """A refusal's first clause: the reasons are long and there are only a handful of kinds."""
    head = text.split(";")[0].split("(")[0].strip()
    return head[:110]


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    report = measure()
    if "--json" in argv:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    print("the same change shown once and shown twice, replayed over the project's own production code"
          " (%d files under canonical/runtime)" % report["corpus"]["files_in_corpus"])
    print()
    print("%-24s %5s %6s | %-6s %6s %6s | %-6s %6s %6s" % (
        "lesson", "hint", "files", "1x rule", "sites", "refus", "2x rule", "sites", "refus"))
    print("-" * 78)
    for row in report["lessons"]:
        once, twice = row["one_showing"], row["two_showings"]
        print("%-24s %5d %6d | %-6d %6d %6d | %-6d %6d %6d" % (
            row["demo"], row["files_with_the_form"], row["files_replayed"],
            len(once["rules"]), once["sites"], once["refused"],
            len(twice["rules"]), twice["sites"], twice["refused"]))
    for row in report["lessons"]:
        print()
        print(row["demo"])
        print("  shown once  : %s" % " ; ".join(row["one_showing"]["rules"]))
        print("  shown twice : %s" % " ; ".join(row["two_showings"]["rules"]))
        for example in row["two_showings"]["examples"]:
            if example["sample"]:
                print("  rewrites %s (%d sites): %s  ->  %s" % (
                    example["file"], example["sites"],
                    example["sample"]["before"], example["sample"]["after"]))
        if row["two_showings"]["refusals"]:
            print("  refused   : %s" % "; ".join(
                "%d x %s" % (n, why) for why, n in row["two_showings"]["refusals"].items()))
    print()
    print(report["what_this_says"])
    print(report["what_this_does_not_say"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
