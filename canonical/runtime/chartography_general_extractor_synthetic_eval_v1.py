#!/usr/bin/env python3
"""Held-out end-to-end evaluation of the general extractor on random synthetic
charts with random typed questions. OCR is simulated from matplotlib text
artists (optionally corrupted: one wrong tick label + box jitter) so the
measurement covers frame/axes/series/table/query logic; the real OCR cell is
measured on the runner. Reports, per question type: answered-correct,
answered-wrong (the critical number), abstained. Zero benchmark data."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from typing import Any, Dict, List

PAL = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
CATS = ["Apple", "Banana", "Cherry", "Dates", "Elder", "Fig", "Grape", "Honey"]


def _setup():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from canonical.tests.test_chartography_general_extractor_v1 import _render, _fake_ocr, _words_from_texts
    return plt, _render, _fake_ocr, _words_from_texts


def _corrupt(words: List[Dict[str, Any]], rng: random.Random) -> List[Dict[str, Any]]:
    from canonical.runtime.chartography_general_extractor_v1 import numeric_token
    out = []
    nums = [i for i, w in enumerate(words) if numeric_token(w["text"]) is not None]
    bad = rng.choice(nums) if nums and rng.random() < 0.5 else None
    for i, w in enumerate(words):
        w = dict(w)
        j = rng.uniform(-2, 2)
        for k in ("x0", "x1", "cx"):
            w[k] += j
        for k in ("y0", "y1", "cy"):
            w[k] += rng.uniform(-2, 2)
        if i == bad:
            w["text"] = str(int(float(w["text"].replace(",", "")) * 7 + 3)) if w["text"].replace(",", "").replace(".", "").isdigit() else w["text"]
        out.append(w)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--seed", type=int, default=4242)
    ap.add_argument("--corrupt-ocr", action="store_true")
    ap.add_argument("--policy", choices=["best_effort", "certified"], default="best_effort")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    plt, render, fake_ocr, words_from_texts = _setup()
    from canonical.runtime import chartography_general_extractor_v1 as G
    G.POLICY = a.policy
    rng = random.Random(a.seed)
    tally: Dict[str, Dict[str, int]] = {}
    wrong_examples: List[str] = []
    reasons: Dict[str, int] = {}
    kind_holder = ["?"]
    cert_tally: Dict[Any, int] = {("certified", "correct"): 0, ("certified", "wrong"): 0,
                                  ("uncertified", "correct"): 0, ("uncertified", "wrong"): 0}
    t0 = time.time()

    def rec(qt: str, outcome: str):
        tally.setdefault(qt, {"correct": 0, "wrong": 0, "abstain": 0})[outcome] += 1

    def check(qt, res, gold, rel=0.05, absmin=0.5, label=None):
        if res["status"] != "ANSWER":
            rec(qt, "abstain")
            key = f"{kind_holder[0]}:{res['status'][:60]}"
            reasons[key] = reasons.get(key, 0) + 1
            return
        if label is not None:
            ok = res["answer"] == label
        else:
            ok = abs(res["answer_numeric"] - gold) <= max(rel * abs(gold), absmin)
        rec(qt, "correct" if ok else "wrong")
        cert_tally[("certified" if res.get("certified") else "uncertified", "correct" if ok else "wrong")] += 1
        if not ok and len(wrong_examples) < 25:
            wrong_examples.append(f"{qt}: gold={gold if label is None else label} got={res['answer']} table={res.get('table')}")

    for i in range(a.n):
        kind = rng.choice(["bar", "barh", "line", "grouped", "pie"])
        k = rng.randint(3, 5 if kind == "pie" else 6)
        kind_holder[0] = kind
        cats = CATS[:k]
        if kind in ("bar", "barh", "grouped", "line"):
            fig, ax = plt.subplots(figsize=(6.4, 4.8))
            if kind == "line":
                years = list(range(2010, 2010 + k + 3))
                cats = [str(y) for y in years]
                vals = [round(rng.uniform(5, 100), 1) for _ in years]
                ax.plot(years, vals, color=PAL[rng.randrange(5)], linewidth=2.0)
                ax.set_xticks(years)
                table = {None: dict(zip(cats, vals))}
            elif kind == "grouped":
                import numpy as np
                va = [round(rng.uniform(5, 100), 1) for _ in cats]
                vb = [round(rng.uniform(5, 100), 1) for _ in cats]
                x = np.arange(k)
                ax.bar(x - 0.2, va, width=0.4, color=PAL[0], label="North")
                ax.bar(x + 0.2, vb, width=0.4, color=PAL[1], label="South")
                ax.set_xticks(x, cats)
                ax.legend(loc=rng.choice(["upper left", "upper right"]))
                table = {"North": dict(zip(cats, va)), "South": dict(zip(cats, vb))}
            else:
                vals = [round(rng.uniform(5, 100), 1) for _ in cats]
                (ax.barh if kind == "barh" else ax.bar)(cats, vals, color=PAL[rng.randrange(5)])
                table = {None: dict(zip(cats, vals))}
            if rng.random() < 0.5:
                ax.grid(True, alpha=0.3)
            rgb = render(fig)
            words = fake_ocr(fig, ax)
            plt.close(fig)
        else:
            w = [rng.uniform(1, 10) for _ in cats]
            fr = [v / sum(w) for v in w]
            fig, ax = plt.subplots(figsize=(5, 5))
            _, texts = ax.pie(fr, labels=cats, colors=PAL[:k], startangle=rng.uniform(0, 360))
            fig.canvas.draw()
            rgb = render(fig)
            words = words_from_texts(fig, texts)
            plt.close(fig)
            table = {None: {c: 100 * f for c, f in zip(cats, fr)}}
        if a.corrupt_ocr:
            words = _corrupt(words, rng)
        solve = lambda q: G.solve("synthetic.png", q, ocr=lambda p: words, rgb=rgb)  # noqa: E731

        if kind == "pie":
            c = rng.choice(cats)
            check("SHARE", solve(f"What percentage share does {c} have?"), table[None][c], rel=0.05, absmin=1.0)
            best = max(table[None], key=table[None].get)
            check("EXTREMA_CAT", solve("Which slice has the largest share?"), None, label=best)
            continue
        sname = rng.choice(list(table)) if kind == "grouped" else None
        row = table[sname]
        sp = f"the value of {sname} " if sname else ""
        c1, c2 = rng.sample(cats, 2)
        check("LOOKUP", solve(f"What is {sp}for {c1}?" if sname else f"What is the value for {c1}?"), row[c1])
        if kind != "grouped":
            check("DIFFERENCE", solve(f"What is the difference between {c1} and {c2}?"), abs(row[c1] - row[c2]))
            check("RATIO", solve(f"What is the ratio of {c1} to {c2}?"), row[c1] / row[c2], absmin=0.02)
            check("AGGREGATE", solve("What is the total of all categories?"), sum(row.values()))
            check("EXTREMA_VAL", solve("What is the highest value in the chart?"), max(row.values()))
            check("EXTREMA_CAT", solve("Which category has the highest value?"), None, label=max(row, key=row.get))
            if kind == "line":
                check("PERCENT_CHANGE", solve(f"What is the percentage change from {c1} to {c2}?"), (row[c2] - row[c1]) / row[c1] * 100, absmin=2.0)
        else:
            check("EXTREMA_CAT", solve(f"Which category has the highest {sname}?"), None, label=max(row, key=row.get))

    total = {k: sum(v.values()) for k, v in tally.items()}
    receipt = {
        "receipt_type": "CHARTOGRAPHY_GENERAL_EXTRACTOR_SYNTHETIC_EVAL_V1",
        "credit_claimed": 0, "benchmark_data_touched": False,
        "ocr": "simulated from matplotlib text artists" + (" + corruption (one wrong tick label in 50% of charts, +/-2px jitter)" if a.corrupt_ocr else ""),
        "seed": a.seed, "charts": a.n, "policy": a.policy, "elapsed_s": round(time.time() - t0, 1),
        "by_certificate": {f"{c}_{o}": n for (c, o), n in cert_tally.items()},
        "by_question_type": {k: dict(v, total=total[k], wrong_rate=round(v["wrong"] / total[k], 4),
                                     correct_rate=round(v["correct"] / total[k], 4)) for k, v in sorted(tally.items())},
        "overall": {
            "questions": sum(total.values()),
            "correct": sum(v["correct"] for v in tally.values()),
            "wrong": sum(v["wrong"] for v in tally.values()),
            "abstain": sum(v["abstain"] for v in tally.values()),
        },
        "wrong_examples": wrong_examples,
        "abstain_reasons": dict(sorted(reasons.items(), key=lambda kv: -kv[1])),
    }
    receipt["sha256_of_body"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    if a.out:
        with open(a.out, "w") as fh:
            fh.write(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps({"overall": receipt["overall"], "by_certificate": receipt["by_certificate"], "by_type": receipt["by_question_type"], "abstain_reasons": receipt["abstain_reasons"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
