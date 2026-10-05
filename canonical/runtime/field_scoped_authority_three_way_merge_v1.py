#!/usr/bin/env python3
"""
Field-scoped authority three-way merge v1.

Purpose
-------
Safely rebase a stale authority candidate onto a rapidly moving live document
without treating unrelated JSON churn as a conflict.

The candidate declares:
  * read_pointers: exact fields whose base values influenced the candidate.
  * write_pointers: exact fields/subtrees the candidate is allowed to change.

The gate then:
  1. proves the candidate changed nothing outside its declared write set;
  2. rejects if any declared read dependency changed on live;
  3. rejects a concurrent write/write collision unless live already equals the
     candidate value;
  4. applies only the declared candidate writes to the live document;
  5. preserves all unrelated live changes.

This is a deterministic rebase primitive, not promotion authority. The merged
output must still pass the domain-specific verifier. Zero terminal credit.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from dataclasses import dataclass
from typing import Any, Sequence

SCHEMA = "FIELD_SCOPED_AUTHORITY_THREE_WAY_MERGE_V1"
_MISSING = object()


class MergeError(ValueError):
    pass


def _validate_json(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        raise MergeError(f"floats forbidden at {path}; use exact strings/integers")
    if isinstance(value, list):
        for i, child in enumerate(value):
            _validate_json(child, f"{path}[{i}]")
        return
    if isinstance(value, dict):
        for k, child in value.items():
            if not isinstance(k, str):
                raise MergeError(f"non-string object key at {path}")
            _validate_json(child, f"{path}/{k}")
        return
    raise MergeError(f"unsupported JSON value at {path}: {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    _validate_json(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _decode(segment: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(segment):
        if segment[i] != "~":
            out.append(segment[i])
            i += 1
            continue
        if i + 1 >= len(segment) or segment[i + 1] not in ("0", "1"):
            raise MergeError(f"invalid RFC-6901 escape in {segment!r}")
        out.append("~" if segment[i + 1] == "0" else "/")
        i += 2
    return "".join(out)


def _encode(segment: str) -> str:
    return segment.replace("~", "~0").replace("/", "~1")


def tokens(pointer: str) -> tuple[str, ...]:
    if pointer == "":
        return ()
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise MergeError(f"invalid JSON pointer: {pointer!r}")
    return tuple(_decode(x) for x in pointer[1:].split("/"))


def pointer_from_tokens(parts: Sequence[str]) -> str:
    if not parts:
        return ""
    return "/" + "/".join(_encode(x) for x in parts)


def get_at(document: Any, pointer: str, default: Any = _MISSING) -> Any:
    cur = document
    for part in tokens(pointer):
        if isinstance(cur, dict):
            if part not in cur:
                if default is not _MISSING:
                    return default
                raise MergeError(f"missing pointer {pointer!r}")
            cur = cur[part]
        elif isinstance(cur, list):
            if part == "-" or not part.isdigit() or (len(part) > 1 and part[0] == "0"):
                if default is not _MISSING:
                    return default
                raise MergeError(f"invalid list index in {pointer!r}")
            idx = int(part)
            if idx >= len(cur):
                if default is not _MISSING:
                    return default
                raise MergeError(f"list index out of range in {pointer!r}")
            cur = cur[idx]
        else:
            if default is not _MISSING:
                return default
            raise MergeError(f"pointer descends through scalar: {pointer!r}")
    return cur


def _parent_and_key(document: Any, pointer: str) -> tuple[Any, str]:
    parts = tokens(pointer)
    if not parts:
        raise MergeError("root writes are forbidden")
    parent = document
    for part in parts[:-1]:
        if isinstance(parent, dict):
            if part not in parent:
                raise MergeError(f"missing parent for write {pointer!r}")
            parent = parent[part]
        elif isinstance(parent, list):
            if not part.isdigit() or (len(part) > 1 and part[0] == "0"):
                raise MergeError(f"invalid list parent index in {pointer!r}")
            idx = int(part)
            if idx >= len(parent):
                raise MergeError(f"list parent index out of range in {pointer!r}")
            parent = parent[idx]
        else:
            raise MergeError(f"write parent is scalar for {pointer!r}")
    return parent, parts[-1]


def set_at(document: Any, pointer: str, value: Any) -> None:
    _validate_json(value)
    parent, key = _parent_and_key(document, pointer)
    if isinstance(parent, dict):
        parent[key] = copy.deepcopy(value)
        return
    if isinstance(parent, list):
        if not key.isdigit() or (len(key) > 1 and key[0] == "0"):
            raise MergeError(f"invalid list write index in {pointer!r}")
        idx = int(key)
        if idx >= len(parent):
            raise MergeError(f"list write index out of range in {pointer!r}")
        parent[idx] = copy.deepcopy(value)
        return
    raise MergeError(f"write parent is not a container for {pointer!r}")


def delete_at(document: Any, pointer: str) -> None:
    parent, key = _parent_and_key(document, pointer)
    if isinstance(parent, dict):
        if key not in parent:
            raise MergeError(f"cannot delete missing key {pointer!r}")
        del parent[key]
        return
    # List deletion shifts indices and can invalidate other pointer semantics.
    raise MergeError("list-element deletion is forbidden; replace the containing list instead")


def validate_pointer_set(pointers: Sequence[str], *, allow_root: bool) -> tuple[str, ...]:
    if len(set(pointers)) != len(pointers):
        raise MergeError("duplicate pointers are forbidden")
    parsed = [(p, tokens(p)) for p in pointers]
    if not allow_root and any(not t for _, t in parsed):
        raise MergeError("root pointer is forbidden in this set")
    for i, (p, a) in enumerate(parsed):
        for q, b in parsed[i + 1 :]:
            short, long = (a, b) if len(a) <= len(b) else (b, a)
            if long[: len(short)] == short:
                raise MergeError(f"overlapping pointers forbidden: {p!r}, {q!r}")
    return tuple(sorted(pointers))


def _equal(a: Any, b: Any) -> bool:
    if a is _MISSING or b is _MISSING:
        return a is b
    return canonical_bytes(a) == canonical_bytes(b)


def _covered(pointer: str, declared: Sequence[str]) -> bool:
    p = tokens(pointer)
    for d in declared:
        dt = tokens(d)
        if p[: len(dt)] == dt:
            return True
    return False


def changed_leaves(base: Any, candidate: Any, path: tuple[str, ...] = ()) -> set[str]:
    """
    Conservative structural diff.

    Dicts recurse to leaves. Lists are atomic because insert/delete shifts make
    leaf-level list rebases unsafe without a stronger sequence merge contract.
    """
    if type(base) is not type(candidate):
        return {pointer_from_tokens(path)}
    if isinstance(base, dict):
        out: set[str] = set()
        keys = set(base) | set(candidate)
        for key in keys:
            child_path = path + (key,)
            if key not in base or key not in candidate:
                out.add(pointer_from_tokens(child_path))
            else:
                out |= changed_leaves(base[key], candidate[key], child_path)
        return out
    if isinstance(base, list):
        return set() if _equal(base, candidate) else {pointer_from_tokens(path)}
    return set() if _equal(base, candidate) else {pointer_from_tokens(path)}


@dataclass(frozen=True)
class Conflict:
    pointer: str
    kind: str
    base_sha256: str | None
    live_sha256: str | None
    candidate_sha256: str | None


def _maybe_digest(value: Any) -> str | None:
    return None if value is _MISSING else digest(value)


def merge_authority(
    base: Any,
    candidate: Any,
    live: Any,
    *,
    read_pointers: Sequence[str],
    write_pointers: Sequence[str],
) -> dict[str, Any]:
    _validate_json(base)
    _validate_json(candidate)
    _validate_json(live)

    reads = validate_pointer_set(read_pointers, allow_root=True)
    writes = validate_pointer_set(write_pointers, allow_root=False)
    if not writes:
        raise MergeError("at least one write pointer is required")

    candidate_changes = changed_leaves(base, candidate)
    escaped = sorted(p for p in candidate_changes if not _covered(p, writes))
    if escaped:
        raise MergeError(
            "candidate changed undeclared paths: " + ", ".join(escaped)
        )

    conflicts: list[Conflict] = []

    # Any changed read dependency means the candidate was computed from stale
    # premises and must be regenerated, even if the write path itself is clear.
    for pointer in reads:
        b = get_at(base, pointer, _MISSING)
        l = get_at(live, pointer, _MISSING)
        if not _equal(b, l):
            conflicts.append(
                Conflict(
                    pointer,
                    "READ_DEPENDENCY_CHANGED",
                    _maybe_digest(b),
                    _maybe_digest(l),
                    _maybe_digest(get_at(candidate, pointer, _MISSING)),
                )
            )

    # A write is safe only if live still equals base at that write scope, or if
    # another concurrent writer already produced exactly the candidate value.
    for pointer in writes:
        b = get_at(base, pointer, _MISSING)
        c = get_at(candidate, pointer, _MISSING)
        l = get_at(live, pointer, _MISSING)
        if _equal(l, b) or _equal(l, c):
            continue
        conflicts.append(
            Conflict(
                pointer,
                "WRITE_WRITE_CONFLICT",
                _maybe_digest(b),
                _maybe_digest(l),
                _maybe_digest(c),
            )
        )

    # Deduplicate conflicts if a pointer appears in both read and write sets.
    dedup: dict[tuple[str, str], Conflict] = {
        (c.pointer, c.kind): c for c in conflicts
    }
    conflicts = list(dedup.values())

    if conflicts:
        return {
            "schema": SCHEMA,
            "mergeable": False,
            "conflicts": [c.__dict__ for c in sorted(conflicts, key=lambda x: (x.pointer, x.kind))],
            "candidate_change_count": len(candidate_changes),
            "terminal_credit_delta": 0,
        }

    merged = copy.deepcopy(live)
    for pointer in writes:
        b = get_at(base, pointer, _MISSING)
        c = get_at(candidate, pointer, _MISSING)
        if _equal(b, c):
            continue
        if c is _MISSING:
            # If live already reflects the deletion, nothing to do.
            if get_at(merged, pointer, _MISSING) is not _MISSING:
                delete_at(merged, pointer)
        else:
            set_at(merged, pointer, c)

    _validate_json(merged)
    live_unrelated = changed_leaves(base, live)
    preserved_unrelated = sorted(
        p for p in live_unrelated
        if not _covered(p, writes) and not _covered(p, reads)
    )

    receipt_core = {
        "schema": SCHEMA,
        "base_sha256": digest(base),
        "candidate_sha256": digest(candidate),
        "live_sha256": digest(live),
        "merged_sha256": digest(merged),
        "read_pointers": list(reads),
        "write_pointers": list(writes),
        "candidate_change_pointers": sorted(candidate_changes),
        "preserved_unrelated_live_change_pointers": preserved_unrelated,
    }
    return {
        **receipt_core,
        "receipt_sha256": digest(receipt_core),
        "mergeable": True,
        "merged": merged,
        "rule": (
            "REBASE_ONLY_IF_DECLARED_READ_PREMISES_ARE_UNCHANGED_AND_"
            "DECLARED_WRITES_HAVE_NO_DIVERGENT_CONCURRENT_WRITER"
        ),
        "requires_domain_verifier_after_merge": True,
        "terminal_credit_delta": 0,
    }


def _self_test() -> None:
    base = {
        "acceptance": {"proved": 14, "unresolved": 24},
        "root2": {"touching": 18, "next": "OLD"},
        "telemetry": {"worker": "a", "counter": 1},
        "root3": {"touching": 9},
    }
    candidate = copy.deepcopy(base)
    candidate["root2"]["next"] = "NEW"

    live = copy.deepcopy(base)
    live["telemetry"]["worker"] = "b"
    live["root3"]["touching"] = 8

    result = merge_authority(
        base,
        candidate,
        live,
        read_pointers=["/acceptance/proved", "/acceptance/unresolved", "/root2/touching"],
        write_pointers=["/root2/next"],
    )
    assert result["mergeable"] is True
    assert result["merged"]["root2"]["next"] == "NEW"
    assert result["merged"]["telemetry"]["worker"] == "b"
    assert result["merged"]["root3"]["touching"] == 8

    # Changed premise must fail closed.
    live2 = copy.deepcopy(live)
    live2["acceptance"]["proved"] = 15
    result = merge_authority(
        base,
        candidate,
        live2,
        read_pointers=["/acceptance/proved", "/acceptance/unresolved", "/root2/touching"],
        write_pointers=["/root2/next"],
    )
    assert result["mergeable"] is False
    assert any(c["kind"] == "READ_DEPENDENCY_CHANGED" for c in result["conflicts"])

    # Divergent concurrent writer must fail closed.
    live3 = copy.deepcopy(live)
    live3["root2"]["next"] = "OTHER"
    result = merge_authority(
        base,
        candidate,
        live3,
        read_pointers=["/acceptance/proved"],
        write_pointers=["/root2/next"],
    )
    assert result["mergeable"] is False
    assert any(c["kind"] == "WRITE_WRITE_CONFLICT" for c in result["conflicts"])

    # Idempotent concurrent writer is safe.
    live4 = copy.deepcopy(live)
    live4["root2"]["next"] = "NEW"
    result = merge_authority(
        base,
        candidate,
        live4,
        read_pointers=["/acceptance/proved"],
        write_pointers=["/root2/next"],
    )
    assert result["mergeable"] is True

    # Undeclared candidate mutation is rejected.
    bad = copy.deepcopy(candidate)
    bad["telemetry"]["counter"] = 99
    try:
        merge_authority(
            base,
            bad,
            live,
            read_pointers=["/acceptance/proved"],
            write_pointers=["/root2/next"],
        )
    except MergeError:
        pass
    else:
        raise AssertionError("undeclared candidate mutation must fail closed")

    print("SELF_TEST_PASS")


def _load(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        value = json.load(fh)
    _validate_json(value)
    return value


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("base")
    p.add_argument("candidate")
    p.add_argument("live")
    p.add_argument("--read", action="append", default=[])
    p.add_argument("--write", action="append", required=True)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args(argv)

    if args.self_test:
        _self_test()
        return 0

    result = merge_authority(
        _load(args.base),
        _load(args.candidate),
        _load(args.live),
        read_pointers=args.read,
        write_pointers=args.write,
    )
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return 0 if result["mergeable"] else 3


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MergeError as exc:
        sys.stderr.write(f"FAIL_CLOSED: {exc}\n")
        raise SystemExit(2)
