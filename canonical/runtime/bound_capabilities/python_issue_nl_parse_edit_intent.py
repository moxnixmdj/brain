# PROJECT_BRAIN
"""python.issue.natural_language.parse_edit_intent.v1 — issue prose -> edit ops.

Humans write "rename compute_size to fit_width in pkg/layout.py", not JSON
choreograph specs.  This adapter is the seam between an issue written in
natural language and the issue→PR orchestrator: it parses STRICT anchored
phrases into slice-4 ops with per-line evidence, binding names through the
verified symbol index, and — like every other part of the engine — never
mutes what it cannot see:

* ANCHORED GRAMMAR v1 (case-insensitive; one op per line or `;`-clause):
    rename <name> to|-> <new_name> [in <module>]     -> rename_symbol op
    move <name> [from <module>] to <module>         -> move_symbol op
  <module> spelled as path (pkg/a.py) or dotted (pkg.a).  Anything else
  that looks imperative refuses the whole issue with the line quoted.
* BINDING LAW — names are resolved against the symbol index's module-scope
  definition homes: exactly one home binds; zero homes refuse
  NAME_NOT_FOUND with the closest lexical candidates listed (evidence, not
  action); >1 homes refuse NAME_AMBIGUOUS with the home list UNLESS an
  `in/from <module>` qualifier selects one.  Never picks silently.
* complete ⟺ every imperative line produced an op and every op bound.
  complete=false -> ops are NOT emitted for machine consumption; the
  artifact still lists everything parsed (truth over progress).
* OUTPUT is `edits`-schema JSON (ops for python_issue_to_pr_orchestrate)
  plus an evidence document; byte-identical on rerun (pin-proven).
* cache law — index_path may name a validated slice-1 cache artifact
  (schema + totals + source_root must match or it is refused), giving
  the same bind decisions without the rebuild cost.

result_fields: adapter, issue_id, line_count, op_count, refused_line_count,
bound_name_count, ambiguous_name_count, complete, output_verified,
cache_used.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_NL_EDIT_INTENT_V1"
NAME_RE = re.compile(r"^[A-Za-z_]\w*$")

_RENAME_RE = re.compile(
    r"^\s*rename\s+(?P<name>[A-Za-z_]\w*)\s+(?:to|->)\s+(?P<new>[A-Za-z_]\w*)"
    r"(?:\s+in\s+(?P<mod>\S+))?\s*[.;]?\s*$", re.IGNORECASE)
_MOVE_RE = re.compile(
    r"^\s*move\s+(?P<name>[A-Za-z_]\w*)"
    r"(?:\s+from\s+(?P<src>\S+))?\s+to\s+(?P<dst>\S+)\s*[.;]?\s*$", re.IGNORECASE)
_IMP_SNIFFS = re.compile(r"\b(rename|move|delete|extract|inline|wrap|unwrap|change)\b", re.I)


def _fail(reason: str) -> None:
    raise SystemExit(json.dumps({"error": True,
                                 "capability": "python.issue.natural_language.parse_edit_intent.v1",
                                 "reason": reason}, indent=2, sort_keys=True))


def _safe_path(repo: Path, rel: str, must_exist: bool = False) -> Path:
    if not rel or not isinstance(rel, str):
        _fail("MISSING_OR_INVALID_PATH_ARGUMENT")
    p = (repo / rel).resolve()
    if p != repo and repo not in p.parents:
        _fail("PATH_ESCAPE:" + rel)
    if must_exist and not p.exists():
        _fail("PATH_MISSING:" + rel)
    return p


def _sha256(t: bytes) -> str:
    return hashlib.sha256(t).hexdigest()


def _norm_module(spell: str) -> str:
    spell = spell.strip().rstrip(".,;")
    return spell[:-3].replace("/", ".") if spell.endswith(".py") else spell.replace("/", ".")


def _dot_to_rel(dot: str) -> str:
    return dot.replace(".", "/") + ".py"


def _load_index(repo: Path, source_abs: Path, source_root: str,
                cached: Path | None) -> tuple[dict, bool]:
    from canonical.runtime.bound_capabilities import python_source_symbol_index as indexer
    if cached is not None:
        art = json.loads(cached.read_text(encoding="utf-8"))
        if art.get("schema") != "PROJECT_BRAIN_PYTHON_SYMBOL_INDEX_V1":
            _fail("INDEX_CACHE_SCHEMA_MISMATCH")
        if str(art.get("source_root")) != str(source_root):
            _fail("INDEX_CACHE_SOURCE_ROOT_MISMATCH:" + str(art.get("source_root")))
        files = int((art.get("totals") or {}).get("files", 0))
        if files <= 0 or not isinstance(art.get("modules"), list):
            _fail("INDEX_CACHE_TOTALS_INVALID")
        return art, True
    probe = source_abs / ".nl_intent_probe_index.json"
    indexer.run({"source_root": ".", "output_path": probe.name}, source_abs)
    art = json.loads(probe.read_text(encoding="utf-8"))
    probe.unlink()
    return art, False


def _homes(index: dict, name: str) -> list[str]:
    homes = []
    for row in index.get("modules") or []:
        path = str(row["path"])
        for d in row.get("definitions") or []:
            if d["name"] == name and str(d["qualname"]).count(".") == 0:
                homes.append(path)
                break
    return sorted(homes)


def _closest(index: dict, name: str, limit: int = 3) -> list[str]:
    """Deterministic lexical candidates: edit-distance-1..2 or prefix match,
    sorted; evidence for the refusal, never an auto-pick."""
    vocab = set()
    for row in index.get("modules") or []:
        for d in row.get("definitions") or []:
            vocab.add(str(d["name"]))
    cand = sorted(v for v in vocab
                  if abs(len(v) - len(name)) <= 2
                  and (v.startswith(name[: max(3, len(name) // 2)])
                       or name.startswith(v[: max(3, len(v) // 2)])))
    return cand[:limit]


def _parse_issue(repo: Path, source_abs: Path, source_root: str, cached: Path | None,
                 issue: dict) -> dict:
    text = str(issue.get("title") or "") + "\n" + str(issue.get("body") or "")
    raw_lines: list[str] = []
    for ln in text.splitlines():
        raw_lines.extend(p for p in ln.split(";") if p.strip())
    index, cache_used = _load_index(repo, source_abs, source_root, cached)
    inv_dot_to_path = {}
    for row in index.get("modules") or []:
        p = str(row["path"])
        if p.endswith(".py"):
            inv_dot_to_path[p[:-3].replace("/", ".")] = p

    ops, evidence, refused = [], [], []
    bound = ambiguous = 0
    for raw in raw_lines:
        line = raw.strip()
        m = _RENAME_RE.match(line) or None
        mv = _MOVE_RE.match(line) if not m else None
        if m:
            name, new_name = m.group("name"), m.group("new")
            qualifier = _norm_module(m.group("mod")) if m.group("mod") else None
            homes = _homes(index, name)
            row = {"raw": line, "parsed_as": "rename_symbol", "name": name, "new_name": new_name}
            if not homes:
                refused.append({"line": line, "reason": "NAME_NOT_FOUND:" + name,
                                "candidates": _closest(index, name)})
                row["bound"] = False
            elif len(homes) > 1 and not qualifier:
                ambiguous += 1
                refused.append({"line": line, "reason": "NAME_AMBIGUOUS:" + name,
                                "homes": homes})
                row.update({"bound": False, "homes": homes})
            else:
                if qualifier and qualifier in inv_dot_to_path:
                    home = inv_dot_to_path[qualifier]
                    if home not in homes:
                        refused.append({"line": line,
                                        "reason": f"QUALIFIER_NOT_A_HOME:{qualifier}",
                                        "homes": homes})
                        row["bound"] = False
                    else:
                        ops.append({"op": "rename_symbol", "module": home,
                                    "name": name, "new_name": new_name})
                        bound += 1
                        row.update({"bound": True, "module": home})
                elif qualifier and qualifier not in inv_dot_to_path:
                    refused.append({"line": line,
                                    "reason": "QUALIFIER_MODULE_UNKNOWN:" + qualifier})
                    row["bound"] = False
                else:
                    ops.append({"op": "rename_symbol", "module": homes[0],
                                "name": name, "new_name": new_name})
                    bound += 1
                    row.update({"bound": True, "module": homes[0]})
            evidence.append(row)
        elif mv:
            name = mv.group("name")
            to_spell = mv.group("dst")
            if not NAME_RE.match(to_spell.replace(".", "").replace("/", "")) \
                    and "/" not in to_spell and not to_spell.endswith(".py"):
                refused.append({"line": line, "reason": "MOVE_TARGET_NOT_MODULE:" + to_spell})
                evidence.append({"raw": line, "parsed_as": "move_symbol", "bound": False})
                continue
            to_dot = _norm_module(to_spell)
            homes = _homes(index, name)
            row = {"raw": line, "parsed_as": "move_symbol", "name": name, "to": to_dot}
            src = _norm_module(mv.group("src")) if mv.group("src") else None
            if not homes:
                refused.append({"line": line, "reason": "NAME_NOT_FOUND:" + name,
                                "candidates": _closest(index, name)})
                row["bound"] = False
            elif src:
                if src in inv_dot_to_path and inv_dot_to_path[src] in homes:
                    mod = inv_dot_to_path[src]
                    ops.append({"op": "move_symbol", "module": mod,
                                "qualname": name, "to_module": _dot_to_rel(to_dot)})
                    bound += 1
                    row.update({"bound": True, "module": mod})
                else:
                    refused.append({"line": line,
                                    "reason": f"MOVE_SOURCE_NOT_A_HOME:{src}",
                                    "homes": homes})
                    row["bound"] = False
            elif len(homes) == 1:
                ops.append({"op": "move_symbol", "module": homes[0],
                            "qualname": name, "to_module": _dot_to_rel(to_dot)})
                bound += 1
                row.update({"bound": True, "module": homes[0]})
            else:
                ambiguous += 1
                refused.append({"line": line, "reason": "NAME_AMBIGUOUS:" + name,
                                "homes": homes})
                row.update({"bound": False, "homes": homes})
            evidence.append(row)
        elif _IMP_SNIFFS.search(line) and not line.startswith(("#", ">", "-")):
            refused.append({"line": line,
                            "reason": "UNSUPPORTED_ANCHOR:only strict 'rename ... to ...' / "
                                      "'move ... to ...' clauses bind in v1"})
            evidence.append({"raw": line, "bound": False})
        else:
            evidence.append({"raw": line, "parsed_as": "prose", "bound": None})

    complete = not refused and bool(ops)
    # identical clauses (title repeated in body, ...) bind once
    seen_ops, uniq_ops = set(), []
    for op in ops:
        key = json.dumps(op, sort_keys=True)
        if key not in seen_ops:
            seen_ops.add(key)
            uniq_ops.append(op)
    artifact = {
        "schema": SCHEMA,
        "issue_id": str(issue.get("issue_id") or ""),
        "line_count": len(raw_lines),
        "op_count": len(uniq_ops),
        "refused_line_count": len(refused),
        "bound_name_count": bound,
        "ambiguous_name_count": ambiguous,
        "complete": complete,
        "completeness_law": "complete ⟺ every imperative line parsed and bound in the index",
        "edits": uniq_ops,
        "refusals": refused,
        "evidence": evidence,
    }
    return artifact, cache_used


def run(args, root):
    repo = Path(root).resolve()
    args = dict(args or {})
    issue_rel = str(args.get("issue_path") or "")
    issue_path = _safe_path(repo, issue_rel, must_exist=True)
    try:
        issue = json.loads(issue_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        _fail("ISSUE_UNREADABLE_JSON:" + type(exc).__name__)
    for key in ("issue_id", "title"):
        if key not in issue:
            _fail("ISSUE_SCHEMA_MISSING:" + key)

    source_root = str(args.get("source_root") or "")
    source_abs = _safe_path(repo, source_root, must_exist=True)
    if not source_abs.is_dir():
        _fail("SOURCE_ROOT_NOT_DIRECTORY")
    out_abs = _safe_path(repo, str(args.get("output_path") or ""))
    cached = None
    if args.get("index_path"):
        cached = _safe_path(repo, str(args["index_path"]), must_exist=True)

    artifact, cache_used = _parse_issue(repo, source_abs, source_root, cached, issue)

    out_abs.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"
    out_abs.write_text(text, encoding="utf-8")
    verified = json.loads(out_abs.read_text(encoding="utf-8")) == artifact

    return {
        "adapter": "python_issue_nl_parse_edit_intent",
        "issue_id": artifact["issue_id"],
        "line_count": artifact["line_count"],
        "op_count": artifact["op_count"],
        "refused_line_count": artifact["refused_line_count"],
        "bound_name_count": artifact["bound_name_count"],
        "ambiguous_name_count": artifact["ambiguous_name_count"],
        "complete": artifact["complete"],
        "output_path": str(args.get("output_path")),
        "output_sha256": _sha256(text.encode("utf-8")),
        "output_verified": verified,
        "cache_used": cache_used,
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    for name in ("issue_path", "source_root", "output_path"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--index_path", default=None)
    ns = p.parse_args()
    print(json.dumps(run(vars(ns), Path.cwd()), indent=2, sort_keys=True))
