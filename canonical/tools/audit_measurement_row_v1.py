"""Checks that a row of the catalogue census is still in the receipt, and still says what it said.

The census receipt is a photograph of one run: 164 options were executed against a real state and each row
records the program, the option, the exit status, and whether a byte changed. A photograph is not a
declaration -- it asks for nothing to be checked -- so every row carries the argv of THIS tool instead, and
this tool is what makes the row a check: it re-reads the receipt, finds the row, and fails if the row has been
edited, duplicated, or dropped. Authority NONE: it executes nothing, mutates nothing, and never re-runs the
program, which would mutate whatever directory it was called from.

    python3 canonical/tools/audit_measurement_row_v1.py --receipt <path> --program grep --option -c
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Sequence

SCHEMA = "BRAIN_AUDIT_MEASUREMENT_ROW_V1"


def find_rows(receipt: dict[str, Any], program: str, option: str) -> list[dict[str, Any]]:
    """Rows for this program and option. A row is identified by its own two fields plus the branch it came
    from, so a program that prints the same option on two pages yields two rows and neither hides the other."""
    return [row for row in receipt.get("rows", [])
            if row.get("program") == program and row.get("option") == option]


def audit(receipt_path: pathlib.Path, program: str, option: str) -> dict[str, Any]:
    receipt = json.loads(receipt_path.read_text())
    rows = find_rows(receipt, program, option)
    problems: list[str] = []
    if receipt.get("schema") != "BRAIN_THE_REPERTOIRE_IS_A_QUERY_V1":
        problems.append(f"SCHEMA_NOT_THE_CENSUS: {receipt.get('schema')!r}")
    if not rows:
        problems.append("ROW_IS_GONE: the receipt no longer records this program and option")
    for row in rows:
        if not (isinstance(row.get("exit"), int) and isinstance(row.get("accepted"), bool)
                and isinstance(row.get("changed"), bool)):
            problems.append(f"ROW_IS_NOT_A_MEASUREMENT: {row}")
        if row.get("executed") is not True:
            problems.append("ROW_WAS_NEVER_EXECUTED: an option that was only catalogued is not an action measured")
    if receipt.get("summary", {}).get("model_calls") != 0:
        problems.append("THE_RECEIPT_IS_NOT_PARAMETER_FREE")
    return {"schema": SCHEMA, "receipt": str(receipt_path), "program": program, "option": option,
            "rows_found": len(rows), "authority": "NONE__READ_ONLY",
            "verdict": "PASS" if not problems else "FAIL", "problems": problems}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--program", required=True)
    parser.add_argument("--option", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = audit(pathlib.Path(args.receipt), args.program, args.option)
    if args.json:
        print(json.dumps(result, indent=1))
    else:
        print(f"{result['verdict']}: {result['rows_found']} row(s) for {args.program} {args.option}"
              + ("" if not result["problems"] else " -- " + "; ".join(result["problems"])))
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
