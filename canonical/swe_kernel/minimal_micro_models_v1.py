#!/usr/bin/env python3
"""Minimal Specialized Micro-Models v1 — Step 4 Pareto Frontier over Proven Job 4b / 5b Residuals.

Three tiny (<2 MB), pure-numpy/stdlib micro-models targeting ONLY the live-measured residuals
where zero-neural Jobs 1+2+3+4a+5a hit their mathematical ceiling:
  1. OverfitRerankerMicroModel (~1 KB weights, <0.1 ms/cand):
     L2-regularized logistic reranker trained via strict k-fold CV on AST-parsimony +
     docstring-operator alignment + behavioral-preservation features to eliminate weak-test
     overfits on HumanEvalFix (Job 3 + Job 4b residual).
  2. SubspaceMemoryEncoder (~1 MB SVD semantic projection, <0.4 ms/query):
     Truncated-SVD latent semantic + character-trigram bridge fused with DominoMemory to
     recover zero-lexical-overlap paraphrases on LoCoMo-10 Cat 1 & Cat 3 (Job 2 + 4b residual).
  3. AstOpcodeMicroLM (~100 KB-2 MB smoothed parent+bigram+trigram AST opcode model):
     Trained on real git commits (e.g., click+jinja) and evaluated on held-out repo commits
     (werkzeug) to measure exact cross-entropy bits/node and Pass@K reachability scaling for
     Job 5b multi-line / multi-file code synthesis.
"""
from __future__ import annotations

import ast
import math
import re
from collections import Counter, defaultdict
from typing import Any, Sequence

import numpy as np

SCHEMA = "BRAIN_MINIMAL_MICRO_MODELS_V1"

# =========================================================================== #
# MICRO-MODEL A: OverfitRerankerMicroModel (~1 KB weights, <0.1 ms/cand)
# =========================================================================== #
_DOC_OP_CUES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (r"\b(below|less than|smaller than|under|negative)\b", ("<",)),
    (r"\b(at most|less than or equal|no more than)\b", ("<=",)),
    (r"\b(greater than|more than|above|larger than|positive|exceed)\b", (">",)),
    (r"\b(at least|greater than or equal|no less than)\b", (">=",)),
    (r"\b(equal|same|match|identical)\b", ("==",)),
    (r"\b(different|not equal|distinct|uneven)\b", ("!=", "set(")),
    (r"\b(abs|absolute|distance|difference)\b", ("abs(",)),
    (r"\b(square|squared)\b", ("** 2", "**2")),
    (r"\b(even|odd|divisible|remainder|modulo)\b", ("%",)),
    (r"\b(lower|lowercase|case-insensitive|insensitive)\b", (".lower(",)),
    (r"\b(upper|uppercase|capital)\b", (".upper(", ".isupper(")),
    (r"\b(swapcase|flip case|toggle case)\b", (".swapcase(",)),
    (r"\b(start|prefix|begins)\b", (".startswith(",)),
    (r"\b(end|suffix)\b", (".endswith(",)),
    (r"\b(reverse|reversed|palindrome|backward)\b", ("[::-1]", "reversed(")),
    (r"\b(sort|sorted|ascending|descending|order)\b", ("sorted(", ".sort(")),
    (r"\b(unique|distinct|duplicate|without duplicates)\b", ("set(",)),
    (r"\b(sum|total|add)\b", ("+", "sum(")),
    (r"\b(product|multiply|times)\b", ("*",)),
    (r"\b(floor|round down)\b", ("floor(", "//")),
    (r"\b(ceil|round up)\b", ("ceil(",)),
    (r"\b(vowel|vowels)\b", ("a", "e", "i", "o", "u")),
)
_OP_KINDS = (
    "cmp_swap", "binop_swap", "boolop_swap", "const_step", "const_flip",
    "method_sibling", "func_sibling", "var_swap", "operand_swap",
    "range_bound", "slice_bound", "wrap_expr", "unwrap_expr", "dual_swap",
    "unary_toggle", "elem_drop", "stmt_delete", "aug_assign_swap",
)
_OP_TO_IDX = {k: i for i, k in enumerate(_OP_KINDS)}


def extract_rerank_features(
    buggy_src: str,
    cand: dict[str, Any],
    docstring: str,
    *,
    n_ex_passers: int,
    buggy_passed_ex: bool,
    behav_diff_rate: float = 0.5,
) -> np.ndarray:
    """Extract 28-dim feature vector capturing parsimony, docstring alignment, and behavioral safety."""
    cand_src = cand["source"]
    op_kind = cand.get("op_kind", "")
    doc_low = (docstring or "").lower()

    # Find exact changed lines between buggy and candidate
    bl = [l.strip() for l in ast.unparse(ast.parse(buggy_src)).splitlines()]
    cl = [l.strip() for l in ast.unparse(ast.parse(cand_src)).splitlines()]
    added_txt = " ".join(c for b, c in zip(bl, cl) if b != c)
    if len(cl) > len(bl):
        added_txt += " " + " ".join(cl[len(bl):])
    removed_txt = " ".join(b for b, c in zip(bl, cl) if b != c)

    # Docstring-to-edit alignment score
    cue_match = 0.0
    cue_anti = 0.0
    for pat, toks in _DOC_OP_CUES:
        if re.search(pat, doc_low):
            if any(t in added_txt and t not in removed_txt for t in toks):
                cue_match += 1.0
            elif any(t in removed_txt and t not in added_txt for t in toks):
                cue_anti += 1.0

    # No-op semantic traps (e.g. .lower() -> .casefold() when example_test already passed!)
    is_noop_like = 1.0 if ("casefold" in added_txt and "lower" in removed_txt) else 0.0
    # Operator severity: replacing `<` with `<=` (boundary-preserving) vs `<` with `!=` (half-space flip!)
    mild_cmp = 1.0 if (op_kind == "cmp_swap" and (("<=" in added_txt and "<" in removed_txt) or (">=" in added_txt and ">" in removed_txt) or ("<" in added_txt and "<=" in removed_txt) or (">" in added_txt and ">=" in removed_txt))) else 0.0
    harsh_cmp = 1.0 if (op_kind == "cmp_swap" and "!=" in added_txt and "==" not in removed_txt) else 0.0
    # Behavioral change score: tiny nonzero behavioral difference is ideal; 0.0 (no-op) or 1.0 (total flip) is suspicious!
    behav_nonzero = 1.0 if behav_diff_rate > 0.0 else 0.0
    behav_moderate = 1.0 if 0.0 < behav_diff_rate <= 0.55 else 0.0

    base = [
        float(cand.get("score", 0.0)) / 5.0,
        float(cand.get("delta", 1)) / 4.0,
        1.0 if cand.get("spec_ok", True) else 0.0,
        cue_match,
        cue_anti,
        is_noop_like,
        mild_cmp,
        harsh_cmp,
        behav_nonzero,
        behav_moderate,
        1.0 / math.log2(max(2, n_ex_passers + 1)),
        1.0 if buggy_passed_ex else 0.0,
    ]
    onehot = [0.0] * len(_OP_KINDS)
    if op_kind in _OP_TO_IDX:
        onehot[_OP_TO_IDX[op_kind]] = 1.0
    return np.asarray(base + onehot, dtype=np.float64)


class OverfitRerankerMicroModel:
    """Tiny (<1 KB) L2-regularized logistic reranker trained by Newton/GD on feature vectors."""

    def __init__(self, dim: int = 30, l2: float = 1.0) -> None:
        self.w = np.zeros(dim, dtype=np.float64)
        self.b = 0.0
        self.l2 = l2

    def fit(self, X: np.ndarray, y: np.ndarray, steps: int = 250, lr: float = 0.15) -> None:
        if len(X) == 0:
            return
        self.w = np.zeros(X.shape[1], dtype=np.float64)
        self.b = 0.0
        n = float(len(X))
        for _ in range(steps):
            logits = np.clip(X @ self.w + self.b, -20.0, 20.0)
            p = 1.0 / (1.0 + np.exp(-logits))
            err = p - y
            gw = (X.T @ err) / n + (self.l2 / n) * self.w
            gb = float(err.mean())
            self.w -= lr * gw
            self.b -= lr * gb

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        logits = np.clip(X @ self.w + self.b, -20.0, 20.0)
        return 1.0 / (1.0 + np.exp(-logits))

    @property
    def size_bytes(self) -> int:
        return int(self.w.nbytes + 8)


# =========================================================================== #
# MICRO-MODEL B: SubspaceMemoryEncoder (~0.5-2 MB SVD + char-4gram semantic bridge)
# =========================================================================== #
_WORD_RE = re.compile(r"[a-z0-9]+")


class SubspaceMemoryEncoder:
    """Zero-LLM latent semantic SVD + character-ngram encoder fused with DominoMemory."""

    def __init__(self, n_components: int = 96) -> None:
        self.n_components = n_components
        self.vocab: dict[str, int] = {}
        self.idf: np.ndarray | None = None
        self.proj: np.ndarray | None = None  # (V, k)
        self.doc_vecs: np.ndarray | None = None  # (N, k) L2-normalized

    @staticmethod
    def _features(text: str) -> list[str]:
        words = [w for w in _WORD_RE.findall(text.lower()) if len(w) >= 2]
        feats = list(words)
        # Character 4-grams bridge morphology & abbreviations (`edu` <-> `education`, `trans` <-> `transgender`)
        for w in words:
            if len(w) >= 4:
                padded = f"<{w}>"
                for i in range(len(padded) - 3):
                    feats.append("#" + padded[i : i + 4])
        return feats

    def fit_conversation(self, texts: Sequence[str], session_ids: Sequence[int] | None = None) -> dict[str, Any]:
        """Fit truncated SVD over TF-IDF + session-window co-occurrence (~20 ms, <1.5 MB)."""
        # Group into overlapping 3-turn windows to capture cross-turn semantic co-occurrence!
        n = len(texts)
        docs_feats = [self._features(t) for t in texts]
        df: Counter[str] = Counter()
        for fs in docs_feats:
            for f in set(fs):
                df[f] += 1
        # Keep features appearing in >=2 turns and <=60% of turns
        kept = [f for f, c in df.items() if 2 <= c <= max(2, int(0.6 * n))]
        # Cap vocab to keep SVD ultra-fast (<25 ms) and compact (<1.5 MB)
        kept.sort(key=lambda f: (-df[f], f))
        kept = kept[:2500]
        self.vocab = {f: i for i, f in enumerate(kept)}
        v = len(kept)
        if v == 0 or n == 0:
            self.proj = np.zeros((0, 0), dtype=np.float32)
            self.doc_vecs = np.zeros((n, 0), dtype=np.float32)
            return {"vocab": 0, "k": 0, "size_bytes": 0}

        self.idf = np.array([math.log((n + 1.0) / (df[f] + 1.0)) + 1.0 for f in kept], dtype=np.float32)
        # Build turn matrix X (n, v) and session-smoothed co-occurrence matrix M (n, v)
        X = np.zeros((n, v), dtype=np.float32)
        for i, fs in enumerate(docs_feats):
            cnt = Counter(fs)
            for f, c in cnt.items():
                j = self.vocab.get(f)
                if j is not None:
                    X[i, j] = (1.0 + math.log(c)) * self.idf[j]
        # Smooth with adjacent turn in same session for SVD basis discovery (learns topic clusters!)
        M = X.copy()
        for i in range(n):
            if i > 0 and (session_ids is None or session_ids[i] == session_ids[i - 1]):
                M[i] += 0.35 * X[i - 1]
            if i + 1 < n and (session_ids is None or session_ids[i] == session_ids[i + 1]):
                M[i] += 0.35 * X[i + 1]
        # Randomized / compact SVD via eigendecomposition of M M^T (n x n where n ~ 400 -> ~8 ms!)
        k = min(self.n_components, n - 1, v - 1)
        if k <= 0:
            self.proj = np.zeros((v, 0), dtype=np.float32)
            self.doc_vecs = np.zeros((n, 0), dtype=np.float32)
            return {"vocab": v, "k": 0, "size_bytes": 0}
        G = M @ M.T  # (n, n)
        eigvals, eigvecs = np.linalg.eigh(G)
        top_idx = np.argsort(eigvals)[::-1][:k]
        svals = np.sqrt(np.maximum(eigvals[top_idx], 1e-8))
        U = eigvecs[:, top_idx]  # (n, k)
        # Right singular vectors V_k = M^T U / svals -> (v, k)
        self.proj = ((M.T @ U) / svals[None, :]).astype(np.float32)
        # Project individual turns (not smoothed) into semantic subspace
        D = X @ self.proj
        norms = np.linalg.norm(D, axis=1, keepdims=True)
        self.doc_vecs = (D / np.maximum(norms, 1e-8)).astype(np.float32)
        return {"vocab": v, "k": k, "size_bytes": int(self.proj.nbytes + self.doc_vecs.nbytes + self.idf.nbytes)}

    def query_scores(self, question: str) -> np.ndarray:
        if self.proj is None or self.doc_vecs is None or self.proj.size == 0:
            return np.zeros(0 if self.doc_vecs is None else len(self.doc_vecs), dtype=np.float32)
        q = np.zeros(len(self.vocab), dtype=np.float32)
        for f, c in Counter(self._features(question)).items():
            j = self.vocab.get(f)
            if j is not None:
                q[j] = (1.0 + math.log(c)) * self.idf[j]
        qv = q @ self.proj
        qn = float(np.linalg.norm(qv))
        if qn < 1e-8:
            return np.zeros(len(self.doc_vecs), dtype=np.float32)
        return self.doc_vecs @ (qv / qn)


# =========================================================================== #
# MICRO-MODEL C: Context-Conditioned AST-Opcode Micro-LM (Job 5b Entropy Scaling)
# =========================================================================== #
class AstOpcodeMicroLM:
    """Interpolated (unigram -> bigram -> trigram+parent) AST opcode LM for measuring Job 5b bits/node."""

    def __init__(self, max_order: int = 3) -> None:
        self.max_order = max_order
        self.uni: Counter[str] = Counter()
        self.bi: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
        self.tri: dict[tuple[str, str, str], Counter[str]] = defaultdict(Counter)
        self.total_toks = 0

    @staticmethod
    def extract_ast_sequence(source: str) -> list[tuple[str, str]]:
        """Pre-order traversal yielding (parent_type, node_type) pairs for executable AST."""
        tree = ast.parse(source)
        seq: list[tuple[str, str]] = []
        def walk(node: ast.AST, parent_t: str) -> None:
            nt = type(node).__name__
            if nt not in ("Load", "Store", "Del"):
                seq.append((parent_t, nt))
            for ch in ast.iter_child_nodes(node):
                walk(ch, nt)
        walk(tree, "ROOT")
        return seq

    def fit_sources(self, sources: Sequence[str]) -> dict[str, Any]:
        for src in sources:
            try:
                seq = self.extract_ast_sequence(src)
            except SyntaxError:
                continue
            prev1, prev2 = "<BOS>", "<BOS>"
            for par, nt in seq:
                self.uni[nt] += 1
                self.total_toks += 1
                if self.max_order >= 2:
                    self.bi[(par, prev1)][nt] += 1
                if self.max_order >= 3:
                    self.tri[(par, prev2, prev1)][nt] += 1
                prev2, prev1 = prev1, nt
        # Estimate serialized parameter footprint (~12 bytes per (ctx, tok, count) entry)
        n_entries = len(self.uni) + sum(len(c) for c in self.bi.values()) + sum(len(c) for c in self.tri.values())
        return {"total_toks": self.total_toks, "vocab": len(self.uni), "entries": n_entries, "size_bytes": n_entries * 16}

    def eval_cross_entropy(self, sources: Sequence[str]) -> dict[str, Any]:
        """Compute exact held-out cross-entropy (bits/node) and perplexity on unseen code."""
        vocab_sz = max(1, len(self.uni) + 1)
        total_bits = 0.0
        n_toks = 0
        for src in sources:
            try:
                seq = self.extract_ast_sequence(src)
            except SyntaxError:
                continue
            prev1, prev2 = "<BOS>", "<BOS>"
            for par, nt in seq:
                p1 = (self.uni.get(nt, 0) + 0.5) / (self.total_toks + 0.5 * vocab_sz)
                p = p1
                if self.max_order >= 2:
                    b_row = self.bi.get((par, prev1))
                    if b_row:
                        btot = sum(b_row.values())
                        lam2 = btot / (btot + 4.0)
                        p2 = (b_row.get(nt, 0) + 0.25) / (btot + 0.25 * vocab_sz)
                        p = lam2 * p2 + (1.0 - lam2) * p1
                if self.max_order >= 3:
                    t_row = self.tri.get((par, prev2, prev1))
                    if t_row:
                        ttot = sum(t_row.values())
                        lam3 = ttot / (ttot + 6.0)
                        p3 = (t_row.get(nt, 0) + 0.2) / (ttot + 0.2 * vocab_sz)
                        p = lam3 * p3 + (1.0 - lam3) * p
                total_bits += -math.log2(max(p, 1e-12))
                n_toks += 1
                prev2, prev1 = prev1, nt
        h = total_bits / max(1, n_toks)
        return {"tokens": n_toks, "bits_per_node": round(h, 4), "perplexity": round(2.0 ** h, 3)}
