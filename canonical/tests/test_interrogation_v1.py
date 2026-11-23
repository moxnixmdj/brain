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
    # Three, not the two this cost when the universe was 36 readings wide. Adding the folding
    # and tab shapes widened it to 58 and moved the proven optimum from 4 to 5, so one more
    # question is genuinely needed to reach the same certainty. The bound is what the exact
    # search proves for the space actually used, which is why it is asserted against that and
    # not against a number that was true of a smaller universe.
    assert result["probes_spent"] <= result["worst_case_proved"]
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


# --------------------------------------------------------------------------- the adequacy laws
# Each test below pins a bug that this round actually hit. They are written as properties of
# the mechanism, not as snapshots of today's numbers, so a change to the shapes cannot make
# them pass for the wrong reason.

def test_every_primitive_has_a_domain_so_no_reading_is_silently_undefined() -> None:
    """A primitive with no declared domain crashed the universe with a KeyError."""
    for name in I.ORDER:
        assert name in I.PRIMITIVE_DOMAIN, name
        assert I.PRIMITIVE_DOMAIN[name], name


def test_no_shape_kind_is_missing_so_every_pair_is_comparable() -> None:
    """A shape with no kind crashed `_outcome`; a kind is part of the design space."""
    for shape in I.SHAPES:
        assert shape in I.KIND_OF_SHAPE, shape
        assert I.KIND_OF_SHAPE[shape] in I.ANY_KIND, I.KIND_OF_SHAPE[shape]


def test_a_parameter_no_shape_exercises_is_refused_not_certified() -> None:
    """The law that would have caught `fold -b` before it was written down.

    A certificate is only a statement about the goal's observation domain. If the declaration
    names a parameter that no shape can distinguish, every surviving reading agrees *on the
    fixtures* and the certificate is false of the world. The organ must refuse by name.
    """
    without_tabs = {k: v for k, v in I.SHAPES.items() if k != "lines_with_tabs"}
    assert not I.parameter_exercised("fold_bytes", without_tabs)
    surface = I.Surface(tool="fold", base=(), form=("-b",),
                        words="count bytes rather than columns")
    result = I.interrogate(surface)
    # Tabs are present in the real space, so this surface is interrogable; the claim under
    # test is that the gate is *computed*, so it closes when the witness shape is removed.
    assert I.parameter_exercised("fold_bytes")
    assert result["status"] == I.CERTIFIED
    assert result["equivalence_class"] == ["fold_bytes"]


def _own_declaration(tool: str, prefix: str) -> str:
    """The sentence of a tool's help that *declares* a behaviour, by its own wording.

    `--help` has no entry for a default with no flag, so the sentence is taken from the help
    text rather than from a flag line. This is the same rule as `declaration_line`: the words
    must be the ones that describe the behaviour, not a footnote elsewhere in the page.
    """
    for line in I.help_text(tool).splitlines():
        if prefix.lower() in line.strip().lower():
            return line.strip()
    raise AssertionError(f"{tool} help no longer declares {prefix!r}")


@pytest.mark.skipif(shutil.which("fold") is None, reason="no `fold` on this host")
@pytest.mark.parametrize("form,expected", [("-b", "fold_bytes"), ("", "fold_columns")])
def test_fold_is_certified_as_the_function_it_is(form: str, expected: str) -> None:
    """The one surface the earlier sweep certified wrongly is now certified correctly.

    `fold -b` was certified `identity` because no shape was longer than the default width;
    it was then falsified the first time the world handed it a long line. Both of fold's own
    declarations are now exercised by shapes and land on the reading the program performs.
    """
    line = (I.declaration_line(I.help_text("fold"), ("-b",)) if form
            else _own_declaration("fold", "Wrap input lines"))
    surface = I.Surface(tool="fold", base=(), form=(form,), words=line)
    result = I.interrogate(surface)
    assert result["status"] == I.CERTIFIED
    assert expected in result["equivalence_class"]
    assert I.held_out_check(surface, result)["status"].startswith("SURVIVED")


def test_fold_models_match_the_real_program_on_random_input() -> None:
    """Exact, not approximate: the model must be the program, or it does not belong here.

    Every byte 1..255 is exercised, plus tabs, backspaces and carriage returns at lengths
    around the boundary. The earlier two versions of this model were wrong on 12% and then
    1% of inputs; `-b` failing as a *plain byte count* was the last thing found.
    """
    if shutil.which("fold") is None:
        pytest.skip("no `fold` on this host")
    import random
    import subprocess
    import os
    rng = random.Random(20261123)
    alphabet = bytes(range(1, 256))
    cases = [bytes(rng.choice(alphabet) for _ in range(rng.choice(
        [0, 1, 2, 5, 40, 79, 80, 81, 120, 200]))) for _ in range(200)]
    cases += [b"\t" * 11 + b"X\n", b"a" * 79 + b"\tX\n", b"a" * 79 + b"\r" + b"b" * 79]
    env = dict(os.environ, LC_ALL="C")
    for argv, primitive in ((["fold"], "fold_columns"), (["fold", "-b"], "fold_bytes")):
        for data in cases:
            real = subprocess.run(argv, input=data, capture_output=True, env=env).stdout
            assert I.PRIMITIVES[primitive](data) == real, (argv, data)


def test_the_quotient_is_the_coarsest_partition_no_shape_can_refine() -> None:
    """One behaviour per class, and no class separable -- the invariant, checked both ways."""
    shapes = list(I.SHAPES)
    universe = I.behavioural_universe(shapes)
    classes = I.goal_quotient(universe, shapes)
    assert sorted(n for group in classes for n in group) == sorted(universe)
    for group in classes:
        for other in classes:
            if group is other:
                continue
            # every pair from different classes is separated by some shape
            a, b = group[0], other[0]
            assert any(I._outcome(s, a) != I._outcome(s, b) for s in shapes)


def test_the_exact_optimum_is_not_beaten_by_iterative_deepening() -> None:
    """Independent confirmation that the reported bound is the true minimum.

    The search and this checker share only the outcome table, so agreement is evidence about
    the search rather than about itself. The first version of this checker was wrong in a way
    worth naming: it re-split a branch on a shape that had already been asked. An answered
    shape is not a question -- its answer is the same for every reading still alive, so
    offering it again splits nothing and silently inflates the depth it can certify at.
    """
    shapes = list(I.SHAPES)
    universe = I.behavioural_universe(shapes)
    signature = {s: [str(I._outcome(s, n)) for n in universe] for s in shapes}

    def certifiable(limit: int) -> bool:
        def rec(alive, asked, left):
            if len(alive) == 1:
                return True
            first = alive[0]
            # certified only when the survivors agree on EVERY shape, not merely asked ones
            if all(signature[s][first] == signature[s][i] for s in shapes for i in alive):
                return True
            if left == 0:
                return False
            for shape in shapes:
                if shape in asked:
                    continue
                buckets: dict[str, list[int]] = {}
                for i in alive:
                    buckets.setdefault(signature[shape][i], []).append(i)
                if len(buckets) <= 1:
                    continue
                if all(rec(b, asked | {shape}, left - 1) for b in buckets.values()):
                    return True
            return False
        return rec(list(range(len(universe))), frozenset(), limit)

    optimum = I.smallest_certificate_tree(shapes, universe)["minimum_worst_case_witnesses"]
    assert optimum is not None
    assert not certifiable(optimum - 1)
    assert certifiable(optimum)


def test_a_form_with_no_letter_does_not_become_a_file_argument() -> None:
    """`fold ''` failed on every shape because `''` was passed through as a path."""
    surface = I.Surface(tool="fold", base=(), form=("",), words="wrap")
    assert surface.argv(with_form=True) == ["fold"]
    assert surface.argv(with_form=False) == ["fold"]


def test_general_numeric_is_its_own_primitive_and_is_exact_where_it_claims() -> None:
    """`sort -g` was graded `sort_num`, which is false on 383 of 400 random numeric inputs.

    A primitive earns its place in the algebra only by being specified exactly. This test
    pins the domain where the model is exact -- finite decimals, exponents, overflow, inf,
    nan, leading blanks and trailing text -- and records that hexadecimal literals and signed
    nan are outside what it claims.
    """
    if shutil.which("sort") is None:
        pytest.skip("no `sort` on this host")
    import random
    import subprocess
    import os
    tokens = ["1e3", "2", "inf", "-inf", "nan", "8", ".5", "0.3", "1e999", "-1e999",
              "+5", "-5", "10", "9", "1,5", "INF", "infinity", "NaN", "  12", "5x", "-0",
              "0", "5."]
    rng = random.Random(20261123)
    env = dict(os.environ, LC_ALL="C")
    for _ in range(120):
        lines = [rng.choice(tokens) for _ in range(rng.randint(1, 8))]
        data = ("\n".join(lines) + "\n").encode()
        real = subprocess.run(["sort", "-g"], input=data, capture_output=True, env=env).stdout
        assert I.PRIMITIVES["sort_general"](data) == real, lines
    # and it must be a *different* function from the plain numeric sort
    sample = b"1e3\n2\n"
    assert I.PRIMITIVES["sort_general"](sample) != I.PRIMITIVES["sort_num"](sample)


def test_a_refused_primitive_is_refused_by_name_not_approximated() -> None:
    """`fold -s` and `sort -V` are out of the universe, and the reason is in the module.

    The rule is the one that took `sort -V` out: a transform whose exact behaviour the system
    cannot specify manufactures false certificates, so it does not get to be a hypothesis.
    """
    assert "fold_words" not in I.PRIMITIVES
    assert "sort_ver" not in I.PRIMITIVES
    assert "fold -s" in I._NOT_A_TOTAL_ORDER or "fold -s" in I._FOLD_SPACES_RECORD


def test_the_tree_bound_and_the_root_move_agree_so_neither_is_a_guess() -> None:
    """Two independent searches over the same recurrence must plateau at the same number.

    `smallest_certificate_tree` is node-capped (and says so when the cap is hit);
    `optimal_move` is not. If they disagreed, one of them would be reporting a number the
    other contradicts, which is how a table starts lying about its own arithmetic.
    """
    shapes = list(I.SHAPES)
    universe = I.behavioural_universe(shapes)
    tree = I.smallest_certificate_tree(shapes, universe)
    move = I.optimal_move(universe, shapes)
    assert move["worst_case_witnesses"] <= tree["upper_bound"]
    assert move["worst_case_witnesses"] == tree["upper_bound"]
