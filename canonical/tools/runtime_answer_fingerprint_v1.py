"""Fingerprint every runtime answer, so a deletion can be proved to have changed none of them.

A deletion PR is only safe if it can be shown to be a deletion: the cheapest possible
predicate is *the runtime answers the same questions the same way, and the answers hash the
same*. This tool asks the unified model the 404 exact-target questions and records the
ordered top-5 ids plus the digest of the whole transcript.

    python3 canonical/tools/runtime_answer_fingerprint_v1.py --out BEFORE.json
    # ... delete something ...
    python3 canonical/tools/runtime_answer_fingerprint_v1.py --check BEFORE.json

``UNCHANGED`` means the deletion removed code that no runtime path reached. ``CHANGED``
prints how many of the 404 answers moved, which is the number the deletion's kill criterion
is actually written against.

No model, no network, no execution of the targets: `find_source` and `route` are index reads.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import pathlib
import re
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

LEDGER = "canonical/verification/PROMOTION_LEDGER_20261127_V1.json"
TEST_DIR = "canonical/tests"
SCHEMA = "PROJECT_BRAIN_RUNTIME_ANSWER_FINGERPRINT_V1"
DEFAULT_OUT = ROOT / "canonical/verification/RUNTIME_ANSWER_FINGERPRINT_20261127_V1.json"
_VERSION = re.compile(r"_?v\d+$|_\d{8}$")


def query_for(test_path: pathlib.Path) -> str:
    """The test author's statement of intent: docstring plus test names, version suffixes stripped."""
    tree = ast.parse(test_path.read_text(encoding="utf-8", errors="replace"))
    parts = [(ast.get_docstring(tree) or "").strip()]
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            parts.append(_VERSION.sub("", node.name[len("test_"):].replace("_", " ")))
    return " ".join(p for p in parts if p).strip()


def questions(root: pathlib.Path) -> list[dict[str, str]]:
    ledger = json.loads((root / LEDGER).read_text())
    rows = sorted((r for r in ledger["rows"] if r["category"] == "SOURCE_ONLY"), key=lambda r: r["path"])
    out: list[dict[str, str]] = []
    for row in rows:
        stem = row["stem"]
        test_path = root / TEST_DIR / f"test_{stem}.py"
        if not test_path.is_file():
            continue
        query = query_for(test_path)
        if query:
            out.append({"module": row["path"], "stem": stem, "query": query})
    return out


def _ids(result: Any) -> list[str]:
    if not isinstance(result, dict):
        return []
    return [str(c.get("path") or c.get("id") or "") for c in result.get("candidates") or []]


def fingerprint(root: pathlib.Path = ROOT, *, top_k: int = 5) -> dict[str, Any]:
    from canonical.runtime import brain_unified_model_v1 as U

    model = U.UnifiedModel(U.load_model(root=root))
    rows = questions(root)
    asked: list[dict[str, Any]] = []
    for row in rows:
        found = _ids(model.find_source(row["query"], top_k=top_k))
        routed = _ids(model.route(row["query"], top_k=top_k))
        asked.append({"module": row["module"], "stem": row["stem"], "find": found, "route": routed})
    payload = json.dumps(asked, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "schema": SCHEMA,
        "n": len(asked),
        "digest": hashlib.sha256(payload).hexdigest(),
        "empty_find": sum(1 for a in asked if not a["find"]),
        "empty_route": sum(1 for a in asked if not a["route"]),
        "answers": asked,
    }


def compare(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    # Keyed by module path, not stem: two ledger rows share a stem, and keying by stem let one
    # shadow the other -- 404 rows, 403 keys.
    prior = {a["module"]: a for a in before.get("answers") or []}
    moved = [a["module"] for a in after.get("answers") or []
             if prior.get(a["module"]) != a]
    # A digest match is not enough: a hand-edited transcript can keep the digest, so the verdict
    # is "unchanged" only if both agree. The test for this caught the first version.
    same = before["digest"] == after["digest"] and not moved
    return {
        "verdict": "UNCHANGED" if same else "CHANGED",
        "before_digest": before["digest"],
        "after_digest": after["digest"],
        "n_before": before["n"],
        "n_after": after["n"],
        "answers_moved": len(moved),
        "moved_stems": moved[:20],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None)
    parser.add_argument("--check", default=None, help="path to a prior fingerprint; compare instead of writing")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args(argv)

    current = fingerprint(ROOT, top_k=args.top_k)
    if args.check:
        before = json.loads(pathlib.Path(args.check).read_text())
        verdict = compare(before, current)
        print(json.dumps(verdict, indent=1))
        return 0 if verdict["verdict"] == "UNCHANGED" else 1

    out = pathlib.Path(args.out) if args.out else DEFAULT_OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(current, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"digest": current["digest"], "n": current["n"],
                      "empty_find": current["empty_find"], "empty_route": current["empty_route"],
                      "out": str(out)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
