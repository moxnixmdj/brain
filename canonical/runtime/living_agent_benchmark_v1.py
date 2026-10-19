"""Living-agent benchmark: black-box tasks with independently written oracles.

Every task here is a *transformation* with an exact expected output.  The
oracle functions are written independently of the learner (no import from
``living_core_v1`` except for the plain ``Table`` container) and are never
shown to it.  Held-out instances come from a frozen RNG stream that the learner
never sees, so passing means the induced program generalizes, not that it
memorized the demonstrations.

The twelve table families mirror ordinary spreadsheet requests.  In addition,
``real_tree_table`` projects the repository's real file tree (name, extension,
directory, byte size) so the same learner can be measured on data nobody
fabricated.
"""
from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.living_core_v1 import Table, fmt_value, parse_number, table_from_rows

SCHEMA = "PROJECT_BRAIN_LIVING_AGENT_BENCHMARK_V1"


def _num(value: float) -> str:
    return fmt_value(value)


def _is_number(value: str) -> bool:
    try:
        parse_number(value)
    except (TypeError, ValueError):
        return False
    return True


def _table(columns: Sequence[str], rows: Sequence[Mapping[str, str]]) -> Table:
    return table_from_rows(columns, rows)


# --------------------------------------------------------------------------- #
# hidden oracles                                                              #
# --------------------------------------------------------------------------- #


def oracle_filter_sort(t: Table) -> Table:
    rows = [dict(r) for r in t.rows if float(r["score"]) > 70]
    rows.sort(key=lambda r: -float(r["score"]))
    return _table(["name", "score"], rows)


def oracle_raise(t: Table) -> Table:
    rows = [
        {"name": r["name"], "new_salary": _num(round(float(r["salary"]) * 1.1, 2))}
        for r in t.rows
    ]
    rows.sort(key=lambda r: r["name"])
    return _table(["name", "new_salary"], rows)


def oracle_group_sum(t: Table) -> Table:
    totals: dict[str, float] = {}
    for r in t.rows:
        totals[r["dept"]] = totals.get(r["dept"], 0.0) + float(r["salary"])
    rows = [{"dept": k, "total": _num(v)} for k, v in totals.items()]
    rows.sort(key=lambda r: -float(r["total"]))
    return _table(["dept", "total"], rows)


def oracle_month_counts(t: Table) -> Table:
    counts: dict[int, int] = {}
    for r in t.rows:
        month = int(r["date"][5:7])
        counts[month] = counts.get(month, 0) + 1
    return _table(
        ["month", "n"], [{"month": str(k), "n": str(v)} for k, v in sorted(counts.items())]
    )


def oracle_unit_price(t: Table) -> Table:
    rows = []
    for r in t.rows:
        unit = round(float(r["total"]) / float(r["qty"]), 2)
        if unit > 10:
            rows.append({"sku": r["sku"], "unit": _num(unit)})
    rows.sort(key=lambda r: -float(r["unit"]))
    return _table(["sku", "unit"], rows)


def oracle_top2(t: Table) -> Table:
    rows = [dict(r) for r in t.rows]
    rows.sort(key=lambda r: -float(r["score"]))
    return _table(["name", "score"], rows[:2])


def oracle_domains(t: Table) -> Table:
    counts: dict[str, int] = {}
    for r in t.rows:
        domain = r["email"].split("@")[1].lower()
        counts[domain] = counts.get(domain, 0) + 1
    return _table(
        ["domain", "n"], [{"domain": k, "n": str(v)} for k, v in sorted(counts.items())]
    )


def oracle_dedupe(t: Table) -> Table:
    seen: set[str] = set()
    rows = []
    for r in t.rows:
        if r["email"] in seen:
            continue
        seen.add(r["email"])
        rows.append({"email": r["email"], "name": r["name"]})
    return _table(["email", "name"], rows)


def oracle_active(t: Table) -> Table:
    rows = [
        {"id": r["id"], "name": r["name"].lower()}
        for r in t.rows
        if r["status"] == "active"
    ]
    # A total order: numeric identifiers first (by value), text after.  A
    # mixed-key sort would raise on a legitimate probe such as id = -1.
    rows.sort(
        key=lambda r: (0, float(r["id"]), "") if _is_number(r["id"]) else (1, 0.0, r["id"])
    )
    return _table(["id", "name"], rows)


def oracle_tax(t: Table) -> Table:
    rows = []
    for r in t.rows:
        total = round(
            float(r["price"]) * float(r["qty"]) * (1 + float(r["rate"]) / 100.0), 2
        )
        rows.append({"sku": r["sku"], "total": _num(total)})
    rows.sort(key=lambda r: -float(r["total"]))
    return _table(["sku", "total"], rows)


def oracle_pct(t: Table) -> Table:
    rows = []
    for r in t.rows:
        before = float(r["before"])
        after = float(r["after"])
        pct = round((after - before) / before * 100.0, 2)
        if pct > 0:
            rows.append({"id": r["id"], "pct": _num(pct)})
    rows.sort(key=lambda r: -float(r["pct"]))
    return _table(["id", "pct"], rows)


def oracle_concat(t: Table) -> Table:
    rows = [
        {"full": (r["first"] + " " + r["last"]).strip(), "city": r["city"].upper()}
        for r in t.rows
    ]
    rows.sort(key=lambda r: r["full"])
    return _table(["full", "city"], rows)


FAMILIES: dict[str, dict[str, Any]] = {
    "filter_sort": {
        "columns": ["name", "score"],
        "spec": {
            "name": ["alice", "bob", "carol", "dave", "erin", "frank", "grace", "heidi"],
            "score": [10, 25, 40, 55, 62, 68, 71, 75, 80, 88, 91, 99],
        },
        "oracle": oracle_filter_sort,
    },
    "raise": {
        "columns": ["name", "salary"],
        "spec": {
            "name": ["alice", "bob", "carol", "dave", "erin"],
            "salary": [30000, 42000, 55500, 61000, 72000, 88000],
        },
        "oracle": oracle_raise,
    },
    "group_sum": {
        "columns": ["dept", "salary"],
        "spec": {
            "dept": ["eng", "sales", "ops", "hr"],
            "salary": [30000, 42000, 55500, 61000, 72000, 88000],
        },
        "oracle": oracle_group_sum,
    },
    "month_counts": {
        "columns": ["date"],
        "spec": {
            "date": [
                "2024-01-05", "2024-02-11", "2024-02-19", "2024-03-02",
                "2024-03-15", "2024-03-28", "2024-04-09",
            ]
        },
        "oracle": oracle_month_counts,
    },
    "unit_price": {
        "columns": ["sku", "qty", "total"],
        "spec": {
            "sku": ["a1", "b2", "c3", "d4", "e5", "f6"],
            "qty": [1, 2, 3, 4, 5, 6],
            "total": [12, 25, 31, 44, 58, 72],
        },
        "oracle": oracle_unit_price,
    },
    "top2": {
        "columns": ["name", "score"],
        "spec": {
            "name": ["alice", "bob", "carol", "dave", "erin", "frank"],
            "score": [10, 25, 40, 55, 62, 68, 71, 75, 80, 88, 91, 99],
        },
        "oracle": oracle_top2,
    },
    "domains": {
        "columns": ["email"],
        "spec": {
            "email": ["a@x.com", "b@y.org", "c@x.com", "d@z.net", "e@y.org", "f@x.com", "g@W.org"]
        },
        "oracle": oracle_domains,
    },
    "dedupe": {
        "columns": ["email", "name"],
        "spec": {
            "email": ["a@x.com", "b@y.org", "a@x.com", "c@z.net", "b@y.org", "d@x.com"],
            "name": ["a", "b", "c", "d", "e", "f"],
        },
        "oracle": oracle_dedupe,
    },
    "active": {
        "columns": ["id", "name", "status"],
        "spec": {
            "id": [1, 2, 3, 4, 5, 6],
            "name": ["Al", "Bo", "Cy", "Di", "Ed", "Fi"],
            "status": ["active", "inactive", "active", "active", "inactive", "active"],
        },
        "oracle": oracle_active,
    },
    "tax": {
        "columns": ["sku", "price", "qty", "rate"],
        "spec": {
            "sku": ["a", "b", "c", "d", "e"],
            "price": [5.5, 12.0, 7.25, 20.0, 3.75],
            "qty": [1, 2, 3, 4, 5],
            "rate": [5, 8, 10, 0, 20],
        },
        "oracle": oracle_tax,
    },
    "pct": {
        "columns": ["id", "before", "after"],
        "spec": {
            "id": [1, 2, 3, 4, 5, 6],
            "before": [100, 200, 50, 80, 120, 60],
            "after": [110, 180, 75, 90, 140, 55],
        },
        "oracle": oracle_pct,
    },
    "concat": {
        "columns": ["first", "last", "city"],
        "spec": {
            "first": ["ann", "bob", "cy", "dana", "eli"],
            "last": ["lee", "kim", "ng", "po", "wu"],
            "city": ["paris", "berlin", "oslo", "rome", "kyiv"],
        },
        "oracle": oracle_concat,
    },
}


def generate_instance(family: str, rng: random.Random) -> Table:
    spec = FAMILIES[family]
    columns = list(spec["columns"])
    rows = []
    for _ in range(rng.randint(3, 7)):
        rows.append({c: str(rng.choice(spec["spec"][c])) for c in columns})
    return _table(columns, rows)


def covering_instance(family: str, rng: random.Random) -> Table:
    """A demonstration that shows one example of every categorical value.

    Few-shot learning is only well posed if the demonstration exhibits the
    vocabulary: no learner can infer that domains are lower-cased from data
    that never contains a capital letter.  Numeric columns are sampled
    randomly, so threshold placement is still the learner's problem.
    """
    spec = FAMILIES[family]
    columns = list(spec["columns"])
    values = {c: list(dict.fromkeys(str(v) for v in spec["spec"][c])) for c in columns}
    rows_needed = max(rng.randint(4, 8), max(len(v) for v in values.values()))
    rows = []
    for i in range(rows_needed):
        rows.append({c: values[c][i % len(values[c])] for c in columns})
    return _table(columns, rows)


class InvalidInstance(Exception):
    """Raised by the oracle when a random instance is outside the task domain."""


def guarded_oracle(family: str) -> Callable[[Table], Table | None]:
    oracle = FAMILIES[family]["oracle"]

    def query(table: Table) -> Table | None:
        try:
            return oracle(table)
        except (ZeroDivisionError, ValueError, TypeError, KeyError, OverflowError):
            # An oracle that cannot answer a probe means the probe is outside
            # the task domain; the learner must be told "no answer", not
            # allowed to crash a query loop.
            return None

    return query


# --------------------------------------------------------------------------- #
# real file-tree projection                                                   #
# --------------------------------------------------------------------------- #


def real_tree_table(root: str | Path, pattern: str = "*.py", limit: int = 400) -> Table:
    """Project a real directory tree into a table (name, ext, dir, size)."""
    root = Path(root)
    rows = []
    count = 0
    for path in sorted(root.rglob(pattern)):
        if not path.is_file():
            continue
        stat = path.stat()
        rows.append(
            {
                "name": path.name,
                "ext": path.suffix.lstrip(".") or "none",
                "dir": str(path.parent.relative_to(root)) or ".",
                "size": str(stat.st_size),
            }
        )
        count += 1
        if count >= limit:
            break
    return _table(["name", "ext", "dir", "size"], rows)


def oracle_large_files(t: Table) -> Table:
    rows = [
        {"name": r["name"], "size": r["size"]}
        for r in t.rows
        if int(r["size"]) > 20000
    ]
    rows.sort(key=lambda r: -int(r["size"]))
    return _table(["name", "size"], rows)


def oracle_bytes_by_ext(t: Table) -> Table:
    totals: dict[str, int] = {}
    for r in t.rows:
        totals[r["ext"]] = totals.get(r["ext"], 0) + int(r["size"])
    return _table(
        ["ext", "total"],
        [
            {"ext": k, "total": str(v)}
            for k, v in sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
    )


REAL_TASKS: dict[str, dict[str, Any]] = {
    "large_files": {"oracle": oracle_large_files},
    "bytes_by_ext": {"oracle": oracle_bytes_by_ext},
}


__all__ = [
    "SCHEMA",
    "FAMILIES",
    "REAL_TASKS",
    "generate_instance",
    "covering_instance",
    "guarded_oracle",
    "real_tree_table",
]
