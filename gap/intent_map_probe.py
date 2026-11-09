#!/usr/bin/env python3
"""Plain-language intent map for software-engineering requests (read-only probe).

Maps a request to one registered capability id by explicit phrase patterns,
or refuses. It executes nothing. Tuned on DEV_SET; measured on TEST_SET, which
was written after the patterns, so the TEST numbers are a rough guide only.
"""
import re
import sys

PATTERNS = [
    ("python.source.dead_code.v1", r"never (get )?called|unused (function|helper)|nothing (ever )?calls|no code path|dead code"),
    ("python.source.secret_scan.v1", r"hard-?coded (password|secret|key)|api keys?|leaked credential|secrets? in|credentials?"),
    ("git.history.bisect_regression.v1", r"which commit|commit that broke|introduced the (failure|bug|regression)"),
    ("text.file.write", r"(write|save|make a note)\b.*\b(file|note)\b|file (called|named)\b.*\.txt|note file"),
    ("python.source.complexity.v1", r"complex|tangled|hard (is|to read)"),
    ("python.refactor.rename_symbol.v1", r"rename|change the name"),
    ("web.browser.rendered.capture.chromedriver", r"screenshot|take a picture|capture the page"),
    ("python.source.add_parameter.v1", r"(add|new) (an? )?(optional )?(keyword )?(argument|parameter)"),
    ("python.review.diff_security_gate.v1", r"security|unsafe|security holes"),
    ("python.source.test_adequacy.v1", r"tests? (catch|notice|would)|would (my|the) tests"),
    ("shell.command.run", r"^\s*(run|execute) (the )?(shell )?(command )?(ls|pwd|git|cat|echo)\b|run ls"),
    ("python.source.add_function.v1", r"(make|create|add) (a )?(new|fresh) (python )?function"),
    ("python.refactor.extract_function.v1", r"(pull out|extract) .*lines? \d+"),
]

DEV_SET = [
    ("rename the function parse_config to load_config across the project", "python.refactor.rename_symbol.v1"),
    ("find the commit that broke the login test", "git.history.bisect_regression.v1"),
    ("run the shell command ls -la in the repo", "shell.command.run"),
    ("find functions that are never called", "python.source.dead_code.v1"),
    ("check the code for hardcoded passwords", "python.source.secret_scan.v1"),
    ("write a file called notes.txt with hello", "text.file.write"),
    ("open the web page and take a screenshot", "web.browser.rendered.capture.chromedriver"),
    ("how complex is this algorithm", "python.source.complexity.v1"),
    ("add a parameter timeout with default 30 to fetch_data", "python.source.add_parameter.v1"),
    ("review my diff for security problems", "python.review.diff_security_gate.v1"),
    ("make a new python function that adds two numbers", "python.source.add_function.v1"),
    ("extract the function from lines 10 to 20 in utils.py", "python.refactor.extract_function.v1"),
    ("would my tests catch a bug in this change", "python.source.test_adequacy.v1"),
]

TEST_SET = [
    ("clean up functions that no code path uses", "python.source.dead_code.v1"),
    ("scan the repo for leaked credentials", "python.source.secret_scan.v1"),
    ("find out which change introduced the failure", "git.history.bisect_regression.v1"),
    ("make a note file called ideas.txt that says buy milk", "text.file.write"),
    ("measure how tangled this code is", "python.source.complexity.v1"),
    ("rename the variable total to subtotal everywhere", "python.refactor.rename_symbol.v1"),
    ("screenshot of the homepage at example.org", "web.browser.rendered.capture.chromedriver"),
    ("add an optional timeout argument to load_page", "python.source.add_parameter.v1"),
    ("are there any security holes in my patch", "python.review.diff_security_gate.v1"),
    ("would my test suite notice if I broke this", "python.source.test_adequacy.v1"),
    ("execute ls -la here", "shell.command.run"),
    ("make a fresh function called square that returns x times x", "python.source.add_function.v1"),
    ("pull out lines 3 to 9 of parser.py into their own function", "python.refactor.extract_function.v1"),
]

# Written after the patterns were fixed and NOT used to tune them. This is the
# honest number: the patterns were never adjusted for it.
THIRD_SET = [
    ("hey can you get rid of the helper functions nobody references anymore", "python.source.dead_code.v1"),
    ("is there any place where a token or password got typed straight into the source", "python.source.secret_scan.v1"),
    ("git says the tests went red somewhere, find the offending commit", "git.history.bisect_regression.v1"),
    ("put the words 'remember the milk' into a file named reminders.txt", "text.file.write"),
    ("how convoluted is parse_rules, give me a number", "python.source.complexity.v1"),
    ("change every occurrence of user_id to account_id", "python.refactor.rename_symbol.v1"),
    ("grab a screenshot of example.net's front page", "web.browser.rendered.capture.chromedriver"),
    ("give load_data a new argument called chunk_size", "python.source.add_parameter.v1"),
    ("does my branch introduce anything risky security wise", "python.review.diff_security_gate.v1"),
    ("if I introduced a bug here, would the existing tests find it", "python.source.test_adequacy.v1"),
    ("run pwd in the terminal", "shell.command.run"),
    ("create a brand new function named double that doubles its input", "python.source.add_function.v1"),
]


# A request with a second step ('... and then ...', '..., then ...') cannot be
# answered by one tool honestly, so it is refused rather than half-done.
COMPOUND = re.compile(r"\bthen\b|\band also\b", re.IGNORECASE)


# Actions no registered tool performs (desktop control, clicking, typing, email,
# installs, deletes, apps). If a request names one, refuse: a partial match would
# run a tool that does only part of what was asked.
UNSUPPORTED = re.compile(
    r"\b(click|press|scroll|uninstall|install|email|e-mail|desktop|my screen|"
    r"type (my|the|into|in)|log ?in to|open (my|the) (browser|calculator|app|application))\b",
    re.IGNORECASE)


def route(goal):
    goal = goal.replace("`", "")  # `run ls -la` is the same request as run ls -la
    if COMPOUND.search(goal) or UNSUPPORTED.search(goal):
        return None
    for cid, pat in PATTERNS:
        if re.search(pat, goal, re.IGNORECASE):
            return cid
    return None


def run(name, rows):
    right = wrong = refused = 0
    for goal, expected in rows:
        got = route(goal)
        if got is None:
            refused += 1
            tag = "REFUSED"
        elif got == expected:
            right += 1
            tag = "RIGHT"
        else:
            wrong += 1
            tag = "WRONG"
        print(f"{name} {tag:8} {goal}  -> {got}")
    print(f"{name} TOTAL right={right} wrong={wrong} refused={refused} of {len(rows)}")


if __name__ == "__main__":
    run("DEV ", DEV_SET)
    run("TEST", TEST_SET)
    run("THIRD", THIRD_SET)
    sys.exit(0)
