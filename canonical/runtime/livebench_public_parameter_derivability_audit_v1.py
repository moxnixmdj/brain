#!/usr/bin/env python3
"""Audit public IFBench prompt/hidden-parameter derivability without terminal data."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_PUBLIC_PARAMETER_AUDIT_V1"

def norm_ws(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()

def analyze(rows: list[dict]) -> dict:
    overlap = {"instruction_rows": 0, "raw_reference_visible": 0, "normalized_reference_visible": 0}
    repeat = {"instruction_rows": 0, "raw_prompt_visible": 0, "score_relevant_slice_equal": 0}
    for row in rows:
        prompt = str(row.get("prompt") or "")
        ids = list(row.get("instruction_id_list") or [])
        kwargs = list(row.get("kwargs") or [])
        for index, instruction_id in enumerate(ids):
            kw = kwargs[index] if index < len(kwargs) and isinstance(kwargs[index], dict) else {}
            if instruction_id == "ratio:overlap":
                overlap["instruction_rows"] += 1
                reference = str(kw.get("reference_text") or "")
                if reference and reference in prompt:
                    overlap["raw_reference_visible"] += 1
                if reference and norm_ws(reference) in norm_ws(prompt):
                    overlap["normalized_reference_visible"] += 1
            if instruction_id == "repeat:repeat_span":
                repeat["instruction_rows"] += 1
                source = str(kw.get("prompt_to_repeat") or "")
                if source and source in prompt:
                    repeat["raw_prompt_visible"] += 1
                start, end = kw.get("n_start"), kw.get("n_end")
                if isinstance(start, (int, float)) and isinstance(end, (int, float)):
                    start, end = int(start), int(end)
                    suffix = (
                        f"Copy the span of words that lies between (and including) index {start} and {end}, "
                        "the indices are word indices, split by whitespace!"
                    )
                    if prompt.endswith(suffix):
                        visible_base = prompt[:-len(suffix)].rstrip()
                        visible_words = re.findall(r"\S+", visible_base)
                        source_words = re.findall(r"\S+", source)
                        if visible_words[start:end + 1] == source_words[start:end + 1]:
                            repeat["score_relevant_slice_equal"] += 1
    return {
        "schema": SCHEMA,
        "rows": len(rows),
        "ratio_overlap": overlap,
        "repeat_span": repeat,
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl")
    ns = ap.parse_args()
    rows = [json.loads(line) for line in Path(ns.jsonl).read_text(encoding="utf-8").splitlines() if line.strip()]
    result = analyze(rows)
    print(json.dumps(result, sort_keys=True))
    expected = {
        "rows": 300,
        "ratio_overlap": {"instruction_rows": 12, "raw_reference_visible": 5, "normalized_reference_visible": 12},
        "repeat_span": {"instruction_rows": 4, "raw_prompt_visible": 3, "score_relevant_slice_equal": 4},
    }
    for key, value in expected.items():
        if result[key] != value:
            raise SystemExit(f"AUDIT_MISMATCH:{key}:{result[key]!r}!={value!r}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
