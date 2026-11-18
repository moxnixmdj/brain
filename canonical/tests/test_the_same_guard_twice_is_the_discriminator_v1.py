"""The switch must not change the program, and the refinement must be fitted, not guessed.

Three failure modes were seen while building this on real code before anything was believed:

  * the node id was built by prefixing the test file onto a name that already carried it
    (`tests/x.py::tests/x.py::test_y`), so pytest ran nothing, returned "no tests ran", and an
    empty run read as a pass until exit code 5 was made a `NO_RUN` instead of a verdict;
  * the discriminator candidates were capped in declaration order, which silently dropped
    `self.envvar` from `Option.get_error_hint` -- the one value that separates the two firings of
    `if self.show_envvar:` -- and the run reported NO_EXACT_FIT on the case it was built for;
  * `predicate_candidates` over a single occurrence yields a "fit" that separates nothing, so a
    guard that fired once must not produce a refinement at all.

These tests execute the instrumented module. Nothing here asserts that instrumentation "looks right":
the same program is run twice, once plain and once instrumented, and the output is compared.
"""

import ast
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "tools"))
sys.path.insert(0, str(ROOT))

import the_same_guard_twice_is_the_discriminator_v1 as switch  # noqa: E402

PROGRAM = '''
import sys


class Option:
    def __init__(self, show_envvar, envvar):
        self.show_envvar = show_envvar
        self.envvar = envvar

    def hint(self):
        result = ""
        if self.show_envvar:
            result += " (env var: '%s')" % (self.__dict__.get("envvar"),)
        return result


def main():
    for show, envvar in ((True, "bar"), (True, None)):
        print("Error: missing option" + Option(show, envvar).hint())


main()
'''


def run(tmp_path, source, *, flip=None, log=None):
    path = tmp_path / "prog.py"
    path.write_text(source, encoding="utf-8")
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("BRAIN_FLIP", None)
    env.pop("BRAIN_SWITCH_LOG", None)
    if flip:
        env["BRAIN_FLIP"] = json.dumps({str(k): list(v) for k, v in flip.items()})
    if log is not None:
        env["BRAIN_SWITCH_LOG"] = str(log)
    done = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, env=env,
                          timeout=60)
    return done.stdout, done.stderr, done.returncode


def instrumented():
    source, sites = switch.instrument_module(PROGRAM)
    return source, sites


def test_instrumentation_does_not_change_the_program(tmp_path):
    plain = run(tmp_path, PROGRAM)[0]
    source, _sites = instrumented()
    assert run(tmp_path, source)[0] == plain
    assert "env var: 'bar'" in plain and "env var: 'None'" in plain


def test_one_occurrence_flip_reaches_exactly_one_case(tmp_path):
    source, sites = instrumented()
    guard = next(site for site in sites if site["guard"] == "self.show_envvar")
    flipped_second = run(tmp_path, source, flip={guard["sid"]: [2]})[0]
    flipped_first = run(tmp_path, source, flip={guard["sid"]: [1]})[0]
    plain = run(tmp_path, PROGRAM)[0]
    assert flipped_second.splitlines()[0] == plain.splitlines()[0]
    assert flipped_second.splitlines()[1] != plain.splitlines()[1]
    assert flipped_second.splitlines()[1] == "Error: missing option"
    assert flipped_first.splitlines()[0] == "Error: missing option"


def test_the_log_records_the_value_that_separates_the_occurrences(tmp_path):
    source, sites = instrumented()
    guard = next(site for site in sites if site["guard"] == "self.show_envvar")
    log = tmp_path / "switch.jsonl"
    run(tmp_path, source, log=log)
    rows = [row for row in switch.read_log(log) if int(row["sid"]) == guard["sid"]]
    assert [row["n"] for row in rows] == [1, 2]
    assert [row["truth"] for row in rows] == [True, True]
    # The guard's own operand does not separate them; the scope does.
    assert rows[0]["operands"]["self.envvar"] != rows[1]["operands"]["self.envvar"]


def logged_site(tmp_path, program=PROGRAM, guard_text="self.show_envvar"):
    source, sites = instrumented() if program is PROGRAM else switch.instrument_module(program)
    guard = next(site for site in sites if site["guard"] == guard_text)
    log = tmp_path / "switch.jsonl"
    run(tmp_path, source, log=log)
    rows = [row for row in switch.read_log(log) if int(row["sid"]) == guard["sid"]]
    return guard, rows


def test_the_refinement_is_selected_by_exact_fit(tmp_path):
    guard, rows = logged_site(tmp_path)
    fit = switch.fit_predicate(guard, rows, must_be_false_at=2)
    assert fit is not None
    assert fit["predicate"] == "self.envvar is not None"
    assert fit["true_at"] == [1] and fit["false_at"] == 2
    assert switch.refine_guard(guard, fit["predicate"]) == \
        "(self.show_envvar) and (self.envvar is not None)"


ONCE = """
class Option:
    def __init__(self, show_envvar, envvar):
        self.show_envvar = show_envvar
        self.envvar = envvar

    def hint(self):
        if self.show_envvar:
            return " (env var: '%s')" % (self.__dict__.get("envvar"))
        return ""


print("Error: missing option" + Option(True, None).hint())
"""


def test_a_guard_that_fired_once_has_no_discriminator(tmp_path):
    guard, rows = logged_site(tmp_path, program=ONCE)
    assert len(rows) == 1
    # Nothing else went through the guard, so a "refinement" would explain nothing: refusing is the
    # honest answer, and it is the difference between a fit and a coincidence.
    assert switch.fit_predicate(guard, rows, must_be_false_at=1) is None


def test_the_predicate_test_reads_the_logged_repr():
    assert switch.holds("self.envvar is not None", "None") is False
    assert switch.holds("self.envvar is not None", "'bar'") is True
    assert switch.holds("self.envvar is None", "None") is True
    assert switch.holds("self.envvar is not None", "<raised AttributeError>") is False
    assert switch.holds("count == 0", "0") is True
    assert switch.holds("count == 0", "'zero'") is False
    # a predicate over a value the log could not render is unanswerable, and unanswerable is not a fit
    assert switch.holds("count == 0", "<__main__.Option object at 0x1>") is None


def test_the_refinement_is_written_into_the_real_source_and_parses(tmp_path):
    _source, sites = instrumented()
    site = next(s for s in sites if s["guard"] == "self.show_envvar")
    patched = switch.replace_test(PROGRAM, site, "(self.show_envvar) and (self.envvar is not None)")
    assert patched is not None
    assert "self.envvar is not None" in patched
    ast.parse(patched)
    # and the patched program now prints the correctly formatted second line
    assert run(tmp_path, patched)[0].splitlines()[1] == "Error: missing option"


def test_a_multi_line_guard_is_not_instrumented():
    program = "def f(a, b):\n    if (\n        a\n        and b\n    ):\n        return 1\n    return 0\n"
    source, sites = switch.instrument_module(program)
    assert sites == []
    assert "if __brain_switch__(" not in source  # the header defines it; nothing calls it


def test_line_numbers_survive_the_rewrite():
    source, sites = instrumented()
    assert switch.HEADER in source
    body = source.replace(switch.HEADER, "", 1)
    assert body.count("\n") == PROGRAM.count("\n")
    for site in sites:
        line = body.splitlines()[site["line"] - 1].strip()
        assert line.startswith("if __brain_switch__("), line


SLICES = """
template = "./x.html"
if template[:2] == "./":
    print("relative")
else:
    print("absolute")
"""


def test_constants_and_slices_are_not_operands(tmp_path):
    """`if template[:2] == './'` has the operands `2` and `:2`; splicing `lambda: (:2)` is a SyntaxError.

    This is not hypothetical: it made jinja2's `loaders.py` unimportable, so the whole test file
    produced no verdicts and three rows of the first sweep were unmeasurable.
    """
    plain = run(tmp_path, SLICES)[0]
    source, sites = switch.instrument_module(SLICES)
    assert sites, "the guard exists and must be instrumented"
    labels = sites[0]["operands"]
    assert ":2" not in labels and "2" not in labels, labels
    assert "lambda: (:2)" not in source and 'lambda: (2)' not in source
    assert run(tmp_path, source)[0] == plain == "relative\n"
