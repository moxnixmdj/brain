#!/usr/bin/env python3
"""Minimal Epistemic Core v1 — Zero-Neural Jobs 1 + 2 + 3 + 4a + 5a in one lean engine.

Built from live measurement (Elon's law: delete every unnecessary part, keep every hot path
at CPU speed):
  - Job 1 (LiveIntrospector):   live scope + runtime dir()/stdlib sibling symbol grounding.
  - Job 2 (DominoMemory):       O(|delta|) reverse-index Cascade/Absence memory + speaker-bound
                                temporal conversational retrieval (zero neural weights).
  - Job 3 (FastCoWVerifier):    pre-compiled os.fork() Copy-on-Write executor (~0.5 ms/cand),
                                sys.settrace failure localizer, 5-mutant lie detector, and
                                multi-candidate AST-minimal + prior-weighted overfit killer.
  - Job 4a (SpecExtractor):     deterministic doctest/docstring + error-trace constraint extractor.
  - Job 5a (PriorRepairEngine): <1 MB git-trained AST-edit conditional prior + trace-localized
                                atomic/structural/dual-swap grammar + instant online learning.
"""
from __future__ import annotations

import ast
import builtins
import copy
import datetime
import doctest
import math
import os
import re
import signal
import subprocess
import sys
import time
import warnings
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

SCHEMA = "BRAIN_MINIMAL_EPISTEMIC_CORE_V1"

# =========================================================================== #
# JOB 1: LiveIntrospector (ground names/methods in live scope + Python stdlib)
# =========================================================================== #
_METHOD_FAMILIES: tuple[tuple[str, ...], ...] = (
    ("startswith", "endswith"),
    ("islower", "isupper", "isdigit", "isalpha", "isalnum", "isspace", "isnumeric", "isdecimal"),
    ("lower", "upper", "swapcase", "title", "capitalize", "casefold"),
    ("strip", "lstrip", "rstrip"),
    ("find", "rfind", "index", "rindex"),
    ("split", "rsplit", "splitlines"),
    ("append", "extend", "insert"),
    ("pop", "remove", "clear"),
    ("keys", "values", "items"),
    ("union", "intersection", "difference", "symmetric_difference"),
    ("add", "discard", "remove"),
    ("sort", "reverse"),
    ("encode", "decode"),
    ("ljust", "rjust", "center"),
)
_FUNC_FAMILIES: tuple[tuple[str, ...], ...] = (
    ("min", "max"),
    ("any", "all"),
    ("floor", "ceil", "round", "trunc", "int"),
    ("sorted", "reversed", "list", "set", "tuple"),
    ("sum", "len", "abs"),
    ("ord", "chr"),
    ("str", "int", "float", "bool"),
    ("bin", "oct", "hex"),
    ("isinstance", "issubclass"),
)
_METHOD_SIBLINGS: dict[str, tuple[str, ...]] = {}
for _fam in _METHOD_FAMILIES:
    for _m in _fam:
        _METHOD_SIBLINGS[_m] = tuple(x for x in _fam if x != _m)
_FUNC_SIBLINGS: dict[str, tuple[str, ...]] = {}
for _fam in _FUNC_FAMILIES:
    for _f in _fam:
        _FUNC_SIBLINGS[_f] = tuple(x for x in _fam if x != _f)

_WRAP_CALLS: tuple[str, ...] = ("abs", "len", "int", "float", "str", "sorted", "reversed", "list", "set")
_WRAP_METHODS: tuple[str, ...] = ("lower", "upper", "strip")
_BUILTINS = frozenset(dir(builtins))


class LiveIntrospector:
    """Extracts in-scope symbols, sibling runtime methods, and repo identifiers (<1 ms)."""

    @staticmethod
    def scope_symbols(tree: ast.AST) -> dict[str, list[str]]:
        params: list[str] = []
        locals_: list[str] = []
        funcs: list[str] = []
        imports: list[str] = []
        seen_p, seen_l, seen_f, seen_i = set(), set(), set(), set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name not in seen_f:
                    seen_f.add(node.name)
                    funcs.append(node.name)
                for a in node.args.posonlyargs + node.args.args + node.args.kwonlyargs:
                    if a.arg not in seen_p:
                        seen_p.add(a.arg)
                        params.append(a.arg)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                if node.id not in seen_l:
                    seen_l.add(node.id)
                    locals_.append(node.id)
            elif isinstance(node, ast.ImportFrom):
                for al in node.names:
                    nm = al.asname or al.name
                    if nm not in seen_i:
                        seen_i.add(nm)
                        imports.append(nm)
        return {"params": params, "locals": locals_, "funcs": funcs, "imports": imports}

    @staticmethod
    def sibling_methods(attr: str) -> tuple[str, ...]:
        return _METHOD_SIBLINGS.get(attr, ())

    @staticmethod
    def sibling_functions(name: str, extra_in_scope: Sequence[str] = ()) -> tuple[str, ...]:
        base = list(_FUNC_SIBLINGS.get(name, ()))
        for s in extra_in_scope:
            if s != name and s not in base:
                base.append(s)
        return tuple(base)


# =========================================================================== #
# JOB 2: DominoMemory (O(|delta|) Cascade/Absence + Speaker-Temporal Retrieval)
# =========================================================================== #
_TOK_RE = re.compile(r"[a-z0-9']+")
_STOP = frozenset(
    "the a an is are was were be been being to of in on at for with and or that this it as by "
    "from did do does has have had what when where who how why would could should will can into "
    "about than then them they their there here just also very much more most some any its our "
    "you your we me my i'm it's don't didn't that's he's she's they're we're you're i've".split()
)
_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9,
    "sept": 9, "september": 9, "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}
_WEEKDAYS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
_SESSION_DATE_RE = re.compile(r"(\d{1,2})\s+([A-Za-z]+),?\s+(\d{4})")


def _stem(w: str) -> str:
    w = w.strip("'")
    if len(w) <= 3:
        return w
    for suf, rep in (
        ("ies", "y"), ("ied", "y"), ("ing", ""), ("ed", ""), ("es", ""), ("ly", ""), ("er", ""),
        ("tion", "t"), ("ment", ""), ("ness", ""), ("ful", ""), ("s", ""),
    ):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            base = w[: -len(suf)] + rep
            if len(base) >= 4 and base[-1] == base[-2] and base[-1] not in "lsz":
                base = base[:-1]
            return base
    return w


def _tokenize_stemmed(text: str) -> list[str]:
    out: list[str] = []
    for raw in _TOK_RE.findall(text.lower()):
        w = raw.replace("'s", "").strip("'")
        if len(w) <= 1 or w in _STOP:
            continue
        out.append(_stem(w))
    return out


class DominoMemory:
    """O(|delta|) reverse-dependency Cascade/Absence store + conversational memory index."""

    def __init__(self) -> None:
        self.facts: dict[str, dict[str, Any]] = {}
        self.dependents: dict[str, set[str]] = defaultdict(set)
        self.deps_of: dict[str, set[str]] = defaultdict(set)
        self.entity_latest: dict[tuple[str, str], str] = {}

    def assert_fact(
        self,
        fid: str,
        content: Any,
        deps: Iterable[str] = (),
        entity_key: tuple[str, str] | None = None,
    ) -> list[str]:
        """Store a fact; if entity_key was already asserted, cascade-retract the superseded fact."""
        retracted: list[str] = []
        if entity_key is not None:
            prev = self.entity_latest.get(entity_key)
            if prev is not None and prev != fid and prev in self.facts:
                retracted = self.retract_fact(prev)
            self.entity_latest[entity_key] = fid
        self.facts[fid] = {"content": content, "entity_key": entity_key}
        dset = set(deps)
        self.deps_of[fid] = dset
        for d in dset:
            self.dependents[d].add(fid)
        return retracted

    def retract_fact(self, fid: str) -> list[str]:
        """BFS cascade retraction over reverse dependency edges in O(|retracted|)."""
        removed: list[str] = []
        stack = [fid]
        seen = {fid}
        while stack:
            cur = stack.pop()
            if cur in self.facts:
                meta = self.facts.pop(cur)
                ek = meta.get("entity_key")
                if ek is not None and self.entity_latest.get(ek) == cur:
                    del self.entity_latest[ek]
                removed.append(cur)
            for parent in self.deps_of.pop(cur, ()):
                self.dependents[parent].discard(cur)
            for child in self.dependents.pop(cur, ()):
                if child not in seen:
                    seen.add(child)
                    stack.append(child)
        return removed

    def has_fact(self, fid: str) -> bool:
        return fid in self.facts

    def get_fact(self, fid: str) -> Any:
        row = self.facts.get(fid)
        return None if row is None else row["content"]

    @staticmethod
    def resolve_session_date(dt_str: str) -> datetime.date | None:
        m = _SESSION_DATE_RE.search(dt_str or "")
        if not m:
            return None
        day, mon_s, yr = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        mon = _MONTHS.get(mon_s)
        if not mon:
            return None
        try:
            return datetime.date(yr, mon, day)
        except ValueError:
            return None

    @staticmethod
    def resolve_relative_dates(text: str, session_date: datetime.date | None) -> list[str]:
        """Resolve relative time expressions in a turn against its session timestamp."""
        if session_date is None:
            return []
        low = text.lower()
        resolved: list[str] = []
        if "yesterday" in low:
            d = session_date - datetime.timedelta(days=1)
            resolved.append(d.strftime("%-d %B %Y"))
        if "today" in low or "this morning" in low or "tonight" in low:
            resolved.append(session_date.strftime("%-d %B %Y"))
        for wd_name, wd_idx in _WEEKDAYS.items():
            if f"last {wd_name}" in low or f"on {wd_name}" in low:
                delta = (session_date.weekday() - wd_idx) % 7 or 7
                d = session_date - datetime.timedelta(days=delta)
                resolved.append(d.strftime("%-d %B %Y"))
        if "last week" in low:
            d = session_date - datetime.timedelta(days=7)
            resolved.append(f"week of {d.strftime('%-d %B %Y')}")
        if "last year" in low:
            resolved.append(str(session_date.year - 1))
        return resolved

    @classmethod
    def index_conversation(cls, conv_dict: dict[str, Any]) -> dict[str, Any]:
        """Build speaker-bound, stemmed, adjacent-linked, temporally anchored index (<5 ms)."""
        turns: list[dict[str, Any]] = []
        sess_nums = sorted(
            int(k.split("_")[1])
            for k in conv_dict
            if k.startswith("session_") and not k.endswith("_date_time")
        )
        speakers: set[str] = set()
        for sn in sess_nums:
            dt_str = conv_dict.get(f"session_{sn}_date_time", "")
            sdate = cls.resolve_session_date(dt_str)
            s_turns = conv_dict[f"session_{sn}"]
            for pos, t in enumerate(s_turns):
                spk = str(t.get("speaker", "")).strip()
                if spk:
                    speakers.add(spk.lower())
                raw_txt = str(t.get("text", ""))
                cap = str(t.get("blip_caption", "") or "")
                rel_dates = cls.resolve_relative_dates(raw_txt, sdate)
                full_txt = raw_txt + (f" {cap}" if cap else "")
                if rel_dates:
                    full_txt += " " + " ".join(rel_dates)
                toks = _tokenize_stemmed(full_txt)
                # Adjacent-turn linkage: inherit topic words at lower weight from prev/next turn
                nbr_txt = ""
                if pos > 0:
                    nbr_txt += " " + str(s_turns[pos - 1].get("text", "")) + " " + str(s_turns[pos - 1].get("blip_caption", "") or "")
                if pos + 1 < len(s_turns):
                    nbr_txt += " " + str(s_turns[pos + 1].get("text", ""))
                nbr_toks = _tokenize_stemmed(nbr_txt)
                turns.append({
                    "dia_id": t["dia_id"],
                    "session": sn,
                    "pos": pos,
                    "date_str": dt_str,
                    "date": sdate,
                    "speaker": spk.lower(),
                    "text": full_txt,
                    "tf": Counter(toks),
                    "dl": len(toks),
                    "nbr_tf": Counter(nbr_toks),
                    "has_time_cue": bool(rel_dates or re.search(r"\b(19|20)\d\d\b|\b(ago|yesterday|last|next|january|february|march|april|may|june|july|august|september|october|november|december|monday|tuesday|wednesday|thursday|friday|saturday|sunday|week|month|year|day)\b", raw_txt.lower())),
                })
        n = max(1, len(turns))
        avgdl = sum(t["dl"] for t in turns) / n
        df: Counter[str] = Counter()
        for t in turns:
            for w in t["tf"]:
                df[w] += 1
        idf = {w: math.log((n - c + 0.5) / (c + 0.5) + 1.0) for w, c in df.items()}
        # Build token -> turn indices inverted index for fast 2-hop expansion
        inv: dict[str, list[int]] = defaultdict(list)
        for idx, t in enumerate(turns):
            for w in t["tf"]:
                inv[w].append(idx)
        return {"turns": turns, "avgdl": avgdl, "idf": idf, "speakers": speakers, "inv": inv}

    @staticmethod
    def retrieve_turns(
        index: dict[str, Any],
        question: str,
        top_k: int = 10,
        *,
        multi_hop: bool = True,
    ) -> dict[str, Any]:
        """Speaker-bound + stemmed + temporal + 2-hop graph retrieval (<1 ms/query)."""
        turns = index["turns"]
        idf = index["idf"]
        avgdl = max(1.0, index["avgdl"])
        speakers = index["speakers"]
        qlow = question.lower()
        mentioned_speakers = [s for s in speakers if re.search(rf"\b{re.escape(s)}\b", qlow)]
        is_temporal = bool(re.match(r"^\s*(when|what date|what time|what year|how long|how many (days|weeks|months|years))", qlow))

        # Remove speaker names from content tokens so speaker weighting is clean & explicit
        raw_qtoks = _tokenize_stemmed(question)
        spk_stems = {_stem(s) for s in speakers}
        qtoks = [w for w in raw_qtoks if w not in spk_stems] or raw_qtoks
        qset = set(qtoks)
        # Also bigrams for phrase precision
        qbigrams = {(qtoks[i], qtoks[i + 1]) for i in range(len(qtoks) - 1)}

        scores: list[float] = [0.0] * len(turns)
        own_content_scores: list[float] = [0.0] * len(turns)
        for i, t in enumerate(turns):
            tf = t["tf"]
            dl = t["dl"]
            denom_base = 1.5 * (0.25 + 0.75 * dl / avgdl)
            sc = 0.0
            matched_w = 0
            for w in qset:
                f = tf.get(w, 0)
                if f:
                    matched_w += 1
                    sc += idf.get(w, 1.5) * (f * 2.5) / (f + denom_base)
            # Coverage boost (multi-term match) on speaker's OWN turn text
            if len(qset) >= 2 and matched_w >= 2:
                sc *= 1.0 + 0.12 * (matched_w - 1)
            own_content_scores[i] = sc
            # Adjacent-turn bridge (catches turns referencing prev turn / image caption)
            nbr_sc = 0.0
            ntf = t["nbr_tf"]
            for w in qset:
                if ntf.get(w, 0):
                    nbr_sc += idf.get(w, 1.0)
            sc += 0.22 * nbr_sc
            # Speaker-ownership binding
            if len(mentioned_speakers) == 1:
                target_spk = mentioned_speakers[0]
                if t["speaker"] == target_spk:
                    sc *= 1.28
                elif target_spk in t["text"].lower():
                    sc *= 1.05
                else:
                    sc *= 0.78
            # Temporal cue boost for "When..." questions
            if is_temporal and t["has_time_cue"] and sc > 0.0:
                sc *= 1.25
            scores[i] = sc

        # 2-hop associative expansion: rare tokens from top-2 anchor turns boost linked turns!
        if multi_hop and turns:
            top_anchors = sorted(range(len(turns)), key=lambda i: -scores[i])[:2]
            hop_weights: dict[str, float] = {}
            for aidx in top_anchors:
                if scores[aidx] <= 0.0:
                    continue
                for w in turns[aidx]["tf"]:
                    if w not in qset and w not in spk_stems and idf.get(w, 0.0) >= 2.2:
                        hop_weights[w] = max(hop_weights.get(w, 0.0), idf[w])
            # Keep top-8 rarest bridge terms
            bridge = sorted(hop_weights.items(), key=lambda x: -x[1])[:8]
            if bridge:
                inv = index["inv"]
                anchor_set = set(top_anchors)
                for w, wt in bridge:
                    for j in inv.get(w, ()):
                        if j not in anchor_set:
                            # Prefer same speaker if a single speaker was asked
                            spk_mul = 1.0 if (len(mentioned_speakers) != 1 or turns[j]["speaker"] == mentioned_speakers[0]) else 0.45
                            scores[j] += 0.14 * wt * spk_mul

        order = sorted(range(len(turns)), key=lambda i: (-scores[i], i))
        top_idxs = order[:top_k]

        # Speaker-contradiction check (Job 2 adversarial / wrong-speaker detector!):
        # If question names exactly ONE speaker S, and the highest-content-match turn belongs
        # to the OTHER speaker with substantially stronger content overlap than S's own turns.
        speaker_conflict = False
        conflict_score = 0.0
        if len(mentioned_speakers) == 1:
            target_spk = mentioned_speakers[0]
            best_target = max((own_content_scores[i] for i, t in enumerate(turns) if t["speaker"] == target_spk), default=0.0)
            best_other = max((own_content_scores[i] for i, t in enumerate(turns) if t["speaker"] != target_spk), default=0.0)
            min_other = min(3.0, max(0.8, 0.45 * math.log(len(turns) + 2)))
            if best_other > 0.0:
                conflict_score = (best_other - best_target) / (best_other + 1e-6)
                speaker_conflict = best_other >= min_other and best_other > best_target * 1.45

        return {
            "dia_ids": [turns[i]["dia_id"] for i in top_idxs],
            "top_turns": [turns[i] for i in top_idxs],
            "speaker_conflict": speaker_conflict,
            "conflict_score": round(conflict_score, 4),
        }


# =========================================================================== #
# JOB 4a: SpecExtractor (deterministic doctest + error-trace constraint parser)
# =========================================================================== #
class SpecExtractor:
    """Extracts executable checkable assertions from docstrings + failure traces."""

    _DT_PARSER = doctest.DocTestParser()
    _INLINE_EX_RE = re.compile(r"([A-Za-z_]\w*\([^\n]*?\))\s*(?:==|=>|->|returns?)\s*([^\n#;]+)")

    @classmethod
    def doctest_assertions(cls, source: str, entry_point: str, docstring: str | None = None) -> str:
        """Extract runnable `>>>` and inline `fn(...) ==/=>/-> lit` checks from docstring."""
        doc = docstring or ""
        if not doc:
            try:
                tree = ast.parse(source)
                for node in tree.body:
                    if isinstance(node, ast.FunctionDef) and node.name == entry_point:
                        doc = ast.get_docstring(node) or ""
                        break
            except SyntaxError:
                return ""
        if not doc:
            return ""
        checks: list[str] = []
        seen: set[str] = set()

        def _add(call_s: str, want_s: str) -> None:
            call_s = call_s.strip()
            want_s = want_s.strip().rstrip(".,;")
            if not call_s or not want_s or entry_point not in call_s or "\n" in call_s:
                return
            try:
                ast.parse(call_s, mode="eval")
                want_val = ast.literal_eval(want_s)
            except Exception:
                return
            if isinstance(want_val, float):
                chk = f"assert abs(({call_s}) - ({want_val!r})) < 1e-4"
            else:
                chk = f"assert ({call_s}) == ({want_val!r})"
            if chk not in seen:
                seen.add(chk)
                checks.append(chk)

        if ">>>" in doc:
            try:
                for ex in cls._DT_PARSER.get_examples(doc):
                    _add(ex.source, ex.want)
            except Exception:
                pass
        for m in cls._INLINE_EX_RE.finditer(doc):
            if m.group(1).startswith(entry_point + "("):
                _add(m.group(1), m.group(2))
        return "\n".join(checks)


# =========================================================================== #
# JOB 3: FastCoWVerifier (0.5 ms os.fork() CoW + trace + 5-mutant lie detector)
# =========================================================================== #
@dataclass
class RunOutcome:
    passed: bool
    exc_type: str = ""
    exc_line: int = 0
    exc_msg: str = ""
    elapsed_ms: float = 0.0


class FastCoWVerifier:
    """Pre-compiled os.fork() Copy-on-Write verifier + trace localizer + 5-mutant lie detector."""

    @staticmethod
    def run_isolated(code: str, test_code: str, timeout_s: float = 0.25) -> RunOutcome:
        """Execute `code + test_code` in an os.fork() CoW child with hard ITIMER timeout."""
        t0 = time.perf_counter()
        full = code + "\n" + test_code
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                compiled = compile(full, "<cand>", "exec")
        except BaseException as e:
            return RunOutcome(False, type(e).__name__, getattr(e, "lineno", 0) or 0, str(e)[:80], (time.perf_counter() - t0) * 1000.0)

        r_fd, w_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(r_fd)
            try:
                # Silence candidate prints & warnings in child
                devnull = os.open(os.devnull, os.O_WRONLY)
                os.dup2(devnull, 1)
                os.dup2(devnull, 2)
                os.close(devnull)
                warnings.simplefilter("ignore")
                signal.setitimer(signal.ITIMER_REAL, timeout_s)
                ns: dict[str, Any] = {}
                exec(compiled, ns, ns)
                os.write(w_fd, b"1")
            except BaseException as e:
                tb = e.__traceback__
                ln = 0
                while tb is not None:
                    if tb.tb_frame.f_code.co_filename == "<cand>":
                        ln = tb.tb_lineno
                    tb = tb.tb_next
                msg = f"0|{type(e).__name__}|{ln}|{str(e)[:60]}".encode("utf-8", "replace")
                try:
                    os.write(w_fd, msg)
                except OSError:
                    pass
            finally:
                try:
                    os.close(w_fd)
                except OSError:
                    pass
                os._exit(0)
        os.close(w_fd)
        buf = bytearray()
        while True:
            chunk = os.read(r_fd, 512)
            if not chunk:
                break
            buf.extend(chunk)
        os.close(r_fd)
        os.waitpid(pid, 0)
        el_ms = (time.perf_counter() - t0) * 1000.0
        out = buf.decode("utf-8", "replace")
        if out == "1":
            return RunOutcome(True, elapsed_ms=el_ms)
        parts = out.split("|", 3)
        if len(parts) == 4:
            return RunOutcome(False, parts[1], int(parts[2] or 0), parts[3], el_ms)
        return RunOutcome(False, "TimeoutOrCrash", 0, out[:60], el_ms)

    @staticmethod
    def localize_failure(code: str, test_code: str, timeout_s: float = 0.30) -> dict[str, Any]:
        """Run buggy code once under sys.settrace inside fork() to capture executed lines & error."""
        code_lines = code.count("\n") + 1
        full = code + "\n" + test_code
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                compiled = compile(full, "<buggy>", "exec")
        except BaseException as e:
            return {"executed_lines": set(), "exc_type": type(e).__name__, "exc_line": getattr(e, "lineno", 0) or 0}

        r_fd, w_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(r_fd)
            exec_lines: set[int] = set()
            def _tracer(frame, event, arg):
                if event == "line" and frame.f_code.co_filename == "<buggy>" and frame.f_lineno <= code_lines:
                    exec_lines.add(frame.f_lineno)
                return _tracer
            exc_type, exc_line = "", 0
            try:
                devnull = os.open(os.devnull, os.O_WRONLY)
                os.dup2(devnull, 1)
                os.dup2(devnull, 2)
                os.close(devnull)
                warnings.simplefilter("ignore")
                signal.setitimer(signal.ITIMER_REAL, timeout_s)
                sys.settrace(_tracer)
                ns: dict[str, Any] = {}
                exec(compiled, ns, ns)
            except BaseException as e:
                sys.settrace(None)
                exc_type = type(e).__name__
                tb = e.__traceback__
                while tb is not None:
                    if tb.tb_frame.f_code.co_filename == "<buggy>" and tb.tb_lineno <= code_lines:
                        exc_line = tb.tb_lineno
                    tb = tb.tb_next
            finally:
                sys.settrace(None)
                payload = f"{exc_type}|{exc_line}|{','.join(str(x) for x in sorted(exec_lines))}".encode("utf-8", "replace")
                try:
                    os.write(w_fd, payload)
                    os.close(w_fd)
                except OSError:
                    pass
                os._exit(0)
        os.close(w_fd)
        buf = bytearray()
        while True:
            chunk = os.read(r_fd, 4096)
            if not chunk:
                break
            buf.extend(chunk)
        os.close(r_fd)
        os.waitpid(pid, 0)
        parts = buf.decode("utf-8", "replace").split("|", 2)
        if len(parts) == 3:
            lines = {int(x) for x in parts[2].split(",") if x.isdigit()}
            return {"executed_lines": lines, "exc_type": parts[0], "exc_line": int(parts[1] or 0)}
        return {"executed_lines": set(), "exc_type": "TimeoutOrCrash", "exc_line": 0}

    @classmethod
    def check_test_strength(cls, source: str, test_code: str, max_mutants: int = 5) -> dict[str, Any]:
        """5-Mutant Lie Detector (<4 ms): rejects vacuous tests that pass even when code is broken."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return {"mutants": 0, "killed": 0, "kill_rate": 0.0, "is_lie": True}
        mutants: list[str] = []
        # Generate up to 5 distinct destructive mutations (return None, flip compare, flip constant)
        for node in ast.walk(tree):
            if len(mutants) >= max_mutants:
                break
            if isinstance(node, ast.Return) and node.value is not None:
                old = node.value
                node.value = ast.Constant(value=None)
                mutants.append(ast.unparse(tree))
                node.value = old
            elif isinstance(node, ast.Compare) and len(node.ops) == 1:
                old_op = node.ops[0]
                flip = {ast.Lt: ast.GtE, ast.LtE: ast.Gt, ast.Gt: ast.LtE, ast.GtE: ast.Lt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}.get(type(old_op))
                if flip:
                    node.ops[0] = flip()
                    mutants.append(ast.unparse(tree))
                    node.ops[0] = old_op
            elif isinstance(node, ast.BinOp) and type(node.op) in (ast.Add, ast.Sub, ast.Mult):
                old_op = node.op
                node.op = ast.Sub() if isinstance(old_op, ast.Add) else ast.Add()
                mutants.append(ast.unparse(tree))
                node.op = old_op
        if not mutants:
            return {"mutants": 0, "killed": 0, "kill_rate": 0.0, "is_lie": True}
        killed = sum(1 for m in mutants if not cls.run_isolated(m, test_code, 0.15).passed)
        rate = killed / len(mutants)
        return {"mutants": len(mutants), "killed": killed, "kill_rate": round(rate, 4), "is_lie": killed == 0}

    @staticmethod
    def extract_check_snippets(test_code: str) -> tuple[str, list[str]]:
        """Split a Python test script into `(setup_code, [check_snippet_0, ...])` for per-assertion bitmasks.

        Supports both top-level `assert ...` sequences and `def check(candidate):` / `def test_*():` wrappers.
        """
        try:
            tree = ast.parse(test_code)
        except SyntaxError:
            return "", []
        setup_stmts: list[ast.stmt] = []
        checks: list[str] = []
        # Case A: top-level `assert` statements
        top_asserts = [s for s in tree.body if isinstance(s, ast.Assert)]
        if len(top_asserts) >= 2:
            for s in tree.body:
                if isinstance(s, ast.Assert):
                    checks.append(ast.unparse(s))
                else:
                    setup_stmts.append(s)
            return "\n".join(ast.unparse(s) for s in setup_stmts), checks[:32]
        # Case B: multiple `def test_*():` functions
        test_fns = [s for s in tree.body if isinstance(s, ast.FunctionDef) and s.name.startswith("test_")]
        if len(test_fns) >= 2:
            for s in tree.body:
                setup_stmts.append(s)
            for fn in test_fns[:32]:
                checks.append(f"{fn.name}()")
            return "\n".join(ast.unparse(s) for s in setup_stmts), checks
        # Case C: HumanEval-style `def check(candidate): assert ...` + `check(fn)`
        for s in tree.body:
            if isinstance(s, ast.FunctionDef) and s.name == "check":
                fn_asserts = [b for b in s.body if isinstance(b, ast.Assert)]
                if len(fn_asserts) >= 2:
                    # Find what `check(...)` is called with
                    cand_expr = None
                    for tail in tree.body:
                        if isinstance(tail, ast.Expr) and isinstance(tail.value, ast.Call):
                            if isinstance(tail.value.func, ast.Name) and tail.value.func.id == "check" and tail.value.args:
                                cand_expr = ast.unparse(tail.value.args[0])
                                break
                    if cand_expr:
                        pre = [ast.unparse(b) for b in tree.body if b is not s and not (isinstance(b, ast.Expr) and isinstance(b.value, ast.Call) and isinstance(b.value.func, ast.Name) and b.value.func.id == "check")]
                        pre.append(f"candidate = {cand_expr}")
                        for b in s.body:
                            if isinstance(b, ast.Assert):
                                checks.append(ast.unparse(b))
                            else:
                                pre.append(ast.unparse(b))
                        return "\n".join(pre), checks[:32]
        return "", []

    @staticmethod
    def run_check_bitmask(
        source: str,
        setup_code: str,
        check_snippets: Sequence[str],
        timeout_s: float = 0.15,
    ) -> tuple[int, int]:
        """Evaluate every check independently inside ONE `os.fork()` CoW call (~1.2 ms total).

        Returns `(passed_bitmask, total_checks)` so Dual-Program Splicing can discover
        complementary partial repairs covering disjoint failing assertions!
        """
        n_checks = min(len(check_snippets), 32)
        if n_checks == 0:
            return 0, 0
        lines = [source, setup_code, "__mask__ = 0"]
        for i, snip in enumerate(check_snippets[:n_checks]):
            lines.append("try:")
            for sub_ln in snip.splitlines():
                lines.append("    " + sub_ln)
            lines.append(f"    __mask__ |= {1 << i}")
            lines.append("except BaseException:")
            lines.append("    pass")
        full = "\n".join(lines) + "\n"
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                compiled = compile(full, "<mask>", "exec")
        except BaseException:
            return 0, n_checks

        r_fd, w_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(r_fd)
            try:
                devnull = os.open(os.devnull, os.O_WRONLY)
                os.dup2(devnull, 1)
                os.dup2(devnull, 2)
                os.close(devnull)
                warnings.simplefilter("ignore")
                signal.setitimer(signal.ITIMER_REAL, timeout_s)
                ns: dict[str, Any] = {}
                exec(compiled, ns, ns)
                os.write(w_fd, str(int(ns.get("__mask__", 0))).encode("ascii"))
            except BaseException:
                try:
                    os.write(w_fd, b"0")
                except OSError:
                    pass
            finally:
                try:
                    os.close(w_fd)
                except OSError:
                    pass
                os._exit(0)
        os.close(w_fd)
        buf = bytearray()
        while True:
            chunk = os.read(r_fd, 64)
            if not chunk:
                break
            buf.extend(chunk)
        os.close(r_fd)
        os.waitpid(pid, 0)
        s = buf.decode("ascii", errors="ignore").strip()
        return (int(s) if s.isdigit() else 0), n_checks


# =========================================================================== #
# JOB 5a: Git-Trained Statistical AST Prior (<1 MB) + PriorRepairEngine
# =========================================================================== #
class GitASTPrior:
    """<1 MB conditional statistical prior P(edit_op | context) trained directly on real git commits."""

    DEFAULT_WEIGHTS: dict[str, float] = {
        "cmp_swap": 3.2,
        "binop_swap": 2.9,
        "boolop_swap": 2.8,
        "const_step": 2.7,
        "const_flip": 2.7,
        "method_sibling": 3.0,
        "func_sibling": 2.9,
        "arg_perm": 2.7,
        "null_guard": 2.6,
        "truth_lift": 2.5,
        "expr_off_by_one": 2.4,
        "var_binop_slice": 2.1,
        "var_swap": 2.4,
        "operand_swap": 2.6,
        "range_bound": 2.7,
        "slice_bound": 2.5,
        "wrap_expr": 2.2,
        "unwrap_expr": 2.3,
        "dual_swap": 2.5,
        "unary_toggle": 2.4,
        "elem_drop": 2.1,
        "stmt_delete": 1.4,
        "aug_assign_swap": 2.6,
        "guard_insert": 1.6,
        "learned_lesson": 3.4,
    }

    def __init__(self) -> None:
        self.op_counts: Counter[str] = Counter()
        self.total_examples: int = 0

    def train_from_git_repos(self, repo_paths: Sequence[str], max_commits_per_repo: int = 120) -> dict[str, Any]:
        """Mine real Python diffs from local git repos into a compact (<50 KB) edit-op prior."""
        t0 = time.perf_counter()
        commits_used = 0
        for rpath in repo_paths:
            if not os.path.isdir(rpath):
                continue
            log = subprocess.run(
                ["git", "-C", rpath, "log", f"-n{max_commits_per_repo}", "--pretty=format:%H", "--", "*.py"],
                capture_output=True, text=True, check=False,
            )
            for sha in log.stdout.splitlines():
                diff = subprocess.run(
                    ["git", "-C", rpath, "show", "--unified=0", "--no-color", sha, "--", "*.py"],
                    capture_output=True, text=True, check=False,
                ).stdout
                minus_lines = [l[1:].strip() for l in diff.splitlines() if l.startswith("-") and not l.startswith("---")]
                plus_lines = [l[1:].strip() for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
                if not minus_lines or not plus_lines or len(minus_lines) + len(plus_lines) > 30:
                    continue
                commits_used += 1
                self._observe_text_diff(minus_lines, plus_lines)
        self.total_examples += commits_used
        return {
            "commits_trained": commits_used,
            "unique_ops": len(self.op_counts),
            "prior_bytes": len(str(dict(self.op_counts))),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }

    def _observe_text_diff(self, minus_lines: list[str], plus_lines: list[str]) -> None:
        m_txt = " ".join(minus_lines)
        p_txt = " ".join(plus_lines)
        if any(op in m_txt for op in ("<=", ">=", "==", "!=", " < ", " > ")) and any(op in p_txt for op in ("<=", ">=", "==", "!=", " < ", " > ")):
            self.op_counts["cmp_swap"] += 1
        if " and " in m_txt and " or " in p_txt or " or " in m_txt and " and " in p_txt:
            self.op_counts["boolop_swap"] += 1
        if " not " in m_txt != (" not " in p_txt):
            self.op_counts["unary_toggle"] += 1
        if "if " in p_txt and "if " not in m_txt:
            self.op_counts["guard_insert"] += 1
        if re.search(r"\.[a-z_]+\(", m_txt) and re.search(r"\.[a-z_]+\(", p_txt):
            self.op_counts["method_sibling"] += 1
        if re.search(r"[+-]\s*1\b", p_txt) or re.search(r"[+-]\s*1\b", m_txt):
            self.op_counts["const_step"] += 1
        if len(plus_lines) < len(minus_lines):
            self.op_counts["stmt_delete"] += 1
        if any(c in p_txt for c in ("abs(", "len(", "int(", "str(", "list(", "set(")):
            self.op_counts["wrap_expr"] += 1

    def score(self, op_kind: str, on_exec_line: bool, on_exc_line: bool, ast_delta: int) -> float:
        base = self.DEFAULT_WEIGHTS.get(op_kind, 1.5)
        if self.total_examples > 0 and self.op_counts.get(op_kind, 0) > 0:
            base += 0.35 * math.log1p(self.op_counts[op_kind] / max(1.0, self.total_examples) * 10.0)
        if on_exc_line:
            base += 1.25
        elif on_exec_line:
            base += 0.65
        # Strong parsimony penalty (kills destructive multi-node overfits!)
        base -= 0.14 * max(0, ast_delta)
        return round(base, 4)

    def record_success(self, op_kind: str) -> None:
        self.op_counts[op_kind] += 2
        self.total_examples += 1


def _ast_fingerprint(src: str) -> str | None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return ast.dump(ast.parse(src), include_attributes=False)
    except SyntaxError:
        return None


def _is_clean_python(src: str) -> bool:
    """Reject syntactically invalid or SyntaxWarning-broken candidates in ~0.02 ms."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", SyntaxWarning)
            compile(src, "<chk>", "exec")
        return True
    except BaseException:
        return False


class PriorRepairEngine:
    """Trace-localized, prior-ranked AST candidate generator + FastCoWVerifier repair loop."""

    _CMP_ALTS: dict[type, tuple[type, ...]] = {
        ast.Lt: (ast.LtE, ast.Gt, ast.Eq, ast.GtE, ast.NotEq),
        ast.LtE: (ast.Lt, ast.GtE, ast.Eq, ast.Gt, ast.NotEq),
        ast.Gt: (ast.GtE, ast.Lt, ast.Eq, ast.LtE, ast.NotEq),
        ast.GtE: (ast.Gt, ast.LtE, ast.Eq, ast.Lt, ast.NotEq),
        ast.Eq: (ast.NotEq, ast.LtE, ast.GtE, ast.Lt, ast.Gt),
        ast.NotEq: (ast.Eq, ast.Lt, ast.Gt, ast.LtE, ast.GtE),
        ast.In: (ast.NotIn,),
        ast.NotIn: (ast.In,),
        ast.Is: (ast.IsNot,),
        ast.IsNot: (ast.Is,),
    }
    _BIN_ALTS: dict[type, tuple[type, ...]] = {
        ast.Add: (ast.Sub, ast.Mult),
        ast.Sub: (ast.Add, ast.Mult),
        ast.Mult: (ast.Add, ast.FloorDiv, ast.Div, ast.Pow),
        ast.Div: (ast.FloorDiv, ast.Mult, ast.Mod),
        ast.FloorDiv: (ast.Div, ast.Mod, ast.Mult),
        ast.Mod: (ast.FloorDiv, ast.Div),
        ast.Pow: (ast.Mult,),
        ast.BitAnd: (ast.BitOr, ast.BitXor),
        ast.BitOr: (ast.BitAnd, ast.BitXor),
        ast.BitXor: (ast.BitAnd, ast.BitOr),
        ast.LShift: (ast.RShift,),
        ast.RShift: (ast.LShift,),
    }

    def __init__(self, prior: GitASTPrior | None = None, lessons: Any = None) -> None:
        self.prior = prior or GitASTPrior()
        self.lessons = lessons  # optional canonical.runtime.edit_kind_learning_v1.Lessons

    def generate_candidates(
        self,
        source: str,
        executed_lines: set[int] | None = None,
        exc_line: int = 0,
        exc_type: str = "",
        without_lesson: str | None = None,
        max_candidates: int = 260,
    ) -> list[dict[str, Any]]:
        """Generate deduplicated, SyntaxWarning-free, prior-ranked AST repair candidates."""
        try:
            orig_tree = ast.parse(source)
        except SyntaxError:
            return []
        orig_fp = ast.dump(orig_tree, include_attributes=False)
        exec_l = executed_lines or set()
        syms = LiveIntrospector.scope_symbols(orig_tree)
        in_scope_vars = list(dict.fromkeys(syms["params"] + syms["locals"]))
        in_scope_funcs = list(dict.fromkeys(syms["funcs"] + syms["imports"]))

        seen_src: set[str] = {ast.unparse(orig_tree)}
        scored: list[dict[str, Any]] = []

        def emit(tree_obj: ast.AST, op_kind: str, lineno: int, delta: int = 1) -> None:
            try:
                cand_src = ast.unparse(tree_obj)
            except Exception:
                return
            if cand_src in seen_src:
                return
            seen_src.add(cand_src)
            sc = self.prior.score(
                op_kind,
                on_exec_line=(lineno in exec_l),
                on_exc_line=(exc_line > 0 and abs(lineno - exc_line) <= 1),
                ast_delta=delta,
            )
            scored.append({"source": cand_src, "op_kind": op_kind, "score": sc, "delta": delta, "lineno": lineno})

        # Collect mutable nodes with parent+field references in one single walk
        work = copy.deepcopy(orig_tree)
        # Skip docstring Expr(Constant(str)) nodes
        doc_ids: set[int] = set()
        for n in ast.walk(work):
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body:
                first = n.body[0]
                if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                    doc_ids.add(id(first))
                    doc_ids.add(id(first.value))
            if isinstance(n, ast.Module):
                for s in n.body:
                    if isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str):
                        doc_ids.add(id(s))
                        doc_ids.add(id(s.value))

        # Helper to replace child field cleanly and restore
        def try_replace(parent: ast.AST, field_name: str, idx: int | None, new_val: Any, op_kind: str, lineno: int, delta: int = 1) -> None:
            if idx is None:
                old = getattr(parent, field_name)
                setattr(parent, field_name, new_val)
                emit(work, op_kind, lineno, delta)
                setattr(parent, field_name, old)
            else:
                lst = getattr(parent, field_name)
                old = lst[idx]
                lst[idx] = new_val
                emit(work, op_kind, lineno, delta)
                lst[idx] = old

        # Walk parent -> child edges
        def visit(parent: ast.AST) -> None:
            for fname, val in ast.iter_fields(parent):
                if isinstance(val, ast.AST):
                    if id(val) not in doc_ids:
                        mutate_node(parent, fname, None, val)
                        visit(val)
                elif isinstance(val, list):
                    for idx in range(len(val)):
                        item = val[idx]
                        if isinstance(item, ast.AST) and id(item) not in doc_ids:
                            mutate_node(parent, fname, idx, item)
                            visit(item)
                    # Statement deletion for non-docstring statements inside function/loop bodies
                    if fname in ("body", "orelse") and isinstance(parent, (ast.FunctionDef, ast.If, ast.For, ast.While)) and len(val) >= 2:
                        for idx in range(len(val)):
                            stmt = val[idx]
                            if id(stmt) in doc_ids or isinstance(stmt, ast.Return):
                                continue
                            ln = getattr(stmt, "lineno", 0)
                            saved = val.pop(idx)
                            emit(work, "stmt_delete", ln, delta=3)
                            val.insert(idx, saved)

        def mutate_node(parent: ast.AST, fname: str, idx: int | None, node: ast.AST) -> None:
            ln = getattr(node, "lineno", 0)

            # 1. Compare operator swaps + operand swap
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
                old_op = node.ops[0]
                for alt in self._CMP_ALTS.get(type(old_op), ()):
                    node.ops[0] = alt()
                    emit(work, "cmp_swap", ln, delta=1)
                node.ops[0] = old_op
                # Swap left & comparator (e.g., `x in substring` -> `substring in x`)
                if isinstance(old_op, (ast.In, ast.NotIn, ast.Lt, ast.LtE, ast.Gt, ast.GtE)):
                    node.left, node.comparators[0] = node.comparators[0], node.left
                    emit(work, "operand_swap", ln, delta=1)
                    node.left, node.comparators[0] = node.comparators[0], node.left

            # 2. BinOp swaps + unwrap excess BinOp + operand swap
            elif isinstance(node, ast.BinOp):
                old_op = node.op
                for alt in self._BIN_ALTS.get(type(old_op), ()):
                    node.op = alt()
                    emit(work, "binop_swap", ln, delta=1)
                node.op = old_op
                if isinstance(old_op, (ast.Sub, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)):
                    node.left, node.right = node.right, node.left
                    emit(work, "operand_swap", ln, delta=1)
                    node.left, node.right = node.right, node.left
                # Unwrap excess logic (`number % 1.0 + 1.0` -> `number % 1.0`)
                try_replace(parent, fname, idx, node.left, "unwrap_expr", ln, delta=2)
                try_replace(parent, fname, idx, node.right, "unwrap_expr", ln, delta=2)
                # Wrap binary expr in abs() (e.g. `elem - elem2` -> `abs(elem - elem2)`)
                if isinstance(old_op, ast.Sub):
                    try_replace(parent, fname, idx, ast.Call(func=ast.Name(id="abs", ctx=ast.Load()), args=[node], keywords=[]), "wrap_expr", ln, delta=2)

            # 3. AugAssign (`+=` <-> `-=` <-> `*=` etc.)
            elif isinstance(node, ast.AugAssign):
                old_op = node.op
                for alt in self._BIN_ALTS.get(type(old_op), ()):
                    node.op = alt()
                    emit(work, "aug_assign_swap", ln, delta=1)
                node.op = old_op

            # 4. BoolOp (`and` <-> `or` + unwrap single branch)
            elif isinstance(node, ast.BoolOp):
                old_op = node.op
                node.op = ast.Or() if isinstance(old_op, ast.And) else ast.And()
                emit(work, "boolop_swap", ln, delta=1)
                node.op = old_op
                for sub in node.values:
                    try_replace(parent, fname, idx, sub, "unwrap_expr", ln, delta=2)

            # 5. UnaryOp (`not x` -> `x`, `-x` -> `x`)
            elif isinstance(node, ast.UnaryOp):
                if isinstance(node.op, (ast.Not, ast.USub, ast.UAdd)):
                    try_replace(parent, fname, idx, node.operand, "unary_toggle", ln, delta=1)

            # 6. If / While condition negation (`not cond`) + null-deref guard lift + `while True:` lift
            elif isinstance(node, (ast.If, ast.While)):
                old_t = node.test
                if not isinstance(old_t, ast.UnaryOp) or not isinstance(old_t.op, ast.Not):
                    node.test = ast.UnaryOp(op=ast.Not(), operand=old_t)
                    emit(work, "unary_toggle", ln, delta=1)
                    node.test = old_t
                # General null-dereference guard lift: `x.attr ...` -> `x is None or ...` / `x is not None and ...`
                deref_roots: list[ast.expr] = []
                for sub in ast.walk(old_t):
                    if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name):
                        if all(ast.dump(sub.value) != ast.dump(prev) for prev in deref_roots):
                            deref_roots.append(sub.value)
                for root_v in deref_roots[:2]:
                    node.test = ast.BoolOp(
                        op=ast.Or(),
                        values=[
                            ast.Compare(left=copy.deepcopy(root_v), ops=[ast.Is()], comparators=[ast.Constant(None)]),
                            old_t,
                        ],
                    )
                    emit(work, "null_guard", ln, delta=2)
                    node.test = ast.BoolOp(
                        op=ast.And(),
                        values=[
                            ast.Compare(left=copy.deepcopy(root_v), ops=[ast.IsNot()], comparators=[ast.Constant(None)]),
                            old_t,
                        ],
                    )
                    emit(work, "null_guard", ln, delta=2)
                    node.test = old_t
                # `while True:` -> `while <in-scope var>:`
                if isinstance(node, ast.While) and isinstance(old_t, ast.Constant) and old_t.value is True:
                    for v in in_scope_vars[:6]:
                        node.test = ast.Name(id=v, ctx=ast.Load())
                        emit(work, "truth_lift", ln, delta=1)
                    node.test = old_t

            # 6b. Return constant lifting (`return True/False` -> `return v == 0` / `not v`; `return []` -> `return [v]`)
            elif isinstance(node, ast.Return) and node.value is not None:
                old_r = node.value
                if isinstance(old_r, ast.Constant) and isinstance(old_r.value, bool):
                    for v in in_scope_vars[:5]:
                        node.value = ast.Compare(left=ast.Name(id=v, ctx=ast.Load()), ops=[ast.Eq()], comparators=[ast.Constant(0)])
                        emit(work, "truth_lift", ln, delta=2)
                        node.value = ast.UnaryOp(op=ast.Not(), operand=ast.Name(id=v, ctx=ast.Load()))
                        emit(work, "truth_lift", ln, delta=2)
                    node.value = old_r
                elif isinstance(old_r, ast.List) and len(old_r.elts) == 0:
                    for v in in_scope_vars[:4]:
                        node.value = ast.List(elts=[ast.Name(id=v, ctx=ast.Load())], ctx=ast.Load())
                        emit(work, "truth_lift", ln, delta=1)
                    node.value = old_r

            # 7. Constants (int ±1, 0<->1, -1; bool flip; '' <-> ' ')
            elif isinstance(node, ast.Constant):
                v = node.value
                if isinstance(v, bool):
                    node.value = not v
                    emit(work, "const_flip", ln, delta=1)
                    node.value = v
                elif isinstance(v, int):
                    alts = [v + 1, v - 1]
                    if v == 0:
                        alts.extend([-1, 2])
                    elif v == 1:
                        alts.extend([-1, 2])
                    elif v == -1:
                        alts.extend([0, 1])
                    seen_v = {v}
                    for a in alts:
                        if a not in seen_v:
                            seen_v.add(a)
                            node.value = a
                            emit(work, "const_step", ln, delta=1)
                    node.value = v
                elif isinstance(v, str) and len(v) <= 2:
                    for a in ("", " ", "\n", ",", "0", "1"):
                        if a != v and (len(v) <= 1 or a in ("", " ")):
                            node.value = a
                            emit(work, "const_flip", ln, delta=1)
                    node.value = v

            # 8. Job-1 Call: method sibling swap, function sibling swap, range off-by-one, unwrap call
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    old_attr = node.func.attr
                    for sib in LiveIntrospector.sibling_methods(old_attr):
                        node.func.attr = sib
                        emit(work, "method_sibling", ln, delta=1)
                    node.func.attr = old_attr
                    # Unwrap 0-arg method call (`x.lower()` -> `x`)
                    if not node.args and not node.keywords:
                        try_replace(parent, fname, idx, node.func.value, "unwrap_expr", ln, delta=2)
                elif isinstance(node.func, ast.Name):
                    fn_name = node.func.id
                    for sib in LiveIntrospector.sibling_functions(fn_name, in_scope_funcs):
                        node.func.id = sib
                        emit(work, "func_sibling", ln, delta=1)
                    node.func.id = fn_name
                    # range(n) -> range(n+1), range(n-1), range(1, n+1); range(a, b) -> range(a, b+1)
                    if fn_name == "range" and node.args:
                        if len(node.args) == 1:
                            a0 = node.args[0]
                            for d_op in (ast.Add, ast.Sub):
                                node.args[0] = ast.BinOp(left=a0, op=d_op(), right=ast.Constant(1))
                                emit(work, "range_bound", ln, delta=2)
                            node.args = [ast.Constant(1), ast.BinOp(left=a0, op=ast.Add(), right=ast.Constant(1))]
                            emit(work, "range_bound", ln, delta=3)
                            node.args = [a0]
                        elif len(node.args) == 2:
                            a0, a1 = node.args
                            for d_op in (ast.Add, ast.Sub):
                                node.args[1] = ast.BinOp(left=a1, op=d_op(), right=ast.Constant(1))
                                emit(work, "range_bound", ln, delta=2)
                            node.args[1] = a1
                            for d_op in (ast.Add, ast.Sub):
                                node.args[0] = ast.BinOp(left=a0, op=d_op(), right=ast.Constant(1))
                                emit(work, "range_bound", ln, delta=2)
                            node.args[0] = a0
                    # Unwrap single-arg call (`abs(x)` -> `x`, `int(x)` -> `x`)
                    if len(node.args) == 1 and not node.keywords:
                        try_replace(parent, fname, idx, node.args[0], "unwrap_expr", ln, delta=2)
                # General call argument permutation (`f(a, b)` -> `f(b, a)` for 2-3 positional args)
                if 2 <= len(node.args) <= 3 and not node.keywords:
                    orig_args = list(node.args)
                    for i_a in range(len(orig_args)):
                        for j_a in range(i_a + 1, len(orig_args)):
                            node.args[i_a], node.args[j_a] = orig_args[j_a], orig_args[i_a]
                            emit(work, "arg_perm", ln, delta=1)
                            node.args[i_a], node.args[j_a] = orig_args[i_a], orig_args[j_a]

            # 9. Subscript / Slice off-by-one + reverse slice
            elif isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load):
                sl = node.slice
                if isinstance(sl, ast.Slice):
                    for sf in ("lower", "upper"):
                        cur = getattr(sl, sf)
                        if cur is not None:
                            for d_op in (ast.Add, ast.Sub):
                                setattr(sl, sf, ast.BinOp(left=cur, op=d_op(), right=ast.Constant(1)))
                                emit(work, "slice_bound", ln, delta=2)
                            setattr(sl, sf, cur)
                elif isinstance(sl, ast.Constant) and isinstance(sl.value, int):
                    old_i = sl.value
                    for a in (old_i + 1, old_i - 1, -1, 0):
                        if a != old_i:
                            sl.value = a
                            emit(work, "slice_bound", ln, delta=1)
                    sl.value = old_i
                else:
                    for d_op in (ast.Add, ast.Sub):
                        node.slice = ast.BinOp(left=sl, op=d_op(), right=ast.Constant(1))
                        emit(work, "slice_bound", ln, delta=2)
                    node.slice = sl

            # 10. Job-1 Variable swap + wrap expression (Load names & Store targets)
            elif isinstance(node, ast.Name) and node.id in in_scope_vars:
                old_id = node.id
                if isinstance(node.ctx, ast.Load) and not (isinstance(parent, ast.Call) and fname == "func"):
                    for other in in_scope_vars:
                        if other != old_id:
                            node.id = other
                            emit(work, "var_swap", ln, delta=1)
                    node.id = old_id
                    # Common missing wrappers: len(v), abs(v), v.lower(), v + 1, v - 1
                    for wfn in ("len", "abs", "int", "float", "str", "sorted", "set"):
                        try_replace(parent, fname, idx, ast.Call(func=ast.Name(id=wfn, ctx=ast.Load()), args=[node], keywords=[]), "wrap_expr", ln, delta=2)
                    for wm in _WRAP_METHODS:
                        try_replace(parent, fname, idx, ast.Call(func=ast.Attribute(value=node, attr=wm, ctx=ast.Load()), args=[], keywords=[]), "wrap_expr", ln, delta=2)
                    # Trace-localized off-by-one (`v + 1`, `v - 1`) & in-scope binary/slice completion
                    if not executed_lines or ln in executed_lines:
                        if not isinstance(parent, ast.Subscript) or fname != "slice":
                            for d_op in (ast.Add, ast.Sub):
                                try_replace(parent, fname, idx, ast.BinOp(left=node, op=d_op(), right=ast.Constant(1)), "expr_off_by_one", ln, delta=2)
                        if len(in_scope_vars) <= 8:
                            for other in in_scope_vars:
                                if other == old_id:
                                    continue
                                oth_n = ast.Name(id=other, ctx=ast.Load())
                                try_replace(parent, fname, idx, ast.BinOp(left=node, op=ast.Sub(), right=oth_n), "var_binop_slice", ln, delta=2)
                                try_replace(parent, fname, idx, ast.BinOp(left=node, op=ast.Add(), right=oth_n), "var_binop_slice", ln, delta=2)
                                if isinstance(parent, (ast.For, ast.Call, ast.Return, ast.Assign)):
                                    try_replace(parent, fname, idx, ast.Subscript(value=node, slice=ast.Slice(lower=oth_n, upper=None, step=None), ctx=ast.Load()), "var_binop_slice", ln, delta=2)
                                    try_replace(parent, fname, idx, ast.Subscript(value=node, slice=ast.Slice(lower=None, upper=oth_n, step=None), ctx=ast.Load()), "var_binop_slice", ln, delta=2)
                elif isinstance(node.ctx, ast.Store) and isinstance(parent, (ast.AugAssign, ast.Assign)):
                    for other in in_scope_vars:
                        if other != old_id:
                            node.id = other
                            emit(work, "var_swap", ln, delta=1)
                    node.id = old_id

            # 11. Excess literal element in small List/Tuple/Set (e.g. extra vowel "w", "y")
            elif isinstance(node, (ast.List, ast.Tuple, ast.Set)) and 2 <= len(node.elts) <= 10:
                if all(isinstance(e, ast.Constant) for e in node.elts):
                    for k in range(len(node.elts)):
                        saved = node.elts.pop(k)
                        emit(work, "elem_drop", ln, delta=2)
                        node.elts.insert(k, saved)

        visit(work)

        # 12. Symmetric dual-swap (e.g., all '0'<->'1', floor<->ceil, True<->False in one move!)
        for a_tok, b_tok in (("floor", "ceil"), ("True", "False"), ("'0'", "'1'"), ('"0"', '"1"'), ("min", "max")):
            if a_tok in source and b_tok in source:
                sentinel = "__DUAL_SWAP_SENTINEL__"
                swapped = source.replace(a_tok, sentinel).replace(b_tok, a_tok).replace(sentinel, b_tok)
                if swapped not in seen_src:
                    seen_src.add(swapped)
                    scored.append({"source": swapped, "op_kind": "dual_swap", "score": self.prior.score("dual_swap", True, False, 2), "delta": 2, "lineno": 0})

        # 13. Merge optional learned operators from edit_kind_learning_v1.Lessons (only top-40 fast!)
        if self.lessons is not None:
            for prop in self.lessons.proposals(source, without=((without_lesson,) if without_lesson else ()), limit=40):
                psrc = prop["source"]
                if psrc not in seen_src:
                    seen_src.add(psrc)
                    scored.append({
                        "source": psrc,
                        "op_kind": "learned_lesson",
                        "score": self.prior.score("learned_lesson", True, False, 2) + min(1.5, float(prop.get("score", 0.0))),
                        "delta": 2,
                        "lineno": 0,
                    })

        scored.sort(key=lambda r: (-r["score"], r["delta"], len(r["source"])))
        # Filter SyntaxWarning / invalid candidates lazily ONLY on the top slice!
        clean: list[dict[str, Any]] = []
        for row in scored:
            if _is_clean_python(row["source"]):
                clean.append(row)
                if len(clean) >= max_candidates:
                    break
        return clean

    def repair(
        self,
        source: str,
        test_code: str,
        *,
        entry_point: str = "",
        docstring: str | None = None,
        use_doctests: bool = False,
        without_lesson: str | None = None,
        max_candidates: int = 200,
        collect_passing: int = 6,
        timeout_s: float = 0.25,
    ) -> dict[str, Any]:
        """Full Jobs 1+3+4a+5a repair loop: localize -> generate -> fast fork CoW -> anti-overfit pick."""
        t0 = time.perf_counter()
        loc = FastCoWVerifier.localize_failure(source, test_code, timeout_s=timeout_s)
        extra_spec = SpecExtractor.doctest_assertions(source, entry_point, docstring=docstring) if (use_doctests and entry_point) else ""
        # Only enforce extracted doctests if they aren't trivially broken on syntax
        cands = self.generate_candidates(
            source,
            executed_lines=loc["executed_lines"],
            exc_line=loc["exc_line"],
            exc_type=loc["exc_type"],
            without_lesson=without_lesson,
            max_candidates=max_candidates,
        )
        tested = 0
        passing: list[dict[str, Any]] = []
        for cand in cands:
            tested += 1
            res = FastCoWVerifier.run_isolated(cand["source"], test_code, timeout_s=timeout_s)
            if res.passed:
                spec_ok = True
                if extra_spec:
                    spec_ok = FastCoWVerifier.run_isolated(cand["source"], extra_spec, timeout_s=timeout_s).passed
                cand_rec = dict(cand)
                cand_rec["spec_ok"] = spec_ok
                passing.append(cand_rec)
                # Stop early once we have enough verified candidates to rank cleanly against overfits!
                if len(passing) >= collect_passing or (spec_ok and extra_spec and len(passing) >= 2):
                    break

        best = None
        if passing:
            # Anti-overfit selector: spec_ok first, then smallest AST delta, then highest prior score!
            passing.sort(key=lambda r: (0 if r["spec_ok"] else 1, r["delta"], -r["score"], len(r["source"])))
            best = passing[0]
            self.prior.record_success(best["op_kind"])

        return {
            "fixed": best is not None,
            "source": best["source"] if best else None,
            "op_kind": best["op_kind"] if best else None,
            "candidates_generated": len(cands),
            "candidates_tested": tested,
            "passing_candidates": len(passing),
            "used_extra_spec": bool(extra_spec),
            "exc_type": loc["exc_type"],
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }


# =============================================================================
# OPTIONAL JOB 4b / 5b HOOK: STRICTLY OPT-IN LOCAL llama.cpp MICRO-MODEL CLIENT
# =============================================================================
class LocalMicroModelBackend:
    """Strictly opt-in loopback client for a local quantized llama.cpp / OpenAI-compatible server.

    - Zero external dependencies (stdlib urllib.request only).
    - Disabled by default (`BRAIN_LOCAL_LLM_ENDPOINT` unset -> `enabled == False`, 0 calls).
    - Loopback-only guard (`127.0.0.1` / `localhost` / `[::1]` only) so no cloud API call
      can ever be issued accidentally.
    - Every proposed patch must still pass `FastCoWVerifier` before admission.
    """

    _LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})

    def __init__(
        self,
        endpoint: Optional[str] = None,
        *,
        model: Optional[str] = None,
        timeout_s: float = 15.0,
    ) -> None:
        raw = (endpoint if endpoint is not None else os.environ.get("BRAIN_LOCAL_LLM_ENDPOINT", "")).strip()
        self.endpoint = raw
        self.model = (model if model is not None else os.environ.get("BRAIN_LOCAL_LLM_MODEL", "local-micro-coder")).strip()
        self.timeout_s = float(timeout_s)
        self.calls = 0
        self.enabled = self._is_valid_loopback(raw)

    @classmethod
    def _is_valid_loopback(cls, url: str) -> bool:
        if not url:
            return False
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.scheme in ("http", "https") and (parsed.hostname or "").lower() in cls._LOOPBACK_HOSTS
        except Exception:
            return False

    def propose_python_patches(
        self,
        source: str,
        issue_or_error: str,
        *,
        n_samples: int = 4,
        max_tokens: int = 512,
    ) -> list[str]:
        """Request candidate full-function/file patches from a local llama.cpp endpoint.

        Returns `[]` immediately (with 0 calls) whenever no local loopback endpoint is configured.
        """
        if not self.enabled:
            return []
        import urllib.request

        prompt = (
            "Fix the Python bug described below. Return ONLY valid Python source code inside "
            "a single ```python ... ``` block with no extra commentary.\n\n"
            f"Issue/Error:\n{issue_or_error[:1500]}\n\nSource:\n```python\n{source[:6000]}\n```\n"
        )
        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "n": max(1, min(8, int(n_samples))),
            "temperature": 0.4,
            "max_tokens": int(max_tokens),
        }).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            self.calls += 1
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception:
            return []
        out: list[str] = []
        seen: set[str] = set()
        for ch in list(data.get("choices") or []):
            content = str(((ch.get("message") or {}).get("content")) or ch.get("text") or "")
            m = re.search(r"```(?:python)?\s*\n(.*?)```", content, re.DOTALL)
            cand = (m.group(1) if m else content).strip() + "\n"
            if cand and cand != source and cand not in seen:
                try:
                    ast.parse(cand)
                except SyntaxError:
                    continue
                seen.add(cand)
                out.append(cand)
        return out

