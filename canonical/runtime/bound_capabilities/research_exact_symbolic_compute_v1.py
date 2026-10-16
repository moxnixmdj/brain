"""Exact symbolic computation over a typed case list, using SymPy.

Reuses ``execute`` from canonical/research/bytes/tools/exact_symbolic_route_v1.py and ``digest``
from semantic_digest_v1.py.  Input JSON: ``{"cases": [{"op": ..., "p": ...}, ...]}``.  Only the
operations whose results were checked by an independent exact-arithmetic oracle are accepted.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

from canonical.runtime.bound_capabilities import research_tool_loader_v1 as loader

SOURCE = "canonical/research/bytes/tools/exact_symbolic_route_v1.py"
DIGEST_SOURCE = "canonical/research/bytes/tools/semantic_digest_v1.py"
SCHEMA = "PROJECT_BRAIN_EXACT_SYMBOLIC_RESULTS_V1"
SUPPORTED_OPS = ("rat", "factor", "coeff", "roots", "diff", "sin_even_integral", "hilbert_det",
                 "binomial_identity", "limit_poly_ratio", "limit_sinx", "linear_solve", "series_coeff")
MAX_CASES = 2000


def run(args, root):
    root = pathlib.Path(root).resolve()
    src = loader.safe_repo_path(root, args.get("input_path"))
    out = loader.safe_repo_path(root, args.get("output_path"))
    if not src.is_file() or src.suffix.lower() != ".json":
        raise RuntimeError("JSON_INPUT_REQUIRED")
    if out.suffix.lower() != ".json" or out == src:
        raise RuntimeError("DISTINCT_JSON_OUTPUT_REQUIRED")
    doc = json.loads(src.read_text(encoding="utf-8"))
    cases = doc.get("cases") if isinstance(doc, dict) else None
    if not isinstance(cases, list) or not cases or len(cases) > MAX_CASES:
        raise RuntimeError("CASES_LIST_REQUIRED_1_TO_%d" % MAX_CASES)
    for i, case in enumerate(cases):
        if not isinstance(case, dict) or case.get("op") not in SUPPORTED_OPS or not isinstance(case.get("p"), list):
            raise RuntimeError("CASE_INVALID_OR_UNSUPPORTED_OP:%d" % i)
    execute = loader.load_symbol(root, SOURCE, "execute")
    digest = loader.load_symbol(root, DIGEST_SOURCE, "digest")
    results = []
    for case in cases:
        value = execute({"op": case["op"], "p": case["p"]})
        results.append({"op": case["op"], "p": case["p"], "result_text": str(value), "result_digest": digest(value)})
    payload = {"schema": SCHEMA, "input_path": src.relative_to(root).as_posix(), "case_count": len(results), "results": results}
    raw = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)
    verified = json.loads(out.read_text(encoding="utf-8"))["case_count"] == len(cases)
    return {
        "adapter": "research_exact_symbolic_compute_v1",
        "status": "PASS" if verified else "FAIL",
        "input_path": payload["input_path"],
        "case_count": len(results),
        "output_path": out.relative_to(root).as_posix(),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": verified,
        "research_source": SOURCE,
    }
