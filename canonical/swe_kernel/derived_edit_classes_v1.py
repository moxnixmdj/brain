"""Edit classes derived from the creature's own successes — no family table, no model.

The falsifier this module exists to answer (stated in FIRST_PRINCIPLES_TEN):

    `operator_family_rewrite_v1` moved the ceiling, but I wrote it. It encodes a family table --
    arithmetic, comparison, boolean -- that a human supplied. The question that decides whether this
    creature can become non-static is narrower:

        Can it derive an edit class from its own successful repairs, and apply it in a context it
        has never edited, without being told what a class is?

Mechanism, entire: 

    1. A successful repair is a pair (before_snippet, after_snippet). Tokenize both. If exactly one
       token differs (ignoring whitespace, comments, and identical position), that difference is a
       *substitution* the creature performed: `-  ->  +`.
    2. Record substitutions. They form a directed graph whose nodes are tokens the creature has
       itself changed. Nothing here knows what a "family" is; the nodes are whatever it observed.
    3. Transitive closure over that graph is the *inferred* edit class. If it has changed `- -> +`
       in one context and `+ -> *` in another, then `- -> *` is an edit it has never performed but
       which its own experience implies.
    4. Proposal: for a failing source, apply every observed AND inferred pair at every real
       occurrence of the left-hand token.

    No family table, no AST node kinds, no model. The only authored content is "a single-token
    substitution is an edit worth generalising", which is the definition of the experiment.

What this is NOT: it does not verify anything. Candidates still run the owed test and the
acceptance gate. It is also not claimed to be better than the hand-written generator -- it is
claimed to be *derived*, which is a different and stronger claim for the purposes of the owner's
question.
"""

from __future__ import annotations

import io
import tokenize
from typing import Iterable, Mapping

# Tokens that carry no meaning for a substitution: formatting, comments, and names. A change of an
# identifier or a literal is a different kind of edit and is deliberately not part of this class.
_IGNORED = {
    tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT,
    tokenize.COMMENT, tokenize.ENCODING, tokenize.ENDMARKER,
}


def _tokens(source: str) -> list[tuple[int, str]] | None:
    """(type, string) for every meaningful token, or None if the source will not tokenize."""
    out: list[tuple[int, str]] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type in _IGNORED:
                continue
            out.append((tok.type, tok.string))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return None
    return out


def derive_substitution(before: str, after: str) -> tuple[str, str] | None:
    """The single-token substitution a repair performed, or None if it was not one.

    Only same-length token streams qualify: an inserted or deleted token is a different edit class
    (a move or a guard), and forcing it into this one would produce pairs that mean nothing.
    """
    if not isinstance(before, str) or not isinstance(after, str):
        return None
    tb, ta = _tokens(before), _tokens(after)
    if tb is None or ta is None or len(tb) != len(ta):
        return None
    diffs = [(a, b) for (t1, a), (t2, b) in zip(tb, ta) if a != b or t1 != t2]
    if len(diffs) != 1:
        return None
    old, new = diffs[0]
    if not old.strip() or not new.strip():
        return None
    return old, new


class DerivedEditClasses:
    """Observed single-token substitutions, plus their transitive closure as inferred edits."""

    def __init__(self) -> None:
        self._observed: set[tuple[str, str]] = set()

    # -- learning ---------------------------------------------------------------------------
    def observe(self, before: str, after: str) -> tuple[str, str] | None:
        pair = derive_substitution(before, after)
        if pair is not None:
            self._observed.add(pair)
        return pair

    def observe_all(self, pairs: Iterable[tuple[str, str]]) -> None:
        for p in pairs:
            if isinstance(p, tuple) and len(p) == 2 and all(isinstance(x, str) for x in p):
                self._observed.add(p)

    # -- inference --------------------------------------------------------------------------
    def observed(self) -> set[tuple[str, str]]:
        return set(self._observed)

    def inferred(self) -> set[tuple[str, str]]:
        """Transitive closure, minus what was directly observed. This is the edit class: edits the
        creature has never performed but which its own experience implies."""
        edges: dict[str, set[str]] = {}
        for a, b in self._observed:
            edges.setdefault(a, set()).add(b)
        closure: set[tuple[str, str]] = set()
        for start in list(edges):
            seen: set[str] = set()
            frontier = [start]
            while frontier:
                node = frontier.pop()
                for nxt in edges.get(node, ()):
                    if nxt == start or nxt in seen:
                        continue
                    seen.add(nxt)
                    frontier.append(nxt)
                    closure.add((start, nxt))
        return closure - self._observed

    def all_pairs(self) -> list[tuple[str, str]]:
        """Every usable edit, each LEFT-HAND TOKEN in turn, ordered by origin then confidence.

        Grouping by left token keeps a proposal limit from being spent on tokens the failing line
        does not contain, and within a token it ranks performed edits above inferred ones, and
        one-hop inferences above longer chains. Nothing here decides correctness; it only decides
        which plausible edit is offered first.

        Correction to an earlier note of mine: I claimed this ordering explained why `- -> *` fired
        while `* -> -` did not. It does not, and I was wrong. `* -> -` was never inferred at all --
        the observed edges were `* -> +`, `+ -> *`, `- -> +`, and from `*` the only reachable node is
        `+` (plus `*` itself, which is excluded as a self-loop). The closure was right; my reading of
        it was not.
        """
        observed = self.observed()
        inferred = self.inferred()
        by_left: dict[str, list[tuple[int, str, str]]] = {}
        for a, b in observed:
            by_left.setdefault(a, []).append((0, b, "observed"))
        for a, b in inferred:
            by_left.setdefault(a, []).append((1 + self._hops(a, b), b, "inferred"))
        out: list[tuple[str, str]] = []
        for a in sorted(by_left):
            for _rank, b, _origin in sorted(by_left[a]):
                out.append((a, b))
        return out

    def _hops(self, start: str, target: str) -> int:
        """Shortest chain length from `start` to `target`, or a large number if unreachable."""
        edges: dict[str, set[str]] = {}
        for a, b in self._observed:
            edges.setdefault(a, set()).add(b)
        frontier, seen, depth = [start], {start}, 0
        while frontier:
            depth += 1
            nxt: list[str] = []
            for node in frontier:
                for cand in edges.get(node, ()):
                    if cand == target:
                        return depth
                    if cand not in seen:
                        seen.add(cand)
                        nxt.append(cand)
            frontier = nxt
        return 99

    # -- proposal ---------------------------------------------------------------------------
    def propose(self, source_text: str, limit: int = 48) -> list[str]:
        """Apply each known pair to every real occurrence of its left-hand token."""
        if not isinstance(source_text, str) or not source_text.strip():
            return []
        spans: list[tuple[int, int, int, str]] = []  # (row, col_start, col_end, text)
        try:
            for tok in tokenize.generate_tokens(io.StringIO(source_text).readline):
                if tok.type in _IGNORED:
                    continue
                spans.append((tok.start[0], tok.start[1], tok.end[1], tok.string))
        except (tokenize.TokenError, IndentationError, SyntaxError):
            return []
        lines = source_text.splitlines(True)
        out: list[str] = []
        by_left: dict[str, list[str]] = {}
        for old, new in self.all_pairs():
            by_left.setdefault(old, []).append(new)
        if not by_left:
            return []
        for row, start, end, text in spans:
            if text not in by_left:
                continue
            line = lines[row - 1]
            if line[start:end] != text:
                continue
            for new in by_left[text]:
                cand = "".join(lines[:row - 1]) + line[:start] + new + line[end:] + "".join(lines[row:])
                if cand == source_text or cand in out:
                    continue
                out.append(cand)
                if len(out) >= limit:
                    return out
        return out

    def summary(self) -> Mapping[str, object]:
        obs, inf = self.observed(), self.inferred()
        return {
            "observed": sorted("->".join(p) for p in obs),
            "inferred": sorted("->".join(p) for p in inf),
            "closed": not inf,
        }
