"""How much does the failing test actually tell us about the fix?

THE QUESTION
------------
Every repair arm in this tree treats the failing test as the oracle: run it, and it says pass or
fail. That is a one-bit channel. The corpus was built so that the test FAILS at ``before`` and
PASSES at ``after`` -- which proves the oracle separates those two points. It does not prove the
oracle separates ``after`` from the *neighbourhood* of ``after``.

That distinction decides where the next unit of effort goes, so it is worth measuring directly:

* If almost no mutant of the real fix survives, the oracle is sharp. Then a search that reaches the
  right neighbourhood will be *identified* as right, and the bottleneck is reach (the generator).
* If many mutants survive, the oracle is blunt. Then search is futile in a specific way: many wrong
  edits look identical to the right one under the test, so a solver can reach the neighbourhood and
  still ship a wrong patch -- and its own internal check will say PASS.

The second outcome would explain, mechanistically, the one result this project has from a real
board: on SWE-bench Pro V2 the engine wrote 3 patches, called all 3 ``PASS`` itself, and the tasks'
own verifiers scored all 3 at 0.0.

WHAT THIS DOES
--------------
For each well-formed task: check out the fix commit, write ``after`` (the real fix), confirm the
failing tests pass, then mutate ONLY the lines the upstream fix changed and re-run the same tests.
A mutant that still passes is a wrong edit the oracle accepts. Nothing here is a solve attempt and
no mutant is counted as a repair; this measures the oracle, not the engine.

    python3 canonical/tools/oracle_discriminating_power_v1.py --limit 8 --mutants 10
"""
from __future__ import annotations

import argparse
import difflib
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from real_fix_oracle_baseline_v1 import Oracle  # noqa: E402

CORPUS = pathlib.Path("canonical/corpus/real_fix_pairs_20261119_V1.json")

# --- the mutation set: small, semantic, and aimed at the fix's own lines ------------- #
_CMP = [("<=", ">="), (">=", "<="), ("<", ">"), (">", "<"), ("==", "!="), ("!=", "=="),
        ("<", "<="), (">=", ">"), (">", ">="), ("<=", "<")]
_NUM = re.compile(r"(?<![\w.])(\d+)(?![\w.])")


def _cmp_mutants(line: str):
    for a, b in _CMP:
        if a in line:
            yield f"cmp:{a}->{b}", line.replace(a, b, 1)


def _bool_mutants(line: str):
    if "True" in line:
        yield "bool:True->False", line.replace("True", "False", 1)
    if "False" in line:
        yield "bool:False->True", line.replace("False", "True", 1)


def _logic_mutants(line: str):
    if " and " in line:
        yield "logic:and->or", line.replace(" and ", " or ", 1)
    if " or " in line:
        yield "logic:or->and", line.replace(" or ", " and ", 1)


def _none_mutants(line: str):
    if "is None" in line:
        yield "none:is->isnot", line.replace("is None", "is not None", 1)
    if "is not None" in line:
        yield "none:isnot->is", line.replace("is not None", "is None", 1)


def _num_mutants(line: str):
    m = _NUM.search(line)
    if m:
        v = int(m.group(1))
        for d in (1, -1):
            yield f"num:{v}->{v + d}", line[:m.start()] + str(v + d) + line[m.end():]


OPERATORS = (_cmp_mutants, _bool_mutants, _logic_mutants, _none_mutants, _num_mutants)


def changed_lines(before: str, after: str) -> list[int]:
    """1-based line numbers in ``after`` that the upstream fix added or modified."""
    sm = difflib.SequenceMatcher(None, before.splitlines(), after.splitlines(), autojunk=False)
    out: set[int] = set()
    for tag, _i1, _i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            out.update(range(j1 + 1, j2 + 1))
    return sorted(out)


def mutants_of(after: str, lines: list[int], cap: int) -> list[tuple[str, str]]:
    src = after.splitlines(keepends=True)
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    # round-robin over operators so one busy line cannot consume the whole budget
    per_line = {n: [m for op in OPERATORS for m in op(src[n - 1].rstrip("\n"))] for n in lines}
    for depth in range(max((len(v) for v in per_line.values()), default=0)):
        for n in lines:
            if depth >= len(per_line[n]):
                continue
            name, new = per_line[n][depth]
            body = "".join(src[: n - 1] + [new + "\n"] + src[n:])
            if name in seen or body == after:
                continue
            seen.add(name)
            out.append((name, body))
            if len(out) >= cap:
                return out
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--mutants", type=int, default=10)
    ap.add_argument("--workdir", default="/tmp/real")
    ap.add_argument("--out", default="/tmp/oracle_power.json")
    a = ap.parse_args(argv)

    tasks = json.loads(CORPUS.read_text())["tasks"][a.offset:]
    workdir = pathlib.Path(a.workdir)
    oracles: dict[str, Oracle] = {}
    rows: list[dict] = []

    for t in tasks[: a.limit]:
        slug = t["repo"]
        if slug not in oracles:
            oracles[slug] = Oracle(slug, workdir)
            if not oracles[slug].ensure().get("ok"):
                rows.append({"repo": slug, "sha": t["sha"][:10], "well_formed": False,
                             "reason": "ENV_UNAVAILABLE"})
                continue
        o = oracles[slug]
        row = {"repo": slug, "sha": t["sha"][:10], "source": t["source"],
               "nodes": len(t["failed_nodes"] or [])}
        try:
            o.checkout(t["sha"])
            o.write_source(t["source"], t["before"])
            if o.test(t["failed_nodes"])["passed"] is not False:
                row.update(well_formed=False, reason="BEFORE_PASSES")
                rows.append(row)
                continue
            o.write_source(t["source"], t["after"])
            if o.test(t["failed_nodes"])["passed"] is not True:
                row.update(well_formed=False, reason="AFTER_FAILS")
                rows.append(row)
                continue

            lines = changed_lines(t["before"], t["after"])
            muts = mutants_of(t["after"], lines, a.mutants)
            survived: list[str] = []
            for name, body in muts:
                o.write_source(t["source"], body)
                if o.test(t["failed_nodes"])["passed"] is True:
                    survived.append(name)
            o.write_source(t["source"], t["after"])
            row.update(well_formed=True, changed_lines=len(lines), mutants=len(muts),
                       survived=len(survived),
                       survival_rate=round(len(survived) / len(muts), 4) if muts else None,
                       survivors=survived)
        except Exception as exc:  # noqa: BLE001
            row.update(well_formed=False, reason=f"HARNESS_{type(exc).__name__}")
        rows.append(row)
        print(f"  {row['repo']:22s} {row['sha']} lines={row.get('changed_lines')} "
              f"mutants={row.get('mutants')} survived={row.get('survived')} "
              f"rate={row.get('survival_rate')} {row.get('reason', '')}", flush=True)

    ok = [r for r in rows if r.get("well_formed")]
    tm = sum(r["mutants"] for r in ok)
    ts = sum(r["survived"] for r in ok)
    summary = {
        "schema": "PROJECT_BRAIN_ORACLE_DISCRIMINATING_POWER_V1",
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "note": ("measures the oracle, not the engine: a surviving mutant is a WRONG edit the "
                 "failing test accepts. No mutant is a solve and none may be counted as one."),
        "tasks_ok": len(ok), "tasks_tried": len(rows),
        "mutants_total": tm, "mutants_survived": ts,
        "survival_rate": round(ts / tm, 4) if tm else None,
        "per_task_zero_survival": sum(1 for r in ok if r["survived"] == 0),
        "rows": rows,
    }
    pathlib.Path(a.out).write_text(json.dumps(summary, indent=1))
    print(f"\n== {len(ok)} tasks | {tm} mutants of the real fix | {ts} SURVIVED the failing test "
          f"| survival {summary['survival_rate']} | tasks with zero survival: "
          f"{summary['per_task_zero_survival']}/{len(ok)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
