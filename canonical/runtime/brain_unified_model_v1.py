#!/usr/bin/env python3
"""Brain Unified Model V1 — one front door over the compiled Brain.

``BRAIN_UNIFIED_MODEL_V1.json`` is a deterministic projection of every live
verified capability, every fabric engine mode, every internalized skill
procedure, and an index of the laws and research the machine reasons from.
This module is the thing you actually run.

Three operations, one contract:

* ``status()``   — what the model contains, and what it explicitly cannot claim.
* ``route()``    — deterministic ranking of a plain goal against the model. It
                   fails closed: an unknown goal is reported as unknown instead
                   of being answered by a guess or an external model.
* ``solve()``    — route, then execute through the authority that owns the
                   capability. Bound capabilities go through
                   ``verified_bound_capability_execution_adapter_v1.execute``,
                   which re-reads the live registry and re-checks evidence.
                   Engine modes go through the unified cognitive fabric unchanged.
* ``recall()``   — just-in-time retrieval over the knowledge index. The model
                   stores hashes, headings and terms, never a copy of the text.

Authority boundary
------------------
This module grants nothing. Every result carries zero capability, ownership and
terminal credit. It does not widen a tolerance, promote a capability, replace
the live registry, or add a model to any producer path. It exposes what Brain
already owns through one addressable artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_UNIFIED_MODEL_V1"
SOLUTION_SCHEMA = "PROJECT_BRAIN_UNIFIED_MODEL_SOLUTION_V1"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT = "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"

# Slot names whose value is the caller's own sentence rather than a resource to
# be discovered. Mirrors the set world_binding_v1 treats as goal text, so the
# two never disagree about what counts as the caller's words.
_GOAL_TEXT_SLOTS = frozenset({"goal", "task", "objective", "query", "question", "text"})

# Kept byte-identical in behaviour to the compiler's tokenizer. A routing table
# compiled with one segmentation and queried with another silently loses recall;
# the verifier checks the two tokenizers agree on a sample of terms.
STOPWORDS = frozenset(
    """
    a an and are as at be by can could do does for from has have how i if in into
    is it its of on or our that the their them then there these this to using was
    we what when where which who why will with without you your
    """.split()
)
TOKEN_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789_+.-")

NON_CLAIMS = (
    "NOT_A_TRAINED_NEURAL_NETWORK__CONTAINS_NO_WEIGHTS",
    "NOT_AN_INDEPENDENT_VERIFICATION__SANDBOX_MEASUREMENT_ONLY",
    "NOT_TERMINAL_AUTHORITY__ZERO_CAPABILITY_AND_TERMINAL_CREDIT",
    "NOT_A_REPLACEMENT_FOR_THE_LIVE_REGISTRY_OR_LAWS",
    "COVERAGE_IS_NOT_CAPABILITY__EXECUTION_STILL_REQUIRES_DECLARED_SUBSTRATE",
)


class UnifiedModelError(ValueError):
    """The artifact or the request violated the model contract."""


# --------------------------------------------------------------------------- bytes


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_value(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def artifact_digest(model: Mapping[str, Any]) -> str:
    return digest_value({k: v for k, v in model.items() if k != "digest"})


def tokenize(text: str) -> list[str]:
    out: list[str] = []
    for raw in str(text or "").casefold().replace("/", " ").split():
        token = "".join(ch for ch in raw if ch in TOKEN_CHARS).strip("._-")
        if len(token) < 2 or token in STOPWORDS:
            continue
        out.append(token)
    return out


# --------------------------------------------------------------------------- loading


def load_model(
    path: str | Path | None = None,
    *,
    root: str | Path | None = None,
    verify: bool = True,
) -> dict[str, Any]:
    base = Path(root or ROOT).resolve()
    target = Path(path) if path else base / DEFAULT_ARTIFACT
    if not target.is_absolute():
        target = base / target
    if not target.is_file():
        raise UnifiedModelError("MODEL_ARTIFACT_MISSING:" + str(target))
    try:
        model = json.loads(target.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UnifiedModelError("MODEL_ARTIFACT_NOT_JSON") from exc
    if not isinstance(model, dict) or model.get("schema") != SCHEMA:
        raise UnifiedModelError("MODEL_SCHEMA_MISMATCH")
    if verify:
        declared = (model.get("digest") or {}).get("value")
        recomputed = artifact_digest(model)
        if not declared or declared != recomputed:
            raise UnifiedModelError("MODEL_DIGEST_MISMATCH")
    return model


# --------------------------------------------------------------------------- model


class UnifiedModel:
    """A loaded, digest-verified unified model."""

    def __init__(self, model: Mapping[str, Any]):
        self.model = dict(model)
        self.digest = str((model.get("digest") or {}).get("value") or "")
        self.capabilities = {
            str(row["id"]): dict(row)
            for row in model.get("capabilities") or []
            if isinstance(row, Mapping) and row.get("id")
        }
        self.engines = {
            str(row["id"]): dict(row)
            for row in model.get("engines") or []
            if isinstance(row, Mapping) and row.get("id")
        }
        self.skills = [dict(row) for row in (model.get("skills") or []) if isinstance(row, Mapping)]
        self.knowledge = [
            dict(row) for row in (model.get("knowledge") or []) if isinstance(row, Mapping)
        ]
        raw_index: dict[str, dict[str, float]] = {
            str(token): {str(cid): float(weight) for cid, weight in postings.items()}
            for token, postings in ((model.get("grammar") or {}).get("index") or {}).items()
        }
        # A receipt-backed capability is indexed under every word of its own
        # path, so `run_long_horizon_continuity_v1.py` is reachable by the
        # ordinary verb "run". Keep only the tokens the verifier itself treats
        # as that capability's triggers -- the declared triggers that are not
        # path segments and are longer than three characters -- so a common
        # short word cannot select a script and execute it. Bound capabilities
        # declare their own keywords and are left exactly as compiled.
        self.receipt_backed_ids: frozenset[str] = frozenset(
            cid
            for cid, row in self.capabilities.items()
            if row.get("kind") == "RECEIPT_BACKED_CAPABILITY"
        )
        self.index: dict[str, dict[str, float]] = {}
        for token, postings in raw_index.items():
            kept = {}
            for cid, weight in postings.items():
                if cid in self.receipt_backed_ids:
                    if token not in self._declared_triggers(cid):
                        continue
                kept[cid] = weight
            if kept:
                self.index[token] = kept
        confidence = (model.get("grammar") or {}).get("confidence") or {}
        self.min_score = float(confidence.get("minimum_best_score", 1.0))
        self.min_coverage = float(confidence.get("minimum_coverage", 0.34))
        self._knowledge_df: dict[str, int] = {}
        self._knowledge_lengths: list[int] = []
        for row in self.knowledge:
            terms = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
            self._knowledge_lengths.append(sum(int(v) for v in terms.values()))
            for term in terms:
                self._knowledge_df[str(term)] = self._knowledge_df.get(str(term), 0) + 1
        self._avg_length = (
            sum(self._knowledge_lengths) / len(self._knowledge_lengths)
            if self._knowledge_lengths
            else 1.0
        ) or 1.0

    # ------------------------------------------------------------------ status

    def status(self) -> dict[str, Any]:
        declared = self.model.get("counts") or {}
        missing_ids = sorted(
            cid
            for cid, row in self.capabilities.items()
            if _missing_declared_dependencies(row)
        )
        present = len(self.capabilities) - len(missing_ids)
        return {
            "schema": SOLUTION_SCHEMA,
            "operation": "STATUS",
            "model_id": self.model.get("model_id"),
            "model_version": self.model.get("model_version"),
            "model_digest": self.digest,
            "counts": {
                "capabilities": len(self.capabilities),
                "bound_capabilities": declared.get("bound_capabilities"),
                "receipt_backed_capabilities": declared.get("receipt_backed_capabilities"),
                "engines": len(self.engines),
                "skills": len(self.skills),
                "knowledge_documents": len(self.knowledge),
                "routing_tokens": len(self.index),
            },
            "declared_dependencies_present": present,
            "declared_dependencies_missing": len(self.capabilities) - present,
            "objective": (self.model.get("objective") or {}).get("verbatim"),
            "non_claims": list(NON_CLAIMS),
            "credit": {
                "capability_credit_delta": 0,
                "ownership_credit_delta": 0,
                "terminal_credit_delta": 0,
            },
        }

    # ------------------------------------------------------------------- route

    def _declared_triggers(self, cid: str) -> set[str]:
        """The tokens the verifier treats as this capability's own triggers.

        Mirrors `verify_brain_unified_model_v1._capability_tokens`: a declared
        trigger counts only if it is not a segment of the capability's own id
        and is longer than three characters. That excludes the path segments
        (`canonical`, `verification`) and short filename fragments (`run`,
        `py`, `v1`) that would otherwise make an ordinary word in a goal select
        this capability.
        """
        row = self.capabilities.get(cid) or {}
        id_tokens = set(tokenize(cid))
        return {
            str(t)
            for t in (row.get("triggers") or [])
            if str(t) not in id_tokens and len(str(t)) > 3
        }

    def _ids_mentioned(self, goal: str) -> set[str]:
        folded = str(goal or "").casefold()
        hits: set[str] = set()
        for cid in self.capabilities:
            if cid.casefold() in folded:
                hits.add(cid)
        for eid in self.engines:
            mode = eid.split(":", 1)[-1].replace("_", " ").casefold()
            if mode and mode in folded:
                hits.add(eid)
        return hits

    def route(self, goal: str, *, top_k: int = 5) -> dict[str, Any]:
        tokens = tokenize(goal)
        scores: dict[str, float] = {}
        matched: set[str] = set()
        for token in tokens:
            postings = self.index.get(token)
            if not postings:
                continue
            matched.add(token)
            for cid, weight in postings.items():
                scores[cid] = scores.get(cid, 0.0) + weight
        mentioned = self._ids_mentioned(goal)
        for cid in mentioned:
            scores[cid] = scores.get(cid, 0.0) + 24.0
            matched.add(cid.casefold())
        coverage = (len(matched) / len(tokens)) if tokens else 0.0
        # Naming a capability by its own id is an address, not a keyword. Its
        # path segments also index capabilities that legitimately claim those
        # words, so a flat +24 can be outscored by the noise the address itself
        # introduced. Sort addressed capabilities ahead of the rest instead of
        # inflating the bonus until it wins by force.
        #
        # Engines are excluded from that priority: they match by mode phrase
        # (`engine:BOUND_CAPABILITY` matches the phrase "bound capability"),
        # which is ordinary keyword overlap, not an address. Promoting them let
        # a 195.977 engine outrank the 911.668 capability the goal named.
        addressed = {cid for cid in mentioned if cid in self.capabilities}
        ranked = sorted(
            scores.items(),
            key=lambda kv: (kv[0] not in addressed, -kv[1], kv[0]),
        )
        rows: list[dict[str, Any]] = []
        for cid, score in ranked[: max(1, int(top_k))]:
            row = self.capabilities.get(cid) or self.engines.get(cid) or {}
            rows.append(
                {
                    "id": cid,
                    "kind": row.get("kind") or "UNKNOWN",
                    "score": round(float(score), 6),
                    "coverage": round(coverage, 6),
                }
            )
        best = ranked[0] if ranked else None
        confident = bool(
            best
            and best[1] >= self.min_score
            and coverage >= self.min_coverage
        )
        return {
            "schema": SOLUTION_SCHEMA,
            "operation": "ROUTE",
            "model_digest": self.digest,
            "goal": goal,
            "query_tokens": tokens,
            "matched_token_count": len(matched),
            "coverage": round(coverage, 6),
            "confident": confident,
            "best": rows[0] if rows else None,
            "candidates": rows,
            "reason": (
                "ROUTED_WITHIN_MODEL"
                if confident
                else "GOAL_NOT_REPRESENTED_IN_MODEL__FAIL_CLOSED"
            ),
        }

    # ------------------------------------------------------------------ recall

    def recall(self, query: str, *, top_k: int = 5) -> dict[str, Any]:
        terms = tokenize(query)
        if not terms:
            raise UnifiedModelError("RECALL_QUERY_EMPTY")
        total_docs = max(1, len(self.knowledge))
        k1, b = 1.5, 0.75
        scored: list[tuple[float, dict[str, Any]]] = []
        for i, row in enumerate(self.knowledge):
            counts = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
            length = self._knowledge_lengths[i] or 1
            score = 0.0
            for term in terms:
                tf = int(counts.get(term, 0))
                if tf <= 0:
                    continue
                df = max(1, self._knowledge_df.get(term, 1))
                idf = math.log(1.0 + (total_docs - df + 0.5) / (df + 0.5))
                score += idf * (tf * (k1 + 1)) / (
                    tf + k1 * (1.0 - b + b * length / self._avg_length)
                )
            # A document's own title is the strongest statement of what it is
            # about. Body term statistics alone can bury a short current law
            # under a long historical one that merely repeats its vocabulary.
            title_terms = set(row.get("title_terms") or [])
            if title_terms:
                overlap = len(set(terms) & title_terms) / max(1, len(set(terms)))
                if overlap >= 1.0:
                    score += 30.0
                elif overlap >= 0.5:
                    score += 10.0 * overlap
            if score > 0:
                scored.append((score, row))

        # Version rule, applied as a ranking invariant rather than a nudge.
        # The repository says the highest version in a law family is current and
        # every lower version is history. BM25 alone cannot know that: a long
        # superseded V4 out-scores a short current V8 on the family's own name.
        # So when the current member of a family is relevant at all, it is
        # lifted above every historical sibling. A query that matches only a
        # historical version still returns it -- history stays answerable, it
        # just cannot impersonate present-day authority.
        families: dict[str, dict[str, Any]] = {}
        for index, (score, row) in enumerate(scored):
            path = Path(str(row.get("path") or ""))
            match = re.fullmatch(r"(.+?)_V\d+\.md", path.name)
            if not match:
                continue
            entry = families.setdefault(match.group(1), {"current": None, "history": []})
            if row.get("authority") == "CURRENT_LAW":
                if entry["current"] is None or score > entry["current"][0]:
                    entry["current"] = (score, index)
            elif row.get("authority") in {"HISTORICAL_LAW_VERSION", "SUPERSEDED_LAW"}:
                entry["history"].append((score, index))
        adjusted = list(scored)
        for entry in families.values():
            if entry["current"] is None or not entry["history"]:
                continue
            current_score, current_index = entry["current"]
            history_max = max(score for score, _ in entry["history"])
            for score, index in entry["history"]:
                adjusted[index] = (score * 0.5, adjusted[index][1])
            adjusted[current_index] = (
                max(current_score, history_max * 1.25 + 1e-6),
                adjusted[current_index][1],
            )
        scored = adjusted
        scored.sort(key=lambda item: (-item[0], str(item[1].get("path") or "")))
        hits = []
        for score, row in scored[: max(1, int(top_k))]:
            path = ROOT / str(row.get("path"))
            excerpt = row.get("summary") or ""
            if path.is_file():
                excerpt = _excerpt(path, terms) or excerpt
            hits.append(
                {
                    "path": row.get("path"),
                    "title": row.get("title"),
                    "kind": row.get("kind"),
                    "authority": row.get("authority"),
                    "sha256": row.get("sha256"),
                    "score": round(score, 6),
                    "excerpt": excerpt,
                }
            )
        return {
            "schema": SOLUTION_SCHEMA,
            "operation": "RECALL",
            "model_digest": self.digest,
            "query": query,
            "query_tokens": terms,
            "hit_count": len(hits),
            "hits": hits,
            "knowledge_is_external": True,
            "credit": {
                "capability_credit_delta": 0,
                "ownership_credit_delta": 0,
                "terminal_credit_delta": 0,
            },
        }

    # ------------------------------------------------------------------- solve

    def solve(
        self,
        goal: str,
        *,
        inputs: Mapping[str, Any] | None = None,
        mode: str = "AUTO",
        capability_id: str | None = None,
        instance_id: str | None = None,
        context_paths: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        requested = str(mode or "AUTO").strip().upper()
        inputs = dict(inputs or {})
        if requested == "RECALL":
            return self.recall(goal)

        routing: dict[str, Any] | None = None
        if capability_id:
            cid = _normalise_capability_id(capability_id)
            if cid not in self.capabilities and cid not in self.engines:
                raise UnifiedModelError("CAPABILITY_NOT_IN_MODEL:" + cid)
            chosen = cid
        else:
            routing = self.route(goal)
            if not routing["confident"]:
                return self._failure(
                    goal,
                    "GOAL_NOT_REPRESENTED_IN_MODEL__FAIL_CLOSED",
                    routing=routing,
                )
            chosen = str(routing["best"]["id"])

        if chosen.startswith("engine:") or chosen.startswith("meta:"):
            return self._dispatch_engine(goal, chosen, inputs, routing)
        return self._execute_capability(
            goal, chosen, inputs, routing, instance_id, context_paths
        )

    # --------------------------------------------------------------- internals

    def _envelope(self, **extra: Any) -> dict[str, Any]:
        out = {
            "schema": SOLUTION_SCHEMA,
            "model_id": self.model.get("model_id"),
            "model_digest": self.digest,
            "credit": {
                "capability_credit_delta": 0,
                "ownership_credit_delta": 0,
                "terminal_credit_delta": 0,
            },
            "non_claims": list(NON_CLAIMS),
        }
        out.update(extra)
        return out

    def _failure(self, goal: str, reason: str, **extra: Any) -> dict[str, Any]:
        return self._envelope(
            operation="SOLVE",
            goal=goal,
            status="FAIL_CLOSED",
            **{"pass": False},
            reason=reason,
            **extra,
        )

    def _execute_capability(
        self,
        goal: str,
        cid: str,
        inputs: Mapping[str, Any],
        routing: Mapping[str, Any] | None,
        instance_id: str | None,
        context_paths: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        row = self.capabilities[cid]
        required = [str(x) for x in (row.get("input_names") or [])]
        inputs = dict(inputs)
        missing = [name for name in required if name not in inputs]
        binding_provenance: dict[str, Any] | None = None
        declared = [str(p) for p in (context_paths or []) if str(p).strip()]
        if missing and declared:
            # Only a caller-declared resource is ever used to fill a slot. With
            # no declaration this path is not taken at all, so the default
            # behaviour is unchanged and an unstated input still fails closed:
            # choosing a file the caller never named would be a choice about
            # what to operate on, and an unverifiable one.
            inputs, binding_provenance, missing = self._bind_from_declared_context(
                goal, cid, required, inputs, missing, declared
            )
        if missing:
            return self._failure(
                goal,
                "CAPABILITY_INPUTS_MISSING:" + ",".join(missing),
                routing=routing,
                capability_id=cid,
                required_inputs=required,
            )
        if str(row.get("incremental_spend_usd", 0)) not in {"0", "0.0"}:
            return self._failure(
                goal,
                "CAPABILITY_NONZERO_SPEND_REJECTED",
                routing=routing,
                capability_id=cid,
            )
        try:
            from canonical.runtime.verified_bound_capability_execution_adapter_v1 import (
                execute as execute_bound,
            )

            raw = execute_bound(
                cid,
                inputs=dict(inputs),
                instance_id=instance_id or ("UNIFIED-MODEL-" + cid),
            )
        except Exception as exc:  # the adapter fails closed; so do we
            return self._failure(
                goal,
                "CAPABILITY_EXECUTION_RAISED:" + type(exc).__name__ + ":" + str(exc),
                routing=routing,
                capability_id=cid,
            )
        passed = raw.get("pass") is True
        # Report what the adapter actually established, not a stronger word for
        # it. The adapter distinguishes a promoted capability whose execution
        # trace was independently checked
        # (PASS__PROMOTED_BOUND_CAPABILITY_EXECUTED_AND_TRACE_VERIFIED) from a
        # receipt-backed one that merely ran and reported success
        # (PASS__RECEIPT_BACKED_BOUND_CAPABILITY_EXECUTED). Relabelling both as
        # "TRACE_VERIFIED" asserted a check that never ran, which let a plain
        # goal that matched a script's filename claim verified execution of it.
        status = str(raw.get("status") or "")
        return self._envelope(
            operation="SOLVE",
            goal=goal,
            status=(
                status
                if passed and status.startswith("PASS__")
                else "FAIL_CLOSED__CAPABILITY_DID_NOT_PASS"
            ),
            **{"pass": bool(passed)},
            reason=None if passed else "CAPABILITY_DID_NOT_PASS",
            routing=routing,
            capability_id=cid,
            binding_provenance=binding_provenance,
            inputs_sha256=raw.get("inputs_sha256"),
            registry_file_sha256=raw.get("registry_file_sha256"),
            rendered_action_sha256=raw.get("rendered_action_sha256"),
            execution=raw,
        )

    def _bind_from_declared_context(
        self,
        goal: str,
        cid: str,
        required: list[str],
        inputs: dict[str, Any],
        missing: list[str],
        declared: list[str],
    ) -> tuple[dict[str, Any], dict[str, Any] | None, list[str]]:
        """Ground unfilled slots from resources the caller explicitly declared.

        The compiled rows carry ``input_names`` but not the registry's
        ``action_template``, and ``world_binding_v1`` reads placeholder names
        from that template, so a minimal one is synthesized here naming exactly
        the slots this capability declares. All grounding stays in the verified
        binder, which fails closed and refuses patterns and globs by design.

        ``declared`` is the whole of what may be used from the surrounding
        world. Nothing is discovered from the wider repository, so a slot can
        only ever be filled with something the caller put in front of the
        model -- or something the caller wrote into the goal sentence itself.
        """
        try:
            from canonical.runtime import world_binding_v1 as wb
        except Exception:
            return inputs, None, missing

        # A path the goal sentence names is the most grounded resource there
        # is: the caller typed it. Declared context supplements it, it must
        # never replace it.
        #
        # `complete_inputs` uses `goal_paths` verbatim whenever a list is
        # passed -- an empty list included -- so handing it `declared` alone
        # used to throw away the named file and let the binder invent another
        # one, while still reporting `missing: []`. A goal naming
        # BOUND_CAPABILITY_REGISTRY_V1.json came back bound to
        # MIGRATION_STATUS_2026-09-10.json. The named paths go first so they
        # win, and the declared ones are still available behind them.
        goal_named: list[str] = []
        try:
            from canonical.runtime import goal_compiler as _gc

            goal_named = [str(p[0]) for p in _gc._repo_paths(goal, wb.ROOT)]
        except Exception:
            goal_named = []

        candidates: list[str] = []
        seen: set[str] = set()
        for path in goal_named + [str(p) for p in declared]:
            if path not in seen:
                seen.add(path)
                candidates.append(path)

        entry = {
            "capability_id": cid,
            "action_template": {
                "args": {name: "${input." + name + "}" for name in required}
            },
        }
        try:
            outcome = wb.complete_inputs(goal, wb.ROOT, entry, goal_paths=candidates)
        except Exception:
            return inputs, None, missing

        # Both sources are caller-supplied: the sentence the caller wrote, and
        # the paths the caller declared. Neither is a discovery.
        allowed = {str(p) for p in declared} | set(goal_named)

        # A slot the capability's own contract declares as `effect_result` must
        # hold an artifact some other capability PRODUCED -- it names the effect
        # and the field to read it from. Filling it from a resource the caller
        # merely declared hands the capability an input that violates its own
        # declared contract, and the failure surfaces much later as an opaque
        # decode error rather than as the refusal it should have been.
        #
        # This is read from the registry contract, not inferred from the slot
        # name or the file's contents: no capability declares an input type, so
        # any type-based guess here would itself be an invention.
        produced_only: set[str] = set()
        try:
            from canonical.runtime import live_integrated_brain_v1 as _lb

            reg_entry = dict(_lb.load_verified_registry()).get(cid) or {}
            for name, spec in (reg_entry.get("proposal_bindings") or {}).items():
                if isinstance(spec, dict) and spec.get("type") == "effect_result":
                    produced_only.add(str(name))
        except Exception:
            produced_only = set()
        filled: dict[str, Any] = {}
        for key in missing:
            value = (outcome.get("inputs") or {}).get(key)
            if value is None:
                continue
            text = str(value)
            low = key.lower()
            # Three kinds of value carry no choice about what to operate on, and
            # only these three are admissible:
            #
            #   1. A destination the binder synthesized. Deterministic; nothing
            #      to defend.
            #   2. The caller's own words. A slot named goal/task/objective is
            #      the sentence that was handed in, not a discovered resource.
            #   3. A path the caller supplied -- either declared as context, or
            #      written into the goal sentence itself.
            #
            # Everything else is refused. That is what keeps `source_root`
            # unbound for a goal that never named a root: a default there would
            # be a choice about what to audit, and an unverifiable one.
            #
            # A slot the contract reserves for a PRODUCED artifact is refused
            # even when the caller supplied the path, because the capability
            # declares it reads that value from another capability's effect.
            is_destination = "output" in low
            is_callers_words = low in _GOAL_TEXT_SLOTS
            if key in produced_only:
                continue
            if not (is_destination or is_callers_words or text in allowed):
                continue
            filled[key] = value

        if not filled:
            return inputs, None, missing

        merged = dict(inputs)
        merged.update(filled)
        still_missing = [name for name in required if name not in merged]
        provenance = {
            "filled_from_declared_context": sorted(filled),
            "values": {k: filled[k] for k in sorted(filled)},
            "declared_context": list(declared),
            "source": str(outcome.get("source") or ""),
        }
        return merged, provenance, still_missing

    def _dispatch_engine(
        self,
        goal: str,
        eid: str,
        inputs: Mapping[str, Any],
        routing: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        row = self.engines[eid]
        mode = str(row.get("mode") or "")
        if not mode:
            return self._failure(goal, "ENGINE_MODE_MISSING", routing=routing, engine_id=eid)
        try:
            from canonical.runtime import unified_cognitive_fabric_v1 as fabric

            request = dict(inputs)
            request["mode"] = mode
            out = fabric.run(request)
        except Exception as exc:
            return self._failure(
                goal,
                "ENGINE_DISPATCH_FAILED:" + type(exc).__name__ + ":" + str(exc),
                routing=routing,
                engine_id=eid,
            )
        if not isinstance(out, Mapping):
            return self._failure(
                goal, "ENGINE_RESULT_NOT_AN_OBJECT", routing=routing, engine_id=eid
            )
        passed = out.get("pass") is True or str(out.get("status") or "").startswith("PASS")
        return self._envelope(
            operation="SOLVE",
            goal=goal,
            status=(
                "PASS__ENGINE_REPORTED_SUCCESS"
                if passed
                else "FAIL_CLOSED__ENGINE_DID_NOT_REPORT_SUCCESS"
            ),
            **{"pass": bool(passed)},
            reason=None if passed else "ENGINE_DID_NOT_REPORT_SUCCESS",
            routing=routing,
            engine_id=eid,
            engine_mode=mode,
            result=dict(out),
        )


# --------------------------------------------------------------------------- helpers


def _missing_declared_dependencies(row: Mapping[str, Any]) -> list[str]:
    """Resolve a capability's declared dependencies against *this* machine.

    The artifact records only the tree-derived declaration, so this answer is
    true of the machine that is answering rather than of whichever machine last
    compiled the model. Names in ``declared_dependency_executables`` are resolved
    on PATH; every other declared name is resolved through the Python import
    machinery.
    """
    declaration = row.get("declared_dependencies") or {}
    checked = declaration.get("declared_dependencies_checked") or []
    on_path = {str(name) for name in declaration.get("declared_dependency_executables") or []}
    missing: list[str] = []
    for entry in checked:
        name = str(entry)
        if not name:
            continue
        if name in on_path:
            found = shutil.which(name) is not None
        else:
            try:
                found = importlib.util.find_spec(name) is not None
            except (ImportError, ValueError):
                # A name the import machinery refuses to resolve is not
                # evidence of presence. Fail closed.
                found = False
        if not found:
            missing.append(name)
    return sorted(set(missing))


def _normalise_capability_id(value: str) -> str:
    cid = str(value or "").strip()
    if cid.startswith("bound:"):
        cid = cid[len("bound:"):]
    return cid


def _excerpt(path: Path, terms: Iterable[str], limit: int = 420) -> str:
    wanted = [t.casefold() for t in terms]
    best = ""
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if len(stripped) < 20:
                continue
            folded = stripped.casefold()
            if any(term in folded for term in wanted):
                best = " ".join(stripped.split())
                break
    except OSError:
        return ""
    return best[:limit]


def open_model(
    path: str | Path | None = None, *, root: str | Path | None = None
) -> UnifiedModel:
    return UnifiedModel(load_model(path, root=root, verify=True))


# --------------------------------------------------------------------------- cli


def _print(payload: Any) -> None:
    print(json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="brain_unified_model_v1",
        description="One front door over the compiled Brain model.",
    )
    parser.add_argument("--artifact", default=None, help="model artifact path")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="show model contents and non-claims")
    route_p = sub.add_parser("route", help="rank a plain goal against the model")
    route_p.add_argument("goal")
    route_p.add_argument("--top-k", type=int, default=5)
    recall_p = sub.add_parser("recall", help="just-in-time knowledge retrieval")
    recall_p.add_argument("query")
    recall_p.add_argument("--top-k", type=int, default=5)
    solve_p = sub.add_parser("solve", help="route and execute")
    solve_p.add_argument("goal")
    solve_p.add_argument("--inputs", default="{}", help="JSON object of inputs")
    solve_p.add_argument("--mode", default="AUTO", choices=["AUTO", "RECALL"])
    solve_p.add_argument("--capability-id", default=None)
    solve_p.add_argument("--instance-id", default=None)
    ns = parser.parse_args(argv)

    model = open_model(ns.artifact)
    if ns.command == "status":
        _print(model.status())
        return 0
    if ns.command == "route":
        _print(model.route(ns.goal, top_k=ns.top_k))
        return 0
    if ns.command == "recall":
        _print(model.recall(ns.query, top_k=ns.top_k))
        return 0
    try:
        inputs = json.loads(ns.inputs)
    except json.JSONDecodeError:
        _print({"status": "FAIL_CLOSED", "reason": "INPUTS_NOT_JSON"})
        return 2
    if not isinstance(inputs, dict):
        _print({"status": "FAIL_CLOSED", "reason": "INPUTS_NOT_OBJECT"})
        return 2
    out = model.solve(
        ns.goal,
        inputs=inputs,
        mode=ns.mode,
        capability_id=ns.capability_id,
        instance_id=ns.instance_id,
    )
    _print(out)
    return 0 if out.get("pass") or out.get("operation") == "RECALL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
