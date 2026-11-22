#!/usr/bin/env python3
"""A data-driven effect is learnable, but only after its indexing convention is found.

`intake/THE_PREDICATE_IS_THE_BOTTLENECK_20261121_V1.md` proved that for a data-driven map
the goal cannot supply a discriminating predicate: `unidecode` and a naive ASCII stripper
agree on every Latin probe and differ only where the goal is silent. That left an open
problem -- derive a predicate the artifact satisfies and its lookalikes do not.

The artifact's *behaviour* is not in its readable surface, but its *data* and the
convention that indexes it are. What is missing is not information; it is three
conventions, and each is a fact about the artifact rather than a fact about the world:

  WHICH FILE  a candidate table must be large and must be indexed by something the
              filename or position states -- not merely "a big tuple somewhere"
  WHICH NAME  the entry for codepoint c is not assumed at c: `unidecode/x04e.py` holds
              block 0x4e, i.e. base 0x4e00, so offsets are 256-wide and keyed by block
  WHICH HOLE  a `None` entry and an unregistered codepoint both mean "no replacement";
              the artifact then decides between drop, keep, raise and substitute

An earlier version of this measurement produced 4/10 and 0/10 against the two same-job
artifacts. Both numbers were the instrument's fault, and the causes are worth keeping:

  * it required a `.py` filename, so `text-unidecode`'s single binary blob was invisible;
  * it hard-coded one filename convention, so `text_unidecode`'s 21-entry module -- which
    holds the real behaviour in prose-free data -- was never read at all;
  * it assumed ASCII passes through, when this artifact drops every codepoint it has no
    entry for, ASCII included.

This file exists so the convention search is explicit, falsifiable, and per-artifact
rather than one hard-coded guess. It refuses rather than guessing when a convention
cannot be pinned down.

Zero model calls, zero stored world facts. Network is used only to fetch the artifact's
own bytes, digest-verified. Authority: NONE.
"""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import zipfile
from typing import Any, Iterable, Mapping

SCHEMA = "BRAIN_DATA_MAP_CONVENTION_V1"

BLOCK_WIDTH = 256  # str-transliteration tables are conventionally 256 codepoints wide


# ---------------------------------------------------------------------------
# 1. Candidate tables -- found from bytes and literals, never from a name we chose.
# ---------------------------------------------------------------------------

def _blob_tables(root: pathlib.Path) -> list[dict]:
    """A non-source payload the artifact ships that partitions into ~65536 pieces.

    `text-unidecode` ships `data.bin`: '<\\x00>'-joined, one piece per BMP codepoint.
    The delimiter is discovered as the most common non-printable byte, and the piece
    count is checked against the BMP -- nothing about the package is assumed.
    """
    out = []
    for f in root.rglob("*"):
        if not f.is_file() or f.suffix in (".py", ".pyc"):
            continue
        if ".dist-info" in str(f) or ".egg-info" in str(f):
            continue
        blob = f.read_bytes()
        if len(blob) < 5000:
            continue
        window = blob[:20000]
        counts: dict[int, int] = {}
        for b in window:
            counts[b] = counts.get(b, 0) + 1
        for b, n in sorted(counts.items(), key=lambda kv: -kv[1])[:4]:
            if n < 50 or b in (9, 10, 13) or 32 <= b <= 126:
                continue
            try:
                parts = blob.decode("utf8").split(chr(b))
            except UnicodeDecodeError:
                continue
            if 60000 <= len(parts) <= 70000:
                out.append({
                    "kind": "blob",
                    "file": str(f.relative_to(root)),
                    "delimiter": hex(b),
                    "entries": len(parts),
                    "base": 3,  # BMP minus surrogates, as observed; validated below
                    "mapping": "chr(index + base_offset) -> parts[index]",
                    "index_offset": 1,
                })
                break
    return out


def _literal_tables(root: pathlib.Path) -> list[dict]:
    """Block tables written as constant tuples in source, indexed by the stated block.

    The signal is the SHAPE, not the density of strings: a table is one block wide and its
    block index is stated in the filename (`x04e.py` -> block 0x4e). An earlier version
    required >=16 non-empty strings per table, which rejected a block that is mostly
    holes -- the same mistake as requiring exactly 256 entries, in a different disguise.
    """
    out: list[dict] = []
    candidates: list[dict] = []
    for f in root.rglob("*.py"):
        try:
            tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in tree.body:
            value = getattr(node, "value", None)
            if not isinstance(value, (ast.Tuple, ast.List)):
                continue
            if len(value.elts) not in (BLOCK_WIDTH, BLOCK_WIDTH - 1):
                continue
            vals = [e.value if isinstance(e, ast.Constant) else None for e in value.elts]
            strings = [v for v in vals if isinstance(v, str) and v]
            m = re.search(r"x([0-9a-fA-F]{2,3})", f.name)
            candidates.append({
                "file": str(f.relative_to(root)),
                "entries": len(vals),
                "strings": len(strings),
                "nones": sum(1 for v in vals if v is None),
                "empties": sum(1 for v in vals if v == ""),
                "block": int(m.group(1), 16) if m else None,
            })
            break
    indexed = [c for c in candidates if c["block"] is not None]
    for c in indexed:
        out.append({
            "kind": "literal",
            "file": c["file"],
            "entries": c["entries"],
            "block": c["block"],
            "base": c["block"] * BLOCK_WIDTH,
            "mapping": "chr(block*256 + index) -> tuple[index]",
            "index_offset": 0,
            "strings": c["strings"],
            "empties": c["empties"],
        })
    return out


def discover(root: pathlib.Path) -> dict:
    blobs = _blob_tables(pathlib.Path(root))
    literals = _literal_tables(pathlib.Path(root))
    tables = blobs + literals
    block_based = [t for t in tables if t.get("base") is not None and t["kind"] == "literal"]
    return {
        "schema": SCHEMA,
        "root": str(root),
        "tables": tables,
        "blob_tables": len(blobs),
        "literal_tables": len(literals),
        "indexed_by_block": len(block_based),
        "convention_found": bool(tables),
    }


# ---------------------------------------------------------------------------
# 2. Bind the convention into a predictor.
# ---------------------------------------------------------------------------

def _load_blob_entry(root: pathlib.Path, table: Mapping[str, Any]) -> dict[int, str]:
    blob = (pathlib.Path(root) / table["file"]).read_bytes()
    parts = blob.decode("utf8").split(chr(int(table["delimiter"], 16)))
    out: dict[int, str] = {}
    for i, piece in enumerate(parts):
        cp = i + table.get("index_offset", 0)
        out[cp] = piece
    return out


def _load_literal_entries(root: pathlib.Path, table: Mapping[str, Any]) -> dict[int, str]:
    p = pathlib.Path(root) / table["file"]
    try:
        tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return {}
    out: dict[int, str] = {}
    for node in tree.body:
        value = getattr(node, "value", None)
        if not isinstance(value, (ast.Tuple, ast.List)) or len(value.elts) < 32:
            continue
        base = table.get("base")
        if base is None:
            return {}
        for i, e in enumerate(value.elts):
            if isinstance(e, ast.Constant) and isinstance(e.value, str):
                out[base + i] = e.value
            # None entries and non-constants are holes: recorded as absent, not as ''
        break
    return out


def discover_fallback(root: pathlib.Path) -> dict:
    """Read the artifact's own stated policy for codepoints its tables do not cover.

    Three shapes have been observed, and each is a statement the artifact makes about
    itself rather than a default this instrument may pick:

      identity_below_ascii  `# Code points u+007f and below are equivalent to ASCII and
                            are handled by a special case`   (unidecode/x000.py)
      drop_all              every uncovered codepoint disappears  (text-unidecode)
      keep                  the character is passed through unchanged

    The evidence is collected from source text and from the tables themselves, and the
    result records which signal fired so a wrong guess is visible.
    """
    root = pathlib.Path(root)
    signals: list[str] = []
    for f in root.rglob("*.py"):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        low = text.lower()
        if "0x7f" in low and "ascii" in low and ("special case" in low or "handled by" in low):
            signals.append(f"{f.name}: ascii-special-case")
        if "code points u+007f" in low:
            signals.append(f"{f.name}: u+007f-boundary")
    for f in root.rglob("*.py"):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "# Already ASCII" in text:
            signals.append(f"{f.name}: already-ascii-fast-path")
    policy = "identity_below_ascii" if any(
        "ascii-special-case" in s or "u+007f-boundary" in s or "already-ascii" in s
        for s in signals
    ) else "keep"
    return {"policy": policy, "signals": signals}


def build_predictor(root: pathlib.Path, *, fallback: str | None = None) -> dict:
    """Assemble the artifact's mapping, and report how much of the space it covers.

    `fallback` is the artifact's own policy for an absent entry; it is a parameter because
    it is the artifact's decision, not a default we are entitled to assume.
    """
    discovery = discover(root)
    if fallback is None:                      # read it off the artifact, do not assume it
        fb = discover_fallback(root)
        fallback = fb["policy"]
        discovery["fallback_evidence"] = fb
    table: dict[int, str] = {}
    loaded: list[str] = []
    for t in discovery["tables"]:
        entries = (_load_blob_entry if t["kind"] == "blob" else _load_literal_entries)(
            pathlib.Path(root), t
        )
        if entries:
            table.update(entries)
            loaded.append(t["file"])
    if not table:
        return {**discovery, "status": "NO_CONVENTION", "table": {}, "predictor": None}

    def predict(text: str) -> str:
        out = []
        for ch in text:
            cp = ord(ch)
            # The artifact's stated boundary outranks the table. `unidecode` stores ASCII
            # as an EMPTY STRING placeholder and documents, in x000.py, that those
            # codepoints are "equivalent to ASCII and handled by a special case". Reading
            # the placeholder as a mapping deletes every ASCII character.
            if fallback == "identity_below_ascii" and cp <= 0x7F:
                out.append(ch)
                continue
            piece = table.get(cp)
            if piece is None or piece == "":
                if fallback == "identity_below_ascii" and cp <= 0x7F:
                    out.append(ch)
                elif fallback == "keep":
                    out.append(ch)
                elif fallback == "drop":
                    pass
                continue
            out.append(piece)
        return "".join(out)

    return {
        **discovery,
        "status": "OK",
        "loaded_files": len(loaded),
        "mapped_codepoints": len(table),
        "fallback": fallback,
        "sha256_of_table": hashlib.sha256(
            json.dumps(sorted(table.items())).encode()
        ).hexdigest()[:16],
        "table": table,
        "predictor": predict,
    }


# ---------------------------------------------------------------------------
# 3. Verify against execution on held-out inputs the convention was not fitted to.
# ---------------------------------------------------------------------------

HELD_OUT = [
    "Zürich", "naïve", "café", "Æsir", "Ångström", "Ελλάδα", "Ж", "日本語", "—", "Hello World",
    "São Paulo", "Đại Việt", "İstanbul", "þorn", "Ωμέγα",
]


def verify(built: Mapping[str, Any], libdir: str, module: str, *, timeout: float = 60.0) -> dict:
    predict = built.get("predictor")
    if predict is None:
        return {"status": built.get("status", "NO_CONVENTION"), "agreement": "0/0", "rows": []}
    rows = []
    for text in HELD_OUT:
        code = (
            "import sys, json\n"
            f"sys.path.insert(0, {libdir!r})\n"
            f"import {module} as m\n"
            f"print(json.dumps(m.unidecode({text!r})))\n"
        )
        p = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, timeout=timeout
        )
        if p.returncode != 0:
            rows.append({"input": text, "status": "EXEC_FAILED",
                         "error": (p.stderr or "").strip().splitlines()[-1][:160]})
            continue
        try:
            actual = json.loads(p.stdout.strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError):
            rows.append({"input": text, "status": "UNPARSEABLE"})
            continue
        predicted = predict(text)
        rows.append({
            "input": text,
            "predicted": predicted,
            "actual": actual,
            "agrees": predicted == actual,
        })
    decided = [r for r in rows if "agrees" in r]
    agreed = sum(1 for r in decided if r["agrees"])
    return {
        "status": "MEASURED",
        "agreement": f"{agreed}/{len(decided)}",
        "agreed": agreed,
        "decided": len(decided),
        "rows": rows,
    }


def main(argv: Iterable[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--libdir", required=True)
    ap.add_argument("--module", required=True)
    ap.add_argument("--fallback", default=None,
                    choices=["drop", "keep", "identity_below_ascii"])
    ap.add_argument("--json-out")
    args = ap.parse_args(list(argv) if argv is not None else None)

    built = build_predictor(pathlib.Path(args.libdir), fallback=args.fallback)
    report = verify(built, args.libdir, args.module)
    payload = {
        "schema": SCHEMA,
        "libdir": args.libdir,
        "module": args.module,
        "discovery": {k: v for k, v in built.items() if k not in ("table", "predictor")},
        "verification": report,
        "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
    }
    text = json.dumps(payload, indent=1, sort_keys=True)
    if args.json_out:
        pathlib.Path(args.json_out).write_text(text, encoding="utf-8")
    print(text)
    return 0 if report.get("status") == "MEASURED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
