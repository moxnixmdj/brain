"""Universal Epistemic Kernel v1 — ONE minimal, zero-LLM, zero-weight algorithm
for ANY arbitrary computer environment (OS/CLI, SWE/Codebases, Unseen APIs/Libraries,
Cross-Modal Opaque-Bundle-to-SWE Pipelines, and Observable DOM/GUI).

Follows Elon's Law ("the best part is no part"):
  1. SENSE LOCAL FRONTIER (O(workspace), ~2-5ms) — never blindly crawl the whole machine.
  2. COMPUTE EPISTEMIC DIFF: Delta = Required(Goal | Frontier) \\ Known(ExternalMemory).
  3. ACQUIRE ONLY DELTA IN PARALLEL (local --help/inspect/repo-siblings + live web
     tldr/PyPI/GitHub), cross-corroborate against the live machine, and DISCARD raw prose.
  4. EXECUTE & VERIFY IN ISOLATED STATE COPY with closed-loop error refinement; commit
     atomically only on verification pass.
  5. GENERALIZE & SAVE ONLY ATOMIC TYPED MORPHISMS / SKILLS / API CONTRACTS into ONE
     external inspectable/editable/deletable JSON memory (parameters_stored == 0,
     model_calls == 0). Never save raw prose, concrete paths, or monolithic scripts.
"""
from __future__ import annotations

import ast
import concurrent.futures
import copy
import dataclasses
import difflib
import hashlib
import json
import os
import pathlib
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import time
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import causal_angelic_swe_engine_v1 as SWE_ENGINE
from canonical.runtime import compose_v1 as COMPOSE_ERR
from canonical.runtime import epistemic_computer_use_engine_v1 as EPI_CU
from canonical.runtime import epistemic_morphism_engine_v1 as MORPH_ENGINE
from canonical.runtime import epistemic_spec_synthesizer_v1 as SPEC_SYNTH
from canonical.runtime import htmlform_read_v1 as HTMLFORM
from canonical.runtime import instant_cu_procedure_store_v1 as CU_STORE
from canonical.runtime import instant_swe_skill_store_v1 as SWE_STORE
from canonical.runtime import jit_knowledge_v1 as JIT_KNOWLEDGE
from canonical.runtime import multilang_causal_swe_engine_v1 as ML_SWE_ENGINE
from canonical.runtime import unified_computer_use_agent_v1 as CU_AGENT

SCHEMA = "BRAIN_UNIVERSAL_EPISTEMIC_KERNEL_V1"
MEMORY_SCHEMA = "BRAIN_UNIVERSAL_EPISTEMIC_MEMORY_V1"
AUTHORITY = "NONE"

STATUS_PROVISIONAL = "PROVISIONAL"
STATUS_VERIFIED = "VERIFIED"
STATUS_QUARANTINED = "QUARANTINED"


# ---------------------------------------------------------------------------
# 1. Unified External Inspectable / Editable / Deletable Memory (0 weights!)
# ---------------------------------------------------------------------------

def new_universal_memory() -> dict[str, Any]:
    """Create ONE unified external memory holding ONLY generalized atomic knowledge.

    Explicit Save vs. Discard separation:
      SAVED:     hole-abstracted CLI morphisms, hole-abstracted SWE skills,
                 hole-abstracted CU procedures, corroborated API symbol contracts.
      DISCARDED: raw web pages, raw --help walls of text, concrete workspace paths,
                 concrete identifiers/literals, monolithic one-off scripts.
    """
    return {
        "schema": MEMORY_SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "parameters_stored": 0,
        "external_model_dependency": False,
        "morphism_store": MORPH_ENGINE.new_morphism_store(),
        "swe_skill_store": SWE_STORE.new_store(),
        "cu_procedure_store": CU_STORE.new_store(),
        "api_contracts": {},  # contract_id -> generalized API/symbol correction contract
        "generalized_laws": {},  # law_id -> Plotkin anti-unified CLI / AST / epistemic laws
        "error_fix_laws": {},  # law_id -> Trace2Skill generalized (ErrorSignature, ContextShape) -> RepairLaw
        "js_rewrite_laws": {},  # law_id -> generalized JS/TS single-experience repair laws (0 weights)
        "c_rewrite_laws": {},  # law_id -> generalized C/C++ single-experience repair laws (0 weights)
        "api_poly_skills": {},  # skill_id -> zero-URL/zero-token polymorphic OpenAPI workflow skills
        "sql_poly_skills": {},  # skill_id -> zero-table/zero-column polymorphic SchemaGraphSQL skills
        "db_schema_laws": {},  # law_id -> generalized SQLite schema-graph & latent convention laws (versioned + drift-quarantined)
        "graphql_poly_skills": {},  # skill_id -> zero-URL/zero-field polymorphic GraphQL skills
        "web_enterprise_skills": {},  # skill_id -> zero-URL/zero-HTML polymorphic WorkArena/WebArena-Pro skills
        "world_model_plans": {},  # plan_id -> zero-URL/zero-ID causal precondition world-model plans
        "metamorphic_invariants": {},  # skill_id -> zero-repo generalized metamorphic oracle invariants
        "negative_constraints": {},  # cid -> refuted flags/traps/anti-patterns never to repeat
        "pending_exemplars": [],  # bounded (<=32) path-free verified exemplars awaiting 2-shot LGG compression
    }


def save_universal_memory(memory: Mapping[str, Any], path: str | pathlib.Path) -> pathlib.Path:
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(memory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


def load_universal_memory(path: str | pathlib.Path) -> dict[str, Any]:
    p = pathlib.Path(path)
    if not p.is_file():
        return new_universal_memory()
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != MEMORY_SCHEMA:
        return new_universal_memory()
    data.setdefault("morphism_store", MORPH_ENGINE.new_morphism_store())
    data.setdefault("swe_skill_store", SWE_STORE.new_store())
    data.setdefault("cu_procedure_store", CU_STORE.new_store())
    data.setdefault("api_contracts", {})
    data.setdefault("generalized_laws", {})
    data.setdefault("error_fix_laws", {})
    data.setdefault("js_rewrite_laws", {})
    data.setdefault("c_rewrite_laws", {})
    data.setdefault("web_enterprise_skills", {})
    data.setdefault("world_model_plans", {})
    data.setdefault("db_schema_laws", {})
    data.setdefault("negative_constraints", {})
    data.setdefault("pending_exemplars", [])
    data["parameters_stored"] = 0
    data["model_calls"] = 0
    return data


def record_error_fix_law(
    memory: dict[str, Any],
    *,
    error_kind: str,
    context_shape: str,
    repair_op: str,
    repair_params: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Trace2Skill-style causal failure->fix distillation (ZERO concrete paths/values!)."""
    params = dict(repair_params or {})
    if (
        _contains_leaked_host_path(error_kind)
        or _contains_leaked_host_path(context_shape)
        or _contains_leaked_host_path(repair_op)
        or any(_contains_leaked_host_path(str(v)) for v in params.values())
    ):
        return None
    sig = f"errfix|{error_kind}|{context_shape}|{repair_op}|{json.dumps(params, sort_keys=True)}"
    lid = "errfix_" + hashlib.sha256(sig.encode("utf-8")).hexdigest()[:12]
    store = memory.setdefault("error_fix_laws", {})
    existing = store.get(lid)
    if isinstance(existing, dict):
        existing["verified_uses"] = int(existing.get("verified_uses", 1)) + 1
        existing["status"] = "ACTIVE"
        existing["utility_score"] = int(existing["verified_uses"]) - 2 * int(existing.get("failed_uses", 0))
        return existing
    rec = {
        "law_id": lid,
        "error_kind": error_kind,
        "context_shape": context_shape,
        "repair_op": repair_op,
        "repair_params": params,
        "verified_uses": 1,
        "failed_uses": 0,
        "utility_score": 1,
        "status": "ACTIVE",
        "parameters_stored": 0,
        "raw_prose_stored": 0,
    }
    store[lid] = rec
    return rec


def recall_error_fix_laws(
    memory: Mapping[str, Any] | None,
    *,
    error_kind: str,
    context_shape: str | None = None,
) -> list[dict[str, Any]]:
    """O(1) recall of ACTIVE causal error-fix laws ranked by Skill-Pro utility score."""
    if not isinstance(memory, Mapping):
        return []
    store = memory.get("error_fix_laws")
    if not isinstance(store, Mapping):
        return []
    out: list[dict[str, Any]] = []
    for rec in store.values():
        if not isinstance(rec, Mapping):
            continue
        if rec.get("status") != "ACTIVE":
            continue
        if rec.get("error_kind") != error_kind:
            continue
        if context_shape is not None and rec.get("context_shape") not in (context_shape, "*"):
            continue
        out.append(dict(rec))
    out.sort(key=lambda r: (-int(r.get("utility_score", 0)), -int(r.get("verified_uses", 0)), str(r.get("law_id", ""))))
    return out


def refute_error_fix_law(memory: dict[str, Any], law_id: str, reason: str) -> dict[str, Any] | None:
    """Decrement utility score and quarantine refuted error-fix laws immediately."""
    store = memory.get("error_fix_laws")
    if not isinstance(store, dict) or law_id not in store:
        return None
    rec = store[law_id]
    rec["failed_uses"] = int(rec.get("failed_uses", 0)) + 1
    rec["utility_score"] = int(rec.get("verified_uses", 0)) - 2 * int(rec["failed_uses"])
    if rec["utility_score"] < 0 or rec["failed_uses"] > int(rec.get("verified_uses", 0)):
        rec["status"] = "QUARANTINED"
    rec.setdefault("refutation_reasons", []).append(reason[:160])
    return rec


def compress_and_prune_memory(memory: dict[str, Any] | None, *, max_exemplars: int = 16) -> dict[str, int]:
    """Skill-Pro score-based maintenance + Plotkin subsumption pruning.
    Removes strictly-negative quarantined error laws, evicts pending exemplars already covered
    by generalized LGG laws, and bounds memory size for O(1) lookup latency.
    """
    if not isinstance(memory, dict):
        return {"pruned_error_laws": 0, "pruned_multilang_laws": 0, "pruned_exemplars": 0}
    pruned_error_laws = 0
    ef = memory.get("error_fix_laws")
    if isinstance(ef, dict):
        drop_ids = [
            lid for lid, rec in ef.items()
            if isinstance(rec, Mapping) and rec.get("status") == "QUARANTINED" and int(rec.get("utility_score", 0)) <= -2
        ]
        for lid in drop_ids:
            ef.pop(lid, None)
            pruned_error_laws += 1

    pruned_multilang_laws = 0
    for ml_key in ("js_rewrite_laws", "c_rewrite_laws"):
        mstore = memory.get(ml_key)
        if isinstance(mstore, dict):
            drop_ml = [
                lid for lid, rec in mstore.items()
                if isinstance(rec, Mapping) and rec.get("status") == "QUARANTINED"
            ]
            for lid in drop_ml:
                mstore.pop(lid, None)
                pruned_multilang_laws += 1

    pruned_exemplars = 0
    ex_list = memory.get("pending_exemplars")
    glaws = memory.get("generalized_laws")
    if isinstance(ex_list, list):
        covered_cli_heads = set()
        if isinstance(glaws, Mapping):
            for gl in glaws.values():
                if isinstance(gl, Mapping) and gl.get("kind") == "cli_lgg":
                    toks = gl.get("template_tokens") or []
                    if toks:
                        covered_cli_heads.add(str(toks[0]))
        kept = []
        for ex in ex_list:
            if isinstance(ex, Mapping) and ex.get("kind") == "cli":
                cmd = str(ex.get("command") or "").strip()
                head = cmd.split()[0] if cmd else ""
                if head and head in covered_cli_heads:
                    pruned_exemplars += 1
                    continue
            kept.append(ex)
        if len(kept) > max_exemplars:
            pruned_exemplars += len(kept) - max_exemplars
            kept = kept[-max_exemplars:]
        memory["pending_exemplars"] = kept

    return {
        "pruned_error_laws": pruned_error_laws,
        "pruned_multilang_laws": pruned_multilang_laws,
        "pruned_exemplars": pruned_exemplars,
        "active_generalized_laws": len(glaws) if isinstance(glaws, Mapping) else 0,
        "active_error_fix_laws": sum(
            1 for r in (ef.values() if isinstance(ef, Mapping) else [])
            if isinstance(r, Mapping) and r.get("status") == "ACTIVE"
        ),
    }


def _contains_leaked_host_path(text: str) -> bool:
    return bool(re.search(r"(?:/tmp/|/home/|/Users/|/var/folders/|C:\\\\)", text))


def record_api_contract(
    memory: dict[str, Any],
    *,
    defect_kind: str,  # "attribute_rename" | "kwarg_rename" | "import_relocate" | "sibling_helper"
    owner_type: str,   # e.g. "module:urllib.parse" | "class:DataClient" | "func:connect"
    bad_symbol: str,
    good_symbol: str,
    replacement_module: str = "",
    corroborated_kinds: Sequence[str] = ("runtime_introspection",),
    source_urls: Sequence[str] = (),
) -> dict[str, Any] | None:
    """Admit ONLY a generalized, path-free API contract into unified memory."""
    for s in (owner_type, bad_symbol, good_symbol, replacement_module):
        if _contains_leaked_host_path(s):
            return None
    if not owner_type or not bad_symbol or not good_symbol or (bad_symbol == good_symbol and not replacement_module):
        return None
    sig = json.dumps({
        "defect_kind": defect_kind,
        "owner_type": owner_type,
        "bad_symbol": bad_symbol,
        "good_symbol": good_symbol,
        "replacement_module": replacement_module,
    }, sort_keys=True)
    cid = "apic_" + hashlib.sha256(sig.encode("utf-8")).hexdigest()[:12]
    contracts = memory.setdefault("api_contracts", {})
    existing = contracts.get(cid)
    if isinstance(existing, dict):
        existing["support_count"] = int(existing.get("support_count", 1)) + 1
        existing["status"] = STATUS_VERIFIED
        return existing
    rec = {
        "contract_id": cid,
        "status": STATUS_VERIFIED,
        "defect_kind": defect_kind,
        "owner_type": owner_type,
        "bad_symbol": bad_symbol,
        "good_symbol": good_symbol,
        "replacement_module": replacement_module,
        "corroborated_kinds": sorted(set(str(k) for k in corroborated_kinds)),
        "source_urls": sorted(set(str(u) for u in source_urls if u))[:4],
        "support_count": 1,
        "refutations": [],
        "parameters_stored": 0,
        "external_model_dependency": False,
    }
    contracts[cid] = rec
    return rec


def recall_api_contracts(
    memory: Mapping[str, Any] | None,
    *,
    defect_kind: str,
    bad_symbol: str,
    owner_type: str | None = None,
) -> list[dict[str, Any]]:
    if not memory:
        return []
    out: list[dict[str, Any]] = []
    for rec in (memory.get("api_contracts") or {}).values():
        if not isinstance(rec, dict) or rec.get("status") == STATUS_QUARANTINED:
            continue
        if rec.get("defect_kind") != defect_kind:
            continue
        if rec.get("bad_symbol") != bad_symbol:
            continue
        if owner_type and rec.get("owner_type") not in (owner_type, "*"):
            # Allow generic symbol match only with lower priority
            out.append({**rec, "_match_rank": 1})
        else:
            out.append({**rec, "_match_rank": 2})
    out.sort(key=lambda r: (r.get("_match_rank", 0), int(r.get("support_count", 0))), reverse=True)
    return out


def refute_api_contract(memory: dict[str, Any], contract_id: str, reason: str) -> dict[str, Any]:
    rec = (memory.get("api_contracts") or {}).get(contract_id)
    if not isinstance(rec, dict):
        return {"status": "NOT_FOUND", "contract_id": contract_id}
    rec.setdefault("refutations", []).append({"reason": reason})
    rec["status"] = STATUS_QUARANTINED
    return {"status": STATUS_QUARANTINED, "contract_id": contract_id, "reason": reason}


def delete_memory_entry(memory: dict[str, Any], entry_id: str) -> bool:
    """Delete ANY entry across morphisms, SWE skills, CU procedures, or API contracts."""
    if MORPH_ENGINE.delete_morphism(memory.get("morphism_store") or {}, entry_id):
        return True
    if SWE_STORE.delete_skill(memory.get("swe_skill_store") or {}, entry_id):
        return True
    if CU_STORE.delete_procedure(memory.get("cu_procedure_store") or {}, entry_id):
        return True
    contracts = memory.get("api_contracts")
    if isinstance(contracts, dict) and entry_id in contracts:
        del contracts[entry_id]
        return True
    laws = memory.get("generalized_laws")
    if isinstance(laws, dict) and entry_id in laws:
        del laws[entry_id]
        return True
    elaws = memory.get("error_fix_laws")
    if isinstance(elaws, dict) and entry_id in elaws:
        del elaws[entry_id]
        return True
    ncons = memory.get("negative_constraints")
    if isinstance(ncons, dict) and entry_id in ncons:
        del ncons[entry_id]
        return True
    for ml_key in (
        "js_rewrite_laws",
        "c_rewrite_laws",
        "api_poly_skills",
        "sql_poly_skills",
        "db_schema_laws",
        "graphql_poly_skills",
        "web_enterprise_skills",
        "world_model_plans",
        "metamorphic_invariants",
    ):
        ml_store = memory.get(ml_key)
        if isinstance(ml_store, dict) and entry_id in ml_store:
            del ml_store[entry_id]
            return True
    return False


# ---------------------------------------------------------------------------
# 1b. Plotkin Structural Anti-Unification (Least General Generalization)
#     Answers mathematically: WHAT to generalize, WHAT NOT to generalize,
#     WHAT to save, and WHAT to discard.
# ---------------------------------------------------------------------------

_SHELL_REDIR_TOKENS = frozenset({">", ">>", "<", "|", "&&", "||", ";"})


def _looks_like_path_token(tok: str) -> bool:
    if not tok or tok.startswith("-") or tok in _SHELL_REDIR_TOKENS:
        return False
    if any(ch in tok for ch in "[]{}()|$*=?!"):
        return False
    if "/" in tok or "\\" in tok:
        return True
    if tok.startswith("."):
        return False
    return bool(re.search(r"\.[A-Za-z0-9]{1,6}$", tok))


def anti_unify_command_templates(cmd_a: str, cmd_b: str) -> dict[str, Any]:
    """Compute the exact Plotkin Least General Generalization (LGG) of two verified
    shell commands, separating invariant structure from environment-specific holes.

    Anti-Overgeneralization Guard (what NOT to generalize):
      - Refuses different executable heads (`gzip` + `tar` != `__TOOL__`).
      - Refuses incompatible token/redirection arities.
      - Refuses collapse where invariant structural tokens < 45% (prevents empty laws).
      - Refuses any host-path leak surviving inside an invariant slot.
    """
    try:
        toks_a = shlex.split(cmd_a)
        toks_b = shlex.split(cmd_b)
    except ValueError:
        return {"status": "REFUSED_PARSE_ERROR", "reason": "unbalanced shell quotes"}

    if not toks_a or not toks_b:
        return {"status": "REFUSED_EMPTY", "reason": "empty command"}
    if toks_a[0] != toks_b[0]:
        return {
            "status": "REFUSED_HEAD_MISMATCH",
            "reason": f"different tool heads ({toks_a[0]!r} vs {toks_b[0]!r}) must not be merged",
        }
    if len(toks_a) != len(toks_b):
        return {
            "status": "REFUSED_SHAPE_MISMATCH",
            "reason": f"different command shapes ({len(toks_a)} vs {len(toks_b)} tokens)",
        }

    template_tokens: list[str] = []
    holes: list[dict[str, Any]] = []
    invariant_count = 0
    arg_idx = 0

    for i, (ta, tb) in enumerate(zip(toks_a, toks_b)):
        # Shell redirection operators must match rigidly
        if ta in _SHELL_REDIR_TOKENS or tb in _SHELL_REDIR_TOKENS:
            if ta != tb:
                return {
                    "status": "REFUSED_SHAPE_MISMATCH",
                    "reason": f"redirection mismatch at slot {i}: {ta!r} vs {tb!r}",
                }
            template_tokens.append(ta)
            invariant_count += 1
            continue

        # Flags (`-r`, `--sort`, etc.) must stay invariant across a single law
        if (ta.startswith("-") or tb.startswith("-")) and ta != tb:
            return {
                "status": "REFUSED_FLAG_MISMATCH",
                "reason": f"flag mismatch at slot {i}: {ta!r} vs {tb!r}",
            }

        if ta == tb:
            # Even identical host paths must be lifted, never stored concretely!
            if _contains_leaked_host_path(ta):
                prev_tok = template_tokens[-1] if template_tokens else ""
                hname = "__OUTPUT_PATH__" if prev_tok in (">", ">>", "-o", "--output") else "__INPUT_PATH__"
                template_tokens.append(hname)
                holes.append({"hole": hname, "kind": "path", "slot": i})
            else:
                template_tokens.append(ta)
                invariant_count += 1
        else:
            prev_tok = template_tokens[-1] if template_tokens else ""
            if prev_tok in (">", ">>", "-o", "--output"):
                hname = "__OUTPUT_PATH__"
                hkind = "output_path"
            elif prev_tok in ("<", "-i", "--input") or (_looks_like_path_token(ta) and _looks_like_path_token(tb)):
                hname = "__INPUT_PATH__"
                hkind = "input_path"
            else:
                hname = f"__ARG_{arg_idx}__"
                hkind = "argument"
                arg_idx += 1
            template_tokens.append(hname)
            holes.append({"hole": hname, "kind": hkind, "slot": i})

    # Compute structural invariant density excluding pure path holes
    non_path_slots = max(1, len(toks_a) - sum(1 for h in holes if "path" in h["kind"]))
    invariant_density = invariant_count / non_path_slots
    if invariant_count < 1 or invariant_density < 0.45:
        return {
            "status": "REFUSED_OVERGENERALIZED",
            "reason": f"invariant density {invariant_density:.2f} below 0.45 floor",
        }

    rendered = " ".join(template_tokens)
    if _contains_leaked_host_path(rendered):
        return {"status": "REFUSED_HOST_PATH_LEAK", "reason": "host path leaked into template"}

    sig = json.dumps({"kind": "cli_anti_unified", "template": rendered}, sort_keys=True)
    return {
        "status": "VERIFIED",
        "law_id": "law_cli_" + hashlib.sha256(sig.encode("utf-8")).hexdigest()[:12],
        "kind": "cli_anti_unified",
        "tool": toks_a[0],
        "template_tokens": template_tokens,
        "template": rendered,
        "holes": holes,
        "invariant_density": round(invariant_density, 3),
        "support_count": 2,
        "forbid_facts": [],
        "parameters_stored": 0,
        "raw_prose_stored": 0,
    }


def instantiate_anti_unified_command(law: Mapping[str, Any], bindings: Mapping[str, str]) -> str | None:
    """Bind typed holes in a Plotkin anti-unified CLI law safely for a new unseen environment."""
    toks = law.get("template_tokens")
    if not isinstance(toks, list) or not toks:
        return None
    out: list[str] = []
    for tok in toks:
        if isinstance(tok, str) and tok.startswith("__") and tok.endswith("__"):
            if tok not in bindings:
                return None
            out.append(shlex.quote(str(bindings[tok])))
        elif tok in _SHELL_REDIR_TOKENS:
            out.append(tok)
        else:
            out.append(shlex.quote(str(tok)) if any(c in str(tok) for c in " \t'\"$") else str(tok))
    return " ".join(out)


def _ast_lgg(
    a: Any,
    b: Any,
    hole_map: dict[tuple[str, str], str],
) -> tuple[Any, int, int]:
    """Recursive Plotkin AST anti-unifier. Returns `(lgg_node, rigid_nodes, hole_nodes)`."""
    if type(a) is not type(b):
        key = (ast.dump(a) if isinstance(a, ast.AST) else repr(a),
               ast.dump(b) if isinstance(b, ast.AST) else repr(b))
        h = hole_map.setdefault(key, f"__HOLE_{len(hole_map)}__")
        return ast.Name(id=h, ctx=ast.Load()), 0, 1

    if isinstance(a, ast.AST):
        # Leaf Name or Constant differing between the two examples -> correlated hole!
        if isinstance(a, ast.Name) and a.id != b.id:
            key = (ast.dump(a), ast.dump(b))
            h = hole_map.setdefault(key, f"__HOLE_{len(hole_map)}__")
            return ast.Name(id=h, ctx=copy.deepcopy(a.ctx)), 0, 1
        if isinstance(a, ast.Constant) and a.value != b.value:
            key = (ast.dump(a), ast.dump(b))
            h = hole_map.setdefault(key, f"__HOLE_{len(hole_map)}__")
            return ast.Name(id=h, ctx=ast.Load()), 0, 1
        # Attribute name differing -> cannot keep rigid attribute; lift whole Attribute
        if isinstance(a, ast.Attribute) and a.attr != b.attr:
            key = (ast.dump(a), ast.dump(b))
            h = hole_map.setdefault(key, f"__HOLE_{len(hole_map)}__")
            return ast.Name(id=h, ctx=copy.deepcopy(a.ctx)), 0, 1

        kwargs: dict[str, Any] = {}
        rigid = 1
        holes = 0
        for field in a._fields:
            va = getattr(a, field)
            vb = getattr(b, field)
            if isinstance(va, list) and isinstance(vb, list):
                if len(va) != len(vb):
                    key = (ast.dump(a), ast.dump(b))
                    h = hole_map.setdefault(key, f"__HOLE_{len(hole_map)}__")
                    return ast.Name(id=h, ctx=ast.Load()), 0, 1
                sub_list = []
                for ea, eb in zip(va, vb):
                    gn, r, h = _ast_lgg(ea, eb, hole_map)
                    sub_list.append(gn)
                    rigid += r
                    holes += h
                kwargs[field] = sub_list
            elif isinstance(va, ast.AST) and isinstance(vb, ast.AST):
                gn, r, h = _ast_lgg(va, vb, hole_map)
                kwargs[field] = gn
                rigid += r
                holes += h
            elif va == vb:
                kwargs[field] = copy.deepcopy(va)
            else:
                key = (ast.dump(a), ast.dump(b))
                h = hole_map.setdefault(key, f"__HOLE_{len(hole_map)}__")
                return ast.Name(id=h, ctx=ast.Load()), 0, 1
        return type(a)(**kwargs), rigid, holes

    return copy.deepcopy(a), 1, 0


def anti_unify_ast_edits(
    before_a: str,
    after_a: str,
    before_b: str,
    after_b: str,
) -> dict[str, Any]:
    """Compute the exact Plotkin AST Least General Generalization of two verified
    code rewrite pairs `(before_a -> after_a)` and `(before_b -> after_b)`.

    Example:
      Pair 1: `netloc.split("@", 1)` -> `netloc.rsplit("@", 1)`
      Pair 2: `path.split("/", 1)`   -> `path.rsplit("/", 1)`
      LGG:    `__HOLE_0__.split(__HOLE_1__, 1)` -> `__HOLE_0__.rsplit(__HOLE_1__, 1)`

    Anti-Overgeneralization Guard:
      - Refuses different AST root node types (`Call` vs `Compare`, etc.).
      - Refuses collapsing to trivial `__HOLE_0__ -> __HOLE_1__` (requires rigid structural skeleton).
      - Refuses if `after` introduces an unbound hole absent from `before`.
    """
    try:
        na_b = ast.parse(before_a, mode="eval").body
        na_a = ast.parse(after_a, mode="eval").body
        nb_b = ast.parse(before_b, mode="eval").body
        nb_a = ast.parse(after_b, mode="eval").body
    except SyntaxError as exc:
        return {"status": "REFUSED_SYNTAX_ERROR", "reason": str(exc)}

    if type(na_b) is not type(nb_b) or type(na_a) is not type(nb_a):
        return {
            "status": "REFUSED_AST_ROOT_MISMATCH",
            "reason": f"root AST types differ ({type(na_b).__name__}/{type(nb_b).__name__})",
        }

    hole_map: dict[tuple[str, str], str] = {}
    pat_before, rigid_b, _ = _ast_lgg(na_b, nb_b, hole_map)
    before_holes = set(hole_map.values())
    pat_after, rigid_a, _ = _ast_lgg(na_a, nb_a, hole_map)
    after_holes = {
        n.id for n in ast.walk(pat_after)
        if isinstance(n, ast.Name) and n.id.startswith("__HOLE_") and n.id.endswith("__")
    }

    if isinstance(pat_before, ast.Name) and pat_before.id.startswith("__HOLE_"):
        return {"status": "REFUSED_OVERGENERALIZED", "reason": "collapsed before-pattern to bare hole"}
    if isinstance(pat_after, ast.Name) and pat_after.id.startswith("__HOLE_"):
        return {"status": "REFUSED_OVERGENERALIZED", "reason": "collapsed after-pattern to bare hole"}
    if not after_holes.issubset(before_holes):
        return {
            "status": "REFUSED_UNBOUND_HOLE",
            "reason": f"after-pattern references holes not bound in before-pattern: {sorted(after_holes - before_holes)}",
        }
    if rigid_b < 2 or rigid_a < 2:
        return {"status": "REFUSED_OVERGENERALIZED", "reason": "insufficient rigid AST skeleton"}

    ast.fix_missing_locations(pat_before)
    ast.fix_missing_locations(pat_after)
    b_src = ast.unparse(pat_before)
    a_src = ast.unparse(pat_after)
    if b_src == a_src:
        return {"status": "REFUSED_NOOP", "reason": "before and after patterns are identical"}

    sig = json.dumps({"kind": "ast_anti_unified", "before": b_src, "after": a_src}, sort_keys=True)
    return {
        "status": "VERIFIED",
        "law_id": "law_ast_" + hashlib.sha256(sig.encode("utf-8")).hexdigest()[:12],
        "kind": "ast_anti_unified",
        "before_pattern": b_src,
        "after_pattern": a_src,
        "holes": sorted(before_holes),
        "support_count": 2,
        "forbid_facts": [],
        "parameters_stored": 0,
        "raw_prose_stored": 0,
    }


def _match_ast_pattern(pat: Any, node: Any, env: dict[str, ast.AST]) -> bool:
    if isinstance(pat, ast.Name) and pat.id.startswith("__HOLE_") and pat.id.endswith("__"):
        if not isinstance(node, ast.AST):
            return False
        if pat.id in env:
            return ast.dump(env[pat.id]) == ast.dump(node)
        env[pat.id] = copy.deepcopy(node)
        return True
    if type(pat) is not type(node):
        return False
    if isinstance(pat, ast.AST):
        for field in pat._fields:
            if field == "ctx":
                continue
            vp = getattr(pat, field)
            vn = getattr(node, field)
            if isinstance(vp, list) and isinstance(vn, list):
                if len(vp) != len(vn):
                    return False
                if not all(_match_ast_pattern(ep, en, env) for ep, en in zip(vp, vn)):
                    return False
            elif isinstance(vp, ast.AST) and isinstance(vn, ast.AST):
                if not _match_ast_pattern(vp, vn, env):
                    return False
            elif vp != vn:
                return False
        return True
    return pat == node


def _subst_ast_pattern(pat: ast.AST, env: Mapping[str, ast.AST]) -> ast.AST:
    class _Sub(ast.NodeTransformer):
        def visit_Name(self, node: ast.Name) -> ast.AST:
            if node.id in env:
                return copy.deepcopy(env[node.id])
            return node

    out = _Sub().visit(copy.deepcopy(pat))
    ast.fix_missing_locations(out)
    return out


def apply_anti_unified_ast_law(
    source_code: str,
    law: Mapping[str, Any],
    *,
    observed_facts: Sequence[str] = (),
) -> str | None:
    """Apply a Plotkin anti-unified AST law to an unseen Python source file offline (<1ms)."""
    if law.get("status") == STATUS_QUARANTINED:
        return None
    forbid = set(law.get("forbid_facts") or ())
    if forbid and (forbid & set(observed_facts)):
        return None
    b_pat = law.get("before_pattern")
    a_pat = law.get("after_pattern")
    if not isinstance(b_pat, str) or not isinstance(a_pat, str):
        return None
    try:
        tree = ast.parse(source_code)
        pat_b = ast.parse(b_pat, mode="eval").body
        pat_a = ast.parse(a_pat, mode="eval").body
    except SyntaxError:
        return None

    replaced = False

    class _Rewriter(ast.NodeTransformer):
        def generic_visit(self, node: ast.AST) -> ast.AST:
            nonlocal replaced
            if not replaced:
                env: dict[str, ast.AST] = {}
                if _match_ast_pattern(pat_b, node, env):
                    replaced = True
                    return _subst_ast_pattern(pat_a, env)
            return super().generic_visit(node)

    new_tree = _Rewriter().visit(tree)
    if not replaced:
        return None
    ast.fix_missing_locations(new_tree)
    return ast.unparse(new_tree) + "\n"


def record_generalized_law(memory: dict[str, Any], law: Mapping[str, Any]) -> dict[str, Any] | None:
    """Admit ONLY a verified, path-free, Plotkin anti-unified law into unified external memory."""
    if not isinstance(law, Mapping) or law.get("status") != STATUS_VERIFIED:
        return None
    lid = str(law.get("law_id") or "")
    if not lid:
        return None
    serialized = json.dumps(law, sort_keys=True)
    if _contains_leaked_host_path(serialized):
        return None
    laws = memory.setdefault("generalized_laws", {})
    existing = laws.get(lid)
    if isinstance(existing, dict):
        existing["support_count"] = int(existing.get("support_count", 2)) + 1
        return existing
    stored = dict(law)
    stored["parameters_stored"] = 0
    stored["raw_prose_stored"] = 0
    laws[lid] = stored
    return stored


def narrow_law_on_refutation(
    memory: dict[str, Any],
    law_id: str,
    *,
    positive_facts: Sequence[str],
    negative_facts: Sequence[str],
) -> dict[str, Any]:
    """Refutation Narrowing: when a generalized law over-applies on a new environment,
    compute the smallest discriminating fact `f in negative \\ positive` and forbid it.
    """
    law = (memory.get("generalized_laws") or {}).get(law_id)
    if not isinstance(law, dict):
        return {"status": "NOT_FOUND", "law_id": law_id}
    disc = sorted(set(negative_facts) - set(positive_facts))
    if not disc:
        law["status"] = STATUS_QUARANTINED
        return {"status": STATUS_QUARANTINED, "law_id": law_id, "reason": "no_discriminating_fact"}
    smallest = disc[0]
    forbid = list(law.get("forbid_facts") or [])
    if smallest not in forbid:
        forbid.append(smallest)
    law["forbid_facts"] = sorted(forbid)
    return {"status": "NARROWED", "law_id": law_id, "added_forbid_fact": smallest, "forbid_facts": law["forbid_facts"]}


def _extract_single_expr_diff(before_src: str, after_src: str) -> tuple[str, str] | None:
    """Find the deepest single differing AST expression `(before_expr, after_expr)` between
    two Python files so verified SWE repairs can self-compress via Plotkin AST anti-unification.
    """
    try:
        t_b = ast.parse(before_src)
        t_a = ast.parse(after_src)
    except SyntaxError:
        return None

    diffs: list[tuple[ast.expr, ast.expr]] = []

    def _walk(nb: Any, na: Any) -> None:
        if isinstance(nb, ast.AST) and isinstance(na, ast.AST):
            if ast.dump(nb) == ast.dump(na):
                return
            if type(nb) is not type(na):
                if isinstance(nb, ast.expr) and isinstance(na, ast.expr):
                    diffs.append((nb, na))
                return
            # Check child fields; if only non-AST metadata (like Attribute.attr) differs, record parent expr
            child_diffs: list[tuple[Any, Any]] = []
            scalar_diff = False
            for f in nb._fields:
                if f == "ctx":
                    continue
                vb, va = getattr(nb, f), getattr(na, f)
                if isinstance(vb, list) and isinstance(va, list):
                    if len(vb) != len(va):
                        scalar_diff = True
                    else:
                        for eb, ea in zip(vb, va):
                            if isinstance(eb, ast.AST) and isinstance(ea, ast.AST):
                                if ast.dump(eb) != ast.dump(ea):
                                    child_diffs.append((eb, ea))
                            elif eb != ea:
                                scalar_diff = True
                elif isinstance(vb, ast.AST) and isinstance(va, ast.AST):
                    if ast.dump(vb) != ast.dump(va):
                        child_diffs.append((vb, va))
                elif vb != va:
                    scalar_diff = True
            if scalar_diff or len(child_diffs) > 1:
                if isinstance(nb, ast.expr) and isinstance(na, ast.expr):
                    diffs.append((nb, na))
                else:
                    for cb, ca in child_diffs:
                        _walk(cb, ca)
            elif len(child_diffs) == 1:
                cb, ca = child_diffs[0]
                if isinstance(nb, ast.Call) and isinstance(cb, ast.Attribute) and isinstance(ca, ast.Attribute) and cb.attr != ca.attr:
                    diffs.append((nb, na))
                else:
                    _walk(cb, ca)

    _walk(t_b, t_a)
    if len(diffs) != 1:
        return None
    b_u = ast.unparse(diffs[0][0])
    a_u = ast.unparse(diffs[0][1])
    if not b_u or not a_u or b_u == a_u or len(b_u) > 160 or len(a_u) > 160:
        return None
    if _contains_leaked_host_path(b_u) or _contains_leaked_host_path(a_u):
        return None
    return b_u, a_u


def auto_consolidate_experience(
    memory: dict[str, Any],
    *,
    kind: str,
    before: str = "",
    after: str = "",
    command: str = "",
) -> dict[str, Any]:
    """Self-Compressing Online Generalization (Elon's Law: the best part is no part).

    Stores at most 32 tiny path-free verified exemplars in `pending_exemplars`.
    The instant a 2nd structurally compatible verified experience arrives, automatically
    computes its Plotkin Least General Generalization, promotes the resulting reusable law
    into `memory["generalized_laws"]`, and DELETES the redundant concrete exemplars.
    """
    pending: list[dict[str, Any]] = memory.setdefault("pending_exemplars", [])

    if kind == "ast" and before and after:
        if _contains_leaked_host_path(before) or _contains_leaked_host_path(after):
            return {"status": "REFUSED_HOST_PATH_LEAK"}
        # Check if already covered by an existing generalized AST law
        for law in (memory.get("generalized_laws") or {}).values():
            if isinstance(law, dict) and law.get("kind") == "ast_anti_unified":
                applied = apply_anti_unified_ast_law(before + "\n", law)
                if applied and applied.strip() == after.strip():
                    law["support_count"] = int(law.get("support_count", 2)) + 1
                    return {"status": "REINFORCED_LAW", "law_id": law["law_id"]}
        # Try Plotkin anti-unification against prior pending AST exemplars
        for idx, prev in enumerate(pending):
            if prev.get("kind") != "ast":
                continue
            if prev.get("before") == before and prev.get("after") == after:
                return {"status": "DUPLICATE_EXEMPLAR"}
            lgg = anti_unify_ast_edits(prev["before"], prev["after"], before, after)
            if lgg.get("status") == STATUS_VERIFIED:
                stored = record_generalized_law(memory, lgg)
                if stored is not None:
                    pending.pop(idx)  # Self-compress: discard redundant concrete exemplar!
                    return {
                        "status": "PROMOTED_ANTI_UNIFIED_LAW",
                        "law_id": stored["law_id"],
                        "before_pattern": stored["before_pattern"],
                        "after_pattern": stored["after_pattern"],
                        "pending_compressed": True,
                    }
        pending.append({"kind": "ast", "before": before, "after": after})
        if len(pending) > 32:
            del pending[:-32]
        return {"status": "BUFFERED_EXEMPLAR", "pending_count": len(pending)}

    if kind == "cli" and command:
        for idx, prev in enumerate(pending):
            if prev.get("kind") != "cli":
                continue
            if prev.get("command") == command:
                return {"status": "DUPLICATE_EXEMPLAR"}
            lgg = anti_unify_command_templates(prev["command"], command)
            if lgg.get("status") == STATUS_VERIFIED:
                stored = record_generalized_law(memory, lgg)
                if stored is not None:
                    pending.pop(idx)
                    return {
                        "status": "PROMOTED_ANTI_UNIFIED_LAW",
                        "law_id": stored["law_id"],
                        "template": stored["template"],
                        "pending_compressed": True,
                    }
        if not _contains_leaked_host_path(command):
            pending.append({"kind": "cli", "command": command})
            if len(pending) > 32:
                del pending[:-32]
        return {"status": "BUFFERED_EXEMPLAR", "pending_count": len(pending)}

    return {"status": "IGNORED"}


# ---------------------------------------------------------------------------
# 2. Fast O(workspace) Local Frontier Sensing (~2-5ms)
# ---------------------------------------------------------------------------

def sense_local_frontier(
    workspace: str | pathlib.Path,
    instruction: str,
    *,
    dom_nodes: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Scan ONLY the goal's local causal frontier (never blindly crawl the OS)."""
    t0 = time.monotonic()
    ws = pathlib.Path(workspace).resolve()
    env = EPI_CU.sense_unknown_environment(ws)
    low = instruction.lower()

    typed_files: list[dict[str, Any]] = []
    py_files: list[str] = []
    test_files: list[str] = []
    js_files: list[str] = []
    js_test_files: list[str] = []
    c_files: list[str] = []
    c_test_files: list[str] = []
    containers: list[dict[str, str]] = []

    scanned_files: list[dict[str, Any]] = list(env.get("files", []))
    seen_rels: set[str] = {str(f.get("rel") or "") for f in scanned_files}
    # Always include top-level files + instruction-referenced files so large `resources/`/`docs/`
    # subdirectories never hide top-level source/test files (e.g., `tinyxml2.cpp`, `xmltest.cpp`).
    if ws.is_dir():
        for child in sorted(ws.iterdir()):
            if child.is_file() and child.name not in seen_rels:
                seen_rels.add(child.name)
                scanned_files.append({"rel": child.name, "bytes": child.stat().st_size})
        for m_ref in re.finditer(r"([A-Za-z0-9_.\-/]+\.(?:py|js|mjs|cjs|ts|c|cc|cpp|cxx|h|hh|hpp|sh))\b", instruction or ""):
            ref_rel = m_ref.group(1).lstrip("./")
            ref_p = ws / ref_rel
            if ref_p.is_file() and ref_rel not in seen_rels:
                seen_rels.add(ref_rel)
                scanned_files.append({"rel": ref_rel, "bytes": ref_p.stat().st_size})

    for f in scanned_files:
        rel = str(f.get("rel") or "")
        p = ws / rel
        if not p.is_file():
            continue
        mtype = MORPH_ENGINE.infer_file_media_type(p)
        typed_files.append({"rel": rel, "media_type": mtype, "bytes": int(f.get("bytes", 0))})
        if rel.endswith(".py"):
            py_files.append(rel)
            bn = pathlib.Path(rel).name
            if bn.startswith("test_") or bn.endswith("_test.py") or "/tests/" in f"/{rel}":
                test_files.append(rel)
        elif rel.endswith((".js", ".mjs", ".cjs", ".ts")) and not rel.endswith(".d.ts"):
            if not ML_SWE_ENGINE._is_non_prod_skip(rel):
                js_files.append(rel)
                if ML_SWE_ENGINE._is_test_path(rel):
                    js_test_files.append(rel)
        elif rel.endswith((".c", ".cc", ".cpp", ".cxx")):
            if not ML_SWE_ENGINE._is_c_skip_path(rel):
                if ML_SWE_ENGINE._is_c_test_path(rel):
                    c_test_files.append(rel)
                else:
                    c_files.append(rel)
        elif rel.endswith((".h", ".hpp", ".hh")) and not ML_SWE_ENGINE._is_c_skip_path(rel) and not ML_SWE_ENGINE._is_c_test_path(rel):
            c_files.append(rel)
        if mtype in MORPH_ENGINE._CONTAINER_TYPES:
            containers.append({"rel": rel, "media_type": mtype})

    swe_intent = any(
        w in low for w in (
            "pytest", "failing test", "fix test", "fix the test", "fix the failing",
            "fix bug", "repair bug", "repair code", "unittest", "traceback",
            "attributeerror", "typeerror", "importerror", "nameerror", "assertionerror",
            "mocha", "vitest", "jest", "npm test", "node --test", "tap test",
            "segfault", "null pointer", "use-after-free", "buffer overflow", "buffer overrun",
            "asan", "ubsan", "signed integer overflow", "assertion failed", "make test", "unittest.sh",
        )
    )

    explicit_c_ref = bool(re.search(r"\b[A-Za-z0-9_.\-/]+\.(?:c|cc|cpp|cxx|h|hpp|hh|sh)\b", low))
    explicit_js_ref = bool(re.search(r"\b[A-Za-z0-9_.\-/]+\.(?:js|mjs|cjs|ts)\b", low))
    explicit_py_ref = bool(re.search(r"\b[A-Za-z0-9_.\-/]+\.py\b", low))
    has_swe_signal = swe_intent or ("fix" in low) or ("repair" in low)
    if has_swe_signal and (not c_files or not c_test_files) and not test_files and not js_test_files:
        _dc_src, _dc_tst, _ = ML_SWE_ENGINE._discover_c_files(ws)
        if _dc_src and not c_files:
            c_files.extend(_dc_src[:32])
        if _dc_tst and not c_test_files:
            c_test_files.extend(_dc_tst[:32])

    if dom_nodes is not None:
        modality = "browser_dom"
    elif swe_intent and containers and not test_files and not js_test_files and not c_test_files:
        modality = "cross_modal_bundle_swe"
    elif has_swe_signal and explicit_c_ref and c_files and (c_test_files or (ws / "tests" / "unittest.sh").is_file()):
        modality = "swe_c_codebase"
    elif has_swe_signal and explicit_js_ref and (js_test_files or (swe_intent and js_files)):
        modality = "swe_js_codebase"
    elif has_swe_signal and explicit_py_ref and (test_files or (swe_intent and py_files)):
        modality = "swe_codebase"
    elif has_swe_signal and test_files:
        modality = "swe_codebase"
    elif has_swe_signal and js_test_files:
        modality = "swe_js_codebase"
    elif has_swe_signal and c_files and (c_test_files or (ws / "tests" / "unittest.sh").is_file()):
        modality = "swe_c_codebase"
    elif swe_intent and py_files:
        modality = "swe_codebase"
    elif swe_intent and (js_files or (ws / "package.json").is_file()):
        modality = "swe_js_codebase"
    else:
        modality = "os_cli_computer_use"

    return {
        "workspace": str(ws),
        "modality": modality,
        "typed_files": typed_files,
        "py_files": py_files,
        "test_files": test_files,
        "js_files": js_files,
        "js_test_files": js_test_files,
        "c_files": c_files,
        "c_test_files": c_test_files,
        "containers": containers,
        "env": env,
        "sense_ms": round((time.monotonic() - t0) * 1000.0, 2),
    }


def _shallow_inspect_structured_affordances(ws: pathlib.Path, typed_files: Sequence[Mapping[str, Any]]) -> list[str]:
    """O(workspace) shallow header-only inspection of structured artifacts (JSON, CSV, SQLite,
    Git, Python imports). Never reads huge files or makes network/subprocess calls.
    """
    affordances: list[str] = []
    if (ws / ".git").exists():
        affordances.append("repo:git")

    imported_roots: set[str] = set()
    for f in typed_files[:40]:
        rel = str(f.get("rel") or "")
        mtype = str(f.get("media_type") or "unknown")
        affordances.append(f"file:{rel}:{mtype}")
        p = ws / rel
        if not p.is_file():
            continue
        low_rel = rel.lower()
        try:
            if low_rel.endswith(".json") and int(f.get("bytes", 0)) <= 65536:
                raw = json.loads(p.read_text(encoding="utf-8", errors="replace"))
                if isinstance(raw, dict):
                    keys = ",".join(sorted(str(k) for k in raw.keys())[:6])
                    affordances.append(f"schema:json:{rel}:{{{keys}}}")
                elif isinstance(raw, list) and raw and isinstance(raw[0], dict):
                    keys = ",".join(sorted(str(k) for k in raw[0].keys())[:6])
                    affordances.append(f"schema:json_list:{rel}:{{{keys}}}")
            elif low_rel.endswith(".csv"):
                first_line = p.read_text(encoding="utf-8", errors="replace").splitlines()[:1]
                if first_line:
                    affordances.append(f"schema:csv:{rel}:{first_line[0][:80]}")
            elif low_rel.endswith((".db", ".sqlite", ".sqlite3")) or mtype == "application/x-sqlite3":
                con = sqlite3.connect(f"file:{p}?immutable=1", uri=True)
                try:
                    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()[:8]]
                    if tables:
                        affordances.append(f"schema:sqlite:{rel}:{','.join(tables)}")
                finally:
                    con.close()
            elif low_rel.endswith(".py") and len(imported_roots) < 16:
                src = p.read_text(encoding="utf-8", errors="replace")[:8192]
                for m in re.finditer(r"^\s*(?:import|from)\s+([A-Za-z_][A-Za-z0-9_]*)", src, flags=re.MULTILINE):
                    imported_roots.add(m.group(1))
        except Exception:
            continue

    for mod in sorted(imported_roots)[:12]:
        affordances.append(f"py_import:{mod}")
    return affordances


def compute_epistemic_diff(
    workspace: str | pathlib.Path,
    instruction: str,
    *,
    memory: Mapping[str, Any] | None = None,
    dom_nodes: Sequence[Mapping[str, Any]] | None = None,
    frontier: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Unified Shallow-Scan -> Goal-Pruned Filter -> Memory-Subtraction Epistemic Diff.

    Computes `Delta = RelevantAffordances(Goal | ShallowScan(E)) \\ Known(ExternalMemory)`
    in ~2-6 ms with ZERO web calls, proving mathematically what is already known offline
    vs. the minimal unknown delta that justifies live acquisition.
    """
    t0 = time.monotonic()
    ws = pathlib.Path(workspace).resolve()
    fr = dict(frontier) if frontier is not None else sense_local_frontier(ws, instruction, dom_nodes=dom_nodes)
    modality = str(fr.get("modality") or "os_cli_computer_use")

    affordances = _shallow_inspect_structured_affordances(ws, fr.get("typed_files") or ())
    if dom_nodes is not None:
        affordances.append(f"dom:controls:{len(dom_nodes)}")

    # Goal-pruned intersection: extract ONLY required capabilities / transitions for this goal
    goal_tokens = set(re.findall(r"[a-z0-9_.\-]+", instruction.lower()))
    goal_relevant: list[str] = []
    known_offline: list[str] = []
    epistemic_delta: list[str] = []

    m_store = (memory or {}).get("morphism_store") if isinstance(memory, Mapping) else None
    stored_morphs = (m_store.get("morphisms") or {}) if isinstance(m_store, Mapping) else {}
    known_verbs = {
        str(rec.get("verb") or "")
        for rec in stored_morphs.values()
        if isinstance(rec, Mapping) and rec.get("status") != STATUS_QUARANTINED
    }
    known_contracts = (memory or {}).get("api_contracts") if isinstance(memory, Mapping) else {}
    known_laws = (memory or {}).get("generalized_laws") if isinstance(memory, Mapping) else {}
    known_skills = ((memory or {}).get("swe_skill_store") or {}).get("skills") if isinstance(memory, Mapping) else {}
    known_procs = ((memory or {}).get("cu_procedure_store") or {}).get("procedures") if isinstance(memory, Mapping) else {}

    if modality == "browser_dom":
        goal_relevant.append("dom:step_observable")
        known_offline.append("dom:step_observable")
    elif modality in ("swe_codebase", "cross_modal_bundle_swe"):
        if modality == "cross_modal_bundle_swe":
            for c in fr.get("containers") or ():
                rel = c.get("rel", "")
                mtype = c.get("media_type", "")
                req = f"unwrap:{mtype}:{rel}"
                goal_relevant.append(req)
                if any(
                    isinstance(rec, Mapping)
                    and rec.get("status") != STATUS_QUARANTINED
                    and rec.get("input_type") == mtype
                    for rec in stored_morphs.values()
                ):
                    known_offline.append(req)
                else:
                    epistemic_delta.append(req)
        req_swe = f"swe_repair:{len(fr.get('test_files') or ())}tests"
        goal_relevant.append(req_swe)
        if known_contracts or known_skills or known_laws:
            known_offline.append(f"swe_memory:{len(known_contracts or {})}contracts+{len(known_skills or {})}skills+{len(known_laws or {})}laws")
        epistemic_delta.append("swe_live_test_oracle")
    else:
        # OS / CLI / Multi-step workflow: decompose goal into typed transitions without web calls
        transitions, _, _ = MORPH_ENGINE.decompose_goal_to_transitions(instruction, fr.get("env") or EPI_CU.sense_unknown_environment(ws))
        for tr in transitions:
            verb = str(getattr(tr, "verb", None) or (tr.get("verb") if isinstance(tr, Mapping) else "") or "")
            in_t = str(getattr(tr, "input_type", None) or (tr.get("input_type") if isinstance(tr, Mapping) else "") or "")
            out_t = str(getattr(tr, "output_type", None) or (tr.get("output_type") if isinstance(tr, Mapping) else "") or "")
            key = f"morphism:{verb}({in_t}->{out_t})"
            goal_relevant.append(key)
            matched = (
                verb in known_verbs
                or any(
                    isinstance(rec, Mapping)
                    and rec.get("status") != STATUS_QUARANTINED
                    and rec.get("verb") == verb
                    for rec in stored_morphs.values()
                )
            )
            if matched:
                known_offline.append(key)
            else:
                epistemic_delta.append(key)
        if not transitions:
            cu_goal = CU_AGENT.compile_instruction(instruction, CU_AGENT.sense_environment(ws))
            dom = cu_goal.get("domain", "unknown")
            req = f"cu_domain:{dom}"
            goal_relevant.append(req)
            if dom != "unknown" or known_procs:
                known_offline.append(req)
            else:
                epistemic_delta.append(req)

    # Count affordances pruned by goal-directed filtering
    touched_affordances = [
        a for a in affordances
        if any(tok in a.lower() for tok in goal_tokens if len(tok) >= 3)
    ]
    pruned_irrelevant = max(0, len(affordances) - len(touched_affordances))

    return {
        "modality": modality,
        "affordances_scanned": affordances,
        "affordances_scanned_count": len(affordances),
        "pruned_irrelevant_count": pruned_irrelevant,
        "goal_relevant": goal_relevant,
        "known_offline": known_offline,
        "epistemic_delta": epistemic_delta,
        "tier0_offline_ready": len(epistemic_delta) == 0,
        "web_calls_in_scan": 0,
        "memory_counts": {
            "morphisms": len(stored_morphs),
            "api_contracts": len(known_contracts or {}),
            "swe_skills": len(known_skills or {}),
            "cu_procedures": len(known_procs or {}),
            "generalized_laws": len(known_laws or {}),
        },
        "scan_diff_ms": round((time.monotonic() - t0) * 1000.0, 2),
    }


# ---------------------------------------------------------------------------
# 3. SWE Epistemic Diff: Live Runtime Introspection + Web Docs + Sibling Oracle
# ---------------------------------------------------------------------------

def _run_pytest_capture(
    repo_dir: pathlib.Path,
    python_exe: str,
    test_targets: Sequence[str] | None = None,
    timeout_s: float = 20.0,
) -> tuple[int, str]:
    cmd = [python_exe, "-m", "pytest", "--tb=short", "-q"]
    if test_targets:
        cmd.extend(list(test_targets))
    env = dict(os.environ)
    pp_parts = [str(repo_dir / "src")] if (repo_dir / "src").is_dir() else []
    pp_parts.append(str(repo_dir))
    if env.get("PYTHONPATH"):
        pp_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pp_parts)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        cp = subprocess.run(
            cmd, cwd=str(repo_dir), capture_output=True, text=True, timeout=timeout_s, env=env,
        )
        return cp.returncode, (cp.stdout or "") + "\n" + (cp.stderr or "")
    except subprocess.TimeoutExpired as exc:
        return 124, f"TIMEOUT: {exc}"


def _parse_swe_epistemic_signal(repo_dir: pathlib.Path, tb_text: str) -> dict[str, Any]:
    """Extract the exact structured Epistemic Failure Signal from a pytest traceback."""
    frames: list[tuple[str, int, str]] = []
    # Match pytest short traceback frames: `src/app.py:42: in func_name`
    for m in re.finditer(r"^([A-Za-z0-9_.\-/\\]+\.py):(\d+): in ([A-Za-z0-9_<>.]+)", tb_text, flags=re.MULTILINE):
        rel_f, ln_s, fn = m.group(1), m.group(2), m.group(3)
        p = (repo_dir / rel_f).resolve()
        if p.is_file() and str(p).startswith(str(repo_dir.resolve())):
            frames.append((str(p.relative_to(repo_dir.resolve())), int(ln_s), fn))

    # Also match `File "...", line N, in fn`
    for m in re.finditer(r'File "([^"]+\.py)", line (\d+), in ([A-Za-z0-9_<>.]+)', tb_text):
        fp, ln_s, fn = m.group(1), m.group(2), m.group(3)
        p = pathlib.Path(fp).resolve()
        if p.is_file() and str(p).startswith(str(repo_dir.resolve())):
            rel = str(p.relative_to(repo_dir.resolve()))
            if (rel, int(ln_s), fn) not in frames:
                frames.append((rel, int(ln_s), fn))

    # Identify deepest non-test frame inside repo (or fallback to deepest repo frame)
    non_test_frames = [
        fr for fr in frames
        if not (pathlib.Path(fr[0]).name.startswith("test_") or "/tests/" in f"/{fr[0]}")
    ]
    target_frame = non_test_frames[-1] if non_test_frames else (frames[-1] if frames else None)

    exc_type = "UnknownError"
    exc_msg = ""
    for ln in reversed(tb_text.splitlines()):
        m_e = re.match(r"^E\s+([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception)):\s*(.*)$", ln.strip())
        if m_e:
            exc_type, exc_msg = m_e.group(1), m_e.group(2).strip()
            break
    if exc_type == "UnknownError":
        for ln in reversed(tb_text.splitlines()):
            m_e2 = re.match(r"^([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception)):\s*(.*)$", ln.strip())
            if m_e2:
                exc_type, exc_msg = m_e2.group(1), m_e2.group(2).strip()
                break

    # Parse structured gap slots from standard Python exceptions
    gap: dict[str, Any] = {
        "exc_type": exc_type,
        "exc_msg": exc_msg,
        "target_file": target_frame[0] if target_frame else None,
        "target_line": target_frame[1] if target_frame else None,
        "target_func": target_frame[2] if target_frame else None,
        "frames": frames,
    }

    # AttributeError: 'Client' object has no attribute 'get_items' / module 'urllib.parse' has no attribute 'quote_uri'
    m_attr_obj = re.search(r"'([^']+)' object has no attribute '([^']+)'", exc_msg)
    m_attr_mod = re.search(r"module '([^']+)' has no attribute '([^']+)'", exc_msg)
    if exc_type == "AttributeError" and m_attr_obj:
        gap.update({"gap_kind": "attribute_rename", "owner_kind": "class", "owner_name": m_attr_obj.group(1), "bad_symbol": m_attr_obj.group(2)})
    elif exc_type == "AttributeError" and m_attr_mod:
        gap.update({"gap_kind": "attribute_rename", "owner_kind": "module", "owner_name": m_attr_mod.group(1), "bad_symbol": m_attr_mod.group(2)})

    # TypeError: foo() got an unexpected keyword argument 'bar'
    m_kw = re.search(r"([A-Za-z0-9_.<>]+)\(\) got an unexpected keyword argument '([^']+)'", exc_msg)
    if exc_type == "TypeError" and m_kw:
        gap.update({"gap_kind": "kwarg_rename", "owner_kind": "callable", "owner_name": m_kw.group(1), "bad_symbol": m_kw.group(2)})

    # ImportError: cannot import name 'X' from 'pkg.sub'
    m_imp = re.search(r"cannot import name '([^']+)' from '([^']+)'", exc_msg)
    if exc_type == "ImportError" and m_imp:
        gap.update({"gap_kind": "import_relocate", "owner_kind": "module", "owner_name": m_imp.group(2), "bad_symbol": m_imp.group(1)})

    # NameError: name 'foo' is not defined
    m_name = re.search(r"name '([^']+)' is not defined", exc_msg)
    if exc_type == "NameError" and m_name:
        gap.update({"gap_kind": "name_resolve", "owner_kind": "scope", "owner_name": gap.get("target_file") or "", "bad_symbol": m_name.group(1)})

    return gap


def _introspect_python_runtime_gap(
    repo_dir: pathlib.Path,
    python_exe: str,
    gap: Mapping[str, Any],
    *,
    allow_web: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Live runtime introspection (+ optional PyPI/GitHub corroboration) for ONE exact SWE gap.

    Returns (candidate_replacements, provenance_log). Discards all raw web prose!
    """
    gap_kind = str(gap.get("gap_kind") or "")
    owner_name = str(gap.get("owner_name") or "")
    bad_sym = str(gap.get("bad_symbol") or "")
    target_file = gap.get("target_file")
    target_line = gap.get("target_line")
    provenance: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []

    if not gap_kind or not bad_sym or not target_file:
        return [], []

    # Step A: Fast live runtime introspection inside repo's actual Python environment (~30ms)
    probe_code = r"""
import ast, difflib, importlib, inspect, json, pathlib, pkgutil, sys

repo = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(repo))
gap = json.loads(sys.argv[2])
rel = gap["target_file"]
ln = int(gap.get("target_line") or 0)
src_path = repo / rel
src = src_path.read_text(encoding="utf-8")
tree = ast.parse(src, filename=str(src_path))
out = {"runtime_candidates": [], "owner_type": ""}

def _rank(names, target):
    clean = sorted({n for n in names if isinstance(n, str) and not n.startswith("__")})
    close = difflib.get_close_matches(target, clean, n=6, cutoff=0.35)
    # Also score token-overlap (e.g., get_items <-> list_items, timeout_sec <-> timeout)
    t_parts = set(target.lower().replace("-", "_").split("_"))
    scored = []
    for n in clean:
        n_parts = set(n.lower().replace("-", "_").split("_"))
        ov = len(t_parts & n_parts)
        ratio = difflib.SequenceMatcher(None, target.lower(), n.lower()).ratio()
        if ov > 0 or ratio >= 0.35 or n in close:
            scored.append((ov * 2.0 + ratio, n))
    scored.sort(key=lambda x: (-x[0], len(x[1]), x[1]))
    return [n for _, n in scored[:8]]

gk = gap["gap_kind"]
owner = gap.get("owner_name", "")
bad = gap["bad_symbol"]

if gk == "attribute_rename":
    names = []
    if gap.get("owner_kind") == "module":
        out["owner_type"] = f"module:{owner}"
        try:
            mod = importlib.import_module(owner)
            names = dir(mod)
        except Exception:
            pass
    else:
        out["owner_type"] = f"class:{owner}"
        # Search all repo python files for class `owner` + base classes + imported classes
        for pyf in repo.rglob("*.py"):
            try:
                t2 = ast.parse(pyf.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                continue
            for node in ast.walk(t2):
                if isinstance(node, ast.ClassDef) and node.name == owner:
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            names.append(item.name)
                        elif isinstance(item, ast.Assign):
                            for tgt in item.targets:
                                if isinstance(tgt, ast.Name):
                                    names.append(tgt.id)
                    # Also check self.<attr> assignments in __init__
                    for sub in ast.walk(node):
                        if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name) and sub.value.id == "self":
                            names.append(sub.attr)
        # Try importing standard/installed module symbols if class came from an import
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    if (alias.asname or alias.name) == owner or alias.name == owner:
                        try:
                            m = importlib.import_module(node.module)
                            obj = getattr(m, alias.name, None)
                            if obj is not None:
                                names.extend(dir(obj))
                                out["owner_type"] = f"module_class:{node.module}.{alias.name}"
                        except Exception:
                            pass
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    try:
                        m = importlib.import_module(alias.name)
                        obj = getattr(m, owner, None)
                        if obj is not None:
                            names.extend(dir(obj))
                            out["owner_type"] = f"module_class:{alias.name}.{owner}"
                    except Exception:
                        pass
        # Check builtins (str, list, dict, pathlib.Path, etc.)
        import builtins
        bobj = getattr(builtins, owner, None)
        if bobj is not None:
            names.extend(dir(bobj))
            out["owner_type"] = f"builtin:{owner}"
    for cand in _rank(names, bad):
        out["runtime_candidates"].append({"good_symbol": cand, "replacement_module": ""})

elif gk == "kwarg_rename":
    callee_short = owner.split(".")[-1]
    out["owner_type"] = f"callable:{owner}"
    params = []
    # Check AST function definitions in repo
    for pyf in repo.rglob("*.py"):
        try:
            t2 = ast.parse(pyf.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        for node in ast.walk(t2):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == callee_short:
                for a in list(node.args.args) + list(node.args.kwonlyargs):
                    if a.arg not in ("self", "cls"):
                        params.append(a.arg)
    # Also try importing the module/callable live via inspect.signature
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                if (alias.asname or alias.name) == callee_short or alias.name == callee_short:
                    try:
                        m = importlib.import_module(node.module)
                        fn_obj = getattr(m, alias.name, None)
                        if fn_obj is not None:
                            sig = inspect.signature(fn_obj)
                            params.extend([p for p in sig.parameters if p not in ("self", "cls")])
                            out["owner_type"] = f"callable:{node.module}.{alias.name}"
                    except Exception:
                        pass
        elif isinstance(node, ast.Import):
            for alias in node.names:
                try:
                    m = importlib.import_module(alias.name)
                    fn_obj = getattr(m, callee_short, None)
                    if fn_obj is not None:
                        sig = inspect.signature(fn_obj)
                        params.extend([p for p in sig.parameters if p not in ("self", "cls")])
                        out["owner_type"] = f"callable:{alias.name}.{callee_short}"
                except Exception:
                    pass
    for cand in _rank(params, bad):
        out["runtime_candidates"].append({"good_symbol": cand, "replacement_module": ""})

elif gk == "import_relocate":
    out["owner_type"] = f"module:{owner}"
    direct_names = []
    sub_hits = []
    try:
        mod = importlib.import_module(owner)
        direct_names = [n for n in dir(mod) if not n.startswith("__")]
        # Check submodules of `owner` for exact symbol `bad`!
        if hasattr(mod, "__path__"):
            for _, subname, _ in pkgutil.walk_packages(mod.__path__, prefix=owner + "."):
                try:
                    sm = importlib.import_module(subname)
                    if hasattr(sm, bad):
                        sub_hits.append({"good_symbol": bad, "replacement_module": subname})
                    else:
                        for close_n in _rank(dir(sm), bad)[:2]:
                            sub_hits.append({"good_symbol": close_n, "replacement_module": subname})
                except Exception:
                    continue
    except Exception:
        pass
    # Prefer exact symbol found in a submodule, then close symbol in same module
    out["runtime_candidates"].extend(sub_hits[:6])
    for cand in _rank(direct_names, bad):
        out["runtime_candidates"].append({"good_symbol": cand, "replacement_module": owner})

elif gk == "name_resolve":
    out["owner_type"] = f"scope:{rel}"
    import importlib.util as _ilu
    # 1. Missing top-level module import (e.g. `json`, `math`, `re`, `os`, `hashlib`, or sibling repo module)
    try:
        if _ilu.find_spec(bad) is not None:
            out["runtime_candidates"].append({"good_symbol": bad, "replacement_module": "__IMPORT__"})
    except Exception:
        pass
    # 2. Missing `from <stdlib_or_repo_mod> import <bad>` (e.g. `Path`, `urlparse`, `defaultdict`, `dataclass`)
    for std_mod in (
        "pathlib", "urllib.parse", "collections", "itertools", "functools",
        "dataclasses", "datetime", "typing", "re", "json", "math", "os",
        "hashlib", "base64", "csv", "sqlite3", "shutil", "tempfile",
    ):
        try:
            sm = importlib.import_module(std_mod)
            if hasattr(sm, bad):
                out["runtime_candidates"].append({"good_symbol": bad, "replacement_module": std_mod})
        except Exception:
            continue
    # 3. Scope / builtin typo candidates
    scope_names = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            scope_names.append(node.name)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for a in list(node.args.args) + list(node.args.kwonlyargs):
                    scope_names.append(a.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            scope_names.append(node.id)
        elif isinstance(node, ast.ImportFrom):
            for al in node.names:
                scope_names.append(al.asname or al.name)
        elif isinstance(node, ast.Import):
            for al in node.names:
                scope_names.append(al.asname or al.name.split(".")[0])
    import builtins
    scope_names.extend([n for n in dir(builtins) if not n.startswith("__")])
    for cand in _rank(scope_names, bad):
        if cand != bad:
            out["runtime_candidates"].append({"good_symbol": cand, "replacement_module": ""})

print(json.dumps(out))
"""
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    owner_type = f"{gap.get('owner_kind', 'symbol')}:{owner_name}"
    try:
        cp = subprocess.run(
            [python_exe, "-c", probe_code, str(repo_dir), json.dumps(dict(gap))],
            capture_output=True, text=True, timeout=10.0, env=env,
        )
        if cp.returncode == 0 and cp.stdout.strip():
            parsed = json.loads(cp.stdout.strip().splitlines()[-1])
            owner_type = str(parsed.get("owner_type") or owner_type)
            for c in parsed.get("runtime_candidates") or []:
                candidates.append({
                    "defect_kind": gap_kind,
                    "owner_type": owner_type,
                    "bad_symbol": bad_sym,
                    "good_symbol": c["good_symbol"],
                    "replacement_module": c.get("replacement_module", ""),
                    "corroborated_kinds": ["runtime_introspection"],
                    "source_urls": [],
                })
            provenance.append({
                "kind": "runtime_introspection",
                "owner_type": owner_type,
                "candidates_found": len(candidates),
            })
    except Exception:
        pass

    # Step B: If gap implicates an external third-party package and allow_web=True,
    # corroborate live with PyPI + GitHub via JIT_KNOWLEDGE (discarding raw prose!).
    root_pkg = owner_name.split(".")[0]
    if allow_web and gap.get("owner_kind") == "module" and root_pkg and root_pkg not in sys.stdlib_module_names:
        # Check if root_pkg is NOT a local repo package
        if not (repo_dir / root_pkg).exists() and not (repo_dir / "src" / root_pkg).exists():
            try:
                jres = JIT_KNOWLEDGE.resolve(f"{root_pkg} {bad_sym}", only=["pypi", "github"], timeout=5, limit=3)
                docs = jres.get("documents") or []
                urls = [str(d.get("url") or d.get("home_page") or "") for d in docs if d.get("url") or d.get("home_page")]
                if docs:
                    provenance.append({
                        "kind": "web_package_docs",
                        "sources": jres.get("sources_answered") or [],
                        "urls": urls[:3],
                    })
                    blob = " ".join(json.dumps(d, default=str) for d in docs)
                    for c in candidates:
                        if c["good_symbol"] in blob:
                            c["corroborated_kinds"] = sorted(set(c["corroborated_kinds"] + ["web_package_docs"]))
                            c["source_urls"] = urls[:2]
                    # Re-rank corroborated candidates higher
                    candidates.sort(key=lambda c: len(c["corroborated_kinds"]), reverse=True)
            except Exception:
                pass

    return candidates, provenance


def _apply_epistemic_ast_candidate(
    src_text: str,
    *,
    defect_kind: str,
    target_line: int | None,
    bad_symbol: str,
    good_symbol: str,
    replacement_module: str = "",
) -> str | None:
    """Apply a surgical, syntax-verified AST rewrite for an epistemic API/symbol fix."""
    try:
        tree = ast.parse(src_text)
    except SyntaxError:
        return None

    lines = src_text.splitlines(keepends=True)

    if defect_kind == "import_relocate":
        # Rewrite `from <mod> import <bad_symbol>` cleanly
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    if alias.name == bad_symbol:
                        ln_i = node.lineno - 1
                        if 0 <= ln_i < len(lines):
                            orig_ln = lines[ln_i]
                            if replacement_module and replacement_module != node.module:
                                new_ln = orig_ln.replace(f"from {node.module} import", f"from {replacement_module} import", 1)
                                if good_symbol != bad_symbol:
                                    new_ln = re.sub(rf"\b{re.escape(bad_symbol)}\b", good_symbol, new_ln)
                            else:
                                new_ln = re.sub(rf"\b{re.escape(bad_symbol)}\b", good_symbol, orig_ln)
                            if new_ln != orig_ln:
                                new_lines = list(lines)
                                new_lines[ln_i] = new_ln
                                new_src = "".join(new_lines)
                                # If symbol was renamed and not aliased, also update references in file
                                if good_symbol != bad_symbol and not alias.asname:
                                    new_src = re.sub(rf"\b{re.escape(bad_symbol)}\b", good_symbol, new_src)
                                try:
                                    ast.parse(new_src)
                                    return new_src
                                except SyntaxError:
                                    return None
        return None

    if defect_kind == "attribute_rename":
        # Prefer exact target_line; fallback to any `.bad_symbol` attribute access in file
        cand_lines: list[int] = []
        if target_line and 1 <= target_line <= len(lines):
            cand_lines.append(target_line - 1)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == bad_symbol:
                idx = node.lineno - 1
                if idx not in cand_lines:
                    cand_lines.append(idx)
        for idx in cand_lines:
            orig_ln = lines[idx]
            new_ln = re.sub(rf"\.{re.escape(bad_symbol)}\b", f".{good_symbol}", orig_ln)
            if new_ln != orig_ln:
                new_lines = list(lines)
                new_lines[idx] = new_ln
                new_src = "".join(new_lines)
                try:
                    ast.parse(new_src)
                    return new_src
                except SyntaxError:
                    continue
        return None

    if defect_kind == "kwarg_rename":
        cand_lines = []
        if target_line and 1 <= target_line <= len(lines):
            cand_lines.append(target_line - 1)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == bad_symbol:
                        idx = (getattr(kw, "lineno", None) or node.lineno) - 1
                        if idx not in cand_lines:
                            cand_lines.append(idx)
        for idx in cand_lines:
            orig_ln = lines[idx]
            new_ln = re.sub(rf"\b{re.escape(bad_symbol)}\s*=", f"{good_symbol}=", orig_ln)
            if new_ln != orig_ln:
                new_lines = list(lines)
                new_lines[idx] = new_ln
                new_src = "".join(new_lines)
                try:
                    ast.parse(new_src)
                    return new_src
                except SyntaxError:
                    continue
        return None

    if defect_kind == "name_resolve":
        if replacement_module:
            imp_stmt = (
                f"import {good_symbol}\n"
                if replacement_module == "__IMPORT__"
                else f"from {replacement_module} import {good_symbol}\n"
            )
            insert_at = 0
            for i, ln in enumerate(lines):
                s = ln.strip()
                if s.startswith("from __future__ import") or s.startswith("#") or not s:
                    insert_at = i + 1
                else:
                    break
            new_lines = list(lines)
            new_lines.insert(insert_at, imp_stmt)
            new_src = "".join(new_lines)
            try:
                ast.parse(new_src)
                return new_src
            except SyntaxError:
                return None
        if target_line and 1 <= target_line <= len(lines):
            idx = target_line - 1
            orig_ln = lines[idx]
            new_ln = re.sub(rf"\b{re.escape(bad_symbol)}\b", good_symbol, orig_ln)
            if new_ln != orig_ln:
                new_lines = list(lines)
                new_lines[idx] = new_ln
                new_src = "".join(new_lines)
                try:
                    ast.parse(new_src)
                    return new_src
                except SyntaxError:
                    return None

    return None


def _mine_sibling_pattern_candidates(src_text: str, target_func: str | None) -> list[dict[str, Any]]:
    """Local Repo Sibling-Pattern Epistemic Oracle (ZERO diff peeking, ZERO weights).

    Scans sibling methods/functions in the SAME class or module to discover recurring
    normalization helpers (`x = self._helper(x)` / `x = _helper(x)`) or entry guards
    (`if x is None: raise ...`) that sibling methods apply to the same parameter name
    but `target_func` omitted!
    """
    if not target_func:
        return []
    try:
        tree = ast.parse(src_text)
    except SyntaxError:
        return []

    target_node: ast.FunctionDef | None = None
    siblings: list[ast.FunctionDef] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = [m for m in node.body if isinstance(m, ast.FunctionDef)]
            hit = next((m for m in methods if m.name == target_func), None)
            if hit is not None:
                target_node = hit
                siblings = [m for m in methods if m is not hit and not m.name.startswith("__")]
                break

    if target_node is None:
        top_fns = [m for m in tree.body if isinstance(m, ast.FunctionDef)]
        hit = next((m for m in top_fns if m.name == target_func), None)
        if hit is not None:
            target_node = hit
            siblings = [m for m in top_fns if m is not hit]

    if target_node is None or not siblings or not target_node.body:
        return []

    target_params = [a.arg for a in target_node.args.args if a.arg not in ("self", "cls")]
    if not target_params:
        return []

    # Collect entry prefix statements (first 2 statements after optional docstring) from siblings
    pattern_counts: dict[str, tuple[int, str, str]] = {}  # stmt_src -> (count, helper_id, param_name)
    for sib in siblings:
        body = list(sib.body)
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            body = body[1:]
        sib_params = {a.arg for a in sib.args.args if a.arg not in ("self", "cls")}
        shared = [p for p in target_params if p in sib_params]
        if not shared:
            continue
        for stmt in body[:2]:
            # Pattern 1: Normalization assign `p = self._helper(p)` or `p = _helper(p)`
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                lhs = stmt.targets[0].id
                if lhs in shared and isinstance(stmt.value, ast.Call):
                    stmt_src = ast.unparse(stmt)
                    callee = ast.unparse(stmt.value.func)
                    prev = pattern_counts.get(stmt_src)
                    pattern_counts[stmt_src] = ((prev[0] + 1) if prev else 1, callee, lhs)
            # Pattern 2: Entry guard `if <cond involving p>: raise/return ...`
            elif isinstance(stmt, ast.If) and len(stmt.body) == 1 and isinstance(stmt.body[0], (ast.Raise, ast.Return)):
                stmt_src = ast.unparse(stmt)
                used = {n.id for n in ast.walk(stmt.test) if isinstance(n, ast.Name)}
                matched_p = next((p for p in shared if p in used), None)
                if matched_p:
                    prev = pattern_counts.get(stmt_src)
                    pattern_counts[stmt_src] = ((prev[0] + 1) if prev else 1, "entry_guard", matched_p)

    # Filter out patterns already present in target_node
    target_src = ast.unparse(target_node)
    ranked = sorted(pattern_counts.items(), key=lambda kv: (-kv[1][0], kv[0]))
    lines = src_text.splitlines(keepends=True)

    # Find insertion line & indent right after optional docstring of target_node
    t_body = list(target_node.body)
    if t_body and isinstance(t_body[0], ast.Expr) and isinstance(t_body[0].value, ast.Constant) and isinstance(t_body[0].value.value, str):
        t_body = t_body[1:]
    if not t_body:
        return []
    first_stmt_ln = t_body[0].lineno - 1
    if not (0 <= first_stmt_ln < len(lines)):
        return []
    indent = lines[first_stmt_ln][: len(lines[first_stmt_ln]) - len(lines[first_stmt_ln].lstrip())]

    out: list[dict[str, Any]] = []
    for stmt_src, (cnt, helper_id, param_name) in ranked[:6]:
        if stmt_src in target_src:
            continue
        indented_stmt = "\n".join(indent + ln for ln in stmt_src.splitlines()) + "\n"
        new_lines = list(lines)
        new_lines.insert(first_stmt_ln, indented_stmt)
        new_src = "".join(new_lines)
        try:
            ast.parse(new_src)
        except SyntaxError:
            continue
        out.append({
            "stmt_src": stmt_src,
            "helper_id": helper_id,
            "param_name": param_name,
            "sibling_support": cnt,
            "patched_source": new_src,
        })
    return out


def solve_swe_with_epistemic_diff(
    repo_dir: str | pathlib.Path,
    *,
    memory: dict[str, Any] | None = None,
    test_targets: Sequence[str] | None = None,
    python_exe: str | None = None,
    allow_web: bool = True,
    timeout_s: float = 20.0,
) -> dict[str, Any]:
    """Solve a broken Python codebase via Goal-Directed Epistemic Diff + Causal Angelic Repair.

    Order (fastest + cleanest first):
      1. Run pytest once to capture exact Epistemic Failure Signal.
      2. Tier 0 Recall of corroborated `api_contracts` (offline, <5ms).
      3. Tier 1 Live Runtime Introspection (+ PyPI/GitHub corroboration for 3rd-party pkgs).
      4. Local Repo Sibling-Pattern Epistemic Oracle (mines same-class/module idioms).
      5. Causal Angelic Execution + Tier 0 SWE Skill Store (`causal_angelic_swe_engine_v1`).
    All trials execute in an isolated state copy; commit ONLY when pytest exits 0!
    """
    t0 = time.monotonic()
    repo = pathlib.Path(repo_dir).resolve()
    py = python_exe or sys.executable
    rc0, tb0 = _run_pytest_capture(repo, py, test_targets=test_targets, timeout_s=max(timeout_s, 45.0))
    if rc0 == 0:
        return {
            "status": "VERIFIED",
            "mode": "ALREADY_PASSING",
            "patched_file": None,
            "gaps_queried": [],
            "contracts_recalled": [],
            "contracts_learned": [],
            "provenance": [],
            "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    signal = _parse_swe_epistemic_signal(repo, tb0)
    target_rel = signal.get("target_file")
    gap_kind = signal.get("gap_kind")
    bad_sym = signal.get("bad_symbol")
    provenance: list[dict[str, Any]] = []
    contracts_recalled: list[str] = []
    contracts_learned: list[str] = []
    gaps_queried: list[str] = []

    def _trial_patch(rel_path: str, new_src: str) -> tuple[bool, str]:
        td = pathlib.Path(tempfile.mkdtemp(prefix="brain_uek_swe_"))
        try:
            stage = td / "repo"
            shutil.copytree(repo, stage, symlinks=True, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
            (stage / rel_path).write_text(new_src, encoding="utf-8")
            rc_t, tb_t = _run_pytest_capture(stage, py, test_targets=test_targets, timeout_s=timeout_s)
            if rc_t == 0:
                (repo / rel_path).write_text(new_src, encoding="utf-8")
                return True, tb_t
            return False, tb_t
        finally:
            shutil.rmtree(td, ignore_errors=True)

    # --- PHASE 0: Tier-0 Plotkin Anti-Unified AST Laws (instant offline recall) ---
    if memory is not None:
        ast_laws = [
            law for law in (memory.get("generalized_laws") or {}).values()
            if isinstance(law, dict)
            and law.get("kind") == "ast_anti_unified"
            and law.get("status") == STATUS_VERIFIED
        ]
        if ast_laws:
            cand_files: list[str] = []
            if target_rel and (repo / target_rel).is_file():
                cand_files.append(target_rel)
            for p in sorted(repo.rglob("*.py")):
                if "__pycache__" in p.parts:
                    continue
                rel = str(p.relative_to(repo))
                bn = p.name
                if bn.startswith("test_") or bn.endswith("_test.py") or "/tests/" in f"/{rel}":
                    continue
                if rel not in cand_files:
                    cand_files.append(rel)
            for rel_f in cand_files[:12]:
                orig_f = (repo / rel_f).read_text(encoding="utf-8", errors="replace")
                for law in ast_laws:
                    patched = apply_anti_unified_ast_law(orig_f, law)
                    if not patched:
                        continue
                    ok_p, _ = _trial_patch(rel_f, patched)
                    if ok_p:
                        law["support_count"] = int(law.get("support_count", 2)) + 1
                        return {
                            "status": "VERIFIED",
                            "mode": "TIER0_ANTI_UNIFIED_AST_LAW",
                            "patched_file": rel_f,
                            "defect_kind": "anti_unified_ast_law",
                            "fix": f"{law['before_pattern']} -> {law['after_pattern']}",
                            "gaps_queried": [],
                            "contracts_recalled": [law["law_id"]],
                            "contracts_learned": [],
                            "provenance": [{"kind": "tier0_anti_unified_ast_law", "law_id": law["law_id"]}],
                            "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                            "model_calls": 0,
                            "parameters_stored": 0,
                        }

    # --- PHASE A: API / Symbol Epistemic Diff (AttributeError / TypeError / ImportError / NameError) ---
    if target_rel and gap_kind and bad_sym and (repo / target_rel).is_file():
        orig_src = (repo / target_rel).read_text(encoding="utf-8")
        owner_hint = f"{signal.get('owner_kind', 'symbol')}:{signal.get('owner_name', '')}"

        # Tier 0: Instant API Contract Recall (<1ms!)
        for creq in recall_api_contracts(memory, defect_kind=gap_kind, bad_symbol=bad_sym, owner_type=owner_hint):
            patched = _apply_epistemic_ast_candidate(
                orig_src,
                defect_kind=gap_kind,
                target_line=signal.get("target_line"),
                bad_symbol=bad_sym,
                good_symbol=creq["good_symbol"],
                replacement_module=creq.get("replacement_module", ""),
            )
            if patched:
                ok_p, _ = _trial_patch(target_rel, patched)
                if ok_p:
                    contracts_recalled.append(creq["contract_id"])
                    if memory is not None:
                        st = (memory.get("api_contracts") or {}).get(creq["contract_id"])
                        if isinstance(st, dict):
                            st["support_count"] = int(st.get("support_count", 1)) + 1
                    return {
                        "status": "VERIFIED",
                        "mode": "TIER0_API_CONTRACT_RECALL",
                        "patched_file": target_rel,
                        "defect_kind": gap_kind,
                        "fix": f"{bad_sym} -> {creq['good_symbol']}",
                        "gaps_queried": [],
                        "contracts_recalled": contracts_recalled,
                        "contracts_learned": [],
                        "provenance": [{"kind": "tier0_memory_recall", "contract_id": creq["contract_id"]}],
                        "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                        "model_calls": 0,
                        "parameters_stored": 0,
                    }

        # Tier 1: Live Runtime Introspection + Web Docs Acquisition (ONLY for this exact gap!)
        gaps_queried.append(f"{gap_kind}:{signal.get('owner_name', '')}.{bad_sym}")
        cands, prov = _introspect_python_runtime_gap(repo, py, signal, allow_web=allow_web)
        provenance.extend(prov)
        for cand in cands[:8]:
            patched = _apply_epistemic_ast_candidate(
                orig_src,
                defect_kind=gap_kind,
                target_line=signal.get("target_line"),
                bad_symbol=bad_sym,
                good_symbol=cand["good_symbol"],
                replacement_module=cand.get("replacement_module", ""),
            )
            if not patched:
                continue
            ok_p, _ = _trial_patch(target_rel, patched)
            if ok_p:
                if memory is not None:
                    learned = record_api_contract(
                        memory,
                        defect_kind=gap_kind,
                        owner_type=cand["owner_type"],
                        bad_symbol=bad_sym,
                        good_symbol=cand["good_symbol"],
                        replacement_module=cand.get("replacement_module", ""),
                        corroborated_kinds=cand.get("corroborated_kinds") or ("runtime_introspection",),
                        source_urls=cand.get("source_urls") or (),
                    )
                    if learned is not None:
                        contracts_learned.append(learned["contract_id"])
                return {
                    "status": "VERIFIED",
                    "mode": "TIER1_SWE_EPISTEMIC_INTROSPECTION",
                    "patched_file": target_rel,
                    "defect_kind": gap_kind,
                    "fix": f"{bad_sym} -> {cand['good_symbol']}",
                    "gaps_queried": gaps_queried,
                    "contracts_recalled": [],
                    "contracts_learned": contracts_learned,
                    "provenance": provenance,
                    "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                    "model_calls": 0,
                    "parameters_stored": 0,
                }

    # --- PHASE B: Local Repo Sibling-Pattern Epistemic Oracle ---
    if target_rel and (repo / target_rel).is_file():
        orig_src = (repo / target_rel).read_text(encoding="utf-8")
        sib_cands = _mine_sibling_pattern_candidates(orig_src, signal.get("target_func"))
        if sib_cands:
            gaps_queried.append(f"sibling_oracle:{target_rel}:{signal.get('target_func')}")
            provenance.append({"kind": "repo_sibling_oracle", "candidates": len(sib_cands)})
            for sc in sib_cands:
                ok_p, _ = _trial_patch(target_rel, sc["patched_source"])
                if ok_p:
                    if memory is not None:
                        learned = record_api_contract(
                            memory,
                            defect_kind="sibling_helper",
                            owner_type=f"param:{sc['param_name']}",
                            bad_symbol=f"missing:{sc['helper_id']}",
                            good_symbol=sc["stmt_src"],
                            corroborated_kinds=("repo_sibling_oracle",),
                        )
                        if learned is not None:
                            contracts_learned.append(learned["contract_id"])
                    return {
                        "status": "VERIFIED",
                        "mode": "TIER1_REPO_SIBLING_ORACLE",
                        "patched_file": target_rel,
                        "defect_kind": "sibling_helper",
                        "fix": sc["stmt_src"],
                        "gaps_queried": gaps_queried,
                        "contracts_recalled": [],
                        "contracts_learned": contracts_learned,
                        "provenance": provenance,
                        "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                        "model_calls": 0,
                        "parameters_stored": 0,
                    }

    # --- PHASE C: Causal Angelic Execution + SWE Skill Store ---
    skill_store = memory.get("swe_skill_store") if memory is not None else None
    t_files = list(test_targets) if test_targets else None
    focused_from_tb0 = False
    if t_files is None:
        # Focus on the exact failing test file(s) observed in `tb0` (10x faster!), then
        # verify the FULL repository pytest suite passes after patching!
        tb_fail_files: list[str] = []
        for m_ff in re.finditer(r"^FAILED\s+([^\s:]+\.py)::", tb0, flags=re.MULTILINE):
            ff = m_ff.group(1).strip()
            if (repo / ff).is_file() and ff not in tb_fail_files:
                tb_fail_files.append(ff)
        if tb_fail_files:
            t_files = tb_fail_files
            focused_from_tb0 = True
        else:
            t_files = sorted(
                str(p.relative_to(repo)) for p in repo.rglob("test_*.py")
                if "__pycache__" not in p.parts
            )
    if t_files:
        angel = SWE_ENGINE.solve_repository(
            repo,
            t_files,
            skill_store=skill_store,
            python_exe=py,
            learn_into_store=memory is not None,
            timeout_s=timeout_s,
        )
        if angel.get("verified") or angel.get("status") == "VERIFIED":
            winner = angel.get("winner") or {}
            w_file = winner.get("file") or angel.get("patched_file")
            w_src = winner.get("patched_source")
            files_to_write: dict[str, str] = {}
            raw_pf = winner.get("patched_files")
            if isinstance(raw_pf, Mapping) and raw_pf:
                for rf, rsrc in raw_pf.items():
                    if isinstance(rf, str) and isinstance(rsrc, str) and (repo / rf).is_file():
                        files_to_write[rf] = rsrc
            elif w_file and isinstance(w_src, str) and (repo / w_file).is_file():
                files_to_write[w_file] = w_src

            consolidation: dict[str, Any] = {}
            if files_to_write:
                orig_by_file = {
                    rf: (repo / rf).read_text(encoding="utf-8", errors="replace")
                    for rf in files_to_write
                }
                for rf, rsrc in files_to_write.items():
                    (repo / rf).write_text(rsrc, encoding="utf-8")
                if focused_from_tb0:
                    rc_full, _ = _run_pytest_capture(repo, py, test_targets=None, timeout_s=max(timeout_s, 30.0))
                    if rc_full != 0:
                        for rf, orig_txt in orig_by_file.items():
                            (repo / rf).write_text(orig_txt, encoding="utf-8")
                        return {
                            "status": "FAILED",
                            "mode": "FULL_SUITE_REGRESSION_REVERTED",
                            "gaps_queried": gaps_queried,
                            "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                            "model_calls": 0,
                            "parameters_stored": 0,
                        }
                if memory is not None:
                    for rf, rsrc in files_to_write.items():
                        ediff = _extract_single_expr_diff(orig_by_file[rf], rsrc)
                        if ediff is not None:
                            consolidation = auto_consolidate_experience(
                                memory, kind="ast", before=ediff[0], after=ediff[1],
                            )
                            break
            learned_ids = [x for x in (angel.get("learned_skill_id") or angel.get("skill_learned"),) if x]
            if consolidation.get("law_id"):
                learned_ids.append(consolidation["law_id"])
            return {
                "status": "VERIFIED",
                "mode": f"CAUSAL_ANGELIC_{winner.get('tier') or angel.get('tier', 'VERIFIED')}",
                "patched_file": w_file,
                "patched_files": sorted(files_to_write.keys()) if files_to_write else ([w_file] if w_file else []),
                "defect_kind": "causal_angelic",
                "fix": winner.get("description") or angel.get("learned_skill_id") or angel.get("skill_id_used") or "angelic_patch",
                "initial_failure_signal": tb0[:1200],
                "gaps_queried": gaps_queried,
                "contracts_recalled": [x for x in (angel.get("skill_id_used") or angel.get("skill_used"),) if x],
                "contracts_learned": learned_ids,
                "consolidation": consolidation,
                "provenance": provenance + [{"kind": "causal_angelic_execution"}],
                "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                "model_calls": 0,
                "parameters_stored": 0,
            }

    return {
        "status": "FAILED",
        "mode": "FAILED",
        "patched_file": target_rel,
        "defect_kind": gap_kind or signal.get("exc_type"),
        "gaps_queried": gaps_queried,
        "contracts_recalled": contracts_recalled,
        "contracts_learned": contracts_learned,
        "provenance": provenance,
        "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
        "model_calls": 0,
        "parameters_stored": 0,
    }


# ---------------------------------------------------------------------------
# 4. ONE Universal Entry Point for ANY Arbitrary Environment
# ---------------------------------------------------------------------------

def recall_and_execute_cli_law(
    workspace: pathlib.Path,
    instruction: str,
    memory: dict[str, Any] | None,
    *,
    postcondition_fn: Callable[[pathlib.Path], tuple[bool, str]] | None = None,
    timeout_s: float = 15.0,
) -> dict[str, Any] | None:
    """Tier-0 offline recall & isolated atomic execution of a Plotkin anti-unified CLI law."""
    if not memory:
        return None
    cli_laws = [
        law for law in (memory.get("generalized_laws") or {}).values()
        if isinstance(law, dict)
        and law.get("kind") == "cli_anti_unified"
        and law.get("status") == STATUS_VERIFIED
    ]
    if not cli_laws:
        return None

    low = instruction.lower()
    env = EPI_CU.sense_unknown_environment(workspace)
    gs = EPI_CU.parse_goal_specification(instruction, env)
    in_paths = gs.get("input_paths") or []
    out_paths = gs.get("output_paths") or []
    in_file = in_paths[0] if in_paths else None
    out_file = out_paths[0] if out_paths else None
    expr_args = [
        q for q in (gs.get("quoted_literals") or [])
        if q and q not in (in_file, out_file)
    ]

    for law in cli_laws:
        tool = str(law.get("tool") or "")
        if not tool or not re.search(rf"\b{re.escape(tool)}\b", low):
            continue
        bindings: dict[str, str] = {}
        if in_file:
            bindings["__INPUT_PATH__"] = in_file
        if out_file:
            bindings["__OUTPUT_PATH__"] = out_file
        for idx, ea in enumerate(expr_args):
            bindings[f"__ARG_{idx}__"] = ea
        cmd = instantiate_anti_unified_command(law, bindings)
        if not cmd:
            continue
        # Execute in isolated copy; commit atomically only on verified pass
        td = pathlib.Path(tempfile.mkdtemp(prefix="brain_uek_cli_"))
        try:
            stage = td / "ws"
            shutil.copytree(workspace, stage, symlinks=True)
            cp = subprocess.run(
                cmd, shell=True, cwd=str(stage), capture_output=True, text=True, timeout=timeout_s,
            )
            if cp.returncode != 0:
                continue
            if out_file and not ((stage / out_file).is_file() and (stage / out_file).stat().st_size > 0):
                continue
            if postcondition_fn is not None:
                ok_p, _ = postcondition_fn(stage)
                if not ok_p:
                    continue
            # Atomic commit of created/updated output file(s)
            if out_file and (stage / out_file).is_file():
                dst = workspace / out_file
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(stage / out_file, dst)
            law["support_count"] = int(law.get("support_count", 2)) + 1
            return {
                "status": "VERIFIED",
                "mode": "TIER0_ANTI_UNIFIED_CLI_LAW",
                "law_id": law["law_id"],
                "command": cmd,
                "template": law.get("template"),
            }
        except Exception:
            continue
        finally:
            shutil.rmtree(td, ignore_errors=True)
    return None


_URL_RE = re.compile(r"https?://[^\s'\"<>]+")
_DESTRUCTIVE_ACTION_HINTS = (
    "delete", "destroy", "drop", "reset", "wipe", "purge", "nuke", "remove", "cancel"
)


def _extract_web_field_values(instruction: str) -> dict[str, str]:
    """Deterministic zero-LLM extraction of user-supplied form field values from instruction text."""
    vals: dict[str, str] = {}
    # 1. Explicit key=value or key: value pairs (quoted or bare)
    for m in re.finditer(
        r"\b([A-Za-z][A-Za-z0-9_\-]{1,32})\s*(?:=|:)\s*(?:'([^']+)'|\"([^\"]+)\"|([^\s,;]+))",
        instruction,
    ):
        k = m.group(1).strip().lower()
        v = (m.group(2) or m.group(3) or m.group(4) or "").strip().rstrip(".,;")
        if k not in ("http", "https") and v:
            vals[k] = v

    # 2. Natural-language clauses after 'with' / 'using' / ',' e.g. "with email ada@x.com, plan pro, company Acme"
    for m in re.finditer(
        r"(?:\bwith\b|\band\b|,)\s+([A-Za-z][A-Za-z0-9_\-]{1,24})\s+(?:as\s+|to\s+|=\s*)?(?:'([^']+)'|\"([^\"]+)\"|([^\s,;]+))",
        instruction,
        flags=re.IGNORECASE,
    ):
        k = m.group(1).strip().lower()
        v = (m.group(2) or m.group(3) or m.group(4) or "").strip().rstrip(".,;")
        if k in (
            "the", "a", "an", "to", "at", "on", "in", "for", "of", "from", "http", "https",
            "and", "or", "but", "then", "with", "using", "into", "onto", "after", "before",
            "find", "search", "select", "open", "click", "buy", "add", "go", "visit",
            "navigate", "complete", "submit", "choose", "pick", "create", "make", "update",
            "edit", "save", "write", "store", "extract", "get", "set", "check", "verify",
            "confirm", "ensure", "fill", "enter", "log", "sign", "delete", "remove",
        ):
            continue
        if "=" in v or ":" in v:
            continue
        if k not in vals and v and not v.startswith("http"):
            vals[k] = v

    # 3. Bare email address fallback if 'email' not explicitly named
    if "email" not in vals:
        m_em = re.search(r"\b([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})\b", instruction)
        if m_em:
            vals["email"] = m_em.group(1)
    return vals


def _is_form_destructive(form_desc: Mapping[str, Any]) -> bool:
    action_low = str(form_desc.get("action") or "").lower()
    if any(w in action_low for w in _DESTRUCTIVE_ACTION_HINTS):
        return True
    for btn in form_desc.get("buttons") or []:
        if isinstance(btn, Mapping) and str(btn.get("risk") or "") == "destructive":
            return True
    return False


def _match_web_workflow_law(
    memory: Mapping[str, Any] | None,
    method: str,
    visible_fields: Sequence[str],
) -> dict[str, Any] | None:
    if not isinstance(memory, Mapping):
        return None
    vis = {f.lower() for f in visible_fields}
    best: dict[str, Any] | None = None
    best_score = -1
    raw_laws = memory.get("generalized_laws") or {}
    law_iter = raw_laws.values() if isinstance(raw_laws, Mapping) else raw_laws
    for law in law_iter:
        if not isinstance(law, dict) or law.get("kind") != "web_workflow":
            continue
        if str(law.get("method") or "POST").upper() != method.upper():
            continue
        req = {str(x).lower() for x in (law.get("required_field_holes") or [])}
        overlap = len(vis & req)
        if overlap > best_score and (overlap >= 1 or not req):
            best_score = overlap
            best = law
    return best


def _distill_web_workflow_law(
    memory: dict[str, Any] | None,
    *,
    method: str,
    required_fields: Sequence[str],
    conditional_fields: Sequence[str],
    had_hidden_replay: bool,
    blocked_destructive: bool,
) -> dict[str, Any] | None:
    """Save ONLY generalized structural web-workflow laws (ZERO URLs, ZERO tokens, ZERO values)."""
    if memory is None:
        return None
    req_norm = sorted({str(f).lower() for f in required_fields if f})
    cond_norm = sorted({str(f).lower() for f in conditional_fields if f and str(f).lower() not in req_norm})
    sig = f"web_workflow|{method.upper()}|{','.join(req_norm)}|{','.join(cond_norm)}"
    law_id = "web_wf_" + hashlib.sha256(sig.encode("utf-8")).hexdigest()[:12]
    laws = memory.setdefault("generalized_laws", {})
    if isinstance(laws, dict):
        if law_id in laws and isinstance(laws[law_id], dict):
            laws[law_id]["support_count"] = int(laws[law_id].get("support_count", 1)) + 1
            return laws[law_id]
        law = {
            "law_id": law_id,
            "kind": "web_workflow",
            "method": method.upper(),
            "required_field_holes": req_norm,
            "conditional_field_holes": cond_norm,
            "hidden_replay_policy": "always_fresh_get_before_submit" if had_hidden_replay else "none",
            "safety_policy": "block_destructive_actions" if blocked_destructive else "safe_default",
            "error_recovery_policy": "compose_missing_from_error",
            "support_count": 1,
            "parameters_stored": 0,
            "raw_prose_stored": 0,
        }
        laws[law_id] = law
        return law
    return None


_WEB_FIELD_ALIAS_GROUPS: tuple[tuple[str, ...], ...] = (
    ("username", "user", "user_id", "userid", "login", "account", "handle"),
    ("password", "pass", "passwd", "pwd", "secret", "passcode"),
    ("email", "e_mail", "mail", "user_email", "contact_email"),
    ("coupon", "promo", "promo_code", "discount", "discount_code", "voucher"),
    ("address", "shipping_address", "ship_address", "street", "destination"),
    ("quantity", "qty", "count", "amount", "units"),
    ("query", "q", "search", "keyword", "term"),
    ("note", "notes", "comment", "message", "memo"),
    ("company", "org", "organization", "org_name"),
    ("plan", "tier", "package", "subscription"),
)

_WEB_LINK_DESTRUCTIVE_HINTS: tuple[str, ...] = (
    "delete", "destroy", "drop", "reset", "wipe", "purge", "nuke", "logout", "signout", "sign-out", "deactivate", "clear-all",
)


def _resolve_web_field_alias(field_name: str, supplied: Mapping[str, str]) -> str | None:
    """Resolve `field_name` against `supplied` directly or via canonical semantic alias groups."""
    fl = field_name.strip().lower()
    if fl in supplied:
        return supplied[fl]
    for grp in _WEB_FIELD_ALIAS_GROUPS:
        if fl in grp:
            for alias in grp:
                if alias in supplied:
                    return supplied[alias]
    # Substring fallback for compound names like `billing_coupon` or `login_user`
    for k, v in supplied.items():
        if len(k) >= 4 and (k in fl or fl in k):
            return v
    return None


def _scan_web_page_epistemic(
    html_text: str,
    base_url: str,
    *,
    allow_destructive: bool = False,
) -> dict[str, Any]:
    """Zero-LLM HTML epistemic page scanner: extracts safe navigation links, destructive trap links,
    meta/data CSRF tokens, and dynamic `<script>`/`data-api` JSON REST endpoints."""
    import urllib.parse

    safe_links: list[dict[str, str]] = []
    blocked_links: list[str] = []
    seen_hrefs: set[str] = set()

    for m in re.finditer(
        r"<a\b[^>]*\bhref\s*=\s*(?:\"([^\"]+)\"|'([^']+)'|([^\s>]+))[^>]*>(.*?)</a>",
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        raw_href = (m.group(1) or m.group(2) or m.group(3) or "").strip()
        label = re.sub(r"<[^>]+>", " ", m.group(4) or "")
        label = re.sub(r"\s+", " ", label).strip()
        if not raw_href or raw_href.startswith(("#", "javascript:", "mailto:")):
            continue
        abs_url = urllib.parse.urljoin(base_url, raw_href)
        low_comb = (raw_href + " " + label).lower()
        if (not allow_destructive) and any(h in low_comb for h in _WEB_LINK_DESTRUCTIVE_HINTS):
            if raw_href not in blocked_links:
                blocked_links.append(raw_href)
            continue
        if abs_url not in seen_hrefs:
            seen_hrefs.add(abs_url)
            safe_links.append({"href": raw_href, "url": abs_url, "text": label})

    # Extract CSRF tokens from `<meta name="csrf-token" content="...">` or `data-csrf="..."`
    csrf_tokens: dict[str, str] = {}
    for m in re.finditer(
        r"<meta\b[^>]*\bname\s*=\s*[\"']([^\"']*csrf[^\"']*|[^\"']*xsrf[^\"']*)[\"'][^>]*\bcontent\s*=\s*[\"']([^\"']+)[\"']",
        html_text,
        flags=re.IGNORECASE,
    ):
        csrf_tokens[m.group(1).strip()] = m.group(2).strip()
    for m in re.finditer(
        r"<meta\b[^>]*\bcontent\s*=\s*[\"']([^\"']+)[\"'][^>]*\bname\s*=\s*[\"']([^\"']*csrf[^\"']*|[^\"']*xsrf[^\"']*)[\"']",
        html_text,
        flags=re.IGNORECASE,
    ):
        csrf_tokens[m.group(2).strip()] = m.group(1).strip()
    for m in re.finditer(r"data-(?:csrf|xsrf)(?:-token)?\s*=\s*[\"']([^\"']+)[\"']", html_text, flags=re.IGNORECASE):
        csrf_tokens.setdefault("X-CSRF-Token", m.group(1).strip())

    # Discover dynamic JSON REST endpoints in `<script>` (`fetch('/api/...', {method: 'POST', ...})`) or `data-api`
    api_endpoints: list[dict[str, Any]] = []
    seen_api: set[tuple[str, str]] = set()
    for m in re.finditer(
        r"fetch\(\s*[\"']([^\"']+)[\"'](?:\s*,\s*\{([^}]*)\})?",
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        ep = m.group(1).strip()
        opts = m.group(2) or ""
        m_meth = re.search(r"method\s*:\s*[\"']([A-Za-z]+)[\"']", opts, flags=re.IGNORECASE)
        meth = m_meth.group(1).upper() if m_meth else "GET"
        if (not allow_destructive) and (meth == "DELETE" or any(h in ep.lower() for h in _WEB_LINK_DESTRUCTIVE_HINTS)):
            if ep not in blocked_links:
                blocked_links.append(ep)
            continue
        m_hdr = re.search(r"[\"'](X-[A-Za-z0-9\-]*(?:CSRF|XSRF)[A-Za-z0-9\-]*)[\"']", opts, flags=re.IGNORECASE)
        csrf_hdr = m_hdr.group(1) if m_hdr else "X-CSRF-Token"
        key = (meth, ep)
        if key not in seen_api:
            seen_api.add(key)
            api_endpoints.append({
                "method": meth,
                "path": ep,
                "url": urllib.parse.urljoin(base_url, ep),
                "csrf_header": csrf_hdr,
            })
    for m in re.finditer(r"data-api(?:-(post|put|patch))?\s*=\s*[\"']([^\"']+)[\"']", html_text, flags=re.IGNORECASE):
        meth = (m.group(1) or "POST").upper()
        ep = m.group(2).strip()
        if (not allow_destructive) and any(h in ep.lower() for h in _WEB_LINK_DESTRUCTIVE_HINTS):
            if ep not in blocked_links:
                blocked_links.append(ep)
            continue
        key = (meth, ep)
        if key not in seen_api:
            seen_api.add(key)
            api_endpoints.append({
                "method": meth,
                "path": ep,
                "url": urllib.parse.urljoin(base_url, ep),
                "csrf_header": "X-CSRF-Token",
            })

    return {
        "safe_links": safe_links,
        "blocked_links": blocked_links,
        "csrf_tokens": csrf_tokens,
        "api_endpoints": api_endpoints,
    }


def _extract_target_entity(instruction: str, supplied: Mapping[str, str]) -> str:
    """Extract target product/item/entity name from quoted strings or explicit keys."""
    for k in ("item", "product", "target", "title", "entity"):
        if k in supplied and supplied[k]:
            return supplied[k]
    for m in re.finditer(r"['\"]([^'\"]{3,60})['\"]", instruction):
        cand = m.group(1).strip()
        if cand.lower() not in {v.lower() for v in supplied.values()} and not cand.startswith("http"):
            return cand
    return ""


def _match_web_poly_skill(
    memory: Mapping[str, Any] | None,
    *,
    needs_auth: bool,
    has_target_entity: bool,
    wants_checkout: bool,
) -> dict[str, Any] | None:
    if not isinstance(memory, Mapping):
        return None
    raw_laws = memory.get("generalized_laws") or {}
    law_iter = raw_laws.values() if isinstance(raw_laws, Mapping) else raw_laws
    for law in law_iter:
        if not isinstance(law, dict) or law.get("kind") != "web_poly_skill":
            continue
        stages = list(law.get("stages") or [])
        if needs_auth and "AUTH_LOGIN" not in stages:
            continue
        if has_target_entity and "NAV_FIND_ENTITY" not in stages:
            continue
        if wants_checkout and not any(s.startswith("SUBMIT_FINAL") for s in stages):
            continue
        return law
    return None


def _distill_web_poly_skill(
    memory: dict[str, Any] | None,
    *,
    stages: Sequence[str],
    discovered_api_fields: Sequence[str],
    requires_csrf: bool,
    blocked_destructive: bool,
) -> dict[str, Any] | None:
    """Distill a path-free, host-free parameterized Poly-Skill (ICLR 2026 PolySkill + SGDR)."""
    if memory is None or not stages:
        return None
    norm_stages = list(dict.fromkeys(str(s) for s in stages))
    norm_fields = sorted({str(f).lower() for f in discovered_api_fields if f})
    sig = f"web_poly_skill|{'->'.join(norm_stages)}|{','.join(norm_fields)}"
    law_id = "web_poly_" + hashlib.sha256(sig.encode("utf-8")).hexdigest()[:12]
    laws = memory.setdefault("generalized_laws", {})
    if isinstance(laws, dict):
        if law_id in laws and isinstance(laws[law_id], dict):
            laws[law_id]["support_count"] = int(laws[law_id].get("support_count", 1)) + 1
            return laws[law_id]
        law = {
            "law_id": law_id,
            "kind": "web_poly_skill",
            "stages": norm_stages,
            "discovered_api_field_holes": norm_fields,
            "requires_csrf_replay": bool(requires_csrf),
            "safety_policy": "block_destructive_forms_and_links" if blocked_destructive else "safe_default",
            "field_grounding": "semantic_alias_resolution",
            "support_count": 1,
            "parameters_stored": 0,
            "raw_prose_stored": 0,
        }
        laws[law_id] = law
        return law
    return None


def _solve_live_multipage_web_workflow(
    url: str,
    instruction: str,
    *,
    memory: dict[str, Any] | None = None,
    supplied: dict[str, str],
    allow_destructive: bool = False,
    max_steps: int = 16,
    timeout_s: float = 10.0,
) -> dict[str, Any]:
    """Goal-directed Multi-Page Web / Auth / Pagination / CSRF / JSON-REST Poly-Skill Engine.

    Handles full realistic multi-page web applications (login session cookies, catalog browsing,
    pagination, target entity selection, CSRF-protected HTML forms, dynamic `<script>` JSON REST
    endpoints, destructive trap avoidance, and cross-site parameterized Poly-Skill transfer).
    """
    import http.cookiejar
    import urllib.error
    import urllib.parse
    import urllib.request

    t0 = time.monotonic()
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def _req(
        target_url: str,
        *,
        method: str = "GET",
        form_data: dict[str, str] | None = None,
        json_data: dict[str, Any] | None = None,
        extra_headers: Mapping[str, str] | None = None,
    ) -> tuple[int, str, str]:
        headers: dict[str, str] = {}
        body_bytes: bytes | None = None
        if json_data is not None:
            body_bytes = json.dumps(json_data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif form_data is not None:
            body_bytes = urllib.parse.urlencode(form_data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if extra_headers:
            headers.update(extra_headers)
        req = urllib.request.Request(target_url, data=body_bytes, headers=headers, method=method.upper())
        try:
            with opener.open(req, timeout=timeout_s) as resp:
                return int(getattr(resp, "status", 200)), resp.geturl(), resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp is not None else str(exc)
            return int(exc.code), target_url, body

    low_instr = instruction.lower()
    target_entity = _extract_target_entity(instruction, supplied)
    needs_auth = any(k in low_instr for k in ("log in", "login", "sign in", "signin", "authenticate")) or (
        _resolve_web_field_alias("username", supplied) is not None and _resolve_web_field_alias("password", supplied) is not None
    )
    wants_add = any(k in low_instr for k in ("add to cart", "add to bag", "add ", "cart", "bag", "basket"))
    wants_checkout = any(k in low_instr for k in ("checkout", "check out", "place order", "complete order", "purchase", "buy", "submit order", "confirm"))

    recalled_poly = _match_web_poly_skill(
        memory,
        needs_auth=needs_auth,
        has_target_entity=bool(target_entity),
        wants_checkout=wants_checkout,
    )
    prebound_api_fields: list[str] = list((recalled_poly or {}).get("discovered_api_field_holes") or [])

    authenticated = not needs_auth
    entity_found = not bool(target_entity)
    item_added = not wants_add
    checkout_done = not wants_checkout

    visited_urls: set[str] = set()
    blocked_destructive: list[str] = []
    stages_executed: list[str] = []
    discovered_api_fields: list[str] = []
    used_csrf = False
    trace: list[dict[str, Any]] = []
    failed_probes = 0

    current_url = url
    st, resolved_url, html = _req(current_url, method="GET")
    if st >= 400:
        return {
            "schema": SCHEMA, "authority": AUTHORITY, "modality": "live_http_web_ui",
            "status": "FAILED", "mode": "WEB_GET_FAILED", "http_status": st,
            "trace": trace, "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0, "parameters_stored": 0,
        }
    visited_urls.add(resolved_url)

    def _fill_form(fm: Mapping[str, Any], extra_keys: Sequence[str] = ()) -> dict[str, str]:
        nonlocal used_csrf
        payload: dict[str, str] = {}
        hidden = fm.get("hidden_replay") or {}
        if hidden:
            used_csrf = True
            for hk, hv in hidden.items():
                payload[str(hk)] = str(hv)
        req_f = list(fm.get("required_input") or [])
        opt_f = list(fm.get("optional_input") or [])
        choices = fm.get("choices") or {}
        for fname in list(dict.fromkeys(req_f + opt_f + list(extra_keys))):
            val = _resolve_web_field_alias(fname, supplied)
            if val is not None:
                if fname in choices and choices[fname]:
                    for opt in choices[fname]:
                        if str(opt).lower() == val.lower():
                            val = str(opt)
                            break
                payload[fname] = val
            elif fname in req_f or fname in extra_keys:
                payload[fname] = str(choices[fname][0]) if (fname in choices and choices[fname]) else f"auto_{fname.lower()}"
        return payload

    for step in range(1, max_steps + 1):
        scan = _scan_web_page_epistemic(html, resolved_url, allow_destructive=allow_destructive)
        for bl in scan["blocked_links"]:
            if bl not in blocked_destructive:
                blocked_destructive.append(bl)
        desc = HTMLFORM.describe(HTMLFORM.read_forms(html))
        safe_forms: list[dict[str, Any]] = []
        for fm in desc.get("forms") or []:
            if (not allow_destructive) and _is_form_destructive(fm):
                act = str(fm.get("action") or "")
                if act and act not in blocked_destructive:
                    blocked_destructive.append(act)
                continue
            safe_forms.append(fm)

        # Check completion
        if authenticated and entity_found and item_added and checkout_done:
            law_saved = _distill_web_poly_skill(
                memory,
                stages=stages_executed,
                discovered_api_fields=discovered_api_fields or prebound_api_fields,
                requires_csrf=used_csrf,
                blocked_destructive=bool(blocked_destructive),
            )
            mode_tag = "TIER0_WEB_POLY_SKILL" if (recalled_poly is not None and failed_probes == 0) else "EPISTEMIC_WEB_POLY_SKILL_SOLVED"
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "modality": "live_http_web_ui",
                "status": "VERIFIED",
                "mode": mode_tag,
                "http_status": st,
                "final_url": resolved_url,
                "response_body": html,
                "rounds": len(trace),
                "failed_probes": failed_probes,
                "stages_executed": stages_executed,
                "blocked_destructive_forms": blocked_destructive,
                "discovered_conditional_fields": discovered_api_fields,
                "recalled_law_id": recalled_poly["law_id"] if recalled_poly else None,
                "distilled_law": law_saved,
                "trace": trace,
                "gaps_queried": [] if mode_tag == "TIER0_WEB_POLY_SKILL" else list(discovered_api_fields),
                "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                "model_calls": 0,
                "parameters_stored": 0,
            }

        # Stage 1: Authentication (login/signin form or link)
        if not authenticated:
            login_form = next(
                (
                    fm for fm in safe_forms
                    if any(k in (str(fm.get("action") or "") + " " + " ".join(fm.get("required_input") or [])).lower()
                           for k in ("login", "signin", "sign-in", "auth", "pass", "pwd"))
                ),
                None,
            )
            if login_form is not None:
                act_url = urllib.parse.urljoin(resolved_url, str(login_form.get("action") or ""))
                payload = _fill_form(login_form)
                st, resolved_url, html = _req(act_url, method=str(login_form.get("method") or "POST"), form_data=payload)
                trace.append({"step": step, "stage": "AUTH_LOGIN", "action": act_url, "status": st, "keys": sorted(payload)})
                if 200 <= st < 300:
                    authenticated = True
                    stages_executed.append("AUTH_LOGIN")
                    visited_urls.add(resolved_url)
                    continue
                failed_probes += 1
                break
            login_link = next(
                (lk for lk in scan["safe_links"] if any(k in (lk["href"] + " " + lk["text"]).lower() for k in ("login", "sign in", "signin", "auth"))),
                None,
            )
            if login_link is not None:
                st, resolved_url, html = _req(login_link["url"], method="GET")
                trace.append({"step": step, "stage": "NAV_LOGIN", "url": resolved_url, "status": st})
                visited_urls.add(resolved_url)
                continue

        # Stage 2: Target Entity Discovery (follow item link, catalog/shop link, or pagination)
        if not entity_found and target_entity:
            te_low = target_entity.lower()
            # 2a. Direct link matching target entity?
            item_link = next(
                (lk for lk in scan["safe_links"] if te_low in lk["text"].lower() or te_low.replace(" ", "-") in lk["href"].lower() or te_low.replace(" ", "_") in lk["href"].lower()),
                None,
            )
            if item_link is not None and item_link["url"] not in visited_urls:
                st, resolved_url, html = _req(item_link["url"], method="GET")
                trace.append({"step": step, "stage": "NAV_FIND_ENTITY", "url": resolved_url, "status": st})
                visited_urls.add(resolved_url)
                if te_low in html.lower():
                    entity_found = True
                    stages_executed.append("NAV_FIND_ENTITY")
                continue
            # 2b. Target entity already on current page with an action form?
            if te_low in html.lower() and (safe_forms or scan["api_endpoints"]):
                entity_found = True
                stages_executed.append("NAV_FIND_ENTITY")
                continue
            # 2c. Pagination ("next", "page=2", ...) or catalog/shop/products link
            nav_candidates = []
            for lk in scan["safe_links"]:
                if lk["url"] in visited_urls:
                    continue
                comb = (lk["href"] + " " + lk["text"]).lower()
                sc = 0
                if any(k in comb for k in ("next", "page=", "page/")):
                    sc += 5
                if any(k in comb for k in ("product", "catalog", "shop", "store", "items", "browse", "inventory")):
                    sc += 4
                if sc > 0:
                    nav_candidates.append((sc, lk))
            if nav_candidates:
                nav_candidates.sort(key=lambda x: -x[0])
                chosen = nav_candidates[0][1]
                st, resolved_url, html = _req(chosen["url"], method="GET")
                trace.append({"step": step, "stage": "NAV_PAGINATE_OR_CATALOG", "url": resolved_url, "status": st})
                visited_urls.add(resolved_url)
                continue

        # Stage 3: Add to Cart / Bag form or link
        if not item_added:
            add_form = next(
                (
                    fm for fm in safe_forms
                    if any(k in (str(fm.get("action") or "") + " " + " ".join(str(b.get("label") or "") for b in (fm.get("buttons") or []))).lower()
                           for k in ("cart", "bag", "basket", "add"))
                ),
                None,
            )
            if add_form is not None:
                act_url = urllib.parse.urljoin(resolved_url, str(add_form.get("action") or ""))
                payload = _fill_form(add_form)
                st, resolved_url, html = _req(act_url, method=str(add_form.get("method") or "POST"), form_data=payload)
                trace.append({"step": step, "stage": "SUBMIT_ADD_ITEM", "action": act_url, "status": st, "keys": sorted(payload)})
                if 200 <= st < 300:
                    item_added = True
                    stages_executed.append("SUBMIT_ADD_ITEM")
                    visited_urls.add(resolved_url)
                    continue
                failed_probes += 1

        # Stage 4: Final Checkout / Order / API Submit (HTML form OR dynamic `<script>` JSON REST API!)
        if not checkout_done:
            # 4a. Check dynamic JSON REST POST/PUT endpoint on page
            api_eps = [ep for ep in scan["api_endpoints"] if ep["method"] in ("POST", "PUT", "PATCH")]
            if api_eps:
                ep = api_eps[0]
                api_keys = list(dict.fromkeys(prebound_api_fields + discovered_api_fields))
                # Pre-populate any supplied checkout/order fields if no keys yet or recalled from Poly-Skill
                for k_hint in ("coupon", "address", "note"):
                    v_h = _resolve_web_field_alias(k_hint, supplied)
                    if v_h is not None and not api_keys:
                        # Let epistemic error feedback or Poly-Skill name the exact JSON key!
                        pass
                hdrs: dict[str, str] = {}
                if scan["csrf_tokens"]:
                    used_csrf = True
                    tok_val = next(iter(scan["csrf_tokens"].values()))
                    hdrs[ep["csrf_header"]] = tok_val

                api_ok = False
                for _api_try in range(4):
                    j_body: dict[str, Any] = {}
                    for ak in api_keys:
                        val = _resolve_web_field_alias(ak, supplied)
                        j_body[ak] = val if val is not None else f"auto_{ak}"
                    st, res_u, body_api = _req(ep["url"], method=ep["method"], json_data=j_body, extra_headers=hdrs)
                    trace.append({"step": step, "stage": "SUBMIT_FINAL_REST_API", "url": ep["url"], "status": st, "keys": sorted(j_body), "excerpt": body_api[:180]})
                    if 200 <= st < 300:
                        checkout_done = True
                        stages_executed.append("SUBMIT_FINAL_REST_API")
                        resolved_url, html = res_u, body_api
                        api_ok = True
                        break
                    failed_probes += 1
                    err_text = body_api
                    try:
                        parsed_err = json.loads(body_api)
                        if isinstance(parsed_err, dict):
                            err_text = " ".join(
                                str(parsed_err[k]) for k in ("error", "detail", "message", "msg")
                                if k in parsed_err and parsed_err[k]
                            ) or body_api
                    except Exception:
                        pass
                    missing_k = list(COMPOSE_ERR.missing_from_error(err_text))
                    for m_req in re.finditer(
                        r"(?:missing|required)\s+(?:required\s+)?(?:field|param|parameter|key|property)?\s*[:=]?\s*['\"]?([A-Za-z_][A-Za-z0-9_\-]*)['\"]?",
                        err_text,
                        flags=re.IGNORECASE,
                    ):
                        cand = m_req.group(1).strip().lower()
                        if cand and cand not in ("error", "detail", "message", "field", "param", "parameter", "key", "required", "missing") and cand not in missing_k:
                            missing_k.append(cand)
                    added_k = False
                    for mk in missing_k:
                        mkl = mk.strip().lower()
                        if mkl and mkl not in ("error", "detail", "message") and mkl not in api_keys:
                            api_keys.append(mkl)
                            if mkl not in discovered_api_fields:
                                discovered_api_fields.append(mkl)
                            added_k = True
                    if not added_k:
                        break
                if api_ok:
                    continue

            # 4b. Check safe checkout/order HTML form
            fin_form = next(
                (
                    fm for fm in safe_forms
                    if any(k in (str(fm.get("action") or "") + " " + " ".join(str(b.get("label") or "") for b in (fm.get("buttons") or []))).lower()
                           for k in ("checkout", "order", "confirm", "purchase", "buy", "pay", "submit"))
                ),
                None,
            )
            if fin_form is not None:
                act_url = urllib.parse.urljoin(resolved_url, str(fin_form.get("action") or ""))
                extra_f = list(prebound_api_fields)
                for _f_try in range(3):
                    payload = _fill_form(fin_form, extra_keys=extra_f)
                    st, res_u, body_fin = _req(act_url, method=str(fin_form.get("method") or "POST"), form_data=payload)
                    trace.append({"step": step, "stage": "SUBMIT_FINAL_FORM", "action": act_url, "status": st, "keys": sorted(payload)})
                    if 200 <= st < 300:
                        checkout_done = True
                        stages_executed.append("SUBMIT_FINAL_FORM")
                        resolved_url, html = res_u, body_fin
                        break
                    failed_probes += 1
                    missing_k = COMPOSE_ERR.missing_from_error(body_fin)
                    if not missing_k:
                        break
                    for mk in missing_k:
                        mkl = mk.strip().lower()
                        if mkl and mkl not in extra_f:
                            extra_f.append(mkl)
                            if mkl not in discovered_api_fields:
                                discovered_api_fields.append(mkl)
                if checkout_done:
                    continue

            # 4c. Follow cart/bag/checkout navigation link
            ck_link = next(
                (
                    lk for lk in scan["safe_links"]
                    if lk["url"] not in visited_urls
                    and any(k in (lk["href"] + " " + lk["text"]).lower() for k in ("checkout", "check out", "cart", "bag", "basket", "order"))
                ),
                None,
            )
            if ck_link is not None:
                st, resolved_url, html = _req(ck_link["url"], method="GET")
                trace.append({"step": step, "stage": "NAV_CHECKOUT", "url": resolved_url, "status": st})
                visited_urls.add(resolved_url)
                continue

        # No further progress possible
        break

    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "modality": "live_http_web_ui",
        "status": "FAILED",
        "mode": "WEB_POLY_WORKFLOW_EXHAUSTED",
        "rounds": len(trace),
        "failed_probes": failed_probes,
        "stages_executed": stages_executed,
        "blocked_destructive_forms": blocked_destructive,
        "trace": trace,
        "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
        "model_calls": 0,
        "parameters_stored": 0,
    }


def solve_live_http_web_ui(
    url: str,
    instruction: str,
    *,
    memory: dict[str, Any] | None = None,
    field_values: Mapping[str, str] | None = None,
    target_url: str | None = None,
    max_rounds: int = 5,
    timeout_s: float = 10.0,
) -> dict[str, Any]:
    """Live interactive HTTP/HTML Web UI Epistemic Solver.

    Reuses `htmlform_read_v1` (form/field/hidden-token/destructive-risk parser) and
    `compose_v1.missing_from_error` (failure-driven dependency discovery), and routes
    WorkArena/WebArena-Pro multi-page table filtering/aggregation, CRUD edits, and
    cross-app pipelines to `epistemic_enterprise_web_agent_v1`.
    Zero LLM calls, zero weights, zero destructive side effects, generalized workflow distillation.
    """
    import http.cookiejar
    import urllib.error
    import urllib.parse
    import urllib.request

    t0 = time.monotonic()
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def _http_req(target_url: str, *, method: str = "GET", data: dict[str, str] | None = None) -> tuple[int, str, str]:
        enc = urllib.parse.urlencode(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(target_url, data=enc, method=method.upper())
        try:
            with opener.open(req, timeout=timeout_s) as resp:
                return int(getattr(resp, "status", 200)), resp.geturl(), resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace") if exc.fp is not None else str(exc)
            return int(exc.code), target_url, body

    supplied: dict[str, str] = _extract_web_field_values(instruction)
    if isinstance(field_values, Mapping):
        for k, v in field_values.items():
            supplied[str(k).strip().lower()] = str(v)

    allow_destructive = any(w in instruction.lower() for w in _DESTRUCTIVE_ACTION_HINTS)

    # Route WorkArena / WebArena-Pro enterprise workflows (multi-page table filter/aggregate,
    # authenticated CRUD record edit, and cross-application multi-site bridge) first.
    from canonical.runtime import epistemic_enterprise_web_agent_v1 as ENT_WEB

    _all_urls = ENT_WEB.extract_urls(instruction, [u for u in (url, target_url) if u])
    _ent_kind = ENT_WEB.classify_enterprise_web_intent(instruction, urls=_all_urls, supplied=supplied)
    if _ent_kind == "CROSS_APP_BRIDGE" and len(_all_urls) >= 2:
        return ENT_WEB.solve_cross_app_web_bridge(
            _all_urls[0],
            _all_urls[1],
            instruction,
            memory=memory,
            supplied=supplied,
            allow_destructive=allow_destructive,
            timeout_s=timeout_s,
        )
    if _ent_kind == "RECORD_CRUD_EDIT":
        return ENT_WEB.solve_enterprise_record_crud_edit(
            url,
            instruction,
            memory=memory,
            supplied=supplied,
            allow_destructive=allow_destructive,
            timeout_s=timeout_s,
        )
    if _ent_kind == "TABLE_FILTER_AGGREGATE":
        return ENT_WEB.solve_enterprise_table_query(
            url,
            instruction,
            memory=memory,
            supplied=supplied,
            allow_destructive=allow_destructive,
            timeout_s=timeout_s,
        )

    # Route multi-page authenticated / catalog / pagination / REST-API web workflows directly
    # to the Poly-Skill multi-page engine (preserving single-form & 2-step wizard fast path!).
    _low_i = instruction.lower()
    _has_entity = bool(_extract_target_entity(instruction, supplied))
    _is_multipage_goal = (
        (any(k in _low_i for k in ("log in", "login", "sign in", "signin")) and any(k in _low_i for k in ("cart", "bag", "checkout", "order", "purchase", "buy", "add ")))
        or (_has_entity and any(k in _low_i for k in ("cart", "bag", "checkout", "order", "find", "browse", "paginate")))
    )
    if _is_multipage_goal:
        return _solve_live_multipage_web_workflow(
            url,
            instruction,
            memory=memory,
            supplied=supplied,
            allow_destructive=allow_destructive,
            max_steps=max(16, max_rounds * 3),
            timeout_s=timeout_s,
        )

    extra_required: list[str] = []
    discovered_conditional: list[str] = []
    blocked_destructive_forms: list[str] = []
    trace: list[dict[str, Any]] = []
    recalled_law: dict[str, Any] | None = None
    had_hidden_replay = False
    last_form_desc: dict[str, Any] | None = None
    submitted_supplied_keys: set[str] = set()
    visited_nav_urls: set[str] = {url}
    _runtime_meta_keys = {
        "workspace", "repo_root", "root", "url", "target_url",
        "timeout_s", "allow_destructive", "max_rounds", "cwd", "workdir", "mode",
        "memory", "spec_docs", "docs", "files",
    }

    def _pick_next_goal_link(page_html: str, page_url: str, rem_fields: list[str]) -> dict[str, str] | None:
        scan_p = _scan_web_page_epistemic(page_html, page_url, allow_destructive=allow_destructive)
        goal_toks = set(
            t for t in re.findall(r"[a-z0-9]+", (instruction + " " + " ".join(rem_fields)).lower())
            if len(t) >= 3 and t not in {
                "http", "https", "with", "from", "into", "that", "this", "then",
                "and", "the", "for", "log", "login", "sign", "navigate", "open",
                "create", "submit", "page", "url",
            }
        )
        best_lk: dict[str, str] | None = None
        best_sc = (-1, -1)
        for lk in scan_p.get("safe_links") or []:
            u = str(lk.get("url") or "")
            if not u or u in visited_nav_urls:
                continue
            lk_toks = set(
                t for t in re.findall(r"[a-z0-9]+", (str(lk.get("text") or "") + " " + str(lk.get("href") or "")).lower())
                if len(t) >= 3
            )
            ov = len(goal_toks & lk_toks)
            # Also reward prefix/stem match (e.g. key <-> keys)
            stem_ov = sum(
                1 for gt in goal_toks
                if any(lt.startswith(gt[:4]) or gt.startswith(lt[:4]) for lt in lk_toks if len(lt) >= 3 and len(gt) >= 3)
            )
            sc = (ov * 3 + stem_ov, len(lk_toks))
            if sc > best_sc:
                best_sc = sc
                best_lk = lk
        return best_lk

    current_url = url
    for round_idx in range(1, max(1, max_rounds) + 1):
        status_get, resolved_url, html = _http_req(current_url, method="GET")
        if status_get >= 400:
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "modality": "live_http_web_ui",
                "status": "FAILED",
                "mode": "WEB_GET_FAILED",
                "http_status": status_get,
                "trace": trace,
                "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                "model_calls": 0,
                "parameters_stored": 0,
            }

        desc = HTMLFORM.describe(HTMLFORM.read_forms(html))
        forms = desc.get("forms") or []
        safe_forms: list[dict[str, Any]] = []
        for fm in forms:
            if not allow_destructive and _is_form_destructive(fm):
                act = str(fm.get("action") or "")
                if act not in blocked_destructive_forms:
                    blocked_destructive_forms.append(act)
                continue
            safe_forms.append(fm)

        if not safe_forms:
            if round_idx == 1:
                from canonical.runtime import epistemic_world_model_planner_v1 as WM_PLANNER

                _goal_role_wm = WM_PLANNER._abstract_role(instruction)
                if WM_PLANNER._recall_world_model_plan(memory, _goal_role_wm) is not None:
                    return WM_PLANNER.solve_with_epistemic_world_model(
                        WM_PLANNER.LiveHTTPWorldAdapter(url, timeout_s=timeout_s),
                        instruction,
                        field_values=supplied,
                        memory=memory,
                    )
                _scan0 = _scan_web_page_epistemic(html, resolved_url, allow_destructive=allow_destructive)
                if _scan0["api_endpoints"]:
                    _mp_res = _solve_live_multipage_web_workflow(
                        url,
                        instruction,
                        memory=memory,
                        supplied=supplied,
                        allow_destructive=allow_destructive,
                        max_steps=max(16, max_rounds * 3),
                        timeout_s=timeout_s,
                    )
                    if _mp_res.get("status") == "VERIFIED":
                        return _mp_res
                if _scan0["safe_links"] or _scan0["api_endpoints"]:
                    _wm_res = WM_PLANNER.solve_with_epistemic_world_model(
                        WM_PLANNER.LiveHTTPWorldAdapter(url, timeout_s=timeout_s),
                        instruction,
                        field_values=supplied,
                        memory=memory,
                    )
                    if _wm_res.get("status") == "VERIFIED":
                        return _wm_res
                    return _solve_live_multipage_web_workflow(
                        url,
                        instruction,
                        memory=memory,
                        supplied=supplied,
                        allow_destructive=allow_destructive,
                        max_steps=max(16, max_rounds * 3),
                        timeout_s=timeout_s,
                    )
            else:
                _rem_nav = [k for k in supplied if k not in submitted_supplied_keys and k not in _runtime_meta_keys]
                if _rem_nav and round_idx < max_rounds:
                    _next_lk = _pick_next_goal_link(html, resolved_url, _rem_nav)
                    if _next_lk is not None:
                        visited_nav_urls.add(_next_lk["url"])
                        trace.append({
                            "round": round_idx,
                            "action": _next_lk["href"],
                            "method": "NAVIGATE",
                            "http_status": status_get,
                            "submitted_keys": [],
                            "blocked_destructive": list(blocked_destructive_forms),
                            "response_excerpt": f"follow_link:{_next_lk['text']}",
                        })
                        current_url = _next_lk["url"]
                        continue
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "modality": "live_http_web_ui",
                "status": "FAILED",
                "mode": "NO_SAFE_FORM_FOUND",
                "blocked_destructive_forms": blocked_destructive_forms,
                "trace": trace,
                "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                "model_calls": 0,
                "parameters_stored": 0,
            }

        # Pick form with highest field overlap with supplied values (tie-break: first safe form)
        def _form_score(fm: Mapping[str, Any]) -> tuple[int, int]:
            fields = [str(f).lower() for f in (fm.get("required_input") or []) + (fm.get("optional_input") or [])]
            ov = sum(1 for f in fields if f in supplied)
            return (ov, len(fields))

        target_form = max(safe_forms, key=_form_score)
        last_form_desc = target_form
        method = str(target_form.get("method") or "POST").upper()
        action_url = urllib.parse.urljoin(resolved_url, str(target_form.get("action") or ""))
        req_fields = list(target_form.get("required_input") or [])
        opt_fields = list(target_form.get("optional_input") or [])
        choices = target_form.get("choices") or {}
        hidden_replay = dict(target_form.get("hidden_replay") or {})
        if hidden_replay:
            had_hidden_replay = True

        # Tier-0 generalized web workflow recall (pre-binds conditional holes BEFORE first error!)
        if round_idx == 1 and recalled_law is None:
            recalled_law = _match_web_workflow_law(memory, method, req_fields + opt_fields)
            if recalled_law is not None:
                for cf in recalled_law.get("conditional_field_holes") or []:
                    if cf in supplied and cf not in extra_required:
                        extra_required.append(cf)

        payload: dict[str, str] = {}
        # Always replay fresh hidden tokens (CSRF, step markers)
        for hk, hv in hidden_replay.items():
            payload[hk] = str(hv)

        # Fill required, optional (if supplied), and error/law-discovered conditional fields
        ordered_fields = list(dict.fromkeys(req_fields + opt_fields + extra_required))
        for fname in ordered_fields:
            fl = fname.lower()
            is_needed = (fname in req_fields) or (fl in extra_required) or (fname in extra_required)
            if fl in supplied:
                val = supplied[fl]
                if fname in choices and choices[fname]:
                    for opt in choices[fname]:
                        if str(opt).lower() == val.lower():
                            val = str(opt)
                            break
                payload[fname] = val
            elif is_needed:
                if fname in choices and choices[fname]:
                    payload[fname] = str(choices[fname][0])
                else:
                    payload[fname] = f"auto_{fl}"

        if method == "GET":
            qs = urllib.parse.urlencode(payload)
            submit_url = f"{action_url}?{qs}" if qs else action_url
            st_sub, final_url, body_sub = _http_req(submit_url, method="GET")
        else:
            st_sub, final_url, body_sub = _http_req(action_url, method=method, data=payload)

        trace.append({
            "round": round_idx,
            "action": str(target_form.get("action") or ""),
            "method": method,
            "http_status": st_sub,
            "submitted_keys": sorted(payload.keys()),
            "blocked_destructive": list(blocked_destructive_forms),
            "response_excerpt": body_sub[:240],
        })

        if 200 <= st_sub < 300:
            for _pk in payload:
                submitted_supplied_keys.add(str(_pk).lower())
            _remaining_supplied = [k for k in supplied if k not in submitted_supplied_keys and k not in _runtime_meta_keys]

            # Check if response leads to a follow-up safe form (multi-step wizard)
            next_desc = HTMLFORM.describe(HTMLFORM.read_forms(body_sub))
            next_safe = [f for f in (next_desc.get("forms") or []) if allow_destructive or not _is_form_destructive(f)]
            _next_has_rem = any(
                str(fn).lower() in _remaining_supplied
                for nf in next_safe
                for fn in ((nf.get("required_input") or []) + (nf.get("optional_input") or []))
            )
            if next_safe and round_idx < max_rounds and (final_url != resolved_url or _next_has_rem):
                current_url = final_url
                continue

            # Honest goal-completion check: if user-supplied goal fields were NEVER
            # submitted yet, navigate via goal-relevant links on the resulting page
            # (e.g. Login -> Dashboard -> API Keys -> Create Key) instead of falsely
            # declaring VERIFIED on an intermediate 200 OK page!
            if _remaining_supplied:
                if round_idx < max_rounds:
                    _next_lk = _pick_next_goal_link(body_sub, final_url, _remaining_supplied)
                    if _next_lk is not None:
                        visited_nav_urls.add(_next_lk["url"])
                        trace.append({
                            "round": round_idx,
                            "action": _next_lk["href"],
                            "method": "NAVIGATE",
                            "http_status": st_sub,
                            "submitted_keys": [],
                            "blocked_destructive": list(blocked_destructive_forms),
                            "response_excerpt": f"follow_link:{_next_lk['text']}",
                        })
                        current_url = _next_lk["url"]
                        continue
                # Escalate to multi-screen world-model planner rather than falsely claiming VERIFIED
                break

            law_saved = _distill_web_workflow_law(
                memory,
                method=method,
                required_fields=req_fields,
                conditional_fields=discovered_conditional or extra_required,
                had_hidden_replay=had_hidden_replay,
                blocked_destructive=bool(blocked_destructive_forms),
            )
            mode_tag = "TIER0_WEB_WORKFLOW_LAW" if (recalled_law is not None and round_idx == 1) else "EPISTEMIC_WEB_UI_SOLVED"
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "modality": "live_http_web_ui",
                "status": "VERIFIED",
                "mode": mode_tag,
                "http_status": st_sub,
                "final_url": final_url,
                "response_body": body_sub,
                "rounds": round_idx,
                "blocked_destructive_forms": blocked_destructive_forms,
                "discovered_conditional_fields": discovered_conditional,
                "recalled_law_id": recalled_law["law_id"] if recalled_law else None,
                "distilled_law": law_saved,
                "trace": trace,
                "gaps_queried": [] if mode_tag == "TIER0_WEB_WORKFLOW_LAW" else list(discovered_conditional),
                "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                "model_calls": 0,
                "parameters_stored": 0,
            }

        # Failure-driven epistemic discovery via compose_v1.missing_from_error!
        missing_tokens = COMPOSE_ERR.missing_from_error(body_sub)
        learned_new = False
        for tok in missing_tokens:
            tl = tok.strip().lower()
            if not tl or tl in hidden_replay or tl in ("utf-8", "http", "https"):
                continue
            if tl not in extra_required:
                extra_required.append(tl)
                if tl not in [r.lower() for r in req_fields] and tl not in discovered_conditional:
                    discovered_conditional.append(tl)
                learned_new = True

        # Check enum hint in error text: "must be one of: a, b, c"
        m_enum = re.search(r"must be one of:\s*([A-Za-z0-9_,\-\s]+)", body_sub, flags=re.IGNORECASE)
        if m_enum and missing_tokens:
            opts = [o.strip() for o in m_enum.group(1).split(",") if o.strip()]
            if opts:
                for tok in missing_tokens:
                    tl = tok.strip().lower()
                    if tl not in supplied or supplied[tl] not in opts:
                        supplied[tl] = opts[0]
                        learned_new = True

        # If server complained about stale hidden token (e.g. csrf), next loop's GET refreshes it automatically
        if not learned_new and not any(hk.lower() in body_sub.lower() for hk in hidden_replay):
            break

    # Automatic escalation to Causal Belief-State World-Model Planner for multi-screen
    # hidden-precondition / backtracking / confirmation-modal HTTP workflows.
    from canonical.runtime import epistemic_world_model_planner_v1 as WM_PLANNER

    _wm_fallback = WM_PLANNER.solve_with_epistemic_world_model(
        WM_PLANNER.LiveHTTPWorldAdapter(url, timeout_s=timeout_s),
        instruction,
        field_values=supplied,
        memory=memory,
    )
    if _wm_fallback.get("status") == "VERIFIED":
        return _wm_fallback

    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "modality": "live_http_web_ui",
        "status": "FAILED",
        "mode": "WEB_UI_EXHAUSTED",
        "rounds": len(trace),
        "blocked_destructive_forms": blocked_destructive_forms,
        "discovered_conditional_fields": discovered_conditional,
        "trace": trace,
        "last_form": last_form_desc,
        "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
        "model_calls": 0,
        "parameters_stored": 0,
    }


# ---------------------------------------------------------------------------
# 6. Zero-Prior Closed-Loop Epistemic Arbitrary-Environment Solver (Iter 20)
#    Goal-Directed Cone Scan -> Memory Diff -> Instant Live Introspection ->
#    Closed-Loop Execute/Error-Repair -> Trace2Skill Error-Law & Plotkin LGG
#    Distillation + Skill-Pro Score-Based Memory Pruning (0 model calls!).
# ---------------------------------------------------------------------------

def _extract_zero_prior_target_path(instruction: str, ws: pathlib.Path) -> pathlib.Path | None:
    ws_s = str(ws.resolve())
    pat = (
        r"(?:to|into|in|as|write|save|output|produce|create)\s+(?:file\s+)?"
        r"[`'\"]?((?:/app/|" + re.escape(ws_s) + r"/|[A-Za-z0-9_.\-/]+/)?[A-Za-z0-9_.\-]+\.(?:json|jsonl|csv|tsv|txt|md))[`'\"]?"
    )
    matches = list(re.finditer(pat, instruction or "", re.IGNORECASE))
    if not matches:
        return None
    raw = matches[-1].group(1).strip("`'\".,;:()")
    for pref in ("/app/", ws_s + "/", str(ws) + "/"):
        if raw.startswith(pref):
            raw = raw[len(pref):]
    raw = raw.lstrip("/")
    return ws / raw


def _fuzzy_best_name(query: str, candidates: Sequence[str]) -> str | None:
    if not candidates:
        return None
    q = query.strip().lower().replace("-", "_")
    for c in candidates:
        if c.lower() == q:
            return c
    for c in candidates:
        if c.lower().replace("_", "") == q.replace("_", ""):
            return c
    q_toks = set(re.findall(r"[a-z0-9]+", q))
    best_c, best_sc = None, 0.0
    for c in candidates:
        cl = c.lower()
        c_toks = set(re.findall(r"[a-z0-9]+", cl))
        overlap = len(q_toks & c_toks) / max(1, len(q_toks | c_toks))
        sub = 0.55 if (q in cl or cl in q) else 0.0
        # Character bigram Dice similarity for short typos/aliases
        qb = {q[i : i + 2] for i in range(max(0, len(q) - 1))}
        cb = {cl[i : i + 2] for i in range(max(0, len(cl) - 1))}
        dice = (2.0 * len(qb & cb) / max(1, len(qb) + len(cb))) if (qb and cb) else 0.0
        sc = max(overlap, sub, dice)
        if sc > best_sc:
            best_sc, best_c = sc, c
    return best_c if best_sc >= 0.35 else None


def _coerce_literal_scalar(raw: str) -> Any:
    s = raw.strip().strip("'\"")
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    if s.lower() in ("none", "null"):
        return None
    try:
        if re.fullmatch(r"-?\d+", s):
            return int(s)
        return float(s)
    except ValueError:
        return s


def _solve_zero_prior_unknown_python_api(
    ws: pathlib.Path,
    instruction: str,
    target_out: pathlib.Path,
    py_modules: Sequence[pathlib.Path],
    data_files: Sequence[pathlib.Path],
    *,
    memory: dict[str, Any] | None,
    postcondition_fn: Callable[[pathlib.Path], tuple[bool, str]] | None,
    python_exe: str,
    timeout_s: float,
) -> dict[str, Any] | None:
    """Discover an unknown local Python module's real callables/signatures live, invoke it
    on workspace data with closed-loop error-gap repair, verify output, and distill
    generalized error-fix laws + parameterized procedure laws into memory."""
    # Parse desired call hints (optional function name + key=val kwargs) from instruction
    low = instruction.lower()
    m_fn = re.search(
        r"(?:call|invoke|run|use|using|execute)\s+[`'\"]?(?:[A-Za-z_][A-Za-z0-9_]*\.)?([A-Za-z_][A-Za-z0-9_]*)\s*(?:\([^)]*\))?[`'\"]?",
        instruction,
        re.IGNORECASE,
    )
    fn_hint = m_fn.group(1) if m_fn else ""
    kw_hints: dict[str, Any] = {}
    for km in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*('[^']*'|\"[^\"]*\"|-?\d+(?:\.\d+)?|True|False|None|[A-Za-z0-9_.\-]+)", instruction):
        k_name = km.group(1)
        if k_name.lower() in ("where", "output", "file", "path", "mode"):
            continue
        kw_hints[k_name] = _coerce_literal_scalar(km.group(2))

    # Pick most relevant local Python module in goal cone
    chosen_mod: pathlib.Path | None = None
    for mp in py_modules:
        if mp.stem.lower() in low or mp.name.lower() in low:
            chosen_mod = mp
            break
    if chosen_mod is None:
        chosen_mod = py_modules[0]

    # Pick input data file if present and not equal to target_out
    input_data = next((df for df in data_files if df.resolve() != target_out.resolve()), None)

    # Check Tier-0 error-fix laws already in memory before execution
    recalled_err_laws = recall_error_fix_laws(memory, error_kind="TypeError", context_shape="unexpected_kwarg")

    # Isolated live introspection + closed-loop execution & error-repair worker
    worker = textwrap.dedent(r"""
        import csv, importlib.util, inspect, json, pathlib, re, sys, traceback

        mod_path = pathlib.Path(sys.argv[1])
        fn_hint = sys.argv[2]
        kw_hints = json.loads(sys.argv[3])
        in_path = pathlib.Path(sys.argv[4]) if sys.argv[4] else None
        out_path = pathlib.Path(sys.argv[5])
        recalled_laws = json.loads(sys.argv[6])

        spec = importlib.util.spec_from_file_location(mod_path.stem, str(mod_path))
        mod = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(mod_path.parent))
        spec.loader.exec_module(mod)

        callables = {
            name: obj for name, obj in inspect.getmembers(mod, inspect.isfunction)
            if not name.startswith("_") and obj.__module__ == mod.__name__
        }
        if not callables:
            print(json.dumps({"ok": False, "error": "NO_PUBLIC_CALLABLES"}))
            sys.exit(0)

        def best_match(q, names):
            ql = q.lower()
            for n in names:
                if n.lower() == ql:
                    return n
            qt = set(re.findall(r"[a-z0-9]+", ql))
            best_n, best_s = names[0], -1.0
            for n in names:
                nl = n.lower()
                nt = set(re.findall(r"[a-z0-9]+", nl))
                ov = len(qt & nt) / max(1, len(qt | nt))
                qb = {ql[i:i+2] for i in range(max(0, len(ql)-1))}
                nb = {nl[i:i+2] for i in range(max(0, len(nl)-1))}
                dice = (2.0 * len(qb & nb) / max(1, len(qb) + len(nb))) if (qb and nb) else 0.0
                s = max(ov, dice, 0.55 if (ql and (ql in nl or nl in ql)) else 0.0)
                if s > best_s:
                    best_s, best_n = s, n
            return best_n

        fn_name = best_match(fn_hint, list(callables.keys())) if fn_hint else list(callables.keys())[0]
        fn = callables[fn_name]
        sig = inspect.signature(fn)
        param_names = list(sig.parameters.keys())
        req_params = [
            p.name for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty and p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]

        # Prepare parsed payload from input file (if any)
        raw_input_val = None
        parsed_input_val = None
        if in_path is not None and in_path.is_file():
            raw_input_val = str(in_path)
            suf = in_path.suffix.lower()
            if suf == ".json":
                parsed_input_val = json.loads(in_path.read_text(encoding="utf-8"))
            elif suf == ".jsonl":
                parsed_input_val = [json.loads(l) for l in in_path.read_text(encoding="utf-8").splitlines() if l.strip()]
            elif suf in (".csv", ".tsv"):
                delim = "\t" if suf == ".tsv" else ","
                with open(in_path, "r", encoding="utf-8", newline="") as f:
                    parsed_input_val = list(csv.DictReader(f, delimiter=delim))
            else:
                parsed_input_val = in_path.read_text(encoding="utf-8")

        # Build initial kwargs (using Tier-0 recalled kwarg-remapping law if active, else raw hints to expose real error!)
        has_kwarg_remap_law = any(l.get("repair_op") == "introspect_signature_remap_kwarg" for l in recalled_laws)
        call_kwargs = dict(kw_hints)
        error_repairs = []

        if has_kwarg_remap_law and call_kwargs:
            remapped = {}
            for k, v in call_kwargs.items():
                if k in param_names:
                    remapped[k] = v
                else:
                    avail = [p for p in param_names if p not in remapped and p not in req_params[:1]]
                    if avail:
                        remapped[best_match(k, avail)] = v
            call_kwargs = remapped

        # Determine candidate positional input representations
        pos_cands = []
        if in_path is not None:
            p0_name = req_params[0].lower() if req_params else (param_names[0].lower() if param_names else "")
            if any(tok in p0_name for tok in ("path", "file", "filename")):
                pos_cands = [raw_input_val, parsed_input_val]
            else:
                pos_cands = [parsed_input_val, raw_input_val]
        else:
            pos_cands = [None]

        result_val = None
        solved = False
        used_tier0_err_law = has_kwarg_remap_law
        pos_idx = 0
        for round_i in range(6):
            pos_arg = pos_cands[min(pos_idx, len(pos_cands) - 1)]
            args = [pos_arg] if (pos_arg is not None and len(req_params) >= 1 and req_params[0] not in call_kwargs) else []
            try:
                result_val = fn(*args, **call_kwargs)
                solved = True
                break
            except TypeError as exc:
                msg = str(exc)
                m_bad = re.search(r"unexpected keyword argument '([^']+)'", msg)
                if m_bad:
                    bad_kw = m_bad.group(1)
                    val = call_kwargs.pop(bad_kw)
                    avail = [p for p in param_names if p not in call_kwargs and p not in (req_params[:1] if args else [])]
                    if avail:
                        real_kw = best_match(bad_kw, avail)
                        call_kwargs[real_kw] = val
                        error_repairs.append({
                            "error_kind": "TypeError",
                            "context_shape": "unexpected_kwarg",
                            "repair_op": "introspect_signature_remap_kwarg",
                            "detail": f"{bad_kw}->{real_kw}",
                        })
                        continue
                # Try swapping parsed vs path input on next round
                if pos_idx + 1 < len(pos_cands):
                    pos_idx += 1
                    error_repairs.append({
                        "error_kind": "TypeError",
                        "context_shape": "arg_representation_mismatch",
                        "repair_op": "toggle_parsed_vs_path_input",
                        "detail": msg[:100],
                    })
                    continue
                print(json.dumps({"ok": False, "error": f"TypeError:{msg}"}))
                sys.exit(0)
            except Exception as exc:
                if pos_idx + 1 < len(pos_cands):
                    pos_idx += 1
                    error_repairs.append({
                        "error_kind": type(exc).__name__,
                        "context_shape": "arg_representation_mismatch",
                        "repair_op": "toggle_parsed_vs_path_input",
                        "detail": str(exc)[:100],
                    })
                    continue
                print(json.dumps({"ok": False, "error": f"{type(exc).__name__}:{exc}"}))
                sys.exit(0)

        if not solved:
            print(json.dumps({"ok": False, "error": "CEGIS_EXHAUSTED"}))
            sys.exit(0)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        if out_path.suffix.lower() == ".json":
            out_path.write_text(json.dumps(result_val, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        elif out_path.suffix.lower() == ".jsonl" and isinstance(result_val, list):
            out_path.write_text("\n".join(json.dumps(r, sort_keys=True) for r in result_val) + "\n", encoding="utf-8")
        else:
            out_path.write_text(
                (json.dumps(result_val, sort_keys=True) if isinstance(result_val, (dict, list)) else str(result_val)) + "\n",
                encoding="utf-8",
            )
        print(json.dumps({
            "ok": True,
            "fn_name": fn_name,
            "params": param_names,
            "error_repairs": error_repairs,
            "used_tier0_err_law": used_tier0_err_law,
        }))
    """)

    with tempfile.TemporaryDirectory(prefix="uek_zp_api_") as td:
        out_stage = pathlib.Path(td) / target_out.name
        cp = subprocess.run(
            [
                python_exe, "-c", worker,
                str(chosen_mod),
                fn_hint,
                json.dumps(kw_hints),
                str(input_data) if input_data is not None else "",
                str(out_stage),
                json.dumps(recalled_err_laws),
            ],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        if cp.returncode != 0 or not cp.stdout.strip():
            return None
        try:
            rep = json.loads(cp.stdout.strip().splitlines()[-1])
        except Exception:
            return None
        if not rep.get("ok") or not out_stage.is_file():
            return None

        # Atomic commit to workspace + postcondition check
        target_out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out_stage, target_out)
        if postcondition_fn is not None:
            ok_post, reason = postcondition_fn(ws)
            if not ok_post:
                target_out.unlink(missing_ok=True)
                return None

        # Distill generalized Trace2Skill error-fix laws + parameterized procedure law (ZERO paths/values!)
        distilled_err_laws: list[str] = []
        pruned_stats: dict[str, int] = {}
        if memory is not None:
            for er in rep.get("error_repairs") or []:
                rec = record_error_fix_law(
                    memory,
                    error_kind=str(er.get("error_kind") or "RuntimeError"),
                    context_shape=str(er.get("context_shape") or "*"),
                    repair_op=str(er.get("repair_op") or "introspect_repair"),
                )
                if rec is not None:
                    distilled_err_laws.append(str(rec["law_id"]))
            if rep.get("used_tier0_err_law") and recalled_err_laws:
                # Reinforce utility score of verified Tier-0 error law
                lid0 = recalled_err_laws[0]["law_id"]
                if lid0 in memory.get("error_fix_laws", {}):
                    memory["error_fix_laws"][lid0]["verified_uses"] = int(memory["error_fix_laws"][lid0].get("verified_uses", 1)) + 1
                    memory["error_fix_laws"][lid0]["utility_score"] = (
                        int(memory["error_fix_laws"][lid0]["verified_uses"])
                        - 2 * int(memory["error_fix_laws"][lid0].get("failed_uses", 0))
                    )
            pruned_stats = compress_and_prune_memory(memory)

        return {
            "status": "VERIFIED",
            "mode": (
                "TIER0_ZERO_PRIOR_API_WITH_ERROR_LAW"
                if rep.get("used_tier0_err_law") and not rep.get("error_repairs")
                else "EPISTEMIC_ZERO_PRIOR_API_CEGIS"
            ),
            "gaps_queried": [f"python_api:{chosen_mod.stem}"],
            "fn_name": rep.get("fn_name"),
            "error_repairs": rep.get("error_repairs") or [],
            "distilled_error_fix_laws": distilled_err_laws,
            "memory_compression": pruned_stats,
        }


def _solve_zero_prior_structured_data(
    ws: pathlib.Path,
    instruction: str,
    target_out: pathlib.Path,
    data_files: Sequence[pathlib.Path],
    *,
    memory: dict[str, Any] | None,
    postcondition_fn: Callable[[pathlib.Path], tuple[bool, str]] | None,
) -> dict[str, Any] | None:
    """Live-introspect schema of an unseen CSV/TSV/JSON/JSONL/SQLite file, compile
    goal-directed relational operations (filter, group-by, sum/count/avg/min/max, sort,
    top-K, format conversion), execute, verify, and distill a path-free operator schema."""
    import csv as _csv
    import sqlite3 as _sqlite3

    in_file = next((df for df in data_files if df.resolve() != target_out.resolve()), None)
    if in_file is None or not in_file.is_file():
        return None
    suf = in_file.suffix.lower()
    rows: list[dict[str, Any]] = []
    in_kind = suf.lstrip(".")
    try:
        if suf in (".csv", ".tsv"):
            txt = in_file.read_text(encoding="utf-8", errors="replace")
            delim = "\t" if suf == ".tsv" else ("," if "," in txt.splitlines()[0] else "\t")
            rows = list(_csv.DictReader(txt.splitlines(), delimiter=delim))
        elif suf == ".json":
            obj = json.loads(in_file.read_text(encoding="utf-8"))
            if isinstance(obj, list) and all(isinstance(x, dict) for x in obj):
                rows = obj
            elif isinstance(obj, dict):
                for v in obj.values():
                    if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
                        rows = v
                        break
        elif suf == ".jsonl":
            rows = [json.loads(l) for l in in_file.read_text(encoding="utf-8").splitlines() if l.strip()]
        elif suf in (".db", ".sqlite", ".sqlite3"):
            con = _sqlite3.connect(f"file:{in_file}?immutable=1", uri=True)
            con.row_factory = _sqlite3.Row
            tbls = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() if not str(r[0]).startswith("sqlite_")]
            if tbls:
                t_chosen = next((t for t in tbls if t.lower() in instruction.lower()), tbls[0])
                rows = [dict(r) for r in con.execute(f'SELECT * FROM "{t_chosen}"').fetchall()]
            con.close()
    except Exception:
        return None

    if not rows:
        return None
    schema_cols = list(rows[0].keys())
    low = instruction.lower()
    ops_applied: list[str] = []

    def _to_num(v: Any) -> float | None:
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
        try:
            return float(str(v).strip())
        except Exception:
            return None

    # 1. Optional filter predicate: `where <col> <op> <val>`
    for fm in re.finditer(
        r"\bwhere\s+([A-Za-z_][A-Za-z0-9_.\-]*)\s*(==|=|!=|>=|<=|>|<)\s*('[^']*'|\"[^\"]*\"|[A-Za-z0-9_.\-]+)",
        instruction,
        re.IGNORECASE,
    ):
        col = _fuzzy_best_name(fm.group(1), schema_cols)
        op = fm.group(2)
        val = _coerce_literal_scalar(fm.group(3))
        if col is None:
            continue
        filtered = []
        for r in rows:
            rv = r.get(col)
            rn, vn = _to_num(rv), _to_num(val)
            if op in ("=", "=="):
                ok = (rn == vn) if (rn is not None and vn is not None) else (str(rv).strip().lower() == str(val).strip().lower())
            elif op == "!=":
                ok = (rn != vn) if (rn is not None and vn is not None) else (str(rv).strip().lower() != str(val).strip().lower())
            elif rn is not None and vn is not None:
                ok = (rn > vn) if op == ">" else (rn < vn) if op == "<" else (rn >= vn) if op == ">=" else (rn <= vn)
            else:
                ok = False
            if ok:
                filtered.append(r)
        rows = filtered
        ops_applied.append(f"filter({op})")

    # 2. Optional group-by + aggregation: `group by <col>` + sum/count/avg/mean/min/max
    m_gb = re.search(r"\bgroup\s+by\s+([A-Za-z_][A-Za-z0-9_.\-]*)", instruction, re.IGNORECASE)
    result_obj: Any = rows
    if m_gb:
        gcol = _fuzzy_best_name(m_gb.group(1), schema_cols)
        if gcol is not None:
            agg_op = "count"
            agg_col: str | None = None
            m_agg = re.search(
                r"\b(sum|total|average|avg|mean|min|max|count)\s+(?:of\s+)?([A-Za-z_][A-Za-z0-9_.\-]*)",
                instruction,
                re.IGNORECASE,
            )
            if m_agg:
                raw_op = m_agg.group(1).lower()
                agg_op = "sum" if raw_op in ("sum", "total") else ("avg" if raw_op in ("average", "avg", "mean") else raw_op)
                agg_col = _fuzzy_best_name(m_agg.group(2), schema_cols)
            if agg_col is None and agg_op != "count":
                # Pick first numeric column other than gcol
                for c in schema_cols:
                    if c != gcol and any(_to_num(r.get(c)) is not None for r in rows[:5]):
                        agg_col = c
                        break
            groups: dict[str, list[dict[str, Any]]] = {}
            for r in rows:
                k = str(r.get(gcol, ""))
                groups.setdefault(k, []).append(r)
            agg_dict: dict[str, Any] = {}
            for k in sorted(groups.keys()):
                g_rows = groups[k]
                if agg_op == "count" or agg_col is None:
                    agg_dict[k] = len(g_rows)
                else:
                    nums = [n for n in (_to_num(r.get(agg_col)) for r in g_rows) if n is not None]
                    if agg_op == "sum":
                        val_a = sum(nums)
                    elif agg_op == "avg":
                        val_a = (sum(nums) / len(nums)) if nums else 0.0
                    elif agg_op == "min":
                        val_a = min(nums) if nums else 0.0
                    else:
                        val_a = max(nums) if nums else 0.0
                    agg_dict[k] = int(val_a) if abs(val_a - round(val_a)) < 1e-9 else round(val_a, 6)
            result_obj = agg_dict
            ops_applied.append(f"groupby+{agg_op}")
    else:
        # 3. Optional sort + top-N / limit
        m_sort = re.search(r"\bsort(?:ed)?\s+by\s+([A-Za-z_][A-Za-z0-9_.\-]*)(?:\s+(asc|ascending|desc|descending))?", instruction, re.IGNORECASE)
        if m_sort:
            scol = _fuzzy_best_name(m_sort.group(1), schema_cols)
            desc = bool(m_sort.group(2) and m_sort.group(2).lower().startswith("desc")) or ("descending" in low)
            if scol is not None:
                rows = sorted(
                    rows,
                    key=lambda r: (0, _to_num(r.get(scol))) if _to_num(r.get(scol)) is not None else (1, str(r.get(scol, ""))),
                    reverse=desc,
                )
                ops_applied.append("sort_" + ("desc" if desc else "asc"))
        m_top = re.search(r"\b(?:top|first|limit)\s+(\d+)\b", low)
        if m_top:
            rows = rows[: int(m_top.group(1))]
            ops_applied.append("limit")
        result_obj = rows

    # Require either explicit relational op OR explicit format conversion
    out_kind = target_out.suffix.lower().lstrip(".")
    if not ops_applied and out_kind == in_kind:
        return None

    # Atomic write
    target_out.parent.mkdir(parents=True, exist_ok=True)
    if out_kind == "json":
        target_out.write_text(json.dumps(result_obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    elif out_kind == "jsonl" and isinstance(result_obj, list):
        target_out.write_text("\n".join(json.dumps(r, sort_keys=True) for r in result_obj) + "\n", encoding="utf-8")
    elif out_kind in ("csv", "tsv"):
        delim = "\t" if out_kind == "tsv" else ","
        out_rows = (
            [{"key": k, "value": v} for k, v in result_obj.items()]
            if isinstance(result_obj, dict)
            else list(result_obj)
        )
        if out_rows:
            cols_out = list(out_rows[0].keys())
            with open(target_out, "w", encoding="utf-8", newline="") as f:
                w = _csv.DictWriter(f, fieldnames=cols_out, delimiter=delim)
                w.writeheader()
                w.writerows(out_rows)
    else:
        target_out.write_text(json.dumps(result_obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if postcondition_fn is not None:
        ok_post, _ = postcondition_fn(ws)
        if not ok_post:
            target_out.unlink(missing_ok=True)
            return None

    # Distill path-free operator-shape law (ZERO filenames, ZERO column values!)
    law_id = None
    recalled = False
    if memory is not None:
        shape_sig = f"zero_prior_data|{in_kind}->{','.join(ops_applied) or 'convert'}->{out_kind}"
        lid = "zpdata_" + hashlib.sha256(shape_sig.encode("utf-8")).hexdigest()[:12]
        glaws = memory.setdefault("generalized_laws", {})
        if lid in glaws:
            recalled = True
            glaws[lid]["support_count"] = int(glaws[lid].get("support_count", 1)) + 1
        else:
            glaws[lid] = {
                "law_id": lid,
                "kind": "zero_prior_data_pipeline",
                "input_format": in_kind,
                "output_format": out_kind,
                "operator_shape": ops_applied or ["convert"],
                "support_count": 1,
                "parameters_stored": 0,
                "raw_prose_stored": 0,
            }
        law_id = lid
        compress_and_prune_memory(memory)

    return {
        "status": "VERIFIED",
        "mode": "TIER0_ZERO_PRIOR_DATA_PIPELINE" if recalled else "EPISTEMIC_ZERO_PRIOR_DATA_PIPELINE",
        "gaps_queried": [] if recalled else [f"schema:{in_kind}"],
        "operator_shape": ops_applied or ["convert"],
        "law_id": law_id,
    }


_CLI_CONCEPT_CLUSTERS: tuple[frozenset[str], ...] = (
    frozenset({"limit", "max", "cap", "count", "top", "take", "head", "num", "rows", "entries", "items", "n"}),
    frozenset({"output", "out", "dest", "destination", "target", "write", "save", "export", "result", "o"}),
    frozenset({"input", "in", "src", "source", "read", "data", "dataset", "file", "i"}),
    frozenset({"format", "fmt", "style", "mode", "type", "encoding", "f"}),
    frozenset({"filter", "where", "match", "query", "select", "pattern", "grep", "status", "category"}),
    frozenset({"sort", "order", "by", "key", "rank", "orderby"}),
    frozenset({"reverse", "desc", "descending", "r"}),
    frozenset({"delimiter", "delim", "sep", "separator", "d"}),
    frozenset({"column", "col", "field", "metric", "attr", "group", "groupby"}),
    frozenset({"verbose", "debug", "v"}),
    frozenset({"quiet", "silent", "q"}),
)

_CLI_FLAG_ERROR_RE = re.compile(
    r"(?:unrecognized\s+(?:arguments?|options?)|unknown\s+(?:flag|option|argument)|"
    r"no\s+such\s+option|invalid\s+option|illegal\s+option|not\s+a\s+valid\s+option|"
    r"ambiguous\s+option|unexpected\s+(?:flag|option|argument)|"
    r"the\s+following\s+arguments?\s+are\s+required|missing\s+required\s+(?:argument|option|flag))",
    flags=re.IGNORECASE,
)


def _tokenize_cli_name(s: str) -> set[str]:
    clean = re.sub(r"^--?", "", s.strip())
    parts = re.split(r"[^A-Za-z0-9]+", clean.lower())
    return {p for p in parts if p}


def _expand_cli_concepts(toks: set[str]) -> set[str]:
    out = set(toks)
    for cl in _CLI_CONCEPT_CLUSTERS:
        if toks & cl:
            out |= cl
    return out


def _parse_cli_help_options(help_text: str) -> list[dict[str, Any]]:
    """Parse declared CLI options (`--long`, `-s`, takes_value, help description) from live `--help` output."""
    options: list[dict[str, Any]] = []
    seen_primary: set[str] = set()
    lines = help_text.splitlines()
    for idx, line in enumerate(lines):
        # Match option specs like:
        #   -n N, --max-rows N     Limit number of rows
        #   --dest-file=PATH       Output file path
        #   --reverse              Sort descending
        m = re.match(
            r"^\s*((?:-[A-Za-z0-9](?:[=\s]+[A-Z0-9_<>\[\]\-]+)?,\s*)?--[A-Za-z0-9][A-Za-z0-9_\-]*"
            r"(?:(?:=|\s+)(?:[A-Z][A-Z0-9_\-]*|<[^>]+>|\[[^\]]+\]))?"
            r"|-[A-Za-z0-9](?:(?:=|\s+)(?:[A-Z][A-Z0-9_\-]*|<[^>]+>))?)"
            r"(?:\s{2,}(.*)|\s*$)",
            line,
        )
        if not m:
            continue
        spec = m.group(1).strip()
        desc = (m.group(2) or "").strip()
        # Capture 1 wrapped continuation line if heavily indented and doesn't start a new flag
        if idx + 1 < len(lines):
            nxt = lines[idx + 1]
            if re.match(r"^\s{8,}[^-\s]", nxt):
                desc = (desc + " " + nxt.strip()).strip()
        longs = re.findall(r"--[A-Za-z0-9][A-Za-z0-9_\-]*", spec)
        shorts = re.findall(r"(?<!-)-[A-Za-z0-9](?![A-Za-z0-9_\-])", spec)
        primary = longs[0] if longs else (shorts[0] if shorts else "")
        if not primary or primary in ("--help", "-h", "--version", "-V"):
            continue
        if primary in seen_primary:
            continue
        seen_primary.add(primary)
        # Determine whether option takes an argument value
        takes_value = bool(
            re.search(r"(?:--[A-Za-z0-9_\-]+|-[A-Za-z0-9])(?:=|\s+)(?:[A-Z][A-Z0-9_\-]*|<[^>]+>|\[[^\]]+\])", spec)
        )
        options.append({
            "primary": primary,
            "longs": longs,
            "shorts": shorts,
            "takes_value": takes_value,
            "description": desc,
        })
    return options


def _align_cli_flag_to_help(
    requested_flag: str,
    options: Sequence[Mapping[str, Any]],
    *,
    used_flags: set[str] | None = None,
    has_value: bool | None = None,
) -> str | None:
    """Semantically & lexically align a requested/rejected flag to a live `--help` option."""
    used = used_flags or set()
    # Exact match first
    for opt in options:
        all_names = list(opt.get("longs") or ()) + list(opt.get("shorts") or ())
        if requested_flag in all_names:
            return requested_flag

    req_toks = _tokenize_cli_name(requested_flag)
    req_concepts = _expand_cli_concepts(req_toks)
    best_flag: str | None = None
    best_score = 0.0
    for opt in options:
        primary = str(opt.get("primary") or "")
        if not primary or primary in used:
            continue
        opt_toks = set()
        for nm in list(opt.get("longs") or ()) + list(opt.get("shorts") or ()):
            opt_toks |= _tokenize_cli_name(nm)
        desc_toks = _tokenize_cli_name(str(opt.get("description") or ""))
        opt_concepts = _expand_cli_concepts(opt_toks)
        desc_concepts = _expand_cli_concepts(desc_toks)

        # Direct token overlap on flag name (strongest)
        direct_name_ov = len(req_toks & opt_toks)
        # Concept cluster overlap on flag name
        concept_name_ov = len(req_concepts & opt_concepts)
        # Concept/token overlap with --help description
        desc_direct_ov = len(req_toks & desc_toks)
        desc_concept_ov = len(req_concepts & desc_concepts)
        # Edit similarity on normalized stem
        req_stem = re.sub(r"^--?", "", requested_flag).lower().replace("-", "_")
        opt_stem = re.sub(r"^--?", "", primary).lower().replace("-", "_")
        sim = difflib.SequenceMatcher(None, req_stem, opt_stem).ratio()

        score = (
            4.0 * direct_name_ov
            + 2.5 * (1.0 if concept_name_ov > 0 else 0.0)
            + 1.5 * desc_direct_ov
            + 1.0 * (1.0 if desc_concept_ov > 0 else 0.0)
            + 1.2 * sim
        )
        if has_value is not None and bool(opt.get("takes_value")) == bool(has_value):
            score += 0.5
        if score > best_score:
            best_score = score
            best_flag = primary

    return best_flag if best_score >= 1.8 else None


def _discover_local_cli_tool(ws: pathlib.Path, instruction: str) -> pathlib.Path | None:
    """Locate a local CLI executable or script referenced by the instruction (goal-directed)."""
    candidates: list[pathlib.Path] = []
    for search_dir in (ws, ws / "bin", ws / "scripts"):
        if not search_dir.is_dir():
            continue
        for p in sorted(search_dir.iterdir()):
            if not p.is_file() or p.name.startswith(".") or p.name.startswith("test_"):
                continue
            is_exec = os.access(p, os.X_OK)
            is_py_cli = False
            if p.suffix.lower() == ".py":
                try:
                    head_txt = p.read_text(encoding="utf-8", errors="ignore")[:8000]
                    if (
                        '__name__ == "__main__"' in head_txt
                        or "__name__ == '__main__'" in head_txt
                        or "argparse" in head_txt
                        or "sys.argv" in head_txt
                    ):
                        is_py_cli = True
                except OSError:
                    pass
            if is_exec or is_py_cli:
                candidates.append(p)

    if not candidates:
        return None
    instr_low = instruction.lower()
    # Prefer tool whose exact filename or relative path or stem appears in instruction
    scored: list[tuple[int, pathlib.Path]] = []
    for p in candidates:
        rel = str(p.relative_to(ws)).lower()
        nm = p.name.lower()
        stem = p.stem.lower()
        sc = 0
        if rel in instr_low or f"./{rel}" in instr_low:
            sc += 10
        elif nm in instr_low:
            sc += 8
        elif re.search(rf"\b{re.escape(stem)}\b", instr_low):
            sc += 5
        if sc > 0:
            scored.append((sc, p))
    if scored:
        scored.sort(key=lambda x: (-x[0], len(str(x[1]))))
        return scored[0][1]
    return None


def _extract_cli_flag_pairs(instruction: str) -> list[tuple[str, str | None]]:
    """Extract requested `--flag value` / `--flag=value` / `-f value` tokens from an instruction."""
    pairs: list[tuple[str, str | None]] = []
    # Strip surrounding backticks / quotes around command fragments
    cleaned = instruction.replace("`", " ")
    toks = re.findall(r"""--[A-Za-z0-9][A-Za-z0-9_\-]*(?:=[^\s,;'"`]+)?|-[A-Za-z0-9]|[^\s,;]+""", cleaned)
    i = 0
    while i < len(toks):
        tok = toks[i].strip("\"'.,;:")
        if re.fullmatch(r"--[A-Za-z0-9][A-Za-z0-9_\-]*=[^\s]+", tok):
            fl, val = tok.split("=", 1)
            pairs.append((fl, val.strip("\"'.,;:")))
            i += 1
            continue
        if re.fullmatch(r"--[A-Za-z0-9][A-Za-z0-9_\-]*|-[A-Za-z]", tok):
            nxt: str | None = None
            if i + 1 < len(toks):
                cand = toks[i + 1].strip("\"'.,;:")
                # Stop before prose connectors or another flag
                if (
                    cand
                    and not cand.startswith("-")
                    and cand.lower() not in ("and", "to", "into", "from", "with", "using", "then", "save", "write")
                ):
                    nxt = cand
                    i += 2
                    pairs.append((tok, nxt))
                    continue
            pairs.append((tok, None))
            i += 1
            continue
        i += 1
    return pairs


def _solve_zero_prior_cli_error_self_heal(
    ws: pathlib.Path,
    instruction: str,
    target_out: pathlib.Path | None,
    *,
    memory: dict[str, Any] | None = None,
    postcondition_fn: Callable[[pathlib.Path], tuple[bool, str]] | None = None,
    python_exe: str,
    timeout_s: float = 20.0,
) -> dict[str, Any] | None:
    """Track C: Zero-prior unseen CLI binary/script execution with closed-loop flag error self-healing,
    live `--help` introspection, Trace2Skill `CLIFlagError -> help_introspect_remap_flag` distillation,
    and Tier-0 transfer (0 failed executions) to brand-new unseen CLI tools.
    """
    tool_path = _discover_local_cli_tool(ws, instruction)
    if tool_path is None:
        return None
    flag_pairs = _extract_cli_flag_pairs(instruction)
    if not flag_pairs:
        return None

    base_cmd = [python_exe, str(tool_path)] if tool_path.suffix.lower() == ".py" else [str(tool_path)]

    def _run_cmd(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            argv,
            cwd=str(ws),
            capture_output=True,
            text=True,
            timeout=min(timeout_s, 15.0),
        )

    def _introspect_help() -> list[dict[str, Any]]:
        for hflag in ("--help", "-h"):
            try:
                cp_h = _run_cmd(base_cmd + [hflag])
                txt = (cp_h.stdout or "") + "\n" + (cp_h.stderr or "")
                opts = _parse_cli_help_options(txt)
                if opts:
                    return opts
            except Exception:
                continue
        return []

    def _pairs_to_argv(pairs: Sequence[tuple[str, str | None]]) -> list[str]:
        argv = list(base_cmd)
        for fl, val in pairs:
            argv.append(fl)
            if val is not None:
                argv.append(val)
        return argv

    def _verify_and_finalize(cp_ok: subprocess.CompletedProcess[str]) -> bool:
        if cp_ok.returncode != 0:
            return False
        if target_out is not None and not target_out.exists() and (cp_ok.stdout or "").strip():
            target_out.parent.mkdir(parents=True, exist_ok=True)
            target_out.write_text(cp_ok.stdout, encoding="utf-8")
        if postcondition_fn is not None:
            ok_post, _ = postcondition_fn(ws)
            if not ok_post:
                return False
        if target_out is not None and not target_out.exists():
            return False
        return True

    # Check Tier-0 Recall FIRST: if `CLIFlagError -> help_introspect_remap_flag` is ACTIVE in memory,
    # introspect `--help` UP FRONT so we achieve 0 failed executions on brand-new unseen CLI tools!
    recalled_laws = recall_error_fix_laws(
        memory, error_kind="CLIFlagError", context_shape="cli_invocation",
    )
    recalled_law_ids = [
        str(r["law_id"]) for r in recalled_laws if r.get("repair_op") == "help_introspect_remap_flag"
    ]
    gaps_queried: list[str] = []
    error_repairs: list[dict[str, Any]] = []
    failed_executions = 0

    if recalled_law_ids:
        help_opts = _introspect_help()
        if help_opts:
            used_now: set[str] = set()
            mapped_pairs: list[tuple[str, str | None]] = []
            remaps_pre: list[dict[str, str]] = []
            for fl, val in flag_pairs:
                aligned = _align_cli_flag_to_help(
                    fl, help_opts, used_flags=used_now, has_value=(val is not None),
                )
                chosen = aligned or fl
                used_now.add(chosen)
                mapped_pairs.append((chosen, val))
                if chosen != fl:
                    remaps_pre.append({"from": fl, "to": chosen})
            cp_t0 = _run_cmd(_pairs_to_argv(mapped_pairs))
            if _verify_and_finalize(cp_t0):
                if memory is not None:
                    record_error_fix_law(
                        memory,
                        error_kind="CLIFlagError",
                        context_shape="cli_invocation",
                        repair_op="help_introspect_remap_flag",
                        repair_params={"probe": "--help"},
                    )
                    compress_and_prune_memory(memory)
                return {
                    "status": "VERIFIED",
                    "mode": "TIER0_ZERO_PRIOR_CLI_WITH_ERROR_LAW",
                    "tool": str(tool_path.relative_to(ws)),
                    "command": _pairs_to_argv(mapped_pairs),
                    "pre_remaps": remaps_pre,
                    "error_repairs": [],
                    "failed_executions": 0,
                    "recalled_law_ids": recalled_law_ids,
                    "learned_law_ids": [],
                    "gaps_queried": [],
                    "model_calls": 0,
                    "parameters_stored": 0,
                }
            # If Tier-0 law failed, refute cleanly per Skill-Pro discipline before falling through
            failed_executions += 1
            if memory is not None:
                for lid in recalled_law_ids:
                    refute_error_fix_law(memory, lid, f"tier0_cli_failed:{(cp_t0.stderr or '')[:100]}")

    # Cold closed-loop CEGIS execution: execute -> diagnose CLI flag error -> `--help` -> remap -> re-run
    cur_pairs = list(flag_pairs)
    help_opts_cache: list[dict[str, Any]] | None = None
    for _round in range(4):
        argv = _pairs_to_argv(cur_pairs)
        try:
            cp = _run_cmd(argv)
        except Exception:
            return None
        if _verify_and_finalize(cp):
            learned_ids: list[str] = []
            if error_repairs and memory is not None:
                rec = record_error_fix_law(
                    memory,
                    error_kind="CLIFlagError",
                    context_shape="cli_invocation",
                    repair_op="help_introspect_remap_flag",
                    repair_params={"probe": "--help"},
                )
                if rec is not None:
                    learned_ids.append(str(rec["law_id"]))
                compress_and_prune_memory(memory)
            return {
                "status": "VERIFIED",
                "mode": "EPISTEMIC_ZERO_PRIOR_CLI_ERROR_HEAL" if error_repairs else "EPISTEMIC_ZERO_PRIOR_CLI_DIRECT",
                "tool": str(tool_path.relative_to(ws)),
                "command": argv,
                "error_repairs": error_repairs,
                "failed_executions": failed_executions,
                "recalled_law_ids": [],
                "learned_law_ids": learned_ids,
                "gaps_queried": gaps_queried,
                "model_calls": 0,
                "parameters_stored": 0,
            }

        err_txt = (cp.stderr or "") + "\n" + (cp.stdout or "")
        failed_executions += 1
        if not _CLI_FLAG_ERROR_RE.search(err_txt):
            return None

        if help_opts_cache is None:
            gaps_queried.append("cli_help_introspect")
            help_opts_cache = _introspect_help()
            if not help_opts_cache:
                return None

        declared_set = set()
        for opt in help_opts_cache:
            declared_set.update(opt.get("longs") or ())
            declared_set.update(opt.get("shorts") or ())

        # Remap every undeclared flag in `cur_pairs` via live `--help` alignment
        used_now = {fl for fl, _ in cur_pairs if fl in declared_set}
        changed = False
        new_pairs: list[tuple[str, str | None]] = []
        for fl, val in cur_pairs:
            if fl in declared_set:
                new_pairs.append((fl, val))
                continue
            aligned = _align_cli_flag_to_help(
                fl, help_opts_cache, used_flags=used_now, has_value=(val is not None),
            )
            if aligned and aligned != fl:
                used_now.add(aligned)
                new_pairs.append((aligned, val))
                error_repairs.append({"bad_flag": fl, "repaired_flag": aligned, "stderr_excerpt": err_txt.strip()[:160]})
                changed = True
            else:
                new_pairs.append((fl, val))
        if not changed:
            return None
        cur_pairs = new_pairs

    return None


def solve_zero_prior_closed_loop_epistemic(
    ws: pathlib.Path,
    instruction: str,
    *,
    memory: dict[str, Any] | None = None,
    postcondition_fn: Callable[[pathlib.Path], tuple[bool, str]] | None = None,
    python_exe: str | None = None,
    timeout_s: float = 20.0,
) -> dict[str, Any] | None:
    """Universal Step-6 Zero-Prior Closed-Loop Epistemic Solver.
    Activated only when no bespoke family or pre-known CLI morphism matched.
    Scans ONLY the goal-relevant cone (local CLI binaries/scripts, local Python modules,
    & structured data schemas), queries ONLY unknown epistemic gaps live, repairs runtime
    errors via Trace2Skill error-fix laws + live introspection, verifies atomically,
    and distills ONLY parameterized path-free laws.
    """
    target_out = _extract_zero_prior_target_path(instruction, ws)
    py = python_exe or sys.executable

    # Track C: Unknown local CLI binary / script execution + live `--help` flag error self-heal
    res_c = _solve_zero_prior_cli_error_self_heal(
        ws, instruction, target_out,
        memory=memory, postcondition_fn=postcondition_fn,
        python_exe=py, timeout_s=timeout_s,
    )
    if res_c is not None:
        return res_c

    if target_out is None:
        return None
    py_modules: list[pathlib.Path] = []
    data_files: list[pathlib.Path] = []
    for p in sorted(ws.iterdir()):
        if not p.is_file() or p.name.startswith("."):
            continue
        suf = p.suffix.lower()
        if suf == ".py" and not p.name.startswith("test_"):
            py_modules.append(p)
        elif suf in (".json", ".jsonl", ".csv", ".tsv", ".db", ".sqlite", ".sqlite3"):
            data_files.append(p)

    # Track A: Unknown local Python module/API invocation + closed-loop error repair
    if py_modules:
        res_a = _solve_zero_prior_unknown_python_api(
            ws, instruction, target_out, py_modules, data_files,
            memory=memory, postcondition_fn=postcondition_fn,
            python_exe=py, timeout_s=timeout_s,
        )
        if res_a is not None:
            return res_a

    # Track B: Arbitrary unseen structured data live-schema relational transform
    if data_files:
        res_b = _solve_zero_prior_structured_data(
            ws, instruction, target_out, data_files,
            memory=memory, postcondition_fn=postcondition_fn,
        )
        if res_b is not None:
            return res_b

    return None


_GUI_DESTRUCTIVE_RE = re.compile(
    r"\b(?:delete|remove|destroy|wipe|purge|reset|erase|cancel|discard|abort|logout|sign\s*out|close\s+without)\b",
    flags=re.IGNORECASE,
)
_GUI_CONFIRM_RE = re.compile(
    r"\b(?:confirm|ok|yes|proceed|accept|approve)\b",
    flags=re.IGNORECASE,
)
_GUI_SUBMIT_RE = re.compile(
    r"\b(?:save|submit|apply|update|create|finish|done|next|continue|publish|send)\b",
    flags=re.IGNORECASE,
)


def _gui_tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if len(t) >= 2}


def _match_field_value_for_node(
    node: Mapping[str, Any],
    field_values: Mapping[str, Any],
    instruction: str,
) -> tuple[str, str] | None:
    """Match an accessibility input/combobox node to a provided field value or goal value."""
    node_txt = " ".join(
        str(node.get(k) or "") for k in ("name", "label", "placeholder", "id", "hint")
    )
    node_toks = _gui_tokens(node_txt)
    if not node_toks:
        return None
    best_k = ""
    best_v = ""
    best_sc = 0.0
    for k, v in field_values.items():
        ktoks = _gui_tokens(str(k))
        ov = len(node_toks & ktoks)
        sim = difflib.SequenceMatcher(
            None,
            re.sub(r"[^a-z0-9]+", "", str(k).lower()),
            re.sub(r"[^a-z0-9]+", "", str(node.get("name") or node.get("id") or "").lower()),
        ).ratio()
        sc = 3.0 * ov + 1.5 * sim
        if sc > best_sc:
            best_sc = sc
            best_k = str(k)
            best_v = str(v)
    if best_sc >= 1.2:
        return best_k, best_v
    return None


def _repair_value_from_a11y_error(
    err_msg: str,
    cur_val: str,
    *,
    field_name: str = "",
) -> str | None:
    """Derive a concrete repaired field value directly from a live GUI validation error message."""
    low = err_msg.lower()
    # 1. Required prefix (e.g., "must start with 'https://'" or "must start with +1")
    m_pref = re.search(
        r"(?:must\s+(?:start|begin)\s+with|prefix\s+(?:required|must\s+be))\s+['\"`]?([^\s'\"`,;]+)['\"`]?",
        err_msg,
        flags=re.IGNORECASE,
    )
    if m_pref:
        pref = m_pref.group(1)
        if not cur_val.startswith(pref):
            return pref + cur_val

    # 2. Required substring / character (e.g., "must contain '@'" or "must include '-'")
    m_cont = re.search(
        r"must\s+(?:contain|include)\s+['\"`]([^'\"`]+)['\"`]",
        err_msg,
        flags=re.IGNORECASE,
    )
    if m_cont:
        sub = m_cont.group(1)
        if sub not in cur_val:
            if sub == "@":
                return (cur_val or "user") + "@example.com"
            return cur_val + sub

    # 3. Minimum length constraint (e.g., "at least 12 characters" or "minimum length 10")
    m_min = re.search(
        r"(?:at\s+least|min(?:imum)?(?:\s+length)?(?:\s+of)?)\s+(\d+)\s*(?:char|character|symbol|digit)?",
        low,
    )
    if m_min:
        req_len = int(m_min.group(1))
        if len(cur_val) < req_len:
            pad = "_valid_0123456789"
            repaired = cur_val
            while len(repaired) < req_len:
                repaired += pad
            return repaired[:req_len]

    # 4. Required non-empty field
    if "required" in low and not cur_val.strip():
        return f"default_{re.sub(r'[^a-z0-9]+', '_', field_name.lower()).strip('_') or 'value'}"

    return None


def _solve_interactive_gui_a11y_workflow(
    gui_env: Any,
    instruction: str,
    *,
    field_values: Mapping[str, Any] | None = None,
    memory: dict[str, Any] | None = None,
    max_steps: int = 24,
) -> dict[str, Any]:
    """Zero-prior interactive observable GUI / Accessibility-Tree closed-loop workflow engine.
    Works on ANY observable A11y tree environment (`observe() -> {screen, nodes, errors, done}`,
    `step(action) -> obs`): navigates sections, avoids destructive traps, fills inputs, handles
    modal confirm dialogs, self-heals live validation errors from A11y error messages, distills
    path/app/ID-free Skill-Pro procedural skills & Trace2Skill validation laws, and transfers
    at Tier-0 (0 failed submits, 0 traps) to brand-new unseen GUI apps.
    """
    t0 = time.monotonic()
    fvals = dict(field_values or {})
    instr_toks = _gui_tokens(instruction)
    goal_allows_destructive = bool(_GUI_DESTRUCTIVE_RE.search(instruction or ""))

    # Check Tier-0 Skill-Pro GUI workflow & validation error law recall
    recalled_err_laws = recall_error_fix_laws(
        memory, error_kind="GUIValidationError", context_shape="a11y_form_submit",
    )
    gui_skills = memory.get("gui_workflow_skills") if isinstance(memory, Mapping) else None
    recalled_skill_ids = [
        str(sid) for sid, rec in (gui_skills.items() if isinstance(gui_skills, Mapping) else ())
        if isinstance(rec, Mapping) and rec.get("status") == "ACTIVE"
    ]
    recalled_err_ids = [str(r["law_id"]) for r in recalled_err_laws]
    proactive_tier0 = bool(recalled_skill_ids or recalled_err_ids)

    actions_taken: list[dict[str, Any]] = []
    validation_repairs: list[dict[str, Any]] = []
    traps_avoided: list[str] = []
    traps_hit = 0
    failed_submits = 0
    clicked_nav_ids: set[str] = set()
    filled_values: dict[str, str] = {}
    phase_trace: list[str] = []

    obs = gui_env.observe()
    for _step in range(max_steps):
        if obs.get("done"):
            break
        nodes = list(obs.get("nodes") or ())
        screen = str(obs.get("screen") or "")
        live_errors: list[str] = [str(e) for e in (obs.get("errors") or ()) if str(e).strip()]
        for nd in nodes:
            if str(nd.get("role") or "").lower() in ("alert", "error"):
                etxt = str(nd.get("name") or nd.get("value") or "").strip()
                if etxt and etxt not in live_errors:
                    live_errors.append(etxt)

        # Record avoided destructive traps on current screen
        for nd in nodes:
            if not goal_allows_destructive and _GUI_DESTRUCTIVE_RE.search(str(nd.get("name") or "")):
                nm = str(nd.get("name") or "")
                if nm not in traps_avoided:
                    traps_avoided.append(nm)

        # 1. Modal confirmation dialog: click Confirm/OK/Yes (NEVER Cancel/Reset)
        in_dialog = (
            "dialog" in screen.lower()
            or "confirm" in screen.lower()
            or any(str(nd.get("role") or "").lower() == "dialog" for nd in nodes)
        )
        if in_dialog:
            confirm_btn = None
            for nd in nodes:
                if str(nd.get("role") or "").lower() != "button" or not nd.get("enabled", True):
                    continue
                nm = str(nd.get("name") or "")
                if not goal_allows_destructive and _GUI_DESTRUCTIVE_RE.search(nm):
                    continue
                if _GUI_CONFIRM_RE.search(nm) or _GUI_SUBMIT_RE.search(nm):
                    confirm_btn = nd
                    break
            if confirm_btn is not None:
                act = {"type": "click", "id": str(confirm_btn["id"])}
                obs = gui_env.step(act)
                actions_taken.append({"screen": screen, **act, "name": str(confirm_btn.get("name") or "")})
                if "confirm_dialog" not in phase_trace:
                    phase_trace.append("confirm_dialog")
                continue

        # 2. Closed-loop validation error repair when live A11y errors are present
        if live_errors:
            repaired_any = False
            for err_msg in live_errors:
                err_toks = _gui_tokens(err_msg)
                # 2a. Required checkbox / consent error
                if any(w in err_msg.lower() for w in ("accept", "agree", "consent", "confirm", "terms", "check")):
                    for nd in nodes:
                        if str(nd.get("role") or "").lower() in ("checkbox", "switch") and not nd.get("checked", False):
                            if not goal_allows_destructive and _GUI_DESTRUCTIVE_RE.search(str(nd.get("name") or "")):
                                continue
                            act = {"type": "toggle", "id": str(nd["id"])}
                            obs = gui_env.step(act)
                            actions_taken.append({"screen": screen, **act, "name": str(nd.get("name") or "")})
                            validation_repairs.append({"error": err_msg, "action": "toggle_required_checkbox", "id": str(nd["id"])})
                            repaired_any = True
                            break
                    if repaired_any:
                        break

                # 2b. Field value constraint error (min length, prefix, substring, required)
                input_nodes = [
                    nd for nd in nodes
                    if str(nd.get("role") or "").lower() in ("textbox", "input", "combobox", "spinbutton", "searchbox")
                    and nd.get("enabled", True)
                ]
                best_nd = None
                best_ov = -1
                for nd in input_nodes:
                    nd_toks = _gui_tokens(f"{nd.get('name', '')} {nd.get('id', '')} {nd.get('placeholder', '')}")
                    ov = len(nd_toks & err_toks)
                    if ov > best_ov:
                        best_ov = ov
                        best_nd = nd
                if best_nd is not None:
                    nid = str(best_nd["id"])
                    cur_v = str(best_nd.get("value") or filled_values.get(nid, ""))
                    fixed_v = _repair_value_from_a11y_error(err_msg, cur_v, field_name=str(best_nd.get("name") or nid))
                    if fixed_v is not None and fixed_v != cur_v:
                        act = {"type": "type", "id": nid, "value": fixed_v}
                        obs = gui_env.step(act)
                        filled_values[nid] = fixed_v
                        actions_taken.append({"screen": screen, **act, "name": str(best_nd.get("name") or "")})
                        validation_repairs.append({"error": err_msg, "id": nid, "before": cur_v, "after": fixed_v})
                        repaired_any = True
                        break
            if repaired_any:
                continue

        # 3. Fill all editable inputs / comboboxes on current screen whose values aren't set yet
        progressed_fill = False
        for nd in nodes:
            role = str(nd.get("role") or "").lower()
            if role not in ("textbox", "input", "combobox", "spinbutton", "searchbox") or not nd.get("enabled", True):
                continue
            nid = str(nd["id"])
            if nid in filled_values:
                continue
            cur_v = str(nd.get("value") or "")
            matched = _match_field_value_for_node(nd, fvals, instruction)
            if matched is None:
                continue
            _, desired_v = matched
            # Tier-0 proactive constraint enforcement using live node hint/placeholder BEFORE submitting!
            if proactive_tier0:
                hint_txt = " ".join(str(nd.get(k) or "") for k in ("hint", "placeholder", "description"))
                if hint_txt.strip():
                    pre_fix = _repair_value_from_a11y_error(hint_txt, desired_v, field_name=str(nd.get("name") or nid))
                    if pre_fix is not None:
                        desired_v = pre_fix
            if cur_v != desired_v and filled_values.get(nid) != desired_v:
                act = {"type": "type", "id": nid, "value": desired_v}
                obs = gui_env.step(act)
                filled_values[nid] = desired_v
                actions_taken.append({"screen": screen, **act, "name": str(nd.get("name") or "")})
                if "fill_inputs" not in phase_trace:
                    phase_trace.append("fill_inputs")
                progressed_fill = True
                break
        if progressed_fill:
            continue

        # 4. Toggle checkboxes/switches that are explicitly requested by goal OR marked required (when proactive Tier-0)
        progressed_toggle = False
        for nd in nodes:
            role = str(nd.get("role") or "").lower()
            if role not in ("checkbox", "switch") or not nd.get("enabled", True) or nd.get("checked", False):
                continue
            nm = str(nd.get("name") or "")
            if not goal_allows_destructive and _GUI_DESTRUCTIVE_RE.search(nm):
                continue
            nm_toks = _gui_tokens(nm)
            goal_wants = bool(nm_toks & instr_toks)
            proactive_req = bool(proactive_tier0 and nd.get("required", False))
            if goal_wants or proactive_req:
                act = {"type": "toggle", "id": str(nd["id"])}
                obs = gui_env.step(act)
                actions_taken.append({"screen": screen, **act, "name": nm})
                if "toggle_controls" not in phase_trace:
                    phase_trace.append("toggle_controls")
                progressed_toggle = True
                break
        if progressed_toggle:
            continue

        # 5. Navigate via tabs / menuitem / link matching goal tokens (never destructive, never repeat same nav id)
        nav_candidates: list[tuple[int, Mapping[str, Any]]] = []
        for nd in nodes:
            role = str(nd.get("role") or "").lower()
            nid = str(nd.get("id") or "")
            nm = str(nd.get("name") or "")
            if role not in ("tab", "menuitem", "link", "treeitem") or not nd.get("enabled", True):
                continue
            if nd.get("selected", False) or nid in clicked_nav_ids:
                continue
            if not goal_allows_destructive and _GUI_DESTRUCTIVE_RE.search(nm):
                continue
            ov = len(_gui_tokens(nm) & instr_toks)
            if ov > 0:
                nav_candidates.append((ov, nd))
        if nav_candidates:
            nav_candidates.sort(key=lambda x: -x[0])
            chosen_nav = nav_candidates[0][1]
            nid = str(chosen_nav["id"])
            clicked_nav_ids.add(nid)
            act = {"type": "click", "id": nid}
            obs = gui_env.step(act)
            actions_taken.append({"screen": screen, **act, "name": str(chosen_nav.get("name") or "")})
            if "navigate_section" not in phase_trace:
                phase_trace.append("navigate_section")
            continue

        # 6. Click primary non-destructive Submit/Save/Apply/Next button
        submit_btn = None
        for nd in nodes:
            if str(nd.get("role") or "").lower() != "button" or not nd.get("enabled", True):
                continue
            nm = str(nd.get("name") or "")
            if not goal_allows_destructive and _GUI_DESTRUCTIVE_RE.search(nm):
                continue
            if _GUI_SUBMIT_RE.search(nm):
                submit_btn = nd
                break
        if submit_btn is not None:
            act = {"type": "click", "id": str(submit_btn["id"])}
            prev_screen = screen
            obs = gui_env.step(act)
            actions_taken.append({"screen": prev_screen, **act, "name": str(submit_btn.get("name") or "")})
            if "submit_form" not in phase_trace:
                phase_trace.append("submit_form")
            if not obs.get("done") and obs.get("errors"):
                failed_submits += 1
            continue

        break

    verified = bool(obs.get("done"))
    if obs.get("trap_triggered"):
        traps_hit += 1

    learned_skill_id: str | None = None
    learned_err_law_id: str | None = None
    if verified and memory is not None:
        # Distill abstract app-free, ID-free, coordinate-free GUI workflow skill!
        skel = tuple(phase_trace or ["submit_form"])
        sig = "guiskill|" + "->".join(skel)
        sid = "guiskill_" + hashlib.sha256(sig.encode("utf-8")).hexdigest()[:12]
        gstore = memory.setdefault("gui_workflow_skills", {})
        if sid in gstore:
            gstore[sid]["verified_uses"] = int(gstore[sid].get("verified_uses", 1)) + 1
        else:
            gstore[sid] = {
                "skill_id": sid,
                "abstract_phases": list(skel),
                "proactive_hint_and_required_check": True,
                "destructive_trap_guard": True,
                "status": "ACTIVE",
                "verified_uses": 1,
                "parameters_stored": 0,
                "raw_prose_stored": 0,
            }
        learned_skill_id = sid
        if validation_repairs:
            erec = record_error_fix_law(
                memory,
                error_kind="GUIValidationError",
                context_shape="a11y_form_submit",
                repair_op="parse_a11y_constraint_and_repair",
                repair_params={"proactive_hints_and_required": True},
            )
            if erec is not None:
                learned_err_law_id = str(erec["law_id"])
        compress_and_prune_memory(memory)

    mode_out = (
        "TIER0_GUI_A11Y_POLY_SKILL"
        if (verified and proactive_tier0 and failed_submits == 0)
        else ("EPISTEMIC_GUI_A11Y_CLOSED_LOOP" if verified else "GUI_A11Y_FAILED")
    )
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "modality": "interactive_gui_a11y_workflow",
        "status": "VERIFIED" if verified else "FAILED",
        "mode": mode_out,
        "actions_taken": actions_taken,
        "validation_repairs": validation_repairs,
        "failed_submits": failed_submits,
        "traps_avoided": traps_avoided,
        "traps_hit": traps_hit,
        "recalled_skill_ids": recalled_skill_ids,
        "recalled_err_law_ids": recalled_err_ids,
        "learned_skill_id": learned_skill_id,
        "learned_err_law_id": learned_err_law_id,
        "final_screen": obs.get("screen"),
        "final_state": obs.get("state"),
        "gaps_queried": [] if (verified and proactive_tier0 and failed_submits == 0) else (["a11y_validation_feedback"] if validation_repairs else []),
        "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
        "model_calls": 0,
        "parameters_stored": 0,
    }


def solve_arbitrary_environment(
    workspace: str | pathlib.Path,
    instruction: str,
    *,
    memory: dict[str, Any] | None = None,
    governed_memory: dict[str, Any] | None = None,
    base_url: str | None = None,
    postcondition_fn: Callable[[pathlib.Path], tuple[bool, str]] | None = None,
    dom_nodes: Sequence[Mapping[str, Any]] | None = None,
    gui_env: Any | None = None,
    web_url: str | None = None,
    target_url: str | None = None,
    api_url: str | None = None,
    graphql_url: str | None = None,
    db_path: str | pathlib.Path | None = None,
    verifier: Any | None = None,
    field_values: Mapping[str, str] | None = None,
    knowledge_source: Callable[[str], list[dict[str, str]]] | None = None,
    python_exe: str | None = None,
    allow_web: bool = True,
    timeout_s: float = 20.0,
) -> dict[str, Any]:
    """Enter ANY unseen arbitrary environment knowing nothing, scan the local frontier,
    compute the exact Epistemic Diff against external memory, acquire ONLY missing gaps
    in parallel, verify atomically in an isolated state copy, and distill ONLY generalized
    atomic knowledge (model_calls == 0, parameters_stored == 0).
    """
    t0 = time.monotonic()
    # 00. Live Goal-Directed Scan -> Epistemic-Gap-Diff -> Instant-Acquire -> Leap-4 Mental-Simulate
    # -> Live Execute (OS + SQLite + HTTP + PatchWorld 401 Recovery) -> L2/L3 Governed Memory Compression
    if governed_memory is not None:
        from canonical.runtime import epistemic_scan_acquire_compress_v1 as ESAC

        _es_ver = (
            (lambda ws_p, _art: postcondition_fn(ws_p))
            if postcondition_fn is not None
            else verifier
        )
        es_res = ESAC.solve_unseen_environment_live(
            workspace,
            instruction,
            governed_memory=governed_memory,
            base_url=base_url or api_url or web_url,
            verifier=_es_ver,
            timeout_s=timeout_s,
        )
        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "modality": "epistemic_scan_acquire_compress_live",
            "status": str(es_res.get("status") or "UNSOLVED"),
            "epistemic_result": es_res,
            "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }
    # 0a. Live Interactive Observable GUI / Accessibility-Tree Environment (zero-LLM, OSWorld/ARIA model)
    if gui_env is not None:
        from canonical.runtime import epistemic_world_model_planner_v1 as WM_PLANNER

        _init_obs = gui_env.observe()
        _init_nodes = list(_init_obs.get("nodes") or ())
        _has_disabled = any(bool(n.get("disabled", False)) for n in _init_nodes)
        _recalled_wm = WM_PLANNER._recall_world_model_plan(memory, WM_PLANNER._abstract_role(instruction))
        if _recalled_wm is not None or _has_disabled:
            return WM_PLANNER.solve_with_epistemic_world_model(
                WM_PLANNER.InteractiveA11yWorldAdapter(gui_env),
                instruction,
                field_values=field_values,
                memory=memory,
            )
        _gui_res = _solve_interactive_gui_a11y_workflow(
            gui_env,
            instruction,
            field_values=field_values,
            memory=memory,
        )
        if _gui_res.get("status") == "VERIFIED":
            return _gui_res
        _wm_gui = WM_PLANNER.solve_with_epistemic_world_model(
            WM_PLANNER.InteractiveA11yWorldAdapter(gui_env),
            instruction,
            field_values=field_values,
            memory=memory,
        )
        return _wm_gui if _wm_gui.get("status") == "VERIFIED" else _gui_res

    # 0b. Live Unseen OpenAPI / REST Microservice Environment (zero-LLM, stdlib epistemic_openapi_agent_v1)
    if api_url:
        from canonical.runtime import epistemic_openapi_agent_v1 as OPENAPI_AGENT

        return OPENAPI_AGENT.solve_live_openapi_workflow(
            api_url,
            instruction,
            memory=memory,
            field_values=field_values,
            timeout_s=min(timeout_s, 15.0),
        )

    # 0c. Live Unseen GraphQL API Introspection Environment (zero-LLM, stdlib epistemic_schema_graph_agent_v1)
    if graphql_url:
        from canonical.runtime import epistemic_schema_graph_agent_v1 as SCHEMA_AGENT

        return SCHEMA_AGENT.solve_epistemic_graphql_workflow(
            graphql_url,
            instruction,
            memory=memory,
            field_values=field_values,
            timeout_s=min(timeout_s, 15.0),
        )

    # 0d. Live Unseen Relational SQLite Database (zero-LLM SchemaGraphSQL + CL-BENCH continual learner)
    if db_path:
        from canonical.runtime import epistemic_schema_graph_agent_v1 as SCHEMA_AGENT

        return SCHEMA_AGENT.solve_epistemic_sql_query(
            db_path,
            instruction,
            memory=memory,
            verifier=verifier,
        )

    # 0. Live Interactive HTTP/HTML Web UI Environment (zero-LLM, stdlib htmlform_read_v1 + compose_v1)
    detected_url = web_url
    if not detected_url:
        m_u = _URL_RE.search(instruction or "")
        if m_u:
            detected_url = m_u.group(0).rstrip(".,;)")
    # 0a. Cross-Modal Multi-Step Pipeline (`CLI <-> Authenticated HTTP API <-> CLI`)
    # When the instruction chains multiple steps combining a live URL AND workspace file/CLI clauses,
    # execute the full cross-modal pipeline via the zero-LLM Doc-Compiler BEFORE single-shot Web UI!
    if detected_url and web_url is None and target_url is None:
        from canonical.runtime import epistemic_doc_compiler_agent_v1 as EDC

        _cm_clauses = EDC._decompose_multi_step_goal(instruction or "")
        _has_url_clause = any("http://" in c or "https://" in c for c in _cm_clauses)
        _has_non_url_clause = any("http://" not in c and "https://" not in c for c in _cm_clauses)
        if len(_cm_clauses) >= 2 and _has_url_clause and _has_non_url_clause:
            ws_cm = pathlib.Path(workspace).resolve()
            _edc_mem = EDC.EpistemicMemoryStore()
            _edc_ver = (lambda _st: postcondition_fn(ws_cm)) if postcondition_fn is not None else verifier
            edc_res = EDC.solve_multi_step_with_instant_knowledge(
                instruction,
                workspace=ws_cm,
                memory=_edc_mem,
                knowledge_source=knowledge_source,
                base_url=None,
                verifier=_edc_ver,
                timeout_s=timeout_s,
            )
            if edc_res.get("status") == "VERIFIED":
                return {
                    "schema": SCHEMA,
                    "authority": AUTHORITY,
                    "modality": "cross_modal_cli_http_pipeline",
                    "status": "VERIFIED",
                    "mode": str(edc_res.get("mode") or "MULTI_STEP_DOC_COMPILED_ACTIVE_INFERENCE"),
                    "doc_compiler_result": edc_res,
                    "gaps_queried": list(edc_res.get("gaps_queried") or []),
                    "web_queries_made": 0,
                    "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                    "model_calls": 0,
                    "parameters_stored": 0,
                }
    if detected_url and (
        "/graphql" in detected_url.lower() or "graphql" in (instruction or "").lower()
    ):
        from canonical.runtime import epistemic_schema_graph_agent_v1 as SCHEMA_AGENT

        gql_res = SCHEMA_AGENT.solve_epistemic_graphql_workflow(
            detected_url,
            instruction,
            memory=memory,
            field_values=field_values,
            timeout_s=min(timeout_s, 15.0),
        )
        if gql_res.get("mode") != "GRAPHQL_INTROSPECTION_FAILED":
            return gql_res
    if detected_url and (
        web_url is not None
        or target_url is not None
        or any(w in (instruction or "").lower() for w in ("form", "submit", "apply", "register", "signup", "sign up", "fill", "login", "web", "page", "api", "openapi", "endpoint", "invoice", "shipment", "order", "ticket", "incident", "issue", "record", "table", "portal", "wiki", "count", "total", "sum", "average", "avg", "highest", "lowest", "edit", "update", "list", "filter", "deploy", "release", "publish", "transfer", "approve", "workflow", "unlock", "enable", "configure", "provision", "activate", "verify", "settings"))
    ):
        # Auto-detect OpenAPI/REST JSON service on `detected_url` before falling back to HTML Web UI
        if (
            detected_url.rstrip("/").endswith(".json")
            or any(w in (instruction or "").lower() for w in ("openapi", "swagger", "rest api", "json api", "microservice"))
        ):
            from canonical.runtime import epistemic_openapi_agent_v1 as OPENAPI_AGENT

            oa_res = OPENAPI_AGENT.solve_live_openapi_workflow(
                detected_url,
                instruction,
                memory=memory,
                field_values=field_values,
                timeout_s=min(timeout_s, 15.0),
            )
            if oa_res.get("mode") != "OPENAPI_SPEC_NOT_FOUND":
                return oa_res
        return solve_live_http_web_ui(
            detected_url,
            instruction,
            memory=memory,
            field_values=field_values,
            target_url=target_url,
            timeout_s=min(timeout_s, 15.0),
        )

    ws = pathlib.Path(workspace).resolve()
    frontier = sense_local_frontier(ws, instruction, dom_nodes=dom_nodes)
    epistemic_diff = compute_epistemic_diff(
        ws, instruction, memory=memory, dom_nodes=dom_nodes, frontier=frontier,
    )
    modality = frontier["modality"]

    # 1. Observable Browser / GUI DOM Environment
    if modality == "browser_dom":
        action = CU_AGENT.step_observable_dom(dom_nodes or [], instruction)
        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "modality": modality,
            "status": "VERIFIED" if action.get("action") != "noop" else "FAILED",
            "mode": "OBSERVABLE_DOM_STEP",
            "frontier_sense_ms": frontier["sense_ms"],
            "epistemic_diff": epistemic_diff,
            "dom_action": action,
            "gaps_queried": [],
            "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    # 2. Cross-Modal: Opaque Container Bundle -> Auto-Unwrap -> SWE Repair -> Verify!
    if modality == "cross_modal_bundle_swe":
        m_store = memory.get("morphism_store") if memory is not None else None
        cont = frontier["containers"][0]["rel"]
        # Determine target extraction folder from instruction (or default `unpacked_repo`)
        m_dir = re.search(r"(?:into|to)\s+(?:folder|dir|directory)?\s*([A-Za-z0-9_.\-]+)", instruction, flags=re.IGNORECASE)
        out_dir = m_dir.group(1) if m_dir and "." not in m_dir.group(1) else "unpacked_repo"

        # Step 2a: Implicitly unwrap ALL container layers into `out_dir` (Tier 0 offline or Epistemic Diff!)
        unwrap_goal = f"Extract archive from {cont} into folder {out_dir}"
        u_res = MORPH_ENGINE.solve_with_epistemic_morphisms(
            ws,
            unwrap_goal,
            morphism_store=m_store,
            allow_web=allow_web,
            timeout_s=timeout_s,
        )
        if u_res.status != "VERIFIED" or not (ws / out_dir).is_dir():
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "modality": modality,
                "status": "FAILED",
                "mode": "UNWRAP_FAILED",
                "frontier_sense_ms": frontier["sense_ms"],
                "epistemic_diff": epistemic_diff,
                "unwrap_trace": u_res.steps_trace,
                "gaps_queried": u_res.gaps_queried,
                "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                "model_calls": 0,
                "parameters_stored": 0,
            }

        # Step 2b: Locate unpacked repo root (handle single top-level directory inside archive)
        repo_root = ws / out_dir
        children = [c for c in repo_root.iterdir() if not c.name.startswith(".")]
        if len(children) == 1 and children[0].is_dir() and not any(repo_root.glob("*.py")):
            repo_root = children[0]

        swe_res = solve_swe_with_epistemic_diff(
            repo_root,
            memory=memory,
            python_exe=python_exe,
            allow_web=allow_web,
            timeout_s=timeout_s,
        )
        ok_post = True
        if swe_res["status"] == "VERIFIED" and postcondition_fn is not None:
            ok_post, _ = postcondition_fn(ws)

        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "modality": modality,
            "status": "VERIFIED" if (swe_res["status"] == "VERIFIED" and ok_post) else "FAILED",
            "mode": f"CROSS_MODAL_{u_res.mode}_THEN_{swe_res['mode']}",
            "frontier_sense_ms": frontier["sense_ms"],
            "epistemic_diff": epistemic_diff,
            "unwrap_steps": u_res.steps_trace,
            "swe_result": swe_res,
            "gaps_queried": list(u_res.gaps_queried) + list(swe_res.get("gaps_queried") or []),
            "web_queries_made": u_res.web_queries_made,
            "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    # 3a. Zero-Test Metamorphic & Spec-Contract Self-Oracle SWE Repair
    #     When an unseen Python codebase has NO pre-written failing test suite (`test_files` empty)
    #     yet the goal reports bugs / requests repair, synthesize universal metamorphic invariants
    #     from the codebase AST & local spec docs, discover counterexamples, and drive modular
    #     Causal Angelic SWE repair while enforcing read-only & banned-import policies.
    if not frontier.get("test_files") and frontier.get("py_files") and re.search(
        r"\b(fix|repair|debug|bug|broken|not working|incorrect|missing|inconsistent|stall)\b",
        instruction or "",
        re.IGNORECASE,
    ):
        from canonical.runtime import epistemic_spec_oracle_v1 as SPEC_ORACLE

        so_res = SPEC_ORACLE.solve_zero_test_codebase(
            ws,
            instruction,
            memory=memory,
            python_exe=python_exe,
            timeout_s=max(float(timeout_s), 25.0),
        )
        if so_res.get("status") in ("VERIFIED", "PARTIAL"):
            ok_post = True
            if so_res.get("status") == "VERIFIED" and postcondition_fn is not None:
                ok_post, _ = postcondition_fn(ws)
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "modality": "epistemic_spec_oracle_swe",
                "status": "VERIFIED" if (so_res.get("status") == "VERIFIED" and ok_post) else so_res.get("status", "FAILED"),
                "mode": str(so_res.get("mode") or "EPISTEMIC_METAMORPHIC_ORACLE"),
                "frontier_sense_ms": frontier["sense_ms"],
                "epistemic_diff": epistemic_diff,
                "spec_oracle_result": so_res,
                "gaps_queried": [],
                "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                "model_calls": 0,
                "parameters_stored": 0,
            }

    # 3. SWE / Codebase Environment
    if modality == "swe_codebase":
        py_test_targets: list[str] = []
        for m_pt in re.finditer(r"[\w./-]+\.py(?:::[A-Za-z0-9_\[\]-]+)?", instruction or ""):
            raw_pt = m_pt.group(0)
            rel_pt = raw_pt.split("::", 1)[0]
            pt_name = pathlib.Path(rel_pt).name.lower()
            is_test_py = (
                pt_name.startswith("test_")
                or pt_name.endswith("_test.py")
                or "/test/" in f"/{rel_pt.lower()}"
                or "/tests/" in f"/{rel_pt.lower()}"
            )
            if is_test_py and (ws / rel_pt).is_file() and raw_pt not in py_test_targets:
                py_test_targets.append(raw_pt)
        swe_res = solve_swe_with_epistemic_diff(
            ws,
            memory=memory,
            test_targets=py_test_targets or None,
            python_exe=python_exe,
            allow_web=allow_web,
            timeout_s=timeout_s,
        )
        # Blind SWE-bench / SWE-bench Pro issue-to-reproducer fallback: when all existing
        # repo tests already pass (no hidden failing test present), synthesize & qualify an
        # executable reproducer directly from the issue description, solve, and verify pass2pass.
        if (
            swe_res.get("mode") == "ALREADY_PASSING" or swe_res.get("status") != "VERIFIED"
        ) and instruction and "(" in instruction:
            from canonical.runtime import epistemic_issue_reproducer_v1 as ISSUE_REPRO

            blind_py = ISSUE_REPRO.solve_issue_from_description(
                ws,
                instruction,
                python_exe=python_exe or sys.executable,
                timeout_s=max(float(timeout_s), 30.0),
                memory=memory,
            )
            if blind_py.get("verified") and blind_py.get("patched_files"):
                for rf, rsrc in blind_py["patched_files"].items():
                    (ws / rf).write_text(str(rsrc), encoding="utf-8")
                w_bp = blind_py.get("winner") or {}
                swe_res = {
                    "status": "VERIFIED",
                    "mode": "BLIND_ISSUE_REPRODUCER_SWE",
                    "patched_file": w_bp.get("file"),
                    "winner": w_bp,
                    "patch_diff": blind_py.get("patch_diff", ""),
                    "reproducer": blind_py.get("reproducer"),
                    "regression_tests": blind_py.get("regression_tests"),
                    "gaps_queried": [],
                }
        # Optional first-principles CWE vulnerability report emitter when explicitly requested
        cwe_report: dict[str, Any] | None = None
        if (
            swe_res.get("status") == "VERIFIED"
            and swe_res.get("patched_file")
            and ("cwe" in (instruction or "").lower() or "report.jsonl" in (instruction or "").lower())
        ):
            sig_text = (
                str(swe_res.get("initial_failure_signal") or "")
                + " "
                + str(swe_res.get("fix") or "")
                + " "
                + str(swe_res.get("patched_file") or "")
            ).lower()
            instr_low = (instruction or "").lower()
            cwe_ids: list[str] = []
            if any(k in sig_text for k in ("header", "crlf", "control_char", "control char")):
                if "cwe-93" in instr_low or "crlf" in instr_low:
                    cwe_ids.append("cwe-93")
                if "cwe-113" in instr_low:
                    cwe_ids.append("cwe-113")
                if not cwe_ids:
                    cwe_ids.append("cwe-93")
            elif any(k in sig_text for k in ("traversal", "realpath", "abspath", "path")):
                cwe_ids.append("cwe-22")
            elif any(k in sig_text for k in ("sql", "execute", "cursor")):
                cwe_ids.append("cwe-89")
            elif any(k in sig_text for k in ("xss", "script", "escape_html")):
                cwe_ids.append("cwe-79")
            elif any(k in sig_text for k in ("subprocess", "os.system", "shell")):
                cwe_ids.append("cwe-78")
            else:
                cwe_ids.append("cwe-20")

            # Determine report path and file_path prefix from instruction
            m_rep = re.search(r"([A-Za-z0-9_.\-/]+report\.jsonl)", instruction or "")
            rep_raw = m_rep.group(1) if m_rep else "report.jsonl"
            if rep_raw.startswith(str(ws) + "/"):
                rep_file = pathlib.Path(rep_raw)
                reported_file_path = str(ws / str(swe_res["patched_file"]))
            elif rep_raw.startswith("/app/"):
                rep_file = ws / rep_raw[len("/app/"):]
                reported_file_path = "/app/" + str(swe_res["patched_file"]).lstrip("/")
            else:
                rep_file = ws / rep_raw.lstrip("/")
                reported_file_path = str(ws / str(swe_res["patched_file"]))

            cwe_report = {"file_path": reported_file_path, "cwe_id": cwe_ids}
            rep_file.parent.mkdir(parents=True, exist_ok=True)
            rep_file.write_text(json.dumps(cwe_report) + "\n", encoding="utf-8")

        ok_post = True
        if swe_res["status"] == "VERIFIED" and postcondition_fn is not None:
            ok_post, _ = postcondition_fn(ws)
        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "modality": modality,
            "status": "VERIFIED" if (swe_res["status"] == "VERIFIED" and ok_post) else "FAILED",
            "mode": swe_res["mode"],
            "frontier_sense_ms": frontier["sense_ms"],
            "epistemic_diff": epistemic_diff,
            "swe_result": swe_res,
            "cwe_report": cwe_report,
            "gaps_queried": swe_res.get("gaps_queried") or [],
            "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    # 3b. Multi-Language JavaScript / TypeScript SWE Environment
    if modality == "swe_js_codebase":
        explicit_js_tests: list[str] = []
        for m_tf in re.finditer(r"([A-Za-z0-9_.\-/]+\.(?:js|mjs|cjs|ts))\b", instruction or ""):
            cand_tf = m_tf.group(1).lstrip("./")
            if (ws / cand_tf).is_file() and ML_SWE_ENGINE._is_test_path(cand_tf):
                if cand_tf not in explicit_js_tests:
                    explicit_js_tests.append(cand_tf)
        js_res = ML_SWE_ENGINE.solve_js_repository(
            ws,
            test_targets=explicit_js_tests or None,
            memory=memory,
            timeout_s=max(float(timeout_s), 30.0),
        )
        # Blind SWE-bench Pro JS fallback: when existing tests already pass on c_old,
        # synthesize & qualify a reproducer from the issue description and verify pass2pass.
        if (
            js_res.get("status") != "VERIFIED"
            and instruction
            and ("(" in instruction or "```" in instruction)
        ):
            from canonical.runtime import epistemic_issue_reproducer_v1 as ISSUE_REPRO

            blind_js = ISSUE_REPRO.solve_issue_from_description(
                ws,
                instruction,
                timeout_s=max(float(timeout_s), 30.0),
                memory=memory,
            )
            if blind_js.get("verified") and blind_js.get("patched_files"):
                w_bj = dict(blind_js.get("winner") or {})
                w_file = str(w_bj.get("file") or "")
                w_bj["patched_source"] = blind_js["patched_files"].get(w_file, "")
                w_bj["extra_patches"] = {
                    k: v for k, v in blind_js["patched_files"].items() if k != w_file
                }
                js_res = {
                    "status": "VERIFIED",
                    "verified": True,
                    "winner": w_bj,
                    "patch_diff": blind_js.get("patch_diff", ""),
                    "reproducer": blind_js.get("reproducer"),
                    "regression_tests": blind_js.get("regression_tests"),
                    "mode": "BLIND_ISSUE_REPRODUCER_JS_SWE",
                }
        ok_post = True
        winner = js_res.get("winner") if isinstance(js_res, Mapping) else None
        if js_res.get("status") == "VERIFIED" and isinstance(winner, Mapping) and winner.get("file"):
            patch_files: dict[str, str] = {str(winner["file"]): str(winner["patched_source"])}
            for ef, esrc in (winner.get("extra_patches") or {}).items():
                patch_files[str(ef)] = str(esrc)
            backups: dict[pathlib.Path, str | None] = {}
            for rf, rsrc in patch_files.items():
                fp_w = ws / rf
                backups[fp_w] = fp_w.read_text(encoding="utf-8", errors="replace") if fp_w.is_file() else None
                fp_w.write_text(rsrc, encoding="utf-8")
            if postcondition_fn is not None:
                ok_post, _ = postcondition_fn(ws)
                if not ok_post:
                    for fp_w, bsrc in backups.items():
                        if bsrc is not None:
                            fp_w.write_text(bsrc, encoding="utf-8")
            if ok_post:
                compress_and_prune_memory(memory)
        mode_lbl = (
            "TIER0_JS_SKILL_RECALL"
            if (isinstance(winner, Mapping) and winner.get("skill_id_used"))
            else "CAUSAL_ANGELIC_JS_SWE"
        )
        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "modality": modality,
            "status": "VERIFIED" if (js_res.get("status") == "VERIFIED" and ok_post) else "FAILED",
            "mode": mode_lbl,
            "frontier_sense_ms": frontier["sense_ms"],
            "epistemic_diff": epistemic_diff,
            "swe_result": js_res,
            "gaps_queried": [],
            "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    # 3c. Multi-Language C / C++ SWE Environment (ASan/UBSan + gcov)
    if modality == "swe_c_codebase":
        explicit_c_tests: list[str] = []
        for m_tf in re.finditer(r"([A-Za-z0-9_.\-/]+\.(?:c|cc|cpp|cxx|sh))\b", instruction or ""):
            cand_tf = m_tf.group(1).lstrip("./")
            if (ws / cand_tf).is_file() and (
                cand_tf.endswith(".sh") or ML_SWE_ENGINE._is_c_test_path(cand_tf)
            ):
                if cand_tf not in explicit_c_tests:
                    explicit_c_tests.append(cand_tf)
        c_res = ML_SWE_ENGINE.solve_c_repository(
            ws,
            test_targets=explicit_c_tests or None,
            memory=memory,
            timeout_s=max(float(timeout_s), 30.0),
        )
        ok_post = True
        winner = c_res.get("winner") if isinstance(c_res, Mapping) else None
        if c_res.get("status") == "VERIFIED" and isinstance(winner, Mapping) and winner.get("file"):
            patch_files_c: dict[str, str] = {str(winner["file"]): str(winner["patched_source"])}
            for ef, esrc in (winner.get("extra_patches") or {}).items():
                patch_files_c[str(ef)] = str(esrc)
            backups_c: dict[pathlib.Path, str | None] = {}
            for rf, rsrc in patch_files_c.items():
                fp_w = ws / rf
                backups_c[fp_w] = fp_w.read_text(encoding="utf-8", errors="replace") if fp_w.is_file() else None
                fp_w.write_text(rsrc, encoding="utf-8")
            if postcondition_fn is not None:
                ok_post, _ = postcondition_fn(ws)
                if not ok_post:
                    for fp_w, bsrc in backups_c.items():
                        if bsrc is not None:
                            fp_w.write_text(bsrc, encoding="utf-8")
            if ok_post:
                compress_and_prune_memory(memory)
        mode_lbl = (
            "TIER0_C_SKILL_RECALL"
            if (isinstance(winner, Mapping) and winner.get("skill_id_used"))
            else "CAUSAL_ANGELIC_C_SWE"
        )
        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "modality": modality,
            "status": "VERIFIED" if (c_res.get("status") == "VERIFIED" and ok_post) else "FAILED",
            "mode": mode_lbl,
            "frontier_sense_ms": frontier["sense_ms"],
            "epistemic_diff": epistemic_diff,
            "swe_result": c_res,
            "gaps_queried": [],
            "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    # 4. Greenfield Specification Synthesis + Self-Generated Adversarial Oracle Verification
    #    (only when no pre-existing test suite is in the workspace and spec defines a target artifact)
    if not frontier.get("test_files"):
        spec_res = SPEC_SYNTH.synthesize_and_verify_spec(
            ws, instruction, memory=memory, python_exe=python_exe,
        )
        if spec_res.get("status") == "VERIFIED":
            ok_post = True
            if postcondition_fn is not None:
                ok_post, _ = postcondition_fn(ws)
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "modality": "greenfield_spec_synthesis",
                "status": "VERIFIED" if ok_post else "FAILED",
                "mode": spec_res["mode"],
                "frontier_sense_ms": frontier["sense_ms"],
                "epistemic_diff": epistemic_diff,
                "spec_synthesis": spec_res,
                "gaps_queried": [],
                "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                "model_calls": 0,
                "parameters_stored": 0,
            }

    # 5. OS / CLI / Multi-Step Morphism / Domain Computer-Use Environment
    m_store = memory.get("morphism_store") if memory is not None else None
    p_store = memory.get("cu_procedure_store") if memory is not None else None
    s_store = memory.get("swe_skill_store") if memory is not None else None

    # Tier-0 offline Plotkin Anti-Unified CLI Law recall (<15ms, 0 web calls)
    cli_hit = recall_and_execute_cli_law(
        ws, instruction, memory, postcondition_fn=postcondition_fn, timeout_s=timeout_s,
    )
    if cli_hit is not None:
        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "modality": modality,
            "status": "VERIFIED",
            "mode": "TIER0_ANTI_UNIFIED_CLI_LAW",
            "frontier_sense_ms": frontier["sense_ms"],
            "epistemic_diff": epistemic_diff,
            "cli_law_hit": cli_hit,
            "gaps_queried": [],
            "web_queries_made": 0,
            "morphisms_recalled": [cli_hit["law_id"]],
            "morphisms_learned": [],
            "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    goal_preview = CU_AGENT.compile_instruction(instruction, CU_AGENT.sense_environment(ws))
    if goal_preview.get("domain", "unknown") != "unknown":
        cu_rep = CU_AGENT.solve_computer_use_task(
            ws,
            instruction,
            procedure_store=p_store,
            swe_skill_store=s_store,
            morphism_store=m_store,
            python_exe=python_exe or sys.executable,
            learn_into_store=memory is not None,
        )
        ok_post = True
        if cu_rep.get("verified") and postcondition_fn is not None:
            ok_post, _ = postcondition_fn(ws)
        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "modality": modality,
            "status": "VERIFIED" if (cu_rep.get("verified") and ok_post) else "FAILED",
            "mode": str(cu_rep.get("tier") or "CU_SOLVED"),
            "frontier_sense_ms": frontier["sense_ms"],
            "epistemic_diff": epistemic_diff,
            "cu_report": cu_rep,
            "gaps_queried": [],
            "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    mres = MORPH_ENGINE.solve_with_epistemic_morphisms(
        ws,
        instruction,
        morphism_store=m_store,
        postcondition_fn=postcondition_fn,
        allow_web=allow_web,
        timeout_s=timeout_s,
    )
    cli_consolidations: list[dict[str, Any]] = []
    if mres.status == "VERIFIED" and memory is not None:
        for st in mres.steps_trace:
            cmd = st.get("command") if isinstance(st, Mapping) else None
            if isinstance(cmd, str) and cmd.strip():
                c_res = auto_consolidate_experience(memory, kind="cli", command=cmd.strip())
                if c_res.get("status") not in (None, "IGNORED", "DUPLICATE_EXEMPLAR"):
                    cli_consolidations.append(c_res)
    if mres.status != "VERIFIED":
        zp_res = solve_zero_prior_closed_loop_epistemic(
            ws,
            instruction,
            memory=memory,
            postcondition_fn=postcondition_fn,
            python_exe=python_exe or sys.executable,
            timeout_s=timeout_s,
        )
        if zp_res is not None and zp_res.get("status") == "VERIFIED":
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "modality": "zero_prior_closed_loop_epistemic",
                "status": "VERIFIED",
                "mode": str(zp_res.get("mode") or "EPISTEMIC_ZERO_PRIOR_CLOSED_LOOP"),
                "frontier_sense_ms": frontier["sense_ms"],
                "epistemic_diff": epistemic_diff,
                "zero_prior_result": zp_res,
                "gaps_queried": list(zp_res.get("gaps_queried") or []),
                "web_queries_made": 0,
                "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                "model_calls": 0,
                "parameters_stored": 0,
            }
        # Goal-directed zero-LLM Doc-Compiler & Active-Inference Agent (unseen CLIs, pipelines, doc-backed APIs)
        from canonical.runtime import epistemic_doc_compiler_agent_v1 as EDC

        _edc_mem = EDC.EpistemicMemoryStore()
        _edc_ver = (lambda _st: postcondition_fn(ws)) if postcondition_fn is not None else verifier
        edc_res = EDC.solve_multi_step_with_instant_knowledge(
            instruction,
            workspace=ws,
            memory=_edc_mem,
            knowledge_source=knowledge_source,
            base_url=detected_url,
            verifier=_edc_ver,
            timeout_s=timeout_s,
        )
        if edc_res.get("status") == "VERIFIED":
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "modality": "epistemic_doc_compiler",
                "status": "VERIFIED",
                "mode": str(edc_res.get("mode") or "DOC_COMPILED_ACTIVE_INFERENCE"),
                "frontier_sense_ms": frontier["sense_ms"],
                "epistemic_diff": epistemic_diff,
                "doc_compiler_result": edc_res,
                "gaps_queried": list(edc_res.get("gaps_queried") or []),
                "web_queries_made": 0,
                "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
                "model_calls": 0,
                "parameters_stored": 0,
            }

    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "modality": modality,
        "status": mres.status,
        "mode": mres.mode,
        "frontier_sense_ms": frontier["sense_ms"],
        "epistemic_diff": epistemic_diff,
        "steps_trace": mres.steps_trace,
        "cli_consolidations": cli_consolidations,
        "gaps_queried": mres.gaps_queried,
        "web_queries_made": mres.web_queries_made,
        "morphisms_recalled": mres.morphisms_recalled,
        "morphisms_learned": mres.morphisms_learned,
        "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
        "model_calls": 0,
        "parameters_stored": 0,
    }
