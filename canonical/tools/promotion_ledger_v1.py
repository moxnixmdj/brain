"""What stands between a module in this tree and a call from the runtime.

The atlas measured how far the model can *reach*: 1,260 domain candidates, 1,005 indexed,
337 executable, 28 invisible. It did not say what the missing attribute is in each case, so
every later play was guessing whether it needed new code, a receipt, or a line of
bookkeeping.

This ledger asks that question once, per module, and answers with the first attribute that
is missing, in the order the runtime actually requires them:

1. ``ROUTED``            the model exposes it as a capability and it carries a receipt
2. ``ROUTED_NO_RECEIPT`` a capability, but nothing in the tree says it ran
3. ``RECEIPTED_UNBOUND`` it ran and was receipted, and is not in the bound registry --
                         **promotable with no new code**
4. ``ADAPTER_UNRECEIPTED`` an adapter file exists in ``bound_capabilities`` with no receipt
5. ``SOURCE_ONLY``       the module is indexed as source and needs a thin adapter
6. ``INVISIBLE``         no route, no receipt, no index entry

Nothing here executes anything: it is a join over four artifacts that already exist plus
the AST-level presence of adapter files. The point is to move the bottleneck from "we
should build capability" to "we can promote it", and to say how much of each is left.
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import sys
from collections import Counter, defaultdict
from typing import Any, Mapping

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.tools import domain_atlas_v1 as A  # noqa: E402

SCHEMA = "PROJECT_BRAIN_PROMOTION_LEDGER_V1"
ADAPTER_DIR = "canonical/runtime/bound_capabilities"

CATEGORIES = (
    "ROUTED",
    "ROUTED_NO_RECEIPT",
    "RECEIPTED_UNBOUND",
    "ADAPTER_UNRECEIPTED",
    "SOURCE_ONLY",
    "INVISIBLE",
)


def _stems_of(values) -> set[str]:
    return {str(v) for v in values if v}


def load_world(root: pathlib.Path = ROOT) -> dict[str, Any]:
    """Read the four artifacts and the adapter directory. No execution, no model."""
    model = json.loads((root / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json").read_text())
    registry = json.loads((root / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
    receipts = json.loads((root / "canonical/runtime/CAPABILITY_RECEIPT_PROJECTION_V1.json").read_text())
    atlas = json.loads((root / "canonical/unified_model/DOMAIN_ATLAS_V1.json").read_text())

    bound = registry.get("capabilities") or {}
    receipted = receipts.get("entries") or {}
    capabilities = {row.get("id"): row for row in model.get("capabilities") or [] if isinstance(row, dict)}

    routed_stems = _stems_of(
        [row.get("adapter_module") for row in capabilities.values()]
        + [str(cid).split(".auto.")[0].split("/")[-1].removesuffix(".py") for cid in capabilities]
    )
    bound_stems = _stems_of([row.get("adapter_module") for row in bound.values() if isinstance(row, dict)])
    receipt_stems = _stems_of([row.get("adapter_module") for row in receipted.values() if isinstance(row, dict)])
    receipted_capabilities = set(receipted)
    adapter_files = {p.stem for p in (root / ADAPTER_DIR).glob("*.py")} if (root / ADAPTER_DIR).is_dir() else set()
    return {
        "capabilities": capabilities,
        "bound": bound,
        "receipted": receipted,
        "receipted_capabilities": receipted_capabilities,
        "atlas": atlas,
        "routed_stems": routed_stems,
        "bound_stems": bound_stems,
        "receipt_stems": receipt_stems,
        "adapter_files": adapter_files,
    }


def classify(stem: str, *, routed: set[str], receipted: set[str], adapter_files: set[str],
             indexed: bool) -> str:
    """The first attribute the runtime is missing, in the order it needs them."""
    if stem in routed and stem in receipted:
        return "ROUTED"
    if stem in routed:
        return "ROUTED_NO_RECEIPT"
    if stem in receipted:
        return "RECEIPTED_UNBOUND"
    if stem in adapter_files:
        return "ADAPTER_UNRECEIPTED"
    if indexed:
        return "SOURCE_ONLY"
    return "INVISIBLE"


def build(root: pathlib.Path = ROOT, *, per_domain: int = 400) -> dict[str, Any]:
    world = load_world(root)
    # The atlas needs the compiled model to know what the source index already covers; without
    # it every row comes back unindexed and the ledger blames the wrong attribute.
    raw_model = json.loads((root / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json").read_text())
    atlas = A.build_atlas(root, model=raw_model, per_domain=per_domain)
    seen: dict[str, dict[str, Any]] = {}
    per_domain: dict[str, Counter] = defaultdict(Counter)
    for domain, payload in atlas["domains"].items():
        for row in payload["top"]:
            rel = row["path"]
            stem = pathlib.PurePosixPath(rel).stem
            category = classify(
                stem,
                routed=world["routed_stems"],
                receipted=world["receipt_stems"],
                adapter_files=world["adapter_files"],
                indexed=bool(row.get("source_index")),
            )
            per_domain[domain][category] += 1
            entry = seen.get(rel)
            if entry is None:
                seen[rel] = {"path": rel, "stem": stem, "domains": [domain], "category": category,
                             "score": row["score"]}
            else:
                entry["domains"].append(domain)
                # A module is as callable as its best category.
                if CATEGORIES.index(category) < CATEGORIES.index(entry["category"]):
                    entry["category"] = category

    rows = sorted(seen.values(), key=lambda r: (CATEGORIES.index(r["category"]), -r["score"], r["path"]))
    totals = Counter(r["category"] for r in rows)
    callable_now = totals["ROUTED"]
    promotable = sorted(
        cid for cid, row in world["receipted"].items()
        if isinstance(row, dict) and str(row.get("adapter_module") or "") in
        {r["stem"] for r in rows if r["category"] == "RECEIPTED_UNBOUND"}
    )
    domain_executable_now = {
        domain: sum(1 for r in rows if domain in r["domains"] and r["category"] == "ROUTED")
        for domain in atlas["domains"]
    }
    domain_executable_after = {
        domain: sum(1 for r in rows if domain in r["domains"] and r["category"] in {"ROUTED", "RECEIPTED_UNBOUND"})
        for domain in atlas["domains"]
    }
    return {
        "schema": SCHEMA,
        "date_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": (
            "join over the compiled model's capabilities, the bound registry, the receipt projection, the adapter "
            "directory and the atlas, assigning each candidate the first attribute the runtime is missing"
        ),
        "order": list(CATEGORIES),
        "candidates": len(rows),
        "totals": {c: totals[c] for c in CATEGORIES},
        "callable_now": callable_now,
        "callable_share": round(callable_now / max(1, len(rows)), 3),
        "promotable_capabilities": promotable,
        "promotable_count": len(promotable),
        "domain_executable_now": domain_executable_now,
        "domain_executable_if_promoted": domain_executable_after,
        "per_domain": {d: {c: counts[c] for c in CATEGORIES} for d, counts in per_domain.items()},
        "next_actions": [
            {"action": "promote_receipted_unbound", "count": len(promotable), "new_code": False},
            {"action": "receipt_existing_adapters", "count": totals["ADAPTER_UNRECEIPTED"], "new_code": False},
            {"action": "write_thin_adapters", "count": totals["SOURCE_ONLY"], "new_code": True},
            {"action": "index_invisible", "count": totals["INVISIBLE"], "new_code": False},
        ],
        "claim_limit": (
            "The ledger says which attribute is missing, not that the module works: a receipt proves one observed "
            "effect, and the absence of one proves only that nothing recorded a run. Nothing here executed a module."
        ),
        "model_calls": 0,
        "network_calls": 0,
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--out", default="canonical/verification/PROMOTION_LEDGER_20261127_V1.json")
    ap.add_argument("--per-domain", type=int, default=400)
    args = ap.parse_args(argv)
    report = build(pathlib.Path(args.root), per_domain=args.per_domain)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "candidates", "totals", "callable_now", "callable_share", "promotable_count",
        "domain_executable_now", "domain_executable_if_promoted", "next_actions")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
