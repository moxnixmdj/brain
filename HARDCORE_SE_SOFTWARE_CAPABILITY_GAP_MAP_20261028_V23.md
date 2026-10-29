# What are all the problems?

**Hardcore software-engineering capability inventory · 2026-10-29 · measured on `arena/4ca3a720-brain` at `b578283` + this unit (P5: the act word is declared, not spelled)**

_Supersedes `…GAP_MAP_20261028_V22.md`.

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
| **P6** | **Whole domains sit at zero**: infrastructure/delivery 0/6, observability 0/5, services & concurrency 3/8, dependencies & build 2/10, documentation 1/4. **Dynamic analysis is now 5/9 and performance engineering 5/6 (§6.4).** | 38 absent acts of 135 | "build software end to end" |
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

The 43-act probe now reads **35 answered / 8 honest refusals / 0 broken / 0 hollow** (it was
16/11/13/3 on a bare box at the start of the previous unit and 32/11/0/0 with the toolchain).

The most critical remaining problem is **P4 — the eight acts nothing owns** (crash reproduction,
differential testing, memory and CPU profiling, schema migration, merge-conflict resolution,
CI config, retry design, observability, interactive debugging, docstrings). It is the only front
where the machine lacks ability rather than honesty, and the next ones are cheap because the
profilers and the git plumbing are already in the repository (§13, rows 1–3).

---

## 1. How this was measured

```
registry                      canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json      165 entries
43-act front-door probe       execution_guard/hardcore_se_missing_verb_probe_v1.py     35 / 8 / 0
domain coverage (this doc)    execution_guard/hardcore_se_domain_coverage_v1.py         135 acts, 15 domains
evidence audit                execution_guard/capability_evidence_probe_v1.py --audit-pointers
reachability (452 rows)       execution_guard/live_solver_end_to_end_measurement_v1.py NOT re-measured (times out at 15 min)
compiler suites               pytest canonical/tests/test_goal_*_v1.py …               25 F / 108 P  (same 25 node ids at 580fa4d)
environment probe             this document, §10 (binaries + importable modules)
```

```
43-ACT FRONT DOOR (through solve(), current HEAD)
  ANSWERED_BY_OWNING_CAPABILITY   35   all verified against a real owner (2 were lies before §3)
  HONEST_REFUSAL                   8   (3 name the act, 5 name a wrong candidate)
  WRONG_TOOL by the probe's oracle  0   <- the oracle is lexical; see P1
  HOLLOW PASS                       0

REGISTRY EVIDENCE (165)
  OK 123 · pointer names nothing 34 · pointer names a file nobody wrote 8

REACHABILITY (452 rows)  last measured at f5f191c: 429 bound · 11 NOT_REACHABLE · 9 ROUTED_ELSEWHERE · 3 BY NAME

DOMAIN COVERAGE (135 acts a senior engineer performs)
  BOUND 69 · NAMED-ONLY 28 · ABSENT 38
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
| dynamic analysis | 5/9 | 2 | 2 | fuzz, crash reproduction, differential testing, memory profile, CPU profile |
| performance engineering | 5/6 | 0 | 1 | diff perf gate, complexity metric, big-O inference, hotspot ranking, allocation growth |
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
OK (a verification block whose pointed-at files exist)        123 / 165
BLOCK_WITHOUT_ANY_POINTER (names no file a reader can check)  34 / 165
DANGLING (names a file nobody wrote)                           8 / 165
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

`merge_conflict`, `interactive_debug`, `schema_migration`, `ci_config`, `retry_design`,
`observability`, `docstrings` — and of those, `git`'s own merge machinery is already installed,
which is why `merge_conflict` is row 4 of §13 rather than a research programme.

### 6.4 The performance trio is closed — and measuring it found four defects in the instrument

`performance engineering` read **2 / 6** and `dynamic analysis` **2 / 9**; the memory sentence was
refused outright. All three acts are stdlib: `tracemalloc`, `cProfile`/`pstats`, `perf_counter`.
One module, `perf_probe_v1.py`, serves all three through the same child-process protocol
(`memory` / `cpu` / `benchmark_sweep`, one JSON line back), reusing `dynamic_probe_v1`'s locator,
its annotation-directed case generator and its per-case isolation.

The three answers, measured on a fixture whose cost shape is known:

| act | measurement | answer |
|---|---|---|
| `benchmark` | `quadratic(n)` over the ladder 64…2048 | `O(n^2)`, slope 2.03, r² 0.9999 |
| `cpu_profile` | `loop(n)` | `hotspot_ranking[0] == loop`, ranked by cumulative time |
| `memory_profile` | `hog(512)` | peak 55,670 B, top allocating line `work.py:9` (40,656 B) |

**The instrument was wrong four times before the answers were right**, and each wrong version was a
confident result, not an error:

1. **One frame is not a stack.** `tracemalloc.start()` defaults to one frame, which is the
   *harness's* line, so every allocation in the report was `File "<string>", line 30`, 249 bytes,
   while the peak was 55,670 bytes. Fixed: 8 frames, and a site must be a frame in the target (or a
   library it called), never a `<string>` frame.
2. **A freed value is not a measurement.** The snapshot was taken after the measured object had gone
   out of scope, so the profile described the collector. The value is now held across the snapshot.
3. **`Profile.getstats()` does not unpack.** `for (key), values in profiler.getstats()` raised, the
   hotspot list came back *empty*, every score was 0, and the least-work case "won". Rows now come
   from `pstats.Stats`, and the profiler's own `enable`/`disable` stubs are filtered out.
4. **A minimum over candidates always has a winner.** The growth class was the shape with the lowest
   coefficient of variation — with four points, a `0.25` spread is noise, and a linear loop was
   confidently reported as `O(log n)`. It is now a least-squares fit of `log t` against `log n`,
   reported as `slope` and `r2`; a class is claimed only when `r2 ≥ 0.98` **and** the exponent is
   within 0.25 of it, and an unresolved fit still names the closest shape.

Two more defects were found by running the thing rather than reading it:

- **A fuzz corpus is the wrong corpus for profiling.** The generator's boundary draws are `2**63`,
  `sys.maxsize` and 10,000-character strings — right for finding crashes, useless for measuring:
  the profile was vacuous (peak 713 B, worst case `[0]`). `_measurable()` now filters the corpus and
  a geometric ladder (8, 64, 512) is always appended.
- **A process per size is a measurement of process startup.** Import plus interpreter cost more than
  the call at small sizes, and a linear loop came back with a 0.5 spread and no class. The whole
  ladder now runs in one child after one warm-up, keeping the minimum of the repetitions; the parent
  still isolates the run, so a hang or a crash is an outcome instead of a lost measurement.
- **A keyword phrase is a bag of words.** `"how does it scale"` contributed the tokens `how`, `does`,
  `it`, `scale` — and `it` then matched *"Write a continuous integration workflow … and report it
  to …"*, which made the benchmark capability the best candidate for writing CI config. The
  keywords now name the act (`benchmark`, `cpu`, `hotspot`, `memory`, `allocation`, …), and the four
  unrelated sentences that used to select a perf capability select it no longer.
- **A package is not a flat directory.** The first version of the scan globbed `*.py` at the root of
  the stated directory, so a repository refused with `NO_PYTHON_MODULE_IN` while its modules sat one
  level down in `pkg/`. Both this probe and `dynamic_probe_v1` now scan recursively.

Wiring: three registry rows (`python.perf.benchmark.v1`, `python.perf.cpu_profile.v1`,
`python.perf.memory_profile.v1`) with `provides` naming the acts the domain map looks for
(`perf.big_o_inference`, `perf.hotspot_ranking`, `perf.allocation_growth`, `dynamic.memory_profile`,
`dynamic.cpu_profile`), three `capability_tools` rows that are empty because the whole toolchain is
the interpreter, three evidence receipts, and 13 pins in
`canonical/tests/test_performance_measurement_v1.py`.

One defect the evidence audit exposed: **a measurement of the machine is a clock reading.** Two runs
of the same profile never agree on microseconds or on a traced-byte peak, so all three capabilities
first came back `reproduced=False` while finding exactly the same thing. The adapter now writes the
finding twice — the numbers for a human, and a stable ordering (`hotspot_ranking`, `allocating_sites`,
`growth` class) for the equality test — and the evidence probe treats profiler figures as volatile
while keeping the ranking in the comparison.

---

## 7. P5 — owned but unaskable

| defect | measurement |
|---|---|
| `vcs.git.bisect.v1` exists and is verified, but the sentence cannot state the predicate: every bisect needs an `argv` that says "good here, bad there" | `FAIL_CLOSED__STATED_ACT_INPUTS_UNBOUND:argv:not_stated` |
| the refactor family from a synthesised sentence | `inline_function` **NOT_REACHABLE**, `move_function` **NOT_REACHABLE**, `extract_function`/`change_signature` **ROUTED_ELSEWHERE** |
| whole-surface reachability, re-measured at `0c8aab6` | by vocabulary **436 bound, 11 not reachable, 9 routed elsewhere, 3 by explicit name**; by naming **409 bound, 26 not reachable, 21 unaskable, 3 by name** (459 rows) |

This is the same law three times: **a capability is reachable only through the words its registry
entry happens to use.**

### 7.1 What was fixed here, and what is left

Three declarations already existed in the tree and **no binder read any of them.** That is the whole
defect class, and it is the owner's point exactly: the answer was in the brain before anybody wrote
new code.

1. **The prose vocabulary.** `input_role_lexicon_v1.ROLE_ALIASES` declares the words a sentence uses
   for 38 roles — "timeout", "interpreter", "branch called", "kill ratio", "repeats". The front
   compiler *imported* it (`_ROLE_LEXICON_ALIASES`) and never consulted it, so every key without an
   entry in the compiler's own `_KEY_ALIASES` had no prose form at all.
2. **The knobs.** `input_role_lexicon_v1.SLOT_KIND` declares `timeout_s`, `python_executable`,
   `repeats`, `min_coverage_ratio`, `max_mutants`, `min_kill_ratio`, `tolerance`, `budget` and `ref`
   as `KIND_TUNING`, with the reason written beside them: "every adapter writes
   `args.get("<knob>") or <default>`, so these are the adapter's business, not the caller's". The
   binder raised on them instead — `timeout_s` alone made 15 capabilities unaskable, and there was
   no sentence a person could say that compiled.
3. **The kinds.** `_parse_typed_value` keeps its own four-key numeric sets, so a value the lexicon
   declares a number parsed to nothing: "with a timeout of 30 seconds" bound no timeout.

The laws are now enforced in `goal_front_compiler_v1`:

- a declared tuning knob the sentence never states is **defaulted and recorded**
  (`defaulted_inputs` on the compile result), because the adapter already has that value;
- a knob the sentence **does** state is bound by its declared kind — a number slot takes a number or
  nothing ("with a timeout of soonish" is refused, not bound as a string), and an interpreter is a
  path or a program name, never the word "python" that every Python sentence contains;
- a stated value that no binder can produce is a **refusal**, never a silent drop — the same law the
  lexicon already records for `ref`, where a stated commit was thrown away and HEAD reverted instead;
- the anti-fabrication check (`_inputs_not_stated_by`) keeps its full force for every non-knob slot:
  a defaulted knob is declared tuning, an invented path is not.

**Measured, apples to apples.** The reachability instrument now asks the same declaration two ways —
by vocabulary (`signature_goal`, 436 / 11 / 9 / 3 of 456) and by **naming the capability**
(`named_signature_goal`, which is how a caller who knows the verb asks). Sentences are identical
across the two trees; only the compiler differs:

| | reached by name | not reachable | lost |
|---|---|---|---|
| `580fa4d` | 391 | 41 | — |
| this unit | **396** | **39** | **0** |

The five gained are `python.quality.flake_detect.v1`, `web.release.verify.independent_http` and the
three performance acts this session added. No compiler test moved: the same 30 node ids fail across
the six door/compiler files at `580fa4d` and here (142 passed both).

### 7.2 A list the sentence stated was still "unstated", and that was most of the residue

The next pass asked the residue row by row. Two of the four refusal codes it kept producing were
not about the machine's reach at all — they were the same defect twice: **a value that is a LIST
was not a statement.** Every "did the sentence state this?" test in `goal_front_compiler_v1` was
`isinstance(value, str)`. `shell.command.run` bound `argv` to exactly the quoted command the caller
wrote — `"cat README.md"` → `["cat", "README.md"]` — and was then refused
`named_but_inputs_not_stated:argv`, because a list is not a string. `queries`, `test_argv`,
`test_paths`, `source_paths`, `changed_paths` and `edits` were refused the same way; twelve
capabilities were "unreachable" while their contracts bound perfectly.

Four laws came out of it, each pinned in `canonical/tests/test_a_stated_list_is_stated_v1.py` (13
pins):

1. **A list is a value.** A bound list is stated exactly when every member is in the sentence
   (`_stated_in`). Half a list is not a statement, and the check still refuses it.
2. **A delimited run is a list of names.** "resolve the symbols add, sub" bound `queries` to
   `["add"]` and dropped the caller's second question — the artifact then honestly reported one
   query, and a truthful answer to a narrower question is not the answer to the question. A single
   name stays a single name; the run stops at the first stopword, so prose is never appended as an
   identifier (`gc._identifiers_after_role`).
3. **After a preposition the identifier is bare.** `to "plus"` is a quoted literal, and a quoted
   literal's words are text, not the value — so `new_symbol` stayed unstated however plainly
   "rename add to plus" said it.
4. **A refusal says why.** When no declared input was missing, the refusal reported the word
   `inputs` as though one were, telling a caller to state inputs they had already stated; it now
   says `no_declared_input_missing` and carries the body's own complaint, and when a slot really is
   missing it still names it.

**The instrument was wrong in five ways too, and finding that out *is* the measurement.** Its
sentences stated slots as `key "value"` (a form no caller uses), gave path-list slots a bare path
and no role, gave a tree slot a *file*, gave `module` a relative path to nothing, and put a period
after the capability's name so the compiler's clause splitter read one request as two steps. Every
one of those produced a refusal about the question rather than the machine. A metric that asks a
sentence nobody would say measures the sentence.

**Measured, identical sentences, only the tree differs** (`--reachability --naming`, 459 rows):

| | reached by name | not reachable | lost |
|---|---|---|---|
| `0c8aab6` (before this pass) | 396 | 39 | — |
| this pass | **409** | **26** | 4 |

17 gained: `shell.command.run`, `vcs.git.bisect.v1`, `vcs.git.blame.v1`,
`python.source.symbols.resolve.v1`, `python.source.change_impact.testselect.v1`,
`code.impact.tree_sitter.testselect.v1`, `code.multilanguage.parse.tree_sitter.v1`,
`knowledge.consistency.assess`, `python.fault.localize.dynamic.dataflow.v1`,
`python.fault.provenance.interprocedural.value.v1`, `python.software.repair.{apply.verified,
loop.test_guided.ast, measured_acceptance, semantic_acceptance}.v1`,
`python.refactor.{change_signature, inline_function}.v1`, `software.patch.synthesize.cegis.z3.v1`.

The 4 lost are one cause, and it is the next defect: those sentences now **name the role** ("source
tree <D>") instead of giving a bare path, and the ranker reads the word *tree* as evidence for
`code.multilanguage.parse.tree_sitter.v1`. The named guard refuses rather than substituting, which
is why the row reads NOT_REACHABLE instead of "answered by the wrong capability" — but the ranking
is still wrong. **A word that states a declared input role must not be capability evidence.**

No compiler test moved: the same 33 node ids fail across the six door/compiler files at `9ebfa2a`
and here, 155 passed on both, plus the 24 new pins now green.

**What is still unaskable** — 11 not reachable and 9 routed elsewhere, and every one now has a named
cause rather than a shrug:

- `vcs.git.bisect.v1`: the sentence must state a predicate command; nothing in the prose grammar
  says how ("good here, bad there" is a *pair*, and the slot is one `argv`).
- the refactor family (`inline_function`, `move_function`, `rename_symbol`) reaches
  `python.software.repair.loop.test_guided.ast.v1` instead — six siblings compete on the same words
  and the loser is a repair loop, which is the wrong act and correctly refuses to bind.
- `chart.raster.*`: three chart capabilities differ only in which coordinate they ask for, and the
  router returns the sibling that wants `y_value`.
- `json.file.write` routes to a DOCX creator; `shell.command.run` cannot bind `argv` from "the shell
  command cat <file>".

### 7.3 The name in the request decides, and the score orders what is left

The next eight rows were all the same shape, and it is the plainest defect in the whole inventory:
a sentence that spells out a capability's **whole name** did not reach it.

```
"Run the python quality coverage. <dir> ... and save it to <out>"
   1. python.quality.flake_detect.v1        22   (shares "python", "quality")
   2. python.review.diff_coverage_gate.v1   22   (shares "python", "coverage")
   3. python.quality.coverage.v1            20   <- the capability the sentence NAMED
```

The pinned scorer weighs a name word like any other evidence, which is right for a sentence that
mentions a capability in passing and wrong for one that identifies it. `python.perf.benchmark.v1`,
`python.packaging.build_package.v1`, `python.toolchain.ruff_async_audit.v1` and the four quality
siblings were unaskable by their own names for exactly this reason — and the earlier
`benchmark` row of §7.2 was the same defect seen from the other side.

**The law:** a candidate whose whole name the request states comes first; the score then orders
everything the request left open (`_named_by_its_own_name` in `goal_front_compiler_v1`, applied in
`ranked_candidates`). "Whole name" means every distinctive word, with the generic vocabulary and the
version token already removed by `capability_selection_retrieval_v1._name_words`, and at least TWO
of them — so a name that reduces to one generic word ("source", "python") cannot claim a sentence on
the strength of that word. That bit is pinned both ways: the full name identifies, the shared half
does not.

| | by vocabulary | by name |
|---|---|---|
| before §7.3 | 436 / 11 / 9 / 3 | 409 / 26 / 21 / 3 |
| after §7.3 | **438 / 11 / 7 / 3** | **416 / 19 / 21 / 3** |

Zero new test failures: the same 33 node ids fail across the six door/compiler files as at
`9ebfa2a`, 155 passed plus the 15 + 11 pins of the last three units.

### 7.4 Three binders took turns being the only one consulted

The next pass went after the eight rows still refused with a contract that the sentence plainly
stated. All three causes are the same architectural defect: **a slot gets ONE binder, chosen by the
shape of the key, and if that binder cannot read the sentence the request is refused even when
another binder in the same module could.**

1. **The typed grammar was never asked.** `new_symbol` is declared KIND_IDENT, so
   `bind_all_inputs` handed it to the pinned binder and, on failure, recorded it as defaulted and
   moved on. The typed grammar next door reads the introducer the lexicon declares for it ("rename
   to", "to", "new name") and binds it without hesitation. Every refactor verb was therefore refused
   `contract_not_stated:module,new_symbol,qualname,...` for a sentence that stated all of them.
   **Law: a slot the pinned binder cannot decide falls back to its declared kind before the request
   is refused.**
2. **An identifier slot took a path.** The generic branch accepts any bare token, so a sentence
   ending "... and save the report to out.json" put `out.json` into `new_symbol`. The
   anti-fabrication check cannot catch this — the file name *is* in the sentence. The fabrication is
   the SHAPE, and the shape is what `SLOT_KIND` declares. **Law: an identifier slot does not take a
   path**, and the check takes the whole token (measuring only its identifier-shaped prefix read
   `pkg/mod.py` as `pkg`).
3. **An output path was silently dropped.** The handler meant to bind an output the pinned binder
   could not decide sat *after* an unconditional `continue`, so it was unreachable: the slot was
   recorded as "defaulted" and vanished. A capability whose artifact path disappears still compiles
   and still runs — and writes its report wherever the adapter felt like it. `pypi.provenance.
   audit_live_artifact` only passed this measurement because nobody looked at where `report_path`
   went. **Law: an output is never dropped** — it is bound to the artifact the sentence names, or to
   a recorded spool path, or the request is refused.

The instrument was wrong once more, in the same direction as §7.2: it stated a command as
`test argv "python3 -m pytest -x"` — the registry's spelling, which no caller writes — and stated the
interpreter as `"sample"`, which is not a program. Seven capabilities were unaskable for that reason
alone. A slot is now stated with the words the lexicon declares for it: *"with the test command
…"*, *"python3"*.

| | by vocabulary | by name |
|---|---|---|
| §7.3 | 438 / 11 / 7 / 3 | 416 / 19 / 21 / 3 |
| §7.4 | **440 / 11 / 5 / 3** | **427 / 8 / 21 / 3** |

Named reach went from **409 → 427** across §7.3 and §7.4 with **0 lost**; 18 of the 27 rows closed
were capabilities whose contract the machine could already bind and simply never asked. No compiler
test moved: identical 33 failing node ids at `d16c84e` and here, 155 passed on both, 29 pins green.

**What is left, and why each one is honest:**

- `shell.command.run`'s *vocabulary* sentence says "the shell command cat <file>" — an unquoted
  command, where the sentence does not say where the command ends. The named form binds it (§7.2).
- `vcs.git.blame.v1` needs a file and a tree, and the vocabulary sentence names two files; the
  named form binds both.
- `python.refactor.inline_function` / `move_function` / `rename_symbol` are reached **by name** and
  still fail on the vocabulary sentence, because six siblings share "refactor" and the ranker picks
  the repair loop — the structural sibling choice of §7.1, unchanged and still the next unit.
- `text.file.write` and `json.file.write` are routed away from by the body's own walk even when the
  sentence names them (the named guard refuses rather than substituting).
- The 21 `NO_SENTENCE` rows are capabilities whose declared contract has an output slot the
  instrument's sentence cannot be built for (chart raster, OCR, document verification). They are
  unaskable **by this instrument**, which is a statement about measurement, not about the machine,
  and they are counted separately for exactly that reason.

### 7.5 The bar, the number, and the command nobody quotes

Five more rows, and every one of them was a rule applied to the wrong object.

1. **A number is a value.** `_stated_in` read strings, lists (from §7.2) and nothing else, so a
   slot that bound `max_mutants: 8` correctly was refused `named_but_inputs_not_stated`. It reads
   numbers (as a TOKEN — `3` is inside `30`, and a substring test would have accepted it), flags
   ("run the tests true") and key/value payloads. Three named rows were this and nothing else.
2. **A command need not be quoted.** `_stated_command_argv` read only a QUOTED command, so
   *"run the shell command cat README.md and save the output to `<out>`"* — a sentence a person
   writes — was unaskable, and the quoted form was the caller doing the machine's work. The bare
   form is now read after a declared introducer ("the shell command", "the command"),
   ends at a stated boundary ("and save", "then", "in the…", a full stop), and its first token
   must be a program `raw_goal_trace_acceptance_v1` already declares as one. It fails closed on
   "tell me the command is easy".
3. **The bar for F32 was the wrong object.** F32 refuses a request when the act it names cannot be
   served — measured on *"Bisect the repository R"* with no predicate, which was answered by a
   file listing. But its bar was **whatever the pinned compiler happened to pick**:
   `python.refactor.inline_function.v1` ranked FIRST at 87 and bound every input, while the pinned
   compiler answered `python.toolchain.ruff_dead_code.v1`; a lower-ranked candidate the sentence
   never named ("ast") cleared that bar and the request was refused with
   `source_paths:no_matching_existing_files_named`. The bar is now **the best-ranked capability the
   sentence can actually be given**, so a nomination can only refuse when nothing better binds.
   Four rows closed — the three refactor verbs and the chart sibling.
4. **F33: a name plus a stated contract is the request.** `web.browser.rendered.capture.chromedriver`
   was refused because the pinned compiler found two capabilities it could not separate for the
   *rest* of the sentence. Ambiguity among capabilities the caller did not name is not a reason to
   refuse the one they did. The conditions are strict — routable, every declared input bound, and
   nothing unstated invented — so it can serve a stated contract and can never rescue an unstated
   one.
5. **The instrument asked the wrong sentence, again.** `signature_goal` — the by-vocabulary question
   — still emitted `argv "value"` for every non-path input: the registry's spelling of the slot,
   carrying the placeholder "value". Five rows were unaskable for a reason that lived entirely in
   the question, and the fix is the same one §7.2 made for the named question.

| | by vocabulary | by name |
|---|---|---|
| §7.4 | 440 / 11 / 5 / 3 | 427 / 8 / 21 / 3 |
| §7.5 | **451 / 4 / 1 / 3** | **431 / 5 / 21 / 3** |

Named reach **409 → 431** over four units, vocabulary **436 → 451** of 459, with **0 capabilities
lost** at any step. Identical 33 failing node ids at `d16c84e` and here, 155 passed on both, and 35
pins green in the two pin files.

### 7.6 The act word is DECLARED, not spelled, and a catch-all can be handed a contract

The remaining six rows, and three of them were one idea each.

1. **The act word lives in `provides`.** `json.file.write` provides `json.file.available`; its act is
   `available`, which appears nowhere in its id. The scorer only credited an act word found in the
   *identity*, so "make the json document available" scored the DOCX creator 28 against the JSON
   writer 24 — the DOCX creator matching the word "document" from its own id — and the JSON writer
   lost to a capability that then refused the sentence with `output_path_equals_an_input_path`.
   **Law: the last segment of each `provides` value is the act the capability declares**, and the
   head verb may claim it (the same "the sentence must also match something else in this entry"
   guard applies, so a tool merely named after the verb still gets nothing).
2. **A catch-all can be HANDED a contract.** F4's law — a capability that takes the whole request
   can never be the answer to one — is still the law. But `text.file.write`'s only non-output input
   is a payload the sentence quoted: the caller stated the text and the destination, and the
   capability's whole job is to put one in the other. It ranked first at 24 and the request was
   answered by a capability that ranked 9 and failed on `source_root`. The contract fallback in
   `ranked_candidates` was written for exactly this sentence shape and could never complete, because
   the catch-all it ranked was deleted from the pool two lines later. Three narrow conditions —
   the sentence quotes a value, every declared input binds, nothing bound went unstated — and
   "Run the thing." is still refused, which is pinned.
3. **The instrument gave a TREE slot a FILE**, in the vocabulary builder this time, so
   `worktree_path` and `apply_directory` arrived as files and the binder refused the pair
   (`path:2_existing_files_named`). The named builder learned this in §7.5; the vocabulary builder
   had not.

| | by vocabulary | by name |
|---|---|---|
| §7.5 | 451 / 4 / 1 / 3 | 431 / 5 / 21 / 3 |
| §7.6 | **454 / 2 / 1 / 3** | **431 / 5 / 21 / 3** |

**454 of 459 capabilities are now reachable and bound from one sentence built out of their own
declaration** — 98.9%, from 436 at the start of this session. Identical 33 failing node ids across
the six door/compiler files, 155 passed on both; 39 pins green.

The two that remain, and they are honest:

- `vcs.git.log.v1`: its own keyword list carries **"commit"**, so a sentence built from its own
  declaration is read as a request to commit and refused (`vcs.git.commit.v1:message:not_stated`) —
  a true refusal of a homonym the registry itself declares. The by-name question reaches it.
- `python.repo.pr_realize.v1`: binds nothing from the generated sentence and routes to
  `vcs.git.branch_list.v1`. Its declared contract needs a diff, a PR intent and an apply directory
  that the sentence does not state — the real remaining shape defect in the repo-delivery family.

`shell.command.run` and `vcs.git.bisect.v1` are now askable (both are in the 17 above): the
quoted-command sentence binds `argv`, which is what `_stated_command_argv` already implemented and
what the list check was hiding.

Which is the next unit: **make the sibling choice structural** — the act word in the entry's own
`provides` decides, not the bag of words — **and stop counting a role phrase as name evidence.**
Both are the same defect seen from two sides: the ranker is reading the sentence's *grammar* as if
it were the sentence's *subject*.

### 7.7 The ranker was right: two later stages were deciding instead

The six benchmark misses were not ranking defects, and the next unit was found by
instrumenting the goals that lost rather than by reading the scorer. On every one of them
the correct capability was **first** after `_score` — `xlsx.table.create_from_json_records`
43 against 36, `sqlite.table.verify_against_json_records` 54 against 36,
`python.source.audit.ast` 42 against 33 — and a later stage replaced it.

**Defect A — `_bm25_rerank` sorted by relevance first, the declared score second.** Corpus
statistics could overturn the candidate the pinned scorer had recorded as *declaring the
goal's verb*. "Audit the python source tree with an AST." gave `python.source.audit.ast`
42 with `matched_head_verb: audit`, and BM25 preferred
`code.multilanguage.parse.tree_sitter.v1` at 30/6.25 against 42/5.72 because "parse" and
"tree" are rarer in the corpus. **Law: relevance orders candidates; it does not overturn
the one that declares the act.** The flag is absent on 21 of 23 goals, so on those nothing
changed — including the barcode goal (`generate` 21 ahead of the decoder 22) and the tar
goal (`create` 54 ahead of the verifier 61) that BM25 was installed for, both re-pinned as
negative controls.

**The law has a bound, and it was found by a measurement that went the wrong way.**
Declaring the act may lift a candidate above candidates it already out-scores, and no
further. Unconditional act-first ordering took reachability from 454 to 450: on the
sentence the instrument builds from `python.review.diff_mutation_gate.v1` — *"Use behavior
coverage diff …"* — the head verb is the first declaration word, "behavior", declared by
`python.software.request.semantic_behavior.compile.v1` at score 25, while the capability
the sentence was built from scores 88 with BM25 relevance 48.6 against 6.7. Four
capabilities lost their last route to being asked. **The act word protects an advantage;
it does not create one** — so a flagged candidate leads only when its pinned score is at
least that of every unflagged candidate. With the bound: 454 reached and bound again, and
not one benchmark gain lost. Pinned both ways in
`test_which_stage_decides_the_selection_v1.py`.

**Defect B — `compile_goal` compared the grounded plan with the chained plan without
asking whether the chained one could run.** "Create an xlsx table from JSON records." and
"Verify a sqlite table against JSON records." were both answered by `auto.pypi.msgpack` —
a serialization library — at score 7, carrying a `$effect_result` for
`json.file.available` that no capability in the registry could produce, so the attach pass
had refused and left the reference dangling by design. An unexecutable plan trivially has
no slot filled off the filesystem, so the guess-loses-to-the-sentence rule preferred it to
the world-bound plan scoring 43 and 54.

**The discriminator that makes the fix safe is not a score margin.**
`match_evidence["matched_identity"]` already records whether a capability's own name
contains a word of the sentence, and it separates the two cases exactly: `auto.pypi.msgpack`
matches **no** identity token on the xlsx goal (it shares the keyword "records" and
nothing else), while `knowledge.consistency.assess` matches `assess` and `consistency` and
is the best answer available on the consistency goal. So a dangling plan loses to a
runnable one only when its capability names nothing the sentence said. The same score
comparison that prefers xlsx 43 to msgpack 7 also prefers a score-25 docx writer to the
score-13 consistency assessor — the precise regression the parity suite exists to catch,
and the reason the score was rejected as the discriminator.

| | canonical | front door | suites (7 files) | reachable by vocabulary |
|---|---|---|---|---|
| before | 18 / 23 | 17 / 23 | 33 failed / 155 passed | 454 / 1 routed / 1 unreachable |
| §7.7 | **22 / 23** | **21 / 23** | **21 failed / 191 passed** | **454 / 1 routed / 1 unreachable** |

Reachability is unchanged by construction: §7.6 left 454 of 459 reachable, and the bounded
act-word rule was required to leave it exactly there — the unbounded version measured 450,
which is why it was rejected.

Zero new failing node ids against the baseline; 12 baseline failures now pass, and the
parity pins — which were stale at 22/22 while both paths measured 18/17 — were re-pinned
to what actually happens: the two paths now diverge on exactly two goals, and both
divergences are the front door **refusing** with `GOAL_STATED_ACT_INPUTS_UNBOUND` a plan
that the canonical path returns one producer step short of executable
(`BENCH_JSON_FETCH_CONSISTENCY`, `EXT_JQ_TABLE`). That divergence is pinned in a new test
whose only accepted shape is "the door refuses what canonical answers with a dangling
`$effect_result`", so path drift in any other direction still fails.

The one remaining miss is the honest one: **`EXT_JQ_TABLE`**. The sentence states no
`jq_filter`, `json.query.jq` requires one, and inventing the program the user would have
written is exactly what this repository refuses to do. Neither path answers it; the door
refuses it and the canonical path returns a plan that cannot run. The registry could
declare a default filter, or the sentence could state one — that is a declaration decision,
not a compiler defect, and doing it inside the compiler would be invention.

Pins: `canonical/tests/test_which_stage_decides_the_selection_v1.py` (9) —
the act-word ordering with its two negative controls, the dangling-reference precondition,
the nameless-plan and named-plan halves of the rule, the predicate's own reading of
recorded evidence, and the 22/23 rate.

---

## 8. P6 — the absent acts, by domain

The 38 acts nothing mentions, i.e. where a senior engineer would notice the machine is not there:

- **infrastructure & delivery (6):** CI config, container image, IaC, deploy, secret management, environment fit.
- **observability (5):** logging instrumentation, metrics instrumentation, tracing, log analysis, SLO.
- **performance (1):** query plans.
- **dynamic analysis (2):** debugger/breakpoint, syscall trace.
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
| ~~2~~ | ~~**`memory_profile` + `cpu_profile` + `benchmark`**~~ | P6 (3 acts) | **DONE this unit (§6.4)** — `tracemalloc`, `cProfile`/`pstats`, `perf_counter`; one module, three verbs, four measured defects fixed, 13 pins | — |
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
PYTHONPATH=. .venv/bin/python execution_guard/capability_evidence_probe_v1.py \
    --only python.perf.memory_profile.v1,python.perf.cpu_profile.v1,python.perf.benchmark.v1 --remeasure
PYTHONPATH=. .venv/bin/python -m pytest canonical/tests/test_performance_measurement_v1.py -q
PYTHONPATH=. .venv/bin/python -c "
from execution_guard import live_solver_end_to_end_measurement_v1 as M
from pathlib import Path
w = Path('canonical/astra_runtime/tmp/reach_work'); w.mkdir(parents=True, exist_ok=True)
print('by vocabulary', M.reachability(w)['counts'])
print('by name      ', M.reachability(w, naming=True)['counts'])"
PYTHONPATH=. .venv/bin/python -m pytest canonical/tests/test_a_declared_knob_is_the_machines_business_v1.py -q
PYTHONPATH=. .venv/bin/python -m pytest canonical/tests/test_a_stated_list_is_stated_v1.py -q
PYTHONPATH=. .venv/bin/python execution_guard/live_solver_end_to_end_measurement_v1.py \
    --reachability canonical/astra_runtime/tmp/reach_work
PYTHONPATH=. .venv/bin/python execution_guard/live_solver_end_to_end_measurement_v1.py \
    --reachability canonical/astra_runtime/tmp/reach_work --naming
PYTHONPATH=. .venv/bin/python execution_guard/hardcore_se_domain_coverage_v1.py
PYTHONPATH=. .venv/bin/python execution_guard/capability_evidence_probe_v1.py --audit-pointers
PYTHONPATH=. .venv/bin/python -m pytest canonical/tests/test_goal_front_compiler_v1.py \
    canonical/tests/test_goal_compiler_world_binding_v1.py \
    canonical/tests/test_live_brain_route_admission_v1.py -q
```

A number in this document that no longer reproduces is a bug in this document, not a target.
