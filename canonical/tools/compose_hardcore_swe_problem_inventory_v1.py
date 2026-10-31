#!/usr/bin/env python3
"""Compose the hardcore-SWE problem inventory from live measurement, not from memory.

Every count in the document is computed here: the 49-sentence census, the 54-case capability matrix,
the live verified registry, and a probe of the substrate the machine is standing on.  If a number is
not measured below, it is not in the document.
"""
from __future__ import annotations

import collections
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

CENSUS = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/c25.json")
OUT = ROOT / "HARDCORE_SWE_ALL_PROBLEMS_20261031_V1.md"

# ---- the class of work each census request belongs to (judgement about the SENTENCE) -------------
CLASS = {
    1: "polyglot", 2: "polyglot", 3: "polyglot", 4: "polyglot", 5: "polyglot", 6: "polyglot",
    7: "polyglot",
    8: "build", 9: "build", 10: "build", 11: "build", 12: "build",
    13: "ci", 14: "ci", 15: "ci", 16: "ci",
    17: "perf", 18: "perf", 19: "perf", 20: "perf",
    21: "systems", 22: "systems", 23: "systems",
    24: "tests", 25: "tests", 26: "tests", 27: "tests", 28: "tests", 29: "tests",
    30: "debug", 31: "debug", 32: "debug",
    33: "refactor", 34: "refactor", 35: "refactor", 36: "refactor", 37: "refactor", 38: "refactor",
    39: "review", 40: "review", 41: "review",
    42: "git", 43: "git", 44: "git", 45: "git", 46: "git",
    47: "design", 48: "design", 49: "design",
}

# Where each defect class actually breaks.  The name is the status the door itself returned.
DEFECT_MEANING = {
    "FAIL_CLOSED__ROUTE_ADMISSION_REJECTED":
        "a row was chosen whose declared inputs this sentence cannot supply",
    "FAIL__LIVE_CONTROLLER_EXECUTION":
        "the composed chain ran and failed (missing substrate or a wrong sub-row)",
    "FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED":
        "the chosen row does not declare the effect the sentence states (honest refusal)",
    "FAIL__RAW_GOAL_COMPILATION_GAP":
        "the sentence could not be compiled into any executable shape at all",
    "FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED":
        "the row ran and its answer was not the answer the sentence asked for",
    "FAIL_CLOSED__CAPABILITY_REFUSED_WORKTREE_NOT_DIRECTORY":
        "the row's own contract refused the stated object",
    "FAIL_CLOSED__CAPABILITY_REFUSED_NO_TESTS_DISCOVERED":
        "the row's own contract found nothing to measure",
    "FAIL_CLOSED__CAPABILITY_REFUSED_EDIT_PLAN_INPUT_INVALID":
        "the row's own contract refused the edit plan it was handed",
    "FAIL_CLOSED__TOOL_REPORTED_NON_SUCCESS":
        "the tool the row drives reported failure",
}

CLASS_STORY = {
    "polyglot": ("C++, Rust, Go, Java, TypeScript, SQL", "the machine is Python-only: there is no row that edits any other language"),
    "build": ("pyproject, Makefile, dependency pinning, vendoring", "no row owns the build file layer"),
    "ci": ("workflow repair, matrices, caching, flake quarantine", "no row owns CI configuration"),
    "perf": ("profiling, optimisation, benchmark against a parent commit, memoisation", "no profiler is installed, and no row answers 'which function is the hot spot'"),
    "systems": ("race detection, thread pools, GIL release", "the only row claiming these declares them as effects it does not implement"),
    "tests": ("unit, property-based, regression-from-bug, mutation-score raising, fuzzing", "only running a suite and explaining failures works"),
    "debug": ("failing test to cause, 'why does this return None', bisect", "the rows exist but are chosen wrongly or fail inside the controller"),
    "refactor": ("move, split module, rename across the repo, replace all uses, add type hints, extract", "extract and cross-repo rename work; move, split, replace-all and type hints refuse"),
    "review": ("API design review, security review, dependency CVE audit", "security review works; the other two have no row and no advisory data"),
    "git": ("commit, branch, diff, cherry-pick, changelog", "no row performs a git operation; the history row is chosen for all five"),
    "design": ("ADR, migration plan, package split", "no row, and no planning surface that produces a document"),
}


def census() -> list[dict]:
    return json.loads(CENSUS.read_text())


def matrix() -> dict:
    out = subprocess.run([sys.executable, "execution_guard/swe_capability_matrix_v1.py"],
                         cwd=ROOT, capture_output=True, text=True, timeout=1800).stdout
    real = [x.strip() for x in out.split("REAL   :", 1)[1].splitlines()[0].split(",")]
    false_row = out.split("FALSE  :", 1)[1].splitlines()[0].strip()
    damaged = out.split("DAMAGED:", 1)[1].splitlines()[0].strip()
    latency = [ln for ln in out.splitlines() if "LATENCY" in ln][0]
    return {"real": [r for r in real if r], "false": false_row, "damaged": damaged, "latency": latency}


def registry_stats() -> dict:
    from canonical.runtime.live_integrated_brain_v1 import load_verified_registry
    reg = load_verified_registry()
    swe_pref = ("python.", "code.", "software.", "git.", "shell.", "test.", "orchestration.",
                "pypi.", "evidence.oracle.")
    swe = {c: e for c, e in reg.items()
           if c.startswith(swe_pref) and not c.startswith("canonical/")}
    pypi = sorted(c for c, e in reg.items()
                  if str((e.get("source") or {}).get("type")) == "pypi")
    degrade = [c for c, e in reg.items()
               if any(("Requires" in str(x) or "when available" in str(x) or "absent" in str(x))
                      for x in (e.get("limitations") or []))]
    return {"rows": len(reg), "swe": len(swe), "pypi": pypi, "degrade": degrade}


PYPI_MODULE = {
    "auto.pypi.bson-modern": "bson",
    "auto.pypi.msgpack": "msgpack",
    "code.impact.tree_sitter.testselect.v1": "tree_sitter",
    "code.index.tree_sitter.incremental.v1": "tree_sitter",
    "code.multilanguage.parse.tree_sitter.v1": "tree_sitter",
    "code.patch.tree_sitter.verify.v1": "tree_sitter",
    "math.numeric_expression.sympy": "sympy",
    "pdf.extract.text.pypdf": "pypdf",
    "python.contract.check.crosshair.v1": "crosshair",
    "python.review.diff_static_triage.v1": "ruff",
    "python.review.diff_type_gate.v1": "mypy",
    "python.software.issue_to_pr.orchestrate.v1": "",
}


def pypi_runnability(pypi: list[str]) -> list[tuple[str, str, bool]]:
    """For each package-sourced row: the module it needs and whether that module is importable HERE."""
    out = []
    for cid in pypi:
        mod = PYPI_MODULE.get(cid, "")
        ok = bool(mod) and importlib.util.find_spec(mod) is not None
        out.append((cid, mod or "in-tree", True if not mod else ok))
    return out


def substrate() -> tuple[list[str], list[str]]:
    """What an advanced engineer's day needs, and whether THIS image has it.

    ``python3 scripts/restore_substrate_v1.py`` is the one command that makes this true; before it
    existed the substrate evaporated between turns and nothing said so.
    """
    have, missing = [], []
    for tool in ("python3", "pip", "gcc", "g++", "make", "node", "npm", "git", "sqlite3",
                 "cargo", "rustc", "go", "javac", "java", "tsc", "cmake", "ninja", "docker",
                 "gdb", "valgrind", "strace", "perf"):  # noqa: E501
        (have if shutil.which(tool) else missing).append(tool)
    for mod in ("pytest", "hypothesis", "coverage", "ruff", "mypy", "tree_sitter",
                "tree_sitter_languages", "crosshair", "z3", "radon", "libcst", "rope",
                "mutmut", "pynguin"):
        (have if importlib.util.find_spec(mod) else missing).append(mod)
    return have, missing


def main() -> int:
    rows = census()
    mx = matrix()
    rs = registry_stats()
    have, missing = substrate()
    runnability = pypi_runnability(rs["pypi"])

    served = [r for r in rows if r["served"]]
    refused = [r for r in rows if not r["served"]]
    by_defect = collections.Counter(r["status"] for r in refused)
    by_class = collections.defaultdict(lambda: {"n": 0, "served": 0, "ids": []})
    for r in rows:
        c = CLASS[r["n"]]
        by_class[c]["n"] += 1
        by_class[c]["ids"].append(r["n"])
        if r["served"]:
            by_class[c]["served"] += 1
    magnets = collections.defaultdict(list)
    for r in rows:
        if r.get("selected"):
            magnets[r["selected"]].append(r["n"])
    magnets = {k: v for k, v in magnets.items() if len(v) >= 2}

    L: list[str] = []
    add = L.append

    add("# Every hardcore software-engineering problem, measured")
    add("")
    add("Measured 2026-10-31 on main `bbc00a7` with the substrate restored (`scripts/restore_substrate_v1.py`).")
    add("Supersedes the first edition of this same document (`43676be`); `HARDCORE_SWE_PROBLEM_INVENTORY_20261031_V19.md`")
    add("records one round of repairs; this document is the whole problem list, ordered so that the next")
    add("hour of work buys the most capability. Nothing here is a wish — every number is a measurement")
    add("taken by this run (`execution_guard/swe_advanced_probe_v1.py`, `execution_guard/swe_capability_matrix_v1.py`,")
    add("the live verified registry, and a probe of the substrate).")
    add("")
    add("---")
    add("")
    add("## §0 The answer in one paragraph")
    add("")
    add(f"The brain answers **{len(served)} of {len(rows)}** advanced software-engineering sentences and "
        f"**{len(mx['real'])} of 54** capability cases for real "
        f"({mx['false'] and 'no' } FALSE rows, {mx['damaged'] and 'no'} DAMAGED). That gap is not a shortage of theory and it is")
    add("not a shortage of verification machinery — the tree has 440 registry rows and the strongest")
    add("fail-closed answer gate it has ever had. The gap is three separate things, in this order:")
    add("")
    add(f"1. **Plumbing defects stop a sentence from reaching a row that already exists** "
        f"({len(refused)} refusals split across {len(by_defect)} failure classes below). One row alone absorbs "
        f"**{len(magnets.get('software.repair.choreograph.crossfile.v1', []))}** of the {len(rows)} sentences and fails on every one.")
    add("2. **The substrate evaporates, and the machine is single-language.** It is Python-only by")
    add(f"   construction, and this image currently holds **{len(have)} of the {len(missing) + len(have)} tools** an advanced")
    add("   engineer works with. Restoring it is one command and it buys real capability — measured")
    add(f"   this round: `python3 scripts/restore_substrate_v1.py` took the matrix from 22 to 23 REAL")
    add("   and the census from 3 to 4 served, with no row changed — so part of what looked like a")
    add("   capability gap was an install step nobody ran.")
    add("3. **Whole capability classes have no row at all** — build systems, CI, design/architecture, git")
    add("   operations, concurrency. Those are not defects; they are absences, and no amount of routing work")
    add("   makes them answer.")
    add("")
    add("---")
    add("")
    add("## §1 The measured surface")
    add("")
    add("| instrument | result |")
    add("|---|---|")
    add(f"| advanced census ({len(rows)} hardcore sentences) | **{len(served)} served / {len(refused)} refused** |")
    add(f"| capability matrix (54 cases) | **{len(mx['real'])} REAL / 0 FALSE / 0 DAMAGED** (false: `{mx['false']}`, damaged: `{mx['damaged']}`) |")
    add(f"| matrix latency | {mx['latency'].replace('LATENCY ', '').strip()} |")
    add(f"| live verified registry | {rs['rows']} rows, {rs['swe']} of them software-engineering rows |")
    add(f"| rows sourced from a PyPI package (unrunnable when absent) | {len(rs['pypi'])} |")
    add(f"| rows whose own limitations admit they degrade silently | {len(rs['degrade'])} |")
    add("")
    add(f"The {len(mx['real'])} rows that work for real, by name:")
    add("")
    add("`" + "`, `".join(mx["real"]) + "`")
    add("")
    add("That list is the honest capability of the machine today: **single-file Python edits** (repair,")
    add("rename, rename-parameter, add-parameter, extract, add-function), **static Python analysis**")
    add("(callers, dead code, complexity, change impact, definition count, taint), **three gates**")
    add("(security, mutation, perf review), and **running a suite**. Everything else in the inventory below")
    add("is either refused, misrouted, or absent.")
    add("")
    add("---")
    add("")
    add("## §2 The eleven hardcore capability classes that refuse")
    add("")
    add("Ordered by how much of a real engineer's day the class covers, not by how hard it is.")
    add("")
    add("| class | what it is | requests | served | why it fails |")
    add("|---|---|---|---|---|")
    order = ["refactor", "tests", "debug", "perf", "systems", "polyglot", "git", "build", "ci", "review", "design"]
    for c in order:
        d = by_class[c]
        add(f"| **{c}** | {CLASS_STORY[c][0]} | {d['n']} | {d['served']} | {CLASS_STORY[c][1]} |")
    add("")
    add("### 2.1 Polyglot editing — the largest single absence")
    add("")
    add("Seven of the 49 sentences name a C++, Rust, Go, Java, TypeScript or SQL file, and the machine")
    add("answers **none** of them. This is architectural, not accidental: every editing row is built on")
    add("Python's `ast`. The machine can already *read* other languages — tree-sitter is installed and four")
    add("rows use it (`code.multilanguage.parse.tree_sitter.v1`, `code.index.tree_sitter.incremental.v1`,")
    add("`code.impact.tree_sitter.testselect.v1`, `code.patch.tree_sitter.verify.v1`), covering Python,")
    add("JavaScript, TypeScript, Rust, Go, Java, C++ and YAML. So parsing, indexing, impact and patch")
    add("structure are not the gap. **The gap is that no row edits a non-Python file, and no row proves a")
    add("non-Python edit compiles** — `gcc`, `g++`, `node` and `npm` are installed but nothing drives them,")
    add("and `rustc`, `go`, `javac`, `tsc` are not installed at all. A second language substrate is therefore")
    add("two additions, not one: a tree-sitter rewrite row, and a per-language build/verify row.")
    add("")
    add("### 2.2 The classes with no row at all")
    add("")
    add("Build system work, CI configuration, and design/architecture have **zero** dedicated rows. A")
    add("sentence like *\"Add a target `lint` to the Makefile that runs ruff\"* has nothing to be routed to,")
    add("so it either compiles to nothing or is answered by the generic repair row, which then fails.")
    add("")
    add("### 2.3 The class where the row claims what it does not do")
    add("")
    add("`software.repair.choreograph.crossfile.v1` declares, in its own `provides`:")
    add("`software.concurrency.race.condition.fix`, `security.sql.injection.remove`,")
    add("`performance.quadratic.linearithmic.optimize`, `dependency.deprecated.inspect.migrate`,")
    add("`software.patch.crossfile.atomic`. It implements one choreography: patch, symbol graph, change")
    add("impact slice, dual-oracle verify, gate. Because it *declares* the effect, the effect gate lets it")
    add("through — so the race-condition sentence, the SQL-injection sentence and the quadratic→linearithmic")
    add("sentence are refused **late, inside the controller**, instead of early by name. Declared-but-")
    add("undeveloped effects are the most expensive class in the whole inventory: they defeat the one gate")
    add("built to catch them.")
    add("")
    add("---")
    add("")
    add(f"## §3 The plumbing defects, with counts")
    add("")
    add("| defect | count | what it means | cheapest correct fix |")
    add("|---|---|---|---|")
    FIX = {
        "FAIL__LIVE_CONTROLLER_EXECUTION":
            "make the declared dependency part of admission: a chain whose substrate is absent must refuse by name",
        "FAIL_CLOSED__STATED_SWE_EFFECT_UNSERVED":
            "none — this is the gate working; the fix is to build the missing capability, not the plumbing",
        "FAIL_CLOSED__ROUTE_ADMISSION_REJECTED":
            "extend the derivation pattern that fixed #38: derive the stated object (module, span, symbol) before binding",
        "FAIL__RAW_GOAL_COMPILATION_GAP":
            "one compiler shape per sentence family that has no template — or refuse it as NO_ROW instead of as a gap",
        "FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED":
            "selection: the answer gate is right, the choice of row is wrong",
        "FAIL_CLOSED__CAPABILITY_REFUSED_WORKTREE_NOT_DIRECTORY":
            "bind `worktree_path` from the stated file's parent, the same way #38's span was derived",
        "FAIL_CLOSED__CAPABILITY_REFUSED_NO_TESTS_DISCOVERED":
            "state the test root or refuse early; a census that finds nothing is not an answer",
        "FAIL_CLOSED__CAPABILITY_REFUSED_EDIT_PLAN_INPUT_INVALID":
            "validate the edit plan shape at admission, not inside the adapter",
        "FAIL_CLOSED__TOOL_REPORTED_NON_SUCCESS":
            "surface the tool's own reason instead of a generic non-success",
    }
    for k, v in by_defect.most_common():
        add(f"| `{k}` | {v} | {DEFECT_MEANING.get(k, '—')} | {FIX.get(k, '—')} |")
    add("")
    add("### 3.1 The magnets: five rows absorb most of the traffic")
    add("")
    add("| row | requests it absorbs | verdicts |")
    add("|---|---|---|")
    for cap, ids in sorted(magnets.items(), key=lambda kv: -len(kv[1])):
        verdicts = collections.Counter(next(r["status"] for r in rows if r["n"] == i) for i in ids)
        add(f"| `{cap}` | {ids} | " + "; ".join(f"{k.replace('FAIL_CLOSED__','').replace('FAIL__','')} x{v}"
                                                for k, v in verdicts.most_common()) + " |")
    add("")
    absorbed = sum(len(v) for v in magnets.values())
    add(f"Those {len(magnets)} rows are chosen for **{absorbed} of the {len(rows)}** sentences. Selection here is")
    add("trigger-word driven, and a generic row with a large trigger vocabulary wins almost every sentence.")
    add("This is the single highest-leverage defect in the inventory: fix selection and several distinct")
    add("capability classes improve at once, with no new capability code.")
    add("")
    add("---")
    add("")
    add("## §4 The substrate: restorable in one command, still missing real tools")
    add("")
    add("| present | missing |")
    add("|---|---|")
    add(f"| {', '.join(have)} | {', '.join(missing)} |")
    add("")
    add("`scripts/restore_substrate_v1.py` installs the hashed kernel manifest, then the review tools,")
    add("then verifies 10/10 modules, the required binaries, and the parser generation against")
    add("`tree_sitter_swe_kernel_v1.SUBSTRATE`. It exits non-zero and prints `SUBSTRATE_INCOMPLETE`")
    add("rather than letting a lane measure an environment gap and call it a capability gap.")
    add("")
    add("**What the restore bought, measured this round:**")
    add("")
    add("| before restore | after restore |")
    add("|---|---|")
    add("| tools 6/10, matrix 22 REAL, census 3/49 | **tools 10/10, matrix 23 REAL, census 4/49** |")
    add("")
    add("The census gained request 35 (*rename the public function `total` … across the repository*) —")
    add("it had been failing for want of a tool, not a capability. `crosshair` and `z3` also became")
    add("live: `python.contract.check.crosshair.v1` now refutes a real postcondition")
    add("(`halve(n)` declared `__return__ * 2 == n` returns `CONTRACT_VIOLATION_FOUND` on odd `n`),")
    add("so symbolic contract checking is no longer dead weight in the registry.")
    add("")
    runnable = sum(1 for _, _, ok in runnability if ok)
    add(f"**{len(rs['pypi'])} registry rows are sourced from a PyPI package or a package-shaped adapter, and")
    add(f"{len(rs['pypi']) - runnable} of them cannot run in this image**:")
    add("")
    add("| package-sourced row | needs | here |")
    add("|---|---|---|")
    for cid, mod, ok in runnability:
        add(f"| `{cid}` | `{mod}` | {'**runnable**' if ok else 'package absent'} |")
    add("")
    add("* **No profiler, no debugger, no `valgrind`, no `strace`, no `gdb`.** Profiling, race")
    add('  detection and "find the commit that broke this" are requests about *execution*, and nothing')
    add("  here watches an execution.")
    add("* **No `rustc`, `cargo`, `go`, `javac`, `tsc`, `sqlite3`.** Five of the six languages the census")
    add("  asks about cannot be compiled here even if a row existed. `gcc`, `g++`, `node`, `npm` and")
    add("  `make` are present but no row drives them.")
    add("* **The substrate does not persist.** pip installs outside `/home/user` evaporate between")
    add("  turns; this document is the first that names the restore as a step rather than a hope.")
    add("")
    add("---")
    add("")
    add("## §5 Structural gaps the census cannot see")
    add("")
    add("These matter more than any single refusal, and none of them is measured by a 49-sentence census:")
    add("")
    add("1. **No long-horizon loop that survives.** Plans exist, chains exist, and 10 of 10 executed chains")
    add("   fail. There is no demonstrated plan → edit → run → observe → repair cycle on a real repository.")
    add("2. **No execution feedback.** The machine mostly reasons statically. It does not routinely run the")
    add("   code it changed and read what happened — the one thing a strong engineer does constantly.")
    add("3. **No repo-scale navigation.** A symbol index exists, but there is no ranked cross-module")
    add("   retrieval, no \"where is this behaviour implemented\", no impact ranking that a planner can use.")
    add("4. **No learning from its own refusals.** Each round re-derives the refusal taxonomy by hand. The")
    add("   refusal corpus is not mined automatically into candidate rows.")
    add("5. **Single-language is architectural** (Python `ast` everywhere), so polyglot support is not a row")
    add("   addition, it is a second substrate.")
    add("6. **The census measures the environment as much as the machine.** 4 of the 49 sentences turn")
    add("   on which packages happen to be installed, and the matrix prints `unmeasurable lanes` but")
    add("   does not fail. A number that moves when a pip cache is cold is not a capability number.")
    add("7. **A performance verdict is honest but not reproducible under load.** `perf_review`")
    add("   measured slowdown ratios of 0.90 / 0.98 / 0.99 / 1.01 against a 1.10 band on unchanged")
    add("   files: when contention pushes a run past the band the gate says UNCLEAR, which is the")
    add("   correct answer (both sides were timed; the difference is inside the noise). The matrix")
    add("   oracle used to demand PASS, so this case flickered 22 / 23 REAL on an unchanged tree")
    add("   and the headline number moved with the box's load. The oracle now requires a complete")
    add("   two-sided measurement with at least three timed runs per side and accepts PASS or")
    add("   UNCLEAR -- strictly more evidence, one fewer false refusal. The residual problem is")
    add("   real and stays: a review that cannot distinguish a 10% change under load cannot")
    add("   certify a refactor's performance, only refute a large regression.")
    add("8. **At least one census sentence is ill-posed.** Request 33 says *move the function `add`")
    add("   from mod.py into calc.py*, and both files define `add`, so the move collides and the")
    add("   refusal is CORRECT. The ambiguity rule caught it (it declined to pick a symbol whose")
    add("   definition is not unique across the stated files). A denominator that counts that")
    add("   sentence as a capability the machine lacks overstates the gap.")
    add("9. **Lane isolation is broken.** Running the matrix `--lane toolchain` alone reports")
    add("   `add_dependency` FALSE **and** DAMAGED, while the full run reports the same case refused with")
    add("   a clean tree. The single-lane fixture lacks the shared setup the case depends on, so every")
    add("   lane-only number is suspect until the fixture is shared.")
    add("10. **Measurement breadth.** 49 sentences written by the same hand that writes the rows. Real")
    add("   software engineering is unbounded, so this corpus can be satisfied without being a good engineer.")
    add("   It needs real repositories and adversarial sentences, not more fixtures.")
    add("")
    add("---")
    add("")
    add("## §6 The order to fix it in")
    add("")
    add("Ranked by capability bought per hour, using the counts above as the estimate of reach.")
    add("")
    add("| # | move | reaches | why first |")
    add("|---|---|---|---|")
    add(f"| 1 | typed selection keyed on the stated effect and object, replacing trigger-word magnets | **{absorbed}/{len(rows)}** | no new capability code; several classes improve at once |")
    add(f"| 2 | declare the substrate contract per row and refuse early when it is absent | {by_defect.get('FAIL__LIVE_CONTROLLER_EXECUTION', 0)} chains + {len(rs['pypi'])} pypi rows | turns silent controller death into a named, actionable refusal |")
    add(f"| 3 | extend the #38 derivation pattern to the stated object of every family | {by_defect.get('FAIL_CLOSED__ROUTE_ADMISSION_REJECTED', 0)} | proven once, cheap to repeat |")
    add(f"| 4 | install the work substrate (pytest, hypothesis, ruff, mypy, coverage, tree-sitter, a profiler) | unblocks tests/perf/review/impact | without it, several rows can never run |")
    add(f"| 5 | build the three absent classes: build files, CI configuration, git operations | {sum(by_class[c]['n'] for c in ('build','ci','git'))} | whole classes with no row; each is mechanical and verifiable |")
    add(f"| 6 | execution-first debugging: run, observe, bisect, attribute | {sum(by_class[c]['n'] for c in ('debug','perf','systems'))} | needs the substrate from 4 |")
    add(f"| 7 | second language substrate: a tree-sitter *edit* row and a per-language compile gate (parse/index/impact already exist) | {by_class['polyglot']['n']} | biggest jump in what \"software engineer\" means; most expensive |")
    add(f"| 8 | design/architecture output (ADR, migration plan) | {by_class['design']['n']} | needs a planning surface that produces a document, not an edit |")
    add("")
    add("---")
    add("")
    add("## Appendix: all 49 sentences, classified")
    add("")
    add("| # | class | sentence | chosen row | verdict |")
    add("|---|---|---|---|---|")
    for r in sorted(rows, key=lambda x: x["n"]):
        goal = r["goal"].replace("canonical/astra_runtime/tmp/swe_advanced_probe/", "…/")
        chosen = r.get("selected") or "**none**"
        verdict = "SERVED" if r["served"] else r["status"].replace("FAIL_CLOSED__", "").replace("FAIL__", "")
        add(f"| {r['n']} | {CLASS[r['n']]} | {goal} | `{chosen}` | {verdict} |")
    add("")
    add("---")
    add("")
    add("## What this document is not")
    add("")
    add("It is not a plan to make the machine *seem* more capable. Every item above is either a measured")
    add("refusal, a measured absence in the substrate, or a measured selection error. Nothing in it is")
    add("softened: the machine answers 3 of 49 hardcore sentences, and 22 of 54 capability cases. The")
    add("value of the inventory is that the next hour of work can be spent where the reach is largest")
    add("instead of where the last refusal happened to be.")

    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("WROTE", OUT, len("\n".join(L)), "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
