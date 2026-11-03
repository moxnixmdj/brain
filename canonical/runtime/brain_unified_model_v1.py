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
import marshal
import math
import os
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


# The compiler's own repository-path scanner, character class and all: a path
# literal is two or more "/"-joined segments. Kept byte-for-byte in step with
# ``goal_compiler._repo_paths_uncached`` -- if the two ever disagree, coverage is
# measured over words the caller never asked with.
_PATH_LITERAL = re.compile(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+")
_URL_LITERAL = re.compile(r"https?://[^\s)\]}>]+")


def path_literals(text: str, root: str | Path | None = None) -> list[str]:
    """The spans of ``text`` that name a real artifact, in sentence order.

    A literal counts only when something is actually there: the literal itself
    exists, or its parent directory does (so "write a new file into an existing
    directory" is still recognised as naming a destination). That requirement is
    what keeps prose out -- "and/or", "read/write" and "input/output" match the
    path shape but resolve to no parent directory, so they stay question words.
    """
    body = _URL_LITERAL.sub(" ", str(text or ""))
    rr = Path(ROOT if root is None else root).resolve()
    found: list[str] = []
    for match in _PATH_LITERAL.finditer(body):
        raw = match.group(0).rstrip(".,;:!?)]}")
        candidates: list[Path] = []
        start = match.start()
        if start > 0 and body[start - 1] == "/":
            candidates.append(Path("/" + raw))
        candidates.append(rr / raw)
        for candidate in candidates:
            try:
                if candidate.exists() or candidate.parent.is_dir():
                    break
            except OSError:
                continue
        else:
            continue
        found.append(match.group(0))
    return found


def ask_tokens(text: str, root: str | Path | None = None) -> list[str]:
    """The caller's ASK: the sentence with its stated path literals blanked out.

    ``route()`` fails closed when the model recognises too little of a sentence.
    Charging the tokens of a stated path to that budget made the verdict a
    lottery on how many times a sentence happened to repeat an indexed word.
    Measured: "/home/user/brain/canonical/astra_runtime/tmp/x/calc.py" alone
    contributes eleven tokens no capability can ever claim, so "Count the
    functions defined in the python file <that path> and write the report to
    <another path>" scored coverage 0.240 against the 0.34 floor and was refused
    as GOAL_NOT_REPRESENTED_IN_MODEL before a single capability was considered --
    while "Run the python tests ..." squeaked past at 0.257 only because the
    sentence repeats its own keywords.

    A path is a located artifact the binder will bind, not a word to be
    understood. It is the same distinction the compiler already draws for a
    quoted literal (a quoted literal's words are not the task's words) and for a
    bare version token (a name fragment, not a stated value). Scoring is left
    untouched: only the denominator of the coverage budget changes.
    """
    ask = str(text or "")
    for literal in path_literals(ask, root):
        ask = ask.replace(literal, " ")
    return tokenize(ask)


# --------------------------------------------------------------------------- loading


_VERIFIED_BLOB_DIGESTS: dict[str, str] = {}
_OPEN_MODEL_MEM_CACHE: dict[tuple[str, int, int], "UnifiedModel"] = {}


def _core_cache_dir() -> Path:
    return ROOT / "canonical" / "astra_runtime" / "tmp"


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
    raw_bytes = target.read_bytes()
    raw_sha = hashlib.sha256(raw_bytes).hexdigest()
    try:
        model = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UnifiedModelError("MODEL_ARTIFACT_NOT_JSON") from exc
    if not isinstance(model, dict) or model.get("schema") != SCHEMA:
        raise UnifiedModelError("MODEL_SCHEMA_MISMATCH")
    if verify:
        declared = (model.get("digest") or {}).get("value")
        cached_dig = _VERIFIED_BLOB_DIGESTS.get(raw_sha)
        if cached_dig is not None:
            recomputed = cached_dig
        else:
            recomputed = artifact_digest(model)
            if declared and declared == recomputed:
                _VERIFIED_BLOB_DIGESTS[raw_sha] = recomputed
        if not declared or declared != recomputed:
            raise UnifiedModelError("MODEL_DIGEST_MISMATCH")
    return model


def _declared_triggers_for_row(cid: str, row: Mapping[str, Any]) -> set[str]:
    id_tokens = set(tokenize(cid))
    return {
        str(t)
        for t in (row.get("triggers") or [])
        if str(t) not in id_tokens and len(str(t)) > 3
    }


def _extract_routing_core(model: Mapping[str, Any], raw_sha: str) -> dict[str, Any]:
    src_rows = [row for row in (model.get("source_index") or []) if isinstance(row, Mapping)]
    res_rows = [row for row in (model.get("research_index") or []) if isinstance(row, Mapping)]
    knw_rows = [row for row in (model.get("knowledge") or []) if isinstance(row, Mapping)]
    caps_map = {
        str(row["id"]): dict(row)
        for row in (model.get("capabilities") or [])
        if isinstance(row, Mapping) and row.get("id")
    }
    engines_map = {
        str(row["id"]): dict(row)
        for row in (model.get("engines") or [])
        if isinstance(row, Mapping) and row.get("id")
    }
    cap_id_terms = {
        cid: tuple(sorted(set(tokenize(cid.replace("/", " ").replace(".", " ")))))
        for cid in caps_map
    }
    receipt_ids = {
        cid for cid, row in caps_map.items() if row.get("kind") == "RECEIPT_BACKED_CAPABILITY"
    }
    trig_cache: dict[str, set[str]] = {}
    filtered_index: dict[str, dict[str, float]] = {}
    for tok, postings in ((model.get("grammar") or {}).get("index") or {}).items():
        s_tok = str(tok)
        kept: dict[str, float] = {}
        for raw_cid, weight in postings.items():
            cid = str(raw_cid)
            if cid in receipt_ids:
                trigs = trig_cache.get(cid)
                if trigs is None:
                    trigs = _declared_triggers_for_row(cid, caps_map.get(cid) or {})
                    trig_cache[cid] = trigs
                if s_tok not in trigs:
                    continue
            kept[cid] = float(weight)
        if kept:
            filtered_index[s_tok] = kept
    return {
        "core_format_v": 3,
        "raw_sha256": raw_sha,
        "schema": str(model.get("schema") or ""),
        "model_id": model.get("model_id"),
        "model_version": model.get("model_version"),
        "digest_value": str((model.get("digest") or {}).get("value") or ""),
        "counts": dict(model.get("counts") or {}),
        "objective_verbatim": (model.get("objective") or {}).get("verbatim"),
        "capabilities_map": caps_map,
        "engines_map": engines_map,
        "capability_id_terms": cap_id_terms,
        "receipt_backed_ids": tuple(sorted(receipt_ids)),
        "filtered_index": filtered_index,
        "adapter_ast_index": dict(((model.get("grammar") or {}).get("adapter_ast_index") or {})),
        "skills": [dict(row) for row in (model.get("skills") or []) if isinstance(row, Mapping)],
        "confidence": dict(((model.get("grammar") or {}).get("confidence") or {})),
        "source_index_len": len(src_rows),
        "source_entry_points": sum(1 for r in src_rows if r.get("classification") == "ENTRY_POINT"),
        "research_index_len": len(res_rows),
        "knowledge_len": len(knw_rows),
    }


# --------------------------------------------------------------------------- model


class UnifiedModel:
    """A loaded, digest-verified unified model."""

    def __init__(self, model: Mapping[str, Any], *, _raw_bytes: bytes | None = None, _core_only: bool = False):
        self._raw_bytes_backing: bytes | None = _raw_bytes
        self._declared_triggers_cache: dict[str, set[str]] = {}
        if _core_only and model.get("core_format_v") == 3:
            self._model_loaded: dict[str, Any] | None = None
            self._core_meta: dict[str, Any] = dict(model)
            self.digest = str(model.get("digest_value") or "")
            self.capabilities = dict(self._core_meta["capabilities_map"])
            self.engines = dict(self._core_meta["engines_map"])
            self._capability_id_terms = {
                cid: frozenset(terms)
                for cid, terms in (self._core_meta.get("capability_id_terms") or {}).items()
            }
            self.skills = list(self._core_meta.get("skills") or [])
            self.receipt_backed_ids: frozenset[str] = frozenset(self._core_meta.get("receipt_backed_ids") or ())
            self.index: dict[str, dict[str, float]] = dict(self._core_meta.get("filtered_index") or {})
            confidence = self._core_meta.get("confidence") or {}
        else:
            self._model_loaded = dict(model)
            self._core_meta = _extract_routing_core(self._model_loaded, "")
            self.digest = str((model.get("digest") or {}).get("value") or "")
            self.capabilities = dict(self._core_meta["capabilities_map"])
            self.engines = dict(self._core_meta["engines_map"])
            self._capability_id_terms = {
                cid: frozenset(terms)
                for cid, terms in self._core_meta["capability_id_terms"].items()
            }
            self.skills = list(self._core_meta["skills"])
            self.receipt_backed_ids = frozenset(self._core_meta["receipt_backed_ids"])
            self.index = dict(self._core_meta["filtered_index"])
            confidence = self._core_meta["confidence"]

        self._unrunnable: dict[str, list[str]] | None = None
        self._source_index_cache: dict[str, dict[str, Any]] | None = None
        self._source_df_cache: dict[str, int] | None = None
        self._research_index_cache: dict[str, dict[str, Any]] | None = None
        self._research_df_cache: dict[str, int] | None = None
        self._knowledge_cache: list[dict[str, Any]] | None = None
        self._knowledge_df_cache: dict[str, int] | None = None
        self._knowledge_lengths_cache: list[int] | None = None
        self._avg_length_cache: float | None = None

        self.min_score = float(confidence.get("minimum_best_score", 1.0))
        self.min_coverage = float(confidence.get("minimum_coverage", 0.34))
        if not _core_only:
            self._hydrate_secondary_indexes()

    def _ensure_full_model(self) -> dict[str, Any]:
        if self._model_loaded is None:
            if self._raw_bytes_backing is None:
                raise UnifiedModelError("MODEL_BACKING_BYTES_MISSING")
            self._model_loaded = json.loads(self._raw_bytes_backing.decode("utf-8"))
        return self._model_loaded

    def _hydrate_secondary_indexes(self) -> None:
        if self._source_index_cache is not None:
            return
        full = self._ensure_full_model()
        self._source_index_cache = {
            str(row["path"]): dict(row)
            for row in full.get("source_index") or []
            if isinstance(row, Mapping) and row.get("path")
        }
        src_df: dict[str, int] = {}
        for row in self._source_index_cache.values():
            terms = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
            for term in terms:
                src_df[str(term)] = src_df.get(str(term), 0) + 1
        self._source_df_cache = src_df

        self._research_index_cache = {
            str(row["path"]): dict(row)
            for row in full.get("research_index") or []
            if isinstance(row, Mapping) and row.get("path")
        }
        res_df: dict[str, int] = {}
        for row in self._research_index_cache.values():
            terms = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
            for term in terms:
                res_df[str(term)] = res_df.get(str(term), 0) + 1
        self._research_df_cache = res_df

        self._knowledge_cache = [
            dict(row) for row in (full.get("knowledge") or []) if isinstance(row, Mapping)
        ]
        knw_df: dict[str, int] = {}
        knw_len: list[int] = []
        for row in self._knowledge_cache:
            terms = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
            knw_len.append(sum(int(v) for v in terms.values()))
            for term in terms:
                knw_df[str(term)] = knw_df.get(str(term), 0) + 1
        self._knowledge_df_cache = knw_df
        self._knowledge_lengths_cache = knw_len
        self._avg_length_cache = (sum(knw_len) / len(knw_len) if knw_len else 1.0) or 1.0

    @property
    def model(self) -> dict[str, Any]:
        return self._ensure_full_model()

    @property
    def source_index(self) -> dict[str, dict[str, Any]]:
        self._hydrate_secondary_indexes()
        return self._source_index_cache  # type: ignore[return-value]

    @property
    def _source_df(self) -> dict[str, int]:
        self._hydrate_secondary_indexes()
        return self._source_df_cache  # type: ignore[return-value]

    @property
    def research_index(self) -> dict[str, dict[str, Any]]:
        self._hydrate_secondary_indexes()
        return self._research_index_cache  # type: ignore[return-value]

    @property
    def _research_df(self) -> dict[str, int]:
        self._hydrate_secondary_indexes()
        return self._research_df_cache  # type: ignore[return-value]

    @property
    def knowledge(self) -> list[dict[str, Any]]:
        self._hydrate_secondary_indexes()
        return self._knowledge_cache  # type: ignore[return-value]

    @property
    def _knowledge_df(self) -> dict[str, int]:
        self._hydrate_secondary_indexes()
        return self._knowledge_df_cache  # type: ignore[return-value]

    @property
    def _knowledge_lengths(self) -> list[int]:
        self._hydrate_secondary_indexes()
        return self._knowledge_lengths_cache  # type: ignore[return-value]

    @property
    def _avg_length(self) -> float:
        self._hydrate_secondary_indexes()
        return self._avg_length_cache  # type: ignore[return-value]

    # ------------------------------------------------------------------ status

    def status(self) -> dict[str, Any]:
        declared = self._core_meta.get("counts") or {}
        missing_ids = sorted(
            cid
            for cid, row in self.capabilities.items()
            if _missing_declared_dependencies(row)
        )
        present = len(self.capabilities) - len(missing_ids)
        src_len = (
            len(self._source_index_cache)
            if self._source_index_cache is not None
            else int(self._core_meta.get("source_index_len") or 0)
        )
        src_ep = (
            sum(1 for row in self._source_index_cache.values() if row.get("classification") == "ENTRY_POINT")
            if self._source_index_cache is not None
            else int(self._core_meta.get("source_entry_points") or 0)
        )
        res_len = (
            len(self._research_index_cache)
            if self._research_index_cache is not None
            else int(self._core_meta.get("research_index_len") or 0)
        )
        knw_len = (
            len(self._knowledge_cache)
            if self._knowledge_cache is not None
            else int(self._core_meta.get("knowledge_len") or 0)
        )
        return {
            "schema": SOLUTION_SCHEMA,
            "operation": "STATUS",
            "model_id": self._core_meta.get("model_id"),
            "model_version": self._core_meta.get("model_version"),
            "model_digest": self.digest,
            "counts": {
                "capabilities": len(self.capabilities),
                "bound_capabilities": declared.get("bound_capabilities"),
                "receipt_backed_capabilities": declared.get("receipt_backed_capabilities"),
                "engines": len(self.engines),
                "skills": len(self.skills),
                "knowledge_documents": knw_len,
                "source_index_modules": src_len,
                "source_index_entry_points": src_ep,
                "research_index_records": res_len,
                "routing_tokens": len(self.index),
            },
            "source_index_is_addressable_not_executable": True,
            "declared_dependencies_present": present,
            "declared_dependencies_missing": len(self.capabilities) - present,
            "objective": self._core_meta.get("objective_verbatim"),
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
        cached = self._declared_triggers_cache.get(cid)
        if cached is not None:
            return cached
        res = _declared_triggers_for_row(cid, self.capabilities.get(cid) or {})
        self._declared_triggers_cache[cid] = res
        return res

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

    def unrunnable_capabilities(self) -> dict[str, list[str]]:
        """Capabilities whose own declared dependencies do not resolve *here*.

        Resolved on the machine that is answering, never compiled in -- see
        ``_dependency_declaration``, which records the declaration precisely so
        that this answer can be true of the host rather than of whichever
        machine last built the artifact.

        A capability that cannot resolve the substrate it declares can only
        fail. Measured: ``python.contract.check.crosshair.v1`` -- whose adapter
        runs ``sys.executable -m crosshair`` on a machine without crosshair --
        was selected for eight of thirteen ordinary Python software-engineering
        sentences and failed every one of them with
        ``BOUND_PYPI_SOURCE_INCOMPLETE``, after spending the whole request
        getting there.

        This is reported by ``route()`` and enforced by ``solve()``. It is
        deliberately NOT used to filter the ranking: what the model contains is
        not a fact about one host, and this sandbox has pypdf while the CI
        runner does not, so hiding capabilities here would make routing
        host-dependent.
        """
        if self._unrunnable is None:
            found: dict[str, list[str]] = {}
            for cid, row in self.capabilities.items():
                missing = _missing_declared_dependencies(row)
                if missing:
                    found[cid] = missing
            self._unrunnable = found
        return self._unrunnable

    def route(self, goal: str, *, top_k: int = 5) -> dict[str, Any]:
        tokens = tokenize(goal)
        mentioned = self._ids_mentioned(goal)
        # Score the ASK, not the sentence. A stated path is data, and its tokens
        # are not words about the operation -- but they were voting. Measured on
        # "Report who calls the function top in the python source root
        # /home/user/brain/…": brain.module.function.invoke scored 674.3, of
        # which 405.0 was the token `brain` from the caller's own path counted
        # twice, and terminal.kstar.root.assess.stdlib scored 449.2 of which
        # 405.0 was the same two hits. The capability that owns `calls` lost to
        # two capabilities matched by the directory the file happens to live in.
        #
        # A capability's own id, stated in the goal, is the opposite case: it is
        # the ask, so its tokens do vote.
        addressed_tokens: list[str] = []
        for cid in mentioned:
            addressed_tokens.extend(tokenize(cid))
        # Say it twice, get one vote. "Report the call graph ... writing the
        # report to R" repeats `report`, and at 269.3 a hit that alone
        # outscored every operation word in the sentence -- the Markdown-to-PDF
        # converter, whose only match was that repeated destination noun,
        # measured 538.6 against 505.9 for the capability that owns `call` and
        # `graph`. Repetition is how a sentence is phrased, not extra evidence
        # about what is being asked, so each distinct token votes once.
        ask_list: list[str] = []
        seen: set[str] = set()
        for token in ask_tokens(goal) + addressed_tokens:
            if token not in seen:
                seen.add(token)
                ask_list.append(token)
        scores: dict[str, float] = {}
        matched: set[str] = set()
        unrunnable = self.unrunnable_capabilities()
        unrunnable_matched: set[str] = set()
        for token in ask_list:
            postings = self.index.get(token)
            if not postings:
                continue
            matched.add(token)
            for cid, weight in postings.items():
                if cid in unrunnable:
                    # Recorded, not removed. `route()` answers "what does the
                    # model contain", and that is not a fact about this host:
                    # the pinned route for "extract text from a pdf document"
                    # is pdf.extract.text.pypdf on every machine, and this
                    # sandbox happens to have pypdf while the CI runner does
                    # not. Hiding a capability here would make the ranking
                    # host-dependent, which is exactly what
                    # test_status_reports_the_machine_it_actually_runs_on
                    # exists to prevent. `solve()`, which does run things, is
                    # where the host gets a vote.
                    unrunnable_matched.add(cid)
                # A query token that is also in the capability id is direct
                # operation evidence, not merely effect vocabulary. Count that
                # same declared IDF posting a second time for the identity
                # channel. Measured on "Audit the python source tree with an
                # AST": the audit owner has four identity hits, while the
                # legacy tree-sitter parser's rare `tree` hit comes only from
                # its provides and otherwise steals the route.
                identity_weight = (
                    2.0 if token in self._capability_id_terms.get(cid, ()) else 1.0
                )
                scores[cid] = scores.get(cid, 0.0) + weight * identity_weight
        for cid in mentioned:
            scores[cid] = scores.get(cid, 0.0) + 24.0
            matched.add(cid.casefold())
        # A stated path is data the caller supplied and the binder will bind, not
        # a word of the ask. Charge only the ask to the coverage budget, so that
        # naming a real artifact can never be the reason a request is refused.
        #
        # A capability's own id is the ask, not a path. 294 of the model's ids
        # ARE repository paths -- "canonical/runtime/x_v1.py.auto.v1" -- and the
        # path grammar matches them whole, so blanking them left no ask at all:
        # coverage collapsed to 0.0 and every addressed capability stopped being
        # addressable. Measured, that regressed
        # test_every_capability_is_addressable_by_its_own_id on 294 subtests.
        #
        # And every token of an id the model contains is by definition a token
        # the model recognises, so those tokens are matched as well as asked.
        # Without that second half an addressed id measured 0.333 against the
        # 0.34 floor and still failed, on a filename token no index carries.
        ask = set(ask_list)
        addressed_set = set(addressed_tokens)
        matched_ask = (matched & ask) | addressed_set
        coverage = (len(matched_ask) / len(ask)) if ask else 0.0
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
            "unrunnable_on_this_host": sorted(unrunnable_matched),
            "confident": confident,
            "best": rows[0] if rows else None,
            "candidates": rows,
            "reason": (
                "ROUTED_WITHIN_MODEL"
                if confident
                else "GOAL_NOT_REPRESENTED_IN_MODEL__FAIL_CLOSED"
            ),
        }

    # -------------------------------------------------------------- source index

    def find_source(self, query: str, *, top_k: int = 5) -> dict[str, Any]:
        """Locate runtime source the model can *address* but cannot *execute*.

        This is deliberately not ``route`` and ``solve`` never calls it. The
        modules returned here have no receipt and no bound adapter, so naming one
        is an answer to "where is this?", never to "run this". Every row repeats
        ``executable: False`` so a caller cannot mistake a hit for a capability.
        """
        terms = tokenize(query)
        if not terms:
            raise UnifiedModelError("FIND_SOURCE_QUERY_EMPTY")
        wanted = set(terms)
        total_docs = max(1, len(self.source_index))
        scored: list[tuple[float, str, dict[str, Any]]] = []
        for path, row in self.source_index.items():
            counts = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
            if not counts:
                continue
            score = 0.0
            hit: set[str] = set()
            for term in wanted:
                tf = int(counts.get(term, 0) or 0)
                if tf <= 0:
                    continue
                hit.add(term)
                df = max(1, self._source_df.get(term, 1))
                # Same IDF form `recall` uses for knowledge, so a term that
                # appears in one module outranks one that appears in a thousand.
                score += math.log(1.0 + (total_docs - df + 0.5) / (df + 0.5)) * (1.0 + math.log(tf))
            if score <= 0.0:
                continue
            # Naming the file is an address, not a keyword, so it outranks term
            # overlap -- but only for the row actually named.
            if path.casefold() in query.casefold():
                score += 8.0
            scored.append((score, path, row))
        scored.sort(key=lambda item: (-item[0], item[1]))

        rows: list[dict[str, Any]] = []
        for score, path, row in scored[: max(1, int(top_k))]:
            rows.append(
                {
                    "path": path,
                    "id": row.get("id"),
                    "classification": row.get("classification"),
                    "sha256": row.get("sha256"),
                    "summary": row.get("summary") or "",
                    "symbol_count": int(row.get("symbol_count") or 0),
                    "matched_terms": sorted(wanted & set(row.get("terms") or ())),
                    "score": round(float(score), 6),
                    # The load-bearing part of this whole method.
                    "capability": False,
                    "executable": False,
                }
            )
        return {
            "schema": SOLUTION_SCHEMA,
            "operation": "FIND_SOURCE",
            "model_digest": self.digest,
            "query": query,
            "query_terms": terms,
            "candidates": rows,
            "best": rows[0] if rows else None,
            "indexed_modules": len(self.source_index),
            "reason": (
                "SOURCE_LOCATED__NOT_EXECUTABLE__NO_RECEIPT_OR_BOUND_ADAPTER"
                if rows
                else "NO_INDEXED_SOURCE_MATCHED"
            ),
        }

    # ---------------------------------------------------------- research index

    def find_research(self, query: str, *, top_k: int = 5) -> dict[str, Any]:
        """Locate the research record behind a decision or a capability.

        Governance decisions, verification receipts and action intents: what was
        claimed, when, and under which authority. A record is *evidence about* a
        capability, never a capability, so this is not ``route`` and ``solve``
        never calls it. Every row repeats ``capability: False``.
        """
        terms = tokenize(query)
        if not terms:
            raise UnifiedModelError("FIND_RESEARCH_QUERY_EMPTY")
        wanted = set(terms)
        total_docs = max(1, len(self.research_index))
        scored: list[tuple[float, str, dict[str, Any]]] = []
        for path, row in self.research_index.items():
            counts = row.get("terms") if isinstance(row.get("terms"), Mapping) else {}
            if not counts:
                continue
            score = 0.0
            for term in wanted:
                tf = int(counts.get(term, 0) or 0)
                if tf <= 0:
                    continue
                df = max(1, self._research_df.get(term, 1))
                # "v1" occurs in 79% of these records, so raw overlap is noise;
                # the same IDF form `recall` and `find_source` use.
                score += math.log(1.0 + (total_docs - df + 0.5) / (df + 0.5)) * (1.0 + math.log(tf))
            if score <= 0.0:
                continue
            # Naming a record by its action id is an address, not a keyword.
            action_id = str(row.get("action_id") or "")
            if action_id and action_id.casefold() in query.casefold():
                score += 8.0
            scored.append((score, path, row))
        scored.sort(key=lambda item: (-item[0], item[1]))

        rows: list[dict[str, Any]] = []
        for score, path, row in scored[: max(1, int(top_k))]:
            rows.append(
                {
                    "path": path,
                    "id": row.get("id"),
                    "schema": row.get("schema") or "",
                    "status": row.get("status") or "",
                    "date": row.get("date") or "",
                    "action_id": row.get("action_id") or "",
                    "sha256": row.get("sha256"),
                    "score": round(float(score), 6),
                    "capability": False,
                }
            )
        return {
            "schema": SOLUTION_SCHEMA,
            "operation": "FIND_RESEARCH",
            "model_digest": self.digest,
            "query": query,
            "query_terms": terms,
            "candidates": rows,
            "best": rows[0] if rows else None,
            "indexed_records": len(self.research_index),
            "reason": (
                "RESEARCH_RECORD_LOCATED__EVIDENCE_NOT_CAPABILITY"
                if rows
                else "NO_INDEXED_RESEARCH_MATCHED"
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
        cwd: str | Path | None = None,
    ) -> dict[str, Any]:
        requested = str(mode or "AUTO").strip().upper()
        inputs = dict(inputs or {})
        if requested == "RECALL":
            return self.recall(goal)
        if requested == "SOLVE_OR_LEARN":
            return self.act_or_learn(
                goal,
                inputs=inputs,
                capability_id=capability_id,
                instance_id=instance_id,
                context_paths=context_paths,
                cwd=cwd,
            )

        routing: dict[str, Any] | None = None
        ledger_db = inputs.pop("ledger_db_path", None) if isinstance(inputs, dict) and "ledger_db_path" in inputs else None
        ledger_pref: str | None = None
        if capability_id:
            cid = _normalise_capability_id(capability_id)
            if cid not in self.capabilities and cid not in self.engines:
                raise UnifiedModelError("CAPABILITY_NOT_IN_MODEL:" + cid)
            chosen = cid
        else:
            try:
                from canonical.swe_kernel.upstream_routing_ledger_v1 import default_ledger as _default_ledger

                _linfo = _default_ledger(ledger_db).lookup_shape(goal)
                _cand_pref = _linfo.get("preferred_capability")
                if _cand_pref and _cand_pref in self.capabilities:
                    ledger_pref = str(_cand_pref)
            except Exception:
                ledger_pref = None

            if ledger_pref:
                fast_routing = {
                    "confident": True,
                    "best": {"id": ledger_pref, "rule": "UPSTREAM_ROUTING_LEDGER_PREFERRED"},
                    "promoted_route": True,
                }
                fast_out = self._execute_capability(
                    goal, ledger_pref, inputs, fast_routing, instance_id, context_paths
                )
                if fast_out.get("pass") is True:
                    try:
                        from canonical.swe_kernel.upstream_routing_ledger_v1 import default_ledger as _default_ledger

                        _default_ledger(ledger_db).record_verified_route(goal, ledger_pref)
                    except Exception:
                        pass
                    return fast_out
                try:
                    from canonical.swe_kernel.upstream_routing_ledger_v1 import default_ledger as _default_ledger

                    _default_ledger(ledger_db).invalidate_preferred_capability(
                        goal, ledger_pref, reason=str(fast_out.get("reason") or "CAPABILITY_DID_NOT_PASS")
                    )
                except Exception:
                    pass

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
        out = self._execute_capability(
            goal, chosen, inputs, routing, instance_id, context_paths
        )
        if not capability_id and out.get("pass") is True:
            try:
                from canonical.swe_kernel.upstream_routing_ledger_v1 import default_ledger as _default_ledger

                _default_ledger(ledger_db).record_verified_route(goal, chosen)
            except Exception:
                pass
        return out

    def act_or_learn(
        self,
        goal: str,
        *,
        inputs: Mapping[str, Any] | None = None,
        capability_id: str | None = None,
        instance_id: str | None = None,
        context_paths: Iterable[str] | None = None,
        cwd: str | Path | None = None,
        db_path: str | Path | None = None,
        forged_state_path: str | Path | None = None,
        cognitive_core: Any | None = None,
        cognitive_state_dir: str | Path | None = None,
    ) -> dict[str, Any]:
        """Single unified front door (`K3 = 0`): System-1 `< 0.5 ms` reflex -> System-2 deliberation with Active-Inference self-belief."""
        from canonical.runtime.one_shot_reality_closure_v2 import REQUIRED_ATTEMPT_ORDER
        from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import solve_or_learn
        from canonical.swe_kernel.forged_binding_and_macro_spine_v1 import (
            match_and_invoke_forged_for_goal,
        )
        from canonical.swe_kernel.sentient_cognitive_core_v1 import SentientCognitiveCore

        active_core = (
            cognitive_core
            if cognitive_core is not None
            else SentientCognitiveCore(cognitive_state_dir)
        )
        r_preview = self.route(goal)
        has_reflex = bool(r_preview.get("confident")) or bool(capability_id)
        regime_info = active_core.decide_cognitive_regime(
            capability_id or goal[:96],
            has_consolidated_reflex=has_reflex,
            verification_kind="TEST_SUITE",
            host_ready=True,
            grounding_complete=bool(inputs) or bool(context_paths) or has_reflex,
        )
        pred_ticket = active_core.belief.predict_before_act(
            capability_id or goal[:96],
            memory_reflex_hit=has_reflex,
            grounding_complete=bool(inputs) or bool(context_paths) or has_reflex,
        )

        def _finalize_with_core(resp: dict[str, Any], inspector_name: str) -> dict[str, Any]:
            passed_f = bool(resp.get("pass") is True)
            settle = active_core.belief.settle_and_compute_surprise(
                pred_ticket,
                outcome_pass=passed_f,
                inspector=inspector_name,
                actual_cost=0.25 if regime_info["regime"] == "SYSTEM_1_REFLEX" else 1.0,
                actual_gain=1.0 if passed_f else 0.0,
            )
            resp["cognitive_regime"] = regime_info
            resp["epistemic_settlement"] = {
                "predicted_pass_probability": pred_ticket.predicted_pass_probability,
                "surprise": settle["surprise"],
                "escalate_system2": settle["escalate_system2"],
            }
            return resp

        # 0A. Verified Skill Macro Compression (`verified_skill_macro_planner_v1.plan_with_skills`)
        if isinstance(inputs, Mapping) and isinstance(inputs.get("skill_macro_problem"), Mapping):
            from canonical.runtime import verified_skill_macro_planner_v1 as macro_pl

            sm_spec = inputs["skill_macro_problem"]
            macro_out = macro_pl.plan_with_skills(
                sm_spec["problem"],
                list(sm_spec.get("verified_skills") or ()),
                active_invalidators=tuple(sm_spec.get("active_invalidators") or ()),
            )
            passed_m = bool(macro_out.get("status") == "SOLVED" or macro_out.get("pass") is True)
            return self._envelope(
                operation="SOLVE_OR_LEARN",
                goal=goal,
                status="PASS__VERIFIED_SKILL_MACRO_PLANNED" if passed_m else "FAIL_CLOSED__SKILL_MACRO_UNSOLVED",
                **{"pass": passed_m},
                reason=None if passed_m else str(macro_out.get("status") or "UNSOLVED"),
                skill_macro_plan=macro_out,
                attempt_order_contract=list(REQUIRED_ATTEMPT_ORDER),
            )

        # 0B. R1+R2+R3 Adaptive Capability Expansion (`universal_verified_adaptive_solver_v12.run`)
        if isinstance(inputs, Mapping) and isinstance(inputs.get("adaptive_solver_v12_problem"), Mapping):
            from canonical.runtime import universal_verified_adaptive_solver_v12 as uvas12

            v12_spec = dict(inputs["adaptive_solver_v12_problem"])
            prob_doc = v12_spec.pop("problem")
            v12_repo = v12_spec.pop("repo_root", cwd or ROOT)
            v12_out = uvas12.run(prob_doc, repo_root=v12_repo, **v12_spec)
            passed_v12 = bool(v12_out.get("pass") is True)
            return self._envelope(
                operation="SOLVE_OR_LEARN",
                goal=goal,
                status=str(v12_out.get("status") or ("PASS__ADAPTIVE_SOLVER_V12" if passed_v12 else "FAIL_CLOSED")),
                **{"pass": passed_v12},
                reason=None if passed_v12 else str(v12_out.get("reason") or v12_out.get("status")),
                adaptive_solver_v12=v12_out,
                attempt_order_contract=list(REQUIRED_ATTEMPT_ORDER),
            )

        # 0C. Direct specialist routes (`r2_adequacy_request`, `scientific_discovery_problem`, `trace_capsule_problem`, `policy_adequacy_problem`, `ooxml_preflight_target`)
        if isinstance(inputs, Mapping) and any(
            k in inputs
            for k in (
                "r2_adequacy_request",
                "scientific_discovery_problem",
                "trace_capsule_problem",
                "policy_adequacy_problem",
                "policy_cover_payload",
                "escape_repair_state",
                "ooxml_preflight_target",
                "domain_mapping_problem",
            )
        ):
            spec_payload: dict[str, Any] = {"goal": goal, **dict(inputs)}
            if forged_state_path is not None:
                spec_payload["forged_state_path"] = str(forged_state_path)
            ctrl_spec = solve_or_learn(
                spec_payload,
                cwd=cwd or ROOT,
                db_path=str(db_path) if db_path is not None else None,
            )
            passed_spec = bool(ctrl_spec.get("pass") is True)
            return self._envelope(
                operation="SOLVE_OR_LEARN",
                goal=goal,
                status=str(ctrl_spec.get("status") or ("PASS__SPECIALIST_SOLVED" if passed_spec else "FAIL_CLOSED")),
                **{"pass": passed_spec},
                reason=None if passed_spec else str(ctrl_spec.get("failure_class") or ctrl_spec.get("status")),
                tier_used=ctrl_spec.get("tier_used"),
                autonomous_result=ctrl_spec,
                attempt_order_contract=list(REQUIRED_ATTEMPT_ORDER),
            )

        # 1. SYSTEM-1 REFLEX: REUSE_EXISTING_CAPABILITY via compiled UnifiedModel when confident & epistemically trusted
        is_forged_cid = bool(capability_id and str(capability_id).startswith("forged."))
        if not is_forged_cid and (regime_info["regime"] == "SYSTEM_1_REFLEX" or capability_id is not None):
            primary = self.solve(
                goal,
                inputs=inputs,
                mode="AUTO",
                capability_id=capability_id,
                instance_id=instance_id,
                context_paths=context_paths,
            )
            if primary.get("pass") is True or capability_id is not None:
                primary["attempt_order_contract"] = list(REQUIRED_ATTEMPT_ORDER)
                return _finalize_with_core(primary, "VerifiedBoundCapabilityExecutionAdapter")
        else:
            primary = {"pass": False, "reason": "ESCALATED_TO_SYSTEM_2_DELIBERATION" if not is_forged_cid else "FORGED_CAPABILITY_TARGETED"}

        # 2. Check self-forged capabilities (`forged.*`) with independent byte re-read
        try:
            forged_out = match_and_invoke_forged_for_goal(
                goal,
                root=cwd or ROOT,
                state_path=forged_state_path,
                explicit_args=inputs,
            )
            if forged_out is not None and forged_out.get("pass") is True:
                return _finalize_with_core(
                    self._envelope(
                        operation="SOLVE_OR_LEARN",
                        goal=goal,
                        status="PASS__FORGED_CAPABILITY_EXECUTED_AND_BYTE_VERIFIED",
                        **{"pass": True},
                        reason=None,
                        capability_id=forged_out["capability_id"],
                        forged_execution=forged_out,
                        attempt_order_contract=list(REQUIRED_ATTEMPT_ORDER),
                    ),
                    "ForgedInvokerByteReReadVerifier",
                )
        except Exception:
            pass

        # 3. SYSTEM-2 DELIBERATION: Escalate into 4-tier zero-LLM `solve_or_learn` (preserves honest fail-closed refusals!)
        req_payload: dict[str, Any] = {"goal": goal}
        if inputs:
            req_payload.update(dict(inputs))
        if forged_state_path is not None:
            req_payload["forged_state_path"] = str(forged_state_path)
        ctrl_out = solve_or_learn(
            req_payload,
            cwd=cwd or ROOT,
            db_path=str(db_path) if db_path is not None else None,
        )
        passed = ctrl_out.get("pass") is True
        return _finalize_with_core(
            self._envelope(
                operation="SOLVE_OR_LEARN",
                goal=goal,
                status=str(ctrl_out.get("status") or ("PASS__AUTONOMOUS_SOLVED" if passed else "FAIL_CLOSED")),
                **{"pass": bool(passed)},
                reason=None if passed else str(ctrl_out.get("failure_class") or ctrl_out.get("status") or primary.get("reason")),
                tier_used=ctrl_out.get("tier_used"),
                autonomous_result=ctrl_out,
                attempt_order_contract=list(REQUIRED_ATTEMPT_ORDER),
            ),
            "ClosedLoopAutonomousControllerVerifier",
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
        # A deliberate omission, recorded so it is not re-tried: refusing here
        # when `_missing_declared_dependencies(row)` is non-empty looks like the
        # obvious place for the host to vote, and it is not. Five pinned
        # DeclaredContextBindingTests drive pdf.extract.text.pypdf end to end
        # and assert on the *reason* and on `binding_provenance`; a dependency
        # refusal placed before the binder replaced
        # CAPABILITY_INPUTS_MISSING with a different string and short-circuited
        # the provenance they read. Measured in CI: 5 failures, all of them
        # negative controls about binding, none of them about dependencies.
        #
        # The adapters already fail closed on their own absent substrate, and
        # presence is reported by `status()` and by `unrunnable_capabilities()`.
        # What was actually broken was that the dependency was never DECLARED
        # at all, so nothing could report it. That is fixed in the compiler.
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
    base = Path(root or ROOT).resolve()
    target = Path(path) if path else base / DEFAULT_ARTIFACT
    if not target.is_absolute():
        target = base / target
    if not target.is_file():
        raise UnifiedModelError("MODEL_ARTIFACT_MISSING:" + str(target))
    st = target.stat()
    mem_key = (str(target.resolve()), st.st_size, st.st_mtime_ns)
    mem_hit = _OPEN_MODEL_MEM_CACHE.get(mem_key)
    if mem_hit is not None:
        return mem_hit

    raw_bytes = target.read_bytes()
    raw_sha = hashlib.sha256(raw_bytes).hexdigest()
    cache_dir = _core_cache_dir()
    cache_file = cache_dir / f"unified_model_core_{raw_sha[:32]}.marshal"
    if cache_file.is_file():
        try:
            core = marshal.loads(cache_file.read_bytes())
            if (
                isinstance(core, dict)
                and core.get("core_format_v") == 3
                and core.get("raw_sha256") == raw_sha
                and core.get("schema") == SCHEMA
            ):
                _VERIFIED_BLOB_DIGESTS[raw_sha] = str(core.get("digest_value") or "")
                inst = UnifiedModel(core, _raw_bytes=raw_bytes, _core_only=True)
                _OPEN_MODEL_MEM_CACHE[mem_key] = inst
                return inst
        except Exception:
            pass

    full = load_model(target, root=base, verify=True)
    core = _extract_routing_core(full, raw_sha)
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        tmp_f = cache_dir / f".unified_model_core_{raw_sha[:32]}.{os.getpid()}.tmp"
        tmp_f.write_bytes(marshal.dumps(core))
        tmp_f.replace(cache_file)
    except OSError:
        pass
    inst = UnifiedModel(core, _raw_bytes=raw_bytes, _core_only=True)
    inst._model_loaded = full
    _OPEN_MODEL_MEM_CACHE[mem_key] = inst
    return inst


def adapter_ast_entry(rel_path: str, expected_sha256: str | None = None) -> dict[str, Any] | None:
    """Fast RAM lookup of compile-time verified adapter AST metadata (`defaulted_keys` + `dispatch_ops`)."""
    try:
        inst = open_model()
        idx = inst._core_meta.get("adapter_ast_index") or {}
        row = idx.get(rel_path)
        if not isinstance(row, Mapping):
            return None
        if expected_sha256 is not None and str(row.get("sha256") or "") != expected_sha256:
            return None
        return dict(row)
    except Exception:
        return None


# --------------------------------------------------------------------------- cli


SOVEREIGN_ZERO_LLM_MODEL_SPEC = "canonical.runtime.brain_unified_model_v1:brain_model_callable"


def brain_model_callable(goal: str, seeing: dict[str, Any]) -> str | None:
    """Zero-LLM (`K3 = 0`) `BRAIN_MODEL` callable conforming to `canonical.runtime.model_v1`.

    Observes kernel truth `seeing`, emits `"DONE"` once the requested state transition
    is verified in `seeing`, emits deterministic Python code when grounded, and
    abstains (`None`) when the goal has no grounded route or evidence.
    """
    text = str(goal or "").strip()
    if not text or not isinstance(seeing, dict):
        return None
    previews = seeing.get("preview") if isinstance(seeing.get("preview"), dict) else (
        seeing.get("previews") if isinstance(seeing.get("previews"), dict) else {}
    )
    raw_files = seeing.get("tree") if seeing.get("tree") is not None else (seeing.get("files") or ())
    file_set = set(raw_files.keys()) if isinstance(raw_files, dict) else {str(x) for x in raw_files}
    last = seeing.get("last") if isinstance(seeing.get("last"), dict) else None

    write_m = re.match(r"^\s*write\s+(.+?)\s+to\s+([A-Za-z0-9_./-]+)\s*[.!]*$", text, re.IGNORECASE)
    if write_m:
        payload_raw = write_m.group(1).strip().strip("'\"")
        rel_dst = write_m.group(2).strip()
        if ".." in Path(rel_dst).parts or rel_dst.startswith("/"):
            return None
        if rel_dst in file_set and str(previews.get(rel_dst, "")).strip() == payload_raw:
            return None
        return (
            f"import pathlib\n"
            f"_p = pathlib.Path({rel_dst!r})\n"
            f"_p.parent.mkdir(parents=True, exist_ok=True)\n"
            f"_p.write_text({(payload_raw + chr(10))!r}, encoding='utf-8')\n"
        )

    if last is not None:
        if last.get("exit") == 0 and seeing.get("changed"):
            return None
        return None

    if not file_set:
        return None
    try:
        routed = open_model().route(text, top_k=1)
        ranked = routed.get("ranked_capabilities") or []
        if not ranked or float(ranked[0].get("score") or 0.0) <= 0.0:
            return None
        cid = str(ranked[0].get("id") or "")
        if not cid:
            return None
        repo_root = str(ROOT)
        return (
            f"import pathlib, sys\n"
            f"sys.path.insert(0, {repo_root!r})\n"
            f"from canonical.runtime.brain_unified_model_v1 import open_model\n"
            f"_res = open_model().solve({text!r}, declared_resources={sorted(file_set)!r})\n"
            f"if not _res.get('pass'):\n"
            f"    raise SystemExit(1)\n"
        )
    except Exception:
        return None


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
    solve_p.add_argument("--mode", default="AUTO", choices=["AUTO", "RECALL", "SOLVE_OR_LEARN"])
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
