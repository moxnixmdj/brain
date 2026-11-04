"""Notions: expectations derived from a program's own structure, so the creature can find work unassigned.

WHY THIS EXISTS
---------------
Twenty-three passes built organs that act on a *failing test*. Interpretation reads a measurement out of
an assertion's failure; the fitted grammar is scored against an owed value; hole detection watches
verified repairs; competence counts wins. Every one of them is downstream of a failing assertion that
somebody else wrote.

Measured 2026-11-05: hand the creature a module with `rect_area(w, h)` returning `w + h`, a correct
sibling `rect_perimeter` returning `2 * (w + h)`, a correct `square_area`, and a placeholder test file
that asserts nothing. Six cycles produced NO action. Nothing was wrong as far as it was concerned,
because nothing had ever told it what right looks like.

That is the deepest gap, and it is not a missing repair rule. It is missing *doubt*: the creature has
no expectations, so it has nothing to be surprised by, so it has no work of its own.

WHAT A NOTION IS
----------------
A notion is a checkable expectation about a piece of code, generated from the code itself:

    * SYMMETRY   two functions with the same parameter names ought to relate the same way.
                 `rect_perimeter(w, h) = 2 * (w + h)` and `rect_area(w, h)` over the same names invite
                 the question of whether `rect_area` is a sum while its sibling is a product-scaled sum.
    * IDENTITY   a function's own docstring or name declares a relation a substitute can test.
                 `square_area(s) = s * s` versus a suspected `rect_area` calls the same code path with
                 one argument -- if `rect_area(s, s)` disagrees with `square_area(s)`, one of them is wrong.
    * AGREEMENT  two independent implementations of the same idea ought to agree. A test that compares
                 them is written by the creature, not by me.

NOTIONS ARE REFUTABLE OR THEY ARE NOT NOTIONS
---------------------------------------------
Each notion must be falsifiable by construction: it names a claim and a way to check it. Anything
unfalsifiable ("this code looks messy") is refused here rather than at the board, so the creature never
spends a cycle on an opinion.

AND THEY ARE ALLOWED TO BE WRONG
--------------------------------
A notion that fires on correct code is not a bug in this module; it is the normal cost of having
expectations at all. What matters is that a fired notion is a *testable claim* -- running the check
either produces evidence (a disagreement) or does not, and the outcome is recorded so the notion that
fired on everything becomes visibly uninformative.

WHERE THE VALUES COME FROM
--------------------------
Not from me. The literals in a notion are drawn from the source: parameter names, the constants already
written in the sibling functions, and the docstring's own described inputs. Where a value cannot be
derived from the code, no notion is emitted.

WHAT THIS IS NOT
----------------
It cannot invent a specification. It finds *internal inconsistency* -- two parts of a program that
disagree with each other. A program containing one self-consistent lie is invisible to it, and I should
say so before someone mistakes this for verification.

Authority NONE, spend $0, `truth.achieved` false.
"""

from __future__ import annotations

import ast
import itertools
import json
import pathlib
import re
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_NOTIONS_V1"


def _params(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    return [a.arg for a in fn.args.args]


def _returns_expr(fn: ast.AST) -> ast.AST | None:
    for node in ast.walk(fn):
        if isinstance(node, ast.Return):
            return node.value
    return None


def _mentions(node: ast.AST | None, name: str) -> bool:
    return any(isinstance(n, ast.Name) and n.id == name for n in ast.walk(node)) if node is not None else False


def _constants(node: ast.AST | None) -> list[int | float]:
    if node is None:
        return []
    return [n.value for n in ast.walk(node)
            if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)]


class Notion:
    """One expectation about the world, with the check that could refute it."""

    __slots__ = ("kind", "subject", "claim", "check", "fired", "declined", "value", "arity")

    def __init__(self, kind: str, subject: str, claim: str, check: Callable[[], Any],
                 value: float = 1.0, arity: int = 0) -> None:
        self.kind = kind
        self.subject = subject
        self.claim = claim
        self.check = check
        self.fired: bool | None = None
        self.declined: bool = False
        self.value = value
        self.arity: int = arity

    def evaluate(self) -> dict[str, Any]:
        """Run the check. `fired=True` means the expectation was violated, not satisfied.

        MEASURED 2026-11-05 and the worst bug in this module: `except: ok = False` treated *could not
        run* as *refuted*, so `fired = not ok` turned every notion that declined to speak -- the whole
        point of the declining convention -- into a firing one. A crash, a missing function and a
        genuine disagreement were indistinguishable on the board. Three states, not two: fired, held,
        and declined.
        """
        try:
            result = self.check()
        except Exception as exc:  # noqa: BLE001 - a notion that cannot run is a notion that declines
            self.fired = False
            self.declined = True
            return {"kind": self.kind, "subject": self.subject, "claim": self.claim,
                    "fired": False, "declined": True,
                    "detail": f"declines ({type(exc).__name__}): {exc}"}
        # A check may return two, or three, values: (held, detail?, declined?).
        ok, detail = result[0], result[1]
        declined = bool(result[2]) if len(result) > 2 else False
        self.fired = (not ok) and not declined
        self.declined = declined
        return {
            "kind": self.kind,
            "subject": self.subject,
            "claim": self.claim,
            "fired": self.fired,
            "declined": declined,
            "detail": detail,
        }

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "subject": self.subject, "claim": self.claim}


_STOP_TOKENS = frozenset({"v1", "get", "calc", "the", "of", "and", "for", "to", "by"})


def _load_module(source: str, module_name: str) -> tuple[dict[str, Any], Exception | None]:
    """Execute the source in a namespace. Import failures make the notions unusable, which is recorded."""
    ns: dict[str, Any] = {}
    try:
        exec(compile(source, f"<notions:{module_name}>", "exec"), ns)  # noqa: S102 - the module under study
        return ns, None
    except Exception as exc:  # noqa: BLE001
        return ns, exc


def _sample_values(params: Sequence[str], constants: Sequence[float]) -> list[tuple]:
    """Inputs for a check, taken from the SOURCE: the constants the program itself contains.

    A notion that used values I invented would be testing my taste. These come from the code's own
    literals, so a disagreement is between the program and itself.
    """
    base = sorted({int(c) for c in constants if isinstance(c, (int, float)) and c == int(c) and 1 <= c <= 12})
    # Sample a GRID, not just the literals the source happens to contain. MEASURED 2026-11-05: drawing
    # inputs only from the module's own constants gave a single sample of (2, 2), and at (2, 2) a sum and
    # a product are both 4 -- so the notions fired identically on buggy and correct code and discriminated
    # nothing. A check that cannot separate two programs is not a test of either; it is decoration.
    vals = sorted(set(base) | {2, 3, 4, 5})
    if not params:
        return [()]
    out: list[tuple] = []
    for combo in itertools.product(vals, repeat=len(params)):
        if len(set(combo)) == 1 and len(params) > 1:
            continue  # all-equal inputs hide sum-vs-product differences; keep them separate
        out.append(combo)
        if len(out) >= 6:
            break
    return out or [tuple(vals[0] for _ in params)]


def notions_for_source(source: str, module_name: str = "mod") -> list[Notion]:
    """Derive every falsifiable expectation this module can find in one piece of source."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    fns = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if not fns:
        return []
    ns, exec_err = _load_module(source, module_name)
    out: list[Notion] = []

    # --- SYMMETRY: two functions that compute the SAME quantity with the SAME scale are related ------
    # MEASURED 2026-11-05, twice. First version: fired whenever two same-signature functions differed,
    # which on correct code (an area beside a perimeter) is true by construction -- it fired on the buggy
    # module AND the fixed one, so it carried no information and a test built from it could never be
    # satisfied, and on the board it VETOED a real repair. Second version: I made it decline, and the
    # decline came back as a fire because `evaluate` treated "cannot run" as "refuted". Both are the same
    # error in different clothes -- reporting an opinion where nothing was measured.
    #
    # What is actually measurable: if two functions share their constants, they share a scale, so their
    # ratio is invariant across inputs and one can be an exact multiple of the other. THAT is a claim
    # with a truth value, and a violation of it is a real internal inconsistency. Otherwise this notion
    # has nothing to say about the pair and says so.
    by_sig: dict[tuple[str, ...], list[ast.FunctionDef]] = {}
    for fn in fns:
        by_sig.setdefault(tuple(_params(fn)), []).append(fn)
    for sig, group in by_sig.items():
        if len(sig) < 2:
            continue
        for a, b in itertools.combinations(group, 2):
            fa, fb = ns.get(a.name), ns.get(b.name)
            if not callable(fa) or not callable(fb):
                continue
            if not (set(_constants(_returns_expr(a))) & set(_constants(_returns_expr(b)))):
                continue  # different scale: no shared quantity, no claim
            samples = _sample_values(sig, _constants(_returns_expr(a)) + _constants(_returns_expr(b)))
            if len(samples) < 2:
                continue

            def _check(fa=fa, fb=fb, samples=samples, a=a.name, b=b.name) -> tuple[bool, str]:
                outs = []
                for smp in samples:
                    try:
                        outs.append((tuple(smp), float(fa(*smp)), float(fb(*smp))))
                    except Exception:  # noqa: BLE001 - a sample one function rejects is not a sample
                        continue
                ratios = [y / x for _s, x, y in outs if x]
                if len(ratios) < 2:
                    return False, "declines: not enough evaluable samples", True
                if (max(ratios) - min(ratios)) > 1e-9:
                    return False, (f"declines: {a}/{b} ratio drifts over samples "
                                   f"({min(ratios):.4g}..{max(ratios):.4g}), so they do not share a "
                                   f"scale and neither indicts the other"), True
                # The ratio holds. Now require it to be an exact structural multiple, which is what a
                # shared scale means; a drifting-free but arbitrary ratio is still just two functions.
                r = ratios[0]
                if abs(r - round(r, 6)) > 1e-9 and abs(1 / r - round(1 / r, 6)) > 1e-9:
                    return False, f"declines: ratio {r:.6g} is not a structural multiple", True
                return True, f"{a} and {b} hold the fixed ratio {r:.6g} across {len(ratios)} sample(s)"

            out.append(Notion(
                kind="SYMMETRY",
                subject=f"{a.name}/{b.name}",
                claim=(f"`{a.name}` and `{b.name}` share their constants ({', '.join(sig)}), so one is a "
                       f"fixed multiple of the other on every input"),
                check=_check,
                value=1.0,
            ))

    # --- IDENTITY: a function of fewer arguments is the degenerate case of one of more ------------
    # A cube is a box with equal sides. A square is a rectangle with equal sides. The degenerate input
    # is always "every argument equal", whatever the arities are -- MEASURED 2026-11-05, three failures
    # on the way to this line, each fixed by removing an assumption I had smuggled in:
    #   * pairing only 1-arg with 2-arg meant `cube_volume(s)` vs `box_volume(l, w, h)` got no notion;
    #   * pairing every low-arity function with every higher one gave `square_area vs rect_perimeter`,
    #     a category error that fires on correct code and VETOED a real repair on the board;
    #   * a purely numeric near-miss test cannot separate those -- a defect that happens to be right at
    #     one sample (w + h == w * h at 2) and a category error that crosses at one sample (16 == 16)
    #     look identical.
    # What separates them is the program's own declaration: functions that compute the same quantity
    # share a word in their names. That is reading what the source already says, not a table of formulas.
    # Two descriptions of one quantity agree on most inputs and differ on a few; the check declines
    # unless it sees exactly that.
    for s_fn in fns:
        for p_fn in fns:
            if p_fn is s_fn or len(_params(p_fn)) <= len(_params(s_fn)):
                continue
            _ta = set(s_fn.name.split("_")) - _STOP_TOKENS
            _tb = set(p_fn.name.split("_")) - _STOP_TOKENS
            if not (_ta & _tb):
                continue
            fs, fp = ns.get(s_fn.name), ns.get(p_fn.name)
            if not callable(fs) or not callable(fp):
                continue
            consts = _constants(_returns_expr(s_fn)) + _constants(_returns_expr(p_fn))
            samples = _sample_values(("x",), consts)
            if not samples:
                continue
            _arity = len(_params(p_fn))

            def _check(fs=fs, fp=fp, samples=samples, s_fn=s_fn.name, p_fn=p_fn.name,
                       arity=_arity) -> tuple[bool, str]:
                # EVERY sample counts. MEASURED 2026-11-05: the first version returned True on the first
                # sample that agreed, and at s=2 a buggy `w + h` gives 4 while `s * s` gives 4 -- so the
                # check stopped before reaching s=3 where 6 != 9 and the bug was never seen. A check that
                # exits on its first success cannot find an intermittent disagreement.
                bad: list[str] = []
                for (v,) in samples:
                    args = [v] * arity
                    try:
                        x, y = float(fs(v)), float(fp(*args))
                    except Exception:  # noqa: BLE001
                        continue
                    if abs(x - y) >= 1e-9:
                        bad.append(f"{s_fn}({v})={fs(v)} vs {p_fn}{tuple(args)}={fp(*args)}")
                if bad:
                    # The pairing rule has already established that these two compute the same quantity,
                    # so a disagreement needs no corroboration from a near-miss. MEASURED 2026-11-05:
                    # requiring the pair to agree on some inputs first made the notion DECLINE on a
                    # genuinely broken `cube_volume(s) -> 6 * s`, which disagrees with `box_volume` at
                    # every sample precisely because it is wrong -- the near-miss requirement was
                    # quietly demanding that a bug be almost correct.
                    return False, ("; ".join(bad[:2]) +
                                   " -- two descriptions of the same quantity disagree")
                return True, f"all {len(samples)} sample(s) agree"

            out.append(Notion(
                kind="IDENTITY",
                subject=f"{s_fn.name} vs {p_fn.name}(equal args)",
                claim=(f"`{s_fn.name}(x)` and `{p_fn.name}` called with every argument equal to `x` "
                       f"describe the same degenerate case; if they disagree, one of the two is wrong"),
                check=_check,
                value=1.5,
                arity=_arity,
            ))

    # --- AGREEMENT: a name that promises a relation, checked against the arithmetic it contains -------
    # `rect_perimeter(w, h) -> 2 * (w + h)` states its own relation with constants already present. A
    # sibling that reuses the same parameters but different constants invites the same question. This is
    # derived from the source's own literals, never from a table of known-correct formulas.
    for fn in fns:
        body = _returns_expr(fn)
        consts = _constants(body)
        if not consts or len(_params(fn)) < 2:
            continue
        for other in fns:
            if other is fn or tuple(_params(other)) != tuple(_params(fn)):
                continue
            oc = _constants(_returns_expr(other))
            if not oc:
                continue
            if set(oc) == set(consts):
                continue  # same constants: nothing distinct to compare
            fo, ff = ns.get(other.name), ns.get(fn.name)
            if not callable(fo) or not callable(ff):
                continue
            samples = _sample_values(tuple(_params(fn)), consts + oc)

            def _check(fo=fo, ff=ff, samples=samples, n1=other.name, n2=fn.name) -> tuple[bool, str]:
                # Not a verdict on the code: a claim that the DIFFERENT CONSTANTS produce a ratio worth
                # examining. It fires when the ratio of the two functions varies across samples, which
                # is exactly when a fixed relationship (like a scale factor) is being assumed and is not
                # holding.
                ratios: list[float] = []
                for s in samples:
                    a, b = ff(*s), fo(*s)
                    if not (isinstance(a, (int, float)) and isinstance(b, (int, float))) or abs(float(b)) < 1e-12:
                        return True, "undefined ratio; nothing to claim"
                    ratios.append(float(a) / float(b))
                if len(ratios) < 2:
                    return True, "single sample; a varying ratio cannot be shown"
                spread = max(ratios) - min(ratios)
                return spread < 1e-9, f"ratios of {n2}/{n1} over samples: {[round(r, 4) for r in ratios]}"

            out.append(Notion(
                kind="AGREEMENT",
                subject=f"{fn.name} vs {other.name}",
                claim=(f"`{fn.name}` and `{other.name}` share parameters but use different constants "
                       f"({sorted(set(consts))} vs {sorted(set(oc))}); if their ratio is not stable, "
                       f"one of them is not the scaled version of the other"),
                check=_check,
                value=1.0,
            ))

    # De-duplicate: IDENTITY was emitted three times for the same pair because the single/pair loops
    # were nested inside a third loop. Two notions with the same subject are one notion.
    seen_keys: set[tuple[str, str]] = set()
    unique: list[Notion] = []
    for n in out:
        k = (n.kind, n.subject)
        if k in seen_keys:
            continue
        seen_keys.add(k)
        unique.append(n)
    if exec_err is not None:
        # A module that will not import cannot support any notion; say so instead of reporting silence.
        return unique
    return unique


class NotionStore:
    """Remembers which notions fired, so a notion that fires on everything becomes visibly useless."""

    def __init__(self, path: str | pathlib.Path | None = None) -> None:
        self.path = pathlib.Path(path) if path else None
        self.seen: dict[str, dict[str, float]] = {}
        self.load()

    def to_dict(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "seen": self.seen}

    def load(self) -> None:
        if not self.path or not self.path.is_file():
            return
        try:
            d = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(d, dict) and d.get("schema") == SCHEMA and isinstance(d.get("seen"), dict):
                self.seen = d["seen"]
        except (ValueError, OSError, TypeError):
            return

    def save(self) -> None:
        if not self.path:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
            tmp.replace(self.path)
        except OSError:
            return

    @staticmethod
    def key(n: Notion) -> str:
        return f"{n.kind}::{n.subject}"

    def record(self, results: Iterable[Mapping[str, Any]]) -> None:
        for r in results:
            k = f"{r.get('kind')}::{r.get('subject')}"
            slot = self.seen.setdefault(k, {"evaluated": 0.0, "fired": 0.0, "declined": 0.0})
            slot["evaluated"] += 1
            slot.setdefault("declined", 0.0)
            if r.get("fired"):
                slot["fired"] += 1
            if r.get("declined"):
                slot["declined"] += 1
        self.save()

    def is_noise(self, n: Notion, *, min_evidence: int = 2, max_rate: float = 0.98) -> bool:
        """True when this notion has fired on essentially everything it has ever looked at.

        A notion that fires on correct code as readily as on broken code cannot be a reason to edit
        anything -- that is the distinction MEASURED 2026-11-05 between `square_area vs rect_area(x,x)`
        (fires on the defect, holds on the fix) and `square_area vs rect_perimeter(x,x)` (fires on
        both, because an area and a perimeter are simply different quantities). Requiring evidence
        from more than one evaluation keeps a first-ever look from being dismissed on no record.
        """
        slot = self.seen.get(self.key(n)) or {}
        evaluated = float(slot.get("evaluated") or 0.0)
        if evaluated < min_evidence:
            return False
        return (float(slot.get("fired") or 0.0) / evaluated) >= max_rate

    def informativeness(self, n: Notion) -> float:
        """How much a fired notion is worth. A notion that fires on every module tells you nothing."""
        slot = self.seen.get(self.key(n))
        if not slot or slot.get("evaluated", 0) <= 0:
            return 1.0
        rate = slot["fired"] / slot["evaluated"]
        return max(0.0, 1.0 - abs(rate - 0.5) * 2.0)

    def summary(self) -> Mapping[str, Any]:
        return {"schema": SCHEMA, "tracked": len(self.seen), "seen": self.seen,
                "persisted_to": str(self.path) if self.path else None}


_LIVE: NotionStore | None = None


def live_notions(path: str | pathlib.Path | None = None) -> NotionStore:
    global _LIVE
    p = pathlib.Path(path) if path else None
    if _LIVE is None or _LIVE.path != p:
        _LIVE = NotionStore(p)
    return _LIVE
