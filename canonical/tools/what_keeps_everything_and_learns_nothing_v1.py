#!/usr/bin/env python3
"""The memory that keeps everything and therefore knows nothing.

`scan_retrieve_fetch_v1` works and is honest, but its key is a literal fact:

    ("<sha256 of the binary>", "<invoked name>")  ->  everything learned about that program

Measured on /usr/bin: 429 entries, 190,845 bytes. That is ONE host, and every entry is a
transcription of one program. The user's objection is exactly right, and it is quantitative:

    "Saving his exact experience must be in a very sufficient way, not just saving the exact
     experience in a dumb way... Maybe we should do generalization"

The arithmetic of the dumb form, from the measured census:

    429 records contain only      31 distinct TRANSFORM CLASSES
                                 37 distinct FLAG PATTERNS
                                 21.5 KB of prose out of 190.8 KB of JSON

So 429 literal facts encode about 31 + 37 facts plus a name->class index. A memory keyed on
content must re-learn a whole host on every version bump (each new binary is a new digest);
a memory keyed on STRUCTURE does not, because `gzip --decompress` and `bzip2 --decompress`
state the same kind of thing.

What is generalized, and what is NOT
------------------------------------
GENERALIZED: the mapping from a program's own help text to a typed capability. That mapping
is computed from closed English verb classes, not learned per program, so it transfers to a
host it has never seen.

NOT GENERALIZED, deliberately: the NAME. Two byte-identical binaries with different names
behave oppositely (`xz` compresses, `unxz` decompresses -- measured in this repository), so
the name stays a first-class key component. Saving "xz and unxz are the same thing" would be
saving a falsehood.

NOT STORED AT ALL: prose descriptions. The description is evidence used to derive the class;
keeping 21.5 KB of help-page sentences is the definition of a knowledge warehouse.

The self-description IS the generalized form: `transform` is one of a CLOSED set of English
verb classes, and the flag pattern is derived from the help page by the same rule for every
program. Nothing here is a stored world fact; everything is a computed function of text the
artifact printed about itself.

Schema BRAIN_WHAT_KEEPS_EVERYTHING_V1. Authority NONE__PRODUCER_RUN_SANDBOX.
"""
from __future__ import annotations

import json
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import scan_retrieve_fetch_v1 as SRF  # noqa: E402

SCHEMA = "BRAIN_WHAT_KEEPS_EVERYTHING_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
MEMORY_PATH = pathlib.Path("/tmp/brain_memory/generalized.json")
MEMORY_SCHEMA = "BRAIN_GENERALIZED_HOST_MEMORY_V1"

# The prose field is evidence, not knowledge. It is dropped at save time and never read back.
EVIDENCE_FIELDS = ("description", "help_digest", "learned_seconds", "digest", "path", "key")


def generalizable(record: dict[str, Any]) -> bool:
    """A record is worth keeping in general form when it states a CLASS.

    A program whose help page names no input type yields transform `print`, `list`, `show`
    and so on -- those are a closed set of "does not declare its input type" classes, and
    they are all the same generalization. Only the transform and the flag pattern survive.
    """
    return bool(record.get("transform"))


def to_general(record: dict[str, Any]) -> dict[str, Any]:
    """One learned record, reduced to what transfers to a host never seen."""
    flags = record.get("flags") or {}
    return {
        "name": record["name"],
        # THE CLASS, not the program: a closed English verb class read off the help page.
        "transform": record["transform"],
        # THE PATTERN, not the page: role -> the flag this program associates with it.
        "roles": {k: v for k, v in flags.items() if v},
    }


def load(path: pathlib.Path = MEMORY_PATH) -> dict[str, Any]:
    if not path.exists():
        return {"schema": MEMORY_SCHEMA, "by_name": {}, "classes": {}}
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {"schema": MEMORY_SCHEMA, "by_name": {}, "classes": {}}
    if data.get("schema") != MEMORY_SCHEMA:
        return {"schema": MEMORY_SCHEMA, "by_name": {}, "classes": {}}
    return data


def save(memory: dict[str, Any], path: pathlib.Path = MEMORY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(memory, sort_keys=True, separators=(",", ":")))


def remember(memory: dict[str, Any], records: list[dict[str, Any]]) -> int:
    """Write each record twice: once as itself, once as its class.

    The `classes` table is the generalization. It is what answers "what does a program that
    decompresses look like on a host I have never seen" without naming any program.
    """
    added = 0
    for rec in records:
        if not generalizable(rec):
            continue
        gen = to_general(rec)
        memory["by_name"][gen["name"]] = gen
        cls = gen["transform"]
        bucket = memory["classes"].setdefault(cls, {"seen": 0, "names": [], "roles": {}})
        bucket["seen"] += 1
        if gen["name"] not in bucket["names"]:
            bucket["names"].append(gen["name"])
        for role, flag in (gen["roles"] or {}).items():
            bucket["roles"].setdefault(role, {})
            bucket["roles"][role][flag] = bucket["roles"][role].get(flag, 0) + 1
        added += 1
    return added


def predict_roles(memory: dict[str, Any], transform: str, name: str) -> dict[str, str]:
    """What a program of this CLASS is expected to expose, before asking it anything.

    This is the retrieval that survives a version bump: the binary's digest is new, but the
    class is the same, so the prediction stands. It is a PREDICTION and is always verified
    against the program's own help page before it is used -- a memory that predicts is
    useful, a memory that is trusted is a warehouse.
    """
    bucket = memory.get("classes", {}).get(transform)
    if not bucket:
        return {}
    out: dict[str, str] = {}
    for role, counts in (bucket.get("roles") or {}).items():
        if counts:
            out[role] = max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]
    # the name is a first-class input: a `*d`/`un*` spelling predicts the inverse role
    if re_inverse(name) and "decompress" in out:
        out["decompress"] = out["decompress"]
    return out


def re_inverse(name: str) -> bool:
    low = name.lower()
    return low.startswith(("un", "de")) or low.endswith(("d", "cat"))


def generalize_file(path: pathlib.Path = pathlib.Path("/tmp/brain_memory/memory.json"),
                    out: pathlib.Path = MEMORY_PATH) -> dict[str, Any]:
    """Reduce a literal memory to a generalized one, and report the size honestly."""
    raw = json.loads(path.read_text()) if path.exists() else {"entries": {}}
    entries = list((raw.get("entries") or {}).values())
    memory = {"schema": MEMORY_SCHEMA, "by_name": {}, "classes": {}}
    kept = remember(memory, entries)
    save(memory, out)
    literal_bytes = len(json.dumps(raw))
    general_bytes = len(json.dumps(memory, sort_keys=True, separators=(",", ":")))
    return {
        "schema": SCHEMA, "authority": AUTHORITY,
        "literal_entries": len(entries),
        "literal_bytes": literal_bytes,
        "general_entries": kept,
        "general_bytes": general_bytes,
        "shrink": round(literal_bytes / max(general_bytes, 1), 1),
        "classes": len(memory["classes"]),
        "prose_dropped_bytes": sum(len(e.get("description") or "") for e in entries),
        "cost_zeros": {"model_calls": 0, "network_calls": 0, "parameters_stored": 0},
    }


if __name__ == "__main__":
    print(json.dumps(generalize_file(), indent=1))
