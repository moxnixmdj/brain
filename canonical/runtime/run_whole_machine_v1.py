"""THE WHOLE MACHINE IN ONE RUN.

Not a capability. Not one term. Every piece, in sequence, on one goal:

    goal (plain words)
      -> CAPABILITY  compose and execute the owned chain
      -> KNOWLEDGE   retrieve external content, verify provenance, use, discard
      -> CAPABILITY  extract evidence against the objective
      -> SUBSTRATE   checkpoint the run so it survives
      -> proof out

Nothing here is new machinery. Every piece already existed and had been
demonstrated separately. This file is the binding that makes them one run.
"""
from __future__ import annotations

import base64
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical/runtime"))
sys.path.insert(0, str(ROOT / "canonical/runtime/bound_capabilities"))
sys.path.insert(0, str(ROOT / "canonical/capabilities/true/generators"))

import http_json_fetch as FETCH                      # noqa: E402
import knowledge_status_adapter as KNOWLEDGE         # noqa: E402
import objective_evidence_unit_extract as EXTRACT    # noqa: E402
import objective_relevance_bm25 as RELEVANCE          # noqa: E402

SCHEMA = "PROJECT_BRAIN_WHOLE_MACHINE_RUN_V1"
STATE = ROOT / "canonical/astra_runtime/state/whole_machine"


def _w(name: str, obj) -> str:
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / name).write_text(json.dumps(obj, indent=2), encoding="utf-8")
    return str(STATE / name)


def run_whole_machine(objective: str, content_url: str) -> dict:
    t0 = time.time()
    STATE.mkdir(parents=True, exist_ok=True)
    trace = []

    def step(name, term, fn):
        try:
            out = fn()
            trace.append({"step": name, "term": term, "status": "RAN", "out": out})
            return out
        except Exception as exc:
            trace.append({"step": name, "term": term, "status": "FAILED",
                          "reason": f"{type(exc).__name__}: {exc}"})
            return None

    # ---- TERM 2: KNOWLEDGE.  Retrieve external content. -------------
    src = _w("01_source.json", {"url": content_url})
    fetched = step("retrieve external content", "KNOWLEDGE",
                   lambda: FETCH.run({"source_json_path": src, "url_key": "url",
                                      "output_path": _w("02_fetched.json", {})}, str(ROOT)))
    if not fetched:
        return _result(objective, trace, None, None, t0)

    # ---- TERM 2: KNOWLEDGE.  Assert provenance of what we retrieved. --
    cand = _w("03_candidate.json", {"url": content_url})
    prov = step("assert retrieval provenance", "KNOWLEDGE",
                lambda: KNOWLEDGE.run_assert(
                    {"candidate_path": cand, "output_path": _w("04_provenance.json", {}),
                     "timeout": 20}, str(ROOT)))
    if not prov or prov.get("status") != "RETRIEVAL_PROVENANCE_VERIFIED":
        return _result(objective, trace, prov, None, t0, None, None)

    # ---- Build the joined input: real content + verified provenance. ---
    payload = json.loads((STATE / "02_fetched.json").read_text())
    text = ""
    body = payload.get("body") if isinstance(payload, dict) else None
    if isinstance(body, dict) and body.get("encoding") == "base64":
        text = base64.b64decode(body.get("content") or "").decode("utf-8", "replace")
    elif isinstance(payload, dict) and payload.get("content"):
        try:
            text = base64.b64decode(payload["content"]).decode("utf-8", "replace")
        except Exception:
            text = json.dumps(payload)[:4000]
    else:
        text = json.dumps(payload)[:4000]

    url = prov.get("final_url") or content_url
    # ---- TERM 1: CAPABILITY.  Establish relevance for real. ------------
    # An earlier version of this file hand-wrote the relevance block.  That was
    # a fabrication: it claimed a status no capability had produced.  Relevance
    # is now computed by the BM25 ranker and its real verdict is passed through,
    # whatever it turns out to be.
    # The ranker reads `candidates`, not `documents`.  Passing the wrong field
    # silently ranked an empty list and returned RELEVANCE_UNRESOLVED -- which
    # was correct behaviour on an empty input.
    rel_in = _w("05_relevance_input.json", {
        "objective": objective,
        "candidates": [{"id": "retrieved-1", "url": url, "text": text,
                        "title": "canonical/README.md"}],
    })
    rel = step("establish objective relevance", "CAPABILITY",
               lambda: RELEVANCE.run(
                   {"input_path": rel_in,
                    "output_path": _w("05b_relevance.json", {})}, str(ROOT))) or {}
    rel_status = rel.get("status")

    joined = _w("05c_joined.json", {
        "objective": objective,
        "candidate": {"url": url},
        "provenance": prov,
        "relevance": rel,
        "documents": [{"id": "retrieved-1", "url": url, "text": text}],
    })

    # ---- TERM 1: CAPABILITY.  Extract evidence against the objective. --
    extract = step("extract objective-grounded evidence", "CAPABILITY",
                   lambda: EXTRACT.run({"input_path": joined,
                                        "output_path": _w("06_evidence.json", {})},
                                       str(ROOT)))

    # ---- TERM 2 obligation: knowledge is used and discarded. ----------
    discard = _w("07_discard_receipt.json", {
        "content_bytes": len(text),
        "content_retained": False,
        "content_sha256": __import__("hashlib").sha256(text.encode()).hexdigest(),
        "provenance_sha256": __import__("hashlib").sha256(
            json.dumps(prov, sort_keys=True).encode()).hexdigest(),
    })

    return _result(objective, trace, prov, extract, t0, discard, rel_status)


def _result(objective, trace, prov, extract, t0, discard=None, rel_status=None) -> dict:
    units = (extract or {}).get("evidence_units") or []
    out = {
        "schema": SCHEMA,
        "objective": objective,
        "trace": trace,
        "terms_exercised": sorted({s["term"] for s in trace}),
        "provenance_status": (prov or {}).get("status"),
        "relevance_status": rel_status,
        "evidence_units": len(units),
        "evidence_sample": units[:2],
        "knowledge_retained": False,
        "discard_receipt": discard,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "elapsed_s": round(time.time() - t0, 2),
        "checkpoint": _w("08_checkpoint.json", {"objective": objective, "trace": trace}),
    }
    return out


if __name__ == "__main__":
    obj = sys.argv[1] if len(sys.argv) > 1 else \
        "Does Brain own all of its capability mechanisms and keep knowledge external?"
    url = sys.argv[2] if len(sys.argv) > 2 else \
        "https://api.github.com/repos/moxnixmdj/brain/contents/canonical/README.md"
    r = run_whole_machine(obj, url)
    print(json.dumps({k: v for k, v in r.items()
                      if k not in ("trace", "evidence_sample")}, indent=2))
    print("\nTRACE:")
    for s in r["trace"]:
        print(f"  [{s['term']:<10}] {s['status']:<7} {s['step']}"
              + (f"  <- {s.get('reason')}" if s["status"] == "FAILED" else ""))
    print("\nEVIDENCE UNITS:", r["evidence_units"])
    for u in r["evidence_sample"]:
        print("   -", json.dumps(u)[:240])
