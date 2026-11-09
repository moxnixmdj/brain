#!/usr/bin/env python3
"""Second hard test set for the intent layer, frozen before any run (read-only).

Written after bb6e057b. Not used to tune anything. Expected values are a
registered tool id, or None when no registered tool fits (refusal is correct).
Computer-use requests (click, type, desktop screenshots, open apps) have no
registered tool, so they are expected to be refused.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from intent_map_probe import route  # noqa: E402
from intent_hard_test import grade  # noqa: E402

CASES = [
    ("hey, the variable temp_val is used in like 9 places across the repo, switch them all to temp_value", "python.refactor.rename_symbol.v1"),
    ("Can you tell me how tangled the module core/parser.py is?", "python.source.complexity.v1"),
    ("snap a screenshot of https://status.example.io", "web.browser.rendered.capture.chromedriver"),
    ("i need a new arg timeout on the connect method", "python.source.add_parameter.v1"),
    ("check whether anything in this changeset looks like a security risk", "python.review.diff_security_gate.v1"),
    ("run pwd", "shell.command.run"),
    ("make a new function that returns the max of a list", "python.source.add_function.v1"),
    ("list the functions in server.py that no one calls", "python.source.dead_code.v1"),
    ("find hardcoded API keys in the repo", "python.source.secret_scan.v1"),
    ("what commit introduced the timeout bug", "git.history.bisect_regression.v1"),
    ("write hello world to greeting.txt", "text.file.write"),
    ("save the report as a text file called report.txt", "text.file.write"),
    ("is this function too complex to maintain", "python.source.complexity.v1"),
    ("how much of the test suite would catch an off-by-one error in pagination", "python.source.test_adequacy.v1"),
    ("lines 5 through 9 of main.py should become a function named setup", "python.refactor.extract_function.v1"),
    ("run `ls -la`", "shell.command.run"),

    ("open my browser and click the login button", None),
    ("type my password into the login box for me", None),
    ("open calculator and add 2 and 2", None),
    ("take a screenshot of my desktop", None),
    ("send an email to the team with the release notes", None),
    ("install numpy and pandas", None),
    ("delete every .pyc file in the repo", None),
    ("what's 17 times 23", None),
    ("summarize this pdf for me", None),
    ("rename the class OldParser to Parser and then run the test suite", None),
    ("add a parameter to fetch and also rename it", None),
    ("is it safe to deploy this?", None),
    ("click through the signup flow in the browser and screenshot it", None),
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
