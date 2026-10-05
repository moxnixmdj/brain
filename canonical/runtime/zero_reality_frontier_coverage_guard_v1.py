from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


class FrontierCoverageError(ValueError):
    pass


def _load(path: str | Path) -> Mapping[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        obj = json.load(fh)
    if not isinstance(obj, Mapping):
        raise FrontierCoverageError(f"JSON_OBJECT_REQUIRED:{path}")
    return obj


def canonical_open_predicates(root_state: Mapping[str, Any]) -> set[str]:
    part = root_state.get("current_residual_root_partition")
    if not isinstance(part, Mapping):
        raise FrontierCoverageError("CURRENT_RESIDUAL_ROOT_PARTITION_MISSING")
    out: set[str] = set()
    for key in ("root1_only", "root2_only", "root3_only", "root2_and_root3"):
        values = part.get(key, [])
        if not isinstance(values, list):
            raise FrontierCoverageError(f"{key.upper()}_MUST_BE_LIST")
        for value in values:
            if not isinstance(value, str) or not value:
                raise FrontierCoverageError(f"{key.upper()}_HAS_INVALID_PREDICATE")
            out.add(value)
    declared = part.get("unresolved_total")
    if declared is not None and declared != len(out):
        raise FrontierCoverageError(
            f"ROOT_STATE_COUNT_MISMATCH:declared={declared}:derived={len(out)}"
        )
    return out


def scheduled_predicates(cut: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    active: set[str] = set()
    dormant: set[str] = set()

    groups = cut.get("current_information_positive_action_groups", [])
    if not isinstance(groups, list):
        raise FrontierCoverageError("ACTIVE_GROUPS_MUST_BE_LIST")
    for group in groups:
        if not isinstance(group, Mapping):
            raise FrontierCoverageError("ACTIVE_GROUP_INVALID")
        preds = group.get("predicates", [])
        if not isinstance(preds, list):
            raise FrontierCoverageError("ACTIVE_PREDICATES_MUST_BE_LIST")
        for pred in preds:
            if not isinstance(pred, str) or not pred:
                raise FrontierCoverageError("ACTIVE_PREDICATE_INVALID")
            active.add(pred)

    nodes = cut.get("dormant_wake_only", [])
    if not isinstance(nodes, list):
        raise FrontierCoverageError("DORMANT_NODES_MUST_BE_LIST")
    for node in nodes:
        if not isinstance(node, Mapping):
            raise FrontierCoverageError("DORMANT_NODE_INVALID")
        values = node.get("predicates")
        if values is None:
            one = node.get("predicate")
            values = [] if one is None else [one]
        if not isinstance(values, list):
            raise FrontierCoverageError("DORMANT_PREDICATES_MUST_BE_LIST")
        for pred in values:
            if not isinstance(pred, str) or not pred:
                raise FrontierCoverageError("DORMANT_PREDICATE_INVALID")
            dormant.add(pred)

    return active, dormant


def verify_frontier(root_state: Mapping[str, Any], cut: Mapping[str, Any]) -> dict[str, Any]:
    open_set = canonical_open_predicates(root_state)
    active, dormant = scheduled_predicates(cut)
    covered = active | dormant
    missing = sorted(open_set - covered)
    extra = sorted(covered - open_set)

    return {
        "status": "PASS" if not missing and not extra else "FAIL_CLOSED",
        "open_count": len(open_set),
        "active_unique_count": len(active),
        "dormant_unique_count": len(dormant),
        "covered_unique_count": len(covered),
        "missing": missing,
        "extra": extra,
        "active_dormant_overlap": sorted(active & dormant),
    }


def verify_files(root_state_path: str | Path, cut_path: str | Path) -> dict[str, Any]:
    result = verify_frontier(_load(root_state_path), _load(cut_path))
    if result["status"] != "PASS":
        raise FrontierCoverageError(json.dumps(result, sort_keys=True))
    return result


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("root_state")
    parser.add_argument("cut")
    args = parser.parse_args()
    print(json.dumps(verify_files(args.root_state, args.cut), sort_keys=True))


if __name__ == "__main__":
    main()
