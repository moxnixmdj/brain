from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import terminal_frontier_compiler_v2 as v2

SCHEMA = "PROJECT_BRAIN_LIVE_TERMINAL_FRONTIER_V3"


class FrontierV3Error(RuntimeError):
    pass


def _open(state: object) -> bool:
    return v2._is_open_state(state)


def _identity_sha256(meta: Mapping[str, Any]) -> str:
    rows: list[str] = []
    for category in (
        "family_mappings",
        "cross_cutting_conditions",
        "proof_basis_repairs",
        "performance_obligations",
    ):
        for item in sorted(str(x) for x in meta.get(category, [])):
            rows.append(category + "\0" + item + "\n")
    return hashlib.sha256("".join(rows).encode("utf-8")).hexdigest()


def meta_envelope_obligations_v3(meta_doc: Mapping[str, Any]) -> dict[str, Any]:
    old = v2.meta_envelope_obligations(meta_doc)

    performance: list[str] = []

    generic = meta_doc.get("terminal_performance_obligations")
    if generic is not None:
        if not isinstance(generic, list):
            raise FrontierV3Error("TERMINAL_PERFORMANCE_OBLIGATIONS_INVALID")
        for index, row in enumerate(generic):
            if not isinstance(row, Mapping):
                raise FrontierV3Error(
                    f"TERMINAL_PERFORMANCE_OBLIGATION_{index}_INVALID"
                )
            if _open(row.get("state")):
                ident = str(row.get("id") or row.get("obligation") or "").strip()
                if not ident:
                    raise FrontierV3Error(
                        f"TERMINAL_PERFORMANCE_OBLIGATION_{index}_IDENTITY_MISSING"
                    )
                performance.append(ident)

    # Current active Root1 V6 uses this singular historical field.
    creative = meta_doc.get("creative_diagram_performance_frontier")
    if isinstance(creative, Mapping) and _open(creative.get("state")):
        ident = str(creative.get("obligation") or creative.get("id") or "").strip()
        if not ident:
            raise FrontierV3Error("CREATIVE_DIAGRAM_PERFORMANCE_IDENTITY_MISSING")
        performance.append(ident)

    if len(performance) != len(set(performance)):
        raise FrontierV3Error("PERFORMANCE_OBLIGATION_IDENTITY_DUPLICATE")

    out = {
        "family_mappings": list(old.get("family_mappings") or []),
        "cross_cutting_conditions": list(old.get("cross_cutting_conditions") or []),
        "proof_basis_repairs": list(old.get("proof_basis_repairs") or []),
        "performance_obligations": sorted(performance),
    }
    out["open_count"] = sum(
        len(out[name])
        for name in (
            "family_mappings",
            "cross_cutting_conditions",
            "proof_basis_repairs",
            "performance_obligations",
        )
    )
    out["identity_sha256"] = _identity_sha256(out)

    declared = meta_doc.get("open_meta_obligation_accounting")
    if isinstance(declared, Mapping):
        expected = declared.get("total_open_meta_obligations")
        if expected is not None and out["open_count"] != int(expected):
            raise FrontierV3Error(
                "META_OPEN_COUNT_DISAGREES_WITH_ACTIVE_ROOT1_AUTHORITY:"
                + str(out["open_count"])
                + ":"
                + str(expected)
            )

    return out


def compile_frontier(root: Path = v2.ROOT) -> dict[str, Any]:
    base = v2.compile_frontier(root)

    version, activation_path, activation = v2._discover_highest_active(
        v2.ROOT1_ACTIVATION_RE, root
    )
    subject_path, subject, verification_path, _ = v2._validate_activation(
        activation_path, activation, root
    )
    meta = meta_envelope_obligations_v3(subject)

    acceptance = base.get("acceptance")
    if not isinstance(acceptance, Mapping):
        raise FrontierV3Error("BASE_ACCEPTANCE_MISSING")

    td = base.get("target_discovery")
    if not isinstance(td, Mapping):
        raise FrontierV3Error("BASE_TARGET_DISCOVERY_MISSING")
    td_complete = td.get("complete") is True

    terminal = v2.terminal_finality(
        acceptance,
        root1_positive_gap_count=int(base.get("root1_positive_gap_count", -1)),
        meta_open_count=int(meta["open_count"]),
        target_discovery_complete=td_complete,
    )

    out = dict(base)
    out["schema"] = SCHEMA
    out["status"] = "TERMINAL_TRUE" if terminal else "TERMINAL_FALSE"
    out["terminal"] = terminal
    out["meta_envelope"] = {
        "active_version": version,
        "activation_path": activation_path,
        "subject_path": subject_path,
        "verification_path": verification_path,
        **meta,
    }
    out["v2_meta_projection_superseded"] = True
    out["accounting"] = {
        **dict(base.get("accounting") or {}),
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "new_reality_units_consumed": 0,
    }
    return out


def main() -> int:
    try:
        print(json.dumps(compile_frontier(), indent=2, sort_keys=True))
        return 0
    except (v2.FrontierCompileError, FrontierV3Error) as exc:
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "status": "FAIL_CLOSED__FRONTIER_COMPILE_ERROR",
                    "error": str(exc),
                    "terminal": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 43


if __name__ == "__main__":
    raise SystemExit(main())
