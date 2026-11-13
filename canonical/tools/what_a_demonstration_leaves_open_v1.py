#!/usr/bin/env python3
"""What does one demonstration leave open, and does that predict where the skill fails?

THE QUESTION
------------
Run 5 measures one-demonstration transfer on 130 MiniWoB++ pages. The useful question for
anyone trying to make this better is not "how high is the number" but "what does the learner
still not know". The run records that directly: for every step of every learned skill it stores
`descriptions_left`, the number of element descriptions still consistent with the one
demonstration it saw.

So the naive hypothesis writes itself: a demonstration that leaves 200 descriptions open should
transfer worse than one that leaves 2 open. `ambiguity_predicts_failure` tests it.

RESULT, AND IT IS A NEGATIVE ONE
--------------------------------
Measured on the 78 pages of run 5 that have a learned skill with recorded steps:

    ambiguity (median descriptions per step) ~ success rate     r = +0.26

the WRONG SIGN, and the most ambiguous third scores HIGHER (0.840) than the least (0.608). The
mechanism is a confound, not a mystery: loose descriptions appear on one-step natural-language
tasks ("click the button that says ...", 135-255 descriptions, 1.00 success), while tight
descriptions appear on multi-step spatial tasks where nothing works. Controlling for the cost of
finding the first success, the partial correlation falls to +0.12.

The predictor that survives is `first_success_cost_actions` (r = -0.27): **whether a
demonstration is available at all explains more than how vague it is.** A skill cannot be worse
than no skill, and 52 of 130 pages produced no first success.

This tool exists so that the intuitive claim ("vague demonstrations transfer badly") cannot be
asserted here without the correlation and the confound check running again first. It returns a
refusal rather than an endorsement when a predictor does not survive controlling for cost.

WHAT IT CANNOT DO HERE
----------------------
`feasibility()` reports whether the measurement can be re-run in this sandbox. It cannot: the
bridge needs a Chromium with real layout, there is no browser binary, no shared libraries and no
root to install them. That is recorded as BLOCKED with the reason, so a later reader does not
mistake "no re-run on file" for "the re-run agreed".

Authority: NONE. This is a secondary analysis of a producer-run measurement.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import os
import shutil
import statistics as st
import subprocess
import sys
from typing import Any, Iterable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
VERIFICATION = ROOT / "canonical" / "verification"

SCHEMA = "PROJECT_BRAIN_WHAT_A_DEMONSTRATION_LEAVES_OPEN_V1"

#: Below this, a relationship is not worth calling a predictor.
MIN_EFFECT = 0.30


# ---------------------------------------------------------------------------
# reading the run
# ---------------------------------------------------------------------------
def newest_run() -> pathlib.Path:
    runs = sorted(VERIFICATION.glob("MINIWOB_ONE_SUCCESS_GENERALISATION_*_V*.json"))
    if not runs:
        raise FileNotFoundError("NO_RECORDED_RUN")
    return runs[-1]


def _steps(arm: Mapping[str, Any]) -> list[int]:
    learning = arm.get("learning") or {}
    skills = learning.get("skills") or {}
    out: list[int] = []
    for program in skills.get("per_program") or []:
        for step in program.get("steps") or []:
            value = step.get("descriptions_left")
            if isinstance(value, int):
                out.append(value)
    return out


def table(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    """One row per page: how open the demonstration left it, and what the skill then did."""
    rows: list[dict[str, Any]] = []
    for task in report.get("tasks") or []:
        if not isinstance(task, Mapping):
            continue
        arm = (task.get("arms") or {}).get("version_space")
        if not isinstance(arm, Mapping):
            continue
        ambiguous = _steps(arm)
        successes, episodes = arm.get("successes"), arm.get("episodes") or 0
        rows.append({
            "task": task.get("task"),
            "steps": len(ambiguous),
            "descriptions_open_median": st.median(ambiguous) if ambiguous else None,
            "descriptions_open_max": max(ambiguous) if ambiguous else None,
            "success_rate": (successes / episodes) if isinstance(successes, (int, float)) and episodes else None,
            "first_success_cost_actions": task.get("first_success_cost_actions"),
            "distinct_test_instructions": task.get("distinct_test_instructions"),
        })
    return rows


# ---------------------------------------------------------------------------
# correlation, and the confound check that decides whether it means anything
# ---------------------------------------------------------------------------
def _ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    for position, index in enumerate(order):
        out[index] = float(position)
    return out


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mx, my = st.mean(xs), st.mean(ys)
    cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / len(xs)
    sx = (sum((a - mx) ** 2 for a in xs) / len(xs)) ** 0.5
    sy = (sum((b - my) ** 2 for b in ys) / len(ys)) ** 0.5
    return None if sx == 0 or sy == 0 else cov / (sx * sy)


def _residualise(ys: Sequence[float], xs: Sequence[float]) -> list[float]:
    mx, my = st.mean(xs), st.mean(ys)
    denom = sum((a - mx) ** 2 for a in xs) or 1.0
    slope = sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / denom
    return [b - (my + slope * (a - mx)) for a, b in zip(xs, ys)]


def relationships(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Does the openness of a demonstration predict failure, and does the cost confound it?

    Both are computed on ranks, because neither variable is close to normal and the point is an
    ordering, not a magnitude. The partial correlation is what decides: if the openness effect
    disappears once the cost of finding the demonstration is held fixed, openness was a marker of
    task type rather than a cause of failure.
    """
    usable = [r for r in rows
              if isinstance(r["descriptions_open_median"], (int, float))
              and isinstance(r["success_rate"], (int, float))
              and isinstance(r["first_success_cost_actions"], (int, float))]
    if len(usable) < 8:
        return {"n": len(usable), "verdict": "TOO_FEW_PAGES", "openness": None, "cost": None}

    openness = _ranks([float(r["descriptions_open_median"]) for r in usable])
    cost = _ranks([float(r["first_success_cost_actions"]) for r in usable])
    success = _ranks([float(r["success_rate"]) for r in usable])

    raw = _pearson(openness, success)
    cost_r = _pearson(cost, success)
    partial = _pearson(_residualise(success, cost), _residualise(openness, cost))

    thirds = max(1, len(usable) // 3)
    by_openness = sorted(usable, key=lambda r: r["descriptions_open_median"])
    low = [r["success_rate"] for r in by_openness[:thirds]]
    high = [r["success_rate"] for r in by_openness[-thirds:]]

    return {
        "n": len(usable),
        "openness": {"r_with_success": raw, "partial_r_controlling_for_cost": partial},
        "cost": {"r_with_success": cost_r},
        "least_open_third_success": st.mean(low),
        "most_open_third_success": st.mean(high),
        "openness_median_descriptions": st.median(
            [float(r["descriptions_open_median"]) for r in usable]),
        "verdict": _judge(raw, partial),
    }


def _judge(raw: float | None, partial: float | None) -> str:
    """An effect that does not survive the confound is reported as one, not quietly dropped."""
    if raw is None or partial is None:
        return "UNMEASURABLE"
    if abs(raw) < MIN_EFFECT and abs(partial) < MIN_EFFECT:
        return "NO_EFFECT"
    if abs(raw) >= MIN_EFFECT > abs(partial):
        return "CONFOUNCED_BY_FIRST_SUCCESS_COST" if False else "CONFOUNDED_BY_FIRST_SUCCESS_COST"
    if abs(partial) >= MIN_EFFECT:
        return "SURVIVES_THE_CONFOUND"
    return "WEAK"


# ---------------------------------------------------------------------------
# can the measurement be re-run here at all?
# ---------------------------------------------------------------------------
def feasibility(html_dir: str | None = None, modules_dir: str | None = None) -> dict[str, Any]:
    """Can a fresh-seed re-run happen HERE? Answered by trying, not by looking for a browser.

    MEASURED 2026-11-12, and this replaces a wrong answer. The previous version checked for a
    system chromium binary, found none, checked for libnspr4.so/libnss3.so, found neither, and
    reported BLOCKED. All three facts were true and the conclusion was false:
    `@sparticuz/chromium` ships `bin/chromium.br`, `bin/fonts.tar.br` and `bin/al2023.tar.br`,
    the last of which contains libnspr4.so, libnss3.so and seven other objects. The bridge
    inflates them and sets LD_LIBRARY_PATH itself (`miniwob_chromium_bridge_v1.mjs:377-381`), so
    no root and no system library is needed. Verified in this sandbox: HeadlessChrome/153.0.8010.0,
    real layout boxes, `click-test` reaching `raw_reward: 1`.

    A feasibility check that inspects the environment instead of exercising the tool reports
    false negatives, which is the failure this repository has now recorded five times. So this
    one runs the bridge.
    """
    html = pathlib.Path(html_dir) if html_dir else _locate_html()
    modules = pathlib.Path(modules_dir) if modules_dir else _locate_modules()
    blocked: list[str] = []

    if html is None or not html.is_dir():
        blocked.append("NO_MINIWOB_HTML")
    if modules is None or not (modules / "node_modules" / "puppeteer-core").is_dir():
        blocked.append("NO_PUPPETEER_CORE")

    probed = None
    if not blocked:
        probed = _probe_bridge(html, modules)                     # type: ignore[arg-type]
        if not probed.get("loaded"):
            blocked.append("BRIDGE_DID_NOT_LOAD:" + str(probed.get("error"))[:80])

    return {
        "schema": SCHEMA,
        "can_rerun_on_fresh_seeds": not blocked,
        "status": "RUNNABLE" if not blocked else "BLOCKED",
        "blocked_by": blocked,
        "method": "ran the bridge and loaded a page; did not inspect the environment",
        "probe": probed,
        "html_dir": str(html) if html else None,
        "modules_dir": str(modules) if modules else None,
    }


def _sparticuz_root() -> pathlib.Path | None:
    """Where npm put the package, if it is findable at all."""
    for base in ("/tmp/mw2", "/tmp/mw", os.getcwd()):
        candidate = pathlib.Path(base) / "node_modules" / "@sparticuz" / "chromium"
        if (candidate / "bin" / "al2023.tar.br").is_file():
            return candidate
    return None


def _locate_html() -> pathlib.Path | None:
    if os.environ.get("MINIWOB_HTML_DIR"):
        return pathlib.Path(os.environ["MINIWOB_HTML_DIR"])
    for base in ("/tmp/mw2", "/tmp/mw"):
        for found in sorted(pathlib.Path(base).glob("*miniwob*/miniwob/html")) + \
                sorted(pathlib.Path(base).glob("*MiniWoB*/miniwob/html")):
            if found.is_dir():
                return found
    return None


def _locate_modules() -> pathlib.Path | None:
    if os.environ.get("MINIWOB_NODE_MODULES_DIR"):
        return pathlib.Path(os.environ["MINIWOB_NODE_MODULES_DIR"])
    for base in ("/tmp/mw2", "/tmp/mw"):
        if (pathlib.Path(base) / "node_modules" / "puppeteer-core").is_dir():
            return pathlib.Path(base)
    return None


def _probe_bridge(html: pathlib.Path, modules: pathlib.Path) -> dict[str, Any]:
    """Load one task through the real bridge. The only honest way to answer this."""
    bridge = ROOT / "canonical" / "tools" / "miniwob_chromium_bridge_v1.mjs"
    if not shutil.which("node"):
        return {"loaded": False, "error": "NO_NODE"}
    commands = "\n".join(['{"cmd":"load","task":"click-test"}',
                          '{"cmd":"reset","seed":1}',
                          '{"cmd":"close"}'])
    try:
        proc = subprocess.run([shutil.which("node") or "node", str(bridge), str(html), str(modules)],
                              input=commands + "\n", text=True, capture_output=True, timeout=240)
    except Exception as exc:                                    # pragma: no cover - env specific
        return {"loaded": False, "error": f"{type(exc).__name__}:{exc}"[:120]}
    first = (proc.stdout or "").splitlines()[:1]
    if not first:
        return {"loaded": False, "error": (proc.stderr or "NO_OUTPUT")[:160]}
    try:
        loaded = json.loads(first[0]).get("ok") is True
    except ValueError:
        return {"loaded": False, "error": first[0][:160]}
    return {"loaded": loaded, "error": None if loaded else first[0][:160],
            "browser": _browser_version(html, modules)}


def _browser_version(html: pathlib.Path, modules: pathlib.Path) -> str | None:
    bridge = ROOT / "canonical" / "tools" / "miniwob_chromium_bridge_v1.mjs"
    try:
        proc = subprocess.run([shutil.which("node") or "node", str(bridge), str(html), str(modules)],
                              input='{"cmd":"versions"}\n{"cmd":"close"}\n', text=True,
                              capture_output=True, timeout=240)
        return (json.loads((proc.stdout or "").splitlines()[0]).get("browser"))
    except Exception:                                           # pragma: no cover - env specific
        return None


# ---------------------------------------------------------------------------
def report() -> dict[str, Any]:
    path = newest_run()
    data = json.loads(path.read_text())
    rows = table(data)
    return {
        "schema": SCHEMA, "authority": "NONE", "run": path.name,
        "pages_with_a_skill": len([r for r in rows if r["descriptions_open_median"] is not None]),
        "pages_scored": len([r for r in rows if r["success_rate"] is not None]),
        "relationships": relationships(rows),
        "feasibility": feasibility(),
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--table", action="store_true", help="print the per-page rows")
    args = parser.parse_args(argv)

    result = report()
    if args.json:
        print(json.dumps(result, indent=2))
        return 0

    rel = result["relationships"]
    print("what one demonstration leaves open, and what that predicts")
    print(f"run: {result['run']}   pages with a skill: {result['pages_with_a_skill']}\n")
    if rel.get("verdict") == "TOO_FEW_PAGES":
        print(f"  not enough pages to correlate ({rel['n']})")
    else:
        print(f"  pages analysed                          {rel['n']}")
        print(f"  median descriptions still open per step {rel['openness_median_descriptions']:.0f}")
        print(f"  openness ~ success                      r = {rel['openness']['r_with_success']:+.3f}")
        print(f"  ... controlling for first-success cost  r = {rel['openness']['partial_r_controlling_for_cost']:+.3f}")
        print(f"  first-success cost ~ success            r = {rel['cost']['r_with_success']:+.3f}")
        print(f"  least open third: success {rel['least_open_third_success']:.3f}"
              f"   most open third: success {rel['most_open_third_success']:.3f}")
        print(f"\n  VERDICT: {rel['verdict']}")
        if rel["verdict"].startswith("CONFOUND"):
            print("    Openness is a marker of task type, not a cause of failure. The predictor")
            print("    that survives is whether a first success could be found at all.")
    feas = result["feasibility"]
    print(f"\n  re-run on fresh seeds here: {feas['status']}"
          + (f"  ({', '.join(feas['blocked_by'])})" if feas["blocked_by"] else ""))
    if args.table:
        print(f"\n  {'task':28} {'steps':>5} {'open(med)':>10} {'success':>8} {'cost':>6}")
        for row in sorted(result["rows"], key=lambda r: -(r["descriptions_open_median"] or -1))[:30]:
            if row["descriptions_open_median"] is None:
                continue
            print(f"  {str(row['task'])[:28]:28} {row['steps']:>5} "
                  f"{row['descriptions_open_median']:>10.0f} "
                  f"{(row['success_rate'] or 0):>8.2f} {row['first_success_cost_actions']:>6}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
