"""Score the contextual-reference resolver on the frozen M0A corpus.

Rules honoured
--------------
HELDOUT_CASES_MUST_NOT_GUIDE_IMPLEMENTATION
    This file never reads a heldout case unless `--split heldout` is requested. The
    dev loop that produced the resolver looked only at `split == "dev"`.

The corpus has two answer shapes, so one scorer cannot serve both:

    referring expressions   bindings: [{mention, antecedent}]
    respectively mapping    bindings: [{subject, object}]

Both are scored, and a case is correct only if EVERY expected binding is matched.
Exact string equality is wrong (`service` vs `the service` are the same referent), so
comparison normalises articles, case, and whitespace before matching.

Usage
    python3 canonical/evaluation/evaluate_contextual_reference_v1.py            # dev
    python3 canonical/evaluation/evaluate_contextual_reference_v1.py --split heldout
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import contextual_reference_resolution_v1 as R  # noqa: E402

CORPUS = (Path(__file__).resolve().parent
          / "M0A_CONTEXTUAL_SEMANTICS_FROZEN_CORPUS_V1.json")


def norm(s):
    """Article-free, case-free, whitespace-free comparison form."""
    if s is None:
        return None
    s = str(s).strip().lower()
    s = re.sub(r"^(the|a|an)\s+", "", s)
    s = re.sub(r"\s+respectively$", "", s)
    s = re.sub(r"[.,;:]+$", "", s)
    return re.sub(r"\s+", " ", s).strip()


def answer_pairs(got):
    """Flatten a resolver result into a comparable {key: value} map."""
    pairs = {}

    def take(d, overwrite=False):
        # A MAPPING BINDING KEYS ON ITS SUBJECT.
        # The resolver reports `subject -> object` for `respectively` and
        # `mention -> antecedent` for a referring expression. Keying the mapping on
        # `mention` inverts it, so the scorer, not the resolver, was wrong here.
        if d.get("subject") is not None:
            k, v = d["subject"], d.get("object")
        elif d.get("mention") is not None:
            k = d["mention"]
            v = (d.get("antecedent") if d.get("antecedent") is not None
                 else d.get("antecedent_predicate"))
        else:
            return
        if overwrite or norm(k) not in pairs:
            pairs[norm(k)] = v

    for b in got.get("bindings") or []:
        take(b, overwrite=True)
    for r in got.get("resolutions") or []:
        take(r)
    return pairs


def expected_pairs(case):
    """Flatten the frozen expectation, or None when the case expects a refusal."""
    exp = case.get("expected") or {}
    if "status" in exp and "bindings" not in exp:
        return None                      # expects FAIL_CLOSED of a stated reason
    out = {}
    for b in exp.get("bindings") or []:
        if b.get("mention") is not None:
            # the corpus names an elided-predicate antecedent `antecedent_predicate`
            out[norm(b["mention"])] = (b.get("antecedent_predicate")
                                       if b.get("antecedent_predicate") is not None
                                       else b.get("antecedent"))
        elif b.get("subject") is not None:
            out[norm(b["subject"])] = b.get("object")
    return out or None


def expected_refusal(case):
    exp = case.get("expected") or {}
    return exp.get("status"), exp.get("reason")


def score_case(case):
    text = case["source"]
    got = R.resolve(text)
    want = expected_pairs(case)
    want_status, want_reason = expected_refusal(case)

    if want is None and want_status:
        ok = (got.get("status") == want_status
              and (want_reason is None or got.get("reason") == want_reason))
        return ok, (want_status, want_reason), (got.get("status"), got.get("reason"))

    have = answer_pairs(got)
    if not have:
        return False, want, {"status": got.get("status"), "reason": got.get("reason")}
    good = all(k in have and norm(have[k]) == norm(v) for k, v in want.items())
    return good, want, {k: have[k] for k in want if k in have}


def _ob_key(d, keys):
    """A normalised tuple over the fields an obligation actually specifies."""
    return tuple(norm(d.get(k)) if d.get(k) is not None else None for k in keys)


def score_obligations(case, got):
    """Every expected obligation must be produced. Extra ones are not penalised here.

    Obligations are scored on the fields the corpus states for each entry, which is why
    an entry with a `condition` is compared WITH that condition: dropping the scope is a
    different requirement, not a terser one.
    """
    exp = (case.get("expected") or {}).get("obligations")
    if not exp:
        return None
    have = got if isinstance(got, list) else (got.get("obligations") or [])
    have_keys = []
    for h in have:
        keys = tuple(k for k in ("condition", "subject", "predicate", "relation", "object")
                     if k in h)
        have_keys.append((keys, _ob_key(h, keys)))
    matched = 0
    detail = []
    for e in exp:
        keys = tuple(k for k in ("condition", "subject", "predicate", "relation", "object")
                     if k in e)
        want = _ob_key(e, keys)
        ok = any(hk == keys and _subseq(w, want) for hk, w in have_keys)
        matched += ok
        detail.append({"want": dict(zip(keys, want)), "ok": ok})
    return matched, len(exp), detail


def _subseq(have, want):
    """Field-by-field containment: `abort` matches `abort on any mismatch`."""
    if have is None or want is None:
        return have == want
    h, w = str(have), str(want)
    return h == w or h in w or w in h


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev", choices=["dev", "heldout", "all"])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    data = json.loads(CORPUS.read_text())
    cases = [c for c in data["cases"]
             if args.split == "all" or c.get("split") == args.split]

    results, n_ok = [], 0
    ob_ok = ob_total = 0
    for c in cases:
        ok, want, got = score_case(c)
        n_ok += ok
        ob = score_obligations(c, R.obligations(c["source"]))
        if ob:
            ob_ok += ob[0]
            ob_total += ob[1]
        results.append({"id": c["id"], "phenomenon": c.get("phenomenon"),
                        "ok": ok, "want": want, "got": got,
                        "obligations": ({"matched": ob[0], "of": ob[1]}
                                        if ob else None)})
        if not args.json:
            print(f"  {'OK  ' if ok else 'MISS'} {c['id']:34s} "
                  f"want={json.dumps(want, ensure_ascii=False)[:60]} "
                  f"got={json.dumps(got, ensure_ascii=False)[:60]}")

    total = len(cases)
    pct = 100.0 * n_ok / total if total else 0.0
    if args.json:
        print(json.dumps({"split": args.split, "correct": n_ok, "total": total,
                          "pct": round(pct, 1),
                          "obligations_correct": ob_ok, "obligations_total": ob_total,
                          "results": results}, indent=1))
    else:
        print(f"\n{args.split.upper()} REFERENCES:    {n_ok}/{total} = {pct:.0f}%")
        if ob_total:
            print(f"{args.split.upper()} OBLIGATIONS:   {ob_ok}/{ob_total} = "
                  f"{100.0 * ob_ok / ob_total:.0f}%")
    return 0 if n_ok == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
