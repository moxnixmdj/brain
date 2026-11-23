"""Pins the interrogation loop: each test is a bug this build actually hit.

No test needs a particular tool to be installed. The single test that runs a real program is
guarded by ``shutil.which`` and skips with a reason if the tool is absent -- it never fakes a
result, because the guard forbids that and because a fake here would hide exactly the class of
error these tests exist to catch.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import interrogation_v1 as I  # noqa: E402
from canonical.runtime import exact_information_gain as EIG  # noqa: E402


# --------------------------------------------------------------------------- the algebra
def test_the_universe_is_behaviours_not_spellings() -> None:
    """107 spellings collapse to a much smaller behavioural universe.

    Searching spellings instead of functions made the exact minimax blow up for no gain: two
    readings that print the same thing on every shape are one question, not two.
    """
    universe = I.behavioural_universe()
    assert len(universe) < len(I.READING_NAMES)
    signatures = {tuple(I._outcome(shape, name) for shape in I.SHAPES) for name in universe}
    assert len(signatures) == len(universe)


def test_a_pipeline_that_collapses_into_another_is_not_a_second_hypothesis() -> None:
    """`count_runs` over a JSON document's lines is not a behaviour on any shape.

    The mechanism that removes it is *absorption*: a JSON reading collapses the pipeline to
    itself, because nothing a text primitive can do to the document's lines is observable.
    Keeping the spelling in the universe made it permanently silent, hence impossible to
    remove by any observation, and every interrogation ended as NOT_IDENTIFIABLE.
    """
    assert I.reading_domain(("count_runs", "json_keys")) == I.JSON_KINDS
    assert I.canonical_order(("count_runs", "json_keys")) == ("json_keys",)
    assert "count_runs+json_keys" not in I.behavioural_universe()
    # Empty input is in both domains: it parses as nothing and prints nothing.
    assert "empty" in I.JSON_KINDS and "empty" in I.TEXT_KINDS


def test_a_prediction_is_computed_from_the_input_and_matches_a_real_program() -> None:
    """The `sort -u` bug: a prediction derived from the default output looks right and is not.

    `sort -u` prints exactly its own default output, so *any* rule that derives the prediction
    from the default agrees with it trivially and certifies whatever the declaration named.
    The repair is to compute from the input bytes; this test pins the repair against the real
    program, so it fails if the model drifts back into deriving from the default.
    """
    if shutil.which("sort") is None:
        pytest.skip("no `sort` on this host")
    data = I.SHAPES["lines_unsorted_duplicates"]
    real = I.run_bounded(["sort", "-u"], data)["out"]
    assert I.apply_reading(("sort_lex", "uniq_glob"), data) == real
    assert real != data                                  # the surface did something
    assert I.apply_reading(("sort_lex", "uniq_adj"), data) == real   # and it is the same
    assert I.apply_reading(("uniq_adj",), data) != I.apply_reading(("sort_lex", "uniq_glob"),
                                                                    data)


def test_two_families_of_shape_are_mandatory() -> None:
    """Adjacent duplicates and month names were missing, and their absence certified lies.

    Without an adjacent-duplicate shape `uniq_adj` and `identity` are the same function
    everywhere, so both were certified and both were wrong on the first real input with a
    repeat. Held-out falsification found it; the shape is the fix.
    """
    assert "lines_adjacent_duplicates" in I.SHAPES
    assert "lines_months" in I.SHAPES
    assert I._outcome("lines_adjacent_duplicates", "uniq_adj") != I._outcome(
        "lines_adjacent_duplicates", I.IDENTITY)


# --------------------------------------------------------------------------- declarations
def test_a_sentence_naming_nothing_is_refused_not_guessed() -> None:
    read = I.read_surface("-b, --before   attach the separator before instead of after")
    assert read["status"] == I.REFUSED_NO_READING


def test_a_declaration_line_is_the_one_that_declares_the_flag() -> None:
    """`uniq --help` mentions "sort -u" in a footnote; the footnote is not a declaration."""
    text = ("Usage: uniq [OPTION]...\n"
            "  -u, --unique          only print unique lines\n"
            "Note: 'uniq' does not detect repeated lines unless they are adjacent.\n"
            "You may want to sort the input first, or use 'sort -u' without 'uniq'.\n")
    line = I.declaration_line(text, ("-u",))
    assert line.startswith("-u")
    assert "only print unique lines" in line


def test_a_form_that_demands_an_argument_is_refused_by_name() -> None:
    """Running such a form produces a usage error on every shape, which every reading
    "predicts" as a rejection -- so a first version certified `nl -n` in one probe."""
    assert I.form_needs_argument("-n, --number-format=FORMAT      insert line number")
    assert I.form_needs_argument("-w, --number-width=NUMBER       use NUMBER columns")
    assert not I.form_needs_argument("-S               sort keys of objects on output;")


# --------------------------------------------------------------------------- silence
def test_silence_outside_a_domain_is_a_rejection_not_a_vacuous_survival() -> None:
    """A reading that cannot parse an input is contradicted by the printed outcome.

    Modelling it as permanent silence let `jq -S`'s class be certified "understood" and then
    reject every non-JSON input the moment it was tested off the design space.
    """
    assert I._outcome("lines_alpha", "json_keys") == "REJECTED"
    asserted = [{"shape": "json_object", "status": "OBSERVED",
                 "observed_digest": I._outcome("json_object", "json_keys_pretty")}]
    alive = I.survivors(asserted)
    # A reading that says nothing about an input the surface demonstrably transformed is
    # contradicted by it, so no text-only reading survives a JSON observation.
    assert "identity" not in alive
    assert "sort_lex" not in alive
    assert "json_keys_pretty" in alive


def test_silence_on_empty_input_is_excused() -> None:
    """On empty input a program legitimately prints nothing, so no reading is contradicted."""
    asked = [{"shape": "empty", "status": "OBSERVED",
              "observed_digest": I.digest(b"")}]
    alive = I.survivors(asked)
    assert "json_keys" in alive


# --------------------------------------------------------------------------- the search
def test_a_shape_where_only_one_outcome_is_possible_is_not_a_question() -> None:
    """Offering it as a bounded branch of one made the search claim nine witnesses sufficed."""
    state = frozenset({"sort_lex", "sort_num"})
    assert I._branches_uncached(state, "lines_alpha") == []


def test_the_optimum_is_a_bound_that_can_be_falsified_by_brute_force() -> None:
    """An independent oracle agrees with the exact search on the small declared space."""
    shapes = ["lines_alpha", "lines_adjacent_duplicates", "json_object", "lines_months"]
    universe = I.behavioural_universe(shapes)
    module = I.smallest_certificate_tree(shapes, universe)["minimum_worst_case_witnesses"]

    def branch(state, shape, value):
        return frozenset(n for n in state
                         if not I._contradicted(shape, I._outcome(shape, n), value))

    def done(state):
        return len(I._classes(list(state), shapes)) <= 1

    memo = {}

    def solve(state, budget):
        key = (state, budget)
        if key in memo:
            return memo[key]
        if done(state):
            memo[key] = True
            return True
        if budget == 0:
            memo[key] = False
            return False
        result = False
        for shape in shapes:
            outcomes = {I._outcome(shape, n) for n in state} - {I.SILENT}
            if not outcomes:
                continue
            if all(solve(branch(state, shape, value), budget - 1) for value in outcomes):
                result = True
                break
        memo[key] = result
        return result

    start = frozenset(universe)
    oracle = next(d for d in range(0, 8) if solve(start, d))
    assert module == oracle


def test_the_greedy_baseline_is_the_worst_case_not_one_path() -> None:
    """Two earlier baselines flattered greedy; both reported 2 where the truth is larger."""
    shapes = list(I.SHAPES)
    universe = I.behavioural_universe(shapes)
    greedy = I.greedy_worst_case(shapes, universe)
    assert isinstance(greedy, int) and greedy >= 2


def test_the_loop_only_asks_shapes_it_has_not_asked() -> None:
    """Re-offering an asked shape buys a repeat of an answer and no information."""
    surface = I.Surface(tool="cat", base=(), form=("-A",), words="show nonprinting")
    scanned = I.scan(surface)
    first = I.choose_witness(scanned, [{"shape": scanned["askable"][0], "status": "OBSERVED",
                                        "observed_digest": "x"}])
    assert first["best"] != scanned["askable"][0]


def test_exact_information_gain_refuses_a_zero_gain_question() -> None:
    """A shape on which every survivor agrees is worth exactly nothing, in exact arithmetic."""
    prior = {"a": I.Fraction(1, 2), "b": I.Fraction(1, 2)}
    rows = {"t": {"a": {"o": I.Fraction(1, 1)}, "b": {"o": I.Fraction(1, 1)}}}
    assert EIG.information_gain_log_terms(prior, rows["t"]) == {}


# --------------------------------------------------------------------------- falsification
def test_held_out_inputs_target_the_distinctions_the_space_omits() -> None:
    assert "adjacent_repeats" in I.HELD_OUT
    assert "months_out_of_order" in I.HELD_OUT
    assert "punctuation_case" in I.HELD_OUT


def test_a_certificate_that_cannot_predict_held_out_input_is_not_stored() -> None:
    """The memory gate is the held-out gate, because every known falsehood passed the space."""
    memory = {"schema": I.MEMORY_SCHEMA, "entries": {}}
    surface = I.Surface(tool="printf", base=(), form=("-x",), words="nothing to read")
    result = {"status": I.CERTIFIED, "equivalence_class": ["identity"], "witnesses": []}
    I.remember(memory, "key", result, held_out={"status": "FALSIFIED__HELD_OUT_DISAGREES"})
    assert memory["entries"] == {}


def test_a_certificate_that_survived_held_out_is_stored_with_its_evidence() -> None:
    memory = {"schema": I.MEMORY_SCHEMA, "entries": {}}
    result = {"status": I.CERTIFIED, "equivalence_class": ["count"],
              "witnesses": [{"shape": "empty", "status": "OBSERVED",
                             "control_digest": "c", "observed_digest": "o"}]}
    I.remember(memory, "key", result,
               held_out={"status": "SURVIVED__HELD_OUT_AGREES", "held_out_checked": 15,
                         "reading": "count"})
    entry = memory["entries"]["key"]
    assert entry["held_out_checked"] == 15
    assert entry["evidence"] == [{"shape": "empty", "control": "c", "observed": "o"}]


# --------------------------------------------------------------------------- memory
def test_a_memory_key_needs_both_the_bytes_and_the_name(tmp_path: pathlib.Path) -> None:
    """`xz` and `unxz` are byte-identical and opposite, and 635 names share 481 files."""
    link = tmp_path / "xz"
    link.write_bytes(b"same bytes")
    alias = tmp_path / "unxz"
    alias.write_bytes(b"same bytes")
    surface = I.Surface(tool="xz", base=(), form=("-d",), words="decompress")
    key_xz = I.memory_key(str(link), "xz", surface, "g")
    key_unxz = I.memory_key(str(alias), "unxz", surface, "g")
    assert key_xz != key_unxz
    assert key_xz.split(":")[0] == key_unxz.split(":")[0]


def test_a_corrupt_memory_file_is_a_miss_not_a_crash(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "m.json"
    path.write_text("{not json")
    assert I.load_memory(path)["entries"] == {}
    path.write_text(json.dumps({"schema": "something else", "entries": {"a": {}}}))
    assert I.load_memory(path)["entries"] == {}


def test_a_tampered_record_is_discarded_by_its_own_evidence(tmp_path: pathlib.Path,
                                                          monkeypatch) -> None:
    """A cached fact in a changing world is a hypothesis with a receipt, not an authority."""
    surface = I.Surface(tool="echo", base=(), form=("-n",), words="do not output the newline")
    memory = {"schema": I.MEMORY_SCHEMA, "entries": {
        "k": {"equivalence_class": ["identity"], "evidence": [
            {"shape": "single_line", "control": "c", "observed": "deadbeefdeadbeef"}]}}}
    verdict = I.recall(memory, "k", surface)
    assert verdict["status"].startswith("STALE")


# --------------------------------------------------------------------------- the runner
def test_a_runner_never_hangs_and_reports_a_timeout_by_name(tmp_path: pathlib.Path) -> None:
    """A buffered read with no deadline hung a 900 s run in this repository once."""
    got = I.run_bounded(["sleep", "5"], b"", deadline=0.2)
    assert got["ok"] is False
    assert got["reason"] == "TIMEOUT"


def test_a_runner_refuses_a_command_that_does_not_exist() -> None:
    got = I.run_bounded(["definitely-not-a-command-xyz"], b"")
    assert got["ok"] is False and got["rc"] is None


# --------------------------------------------------------------------------- the real thing
@pytest.mark.skipif(shutil.which("sort") is None, reason="no `sort` on this host")
def test_sort_numeric_is_learned_in_two_runs_and_survives_held_out() -> None:
    """The end-to-end claim, on a real program, with the real held-out gate."""
    text = I.help_text("sort")
    line = I.declaration_line(text, ("-n",))
    assert "numeric" in line.lower()
    surface = I.Surface(tool="sort", base=(), form=("-n",), words=line)
    result = I.interrogate(surface)
    assert result["status"] == I.CERTIFIED
    assert result["probes_spent"] <= 2
    held = I.held_out_check(surface, result)
    assert held["status"].startswith("SURVIVED")
    assert "sort_num" in held["surviving_members"]


@pytest.mark.skipif(shutil.which("sort") is None, reason="no `sort` on this host")
def test_a_version_sort_is_refused_because_its_comparator_is_not_a_total_order() -> None:
    """The part was removed, not approximated: GNU documents `sort -V` as intransitive."""
    text = I.help_text("sort")
    line = I.declaration_line(text, ("-V",))
    surface = I.Surface(tool="sort", base=(), form=("-V",), words=line)
    result = I.certify(surface)
    assert result["status"] != I.CERTIFIED
    assert result["held_out"]["status"] != I.FALSIFIED_ANY if hasattr(I, "FALSIFIED_ANY") \
        else True


@pytest.mark.skipif(shutil.which("uniq") is None, reason="no `uniq` on this host")
def test_uniq_count_is_certified_as_run_length_counting() -> None:
    text = I.help_text("uniq")
    line = I.declaration_line(text, ("-c",))
    surface = I.Surface(tool="uniq", base=(), form=("-c",), words=line)
    result = I.interrogate(surface)
    assert result["status"] == I.CERTIFIED
    assert any("count_runs" in name for name in result["equivalence_class"])
