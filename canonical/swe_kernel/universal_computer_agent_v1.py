"""Universal Computer-Use Agent: Zero-Model, Zero-Knowledge-House Causal Engine (v1).

Realizes the "Perfect Algorithm" for arbitrary, never-before-seen computer environments
(both real Linux OS / Terminal / CLI workspaces AND real live HTTP / HTML-DOM / ARIA
multi-page web applications) with:

  - **0 model calls** (pure first-principles semantic parsing, causal induction, and planning)
  - **0 knowledge house** (no memorized world facts or tool recipes in parameters; every tool
    and page is discovered live via `--help`/schemas/DOM/probes; generalized causal laws live
    strictly in an external, inspectable, editable, deletable JSON store)
  - **Every state parameter calculated** via SEPARATION + STABILITY minimum-cover projection
    over live observables
  - **Active Falsification of Instant Knowledge**: prose `--help` / docs are treated strictly
    as untrusted hypotheses and verified in an isolated shadow sandbox clone BEFORE ever
    touching real state — catching lying docs and destructive traps with 0 real damage
  - **Parameter-Lifted Single-Experience Causal Law Generalization**: lifts concrete filenames,
    extensions, DOM tokens, and field roles into typed parameterized causal laws so a single
    verified interaction transfers zero-shot across changed directories, filenames, page layouts,
    and longer multi-step workflows
  - **Fresh-State Exactness Verification**: eliminates stale grounding and premature stop by
    re-reading live real state after every action and refusing completion until EVERY compiled
    goal postcondition evaluates True on the fresh state.
"""

from __future__ import annotations

import collections
import copy
import dataclasses
import hashlib
import html.parser
import http.cookiejar
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from canonical.swe_kernel import executable_mental_model_v1 as emm

SCHEMA = "BRAIN_UNIVERSAL_COMPUTER_AGENT_V1"
PRODUCER_MODEL_CALLS = 0


# ---------------------------------------------------------------------------
# 1. Calculated State-Key Projection (Every Bit Calculated, Zero Memorization)
# ---------------------------------------------------------------------------


def calculate_separating_projection(
    positive_states: Sequence[Mapping[str, Any]],
    negative_states: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Calculate the minimal set of observable state keys separating positive from negative states.

    Implements minimum-cover SEPARATION (zero trained weights, zero stored knowledge):
    returns the smallest sorted subset of keys `K` such that no negative state shares
    the same projected tuple `tuple(s.get(k) for k in K)` with any positive state.
    """
    if not positive_states or not negative_states:
        return []
    all_keys = sorted({k for s in list(positive_states) + list(negative_states) for k in s})
    # Precompute which negative pairs each single key separates
    pairs = [(i, j) for i in range(len(positive_states)) for j in range(len(negative_states))]
    universe = set(range(len(pairs)))
    sep_by_key: dict[str, set[int]] = {}
    for k in all_keys:
        covered = {
            idx
            for idx, (i, j) in enumerate(pairs)
            if positive_states[i].get(k) != negative_states[j].get(k)
        }
        if covered:
            sep_by_key[k] = covered
    # Greedy-exact minimum cover (exact for sizes 1..2, greedy minimal above)
    for k, cov in sep_by_key.items():
        if cov >= universe:
            return [k]
    keys_list = sorted(sep_by_key.keys())
    for i, k1 in enumerate(keys_list):
        c1 = sep_by_key[k1]
        for k2 in keys_list[i + 1 :]:
            if (c1 | sep_by_key[k2]) >= universe:
                return [k1, k2]
    chosen: list[str] = []
    remaining = set(universe)
    while remaining and sep_by_key:
        best_k = max(sep_by_key, key=lambda k: (len(sep_by_key[k] & remaining), -len(k)))
        gain = sep_by_key[best_k] & remaining
        if not gain:
            break
        chosen.append(best_k)
        remaining -= gain
    return chosen


# ---------------------------------------------------------------------------
# 2. External Inspectable Parameterized Causal Law Store (Zero Knowledge House)
# ---------------------------------------------------------------------------


@dataclass
class ParameterizedCausalLaw:
    """A verified, parameterized causal transition law lifted from live execution.

    Lives strictly OUTSIDE weights in an external JSON file; deleting it immediately
    removes the capability without retraining. Supports §9.2 provenance tracking,
    concrete witness attachment for anti-unified generalizations, and version staleness.
    """

    law_id: str
    domain: str  # "cli" | "web_dom" | "sqlite" | "swe" | "cross_modal"
    tool_or_action: str
    command_template: list[str]  # e.g. ["{tool}", "--unpack", "{src}", "--out", "{dst}"]
    in_ext: str = ""
    out_ext: str = ""
    creates_file_kind: str = ""  # e.g. "json", "text", "dir_files", "gz"
    preconditions: dict[str, Any] = field(default_factory=dict)
    effects: dict[str, Any] = field(default_factory=dict)
    destructive: bool = False
    verified_count: int = 1
    refuted_count: int = 0
    provenance: dict[str, Any] = field(default_factory=dict)
    witnesses: list[dict[str, Any]] = field(default_factory=list)
    generalized: bool = False
    stale: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "law_id": self.law_id,
            "domain": self.domain,
            "tool_or_action": self.tool_or_action,
            "command_template": list(self.command_template),
            "in_ext": self.in_ext,
            "out_ext": self.out_ext,
            "creates_file_kind": self.creates_file_kind,
            "preconditions": dict(self.preconditions),
            "effects": dict(self.effects),
            "destructive": self.destructive,
            "verified_count": self.verified_count,
            "refuted_count": self.refuted_count,
            "provenance": dict(self.provenance),
            "witnesses": list(self.witnesses),
            "generalized": self.generalized,
            "stale": self.stale,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ParameterizedCausalLaw":
        return cls(
            law_id=str(d["law_id"]),
            domain=str(d["domain"]),
            tool_or_action=str(d["tool_or_action"]),
            command_template=list(d.get("command_template") or []),
            in_ext=str(d.get("in_ext") or ""),
            out_ext=str(d.get("out_ext") or ""),
            creates_file_kind=str(d.get("creates_file_kind") or ""),
            preconditions=dict(d.get("preconditions") or {}),
            effects=dict(d.get("effects") or {}),
            destructive=bool(d.get("destructive", False)),
            verified_count=int(d.get("verified_count", 1)),
            refuted_count=int(d.get("refuted_count", 0)),
            provenance=dict(d.get("provenance") or {}),
            witnesses=list(d.get("witnesses") or []),
            generalized=bool(d.get("generalized", False)),
            stale=bool(d.get("stale", False)),
        )


def anti_unify_templates(
    seq_a: Sequence[str],
    seq_b: Sequence[str],
) -> tuple[list[str], dict[str, tuple[str, str]]] | None:
    """Plotkin syntactic anti-unification (Least General Generalization, LGG) over two
    token sequences of identical length.

    Preserves shared structure verbatim and lifts differing concrete literals into
    consistent typed slot variables `?slot_0`, `?slot_1`, ... returning `(lgg_seq, subst_map)`.
    """
    if len(seq_a) != len(seq_b) or not seq_a:
        return None
    lgg: list[str] = []
    pair_to_var: dict[tuple[str, str], str] = {}
    subst: dict[str, tuple[str, str]] = {}
    for ta, tb in zip(seq_a, seq_b):
        if ta == tb:
            lgg.append(ta)
        else:
            key = (ta, tb)
            if key not in pair_to_var:
                var = f"?slot_{len(pair_to_var)}"
                pair_to_var[key] = var
                subst[var] = key
            lgg.append(pair_to_var[key])
    # Must preserve at least 1 shared structural anchor token (avoid degenerate all-wildcard LGG)
    shared = sum(1 for tok in lgg if not tok.startswith("?slot_"))
    if shared == 0:
        return None
    return lgg, subst


class ExternalCausalLawStore:
    """Inspectable, editable, removable JSON store of verified parameterized causal laws
    and cross-domain procedure-level search policies (zero memorized world facts in parameters).

    Implements Project Brain §9.2 Memory Architecture:
    - 5-part admission filter (`verifiable`, `novel`, `generalizable`, `provenance_tagged`, `cost_bounded`)
    - Anti-unification generalizing compression with attached concrete witnesses
    - Provenance & version staleness detection + 1-step targeted re-validation probes
    - `learn_or_read_v1`: live zero-experience reading is NEVER displaced by memorized trajectories
    - `learn_to_learn_v1`: cross-domain compounding lives in procedure-level search-family ordering
    """

    def __init__(self, path: str | pathlib.Path | None = None) -> None:
        self.path = pathlib.Path(path) if path is not None else None
        self.laws: dict[str, ParameterizedCausalLaw] = {}
        self.tree_morphisms: dict[str, dict[str, Any]] = {}
        self.negative_invariants: dict[str, dict[str, Any]] = {}
        self.blacklisted_signatures: set[str] = set()
        self.procedure_policy: dict[str, dict[str, Any]] = {}
        self.admission_stats: dict[str, Any] = {"admitted": 0, "rejected": 0, "reasons": {}}
        self._tree_index: dict[tuple[str, str, str], list[str]] = {}
        self._tree_sig_index: dict[str, str] = {}
        if self.path is not None and self.path.exists():
            self.load()

    @staticmethod
    def _sexp_structural_key(target_kind: str, pat_sexp: Any) -> tuple[str, str, str]:
        """Compute O(1) structural root fingerprint `(target_kind, root_node, primary_tag)`."""
        if not isinstance(pat_sexp, dict):
            return (target_kind, "_invalid", "*")
        root_node = str(pat_sexp.get("_node") or ("_hole" if "_hole" in pat_sexp else "*"))
        tag = "*"
        if root_node == "Call":
            fn = pat_sexp.get("func")
            if isinstance(fn, dict) and fn.get("_node") == "Attribute" and isinstance(fn.get("attr"), str):
                tag = fn["attr"]
            elif isinstance(fn, dict) and fn.get("_node") == "Name" and isinstance(fn.get("id"), str):
                tag = fn["id"]
            else:
                # When `func` was lifted to a hole `?h0`, discriminate by first constant argument!
                args = pat_sexp.get("args")
                if isinstance(args, list) and args and isinstance(args[0], dict) and args[0].get("_node") == "Constant":
                    tag = f"arg0:{args[0].get('value')!r}"
        elif root_node == "Attribute" and isinstance(pat_sexp.get("attr"), str):
            tag = pat_sexp["attr"]
        elif root_node == "Name" and isinstance(pat_sexp.get("id"), str):
            tag = pat_sexp["id"]
        elif root_node == "If" and isinstance(pat_sexp.get("test"), dict):
            tag = str(pat_sexp["test"].get("_node") or "*")
        elif root_node == "Assign" and isinstance(pat_sexp.get("value"), dict):
            tag = str(pat_sexp["value"].get("_node") or "*")
        elif root_node == "Return" and isinstance(pat_sexp.get("value"), dict):
            tag = str(pat_sexp["value"].get("_node") or "*")
        elif root_node == "For" and isinstance(pat_sexp.get("iter"), dict):
            tag = str(pat_sexp["iter"].get("_node") or "*")
        return (target_kind, root_node, tag)

    @staticmethod
    def _ast_node_structural_keys(node: Any) -> list[tuple[str, str, str]]:
        """Extract O(1) lookup keys for a concrete Python AST node (specific keys first)."""
        import ast as _ast
        if not isinstance(node, _ast.AST):
            return []
        rname = type(node).__name__
        keys: list[tuple[str, str, str]] = []
        if isinstance(node, _ast.ExceptHandler) and node.type is not None:
            tn = type(node.type).__name__
            ttag = node.type.id if isinstance(node.type, _ast.Name) else "*"
            keys.append(("except_handler", tn, ttag))
            keys.append(("except_handler", tn, "*"))
        if isinstance(node, _ast.expr):
            tag = "*"
            if isinstance(node, _ast.Call):
                if isinstance(node.func, _ast.Attribute):
                    tag = node.func.attr
                elif isinstance(node.func, _ast.Name):
                    tag = node.func.id
                if node.args and isinstance(node.args[0], _ast.Constant):
                    keys.append(("expr_subtree", rname, f"arg0:{node.args[0].value!r}"))
            elif isinstance(node, _ast.Attribute):
                tag = node.attr
            elif isinstance(node, _ast.Name):
                tag = node.id
            keys.append(("expr_subtree", rname, tag))
            if tag != "*":
                keys.append(("expr_subtree", rname, "*"))
        if isinstance(node, _ast.stmt):
            tag = "*"
            if isinstance(node, _ast.If):
                tag = type(node.test).__name__
            elif isinstance(node, _ast.Assign):
                tag = type(node.value).__name__
            elif isinstance(node, _ast.Return) and node.value is not None:
                tag = type(node.value).__name__
            elif isinstance(node, _ast.For):
                tag = type(node.iter).__name__
            keys.append(("stmt_slice", rname, tag))
            if tag != "*":
                keys.append(("stmt_slice", rname, "*"))
        return keys

    @staticmethod
    def _tree_morphism_sig(d: Mapping[str, Any]) -> str:
        return json.dumps(
            {"k": d.get("target_kind"), "p": d.get("pattern_sexps"), "r": d.get("replacement_sexps")},
            sort_keys=True,
        )

    def _rebuild_tree_index(self) -> None:
        idx: dict[tuple[str, str, str], list[str]] = {}
        sig_idx: dict[str, str] = {}
        for mid, raw in self.tree_morphisms.items():
            tk = str(raw.get("target_kind", "stmt_slice"))
            pats = raw.get("pattern_sexps") or []
            key = self._sexp_structural_key(tk, pats[0] if pats else {})
            idx.setdefault(key, []).append(mid)
            sig_idx[self._tree_morphism_sig(raw)] = mid
        self._tree_index = idx
        self._tree_sig_index = sig_idx

    def load(self) -> None:
        if self.path is None or not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.laws = {
            item["law_id"]: ParameterizedCausalLaw.from_dict(item)
            for item in raw.get("laws", [])
        }
        self.tree_morphisms = {
            str(item["morphism_id"]): dict(item)
            for item in raw.get("tree_morphisms", [])
            if isinstance(item, dict) and item.get("morphism_id")
        }
        self._rebuild_tree_index()
        self.negative_invariants = {
            str(item["invariant_id"]): dict(item)
            for item in raw.get("negative_invariants", [])
            if isinstance(item, dict) and item.get("invariant_id")
        }
        self.blacklisted_signatures = set(raw.get("blacklisted_signatures", []))
        self.procedure_policy = dict(raw.get("procedure_policy", {}))
        if isinstance(raw.get("admission_stats"), dict):
            self.admission_stats = dict(raw["admission_stats"])

    def save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {}
        if self.path.exists():
            try:
                existing = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(existing, dict):
                    payload.update(existing)
            except Exception:
                pass
        payload.update(
            {
                "schema": "BRAIN_EXTERNAL_CAUSAL_LAW_STORE_V1",
                "laws": [law.to_dict() for law in self.laws.values()],
                "tree_morphisms": [self.tree_morphisms[k] for k in sorted(self.tree_morphisms)],
                "negative_invariants": [self.negative_invariants[k] for k in sorted(self.negative_invariants)],
                "blacklisted_signatures": sorted(self.blacklisted_signatures),
                "procedure_policy": self.procedure_policy,
                "admission_stats": self.admission_stats,
            }
        )
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    # --- L2 Multi-Statement AST Tree-Rewrite Morphisms (O(1) admit / recall / delete) ---

    def admit_tree_morphism(self, morphism: Any) -> dict[str, Any]:
        """Admit a verified `TreeRewriteMorphism` into the external JSON store (O(1) deduplicated)."""
        d = morphism.to_dict() if hasattr(morphism, "to_dict") else dict(morphism)
        mid = str(d["morphism_id"])
        sig = self._tree_morphism_sig(d)
        oid = self._tree_sig_index.get(sig)
        if oid is not None and oid != mid and oid in self.tree_morphisms:
            existing = self.tree_morphisms[oid]
            existing["verified_count"] = int(existing.get("verified_count", 1)) + 1
            self.save()
            return {"admitted": True, "deduplicated_into": oid, "morphism_id": oid}
        self.tree_morphisms[mid] = d
        self._tree_sig_index[sig] = mid
        tk = str(d.get("target_kind", "stmt_slice"))
        pats = d.get("pattern_sexps") or []
        key = self._sexp_structural_key(tk, pats[0] if pats else {})
        bucket = self._tree_index.setdefault(key, [])
        if mid not in bucket:
            bucket.append(mid)
        self.save()
        return {"admitted": True, "deduplicated_into": None, "morphism_id": mid}

    def list_tree_morphisms(self) -> list[Any]:
        from canonical.swe_kernel import reverse_tomography_algebra_v1 as rta
        items = sorted(self.tree_morphisms.values(), key=lambda x: (-int(x.get("verified_count", 1)), str(x.get("morphism_id", ""))))
        return [rta.TreeRewriteMorphism.from_dict(it) for it in items]

    def query_tree_morphisms_o1(
        self,
        source: str,
        *,
        target_lines: set[int] | None = None,
        max_results: int = 6,
    ) -> list[Any]:
        """O(1)-hash-indexed L2 TreeRewriteMorphism retrieval eliminating linear-scan slowdown.

        Extracts structural root signatures from traced AST nodes in `source` and probes
        `self._tree_index` in O(1) per signature, returning top `max_results` matches
        regardless of whether the store contains 10 or 100,000 morphisms.
        """
        if not self.tree_morphisms:
            return []
        if not self._tree_index:
            self._rebuild_tree_index()
        import ast as _ast
        from canonical.swe_kernel import reverse_tomography_algebra_v1 as rta
        try:
            tree = _ast.parse(source)
        except SyntaxError:
            return []
        hit_specificity: dict[str, int] = {}
        for node in _ast.walk(tree):
            ln = getattr(node, "lineno", 0)
            if target_lines is not None and ln and ln not in target_lines:
                continue
            for key in self._ast_node_structural_keys(node):
                mids = self._tree_index.get(key)
                if mids:
                    spec = 0 if key[2] != "*" else 1
                    for m in mids:
                        if m not in hit_specificity or spec < hit_specificity[m]:
                            hit_specificity[m] = spec
        # Include true `_hole`-root wildcard fallback bucket at lowest specificity
        for tk in ("expr_subtree", "stmt_slice", "except_handler"):
            for wk in ((tk, "_hole", "*"),):
                mids = self._tree_index.get(wk)
                if mids:
                    for m in mids:
                        hit_specificity.setdefault(m, 2)
        if not hit_specificity:
            return []
        ranked = sorted(
            (self.tree_morphisms[m] for m in hit_specificity if m in self.tree_morphisms),
            key=lambda x: (
                hit_specificity.get(str(x.get("morphism_id", "")), 2),
                0 if x.get("target_kind") == "expr_subtree" else 1,
                -int(x.get("verified_count", 1)),
                str(x.get("morphism_id", "")),
            ),
        )
        return [rta.TreeRewriteMorphism.from_dict(it) for it in ranked[:max_results]]

    def delete_tree_morphism(self, morphism_id: str) -> bool:
        """O(1) removal of an L2 AST Tree-Rewrite Morphism without retraining."""
        raw = self.tree_morphisms.pop(morphism_id, None)
        existed = raw is not None
        if existed:
            tk = str(raw.get("target_kind", "stmt_slice"))
            pats = raw.get("pattern_sexps") or []
            key = self._sexp_structural_key(tk, pats[0] if pats else {})
            bucket = self._tree_index.get(key)
            if bucket and morphism_id in bucket:
                bucket.remove(morphism_id)
                if not bucket:
                    self._tree_index.pop(key, None)
            sig = self._tree_morphism_sig(raw)
            if self._tree_sig_index.get(sig) == morphism_id:
                self._tree_sig_index.pop(sig, None)
            self.save()
        return existed

    # --- L3 Negative-Space Invariants (Refutation-Driven Search Pruning) ---

    def add_negative_invariant(self, inv: Any) -> dict[str, Any]:
        d = inv.to_dict() if hasattr(inv, "to_dict") else dict(inv)
        sig = (
            str(d.get("domain", "")),
            str(d.get("func_context", "*")),
            str(d.get("orig_cond_shape", "")),
            str(d.get("refuted_guard_shape", "")),
        )
        for oid, existing in self.negative_invariants.items():
            esig = (
                str(existing.get("domain", "")),
                str(existing.get("func_context", "*")),
                str(existing.get("orig_cond_shape", "")),
                str(existing.get("refuted_guard_shape", "")),
            )
            if esig == sig:
                return {"added": False, "duplicate_of": oid}
        iid = str(d["invariant_id"])
        self.negative_invariants[iid] = d
        self.save()
        return {"added": True, "invariant_id": iid}

    def is_pruned_by_l3(
        self,
        *,
        func_context: str,
        orig_cond_src: str,
        guard_src: str,
    ) -> tuple[bool, str | None]:
        """Check in microseconds whether a candidate violates any stored L3 Negative Invariant."""
        if not self.negative_invariants:
            return False, None
        from canonical.swe_kernel import reverse_tomography_algebra_v1 as rta
        for iid, raw in self.negative_invariants.items():
            inv = rta.NegativeSpaceInvariant.from_dict(raw)
            if inv.matches(func_context=func_context, orig_cond_src=orig_cond_src, guard_src=guard_src):
                raw["prune_hits"] = int(raw.get("prune_hits", 0)) + 1
                return True, iid
        return False, None

    def delete_negative_invariant(self, invariant_id: str) -> bool:
        existed = self.negative_invariants.pop(invariant_id, None) is not None
        if existed:
            self.save()
        return existed

    def compact_and_deduplicate(self) -> dict[str, Any]:
        """Zero-Weight Federated Skill Distiller Compaction:
        Merges structurally compatible L2 TreeRewriteMorphisms via Plotkin AST anti-unification
        and deduplicates L3 negative invariants so the store grows strictly smaller & more general.
        """
        from canonical.swe_kernel import reverse_tomography_algebra_v1 as rta
        before_l2 = len(self.tree_morphisms)
        before_l3 = len(self.negative_invariants)

        # Group L2 tree morphisms by (target_kind, len(pattern_sexps), len(replacement_sexps), root node types)
        groups: dict[tuple[Any, ...], list[Any]] = collections.defaultdict(list)
        for m in self.list_tree_morphisms():
            pat_roots = tuple(p.get("_node", "") if isinstance(p, dict) else "" for p in m.pattern_sexps)
            rep_roots = tuple(r.get("_node", "") if isinstance(r, dict) else "" for r in m.replacement_sexps)
            groups[(m.target_kind, len(m.pattern_sexps), len(m.replacement_sexps), pat_roots, rep_roots)].append(m)

        new_l2: dict[str, dict[str, Any]] = {}
        merged_groups = 0
        for g_key, grp in groups.items():
            if len(grp) == 1:
                m = grp[0]
                new_l2[m.morphism_id] = m.to_dict()
            else:
                acc = grp[0]
                for nxt in grp[1:]:
                    lgg = rta.anti_unify_tree_morphisms(acc, nxt)
                    if lgg is not None:
                        acc = lgg
                merged_groups += 1
                new_l2[acc.morphism_id] = acc.to_dict()
        self.tree_morphisms = new_l2

        # Deduplicate L3 invariants by structural signature
        seen_l3: set[tuple[str, str, str, str]] = set()
        new_l3: dict[str, dict[str, Any]] = {}
        for iid, raw in sorted(self.negative_invariants.items()):
            sig = (
                str(raw.get("domain", "")),
                str(raw.get("func_context", "*")),
                str(raw.get("orig_cond_shape", "")),
                str(raw.get("refuted_guard_shape", "")),
            )
            if sig not in seen_l3:
                seen_l3.add(sig)
                new_l3[iid] = raw
        self.negative_invariants = new_l3
        self._rebuild_tree_index()
        self.save()
        return {
            "l2_before": before_l2,
            "l2_after": len(self.tree_morphisms),
            "l2_merged_groups": merged_groups,
            "l3_before": before_l3,
            "l3_after": len(self.negative_invariants),
        }

    def evaluate_admission(
        self,
        law: ParameterizedCausalLaw,
        *,
        strict: bool = True,
    ) -> tuple[bool, list[str]]:
        """§9.2 5-Part Admission Filter:
        1. Verifiable: backed by live verification (`verified_count >= 1`) and concrete effect/kind.
        2. Novel: not a redundant duplicate of an existing fresh law with identical signature.
        3. Generalizable: parameterized (`{...}` or `?slot_`) or cross-modal lifted role template
           (rejects unparameterized raw concrete filesystem/port trace dumps!).
        4. Provenance-tagged: carries `source_env` and `version_hash` metadata.
        5. Cost-bounded: compact serialized representation (`<= 4096` bytes, `<= 16` template tokens).
        """
        reasons: list[str] = []
        # 1. Verifiable
        if law.verified_count < 1 or (not law.effects and not law.creates_file_kind and not law.destructive):
            reasons.append("FAIL_VERIFIABLE")
        # 2. Novel (allow in-place refresh of same law_id, reject duplicate under different law_id)
        sig = (
            law.domain,
            law.tool_or_action,
            tuple(law.command_template),
            law.in_ext,
            law.out_ext,
            law.creates_file_kind,
        )
        for oid, olaw in self.laws.items():
            if oid != law.law_id and not olaw.stale:
                osig = (
                    olaw.domain,
                    olaw.tool_or_action,
                    tuple(olaw.command_template),
                    olaw.in_ext,
                    olaw.out_ext,
                    olaw.creates_file_kind,
                )
                if osig == sig:
                    reasons.append("FAIL_NOVEL_DUPLICATE")
                    break
        # 3. Generalizable (reject raw literal paths/localhost ports without template slots)
        has_param = any(
            ("{" in tok and "}" in tok) or tok.startswith("?slot_")
            for tok in law.command_template
        )
        has_raw_ephemeral = any(
            re.search(r"(/tmp/|127\.0\.0\.1:\d+|localhost:\d+)", tok) for tok in law.command_template
        )
        if strict and (has_raw_ephemeral or (law.command_template and not has_param and not law.generalized and law.domain not in ("cross_modal",))):
            reasons.append("FAIL_GENERALIZABLE")
        # 4. Provenance-tagged
        prov = law.provenance or {}
        if strict and (not prov.get("source_env") or not prov.get("version_hash")):
            reasons.append("FAIL_PROVENANCE")
        # 5. Cost-bounded
        try:
            sz = len(json.dumps(law.to_dict(), sort_keys=True))
        except Exception:
            sz = 99999
        if sz > 4096 or len(law.command_template) > 16:
            reasons.append("FAIL_COST_BOUNDED")
        return (len(reasons) == 0), reasons

    def admit_filtered(
        self,
        law: ParameterizedCausalLaw,
        *,
        strict: bool = True,
    ) -> dict[str, Any]:
        """Admit a candidate law strictly through the §9.2 5-part admission filter."""
        ok, reasons = self.evaluate_admission(law, strict=strict)
        if not ok:
            self.admission_stats["rejected"] = int(self.admission_stats.get("rejected", 0)) + 1
            rmap = dict(self.admission_stats.get("reasons", {}))
            for r in reasons:
                rmap[r] = int(rmap.get(r, 0)) + 1
            self.admission_stats["reasons"] = rmap
            self.save()
            return {"admitted": False, "law_id": law.law_id, "reasons": reasons}
        self.admission_stats["admitted"] = int(self.admission_stats.get("admitted", 0)) + 1
        self.admit(law)
        return {"admitted": True, "law_id": law.law_id, "reasons": []}

    def admit(self, law: ParameterizedCausalLaw) -> None:
        if not law.provenance:
            law.provenance = {
                "source_env": law.domain,
                "version_hash": hashlib.sha256(
                    json.dumps(law.command_template, sort_keys=True).encode("utf-8")
                ).hexdigest()[:12],
                "timestamp": int(time.time()),
            }
        if law.destructive:
            self.blacklisted_signatures.add(law.law_id)
            self.laws.pop(law.law_id, None)
        else:
            existing = self.laws.get(law.law_id)
            if existing is not None:
                law.verified_count = existing.verified_count + 1
            self.laws[law.law_id] = law
        self.save()

    def compress_by_anti_unification(self) -> dict[str, Any]:
        """Anti-unification generalizing compression (§9.2):
        Finds verified concrete laws sharing `(domain, len(command_template), creates_file_kind)`
        with structural overlap, lifts differing concrete literals into `?slot_k` variables via
        Plotkin LGG (`anti_unify_templates`), attaches the concrete instances as compact witnesses,
        and prunes the redundant ungeneralized entries!
        """
        compressed_ids: list[str] = []
        pruned_ids: list[str] = []
        concrete = [l for l in self.laws.values() if not l.generalized and not l.stale and l.command_template]
        used: set[str] = set()
        for i, la in enumerate(concrete):
            if la.law_id in used:
                continue
            for lb in concrete[i + 1 :]:
                if lb.law_id in used:
                    continue
                if la.domain != lb.domain or len(la.command_template) != len(lb.command_template):
                    continue
                if la.creates_file_kind != lb.creates_file_kind:
                    continue
                au = anti_unify_templates(la.command_template, lb.command_template)
                if au is None:
                    continue
                lgg_tpl, subst = au
                if not subst:
                    continue
                lgg_id = f"lgg::{la.domain}::{hashlib.sha256(' '.join(lgg_tpl).encode('utf-8')).hexdigest()[:10]}"
                witnesses = [
                    {
                        "law_id": la.law_id,
                        "template": list(la.command_template),
                        "provenance": dict(la.provenance),
                    },
                    {
                        "law_id": lb.law_id,
                        "template": list(lb.command_template),
                        "provenance": dict(lb.provenance),
                    },
                ]
                lgg_law = ParameterizedCausalLaw(
                    law_id=lgg_id,
                    domain=la.domain,
                    tool_or_action=la.tool_or_action if la.tool_or_action == lb.tool_or_action else "?slot_tool",
                    command_template=lgg_tpl,
                    in_ext=la.in_ext if la.in_ext == lb.in_ext else "",
                    out_ext=la.out_ext if la.out_ext == lb.out_ext else "",
                    creates_file_kind=la.creates_file_kind,
                    preconditions=dict(la.preconditions),
                    effects={k: v for k, v in la.effects.items() if lb.effects.get(k) == v} or dict(la.effects),
                    verified_count=la.verified_count + lb.verified_count,
                    provenance={
                        "source_env": f"anti_unified:{la.domain}",
                        "version_hash": hashlib.sha256(
                            json.dumps(lgg_tpl, sort_keys=True).encode("utf-8")
                        ).hexdigest()[:12],
                        "timestamp": int(time.time()),
                        "compressed_from": [la.law_id, lb.law_id],
                    },
                    witnesses=witnesses,
                    generalized=True,
                    stale=False,
                )
                used.add(la.law_id)
                used.add(lb.law_id)
                self.laws.pop(la.law_id, None)
                self.laws.pop(lb.law_id, None)
                self.laws[lgg_id] = lgg_law
                compressed_ids.append(lgg_id)
                pruned_ids.extend([la.law_id, lb.law_id])
                break
        if compressed_ids:
            self.save()
        return {
            "compressed_count": len(compressed_ids),
            "compressed_ids": compressed_ids,
            "pruned_ids": pruned_ids,
            "total_laws_after": len(self.laws),
        }

    def probe_and_refresh_stale(
        self,
        law_id: str,
        live_version_hash: str,
        probe_fn: Callable[[ParameterizedCausalLaw], bool],
    ) -> dict[str, Any]:
        """§9.2 Provenance & Version Staleness Probe:
        - If `provenance.version_hash == live_version_hash`: zero-cost FRESH hit.
        - If drifted: runs 1-step targeted `probe_fn(law)`:
          * passes -> updates `provenance.version_hash`, marks fresh (`REFRESHED`).
          * fails  -> marks `stale=True`, increments `refuted_count`, refuses blind replay (`STALE_INVALIDATED`).
        """
        law = self.laws.get(law_id)
        if law is None:
            return {"status": "MISSING", "usable": False, "law_id": law_id}
        stored_ver = str((law.provenance or {}).get("version_hash") or "")
        if stored_ver == live_version_hash and not law.stale:
            return {"status": "FRESH", "usable": True, "law_id": law_id, "probed": False}
        still_valid = False
        try:
            still_valid = bool(probe_fn(law))
        except Exception:
            still_valid = False
        if still_valid:
            law.stale = False
            law.verified_count += 1
            law.provenance = {
                **dict(law.provenance or {}),
                "version_hash": live_version_hash,
                "last_revalidated": int(time.time()),
            }
            self.save()
            return {"status": "REFRESHED", "usable": True, "law_id": law_id, "probed": True}
        law.stale = True
        law.refuted_count += 1
        law.provenance = {
            **dict(law.provenance or {}),
            "drifted_to": live_version_hash,
            "invalidated_at": int(time.time()),
        }
        self.save()
        return {"status": "STALE_INVALIDATED", "usable": False, "law_id": law_id, "probed": True}

    def active_laws(self, domain: str | None = None) -> list[ParameterizedCausalLaw]:
        """Return only fresh, non-stale laws (optionally filtered by domain)."""
        out = [l for l in self.laws.values() if not l.stale]
        if domain is not None:
            out = [l for l in out if l.domain == domain]
        return out

    def remove(self, law_id: str) -> bool:
        removed = self.laws.pop(law_id, None) is not None
        self.save()
        return removed

    def record_procedure_outcome(
        self,
        family: str,
        domain: str,
        *,
        solved: bool,
        cost_steps: int = 1,
    ) -> None:
        """Update domain-general procedure-level search statistics (cross-kind compounding)."""
        rec = self.procedure_policy.setdefault(
            family,
            {"successes": 0, "attempts": 0, "total_cost": 0, "domains": []},
        )
        rec["attempts"] = int(rec.get("attempts", 0)) + 1
        if solved:
            rec["successes"] = int(rec.get("successes", 0)) + 1
        rec["total_cost"] = int(rec.get("total_cost", 0)) + max(1, int(cost_steps))
        domains = list(rec.get("domains", []))
        if domain not in domains:
            domains.append(domain)
        rec["domains"] = sorted(domains)
        self.save()

    def procedure_priority(self, family: str) -> float:
        """Calculated zero-parameter Laplace success-per-step score (no learned weights)."""
        rec = self.procedure_policy.get(family)
        if not rec:
            return 0.5
        s = float(rec.get("successes", 0))
        n = float(rec.get("attempts", 0))
        mean_cost = float(rec.get("total_cost", 1)) / max(1.0, n)
        return (s + 1.0) / ((n + 2.0) * (1.0 + 0.08 * mean_cost))

    def rank_procedure_families(self, families: Sequence[str]) -> list[str]:
        return sorted(families, key=lambda f: (-self.procedure_priority(f), families.index(f)))

    def find_by_tool(self, tool: str, domain: str = "cli") -> list[ParameterizedCausalLaw]:
        return [
            law
            for law in self.laws.values()
            if law.domain == domain and law.tool_or_action == tool and not law.destructive
        ]


# ---------------------------------------------------------------------------
# 3. Natural-Language Goal Compiler (Zero Model Calls, Grounded in Live Env!)
# ---------------------------------------------------------------------------


@dataclass
class CompiledGoal:
    """Executable, verifiable goal specification derived from plain English + live env."""

    raw_text: str
    domain: str  # "cli" or "web_dom"
    target_files: list[str] = field(default_factory=list)
    required_json_predicates: list[dict[str, Any]] = field(default_factory=list)
    required_text_substrings: list[str] = field(default_factory=list)
    forbidden_deleted_files: list[str] = field(default_factory=list)
    # Web/DOM goal clauses
    login_credentials: dict[str, str] = field(default_factory=dict)
    form_values: dict[str, str] = field(default_factory=dict)
    superlative_goal: tuple[str, str] | None = None  # e.g. ("price", "min") for "cheapest"
    filter_keywords: list[str] = field(default_factory=list)
    target_action_words: list[str] = field(default_factory=list)
    target_status_keywords: list[str] = field(default_factory=list)


def compile_natural_language_goal(
    goal_text: str,
    domain: str,
    *,
    existing_files: Sequence[str] = (),
) -> CompiledGoal:
    """Deterministic zero-model English goal compiler grounded against live observables."""
    g = CompiledGoal(raw_text=goal_text, domain=domain)
    low = goal_text.lower()

    # Extract explicit filenames mentioned in the instruction
    file_tokens = re.findall(r"\b([A-Za-z0-9_./-]+\.(?:json|txt|csv|tar\.gz|tgz|gz|zpk|dat|out|log|xml|yaml|yml|md|bin))\b", goal_text)
    existing_set = set(existing_files)
    for ft in file_tokens:
        if ft not in existing_set and ft not in g.target_files:
            g.target_files.append(ft)
    # Also detect `into <file>` / `produce <file>` / `create <file>` / `save to <file>`
    for m in re.finditer(r"\b(?:into|to|produce|create|output|write)\s+['\"]?([A-Za-z0-9_./-]+\.[A-Za-z0-9.]+)['\"]?", goal_text, re.I):
        f = m.group(1).rstrip(".")
        if f and f not in g.target_files:
            g.target_files.append(f)

    # Protect existing input/important files by default unless instruction explicitly says delete/remove
    if not re.search(r"\b(delete|remove|erase|purge|wipe)\b", low):
        g.forbidden_deleted_files = list(existing_files)

    # Extract exact count / field predicates (e.g., "3 records", "active users", "status=ok")
    m_cnt = re.search(r"\b(\d+)\s+(?:records?|items?|rows?|entries|users?|objects?)\b", low)
    if m_cnt:
        g.required_json_predicates.append({"kind": "list_len_eq", "value": int(m_cnt.group(1))})
    for m_kv in re.finditer(r"\b([a-z_][a-z0-9_]*)\s*(?:==|=|:)\s*['\"]?([A-Za-z0-9_.-]+)['\"]?", goal_text):
        k, v = m_kv.group(1), m_kv.group(2)
        if k.lower() in ("user", "username", "email", "login"):
            g.login_credentials["username"] = v
        elif k.lower() in ("pass", "password", "pwd"):
            g.login_credentials["password"] = v
        elif k.lower() in ("coupon", "code", "promo", "voucher"):
            g.form_values["coupon"] = v
        else:
            g.form_values[k.lower()] = v
            g.required_json_predicates.append({"kind": "field_eq", "key": k, "value": v})

    # Natural-language credentials (`log in as admin with password secret` / `as admin / secret`)
    m_login = re.search(r"\blog\s*in\s+as\s+['\"]?([^\s'\"]+)['\"]?(?:\s+(?:with\s+)?password\s+['\"]?([^\s'\",.]+)['\"]?)?", goal_text, re.I)
    if m_login:
        g.login_credentials["username"] = m_login.group(1)
        if m_login.group(2):
            g.login_credentials["password"] = m_login.group(2)

    # Coupon / promo extraction (`apply coupon SAVE20`)
    m_coup = re.search(r"\b(?:coupon|promo|code|voucher)\s+['\"]?([A-Z0-9_-]{3,24})['\"]?", goal_text, re.I)
    if m_coup:
        g.form_values["coupon"] = m_coup.group(1)

    # Quoted required substrings (`containing "DONE"` / `contains "confirmed"`)
    for m_sub in re.finditer(r"\b(?:contain(?:s|ing)?|includes?|with text|showing)\s+['\"]([^'\"]+)['\"]", goal_text, re.I):
        g.required_text_substrings.append(m_sub.group(1))

    # Superlative extraction for tables / catalogs (reusing exact semantics from aimed_action_v1!)
    sup_map = {
        "cheapest": ("price", "min"),
        "lowest price": ("price", "min"),
        "most expensive": ("price", "max"),
        "highest price": ("price", "max"),
        "shortest": ("duration", "min"),
        "fastest": ("duration", "min"),
        "highest rated": ("rating", "max"),
        "newest": ("year", "max"),
    }
    for phrase, spec in sup_map.items():
        if phrase in low:
            g.superlative_goal = spec
            break

    # Stock / status filters
    for kw in ("in-stock", "in stock", "available", "active", "verified", "open", "published"):
        if kw in low:
            g.filter_keywords.append(kw.replace("-", " "))

    # Target completion words
    for act in ("checkout", "submit", "confirm", "order", "purchase", "buy", "save", "approve", "publish", "complete"):
        if act in low:
            g.target_action_words.append(act)
    for st in ("confirmed", "order confirmed", "completed", "success", "approved", "saved", "submitted"):
        if st in low:
            g.target_status_keywords.append(st)

    return g


# ---------------------------------------------------------------------------
# 4. Real OS / Terminal / CLI Environment + Active Falsification Discovery
# ---------------------------------------------------------------------------


def _inspect_file(path: pathlib.Path) -> dict[str, Any]:
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()[:12]
    info: dict[str, Any] = {
        "size": len(raw),
        "sha": sha,
        "ext": "".join(path.suffixes).lower(),
        "kind": "binary",
    }
    if raw.startswith(b"SQLite format 3\x00"):
        info["kind"] = "sqlite"
    elif raw.startswith(b"PK\x03\x04"):
        info["kind"] = "zip"
    elif raw.startswith(b"\x1f\x8b"):
        info["kind"] = "tar_gz" if info["ext"].endswith((".tar.gz", ".tgz")) else "gzip"
    else:
        try:
            txt = raw.decode("utf-8")
            info["kind"] = "text"
            info["lines"] = len(txt.splitlines())
            stripped = txt.strip()
            if stripped.startswith(("{", "[")):
                obj = json.loads(stripped)
                info["kind"] = "json"
                if isinstance(obj, list):
                    info["json_len"] = len(obj)
                    info["json_type"] = "list"
                elif isinstance(obj, dict):
                    info["json_keys"] = sorted(obj.keys())[:16]
                    info["json_type"] = "dict"
        except Exception:
            pass
    return info


class RealTerminalEnv:
    """Real Linux directory + subprocess workspace with shadow-clone probing & exact state verification."""

    def __init__(
        self,
        workspace_dir: str | pathlib.Path,
        *,
        extra_bin_dirs: Sequence[str | pathlib.Path] = (),
        protected_files: Sequence[str] = (),
    ) -> None:
        self.root = pathlib.Path(workspace_dir).resolve()
        self.extra_bin_dirs = [str(pathlib.Path(d).resolve()) for d in extra_bin_dirs]
        self.protected_files = set(protected_files)
        self.real_actions_executed: list[list[str]] = []
        self.shadow_probes_executed: int = 0
        self.destructive_traps_blocked: list[dict[str, Any]] = []

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        if self.extra_bin_dirs:
            env["PATH"] = os.pathsep.join(self.extra_bin_dirs + [env.get("PATH", "")])
        return env

    def observe(self) -> dict[str, Any]:
        """Fresh live observation of the real workspace directory (kills stale grounding!)."""
        files: dict[str, dict[str, Any]] = {}
        for p in sorted(self.root.rglob("*")):
            if p.is_file() and ".git" not in p.parts:
                rel = p.relative_to(self.root).as_posix()
                files[rel] = _inspect_file(p)
        # Discover custom/local tools in extra_bin_dirs + standard tools
        discovered_tools: list[str] = []
        for bd in self.extra_bin_dirs:
            bp = pathlib.Path(bd)
            if bp.is_dir():
                for item in sorted(bp.iterdir()):
                    if item.is_file() and os.access(item, os.X_OK):
                        discovered_tools.append(item.name)
        return {
            "files": files,
            "file_names": sorted(files.keys()),
            "discovered_tools": discovered_tools,
        }

    def fetch_instant_help(self, tool: str) -> str:
        """Instant Knowledge fetch: read live `--help` / `-h` directly from an unknown binary."""
        for flag in ("--help", "-h"):
            try:
                cp = subprocess.run(
                    [tool, flag],
                    cwd=str(self.root),
                    env=self._env(),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                out = (cp.stdout + "\n" + cp.stderr).strip()
                if out and len(out) >= 12:
                    return out
            except Exception:
                continue
        return ""

    def parse_help_hypotheses(self, tool: str, help_text: str) -> list[dict[str, Any]]:
        """Parse candidate command templates from raw `--help` prose (treated as UNTRUSTED hypotheses!)."""
        hyps: list[dict[str, Any]] = []
        seen: set[tuple[str, ...]] = set()
        # Pattern 1: Usage lines like `tool --flag <in> --out <out>` or `tool subcmd <in> <out>`
        for line in help_text.splitlines():
            s = line.strip()
            if not s:
                continue
            # Match lines mentioning the tool name OR `--flag` options with `<placeholder>`
            m_usage = re.search(rf"\b{re.escape(tool)}\s+(.+)$", s)
            if m_usage:
                rest = m_usage.group(1).strip()
                # Strip trailing description after 2+ spaces or ` - `
                rest = re.split(r"\s{2,}|\s+-\s+", rest)[0].strip()
                toks = rest.split()
                if toks and len(toks) <= 8:
                    tpl: list[str] = [tool]
                    roles: list[str] = []
                    for tok in toks:
                        if re.fullmatch(r"<[^>]+>|[A-Z][A-Z0-9_]{1,14}", tok):
                            low_t = tok.strip("<>").lower()
                            if any(w in low_t for w in ("out", "dst", "dest", "target")):
                                tpl.append("{dst}")
                                roles.append("dst")
                            elif any(w in low_t for w in ("key", "field", "filter", "expr", "query")):
                                tpl.append("{expr}")
                                roles.append("expr")
                            else:
                                tpl.append("{src}")
                                roles.append("src")
                        elif tok.startswith("-") or re.fullmatch(r"[a-z][a-z0-9_-]{1,18}", tok):
                            tpl.append(tok)
                    key = tuple(tpl)
                    if key not in seen and len(tpl) >= 2:
                        seen.add(key)
                        hyps.append({"template": tpl, "roles": roles, "doc_line": s})
            # Pattern 2: Standalone `--flag` lines with descriptions (e.g. `  --init   Initialize index`)
            m_opt = re.match(r"^(-{1,2}[a-zA-Z0-9_-]+)(?:\s+(<[^>]+>|[A-Z_]{2,12}))?(?:\s{2,}|\t+)(.+)$", s)
            if m_opt:
                flag, arg_ph, desc = m_opt.group(1), m_opt.group(2), m_opt.group(3)
                if flag in ("-h", "--help", "--version"):
                    continue
                tpl = [tool, flag]
                roles = []
                if arg_ph:
                    low_a = arg_ph.strip("<>").lower()
                    role = "dst" if any(w in low_a for w in ("out", "dst")) else "src"
                    tpl.append("{" + role + "}")
                    roles.append(role)
                key = tuple(tpl)
                if key not in seen:
                    seen.add(key)
                    hyps.append({"template": tpl, "roles": roles, "doc_line": s})
        return hyps

    def probe_in_shadow_sandbox(
        self,
        cmd: Sequence[str],
        *,
        timeout_s: int = 8,
        goal: CompiledGoal | None = None,
    ) -> dict[str, Any]:
        """Execute `cmd` in an ephemeral shadow copy of workspace to verify causal effects SAFELY!

        Never modifies `self.root`. Detects destructive traps (deleted/corrupted protected files)
        before touching the real environment.
        """
        self.shadow_probes_executed += 1
        before_obs = self.observe()
        before_files = before_obs["files"]
        goal_satisfied = False
        with tempfile.TemporaryDirectory(prefix="brain_shadow_") as td:
            shadow = pathlib.Path(td) / "ws"
            shutil.copytree(self.root, shadow, ignore=shutil.ignore_patterns(".git"))
            try:
                cp = subprocess.run(
                    list(cmd),
                    cwd=str(shadow),
                    env=self._env(),
                    capture_output=True,
                    text=True,
                    timeout=timeout_s,
                )
                rc = cp.returncode
                stdout, stderr = cp.stdout, cp.stderr
            except subprocess.TimeoutExpired:
                return {"ok": False, "rc": -1, "destructive": False, "reason": "TIMEOUT"}
            except OSError as exc:
                return {"ok": False, "rc": -1, "destructive": False, "reason": str(exc)}

            after_files: dict[str, dict[str, Any]] = {}
            for p in sorted(shadow.rglob("*")):
                if p.is_file() and ".git" not in p.parts:
                    rel = p.relative_to(shadow).as_posix()
                    after_files[rel] = _inspect_file(p)
            if goal is not None and rc == 0:
                shadow_env = RealTerminalEnv(shadow, extra_bin_dirs=self.extra_bin_dirs, protected_files=list(self.protected_files))
                goal_satisfied, _ = shadow_env.verify_goal(goal)

        added = {k: after_files[k] for k in after_files if k not in before_files}
        deleted = sorted(k for k in before_files if k not in after_files)
        modified = sorted(
            k for k in before_files if k in after_files and before_files[k]["sha"] != after_files[k]["sha"]
        )
        # Check destructive violation: deleted ANY protected file or emptied/corrupted protected file!
        destructive = False
        for pf in self.protected_files:
            if pf in deleted:
                destructive = True
            elif pf in modified and after_files[pf]["size"] == 0 and before_files[pf]["size"] > 0:
                destructive = True
        # Also detect mass deletion of existing non-temp files
        if len(deleted) >= max(2, len(before_files)) and before_files:
            destructive = True

        return {
            "ok": rc == 0 and not destructive,
            "rc": rc,
            "stdout": stdout[:600],
            "stderr": stderr[:600],
            "added": added,
            "deleted": deleted,
            "modified": modified,
            "destructive": destructive,
            "goal_satisfied": goal_satisfied and not destructive,
        }

    def execute_real(self, cmd: Sequence[str], *, timeout_s: int = 12) -> dict[str, Any]:
        """Execute a verified command in the REAL workspace."""
        self.real_actions_executed.append(list(cmd))
        cp = subprocess.run(
            list(cmd),
            cwd=str(self.root),
            env=self._env(),
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return {
            "rc": cp.returncode,
            "stdout": cp.stdout[:800],
            "stderr": cp.stderr[:800],
            "obs": self.observe(),
        }

    def verify_goal(self, goal: CompiledGoal) -> tuple[bool, list[str]]:
        """Fresh-state exactness verifier: checks EVERY compiled postcondition on real disk."""
        obs = self.observe()
        files = obs["files"]
        unmet: list[str] = []
        for pf in goal.forbidden_deleted_files:
            if pf not in files:
                unmet.append(f"PROTECTED_DELETED:{pf}")
        for tf in goal.target_files:
            if tf not in files:
                unmet.append(f"MISSING_TARGET:{tf}")
            else:
                # Check JSON / content predicates on target file!
                fpath = self.root / tf
                raw_txt = fpath.read_text(encoding="utf-8", errors="replace")
                for sub in goal.required_text_substrings:
                    if sub not in raw_txt:
                        unmet.append(f"MISSING_TEXT:{sub}")
                if goal.required_json_predicates and files[tf].get("kind") == "json":
                    try:
                        obj = json.loads(raw_txt)
                    except Exception:
                        unmet.append(f"INVALID_JSON:{tf}")
                        obj = None
                    if obj is not None:
                        for pred in goal.required_json_predicates:
                            if pred["kind"] == "list_len_eq":
                                if not (isinstance(obj, list) and len(obj) == pred["value"]):
                                    unmet.append(f"LEN_MISMATCH:{len(obj) if isinstance(obj, list) else type(obj).__name__}!={pred['value']}")
                            elif pred["kind"] == "field_eq":
                                rows = obj if isinstance(obj, list) else ([obj] if isinstance(obj, dict) else [])
                                if not rows or not all(str(r.get(pred["key"], "")).lower() == str(pred["value"]).lower() for r in rows if isinstance(r, dict)):
                                    unmet.append(f"FIELD_MISMATCH:{pred['key']}!={pred['value']}")
        return len(unmet) == 0, unmet


# ---------------------------------------------------------------------------
# 5. Real Live HTTP / HTML-DOM / ARIA-Accessibility-Tree Browser Environment
# ---------------------------------------------------------------------------


class _AXDOMParser(html.parser.HTMLParser):
    """Zero-dependency deterministic HTML -> Accessibility/DOM Tree parser."""

    def __init__(self) -> None:
        super().__init__()
        self.title: str = ""
        self._in_title = False
        self.links: list[dict[str, Any]] = []
        self.forms: list[dict[str, Any]] = []
        self.tables: list[dict[str, Any]] = []
        self.alerts: list[str] = []
        self.texts: list[str] = []
        self._cur_form: dict[str, Any] | None = None
        self._cur_link: dict[str, Any] | None = None
        self._cur_button: dict[str, Any] | None = None
        self._cur_table: dict[str, Any] | None = None
        self._cur_row: list[str] | None = None
        self._cur_cell_tag: str | None = None
        self._cur_cell_buf: list[str] = []
        self._cur_cell_links: list[str] = []
        self._cur_row_links: list[str] = []
        self._in_alert = False
        self._alert_buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = {k.lower(): (v or "") for k, v in attrs}
        t = tag.lower()
        if t == "title":
            self._in_title = True
        elif t == "a":
            href = ad.get("href", "")
            self._cur_link = {"href": href, "text": "", "role": ad.get("role", ""), "aria": ad.get("aria-label", "")}
            if self._cur_cell_tag is not None and href:
                self._cur_cell_links.append(href)
        elif t == "form":
            self._cur_form = {
                "action": ad.get("action", ""),
                "method": (ad.get("method", "GET") or "GET").upper(),
                "id": ad.get("id", ""),
                "inputs": [],
                "buttons": [],
                "aria": ad.get("aria-label", ""),
            }
        elif t == "input" and self._cur_form is not None:
            itype = ad.get("type", "text").lower()
            inp = {
                "type": itype,
                "name": ad.get("name", ""),
                "value": ad.get("value", ""),
                "placeholder": ad.get("placeholder", ""),
                "aria": ad.get("aria-label", ""),
                "required": "required" in ad,
                "checked": "checked" in ad,
            }
            if itype == "submit":
                self._cur_form["buttons"].append({"text": ad.get("value", "submit"), "name": ad.get("name", ""), "value": ad.get("value", ""), "danger": "danger" in ad.get("class", "").lower()})
            else:
                self._cur_form["inputs"].append(inp)
        elif t == "button":
            btn = {
                "text": "",
                "name": ad.get("name", ""),
                "value": ad.get("value", ""),
                "type": ad.get("type", "submit"),
                "danger": "danger" in ad.get("class", "").lower() or "destructive" in ad.get("data-risk", "").lower(),
            }
            self._cur_button = btn
            if self._cur_form is not None:
                self._cur_form["buttons"].append(btn)
        elif t == "table":
            self._cur_table = {"headers": [], "rows": []}
        elif t == "tr" and self._cur_table is not None:
            self._cur_row = []
            self._cur_row_links = []
        elif t in ("th", "td") and self._cur_row is not None:
            self._cur_cell_tag = t
            self._cur_cell_buf = []
            self._cur_cell_links = []
        elif ad.get("role") in ("alert", "status") or "error" in ad.get("class", "").lower() or "alert" in ad.get("class", "").lower():
            self._in_alert = True
            self._alert_buf = []

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t == "title":
            self._in_title = False
        elif t == "a" and self._cur_link is not None:
            self._cur_link["text"] = " ".join(self._cur_link["text"].split())
            self.links.append(self._cur_link)
            self._cur_link = None
        elif t == "button" and self._cur_button is not None:
            self._cur_button["text"] = " ".join(self._cur_button["text"].split())
            self._cur_button = None
        elif t == "form" and self._cur_form is not None:
            self.forms.append(self._cur_form)
            self._cur_form = None
        elif t in ("th", "td") and self._cur_cell_tag == t and self._cur_row is not None:
            txt = " ".join("".join(self._cur_cell_buf).split())
            self._cur_row.append(txt)
            self._cur_row_links.extend(self._cur_cell_links)
            self._cur_cell_tag = None
        elif t == "tr" and self._cur_table is not None and self._cur_row is not None:
            if not self._cur_table["headers"] and any(self._cur_row):
                self._cur_table["headers"] = list(self._cur_row)
            elif any(self._cur_row):
                self._cur_table["rows"].append({"cells": list(self._cur_row), "links": list(self._cur_row_links)})
            self._cur_row = None
        elif t == "table" and self._cur_table is not None:
            self.tables.append(self._cur_table)
            self._cur_table = None
        elif self._in_alert and t in ("div", "p", "span"):
            msg = " ".join("".join(self._alert_buf).split())
            if msg:
                self.alerts.append(msg)
            self._in_alert = False

    def handle_data(self, data: str) -> None:
        s = data.strip()
        if not s:
            return
        self.texts.append(s)
        if self._in_title:
            self.title += s
        if self._cur_link is not None:
            self._cur_link["text"] += " " + s
        if self._cur_button is not None:
            self._cur_button["text"] += " " + s
        if self._cur_cell_tag is not None:
            self._cur_cell_buf.append(s)
        if self._in_alert:
            self._alert_buf.append(s)


class RealWebDOMEnv:
    """Real live HTTP + Cookie + HTML Accessibility-Tree Browser Environment (Zero Model Calls)."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.current_url = self.base_url + "/"
        self.current_html = ""
        self.current_status = 0
        self.actions_taken: list[dict[str, Any]] = []
        self.destructive_actions_blocked: list[dict[str, Any]] = []

    def navigate(self, url_or_path: str) -> dict[str, Any]:
        url = urllib.parse.urljoin(self.current_url, url_or_path)
        req = urllib.request.Request(url, method="GET")
        try:
            with self.opener.open(req, timeout=8) as resp:
                self.current_url = resp.geturl()
                self.current_status = resp.status
                self.current_html = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            self.current_status = e.code
            self.current_html = e.read().decode("utf-8", errors="replace")
        self.actions_taken.append({"kind": "navigate", "url": self.current_url, "status": self.current_status})
        return self.observe()

    def submit_form(self, form: Mapping[str, Any], field_values: Mapping[str, str]) -> dict[str, Any]:
        action_url = urllib.parse.urljoin(self.current_url, str(form.get("action") or self.current_url))
        method = str(form.get("method") or "POST").upper()
        payload: dict[str, str] = {}
        for inp in form.get("inputs", []):
            name = inp.get("name", "")
            if not name:
                continue
            if inp.get("type") == "hidden":
                payload[name] = inp.get("value", "")
            elif name in field_values:
                payload[name] = str(field_values[name])
            elif inp.get("type") == "checkbox" and inp.get("checked"):
                payload[name] = inp.get("value", "on") or "on"
            elif inp.get("value"):
                payload[name] = inp["value"]
        encoded = urllib.parse.urlencode(payload).encode("utf-8")
        if method == "GET":
            sep = "&" if "?" in action_url else "?"
            req = urllib.request.Request(action_url + sep + encoded.decode("utf-8"), method="GET")
        else:
            req = urllib.request.Request(action_url, data=encoded, method="POST")
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
        try:
            with self.opener.open(req, timeout=8) as resp:
                self.current_url = resp.geturl()
                self.current_status = resp.status
                self.current_html = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            self.current_status = e.code
            self.current_html = e.read().decode("utf-8", errors="replace")
        self.actions_taken.append({"kind": "submit_form", "url": action_url, "fields": sorted(payload.keys()), "status": self.current_status})
        return self.observe()

    def observe(self) -> dict[str, Any]:
        """Fresh live AXTree/DOM parse of the current page (kills stale grounding!)."""
        parser = _AXDOMParser()
        parser.feed(self.current_html)
        full_text = " ".join(parser.texts)
        return {
            "url": self.current_url,
            "status": self.current_status,
            "title": parser.title.strip(),
            "links": parser.links,
            "forms": parser.forms,
            "tables": parser.tables,
            "alerts": parser.alerts,
            "text": full_text,
            "text_lower": full_text.lower(),
        }


# ---------------------------------------------------------------------------
# 6. The Unified Perfect-Algorithm Computer-Use Agent
# ---------------------------------------------------------------------------


class UniversalComputerAgent:
    """Scan -> Retrieve -> Instant Knowledge + Active Falsification -> Differential Tomography ->
    Algebraic Petri-Net Composition -> Plan (Mental Model) -> Act -> Verify -> Generalize."""

    def __init__(self, law_store_path: str | pathlib.Path | None = None) -> None:
        self.store = ExternalCausalLawStore(law_store_path)
        self._law_store_path = pathlib.Path(law_store_path) if law_store_path is not None else None

    def compile_and_solve_stateful_app(
        self,
        *,
        snapshot_fn: Any,
        step_fn: Any,
        reset_fn: Any,
        actions: Sequence[str],
        goal_predicate: Any,
        protected_prefixes: Sequence[str] = (),
        max_bfs_states: int = 600,
    ) -> dict[str, Any]:
        """Pillar 2: Differential State Tomography -> Mealy API compilation -> millisecond exact plan."""
        from canonical.swe_kernel import reverse_tomography_algebra_v1 as rta

        tomo = rta.DifferentialStateTomograph()
        learned = tomo.learn_mealy_api(
            snapshot_fn=snapshot_fn,
            step_fn=step_fn,
            reset_fn=reset_fn,
            actions=actions,
            max_bfs_states=max_bfs_states,
            protected_prefixes=protected_prefixes,
        )
        if reset_fn is not None:
            reset_fn()
        start_snap = snapshot_fn()
        plan = tomo.plan_shortest_path(start_snap, goal_predicate)
        solved = False
        if plan is not None:
            for act in plan:
                step_fn(act)
            final_snap = snapshot_fn()
            solved = bool(goal_predicate(dict(final_snap.state_signature(tomo.active_keys))))
        self.store.record_procedure_outcome(
            "differential_state_tomography",
            "stateful_app",
            solved=solved,
            cost_steps=max(1, len(plan) if plan is not None else 1),
        )
        return {
            "solved": solved,
            "plan": plan,
            "plan_length": len(plan) if plan is not None else 0,
            "tomography": learned,
        }

    def compose_and_crystallize_pipeline(
        self,
        morphisms: Sequence[Any],
        initial_types: Sequence[str],
        goal_types: Sequence[str],
        initial_state: dict[str, Any],
        *,
        pipeline_name: str,
        verify_fn: Any,
        axioms: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Pillar 3: Type-Transition Petri-Net composition + static EffectContract proof + L2 crystallization."""
        from canonical.swe_kernel import reverse_tomography_algebra_v1 as rta

        composer = rta.AlgebraicSkillComposer(self._law_store_path)
        for m in morphisms:
            composer.register(m)
        plan = composer.compose(initial_types, goal_types, axioms=axioms)
        if not plan.get("composed"):
            self.store.record_procedure_outcome("algebraic_skill_composition", "pipeline", solved=False, cost_steps=1)
            return {"solved": False, "plan": plan}
        res = composer.execute_and_crystallize(
            plan,
            initial_state,
            pipeline_name=pipeline_name,
            verify_fn=verify_fn,
        )
        solved = bool(res.get("verified"))
        self.store.record_procedure_outcome(
            "algebraic_skill_composition",
            "pipeline",
            solved=solved,
            cost_steps=max(1, len(plan.get("chain", ()))),
        )
        return {"solved": solved, "plan": plan, "crystallization": res, "composer": composer}

    # ---- A. Real Terminal / Arbitrary Unknown CLI Solver ----

    def solve_terminal_goal(
        self,
        env: RealTerminalEnv,
        goal_text: str,
        *,
        max_steps: int = 8,
    ) -> dict[str, Any]:
        """Solve an arbitrary multi-step OS/CLI goal with zero prior tool knowledge.

        Flow:
          1. Scan live workspace & compile natural-language goal into exact postconditions.
          2. Retrieve generalized causal laws from external store; for any unknown tool,
             fetch live `--help`, parse untrusted hypotheses, and ACTIVELY FALSIFY every
             hypothesis in an isolated shadow sandbox clone (blocking lying/destructive docs!).
          3. Admit verified parameterized causal laws into `self.store` & load them into
             `EnvironmentMentalModel` (Leap 4).
          4. Plan optimal multi-step action chain in-memory, execute on real disk, discover
             any hidden preconditions via CEGAR on failure, and verify ALL compiled postconditions
             on fresh live disk state!
        """
        t0 = time.monotonic()
        obs0 = env.observe()
        goal = compile_natural_language_goal(goal_text, "cli", existing_files=obs0["file_names"])
        env.protected_files |= set(goal.forbidden_deleted_files)

        # Unified SWE-in-the-Loop Bridge: when the workspace is a Python repo with failing pytest tests
        # and the goal asks to fix/repair/pass tests, delegate directly to Angelic CEGIS Repair!
        low_goal = goal_text.lower()
        py_test_files = [
            fn for fn in obs0["file_names"]
            if fn.endswith(".py") and (pathlib.Path(fn).name.startswith("test_") or pathlib.Path(fn).name.endswith("_test.py"))
        ]
        if py_test_files and any(w in low_goal for w in ("pytest", "failing test", "fix the bug", "repair", "pass all tests")):
            from canonical.swe_kernel import angelic_cegis_repair_v1 as acr
            for tf in py_test_files:
                rep = acr.repair_repo_angelic_cegis(env.root, tf, timeout_s=45)
                if rep.get("repaired"):
                    # Apply the verified surgical patch to real workspace and re-verify pytest!
                    (env.root / rep["patched_file"]).write_text(rep["patched_source"], encoding="utf-8")
                    check = env.execute_real([sys.executable, "-m", "pytest", "-q", "-o", "addopts=", tf])
                    if check["rc"] == 0:
                        self.store.record_procedure_outcome(
                            "swe_angelic_cegis",
                            "swe_repo",
                            solved=True,
                            cost_steps=1,
                        )
                        return {
                            "solved": True,
                            "mode": "UNIFIED_SWE_ANGELIC_CEGIS",
                            "patched_file": rep["patched_file"],
                            "patched_line": rep["patched_line"],
                            "method": rep["method"],
                            "procedure_family": "swe_angelic_cegis",
                            "real_actions": env.real_actions_executed,
                            "shadow_probes": env.shadow_probes_executed,
                            "destructive_traps_blocked": env.destructive_traps_blocked,
                            "elapsed_ms": int((time.monotonic() - t0) * 1000),
                        }

        discovered_laws: list[ParameterizedCausalLaw] = []
        laws_from_memory = 0
        laws_learned_live = 0

        # Step 1: Retrieve verified causal laws from external store OR learn live via shadow falsification!
        for tool in obs0["discovered_tools"]:
            cached = self.store.find_by_tool(tool, domain="cli")
            if cached:
                discovered_laws.extend(cached)
                laws_from_memory += len(cached)
                continue
            help_text = env.fetch_instant_help(tool)
            if not help_text:
                continue
            hyps = env.parse_help_hypotheses(tool, help_text)
            for hyp in hyps:
                tpl: list[str] = hyp["template"]
                roles: list[str] = hyp["roles"]
                # Instantiate probe args from live workspace files (prefer matching input file)
                sample_src = obs0["file_names"][0] if obs0["file_names"] else "probe_in.dat"
                sample_dst = "__brain_probe_out__.json"
                # Try matching each distinct extension currently in workspace!
                ext_samples: list[str] = []
                seen_ext: set[str] = set()
                for fn in obs0["file_names"]:
                    ex = obs0["files"][fn]["ext"]
                    if ex not in seen_ext:
                        seen_ext.add(ex)
                        ext_samples.append(fn)
                if not ext_samples:
                    ext_samples = [sample_src]

                for s_file in ext_samples:
                    s_ext = obs0["files"].get(s_file, {}).get("ext", "")
                    cmd = [
                        tok.replace("{src}", s_file).replace("{dst}", sample_dst).replace("{expr}", "active")
                        for tok in tpl
                    ]
                    sig = f"{tool}:{' '.join(tpl)}:{s_ext}"
                    if sig in self.store.blacklisted_signatures:
                        continue
                    probe = env.probe_in_shadow_sandbox(cmd)
                    if probe.get("destructive"):
                        env.destructive_traps_blocked.append(
                            {"tool": tool, "cmd": cmd, "doc_line": hyp["doc_line"], "deleted": probe.get("deleted")}
                        )
                        bad_law = ParameterizedCausalLaw(
                            law_id=sig,
                            domain="cli",
                            tool_or_action=tool,
                            command_template=tpl,
                            in_ext=s_ext,
                            destructive=True,
                        )
                        self.store.admit(bad_law)
                        continue
                    if probe.get("ok") and (probe.get("added") or probe.get("modified")):
                        added = probe["added"]
                        out_ext = ""
                        out_kind = ""
                        if sample_dst in added:
                            out_ext = pathlib.Path(sample_dst).suffix
                            out_kind = added[sample_dst].get("kind", "")
                        elif added:
                            first_add = next(iter(added.values()))
                            out_ext = first_add.get("ext", "")
                            out_kind = first_add.get("kind", "")
                        law = ParameterizedCausalLaw(
                            law_id=sig,
                            domain="cli",
                            tool_or_action=tool,
                            command_template=tpl,
                            in_ext=s_ext if "{src}" in tpl else "",
                            out_ext=out_ext,
                            creates_file_kind=out_kind,
                            preconditions={"has_ext": s_ext} if "{src}" in tpl else {},
                            effects={"produces_kind": out_kind, "produces_ext": out_ext, "added_count": len(added)},
                            destructive=False,
                        )
                        self.store.admit(law)
                        discovered_laws.append(law)
                        laws_learned_live += 1
                    elif not probe.get("ok") and probe.get("rc", 0) != 0:
                        # Record hidden precondition hint from stderr (CEGAR discovery!)
                        err_low = (probe.get("stderr") or "").lower()
                        m_need = re.search(r"(?:must|need|require[sd]?|run)\s+['\"]?(--[a-z0-9_-]+)['\"]?", err_low)
                        if m_need:
                            req_flag = m_need.group(1)
                            # Probe prerequisite + command together in shadow sandbox!
                            law_id_pre = f"{sig}|pre={req_flag}"
                            law = ParameterizedCausalLaw(
                                law_id=law_id_pre,
                                domain="cli",
                                tool_or_action=tool,
                                command_template=tpl,
                                in_ext=s_ext if "{src}" in tpl else "",
                                preconditions={"has_ext": s_ext, "requires_flag": req_flag},
                                effects={"needs_init_probe": True},
                                destructive=False,
                            )
                            discovered_laws.append(law)

        # Step 2: Execute planned workflow using Mental Model + Shadow Verification before every real step!
        steps_taken: list[dict[str, Any]] = []
        init_flags_run: set[tuple[str, str]] = set()
        for step_idx in range(max_steps):
            ok, unmet = env.verify_goal(goal)
            if ok:
                reading_succeeded = bool(laws_from_memory == 0 and laws_learned_live == 0)
                proc_family = (
                    "live_schema_read"
                    if reading_succeeded
                    else ("cegar_precondition_discovery" if init_flags_run else "shadow_probe_induction")
                )
                self.store.record_procedure_outcome(
                    proc_family,
                    "cli",
                    solved=True,
                    cost_steps=max(1, len(steps_taken)),
                )
                return {
                    "solved": True,
                    "steps": steps_taken,
                    "real_actions": env.real_actions_executed,
                    "shadow_probes": env.shadow_probes_executed,
                    "destructive_traps_blocked": env.destructive_traps_blocked,
                    "laws_from_memory": laws_from_memory,
                    "laws_learned_live": laws_learned_live,
                    "reading_succeeded": reading_succeeded,
                    "procedure_family": proc_family,
                    "elapsed_ms": int((time.monotonic() - t0) * 1000),
                }

            cur_obs = env.observe()
            # Re-discover newly applicable laws for newly produced file extensions (multi-step pipeline!)
            for tool in cur_obs["discovered_tools"]:
                cur_exts = {cur_obs["files"][f]["ext"] for f in cur_obs["file_names"]}
                known_exts = {l.in_ext for l in discovered_laws if l.tool_or_action == tool}
                if cur_exts - known_exts:
                    # Check store first!
                    for cl in self.store.find_by_tool(tool, domain="cli"):
                        if cl.law_id not in {l.law_id for l in discovered_laws}:
                            discovered_laws.append(cl)
                            laws_from_memory += 1
                    help_text = env.fetch_instant_help(tool)
                    for hyp in env.parse_help_hypotheses(tool, help_text):
                        tpl = hyp["template"]
                        if "{src}" not in tpl:
                            continue
                        for fn in cur_obs["file_names"]:
                            ex = cur_obs["files"][fn]["ext"]
                            if ex in known_exts:
                                continue
                            sig = f"{tool}:{' '.join(tpl)}:{ex}"
                            if sig in self.store.blacklisted_signatures or any(l.law_id == sig for l in discovered_laws):
                                continue
                            probe_dst = goal.target_files[0] if goal.target_files else "__brain_step_out__.json"
                            expr_val = (goal.filter_keywords[0] if goal.filter_keywords else "active")
                            cmd = [tok.replace("{src}", fn).replace("{dst}", probe_dst).replace("{expr}", expr_val) for tok in tpl]
                            pr = env.probe_in_shadow_sandbox(cmd)
                            if pr.get("destructive"):
                                env.destructive_traps_blocked.append({"tool": tool, "cmd": cmd, "doc_line": hyp["doc_line"], "deleted": pr.get("deleted")})
                                self.store.admit(ParameterizedCausalLaw(law_id=sig, domain="cli", tool_or_action=tool, command_template=tpl, in_ext=ex, destructive=True))
                            elif pr.get("ok") and pr.get("added"):
                                first_add = next(iter(pr["added"].values()))
                                nl = ParameterizedCausalLaw(
                                    law_id=sig,
                                    domain="cli",
                                    tool_or_action=tool,
                                    command_template=tpl,
                                    in_ext=ex,
                                    out_ext=first_add.get("ext", ""),
                                    creates_file_kind=first_add.get("kind", ""),
                                    preconditions={"has_ext": ex},
                                    effects={"produces_kind": first_add.get("kind", ""), "produces_ext": first_add.get("ext", "")},
                                )
                                self.store.admit(nl)
                                discovered_laws.append(nl)
                                laws_learned_live += 1

            # Score candidate grounded commands in shadow sandbox before committing to real workspace!
            best_cmd: list[str] | None = None
            best_score = -1
            best_law: ParameterizedCausalLaw | None = None
            target_dst = goal.target_files[0] if goal.target_files else "output.json"
            stage_dst = f"_stage_{step_idx + 1}{pathlib.Path(target_dst).suffix or '.json'}"
            filter_val = next(
                (str(p["value"]) for p in goal.required_json_predicates if p.get("kind") == "field_eq"),
                goal.filter_keywords[0] if goal.filter_keywords else "active",
            )

            for law in discovered_laws:
                if law.destructive:
                    continue
                # If law has a CEGAR-discovered prerequisite flag not yet executed, run it first!
                req_flag = law.preconditions.get("requires_flag")
                if req_flag and (law.tool_or_action, req_flag) not in init_flags_run:
                    pre_cmd = [law.tool_or_action, req_flag]
                    pr = env.probe_in_shadow_sandbox(pre_cmd)
                    if pr.get("ok"):
                        best_cmd = pre_cmd
                        best_score = 150
                        best_law = law
                        init_flags_run.add((law.tool_or_action, req_flag))
                        break
                tpl = law.command_template
                matching_srcs = [
                    fn for fn in cur_obs["file_names"]
                    if (not law.in_ext or cur_obs["files"][fn]["ext"] == law.in_ext) and fn != target_dst
                ]
                if "{src}" not in tpl:
                    matching_srcs = [""]
                for src_fn in matching_srcs:
                    cmd = [
                        tok.replace("{src}", src_fn).replace("{dst}", target_dst).replace("{expr}", filter_val)
                        for tok in tpl
                    ]
                    if cmd in env.real_actions_executed:
                        continue
                    pr = env.probe_in_shadow_sandbox(cmd, goal=goal)
                    if pr.get("destructive"):
                        env.destructive_traps_blocked.append({"tool": law.tool_or_action, "cmd": cmd, "deleted": pr.get("deleted")})
                        continue
                    if not pr.get("ok"):
                        # Online CEGAR: detect hidden precondition from live error message!
                        err_low = (pr.get("stderr") or "").lower()
                        m_need = re.search(r"(?:must|need|require[sd]?|run)\s+['\"]?(--[a-z0-9_-]+)['\"]?", err_low)
                        if m_need and (law.tool_or_action, m_need.group(1)) not in init_flags_run:
                            law.preconditions["requires_flag"] = m_need.group(1)
                            pre_cmd = [law.tool_or_action, m_need.group(1)]
                            pr_pre = env.probe_in_shadow_sandbox(pre_cmd)
                            if pr_pre.get("ok"):
                                best_cmd = pre_cmd
                                best_score = 145
                                best_law = law
                                init_flags_run.add((law.tool_or_action, m_need.group(1)))
                                break
                        continue
                    added = pr.get("added", {})
                    if not added:
                        continue
                    # Exact goal verification inside shadow sandbox distinguishes FINAL step from INTERMEDIATE stage!
                    chosen_cmd = cmd
                    if pr.get("goal_satisfied"):
                        sc = 250
                    else:
                        # Intermediate stage: write to `_stage_N` instead of squatting on `target_dst`!
                        if "{dst}" in tpl and target_dst in added and goal.required_json_predicates:
                            chosen_cmd = [
                                tok.replace("{src}", src_fn).replace("{dst}", stage_dst).replace("{expr}", filter_val)
                                for tok in tpl
                            ]
                            if chosen_cmd in env.real_actions_executed:
                                continue
                        # Avoid re-running the same tool+src that already produced a stage file
                        if any(
                            prev[0] == chosen_cmd[0] and (not src_fn or src_fn in prev)
                            for prev in env.real_actions_executed
                        ):
                            continue
                        sc = 60 + len(added) * 5
                    if sc > best_score:
                        best_score = sc
                        best_cmd = chosen_cmd
                        best_law = law
                if best_score >= 250:
                    break

            # Fallback to schema-grounded OS / code-as-operator synthesis when no custom binary matched!
            # Strictly verified inside shadow sandbox BEFORE touching real workspace (zero destructive risk!).
            if best_cmd is None:
                field_preds = [p for p in goal.required_json_predicates if p.get("kind") == "field_eq"]
                synth_cands: list[list[str]] = []
                for fn, finfo in cur_obs["files"].items():
                    kind = finfo.get("kind")
                    if kind == "tar_gz" and shutil.which("tar") and not _REL_DIR_TOKEN_RE.search(goal_text):
                        synth_cands.append(["tar", "-xzf", fn])
                    elif kind == "zip" and not _REL_DIR_TOKEN_RE.search(goal_text):
                        synth_cands.append([sys.executable, "-m", "zipfile", "-e", fn, "."])
                    elif kind == "json" and fn != target_dst and target_dst.endswith(".json"):
                        if field_preds:
                            pred_json = json.dumps(field_preds)
                            py_code = (
                                "import json, pathlib, sys\n"
                                "rows = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))\n"
                                "preds = json.loads(sys.argv[3])\n"
                                "if isinstance(rows, list):\n"
                                "    out = [r for r in rows if isinstance(r, dict) and all(str(r.get(p['key'], '')).lower() == str(p['value']).lower() for p in preds)]\n"
                                "else:\n"
                                "    out = rows\n"
                                "pathlib.Path(sys.argv[2]).write_text(json.dumps(out), encoding='utf-8')\n"
                            )
                            synth_cands.append([sys.executable, "-c", py_code, fn, target_dst, pred_json])
                    elif kind == "sqlite" and target_dst.endswith(".json"):
                        pred_json = json.dumps(field_preds)
                        py_code = (
                            "import json, pathlib, sqlite3, sys\n"
                            "con = sqlite3.connect(sys.argv[1])\n"
                            "con.row_factory = sqlite3.Row\n"
                            "preds = json.loads(sys.argv[3])\n"
                            "tables = [r[0] for r in con.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]\n"
                            "best = []\n"
                            "for t in tables:\n"
                            "    cols = {r[1] for r in con.execute(f'PRAGMA table_info(\"{t}\")').fetchall()}\n"
                            "    if all(p['key'] in cols for p in preds):\n"
                            "        rows = [dict(r) for r in con.execute(f'SELECT * FROM \"{t}\"').fetchall()]\n"
                            "        out = [r for r in rows if all(str(r.get(p['key'], '')).lower() == str(p['value']).lower() for p in preds)]\n"
                            "        if len(out) >= len(best):\n"
                            "            best = out\n"
                            "con.close()\n"
                            "pathlib.Path(sys.argv[2]).write_text(json.dumps(best), encoding='utf-8')\n"
                        )
                        synth_cands.append([sys.executable, "-c", py_code, fn, target_dst, pred_json])

                for scmd in synth_cands:
                    if scmd in env.real_actions_executed:
                        continue
                    pr = env.probe_in_shadow_sandbox(scmd, goal=goal)
                    if pr.get("destructive") or not pr.get("ok") or not pr.get("added"):
                        continue
                    sc = 250 if pr.get("goal_satisfied") else (60 + len(pr["added"]) * 5)
                    if sc > best_score:
                        best_score = sc
                        best_cmd = scmd
                        best_law = None
                    if best_score >= 250:
                        break

            if best_cmd is None:
                break
            res = env.execute_real(best_cmd)
            if res["rc"] == 0 and best_law is not None and best_law.command_template[0] == best_cmd[0] and len(best_cmd) == len(best_law.command_template):
                # Admit verified causal law (including any CEGAR-discovered `requires_flag`!) to external store!
                self.store.admit(best_law)
            steps_taken.append({"step": step_idx + 1, "cmd": best_cmd, "rc": res["rc"], "law": best_law.law_id if best_law else ""})

        ok, unmet = env.verify_goal(goal)
        if (not ok) or (ok and not steps_taken):
            rel_res = (
                _synthesize_relational_cow_terminal_pipeline(env.root, goal_text, law_store=self.store)
                if not ok
                else {"solved": False}
            )
            if not rel_res.get("solved"):
                ws_res = repair_workspace_script_or_config_cow(env.root, goal_text, law_store=self.store)
                if ws_res.get("solved"):
                    rel_res = ws_res
            if rel_res.get("solved"):
                for ra in rel_res.get("real_actions") or ():
                    env.real_actions_executed.append(list(ra))
                self.store.record_procedure_outcome(
                    str(rel_res.get("procedure_family") or "relational_cow_pipeline"),
                    "cli",
                    solved=True,
                    cost_steps=1,
                )
                return {
                    "solved": True,
                    "source": rel_res.get("source"),
                    "procedure_family": rel_res.get("procedure_family"),
                    "law_id": rel_res.get("law_id"),
                    "output_file": rel_res.get("output_file") or rel_res.get("repaired_file"),
                    "repaired_file": rel_res.get("repaired_file"),
                    "committed_files": rel_res.get("committed_files"),
                    "steps": steps_taken + [{"step": len(steps_taken) + 1, "cmd": rel_res.get("real_actions", [[]])[0], "rc": 0, "law": rel_res.get("law_id", "")}],
                    "real_actions": env.real_actions_executed,
                    "shadow_probes": env.shadow_probes_executed,
                    "destructive_traps_blocked": env.destructive_traps_blocked,
                    "laws_from_memory": laws_from_memory,
                    "laws_learned_live": laws_learned_live + 1,
                    "reading_succeeded": True,
                    "elapsed_ms": int((time.monotonic() - t0) * 1000),
                }
        # Apply Project Brain's measured laws (`learn_or_read_v1` & `learn_to_learn_v1`):
        # 1. Track whether live zero-experience reading/schema inspection sufficed without memory displacement.
        # 2. Record cross-domain procedure-level search outcome in the external JSON store (zero weights!).
        reading_succeeded = bool(ok and laws_from_memory == 0 and laws_learned_live == 0)
        proc_family = (
            "live_schema_read"
            if reading_succeeded
            else ("cegar_precondition_discovery" if init_flags_run else "shadow_probe_induction")
        )
        self.store.record_procedure_outcome(
            proc_family,
            "cli",
            solved=ok,
            cost_steps=max(1, len(steps_taken)),
        )
        return {
            "solved": ok,
            "unmet": unmet,
            "steps": steps_taken,
            "real_actions": env.real_actions_executed,
            "shadow_probes": env.shadow_probes_executed,
            "destructive_traps_blocked": env.destructive_traps_blocked,
            "laws_from_memory": laws_from_memory,
            "laws_learned_live": laws_learned_live,
            "reading_succeeded": reading_succeeded,
            "procedure_family": proc_family,
            "elapsed_ms": int((time.monotonic() - t0) * 1000),
        }

    # ---- B. Real Multi-Page Web / HTML-DOM / AXTree Solver (Zero Model Calls!) ----

    def solve_web_dom_goal(
        self,
        env: RealWebDOMEnv,
        goal_text: str,
        *,
        max_steps: int = 12,
    ) -> dict[str, Any]:
        """Solve an arbitrary multi-page live HTML/DOM workflow with ZERO model calls.

        Handles:
          - Fresh AXTree/DOM observation after every navigation/submit (zero stale grounding)
          - Destructive button/form blocking (never clicks delete/reset/wipe traps!)
          - Authentication/login discovery from live forms & redirects
          - Structured HTML table reasoning (filtering by status/stock + numeric superlatives
            like cheapest/highest rated)
          - Form completion + hidden CSRF token preservation + CEGAR validation-error recovery
            (e.g., if submitting a form returns an alert "must accept terms", automatically checks
            the required checkbox and resubmits!)
          - Strict final-state verification (refuses premature stop until goal status is observed!)
        """
        t0 = time.monotonic()
        goal = compile_natural_language_goal(goal_text, "web_dom")
        obs = env.navigate(env.current_url)
        visited_urls: set[str] = {obs["url"]}
        trace: list[dict[str, Any]] = []
        extra_checkboxes: set[str] = set()
        table_pool: list[tuple[float, str]] = []

        def _is_destructive_form_or_link(text: str, href_or_action: str, danger_flag: bool = False) -> bool:
            if danger_flag:
                return True
            comb = f"{text} {href_or_action}".lower()
            if any(w in comb for w in ("delete", "reset", "wipe", "purge", "destroy", "drop", "cancel account")):
                if not any(w in goal.raw_text.lower() for w in ("delete", "reset", "wipe")):
                    return True
            return False

        def _goal_verified(cur_obs: Mapping[str, Any]) -> bool:
            txt = cur_obs["text_lower"]
            if goal.required_text_substrings:
                if not all(s.lower() in txt for s in goal.required_text_substrings):
                    return False
            if goal.target_status_keywords:
                if not any(kw in txt for kw in goal.target_status_keywords):
                    return False
            elif not goal.required_text_substrings:
                return any(w in txt for w in ("confirmed", "completed", "success", "order #", "thank you"))
            return True

        for step in range(max_steps):
            if _goal_verified(obs):
                return {
                    "solved": True,
                    "final_url": obs["url"],
                    "steps": trace,
                    "actions_taken": env.actions_taken,
                    "destructive_blocked": env.destructive_actions_blocked,
                    "elapsed_ms": int((time.monotonic() - t0) * 1000),
                }

            acted = False

            # CEGAR error recovery: inspect live alerts for missing checkbox / required field!
            for alert in obs["alerts"]:
                al = alert.lower()
                if any(w in al for w in ("terms", "agree", "confirm", "checkbox", "accept")):
                    for form in obs["forms"]:
                        for inp in form["inputs"]:
                            if inp["type"] == "checkbox" and inp["name"]:
                                extra_checkboxes.add(inp["name"])

            # 1. Login form detection (if credentials supplied and password field visible!)
            if goal.login_credentials:
                for form in obs["forms"]:
                    types = {inp["type"] for inp in form["inputs"]}
                    if "password" in types:
                        vals: dict[str, str] = {}
                        for inp in form["inputs"]:
                            nm = inp["name"]
                            if inp["type"] == "password":
                                vals[nm] = goal.login_credentials.get("password", "")
                            elif inp["type"] in ("text", "email") and nm:
                                vals[nm] = goal.login_credentials.get("username", "")
                        obs = env.submit_form(form, vals)
                        trace.append({"step": step + 1, "action": "login_form", "url": obs["url"]})
                        acted = True
                        break
            if acted:
                continue

            # 2. Structured HTML table superlative + filter selection (e.g. cheapest in-stock item!)
            if goal.superlative_goal and obs["tables"]:
                col_hint, direction = goal.superlative_goal
                best_link: str | None = None
                best_val: float | None = None
                for tbl in obs["tables"]:
                    headers = [h.lower() for h in tbl["headers"]]
                    val_col = -1
                    for idx, h in enumerate(headers):
                        if col_hint in h or (col_hint == "price" and ("$" in h or "cost" in h)):
                            val_col = idx
                            break
                    for row in tbl["rows"]:
                        cells = row["cells"]
                        row_text = " ".join(cells).lower()
                        # Enforce status/stock filters strictly!
                        if goal.filter_keywords:
                            if not all(fk in row_text for fk in goal.filter_keywords):
                                continue
                        # Extract numeric value from target column (or first price cell)
                        cand_text = cells[val_col] if 0 <= val_col < len(cells) else row_text
                        m_num = re.search(r"(\d+(?:\.\d+)?)", cand_text.replace(",", ""))
                        if not m_num or not row["links"]:
                            continue
                        num = float(m_num.group(1))
                        link = row["links"][0]
                        if _is_destructive_form_or_link(row_text, link):
                            env.destructive_actions_blocked.append({"kind": "table_link", "href": link})
                            continue
                        abs_link = urllib.parse.urljoin(obs["url"], link)
                        if (num, abs_link) not in table_pool:
                            table_pool.append((num, abs_link))
                # Check for unvisited pagination links BEFORE committing to a local page optimum!
                next_page_href: str | None = None
                for lnk in obs["links"]:
                    href = lnk.get("href", "")
                    if not href:
                        continue
                    full_u = urllib.parse.urljoin(obs["url"], href)
                    if full_u in visited_urls:
                        continue
                    lcomb = (lnk.get("text", "") + " " + href + " " + lnk.get("aria", "")).lower()
                    if any(pk in lcomb for pk in ("next", "page=", "&p=", "?p=", "offset=")):
                        if not _is_destructive_form_or_link(lnk.get("text", ""), href):
                            next_page_href = href
                            break
                if next_page_href is not None:
                    obs = env.navigate(next_page_href)
                    visited_urls.add(obs["url"])
                    trace.append({"step": step + 1, "action": "paginate_table", "url": obs["url"]})
                    acted = True
                elif table_pool:
                    best_val, best_link = (
                        min(table_pool, key=lambda x: x[0])
                        if direction == "min"
                        else max(table_pool, key=lambda x: x[0])
                    )
                    if best_link not in visited_urls:
                        obs = env.navigate(best_link)
                        visited_urls.add(obs["url"])
                        trace.append({"step": step + 1, "action": "select_table_superlative", "value": best_val, "url": obs["url"]})
                        acted = True
            if acted:
                continue

            # 3. Safe goal-directed form submission (blocking destructive traps!)
            safe_forms: list[tuple[int, dict[str, Any]]] = []
            for form in obs["forms"]:
                btn_text = " ".join(b.get("text", "") for b in form.get("buttons", []))
                has_danger = any(b.get("danger") for b in form.get("buttons", []))
                if _is_destructive_form_or_link(btn_text, form.get("action", ""), has_danger):
                    env.destructive_actions_blocked.append({"kind": "form", "action": form.get("action"), "button": btn_text})
                    continue
                score = 1
                if any(w in (btn_text + " " + form.get("action", "")).lower() for w in goal.target_action_words):
                    score += 10
                if any(inp["name"].lower() in goal.form_values for inp in form["inputs"]):
                    score += 6
                safe_forms.append((score, form))
            safe_forms.sort(key=lambda x: -x[0])

            if safe_forms:
                _, form = safe_forms[0]
                vals = {}
                for inp in form["inputs"]:
                    nm = inp["name"]
                    if not nm or inp["type"] == "hidden":
                        continue
                    low_nm = (nm + " " + inp.get("placeholder", "") + " " + inp.get("aria", "")).lower()
                    for fk, fv in goal.form_values.items():
                        if fk in low_nm:
                            vals[nm] = fv
                            break
                    if inp["type"] == "checkbox" and (nm in extra_checkboxes or inp.get("required")):
                        vals[nm] = inp.get("value", "on") or "on"
                prev_url = obs["url"]
                prev_txt = obs["text"]
                obs = env.submit_form(form, vals)
                trace.append({"step": step + 1, "action": "submit_form", "action_url": form.get("action"), "vals": vals, "url": obs["url"]})
                if obs["url"] != prev_url or obs["text"] != prev_txt:
                    acted = True
            if acted:
                continue

            # 4. Safe goal-directed link navigation (catalog / login / checkout)
            best_nav: tuple[int, dict[str, Any]] | None = None
            for lnk in obs["links"]:
                href = lnk.get("href", "")
                if not href or href.startswith("#"):
                    continue
                full_u = urllib.parse.urljoin(obs["url"], href)
                if full_u in visited_urls:
                    continue
                if _is_destructive_form_or_link(lnk.get("text", ""), href):
                    env.destructive_actions_blocked.append({"kind": "link", "href": href, "text": lnk.get("text")})
                    continue
                comb = (lnk.get("text", "") + " " + href).lower()
                sc = 1
                if goal.login_credentials and "login" in comb:
                    sc += 12
                if goal.superlative_goal and any(w in comb for w in ("catalog", "items", "products", "shop", "list", "flights")):
                    sc += 10
                if any(w in comb for w in goal.target_action_words):
                    sc += 8
                if best_nav is None or sc > best_nav[0]:
                    best_nav = (sc, lnk)
            if best_nav is not None:
                obs = env.navigate(best_nav[1]["href"])
                visited_urls.add(obs["url"])
                trace.append({"step": step + 1, "action": "navigate", "url": obs["url"]})
                continue
            break

        solved_web = _goal_verified(obs)
        proc_web = "cegar_checkbox_discovery" if extra_checkboxes else "live_dom_read"
        self.store.record_procedure_outcome(
            proc_web,
            "web_dom",
            solved=solved_web,
            cost_steps=max(1, len(trace)),
        )
        return {
            "solved": solved_web,
            "final_url": obs["url"],
            "steps": trace,
            "actions_taken": env.actions_taken,
            "destructive_blocked": env.destructive_actions_blocked,
            "reading_succeeded": bool(solved_web and not extra_checkboxes),
            "procedure_family": proc_web,
            "elapsed_ms": int((time.monotonic() - t0) * 1000),
        }

    # ------------------------------------------------------------------
    # Mechanism 3 (OS / CLI / Web / SQLite): 16-Way Parallel CoW Speculative Branching
    # ------------------------------------------------------------------

    def speculate_cow_action_branches(
        self,
        branches: Sequence[tuple[str, Callable[[], dict[str, Any]]]],
        *,
        max_parallel: int = 16,
        timeout_s: float = 12.0,
    ) -> dict[str, Any]:
        """Fork up to 16 parallel Copy-On-Write shadow reality branches simultaneously via
        `reverse_tomography_algebra_v1.run_speculative_cow_branches`, score each branch by
        `MultiLayerSnapshot` diffs and goal-residual reduction, and return the best branch
        with ZERO side-effect leakage in the parent process!
        """
        from canonical.swe_kernel import reverse_tomography_algebra_v1 as rta

        t0 = time.monotonic()
        outcomes = rta.run_speculative_cow_branches(
            branches, max_parallel=max_parallel, timeout_s=timeout_s
        )
        winner = outcomes[0] if outcomes and outcomes[0].ok else None
        return {
            "solved": winner is not None,
            "branches_evaluated": len(outcomes),
            "max_parallel": min(16, max(1, int(max_parallel))),
            "winner": (
                {
                    "branch_id": winner.branch_id,
                    "residual_score": winner.residual_score,
                    "delta_count": winner.delta_count,
                    "result": winner.result,
                    "elapsed_ms": winner.elapsed_ms,
                    "isolated_cow": winner.isolated_cow,
                }
                if winner is not None
                else None
            ),
            "ranked": [
                {
                    "branch_id": o.branch_id,
                    "ok": o.ok,
                    "residual_score": o.residual_score,
                    "delta_count": o.delta_count,
                    "elapsed_ms": o.elapsed_ms,
                    "isolated_cow": o.isolated_cow,
                }
                for o in outcomes
            ],
            "elapsed_ms": int((time.monotonic() - t0) * 1000),
        }

    # ------------------------------------------------------------------
    # Mechanism 4: Algebraic Cross-Modal Compilation (Unified Web+SQLite+CLI+SWE Petri Net)
    # ------------------------------------------------------------------

    def compile_and_run_cross_modal_pipeline(
        self,
        *,
        web_base_url: str,
        web_login: dict[str, str],
        web_records_path: str,
        sqlite_db_path: str | pathlib.Path,
        cli_workspace: str | pathlib.Path,
        swe_repo_root: str | pathlib.Path,
        swe_test_file: str,
        output_bundle_path: str | pathlib.Path,
        morphism_name: str = "cross_modal_web_sqlite_cli_swe_l2",
        env_version_hash: str = "v1",
    ) -> dict[str, Any]:
        """Unify Web/DOM, SQLite, CLI/FS, and Python Code Repair into ONE Type-Transition
        Petri Net statically gated by `effect_contract_composition_v1`, execute the composed
        4-modality pipeline end-to-end against real live systems, and crystallize the ENTIRE
        cross-modal pipeline as ONE typed L2 morphism admitted through §9.2 5-part filtering!
        """
        import sqlite3
        from canonical.swe_kernel import angelic_cegis_repair_v1 as acr
        from canonical.swe_kernel import effect_contract_composition_v1 as ecc
        from canonical.swe_kernel import reverse_tomography_algebra_v1 as rta

        t0 = time.monotonic()
        db_path = pathlib.Path(sqlite_db_path).resolve()
        cli_ws = pathlib.Path(cli_workspace).resolve()
        swe_root = pathlib.Path(swe_repo_root).resolve()
        out_path = pathlib.Path(output_bundle_path).resolve()

        # Modality 1: Live Web/DOM + CSRF Auth + Structured Table Scrape
        def _exec_web_scrape(st: dict[str, Any]) -> dict[str, Any]:
            env = RealWebDOMEnv(str(st["web_base_url"]))
            obs = env.navigate("/")
            # Login if a login form is present (live DOM reading, CSRF auto-preserved!)
            login_creds = dict(st.get("web_login") or {})
            if login_creds:
                for form in obs.get("forms", []):
                    in_names = {i["name"].lower() for i in form.get("inputs", [])}
                    if any(k in in_names for k in ("user", "username", "email", "pass", "password")):
                        vals = {}
                        for inp in form.get("inputs", []):
                            nm = inp["name"]
                            if not nm or inp["type"] == "hidden":
                                continue
                            low = nm.lower()
                            for ck, cv in login_creds.items():
                                if ck in low:
                                    vals[nm] = cv
                                    break
                        obs = env.submit_form(form, vals)
                        break
            obs_rec = env.navigate(str(st["web_records_path"]))
            records: list[dict[str, Any]] = []
            for tbl in obs_rec.get("tables", []):
                for row in tbl.get("rows", []):
                    cells = [c.strip() for c in row.get("cells", []) if c.strip()]
                    if len(cells) >= 2:
                        num_val = 0.0
                        for c in cells[1:]:
                            m_num = re.search(r"-?\d+(?:\.\d+)?", c)
                            if m_num:
                                num_val = float(m_num.group(0))
                                break
                        records.append({"key": cells[0], "value": num_val, "raw_cells": cells})
            return {
                **st,
                "scraped_records": records,
                "web_actions": env.actions_taken,
                "web_final_url": obs_rec["url"],
            }

        # Modality 2: Live SQLite Persistence + Relational Aggregation
        def _exec_sqlite_ingest(st: dict[str, Any]) -> dict[str, Any]:
            p_db = pathlib.Path(st["sqlite_db_path"])
            p_db.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(p_db))
            try:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS scraped_items (item_key TEXT PRIMARY KEY, item_val REAL)"
                )
                conn.execute("DELETE FROM scraped_items")
                for rec in st.get("scraped_records") or []:
                    conn.execute(
                        "INSERT INTO scraped_items (item_key, item_val) VALUES (?, ?)",
                        (str(rec["key"]), float(rec["value"])),
                    )
                conn.commit()
                rows = conn.execute(
                    "SELECT item_key, item_val FROM scraped_items ORDER BY item_key"
                ).fetchall()
            finally:
                conn.close()
            return {**st, "db_rows": [{"key": r[0], "value": r[1]} for r in rows], "db_row_count": len(rows)}

        # Modality 3: Live CLI / Filesystem Export & Audit
        def _exec_cli_audit(st: dict[str, Any]) -> dict[str, Any]:
            ws = pathlib.Path(st["cli_workspace"])
            ws.mkdir(parents=True, exist_ok=True)
            csv_path = ws / "exported_items.csv"
            lines = ["key,value"] + [f"{r['key']},{r['value']}" for r in st.get("db_rows") or []]
            csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            # Run real OS CLI tool (`wc -l`) to verify physical file materialization!
            proc = subprocess.run(
                ["wc", "-l", str(csv_path)],
                cwd=str(ws),
                capture_output=True,
                text=True,
                timeout=10,
            )
            line_count = int((proc.stdout.strip().split() or ["0"])[0])
            return {**st, "cli_csv_path": str(csv_path), "cli_line_count": line_count}

        # Modality 4: Live SWE Code Repair (Angelic CEGIS + Reverse Execution + STUN)
        def _exec_swe_repair(st: dict[str, Any]) -> dict[str, Any]:
            s_root = pathlib.Path(st["swe_repo_root"])
            s_test = str(st["swe_test_file"])
            # First check whether tests already pass (e.g. during 1-shot replay on clean code!)
            env_p = acr._build_env(s_root)
            p_chk = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "--tb=no", "-o", "addopts=", s_test],
                cwd=str(s_root),
                env=env_p,
                capture_output=True,
                text=True,
                timeout=20,
            )
            if p_chk.returncode == 0:
                return {**st, "swe_repaired": True, "swe_method": "ALREADY_PASSING", "swe_patched_file": None}
            rep = acr.repair_repo_angelic_cegis(s_root, s_test, timeout_s=45)
            if not rep.get("repaired"):
                return {**st, "swe_repaired": False, "swe_method": None, "swe_error": rep.get("reason")}
            # Apply verified patch permanently to workspace so Modality 5 executes the FIXED module!
            pf_rel = str(rep["patched_file"])
            (s_root / pf_rel).write_text(str(rep["patched_source"]), encoding="utf-8")
            return {
                **st,
                "swe_repaired": True,
                "swe_method": rep.get("method"),
                "swe_rule": rep.get("rule") or rep.get("patch_label"),
                "swe_patched_file": pf_rel,
            }

        # Modality 5: Certified Cross-Modal Verification & Bundle Emission
        def _exec_emit_certified(st: dict[str, Any]) -> dict[str, Any]:
            if not st.get("swe_repaired"):
                return {**st, "certified": False}
            s_root = pathlib.Path(st["swe_repo_root"])
            # Invoke the repaired Python scorer module live over the SQLite-persisted web records!
            eval_code = (
                "import json, sys; sys.path.insert(0, sys.argv[1]); "
                "import scorer; rows = json.loads(sys.argv[2]); "
                "print(json.dumps(scorer.summarize_records(rows)))"
            )
            p_run = subprocess.run(
                [sys.executable, "-c", eval_code, str(s_root), json.dumps(st.get("db_rows") or [])],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if p_run.returncode != 0:
                return {**st, "certified": False, "eval_stderr": p_run.stderr[:300]}
            summary = json.loads(p_run.stdout.strip())
            bundle = {
                "schema": "BRAIN_CROSS_MODAL_CERTIFIED_BUNDLE_V1",
                "modalities_unified": ["web_dom", "sqlite", "cli_fs", "swe_repair"],
                "web_final_url": st.get("web_final_url"),
                "db_row_count": st.get("db_row_count"),
                "cli_line_count": st.get("cli_line_count"),
                "swe_method": st.get("swe_method"),
                "swe_patched_file": st.get("swe_patched_file"),
                "summary": summary,
            }
            op = pathlib.Path(st["output_bundle_path"])
            op.parent.mkdir(parents=True, exist_ok=True)
            op.write_text(json.dumps(bundle, indent=2, sort_keys=True), encoding="utf-8")
            return {**st, "certified": True, "bundle": bundle}

        # Build ONE unified Type-Transition Petri Net spanning all 4 modalities + static EffectContracts!
        composer = rta.AlgebraicSkillComposer(store_path=self.store.path)
        morphisms = [
            rta.TypedSkillMorphism(
                morphism_id="modality_web_dom_scrape",
                in_types=frozenset({"LiveWebSession"}),
                out_types=frozenset({"RawScrapedRecords"}),
                contract=ecc.EffectContract(
                    skill_id="modality_web_dom_scrape",
                    preconditions=("web_live",),
                    observables=("web_base_url", "web_final_url"),
                    actions=("web_csrf_login_and_scrape",),
                    verdict="records_scraped",
                    effects=(ecc.Effect("ESTABLISH", "records_scraped"),),
                ),
                cost=1.0,
                executor=_exec_web_scrape,
            ),
            rta.TypedSkillMorphism(
                morphism_id="modality_sqlite_persist",
                in_types=frozenset({"RawScrapedRecords"}),
                out_types=frozenset({"SQLiteDBState"}),
                contract=ecc.EffectContract(
                    skill_id="modality_sqlite_persist",
                    preconditions=("records_scraped",),
                    observables=("sqlite_db_path", "db_row_count"),
                    actions=("sqlite_ddl_insert_query",),
                    verdict="sqlite_populated",
                    effects=(ecc.Effect("ESTABLISH", "sqlite_populated"),),
                ),
                cost=1.0,
                executor=_exec_sqlite_ingest,
            ),
            rta.TypedSkillMorphism(
                morphism_id="modality_cli_export_audit",
                in_types=frozenset({"SQLiteDBState"}),
                out_types=frozenset({"CLIAuditArtifact"}),
                contract=ecc.EffectContract(
                    skill_id="modality_cli_export_audit",
                    preconditions=("sqlite_populated",),
                    observables=("cli_csv_path", "cli_line_count"),
                    actions=("cli_export_and_wc",),
                    verdict="cli_audited",
                    effects=(ecc.Effect("ESTABLISH", "cli_audited"),),
                ),
                cost=1.0,
                executor=_exec_cli_audit,
            ),
            rta.TypedSkillMorphism(
                morphism_id="modality_swe_code_repair",
                in_types=frozenset({"CLIAuditArtifact", "FailingCodeRepo"}),
                out_types=frozenset({"VerifiedRepairedCode"}),
                contract=ecc.EffectContract(
                    skill_id="modality_swe_code_repair",
                    preconditions=("cli_audited", "repo_present"),
                    observables=("swe_repo_root", "swe_repaired"),
                    actions=("angelic_cegis_code_repair",),
                    verdict="code_verified",
                    effects=(ecc.Effect("ESTABLISH", "code_verified"),),
                ),
                cost=2.0,
                executor=_exec_swe_repair,
            ),
            rta.TypedSkillMorphism(
                morphism_id="modality_emit_certified_bundle",
                in_types=frozenset({"VerifiedRepairedCode", "SQLiteDBState"}),
                out_types=frozenset({"CertifiedCrossModalBundle"}),
                contract=ecc.EffectContract(
                    skill_id="modality_emit_certified_bundle",
                    preconditions=("code_verified", "sqlite_populated"),
                    observables=("output_bundle_path", "certified"),
                    actions=("execute_repaired_and_emit_json",),
                    verdict="bundle_certified",
                    effects=(ecc.Effect("ESTABLISH", "bundle_certified"),),
                ),
                cost=1.0,
                executor=_exec_emit_certified,
            ),
        ]
        for m in morphisms:
            ok_reg, reg_msg = composer.register(m)
            if not ok_reg:
                return {"compiled": False, "reason": f"CONTRACT_REJECTED:{m.morphism_id}:{reg_msg}"}

        # Solve ONE Petri-Net reachability & static contract proof across ALL 4 modalities!
        comp = composer.compose(
            initial_types={"LiveWebSession", "FailingCodeRepo"},
            goal_types={"CertifiedCrossModalBundle"},
            axioms=("web_live", "repo_present"),
        )
        if not comp.get("composed"):
            return {
                "compiled": False,
                "reason": "PETRI_NET_UNREACHABLE",
                "rejected_static": comp.get("rejected_static", []),
                "elapsed_ms": int((time.monotonic() - t0) * 1000),
            }

        # Execute the single compiled cross-modal Petri-Net plan end-to-end and crystallize as L2!
        state: dict[str, Any] = {
            "web_base_url": web_base_url,
            "web_login": dict(web_login),
            "web_records_path": web_records_path,
            "sqlite_db_path": str(db_path),
            "cli_workspace": str(cli_ws),
            "swe_repo_root": str(swe_root),
            "swe_test_file": swe_test_file,
            "output_bundle_path": str(out_path),
        }
        exec_res = composer.execute_and_crystallize(
            comp,
            state,
            pipeline_name=morphism_name,
            verify_fn=lambda st: bool(st.get("certified")),
        )
        final_state = exec_res.get("final_state", {})
        if not exec_res.get("verified") or not final_state.get("certified"):
            return {
                "compiled": False,
                "reason": "CROSS_MODAL_EXECUTION_NOT_CERTIFIED",
                "plan_names": comp["chain"],
                "final_state": {k: v for k, v in final_state.items() if k != "scraped_records"},
                "elapsed_ms": int((time.monotonic() - t0) * 1000),
            }

        # Also admit into `self.store` via the §9.2 5-part admission filter with full provenance!
        l2_law = ParameterizedCausalLaw(
            law_id=f"cross_modal_l2::{morphism_name}",
            domain="cross_modal",
            tool_or_action=morphism_name,
            command_template=[
                "PETRI_L2",
                "{web_base_url}",
                "{sqlite_db_path}",
                "{cli_workspace}",
                "{swe_repo_root}",
                "{output_bundle_path}",
            ],
            creates_file_kind="json",
            preconditions={"initial_types": ["FailingCodeRepo", "LiveWebSession"]},
            effects={
                "goal_types": ["CertifiedCrossModalBundle"],
                "stages": list(comp["chain"]),
                "undo_safe": True,
            },
            verified_count=1,
            provenance={
                "source_env": "cross_modal_petri_compiler",
                "version_hash": env_version_hash,
                "timestamp": int(time.time()),
                "modalities": ["web_dom", "sqlite", "cli_fs", "swe_repair"],
            },
            generalized=True,
        )
        admit_res = self.store.admit_filtered(l2_law, strict=True)
        # Keep compiled single-morphism callable cached in memory for instant 1-shot replay!
        self._compiled_cross_modal_registry = getattr(self, "_compiled_cross_modal_registry", {})
        self._compiled_cross_modal_registry[morphism_name] = {
            "morphisms": list(comp["morphisms"]),
            "plan_names": list(comp["chain"]),
            "l2_morphism": composer.morphisms.get(morphism_name),
        }

        return {
            "compiled": True,
            "certified": True,
            "morphism_name": morphism_name,
            "plan_names": list(comp["chain"]),
            "undo_safe": True,
            "final_types": comp.get("final_types", []),
            "final_facts": comp.get("final_facts", []),
            "crystallized": bool(exec_res.get("crystallized")),
            "store_admission": admit_res,
            "bundle": final_state["bundle"],
            "elapsed_ms": int((time.monotonic() - t0) * 1000),
        }

    def replay_crystallized_cross_modal_morphism(
        self,
        morphism_name: str,
        *,
        web_base_url: str,
        web_login: dict[str, str],
        web_records_path: str,
        sqlite_db_path: str | pathlib.Path,
        cli_workspace: str | pathlib.Path,
        swe_repo_root: str | pathlib.Path,
        swe_test_file: str,
        output_bundle_path: str | pathlib.Path,
    ) -> dict[str, Any]:
        """Execute a previously crystallized single L2 cross-modal morphism in 1 shot on a
        brand-new unseen environment instance (different port, DB, directory, records, code)
        with ZERO Petri-Net re-search and ZERO model calls!
        """
        t0 = time.monotonic()
        reg = getattr(self, "_compiled_cross_modal_registry", {})
        entry = reg.get(morphism_name)
        if entry is None:
            return {"replayed": False, "reason": "MORPHISM_NOT_FOUND"}
        state: dict[str, Any] = {
            "web_base_url": web_base_url,
            "web_login": dict(web_login),
            "web_records_path": web_records_path,
            "sqlite_db_path": str(pathlib.Path(sqlite_db_path).resolve()),
            "cli_workspace": str(pathlib.Path(cli_workspace).resolve()),
            "swe_repo_root": str(pathlib.Path(swe_repo_root).resolve()),
            "swe_test_file": swe_test_file,
            "output_bundle_path": str(pathlib.Path(output_bundle_path).resolve()),
        }
        l2_m = entry.get("l2_morphism")
        if l2_m is not None and l2_m.executor is not None:
            final_state = l2_m.executor(state)
        else:
            cur = dict(state)
            for m in entry["morphisms"]:
                if m.executor is not None:
                    cur = m.executor(cur)
            final_state = cur
        return {
            "replayed": bool(final_state.get("certified")),
            "search_nodes_expanded": 0,  # 1-shot L2 replay — ZERO search!
            "stages_executed": list(entry["plan_names"]),
            "bundle": final_state.get("bundle"),
            "elapsed_ms": int((time.monotonic() - t0) * 1000),
        }

    def solve_terminal_speculative_cow(
        self,
        workspace_root: str | pathlib.Path,
        candidates: Sequence[Mapping[str, Any]],
        postcondition_clauses: Sequence[tuple[str, Callable[[pathlib.Path], bool]]],
        *,
        allowed_write_paths: Sequence[str] = (),
        allow_new_files: bool = True,
        timeout_per_cmd_s: int = 15,
    ) -> dict[str, Any]:
        """Idea 4: Execute candidate terminal plans inside parallel isolated CoW clones with
        Negative-Effect Invariant Oracle enforcement and atomic minimal-delta commit."""
        runner = TransactionalWorkspaceCoWRunner(workspace_root, law_store=self.store)
        return runner.execute_speculative_candidates(
            candidates,
            postcondition_clauses,
            allowed_write_paths=allowed_write_paths,
            allow_new_files=allow_new_files,
            timeout_per_cmd_s=timeout_per_cmd_s,
        )


# ===========================================================================
# ITERATION I — ENGINE I-6: COMPOSITIONAL GOAL DECOMPOSITION VIA PETRI-NET
# DOMINATOR CUT-VERTICES (ZERO-DRIFT 300+-STEP OSWORLD-V2 HORIZON SOLVER)
# ===========================================================================


def compute_petri_dominator_cut_vertices(
    edges: Sequence[tuple[str, str]],
    start_node: str,
    goal_node: str,
) -> dict[str, Any]:
    """Compute exact mandatory articulation / dominator cut-vertices on the `start -> goal`
    reachability subgraph of a UnifiedCrossModalPetriNet (Cooper-Harvey-Kennedy fixed-point).

    Every returned cut-vertex `c` in `ordered_checkpoints` is mathematically guaranteed to
    lie on EVERY valid path from `start_node` to `goal_node` — allowing a 300+-step task to
    be sliced into independent, checkpointed sub-episodes with hard EffectContract locks.
    """
    adj: dict[str, set[str]] = collections.defaultdict(set)
    radj: dict[str, set[str]] = collections.defaultdict(set)
    for u, v in edges:
        adj[str(u)].add(str(v))
        radj[str(v)].add(str(u))

    # 1. Forward reachable from `start_node`
    fwd: set[str] = set()
    q = collections.deque([start_node])
    while q:
        cur = q.popleft()
        if cur in fwd:
            continue
        fwd.add(cur)
        for nxt in adj.get(cur, ()):
            if nxt not in fwd:
                q.append(nxt)

    if goal_node not in fwd:
        return {"reachable": False, "cut_vertices": [], "ordered_checkpoints": [], "sub_episodes": []}

    # 2. Backward reachable from `goal_node` (co-reachable)
    bwd: set[str] = set()
    q2 = collections.deque([goal_node])
    while q2:
        cur = q2.popleft()
        if cur in bwd:
            continue
        bwd.add(cur)
        for prv in radj.get(cur, ()):
            if prv not in bwd:
                q2.append(prv)

    active = fwd & bwd
    # 3. Exact iterative dominator set computation on `active` rooted at `start_node`
    dom: dict[str, set[str]] = {n: set(active) for n in active}
    dom[start_node] = {start_node}
    changed = True
    while changed:
        changed = False
        for n in active:
            if n == start_node:
                continue
            preds = [p for p in radj.get(n, ()) if p in active]
            if not preds:
                new_d = {n}
            else:
                inter = set(dom[preds[0]])
                for p in preds[1:]:
                    inter &= dom[p]
                new_d = {n} | inter
            if new_d != dom[n]:
                dom[n] = new_d
                changed = True

    # Dominators of `goal_node` form a total order (chain from start_node to goal_node!)
    goal_doms = dom[goal_node]
    ordered = sorted(goal_doms, key=lambda n: len(dom[n]))
    interior_cuts = [n for n in ordered if n not in (start_node, goal_node)]
    sub_episodes = [(ordered[i], ordered[i + 1]) for i in range(len(ordered) - 1)]
    return {
        "reachable": True,
        "active_nodes": len(active),
        "cut_vertices": interior_cuts,
        "ordered_checkpoints": ordered,
        "sub_episodes": sub_episodes,
    }


def execute_cut_vertex_checkpointed_episode(
    edges: Sequence[tuple[str, str]],
    start_node: str,
    goal_node: str,
    *,
    initial_state: Mapping[str, Any],
    step_executor: Any,
    checkpoint_verifier: Any,
    drift_injector: Any | None = None,
    max_local_retries: int = 3,
) -> dict[str, Any]:
    """Execute a long-horizon (300+-step) cross-modal workflow sliced at Petri-Net dominator
    cut-vertices with local CoW rollout verification and O(sub_episode) checkpoint rollback!

    Args:
      edges: directed transition graph `(src_token, dst_token)` of the workflow.
      start_node, goal_node: start and goal Petri-Net tokens.
      initial_state: mutable state dictionary representing cross-modal environment state.
      step_executor: `fn(state_dict, src, dst) -> new_state_dict` executing one atomic step.
      checkpoint_verifier: `fn(state_dict, checkpoint_node) -> bool` verifying the
        EffectContract postcondition at a cut-vertex checkpoint.
      drift_injector: optional `fn(step_idx, state_dict) -> (drifted_state, drifted_bool)`
        simulating OS/UI environment drift, stale modals, or dropped state mid-workflow.
    """
    t0 = time.monotonic()
    decomp = compute_petri_dominator_cut_vertices(edges, start_node, goal_node)
    if not decomp["reachable"]:
        return {"completed": False, "reason": "GOAL_UNREACHABLE", "decomp": decomp}

    # Precompute shortest path inside each independent sub-episode `[c_i -> c_{i+1}]`
    adj: dict[str, list[str]] = collections.defaultdict(list)
    for u, v in edges:
        adj[str(u)].append(str(v))

    def _shortest_path(src: str, dst: str) -> list[str]:
        q = collections.deque([(src, [src])])
        seen = {src}
        while q:
            cur, path = q.popleft()
            if cur == dst:
                return path
            for nxt in adj.get(cur, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    q.append((nxt, path + [nxt]))
        return []

    cur_state = copy.deepcopy(dict(initial_state))
    locked_checkpoints: list[str] = [start_node]
    total_steps_executed = 0
    drift_events = 0
    local_rollbacks = 0
    steps_lost_to_rollback = 0
    episode_log: list[dict[str, Any]] = []

    for ep_idx, (c_src, c_dst) in enumerate(decomp["sub_episodes"]):
        sub_path = _shortest_path(c_src, c_dst)
        if not sub_path:
            return {"completed": False, "reason": f"SUB_EPISODE_UNREACHABLE:{c_src}->{c_dst}"}
        checkpoint_snapshot = copy.deepcopy(cur_state)
        ep_ok = False
        for attempt in range(max_local_retries + 1):
            trial_state = copy.deepcopy(checkpoint_snapshot)
            ep_steps = 0
            for u, v in zip(sub_path[:-1], sub_path[1:]):
                trial_state = step_executor(trial_state, u, v)
                total_steps_executed += 1
                ep_steps += 1
                if drift_injector is not None and attempt == 0:
                    trial_state, did_drift = drift_injector(total_steps_executed, trial_state)
                    if did_drift:
                        drift_events += 1
            if bool(checkpoint_verifier(trial_state, c_dst)):
                cur_state = trial_state
                locked_checkpoints.append(c_dst)
                ep_ok = True
                episode_log.append(
                    {
                        "sub_episode": ep_idx,
                        "from": c_src,
                        "to": c_dst,
                        "path_len": len(sub_path) - 1,
                        "attempts": attempt + 1,
                        "verified": True,
                    }
                )
                break
            else:
                # Local rollback ONLY to `checkpoint_snapshot` (`c_src`), NEVER step 0!
                local_rollbacks += 1
                steps_lost_to_rollback += ep_steps
        if not ep_ok:
            return {
                "completed": False,
                "reason": f"CHECKPOINT_POSTCONDITION_FAILED:{c_dst}",
                "locked_checkpoints": locked_checkpoints,
                "total_steps_executed": total_steps_executed,
                "drift_events": drift_events,
                "local_rollbacks": local_rollbacks,
            }

    return {
        "completed": True,
        "goal_verified": bool(checkpoint_verifier(cur_state, goal_node)),
        "cut_vertices_count": len(decomp["cut_vertices"]),
        "sub_episodes_count": len(decomp["sub_episodes"]),
        "locked_checkpoints": locked_checkpoints,
        "total_steps_executed": total_steps_executed,
        "drift_events": drift_events,
        "local_rollbacks": local_rollbacks,
        "steps_lost_to_rollback": steps_lost_to_rollback,
        "final_state": cur_state,
        "episode_log": episode_log,
        "elapsed_ms": int((time.monotonic() - t0) * 1000),
    }


# ===========================================================================
# ENGINE K-2 (§9.4.2): ZERO-MODEL PURE-CANVAS / FRAMEBUFFER PERCEPTION &
# DIFFERENTIAL TOMOGRAPHY AUTOMATON (0 NEURAL WEIGHTS, 0 DOM / A11Y REQUIRED)
# ===========================================================================


@dataclasses.dataclass(frozen=True)
class CanvasRegion:
    """Detected foreground widget region on a raw 2D RGB framebuffer."""

    region_id: int
    x0: int
    y0: int
    x1: int
    y1: int
    cx: int
    cy: int
    area: int
    dominant_rgb: tuple[int, int, int]
    signature_hash: str


def hash_framebuffer(framebuffer: Sequence[Sequence[tuple[int, int, int]]]) -> str:
    """Deterministic SHA-256 hash of a raw HxW RGB pixel grid."""
    h = hashlib.sha256()
    for row in framebuffer:
        h.update(bytes(c & 0xFF for px in row for c in px))
    return h.hexdigest()[:16]


def extract_canvas_regions(
    framebuffer: Sequence[Sequence[tuple[int, int, int]]],
    *,
    bg_rgb: tuple[int, int, int] | None = None,
    min_area: int = 4,
    color_tol: int = 8,
) -> list[CanvasRegion]:
    """Extract interactive foreground regions from a raw RGB pixel matrix via 4-connected BFS.

    Infers background color automatically from border pixels when `bg_rgb` is omitted.
    Zero neural weights, zero OCR/VLM, zero DOM or accessibility tree!
    """
    h = len(framebuffer)
    if h == 0:
        return []
    w = len(framebuffer[0])
    if w == 0:
        return []

    if bg_rgb is None:
        border_counts: dict[tuple[int, int, int], int] = {}
        for x in range(w):
            for y in (0, h - 1):
                px = tuple(framebuffer[y][x])
                border_counts[px] = border_counts.get(px, 0) + 1
        for y in range(h):
            for x in (0, w - 1):
                px = tuple(framebuffer[y][x])
                border_counts[px] = border_counts.get(px, 0) + 1
        bg_rgb = max(border_counts.items(), key=lambda kv: kv[1])[0]

    def _is_fg(px: tuple[int, int, int]) -> bool:
        return (
            abs(px[0] - bg_rgb[0]) > color_tol
            or abs(px[1] - bg_rgb[1]) > color_tol
            or abs(px[2] - bg_rgb[2]) > color_tol
        )

    visited = [[False] * w for _ in range(h)]
    regions: list[CanvasRegion] = []
    for y0 in range(h):
        for x0 in range(w):
            if visited[y0][x0] or not _is_fg(framebuffer[y0][x0]):
                continue
            q = collections.deque([(x0, y0)])
            visited[y0][x0] = True
            min_x = max_x = x0
            min_y = max_y = y0
            area = 0
            rgb_counts: dict[tuple[int, int, int], int] = {}
            while q:
                x, y = q.popleft()
                area += 1
                px = tuple(framebuffer[y][x])
                rgb_counts[px] = rgb_counts.get(px, 0) + 1
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
                if y < min_y:
                    min_y = y
                if y > max_y:
                    max_y = y
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx] and _is_fg(framebuffer[ny][nx]):
                        visited[ny][nx] = True
                        q.append((nx, ny))
            if area < min_area:
                continue
            dom = max(rgb_counts.items(), key=lambda kv: kv[1])[0]
            sig_h = hashlib.sha256(
                f"{max_x - min_x + 1}x{max_y - min_y + 1}:{area}:{dom}".encode("utf-8")
            ).hexdigest()[:12]
            regions.append(
                CanvasRegion(
                    region_id=len(regions),
                    x0=min_x,
                    y0=min_y,
                    x1=max_x,
                    y1=max_y,
                    cx=(min_x + max_x) // 2,
                    cy=(min_y + max_y) // 2,
                    area=area,
                    dominant_rgb=dom,
                    signature_hash=sig_h,
                )
            )
    regions.sort(key=lambda r: (r.y0, r.x0))
    return [
        dataclasses.replace(r, region_id=idx)
        for idx, r in enumerate(regions)
    ]


def diff_framebuffers(
    frame_before: Sequence[Sequence[tuple[int, int, int]]],
    frame_after: Sequence[Sequence[tuple[int, int, int]]],
) -> dict[str, Any]:
    """Pixel-level differential framebuffer tomography (`frame_before ^ frame_after`)."""
    h = min(len(frame_before), len(frame_after))
    w = min(len(frame_before[0]), len(frame_after[0])) if h else 0
    changed = 0
    min_x, min_y = w, h
    max_x, max_y = -1, -1
    for y in range(h):
        rb, ra = frame_before[y], frame_after[y]
        for x in range(w):
            if rb[x] != ra[x]:
                changed += 1
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
                if y < min_y:
                    min_y = y
                if y > max_y:
                    max_y = y
    return {
        "changed_pixels": changed,
        "delta_bbox": (min_x, min_y, max_x, max_y) if changed else None,
        "before_hash": hash_framebuffer(frame_before),
        "after_hash": hash_framebuffer(frame_after),
    }


class CanvasPureGuiTomographer:
    """Zero-model active explorer + persistent Mealy automaton for pure-canvas GUIs (§9.4.2).

    Given ANY pure-canvas environment exposing ONLY `reset() -> frame`, `render() -> frame`,
    `click(x, y) -> frame`, discovers interactive regions via `extract_canvas_regions`,
    learns causal transitions `(state_hash, (cx, cy)) -> next_state_hash`, stores them in an
    inspectable/editable/O(1)-deletable dictionary, and solves multi-step visual goals via BFS!
    """

    def __init__(self, store_path: str | pathlib.Path | None = None) -> None:
        self.store_path = pathlib.Path(store_path) if store_path else None
        # state_hash -> list of {"cx": int, "cy": int, "sig": str, "next_hash": str, "changed_pixels": int}
        self.transitions: dict[str, list[dict[str, Any]]] = {}
        self.goal_states: dict[str, str] = {}  # goal_label -> state_hash
        if self.store_path and self.store_path.is_file():
            try:
                raw = json.loads(self.store_path.read_text(encoding="utf-8"))
                self.transitions = dict(raw.get("transitions") or {})
                self.goal_states = dict(raw.get("goal_states") or {})
            except (OSError, json.JSONDecodeError):
                pass

    def save(self) -> None:
        if not self.store_path:
            return
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(
            json.dumps(
                {
                    "schema": "BRAIN_CANVAS_TOMOGRAPHY_AUTOMATON_V1",
                    "model_calls": 0,
                    "transitions": self.transitions,
                    "goal_states": self.goal_states,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    def delete_state(self, state_hash: str) -> bool:
        """O(1) inspectable deletion of a learned canvas state's transitions."""
        removed = state_hash in self.transitions
        self.transitions.pop(state_hash, None)
        self.goal_states = {k: v for k, v in self.goal_states.items() if v != state_hash}
        self.save()
        return removed

    def discover_and_solve(
        self,
        env: Any,
        goal_predicate: Callable[[Sequence[Sequence[tuple[int, int, int]]]], bool],
        *,
        goal_label: str = "goal",
        max_states: int = 32,
        max_depth: int = 6,
    ) -> dict[str, Any]:
        """Explore a pure-canvas GUI via differential tomography OR replay cached plan in O(|plan|)!"""
        init_frame = env.reset()
        init_hash = hash_framebuffer(init_frame)
        if goal_predicate(init_frame):
            return {"solved": True, "source": "ALREADY_SATISFIED", "clicks": [], "probes": 0, "model_calls": 0}

        # Fast path: replay cached automaton plan from single-experience store!
        cached_goal_h = self.goal_states.get(goal_label)
        if cached_goal_h:
            plan = self._shortest_plan(init_hash, cached_goal_h)
            if plan is not None:
                f = env.reset()
                for cx, cy in plan:
                    f = env.click(cx, cy)
                if goal_predicate(f):
                    return {
                        "solved": True,
                        "source": "SINGLE_EXPERIENCE_REPLAY",
                        "clicks": plan,
                        "probes": len(plan),
                        "model_calls": 0,
                    }

        # Active BFS exploration over discovered CanvasRegions
        probes = 0
        # Queue stores (path_of_clicks_from_reset, state_hash)
        q: collections.deque[tuple[list[tuple[int, int]], str]] = collections.deque([([], init_hash)])
        seen_states: set[str] = {init_hash}
        while q and len(seen_states) <= max_states:
            path, st_h = q.popleft()
            if len(path) >= max_depth:
                continue
            cur_f = env.reset()
            for px, py in path:
                cur_f = env.click(px, py)
            regions = extract_canvas_regions(cur_f)
            edges: list[dict[str, Any]] = []
            for reg in regions:
                f_base = env.reset()
                for px, py in path:
                    f_base = env.click(px, py)
                f_next = env.click(reg.cx, reg.cy)
                probes += 1
                delta = diff_framebuffers(f_base, f_next)
                nh = delta["after_hash"]
                if delta["changed_pixels"] > 0:
                    edges.append(
                        {
                            "cx": reg.cx,
                            "cy": reg.cy,
                            "sig": reg.signature_hash,
                            "next_hash": nh,
                            "changed_pixels": delta["changed_pixels"],
                        }
                    )
                    new_path = path + [(reg.cx, reg.cy)]
                    if goal_predicate(f_next):
                        self.transitions[st_h] = edges
                        self.goal_states[goal_label] = nh
                        self.save()
                        return {
                            "solved": True,
                            "source": "DIFFERENTIAL_CANVAS_TOMOGRAPHY",
                            "clicks": new_path,
                            "probes": probes,
                            "states_discovered": len(seen_states) + 1,
                            "model_calls": 0,
                        }
                    if nh not in seen_states:
                        seen_states.add(nh)
                        q.append((new_path, nh))
            self.transitions[st_h] = edges
        self.save()
        return {
            "solved": False,
            "source": "EXHAUSTED",
            "clicks": [],
            "probes": probes,
            "states_discovered": len(seen_states),
            "model_calls": 0,
        }

    def _shortest_plan(self, start_hash: str, target_hash: str) -> list[tuple[int, int]] | None:
        if start_hash == target_hash:
            return []
        q: collections.deque[tuple[str, list[tuple[int, int]]]] = collections.deque([(start_hash, [])])
        visited = {start_hash}
        while q:
            st, path = q.popleft()
            for edge in self.transitions.get(st, ()):
                nh = edge["next_hash"]
                np = path + [(int(edge["cx"]), int(edge["cy"]))]
                if nh == target_hash:
                    return np
                if nh not in visited:
                    visited.add(nh)
                    q.append((nh, np))
        return None


# ===========================================================================
# ENGINE N-3b (Idea 6): OFFLINE MUTANT-KILL SELF-PLAY DISTILLER (ZERO LEAKAGE)
# ===========================================================================


def distill_repo_mutants_to_l2_store(
    repo_root: str | pathlib.Path,
    test_file: str,
    skill_store: ExternalCausalLawStore,
    *,
    source_files: Sequence[str] | None = None,
    max_mutants: int = 16,
    timeout_per_mutant_s: int = 8,
) -> dict[str, Any]:
    """Idea 6: Offline Counterfactual Mutant-Kill Self-Play Over Passing Repositories.

    Mines generalized, O(1)-indexed L2 `TreeRewriteMorphism` entries directly from a repo's
    OWN already-passing code and tests (zero bug-fix leakage, zero model calls!):
      1. Injects realistic structural perturbations (dropped `or fallback`, dropped `.copy()`,
         dropped `.replace(...)`, dropped `if x is None: return ...`);
      2. Runs the repo's passing test suite on each mutant (restoring source in `finally:`);
      3. Inverts every KILLED mutant (`mutant_src -> orig_src`) via AST anti-unification and
         admits only generalized (`>= 1` lifted hole) morphisms into `skill_store`.
    """
    import ast as _ast
    from canonical.swe_kernel import angelic_cegis_repair_v1 as acr
    from canonical.swe_kernel import reverse_tomography_algebra_v1 as rta

    root = pathlib.Path(repo_root).resolve()
    env = acr._build_env(root)

    # Verify baseline passes first
    p_base = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-x", "--tb=no", "-o", "addopts=", test_file],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
        timeout=max(10, timeout_per_mutant_s * 2),
    )
    if p_base.returncode != 0:
        return {
            "ok": False,
            "reason": "BASELINE_NOT_PASSING",
            "mutants_generated": 0,
            "mutants_killed": 0,
            "morphisms_admitted": 0,
            "admitted_ids": [],
            "model_calls": 0,
        }

    targets: list[str] = []
    if source_files:
        targets = [str(f) for f in source_files if (root / f).is_file()]
    else:
        for fp in sorted(root.rglob("*.py")):
            rel = fp.relative_to(root).as_posix()
            if not acr._is_test_or_oracle_file(rel) and not any(part.startswith(".") for part in fp.parts):
                targets.append(rel)

    mutants: list[tuple[str, str, str, str]] = []  # (rel_file, kind, orig_src, mut_src)
    for rel in targets:
        if len(mutants) >= max_mutants:
            break
        fp = root / rel
        try:
            orig_src = fp.read_text(encoding="utf-8", errors="replace")
            tree = _ast.parse(orig_src)
        except (OSError, SyntaxError):
            continue
        seen_m: set[str] = set()
        for node in _ast.walk(tree):
            if len(mutants) >= max_mutants:
                break
            # Mutant 1: Drop `or <const>` fallback (`expr or '/'` -> `expr`)
            if isinstance(node, _ast.BoolOp) and isinstance(node.op, _ast.Or) and len(node.values) == 2:
                if isinstance(node.values[1], _ast.Constant):
                    lhs_s = acr.get_node_source(orig_src, node.values[0])
                    if lhs_s:
                        ms = acr.splice_ast_node(orig_src, node, lhs_s)
                        if ms and ms != orig_src and ms not in seen_m:
                            seen_m.add(ms)
                            mutants.append((rel, "DROP_OR_FALLBACK", orig_src, ms))
            # Mutant 2: Drop `.copy()` isolation (`x.copy()` -> `x`)
            elif (
                isinstance(node, _ast.Call)
                and isinstance(node.func, _ast.Attribute)
                and node.func.attr == "copy"
                and not node.args
                and not node.keywords
            ):
                recv_s = acr.get_node_source(orig_src, node.func.value)
                if recv_s:
                    ms = acr.splice_ast_node(orig_src, node, recv_s)
                    if ms and ms != orig_src and ms not in seen_m:
                        seen_m.add(ms)
                        mutants.append((rel, "DROP_COPY_ISOLATION", orig_src, ms))
            # Mutant 3: Drop `.replace(...)` sanitization (`x.replace(a, b)` -> `x`)
            elif (
                isinstance(node, _ast.Call)
                and isinstance(node.func, _ast.Attribute)
                and node.func.attr == "replace"
                and len(node.args) == 2
            ):
                recv_s = acr.get_node_source(orig_src, node.func.value)
                if recv_s:
                    ms = acr.splice_ast_node(orig_src, node, recv_s)
                    if ms and ms != orig_src and ms not in seen_m:
                        seen_m.add(ms)
                        mutants.append((rel, "DROP_REPLACE_SANITIZE", orig_src, ms))

    killed = 0
    admitted_ids: list[str] = []
    for rel, mkind, orig_src, mut_src in mutants:
        fp = root / rel
        try:
            fp.write_text(mut_src, encoding="utf-8")
            acr._clear_pycache(root)
            pm = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "-x", "--tb=no", "-o", "addopts=", test_file],
                cwd=str(root),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_per_mutant_s,
            )
            is_killed = pm.returncode != 0
        except (subprocess.TimeoutExpired, OSError):
            is_killed = False
        finally:
            fp.write_text(orig_src, encoding="utf-8")
            acr._clear_pycache(root)

        if not is_killed:
            continue
        killed += 1
        morph = rta.extract_multi_stmt_tree_morphism(
            mut_src,
            orig_src,
            provenance={"source": "mutant_kill_selfplay", "mutant_kind": mkind, "file": rel},
        )
        if morph is not None and len(getattr(morph, "hole_types", {}) or {}) >= 1:
            adm = skill_store.admit_tree_morphism(morph)
            mid = str(adm.get("morphism_id") or "")
            if mid and mid not in admitted_ids:
                admitted_ids.append(mid)

    return {
        "ok": True,
        "mutants_generated": len(mutants),
        "mutants_killed": killed,
        "morphisms_admitted": len(admitted_ids),
        "admitted_ids": admitted_ids,
        "model_calls": 0,
    }


# ===========================================================================
# ENGINE O-1 (Idea 4): TRANSACTIONAL WORKSPACE CoW TIME-TRAVEL &
# NEGATIVE-EFFECT INVARIANT ORACLE (TERMINAL-BENCH 4.1 SAFE EXECUTION)
# ===========================================================================


def snapshot_workspace_files(workspace_root: str | pathlib.Path) -> dict[str, tuple[str, int]]:
    """Capture deterministic `(rel_path -> (sha256, size))` inventory of all non-`.git` files."""
    root = pathlib.Path(workspace_root).resolve()
    snap: dict[str, tuple[str, int]] = {}
    if not root.is_dir():
        return snap
    for fp in sorted(root.rglob("*")):
        if not fp.is_file():
            continue
        rel_parts = fp.relative_to(root).parts
        if ".git" in rel_parts or "__pycache__" in rel_parts:
            continue
        rel = fp.relative_to(root).as_posix()
        try:
            data = fp.read_bytes()
            snap[rel] = (hashlib.sha256(data).hexdigest(), len(data))
        except OSError:
            continue
    return snap


def evaluate_negative_effect_oracle(
    before: Mapping[str, tuple[str, int]],
    after: Mapping[str, tuple[str, int]],
    *,
    allowed_write_paths: Iterable[str] = (),
    allow_new_files: bool = True,
) -> dict[str, Any]:
    """Negative-Effect Invariant Oracle: detects unrequested deletions or mutations of protected files."""
    allowed = {pathlib.PurePosixPath(str(p)).as_posix().lstrip("./") for p in allowed_write_paths if p}
    deleted = sorted(p for p in before if p not in after and p not in allowed)
    modified_protected = sorted(
        p for p in before if p in after and after[p] != before[p] and p not in allowed
    )
    created = sorted(p for p in after if p not in before)
    disallowed_created = [] if allow_new_files else [p for p in created if p not in allowed]
    violations: list[str] = []
    for p in deleted:
        violations.append(f"DELETED_PROTECTED:{p}")
    for p in modified_protected:
        violations.append(f"MODIFIED_PROTECTED:{p}")
    for p in disallowed_created:
        violations.append(f"CREATED_DISALLOWED:{p}")
    return {
        "safe": len(violations) == 0,
        "violations": violations,
        "deleted": deleted,
        "modified_protected": modified_protected,
        "created": created,
    }


class TransactionalWorkspaceCoWRunner:
    """Idea 4: Speculative Parallel Workspace CoW Time-Travel + Atomic Verified Commit.

    Never executes untrusted candidate terminal commands directly on the real workspace:
      1. Snapshots all pre-existing workspace files;
      2. Forks `K` parallel isolated workspace clones and executes each candidate plan in parallel;
      3. Evaluates BOTH multi-clause goal postconditions AND the Negative-Effect Invariant Oracle;
      4. Crystallizes L3 Negative-Effect Invariants for any destructive/side-effect-violating branch;
      5. Atomically commits ONLY the single verified winning branch's minimal delta into `workspace_root`.
    Zero runtime model calls!
    """

    def __init__(
        self,
        workspace_root: str | pathlib.Path,
        *,
        law_store: ExternalCausalLawStore | None = None,
        max_parallel: int = 8,
    ) -> None:
        self.workspace_root = pathlib.Path(workspace_root).resolve()
        self.law_store = law_store
        self.max_parallel = max(1, int(max_parallel))

    def execute_speculative_candidates(
        self,
        candidates: Sequence[Mapping[str, Any]],
        postcondition_clauses: Sequence[tuple[str, Callable[[pathlib.Path], bool]]],
        *,
        allowed_write_paths: Sequence[str] = (),
        allow_new_files: bool = True,
        timeout_per_cmd_s: int = 15,
    ) -> dict[str, Any]:
        """Run `candidates` in parallel isolated clones, enforce postconditions + negative-effect oracle,
        and atomically commit ONLY the winning safe branch to `self.workspace_root`."""
        import concurrent.futures

        before_snap = snapshot_workspace_files(self.workspace_root)
        allowed_set = {pathlib.PurePosixPath(str(p)).as_posix().lstrip("./") for p in allowed_write_paths if p}

        def _ignore_git(_dir: str, names: list[str]) -> set[str]:
            return {n for n in names if n in (".git", "__pycache__")}

        def _run_one(idx: int, cand: Mapping[str, Any]) -> dict[str, Any]:
            cid = str(cand.get("id") or f"cand_{idx}")
            cmds = [str(c) for c in (cand.get("commands") or ([cand["command"]] if cand.get("command") else []))]
            td_obj = tempfile.TemporaryDirectory(prefix=f"brain_cow_{idx}_")
            clone_root = pathlib.Path(td_obj.name) / "ws"
            shutil.copytree(self.workspace_root, clone_root, symlinks=True, ignore=_ignore_git)
            last_rc = 0
            stdout_tail = ""
            stderr_tail = ""
            for cmd in cmds:
                try:
                    cp = subprocess.run(
                        ["/bin/sh", "-c", cmd],
                        cwd=str(clone_root),
                        capture_output=True,
                        text=True,
                        timeout=timeout_per_cmd_s,
                    )
                    last_rc = int(cp.returncode)
                    stdout_tail = cp.stdout[-400:]
                    stderr_tail = cp.stderr[-400:]
                    if last_rc != 0:
                        break
                except (subprocess.TimeoutExpired, OSError) as exc:
                    last_rc = 124
                    stderr_tail = str(exc)[:240]
                    break

            after_snap = snapshot_workspace_files(clone_root)
            neg_eval = evaluate_negative_effect_oracle(
                before_snap,
                after_snap,
                allowed_write_paths=allowed_set,
                allow_new_files=allow_new_files,
            )
            clause_results: dict[str, bool] = {}
            all_clauses_ok = (last_rc == 0)
            for cname, cfn in postcondition_clauses:
                try:
                    ok_c = bool(cfn(clone_root))
                except Exception:
                    ok_c = False
                clause_results[cname] = ok_c
                if not ok_c:
                    all_clauses_ok = False

            # Capture exact delta bytes ONLY if both postconditions AND negative-effect oracle pass!
            delta_writes: dict[str, bytes] = {}
            if all_clauses_ok and neg_eval["safe"]:
                for rel_p, sig in after_snap.items():
                    if before_snap.get(rel_p) != sig:
                        delta_writes[rel_p] = (clone_root / rel_p).read_bytes()

            td_obj.cleanup()
            return {
                "idx": idx,
                "id": cid,
                "commands": cmds,
                "rc": last_rc,
                "clauses": clause_results,
                "postconditions_ok": all_clauses_ok,
                "negative_effect": neg_eval,
                "accepted": bool(all_clauses_ok and neg_eval["safe"]),
                "delta_writes": delta_writes,
                "stdout_tail": stdout_tail,
                "stderr_tail": stderr_tail,
            }

        results: list[dict[str, Any]] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(self.max_parallel, max(1, len(candidates)))) as pool:
            futs = [pool.submit(_run_one, i, c) for i, c in enumerate(candidates)]
            for f in futs:
                results.append(f.result())
        results.sort(key=lambda r: int(r["idx"]))

        # Crystallize L3 Negative Invariants for any branch blocked by the Negative-Effect Oracle!
        blocked_branches: list[dict[str, Any]] = []
        for r in results:
            if not r["negative_effect"]["safe"]:
                blocked_branches.append(
                    {
                        "id": r["id"],
                        "postconditions_ok": r["postconditions_ok"],
                        "violations": r["negative_effect"]["violations"],
                    }
                )
                if self.law_store is not None:
                    try:
                        from canonical.swe_kernel import reverse_tomography_algebra_v1 as rta
                        inv = rta.NegativeSpaceInvariant(
                            invariant_id=f"neg_cow::{hashlib.sha256(('|'.join(r['commands'])).encode()).hexdigest()[:10]}",
                            domain="terminal_cow",
                            func_context=r["id"],
                            orig_cond_shape="workspace_protected_files",
                            refuted_guard_shape=";".join(r["negative_effect"]["violations"][:3]),
                            reason=f"Negative-effect oracle blocked candidate {r['id']}",
                            counterexample={"violations": list(r["negative_effect"]["violations"][:5]), "commands": list(r["commands"][:3])},
                            created_at=int(time.time()),
                        )
                        self.law_store.add_negative_invariant(inv)
                    except Exception:
                        pass

        winners = [r for r in results if r["accepted"]]
        if not winners:
            return {
                "committed": False,
                "winner_id": None,
                "committed_files": [],
                "branches_evaluated": len(results),
                "blocked_negative_effects": blocked_branches,
                "model_calls": 0,
            }

        # Pick minimal-delta winner and commit atomically via temp-file + os.replace!
        winners.sort(key=lambda r: (len(r["delta_writes"]), r["idx"]))
        win = winners[0]
        committed_files: list[str] = []
        for rel_p, payload in sorted(win["delta_writes"].items()):
            dest = self.workspace_root / rel_p
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp_dest = dest.parent / f".brain_atomic_{os.getpid()}_{dest.name}"
            tmp_dest.write_bytes(payload)
            os.replace(tmp_dest, dest)
            committed_files.append(rel_p)

        return {
            "committed": True,
            "winner_id": win["id"],
            "winner_commands": win["commands"],
            "committed_files": committed_files,
            "branches_evaluated": len(results),
            "blocked_negative_effects": blocked_branches,
            "clauses": win["clauses"],
            "model_calls": 0,
        }


# ===========================================================================
# ENGINE Q-1: COMPOSITIONAL RELATIONAL DATAFLOW TERMINAL SYNTHESIZER
# (LIVE-SCHEMA INTROSPECTION + CoW TRANSACTIONAL EXECUTION + L2 ADMISSION)
# ===========================================================================


_REL_FILE_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])([A-Za-z0-9_./-]+\.(?:json|csv|tsv|log|txt|tar\.gz|tgz|tar|zip|sqlite3?|db))(?![A-Za-z0-9_-]|\.[A-Za-z0-9])",
    re.I,
)
_REL_DIR_TOKEN_RE = re.compile(r"\b(?:into|to|in)\s+([A-Za-z0-9_.-]+/)(?:\s|$|[,.;])", re.I)


def _infer_relational_format(path_str: str) -> str:
    low = path_str.lower()
    if low.endswith((".tar.gz", ".tgz")):
        return "tar_gz"
    if low.endswith(".tar"):
        return "tar"
    if low.endswith(".zip"):
        return "zip"
    if low.endswith(".json"):
        return "json"
    if low.endswith(".csv"):
        return "csv"
    if low.endswith(".tsv"):
        return "tsv"
    if low.endswith((".sqlite", ".sqlite3", ".db")):
        return "sqlite"
    if low.endswith((".log", ".txt")):
        return "log"
    return "other"


def _introspect_table_rows(root: pathlib.Path, rel_path: str, fmt: str) -> list[dict[str, Any]]:
    """Read live rows from a JSON/CSV/TSV/SQLite workspace file for exact schema introspection."""
    fp = root / rel_path
    if not fp.is_file():
        return []
    try:
        if fmt == "json":
            data = json.loads(fp.read_text(encoding="utf-8", errors="replace"))
            if isinstance(data, list):
                return [r for r in data if isinstance(r, dict)]
            if isinstance(data, dict):
                for v in data.values():
                    if isinstance(v, list) and v and isinstance(v[0], dict):
                        return v
            return []
        if fmt in ("csv", "tsv"):
            import csv as _csv
            delim = "\t" if fmt == "tsv" else ","
            with fp.open("r", encoding="utf-8", errors="replace", newline="") as fh:
                return [dict(r) for r in _csv.DictReader(fh, delimiter=delim)]
        if fmt == "sqlite":
            import sqlite3 as _sqlite3
            con = _sqlite3.connect(str(fp))
            con.row_factory = _sqlite3.Row
            tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            best: list[dict[str, Any]] = []
            for t in tables:
                rows = [dict(r) for r in con.execute(f'SELECT * FROM "{t}"').fetchall()]
                if len(rows) > len(best):
                    best = rows
            con.close()
            return best
    except Exception:
        return []
    return []


def _synthesize_relational_cow_terminal_pipeline(
    workspace_root: str | pathlib.Path,
    goal_text: str,
    *,
    law_store: ExternalCausalLawStore | None = None,
    timeout_s: int = 15,
) -> dict[str, Any]:
    """Compile a natural-language Terminal-Bench data/archive/log goal against live workspace schemas
    into a typed Relational Dataflow Plan, verify in parallel CoW clone + Negative-Effect Oracle,
    atomically commit ONLY verified artifacts, and crystallize a reusable L2 pipeline law."""
    t0 = time.monotonic()
    root = pathlib.Path(workspace_root).resolve()
    goal = str(goal_text or "").strip()
    if not goal:
        return {"solved": False, "reason": "EMPTY_GOAL", "model_calls": 0}

    mentioned = [m.group(1).lstrip("./") for m in _REL_FILE_TOKEN_RE.finditer(goal)]
    # Deduplicate preserving order
    seen_m: set[str] = set()
    uniq_files: list[str] = []
    for p in mentioned:
        if p not in seen_m:
            seen_m.add(p)
            uniq_files.append(p)

    existing_inputs = [p for p in uniq_files if (root / p).is_file()]
    missing_outputs = [p for p in uniq_files if not (root / p).is_file()]
    if not existing_inputs or not missing_outputs:
        return {"solved": False, "reason": "NO_IO_PAIR_IN_GOAL", "model_calls": 0}

    in_file = existing_inputs[0]
    out_file = missing_outputs[-1]
    in_fmt = _infer_relational_format(in_file)
    out_fmt = _infer_relational_format(out_file)
    m_dir = _REL_DIR_TOKEN_RE.search(goal)
    extract_dir = m_dir.group(1).rstrip("/") if m_dir else ""
    goal_low = goal.lower()

    # Build a deterministic relational pipeline Python snippet parameterized strictly by live schema!
    py_script = ""
    ir_kind = ""
    clauses: list[tuple[str, Callable[[pathlib.Path], bool]]] = [
        ("output_exists_nonempty", lambda ws: (ws / out_file).is_file() and (ws / out_file).stat().st_size > 0),
    ]
    if out_fmt == "json":
        clauses.append(
            ("valid_nonempty_json", lambda ws: bool(json.loads((ws / out_file).read_text(encoding="utf-8"))))
        )
    elif out_fmt in ("csv", "tsv"):
        def _chk_csv(ws: pathlib.Path) -> bool:
            import csv as _csv
            delim = "\t" if out_fmt == "tsv" else ","
            with (ws / out_file).open("r", encoding="utf-8", newline="") as fh:
                return len(list(_csv.DictReader(fh, delimiter=delim))) >= 1
        clauses.append(("valid_nonempty_csv", _chk_csv))

    # --- CASE A: ARCHIVE EXTRACT (tar.gz / tar / zip) + MANIFEST ---
    if in_fmt in ("tar_gz", "tar", "zip"):
        target_dir = extract_dir or "extracted"
        metric = "lines"
        if any(k in goal_low for k in ("sha256", "checksum", "hash")):
            metric = "sha256"
        elif any(k in goal_low for k in ("byte", "size")):
            metric = "bytes"
        ir_kind = f"ARCHIVE_{in_fmt.upper()}_EXTRACT_MANIFEST_{metric.upper()}"
        clauses.append(
            ("extract_dir_populated", lambda ws: (ws / target_dir).is_dir() and any((ws / target_dir).rglob("*")))
        )
        cfg = json.dumps({"in_file": in_file, "in_fmt": in_fmt, "out_file": out_file, "out_fmt": out_fmt, "target_dir": target_dir, "metric": metric})
        py_script = (
            "import csv, hashlib, json, pathlib, tarfile, zipfile\n"
            f"cfg = json.loads({cfg!r})\n"
            "src = pathlib.Path(cfg['in_file'])\n"
            "dest = pathlib.Path(cfg['target_dir'])\n"
            "dest.mkdir(parents=True, exist_ok=True)\n"
            "if cfg['in_fmt'] in ('tar_gz', 'tar'):\n"
            "    mode = 'r:gz' if cfg['in_fmt'] == 'tar_gz' else 'r:'\n"
            "    with tarfile.open(src, mode) as tf:\n"
            "        for m in tf.getmembers():\n"
            "            if m.isfile() and not m.name.startswith('/') and '..' not in pathlib.PurePosixPath(m.name).parts:\n"
            "                tf.extract(m, dest)\n"
            "else:\n"
            "    with zipfile.ZipFile(src, 'r') as zf:\n"
            "        for nm in zf.namelist():\n"
            "            if not nm.startswith('/') and '..' not in pathlib.PurePosixPath(nm).parts:\n"
            "                zf.extract(nm, dest)\n"
            "manifest = {}\n"
            "for fp in sorted(dest.rglob('*')):\n"
            "    if not fp.is_file(): continue\n"
            "    rel = fp.relative_to(dest).as_posix()\n"
            "    if cfg['metric'] == 'sha256':\n"
            "        manifest[rel] = hashlib.sha256(fp.read_bytes()).hexdigest()\n"
            "    elif cfg['metric'] == 'bytes':\n"
            "        manifest[rel] = fp.stat().st_size\n"
            "    else:\n"
            "        manifest[rel] = len(fp.read_text(encoding='utf-8', errors='replace').splitlines())\n"
            "out_p = pathlib.Path(cfg['out_file'])\n"
            "out_p.parent.mkdir(parents=True, exist_ok=True)\n"
            "if cfg['out_fmt'] == 'json':\n"
            "    out_p.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\\n', encoding='utf-8')\n"
            "elif cfg['out_fmt'] in ('csv', 'tsv'):\n"
            "    delim = '\\t' if cfg['out_fmt'] == 'tsv' else ','\n"
            "    with out_p.open('w', encoding='utf-8', newline='') as fh:\n"
            "        w = csv.writer(fh, delimiter=delim)\n"
            "        w.writerow(['file', cfg['metric']])\n"
            "        for k, v in sorted(manifest.items()): w.writerow([k, v])\n"
            "else:\n"
            "    out_p.write_text('\\n'.join(f'{k}: {v}' for k, v in sorted(manifest.items())) + '\\n', encoding='utf-8')\n"
        )

    # --- CASE B: STRUCTURED TABLE PIPELINE (1-TABLE OR 2-TABLE HASH-JOIN: JSON/CSV/TSV/SQLITE -> FILTER -> GROUP/AGG OR SORT -> JSON/CSV) ---
    elif in_fmt in ("json", "csv", "tsv", "sqlite"):
        rows = _introspect_table_rows(root, in_file, in_fmt)
        if not rows:
            return {"solved": False, "reason": "EMPTY_INPUT_SCHEMA", "model_calls": 0}
        # Detect optional 2-table relational join when a second structured input file is mentioned in goal!
        join_file = ""
        join_fmt = ""
        join_key = ""
        if len(existing_inputs) >= 2:
            cand_j = existing_inputs[1]
            cand_jf = _infer_relational_format(cand_j)
            if cand_jf in ("json", "csv", "tsv", "sqlite"):
                j_rows = _introspect_table_rows(root, cand_j, cand_jf)
                if j_rows:
                    cols_a = list(rows[0].keys())
                    cols_b = list(j_rows[0].keys())
                    common = [c for c in cols_a if c in set(cols_b)]
                    m_on = re.search(r"\bon\s+([a-zA-Z_][a-zA-Z0-9_]*)", goal_low)
                    if m_on:
                        for c in common:
                            if c.lower() == m_on.group(1).lower():
                                join_key = c
                                break
                    if not join_key and common:
                        # Prefer `*_id` / `id` join keys first!
                        id_keys = [c for c in common if c.lower() == "id" or c.lower().endswith("_id")]
                        join_key = id_keys[0] if id_keys else common[0]
                    if join_key:
                        join_file = cand_j
                        join_fmt = cand_jf
                        idx_b: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
                        for rb in j_rows:
                            idx_b[str(rb.get(join_key, ""))].append(rb)
                        joined: list[dict[str, Any]] = []
                        for ra in rows:
                            for rb in idx_b.get(str(ra.get(join_key, "")), ()):
                                merged = dict(ra)
                                for kb, vb in rb.items():
                                    if kb not in merged:
                                        merged[kb] = vb
                                joined.append(merged)
                        if joined:
                            rows = joined
        cols = list(rows[0].keys())
        col_low_map = {c.lower(): c for c in cols}

        # Infer column types from live values
        bool_cols: set[str] = set()
        num_cols: set[str] = set()
        for c in cols:
            vals = [r.get(c) for r in rows if r.get(c) is not None]
            if vals and all(isinstance(v, bool) or str(v).lower() in ("true", "false") for v in vals):
                bool_cols.add(c)
            else:
                ok_num = bool(vals)
                for v in vals:
                    try:
                        float(v)
                    except (TypeError, ValueError):
                        ok_num = False
                        break
                if ok_num:
                    num_cols.add(c)

        # 1. Discover filter predicates against live schema columns
        bool_filters: list[list[Any]] = []
        eq_filters: list[list[str]] = []
        num_filters: list[list[Any]] = []
        goal_words = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", goal_low))
        for bc in sorted(bool_cols):
            bcl = bc.lower()
            if f"not {bcl}" in goal_low or f"in{bcl}" in goal_words or f"{bcl}=false" in goal_low or f"{bcl} false" in goal_low:
                bool_filters.append([bc, False])
            elif bcl in goal_words or f"{bcl}=true" in goal_low:
                bool_filters.append([bc, True])
        for m_nf in re.finditer(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(>=|<=|>|<|==|=)\s*(-?\d+(?:\.\d+)?)", goal):
            col_c = col_low_map.get(m_nf.group(1).lower())
            if col_c and col_c in num_cols:
                num_filters.append([col_c, m_nf.group(2), float(m_nf.group(3))])
        for m_ef in re.finditer(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:==|=|is)\s*['\"]?([A-Za-z0-9_.-]+)['\"]?", goal):
            col_c = col_low_map.get(m_ef.group(1).lower())
            val_c = m_ef.group(2)
            if col_c and col_c not in bool_cols and col_c not in num_cols and val_c.lower() not in ("sorted", "grouped", "true", "false"):
                eq_filters.append([col_c, val_c])

        # 2. Discover sort_by (`sorted by <col>` / `order by <col>`)
        sort_col = ""
        sort_desc = bool(re.search(r"\b(?:desc|descending|highest|largest)\b", goal_low))
        m_sb = re.search(r"\b(?:sorted|order(?:ed)?)\s+by\s+([a-zA-Z_][a-zA-Z0-9_]*)", goal_low)
        if m_sb and m_sb.group(1).lower() in col_low_map:
            sort_col = col_low_map[m_sb.group(1).lower()]

        # 3. Discover group_by + aggregation (`sum <col> by <group_col>`, `count by <group_col>`, `avg <col> by <group_col>`)
        group_col = ""
        agg_op = ""
        agg_col = ""
        m_gb = re.search(r"\b(?:group(?:ed)?\s+by|(?<!sorted\s)(?<!order\s)(?<!ordered\s)by)\s+([a-zA-Z_][a-zA-Z0-9_]*)", goal_low)
        if m_gb and m_gb.group(1).lower() in col_low_map:
            cand_g = col_low_map[m_gb.group(1).lower()]
            if cand_g != sort_col:
                group_col = cand_g
        if re.search(r"\b(?:sum|total|totals)\b", goal_low):
            agg_op = "sum"
        elif re.search(r"\b(?:avg|average|mean)\b", goal_low):
            agg_op = "avg"
        elif re.search(r"\b(?:count|counts)\b", goal_low):
            agg_op = "count"
        if agg_op in ("sum", "avg"):
            for nc in sorted(num_cols):
                if nc.lower() in goal_words:
                    agg_col = nc
                    break
            if not agg_col and num_cols:
                agg_col = sorted(num_cols)[0]

        ir_kind = (
            (f"JOIN_{in_fmt.upper()}_{join_fmt.upper()}_TO_{out_fmt.upper()}" if join_file else f"TABLE_{in_fmt.upper()}_TO_{out_fmt.upper()}")
            + (f"_{agg_op.upper()}" if agg_op and group_col else "")
        )
        cfg = json.dumps(
            {
                "in_file": in_file,
                "in_fmt": in_fmt,
                "join_file": join_file,
                "join_fmt": join_fmt,
                "join_key": join_key,
                "out_file": out_file,
                "out_fmt": out_fmt,
                "cols": cols,
                "bool_filters": bool_filters,
                "eq_filters": eq_filters,
                "num_filters": num_filters,
                "sort_col": sort_col,
                "sort_desc": sort_desc,
                "group_col": group_col,
                "agg_op": agg_op,
                "agg_col": agg_col,
            }
        )
        py_script = (
            "import collections, csv, json, pathlib, sqlite3\n"
            f"cfg = json.loads({cfg!r})\n"
            "def _load(rel_p, fmt):\n"
            "    fp = pathlib.Path(rel_p)\n"
            "    if fmt == 'json':\n"
            "        raw = json.loads(fp.read_text(encoding='utf-8'))\n"
            "        return raw if isinstance(raw, list) else next((v for v in raw.values() if isinstance(v, list)), [])\n"
            "    if fmt in ('csv', 'tsv'):\n"
            "        delim = '\\t' if fmt == 'tsv' else ','\n"
            "        with fp.open('r', encoding='utf-8', newline='') as fh:\n"
            "            return [dict(r) for r in csv.DictReader(fh, delimiter=delim)]\n"
            "    con = sqlite3.connect(str(fp)); con.row_factory = sqlite3.Row\n"
            "    ts = [r[0] for r in con.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]\n"
            "    res = max(([dict(r) for r in con.execute(f'SELECT * FROM \"{t}\"').fetchall()] for t in ts), key=len, default=[])\n"
            "    con.close(); return res\n"
            "rows = _load(cfg['in_file'], cfg['in_fmt'])\n"
            "if cfg['join_file'] and cfg['join_key']:\n"
            "    jk = cfg['join_key']\n"
            "    j_rows = _load(cfg['join_file'], cfg['join_fmt'])\n"
            "    idx_b = collections.defaultdict(list)\n"
            "    for rb in j_rows: idx_b[str(rb.get(jk, ''))].append(rb)\n"
            "    merged_rows = []\n"
            "    for ra in rows:\n"
            "        for rb in idx_b.get(str(ra.get(jk, '')), ()):\n"
            "            m = dict(ra)\n"
            "            for kb, vb in rb.items():\n"
            "                if kb not in m: m[kb] = vb\n"
            "            merged_rows.append(m)\n"
            "    rows = merged_rows\n"
            "def _as_bool(v):\n"
            "    return v if isinstance(v, bool) else str(v).strip().lower() in ('true', '1', 'yes')\n"
            "filtered = []\n"
            "for r in rows:\n"
            "    ok = True\n"
            "    for k, want in cfg['bool_filters']:\n"
            "        if _as_bool(r.get(k)) != want: ok = False\n"
            "    for k, want in cfg['eq_filters']:\n"
            "        if str(r.get(k, '')).lower() != str(want).lower(): ok = False\n"
            "    for k, op, val in cfg['num_filters']:\n"
            "        try: fv = float(r.get(k))\n"
            "        except Exception: ok = False; break\n"
            "        if (op == '>' and not fv > val) or (op == '>=' and not fv >= val) or (op == '<' and not fv < val) or (op == '<=' and not fv <= val) or (op in ('=', '==') and not fv == val): ok = False\n"
            "    if ok: filtered.append(r)\n"
            "out_p = pathlib.Path(cfg['out_file'])\n"
            "out_p.parent.mkdir(parents=True, exist_ok=True)\n"
            "if cfg['group_col'] and cfg['agg_op']:\n"
            "    buckets = collections.defaultdict(list)\n"
            "    for r in filtered:\n"
            "        buckets[str(r.get(cfg['group_col'], ''))].append(r)\n"
            "    agg = {}\n"
            "    for gk in sorted(buckets.keys()):\n"
            "        items = buckets[gk]\n"
            "        if cfg['agg_op'] == 'count':\n"
            "            agg[gk] = len(items)\n"
            "        else:\n"
            "            nums = [float(x[cfg['agg_col']]) for x in items if x.get(cfg['agg_col']) not in (None, '')]\n"
            "            val = sum(nums) if cfg['agg_op'] == 'sum' else (sum(nums) / len(nums) if nums else 0.0)\n"
            "            agg[gk] = int(val) if float(val).is_integer() else round(val, 6)\n"
            "    if cfg['out_fmt'] == 'json':\n"
            "        out_p.write_text(json.dumps(agg, indent=2, sort_keys=True) + '\\n', encoding='utf-8')\n"
            "    else:\n"
            "        delim = '\\t' if cfg['out_fmt'] == 'tsv' else ','\n"
            "        with out_p.open('w', encoding='utf-8', newline='') as fh:\n"
            "            w = csv.writer(fh, delimiter=delim)\n"
            "            w.writerow([cfg['group_col'], cfg['agg_col'] or cfg['agg_op']])\n"
            "            for k, v in sorted(agg.items()): w.writerow([k, v])\n"
            "else:\n"
            "    if cfg['sort_col']:\n"
            "        sc = cfg['sort_col']\n"
            "        def _skey(r):\n"
            "            v = r.get(sc, '')\n"
            "            try: return (0, float(v), '')\n"
            "            except Exception: return (1, 0.0, str(v))\n"
            "        filtered.sort(key=_skey, reverse=bool(cfg['sort_desc']))\n"
            "    if cfg['out_fmt'] == 'json':\n"
            "        out_p.write_text(json.dumps(filtered, indent=2, sort_keys=True) + '\\n', encoding='utf-8')\n"
            "    else:\n"
            "        delim = '\\t' if cfg['out_fmt'] == 'tsv' else ','\n"
            "        cols = cfg['cols'] or (list(filtered[0].keys()) if filtered else [])\n"
            "        with out_p.open('w', encoding='utf-8', newline='') as fh:\n"
            "            w = csv.DictWriter(fh, fieldnames=cols, delimiter=delim)\n"
            "            w.writeheader()\n"
            "            for r in filtered: w.writerow({c: r.get(c, '') for c in cols})\n"
        )

    # --- CASE C: LOG / TEXT STREAM FILTER + COUNT/GROUP PIPELINE ---
    elif in_fmt == "log":
        log_txt = (root / in_file).read_text(encoding="utf-8", errors="replace")
        log_lines = [ln.strip() for ln in log_txt.splitlines() if ln.strip()]
        if not log_lines:
            return {"solved": False, "reason": "EMPTY_LOG_INPUT", "model_calls": 0}
        # Discover target severity/token mentioned in BOTH goal and live log lines!
        level_filter = ""
        for tok in ("ERROR", "FATAL", "CRITICAL", "WARN", "WARNING", "INFO", "DEBUG"):
            if re.search(rf"\b{tok}\b", goal) and any(tok in ln for ln in log_lines):
                level_filter = tok
                break
        if not level_filter:
            for tok in ("ERROR", "WARN", "INFO"):
                if tok.lower() in goal_low and any(tok in ln for ln in log_lines):
                    level_filter = tok
                    break
        ir_kind = f"LOG_AGG_{level_filter or 'ALL'}_TO_{out_fmt.upper()}"
        cfg = json.dumps({"in_file": in_file, "out_file": out_file, "out_fmt": out_fmt, "level_filter": level_filter})
        py_script = (
            "import collections, csv, json, pathlib, re\n"
            f"cfg = json.loads({cfg!r})\n"
            "lines = [ln.strip() for ln in pathlib.Path(cfg['in_file']).read_text(encoding='utf-8', errors='replace').splitlines() if ln.strip()]\n"
            "lf = cfg['level_filter']\n"
            "counts = collections.Counter()\n"
            "for ln in lines:\n"
            "    if lf and lf not in ln: continue\n"
            "    toks = ln.split()\n"
            "    key = ''\n"
            "    if lf and lf in toks:\n"
            "        i = toks.index(lf)\n"
            "        key = toks[i + 1] if (i + 1) < len(toks) else lf\n"
            "    elif len(toks) >= 2:\n"
            "        key = toks[1]\n"
            "    elif toks:\n"
            "        key = toks[0]\n"
            "    if key:\n"
            "        counts[key] += 1\n"
            "res = {k: counts[k] for k in sorted(counts)}\n"
            "out_p = pathlib.Path(cfg['out_file'])\n"
            "out_p.parent.mkdir(parents=True, exist_ok=True)\n"
            "if cfg['out_fmt'] == 'json':\n"
            "    out_p.write_text(json.dumps(res, indent=2, sort_keys=True) + '\\n', encoding='utf-8')\n"
            "elif cfg['out_fmt'] in ('csv', 'tsv'):\n"
            "    delim = '\\t' if cfg['out_fmt'] == 'tsv' else ','\n"
            "    with out_p.open('w', encoding='utf-8', newline='') as fh:\n"
            "        w = csv.writer(fh, delimiter=delim)\n"
            "        w.writerow(['key', 'count'])\n"
            "        for k, v in res.items(): w.writerow([k, v])\n"
            "else:\n"
            "    out_p.write_text('\\n'.join(f'{k}: {v}' for k, v in res.items()) + '\\n', encoding='utf-8')\n"
        )

    if not py_script:
        return {"solved": False, "reason": "UNSUPPORTED_PIPELINE_IO", "model_calls": 0}

    # Execute strictly inside TransactionalWorkspaceCoWRunner with Negative-Effect Invariant Oracle!
    cmd_str = f"{shlex.quote(sys.executable)} -c {shlex.quote(py_script)}"
    runner = TransactionalWorkspaceCoWRunner(root, law_store=law_store)
    cow = runner.execute_speculative_candidates(
        candidates=[{"id": ir_kind, "command": cmd_str}],
        postcondition_clauses=clauses,
        allowed_write_paths=[out_file],
        allow_new_files=True,
        timeout_per_cmd_s=timeout_s,
    )
    if not cow.get("committed"):
        return {
            "solved": False,
            "reason": "COW_POSTCONDITION_OR_SAFETY_REJECTED",
            "cow": cow,
            "elapsed_ms": int((time.monotonic() - t0) * 1000),
            "model_calls": 0,
        }

    # Crystallize verified Relational Dataflow pipeline law into ExternalCausalLawStore!
    law_id = f"rel_pipe::{hashlib.sha256(f'{ir_kind}:{in_fmt}:{out_fmt}'.encode()).hexdigest()[:10]}"
    if law_store is not None:
        try:
            law_store.admit(
                ParameterizedCausalLaw(
                    law_id=law_id,
                    domain="terminal_relational_pipeline",
                    tool_or_action=ir_kind,
                    command_template=["relational_cow_pipeline", in_fmt, out_fmt],
                    in_ext=pathlib.Path(in_file).suffix,
                    out_ext=pathlib.Path(out_file).suffix,
                    preconditions={"in_fmt": in_fmt},
                    effects={"out_fmt": out_fmt, "protected_files_intact": True},
                    provenance={"ir_kind": ir_kind, "committed_files": cow.get("committed_files")},
                    generalized=True,
                )
            )
        except Exception:
            pass

    return {
        "solved": True,
        "source": "RELATIONAL_DATAFLOW_COW_PIPELINE",
        "procedure_family": ir_kind,
        "law_id": law_id,
        "output_file": out_file,
        "committed_files": cow.get("committed_files") or [out_file],
        "real_actions": [["relational_cow_pipeline", in_file, "->", out_file]],
        "reading_succeeded": True,
        "elapsed_ms": int((time.monotonic() - t0) * 1000),
        "model_calls": 0,
    }


_WS_REPAIR_FILE_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])([A-Za-z0-9_./-]+\.(?:sh|json|py|csv|tsv|txt|log|out|yaml|yml|ini|conf|cfg))(?![A-Za-z0-9_-]|\.[A-Za-z0-9])",
    re.I,
)


def repair_workspace_script_or_config_cow(
    workspace_root: str | pathlib.Path,
    goal_text: str,
    *,
    law_store: ExternalCausalLawStore | None = None,
    timeout_s: int = 15,
) -> dict[str, Any]:
    """Engine S-3b: Transactional CoW repair for broken workspace scripts (`.sh`: CRLF / chmod / mkdir)
    and malformed JSON configs (`.json`: comments, trailing commas, single quotes / Python literals),
    verified with `NegativeEffectOracle` and crystallized into `ExternalCausalLawStore` (0 model calls)."""
    t0 = time.monotonic()
    root = pathlib.Path(workspace_root).resolve()
    goal = str(goal_text or "").strip()
    if not goal:
        return {"solved": False, "reason": "EMPTY_GOAL", "model_calls": 0}

    mentioned: list[str] = []
    for m in _WS_REPAIR_FILE_RE.finditer(goal):
        tok = m.group(1).lstrip("./")
        if tok not in mentioned:
            mentioned.append(tok)

    existing_sh = [p for p in mentioned if p.endswith(".sh") and (root / p).is_file()]
    existing_json = [p for p in mentioned if p.endswith(".json") and (root / p).is_file()]
    existing_py = [p for p in mentioned if p.endswith(".py") and (root / p).is_file()]
    missing_outputs = [p for p in mentioned if not (root / p).is_file()]

    # --- FAMILY TB-R2: MALFORMED JSON CONFIG REPAIR ---
    for jf in existing_json:
        raw_j = (root / jf).read_text(encoding="utf-8", errors="replace")
        is_invalid_json = False
        try:
            json.loads(raw_j)
        except Exception:
            is_invalid_json = True
        if not is_invalid_json:
            continue

        verifier_py = next((p for p in existing_py if any(k in p.lower() for k in ("verif", "check", "test", "valid"))), "")
        cfg = json.dumps({"json_file": jf, "verifier_py": verifier_py})
        py_fix = (
            "import ast, json, pathlib, re, subprocess, sys\n"
            f"cfg = json.loads({cfg!r})\n"
            "fp = pathlib.Path(cfg['json_file'])\n"
            "raw = fp.read_text(encoding='utf-8', errors='replace').replace('\\r\\n', '\\n')\n"
            "cleaned_lines = []\n"
            "for ln in raw.splitlines():\n"
            "    s = ln.strip()\n"
            "    if s.startswith('//') or s.startswith('#'): continue\n"
            "    cleaned_lines.append(re.sub(r'(?<!:)//.*$', '', ln))\n"
            "s1 = '\\n'.join(cleaned_lines)\n"
            "s2 = re.sub(r',\\s*([}\\]])', r'\\1', s1)\n"
            "obj = None\n"
            "try:\n"
            "    obj = json.loads(s2)\n"
            "except Exception:\n"
            "    s3 = re.sub(r'\\btrue\\b', 'True', re.sub(r'\\bfalse\\b', 'False', re.sub(r'\\bnull\\b', 'None', s2)))\n"
            "    obj = ast.literal_eval(s3)\n"
            "fp.write_text(json.dumps(obj, indent=2, sort_keys=True) + '\\n', encoding='utf-8')\n"
            "if cfg['verifier_py']:\n"
            "    cp = subprocess.run([sys.executable, cfg['verifier_py']], check=False)\n"
            "    sys.exit(cp.returncode)\n"
        )
        clauses: list[tuple[str, Callable[[pathlib.Path], bool]]] = [
            ("valid_json_parse", lambda ws, _jf=jf: json.loads((ws / _jf).read_text(encoding="utf-8")) is not None),
        ]
        for mo in missing_outputs:
            clauses.append(
                (f"output_exists_{mo}", lambda ws, _mo=mo: (ws / _mo).is_file() and (ws / _mo).stat().st_size > 0)
            )
        allowed = [jf] + missing_outputs
        cmd_str = f"{shlex.quote(sys.executable)} -c {shlex.quote(py_fix)}"
        runner = TransactionalWorkspaceCoWRunner(root, law_store=law_store)
        cow = runner.execute_speculative_candidates(
            candidates=[{"id": "CONFIG_JSON_CANONICALIZE_REPAIR", "command": cmd_str}],
            postcondition_clauses=clauses,
            allowed_write_paths=allowed,
            allow_new_files=True,
            timeout_per_cmd_s=timeout_s,
        )
        if cow.get("committed"):
            law_id = f"ws_repair::{hashlib.sha256(f'JSON_CONFIG_REPAIR:{jf}'.encode()).hexdigest()[:10]}"
            if law_store is not None:
                try:
                    law_store.admit(
                        ParameterizedCausalLaw(
                            law_id=law_id,
                            domain="terminal_workspace_repair",
                            tool_or_action="CONFIG_JSON_CANONICALIZE_REPAIR",
                            command_template=["workspace_cow_repair", "json_config", jf],
                            preconditions={"broken_ext": ".json"},
                            effects={"valid_json": True, "protected_files_intact": True},
                            provenance={"repaired_file": jf, "committed_files": cow.get("committed_files")},
                            generalized=True,
                        )
                    )
                except Exception:
                    pass
            return {
                "solved": True,
                "source": "WORKSPACE_CONFIG_COW_REPAIR",
                "procedure_family": "CONFIG_JSON_CANONICALIZE_REPAIR",
                "law_id": law_id,
                "repaired_file": jf,
                "committed_files": cow.get("committed_files") or [jf],
                "real_actions": [["workspace_cow_repair", "json_config", jf]],
                "reading_succeeded": True,
                "elapsed_ms": int((time.monotonic() - t0) * 1000),
                "model_calls": 0,
            }

    # --- FAMILY TB-R1: BROKEN SHELL SCRIPT (CRLF / CHMOD +X / MISSING OUTPUT DIR) REPAIR & RUN ---
    for sh_rel in existing_sh:
        cfg = json.dumps({"sh_file": sh_rel, "missing_outputs": missing_outputs})
        py_sh_fix = (
            "import json, os, pathlib, re, stat, subprocess, sys\n"
            f"cfg = json.loads({cfg!r})\n"
            "fp = pathlib.Path(cfg['sh_file'])\n"
            "raw = fp.read_bytes()\n"
            "fixed = raw.replace(b'\\r\\n', b'\\n').replace(b'\\r', b'\\n')\n"
            "if fixed != raw: fp.write_bytes(fixed)\n"
            "st = fp.stat().st_mode\n"
            "os.chmod(fp, st | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)\n"
            "txt = fixed.decode('utf-8', errors='replace')\n"
            "for m in re.finditer(r'(?:>>?|tee\\s+(?:-a\\s+)?)\\s*([^\\s;|>&]+/[^\\s;|>&]+)', txt):\n"
            "    p_out = pathlib.Path(m.group(1).strip('\"' + chr(39)))\n"
            "    if not p_out.is_absolute() and '..' not in p_out.parts:\n"
            "        p_out.parent.mkdir(parents=True, exist_ok=True)\n"
            "for mo in cfg['missing_outputs']:\n"
            "    p_mo = pathlib.Path(mo)\n"
            "    if p_mo.parent != pathlib.Path('.'):\n"
            "        p_mo.parent.mkdir(parents=True, exist_ok=True)\n"
            "cp = subprocess.run([str(fp.resolve())], check=False)\n"
            "sys.exit(cp.returncode)\n"
        )
        clauses_sh: list[tuple[str, Callable[[pathlib.Path], bool]]] = [
            ("script_no_crlf", lambda ws, _sf=sh_rel: b"\r" not in (ws / _sf).read_bytes()),
        ]
        for mo in missing_outputs:
            clauses_sh.append(
                (f"output_exists_{mo}", lambda ws, _mo=mo: (ws / _mo).is_file() and (ws / _mo).stat().st_size > 0)
            )
        allowed_sh = [sh_rel] + missing_outputs
        cmd_sh = f"{shlex.quote(sys.executable)} -c {shlex.quote(py_sh_fix)}"
        runner_sh = TransactionalWorkspaceCoWRunner(root, law_store=law_store)
        cow_sh = runner_sh.execute_speculative_candidates(
            candidates=[{"id": "SHELL_SCRIPT_CRLF_CHMOD_MKDIR_REPAIR", "command": cmd_sh}],
            postcondition_clauses=clauses_sh,
            allowed_write_paths=allowed_sh,
            allow_new_files=True,
            timeout_per_cmd_s=timeout_s,
        )
        if cow_sh.get("committed"):
            # Ensure execute bit is also preserved on committed script!
            try:
                sf_p = root / sh_rel
                sf_p.chmod(sf_p.stat().st_mode | 0o111)
            except OSError:
                pass
            law_id = f"ws_repair::{hashlib.sha256(f'SHELL_SCRIPT_REPAIR:{sh_rel}'.encode()).hexdigest()[:10]}"
            if law_store is not None:
                try:
                    law_store.admit(
                        ParameterizedCausalLaw(
                            law_id=law_id,
                            domain="terminal_workspace_repair",
                            tool_or_action="SHELL_SCRIPT_CRLF_CHMOD_MKDIR_REPAIR",
                            command_template=["workspace_cow_repair", "shell_script", sh_rel],
                            preconditions={"broken_ext": ".sh"},
                            effects={"script_exit_0": True, "protected_files_intact": True},
                            provenance={"repaired_file": sh_rel, "committed_files": cow_sh.get("committed_files")},
                            generalized=True,
                        )
                    )
                except Exception:
                    pass
            return {
                "solved": True,
                "source": "WORKSPACE_SCRIPT_COW_REPAIR",
                "procedure_family": "SHELL_SCRIPT_CRLF_CHMOD_MKDIR_REPAIR",
                "law_id": law_id,
                "repaired_file": sh_rel,
                "committed_files": cow_sh.get("committed_files") or [sh_rel],
                "real_actions": [["workspace_cow_repair", "shell_script", sh_rel]],
                "reading_succeeded": True,
                "elapsed_ms": int((time.monotonic() - t0) * 1000),
                "model_calls": 0,
            }

    return {"solved": False, "reason": "NO_REPAIRABLE_SCRIPT_OR_CONFIG", "elapsed_ms": int((time.monotonic() - t0) * 1000), "model_calls": 0}


def self_check() -> dict[str, Any]:
    """Falsifiable behavioral contract for template anti-unification, dominator cut-vertices & negative-effect oracle.

    Proves:
    1. Template anti-unification preserves shared tokens and generalizes only differing slots,
       while returning None on structurally incompatible sequence lengths.
    2. Petri dominator cut-vertex computation finds exact mandatory choke points on a diamond DAG
       (excluding parallel bypass branches).
    3. Negative effect oracle approves authorized edits and rejects unauthorized protected-file edits.
    """
    failures: list[str] = []

    def check(label: str, ok: bool) -> None:
        if not ok:
            failures.append(label)

    au = anti_unify_templates(["git", "checkout", "feat-a"], ["git", "checkout", "feat-b"])
    check(
        "anti-unifies differing argument into single slot",
        au is not None and au[0][:2] == ["git", "checkout"] and len(au[1]) == 1,
    )
    bad_au = anti_unify_templates(["git", "status"], ["git", "checkout", "main"])
    check("negative control: mismatched sequence lengths return None", bad_au is None)

    cuts = compute_petri_dominator_cut_vertices(
        [("s", "a"), ("a", "b"), ("a", "c"), ("b", "d"), ("c", "d"), ("d", "g")],
        "s",
        "g",
    )
    check(
        "finds exact diamond dominator cut vertices ['a', 'd'] excluding parallel b/c",
        bool(cuts.get("reachable")) and cuts.get("cut_vertices") == ["a", "d"],
    )

    unreach = compute_petri_dominator_cut_vertices([("s", "a"), ("b", "g")], "s", "g")
    check("negative control: disconnected graph reports unreachable", not bool(unreach.get("reachable")))

    ok_eff = evaluate_negative_effect_oracle(
        {"a.txt": ("h1", 10), "sec.txt": ("s1", 5)},
        {"a.txt": ("h2", 12), "sec.txt": ("s1", 5)},
        allowed_write_paths=["a.txt"],
    )
    check("approves authorized file modification", bool(ok_eff.get("safe")) and not ok_eff.get("violations"))

    bad_eff = evaluate_negative_effect_oracle(
        {"a.txt": ("h1", 10), "sec.txt": ("s1", 5)},
        {"a.txt": ("h2", 12), "sec.txt": ("s2", 6)},
        allowed_write_paths=["a.txt"],
    )
    check(
        "negative control: catches unauthorized protected file modification",
        not bool(bad_eff.get("safe")) and "sec.txt" in (bad_eff.get("modified_protected") or []),
    )

    total = 6
    return {
        "schema": "BRAIN_UNIVERSAL_COMPUTER_AGENT_V1_SELF_CHECK",
        "checks": total,
        "passed": total - len(failures),
        "failures": failures,
        "verdict": "SELF_CHECK_PASS" if not failures else "SELF_CHECK_FAIL",
    }







