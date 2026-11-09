#!/usr/bin/env python3
"""Hard, realistic test set for the plain-language intent layer (read-only).

Written after intent_map_probe.py was frozen. Nothing here is used to tune the
patterns. Expected values name a tool that exists in the verified registry, or
None when no registered tool fits the request (the correct answer is a refusal).

Grading:
  RIGHT         got == expected
  REFUSED       got is None and expected is a tool (a missed request)
  WRONG         got is a different tool
  WRONG_ACTION  got is a tool but expected is None (the dangerous case)
  CORRECT_NONE  got is None and expected is None
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from intent_map_probe import route  # noqa: E402

CASES = [
    # Real requests, messy wording, typos, casual tone
    ("pls rename fetch_usr to fetch_user everywhere in src", "python.refactor.rename_symbol.v1"),
    ("theres a bunch of functions in utils.py nobody calls, find them", "python.source.dead_code.v1"),
    ("is there a password hardcoded anywhere in config.py?", "python.source.secret_scan.v1"),
    ("which commit broke the build? it was green last friday", "git.history.bisect_regression.v1"),
    ("make a file summary.txt containing the three bullet points above", "text.file.write"),
    ("how complex is process_order in orders.py", "python.source.complexity.v1"),
    ("take a screenshot of localhost:3000 after login", "web.browser.rendered.capture.chromedriver"),
    ("add an argument verbose=False to the save function", "python.source.add_parameter.v1"),
    ("does this diff leak anything sensitive or open a security hole", "python.review.diff_security_gate.v1"),
    ("would the unit tests notice if someone flipped a < to <= in this function", "python.source.test_adequacy.v1"),
    ("run `git status` in the repo", "shell.command.run"),
    ("execute: cat README.md", "shell.command.run"),
    ("create a fresh function parse_line(s) that splits on tabs", "python.source.add_function.v1"),
    ("pull the body of lines 40-60 of app.py out into a helper", "python.refactor.extract_function.v1"),
    ("move the function load_config from settings.py into config_io.py", "python.refactor.move_function.v1"),
    ("make a tar.gz of the src folder", "archive.tar_gz.create_from_manifest"),
    ("get the text out of report.pdf", "pdf.extract.text.pypdf"),
    ("use jq to pull the name field from users.json", "json.query.jq"),
    ("did my change drop test coverage", "python.review.diff_coverage_gate.v1"),
    ("audit the unittest suite for weak assertions", "python.tests.audit.unittest"),
    ("extract lines 10 to 20 in utils.py into a function called helper", "python.refactor.extract_function.v1"),
    ("security review my migration script before I run it", "python.review.diff_security_gate.v1"),
    ("screenshot the dashboard at http://example.com", "web.browser.rendered.capture.chromedriver"),
    ("the sorting function is hard to read, how hard", "python.source.complexity.v1"),
    ("run ls -la", "shell.command.run"),
    ("make a new function that reads a csv and returns rows", "python.source.add_function.v1"),

    # Requests with no matching registered tool: the correct answer is a refusal
    ("delete the old build folder", None),
    ("add docstrings to every public function in the package", None),
    ("run mypy over the project and tell me the errors", None),
    ("what's the weather in cairo today", None),
    ("book me a flight to cairo", None),
    ("find every place we use the old logger name", None),
    ("is my change safe to ship?", None),

    # Compound and distractor requests: one tool cannot honestly answer these
    ("rename the file old.py to new.py and then run the tests", None),
    ("the function is way too complicated, check its complexity, then refactor it", None),
    ("tell me which tests would fail if I deleted the cache module", None),
]


def grade(goal, expected, got):
    if expected is None:
        return "CORRECT_NONE" if got is None else "WRONG_ACTION"
    if got is None:
        return "REFUSED"
    return "RIGHT" if got == expected else "WRONG"


def main():
    counts = {}
    for goal, expected in CASES:
        got = route(goal)
        tag = grade(goal, expected, got)
        counts[tag] = counts.get(tag, 0) + 1
        print(f"{tag:13} {goal}  -> {got}")
    total = len(CASES)
    print("TOTALS", total, counts)
    correct = counts.get("RIGHT", 0) + counts.get("CORRECT_NONE", 0)
    print(f"CORRECT {correct}/{total}  WRONG_ACTION {counts.get('WRONG_ACTION', 0)}  WRONG {counts.get('WRONG', 0)}  REFUSED {counts.get('REFUSED', 0)}")


if __name__ == "__main__":
    main()
