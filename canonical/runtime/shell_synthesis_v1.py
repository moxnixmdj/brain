"""Shell pipeline synthesis from input/output examples.

The creature is given *what the result should look like*, never the command.
It searches a typed space of stdin->stdout filters, evaluates hypotheses with a
fast exact interpreter, and then proves the winner by executing it on the real
computer surface.

Why an interpreter is not cheating: the interpreter only orders the search.
Nothing is admitted until the real shell produces the exact expected bytes on
every example, so a modelling mistake becomes a rejected candidate, never a
false skill.  The speed difference is what makes "instant" possible: thousands
of hypotheses are scored in microseconds, and only the winner is executed.

The search is not a task table.  Stages are typed transformations; the same
engine derives word counting, unique-word listing, field extraction, line
selection and their compositions from the examples alone.
"""
from __future__ import annotations

import difflib
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_SHELL_SYNTHESIS_V1"

TEXT = "TEXT"
LINES = "LINES"
COUNT = "COUNT"


# --------------------------------------------------------------------------- #
# exact interpreters for the admitted stages                                   #
# --------------------------------------------------------------------------- #


def as_lines(text: str) -> list[str]:
    if not text:
        return []
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def as_text(lines: Sequence[str]) -> str:
    return "\n".join(lines) + "\n" if lines else ""


def _wc_l(text: str) -> str:
    return str(text.count("\n")) + "\n"


def _sort(text: str) -> str:
    return as_text(sorted(as_lines(text), key=lambda line: line.encode()))


def _sort_reverse(text: str) -> str:
    return as_text(sorted(as_lines(text), key=lambda line: line.encode(), reverse=True))


_NUMBER_PREFIX = re.compile(r"^\s*([-+]?\d+(?:\.\d+)?)")


def _sort_numeric(text: str) -> str:
    # GNU sort is not stable without --stable: equal numeric keys fall back to
    # a whole-line comparison.  Mirroring that here keeps the interpreter and
    # the real shell in agreement.
    def key(line: str) -> tuple[int, float, bytes]:
        match = _NUMBER_PREFIX.match(line)
        rank = (0, float(match.group(1))) if match else (1, 0.0)
        return (rank[0], rank[1], line.encode())

    return as_text(sorted(as_lines(text), key=key))


def _sort_unique(text: str) -> str:
    return as_text(sorted(set(as_lines(text)), key=lambda line: line.encode()))


def _uniq(text: str) -> str:
    out: list[str] = []
    for line in as_lines(text):
        if not out or out[-1] != line:
            out.append(line)
    return as_text(out)


def _drop_empty(text: str) -> str:
    return as_text([line for line in as_lines(text) if line != ""])


def _split_words(text: str) -> str:
    return re.sub(r" +", "\n", text)


def _lower(text: str) -> str:
    return text.lower()


def _upper(text: str) -> str:
    return text.upper()


def _first_field(text: str) -> str:
    return as_text([(line.split() or [""])[0] for line in as_lines(text)])


def _cut(column: int) -> Callable[[str], str]:
    return _cut_on(",", column)


def _cut_on(separator: str, column: int) -> Callable[[str], str]:
    def cut(text: str) -> str:
        return as_text(
            [(line.split(separator) + [""] * column)[column - 1] for line in as_lines(text)]
        )

    return cut


def _field(column: int) -> Callable[[str], str]:
    def field(text: str) -> str:
        return as_text([(line.split() + [""] * column)[column - 1] for line in as_lines(text)])

    return field


def _sum_last_column(text: str) -> str:
    total = 0.0
    for line in as_lines(text):
        field = line.split(",")[-1].strip()
        try:
            total += float(field)
        except ValueError:
            pass
    return "%.0f\n" % total


def _sum_first_column(text: str) -> str:
    total = 0.0
    for line in as_lines(text):
        field = line.split(",")[0].strip()
        try:
            total += float(field)
        except ValueError:
            pass
    return "%.0f\n" % total


def _drop_header(text: str) -> str:
    return as_text(as_lines(text)[1:])


def _head(n: int) -> Callable[[str], str]:
    return lambda text: as_text(as_lines(text)[:n])


def _tail(n: int) -> Callable[[str], str]:
    return lambda text: as_text(as_lines(text)[-n:])


def _sed_line(n: int) -> Callable[[str], str]:
    return lambda text: as_text(as_lines(text)[n - 1: n])


@dataclass(frozen=True)
class Stage:
    shell: str
    input_type: str
    output_type: str
    apply: Callable[[str], str]

    def accepts(self, kind: str) -> bool:
        """Raw file text is already a sequence of lines; a line stream is not
        automatically a bag of words.  Only that direction is widened."""
        if self.input_type == LINES:
            return kind in (TEXT, LINES)
        return kind == self.input_type


STAGES: tuple[Stage, ...] = (
    Stage("sort", LINES, LINES, _sort),
    Stage("sort -r", LINES, LINES, _sort_reverse),
    Stage("sort -n", LINES, LINES, _sort_numeric),
    Stage("sort -u", LINES, LINES, _sort_unique),
    Stage("uniq", LINES, LINES, _uniq),
    Stage("grep -v '^$'", LINES, LINES, _drop_empty),
    Stage("tr -s ' ' '\\n'", TEXT, LINES, _split_words),
    Stage("tr '[:upper:]' '[:lower:]'", TEXT, TEXT, _lower),
    Stage("tr '[:lower:]' '[:upper:]'", TEXT, TEXT, _upper),
    Stage("awk '{print $1}'", LINES, LINES, _first_field),
    Stage("cut -d, -f1", LINES, LINES, _cut(1)),
    Stage("cut -d, -f2", LINES, LINES, _cut(2)),
    Stage("tail -n +2", LINES, LINES, _drop_header),
    Stage("head -n 3", LINES, LINES, _head(3)),
    Stage("tail -n 3", LINES, LINES, _tail(3)),
    Stage("sed -n '3p'", LINES, LINES, _sed_line(3)),
    Stage("awk -F, '{s+=$NF} END {printf \"%.0f\\n\", s}'", LINES, COUNT, _sum_last_column),
    Stage("awk -F, '{s+=$1} END {printf \"%.0f\\n\", s}'", LINES, COUNT, _sum_first_column),
    Stage("wc -l", LINES, COUNT, _wc_l),
)

_BY_SHELL = {stage.shell: stage for stage in STAGES}

_SEPARATORS = ((",", ","), ("\t", "\\t"), ("|", "|"), (";", ";"), (":", ":"))


def instantiate(examples: Sequence[tuple[str, str]]) -> tuple[Stage, ...]:
    """The stage vocabulary, extended by parameters read off the data.

    The base stages are a grammar, not a task list: ``cut`` needs a separator
    and a field index, ``head``/``tail`` need a count, ``awk`` needs a field.
    Rather than enumerating every combination in advance, the parameters are
    taken from what the examples actually contain: separators that appear in
    the inputs, and line counts that appear in the expected outputs.  A data
    format nobody anticipated therefore still has a chance of being handled.
    """
    stages: list[Stage] = list(STAGES)
    seen = {stage.shell for stage in stages}
    text = "\n".join(source for source, _ in examples)

    def add(stage: Stage) -> None:
        if stage.shell not in seen:
            seen.add(stage.shell)
            stages.append(stage)

    for literal, argument in _SEPARATORS:
        if literal not in text:
            continue
        for column in (2, 3):
            if literal == "\t":
                add(Stage(f"awk -F'{argument}' '{{print ${column}}}'", LINES, LINES, _cut_on("\t", column)))
            else:
                add(Stage(f"cut -d'{literal}' -f{column}", LINES, LINES, _cut_on(literal, column)))
    if any(len(line.split()) > 1 for line in text.splitlines()):
        for column in (2, 3):
            add(Stage(f"awk '{{print ${column}}}'", LINES, LINES, _field(column)))
    counts = {len(as_lines(expected)) for _, expected in examples}
    for k in sorted(count for count in counts if 2 <= count <= 40):
        add(Stage(f"head -n {k}", LINES, LINES, _head(k)))
        add(Stage(f"tail -n {k}", LINES, LINES, _tail(k)))
    return tuple(stages)



# --------------------------------------------------------------------------- #
# search                                                                       #
# --------------------------------------------------------------------------- #


def _line_set(text: str) -> set[str]:
    return set(as_lines(text))


def progress_score(actual: str, expected: str) -> float:
    """How far a partial pipeline has moved towards the target.

    Dropping a header line is a common first step that *lowers* naive similarity
    (the header text disappears from the output), so the score also considers
    the candidate with its first line removed.  Without this, beam search prunes
    the very branch that solves table-shaped data.
    """
    target = _line_set(expected)
    if not target:
        return 0.0
    whole = _line_set(actual)
    trimmed = set(as_lines(actual)[1:])
    whole_score = len(whole & target) / len(whole | target)
    trimmed_score = len(trimmed & target) / len(trimmed | target) if trimmed else 0.0
    return max(whole_score, trimmed_score)


def similarity(actual: str, expected: str) -> float:
    """Graded agreement used only to order hypotheses, never to accept one."""
    if actual == expected:
        return 1.0
    a_lines, e_lines = as_lines(actual), as_lines(expected)
    if len(e_lines) == 1 and re.fullmatch(r"-?\d+", e_lines[0].strip() or "x"):
        try:
            want = int(e_lines[0])
            got = int(a_lines[0]) if a_lines else -1
            return 1.0 / (1.0 + abs(want - got))
        except (ValueError, IndexError):
            return 0.0
    if not a_lines and not e_lines:
        return 1.0
    set_a, set_e = set(a_lines), set(e_lines)
    union = set_a | set_e
    jaccard = len(set_a & set_e) / len(union) if union else 1.0
    if len(actual) + len(expected) > 2000 or len(a_lines) > 40 or len(e_lines) > 40:
        # Long outputs are ordered by set agreement alone.  The character-level
        # ratio is a tie-breaker for short texts; on large ones it would cost
        # more than the whole search.
        return jaccard
    ratio = difflib.SequenceMatcher(None, actual, expected).ratio()
    return 0.6 * jaccard + 0.4 * ratio


@dataclass
class Synthesis:
    stages: tuple[str, ...] = ()
    command: str = ""
    seconds: float = 0.0
    candidates: int = 0
    verified: bool = False
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA + "_RESULT",
            "stages": list(self.stages),
            "command": self.command,
            "seconds": round(self.seconds, 4),
            "candidates": self.candidates,
            "verified": self.verified,
            "reason": self.reason,
        }


def search(
    examples: Sequence[tuple[str, str]],
    *,
    max_length: int = 3,
    beam: int = 160,
    time_budget_s: float = 2.0,
    stages: Sequence[Stage] | None = None,
) -> tuple[list[tuple[str, ...]], dict[str, Any]]:
    """Return candidate pipelines ordered by plausibility, plus search stats.

    ``examples`` are (input text, expected stdout).  Candidates are *not*
    trusted: the caller must execute them on the real computer.
    """
    if not examples:
        return [], {"candidates": 0, "reason": "NO_EXAMPLES"}
    started = time.perf_counter()
    vocabulary = tuple(stages) if stages is not None else instantiate(examples)
    expected = [text for _, text in examples]
    count_target: int | None = None
    if all(re.fullmatch(r"-?\d+\n?", text.strip() + "\n") for text in expected):
        try:
            values = [int(text.strip()) for text in expected]
            count_target = values[0] if len(set(values)) == 1 else None
        except ValueError:
            count_target = None

    def line_count_hint(text: str) -> float:
        """A count is the length of something: a line stream of exactly N lines
        is one step away from the answer, and would otherwise be pruned because
        it does not resemble the integer at all."""
        if count_target is None:
            return 0.0
        lines = len(as_lines(text))
        return max(0.0, 1.0 - abs(lines - count_target) / max(count_target, 1))
    frontier: list[tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = [
        (tuple(), tuple(TEXT for _ in examples), tuple(text for text, _ in examples))
    ]
    ordered: list[tuple[str, ...]] = []
    tried = 0
    for _length in range(1, max_length + 1):
        level: list[tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], int, float]] = []
        signatures: set[tuple[str, ...]] = set()
        exact_here: list[tuple[tuple[str, ...], tuple[str, ...]]] = []
        for stages, types, texts in frontier:
            for stage in vocabulary:
                if not all(stage.accepts(kind) for kind in types):
                    continue
                produced: list[str] = []
                produced_types: list[str] = []
                failed = False
                for value, kind in zip(texts, types):
                    if not stage.accepts(kind):
                        produced.append(value)
                        produced_types.append(kind)
                        continue
                    try:
                        value = stage.apply(value)
                    except (ValueError, TypeError, ZeroDivisionError):
                        failed = True
                        break
                    produced.append(value)
                    produced_types.append(stage.output_type)
                if failed:
                    continue
                tried += 1
                new_stages = stages + (stage.shell,)
                exact = sum(1 for got, want in zip(produced, expected) if got == want)
                if exact == len(expected):
                    # Exact hypotheses are terminal: they are never expanded.
                    # They are not deduplicated against each other, because two
                    # mechanisms can agree on the interpreter and disagree in
                    # the real shell; the shell decides.
                    exact_here.append((new_stages, tuple(produced)))
                    continue
                # Expansion, by contrast, is deduplicated by behaviour: siblings
                # that produce identical text lead to identical descendants.
                signature = tuple(produced)
                if signature in signatures:
                    continue
                signatures.add(signature)
                score = sum(progress_score(got, want) for got, want in zip(produced, expected)) / len(expected)
                if count_target is not None:
                    score = max(score, sum(line_count_hint(got) for got in produced) / len(produced))
                level.append(
                    (new_stages, signature, tuple(produced_types), tuple(produced), exact, score)
                )
        level.sort(key=lambda item: (-item[4], -item[5], len(item[0])))
        if exact_here:
            # Among equally exact pipelines, prefer ones whose stages actually
            # did something.  A "sort -n" that happens to be stable on the
            # examples is a no-op hypothesis; it must not outrank the stage
            # that really transforms the text.
            def changed(item: tuple[tuple[str, ...], tuple[str, ...]]) -> int:
                stages, produced = item
                count = 0
                for stage_name in stages:
                    stage = _BY_SHELL.get(stage_name) or next(
                        candidate for candidate in vocabulary if candidate.shell == stage_name
                    )
                    if any(
                        stage.apply(before) != before
                        for before in (text for text, _ in examples)
                    ):
                        count += 1
                return count

            def positional(item: tuple[tuple[str, ...], tuple[str, ...]]) -> int:
                # Fixed index stages explain one observation and nothing else;
                # when an equally exact pipeline avoids them, prefer that one.
                return sum(
                    1
                    for name in item[0]
                    if name in ("sed -n '3p'", "head -n 3", "tail -n 3")
                )

            def sanitizes_first(item: tuple[tuple[str, ...], tuple[str, ...]]) -> int:
                # A header row is not data.  When a pipeline drops it, doing so
                # before reading fields is the explanation that keeps working
                # when a value happens to sort next to the header text.
                stages = item[0]
                return stages.index("tail -n +2") if "tail -n +2" in stages else len(stages)

            exact_here.sort(
                key=lambda item: (
                    -changed(item),
                    positional(item),
                    sanitizes_first(item),
                    len(item[0]),
                    item[0],
                )
            )
            ordered.extend(stages for stages, _ in exact_here)
            break
        if not level:
            break
        # Keep breadth in every output type, so a COUNT-shaped branch is not
        # crowded out by the many LINES-shaped ones.
        selected: list[tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = []
        per_type: dict[str, int] = {}
        for stages, _sig, types, produced, _exact, _score in level:
            signature = types
            if per_type.get(str(signature), 0) >= max(8, beam // 4):
                continue
            per_type[str(signature)] = per_type.get(str(signature), 0) + 1
            selected.append((stages, types, produced))
            if len(selected) >= beam:
                break
        frontier = selected
        if time.perf_counter() - started > time_budget_s:
            break
    stats = {"candidates": tried, "seconds": round(time.perf_counter() - started, 4)}
    return ordered[:16], stats


def command_for(stages: Sequence[str], input_slot: str = "path") -> str:
    return "cat {" + input_slot + "} | " + " | ".join(stages)


def verify(
    run: Callable[[str], Any],
    stages: Sequence[str],
    examples: Sequence[tuple[str, str]],
    *,
    input_slot_values: Sequence[str] | None = None,
) -> tuple[bool, str, list[dict[str, Any]]]:
    """Execute a candidate on the real surface and require exact bytes.

    ``run`` receives a shell command and returns an object with ``ok`` and
    ``stdout``.  Every example must match exactly; the first mismatch is
    reported so the caller can learn from it.
    """
    template = command_for(stages)
    failures: list[dict[str, Any]] = []
    for index, (_, expected) in enumerate(examples):
        binding = (input_slot_values or [])[index] if input_slot_values else str(index)
        command = template.replace("{path}", binding)
        result = run(command)
        if not getattr(result, "ok", False):
            failures.append({"example": index, "reason": "COMMAND_FAILED", "stderr": getattr(result, "stderr", "")[:400]})
            return False, command, failures
        if result.stdout != expected:
            failures.append(
                {
                    "example": index,
                    "reason": "OUTPUT_MISMATCH",
                    "expected": expected[:400],
                    "actual": result.stdout[:400],
                }
            )
            return False, command, failures
    return True, template, failures


__all__ = [
    "SCHEMA",
    "TEXT",
    "LINES",
    "COUNT",
    "STAGES",
    "Stage",
    "Synthesis",
    "instantiate",
    "search",
    "similarity",
    "command_for",
    "verify",
    "as_lines",
    "as_text",
]
