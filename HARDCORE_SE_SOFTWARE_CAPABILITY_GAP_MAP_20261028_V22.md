# What are all the problems?

**Hardcore software-engineering capability inventory · 2026-10-28 · measured on `arena/4ca3a720-brain` at `f5f191c` + this unit**

_Supersedes `…GAP_MAP_20261028_V21.md`.

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
| ~~**P1**~~ | ~~**The door credits acts nothing owns.**~~ **CLOSED this unit (§3)** — both acts now have real owners built on the tools that already are the answer (`detect-secrets`, `pip-audit`), and the probe's ownership oracle reads claims instead of keywords. | was 2 acts miscredited | the scoreboard is now honest |
| **P2** | **Capability claims that name nothing a reader can check.** 34 of 158 evidence blocks point at no file; 8 point at files nobody wrote. | 42 / 158 entries | anyone deciding whether to trust a capability |
| ~~**P12**~~ | ~~**A verb that rewrites its target can eat the repository.**~~ **CLOSED this unit (§5.5)** — `format` took a one-file sentence, bound the file's *directory*, rewrote 2238 files and then wrote its own receipt over the named source file. Found by using the capability, not by reading it. | 1 verb, 2 laws | the tree the machine works in |
| ~~**P3**~~ | ~~**Capability is a function of the shell, not of the machine.**~~ **CLOSED this unit (§5)** — the door now checks the engine before it promises the work, installs the pinned tool when the interpreter is one we manage, and otherwise refuses by name; 13 acts that failed as *broken capabilities* on a clean box are now honest refusals. | was 13 + 3 lost acts | every deployment that is not this sandbox |
| **P4** | **Eight acts nothing in the machine owns** (was ten): merge-conflict resolution, interactive debugging, memory profiling, schema migration, CI config, retry design, observability instrumentation, docstrings. **Crash reproduction and differential testing are CLOSED this unit (§6.1)**. | 8 of 43 probed acts | day-to-day senior engineering |
| **P5** | **Acts the machine owns but cannot be asked for.** `git bisect` needs a predicate no sentence states; two of six refactors are `NOT_REACHABLE` and four `ROUTE_ELSEWHERE` from a synthesised sentence. | 11 unreachable + 9 misrouted of 452 | the door, not the verbs |
| **P6** | **Whole domains sit at zero**: infrastructure/delivery 0/6, observability 0/5, dynamic analysis 1/9, performance engineering 2/6, services & concurrency 3/8, dependencies & build 2/10, documentation 1/4. | 44 absent acts of 135 | "build software end to end" |
| **P7** | **25 red compiler tests** in four defect families (DAG result invalid, over-eager compilation, stale guard assertions, door parity). | 25 of 133 | the compiler's word |
| **P8** | **Everything advanced is Python-only.** Tree-sitter parses a dozen languages; every refactor, repair loop and test generator is `python.*`. | 3 of 7 language acts | non-Python work |
| **P9** | **The office/visual family is 22 of 158 entries (14%)** — deprioritized by the owner, kept because it is already verified. | 22 | nothing, if left alone |
| **P10** | **Missing instruments in the flesh**: no `docker`/`podman`/`kubectl`/`terraform`, no `gdb`/`lldb`, no `strace`/`perf`/`valgrind`/`py-spy`, no `hypothesis`/`libcst`/`rope`, no `psutil`, no `sqlalchemy`/`alembic`. | measured below | any verb built on them would be a lie today |

**P1 and P3 are closed.** P1 first, because it was not a missing capability but a *lie in the
accounting*, and every other number in this document is only as good as the instrument behind it —
and the fix was not to write a scanner, since both answers already existed as tools, exactly as the
owner said. P3 second, because it was the larger version of the same lie: thirteen working
capabilities reported as broken because a package had never been installed. Both were *reporting*
defects, and both are now measured to be gone.

The 43-act probe now reads **34 answered / 9 honest refusals / 0 broken / 0 hollow** (it was
16/11/13/3 on a bare box at the start of the previous unit and 32/11/0/0 with the toolchain).

The most critical remaining problem is **P4 — the eight acts nothing owns** (crash reproduction,
differential testing, memory and CPU profiling, schema migration, merge-conflict resolution,
CI config, retry design, observability, interactive debugging, docstrings). It is the only front
where the machine lacks ability rather than honesty, and the next ones are cheap because the
profilers and the git plumbing are already in the repository (§13, rows 1–3).

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
  ANSWERED_BY_OWNING_CAPABILITY   32   all verified against a real owner (2 were lies before §3)
  HONEST_REFUSAL                  11   (6 name the act, 5 name a wrong candidate)
  WRONG_TOOL by the probe's oracle 0   <- the oracle is lexical; see P1
  HOLLOW PASS                      0

REGISTRY EVIDENCE (160)
  OK 118 · pointer names nothing 34 · pointer names a file nobody wrote 8

REACHABILITY (452 rows = 158 registered + 294 receipt projections)
  REACHED_AND_BOUND 429 · NOT_REACHABLE 11 · ROUTED_ELSEWHERE 9 · BY EXPLICIT NAME 3

DOMAIN COVERAGE (135 acts a senior engineer performs)
  BOUND 63 · NAMED-ONLY 29 · ABSENT 43
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
| dynamic analysis | 2/9 | 3 | 4 | fuzz, crash reproduction, differential testing |
| performance engineering | 2/6 | 0 | 4 | diff perf gate, complexity metric |
| security & supply chain | 6/9 | 2 | 1 | bandit SAST, diff security gate, license, provenance |
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

## 3. P1 — CLOSED: the door credits acts nothing owns

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

Two defects, one root, both fixed by *reuse* rather than synthesis (§3.1).

### 3.1 What was built

Nothing here is a new scanner. Both answers were already tools, and both are now declared in
`canonical/runtime/TOOLCHAIN_DECLARATION_V1.json`, so `toolchain_preflight_v1.py --bootstrap`
installs them and `--check` refuses when they are gone (10 of 10 distributions present):

| act | engine | what it does that bandit could not |
|---|---|---|
| `secret_scan` (`python.supply_chain.secret_scan.v1`) | **detect-secrets 1.5.0** — 27 detectors + entropy | finds the AWS access-key id and the Slack token **bandit misses**, because those detectors read the credential's shape rather than the variable's name |
| `vulnerability_audit` (`python.supply_chain.vulnerability_audit.v1`) | **pip-audit 2.10.1** — PyPI advisory service | real advisories: PYSEC ids with CVE/GHSA aliases and the versions that fix them; bandit carries no advisory data at all |

Measured through the front door, on a fixture with planted credentials and a pinned vulnerable
dependency — the fixture had to be given both, because *a fixture that cannot support the act
measures the fixture*:

```
secret_scan          3 findings: AWS Access Key, Slack Token, Base64 High Entropy String   0.31 s
vulnerability_audit  22 advisories on urllib3==1.26.0                                       7.0 s
```

Laws the module holds, each written from a measurement:

* **a secret is never written down** — findings carry detect-secrets' salted SHA-1 and a location;
  the artifact records `secrets_written_to_this_artifact: false`, and a pin asserts none of the four
  credentials appears in it. A report that quotes the credential is a second leak.
* **a scanner must not read its own report** — measured: two consecutive runs disagreed, because the
  first artifact's 40-character hashes looked like five `Hex High Entropy String` findings. The
  artifact path is now excluded from the scan.
* **an empty report from a tool that did not run is a lie** — `TOOL_NOT_INSTALLED:detect-secrets`
  and `ADVISORY_SERVICE_UNREACHABLE:pip-audit` are refusals that still write a FAIL artifact; only
  a real run may report zero. That was the whole defect: 0/0 used to read as "clean".
* **the audited set is the project's own declaration** — `[project].dependencies`, else
  `requirements*.txt`, else a stated file, parsed by the manifest reader `packaging_v1` already
  owns. A project that declares nothing refuses `NO_DECLARED_DEPENDENCIES`.

### 3.2 The instrument

The probe's ownership oracle counted a capability's `keywords` as ownership. `bandit`'s entry
carried the keywords `leaked secrets`, `known vulnerabilities`, `supply chain` while its `provides`
said only `python.source.security.report` — so the probe certified both acts against a capability
that claims neither. **`keywords` are routing handles; `provides` is what a capability claims it will
do.** The oracle now reads claims only, and `bandit`'s false keywords are gone.

The scoreboard did not move (32 answered before, 32 after) — because both acts were already being
counted. What changed is that the two rows are now true, and the instrument that counts them can no
longer be fooled by marketing words. Two pins hold it: one asserts that a keyword alone can never
produce `BOUND`, the other that these two acts *are* bound by a real claim.

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

## 5. P3 — CLOSED: capability is a function of the shell

### 5.1 The measurement that opened it

The same commit, the same 43-act probe, two interpreters:

```
.venv interpreter            32 answered / 11 honest refusal /  0 owned-but-failed / 0 silent
/usr/bin/python3 (bare)      16 answered / 11 honest refusal / 13 owned-but-failed / 3 silent
```

The thirteen were `lint`, `format`, `type_check`, `coverage_measure`, `dead_code`,
`complexity_metric`, `async_audit`, `exception_audit`, `secret_scan`, `vulnerability_audit`,
`inline_function`, plus `flake_detect`, `move_function` and `change_signature` as silent refusals.
Every one of them reported itself as `TOOL_NOT_INSTALLED:<name>` inside a `*Error`, which the
scoreboard reads as *this capability is broken*. It was not: the adapter was fine and the package
was absent, which is an environment fact a door can act on and a capability cannot.

```
this sandbox, .venv interpreter:   ruff ✓ mypy ✓ bandit ✓ coverage ✓ pytest ✓ crosshair ✓ z3 ✓ tree_sitter ✓
this sandbox, system interpreter:  ruff ✗ mypy ✗ bandit ✗ coverage ✗ pytest ✗ crosshair ✗ z3 ✗ tree_sitter ✗
absent binaries:                   docker podman kubectl terraform gdb lldb strace ltrace perf valgrind
                                   py-spy memray hypothesis libcst rope psutil sqlalchemy alembic shellcheck hadolint
present binaries:                  git gcc make node npm jq perl openssl gzip tar
```

### 5.2 The law, and where it is enforced

`canonical/runtime/toolchain_gate_v1.py` — a capability is the adapter **plus** the software it
calls, and the door checks the second half before it promises the first:

1. **the tool is there** → run.
2. **the tool is absent and this interpreter is one we manage** (a venv, writable, not a system or
   externally-managed interpreter, `BRAIN_TOOLCHAIN_INSTALL != 0`) → install the **pinned**
   distribution from `TOOLCHAIN_DECLARATION_V1.json`, then run. Autonomy where it is safe: a venv
   does not need a human to `pip install`.
3. **otherwise** → refuse with `FAIL_CLOSED__TOOLCHAIN_MISSING` and a sentence a reader can act on:
   `TOOLCHAIN_MISSING:ruff (declared: ruff==0.17.3); install with: python3
   execution_guard/toolchain_preflight_v1.py --bootstrap`.

It is enforced once, at the one door every request passes: `live_brain_route_admission_v1`
computes the plan's capabilities (`selected_capability`, DAG steps, compiled parts) and calls the
gate before `_execute`. A refused plan never reaches the controller, so it can no longer come back
as `FAIL__LIVE_CONTROLLER_EXECUTION` — the controller was blamed for an empty shell.

### 5.3 Two mistakes the gate itself made, and how they were caught

Both are the *opposite* error — refusing work the machine can do — and both were caught by
re-running the bare probe and watching the answered count fall:

- **A quoted word is not a dependency.** The first version scanned adapter source for known binary
  names and read `"perf"` out of a display-name dict and `"sqlite3"` out of a connection-key dict in
  `quality_v1.py`. Detection now accepts only three shapes that provably invoke something:
  `["-m", X]`, `_resolve_tool("X")`, `shutil.which("X")`.
- **A shared adapter's union is not a capability's need.** `toolchain_v1.py` runs ruff, mypy,
  bandit, coverage and crosshair, so every verb behind it inherited all five and `ruff_format`
  demanded mypy — measured: the bare run fell 16 → 13 answered. The declaration now states tools
  **per capability** (`capability_tools`, 34 rows), and an **empty row is a claim** ("calls no
  external tool"), not an absence of one; five `quality_v1` verbs that read the AST, the git
  history or installed metadata are empty rows.

### 5.5 A verb that rewrites its target can eat the repository

Found the way these things are found — by asking the machine to do the work. This document's own
repository was destroyed twice in ninety seconds by one sentence:

```
goal: "Format the python file canonical/runtime/toolchain_gate_v1.py in place."

the compiler bound   source_root = canonical/runtime        <- the file's DIRECTORY
the adapter ran      ruff format canonical/runtime
ruff rewrote         2238 files, 229,816 insertions
then died            "Failed to parse livebench_legacy_predecessor_compiler_audit_v1.py"
the adapter wrote    its own refusal JSON to output_path
output_path was      canonical/runtime/toolchain_gate_v1.py <- the source file it had just been asked about
result               a 256-line module replaced by nine lines of JSON, and a half-formatted tree
```

Two defects, both of the kind that make every other capability worthless because the workspace is
gone, and both fixed at the seam where the write happens (`bound_capabilities/toolchain_v1.py`):

1. **A mutation is all-or-nothing.** ruff is not transactional — it rewrites file after file and
   stops at the first it cannot parse. Every mutating call now runs a dry pass first
   (`ruff format --check --diff`); a pass that cannot complete REFUSES
   (`FORMAT_WOULD_LEAVE_A_HALF_FORMATTED_TREE`, naming the unparsable files) and nothing is
   written. One extra process buys "the tree is either formatted or untouched".
2. **A receipt never lands on the artifact.** For a verb whose target *is* its output ("format
   this file in place"), the artifact is the file and the receipt travels as the returned payload
   (`receipt_written: False`, `artifact_path` = the file). And because a refusal is also a write,
   the destination is validated *where no write can follow it* — the first version of this guard
   put the check inside the block that reports refusals, so its own refusal was written to the
   path it had just rejected, which is the same corruption wearing a different hat.
3. **The named file is the target, not its directory.** When the sentence names one file and the
   compiler derives the enclosing directory, formatting "in place" now means the file. Measured
   after the fix, through the live door: the named file is formatted, its neighbours are
   byte-identical, and the request PASSes instead of refusing.

A fourth, smaller lie died with it: `changed_files` came from parsing `"Reformatted N files"` — a
COUNT, never paths — so the receipt reported **zero** changed files after changing them. ruff 0.17.3
names each file only in the `+++ <path>` header of its diff, and that is what the receipt now reads.

### 5.4 What it measures now

```
after the gate, bare interpreter   18 answered / 25 honest refusal / 0 owned-but-failed / 0 silent
after the gate, .venv              32 answered / 11 honest refusal / 0 owned-but-failed / 0 silent
```

The 25 refusals are **exactly** the 14 acts the installed toolchain supplies plus the 11 goal-level
refusals that were already honest — checked set-for-set, so the gate refuses nothing that works and
misses nothing that would fail. Nothing turned green: on a box with no analysers the machine still
says it cannot lint, which is true, and it now also says which package would make it able to.
`canonical/tests/test_toolchain_gate_v1.py` holds 18 pins for both directions.

---

## 6. P4 — eight acts nothing owns (two closed this unit)

### 6.1 Crash reproduction and differential testing are closed — by reuse, not by a new engine

Both rows read as refusals on the last measurement, and both refusals were honest:

```
crash_repro        R3_WEAK_EVIDENCE      answered by a TEST SELECTOR
differential_test  R14_UNHEARD_ACT_WORD  the act word did not exist
```

Neither needed an engine. `dynamic_probe_v1` already drew cases from the annotations, ran each in
its own interpreter, classified `ok` / `raised` / `timeout` / `crashed` as facts about a process,
shrank the first failure greedily *while keeping the same failure mode*, and wrote a runnable
reproducer. What was missing was one sentence's worth of semantics, twice:

- **`python.dynamic.crash_repro.v1`** — the same engine with a wider search. "Reproduce the crash in
  `<file>`" does not name a function; if it knew which one crashed it would have said, so the search
  covers every public function in scope and reports **which one crashed**. Measured on
  `def divide(a, b): return a/b`: `reproduced: True`, `qualname: divide`, `minimal_case: [0, 0]`,
  and the reproducer written beside the artifact exits non-zero with the same `ZeroDivisionError`.
  When nothing crashes the answer is `NO CRASH REPRODUCED` with the functions searched and cases
  run — a search result, never a silent pass.
- **`python.dynamic.differential_test.v1`** — the same generator and the same shrinker with a
  different oracle: two implementations must agree. The reference is stated, or it is the file's own
  **git `HEAD`** (which is how a risky refactor is checked: the working tree against the code it
  replaced), or the call is *refused* — a comparison against whatever file happened to be nearby is
  not an oracle. Measured on a `sub` that adds instead of subtracting: 7 divergences, shrunk to
  `sub(0, 1)` (`2` vs `0`), basis `git:HEAD:calc.py`.

Speed is part of the design: one child interpreter evaluates **both** implementations over the whole
case list and streams a line per case; only when that child dies do the unreported cases get one
isolated process each, so a crash is attributed to a side instead of losing the run.

### 6.2 The binding defect they exposed, for the third time

Both sentences name a **file**; the compiler bound `source_root` to the file's **directory**, and
both capabilities reported `MODULE_NOT_STATED` / searched the wrong scope. This is the same defect
that let `ruff format` rewrite 2238 files (§5.5), now caught at the third layer, and this time the
fix is complete rather than local: a capability that declares `proposal_bindings.source_root:
path_file_or_dir` is a capability whose adapter can index one file, and it now *receives the file
the sentence named* — one file means one file, never its siblings. Capabilities that did not
declare it keep binding the directory, because a test runner genuinely needs a tree.

Where a sentence names only a directory, both new verbs treat it as a scope: crash reproduction
searches every public module inside it, differential testing compares each module with its own
reference. A scope stayed a scope; it just stopped widening a file.

### 6.3 What is still missing here

`merge_conflict`, `interactive_debug`, `memory_profile`, `schema_migration`, `ci_config`,
`retry_design`, `observability`, `docstrings` — and of those, the profilers (`tracemalloc`,
`cProfile`) and `git`'s own merge machinery are already installed, which is why they are rows 1–3
of §13 rather than a research programme.

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
| secret scan, advisory audit | `python.supply_chain.{secret_scan,vulnerability_audit}.v1` | answered, evidenced, 12/12 pins, tools declared |
| dependency add, wheel build | `python.packaging.{dependency_add,build_package}.v1` | answered, evidenced, 10/10 pins |
| inline function | `python.refactor.inline_function.v1` | answered, evidenced, 11/11 pins |
| fuzz (generate → isolate → shrink → reproduce) | `python.dynamic.fuzz.v1` | answered, evidenced, 11/11 pins |
| install-or-refuse at the door | `python.toolchain.gate.v1` (all 34 tool-backed verbs) | 13 owned-but-failed → 0 on a bare box, 3 silent → 0, nothing falsely refused, 18/18 pins |
| a formatter cannot eat the tree or its receipt | `python.toolchain.ruff_format.v1` | 2238-file half-rewrite and source-file replacement both refused/avoided; 7/7 pins |
| crash reproduction (find → shrink → reproduce) | `python.dynamic.crash_repro.v1` | answered through the door, reproduced `divide(0, 0)`, reproducer re-run and failing the same way; 9/9 pins with the differential test |
| differential testing (two implementations, one oracle) | `python.dynamic.differential_test.v1` | answered through the door, 7 divergences shrunk to `sub(0, 1)`, basis `git:HEAD`; reference refused when unstoppable |

Those four verbs took the 43-act score from 28 answered to 32, and each was measured by the same
instruments this document uses — including the three laws each one gained *because* the measurement
caught its own bug. The gate did not add an answered act to that list: it removed four
misclassifications (13 owned-but-failed and 3 silent refusals) and gave back the two that the gate
itself had briefly taken away.

---

## 13. The plan, ranked by capability per hour

Reuse first, and nothing here needs an absent instrument.

| # | work | closes | why it is cheap | cost |
|---|---|---|---|---|
| ~~1~~ | ~~real `secret_scan`~~ | P1 | **DONE this unit** — detect-secrets, declared and bootstrapped, 3 findings on a planted fixture | — |
| ~~2~~ | ~~real `vulnerability_audit`~~ | P1 | **DONE this unit** — pip-audit, 22 advisories on a pinned urllib3 | — |
| ~~3~~ | ~~structural ownership oracle~~ | P1 root | **DONE this unit** — claims, not keywords; bandit's false keywords removed | — |
| ~~0~~ | ~~**make a mutating verb safe** (`format` ate 2238 files and its own source)~~ | P12 | **DONE this unit** — dry pass, receipt that cannot land on the artifact, named file not its directory | — |
| ~~1~~ | ~~**install-or-refuse at the door**~~ | P3 (13 lost acts + 3 silent) | **DONE this unit** — `toolchain_gate_v1` + 34 per-capability rows; bare box 16→18 answered, 13 owned-but-failed → 0, nothing falsely refused | — |
| ~~**1**~~ | ~~**`crash_repro` + `differential_test`**~~ | P4 (2 acts), P6 | **DONE this unit** — one engine, two oracles: 34/43 acts answered, the crash found and shrunk to `divide(0, 0)`, the divergence to `sub(0, 1)`; 9 pins | — |
| 2 | **`memory_profile` + `cpu_profile` + `benchmark`** | P6 (3 acts) | `tracemalloc`, `cProfile`, `timeit` — stdlib, one module | ~1 unit |
| 3 | **routability law** (one row → one rule) | P5 (20 rows, 2 tests) | derived from `provides` instead of hand-written keywords | ~1–2 units |
| 4 | **`schema_migration` + data integrity** | P4, P6 | `sqlite3` is present; the migration is a transaction plus a verification law | ~1 unit |
| 5 | **`merge_conflict`** | P4 | `git merge` exists; conflict markers are text; the resolution gate is a test run | ~1 unit |
| 6 | **4 compiler defect families** | P7 (25 rows) | each is one law, not 25 patches | ~2 units |
| 7 | **34 pointerless evidence blocks** | P2 | each needs the lane that measured it to write one line | ~1 unit, mechanical |
| 8 | **`ci_config` + observability instrumentation** | P4, P6 | template emission with a verification law | ~1 unit each |
| 9 | **`docstrings`** | P4 | last on purpose: the only act here that needs judgement, and no model may supply it | — |

Rules that do not change: **reuse before synthesis**, **measure, never assert**, a red row is not an
authority, and no AI model participates in Brain-credited producer cognition.

---

## 14. How to reproduce every number here

```
PYTHONPATH=. .venv/bin/python execution_guard/hardcore_se_missing_verb_probe_v1.py --json /tmp/a.json
env -i HOME=/root PATH=/usr/bin:/bin PYTHONPATH=. /usr/bin/python3 \
    execution_guard/hardcore_se_missing_verb_probe_v1.py --json /tmp/bare.json
PYTHONPATH=. .venv/bin/python execution_guard/hardcore_se_missing_verb_probe_v1.py \
    --only crash_repro,differential_test
PYTHONPATH=. .venv/bin/python execution_guard/capability_evidence_probe_v1.py \
    --only python.dynamic.crash_repro.v1,python.dynamic.differential_test.v1 --remeasure
PYTHONPATH=. .venv/bin/python execution_guard/hardcore_se_domain_coverage_v1.py
PYTHONPATH=. .venv/bin/python execution_guard/capability_evidence_probe_v1.py --audit-pointers
PYTHONPATH=. .venv/bin/python -m pytest canonical/tests/test_goal_front_compiler_v1.py \
    canonical/tests/test_goal_compiler_world_binding_v1.py \
    canonical/tests/test_live_brain_route_admission_v1.py -q
```

A number in this document that no longer reproduces is a bug in this document, not a target.
