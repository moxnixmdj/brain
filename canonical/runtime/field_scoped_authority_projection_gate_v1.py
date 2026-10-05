#!/usr/bin/env python3
"""
Field-scoped authority projection gate v1.

Purpose
-------
Reduce false verifier staleness caused by monolithic authority JSON blobs.

A verifier declares the exact RFC-6901 JSON pointers it is permitted to depend
on. This module projects only those values, content-addresses them, and emits a
manifest. A later authority document is stale iff a declared dependency changed
(or cannot be resolved). Changes outside the declared projection do not stale
the receipt.

Security / truth rules
----------------------
* Fail closed on malformed pointers, duplicate pointers, overlapping
  parent/child pointers, missing values, unsupported JSON values, or manifest
  tampering.
* Floats are deliberately rejected. Authority values that require decimals
  should use exact strings or integers so cross-runtime hashing stays exact.
* A downstream verifier should consume the sealed projection, not the original
  authority document. That makes undeclared dependencies impossible by
  construction.
* This is infrastructure only. It grants zero capability, family, acceptance,
  execution, promotion, or fresh-reality credit by itself.

No third-party dependencies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = "FIELD_SCOPED_AUTHORITY_PROJECTION_GATE_V1"


class GateError(ValueError):
    """Fail-closed input or verification error."""


def _validate_json_value(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        raise GateError(f"floats are forbidden at {path}; use an exact string/integer")
    if isinstance(value, list):
        for i, child in enumerate(value):
            _validate_json_value(child, f"{path}[{i}]")
        return
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise GateError(f"non-string object key at {path}: {key!r}")
            _validate_json_value(child, f"{path}/{key}")
        return
    raise GateError(f"unsupported JSON value at {path}: {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    """Deterministic JSON bytes for the restricted authority JSON domain."""
    _validate_json_value(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256_hex(canonical_bytes(value))


def _decode_pointer_segment(segment: str) -> str:
    # RFC-6901 allows only ~0 and ~1 escapes. Reject every other '~' sequence.
    i = 0
    out: list[str] = []
    while i < len(segment):
        ch = segment[i]
        if ch != "~":
            out.append(ch)
            i += 1
            continue
        if i + 1 >= len(segment) or segment[i + 1] not in ("0", "1"):
            raise GateError(f"invalid RFC-6901 escape in segment {segment!r}")
        out.append("~" if segment[i + 1] == "0" else "/")
        i += 2
    return "".join(out)


def parse_pointer(pointer: str) -> list[str]:
    if pointer == "":
        return []
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise GateError(f"JSON pointer must be '' or begin with '/': {pointer!r}")
    return [_decode_pointer_segment(x) for x in pointer[1:].split("/")]


def resolve_pointer(document: Any, pointer: str) -> Any:
    value = document
    for segment in parse_pointer(pointer):
        if isinstance(value, dict):
            if segment not in value:
                raise GateError(f"missing object key for pointer {pointer!r}: {segment!r}")
            value = value[segment]
            continue
        if isinstance(value, list):
            if segment == "-" or not segment.isdigit():
                raise GateError(f"invalid list index in pointer {pointer!r}: {segment!r}")
            if len(segment) > 1 and segment[0] == "0":
                raise GateError(f"non-canonical list index in pointer {pointer!r}: {segment!r}")
            index = int(segment)
            if index >= len(value):
                raise GateError(f"list index out of range in pointer {pointer!r}: {index}")
            value = value[index]
            continue
        raise GateError(
            f"pointer {pointer!r} descends through non-container {type(value).__name__}"
        )
    _validate_json_value(value, pointer or "$")
    return value


def _pointer_tokens(pointer: str) -> tuple[str, ...]:
    return tuple(parse_pointer(pointer))


def validate_pointer_set(pointers: Sequence[str]) -> tuple[str, ...]:
    if not pointers:
        raise GateError("at least one dependency pointer is required")
    if len(set(pointers)) != len(pointers):
        raise GateError("duplicate dependency pointers are forbidden")

    tokenized = [(p, _pointer_tokens(p)) for p in pointers]
    for i, (p, a) in enumerate(tokenized):
        for q, b in tokenized[i + 1 :]:
            shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
            if longer[: len(shorter)] == shorter:
                raise GateError(
                    f"overlapping parent/child pointers are forbidden: {p!r}, {q!r}"
                )
    return tuple(sorted(pointers))


def sealed_projection(document: Any, pointers: Sequence[str]) -> dict[str, Any]:
    ordered = validate_pointer_set(pointers)
    return {pointer: resolve_pointer(document, pointer) for pointer in ordered}


def freeze_manifest(
    document: Any,
    pointers: Sequence[str],
    *,
    source_path: str,
    source_blob_sha: str | None = None,
) -> dict[str, Any]:
    projection = sealed_projection(document, pointers)
    dependencies = [
        {
            "pointer": pointer,
            "value_sha256": canonical_sha256(projection[pointer]),
        }
        for pointer in sorted(projection)
    ]
    core = {
        "schema_version": SCHEMA_VERSION,
        "source_path": source_path,
        "dependencies": dependencies,
        "projection_sha256": canonical_sha256(projection),
    }
    if source_blob_sha is not None:
        core["source_blob_sha_at_freeze_nonbinding"] = source_blob_sha
    manifest = dict(core)
    manifest["manifest_sha256"] = canonical_sha256(core)
    return manifest


def _validate_manifest_shape(manifest: Mapping[str, Any]) -> None:
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise GateError("wrong or missing schema_version")
    if not isinstance(manifest.get("source_path"), str) or not manifest["source_path"]:
        raise GateError("manifest source_path must be a non-empty string")
    deps = manifest.get("dependencies")
    if not isinstance(deps, list) or not deps:
        raise GateError("manifest dependencies must be a non-empty list")
    pointers: list[str] = []
    for dep in deps:
        if not isinstance(dep, dict):
            raise GateError("dependency entry must be an object")
        pointer = dep.get("pointer")
        digest = dep.get("value_sha256")
        if not isinstance(pointer, str):
            raise GateError("dependency pointer must be a string")
        if not isinstance(digest, str) or len(digest) != 64:
            raise GateError(f"bad value_sha256 for {pointer!r}")
        pointers.append(pointer)
    validate_pointer_set(pointers)

    supplied = manifest.get("manifest_sha256")
    if not isinstance(supplied, str) or len(supplied) != 64:
        raise GateError("manifest_sha256 missing or malformed")
    core = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    expected = canonical_sha256(core)
    if supplied != expected:
        raise GateError("manifest self-hash mismatch")


def check_manifest(document: Any, manifest: Mapping[str, Any]) -> dict[str, Any]:
    """
    Verify a live document against a frozen field-scoped dependency manifest.

    Result:
      stale=False only when every declared value is exactly unchanged.
      Changes outside the declared projection are intentionally irrelevant.
    """
    _validate_manifest_shape(manifest)
    changed: list[dict[str, str]] = []
    live_projection: dict[str, Any] = {}

    for dep in manifest["dependencies"]:
        pointer = dep["pointer"]
        try:
            value = resolve_pointer(document, pointer)
            live_projection[pointer] = value
            live_hash = canonical_sha256(value)
            if live_hash != dep["value_sha256"]:
                changed.append(
                    {
                        "pointer": pointer,
                        "reason": "VALUE_CHANGED",
                        "expected_sha256": dep["value_sha256"],
                        "live_sha256": live_hash,
                    }
                )
        except GateError as exc:
            changed.append(
                {
                    "pointer": pointer,
                    "reason": "UNRESOLVABLE",
                    "error": str(exc),
                }
            )

    projection_hash = canonical_sha256(live_projection) if not changed else None
    if not changed and projection_hash != manifest["projection_sha256"]:
        # This should be unreachable if per-field hashes and canonicalization are sound.
        raise GateError("projection aggregate mismatch despite unchanged leaf hashes")

    return {
        "schema_version": SCHEMA_VERSION,
        "stale": bool(changed),
        "changed_dependencies": changed,
        "live_projection_sha256": projection_hash,
        "manifest_sha256": manifest["manifest_sha256"],
        "rule": (
            "STALE_IFF_DECLARED_DEPENDENCY_CHANGED_OR_UNRESOLVABLE__"
            "UNDECLARED_AUTHORITY_CHURN_IS_NON_LOAD_BEARING"
        ),
        "terminal_credit_delta": 0,
    }


def bind_receipt(
    *,
    manifest: Mapping[str, Any],
    candidate_diff_sha256: str,
    verifier_sha256: str,
    test_suite_sha256: str,
    live_parent_commit_sha: str,
    verdict: str,
) -> dict[str, Any]:
    """Bind an external verification result to the exact dependency projection."""
    _validate_manifest_shape(manifest)
    for label, digest in (
        ("candidate_diff_sha256", candidate_diff_sha256),
        ("verifier_sha256", verifier_sha256),
        ("test_suite_sha256", test_suite_sha256),
    ):
        if not isinstance(digest, str) or len(digest) != 64:
            raise GateError(f"{label} must be a 64-character SHA-256 hex digest")
    if not isinstance(live_parent_commit_sha, str) or not live_parent_commit_sha:
        raise GateError("live_parent_commit_sha is required")
    if verdict not in {"PASS", "FAIL"}:
        raise GateError("verdict must be PASS or FAIL")

    core = {
        "schema_version": SCHEMA_VERSION,
        "dependency_manifest_sha256": manifest["manifest_sha256"],
        "projection_sha256": manifest["projection_sha256"],
        "candidate_diff_sha256": candidate_diff_sha256,
        "verifier_sha256": verifier_sha256,
        "test_suite_sha256": test_suite_sha256,
        "live_parent_commit_sha": live_parent_commit_sha,
        "verdict": verdict,
        "terminal_credit_delta": 0,
    }
    receipt = dict(core)
    receipt["receipt_sha256"] = canonical_sha256(core)
    return receipt


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        value = json.load(fh)
    _validate_json_value(value)
    return value


def write_json(value: Any) -> None:
    sys.stdout.write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def _self_test() -> None:
    base = {
        "acceptance": {"proved": 14, "unresolved": 24},
        "root2": {"touching": 18, "fresh_reality": False},
        "telemetry": {"last_worker": "alpha", "counter": 1},
        "notes": ["a", "b"],
    }
    pointers = ["/acceptance/proved", "/acceptance/unresolved", "/root2/touching"]
    manifest = freeze_manifest(
        base,
        pointers,
        source_path="canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json",
        source_blob_sha="deadbeef",
    )

    # Unrelated same-file churn must not invalidate the proof.
    unrelated = json.loads(json.dumps(base))
    unrelated["telemetry"]["counter"] = 999
    unrelated["telemetry"]["last_worker"] = "omega"
    assert check_manifest(unrelated, manifest)["stale"] is False

    # Object key ordering must be irrelevant.
    reordered = {
        "notes": ["a", "b"],
        "telemetry": {"counter": 1, "last_worker": "alpha"},
        "root2": {"fresh_reality": False, "touching": 18},
        "acceptance": {"unresolved": 24, "proved": 14},
    }
    assert check_manifest(reordered, manifest)["stale"] is False

    # A load-bearing field change must stale immediately.
    changed = json.loads(json.dumps(base))
    changed["acceptance"]["proved"] = 15
    result = check_manifest(changed, manifest)
    assert result["stale"] is True
    assert result["changed_dependencies"][0]["pointer"] == "/acceptance/proved"

    # Missing bound state fails closed.
    missing = json.loads(json.dumps(base))
    del missing["root2"]["touching"]
    result = check_manifest(missing, manifest)
    assert result["stale"] is True
    assert any(x["reason"] == "UNRESOLVABLE" for x in result["changed_dependencies"])

    # Parent/child overlap is forbidden because it muddies the declared dependency cone.
    try:
        freeze_manifest(base, ["/acceptance", "/acceptance/proved"], source_path="x.json")
    except GateError:
        pass
    else:
        raise AssertionError("overlapping pointers must fail closed")

    # Floats are forbidden for cross-runtime exactness.
    try:
        freeze_manifest({"x": 1.2}, ["/x"], source_path="x.json")
    except GateError:
        pass
    else:
        raise AssertionError("floats must fail closed")

    # Manifest tampering must be detected.
    tampered = json.loads(json.dumps(manifest))
    tampered["dependencies"][0]["value_sha256"] = "0" * 64
    try:
        check_manifest(base, tampered)
    except GateError:
        pass
    else:
        raise AssertionError("tampered manifest must fail closed")

    # Receipt binding is deterministic and content-addressed.
    zeros = "0" * 64
    receipt_a = bind_receipt(
        manifest=manifest,
        candidate_diff_sha256=zeros,
        verifier_sha256=zeros,
        test_suite_sha256=zeros,
        live_parent_commit_sha="abc123",
        verdict="PASS",
    )
    receipt_b = bind_receipt(
        manifest=manifest,
        candidate_diff_sha256=zeros,
        verifier_sha256=zeros,
        test_suite_sha256=zeros,
        live_parent_commit_sha="abc123",
        verdict="PASS",
    )
    assert receipt_a == receipt_b

    print("SELF_TEST_PASS")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    freeze = sub.add_parser("freeze", help="freeze a field-scoped dependency manifest")
    freeze.add_argument("document")
    freeze.add_argument("--source-path", required=True)
    freeze.add_argument("--source-blob-sha")
    freeze.add_argument("--pointer", action="append", required=True)

    check = sub.add_parser("check", help="check a live document against a manifest")
    check.add_argument("document")
    check.add_argument("manifest")

    project = sub.add_parser("project", help="emit only the declared verifier inputs")
    project.add_argument("document")
    project.add_argument("--pointer", action="append", required=True)

    sub.add_parser("self-test", help="run deterministic built-in tests")

    args = parser.parse_args(argv)

    if args.cmd == "freeze":
        manifest = freeze_manifest(
            load_json(args.document),
            args.pointer,
            source_path=args.source_path,
            source_blob_sha=args.source_blob_sha,
        )
        write_json(manifest)
        return 0

    if args.cmd == "check":
        result = check_manifest(load_json(args.document), load_json(args.manifest))
        write_json(result)
        return 1 if result["stale"] else 0

    if args.cmd == "project":
        write_json(sealed_projection(load_json(args.document), args.pointer))
        return 0

    if args.cmd == "self-test":
        _self_test()
        return 0

    raise AssertionError("unreachable")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        sys.stderr.write(f"FAIL_CLOSED: {exc}\n")
        raise SystemExit(2)
