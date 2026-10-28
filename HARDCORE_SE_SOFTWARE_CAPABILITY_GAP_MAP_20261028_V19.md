# What are all the problems?

**Hardcore software-engineering capability inventory · 2026-10-28 · measured on `arena/4ca3a720-brain` at `ce300be`**

_Supersedes `…GAP_MAP_20261028_V18.md`. Everything in the earlier V-series is either re-measured here or summarised in §12._

This is the complete answer to *"what are all the problems?"*, restricted to what the owner asked for:
the machine must be the most advanced, fastest software engineer — repair, refactor, analysis,
testing, build, release, performance, security, delivery. PDF/XLSX/DOCX/chart work is measured and
then set aside (§9): it is 14% of the registry and 0% of this inventory's priorities.

Everything below is measured by a re-runnable instrument on the current commit. No claim in this
document rests on an earlier reading.

---

## 0. The answer in one page

| # | problem | size | who it hurts |
|---|---|---|---|
| **P1** | **The door credits acts nothing owns.** "Scan for secrets" and "audit dependencies for vulnerabilities" are both answered by `bandit` and counted as *answered by their owning capability*. Measured: 2 of 3 planted secrets found — by *variable name*, so a `ghp_…` GitHub token in a variable called `TOKEN` was caught while an `AKIA…` AWS access-key id in `AWS_ACCESS_KEY_ID` was not — and no advisory database anywhere. The probe's ownership oracle is lexical, so it certifies the wrong tool. | 2 acts miscredited, 1 oracle wrong | the whole scoreboard — a machine that says "done" having done something else is worse than one that refuses |
| **P2** | **Capability claims that name nothing a reader can check.** 34 of 158 evidence blocks point at no file; 8 point at files nobody wrote. | 42 / 158 entries | anyone deciding whether to trust a capability |
| **P3** | **Capability is a function of the shell, not of the machine.** `ruff`, `mypy`, `bandit`, `coverage`, `pytest`, `crosshair`, `z3`, `tree_sitter` are importable from `.venv` and from **none** of the system interpreters. Nothing installs-or-refuses, so 8 analyser families vanish silently on a clean box. | 45 of 158 shell out to a tool | every deployment that is not this sandbox |
| **P4** | **Ten acts nothing in the machine owns**: merge-conflict resolution, interactive debugging, crash reproduction, memory profiling, differential testing, schema migration, CI config, retry design, observability instrumentation, docstrings. | 10 of 43 probed acts | day-to-day senior engineering |
| **P5** | **Acts the machine owns but cannot be asked for.** `git bisect` needs a predicate no sentence states; two of six refactors are `NOT_REACHABLE` and four `ROUTE_ELSEWHERE` from a synthesised sentence. | 11 unreachable + 9 misrouted of 452 | the door, not the verbs |
| **P6** | **Whole domains sit at zero**: infrastructure/delivery 0/6, observability 0/5, dynamic analysis 1/9, performance engineering 2/6, services & concurrency 3/8, dependencies & build 2/10, documentation 1/4. | 44 absent acts of 135 | "build software end to end" |
| **P7** | **25 red compiler tests** in four defect families (DAG result invalid, over-eager compilation, stale guard assertions, door parity). | 25 of 133 | the compiler's word |
| **P8** | **Everything advanced is Python-only.** Tree-sitter parses a dozen languages; every refactor, repair loop and test generator is `python.*`. | 3 of 7 language acts | non-Python work |
| **P9** | **The office/visual family is 22 of 158 entries (14%)** — deprioritized by the owner, kept because it is already verified. | 22 | nothing, if left alone |
| **P10** | **Missing instruments in the flesh**: no `docker`/`podman`/`kubectl`/`terraform`, no `gdb`/`lldb`, no `strace`/`perf`/`valgrind`/`py-spy`, no `hypothesis`/`libcst`/`rope`, no `psutil`, no `sqlalchemy`/`alembic`. | measured below | any verb built on them would be a lie today |

**The single most critical problem is P1**, and it is not a missing capability — it is a *lie in the
accounting*. Every other number in this document (and in every earlier V-series document) is only
as good as the instrument that produced it, and that instrument currently certifies a SAST scanner
as a secret scanner and a CVE auditor. A machine that must eventually work unsupervised can survive
"I cannot do that"; it cannot survive "I did that" when it did something else.

---

## 1. How this was measured

```
registry                      canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json      158 entries
43-act front-door probe       execution_guard/hardcore_se_missing_verb_probe_v1.py     32 / 11 / 0
domain coverage (this doc)    execution_guard/hardcore_se_domain_coverage_v1.py         135 acts, 15 domains
evidence audit                execution_guard/capability_evidence_probe_v1.py --audit-pointers
reachability (452 rows)       execution_guard/live_solver_end_to_end_measurement_v1.py
compiler suites               pytest canonical/tests/test_goal_*_v1.py …               25 F / 108 P
environment probe             this document, §10 (binaries + importable modules)
```

```
43-ACT FRONT DOOR (through solve(), current HEAD)
  ANSWERED_BY_OWNING_CAPABILITY   32   of which 2 are WRONG TOOL by direct test (P1) -> 30 honest
  HONEST_REFUSAL                  11   (6 name the act, 5 name a wrong candidate)
  WRONG_TOOL by the probe's oracle 0   <- the oracle is lexical; see P1
  HOLLOW PASS                      0

REGISTRY EVIDENCE (158)
  OK 116 · pointer names nothing 34 · pointer names a file nobody wrote 8

REACHABILITY (452 rows = 158 registered + 294 receipt projections)
  REACHED_AND_BOUND 429 · NOT_REACHABLE 11 · ROUTED_ELSEWHERE 9 · BY EXPLICIT NAME 3

DOMAIN COVERAGE (135 acts a senior engineer performs)
  BOUND 60 · NAMED-ONLY 31 · ABSENT 44
```

---

## 2. The domain matrix

`BOUND` = some capability's `provides` names the act (a claim). `NAMED` = only a keyword mentions
it (vocabulary, not capability). `ABSENT` = nothing in the machine mentions it.

| domain | bound | named | absent | what bound looks like |
|---|---|---|---|---|
| version control | 10/17 | 4 | 3 | status, diff, commit, branch, checkout, revert, rebase, bisect, blame, stash |
| refactoring | 6/14 | 2 | 6 | rename symbol/parameter, extract, inline, move, change signature |
| static analysis | 10/13 | 1 | 2 | ruff, mypy, complexity, dead code, duplication, symbols, resolve, impact, tree-sitter index |
| testing | 6/10 | 2 | 2 | coverage, slice, scaffold, flake detect, property oracle, contract oracle |
| dynamic analysis | 1/9 | 4 | 4 | fuzz |
| performance engineering | 2/6 | 0 | 4 | diff perf gate, complexity metric |
| security & supply chain | 4/9 | 4 | 1 | bandit SAST, diff security gate, license, provenance |
| dependencies & build | 2/10 | 3 | 5 | wheel build, dependency add |
| data & persistence | 5/9 | 1 | 3 | sqlite create/verify, json, yaml, binary codecs |
| services & concurrency | 3/8 | 0 | 5 | http fetch, shell, async audit |
| infrastructure & delivery | 0/6 | 4 | 2 | — |
| observability | 0/5 | 2 | 3 | — |
| documentation | 1/4 | 0 | 3 | changelog |
| review & delivery flow | 7/8 | 0 | 1 | coverage gate, mutation gate, type gate, static triage, PR land, issue→PR |
| multi-language | 3/7 | 4 | 0 | tree-sitter parse, patch verify, python index |

The shape is unmistakable: **the machine is deep where the work is text analysis over one Python
file, and empty where the work is a running system** — processes, resources, services,
infrastructure, time.

Receipt: `canonical/astra_runtime/evidence/HARDCORE-SE-DOMAIN-COVERAGE-V1__RECEIPT.json`.

---

## 3. P1 — the door credits acts nothing owns

The 43-act probe reports `secret_scan` and `vulnerability_audit` as
`ANSWERED_BY_OWNING_CAPABILITY`, both selecting `python.toolchain.bandit_security.v1`.

Measured directly, on a fixture with three planted secrets:

```
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
DB_PASSWORD       = "hunter2"
TOKEN             = "ghp_012345678901234567890123456789012345"

bandit via the capability:  line 2 `DB_PASSWORD`      B105 hardcoded_password_string (low)
                            line 3 `TOKEN` (ghp_…)   B105 hardcoded_password_string (low)
                            line 1 `AWS_ACCESS_KEY_ID` (AKIA…)  NOT REPORTED
                            detection is by VARIABLE NAME, not by credential shape
advisory database:          none — bandit has no CVE/OSV data at all
```

So: **secret scanning is 2/3, and the miss is the interesting one** — a credential whose variable
happens not to be called `password`/`token` is invisible, which is exactly the shape real leaked
keys have. And vulnerability auditing is **0/0**: there is no advisory data to be right or wrong
about; it is a code-pattern scanner. Both are counted as answered because the probe's ownership oracle asks
whether the selected capability's `provides` *shares words* with the act, and `python.source.security.report`
shares "security".

Two defects, one root:

1. **A missing capability is being reported as a present one.** The fix is a real secret scanner
   (entropy + provider regexes, path-aware, with a planted-defect oracle) and a real advisory lane
   (OSV/`pip-audit` semantics, or an explicitly offline advisory snapshot). Until then the honest
   answer for both acts is a refusal that names the act.
2. **The instrument prefers wrong tools to refusals.** The ownership oracle must be *structural*
   (does the capability's `provides` name the act's object, or does its action template's target
   equal the act's target?) rather than lexical overlap. This is the same lesson Class B taught at
   the front door two units ago: a confident wrong answer costs more than a refusal — including when
   the confident wrong answer is the *measurement*.

---

## 4. P2 — capability claims that name nothing

```
OK (a verification block whose pointed-at files exist)        116 / 158
BLOCK_WITHOUT_ANY_POINTER (names no file a reader can check)  34 / 158
DANGLING (names a file nobody wrote)                           8 / 158
```

The 8 dangling are pinned by name in
`canonical/tests/test_capability_evidence_is_measured_not_asserted_v1.py`, so they cannot grow
silently — but 34 entries still assert a `verified` status with no artifact behind it. That is the
same defect P1 is, one layer down: **the registry's confidence is not backed by anything a reader
can open.**

---

## 5. P3 — capability is a function of the shell

```
this sandbox, .venv interpreter:   ruff ✓ mypy ✓ bandit ✓ coverage ✓ pytest ✓ crosshair ✓ z3 ✓ tree_sitter ✓
this sandbox, system interpreter:  ruff ✗ mypy ✗ bandit ✗ coverage ✗ pytest ✗ crosshair ✗ z3 ✗ tree_sitter ✗
absent binaries:                   docker podman kubectl terraform gdb lldb strace ltrace perf valgrind
                                   py-spy memray hypothesis libcst rope psutil sqlalchemy alembic shellcheck hadolint
present binaries:                  git gcc make node npm jq perl openssl gzip tar
```

Measured over the registry and the adapters behind it: **46 of 158 capabilities shell out** — 45 to
a `-m` tool (`ruff`, `mypy`, `bandit`, `coverage`, `pytest`, `crosshair`) and 23 to `git` (some do
both). On any interpreter but this one the tool-backed ones fail — and they fail as
`OWNED_BUT_FAILED`, which the scoreboard reads as a capability defect when it is an environment
fact. `git` is the exception that proves the rule: it is a real binary, present everywhere, which is
why the 12 VCS verbs are the only family that is environment-independent. The fix is one law at the door: **install-or-refuse** — if a capability declares a tool, the
door either satisfies it or refuses the request naming the tool, before anything is promised.

---

## 6. P4 — the ten acts nothing owns

Measured through the front door, each named by the sentence an engineer would write:

| act | what the door does now |
|---|---|
| merge-conflict resolution | `NO_VERIFIED_CAPABILITY_MATCH` (a symbol-resolve candidate wants `queries`) |
| interactive debugging | refuses; a static auditor is proposed and rejected (`R12`) |
| crash reproduction + shrink | refuses; a test-selection candidate is proposed and rejected (`R3`) |
| memory profiling | mis-compiles to an acceptance-measurement verb that wants `test_argv` |
| differential testing | refuses; the incremental indexer is proposed and rejected (`R14`) |
| schema migration | a sqlite writer wants `json_path` — the wrong object |
| CI configuration | `NO_VERIFIED_CAPABILITY_MATCH` |
| retry design | refuses; a symbol indexer is proposed and rejected (`R14`) |
| observability instrumentation | **now binds `python.packaging.dependency_add.v1`** and fails on `dependency:not_stated` — my own new verb became the candidate for "add logging" |
| docstrings | refuses; a static auditor is proposed and rejected (`R14`) |

Two of these are cheap reuse rather than new science: **crash reproduction** is the shrinker and
reproducer that `fuzz` already ships (§12), and **differential testing** is the same runner pointed
at two coordinates. **Memory profiling** is `tracemalloc` from the stdlib. **Observability** and
**CI config** are template-emission with a verification law.

---

## 7. P5 — owned but unaskable

| defect | measurement |
|---|---|
| `vcs.git.bisect.v1` exists and is verified, but the sentence cannot state the predicate: every bisect needs an `argv` that says "good here, bad there" | `FAIL_CLOSED__STATED_ACT_INPUTS_UNBOUND:argv:not_stated` |
| the refactor family from a synthesised sentence | `inline_function` **NOT_REACHABLE**, `move_function` **NOT_REACHABLE**, `extract_function`/`change_signature` **ROUTED_ELSEWHERE** |
| whole-surface reachability | 429 bound, **11 not reachable, 9 routed elsewhere, 3 reached only by explicit name** |

This is the same law three times: **a capability is reachable only through the words its registry
entry happens to use.** Fixing it once — one row, one rule, derived from `provides` rather than
hand-written keywords — moves 20 rows and two failing tests at once (P7).

---

## 8. P6 — the absent acts, by domain

The 44 acts nothing mentions, i.e. where a senior engineer would notice the machine is not there:

- **infrastructure & delivery (6):** CI config, container image, IaC, deploy, secret management, environment fit.
- **observability (5):** logging instrumentation, metrics instrumentation, tracing, log analysis, SLO.
- **performance (4):** big-O inference, hotspot ranking, allocation growth, query plans.
- **dynamic analysis (4):** memory profile, CPU profile, debugger/breakpoint, syscall trace.
- **services & concurrency (5):** retry policy, timeout policy, circuit breaker, task graph, local HTTP server.
- **dependencies & build (5):** install, upgrade, remove, lockfile, reproducible build, publish.
- **refactoring (6):** extract variable, encapsulate field, pull-up method, replace conditional, unused-import removal, split module.
- **version control (3):** cherry-pick, worktree, reflog-undo.
- **data (3):** schema migration, query optimisation, transaction/integrity.
- **documentation (3):** docstrings, README, API reference.
- **static analysis (2):** call graph, package dependency graph.
- **testing (2):** differential, golden/snapshot.

---

## 9. P9 — the office share, measured and set aside

22 of 158 entries (14%) are PDF / DOCX / XLSX / chart-raster / image / finance-document work. They
are verified and they work; they are **not** where the owner's goal lives, and nothing in this plan
spends a minute on them. They are listed only so the denominator is honest.

---

## 10. P10 — the instruments that are not here

Anything built on these would be a claim with nothing behind it today:

`docker`, `podman`, `kubectl`, `terraform`, `gdb`, `lldb`, `strace`, `ltrace`, `perf`, `valgrind`,
`py-spy`, `memray`, `hypothesis`, `libcst`, `rope`, `psutil`, `sqlalchemy`, `alembic`, `shellcheck`,
`hadolint`, `coverage` (as a binary), `z3` (as a binary), `cvc5`, `protoc`, `java`, `go`, `cargo`,
`rustc`, `clang`, `cmake`, `hyperfine`, `shellcheck`.

That is not a blocker list — it is a **design constraint**: every verb in the plan below is built on
what is present (`git`, `gcc`, `make`, `node`, `npm`, `jq`, `perl`, `openssl`, stdlib
`ast`/`subprocess`/`tracemalloc`/`cProfile`/`sqlite3`/`zlib`, and the `.venv` analysers), and
anything that would need an absent instrument is refused by name instead of faked.

---

## 11. P7 — the 25 red compiler tests

Four families, each a law with more than one failing row behind it:

| family | rows | where it belongs |
|---|---|---|
| multi-step DAG returns `FAIL__CAPABILITY_DAG_RESULT_INVALID` / `NO_OBSERVED_EFFECT` | 5 | the DAG executor, not the compiler |
| a sentence that should stay open compiles anyway (`DID NOT RAISE`) or binds wrong code | 5 | over-eager compilation |
| guard-code assertions older than the guard (`R1`/`R3` vs `R12`/`R14`) | 3 | stale tests — the guard improved |
| reachability counts, quoted literals, door parity, `r9` rate | 12 | Class D, measured as a rate |

Red is not authority; the owner decides targets. But 25 red rows in four families is a work queue,
not a fog.

---

## 12. What is already closed (do not re-do)

| act | capability | measured |
|---|---|---|
| dependency add, wheel build | `python.packaging.{dependency_add,build_package}.v1` | answered, evidenced, 10/10 pins |
| inline function | `python.refactor.inline_function.v1` | answered, evidenced, 11/11 pins |
| fuzz (generate → isolate → shrink → reproduce) | `python.dynamic.fuzz.v1` | answered, evidenced, 11/11 pins |

Those four verbs took the 43-act score from 28 answered to 32, and each was measured by the same
instruments this document uses — including the three laws each one gained *because* the measurement
caught its own bug.

---

## 13. The plan, ranked by capability per hour

Reuse first, and nothing here needs an absent instrument.

| # | work | closes | why it is cheap | cost |
|---|---|---|---|---|
| 1 | **Real `secret_scan`** (entropy + provider regexes, path-aware, planted-defect oracle) | P1 (one of two miscredits) | one module over `pathlib` + `re`; the artifact law exists | ~1 unit |
| 2 | **Real `vulnerability_audit`** (offline advisory snapshot or explicit refusal naming the missing database) | P1 | `pip-audit`-shaped over the installed metadata; must say "no database" if there is none | ~1 unit |
| 3 | **Structural ownership oracle in the probe** | P1 root | the probe already knows the selected capability and its `provides`; the act table needs an object, not a word | ~½ unit |
| 4 | **install-or-refuse at the door** | P3 (45 tool-backed capabilities) | the toolchain is already declared; nothing enforces it | ~1 unit |
| 5 | **`crash_repro` + `differential_test`** | P4 (2 acts), P6 | the runner, the shrinker and the reproducer exist inside `fuzz` | ~1 unit for both |
| 6 | **`memory_profile` + `cpu_profile` + `benchmark`** | P6 (3 acts) | `tracemalloc`, `cProfile`, `timeit` — stdlib, one module | ~1 unit |
| 7 | **routability law** (one row → one rule) | P5 (20 rows, 2 tests) | derived from `provides` instead of hand-written keywords | ~1–2 units |
| 8 | **`schema_migration` + data integrity** | P4, P6 | `sqlite3` is present; the migration is a transaction plus a verification law | ~1 unit |
| 9 | **`merge_conflict`** | P4 | `git merge` exists; conflict markers are text; the resolution gate is a test run | ~1 unit |
| 10 | **4 compiler defect families** | P7 (25 rows) | each is one law, not 25 patches | ~2 units |
| 11 | **34 pointerless evidence blocks** | P2 | each needs the lane that measured it to write one line | ~1 unit, mechanical |
| 12 | **`ci_config` + observability instrumentation** | P4, P6 | template emission with a verification law | ~1 unit each |
| 13 | **`docstrings`** | P4 | last on purpose: the only act here that needs judgement, and no model may supply it | — |

Rules that do not change: **reuse before synthesis**, **measure, never assert**, a red row is not an
authority, and no AI model participates in Brain-credited producer cognition.

---

## 14. How to reproduce every number here

```
PYTHONPATH=. .venv/bin/python execution_guard/hardcore_se_missing_verb_probe_v1.py --json /tmp/a.json
PYTHONPATH=. .venv/bin/python execution_guard/hardcore_se_domain_coverage_v1.py
PYTHONPATH=. .venv/bin/python execution_guard/capability_evidence_probe_v1.py --audit-pointers
PYTHONPATH=. .venv/bin/python -m pytest canonical/tests/test_goal_front_compiler_v1.py \
    canonical/tests/test_goal_compiler_world_binding_v1.py \
    canonical/tests/test_live_brain_route_admission_v1.py -q
```

A number in this document that no longer reproduces is a bug in this document, not a target.
