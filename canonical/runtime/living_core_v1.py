"""Living core V1: one-shot induction, active experiments, salient memory.

Why this module exists
----------------------
Project Brain owns many *fixed* capability kernels.  A fixed kernel is a
program: it does exactly what it was written to do and nothing else.  The
mission needs the opposite property: a system that meets a task it has never
seen, finds out what it must know, learns it from the smallest possible
evidence, verifies the learned mechanism, and keeps only what is worth keeping.

This module is the substrate for that property.  It has four parts:

1. ``Table`` / expression / program machinery: a small, exact data-transform
   language (CSV in, CSV out) with deterministic evaluation.
2. ``synthesize``: constructive, example-guided program synthesis over that
   language.  It is not a classifier over known task names; it searches the
   space of programs consistent with the evidence.
3. ``induce``: counterexample-guided active induction.  Given a queryable
   black box and one or two demonstrations, it chooses its own experiments,
   eliminates inconsistent hypotheses, and returns a program plus the exact
   probe/validation record.  This is "instant learning" in the operational
   sense: a reusable mechanism from one demonstration, verified on inputs the
   teacher never supplied.
4. ``Memory``: episodic memory with learned salience.  Retrieval weights are
   fit online from retrieval outcomes, so the creature learns *what is worth
   remembering* instead of being told.

Hard boundaries (honest, fail-closed):
- stdlib only; no network, no model, no learned weights outside this file;
- a synthesized program is valid only for the exact column/format contract it
  was verified against; anything else raises rather than guessing;
- nothing here grants capability, ownership or terminal credit.  A mechanism
  becomes credit only after independent held-out verification, elsewhere.
"""
from __future__ import annotations

import csv
import hashlib
import heapq
import io
import json
import math
import random
import re
import statistics
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_LIVING_CORE_V1"

# --------------------------------------------------------------------------- #
# exact cell formatting (part of the file-format contract, not of any task)    #
# --------------------------------------------------------------------------- #

_NUMERIC_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
_INT_RE = re.compile(r"^[+-]?\d+$")


class LivingCoreError(ValueError):
    """Fail-closed error.  Never silently guessed over."""


def fmt_value(value: Any) -> str:
    """Canonical rendering used for every comparison in this module.

    Integral reals render as integers; other reals render with at most six
    decimals and no trailing zeros.  The contract is deliberately simple so a
    black box and a learner can agree on bytes without sharing code.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise LivingCoreError("NONFINITE_CELL")
        if abs(value - round(value)) <= 1e-9:
            return str(int(round(value)))
        text = f"{value:.6f}".rstrip("0").rstrip(".")
        if text in ("", "-0"):
            text = "0"
        return text
    return str(value)


@lru_cache(maxsize=1 << 16)
def _parse_number_text(raw: str) -> float:
    """Parsing a cell is pure, and induction re-reads the same cells millions of
    times while enumerating hypotheses; caching turns that into a dict lookup."""
    if not raw:
        raise LivingCoreError("EMPTY_NOT_NUMERIC")
    cleaned = raw.replace(",", "").replace("$", "").rstrip("%").strip()
    cleaned = cleaned.replace("€", "").replace("£", "")
    if not _NUMERIC_RE.match(cleaned):
        raise LivingCoreError("NOT_NUMERIC:" + raw)
    return float(cleaned)


def parse_number(text: Any) -> float:
    if isinstance(text, bool):
        raise LivingCoreError("BOOLEAN_NOT_NUMERIC")
    if isinstance(text, (int, float)):
        value = float(text)
        if not math.isfinite(value):
            raise LivingCoreError("NONFINITE_NUMBER")
        return value
    return _parse_number_text(str(text).strip())


def _is_number(text: Any) -> bool:
    try:
        parse_number(text)
        return True
    except LivingCoreError:
        return False


# --------------------------------------------------------------------------- #
# table I/O                                                                    #
# --------------------------------------------------------------------------- #


@dataclass
class Table:
    columns: list[str]
    rows: list[dict[str, str]]

    def copy(self) -> "Table":
        return Table(list(self.columns), [dict(r) for r in self.rows])

    def signature(self) -> tuple[str, ...]:
        return tuple(self.columns)

    def key(self) -> str:
        body = json.dumps(
            {"columns": self.columns, "rows": self.rows},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
        return hashlib.sha256(body).hexdigest()

    def to_csv(self, delimiter: str = ",") -> str:
        out = io.StringIO(newline="")
        writer = csv.writer(
            out, delimiter=delimiter, lineterminator="\n", quoting=csv.QUOTE_MINIMAL
        )
        writer.writerow(self.columns)
        for row in self.rows:
            writer.writerow([row.get(c, "") for c in self.columns])
        return out.getvalue()


def table_from_csv(text: str, delimiter: str = ",") -> Table:
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        header = next(reader)
    except StopIteration as exc:
        raise LivingCoreError("CSV_EMPTY") from exc
    header = [h.strip() for h in header]
    if not header or any(not h for h in header):
        raise LivingCoreError("CSV_HEADER_INVALID")
    if len(set(header)) != len(header):
        raise LivingCoreError("CSV_HEADER_DUPLICATE")
    rows: list[dict[str, str]] = []
    for index, raw in enumerate(reader, start=2):
        if not raw:
            continue
        if len(raw) != len(header):
            raise LivingCoreError(f"CSV_ROW_WIDTH:{index}")
        rows.append({name: value for name, value in zip(header, raw)})
    return Table(header, rows)


def table_from_rows(columns: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> Table:
    cols = [str(c) for c in columns]
    materialized = [
        {c: fmt_value(row.get(c, "")) if not isinstance(row.get(c), str) else str(row.get(c, "")) for c in cols}
        for row in rows
    ]
    return Table(cols, materialized)


# --------------------------------------------------------------------------- #
# expressions                                                                  #
# --------------------------------------------------------------------------- #
# Representation: ("col", name) | ("lit", value) | (op, (args...), ((k, v),...))
# Everything is hashable, serializable and evaluated by one function.

Expr = tuple


def col(name: str) -> Expr:
    return ("col", str(name))


def lit(value: Any) -> Expr:
    return ("lit", value)


def call(op: str, args: Sequence[Expr], **params: Any) -> Expr:
    return (str(op), tuple(args), tuple(sorted(params.items())))


def _p(expr: Expr) -> dict[str, Any]:
    return dict(expr[2]) if len(expr) > 2 else {}


def expr_to_json(expr: Expr) -> Any:
    if expr[0] in ("col", "lit"):
        return {"op": expr[0], "value": expr[1]}
    return {
        "op": expr[0],
        "args": [expr_to_json(a) for a in expr[1]],
        "params": dict(expr[2]),
    }


def expr_from_json(node: Any) -> Expr:
    if not isinstance(node, Mapping):
        raise LivingCoreError("EXPR_JSON_INVALID")
    op = str(node.get("op"))
    if op in ("col", "lit"):
        return (op, node.get("value"))
    return (op, tuple(expr_from_json(a) for a in node.get("args", [])), tuple(sorted(dict(node.get("params", {})).items())))


def _date_parts(value: Any) -> tuple[int, int, int]:
    text = str(value).strip()
    match = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})", text)
    if not match:
        raise LivingCoreError("DATE_UNPARSEABLE:" + text)
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def _compile_expr(expr: Expr) -> Callable[[Mapping[str, str]], Any]:
    """Turn an expression tree into a closure.

    The learner evaluates the same expression millions of times while it
    enumerates hypotheses, so the tree walk is paid once at compile time rather
    than once per row.  Semantics are identical to ``eval_expr_interpreted``.
    """
    op = expr[0]
    if op == "col":
        name = expr[1]

        def column(row: Mapping[str, str]) -> Any:
            return row.get(name, "")

        return column
    if op == "lit":
        value = expr[1]

        def literal(row: Mapping[str, str]) -> Any:
            return value

        return literal
    args = [_compile_expr(a) for a in expr[1]]
    params = dict(expr[2]) if len(expr) > 2 else {}
    if op == "add":
        return lambda row: parse_number(args[0](row)) + parse_number(args[1](row))
    if op == "sub":
        return lambda row: parse_number(args[0](row)) - parse_number(args[1](row))
    if op == "mul":
        return lambda row: parse_number(args[0](row)) * parse_number(args[1](row))
    if op == "div":

        def divide(row: Mapping[str, str]) -> Any:
            denominator = parse_number(args[1](row))
            if denominator == 0:
                raise LivingCoreError("DIVISION_BY_ZERO")
            return parse_number(args[0](row)) / denominator

        return divide
    if op == "mod":

        def modulo(row: Mapping[str, str]) -> Any:
            denominator = parse_number(args[1](row))
            if denominator == 0:
                raise LivingCoreError("MODULO_BY_ZERO")
            return math.fmod(parse_number(args[0](row)), denominator)

        return modulo
    if op == "min":
        return lambda row: min(parse_number(args[0](row)), parse_number(args[1](row)))
    if op == "max":
        return lambda row: max(parse_number(args[0](row)), parse_number(args[1](row)))
    if op == "neg":
        return lambda row: -parse_number(args[0](row))
    if op == "abs":
        return lambda row: abs(parse_number(args[0](row)))
    if op == "round":
        places = int(params["k"])
        return lambda row: round(parse_number(args[0](row)), places)
    if op == "lower":
        return lambda row: str(args[0](row)).lower()
    if op == "upper":
        return lambda row: str(args[0](row)).upper()
    if op == "title":
        return lambda row: str(args[0](row)).title()
    if op == "strip":
        return lambda row: str(args[0](row)).strip()
    if op == "len":
        return lambda row: len(str(args[0](row)))
    if op == "number":

        def number(row: Mapping[str, str]) -> Any:
            found = re.search(r"[+-]?\d+(?:\.\d+)?", str(args[0](row)).replace(",", ""))
            if not found:
                raise LivingCoreError("NO_NUMBER_IN_CELL")
            return float(found.group(0))

        return number
    if op == "year":
        return lambda row: _date_parts(args[0](row))[0]
    if op == "month":
        return lambda row: _date_parts(args[0](row))[1]
    if op == "day":
        return lambda row: _date_parts(args[0](row))[2]
    if op == "split":
        separator = str(params["sep"])
        index = int(params["idx"])

        def split_at(row: Mapping[str, str]) -> Any:
            parts = str(args[0](row)).split(separator)
            if index >= len(parts) or index < -len(parts):
                raise LivingCoreError("SPLIT_INDEX_OUT_OF_RANGE")
            return parts[index]

        return split_at
    if op == "before":
        separator = str(params["sep"])

        def before(row: Mapping[str, str]) -> Any:
            text = str(args[0](row))
            if separator not in text:
                raise LivingCoreError("SEPARATOR_ABSENT")
            return text.split(separator)[0]

        return before
    if op == "after":
        separator = str(params["sep"])

        def after(row: Mapping[str, str]) -> Any:
            text = str(args[0](row))
            if separator not in text:
                raise LivingCoreError("SEPARATOR_ABSENT")
            return text.split(separator, 1)[1]

        return after
    if op == "strip_prefix":
        prefix = str(params["s"])

        def strip_prefix(row: Mapping[str, str]) -> Any:
            text = str(args[0](row))
            if not text.startswith(prefix):
                raise LivingCoreError("PREFIX_ABSENT")
            return text[len(prefix):]

        return strip_prefix
    if op == "strip_suffix":
        suffix = str(params["s"])

        def strip_suffix(row: Mapping[str, str]) -> Any:
            text = str(args[0](row))
            if not text.endswith(suffix):
                raise LivingCoreError("SUFFIX_ABSENT")
            return text[: len(text) - len(suffix)] if suffix else text

        return strip_suffix
    if op == "slice":
        start = int(params["start"])
        end = int(params["end"])
        return lambda row: str(args[0](row))[start:end]
    if op == "concat":
        separator = str(params["sep"])
        return lambda row: str(args[0](row)) + separator + str(args[1](row))
    raise LivingCoreError("EXPR_OP_UNKNOWN:" + op)


_COMPILED_EXPRS: dict[Expr, Callable[[Mapping[str, str]], Any]] = {}


def compile_expr(expr: Expr) -> Callable[[Mapping[str, str]], Any]:
    """Compile with a bounded memo, so repeated trees cost one dict lookup."""
    try:
        return _COMPILED_EXPRS[expr]
    except (KeyError, TypeError):
        pass
    compiled = _compile_expr(expr)
    try:
        if len(_COMPILED_EXPRS) < 16384:
            _COMPILED_EXPRS[expr] = compiled
    except TypeError:
        pass
    return compiled


def eval_expr(expr: Expr, row: Mapping[str, str]) -> Any:
    return compile_expr(expr)(row)


def eval_expr_interpreted(expr: Expr, row: Mapping[str, str]) -> Any:
    """Reference evaluator: a direct tree walk, kept as the definition of
    what an expression means.  ``eval_expr`` compiles to closures for speed
    and a differential test pins the two together."""
    op = expr[0]
    if op == "col":
        return row.get(expr[1], "")
    if op == "lit":
        return expr[1]
    args = [eval_expr(a, row) for a in expr[1]]
    params = _p(expr)
    if op == "add":
        return parse_number(args[0]) + parse_number(args[1])
    if op == "sub":
        return parse_number(args[0]) - parse_number(args[1])
    if op == "mul":
        return parse_number(args[0]) * parse_number(args[1])
    if op == "div":
        denominator = parse_number(args[1])
        if denominator == 0:
            raise LivingCoreError("DIVISION_BY_ZERO")
        return parse_number(args[0]) / denominator
    if op == "mod":
        denominator = parse_number(args[1])
        if denominator == 0:
            raise LivingCoreError("MODULO_BY_ZERO")
        return math.fmod(parse_number(args[0]), denominator)
    if op == "min":
        return min(parse_number(args[0]), parse_number(args[1]))
    if op == "max":
        return max(parse_number(args[0]), parse_number(args[1]))
    if op == "neg":
        return -parse_number(args[0])
    if op == "abs":
        return abs(parse_number(args[0]))
    if op == "round":
        return round(parse_number(args[0]), int(params["k"]))
    if op == "lower":
        return str(args[0]).lower()
    if op == "upper":
        return str(args[0]).upper()
    if op == "title":
        return str(args[0]).title()
    if op == "strip":
        return str(args[0]).strip()
    if op == "len":
        return len(str(args[0]))
    if op == "number":
        found = re.search(r"[+-]?\d+(?:\.\d+)?", str(args[0]).replace(",", ""))
        if not found:
            raise LivingCoreError("NO_NUMBER_IN_CELL")
        return float(found.group(0))
    if op == "year":
        return _date_parts(args[0])[0]
    if op == "month":
        return _date_parts(args[0])[1]
    if op == "day":
        return _date_parts(args[0])[2]
    if op == "split":
        parts = str(args[0]).split(str(params["sep"]))
        index = int(params["idx"])
        if index >= len(parts) or index < -len(parts):
            raise LivingCoreError("SPLIT_INDEX_OUT_OF_RANGE")
        return parts[index]
    if op == "before":
        text = str(args[0])
        sep = str(params["sep"])
        if sep not in text:
            raise LivingCoreError("SEPARATOR_ABSENT")
        return text.split(sep)[0]
    if op == "after":
        text = str(args[0])
        sep = str(params["sep"])
        if sep not in text:
            raise LivingCoreError("SEPARATOR_ABSENT")
        return text.split(sep, 1)[1]
    if op == "strip_prefix":
        prefix = str(params["s"])
        text = str(args[0])
        if not text.startswith(prefix):
            raise LivingCoreError("PREFIX_ABSENT")
        return text[len(prefix):]
    if op == "strip_suffix":
        suffix = str(params["s"])
        text = str(args[0])
        if not text.endswith(suffix):
            raise LivingCoreError("SUFFIX_ABSENT")
        return text[: len(text) - len(suffix)] if suffix else text
    if op == "slice":
        start = int(params["start"])
        end = int(params["end"])
        return str(args[0])[start:end]
    if op == "concat":
        return str(args[0]) + str(params["sep"]) + str(args[1])
    raise LivingCoreError("EXPR_OP_UNKNOWN:" + op)


def expr_text(expr: Expr) -> str:
    """Compact human-readable form used in skill descriptions."""
    op = expr[0]
    if op == "col":
        return str(expr[1])
    if op == "lit":
        return fmt_value(expr[1])
    params = _p(expr)
    args = ", ".join(expr_text(a) for a in expr[1])
    if params:
        return f"{op}({args}; {', '.join(f'{k}={v}' for k, v in params.items())})"
    return f"{op}({args})"


def eval_formatted(expr: Expr, row: Mapping[str, str]) -> str:
    return fmt_value(eval_expr(expr, row))


# --------------------------------------------------------------------------- #
# programs                                                                     #
# --------------------------------------------------------------------------- #


def program_to_json(program: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for step in program:
        item: dict[str, Any] = {"op": step["op"]}
        for key, value in step.items():
            if key == "op":
                continue
            if key in ("expr", "left", "right"):
                item[key] = expr_to_json(value)
            elif key == "exprs":
                item[key] = [expr_to_json(v) for v in value]
            elif key == "aggs":
                item[key] = [
                    {**a, "expr": expr_to_json(a["expr"])} for a in value
                ]
            else:
                item[key] = value
        out.append(item)
    return out


def program_from_json(program: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for step in program:
        item: dict[str, Any] = {"op": step["op"]}
        for key, value in step.items():
            if key == "op":
                continue
            if key in ("expr", "left", "right"):
                item[key] = expr_from_json(value)
            elif key == "exprs":
                item[key] = [expr_from_json(v) for v in value]
            elif key == "aggs":
                item[key] = [{**a, "expr": expr_from_json(a["expr"])} for a in value]
            else:
                item[key] = value
        out.append(item)
    return out


def _sort_key(value: Any) -> tuple[int, Any]:
    text = str(value)
    try:
        return (0, parse_number(text))
    except LivingCoreError:
        return (1, text)


def _cmp(expr: Expr, cmp: str, value: Any, row: Mapping[str, str]) -> bool:
    left = eval_expr(expr, row)
    if cmp == "in":
        return fmt_value(left) in {fmt_value(v) for v in value}
    if cmp == "notin":
        return fmt_value(left) not in {fmt_value(v) for v in value}
    if cmp in ("contains", "startswith", "endswith"):
        text = str(left)
        probe = str(value)
        if cmp == "contains":
            return probe in text
        if cmp == "startswith":
            return text.startswith(probe)
        return text.endswith(probe)
    if cmp == "nonempty":
        return str(left).strip() != ""
    if cmp == "empty":
        return str(left).strip() == ""
    if cmp == "regex":
        return re.search(str(value), str(left)) is not None
    try:
        a = parse_number(left)
        b = parse_number(value)
    except LivingCoreError:
        if cmp in ("eq", "ne"):
            same = fmt_value(left) == fmt_value(value)
            return same if cmp == "eq" else not same
        return False
    if cmp == "eq":
        return a == b
    if cmp == "ne":
        return a != b
    if cmp == "gt":
        return a > b
    if cmp == "ge":
        return a >= b
    if cmp == "lt":
        return a < b
    if cmp == "le":
        return a <= b
    raise LivingCoreError("FILTER_CMP_UNKNOWN:" + cmp)


def apply_program(program: Sequence[Mapping[str, Any]], table: Table) -> Table:
    columns = list(table.columns)
    rows = [dict(r) for r in table.rows]
    for step_index, step in enumerate(program):
        op = step["op"]
        if op == "filter":
            rows = [r for r in rows if _cmp(step["expr"], step["cmp"], step["value"], r)]
        elif op == "project":
            items = step["items"]
            new_columns = [item["name"] for item in items]
            compiled = [(item["name"], compile_expr(item["expr"])) for item in items]
            projected = []
            for r in rows:
                projected.append({name: fmt_value(fn(r)) for name, fn in compiled})
            columns, rows = new_columns, projected
        elif op == "group":
            keys = step["keys"]
            aggs = step["aggs"]
            buckets: dict[tuple[str, ...], list[dict[str, str]]] = {}
            order: list[tuple[str, ...]] = []
            key_fns = [compile_expr(k["expr"]) for k in keys]
            for r in rows:
                key = tuple(fmt_value(fn(r)) for fn in key_fns)
                if key not in buckets:
                    buckets[key] = []
                    order.append(key)
                buckets[key].append(r)
            if not keys:
                if not order:
                    order.append(tuple())
                    buckets[tuple()] = []
            new_columns = [k["name"] for k in keys] + [a["name"] for a in aggs]
            agg_fns = [compile_expr(a["expr"]) for a in aggs]
            grouped = []
            for key in order:
                bucket = buckets[key]
                record: dict[str, str] = {}
                for spec, part in zip(keys, key):
                    record[spec["name"]] = part
                for agg, agg_fn in zip(aggs, agg_fns):
                    values = [agg_fn(r) for r in bucket]
                    record[agg["name"]] = fmt_value(_aggregate(agg["agg"], values, bucket, agg.get("k", 2)))
                grouped.append(record)
            columns, rows = new_columns, grouped
        elif op == "dedupe":
            keys = step.get("keys")
            seen = set()
            kept = []
            key_fns = [compile_expr(k) for k in keys] if keys else []
            for r in rows:
                if keys:
                    sig = tuple(fmt_value(fn(r)) for fn in key_fns)
                else:
                    sig = tuple(r.get(c, "") for c in columns)
                if sig in seen:
                    continue
                seen.add(sig)
                kept.append(r)
            rows = kept
        elif op == "sort":
            for spec in reversed(step["keys"]):
                spec_fn = compile_expr(spec["expr"])
                rows.sort(
                    key=lambda r, fn=spec_fn: _sort_key(fn(r)),
                    reverse=bool(spec.get("desc", False)),
                )
        elif op == "limit":
            rows = rows[: int(step["n"])]
        elif op == "error":
            raise LivingCoreError("PROGRAM_TERMINAL_ERROR_STEP")
        else:
            raise LivingCoreError(f"PROGRAM_OP_UNKNOWN:{op}@{step_index}")
    return Table(columns, rows)


def _aggregate(agg: str, values: Sequence[Any], bucket: Sequence[Mapping[str, str]], k: int = 2) -> Any:
    if agg == "count":
        return len(bucket)
    if agg == "count_distinct":
        return len({fmt_value(v) for v in values})
    if agg == "first":
        return values[0] if values else ""
    if agg == "last":
        return values[-1] if values else ""
    numbers = [parse_number(v) for v in values]
    if not numbers:
        raise LivingCoreError("AGGREGATE_EMPTY")
    if agg == "sum":
        return sum(numbers)
    if agg == "mean":
        return round(sum(numbers) / len(numbers), int(k))
    if agg == "min":
        return min(numbers)
    if agg == "max":
        return max(numbers)
    raise LivingCoreError("AGG_UNKNOWN:" + agg)


def apply_rows(program: Sequence[Mapping[str, Any]], columns: Sequence[str], rows: Sequence[Mapping[str, str]]) -> Table:
    return apply_program(program, Table(list(columns), [dict(r) for r in rows]))


# --------------------------------------------------------------------------- #
# expression inference                                                         #
# --------------------------------------------------------------------------- #

_SEP_POOL = (",", "-", "/", " ", "@", ":", "|", "_", ".", ";", "#", "=", "(", ")")
# Background knowledge: human-authored thresholds are usually round numbers.
# These are priors, never assumptions: every candidate is still checked against
# all evidence and all validation probes.
_ROUND_NUMBERS = (0.0, 1.0, 2.0, 3.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0,
                  50.0, 60.0, 70.0, 75.0, 80.0, 90.0, 100.0, 250.0, 500.0, 1000.0)


def _round_numbers(low: float, high: float) -> list[float]:
    """Round thresholds at every relevant magnitude, not just small ones.

    People choose 20000 bytes, not 19909.  A threshold learner without this
    prior overfits the demonstration gap and fails at the first unseen value.
    """
    numbers = [n for n in _ROUND_NUMBERS if low - 1 <= n <= high + 1]
    power = 1.0
    for _ in range(10):
        for multiplier in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.5):
            value = multiplier * power
            if low - 1 <= value <= high + 1:
                numbers.append(value)
        power *= 10.0
    return sorted(set(numbers))


def _midpoints(numbers: Sequence[float], limit: int = 200) -> list[float]:
    out = []
    for left, right in zip(numbers, numbers[1:]):
        out.append((left + right) / 2.0)
        if len(out) >= limit:
            break
    return out


def _sample(rows: Sequence[Mapping[str, str]], limit: int = 24) -> list[Mapping[str, str]]:
    if len(rows) <= limit:
        return list(rows)
    step = len(rows) / float(limit)
    return [rows[min(len(rows) - 1, int(i * step))] for i in range(limit)]


def _expr_values(expr: Expr, rows: Sequence[Mapping[str, str]]) -> tuple[str, ...] | None:
    out = []
    for row in rows:
        try:
            out.append(fmt_value(eval_expr(expr, row)))
        except (LivingCoreError, ValueError, TypeError, OverflowError, ZeroDivisionError):
            return None
    return tuple(out)


def _target_hit(expr: Expr, rows: Sequence[Mapping[str, str]], targets: Sequence[str]) -> bool:
    if len(rows) != len(targets):
        return False
    for row, target in zip(rows, targets):
        try:
            if fmt_value(eval_expr(expr, row)) != target:
                return False
        except (LivingCoreError, ValueError, TypeError, OverflowError, ZeroDivisionError):
            return False
    return True


def _seps_for(values: Sequence[str]) -> list[str]:
    found = set()
    for value in values[:64]:
        for char in value:
            if char in _SEP_POOL:
                found.add(char)
    return sorted(found)


def infer_expressions(
    rows: Sequence[Mapping[str, str]],
    targets: Sequence[str],
    columns: Sequence[str],
    *,
    limit: int = 6,
    unordered: bool = False,
    subset: bool = False,
) -> list[Expr]:
    """Return expressions that reproduce every (row -> target) pair exactly.

    The search is constructive.  Each candidate family is instantiated from
    the observed values (not from task names) and then filtered by exact
    behavioural equality.  It is fast because failing candidates usually die
    on the first few rows.
    """
    if len(rows) != len(targets) and not subset:
        raise LivingCoreError("TARGET_LENGTH_MISMATCH")
    if not rows:
        return []
    def spread(sequence, count=24):
        if len(sequence) <= count:
            return list(sequence)
        indices = sorted({int(i * (len(sequence) - 1) / (count - 1)) for i in range(count)})
        return [sequence[i] for i in indices]

    if subset:
        # A subset has fewer targets than rows; containment is checked on the
        # complete evidence (no sampling), otherwise counts are not comparable.
        sample_rows = list(rows)
        sample_targets = list(targets)
    elif unordered:
        # Unordered comparison still requires aligned (row, target) pairs.
        if len(rows) <= 24:
            pairs_sample = list(zip(rows, targets))
        else:
            indices = sorted({int(i * (len(rows) - 1) / 23) for i in range(24)})
            pairs_sample = [(rows[i], targets[i]) for i in indices]
        sample_rows = [r for r, _ in pairs_sample]
        sample_targets = [t for _, t in pairs_sample]
    else:
        # Deterministic, aligned sample of (row, target) pairs.
        if len(rows) <= 24:
            pairs_sample = list(zip(rows, targets))
        else:
            indices = sorted({int(i * (len(rows) - 1) / 23) for i in range(24)})
            pairs_sample = [(rows[i], targets[i]) for i in indices]
        sample_rows = [r for r, _ in pairs_sample]
        sample_targets = [t for _, t in pairs_sample]

    from collections import Counter as _Counter

    matches: list[Expr] = []
    seen_full: set[tuple[str, ...]] = set()
    target_sample_sorted = tuple(sorted(sample_targets)) if unordered else None
    target_sample_counts = _Counter(sample_targets) if subset else None
    target_counts = _Counter(targets)

    def consider(expr: Expr) -> None:
        values = _expr_values(expr, sample_rows)
        if values is None:
            return
        if subset:
            counts = _Counter(values)
            if any(counts[k] < n for k, n in target_sample_counts.items()):
                return
        elif unordered:
            if tuple(sorted(values)) != target_sample_sorted:
                return
        elif not all(v == t for v, t in zip(values, sample_targets)):
            return
        # De-duplicate on full behaviour, never on the sample: two expressions
        # can agree on a sample and diverge on the rows it did not include.
        all_values = _expr_values(expr, rows)
        if all_values is None:
            return
        if subset:
            counts = _Counter(all_values)
            if any(counts[k] < n for k, n in target_counts.items()):
                return
            key = tuple(sorted(all_values))
        elif unordered:
            if sorted(all_values) != sorted(targets):
                return
            key = tuple(sorted(all_values))
        else:
            if not all(v == t for v, t in zip(all_values, targets)):
                return
            key = all_values
        if key in seen_full:
            return
        seen_full.add(key)
        matches.append(expr)

    atoms = [col(c) for c in columns]

    # 1. atoms and unary transforms
    for atom in atoms:
        consider(atom)
    unary_ops: list[Expr] = []
    for atom in atoms:
        for op in ("lower", "upper", "strip", "title", "len", "abs", "number", "year", "month", "day"):
            unary_ops.append(call(op, [atom]))
        for k in (0, 1, 2, 3):
            unary_ops.append(call("round", [atom], k=k))
    for expr in unary_ops:
        consider(expr)

    # 2. string decomposition with parameters instantiated from the data
    text_values = [str(row.get(c, "")) for c in columns for row in sample_rows]
    seps = _seps_for(text_values) or list(_SEP_POOL[:6])
    for atom in atoms:
        for sep in seps:
            for idx in (-2, -1, 0, 1, 2):
                consider(call("split", [atom], sep=sep, idx=idx))
            consider(call("before", [atom], sep=sep))
            consider(call("after", [atom], sep=sep))
    for atom in atoms:
        first = str(sample_rows[0].get(atom[1], ""))

        for start in range(0, min(len(first), 12) + 1):
            for end in range(start, min(len(first), 16) + 1):
                if first[start:end] == sample_targets[0]:
                    consider(call("slice", [atom], start=start, end=end))
        for index in range(0, min(len(first), 12)):
            if first[:index] == sample_targets[0]:
                consider(call("strip_prefix", [atom], s=first[:index]))
            if first[index:] == sample_targets[0]:
                consider(call("strip_suffix", [atom], s=first[index:]))
        # suffix/prefix removal learned from the first pair
        if first.startswith(str(sample_targets[0])):
            consider(call("strip_suffix", [atom], s=first[len(sample_targets[0]):]))
        if first.endswith(str(sample_targets[0])):
            consider(call("strip_prefix", [atom], s=first[: len(first) - len(sample_targets[0])]))

    # 3. concatenation of two columns with a learned separator
    for i, left in enumerate(atoms):
        for right in atoms[i + 1:]:
            consider(call("concat", [left, right], sep=""))
            consider(call("concat", [right, left], sep=""))
            for sep in seps:
                consider(call("concat", [left, right], sep=sep))
                consider(call("concat", [right, left], sep=sep))

    # A simple exact expression already answers the question; expensive
    # multi-term templates are only searched when the simple families fail.
    simple_found = bool(matches) and min(
        (1 if m[0] in ("col", "lit") else 1 + sum(1 for _ in m[1])) for m in matches
    ) <= 2

    # 4. numeric candidates: affine fits, products, ratios, templates
    numeric_targets: list[float] | None = None
    try:
        numeric_targets = [parse_number(t) for t in targets]
    except LivingCoreError:
        numeric_targets = None

    if numeric_targets is not None and not simple_found:
        def consider_numeric(expr: Expr) -> None:
            consider(expr)
            for k in (0, 1, 2):
                consider(call("round", [expr], k=k))

        # affine from two rows with distinct source values
        for atom in atoms:
            vals: list[tuple[float, float]] = []
            for row, target in zip(rows, numeric_targets):
                try:
                    vals.append((parse_number(eval_expr(atom, row)), target))
                except (LivingCoreError, ValueError):
                    vals = []
                    break
            if len(vals) < 2:
                continue
            for (x1, y1), (x2, y2) in zip(vals, vals[1:]):
                if abs(x2 - x1) <= 1e-12:
                    continue
                alpha = (y2 - y1) / (x2 - x1)
                beta = y1 - alpha * x1
                if not (math.isfinite(alpha) and math.isfinite(beta)):
                    continue
                if abs(alpha) < 1e9 and abs(beta) < 1e12:
                    expr = call("add", [call("mul", [atom, lit(alpha)]), lit(beta)])
                    consider_numeric(expr)
                    if abs(beta) <= 1e-12:
                        consider_numeric(call("mul", [atom, lit(alpha)]))
                break

        binary_ops = ("mul", "div", "add", "sub")
        for i, left in enumerate(atoms):
            for right in atoms[i + 1:]:
                for op in binary_ops:
                    consider_numeric(call(op, [left, right]))
                    consider_numeric(call(op, [right, left]))
                # products and ratios with a learned scale
                for op in ("mul", "div"):
                    for a, b in ((left, right), (right, left)):
                        for row, target in zip(rows, numeric_targets):
                            try:
                                base = parse_number(eval_expr(call(op, [a, b]), row))
                                if abs(base) <= 1e-12:
                                    break
                                scale = target / base
                            except (LivingCoreError, ValueError, ZeroDivisionError):
                                break
                        else:
                            if math.isfinite(scale) and abs(scale) < 1e9:
                                consider_numeric(call("mul", [call(op, [a, b]), lit(scale)]))
                            continue
                # three-term templates
        # Bounded three-term templates (background knowledge, not task names).
        small = atoms[:8]
        for a in small:
            for b in small:
                if a == b:
                    continue
                for c in small:
                    if c in (a, b):
                        continue
                    consider_numeric(call("mul", [call("mul", [a, b]), c]))
                    consider_numeric(call("mul", [call("add", [a, b]), c]))
                    consider_numeric(call("div", [call("sub", [a, b]), b]))
                    consider_numeric(
                        call("mul", [call("div", [call("sub", [a, b]), b]), lit(100.0)])
                    )
                    consider_numeric(
                        call("mul", [a, call("add", [lit(1.0), call("div", [c, lit(100.0)])])])
                    )

        # four-term tax / markup template
        small = atoms[:8]
        for a in small:
            for b in small:
                if a == b:
                    continue
                for c in small:
                    if c in (a, b):
                        continue
                    consider_numeric(
                        call("mul", [call("mul", [a, b]),
                                     call("add", [lit(1.0), call("div", [c, lit(100.0)])])])
                    )

    # 5. final full verification and stable ordering by expression size
    def size(expr: Expr) -> int:
        if expr[0] in ("col", "lit"):
            return 1
        return 1 + sum(size(a) for a in expr[1])

    unique: dict[Expr, None] = {}
    for expr in matches:
        unique[expr] = None
    ordered = sorted(unique, key=lambda e: (size(e), expr_text(e)))
    return ordered[:limit]


# --------------------------------------------------------------------------- #
# program synthesis                                                            #
# --------------------------------------------------------------------------- #


def _multiset(rows: Sequence[Mapping[str, str]], columns: Sequence[str]) -> tuple[tuple[str, ...], ...]:
    return tuple(sorted(tuple(str(r.get(c, "")) for c in columns) for r in rows))


def _program_signature(program: Sequence[Mapping[str, Any]]) -> str:
    return hashlib.sha256(
        json.dumps(program_to_json(program), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _project_from_exprs(items: Sequence[tuple[str, Expr]]) -> dict[str, Any]:
    return {"op": "project", "items": [{"name": name, "expr": expr} for name, expr in items]}


def _infer_filter(rows: Sequence[Mapping[str, str]], kept: Sequence[bool], columns: Sequence[str]) -> list[dict[str, Any]]:
    """Find predicates (up to a conjunction of two) that select exactly `kept`."""
    if not rows:
        return []
    if all(kept):
        return []
    if not any(kept):
        return [{"op": "filter", "expr": lit(""), "cmp": "empty", "value": True}]

    found: list[tuple[int, dict[str, Any]]] = []

    def evaluate(expr: Expr) -> list[str] | None:
        values = []
        for row in rows:
            try:
                values.append(fmt_value(eval_expr(expr, row)))
            except (LivingCoreError, ValueError, TypeError, OverflowError, ZeroDivisionError):
                return None
        return values

    def test(expr: Expr, values: Sequence[str], base_cost: int = 1) -> None:
        kept_values = {values[i] for i, k in enumerate(kept) if k}
        dropped_values = {values[i] for i, k in enumerate(kept) if not k}
        numeric_values = all(v.strip() == "" or _is_number(v) for v in values)
        if kept_values and dropped_values and kept_values.isdisjoint(dropped_values):
            # Numbers are ordered quantities: "keep everything except 70" is a
            # far less likely rule than "keep above a threshold".  Equality on
            # a numeric column is admitted only as a late, expensive guess.
            penalty = 3 if numeric_values else 0
            if len(kept_values) <= 6:
                add(expr, "in", sorted(kept_values), cost=base_cost + len(kept_values) + penalty)
            if len(dropped_values) <= 6:
                add(expr, "notin", sorted(dropped_values), cost=base_cost + len(dropped_values) + penalty)
            if len(kept_values) == 1:
                add(expr, "eq", next(iter(kept_values)), cost=base_cost + penalty)
            if len(dropped_values) == 1:
                add(expr, "ne", next(iter(dropped_values)), cost=base_cost + penalty)
        if all(v.strip() == "" or _is_number(v) for v in values):
            numeric = [(i, parse_number(v)) for i, v in enumerate(values) if v.strip() != ""]
            kept_nums = [v for i, v in numeric if kept[i]]
            drop_nums = [v for i, v in numeric if not kept[i]]
            if kept_nums and drop_nums:
                if min(kept_nums) > max(drop_nums):
                    # A round threshold is the more probable cause; the exact
                    # extreme of the observed gap is the fallback, not the prior.
                    add(expr, "gt", fmt_value(max(drop_nums)), cost=base_cost + 1)
                    add(expr, "ge", fmt_value(min(kept_nums)), cost=base_cost + 2)
                    for number in _round_numbers(max(drop_nums), min(kept_nums)):
                        if max(drop_nums) < number <= min(kept_nums):
                            add(expr, "ge", fmt_value(number), cost=base_cost)
                            if number > max(drop_nums):
                                add(expr, "gt", fmt_value(number), cost=base_cost)
                if max(kept_nums) < min(drop_nums):
                    add(expr, "lt", fmt_value(min(drop_nums)), cost=base_cost + 1)
                    add(expr, "le", fmt_value(max(kept_nums)), cost=base_cost + 2)
                    for number in _round_numbers(max(kept_nums), min(drop_nums)):
                        if max(kept_nums) < number <= min(drop_nums):
                            add(expr, "le", fmt_value(number), cost=base_cost)
                            if number < min(drop_nums):
                                add(expr, "lt", fmt_value(number), cost=base_cost)
            elif kept_nums and not drop_nums:
                add(expr, "nonempty", True, cost=base_cost)
            elif drop_nums and not kept_nums:
                add(expr, "empty", True, cost=base_cost)
        if kept_values and dropped_values:
            for pattern in _common_patterns(kept_values, dropped_values):
                add(expr, "contains", pattern, cost=base_cost + 1)

    def add(expr: Expr, cmp: str, value: Any, cost: int) -> None:
        mask = []
        for row in rows:
            try:
                mask.append(_cmp(expr, cmp, value, row))
            except (LivingCoreError, ValueError, TypeError):
                mask.append(False)
        if mask == list(kept):
            found.append((cost, {"op": "filter", "expr": expr, "cmp": cmp, "value": value}))

    numeric_columns = {
        c for c in columns if all(_is_number(r.get(c, "")) or str(r.get(c, "")) == "" for r in rows)
    }
    exprs: list[Expr] = [col(c) for c in columns]
    for c in columns:
        for op in ("lower", "upper", "strip", "year", "month", "day", "len"):
            if op in ("lower", "upper", "strip") and c in numeric_columns:
                continue
            exprs.append(call(op, [col(c)]))
        for k in (0, 2):
            exprs.append(call("round", [col(c)], k=k))
    for i, a in enumerate(columns):
        for b in columns[i + 1:]:
            for op in ("mul", "div", "add", "sub"):
                exprs.append(call(op, [col(a), col(b)]))
                exprs.append(call(op, [col(b), col(a)]))
            exprs.append(call("mul", [call("div", [call("sub", [col(b), col(a)]), col(a)]), lit(100.0)]))
            exprs.append(call("mul", [call("div", [call("sub", [col(a), col(b)]), col(b)]), lit(100.0)]))
            exprs.append(call("round", [call("div", [col(a), col(b)])], k=2))
            exprs.append(call("mul", [call("mul", [col(a), col(b)]), lit(0.01)]))
    # keep the pool bounded and deterministic
    seen_expr: set[Expr] = set()
    ordered: list[Expr] = []
    for expr in exprs:
        if expr in seen_expr:
            continue
        seen_expr.add(expr)
        ordered.append(expr)
        if len(ordered) >= 140:
            break
    for expr in ordered:
        values = evaluate(expr)
        if values is None:
            continue
        test(expr, values)

    if found:
        found.sort(key=lambda item: (item[0], len(json.dumps(item[1], default=str))))
        unique_filters: list[dict[str, Any]] = []
        signatures = set()
        for _, step in found:
            sig = json.dumps({**step, "expr": expr_to_json(step["expr"])}, sort_keys=True, default=str)
            if sig in signatures:
                continue
            signatures.add(sig)
            unique_filters.append(step)
            if len(unique_filters) >= 6:
                break
        return unique_filters

    # conjunction of two simple predicates
    simple: list[dict[str, Any]] = []
    for expr in ordered[:40]:
        values = evaluate(expr)
        if values is None:
            continue
        for value in sorted(set(values))[:16]:
            simple.append({"op": "filter", "expr": expr, "cmp": "eq", "value": value})
            simple.append({"op": "filter", "expr": expr, "cmp": "ne", "value": value})
            if _is_number(value):
                for cmp in ("gt", "lt", "ge", "le"):
                    simple.append({"op": "filter", "expr": expr, "cmp": cmp, "value": value})
    for i, first in enumerate(simple[:220]):
        for second in simple[i + 1: i + 24]:
            mask = []
            for row in rows:
                try:
                    mask.append(
                        _cmp(first["expr"], first["cmp"], first["value"], row)
                        and _cmp(second["expr"], second["cmp"], second["value"], row)
                    )
                except (LivingCoreError, ValueError, TypeError):
                    mask.append(False)
            if mask == list(kept):
                return [first, second]
    return []


def _predicate_mask(predicate: Mapping[str, Any], rows: Sequence[Mapping[str, str]]) -> list[bool]:
    mask = []
    for row in rows:
        try:
            mask.append(_cmp(predicate["expr"], predicate["cmp"], predicate["value"], row))
        except (LivingCoreError, ValueError, TypeError):
            mask.append(False)
    return mask


def _predicate_holds(predicate: Mapping[str, Any], row: Mapping[str, str]) -> bool:
    try:
        return bool(_cmp(predicate["expr"], predicate["cmp"], predicate["value"], row))
    except (LivingCoreError, ValueError, TypeError):
        return False


def induce_rule(
    rows: Sequence[Mapping[str, str]],
    kept: Sequence[bool],
    columns: Sequence[str] | None = None,
) -> list[dict[str, Any]] | None:
    """The simplest conjunction of predicates that selects exactly ``kept``.

    Returns a list of filter steps (one for a simple rule, two for a
    conjunction), or ``None`` when no rule within the vocabulary separates the
    examples.  ``None`` is an honest answer; the caller must not fall back to a
    guess.
    """
    if not rows:
        return None
    columns = list(columns or rows[0].keys())
    if all(kept):
        return []
    if not any(kept):
        return [{"op": "filter", "expr": lit(""), "cmp": "empty", "value": True}]
    found = _infer_filter(rows, kept, columns)
    if not found:
        return None
    target = list(kept)
    for candidate in found:
        if _predicate_mask(candidate, rows) == target:
            return [candidate]
    if len(found) >= 2:
        combined = [
            all(_predicate_holds(p, row) for p in found) for row in rows
        ]
        if combined == target:
            return list(found)
    return None


def expr_columns(expr: Any) -> set[str]:
    """Column names an expression reads.  Used to know which observations a
    rule actually depends on."""
    if isinstance(expr, tuple):
        if expr[0] == "col":
            return {str(expr[1])}
        out: set[str] = set()
        for argument in expr[1]:
            out |= expr_columns(argument)
        return out
    if isinstance(expr, Mapping):
        if expr.get("op") == "col":
            return {str(expr["value"])}
        out: set[str] = set()
        for argument in expr.get("args", ()):
            out |= expr_columns(argument)
        return out
    return set()


@dataclass
class DecisionList:
    """An ordered list of (predicate -> action) rules: a learned controller.

    First match wins.  Rules are ordered from most specific to least, and a
    rule with no predicate is the default.  On unseen states the first matching
    rule fires; when nothing matches, ``decide`` returns ``None`` and the caller
    must fail closed instead of guessing.
    """

    rules: list[dict[str, Any]]
    features: list[str] = field(default_factory=list)

    def firing_rule(self, row: Mapping[str, str]) -> dict[str, Any] | None:
        for rule in self.rules:
            predicates = rule.get("predicates") or []
            if all(_predicate_holds(p, row) for p in predicates):
                return rule
        return None

    def decide(self, row: Mapping[str, str]) -> str | None:
        rule = self.firing_rule(row)
        return str(rule["action"]) if rule is not None else None

    def supporting_features(self, policy_id: str = "") -> set[str]:
        names: set[str] = set()
        for rule in self.rules:
            for predicate in rule.get("predicates") or []:
                names |= expr_columns(predicate["expr"])
        return names

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA + "_DECISION_LIST",
            "features": list(self.features),
            "rules": [
                {
                    "action": rule["action"],
                    "predicates": [
                        {"expr": expr_to_json(p["expr"]), "cmp": p["cmp"], "value": p["value"]}
                        for p in rule.get("predicates") or []
                    ],
                }
                for rule in self.rules
            ],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DecisionList":
        if payload.get("schema") != SCHEMA + "_DECISION_LIST":
            raise LivingCoreError("DECISION_SCHEMA_MISMATCH")
        rules = []
        for rule in payload.get("rules", []):
            rules.append(
                {
                    "action": str(rule["action"]),
                    "predicates": [
                        {
                            "op": "filter",
                            "expr": expr_from_json(p["expr"]),
                            "cmp": str(p["cmp"]),
                            "value": p["value"],
                        }
                        for p in rule.get("predicates", [])
                    ],
                }
            )
        return cls(rules=rules, features=[str(f) for f in payload.get("features", [])])


def induce_decisions(
    rows: Sequence[Mapping[str, str]],
    labels: Sequence[str],
    columns: Sequence[str] | None = None,
    *,
    max_rules: int = 12,
) -> DecisionList | None:
    """Induce a first-match decision list that reproduces every observed label.

    Every rule must select *exactly* its class's rows, so the rules cannot
    contradict the data they were learned from.  The learned list is then
    replayed over all examples; a single mistake rejects the whole policy.
    """
    if not rows or len(rows) != len(labels):
        return None
    columns = list(columns or rows[0].keys())
    rules: list[dict[str, Any]] = []
    for label in dict.fromkeys(labels):
        kept = [item == label for item in labels]
        predicates = induce_rule(rows, kept, columns)
        if predicates is None:
            return None
        rules.append({"action": label, "predicates": predicates})
    rules.sort(key=lambda rule: (len(rule["predicates"]), -len(rule["action"])))
    rules = rules[:max_rules]
    policy = DecisionList(rules=rules, features=columns)
    for row, label in zip(rows, labels):
        if policy.decide(row) != label:
            return None
    return policy


def _common_patterns(kept: set[str], dropped: set[str]) -> list[str]:
    pats: list[str] = []
    for value in sorted(kept)[:12]:
        for token in re.split(r"[\s/@:,\-_.]+", value):
            if len(token) >= 2 and all(token in v for v in kept) and not any(token in d for d in dropped):
                pats.append(token)
    for value in sorted(kept)[:12]:
        prefix = value
        while prefix and any(d.startswith(prefix) for d in dropped):
            prefix = prefix[:-1]
        if len(prefix) >= 2 and all(v.startswith(prefix) for v in kept):
            pats.append(prefix)
        suffix = value
        while suffix and any(d.endswith(suffix) for d in dropped):
            suffix = suffix[1:]
        if len(suffix) >= 2 and all(v.endswith(suffix) for v in kept):
            pats.append(suffix)
    return sorted(set(pats))[:8]


def _match_rows(
    in_rows: Sequence[Mapping[str, str]], out_rows: Sequence[Mapping[str, str]]
) -> tuple[list[int], list[bool]] | None:
    """Match output rows to input rows on shared columns.

    Returns (order, mask) where order[i] is the input index aligned with
    output row i, or None when the outputs cannot be aligned this way.
    """
    shared = [c for c in (out_rows[0].keys() if out_rows else []) if in_rows and c in in_rows[0]]
    if not shared:
        return None
    used = [False] * len(in_rows)
    kept = [False] * len(in_rows)
    order: list[int] = []
    for out_row in out_rows:
        found = -1
        for i, in_row in enumerate(in_rows):
            if used[i]:
                continue
            if all(str(in_row.get(c, "")) == str(out_row.get(c, "")) for c in shared):
                found = i
                break
        if found < 0:
            return None
        used[found] = True
        kept[found] = True
        order.append(found)
    return order, kept


def _infer_kept_mask(
    in_rows: Sequence[Mapping[str, str]], out_rows: Sequence[Mapping[str, str]]
) -> list[bool] | None:
    matched = _match_rows(in_rows, out_rows)
    if matched is None:
        return None
    return matched[1]


def _infer_sort(
    core: Table, target: Table, *, allow_limit: bool, extra_limits: Sequence[int] = ()
) -> list[list[dict[str, Any]]]:
    """Return candidate sort (and possibly limit) suffix steps."""
    if list(core.columns) != list(target.columns):
        return []
    results: list[list[dict[str, Any]]] = []

    def matches(steps: Sequence[Mapping[str, Any]]) -> bool:
        try:
            out = apply_program(steps, core)
        except (LivingCoreError, ValueError, TypeError):
            return False
        return out.columns == target.columns and out.rows == target.rows

    identical = core.rows == target.rows

    key_pool: list[Expr] = [col(c) for c in core.columns]
    for c in core.columns:
        key_pool.append(call("number", [col(c)]))
        key_pool.append(call("lower", [col(c)]))
        key_pool.append(call("len", [col(c)]))

    limit_values = sorted({len(target.rows), *[int(n) for n in extra_limits]})
    single_sort: list[list[dict[str, Any]]] = []
    for expr in key_pool:
        for desc in (False, True):
            step = {"op": "sort", "keys": [{"expr": expr, "desc": desc}]}
            single_sort.append([step])
            if allow_limit:
                for n in limit_values:
                    if n > 0 and (n < len(core.rows) or n in set(extra_limits)):
                        single_sort.append([step, {"op": "limit", "n": n}])

    for steps in single_sort:
        if matches(steps):
            results.append(list(steps))

    if not results and len(core.rows) == len(target.rows):
        # two-key sorts
        for i, first in enumerate(key_pool):
            for second in key_pool[i + 1:]:
                for d1 in (False, True):
                    for d2 in (False, True):
                        steps = [{"op": "sort", "keys": [
                            {"expr": first, "desc": d1},
                            {"expr": second, "desc": d2},
                        ]}]
                        if matches(steps):
                            results.append(steps)
                        if len(results) >= 4:
                            break
                    if len(results) >= 4:
                        break
                if len(results) >= 4:
                    break
            if len(results) >= 4:
                break
    # Incidental order is not an explanation.  When an explicit sort also
    # reproduces the demonstration, it is the safer hypothesis: it survives a
    # shuffled input, while "the rows happened to arrive in this order" does
    # not.  The no-op stays last as a fallback.
    if identical and not results:
        results.append([])
    elif identical:
        results.append([])
    return results


def _dedupe_step(columns: Sequence[str], keys: Sequence[str] | None) -> dict[str, Any]:
    return {"op": "dedupe", "keys": [col(k) for k in keys] if keys else None}


def _wrap_order(
    core: Table,
    target: Table,
    extra_limits: Sequence[int] = (),
    *,
    core_program: Sequence[Mapping[str, Any]] | None = None,
    pairs: Sequence[tuple[Table, Table]] | None = None,
) -> list[list[dict[str, Any]]]:
    """All suffixes (dedupe/sort/limit) that turn core into target.

    When the whole pair set is supplied, a suffix is kept only if it turns the
    core into the exact target on *every* pair.  That check is what stops a
    coincidental suffix from crowding out the real one in the cap.
    """
    suites: list[list[dict[str, Any]]] = []
    direct = _infer_sort(core, target, allow_limit=True, extra_limits=extra_limits)
    suites.extend(direct)

    # dedupe then order: try full-row and every single/pair key column
    key_sets: list[list[str] | None] = [None]
    shared = [c for c in target.columns if c in core.columns]
    key_sets.extend([[c] for c in shared])
    key_sets.extend([[a, b] for i, a in enumerate(shared) for b in shared[i + 1:]])
    for keys in key_sets:
        dedupe = _dedupe_step(core.columns, None if keys is None else list(keys))
        try:
            deduped = apply_program([dedupe], core)
        except (LivingCoreError, ValueError, TypeError):
            continue
        if deduped.rows == target.rows and deduped.columns == target.columns:
            suites.append([dedupe])
        else:
            for suffix in _infer_sort(deduped, target, allow_limit=True, extra_limits=extra_limits):
                suites.append([dedupe] + suffix)
    # stable determinism
    seen = set()
    unique: list[list[dict[str, Any]]] = []
    for suite in suites:
        key = json.dumps(program_to_json(suite), sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique.append(suite)
    if core_program is not None and pairs is not None:
        verified = []
        for suite in unique:
            program = list(core_program) + list(suite)
            ok = True
            for table_in, table_out in pairs:
                try:
                    produced = apply_program(program, table_in)
                except (LivingCoreError, ValueError, TypeError):
                    ok = False
                    break
                if produced.columns != table_out.columns or produced.rows != table_out.rows:
                    ok = False
                    break
            if ok:
                verified.append(suite)
        return verified
    return unique[:6]


def _aligned_columns(
    kept_rows: Sequence[Mapping[str, str]], out: Table
) -> list[str]:
    return list(out.columns)


def _core_consistent(
    program: Sequence[Mapping[str, Any]],
    pairs: Sequence[tuple[Table, Table]],
    *,
    order_matters: bool,
) -> bool:
    for table_in, table_out in pairs:
        try:
            produced = apply_program(program, table_in)
        except (LivingCoreError, ValueError, TypeError):
            return False
        if produced.columns != table_out.columns:
            return False
        if order_matters:
            if produced.rows != table_out.rows:
                return False
        else:
            if _multiset(produced.rows, produced.columns) != _multiset(table_out.rows, table_out.columns):
                return False
    return True


def _projection_cores(pairs: Sequence[tuple[Table, Table]], max_programs: int = 24) -> list[list[dict[str, Any]]]:
    """Construct projection/filter programs consistent with all pairs.

    Row order is *not* required here; ordering is recovered separately, so a
    program that is right up to sorting is still a candidate.  Examples whose
    output is empty carry information only as a final check: they are not used
    to infer expressions (there is nothing to align), but a program must still
    reproduce them.
    """
    nonempty = [(a, b) for a, b in pairs if b.rows]
    if not nonempty:
        return []
    if len(nonempty) != len(pairs):
        cores = _projection_cores(nonempty, max_programs)
        return [core for core in cores if _core_consistent(core, pairs, order_matters=False)]
    same_length = all(len(a.rows) == len(b.rows) for a, b in pairs)
    results: list[list[dict[str, Any]]] = []

    def infer_from(rows: Sequence[Mapping[str, str]], out_rows: Sequence[Mapping[str, str]], out_columns: Sequence[str], unordered: bool = False) -> list[dict[str, Any]] | None:
        per_column: list[list[Expr]] = []
        input_columns = list(rows[0].keys()) if rows else []
        for name in out_columns:
            targets = [str(r.get(name, "")) for r in out_rows]
            exprs = infer_expressions(rows, targets, input_columns, unordered=unordered)
            if not exprs:
                return None
            per_column.append(exprs[:2])
        combos = [()]
        for exprs in per_column:
            combos = [c + (e,) for c in combos for e in exprs]
            if len(combos) > max_programs:
                combos = combos[:max_programs]
        items = list(zip(out_columns, combos[0])) if combos else []
        return [_project_from_exprs(items)]

    def _infer_from_aligned(rows, out_rows, out_columns, cap):
        return infer_from(rows, out_rows, out_columns, unordered=False)

    def _infer_from_unordered(rows, out_rows, out_columns, cap):
        return infer_from(rows, out_rows, out_columns, unordered=True)

    if same_length:
        out_columns = list(pairs[0][1].columns)
        if any(list(b.columns) != out_columns for _, b in pairs):
            return []
        alignments = [_match_rows(a.rows, b.rows) for a, b in pairs]
        out_rows = [r for _, b in pairs for r in b.rows]
        program = None
        if all(m is not None for m in alignments):
            rows = [a.rows[i] for (a, _), m in zip(pairs, alignments) for i in m[0]]
            program = _infer_from_aligned(rows, out_rows, out_columns, max_programs)
        if program is None or not _core_consistent(program, pairs, order_matters=False):
            rows = [r for a, _ in pairs for r in a.rows]
            program = _infer_from_unordered(rows, out_rows, out_columns, max_programs)
        if program and _core_consistent(program, pairs, order_matters=False):
            results.append(program)
        if not results:
            results.extend(_filtered_projection_cores(pairs))
        return results

    # Row counts differ.  Recover which input rows survived, per pair.
    kept_by_pair: list[list[bool]] = []
    order_by_pair: list[list[int] | None] = []
    for table_in, table_out in pairs:
        if len(table_out.rows) == 0:
            return []
        matched = _match_rows(table_in.rows, table_out.rows)
        if matched is None:
            n = len(table_out.rows)
            if n <= len(table_in.rows):
                kept_by_pair.append([i < n for i in range(len(table_in.rows))])
                order_by_pair.append(list(range(n)))
            else:
                return []
        else:
            order_by_pair.append(matched[0])
            kept_by_pair.append(matched[1])

    # Filter route: one predicate inferred jointly from every pair.  Local
    # per-pair thresholds are combined, so a global threshold is recovered
    # instead of demanding identical local guesses.
    combined_rows = [r for table_in, _ in pairs for r in table_in.rows]
    combined_kept = [k for kept in kept_by_pair for k in kept]
    filters = _infer_filter(combined_rows, combined_kept, list(pairs[0][0].columns))
    if filters:
        out_columns = list(pairs[0][1].columns)
        out_rows = [r for _, table_out in pairs for r in table_out.rows]
        if all(o is not None for o in order_by_pair):
            kept_rows = [table_in.rows[i] for (table_in, _), order in zip(pairs, order_by_pair) for i in order]
        else:
            kept_rows = [r for (table_in, _), kept in zip(pairs, kept_by_pair) for r, k in zip(table_in.rows, kept) if k]
        for first in filters[:6]:
            program = infer_from(kept_rows, out_rows, out_columns)
            if program is None or not _core_consistent([first] + program, pairs, order_matters=False):
                if all(o is not None for o in order_by_pair):
                    unordered_rows = [table_in.rows[i] for (table_in, _), kept in zip(pairs, kept_by_pair) for i, k in enumerate(kept) if k]
                else:
                    unordered_rows = kept_rows
                program = infer_from(unordered_rows, out_rows, out_columns, unordered=True)
            if program:
                candidate = [first] + program
                if _core_consistent(candidate, pairs, order_matters=False):
                    results.append(candidate)

    # No-filter route: projection from all rows, plus dedupe/limit/order.
    rows = [r for table_in, _ in pairs for r in table_in.rows]
    out_rows = [r for _, table_out in pairs for r in table_out.rows]
    out_columns = list(pairs[0][1].columns)
    if any(list(b.columns) != out_columns for _, b in pairs):
        return results
    # Align targets with kept rows when possible; otherwise use kept rows only.
    if all(o is not None for o in order_by_pair):
        kept_rows = [table_in.rows[i] for (table_in, _), order in zip(pairs, order_by_pair) for i in order]
    else:
        kept_rows = [r for (table_in, _), kept in zip(pairs, kept_by_pair) for r, k in zip(table_in.rows, kept) if k]
    program = infer_from(kept_rows, out_rows, out_columns)
    if program:
        # The core has no filter; the surviving rows are exactly the kept rows.
        # Verify the projection on those rows, then let ordering/limit suffixes
        # (recovered by the caller) turn it into a complete program.
        if _core_consistent(program, pairs, order_matters=False):
            results.append(program)
        else:
            ok = True
            for (table_in, table_out), kept in zip(pairs, kept_by_pair):
                restricted = Table(table_in.columns, [dict(r) for r, k in zip(table_in.rows, kept) if k])
                try:
                    produced = apply_program(program, restricted)
                except (LivingCoreError, ValueError, TypeError):
                    ok = False
                    break
                if produced.columns != table_out.columns:
                    ok = False
                    break
                if _multiset(produced.rows, produced.columns) != _multiset(table_out.rows, table_out.columns):
                    ok = False
                    break
            if ok:
                results.append(program)
    return results


def _aggregate_cores(pairs: Sequence[tuple[Table, Table]], max_programs: int = 12) -> list[list[dict[str, Any]]]:
    """Construct group-by programs consistent with all pairs, modulo row order.

    The search is key-first: a candidate grouping must reproduce the output's
    key columns before any aggregate is tried.  That check removes almost all
    of the space cheaply, which is what keeps induction interactive.
    """
    nonempty = [(a, b) for a, b in pairs if b.rows]
    if not nonempty or len(nonempty) != len(pairs):
        return []
    if any(len(b.rows) > len(a.rows) for a, b in pairs):
        return []
    out_columns = list(pairs[0][1].columns)
    if any(list(b.columns) != out_columns for _, b in pairs):
        return []
    first_in, first_out = pairs[0]
    if not first_out.rows:
        return []

    # ---- expression pools -------------------------------------------------
    columns = list(first_in.columns)
    key_expr_pool: list[Expr] = [col(c) for c in columns]
    all_text = [str(r.get(c, "")) for c in columns for r in first_in.rows]
    seps = _seps_for(all_text) or [",", "@", " ", "-", "/", "_", ":", "|", "."]
    for c in columns:
        for op in ("lower", "upper", "year", "month", "day"):
            key_expr_pool.append(call(op, [col(c)]))
        for sep in seps[:6]:
            key_expr_pool.append(call("after", [col(c)], sep=sep))
            key_expr_pool.append(call("before", [col(c)], sep=sep))
            key_expr_pool.append(call("split", [col(c)], sep=sep, idx=1))
            key_expr_pool.append(call("lower", [call("after", [col(c)], sep=sep)]))
    key_expr_pool = list(dict.fromkeys(key_expr_pool))[:48]

    value_expr_pool: list[Expr] = [col(c) for c in columns]
    numeric_cols = [c for c in columns if all(_is_number(r.get(c, "")) for r in first_in.rows)]
    for i, a in enumerate(numeric_cols):
        for b in numeric_cols[i + 1:]:
            value_expr_pool.append(call("mul", [col(a), col(b)]))
            value_expr_pool.append(call("div", [col(a), col(b)]))
    value_expr_pool = list(dict.fromkeys(value_expr_pool))[:24]

    # ---- filters (only used if the unfiltered grouping fails) -------------
    def candidate_filters() -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for c in columns:
            values = sorted({str(r.get(c, "")) for r in first_in.rows})
            for value in values[:10]:
                if _is_number(value):
                    for cmp in ("gt", "ge", "lt", "le"):
                        out.append({"op": "filter", "expr": col(c), "cmp": cmp, "value": value})
                out.append({"op": "filter", "expr": col(c), "cmp": "eq", "value": value})
                out.append({"op": "filter", "expr": col(c), "cmp": "ne", "value": value})
        return out[:60]

    def filtered_rows(table: Table, step: dict[str, Any] | None) -> list[dict[str, str]]:
        if step is None:
            return [dict(r) for r in table.rows]
        return [dict(r) for r in table.rows if _cmp(step["expr"], step["cmp"], step["value"], r)]

    def eval_vector(expr: Expr, rows: Sequence[Mapping[str, str]]) -> tuple[str, ...] | None:
        values = _expr_values(expr, rows)
        return values

    from itertools import combinations

    results: list[list[dict[str, Any]]] = []
    seen: set[str] = set()

    filter_steps: list[dict[str, Any] | None] = [None]
    for step in candidate_filters():
        filter_steps.append(step)
    for filter_step in filter_steps:
        rows_by_pair = [filtered_rows(table_in, filter_step) for table_in, _ in pairs]
        if any(len(rows) == 0 for rows in rows_by_pair):
            continue
        # Precompute values for the first pair.
        first_rows = rows_by_pair[0]
        key_values = {e: eval_vector(e, first_rows) for e in key_expr_pool}
        value_values = {e: eval_vector(e, first_rows) for e in value_expr_pool}

        for key_size in (0, 1, 2):
            if key_size > len(out_columns):
                continue
            for out_key_indices in combinations(range(len(out_columns)), key_size):
                out_key_multiset = tuple(sorted(
                    tuple(str(r.get(out_columns[i], "")) for i in out_key_indices)
                    for r in first_out.rows
                ))
                key_expr_choices = (
                    combinations([e for e in key_expr_pool if key_values.get(e) is not None], key_size)
                    if key_size else [()]
                )
                for keys_tuple in key_expr_choices:
                    key_vectors = [key_values[e] for e in keys_tuple]
                    grouped = _group_indices(key_vectors, len(first_rows)) if key_size else {tuple(): list(range(len(first_rows)))}
                    if grouped is None:
                        continue
                    grouped_key_multiset = tuple(sorted(grouped.keys()))
                    if grouped_key_multiset != out_key_multiset:
                        continue
                    keys_spec = [
                        {"name": out_columns[i], "expr": e}
                        for i, e in zip(out_key_indices, keys_tuple)
                    ]
                    aggs_spec: list[dict[str, Any]] = []
                    valid = True
                    for out_index in range(len(out_columns)):
                        if out_index in out_key_indices:
                            continue
                        name = out_columns[out_index]
                        target_values = sorted(str(r.get(name, "")) for r in first_out.rows)
                        found = None
                        specs: list[dict[str, Any]] = [{"name": name, "agg": "count", "expr": lit(1)}]
                        for e in value_expr_pool:
                            if value_values.get(e) is None:
                                continue
                            for agg in ("sum", "mean", "min", "max", "first", "last"):
                                specs.append({"name": name, "agg": agg, "expr": e})
                            specs.append({"name": name, "agg": "count_distinct", "expr": e})
                        for spec in specs:
                            produced = _aggregate_groups(grouped, first_rows, keys_spec, aggs_spec + [spec])
                            if produced is None:
                                continue
                            if sorted(str(r.get(name, "")) for r in produced) != target_values:
                                continue
                            ok = True
                            for rows, (_, table_out) in zip(rows_by_pair[1:], pairs[1:]):
                                vectors = [eval_vector(e, rows) for e in keys_tuple]
                                groups2 = _group_indices(vectors, len(rows)) if key_size else {tuple(): list(range(len(rows)))}
                                if groups2 is None:
                                    ok = False
                                    break
                                produced2 = _aggregate_groups(groups2, rows, [{"name": out_columns[i], "expr": e} for i, e in zip(out_key_indices, keys_tuple)], aggs_spec + [spec])
                                if produced2 is None or sorted(str(r.get(name, "")) for r in produced2) != sorted(
                                    str(r.get(name, "")) for r in table_out.rows
                                ):
                                    ok = False
                                    break
                            if ok:
                                found = spec
                                break
                        if found is None:
                            valid = False
                            break
                        aggs_spec.append(found)
                    if not valid:
                        continue
                    program = [s for s in (filter_step,) if s] + [
                        {"op": "group", "keys": keys_spec, "aggs": aggs_spec}
                    ]
                    if not _core_consistent(program, pairs, order_matters=False):
                        continue
                    sig = _program_signature(program)
                    if sig in seen:
                        continue
                    seen.add(sig)
                    results.append(program)
                    if len(results) >= max_programs:
                        return results
        if results:
            break
    return results


def _group_indices(
    key_vectors: Sequence[Sequence[str]], row_count: int
) -> dict[tuple[str, ...], list[int]] | None:
    if not key_vectors:
        return {tuple(): list(range(row_count))}
    for vector in key_vectors:
        if vector is None or len(vector) != row_count:
            return None
    groups: dict[tuple[str, ...], list[int]] = {}
    for i in range(row_count):
        key = tuple(vector[i] for vector in key_vectors)
        groups.setdefault(key, []).append(i)
    return groups


def _aggregate_groups(
    groups: Mapping[tuple[str, ...], Sequence[int]],
    rows: Sequence[Mapping[str, str]],
    keys_spec: Sequence[Mapping[str, Any]],
    aggs: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]] | None:
    out: list[dict[str, str]] = []
    try:
        for key, indices in groups.items():
            record: dict[str, str] = {}
            for spec, part in zip(keys_spec, key):
                record[spec["name"]] = part
            for agg in aggs:
                values = [eval_expr(agg["expr"], rows[i]) for i in indices]
                record[agg["name"]] = fmt_value(_aggregate(agg["agg"], values, [rows[i] for i in indices], agg.get("k", 2)))
            out.append(record)
    except (LivingCoreError, ValueError, TypeError, ZeroDivisionError, OverflowError):
        return None
    return out


def _filter_candidate_pool(
    rows: Sequence[Mapping[str, str]], columns: Sequence[str], limit: int = 800
) -> list[dict[str, Any]]:
    """Candidate predicates over plain and derived quantities.

    Generation is round-robin across expressions in two phases, so one
    busy expression (for example an id column) cannot starve the derived
    expressions that this fallback exists to find.
    """
    exprs: list[Expr] = []
    for i, a in enumerate(columns):
        for b in columns[i + 1:]:
            for op in ("mul", "div", "add", "sub"):
                exprs.append(call(op, [col(a), col(b)]))
                exprs.append(call(op, [col(b), col(a)]))
            exprs.append(call("round", [call("div", [col(a), col(b)])], k=2))
            exprs.append(call("round", [call("div", [col(b), col(a)])], k=2))
            exprs.append(call("mul", [call("div", [call("sub", [col(b), col(a)]), col(a)]), lit(100.0)]))
            exprs.append(call("mul", [call("div", [call("sub", [col(a), col(b)]), col(b)]), lit(100.0)]))
    numeric_columns = {
        c for c in columns if all(_is_number(r.get(c, "")) or str(r.get(c, "")) == "" for r in rows)
    }
    for c in columns:
        exprs.append(col(c))
        for op in ("lower", "upper", "strip", "year", "month", "day", "len"):
            if op in ("lower", "upper", "strip") and c in numeric_columns:
                continue
            exprs.append(call(op, [col(c)]))
        for k in (0, 2):
            exprs.append(call("round", [col(c)], k=k))
    exprs = list(dict.fromkeys(exprs))

    plans: list[tuple[Expr, list[tuple[str, Any]]]] = []
    for expr in exprs:
        values = []
        try:
            for row in rows:
                values.append(fmt_value(eval_expr(expr, row)))
        except (LivingCoreError, ValueError, TypeError, ZeroDivisionError, OverflowError):
            continue
        unique = sorted(set(values))
        if not unique:
            continue
        numeric = all(_is_number(v) or v.strip() == "" for v in unique)
        candidates: list[tuple[str, Any]] = []
        if numeric:
            numbers = sorted({parse_number(v) for v in unique if v.strip() != ""})
            if not numbers:
                continue
            low, high = numbers[0], numbers[-1]
            prioritized = _round_numbers(low, high)
            prioritized.extend(numbers[:10])
            prioritized.extend(_midpoints(numbers))
            rendered: list[str] = []
            for number in prioritized:
                text = fmt_value(number)
                if text not in rendered:
                    rendered.append(text)
            for value in rendered:
                candidates.append(("gt", value))
                candidates.append(("lt", value))
            for value in rendered[:8]:
                for cmp in ("ge", "le", "eq"):
                    candidates.append((cmp, value))
            if 2 <= len(unique) <= 8:
                candidates.append(("in", unique[:8]))
        else:
            for value in unique[:6]:
                for cmp in ("eq", "ne", "contains", "startswith", "endswith"):
                    candidates.append((cmp, value))
            if 2 <= len(unique) <= 8:
                candidates.append(("in", unique[:8]))
        plans.append((expr, candidates))

    steps: list[dict[str, Any]] = []
    seen: set[str] = set()

    def push(expr: Expr, cmp: str, value: Any) -> bool:
        step = {"op": "filter", "expr": expr, "cmp": cmp, "value": value}
        sig = json.dumps({**step, "expr": expr_to_json(expr)}, sort_keys=True, default=str)
        if sig in seen:
            return True
        seen.add(sig)
        steps.append(step)
        return len(steps) < limit

    # phase 1: a short prefix from every expression
    for expr, candidates in plans:
        for cmp, value in candidates[:10]:
            if not push(expr, cmp, value):
                return steps
    # phase 2: fill the remainder round-robin
    for expr, candidates in plans:
        for cmp, value in candidates[10:]:
            if not push(expr, cmp, value):
                return steps
    return steps[:limit]


def _filtered_projection_cores(pairs: Sequence[tuple[Table, Table]], max_programs: int = 12) -> list[list[dict[str, Any]]]:
    """Infer filter + projection jointly by exact whole-program search.

    This is the route for tasks where output rows cannot be aligned to input
    rows one-to-one (computed identifiers, duplicate keys, filtered subsets).
    Expressions are inferred from the output value multiset (subset semantics)
    and every filter candidate is checked by running the whole program.
    """
    if not pairs:
        return []
    out_columns = list(pairs[0][1].columns)
    if any(list(b.columns) != out_columns for _, b in pairs):
        return []
    in_columns = list(pairs[0][0].columns)
    if any(list(a.columns) != in_columns for a, _ in pairs):
        return []
    all_rows = [r for a, _ in pairs for r in a.rows]
    if not all_rows:
        return []
    expr_sets: list[list[Expr]] = []
    for name in out_columns:
        targets = [str(r.get(name, "")) for _, b in pairs for r in b.rows]
        exprs = infer_expressions(all_rows, targets, in_columns, unordered=True, subset=True, limit=3)
        if not exprs:
            return []
        expr_sets.append(exprs[:2])
    combos = [()]
    for exprs in expr_sets:
        combos = [c + (e,) for c in combos for e in exprs][:max_programs]
    items_list = [list(zip(out_columns, combo)) for combo in combos]

    results: list[list[dict[str, Any]]] = []
    filters = [None] + _filter_candidate_pool(all_rows, in_columns)
    for filter_step in filters:
        for items in items_list:
            program = [s for s in (filter_step,) if s] + [{"op": "project", "items": [
                {"name": name, "expr": expr} for name, expr in items
            ]}]
            if filter_step is not None and not _core_consistent(program, pairs, order_matters=False):
                continue
            if filter_step is None:
                # Without a filter the core is a superset; dedupe/sort/limit
                # suffixes are what select the output rows.
                produced = apply_program(program, pairs[0][0])
                if produced.columns != out_columns:
                    continue
                if any(
                    not all(
                        str(r.get(name, "")) in {str(row.get(name, "")) for row in produced.rows}
                        for r in table_out.rows
                    )
                    for name in out_columns
                    for _, table_out in pairs
                ):
                    continue
            sig = _program_signature(program)
            if all(_program_signature(existing) != sig for existing in results):
                results.append(program)
            if len(results) >= max_programs:
                return results
    return results


def _common_suffixes(
    core: Sequence[Mapping[str, Any]],
    pairs: Sequence[tuple[Table, Table]],
    all_limits: Sequence[int],
) -> list[list[dict[str, Any]]]:
    """Ordering suffixes that work for every pair, including no-op limits."""
    per_pair: list[dict[str, list[dict[str, Any]]]] = []
    for table_in, table_out in pairs:
        try:
            produced = apply_program(core, table_in)
        except (LivingCoreError, ValueError, TypeError):
            return []
        options: dict[str, list[dict[str, Any]]] = {}
        for suffix in _wrap_order(produced, table_out, extra_limits=all_limits):
            sig = json.dumps(program_to_json(suffix), sort_keys=True)
            options[sig] = list(suffix)
        if not options:
            return []
        per_pair.append(options)
    common = set(per_pair[0])
    for options in per_pair[1:]:
        common &= set(options)
    return [per_pair[0][sig] for sig in sorted(common)][:8]


def synthesize(pairs: Sequence[tuple[Table, Table]], *, max_programs: int = 40) -> list[list[dict[str, Any]]]:
    """Return every program consistent with all (input, output) pairs.

    Consistency is exact for the final program: same column order, same row
    order, same cell bytes.  Candidate *cores* may be right only up to row
    order; ordering is then recovered as an explicit suffix of the program.
    """
    if not pairs:
        raise LivingCoreError("PAIRS_REQUIRED")
    programs: list[list[dict[str, Any]]] = []
    seen: set[str] = set()

    def add(program: Sequence[Mapping[str, Any]]) -> None:
        for table_in, table_out in pairs:
            try:
                produced = apply_program(program, table_in)
            except (LivingCoreError, ValueError, TypeError):
                return
            if produced.columns != table_out.columns or produced.rows != table_out.rows:
                return
        sig = _program_signature(program)
        if sig not in seen:
            seen.add(sig)
            programs.append(list(program))

    all_limits = sorted({len(b.rows) for _, b in pairs})
    first_in, first_out = pairs[0]

    def try_cores(cores: Sequence[Sequence[Mapping[str, Any]]]) -> None:
        for core in cores:
            add(core)
            if len(programs) >= max_programs:
                return
            try:
                produced = apply_program(core, first_in)
            except (LivingCoreError, ValueError, TypeError):
                continue
            if produced.columns != first_out.columns:
                continue
            suffixes = _wrap_order(
                produced,
                first_out,
                extra_limits=all_limits,
                core_program=core,
                pairs=pairs,
            )
            for suffix in suffixes:
                if not suffix:
                    continue
                add(list(core) + suffix)
            if len(programs) < 2:
                for suffix in _common_suffixes(core, pairs, all_limits):
                    add(list(core) + suffix)

    try_cores(_projection_cores(pairs))
    if not programs:
        try_cores(_filtered_projection_cores(pairs))
    if not programs:
        try_cores(_aggregate_cores(pairs))
    return programs


# --------------------------------------------------------------------------- #
# active induction                                                             #
# --------------------------------------------------------------------------- #


@dataclass
class InductionResult:
    success: bool
    program: list[dict[str, Any]] | None
    probes: int
    demonstrations: int
    rounds: int
    validation_cases: int
    failure_reason: str | None = None
    consistent_programs: int = 0
    ambiguous: bool = False
    transcript: list[dict[str, Any]] = field(default_factory=list)
    model_dependency_count: int = 0
    incremental_spend_usd: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA + "_INDUCTION",
            "success": self.success,
            "program": program_to_json(self.program) if self.program else None,
            "probes": self.probes,
            "demonstrations": self.demonstrations,
            "rounds": self.rounds,
            "validation_cases": self.validation_cases,
            "consistent_programs": self.consistent_programs,
            "ambiguous": self.ambiguous,
            "failure_reason": self.failure_reason,
            "model_dependency_count": 0,
            "network_dependency_count": 0,
            "incremental_spend_usd": 0,
        }


def _schema_from_tables(tables: Sequence[Table]) -> dict[str, Any]:
    first = tables[0]
    columns = list(first.columns)
    info: dict[str, Any] = {"columns": columns, "types": {}, "values": {}, "widths": {}}
    for c in columns:
        values = [str(t.rows[i].get(c, "")) for t in tables for i in range(len(t.rows))]
        info["values"][c] = values
        info["widths"][c] = (min(len(v) for v in values), max(len(v) for v in values)) if values else (0, 0)
        if values and all(_is_number(v) for v in values if v != ""):
            nums = [parse_number(v) for v in values if v != ""]
            info["types"][c] = "number" if nums else "text"
            info.setdefault("integral", {})[c] = all(abs(n - round(n)) <= 1e-9 for n in nums)
        elif values and all(re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}", v) for v in values):
            info["types"][c] = "date"
        else:
            info["types"][c] = "text"
    return info


def _generate_input(schema: Mapping[str, Any], rng: random.Random, *, novel: bool) -> Table:
    """Generate a probe inside the observed value support.

    Probes are for discriminating hypotheses, not for inventing new domains.
    Text categories, date formats and identifier vocabularies stay inside the
    support of the demonstrations; numbers additionally explore boundary
    values (midpoints and neighbours) because thresholds live between observed
    values.  Duplicates and empty results are deliberately possible.
    """
    columns = list(schema["columns"])
    rows: list[dict[str, str]] = []
    count = rng.randint(1, 9) if novel else rng.randint(2, 6)
    cover_all = bool(novel) and rng.random() < 0.5
    for row_index in range(count):
        row: dict[str, str] = {}
        for column_index, c in enumerate(columns):
            kind = schema["types"][c]
            values = [v for v in schema["values"][c] if v != ""]
            if kind == "number" and values:
                numbers = sorted({parse_number(v) for v in values})
                integral = bool(schema.get("integral", {}).get(c, all(abs(n - round(n)) <= 1e-9 for n in numbers)))
                if novel:
                    if integral:
                        low, high = int(round(numbers[0])), int(round(numbers[-1]))
                        choices = list(range(low - 1, high + 2))
                        if len(choices) > 160:
                            choices = sorted({low - 1, high + 1, 0, *numbers,
                                              *(rng.randint(low, high) for _ in range(40))})
                    else:
                        choices = list(numbers)
                        for left, right in zip(numbers, numbers[1:]):
                            choices.extend([(left + right) / 2.0, left + 1.0, right - 1.0])
                        choices.extend([numbers[0] - 1.0, numbers[-1] + 1.0])
                    value = rng.choice(choices)
                else:
                    value = rng.choice(numbers)
                if cover_all and len(choices) > 1 and row_index < 6:
                    value = sorted(set(choices))[(row_index + column_index) % min(len(set(choices)), 6)]
                row[c] = fmt_value(value)
            elif kind == "date" and values:
                if cover_all and len(values) > 1:
                    row[c] = values[(row_index + column_index) % len(values)]
                else:
                    row[c] = rng.choice(values) if not novel else _neighbour_date(rng.choice(values), rng)
            else:
                pool = values or [""]
                if cover_all and len(pool) > 1:
                    row[c] = pool[(row_index + column_index) % len(pool)]
                else:
                    row[c] = rng.choice(pool)
        rows.append(row)
    if len(rows) >= 3 and rng.random() < 0.6:
        rows.append(dict(rng.choice(rows)))
    if rng.random() < 0.2 and len(rows) > 1:
        rows.pop(rng.randrange(len(rows)))
    rng.shuffle(rows)
    return Table(columns, rows)


def _coverage_input(schema: Mapping[str, Any]) -> Table:
    """Deterministic input that exercises every observed categorical value and
    the numeric extremes.  Validation must touch the support boundary, not
    only random draws, or two different mechanisms can look identical.
    """
    columns = list(schema["columns"])
    pools: dict[str, list[str]] = {}
    for c in columns:
        values = [v for v in schema["values"][c] if v != ""]
        if schema["types"][c] == "number" and values:
            numbers = sorted({parse_number(v) for v in values})
            pools[c] = [fmt_value(n) for n in (numbers[0], numbers[-1], numbers[len(numbers) // 2])]
        else:
            pools[c] = list(dict.fromkeys(values))[:8] or [""]
    count = max(len(pool) for pool in pools.values())
    count = max(count, 2)
    rows = []
    for i in range(min(count, 10)):
        rows.append({c: pools[c][i % len(pools[c])] for c in columns})
    return Table(columns, rows)


def _permuted_inputs(schema: Mapping[str, Any]) -> list[Table]:
    """Two inputs that differ only by row order, spanning the whole support.

    A mechanism that sorts and a mechanism that preserves input order agree on
    plenty of small random draws; they cannot agree on both an ordering and its
    reversal when every value is present.  These cases make that difference
    observable without spending a probe on luck.
    """
    columns = list(schema["columns"])
    pools: dict[str, list[str]] = {}
    for c in columns:
        values = [v for v in schema["values"][c] if v != ""]
        if schema["types"][c] == "number" and values:
            numbers = sorted({parse_number(v) for v in values})
            pools[c] = [fmt_value(n) for n in numbers]
        else:
            pools[c] = list(dict.fromkeys(values))
        if not pools[c]:
            pools[c] = [""]
    count = max(len(pool) for pool in pools.values())
    count = min(max(count, 2), 12)
    rows = [{c: pools[c][i % len(pools[c])] for c in columns} for i in range(count)]
    return [Table(columns, rows), Table(columns, list(reversed(rows)))]


def _neighbour_date(value: str, rng: random.Random) -> str:
    match = re.match(r"^(\d{4})([-/])(\d{1,2})([-/])(\d{1,2})", value)
    if not match:
        return value
    year = int(match.group(1))
    month = int(match.group(3))
    day = int(match.group(5))
    if rng.random() < 0.5:
        month = min(12, max(1, month + rng.choice([-1, 0, 1])))
    else:
        day = min(28, max(1, day + rng.choice([-2, -1, 0, 1, 2])))
    sep = match.group(2)
    return f"{year:04d}{sep}{month:02d}{sep}{day:02d}"


def _mutate_date(value: str, rng: random.Random) -> str:
    match = re.match(r"^(\d{4})([-/])(\d{1,2})([-/])(\d{1,2})", value)
    if not match:
        return value
    year = int(match.group(1)) + rng.choice([-1, 0, 1])
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    sep = match.group(2)
    return f"{year:04d}{sep}{month:02d}{sep}{day:02d}"


def _discriminating_input(
    candidates: Sequence[Sequence[Mapping[str, Any]]],
    schema: Mapping[str, Any],
    rng: random.Random,
    *,
    seen: set[str] | None = None,
    pool: Sequence[Table] | None = None,
) -> Table:
    best: Table | None = None
    best_score = -1
    pool = list(pool) if pool is not None else _battery(schema, rng)
    for table in pool:
        if seen and table.to_csv() in seen:
            # Asking the same question twice buys nothing and costs a probe.
            continue
        predictions = []
        for program in candidates:
            try:
                out = apply_program(program, table)
                predictions.append(tuple((tuple(r.items()) for r in out.rows)))
            except (LivingCoreError, ValueError, TypeError):
                predictions.append(("__error__",))
        distinct = len(set(predictions))
        if distinct > best_score:
            best_score = distinct
            best = table
            if distinct == len(candidates):
                break
    if best is None:
        for _ in range(20):
            fresh = _generate_input(schema, rng, novel=True)
            if not seen or fresh.to_csv() not in seen:
                return fresh
        best = _generate_input(schema, rng, novel=True)
    return best


def _covering_inputs(schema: Mapping[str, Any], *, limit: int = 64) -> list[Table]:
    """Tables that pair every value of one column with every value of another.

    Independent sampling of columns is a bad experiment: with six values per
    column the interesting combination is one cell in thirty-six, so a handful
    of random draws routinely never visits it.  A pair-covering design visits
    every combination once, which is the cheapest way to see how two columns
    interact -- and interaction is where a wrong hypothesis dies.
    """
    columns = list(schema["columns"])
    pools: dict[str, list[str]] = {}
    for c in columns:
        values = [v for v in dict.fromkeys(str(v) for v in schema["values"][c]) if v != ""]
        pools[c] = values[:8] or [""]
    tables: list[Table] = []
    for i in range(len(columns)):
        for j in range(i + 1, len(columns)):
            left, right = columns[i], columns[j]
            rows: list[dict[str, str]] = []
            for left_value in pools[left]:
                for right_value in pools[right]:
                    if len(rows) >= limit:
                        break
                    row: dict[str, str] = {}
                    for c in columns:
                        if c == left:
                            row[c] = left_value
                        elif c == right:
                            row[c] = right_value
                        else:
                            pool = pools[c]
                            row[c] = pool[len(rows) % len(pool)]
                    rows.append(row)
            if rows:
                tables.append(Table(columns, rows))
    return tables


def _battery(schema: Mapping[str, Any], rng: random.Random, *, extra: int = 12) -> list[Table]:
    """Inputs a hypothesis can be tested against without inventing a domain.

    Deterministic coverage, ordering and pair-covering cases come first -- they
    carry the most information per query -- followed by fresh draws so later
    rounds are not stuck asking the same question twice.
    """
    return (
        [_coverage_input(schema)]
        + _permuted_inputs(schema)
        + _covering_inputs(schema)
        + [_generate_input(schema, rng, novel=True) for _ in range(extra)]
    )


def _behaviour(program: Sequence[Mapping[str, Any]], table: Table) -> tuple[Any, ...]:
    try:
        out = apply_program(program, table)
    except (LivingCoreError, ValueError, TypeError):
        return ("__error__",)
    return (tuple(out.columns), tuple(tuple(row.items()) for row in out.rows))


def induce(
    query: Callable[[Table], Table | None],
    demonstrations: Sequence[tuple[Table, Table]],
    *,
    seed: int = 0,
    max_probes: int = 24,
    validation_cases: int = 6,
    max_rounds: int | None = None,
    max_programs: int = 40,
    time_budget_s: float | None = None,
) -> InductionResult:
    """Learn an exact program from few demonstrations and self-chosen probes.

    ``query`` is the only access to the hidden mechanism.  It may return
    ``None`` for an inadmissible probe (crash, timeout, domain violation), in
    which case the probe is discarded and counted, never guessed over.

    Learning stops when the learner *knows* -- one behaviour survives every
    question the data justifies and validation agrees -- or when a stated
    resource (``max_probes``, ``time_budget_s``) is spent.  There is no fixed
    number of steps: ``max_rounds`` is only a safety valve for callers that
    need one.  When several programs remain that no justified input can
    separate, the simplest is returned and the ambiguity is reported instead
    of being hidden.
    """
    if not demonstrations:
        raise LivingCoreError("DEMONSTRATION_REQUIRED")
    import time as _time

    started = _time.monotonic()
    rng = random.Random(seed)
    pairs: list[tuple[Table, Table]] = [(a.copy(), b.copy()) for a, b in demonstrations]
    transcript: list[dict[str, Any]] = []
    probes = 0
    invalid = 0
    validated = 0
    schema = _schema_from_tables([a for a, _ in pairs])
    rounds = 0
    round_limit = max_rounds if max_rounds is not None else max(64, 8 * max(1, max_probes))

    def over_budget() -> bool:
        return time_budget_s is not None and (_time.monotonic() - started) > time_budget_s

    def known(table: Table) -> bool:
        return table.to_csv() in {t.to_csv() for t, _ in pairs}

    def admit(table: Table, out: Table | None) -> None:
        nonlocal probes, invalid, schema
        probes += 1
        if out is None:
            invalid += 1
            return
        pairs.append((table, out))
        schema = _schema_from_tables([a for a, _ in pairs])

    while rounds < round_limit and not over_budget():
        if probes >= max_probes:
            # Every way forward from here -- a discriminating probe or an
            # honest validation -- costs a query, and the budget is spent.
            break
        rounds += 1
        candidates = synthesize(pairs, max_programs=max_programs)
        transcript.append({"round": rounds, "consistent_programs": len(candidates)})
        if not candidates:
            if probes >= max_probes:
                break
            probe = _generate_input(schema, rng, novel=True)
            for _ in range(20):
                if not known(probe):
                    break
                probe = _generate_input(schema, rng, novel=True)
            if known(probe):
                break
            out = query(probe)
            admit(probe, out)
            transcript.append({"probe": probe.to_csv(), "admitted": out is not None})
            continue

        cheap = _battery(schema, rng)
        sharp = _covering_inputs(schema)

        def splits(tables: Sequence[Table]) -> list[Table]:
            """Tables that still separate the surviving hypotheses."""
            useful = []
            for table in tables:
                if known(table):
                    continue
                signatures = {_behaviour(candidate, table) for candidate in candidates}
                if len(signatures) > 1:
                    useful.append(table)
            return useful

        def validate(candidate: Sequence[Mapping[str, Any]]) -> bool:
            nonlocal validated
            inputs: list[Table] = []
            asked = {table.to_csv() for table, _ in pairs}
            for table in _battery(schema, rng, extra=validation_cases):
                key = table.to_csv()
                if key in asked:
                    continue
                asked.add(key)
                inputs.append(table)
            remaining = max_probes - probes
            if remaining < len(inputs):
                # Never claim validation that was not paid for.  Fewer cases
                # is a weaker claim, and the count says exactly what was done.
                inputs = inputs[: max(0, remaining)]
            paid = 0
            for case, probe in enumerate(inputs):
                out = query(probe)
                admit(probe, out)
                if out is None:
                    continue
                if _behaviour(candidate, probe) != _behaviour_from(out):
                    transcript.append({"validation_mismatch": True, "case": case + 1})
                    return False
                paid += 1
            if paid < min(2, validation_cases):
                # Too little evidence to call it learned.
                return False
            validated = paid
            transcript.append({"validated": True, "cases": paid})
            return True

        def finish(candidate: Sequence[Mapping[str, Any]], consistent: int) -> InductionResult:
            return InductionResult(
                success=True,
                program=[dict(step) for step in candidate],
                probes=probes,
                demonstrations=len(demonstrations),
                rounds=rounds,
                validation_cases=validated,
                consistent_programs=consistent,
                transcript=transcript,
            )

        # Evidence ladder, cheapest first.  Random draws and coverage cases are
        # cheap to reason about; the pair-covering design is what exposes a
        # wrong threshold, so it is paid for only when the cheap questions stop
        # separating the survivors.
        candidates_pool = splits(cheap) or splits(sharp)
        if not candidates_pool:
            # No justified input separates what is left: the survivors are one
            # mechanism on this domain.  Occam chooses, and how many programs
            # remain consistent is reported rather than hidden.
            if validate(simplest_program(candidates)):
                return finish(simplest_program(candidates), len(candidates))
            continue

        if probes >= max_probes:
            break

        probe = _discriminating_input(
            candidates,
            schema,
            rng,
            seen={table.to_csv() for table, _ in pairs},
            pool=candidates_pool,
        )
        out = query(probe)
        admit(probe, out)
        if out is not None:
            transcript.append({"probe": probe.to_csv(), "admitted": True, "round": rounds})

    return InductionResult(
        success=False,
        program=None,
        probes=probes,
        demonstrations=len(demonstrations),
        rounds=rounds,
        validation_cases=0,
        consistent_programs=0,
        ambiguous=True,
        failure_reason="NO_CONSISTENT_PROGRAM_WITHIN_BUDGET",
        transcript=transcript,
    )


def _behaviour_from(out: Table) -> tuple[Any, ...]:
    return (tuple(out.columns), tuple(tuple(row.items()) for row in out.rows))


def _separation(candidates: Sequence[Sequence[Mapping[str, Any]]], table: Table) -> int:
    return len({_behaviour(program, table) for program in candidates})


def simplest_program(
    candidates: Sequence[Sequence[Mapping[str, Any]]],
) -> Sequence[Mapping[str, Any]]:
    """The least arbitrary explanation among equally consistent programs.

    An explicit ordering is a mechanism; "the rows happened to arrive that way"
    is a coincidence, so a program that says what it does ranks first.
    """

    def rank(program: Sequence[Mapping[str, Any]]) -> tuple[Any, ...]:
        has_sort = any(step.get("op") == "sort" for step in program)
        return (0 if has_sort else 1, len(program), _program_signature(program))

    return min(candidates, key=rank)


# --------------------------------------------------------------------------- #
# learned salience memory                                                      #
# --------------------------------------------------------------------------- #


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9_]+", text.lower()) if len(t) > 1}


class SalienceModel:
    """Online logistic ranker over interpretable salience features.

    The features are the creature's answer to "what is worth remembering?":
    goal relevance, recency, surprise, demonstrated usefulness and cost saved.
    Weights are learned from retrieval outcomes, so importance is not a
    hand-written constant that someone guessed in advance.
    """

    FEATURES = ("relevance", "recency", "surprise", "usefulness", "cost_saved", "bias")

    def __init__(self) -> None:
        self.weights = {
            "relevance": 1.0,
            "recency": 1.0,
            "surprise": 0.5,
            "usefulness": 1.0,
            "cost_saved": 0.5,
            "bias": -1.0,
        }
        self.updates = 0

    def score(self, features: Mapping[str, float]) -> float:
        return sum(self.weights[k] * float(features.get(k, 0.0)) for k in self.FEATURES)

    def probability(self, features: Mapping[str, float]) -> float:
        value = self.score(features)
        if value >= 0:
            z = math.exp(-min(value, 60.0))
            return 1.0 / (1.0 + z)
        z = math.exp(max(value, -60.0))
        return z / (1.0 + z)

    def learn(self, features: Mapping[str, float], label: int, *, rate: float = 0.25) -> None:
        if label not in (0, 1):
            raise LivingCoreError("SALIENCE_LABEL_INVALID")
        p = self.probability(features)
        error = float(label) - p
        for key in self.FEATURES:
            self.weights[key] += rate * error * float(features.get(key, 0.0))
        self.updates += 1

    def to_dict(self) -> dict[str, Any]:
        return {"weights": dict(self.weights), "updates": self.updates}


@dataclass
class MemoryEntry:
    entry_id: str
    kind: str  # skill | episode | fact
    text: str
    payload: dict[str, Any]
    created: int
    last_used: int
    uses: int = 0
    successes: int = 0
    failures: int = 0
    surprise: float = 0.0
    cost_saved: float = 0.0
    confidence: float = 0.5
    retired: bool = False
    tags: tuple[str, ...] = ()

    def salience_features(
        self,
        now: int,
        query_tokens: set[str],
        half_life: float = 200.0,
        *,
        tokens: frozenset[str] | set[str] | None = None,
    ) -> dict[str, float]:
        entry_tokens = _tokens(self.text) if tokens is None else tokens
        union = entry_tokens | query_tokens
        relevance = (len(entry_tokens & query_tokens) / len(union)) if union else 0.0
        age = max(0, now - self.last_used)
        recency = 0.5 ** (age / half_life)
        usefulness = (self.successes + 0.5) / (self.uses + 1.0)
        return {
            "relevance": relevance,
            "recency": recency,
            "surprise": min(1.0, self.surprise),
            "usefulness": usefulness,
            "cost_saved": min(1.0, self.cost_saved),
            "bias": 1.0,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "kind": self.kind,
            "text": self.text,
            "payload": self.payload,
            "created": self.created,
            "last_used": self.last_used,
            "uses": self.uses,
            "successes": self.successes,
            "failures": self.failures,
            "surprise": self.surprise,
            "cost_saved": self.cost_saved,
            "confidence": self.confidence,
            "retired": self.retired,
            "tags": list(self.tags),
        }


class Memory:
    """Episodic + semantic + procedural memory with learned salience."""

    def __init__(self, *, half_life: float = 200.0) -> None:
        self.entries: dict[str, MemoryEntry] = {}
        self.order: list[str] = []
        self.clock = 0
        self.model = SalienceModel()
        self.half_life = half_life
        self.retrieval_log: list[dict[str, Any]] = []
        # Retrieval index.  ``_postings`` maps a token to the entries that
        # contain it, so a query only scores entries that can have non-zero
        # relevance.  Everything else has relevance 0 by definition, and its
        # score is therefore a query-independent number that can be kept
        # sorted once and merged in.  The result is identical to scanning every
        # entry (the acceptance suite compares against a brute-force scorer),
        # but the work per query scales with the posting list, not with the
        # size of memory.
        self._postings: dict[str, set[str]] = {}
        self._entry_tokens: dict[str, frozenset[str]] = {}
        self._static: list[tuple[float, str]] | None = None
        self._static_stamp: tuple[int, int] | None = None
        self._rest: dict[str, float] = {}

    # -- write ------------------------------------------------------------
    def add(
        self,
        kind: str,
        text: str,
        payload: Mapping[str, Any],
        *,
        surprise: float = 0.0,
        cost_saved: float = 0.0,
        confidence: float = 0.5,
        tags: Sequence[str] = (),
    ) -> str:
        if kind not in ("skill", "episode", "fact"):
            raise LivingCoreError("MEMORY_KIND_INVALID")
        self.clock += 1
        digest = hashlib.sha256(
            json.dumps({"kind": kind, "text": text, "payload": payload, "clock": self.clock}, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]
        entry_id = f"{kind[:1]}-{digest}"
        entry = MemoryEntry(
            entry_id=entry_id,
            kind=kind,
            text=text,
            payload=dict(payload),
            created=self.clock,
            last_used=self.clock,
            surprise=float(surprise),
            cost_saved=float(cost_saved),
            confidence=float(confidence),
            tags=tuple(tags),
        )
        self.entries[entry_id] = entry
        self.order.append(entry_id)
        tokens = frozenset(_tokens(text))
        self._entry_tokens[entry_id] = tokens
        for token in tokens:
            self._postings.setdefault(token, set()).add(entry_id)
        self._static = None
        return entry_id

    # -- index ------------------------------------------------------------
    def _invalidate(self) -> None:
        self._static = None
        self._rest = {}

    def rebuild_index(self) -> None:
        """Reconstruct the retrieval index from the entries themselves.

        Used after loading a snapshot: the index is derived state and never
        trusted from disk.
        """
        self._postings.clear()
        self._entry_tokens.clear()
        self._invalidate()
        for entry in self.entries.values():
            tokens = frozenset(_tokens(entry.text))
            self._entry_tokens[entry.entry_id] = tokens
            for token in tokens:
                self._postings.setdefault(token, set()).add(entry.entry_id)

    def _static_scores(self) -> list[tuple[float, str]]:
        """Entries ordered by the query-independent part of their salience.

        For an entry whose text shares no token with the query, relevance is
        exactly 0, so its score is this number.  Keeping it sorted once per
        change turns the "everything else" half of retrieval into a merge.
        """
        stamp = (self.clock, self.model.updates)
        if self._static is not None and self._static_stamp == stamp:
            return self._static
        scored = []
        rest: dict[str, float] = {}
        weights = self.model.weights
        for entry in self.entries.values():
            if entry.retired:
                continue
            features = entry.salience_features(
                self.clock, frozenset(), self.half_life,
                tokens=self._entry_tokens.get(entry.entry_id, frozenset()),
            )
            features["relevance"] = 0.0
            value = self.model.score(features)
            scored.append((value, entry.entry_id))
            rest[entry.entry_id] = value
        scored.sort(key=lambda item: (-item[0], item[1]))
        self._static = scored
        self._rest = rest
        self._static_stamp = stamp
        return scored

    def touch(self, entry_id: str, *, success: bool, cost_saved: float = 0.0) -> None:
        entry = self.entries[entry_id]
        entry.uses += 1
        entry.last_used = self.clock
        if success:
            entry.successes += 1
        else:
            entry.failures += 1
        entry.cost_saved = max(entry.cost_saved, float(cost_saved))
        features = entry.salience_features(
            self.clock, self._entry_tokens.get(entry_id, frozenset()), self.half_life
        )
        self.model.learn(features, 1 if success else 0)
        self._invalidate()

    # -- read -------------------------------------------------------------
    def retrieve(self, query: str, *, kind: str | None = None, k: int = 5) -> list[tuple[float, MemoryEntry]]:
        query_tokens = _tokens(query)
        candidates: set[str] = set()
        for token in query_tokens:
            candidates |= self._postings.get(token, set())

        if self._static is None or self._static_stamp != (self.clock, self.model.updates):
            self._static_scores()
        rest = self._rest
        weight = self.model.weights["relevance"]
        candidate_scores: list[tuple[float, MemoryEntry]] = []
        append = candidate_scores.append
        for entry_id in candidates:
            entry = self.entries.get(entry_id)
            if entry is None or entry.retired:
                continue
            if kind is not None and entry.kind != kind:
                continue
            tokens = self._entry_tokens.get(entry_id)
            if tokens is None:
                features = entry.salience_features(self.clock, query_tokens, self.half_life)
                score = self.model.score(features)
            else:
                union = tokens | query_tokens
                relevance = (len(tokens & query_tokens) / len(union)) if union else 0.0
                score = rest.get(entry_id, 0.0) + weight * relevance
            append((score, entry))
        if len(candidate_scores) > k:
            scored = heapq.nlargest(k, candidate_scores, key=lambda item: (item[0], item[1].entry_id))
        else:
            scored = candidate_scores
        scored.sort(key=lambda item: (-item[0], item[1].entry_id))

        # Entries that share no token with the query have relevance exactly 0,
        # so their score is the query-independent number kept sorted above.
        # Merge them in until the worst kept score wins.
        for score, entry_id in self._static_scores():
            if len(scored) == k and (-scored[-1][0], scored[-1][1].entry_id) <= (-score, entry_id):
                break
            if entry_id in candidates:
                continue
            entry = self.entries[entry_id]
            if kind is not None and entry.kind != kind:
                continue
            scored.append((score, entry))
            scored.sort(key=lambda item: (-item[0], item[1].entry_id))
            scored = scored[:k]
        return scored

    def record_retrieval(self, query: str, entry_id: str, *, success: bool) -> None:
        entry = self.entries[entry_id]
        features = entry.salience_features(
            self.clock, _tokens(query), self.half_life,
            tokens=self._entry_tokens.get(entry_id),
        )
        self.model.learn(features, 1 if success else 0)
        self._invalidate()
        self.retrieval_log.append(
            {"clock": self.clock, "query": query, "entry_id": entry_id, "success": bool(success)}
        )

    # -- compression ------------------------------------------------------
    def consolidate(self, *, similarity: float = 0.92) -> dict[str, int]:
        """Merge near-duplicate episodes and retire superseded successes.

        Keeps the most informative member of each cluster (highest surprise /
        failure count), sums the evidence, and leaves the retrieval set no
        worse.  No entry is deleted; it is retired with its payload intact.
        """
        merged = 0
        retired = 0
        episodes = [e for e in self.entries.values() if e.kind == "episode" and not e.retired]
        episodes.sort(key=lambda e: (-e.surprise, -e.failures, e.entry_id))
        kept: list[MemoryEntry] = []
        for entry in episodes:
            duplicate = None
            tokens = _tokens(entry.text)
            for other in kept:
                other_tokens = _tokens(other.text)
                union = tokens | other_tokens
                if union and len(tokens & other_tokens) / len(union) >= similarity:
                    duplicate = other
                    break
            if duplicate is None:
                kept.append(entry)
                continue
            duplicate.uses += entry.uses
            duplicate.successes += entry.successes
            duplicate.failures += entry.failures
            duplicate.surprise = max(duplicate.surprise, entry.surprise)
            duplicate.cost_saved = max(duplicate.cost_saved, entry.cost_saved)
            entry.retired = True
            self._invalidate()
            merged += 1
            retired += 1

        # retire repeated low-information successes beyond the best two per skill
        by_skill: dict[str, list[MemoryEntry]] = {}
        for entry in kept:
            if entry.failures == 0 and entry.surprise <= 0.1:
                by_skill.setdefault(str(entry.payload.get("skill_id")), []).append(entry)
        for entries in by_skill.values():
            entries.sort(key=lambda e: (-e.successes, -e.last_used))
            for entry in entries[2:]:
                entry.retired = True
                self._invalidate()
                retired += 1
        return {"merged": merged, "retired": retired, "active": len(self.active())}

    def active(self) -> list[MemoryEntry]:
        return [e for e in self.entries.values() if not e.retired]

    def payload_bytes(self, *, active_only: bool = True) -> int:
        """Working-set size: what retrieval must scan.

        Retired entries are cold storage (``archived_bytes``); keeping them out
        of this number is what makes consolidation a measurable compression
        instead of a bookkeeping flag that changes nothing.
        """
        body = [
            e.to_dict()
            for e in self.entries.values()
            if not (active_only and e.retired)
        ]
        return len(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())

    def archived_bytes(self) -> int:
        body = [e.to_dict() for e in self.entries.values() if e.retired]
        return len(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA + "_MEMORY",
            "clock": self.clock,
            "entries": [e.to_dict() for e in self.entries.values()],
            "salience": self.model.to_dict(),
            "retrieval_log": list(self.retrieval_log),
            "bytes": self.payload_bytes(),
            "archived_bytes": self.archived_bytes(),
            "active": len(self.active()),
        }


__all__ = [
    "SCHEMA",
    "LivingCoreError",
    "Table",
    "fmt_value",
    "parse_number",
    "table_from_csv",
    "table_from_rows",
    "expr_to_json",
    "expr_from_json",
    "program_to_json",
    "program_from_json",
    "apply_program",
    "infer_expressions",
    "synthesize",
    "induce",
    "simplest_program",
    "InductionResult",
    "SalienceModel",
    "Memory",
    "DecisionList",
    "expr_columns",
    "induce_rule",
    "induce_decisions",
    "MemoryEntry",
]
