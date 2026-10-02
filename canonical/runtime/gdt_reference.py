"""Deterministic bounded lookup for pinned GD&T symbols and modifiers.

This module recognizes only exact Unicode symbols present in the pinned CC0
reference slice. It does not infer full feature-control-frame semantics,
drawing geometry, or unstated standard rules.
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Any

SCHEMA = "BRAIN_GDT_REFERENCE_LOOKUP_V1"

_BASE = (
    Path(__file__).resolve().parents[1]
    / "capabilities"
    / "internalized"
    / "engineering_reference_data"
    / "dbe1df06"
    / "data"
)


@lru_cache(maxsize=1)
def _symbols() -> list[dict[str, str]]:
    with (_BASE / "gdt-symbols.csv").open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


@lru_cache(maxsize=1)
def _modifiers() -> list[dict[str, str]]:
    with (_BASE / "gdt-modifiers.csv").open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def lookup_gdt_symbol(symbol: str, *, standard: str | None = None) -> dict[str, Any]:
    if not isinstance(symbol, str) or len(symbol) != 1:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "EXPECTED_SINGLE_SYMBOL"}

    for row in _symbols():
        if row["symbol"] != symbol:
            continue
        out: dict[str, Any] = {
            "schema": SCHEMA,
            "status": "MATCH",
            "kind": "CHARACTERISTIC",
            "record": dict(row),
            "terminal_authority": False,
        }
        if standard is not None:
            key = {
                "ASME_Y14_5_2018": "asme_y14_5_2018",
                "ISO_1101": "iso_1101",
            }.get(standard.upper())
            if key is None:
                return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "UNSUPPORTED_STANDARD"}
            out["standard"] = standard.upper()
            out["standard_status"] = row[key]
        return out

    for row in _modifiers():
        if row["symbol"] == symbol:
            return {
                "schema": SCHEMA,
                "status": "MATCH",
                "kind": "MODIFIER",
                "record": dict(row),
                "terminal_authority": False,
            }

    return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "UNKNOWN_SYMBOL"}


def extract_known_gdt_tokens(text: str) -> dict[str, Any]:
    if not isinstance(text, str):
        raise ValueError("text must be str")

    symbol_map = {row["symbol"]: ("CHARACTERISTIC", row) for row in _symbols()}
    modifier_map = {row["symbol"]: ("MODIFIER", row) for row in _modifiers()}
    found: list[dict[str, Any]] = []
    for index, ch in enumerate(text):
        hit = symbol_map.get(ch) or modifier_map.get(ch)
        if hit is None:
            continue
        kind, row = hit
        found.append({
            "index": index,
            "symbol": ch,
            "kind": kind,
            "name": row.get("characteristic") or row.get("modifier"),
        })

    return {
        "schema": SCHEMA,
        "status": "PARSED",
        "tokens": found,
        "count": len(found),
        "terminal_authority": False,
        "scope": "EXACT_PINNED_UNICODE_GDT_CHARACTERISTIC_AND_MODIFIER_RECOGNITION_ONLY",
    }
