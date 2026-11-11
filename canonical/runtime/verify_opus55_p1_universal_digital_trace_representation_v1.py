"""Fail-closed verifier for the P1 universal digital-trace representation candidate.

This verifies exact canonical dependencies and the injective codec construction used by
the representation theorem. It does not verify P2/P3, performance dominance, or
literal terminal finality.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = "canonical/governance/OPUS55_P1_UNIVERSAL_DIGITAL_TRACE_REPRESENTATION_20261005_V1.json"
DEPENDENCIES = {
    "canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json":
        "661a57f839101fbf54c7e4edc76166c65ce9327d",
    "canonical/governance/OPUS55_FIXED_INTERFACE_TRACE_SUPERSET_COVERAGE_CERTIFICATE_20261005_V1.json":
        "146b237515ba8867acd6778b291e340e5e9138fc",
    "canonical/governance/FUNCTIONAL_ROLE_BASIS_TARGET_COMPLETENESS_GUARD_20261005_V1.json":
        "c20051932a2caaef4ef6907da27cb2806e7325eb",
}


def git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _u64(n: int) -> bytes:
    if n < 0 or n >= 1 << 64:
        raise ValueError("LENGTH_OUT_OF_RANGE")
    return n.to_bytes(8, "big")


def _read_u64(data: bytes, offset: int) -> tuple[int, int]:
    end = offset + 8
    if end > len(data):
        raise ValueError("TRUNCATED_LENGTH")
    return int.from_bytes(data[offset:end], "big"), end


def encode_record(fields: list[bytes]) -> bytes:
    out = [_u64(len(fields))]
    for field in fields:
        if not isinstance(field, bytes):
            raise TypeError("FIELD_NOT_BYTES")
        out.extend((_u64(len(field)), field))
    return b"".join(out)


def decode_record(data: bytes) -> list[bytes]:
    count, offset = _read_u64(data, 0)
    fields: list[bytes] = []
    for _ in range(count):
        size, offset = _read_u64(data, offset)
        end = offset + size
        if end > len(data):
            raise ValueError("TRUNCATED_FIELD")
        fields.append(data[offset:end])
        offset = end
    if offset != len(data):
        raise ValueError("TRAILING_BYTES")
    return fields


def encode_trace(events: list[list[bytes]]) -> bytes:
    encoded = [encode_record(event) for event in events]
    out = [_u64(len(encoded))]
    for event in encoded:
        out.extend((_u64(len(event)), event))
    return b"".join(out)


def decode_trace(data: bytes) -> list[list[bytes]]:
    count, offset = _read_u64(data, 0)
    events: list[list[bytes]] = []
    for _ in range(count):
        size, offset = _read_u64(data, offset)
        end = offset + size
        if end > len(data):
            raise ValueError("TRUNCATED_EVENT")
        events.append(decode_record(data[offset:end]))
        offset = end
    if offset != len(data):
        raise ValueError("TRAILING_TRACE_BYTES")
    return events


def _codec_falsification_sweep() -> list[str]:
    errors: list[str] = []
    atoms = [b"", b"\x00", b"a", b"ab", b"\xff"]
    records = [list(x) for n in range(4) for x in itertools.product(atoms, repeat=n)]
    seen: dict[bytes, list[bytes]] = {}
    for record in records:
        enc = encode_record(record)
        if decode_record(enc) != record:
            errors.append("RECORD_ROUNDTRIP")
            break
        old = seen.get(enc)
        if old is not None and old != record:
            errors.append("RECORD_COLLISION")
            break
        seen[enc] = record

    traces = [[], [[b""]], [[b"a"]], [[b"a"], [b"b", b""]], [[b"\x00", b"\xff"]]]
    trace_seen: dict[bytes, list[list[bytes]]] = {}
    for trace in traces:
        enc = encode_trace(trace)
        if decode_trace(enc) != trace:
            errors.append("TRACE_ROUNDTRIP")
            break
        old = trace_seen.get(enc)
        if old is not None and old != trace:
            errors.append("TRACE_COLLISION")
            break
        trace_seen[enc] = trace
    return errors


def verify(root: Path = ROOT) -> dict:
    errors: list[str] = []
    drift = {}
    for rel, expected in DEPENDENCIES.items():
        actual = git_blob(root / rel)
        if actual != expected:
            drift[rel] = {"expected": expected, "actual": actual}
    if drift:
        errors.append("CANONICAL_DEPENDENCY_DRIFT")

    spec = json.loads((root / SPEC).read_text())
    if spec.get("schema") != "PROJECT_BRAIN_OPUS55_P1_UNIVERSAL_DIGITAL_TRACE_REPRESENTATION_V1":
        errors.append("SCHEMA")
    theorem = spec.get("theorem", {})
    if theorem.get("result_if_independently_verified") != "P1_INTERFACE_REPRESENTATION_COMPLETENESS_PASS":
        errors.append("P1_RESULT")
    nonclaims = set(theorem.get("does_not_prove", []))
    for required in {
        "P2_ROLE_CLASSIFICATION_TOTALITY",
        "P3_ROLE_TO_FAMILY_SEMANTIC_TOTALITY",
        "BRAIN_EQUAL_OR_BETTER_DOMINANCE_OVER_THE_REPRESENTED_DOMAIN",
        "TERMINAL_FINALITY",
    }:
        if required not in nonclaims:
            errors.append("MISSING_NONCLAIM:" + required)

    errors.extend(_codec_falsification_sweep())

    accounting = spec.get("accounting", {})
    for key in (
        "incremental_spend_usd",
        "new_reality_units_consumed",
        "terminal_cases_consumed",
        "acceptance_credit_delta",
        "family_credit_delta",
        "capability_credit_delta",
        "ownership_credit_delta",
    ):
        if accounting.get(key) != 0:
            errors.append("NONZERO_ACCOUNTING:" + key)

    for flag in ("scheduling_authority", "execution_authority", "promotion_authority", "fresh_reality_authority"):
        if spec.get(flag) is not False:
            errors.append("AUTHORITY_LEAK:" + flag)

    return {
        "schema": "PROJECT_BRAIN_OPUS55_P1_UNIVERSAL_DIGITAL_TRACE_REPRESENTATION_VERDICT_V1",
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "dependency_drift": drift,
        "codec_injective_falsification_sweep": not any(x.endswith("COLLISION") for x in errors),
        "codec_roundtrip_falsification_sweep": not any("ROUNDTRIP" in x for x in errors),
        "p1_candidate_mechanically_coherent": not errors,
        "p2_proved": False,
        "p3_proved": False,
        "terminal": False,
        "acceptance_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
