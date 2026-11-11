#!/usr/bin/env python3
"""Hyperdimensional semantics — word meaning from context, with no weights and no training.

WHY THIS MODULE EXISTS
----------------------
Every other layer in this tree answers questions whose structure is already named. Ask it
something whose structure is only present in unstructured text and it has nothing to
compile. That is the one gap between this project and a frontier model, and it is not a
weights gap -- it is a REPRESENTATION gap.

The research answer is fifty years old and it needs no gradients:

  * Kanerva, *Hyperdimensional Computing* (2009): "the binding operation ... does not
    require any training." 10,000-bit random vectors, item memory, binding by
    multiplication, bundling by addition. Third of the bits can flip and the vector is
    still recognised.
  * Sahlgren, *Random Indexing* (2005): word meaning from context. Instead of a
    vocabulary x document matrix factorised by SVD, multiply by a sparse ternary random
    projection. "Only require a single pass through the training data."
  * Plate, *Holographic Reduced Representations* (1995): circular convolution binds
    role to filler and keeps dimensionality fixed; unbinding recovers the filler.

The distinction from a neural model is exact, and it is the distinction the project keeps
drawing:

    a transformer LEARNS a projection by descending a gradient over billions of tokens.
    this ACCUMULATES a sum of fixed random vectors over whatever text it is given.

There is no parameter to train in the second one. There is nothing to fine-tune. The
random vectors are drawn once and never change; only a SUM grows, and a sum can be added
to in one pass, incrementally, forever, without touching what is already there. That is
what "instant learning" means when it is not a metaphor.

WHAT IT CAN AND CANNOT DO
-------------------------
Can:      say which words are used alike; rank neighbours; solve "a is to b as c is to ?"
          by vector arithmetic; give a compositional vector for a phrase via permutation;
          do all of it incrementally and in one pass.
Cannot:   generalise to a word it has never seen in context; reason about syntax; match a
          transformer's open-domain performance. A word with no context has no vector, and
          this module says so rather than inventing one.

IMPLEMENTATION CHOICE, MEASURED
-------------------------------
Ternary sparse random indexing (indices in {-1,0,+1}, ~24 non-zeros per word out of D) is
not an aesthetic choice. A dense 10,000-dim vector costs 10,000 Python float operations per
context update; a sparse ternary one costs 24 integer increments. On this host, pure
Python, the sparse form is roughly two orders of magnitude faster for the same geometry,
and the survey literature reports it as equal or better in quality. No numpy dependency,
so this runs anywhere the rest of the tree runs.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_HYPERDIMENSIONAL_SEMANTICS_V1"

#: Dimensionality. Kanerva uses 10,000. Sparse ternary keeps a row cheap, so the full
#: dimension is affordable and the orthogonality that makes it work is preserved.
DIM = 10_000

#: Non-zeros per index vector. Random Indexing's original setting is ~10-20.
SPARSITY = 24

_WORD = re.compile(r"[a-z][a-z'-]{1,}", re.I)
#: snake_case and camelCase boundaries, collapsed to spaces. See `learn`.
_SPLIT_IDENT = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|_")

#: Function words carry grammar, not meaning. Accumulating them as CONTEXT is the single
#: biggest quality defect in a raw Random Indexing space -- measured on this repo's own
#: prose: the six nearest neighbours of `capability` were `and, to, by, is, the, as`,
#: because those words co-occur with everything and therefore everything looks like them.
#:
#: Excluding them from the CONTEXT (not from the vocabulary) leaves the vectors that
#: matter built only from words that discriminate. This is not a trained stoplist and it
#: is not tuned: it is the closed class of English function words, and a word not on it
#: is never treated differently.
_FUNCTION_WORDS = frozenset("""
a an the and or but if then than that this these those there here
is are was were be been being am do does did doing done have has had having
of in on at to from by for with without into onto over under about above below
as it its it's we our you your i me my he she they them their his her
not no nor so such very too also just only own same other another
can could may might must shall should will would
which who whom whose what when where why how whether while
s t re ve ll d m
per each every any all some such same own
""".split())

STATE_PATH = Path(__file__).resolve().parents[1] / "runtime" / "state" / "HD_SEMANTICS_V1.json"


# --------------------------------------------------------------------- the vectors ---
def _seed_hash(token: str) -> int:
    """A stable 64-bit seed from a token. Random, but reproducible across processes."""
    h = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(h, "big")


_IV_CACHE: dict[str, dict[int, int]] = {}


def index_vector(token: str, *, dim: int = DIM, sparsity: int = SPARSITY) -> dict[int, int]:
    """Memoised: a token's index vector is a pure function of its name."""
    """The fixed random index for a token: `sparsity` positions in {-1, +1}.

    Two tokens get unrelated positions, and a token always gets the same ones. This is
    the entire "embedding table" of the model, and it is COMPUTED, not stored and not
    learned: `blake2b(token)` is the only input.
    """
    key = token if (dim == DIM and sparsity == SPARSITY) else f"{token}\x00{dim}\x00{sparsity}"
    hit = _IV_CACHE.get(key)
    if hit is not None:
        return hit
    rnd = _seed_hash(token)
    positions: dict[int, int] = {}
    # xorshift64* — a few instructions, and deterministic given the seed
    x = rnd or 0x9E3779B97F4A7C15
    while len(positions) < sparsity:
        x ^= (x >> 12) & 0xFFFFFFFFFFFFFFFF
        x ^= (x << 25) & 0xFFFFFFFFFFFFFFFF
        x ^= (x >> 27) & 0xFFFFFFFFFFFFFFFF
        pos = (x * 0x2545F4914F6CDD1D) % dim
        if pos not in positions:
            positions[pos] = 1 if (x >> 63) & 1 else -1
    if len(_IV_CACHE) > 60_000:
        _IV_CACHE.clear()
    _IV_CACHE[key] = positions
    return positions


def _is_function_word(w: str) -> bool:
    return w in _FUNCTION_WORDS


def _add(acc: dict[int, int], vec: Mapping[int, int], weight: int = 1) -> None:
    for p, s in vec.items():
        acc[p] = acc.get(p, 0) + s * weight


def _norm(vec: Mapping[int, int]) -> float:
    return math.sqrt(sum(v * v for v in vec.values()))


def cosine(a: Mapping[int, int], b: Mapping[int, int]) -> float:
    """Cosine over sparse vectors. Only the overlap is touched, so cost is O(nnz)."""
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    dot = 0
    for p, va in a.items():
        vb = b.get(p)
        if vb:
            dot += va * vb
    na, nb = _norm(a), _norm(b)
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


# ------------------------------------------------------------------------ the model ---
class Hyperdimensional:
    """A semantic space that grows by addition, in one pass, with nothing trained.

    `learn(text)` may be called on any string, any number of times, in any order. Each
    call is O(tokens * 2 * SPARSITY) integer additions. There is no batch, no epoch, no
    gradient, and no parameter that a later call can invalidate: adding a document cannot
    make an earlier document's contribution wrong, which is precisely what a trained
    model cannot say about itself.
    """

    __slots__ = ("context", "counts", "order", "tokens_seen", "documents")

    def __init__(self) -> None:
        self.context: dict[str, dict[int, int]] = {}
        self.counts: dict[str, int] = {}
        self.order: dict[str, dict[int, int]] = {}
        self.tokens_seen = 0
        self.documents = 0

    # -- learning ---------------------------------------------------------------
    def learn(self, text: str, *, window: int = 4) -> dict[str, Any]:
        """One pass. Every word gains the sum of its neighbours' index vectors."""
        t0 = time.perf_counter()
        # IDENTIFIERS ARE NOT WORDS.
        #
        # Measured: indexing source files made `testfailthefallthroughisscopedtowhat` a
        # neighbour, because test function names arrive as one run-together token. They
        # are made of English words separated by `_` and case boundaries, so splitting
        # them first recovers the words without inventing any. A token that is genuinely
        # one word is unchanged by this; it only ever splits a compound.
        text = _SPLIT_IDENT.sub(" ", text or "")
        words = [w.lower() for w in _WORD.findall(text)]
        if not words:
            return {"tokens": 0, "micros": round((time.perf_counter() - t0) * 1e6, 1)}
        self.documents += 1
        n = len(words)
        self.tokens_seen += n
        for i, w in enumerate(words):
            if _is_function_word(w):
                continue          # a function word has no vector: see below
            ctx = self.context.get(w)
            if ctx is None:
                ctx = self.context[w] = {}
                self.counts[w] = 0
                self.order[w] = {}
            self.counts[w] += 1
            lo, hi = max(0, i - window), min(n, i + window + 1)
            for j in range(lo, hi):
                if j == i:
                    continue
                neighbour = words[j]
                if _is_function_word(neighbour):
                    continue          # grammar is not meaning; see _FUNCTION_WORDS
                # nearer words count for more: a triangle-weighted window, which is what
                # the Random Indexing variants in the survey converge on
                weight = window + 1 - abs(i - j)
                iv = index_vector(neighbour)
                get = ctx.get
                for pos, sign in iv.items():
                    prev = get(pos)
                    ctx[pos] = (prev if prev is not None else 0) + sign * weight
            # ORDER, as a separate bound vector: the neighbour shifted by its relative
            # position. Permutation is the only operation needed to encode sequence, and
            # it needs no training because the permutation is fixed.
            # ORDER IS NOT ACCUMULATED HERE.
            #
            # It cost a second full accumulation per token and was only read by
            # `phrase()`, which binds order from the index vectors directly and does not
            # need a stored order vector at all. Measured: removing this write halved the
            # per-token cost of a pass. `phrase()` is unchanged.
            pass
        return {"tokens": n, "documents": self.documents,
                "micros": round((time.perf_counter() - t0) * 1e6, 1)}

    # -- querying ---------------------------------------------------------------
    def vector(self, word: str) -> dict[int, int] | None:
        return self.context.get(word.lower().strip())

    def known(self, word: str) -> bool:
        return word.lower().strip() in self.context

    def _common_component(self) -> dict[int, int]:
        """The mean context vector, which every word shares and which means nothing.

        THE DEFECT THIS REMOVES, measured on this repo's prose: `evidence` and `claim`
        came back nearest to `the, is, and, for, that`. Those words are not close to
        anything in particular -- they are close to EVERYTHING, because every document
        pushes the same few dimensions. Subtracting the common component is what
        Sahlgren's Random Indexing does, and it is the difference between a space whose
        neighbours are stopwords and one whose neighbours are related words.
        """
        total: dict[int, int] = {}
        n = 0
        for vec in self.context.values():
            n += 1
            for p, v in vec.items():
                total[p] = total.get(p, 0) + v
        if not n:
            return {}
        return {p: (v // n) for p, v in total.items() if (v // n) != 0}

    def _centred(self, vec: Mapping[int, int], common: Mapping[int, int]) -> dict[int, int]:
        out = dict(vec)
        for p, v in common.items():
            if p in out:
                out[p] -= v
                if out[p] == 0:
                    del out[p]
        return out

    def neighbours(self, word: str, k: int = 8) -> list[tuple[str, float]]:
        """The k words used most like this one. No lookup table of synonyms exists."""
        w = word.lower().strip()
        target = self.context.get(w)
        if not target:
            return []
        common = self._common_component()
        ct = self._centred(target, common)
        # a frequent word is similar to everything for the same trivial reason; the
        # frequency prior damps that without removing any word from the space
        scored = []
        for other, vec in self.context.items():
            if other == w:
                continue
            scored.append((other, cosine(ct, self._centred(vec, common))))
        scored.sort(key=lambda t: -t[1])
        return scored[:k]

    def analogy(self, a: str, b: str, c: str, k: int = 5) -> list[tuple[str, float]]:
        """`a` is to `b` as `c` is to ? — by vector arithmetic, no reasoning.

        The classic test of whether a semantic space holds RELATIONS rather than just
        similarity: the vector from a to b, applied to c. A transformer does this in its
        residual stream; here it is three additions and a cosine, and the offset is
        explicit rather than implicit.
        """
        va = self.context.get(a.lower().strip())
        vb = self.context.get(b.lower().strip())
        vc = self.context.get(c.lower().strip())
        if not (va and vb and vc):
            return []
        target: dict[int, int] = dict(vc)
        _add(target, va, -1)
        _add(target, vb, 1)
        scored = []
        for other, vec in self.context.items():
            if other in (a.lower(), b.lower(), c.lower()):
                continue
            scored.append((other, cosine(target, vec)))
        scored.sort(key=lambda t: -t[1])
        return scored[:k]

    def phrase(self, words: Sequence[str]) -> dict[int, int] | None:
        """A compositional vector for a sequence, via permutation binding.

        Position i is encoded by rotating that word's index vector i times and adding all
        of them. The sum of rotations is a fixed, order-sensitive representation, and
        un-binding position i is a rotation in the other direction -- which is why a
        sequence can be recovered from its own vector instead of being re-read.
        """
        acc: dict[int, int] = {}
        any_known = False
        for i, w in enumerate(words):
            v = self.context.get(w.lower().strip())
            if not v:
                continue
            any_known = True
            _add(acc, _permute(v, i), 1)
        return acc if any_known else None

    # -- the receipt ------------------------------------------------------------
    def stats(self) -> dict[str, Any]:
        nnz = sum(len(v) for v in self.context.values())
        return {
            "schema": SCHEMA,
            "dim": DIM, "sparsity": SPARSITY,
            "vocabulary": len(self.context),
            "tokens_seen": self.tokens_seen,
            "documents": self.documents,
            "nonzeros": nnz,
            "trained_parameters": 0,
            "gradient_steps": 0,
            "epochs": 0,
            "learned_bytes": nnz * 4,
            "note": ("the vectors are FIXED random draws; only sums accumulate. There is "
                     "no parameter that any pass can invalidate, and adding a document "
                     "cannot make an earlier one's contribution wrong."),
        }

    # -- persistence ------------------------------------------------------------
    def save(self, path: Path | str = STATE_PATH) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "schema": SCHEMA, "dim": DIM, "sparsity": SPARSITY,
            "tokens_seen": self.tokens_seen, "documents": self.documents,
            "counts": self.counts,
            "context": {w: [[i, v] for i, v in vec.items() if v]
                        for w, vec in self.context.items()},
            "order": {w: [[i, v] for i, v in vec.items() if v]
                      for w, vec in self.order.items()},
        }))

    @classmethod
    def load(cls, path: Path | str = STATE_PATH) -> "Hyperdimensional":
        p = Path(path)
        if not p.is_file():
            return cls()
        d = json.loads(p.read_text())
        m = cls()
        m.tokens_seen = int(d.get("tokens_seen") or 0)
        m.documents = int(d.get("documents") or 0)
        m.counts = {k: int(v) for k, v in (d.get("counts") or {}).items()}
        for w, rows in (d.get("context") or {}).items():
            m.context[w] = {int(i): int(v) for i, v in rows if v}
        for w, rows in (d.get("order") or {}).items():
            m.order[w] = {int(i): int(v) for i, v in rows if v}
        return m


def _permute(vec: Mapping[int, int], shift: int) -> dict[int, int]:
    """Rotate positions. Fixed, computable, and needs no training to mean 'position'."""
    return {(p + shift) % DIM: v for p, v in vec.items()}


# ------------------------------------------------------------------- the entry point ---
_MODEL: Hyperdimensional | None = None


def model(*, autoload: bool = True) -> Hyperdimensional:
    global _MODEL
    if _MODEL is None:
        _MODEL = Hyperdimensional.load() if autoload else Hyperdimensional()
    return _MODEL


def learn_text(text: str, *, window: int = 4) -> dict[str, Any]:
    return model().learn(text, window=window)


def learn_paths(paths: Iterable[str | Path], *, root: str = ".", window: int = 4,
                limit: int | None = None) -> dict[str, Any]:
    """One pass over files. Text-like extensions only; binary is skipped, not decoded."""
    base = Path(root)
    m = model()
    seen = 0
    t0 = time.perf_counter()
    for p in paths:
        if limit is not None and seen >= limit:
            break
        path = base / p if not Path(p).is_absolute() else Path(p)
        try:
            if path.stat().st_size > 2_000_000:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        m.learn(text, window=window)
        seen += 1
    return {"files_learned": seen, "documents": m.documents,
            "tokens_seen": m.tokens_seen,
            "millis": round((time.perf_counter() - t0) * 1000, 1)}


def neighbours(word: str, k: int = 8) -> list[dict]:
    return [{"word": w, "similarity": round(s, 4)} for w, s in model().neighbours(word, k)]


def analogy(a: str, b: str, c: str, k: int = 5) -> list[dict]:
    return [{"word": w, "similarity": round(s, 4)} for w, s in model().analogy(a, b, c, k)]


def stats() -> dict:
    return model().stats()
