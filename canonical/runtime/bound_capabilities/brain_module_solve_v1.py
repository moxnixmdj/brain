"""Find the Brain function that fits a task description AND a payload, then run it read-only.

    Use a Brain function for the task "classify whether the claim is supported by the evidence"
    on the payload claims.json and save the result to out.json.

Selection is deterministic and explained in the output record:

1. Signature fit (typed, strong): the payload must be callable on the function exactly as
   ``brain_module_invoke_runner_v1`` would bind it.  A JSON object whose keys are parameter names
   (``EXACT_KWARGS``) beats a single positional argument (``POSITIONAL``) or an empty payload for a
   function without required parameters (``NO_ARGUMENTS``).  Incompatible functions are never chosen.
2. Description fit: IDF-weighted overlap between the task words and the function's name, docstring,
   module name, module docstring and parameter names.  Zero overlap fails closed.
3. Ambiguity fails closed: if a function from a DIFFERENT family (module name without its version
   suffix) scores within 10% of the best, nothing runs and the candidates are listed.  Versions of
   the same family resolve to TEST_EVIDENCED first, then most passing cases, then newest version;
   the alternatives are recorded.

Execution, pins and tiers are exactly those of ``brain_module_invoke_v1``.
"""
from __future__ import annotations

import json
import math
import pathlib
import re
from typing import Any

from canonical.runtime.bound_capabilities import brain_module_invoke_v1 as invoker

CAPABILITY_ID = "brain.module.function.solve"
AMBIGUITY_RATIO = 0.9
_STOP = frozenset("""a an and are as at be by for from has have in into is it its of on or that the this to was
were will with use using brain function task payload result save write file json given whether""".split())
_COMPAT_RANK = {"EXACT_KWARGS": 3, "NO_ARGUMENTS": 2, "POSITIONAL": 1}


def _stem(word: str) -> str:
    for suffix in ("ing", "ies", "ed", "es", "s"):
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)] + ("y" if suffix == "ies" else "")
    return word


def tokens(text: str) -> list[str]:
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(text or ""))
    return [_stem(w) for w in re.findall(r"[a-z0-9]+", text.lower().replace("_", " ")) if len(w) > 2 and w not in _STOP and not w.isdigit()]


def family(rel: str) -> str:
    return re.sub(r"(_v\d+)+$", "", pathlib.PurePosixPath(rel).stem)


def _version(rel: str) -> int:
    m = re.search(r"_v(\d+)$", pathlib.PurePosixPath(rel).stem)
    return int(m.group(1)) if m else 0


def compatibility(sig: dict[str, Any], payload: Any) -> str | None:
    params, required = set(sig.get("params") or []), list(sig.get("required") or [])
    if isinstance(payload, dict) and payload and (set(payload) <= params or sig.get("var_kw")):
        if all(r in payload or r in ("root", "repo_root") for r in required):
            return "EXACT_KWARGS"
        return None
    if payload in ({}, None):
        return "NO_ARGUMENTS" if not required else None
    return "POSITIONAL" if len(required) == 1 else None


def _documents(evidence: dict[str, Any]) -> list[tuple[str, str, dict[str, Any], dict[str, list[str]]]]:
    docs = []
    for rel, row in evidence["modules"].items():
        for fname, fn in row["functions"].items():
            fields = {
                "name": tokens(fname),
                "doc": tokens(fn.get("doc", "")),
                "module": tokens(family(rel)),
                "module_doc": tokens(row.get("doc", "")),
                "params": tokens(" ".join((fn.get("signature") or {}).get("params") or [])),
            }
            docs.append((rel, fname, fn, fields))
    return docs


_WEIGHTS = {"name": 3.0, "doc": 2.0, "module": 1.5, "module_doc": 1.0, "params": 1.0}


_INDEX: dict[int, tuple[Any, list, dict[str, int]]] = {}


def _index(evidence: dict[str, Any]) -> tuple[list, dict[str, int]]:
    """Documents + document frequencies, built once per loaded evidence object."""
    hit = _INDEX.get(id(evidence))
    if hit is not None and hit[0] is evidence:
        return hit[1], hit[2]
    docs = _documents(evidence)
    df: dict[str, int] = {}
    for *_, fields in docs:
        for w in set().union(*fields.values()):
            df[w] = df.get(w, 0) + 1
    _INDEX.clear()
    _INDEX[id(evidence)] = (evidence, docs, df)
    return docs, df


def rank(task: str, payload: Any, evidence: dict[str, Any]) -> list[dict[str, Any]]:
    docs, df = _index(evidence)
    n = len(docs)
    want = set(tokens(task))
    out = []
    for rel, fname, fn, fields in docs:
        compat = compatibility(fn.get("signature") or {}, payload)
        if compat is None:
            continue
        score = 0.0
        for w in want:
            idf = math.log(1 + n / (1 + df.get(w, 0)))
            score += idf * max((_WEIGHTS[k] for k, toks in fields.items() if w in toks), default=0.0)
        out.append({"source_path": rel, "function": fname, "compatibility": compat, "score": round(score, 6),
                    "tier": fn["tier"], "passing_cases": fn.get("passing_cases", 0), "family": family(rel)})
    out.sort(key=lambda c: (-_COMPAT_RANK[c["compatibility"]], -c["score"], c["tier"] != invoker.TIER_TESTED,
                            -c["passing_cases"], -_version(c["source_path"]), c["source_path"], c["function"]))
    return out


def select(task: str, payload: Any, evidence: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not tokens(task):
        raise invoker.ModuleInvokeRefused("TASK_DESCRIPTION_REQUIRED")
    ranked = rank(task, payload, evidence)
    if not ranked:
        raise invoker.ModuleInvokeRefused("NO_FUNCTION_ACCEPTS_THIS_PAYLOAD")
    best_class = _COMPAT_RANK[ranked[0]["compatibility"]]
    pool = [c for c in ranked if _COMPAT_RANK[c["compatibility"]] == best_class]
    top = pool[0]
    if top["score"] <= 0:
        raise invoker.ModuleInvokeRefused("NO_FUNCTION_MATCHES_THE_TASK_DESCRIPTION:%d_signature_compatible" % len(pool))
    rivals = [c for c in pool[1:] if c["family"] != top["family"] and c["score"] >= AMBIGUITY_RATIO * top["score"]]
    if rivals:
        listed = "; ".join("%s:%s(%.2f)" % (c["source_path"], c["function"], c["score"]) for c in [top] + rivals[:4])
        raise invoker.ModuleInvokeRefused("AMBIGUOUS_TASK__NAME_THE_MODULE_OR_REFINE_THE_TASK: " + listed)
    alternatives = [c for c in pool[1:6]]
    return top, alternatives


def run(args: dict[str, Any], root: Any) -> dict[str, Any]:
    root = pathlib.Path(root).resolve()
    task = str(args.get("task") or "").strip()
    payload_path = invoker._repo_path(root, args.get("json_path"))
    output = invoker._repo_path(root, args.get("output_path"))
    if output == payload_path:
        raise invoker.ModuleInvokeRefused("OUTPUT_PATH_EQUALS_AN_INPUT")
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    evidence = invoker.load_evidence(root)
    top, alternatives = select(task, payload, evidence)
    adm = invoker.admitted(root, top["source_path"], top["function"], evidence)
    result = invoker.invoke(root, top["source_path"], top["function"], payload)
    selected_by = {"task": task, "chosen": top, "next_candidates": alternatives,
                   "rule": "signature fit, then IDF description overlap; different-family tie within 10% fails closed"}
    status = invoker.write_record(root, output, top["source_path"], top["function"], adm, payload_path, result,
                                  extra={"capability_id": CAPABILITY_ID, "selected_by": selected_by})
    status["selected"] = "%s:%s" % (top["source_path"], top["function"])
    return status
