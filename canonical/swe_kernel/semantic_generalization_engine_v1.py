"""Neuro-symbolic compositional & causal generalization engine (Problem 2).

This module replaces the original keyword/TF-IDF design, which was a lookup
with synonyms: it could not say *why* an answer was right, it silently
mis-counted whenever the question fell outside two hard-coded verbs, and its
"confidence" was a vocabulary overlap score. That design is gone. The four
pillars below are the mechanism; every answer the engine emits carries a
receipt chain that shows which pillar produced it and why it is believed.

Pillar 1 — OnlineParametricPolicyModel
    A genuinely trainable parametric model (weight matrices W_op, W_concept,
    W_domain) trained online with cross-entropy gradient descent on verified
    experiences. It corroborates the symbolic parse and is used for ranking
    and for the pre/post-loss learning receipt (loss_before > loss_after,
    ||ΔW||₂ recorded). It NEVER emits an answer on its own: a confident
    matrix cannot override an honest refusal, and an uncertain matrix cannot
    veto a verified parse.

Pillar 2 — SemanticTaskParser + CompositionalProgramSynthesizer
    A typed parser producing a SemanticTaskAST:
        operation ∈ {count, list, breakdown, exists, compare}
        concept   ∈ 19 Python-AST concepts (function, async_function, class,
                    method, if_statement, for_loop, while_loop, loop, import,
                    return_statement, try_block, raise_statement, call,
                    assignment, assertion, comprehension, decorator,
                    docstring, parameter) plus domain-native concepts
                    (heading, section, code_block, bullet, link, word, line,
                    key, entry, object, array, number, string, boolean, null,
                    row, column, cell, character)
        qualifiers ∈ public, private, name_prefix, name_suffix, name_contains,
                    min_args, max_args, has_decorator, has_docstring
    The synthesizer compiles the AST into an explicit, inspectable plan
    (LOAD → PARSE_<domain> → SELECT_<concept> → FILTER_qualifiers →
    REDUCE_<operation>) that is executed by a deterministic interpreter.
    Composition is real: operations, concepts and qualifiers combine freely
    instead of being matched as whole phrases.

Pillar 3 — CrossDomainSchemaTransfer
    The same abstract operator schema is instantiated per domain through a
    domain adapter registry. Nothing about "how many X" is baked to Python:
    the adapter declares how X is parsed, selected and reduced in Markdown
    (headings/fenced code blocks/bullets/links/words/lines), JSON (keys,
    entries, objects, arrays, numbers, strings, booleans, nulls), CSV
    (rows/columns/cells) and plain text (lines/words/characters). Python
    concepts asked about inside Markdown fenced code blocks are transferred
    through the composition: PARSE_markdown → EXTRACT_python_blocks →
    PARSE_python → SELECT_<concept>. Termination of the transfer is always
    a verified program run, never a recall of a previous answer.

Pillar 4 — CausalMechanismVerifier
    Why is the answer right? Because the synthesized program is probed on
    interventions, in the spirit of Pearl's do-operator:

      * precondition checks        — targets exist, domain parses, the
                                     concept/operation are known, the
                                     qualifier combination is feasible and
                                     applicable to the concept.
      * positive_intervention      — do(source := synthetic fixture with a
        probe                        hand-computed answer). The program must
                                     reproduce the known answer.
      * null_probe                 — do(source := fixture with zero matches).
                                     The program must answer 0 / [].
      * confounder_probe           — do(source := fixture full of the
                                     target's surface words in comments and
                                     strings). The program must NOT be fooled
                                     by lexical confounds (AST grounding).
      * postconditions             — the answer's type/sign/shape matches the
                                     operation (int ≥ 0 for count, list of
                                     names for list, ...).

    Any failed precondition, probe or postcondition converts the run into
    FAIL_CLOSED__* with the failing probe named in the receipt. There is no
    path from "the verifier disagrees" to a returned answer.

Honesty boundaries (all fail closed, never guess):
    * unrecognized operation / concept        → FAIL_CLOSED__OPERATION_UNRECOGNIZED / __CONCEPT_UNRECOGNIZED
    * no target file in the goal              → FAIL_CLOSED__NO_TARGET_FILE
    * target does not exist / unreadable      → FAIL_CLOSED__TARGET_NOT_FOUND
    * unknown or unparseable domain           → FAIL_CLOSED__DOMAIN_UNRECOGNIZED / __DOMAIN_PARSE_FAILED
    * negated request                         → FAIL_CLOSED__UNGROUNDED_NEGATION
    * qualifier inapplicable to the concept   → FAIL_CLOSED__INAPPLICABLE_QUALIFIER
    * qualifier combination is infeasible     → FAIL_CLOSED__QUALIFIER_COMBINATION_INFEASIBLE
    * any causal probe / postcondition fails  → FAIL_CLOSED__CAUSAL_VERIFICATION_FAILED

What this engine deliberately does NOT do: it does not solve open-ended
engineering goals ("fix the failing tests"), it does not invent concepts it
has no selector for, and it does not convert low probability into an answer.
It answers exactly the compositional counting/listing/breakdown family that
it can ground, verify, and explain — and refuses the rest.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import io
import json
import math
import random
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_NEUROSYMBOLIC_GENERALIZATION_ENGINE_V1"
PLAN_SCHEMA = "BRAIN_GENERALIZATION_PLAN_V1"

_REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Shared lexicon
# ---------------------------------------------------------------------------

PY_CONCEPTS = (
    "function", "async_function", "class", "method", "if_statement",
    "for_loop", "while_loop", "loop", "import", "return_statement",
    "try_block", "raise_statement", "call", "assignment", "assertion",
    "comprehension", "decorator", "docstring", "parameter",
)
MARKDOWN_CONCEPTS = ("heading", "section", "code_block", "bullet", "link", "word", "line")
JSON_CONCEPTS = ("key", "entry", "object", "array", "number", "string", "boolean", "null")
CSV_CONCEPTS = ("row", "column", "cell")
TEXT_CONCEPTS = ("line", "word", "character")
ALL_CONCEPTS = tuple(dict.fromkeys(PY_CONCEPTS + MARKDOWN_CONCEPTS + JSON_CONCEPTS + CSV_CONCEPTS + TEXT_CONCEPTS))

OPERATIONS = ("count", "list", "breakdown", "exists", "compare")
DOMAINS = ("python_ast", "markdown", "json", "csv", "text")

_EXT_TO_DOMAIN = {
    ".py": "python_ast",
    ".md": "markdown", ".markdown": "markdown",
    ".json": "json", ".jsonl": "json",
    ".csv": "csv", ".tsv": "csv",
    ".txt": "text", ".text": "text", ".log": "text",
}

_NAMED_CONCEPTS = ("function", "async_function", "class", "method")
_FUNCTION_CONCEPTS = ("function", "async_function", "method")

#: Which concepts are coherent per domain (python concepts transfer into
#: markdown fenced code blocks). An out-of-domain concept is refused honestly.
_DOMAIN_CONCEPTS = {
    "python_ast": tuple(PY_CONCEPTS),
    "markdown": tuple(MARKDOWN_CONCEPTS) + tuple(PY_CONCEPTS),
    "json": tuple(JSON_CONCEPTS),
    "csv": tuple(CSV_CONCEPTS),
    "text": tuple(TEXT_CONCEPTS),
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# ---------------------------------------------------------------------------
# Failure taxonomy
# ---------------------------------------------------------------------------

class CausalVerificationFailure(Exception):
    """A causal probe or postcondition failed; the run must not emit an answer."""

    def __init__(self, probe: str, detail: str):
        super().__init__(f"{probe}: {detail}")
        self.probe = probe
        self.detail = detail


class QualifierFailure(Exception):
    """The qualifier set is inapplicable to the concept or infeasible."""


# ===========================================================================
# Pillar 1 — Online parametric policy model
# ===========================================================================

def _hash_features(text: str, n_features: int = 128) -> list[float]:
    """Hashed bag of unigrams+bigrams, L2-normalised. Deterministic."""
    vec = [0.0] * n_features
    words = re.findall(r"\w+", text.lower())
    grams = list(words) + [f"{words[i]}_{words[i + 1]}" for i in range(len(words) - 1)]
    for gram in grams:
        h = hashlib.sha256(gram.encode("utf-8")).hexdigest()
        idx = int(h, 16) % n_features
        sign = 1.0 if int(h, 16) % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _init_matrix(rows: int, cols: int, seed: int) -> list[list[float]]:
    rng = random.Random(seed)
    return [[rng.uniform(-0.1, 0.1) for _ in range(cols)] for _ in range(rows)]


def _softmax(logits: Sequence[float]) -> list[float]:
    m = max(logits)
    exps = [math.exp(x - m) for x in logits]
    total = sum(exps) or 1.0
    return [e / total for e in exps]


class OnlineParametricPolicyModel:
    """Trainable weight matrices updated online from verified experiences.

    Three linear heads (op / concept / domain) over hashed text features,
    trained with cross-entropy gradient descent plus decoupled weight decay.
    Every update returns a verifiable receipt: pre/post loss, pre/post
    probability assigned to the verified label, and ||ΔW||₂.
    """

    OP_LABELS = OPERATIONS
    CONCEPT_LABELS = ALL_CONCEPTS
    DOMAIN_LABELS = DOMAINS

    def __init__(self, n_features: int = 128, state_path: Path | None = None):
        self.n_features = n_features
        self.state_path = Path(state_path) if state_path else (
            _REPO_ROOT / "canonical/astra_runtime/generalization/GENERALIZATION_POLICY_V1.json"
        )
        self.W_op = _init_matrix(n_features, len(self.OP_LABELS), seed=0xA01)
        self.W_concept = _init_matrix(n_features, len(self.CONCEPT_LABELS), seed=0xB02)
        self.W_domain = _init_matrix(n_features, len(self.DOMAIN_LABELS), seed=0xC03)
        self.updates = 0
        self._load()

    # -- persistence ---------------------------------------------------------
    def _load(self) -> None:
        try:
            if self.state_path and self.state_path.is_file():
                data = json.loads(self.state_path.read_text(encoding="utf-8"))
                if data.get("schema") == "BRAIN_ONLINE_PARAMETRIC_POLICY_V1":
                    self.W_op = data["W_op"]
                    self.W_concept = data["W_concept"]
                    self.W_domain = data["W_domain"]
                    self.updates = int(data.get("updates", 0))
        except Exception:
            # A corrupt policy state must never break solving: start fresh.
            pass

    def _save(self) -> None:
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "schema": "BRAIN_ONLINE_PARAMETRIC_POLICY_V1",
                "n_features": self.n_features,
                "op_labels": list(self.OP_LABELS),
                "concept_labels": list(self.CONCEPT_LABELS),
                "domain_labels": list(self.DOMAIN_LABELS),
                "W_op": self.W_op,
                "W_concept": self.W_concept,
                "W_domain": self.W_domain,
                "updates": self.updates,
            }
            self.state_path.write_text(json.dumps(payload), encoding="utf-8")
        except Exception:
            pass

    # -- inference -----------------------------------------------------------
    @staticmethod
    def _head_probs(features: Sequence[float], W: Sequence[Sequence[float]], labels: Sequence[str]) -> dict[str, float]:
        logits = []
        for j in range(len(labels)):
            s = 0.0
            for i, f in enumerate(features):
                if f:
                    s += W[i][j] * f
            logits.append(s)
        probs = _softmax(logits)
        return dict(zip(labels, probs))

    def predict(self, goal: str) -> dict[str, Any]:
        features = _hash_features(goal, self.n_features)
        op_p = self._head_probs(features, self.W_op, self.OP_LABELS)
        concept_p = self._head_probs(features, self.W_concept, self.CONCEPT_LABELS)
        domain_p = self._head_probs(features, self.W_domain, self.DOMAIN_LABELS)
        best_op, best_op_p = max(op_p.items(), key=lambda kv: kv[1])
        best_concept, best_concept_p = max(concept_p.items(), key=lambda kv: kv[1])
        best_domain, best_domain_p = max(domain_p.items(), key=lambda kv: kv[1])
        return {
            "operation": op_p,
            "concept": concept_p,
            "domain": domain_p,
            "best_operation": best_op,
            "best_operation_prob": round(best_op_p, 6),
            "best_concept": best_concept,
            "best_concept_prob": round(best_concept_p, 6),
            "best_domain": best_domain,
            "best_domain_prob": round(best_domain_p, 6),
            "updates": self.updates,
        }

    # -- training ------------------------------------------------------------
    @staticmethod
    def _loss_and_probs(features, W, labels, target_index):
        logits = []
        for j in range(len(labels)):
            s = 0.0
            for i, f in enumerate(features):
                if f:
                    s += W[i][j] * f
            logits.append(s)
        probs = _softmax(logits)
        loss = -math.log(max(probs[target_index], 1e-12))
        return loss, probs

    def loss(self, goal: str, operation: str, concept: str, domain: str) -> float:
        features = _hash_features(goal, self.n_features)
        total = 0.0
        for labels, W, target in (
            (self.OP_LABELS, self.W_op, self.OP_LABELS.index(operation)),
            (self.CONCEPT_LABELS, self.W_concept, self.CONCEPT_LABELS.index(concept)),
            (self.DOMAIN_LABELS, self.W_domain, self.DOMAIN_LABELS.index(domain)),
        ):
            loss, _ = self._loss_and_probs(features, W, labels, target)
            total += loss
        return total / 3.0

    def update_from_experience(
        self,
        goal: str,
        operation: str,
        concept: str,
        domain: str,
        *,
        learning_rate: float = 0.05,
        weight_decay: float = 1e-4,
        persist: bool = True,
    ) -> dict[str, Any]:
        """One verified experience → one gradient step on every head."""
        features = _hash_features(goal, self.n_features)
        pre_total, pre_correct_prob = 0.0, 1.0
        heads = []
        for labels, W, target_name in (
            (self.OP_LABELS, self.W_op, operation),
            (self.CONCEPT_LABELS, self.W_concept, concept),
            (self.DOMAIN_LABELS, self.W_domain, domain),
        ):
            ti = labels.index(target_name)
            loss, probs = self._loss_and_probs(features, W, labels, ti)
            pre_total += loss
            pre_correct_prob *= probs[ti]
            grad = list(probs)
            grad[ti] -= 1.0  # d(CE)/dz
            heads.append((W, grad, labels, ti))
        pre_loss = pre_total / 3.0

        delta_sq = 0.0
        for W, grad, labels, ti in heads:
            for i, f in enumerate(features):
                if not f:
                    continue
                row = W[i]
                for j in range(len(labels)):
                    g = grad[j] * f + weight_decay * row[j]
                    change = learning_rate * g
                    row[j] -= change
                    delta_sq += change * change

        post_total, post_correct_prob = 0.0, 1.0
        for labels, W, target_name in (
            (self.OP_LABELS, self.W_op, operation),
            (self.CONCEPT_LABELS, self.W_concept, concept),
            (self.DOMAIN_LABELS, self.W_domain, domain),
        ):
            ti = labels.index(target_name)
            loss, probs = self._loss_and_probs(features, W, labels, ti)
            post_total += loss
            post_correct_prob *= probs[ti]
        post_loss = post_total / 3.0

        self.updates += 1
        if persist:
            self._save()
        return {
            "schema": "BRAIN_POLICY_UPDATE_RECEIPT_V1",
            "pre_loss": round(pre_loss, 6),
            "post_loss": round(post_loss, 6),
            "loss_delta": round(pre_loss - post_loss, 6),
            "pre_correct_prob": round(pre_correct_prob, 6),
            "post_correct_prob": round(post_correct_prob, 6),
            "delta_w_l2": round(math.sqrt(delta_sq), 6),
            "learning_rate": learning_rate,
            "weight_decay": weight_decay,
            "heads_updated": ["op", "concept", "domain"],
            "updates": self.updates,
        }


# ===========================================================================
# Pillar 2 — typed parsing of the task into a SemanticTaskAST
# ===========================================================================

_FILE_RE = re.compile(
    r"(?<![\w./-])((?:/)?(?:[\w.\-]+/)*[\w\-][\w.\-]*\.(?:py|md|markdown|json|jsonl|csv|tsv|txt|text|log))\b"
)

_NEGATION_RE = re.compile(
    r"\b(without|does\s*not\s+contain|doesn't\s+contain|don't\s+contain|do\s+not\s+contain|not\s+contain|contain(?:s)?\s+no\b)",
    re.IGNORECASE,
)

_OP_COUNT_RE = re.compile(r"\b(count|counts|counted|how\s+many|number\s+of|tally|total\s+number\s+of)\b", re.IGNORECASE)
_OP_BREAKDOWN_RE = re.compile(r"\b(breakdown|distribution|histogram|per[- ]type|by\s+type|by\s+kind)\b", re.IGNORECASE)
_OP_EXISTS_RE = re.compile(r"\b(is\s+there|are\s+there|does\b.*\bcontain|any\b)\b", re.IGNORECASE)
_OP_COMPARE_RE = re.compile(r"\b(compare|versus|vs\.?|difference\s+between)\b", re.IGNORECASE)
_OP_LIST_RE = re.compile(
    r"\b(list|lists|listed|show|shows|enumerate|enumerates|display|displays|names?\s+of|what\s+are|which|identify|identifies)\b",
    re.IGNORECASE,
)

# Concept lexicon: regex → canonical concept. Multi-word / longer forms first.
_CONCEPT_PATTERNS: Sequence[tuple[re.Pattern[str], str]] = tuple(
    (re.compile(p, re.IGNORECASE), c)
    for p, c in [
        (r"\basync[\s_]+(?:def[\s_]+|function[\s_]+)?(?:functions?|methods?|defs?|subroutines?)\b", "async_function"),
        (r"\b(?:function|functions|subroutine|subroutines|routine|routines|method|methods|def|defs|definition|definitions)\b", "function"),
        (r"\b(?:class|classes|type|types|exception|exceptions)\b", "class"),
        (r"\bif[\s_]+(?:statement|statements|branch|branches|clause|clauses)\b", "if_statement"),
        (r"\b(?:if|elif|else)[\s_]+statement\b", "if_statement"),
        (r"\bfor[\s_]+loop(?:s)?\b", "for_loop"),
        (r"\bwhile[\s_]+loop(?:s)?\b", "while_loop"),
        (r"\bloop(?:s)?\b", "loop"),
        (r"\bimport[\s_]+(?:statement|statements)?\b", "import"),
        (r"\bfrom\s+imports?\b", "import"),
        (r"\breturn[\s_]+statement(?:s)?\b", "return_statement"),
        (r"\btry[\s_]+(?:block|blocks|statement|statements)\b", "try_block"),
        (r"\bexception[\s_]+handler(?:s)?\b", "try_block"),
        (r"\braise[\s_]+statement(?:s)?\b", "raise_statement"),
        (r"\b(?:function[\s_]+)?calls?[\s_]+sites?\b", "call"),
        (r"\bcall[\s_]+sites?\b", "call"),
        (r"\bcalls\b", "call"),
        (r"\b(?:assignment|assignments|assigned)[\s_]+(?:statement|statements)?\b", "assignment"),
        (r"\bassert(?:s|ion|ions)?\b", "assertion"),
        (r"\b(?:list|dict|set|generator)\s+comprehensions?\b|\bcomprehensions?\b", "comprehension"),
        (r"\bdecorator(?:s)?\b", "decorator"),
        (r"\bdocstring(?:s)?\b", "docstring"),
        (r"\b(?:parameter|parameters|param|params|argument|arguments|arg|args)\b", "parameter"),
        # Markdown domain
        (r"\b(?:heading|headings|header|headers)\b", "heading"),
        (r"\bsection(?:s)?\b", "section"),
        (r"\b(?:code\s+block|code\s+blocks|fenced\s+code|code\s+fence|code\s+fences)\b", "code_block"),
        (r"\b(?:bullet|bullets|list\s+item|list\s+items)\b", "bullet"),
        (r"\blink(?:s)?\b", "link"),
        # JSON domain
        (r"\bentr(?:y|ies)\b", "entry"),
        (r"\bkey(?:s)?\b", "key"),
        (r"\bobject(?:s)?\b", "object"),
        (r"\barray(?:s)?\b", "array"),
        (r"\bnumber(?:s)?\b", "number"),
        (r"\bstring(?:s)?\b", "string"),
        (r"\b(?:boolean|booleans|bool)\b", "boolean"),
        (r"\bnull(?:s)?\b", "null"),
        # CSV domain
        (r"\brow(?:s)?\b", "row"),
        (r"\bcolumn(?:s)?\b", "column"),
        (r"\bcell(?:s)?\b", "cell"),
        # Text domain
        (r"\bcharacter(?:s)?\b", "character"),
        (r"\bword(?:s)?\b", "word"),
        (r"\bline(?:s)?\b", "line"),
    ]
)

# "method" was mapped into "function" above only when combined with async/function words;
# give bare "method(s)" its own concept.
_METHOD_BARE_RE = re.compile(r"\bmethods?\b", re.IGNORECASE)

_MIN_ARGS_RES = [
    re.compile(r"(?:at\s+least|minimum\s+of|a\s+minimum\s+of|min(?:imum)?\s+of)\s+(\d+)\s*(?:parameters|params?|arguments|args?)", re.IGNORECASE),
    re.compile(r"with\s+(\d+)\s+or\s+more\s+(?:parameters|params?|arguments|args?)", re.IGNORECASE),
    re.compile(r"(\d+)\s*\+\s*(?:parameters|params?|arguments|args?)", re.IGNORECASE),
]
_MAX_ARGS_RES = [
    re.compile(r"(?:at\s+most|maximum\s+of|a\s+maximum\s+of|max(?:imum)?\s+of|no\s+more\s+than)\s+(\d+)\s*(?:parameters|params?|arguments|args?)", re.IGNORECASE),
    re.compile(r"with\s+(\d+)\s+or\s+fewer\s+(?:parameters|params?|arguments|args?)", re.IGNORECASE),
]
_NAME_PREFIX_RE = re.compile(r"(?:named|prefixed\s+with|name\s+prefix(?:\s+of|\s*[:=])?|starts?\s+with)\s*['\"`]?([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)
_NAME_SUFFIX_RE = re.compile(r"(?:suffix(?:ed)?\s+with|end(?:s|ing)?\s+with)\s*['\"`]?([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)
_NAME_CONTAINS_RE = re.compile(r"(?:containing|name\s+contains?|substring)\s*['\"`]?([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)
_HAS_DECORATOR_RE = re.compile(r"\b(?:with|has|having|including|and)\s+(?:a\s+|an\s+)?decorators?\b|\bdecorated\b", re.IGNORECASE)
_HAS_DOCSTRING_RE = re.compile(r"\b(?:with|has|having|including|and)\s+(?:a\s+|an\s+)?docstrings?\b|\bdocumented\b", re.IGNORECASE)
_PUBLIC_RE = re.compile(r"\bpublic\b", re.IGNORECASE)
_PRIVATE_RE = re.compile(r"\bprivate\b", re.IGNORECASE)


@dataclass
class SemanticTaskAST:
    operation: str
    concept: str
    domain: str
    targets: list[str]
    qualifiers: dict[str, Any]
    confidence: float
    notes: list[str]
    raw_goal: str
    unparsed_qualifiers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "concept": self.concept,
            "domain": self.domain,
            "targets": list(self.targets),
            "qualifiers": dict(self.qualifiers),
            "confidence": self.confidence,
            "notes": list(self.notes),
            "raw_goal": self.raw_goal,
            "unparsed_qualifiers": list(self.unparsed_qualifiers),
        }


def _domain_for_target(path: str) -> str | None:
    ext = Path(path).suffix.lower()
    return _EXT_TO_DOMAIN.get(ext)


def parse_task(goal: str) -> SemanticTaskAST:
    """Parse a goal into a typed SemanticTaskAST. Never raises; confidence and
    notes carry uncertainty. Unparseable requests get operation='unknown' or
    concept='unknown' and are refused downstream."""
    text = goal.strip()
    notes: list[str] = []

    # --- targets (multi-file aware) ---
    targets: list[str] = []
    for m in _FILE_RE.finditer(text):
        candidate = m.group(1)
        if candidate not in targets:
            targets.append(candidate)

    # --- domain ---
    domains = {_domain_for_target(t) for t in targets} - {None}
    if len(domains) == 1:
        domain = next(iter(domains))
    elif len(domains) > 1:
        domain = "mixed"
        notes.append("targets span multiple domains")
    elif targets:
        domain = "unknown"
        notes.append("no domain adapter for target extension")
    else:
        domain = "unknown"

    # --- operation ---
    if _OP_BREAKDOWN_RE.search(text):
        operation = "breakdown"
    elif _OP_COMPARE_RE.search(text):
        operation = "compare"
    elif _OP_COUNT_RE.search(text):
        operation = "count"
    elif _OP_EXISTS_RE.search(text):
        operation = "exists"
    elif _OP_LIST_RE.search(text):
        operation = "list"
    else:
        operation = "unknown"
        notes.append("no operation verb recognized")

    # --- concept ---
    concept = "unknown"
    allowed = _DOMAIN_CONCEPTS.get(domain)  # None when no target was found: unfiltered, refused later anyway

    def _allowed(candidate: str) -> bool:
        return allowed is None or candidate in allowed

    async_match = re.search(
        r"\basync[\s_]+(?:def[\s_]+|function[\s_]+|method[\s_]+)?(?:functions?|methods?|defs?|subroutines?)\b",
        text, re.IGNORECASE,
    )
    bare_method = _METHOD_BARE_RE.search(text)
    if async_match and _allowed("async_function"):
        concept = "async_function"
    elif bare_method and _allowed("method"):
        concept = "method"
    else:
        for pattern, candidate in _CONCEPT_PATTERNS:
            if candidate == "async_function":
                continue
            if not _allowed(candidate):
                continue
            m = pattern.search(text)
            if m:
                concept = candidate
                break
    # breakdown needs no concept: it distributes over all domain concepts
    if concept == "unknown" and operation == "breakdown":
        concept = "all"
    if concept == "unknown":
        notes.append("no concept recognized")

    # 'function calls' phrasing belongs to 'call', not 'function'
    if re.search(r"\bfunction\s+calls\b", text, re.IGNORECASE):
        concept = "call"

    # --- qualifiers ---
    qualifiers: dict[str, Any] = {}
    if _PUBLIC_RE.search(text):
        qualifiers["public"] = True
    if _PRIVATE_RE.search(text):
        qualifiers["private"] = True
    for rx in _MIN_ARGS_RES:
        m = rx.search(text)
        if m:
            qualifiers["min_args"] = int(m.group(1))
            break
    for rx in _MAX_ARGS_RES:
        m = rx.search(text)
        if m:
            qualifiers["max_args"] = int(m.group(1))
            break
    m = _NAME_PREFIX_RE.search(text)
    if m:
        qualifiers["name_prefix"] = m.group(1)
    m = _NAME_SUFFIX_RE.search(text)
    if m:
        qualifiers["name_suffix"] = m.group(1)
    m = _NAME_CONTAINS_RE.search(text)
    if m:
        qualifiers["name_contains"] = m.group(1)
    if _HAS_DECORATOR_RE.search(text):
        qualifiers["has_decorator"] = True
    if _HAS_DOCSTRING_RE.search(text):
        qualifiers["has_docstring"] = True

    # an argument-count marker the parser could not turn into a bound means
    # the qualifier would be silently dropped -- refuse instead
    unparsed_qualifiers: list[str] = []
    if (
        "min_args" not in qualifiers
        and "max_args" not in qualifiers
        and re.search(r"\b(at\s+least|at\s+most|minimum|maximum|or\s+more|or\s+fewer|no\s+more\s+than)\s+\d+", text, re.IGNORECASE)
    ):
        unparsed_qualifiers.append("argument_count")

    # --- confidence ---
    confidence = 0.2
    if operation != "unknown":
        confidence += 0.3
    if concept != "unknown":
        confidence += 0.3
    if targets:
        confidence += 0.15
    if domain not in ("unknown", "mixed"):
        confidence += 0.05
    confidence = min(1.0, confidence)

    return SemanticTaskAST(
        operation=operation,
        concept=concept,
        domain=domain,
        targets=targets,
        qualifiers=qualifiers,
        confidence=round(confidence, 3),
        notes=notes,
        raw_goal=text,
        unparsed_qualifiers=unparsed_qualifiers,
    )


# ===========================================================================
# Pillar 2/3 — plan synthesis and the deterministic interpreter
# ===========================================================================

def synthesize_plan(task: SemanticTaskAST) -> dict[str, Any]:
    pipeline = ["LOAD"]
    if task.concept == "all":
        domain_parse = {
            "python_ast": "PARSE_PYTHON_AST",
            "markdown": "PARSE_MARKDOWN",
            "json": "PARSE_JSON",
            "csv": "PARSE_CSV",
            "text": "READ_TEXT",
        }.get(task.domain, "PARSE_UNKNOWN")
        pipeline += [domain_parse, "SELECT_ALL_CONCEPTS"]
    elif task.domain == "python_ast":
        pipeline += ["PARSE_PYTHON_AST", f"SELECT_{task.concept.upper()}"]
    elif task.domain == "markdown":
        if task.concept in PY_CONCEPTS:
            pipeline += ["PARSE_MARKDOWN", "EXTRACT_FENCED_CODE_BLOCKS", "PARSE_PYTHON_AST", f"SELECT_{task.concept.upper()}"]
        else:
            pipeline += ["PARSE_MARKDOWN", f"SELECT_{task.concept.upper()}"]
    elif task.domain == "json":
        pipeline += ["PARSE_JSON", f"SELECT_{task.concept.upper()}"]
    elif task.domain == "csv":
        pipeline += ["PARSE_CSV", f"SELECT_{task.concept.upper()}"]
    elif task.domain == "text":
        pipeline += ["READ_TEXT", f"SELECT_{task.concept.upper()}"]
    else:
        pipeline += ["PARSE_UNKNOWN"]
    if task.qualifiers:
        pipeline.append("FILTER_QUALIFIERS")
    pipeline.append(f"REDUCE_{task.operation.upper()}")
    return {
        "schema": PLAN_SCHEMA,
        "operation": task.operation,
        "concept": task.concept,
        "domain": task.domain,
        "targets": list(task.targets),
        "qualifiers": dict(task.qualifiers),
        "pipeline": pipeline,
    }


# --- python AST selection ---------------------------------------------------

_TRY_TYPES = tuple(t for t in (getattr(ast, "Try", None), getattr(ast, "TryStar", None)) if t is not None)


def _iter_nodes_source_order(tree: ast.AST):
    """Pre-order (source order) node iteration, unlike ast.walk's BFS.

    Answers name lists in the order a reader meets them in the file, which is
    the least surprising contract for a counting/listing tool.
    """
    stack: list[ast.AST] = [tree]
    while stack:
        node = stack.pop()
        yield node
        children = list(ast.iter_child_nodes(node))
        stack.extend(reversed(children))


def _parent_map(tree: ast.AST) -> dict[int, ast.AST | None]:
    pm: dict[int, ast.AST | None] = {}

    def visit(node: ast.AST, parent: ast.AST | None) -> None:
        pm[id(node)] = parent
        for child in ast.iter_child_nodes(node):
            visit(child, node)

    visit(tree, None)
    return pm


def _nparams(func: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    a = func.args
    return (
        len(a.posonlyargs) + len(a.args) + len(a.kwonlyargs)
        + (1 if a.vararg else 0) + (1 if a.kwarg else 0)
    )


def _node_name(node: ast.AST) -> str:
    for attr in ("name", "id", "arg", "module"):
        value = getattr(node, attr, None)
        if isinstance(value, str):
            return value
    return type(node).__name__


def _select_python(tree: ast.AST, concept: str) -> list[ast.AST]:
    parents = _parent_map(tree)

    def defs():
        return [n for n in _iter_nodes_source_order(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]

    if concept == "function":
        return [n for n in _iter_nodes_source_order(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if concept == "async_function":
        return [n for n in _iter_nodes_source_order(tree) if isinstance(n, ast.AsyncFunctionDef)]
    if concept == "class":
        return [n for n in _iter_nodes_source_order(tree) if isinstance(n, ast.ClassDef)]
    if concept == "method":
        return [n for n in defs() if isinstance(parents.get(id(n)), ast.ClassDef)]
    if concept == "if_statement":
        return [n for n in _iter_nodes_source_order(tree) if isinstance(n, ast.If)]
    if concept == "for_loop":
        return [n for n in _iter_nodes_source_order(tree) if isinstance(n, (ast.For, ast.AsyncFor))]
    if concept == "while_loop":
        return [n for n in _iter_nodes_source_order(tree) if isinstance(n, ast.While)]
    if concept == "loop":
        return [n for n in _iter_nodes_source_order(tree) if isinstance(n, (ast.For, ast.AsyncFor, ast.While))]
    if concept == "import":
        return [n for n in _iter_nodes_source_order(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    if concept == "return_statement":
        return [n for n in _iter_nodes_source_order(tree) if isinstance(n, ast.Return)]
    if concept == "try_block":
        return [n for n in _iter_nodes_source_order(tree) if isinstance(n, _TRY_TYPES)]
    if concept == "raise_statement":
        return [n for n in _iter_nodes_source_order(tree) if isinstance(n, ast.Raise)]
    if concept == "call":
        return [n for n in _iter_nodes_source_order(tree) if isinstance(n, ast.Call)]
    if concept == "assignment":
        return [n for n in _iter_nodes_source_order(tree) if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign))]
    if concept == "assertion":
        return [n for n in _iter_nodes_source_order(tree) if isinstance(n, ast.Assert)]
    if concept == "comprehension":
        return [n for n in _iter_nodes_source_order(tree) if isinstance(n, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp))]
    if concept == "decorator":
        nodes: list[ast.AST] = []
        for n in _iter_nodes_source_order(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                nodes.extend(getattr(n, "decorator_list", []))
        return nodes
    if concept == "docstring":
        return [
            n for n in _iter_nodes_source_order(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and ast.get_docstring(n) is not None
        ]
    if concept == "parameter":
        params: list[ast.AST] = []
        for n in defs():
            a = n.args
            params.extend(list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs))
            if a.vararg is not None:
                params.append(a.vararg)
            if a.kwarg is not None:
                params.append(a.kwarg)
        return params
    return []


def _named(node: ast.AST) -> bool:
    return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))


def _parameter_owner(tree: ast.AST, param: ast.arg) -> str | None:
    parents = _parent_map(tree)
    p = parents.get(id(param))
    while p is not None and not isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)):
        p = parents.get(id(p))
    return p.name if p is not None else None  # type: ignore[return-value]


def _qualifier_applies(node: ast.AST, concept: str) -> bool:
    if concept in _FUNCTION_CONCEPTS or concept == "class":
        return _named(node)
    if concept == "parameter":
        return False  # parameters are qualified through their function in this engine: refused honestly
    return False


def _apply_qualifiers(nodes: list[ast.AST], qualifiers: Mapping[str, Any], concept: str) -> list[ast.AST]:
    out = list(nodes)
    if qualifiers.get("public"):
        out = [n for n in out if _named(n) and not _node_name(n).startswith("_")]
    if qualifiers.get("private"):
        out = [n for n in out if _named(n) and _node_name(n).startswith("_")]
    if "name_prefix" in qualifiers:
        pref = str(qualifiers["name_prefix"])
        out = [n for n in out if _named(n) and _node_name(n).startswith(pref)]
    if "name_suffix" in qualifiers:
        suff = str(qualifiers["name_suffix"])
        out = [n for n in out if _named(n) and _node_name(n).endswith(suff)]
    if "name_contains" in qualifiers:
        needle = str(qualifiers["name_contains"])
        out = [n for n in out if _named(n) and needle in _node_name(n)]
    if "min_args" in qualifiers:
        k = int(qualifiers["min_args"])
        out = [n for n in out if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and _nparams(n) >= k]
    if "max_args" in qualifiers:
        k = int(qualifiers["max_args"])
        out = [n for n in out if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and _nparams(n) <= k]
    if qualifiers.get("has_decorator"):
        out = [n for n in out if _named(n) and len(getattr(n, "decorator_list", [])) > 0]
    if qualifiers.get("has_docstring"):
        out = [n for n in out if _named(n) and ast.get_docstring(n) is not None]
    return out


_ARG_QUALIFIERS = ("min_args", "max_args")
_NAME_QUALIFIERS = ("public", "private", "name_prefix", "name_suffix", "name_contains", "has_decorator", "has_docstring")
_ALL_QUALIFIER_KEYS = _ARG_QUALIFIERS + _NAME_QUALIFIERS


def _check_qualifier_applicability(concept: str, domain: str, qualifiers: Mapping[str, Any]) -> None:
    if not qualifiers:
        return
    if domain != "python_ast":
        raise QualifierFailure(f"qualifiers are not applicable in domain {domain!r}")
    if concept not in _NAMED_CONCEPTS:
        raise QualifierFailure(f"qualifiers are only applicable to named definitions (function/async_function/class/method), not {concept!r}")
    if concept == "class" and any(k in qualifiers for k in _ARG_QUALIFIERS):
        raise QualifierFailure("argument-count qualifiers are not applicable to classes")
    # feasibility of the argument window
    mn, mx = qualifiers.get("min_args"), qualifiers.get("max_args")
    if mn is not None and mx is not None and int(mn) > int(mx):
        raise QualifierFailure(f"infeasible argument window: min_args={mn} > max_args={mx}")


def _describe_node(node: ast.AST, concept: str, tree: ast.AST | None = None) -> str:
    line = getattr(node, "lineno", 0)
    if concept == "parameter":
        owner = _parameter_owner(tree, node) if tree is not None and isinstance(node, ast.arg) else None
        name = _node_name(node)
        return f"{name} (in {owner})@L{line}" if owner else f"{name}@L{line}"
    if concept == "decorator":
        return f"decorator@L{line}"
    return f"{_node_name(node)}@L{line}"


def _list_name(node: ast.AST, concept: str) -> str:
    if concept == "parameter":
        return _node_name(node)
    if concept == "decorator":
        return type(node).__name__
    return _node_name(node)


# --- markdown parsing -------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+")
_MD_LINK_RE = re.compile(r"\[[^\]]+\]\([^)]+\)")
_MD_WORD_RE = re.compile(r"\w+")
_FENCE_RE = re.compile(r"^\s*```([A-Za-z0-9_+\-]*)\s*$")


@dataclass
class MarkdownStructure:
    headings: list[tuple[int, str, int]] = field(default_factory=list)      # (level, text, lineno)
    bullets: list[tuple[str, int]] = field(default_factory=list)            # (text, lineno)
    links: list[tuple[str, int]] = field(default_factory=list)              # (target, lineno)
    code_blocks: list[tuple[str, str, int]] = field(default_factory=list)   # (lang, code, start_lineno)
    lines: list[str] = field(default_factory=list)


def parse_markdown(text: str) -> MarkdownStructure:
    structure = MarkdownStructure(lines=text.splitlines())
    in_block = False
    fence_lang = ""
    block_lines: list[str] = []
    block_start = 0
    for lineno, raw in enumerate(structure.lines, start=1):
        fence = _FENCE_RE.match(raw)
        if fence:
            if not in_block:
                in_block = True
                fence_lang = fence.group(1).lower()
                block_lines = []
                block_start = lineno
            else:
                in_block = False
                structure.code_blocks.append((fence_lang, "\n".join(block_lines), block_start))
            continue
        if in_block:
            block_lines.append(raw)
            continue
        heading = _HEADING_RE.match(raw)
        if heading:
            structure.headings.append((len(heading.group(1)), heading.group(2).strip(), lineno))
            continue
        if _BULLET_RE.match(raw):
            structure.bullets.append((_BULLET_RE.sub("", raw).strip(), lineno))
        for link in _MD_LINK_RE.finditer(raw):
            structure.links.append((link.group(0), lineno))
    if in_block:  # unterminated fence: the block still exists and counts honestly
        structure.code_blocks.append((fence_lang, "\n".join(block_lines), block_start))
    return structure


def _select_markdown(structure: MarkdownStructure, concept: str) -> list[Any]:
    if concept in ("heading", "section"):
        return structure.headings
    if concept == "code_block":
        return structure.code_blocks
    if concept == "bullet":
        return structure.bullets
    if concept == "link":
        return structure.links
    if concept == "word":
        return _MD_WORD_RE.findall("\n".join(structure.lines))
    if concept == "line":
        return structure.lines
    return []


def _python_blocks(structure: MarkdownStructure) -> list[tuple[str, int]]:
    blocks = []
    for lang, code, start in structure.code_blocks:
        if lang in ("", "python", "py", "python3"):
            blocks.append((code, start))
    return blocks


# --- JSON selection ---------------------------------------------------------

def _select_json(node: Any, concept: str, *, _root: bool = True, _path: str = "$") -> list[tuple[str, Any]]:
    out: list[tuple[str, Any]] = []
    if isinstance(node, dict):
        if concept in ("key", "entry"):
            if concept == "key" or _root:
                for k in node:
                    out.append((f"{_path}.{k}", k))
        if concept == "object":
            out.append((_path, node))
        for k, v in node.items():
            out.extend(_select_json(v, concept, _root=False, _path=f"{_path}.{k}"))
    elif isinstance(node, list):
        if concept == "array":
            out.append((_path, node))
        for i, v in enumerate(node):
            out.extend(_select_json(v, concept, _root=False, _path=f"{_path}[{i}]"))
    elif isinstance(node, bool):
        if concept == "boolean":
            out.append((_path, node))
    elif isinstance(node, (int, float)):
        if concept == "number":
            out.append((_path, node))
    elif isinstance(node, str):
        if concept == "string":
            out.append((_path, node))
    elif node is None:
        if concept == "null":
            out.append((_path, node))
    return out


# --- CSV selection ----------------------------------------------------------

def _parse_csv(text: str, delimiter: str | None = None) -> tuple[list[str], list[list[str]]]:
    sample = text[:4096]
    if delimiter is None:
        if sample.strip():
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                delimiter = dialect.delimiter
            except Exception:
                delimiter = "\t" if sample.splitlines() and sample.splitlines()[0].count("\t") >= sample.splitlines()[0].count(",") else ","
        else:
            delimiter = ","
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    if not rows:
        return [], []
    return rows[0], rows[1:]


def _select_csv(header: list[str], rows: list[list[str]], concept: str) -> list[Any]:
    if concept == "row":
        return rows
    if concept == "column":
        return header
    if concept == "cell":
        return [cell for row in rows for cell in row]
    return []


# --- text selection ---------------------------------------------------------

_TEXT_WORD_RE = re.compile(r"\w+")


def _select_text(text: str, concept: str) -> list[Any]:
    if concept == "line":
        return text.splitlines()
    if concept == "word":
        return _TEXT_WORD_RE.findall(text)
    if concept == "character":
        return list(text)
    return []


# --- the reducer ------------------------------------------------------------

def _plan_counts(domain: str, concept: str, sources: Mapping[str, str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for target, text in sources.items():
        counts[target] = len(_select_concept_in_source(domain, concept, text))
    return counts


def _select_concept_in_source(domain: str, concept: str, text: str) -> list[Any]:
    if domain == "python_ast":
        tree = ast.parse(text)
        return _select_python(tree, concept)
    if domain == "markdown":
        structure = parse_markdown(text)
        if concept in PY_CONCEPTS:
            nodes: list[Any] = []
            for code, _start in _python_blocks(structure):
                try:
                    tree = ast.parse(code)
                except SyntaxError:
                    continue
                nodes.extend(_select_python(tree, concept))
            return nodes
        return _select_markdown(structure, concept)
    if domain == "json":
        if text.strip().startswith("{") or text.strip().startswith("["):
            data = json.loads(text)
            return _select_json(data, concept)
        # JSONL: newline-delimited objects
        out: list[Any] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            out.extend(_select_json(json.loads(line), concept, _root=True, _path="$"))
        return out
    if domain == "csv":
        header, rows = _parse_csv(text, None)
        return _select_csv(header, rows, concept)
    if domain == "text":
        return _select_text(text, concept)
    return []


def _describe_items(domain: str, concept: str, text: str, items: list[Any]) -> list[str]:
    if domain == "python_ast":
        tree = ast.parse(text)
        return [_describe_node(n, concept, tree) for n in items]
    if domain == "markdown":
        if concept in PY_CONCEPTS:
            return [_list_name(n, concept) for n in items]
        out = []
        for item in items:
            if concept in ("heading", "section"):
                out.append(str(item[1]))
            elif concept == "code_block":
                out.append(f"code_block:{item[0] or 'plain'}@L{item[2]}")
            elif concept in ("bullet", "link"):
                out.append(str(item[0]))
            elif concept in ("word", "line"):
                out.append(str(item))
        return out
    if domain == "json":
        return [str(item[0]) for item in items]
    if domain == "csv":
        if concept == "row":
            return [" | ".join(str(c) for c in row) for row in items]
        return [str(item) for item in items]
    if domain == "text":
        return [str(item) for item in items]
    return [str(item) for item in items]


def _breakdown(domain: str, text: str) -> dict[str, int]:
    concepts: Sequence[str]
    if domain == "python_ast":
        concepts = PY_CONCEPTS
    elif domain == "markdown":
        concepts = MARKDOWN_CONCEPTS
    elif domain == "json":
        concepts = JSON_CONCEPTS
    elif domain == "csv":
        concepts = CSV_CONCEPTS
    elif domain == "text":
        concepts = TEXT_CONCEPTS
    else:
        concepts = ()
    return {c: len(_select_concept_in_source(domain, c, text)) for c in concepts}


def _run_plan(plan: Mapping[str, Any], sources: Mapping[str, str]) -> dict[str, Any]:
    """Execute a synthesized plan over in-memory sources. Pure & deterministic."""
    domain = str(plan["domain"])
    concept = str(plan["concept"])
    operation = str(plan["operation"])
    qualifiers = dict(plan.get("qualifiers") or {})
    targets = list(sources)

    per_target: dict[str, list[Any]] = {}
    per_target_items: dict[str, list[str]] = {}
    for target in targets:
        text = sources[target]
        items = _select_concept_in_source(domain, concept, text)
        if domain == "python_ast" and qualifiers:
            tree = ast.parse(text)
            items = _apply_qualifiers(items, qualifiers, concept)
        per_target[target] = items
        per_target_items[target] = _describe_items(domain, concept, text, items)

    total = sum(len(v) for v in per_target.values())

    if operation == "count":
        answer: Any = total
    elif operation == "exists":
        answer = total > 0
    elif operation == "list":
        if len(targets) == 1:
            only = targets[0]
            if domain == "python_ast":
                answer = [_list_name(n, concept) for n in per_target[only]]
            else:
                answer = list(per_target_items[only])
        else:
            answer = {t: per_target_items[t] for t in targets}
    elif operation == "breakdown":
        if len(targets) == 1:
            answer = _breakdown(domain, sources[targets[0]])
        else:
            answer = {t: _breakdown(domain, sources[t]) for t in targets}
    elif operation == "compare":
        if len(targets) != 2:
            raise QualifierFailure(f"compare requires exactly 2 targets, got {len(targets)}")
        left, right = (len(per_target[t]) for t in targets)
        answer = {
            "left_target": targets[0],
            "right_target": targets[1],
            "left": left,
            "right": right,
            "delta": left - right,
            "concept": concept,
        }
    else:
        raise QualifierFailure(f"unknown operation {operation!r}")

    return {
        "answer": answer,
        "operation": operation,
        "concept": concept,
        "domain": domain,
        "targets": targets,
        "per_target_counts": {t: len(v) for t, v in per_target.items()},
        "total_matches": total,
    }


def _load_sources(targets: Sequence[str], root: Path) -> dict[str, str]:
    sources: dict[str, str] = {}
    for target in targets:
        path = Path(target)
        if not path.is_absolute():
            path = root / path
        sources[target] = path.read_text(encoding="utf-8")
    return sources


# ===========================================================================
# Pillar 4 — causal mechanism verifier (do-calculus interventions)
# ===========================================================================

#: Hand-computed ground truth for the Python fixture. Every concept in
#: PY_CONCEPTS is anchored here; if the selector stops matching these
#: constants, the verifier fails closed before any real file is read.
PY_FIXTURE = (
    '"""Fixture module."""\n'
    '\n'
    'import os\n'
    'from pathlib import Path\n'
    '\n'
    '\n'
    'def alpha(a, b, c):\n'
    '    """alpha docstring."""\n'
    '    if a:\n'
    '        for i in range(c):\n'
    '            pass\n'
    '    return a\n'
    '\n'
    '\n'
    'def _beta(x):\n'
    '    return x\n'
    '\n'
    '\n'
    'async def gamma():\n'
    '    while True:\n'
    '        break\n'
    '\n'
    '\n'
    'class Delta:\n'
    '    """Delta docstring."""\n'
    '\n'
    '    @staticmethod\n'
    '    def epsilon(self):\n'
    '        try:\n'
    '            raise ValueError\n'
    '        except ValueError:\n'
    '            return None\n'
    '\n'
    '\n'
    'zeta = [i for i in range(3)]\n'
    'assert _beta(1) is not None\n'
    'os.getcwd()\n'
)

PY_FIXTURE_EXPECT: dict[str, int] = {
    "function": 4, "async_function": 1, "class": 1, "method": 1,
    "if_statement": 1, "for_loop": 1, "while_loop": 1, "loop": 2,
    "import": 2, "return_statement": 3, "try_block": 1, "raise_statement": 1,
    "call": 4, "assignment": 1, "assertion": 1, "comprehension": 1,
    "decorator": 1, "docstring": 2, "parameter": 5,
}
PY_FIXTURE_LIST_EXPECT: dict[str, list[str]] = {
    "function": ["alpha", "_beta", "gamma", "epsilon"],
    "async_function": ["gamma"],
    "class": ["Delta"],
    "method": ["epsilon"],
    "parameter": ["a", "b", "c", "x", "self"],
}

#: Confounder fixture: every surface token of every Python concept appears in
#: comments or strings, and only assignments genuinely occur.
PY_CONFOUNDER = (
    '# def commented_function(): pass\n'
    '# class CommentedClass: pass\n'
    "s = 'def string_function():'\n"
    "t = 'class StringClass:'\n"
    "u = 'if a for b while c import d return e try f raise g call h'\n"
)
PY_CONFOUNDER_EXPECT: dict[str, int] = {concept: (3 if concept == "assignment" else 0) for concept in PY_CONCEPTS}

PY_NULL = "pass\n"

MD_FIXTURE = (
    '# Title\n'
    '\n'
    'Intro words here today.\n'
    '\n'
    '## Section A\n'
    '\n'
    'Text with a [link one](https://example.com/a) inside.\n'
    '\n'
    '- alpha\n'
    '- beta\n'
    '- gamma\n'
    '\n'
    '```python\n'
    'def md_alpha():\n'
    '    return 1\n'
    '\n'
    'def md_beta():\n'
    '    return 2\n'
    '```\n'
    '\n'
    '## Section B\n'
    '\n'
    'More [link two](https://example.org/b) text here.\n'
)
_MD_WORD_COUNT = len(_MD_WORD_RE.findall(MD_FIXTURE))
_MD_LINE_COUNT = len(MD_FIXTURE.splitlines())
MD_FIXTURE_EXPECT: dict[str, int] = {
    "heading": 3, "section": 3, "code_block": 1, "bullet": 3, "link": 2,
    "word": _MD_WORD_COUNT, "line": _MD_LINE_COUNT,
    # python concepts transferred through the fenced block
    "function": 2, "async_function": 0, "class": 0, "method": 0,
    "if_statement": 0, "for_loop": 0, "while_loop": 0, "loop": 0,
    "import": 0, "return_statement": 2, "try_block": 0, "raise_statement": 0,
    "call": 0, "assignment": 0, "assertion": 0, "comprehension": 0,
    "decorator": 0, "docstring": 0, "parameter": 0,
}
MD_FIXTURE_LIST_EXPECT: dict[str, list[str]] = {
    "function": ["md_alpha", "md_beta"],
    "heading": ["Title", "Section A", "Section B"],
    "bullet": ["alpha", "beta", "gamma"],
    "link": ["[link one](https://example.com/a)", "[link two](https://example.org/b)"],
}
MD_CONFOUNDER = (
    '# Comment full of python words\n'
    '\n'
    '```python\n'
    '# def ghost_function(): pass\n'
    '# class GhostClass: pass\n'
    "note = 'def still_not_real():'\n"
    '```\n'
)
MD_CONFOUNDER_EXPECT: dict[str, int] = {concept: (1 if concept == "assignment" else 0) for concept in PY_CONCEPTS}
MD_NULL = ""

JSON_FIXTURE_TEXT = '{"name": "demo", "count": 3, "tags": ["a", "b"], "nested": {"a": 1, "b": 2}, "flag": true, "nothing": null}'
JSON_FIXTURE_EXPECT: dict[str, int] = {
    "key": 8, "entry": 6, "object": 2, "array": 1,
    "number": 3, "string": 3, "boolean": 1, "null": 1,
}
JSON_NULL = '{}'
#: concepts whose null probe is not applicable (the empty container is itself a match)
JSON_NULL_SKIP = {"object"}

CSV_FIXTURE_TEXT = "host,region,count\nweb1,eu,10\nweb2,us,20\nweb3,apac,30\n"
CSV_FIXTURE_EXPECT: dict[str, int] = {"row": 3, "column": 3, "cell": 9}
CSV_NULL = ""  # no header → 0 rows / columns / cells

TEXT_FIXTURE = "alpha beta gamma\ndelta epsilon\nzeta\n"
TEXT_FIXTURE_EXPECT: dict[str, int] = {"line": 3, "word": 6, "character": len(TEXT_FIXTURE)}
TEXT_NULL = ""


_BREAKDOWN_ANCHORS = {
    "python_ast": ("function", 4),
    "markdown": ("heading", 3),
    "json": ("key", 8),
    "csv": ("row", 3),
    "text": ("line", 3),
}


def _identifier(text: str) -> str:
    cleaned = re.sub(r"\W", "_", text)
    if not cleaned:
        cleaned = "q"
    if cleaned[0].isdigit():
        cleaned = "q" + cleaned
    return cleaned


def _satisfies_qualifiers(name: str, n_params: int, has_decorator: bool, has_docstring: bool,
                          qualifiers: Mapping[str, Any]) -> bool:
    if qualifiers.get("public") and name.startswith("_"):
        return False
    if qualifiers.get("private") and not name.startswith("_"):
        return False
    if "name_prefix" in qualifiers and not name.startswith(str(qualifiers["name_prefix"])):
        return False
    if "name_suffix" in qualifiers and not name.endswith(str(qualifiers["name_suffix"])):
        return False
    if "name_contains" in qualifiers and str(qualifiers["name_contains"]) not in name:
        return False
    if "min_args" in qualifiers and n_params < int(qualifiers["min_args"]):
        return False
    if "max_args" in qualifiers and n_params > int(qualifiers["max_args"]):
        return False
    if qualifiers.get("has_decorator") and not has_decorator:
        return False
    if qualifiers.get("has_docstring") and not has_docstring:
        return False
    return True


def build_qualified_python_fixture(concept: str, qualifiers: Mapping[str, Any]) -> tuple[str, int, list[str]]:
    """Build a synthetic python fixture where exactly one node matches ALL
    qualifiers. Returns (source, expected_count, expected_names).

    The fixture contains a "good" node that satisfies every qualifier and a
    "bad" node that violates exactly one designated qualifier (the first in
    canonical order) while satisfying the rest. Raises QualifierFailure when
    the qualifier set is infeasible; the engine fails closed in that case.
    """
    if concept not in _NAMED_CONCEPTS:
        raise QualifierFailure(f"concept {concept!r} cannot carry qualifiers")
    if concept == "class" and any(k in qualifiers for k in _ARG_QUALIFIERS):
        raise QualifierFailure("argument-count qualifiers are not applicable to classes")
    mn, mx = qualifiers.get("min_args"), qualifiers.get("max_args")
    if mn is not None and mx is not None and int(mn) > int(mx):
        raise QualifierFailure(f"infeasible argument window: min_args={mn} > max_args={mx}")

    # --- good name ---
    name = "fixnode"
    if "name_prefix" in qualifiers:
        name = _identifier(str(qualifiers["name_prefix"])) + "_" + name
    if "name_suffix" in qualifiers:
        name = name + "_" + _identifier(str(qualifiers["name_suffix"]))
    if "name_contains" in qualifiers:
        needle = _identifier(str(qualifiers["name_contains"]))
        if needle not in name:
            name = name + "_" + needle
    if qualifiers.get("private") and not name.startswith("_"):
        name = "_" + name
    if qualifiers.get("public") and name.startswith("_"):
        name = name.lstrip("_") or "fixnode_public"
    good_name = _identifier(name) if not name.startswith("_") else "_" + _identifier(name[1:])

    # --- good param count ---
    if concept == "class":
        good_n = 0
    else:
        lo = int(mn) if mn is not None else None
        hi = int(mx) if mx is not None else None
        if lo is None and hi is None:
            good_n = 2
        elif lo is None:
            good_n = min(2, hi)  # type: ignore[arg-type]
        elif hi is None:
            good_n = max(lo, 1)
        else:
            good_n = max(lo, min(hi, (lo + hi) // 2))

    # --- designated (single) violation for the bad node ---
    order = ["public", "private", "name_prefix", "name_suffix", "name_contains",
             "min_args", "max_args", "has_decorator", "has_docstring"]
    designated = None
    for k in order:
        if k not in qualifiers:
            continue
        if k == "min_args" and int(qualifiers["min_args"]) == 0:
            continue  # nothing is below 0: this axis cannot be violated
        designated = k
        break

    bad_n = good_n
    if designated == "min_args":
        bad_n = int(qualifiers["min_args"]) - 1
    elif designated == "max_args":
        bad_n = int(qualifiers["max_args"]) + 1

    bad_name = good_name
    if designated == "public":
        bad_name = "_" + good_name.lstrip("_")
    elif designated == "private":
        bad_name = good_name.lstrip("_") or "publicfix"
    elif designated == "name_prefix":
        prefix = str(qualifiers["name_prefix"])
        cand = "zz_" + good_name
        counter = 0
        while cand.startswith(prefix):
            counter += 1
            cand = f"z{counter}_" + good_name
            if counter > 200:
                raise QualifierFailure(f"cannot construct a non-prefix fixture for prefix {prefix!r}")
        bad_name = cand
    elif designated == "name_suffix":
        suffix = str(qualifiers["name_suffix"])
        cand = good_name + "_zz"
        counter = 0
        while cand.endswith(suffix):
            counter += 1
            cand = cand + "z" * counter
            if counter > 200:
                raise QualifierFailure(f"cannot construct a non-suffix fixture for suffix {suffix!r}")
        bad_name = cand
    elif designated == "name_contains":
        needle = str(qualifiers["name_contains"])
        cand = "unmatchedqvx"
        counter = 0
        while needle in cand:
            counter += 1
            cand = "zqvx" + "q" * (30 + counter)
            if counter > 200:
                raise QualifierFailure(f"cannot construct a non-containing fixture for needle {needle!r}")
        bad_name = cand

    def _emit(emit_name: str, n_params: int, violated: str | None) -> str:
        want_decorator = bool(qualifiers.get("has_decorator")) and violated != "has_decorator"
        want_docstring = bool(qualifiers.get("has_docstring")) and violated != "has_docstring"
        if concept == "class":
            decorator = "@staticmethod\n" if want_decorator else ""
            body = '    """docstring."""\n    pass\n' if want_docstring else "    pass\n"
            return f"{decorator}class {emit_name}:\n{body}\n"
        params = ", ".join(f"p{i}" for i in range(n_params))
        prefix = "async def" if concept == "async_function" else "def"
        body_lines = []
        if want_docstring:
            body_lines.append('    """docstring."""')
        body_lines.append("    return 1")
        body = "\n".join(body_lines) + "\n"
        decorator = "@staticmethod\n" if want_decorator else ""
        if concept == "method":
            return f"class QHolder:\n" + "".join(
                "    " + line + "\n" for line in f"{decorator}{prefix} {emit_name}({params}):\n{body}".splitlines()
            ) + "\n"
        return f"{decorator}{prefix} {emit_name}({params}):\n{body}\n"

    good_src = _emit(good_name, good_n, None)
    if designated is None:
        source = good_src
    else:
        source = good_src + "\n" + _emit(bad_name, bad_n, designated)

    # sanity-check the fixture before it is used as ground truth
    tree = ast.parse(source)

    def _named_nodes(tree_: ast.AST) -> list[ast.AST]:
        return _select_python(tree_, concept)

    matched = _apply_qualifiers(_named_nodes(tree), qualifiers, concept)
    names = [_node_name(n) for n in matched]
    if names != [good_name]:
        raise QualifierFailure(
            f"qualifier fixture self-check failed for concept={concept} qualifiers={dict(qualifiers)}: "
            f"matched {names}, expected [{good_name}]"
        )
    return source, 1, [good_name]


class CausalMechanismVerifier:
    """Verifies *why* a synthesized program is right, before it is trusted."""

    def __init__(self, plan: Mapping[str, Any]):
        self.plan = dict(plan)
        self.domain = str(self.plan["domain"])
        self.concept = str(self.plan["concept"])
        self.operation = str(self.plan["operation"])
        self.qualifiers = dict(self.plan.get("qualifiers") or {})

    # -- fixtures per domain --------------------------------------------------
    def _positive_fixture(self) -> tuple[dict[str, str], dict[str, Any]]:
        """Returns (sources, expectation). expectation carries count/list keys."""
        domain = self.domain
        concept = self.concept
        if concept == "all":  # breakdown distributes over every domain concept
            fixture = {
                "python_ast": ("__probe__.py", PY_FIXTURE),
                "markdown": ("__probe__.md", MD_FIXTURE),
                "json": ("__probe__.json", JSON_FIXTURE_TEXT),
                "csv": ("__probe__.csv", CSV_FIXTURE_TEXT),
                "text": ("__probe__.txt", TEXT_FIXTURE),
            }[domain]
            anchor_name, anchor_value = _BREAKDOWN_ANCHORS[domain]
            return {fixture[0]: fixture[1]}, {
                "count": None, "names": None,
                "breakdown_anchor": (anchor_name, anchor_value),
            }
        if domain == "python_ast":
            if self.qualifiers:
                source, count, names = build_qualified_python_fixture(concept, self.qualifiers)
                return {"__probe__.py": source}, {"count": count, "names": names}
            return {"__probe__.py": PY_FIXTURE}, {
                "count": PY_FIXTURE_EXPECT[concept],
                "names": PY_FIXTURE_LIST_EXPECT.get(concept),
            }
        if domain == "markdown":
            return {"__probe__.md": MD_FIXTURE}, {
                "count": MD_FIXTURE_EXPECT[concept],
                "names": MD_FIXTURE_LIST_EXPECT.get(concept),
            }
        if domain == "json":
            return {"__probe__.json": JSON_FIXTURE_TEXT}, {"count": JSON_FIXTURE_EXPECT[concept], "names": None}
        if domain == "csv":
            return {"__probe__.csv": CSV_FIXTURE_TEXT}, {"count": CSV_FIXTURE_EXPECT[concept], "names": None}
        if domain == "text":
            return {"__probe__.txt": TEXT_FIXTURE}, {"count": TEXT_FIXTURE_EXPECT[concept], "names": None}
        raise CausalVerificationFailure("positive_intervention_probe", f"no fixture for domain {domain!r}")

    def _null_sources(self) -> tuple[dict[str, str] | None, int | None]:
        if self.concept == "all":
            return self._null_sources_for_all(), 0
        domain = self.domain
        if domain == "python_ast":
            return {"__probe__.py": PY_NULL}, 0
        if domain == "markdown":
            return {"__probe__.md": MD_NULL}, 0
        if domain == "json":
            if self.concept in JSON_NULL_SKIP:
                return None, None
            return {"__probe__.json": JSON_NULL}, 0
        if domain == "csv":
            return {"__probe__.csv": CSV_NULL}, 0
        if domain == "text":
            return {"__probe__.txt": TEXT_NULL}, 0
        return None, None

    def _null_sources_for_all(self) -> dict[str, str] | None:
        return {
            "python_ast": {"__probe__.py": PY_NULL},
            "markdown": {"__probe__.md": MD_NULL},
            "json": {"__probe__.json": JSON_NULL},
            "csv": {"__probe__.csv": CSV_NULL},
            "text": {"__probe__.txt": TEXT_NULL},
        }.get(self.domain)

    def _confounder_sources(self) -> tuple[dict[str, str] | None, int | None]:
        if self.concept == "all":
            return None, None  # breakdown has no single lexical confound axis
        domain = self.domain
        if domain == "python_ast":
            return {"__probe__.py": PY_CONFOUNDER}, PY_CONFOUNDER_EXPECT[self.concept]
        if domain == "markdown":
            if self.concept in PY_CONCEPTS:
                return {"__probe__.md": MD_CONFOUNDER}, MD_CONFOUNDER_EXPECT[self.concept]
            return None, None  # markdown-native concepts have no lexical python confound
        return None, None

    # -- probes ---------------------------------------------------------------
    @staticmethod
    def _count_in(plan: Mapping[str, Any], sources: Mapping[str, str]) -> int:
        out = _run_plan({**plan, "operation": "count"}, sources)
        return int(out["answer"])

    @staticmethod
    def _list_in(plan: Mapping[str, Any], sources: Mapping[str, str]) -> list[str]:
        out = _run_plan({**plan, "operation": "list"}, sources)
        answer = out["answer"]
        return list(answer) if isinstance(answer, list) else []

    def probe_positive_intervention(self) -> dict[str, Any]:
        sources, expectation = self._positive_fixture()
        # breakdown: verify the distribution against a hand-computed anchor
        if self.operation == "breakdown":
            out = _run_plan({**self.plan, "operation": "breakdown"}, sources)
            bd = out["answer"]
            anchor_name, anchor_value = expectation["breakdown_anchor"]
            good = (
                isinstance(bd, dict)
                and bd.get(anchor_name) == anchor_value
                and all(isinstance(v, int) and v >= 0 for v in bd.values())
            )
            detail = f"do(source:=fixture): breakdown anchor {anchor_name}=={anchor_value}; got {bd!r}"
            if not good:
                raise CausalVerificationFailure("positive_intervention_probe", detail)
            return {"probe": "positive_intervention_probe", "applicable": True, "passed": True, "detail": detail}

        expected_count = int(expectation["count"])
        got_count = self._count_in(self.plan, sources)
        passed = got_count == expected_count
        detail = f"do(source:=fixture): expected count {expected_count}, got {got_count}"
        result = {"probe": "positive_intervention_probe", "applicable": True, "passed": passed, "detail": detail}

        if self.operation == "list" and passed:
            got_names = self._list_in(self.plan, sources)
            expected_names = expectation.get("names")
            if expected_names is not None:
                names_ok = got_names == list(expected_names)
                result["detail"] += f"; list expected {expected_names}, got {got_names}"
            else:
                names_ok = len(got_names) == expected_count and all(isinstance(i, str) for i in got_names)
                result["detail"] += f"; list of {len(got_names)} names (count-aligned)"
            result["passed"] = names_ok
        if self.operation == "exists" and passed:
            out = _run_plan({**self.plan, "operation": "exists"}, sources)
            exists_ok = bool(out["answer"]) is (expected_count > 0)
            result["passed"] = exists_ok
            result["detail"] += f"; exists expected {expected_count > 0}, got {out['answer']}"
        if self.operation == "compare" and passed:
            result["detail"] += "; compare delta identity checked in postconditions"
        if not result["passed"]:
            raise CausalVerificationFailure("positive_intervention_probe", result["detail"])
        return result

    def probe_null(self) -> dict[str, Any]:
        if self.operation == "breakdown":
            sources, _expected = self._null_sources()
            if sources is None:
                return {"probe": "null_probe", "applicable": False, "passed": True,
                        "detail": "not applicable for this (domain, concept)"}
            out = _run_plan({**self.plan, "operation": "breakdown"}, sources)
            bd = out["answer"]
            flat = bd if isinstance(bd, dict) and all(isinstance(v, int) for v in bd.values()) else None
            good = flat is not None and all(v == 0 for v in flat.values())
            if self.domain == "json" and flat is not None:
                # an empty JSON object is itself exactly one object; everything else must be 0
                good = flat.get("object") == 1 and all(v == 0 for k, v in flat.items() if k != "object")
            detail = f"do(source:=empty_fixture): breakdown all-zero; got {bd!r}"
            if not good:
                raise CausalVerificationFailure("null_probe", detail)
            return {"probe": "null_probe", "applicable": True, "passed": True, "detail": detail}
        sources, expected = self._null_sources()
        if sources is None:
            return {"probe": "null_probe", "applicable": False, "passed": True,
                    "detail": "not applicable for this (domain, concept)"}
        got = self._count_in(self.plan, sources)
        passed = got == expected
        detail = f"do(source:=empty_fixture): expected count {expected}, got {got}"
        if not passed:
            raise CausalVerificationFailure("null_probe", detail)
        return {"probe": "null_probe", "applicable": True, "passed": True, "detail": detail}

    def probe_confounder(self) -> dict[str, Any]:
        if self.operation == "breakdown":
            return {"probe": "confounder_intervention_probe", "applicable": False, "passed": True,
                    "detail": "breakdown has no single lexical confound axis"}
        sources, expected = self._confounder_sources()
        if sources is None:
            return {"probe": "confounder_intervention_probe", "applicable": False, "passed": True,
                    "detail": "not applicable for this (domain, concept)"}
        got = self._count_in(self.plan, sources)
        passed = got == expected
        detail = f"do(source:=lexical_confounder): expected count {expected}, got {got}"
        if not passed:
            raise CausalVerificationFailure("confounder_intervention_probe", detail)
        return {"probe": "confounder_intervention_probe", "applicable": True, "passed": True, "detail": detail}

    def verify_preconditions(self, targets: Sequence[str], root: Path) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []
        ok = True
        for target in targets:
            path = Path(target)
            if not path.is_absolute():
                path = root / path
            exists = path.is_file()
            checks.append({"check": "target_exists", "target": target, "passed": bool(exists)})
            if not exists:
                ok = False
        if self.operation == "compare" and len(targets) != 2:
            checks.append({"check": "compare_requires_two_targets", "passed": False})
            ok = False
        # qualifier applicability (mirrors _check_qualifier_applicability but as a receipt)
        try:
            _check_qualifier_applicability(self.concept, self.domain, self.qualifiers)
            checks.append({"check": "qualifiers_applicable", "passed": True})
        except QualifierFailure as exc:
            checks.append({"check": "qualifiers_applicable", "passed": False, "detail": str(exc)})
            ok = False
        return {"checks": checks, "all_passed": ok}

    def verify_all(self, targets: Sequence[str], root: Path) -> dict[str, Any]:
        pre = self.verify_preconditions(targets, root)
        probes = []
        if pre["all_passed"]:
            probes.append(self.probe_positive_intervention())
            probes.append(self.probe_null())
            probes.append(self.probe_confounder())
        return {
            "schema": "BRAIN_CAUSAL_VERIFICATION_RECEIPT_V1",
            "preconditions": pre,
            "probes": probes,
            "all_passed": bool(pre["all_passed"]) and all(p["passed"] for p in probes),
        }


def verify_postconditions(operation: str, answer: Any) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    ok = True
    if operation == "count":
        good = isinstance(answer, int) and not isinstance(answer, bool) and answer >= 0 and answer <= 10**8
        checks.append({"check": "count_is_nonnegative_int", "passed": good})
        ok = ok and good
    elif operation == "exists":
        good = isinstance(answer, bool)
        checks.append({"check": "exists_is_bool", "passed": good})
        ok = ok and good
    elif operation == "list":
        if isinstance(answer, list):
            good = all(isinstance(item, str) for item in answer)
            checks.append({"check": "list_items_are_strings", "passed": good})
        elif isinstance(answer, dict):
            good = all(isinstance(v, list) and all(isinstance(i, str) for i in v) for v in answer.values())
            checks.append({"check": "multi_list_shape", "passed": good})
        else:
            good = False
            checks.append({"check": "list_shape", "passed": False})
        ok = ok and good
    elif operation == "breakdown":
        if isinstance(answer, dict):
            if answer and all(isinstance(v, dict) for v in answer.values()):
                good = all(isinstance(x, int) and x >= 0 for v in answer.values() for x in v.values())
            else:
                good = all(isinstance(v, int) and v >= 0 for v in answer.values())
            checks.append({"check": "breakdown_values_nonnegative_ints", "passed": good})
        else:
            good = False
            checks.append({"check": "breakdown_is_dict", "passed": False})
        ok = ok and good
    elif operation == "compare":
        good = (
            isinstance(answer, dict)
            and isinstance(answer.get("left"), int)
            and isinstance(answer.get("right"), int)
            and answer.get("delta") == answer["left"] - answer["right"]
        )
        checks.append({"check": "compare_delta_identity", "passed": good})
        ok = ok and good
    return {"checks": checks, "all_passed": ok}


# ===========================================================================
# The engine: parse → corroborate → synthesize → verify → execute → learn
# ===========================================================================

_DEFAULT_EXPERIENCES = _REPO_ROOT / "canonical/astra_runtime/generalization/GENERALIZATION_EXPERIENCES_V1.json"


def _fail_closed(status: str, goal: str, *, task: SemanticTaskAST | None = None,
                 policy: Mapping[str, Any] | None = None, detail: str | None = None,
                 elapsed_ms: float = 0.0, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "pass": False,
        "status": status,
        "failure_class": status,
        "generalization_used": False,
        "answer": None,
        "goal": goal,
        "elapsed_ms": round(elapsed_ms, 3),
    }
    if task is not None:
        payload["task_ast"] = task.to_dict()
    if policy is not None:
        payload["policy_prediction"] = policy
    if detail:
        payload["detail"] = detail
    if extra:
        payload.update(dict(extra))
    return payload


class GeneralizationEngine:
    """Neuro-symbolic compositional & causal generalization over the
    count/list/breakdown/exists/compare family, across five domains."""

    def __init__(
        self,
        experiences_path: Path | None = None,
        embeddings_path: Path | None = None,
        policy_path: Path | None = None,
    ):
        self.experiences_path = Path(experiences_path) if experiences_path else _DEFAULT_EXPERIENCES
        self.embeddings_path = Path(embeddings_path) if embeddings_path else (
            self.experiences_path.parent / "TASK_EMBEDDINGS_V1.json"
        )
        self.policy = OnlineParametricPolicyModel(state_path=policy_path)
        self.experiences = self._load_experiences()
        self.embeddings = self._load_embeddings()
        self.vocab = self._build_vocabulary()
        self.idf = self._compute_idf()

    # ------------------------------------------------------------------
    # Experience store (TF-IDF retrieval; the *mechanism* lives elsewhere)
    # ------------------------------------------------------------------
    def _load_experiences(self) -> dict[str, Any]:
        if self.experiences_path.is_file():
            try:
                return json.loads(self.experiences_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "schema": SCHEMA,
            "experiences": [],
            "metadata": {"created_at": _utcnow(), "version": "2.0"},
        }

    def _load_embeddings(self) -> dict[str, Any]:
        if self.embeddings_path.is_file():
            try:
                return json.loads(self.embeddings_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"embeddings": {}}

    def _save_experiences(self) -> None:
        try:
            self.experiences_path.parent.mkdir(parents=True, exist_ok=True)
            self.experiences_path.write_text(
                json.dumps(self.experiences, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass

    def _save_embeddings(self) -> None:
        try:
            self.embeddings_path.parent.mkdir(parents=True, exist_ok=True)
            self.embeddings_path.write_text(
                json.dumps(self.embeddings, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception:
            pass

    def _tokenize(self, text: str) -> list[str]:
        words = re.findall(r"\b\w+\b", text.lower())
        tokens = list(words)
        tokens.extend(f"{words[i]}_{words[i + 1]}" for i in range(len(words) - 1))
        return tokens

    def _build_vocabulary(self) -> dict[str, int]:
        vocab: dict[str, int] = {}
        for exp in self.experiences.get("experiences", []):
            for token in self._tokenize(exp.get("task_description", "")):
                if token not in vocab:
                    vocab[token] = len(vocab)
        return vocab

    def _compute_idf(self) -> dict[str, float]:
        docs = [exp.get("task_description", "") for exp in self.experiences.get("experiences", [])]
        doc_count = len(docs)
        if doc_count == 0:
            return {}
        df: Counter[str] = Counter()
        for doc in docs:
            for token in set(self._tokenize(doc)):
                df[token] += 1
        return {token: math.log((doc_count + 1) / (freq + 1)) + 1 for token, freq in df.items()}

    def _embed_task(self, task_description: str) -> dict[str, float]:
        tokens = self._tokenize(task_description)
        tf = Counter(tokens)
        if not tf:
            return {}
        max_tf = max(tf.values())
        return {token: (count / max_tf) * self.idf.get(token, 1.0) for token, count in tf.items()}

    @staticmethod
    def _cosine_similarity(emb1: Mapping[str, float], emb2: Mapping[str, float]) -> float:
        common = set(emb1) & set(emb2)
        if not common:
            return 0.0
        dot = sum(emb1[t] * emb2[t] for t in common)
        mag1 = math.sqrt(sum(v * v for v in emb1.values()))
        mag2 = math.sqrt(sum(v * v for v in emb2.values()))
        return 0.0 if mag1 == 0.0 or mag2 == 0.0 else dot / (mag1 * mag2)

    def store_experience(
        self,
        task_description: str,
        trajectory: list[dict[str, Any]],
        outcome: str,
        strategy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Persist a verified experience. Only verified successes should be
        stored as outcome='success' — this is the training signal for Pillar 1."""
        embedding = self._embed_task(task_description)
        exp_id = hashlib.sha256(task_description.encode("utf-8")).hexdigest()[:16]
        experience = {
            "id": exp_id,
            "task_description": task_description,
            "trajectory": trajectory,
            "outcome": outcome,
            "strategy": strategy,
            "embedding": embedding,
            "stored_at": _utcnow(),
        }
        self.experiences.setdefault("experiences", []).append(experience)
        self.embeddings.setdefault("embeddings", {})[exp_id] = embedding
        self.vocab = self._build_vocabulary()
        self.idf = self._compute_idf()
        self._save_experiences()
        self._save_embeddings()
        return experience

    def retrieve_similar(
        self,
        task_description: str,
        top_k: int = 5,
        min_similarity: float = 0.3,
    ) -> list[dict[str, Any]]:
        novel = self._embed_task(task_description)
        scored: list[tuple[float, dict[str, Any]]] = []
        for exp in self.experiences.get("experiences", []):
            sim = self._cosine_similarity(novel, self.embeddings.get("embeddings", {}).get(exp.get("id"), exp.get("embedding", {})))
            if sim >= min_similarity:
                scored.append((sim, exp))
        scored.sort(key=lambda kv: kv[0], reverse=True)
        return [{**exp, "similarity_score": round(score, 6)} for score, exp in scored[:top_k]]

    # ------------------------------------------------------------------
    # The solve pipeline
    # ------------------------------------------------------------------
    def solve_task(
        self,
        goal: str,
        *,
        work_cwd: Path | str | None = None,
        learn_update: bool = True,
        top_k: int = 3,
        persist_policy: bool = True,
        store_experience: bool = True,
    ) -> dict[str, Any]:
        t0 = time.perf_counter_ns()
        root = Path(work_cwd) if work_cwd else Path.cwd()
        root = root.resolve()

        task = parse_task(goal)
        policy_prediction = self.policy.predict(goal)

        def elapsed() -> float:
            return (time.perf_counter_ns() - t0) / 1e6

        # --- honesty gate 1: negation ---
        if _NEGATION_RE.search(goal):
            return _fail_closed(
                "FAIL_CLOSED__UNGROUNDED_NEGATION", goal, task=task, policy=policy_prediction,
                detail="negated requests are not answered by this engine; it verifies presence, not absence",
                elapsed_ms=elapsed(),
            )

        # --- honesty gate 2: operation ---
        if task.operation == "unknown":
            return _fail_closed(
                "FAIL_CLOSED__OPERATION_UNRECOGNIZED", goal, task=task, policy=policy_prediction,
                detail="no operation verb recognized (count|list|breakdown|exists|compare)",
                elapsed_ms=elapsed(),
            )

        # --- honesty gate 3: concept ---
        if task.concept == "unknown":
            return _fail_closed(
                "FAIL_CLOSED__CONCEPT_UNRECOGNIZED", goal, task=task, policy=policy_prediction,
                detail="no known concept recognized in the request",
                elapsed_ms=elapsed(),
            )

        # --- honesty gate 4: targets ---
        if not task.targets:
            return _fail_closed(
                "FAIL_CLOSED__NO_TARGET_FILE", goal, task=task, policy=policy_prediction,
                detail="no target file path found in the goal",
                elapsed_ms=elapsed(),
            )

        # --- honesty gate 4b: caller-workspace confinement ---
        # A read-only answer engine must not become a parent-directory scanner.
        # Resolve every target before existence checks or reads; symlink escapes
        # are refused just like absolute paths outside the caller root.
        for target in task.targets:
            raw = Path(target)
            candidate = raw if raw.is_absolute() else root / raw
            try:
                resolved = candidate.resolve()
            except (OSError, RuntimeError) as exc:
                return _fail_closed(
                    "FAIL_CLOSED__TARGET_RESOLUTION_FAILED", goal, task=task, policy=policy_prediction,
                    detail=f"{type(exc).__name__}: {exc}", elapsed_ms=elapsed(),
                    extra={"target": target},
                )
            if not resolved.is_relative_to(root):
                return _fail_closed(
                    "FAIL_CLOSED__TARGET_OUTSIDE_ROOT", goal, task=task, policy=policy_prediction,
                    detail=str(resolved), elapsed_ms=elapsed(),
                    extra={"target": target, "workspace_root": str(root)},
                )

        # --- honesty gate 5: domain ---
        if task.domain in ("unknown", "mixed"):
            return _fail_closed(
                "FAIL_CLOSED__DOMAIN_UNRECOGNIZED", goal, task=task, policy=policy_prediction,
                detail=f"no single domain adapter for targets {task.targets}",
                elapsed_ms=elapsed(),
            )

        # --- honesty gate 6: a qualifier the parser cannot ground ---
        if task.unparsed_qualifiers:
            return _fail_closed(
                "FAIL_CLOSED__QUALIFIER_UNPARSED", goal, task=task, policy=policy_prediction,
                detail=f"qualifier marker(s) present but not groundable: {', '.join(task.unparsed_qualifiers)}",
                elapsed_ms=elapsed(),
            )

        # --- honesty gate 7: qualifiers are meaningless for a whole-file breakdown ---
        if task.operation == "breakdown" and task.qualifiers:
            return _fail_closed(
                "FAIL_CLOSED__INAPPLICABLE_QUALIFIER", goal, task=task, policy=policy_prediction,
                detail="qualifiers do not compose with a whole-file breakdown; ask for a qualified count instead",
                elapsed_ms=elapsed(),
            )

        # --- plan ---
        try:
            _check_qualifier_applicability(task.concept, task.domain, task.qualifiers)
        except QualifierFailure as exc:
            return _fail_closed(
                "FAIL_CLOSED__INAPPLICABLE_QUALIFIER", goal, task=task, policy=policy_prediction,
                detail=str(exc), elapsed_ms=elapsed(),
            )
        plan = synthesize_plan(task)
        plan["plan_signature"] = hashlib.sha256(_canonical_json(plan).encode("utf-8")).hexdigest()[:16]

        # --- verify (preconditions + interventional probes) ---
        verifier = CausalMechanismVerifier(plan)
        try:
            verification = verifier.verify_all(task.targets, root)
        except CausalVerificationFailure as exc:
            return _fail_closed(
                "FAIL_CLOSED__CAUSAL_VERIFICATION_FAILED", goal, task=task, policy=policy_prediction,
                detail=str(exc), elapsed_ms=elapsed(),
                extra={"plan": plan, "failed_probe": exc.probe},
            )
        except QualifierFailure as exc:
            return _fail_closed(
                "FAIL_CLOSED__QUALIFIER_COMBINATION_INFEASIBLE", goal, task=task, policy=policy_prediction,
                detail=str(exc), elapsed_ms=elapsed(), extra={"plan": plan},
            )
        if not verification["all_passed"]:
            failed = [c for c in verification["preconditions"]["checks"] if not c.get("passed")]
            status = "FAIL_CLOSED__TARGET_NOT_FOUND" if any(c.get("check") == "target_exists" for c in failed) else "FAIL_CLOSED__PRECONDITION_FAILED"
            return _fail_closed(
                status, goal, task=task, policy=policy_prediction,
                detail="precondition(s) failed", elapsed_ms=elapsed(),
                extra={"plan": plan, "causal_verification": verification},
            )

        # --- execute ---
        try:
            sources = _load_sources(task.targets, root)
            payload = _run_plan(plan, sources)
        except (SyntaxError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            return _fail_closed(
                "FAIL_CLOSED__DOMAIN_PARSE_FAILED", goal, task=task, policy=policy_prediction,
                detail=f"{type(exc).__name__}: {exc}", elapsed_ms=elapsed(), extra={"plan": plan},
            )
        except OSError as exc:
            return _fail_closed(
                "FAIL_CLOSED__TARGET_NOT_FOUND", goal, task=task, policy=policy_prediction,
                detail=str(exc), elapsed_ms=elapsed(), extra={"plan": plan},
            )

        # --- postconditions ---
        post = verify_postconditions(task.operation, payload["answer"])
        if not post["all_passed"]:
            return _fail_closed(
                "FAIL_CLOSED__POSTCONDITION_FAILED", goal, task=task, policy=policy_prediction,
                detail="postcondition(s) failed", elapsed_ms=elapsed(),
                extra={"plan": plan, "causal_verification": verification, "postconditions": post},
            )

        # --- online learning from the verified experience ---
        policy_receipt = None
        if learn_update:
            try:
                policy_receipt = self.policy.update_from_experience(
                    goal, task.operation, task.concept, task.domain,
                    persist=persist_policy,
                )
            except Exception:
                policy_receipt = {"schema": "BRAIN_POLICY_UPDATE_RECEIPT_V1", "error": "update failed"}
        if learn_update and store_experience:
            try:
                self.store_experience(
                    task_description=goal,
                    trajectory=[{
                        "action": "neurosymbolic_solve",
                        "plan_signature": plan["plan_signature"],
                        "pipeline": plan["pipeline"],
                    }],
                    outcome="success",
                    strategy={
                        "type": "verified_compositional_program",
                        "task_type": "information_retrieval",
                        "operation": task.operation,
                        "concept": task.concept,
                        "domain": task.domain,
                        "plan_signature": plan["plan_signature"],
                    },
                )
            except Exception:
                pass

        similar = self.retrieve_similar(goal, top_k=top_k)
        similar_receipts = [
            {"id": exp.get("id"), "similarity": exp.get("similarity_score")}
            for exp in similar
        ]

        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__NEUROSYMBOLIC_GENERALIZATION",
            "failure_class": None,
            "answer": payload["answer"],
            "answer_kind": task.operation,
            "generalization_used": True,
            "goal": goal,
            "task_ast": task.to_dict(),
            "plan": plan,
            "per_target_counts": payload["per_target_counts"],
            "total_matches": payload["total_matches"],
            "causal_verification": verification,
            "postconditions": post,
            "policy_receipt": policy_receipt,
            "policy_prediction": policy_prediction,
            "similar_experiences": similar_receipts,
            "similar_experiences_count": len(similar_receipts),
            "top_similarities": [s["similarity"] for s in similar_receipts],
            "elapsed_ms": round(elapsed(), 3),
        }


class SemanticGeneralizationEngine(GeneralizationEngine):
    """Backwards-compatible name for the engine.

    The old TF-IDF lookup design was removed; this class keeps the import
    surface stable for callers that used ``SemanticGeneralizationEngine``.
    """

    def adapt_strategy(
        self,
        similar_experiences: list[dict[str, Any]],
        novel_task: str,
    ) -> dict[str, Any] | None:
        successful = [e for e in similar_experiences if e.get("outcome") == "success" and e.get("strategy")]
        if not successful:
            return None
        base = successful[0]["strategy"]
        return {
            "base_strategy": base,
            "common_task_types": list({e.get("strategy", {}).get("task_type") for e in successful if e.get("strategy")}),
            "adaptation_notes": f"Adapted from {len(similar_experiences)} similar experiences; execution is by verified synthesized program, not recall.",
            "source_experiences": [e.get("id") for e in similar_experiences[:3]],
            "novel_task": novel_task,
            "adapted_at": _utcnow(),
        }

    def generalize_and_solve(self, task_description: str, top_k: int = 5) -> dict[str, Any]:
        result = self.solve_task(task_description, top_k=top_k)
        similar = self.retrieve_similar(task_description, top_k=top_k)
        adapted = self.adapt_strategy(similar, task_description)
        return {
            **result,
            "novel_task": task_description,
            "similar_experiences_found": len(similar),
            "top_similarities": [e.get("similarity_score") for e in similar[:3]],
            "adapted_strategy": adapted,
            "timestamp": _utcnow(),
        }
