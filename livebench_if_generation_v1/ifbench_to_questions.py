#!/usr/bin/env python3
"""Convert allenai/IFBench ``data/IFBench_test.jsonl`` into the kit's questions format.

PROVISIONAL tooling. Purpose: a NON-FROZEN development proxy for LiveBench IF. LiveBench's current
IF questions are scored with the same 58 IFBench checker types, so these 300 public prompts exercise
every checker, although each prompt carries fewer constraints (about 1.15 on average, against about 3
for LiveBench) and has no article wrapper.

Licenses: IFBench code is Apache-2.0; its data is ODC-BY-1.0 (research and educational use,
attribution required). Source: https://github.com/allenai/IFBench
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REQUIRED = ("key", "prompt", "instruction_id_list", "kwargs")


def convert(rows: Sequence[Mapping[str, Any]], task: str = "ifbench_test") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[Any] = set()
    for i, row in enumerate(rows):
        for field in REQUIRED:
            if field not in row:
                raise ValueError(f"row {i} lacks {field!r}")
        key = row["key"]
        if key in seen:
            raise ValueError(f"duplicate key {key!r}")
        seen.add(key)
        ids, kwargs = row["instruction_id_list"], row["kwargs"]
        if not isinstance(ids, list) or not isinstance(kwargs, list) or len(ids) != len(kwargs) or not ids:
            raise ValueError(f"row {i}: instruction_id_list and kwargs must be equal-length non-empty lists")
        if not isinstance(row["prompt"], str) or not row["prompt"].strip():
            raise ValueError(f"row {i}: empty prompt")
        out.append({"question_id": f"ifbench-{key}", "task": task, "turns": [row["prompt"]],
                    "instruction_id_list": ids, "kwargs": kwargs})
    return out


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--task", default="ifbench_test")
    args = ap.parse_args(argv)
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    try:
        converted = convert(rows, args.task)
    except ValueError as exc:
        print(f"BLOCKED {exc}", file=sys.stderr)
        return 2
    args.output.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in converted) + "\n", encoding="utf-8")
    print(json.dumps({"converted": len(converted)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
