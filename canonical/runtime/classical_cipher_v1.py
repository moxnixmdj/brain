#!/usr/bin/env python3
"""Classical substitution-cipher analysis for arbitrary environments.

WHY THIS EXISTS
---------------
`terminal-bench-4/interleaved-vigenere` needs a deterministic, zero-model
attack on a polyalphabetic substitution specimen placed in /app. Building the
attack for that one benchmark item would be hand-solving the test, which
violates Brain integrity. This module is therefore written as a *general*
capability, admitted only on unseen victims (see admission()), from the
public classical-cryptanalysis literature:

  * index of coincidence (Friedman 1922)      -- mono- vs polyalphabetic
  * Kasiski examination (1863)                -- period candidates
  * per-column chi-squared (Friedman)         -- per-column shift recovery
  * coordinate-ascent over columns, scored by a derived bigram log-likelihood
  * model classes: Vigenere (straight), Beaufort, and two interleaved
    Vigenere streams (alternating letter positions, independent periods)

The English statistics are NOT parameters and NOT a model. They live in
`language_statistics_en_v1.json`, an inspectable store file derived from
this repository's own markdown prose (provenance inside the file), and the
emitted cracker artifact embeds the same tables as data. Delete the file
and the capability degrades honestly to uniform priors.

Verification criteria, from first principles, weakest to strongest:
  1. RC != 0 refused.
  2. Index of coincidence of recovered plaintext approaches English (~0.066).
  3. Bigram log-likelihood of recovered plaintext beats every competing
     candidate by an explicit margin.
  4. zlib compression ratio of the recovered plaintext beats the ciphertext
     (a knowledge-free redundancy oracle -- works even with tables deleted).

Model calls: 0. Network at decision time: 0. Everything is computed.
Authority: NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT.
"""
from __future__ import annotations

import json
import math
import pathlib
import string
import zlib
from typing import Any, Mapping

SCHEMA = "BRAIN_CLASSICAL_CIPHER_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
_STATS_PATH = pathlib.Path(__file__).resolve().parent / "language_statistics_en_v1.json"

_A = 65
_ALPH = string.ascii_uppercase


def _letters(text: str) -> str:
    return "".join(ch for ch in text.upper() if ch in _ALPH)


def load_stats(path: str | pathlib.Path | None = None) -> dict[str, Any]:
    p = pathlib.Path(path) if path else _STATS_PATH
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"monogram": {c: 1.0 / 26 for c in _ALPH}, "bigram": {},
                "refused": f"STATS_UNAVAILABLE:{p.name}:{type(exc).__name__}"}
    return data


def ioc(text: str) -> float:
    t = _letters(text)
    n = len(t)
    if n < 2:
        return 0.0
    counts = [t.count(c) for c in _ALPH]
    return sum(c * (c - 1) for c in counts) / (n * (n - 1))


def _log_mono(stats: Mapping[str, Any]) -> dict[str, float]:
    m = stats.get("monogram") or {}
    return {c: math.log(max(float(m.get(c, 1.0 / 26)), 1e-9)) for c in _ALPH}


def _log_bigram(stats: Mapping[str, Any]) -> dict[str, float]:
    bg = stats.get("bigram") or {}
    floor = float(stats.get("bigram_floor", 1e-9))
    table = {k: math.log(max(float(v), floor)) for k, v in bg.items()}
    return table | {"_default": math.log(floor)}


def _score_text(t: str, lmono: Mapping[str, float], lbg: Mapping[str, Any]) -> float:
    """Log-likelihood of a letter stream. Higher is better."""
    t = _letters(t)
    if not t:
        return -1e18
    default = float(lbg.get("_default")) if lbg.get("_default") is not None else math.log(1e-9)
    s = sum(lmono[c] for c in t) * 0.15  # weak mono prior, guards degenerate keys
    prev = t[0]
    for cur in t[1:]:
        pair = prev + cur
        v = lbg.get(pair)
        s += float(v) if v is not None else default
        prev = cur
    return s


def _chi2_column(column: str) -> list[float]:
    """Return 26 scores (higher better): log-likelihood of the column under each shift."""
    counts = [column.count(c) for c in _ALPH]
    total = max(len(column), 1)
    # Friedman: shift s aligns cipher letter c with plain letter (c - s).
    scores = []
    for s in range(26):
        sc = 0.0
        for c_i, c in enumerate(_ALPH):
            n = counts[c_i]
            if n:
                p = _EN_FREQ[(c_i - s) % 26]
                sc += n * math.log(p)
        scores.append(sc)
    return scores


# Friedman monogram frequencies (public, standard tables) used only inside chi-squared
# seeding; the store file carries the derived statistics of record.
_EN_FREQ = [0.08167, 0.01492, 0.02782, 0.04253, 0.12702, 0.02228, 0.02015, 0.06094,
            0.06966, 0.00153, 0.00772, 0.04025, 0.02406, 0.06749, 0.07507, 0.01929,
            0.00095, 0.05987, 0.06327, 0.09056, 0.02758, 0.00978, 0.02360, 0.00150,
            0.01974, 0.00074]


def _break_vigenere(t: str, lmono: Mapping[str, float], lbg: Mapping[str, Any],
                    max_period: int, transform: str = "straight") -> list[dict[str, Any]]:
    """Return candidate decryptions sorted by score (best first)."""
    n = len(t)
    out: list[dict[str, Any]] = []

    def apply(text: str, key: str) -> str:
        res = []
        for i, ch in enumerate(text):
            p = ord(ch) - _A
            k = ord(key[i % len(key)]) - _A
            if transform == "straight":
                c = (p - k) % 26
            elif transform == "beaufort":
                c = (k - p) % 26
            else:  # variant_beaufort
                c = (p + k) % 26
            res.append(_ALPH[c])
        return "".join(res)

    # Cheap full-spectrum pass: monogram-seeded keys for EVERY period, scored by bigram.
    # (No reliance on chi-squared seed order; seeds are only a starting point.)
    harvest: list[dict[str, Any]] = []
    for k in range(1, min(max_period, max(2, n // 6)) + 1):
        cols = [t[i::k] for i in range(k)]
        key_shifts = []
        for col in cols:
            sc = _chi2_column(col)
            key_shifts.append(sc.index(max(sc)))
        key = "".join(_ALPH[x] for x in key_shifts)
        plain = apply(t, key)
        harvest.append({"variant": f"vigenere_{transform}", "key": key, "period": k,
                        "plaintext": plain, "score": _score_text(plain, lmono, lbg)})
    for cand in harvest:
        cand["zlib_bytes"] = len(zlib.compress(cand["plaintext"].encode()))
    # Keep the global top seeds: both by score and by knowledge-free zlib redundancy.
    by_score = sorted(harvest, key=lambda c: -c["score"])[:3]
    by_zlib = sorted(harvest, key=lambda c: (c["zlib_bytes"], -c["score"]))[:3]
    refine_set: list[dict[str, Any]] = []
    seen_keys = set()
    for cand in by_score + by_zlib:
        if cand["key"] not in seen_keys:
            seen_keys.add(cand["key"])
            refine_set.append(cand)
    for cand in refine_set:
        k = cand["period"]
        cols = [t[i::k] for i in range(k)]
        key_shifts = [ord(c) - _A for c in cand["key"]]
        for _ in range(2):
            for j in range(k):
                probe = key_shifts.copy()
                best_full, best_shift = None, key_shifts[j]
                for s in range(26):
                    probe[j] = s
                    p = apply(t, "".join(_ALPH[x] for x in probe))
                    sc = _score_text(p, lmono, lbg)
                    if best_full is None or sc > best_full:
                        best_full, best_shift = sc, s
                key_shifts[j] = best_shift
        key = "".join(_ALPH[x] for x in key_shifts)
        plain = apply(t, key)
        out.append({"variant": f"vigenere_{transform}", "key": key, "period": k,
                    "plaintext": plain,
                    "score": _score_text(plain, lmono, lbg),
                    "zlib_bytes": len(zlib.compress(plain.encode()))})
    # Also return the raw harvest champions (unrefined) so the caller's zlib
    # arbiter sees every promising basin, not just the refined few.
    out.extend(sorted(harvest, key=lambda c: (c["zlib_bytes"], -c["score"]))[:6])
    out.sort(key=lambda c: (c.get("zlib_bytes") or 10**9, -c["score"]))
    return out


def zlib_margin_hint(cands: list[dict[str, Any]]) -> int:
    if not cands:
        return 0
    best_plain = cands[0].get("plaintext")
    runner = next((c for c in cands[1:] if c.get("plaintext") != best_plain), None)
    if runner is None:
        return 10**9
    return int(runner.get("zlib_bytes", 10**9)) - int(cands[0].get("zlib_bytes", 10**9))


def crack(text: str, *, max_period: int = 40, stats_path: str | pathlib.Path | None = None) -> dict[str, Any]:
    """Crack a classical substitution specimen. Never guesses blindly: reports every tried family."""
    t = _letters(text)
    stats = load_stats(stats_path)
    lmono = _log_mono(stats)
    lbg = _log_bigram(stats)
    candidates: list[dict[str, Any]] = []
    t_ioc = ioc(t)
    # Model class 1 & 2: single straight/Beaufort stream
    for transform in ("straight", "beaufort"):
        candidates.extend(_break_vigenere(t, lmono, lbg, max_period, transform))
    # Model class 3: N interleaved streams (stride s = letter index mod s), independent periods.
    for stride in (2, 3, 4, 5, 6):
        streams = [t[i::stride] for i in range(stride)]
        if min(len(s) for s in streams) < 60:
            continue
        sub = []
        for s in streams:
            stream_cands = _break_vigenere(s, lmono, lbg, min(max_period, 30), "straight")
            stream_cands.sort(key=lambda c: (c.get("zlib_bytes") or 10**9, -c["score"]))
            sub.append(stream_cands[:3])
        import itertools
        trials = []
        for combo in itertools.product(*sub):
            joined = []
            streams_plain = [c["plaintext"] for c in combo]
            for pos in range(len(t)):
                si = pos % stride
                j = pos // stride
                joined.append(streams_plain[si][j] if j < len(streams_plain[si]) else "")
            trials.append((combo, "".join(joined)))
        trials.sort(key=lambda x: len(zlib.compress(x[1].encode())))
        for combo, plain in trials[:8]:
            candidates.append({
                "variant": f"interleaved{stride}",
                "key": "|".join(c["key"] for c in combo),
                "period": "|".join(str(c["period"]) for c in combo),
                "plaintext": plain,
                "score": _score_text(plain, lmono, lbg)})
    ct_compressed = zlib.compress(t.encode())
    for c in candidates:
        c["zlib_bytes"] = len(zlib.compress(c["plaintext"].encode()))
    candidates.sort(key=lambda c: (c["zlib_bytes"], -c["score"]))
    top_diag = [{"variant": c.get("variant"), "zlib_bytes": c.get("zlib_bytes"),
                 "score": round(c.get("score", 0.0), 1)} for c in candidates[:5]]
    best = candidates[0] if candidates else None
    best_by_score = max(candidates, key=lambda c: c["score"]) if candidates else None
    # True confidence discriminator: the runner-up with a DIFFERENT plaintext.
    # (Equivalent-key twins tie at zero and would falsely read as "no margin".)
    best_plain = (best or {}).get("plaintext")
    second = next((c for c in candidates[1:] if c.get("plaintext") != best_plain), None)
    margin = (best["score"] - second["score"]) if (best and second) else None
    zlib_margin = ((second["zlib_bytes"] - best["zlib_bytes"])
                   if (best and second) else None)
    compressed = zlib.compress((best["plaintext"] if best else "").encode())
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "status": "CRACKED" if best else "NO_CANDIDATE",
        "ioc_ciphertext": round(t_ioc, 4),
        "best": best,
        "margin_vs_runner_up": margin,
        "zlib_margin_vs_runner_up": zlib_margin,
        "best_by_score_variant": (best_by_score or {}).get("variant"),
        "best_by_score_key": (best_by_score or {}).get("key"),
        "zlib_bytes_plaintext": len(compressed),
        "zlib_bytes_ciphertext": len(ct_compressed),
        "compressibility_verdict": ("PLAINTEXT_COMPRESSES_BETTER"
                                     if best and len(compressed) < len(ct_compressed)
                                     else "NO_COMPRESSION_GAIN"),
        "confidence": ("HIGH" if zlib_margin_hint(candidates) >= 10 else
                       ("LOW" if candidates else "NONE")),
        "top_candidates_by_zlib": top_diag,
        "candidates_tried": len(candidates),
        "stats_refused": stats.get("refused"),
        "model_calls": 0,
        "parameters_stored": 0,
    }


# --------------------------------------------------------------------------- #
# artifact emission: a self-contained cracker Brain can leave in the environment
# --------------------------------------------------------------------------- #
_CRACKER_TEMPLATE = '''#!/usr/bin/env python3
"""Self-contained classical-cipher cracker (Vigenere/Beaufort/interleaved Vigenere).
Usage: python3 cracker.py [ciphertext_file]  (or stdin). Prints plaintext to stdout."""
import sys, math, zlib, string
ENG_MONO = __MONO_LITERAL__
ENG_BIGRAM = __BIGRAM_LITERAL__
ALPH = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
EN_FREQ = __EN_FREQ_LITERAL__

def ioc(t):
    n = len(t)
    if n < 2: return 0.0
    counts = [t.count(c) for c in ALPH]
    return sum(c*(c-1) for c in counts)/(n*(n-1))

def score(t):
    s = sum(ENG_MONO[c] for c in t)*0.15
    m = ENG_BIGRAM
    mono = ENG_MONO
    prev = t[0]
    for cur in t[1:]:
        logp = m.get(prev+cur)
        s += logp if logp is not None else (mono[prev] + mono[cur])*0.5
        prev = cur
    return s

def chi2col(col):
    counts = [col.count(c) for c in ALPH]
    out = []
    for s in range(26):
        sc = 0.0
        for i in range(26):
            if counts[i]:
                sc += counts[i]*math.log(EN_FREQ[(i-s) % 26])
        out.append(sc)
    return out

def apply_key(t, key, transform):
    res = []
    for i, ch in enumerate(t):
        p = ord(ch)-65; k = ord(key[i % len(key)])-65
        if transform == "straight": c = (p-k) % 26
        elif transform == "beaufort": c = (k-p) % 26
        else: c = (p+k) % 26
        res.append(ALPH[c])
    return "".join(res)

def break_vig(t, max_period, transform):
    n = len(t)
    cands = []
    harvest = []
    for k in range(1, min(max_period, max(2, n//6))+1):
        cols = [t[i::k] for i in range(k)]
        shifts = []
        for c in cols:
            if not c:
                shifts.append(0); continue
            sc = chi2col(c)
            shifts.append(sc.index(max(sc)))
        key = "".join(ALPH[x] for x in shifts)
        plain = apply_key(t, key, transform)
        harvest.append({"variant": "vigenere_"+transform, "key": key, "score": score(plain), "plaintext": plain})
    for cand in harvest:
        cand["zlib_bytes"] = len(zlib.compress(cand["plaintext"].encode()))
    by_score = sorted(harvest, key=lambda c: -c["score"])[:3]
    by_zlib = sorted(harvest, key=lambda c: (c["zlib_bytes"], -c["score"]))[:3]
    refine, seen = [], set()
    for cand in by_score + by_zlib:
        if cand["key"] not in seen:
            seen.add(cand["key"])
            refine.append(cand)
    for cand in refine:
        k = len(cand["key"])
        shifts = [ord(c)-65 for c in cand["key"]]
        for _ in range(2):
            for j in range(k):
                probe = shifts.copy()
                best = (None, shifts[j])
                for s in range(26):
                    probe[j] = s
                    sc = score(apply_key(t, "".join(ALPH[x] for x in probe), transform))
                    if best[0] is None or sc > best[0]:
                        best = (sc, s)
                shifts[j] = best[1]
        key = "".join(ALPH[x] for x in shifts)
        plain = apply_key(t, key, transform)
        cands.append({"variant": "vigenere_"+transform, "key": key, "score": score(plain),
                      "plaintext": plain, "zlib_bytes": len(zlib.compress(plain.encode()))})
    cands.extend(sorted(harvest, key=lambda c: (c["zlib_bytes"], -c["score"]))[:6])
    cands.sort(key=lambda c: (c.get("zlib_bytes") or 10**9, -c["score"]))
    return cands

def crack(t):
    cands = []
    for tr in ("straight", "beaufort"):
        cands += break_vig(t, 40, tr)
    import itertools
    for stride in (2, 3, 4, 5, 6):
        streams = [t[i::stride] for i in range(stride)]
        if min(len(s) for s in streams) < 60:
            continue
        sub = []
        for s in streams:
            sub.append(break_vig(s, 30, "straight")[:3])
        trials = []
        for combo in itertools.product(*sub):
            joined = []
            sp = [c["plaintext"] for c in combo]
            for pos in range(len(t)):
                si = pos % stride
                j = pos // stride
                joined.append(sp[si][j] if j < len(sp[si]) else "")
            plain = "".join(joined)
            trials.append((combo, plain))
        trials.sort(key=lambda x: len(zlib.compress(x[1].encode())))
        for combo, plain in trials[:8]:
            cands.append({"variant": "interleaved" + str(stride),
                          "key": "|".join(c["key"] for c in combo),
                          "score": score(plain), "plaintext": plain})
    for c in cands:
        c["zlib_bytes"] = len(zlib.compress(c["plaintext"].encode()))
    cands.sort(key=lambda c: (c["zlib_bytes"], -c["score"]))
    return cands[0] if cands else None

def main():
    if len(sys.argv) > 1:
        raw = open(sys.argv[1], "rb").read().decode("utf-8", errors="ignore")
    else:
        raw = sys.stdin.read()
    t = "".join(ch for ch in raw.upper() if ch in ALPH)
    best = crack(t)
    if best:
        sys.stdout.write(best["plaintext"] + "\\n")
    else:
        sys.stdout.write("")
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''


def emit_cracker(destination: str | pathlib.Path, *, stats_path: str | pathlib.Path | None = None) -> dict[str, Any]:
    """Write a self-contained cracker artifact (plain data tables, no dependencies)."""
    stats = load_stats(stats_path)
    mono = {c: round(math.log(max(float(v), 1e-9)), 6) for c, v in (stats.get("monogram") or {}).items()}
    bg = {k: round(math.log(max(float(v), 1e-9)), 6) for k, v in (stats.get("bigram") or {}).items()}
    content = (_CRACKER_TEMPLATE
               .replace("__MONO_LITERAL__", repr(mono))
               .replace("__BIGRAM_LITERAL__", repr(bg))
               .replace("__EN_FREQ_LITERAL__", repr(_EN_FREQ)))
    dest = pathlib.Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.chmod(0o700)
    tmp.replace(dest)
    return {"schema": SCHEMA, "authority": AUTHORITY, "status": "ARTIFACT_WRITTEN",
            "path": str(dest), "bytes": dest.stat().st_size,
            "tables_embedded": {"monogram": len(mono), "bigram": len(bg)},
            "model_calls": 0, "parameters_stored": 0}


def admission(victims: list[dict[str, Any]]) -> dict[str, Any]:
    """Admission harness: attack specimens produced by an INDEPENDENT generator.

    `victims`: list of {name, plaintext (letters), variant, period, key}. The caller is
    responsible for generating victims from real English prose with known answers;
    this function measures exact key and exact plaintext recovery and refuses if
    recovery is weak. A rule admitted here must be re-verified on new victims.
    """
    results = []
    recovered_key = 0
    recovered_plain = 0
    for v in victims:
        pt = _letters(v["plaintext"])
        ct = encrypt(pt, v["variant"], str(v["key"]))
        out = crack(ct)
        best = out.get("best") or {}
        plain_ok = best.get("plaintext") == pt
        best_key_norm = str(best.get("key", "")).split("|")
        truth_key_norm = str(v["key"]).split("|")
        key_ok = plain_ok or [k.upper() for k in best_key_norm] == [k.upper() for k in truth_key_norm]
        recovered_key += int(bool(key_ok))
        recovered_plain += int(bool(plain_ok))
        results.append({"name": v.get("name"), "variant": v.get("variant"),
                        "expected_key": str(v["key"]), "recovered_key": best.get("key"),
                        "plaintext_exact": bool(plain_ok), "ioc_ciphertext": out.get("ioc_ciphertext")})
    n = len(victims)
    return {"schema": SCHEMA, "authority": AUTHORITY,
            "victims": n,
            "key_recovery": f"{recovered_key}/{n}",
            "plaintext_recovery": f"{recovered_plain}/{n}",
            "pass": n > 0 and recovered_plain == n,
            "results": results,
            "model_calls": 0}


def encrypt(plaintext: str, variant: str, key: str) -> str:
    """Reference encryptor used ONLY by the admission harness (never at decision time)."""
    t = _letters(plaintext)

    if variant.startswith("interleaved"):
        stride = int(variant.replace("interleaved", ""))
        keys = [s.upper() for s in key.split("|")]
        assert len(keys) == stride, "interleaved variant key count must match stride"
        counters = [0] * stride
        out = []
        for i, ch in enumerate(t):
            stream = i % stride
            k = keys[stream][counters[stream] % len(keys[stream])]
            counters[stream] += 1
            out.append(_ALPH[(ord(ch) - _A + ord(k) - _A) % 26])
        return "".join(out)
    k = key.upper()
    if variant == "beaufort":
        return "".join(_ALPH[(ord(k[i % len(k)]) - _A - (ord(c) - _A)) % 26] for i, c in enumerate(t))
    return "".join(_ALPH[(ord(c) - _A + ord(k[i % len(k)]) - _A) % 26] for i, c in enumerate(t))
