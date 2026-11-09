#!/usr/bin/env python3
"""Third hard test set for the intent layer, written and frozen BEFORE the
unsupported-action rule was run against it. Not used to tune anything.
Includes one known trap ('and also' compound) that the rule does not catch.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from intent_map_probe import route  # noqa: E402
from intent_hard_test import grade  # noqa: E402

CASES = [
    ("rename the method get_data to fetch_data in client.py", "python.refactor.rename_symbol.v1"),
    ("how complex is the function render_table", "python.source.complexity.v1"),
    ("make a screenshot of the login page at localhost:8080", "web.browser.rendered.capture.chromedriver"),
    ("run pwd", "shell.command.run"),
    ("make a new function that returns the sum of two lists", "python.source.add_function.v1"),
    ("find hardcoded passwords in the codebase", "python.source.secret_scan.v1"),
    ("which commit broke the parser", "git.history.bisect_regression.v1"),
    ("save the summary as a text file called summary.txt", "text.file.write"),
    ("is this module too complex", "python.source.complexity.v1"),
    ("security review this change", "python.review.diff_security_gate.v1"),
    ("run `pwd`", "shell.command.run"),

    ("click the save button in the app", None),
    ("type the report title into the form for me", None),
    ("open my calculator", None),
    ("take a screenshot of my desktop", None),
    ("send the release notes to the team by email", None),
    ("uninstall the old package", None),
    ("what's the capital of egypt", None),
    ("rename this file and then run tests", None),
    ("scroll down and screenshot the feed", None),
    ("press enter in the terminal", None),
    ("add a parameter and also rename the function", None),
]


def main():
    counts = {}
    for goal, expected in CASES:
        got = route(goal)
        tag = grade(goal, expected, got)
        counts[tag] = counts.get(tag, 0) + 1
        print(f"{tag:13} {goal}  -> {got}")
    total = len(CASES)
    correct = counts.get("RIGHT", 0) + counts.get("CORRECT_NONE", 0)
    print("TOTALS", total, counts)
    print(f"CORRECT {correct}/{total}  WRONG_ACTION {counts.get('WRONG_ACTION', 0)}  WRONG {counts.get('WRONG', 0)}  REFUSED {counts.get('REFUSED', 0)}")


if __name__ == "__main__":
    main()
