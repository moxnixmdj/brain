# HARDCORE SOFTWARE-ENGINEERING PROBLEM INVENTORY

> **Superseded by [`HARDCORE_SE_PROBLEM_INVENTORY_20261029_V2.md`](HARDCORE_SE_PROBLEM_INVENTORY_20261029_V2.md).**
> This file is historical: its P0/P1 and P4–P8 claims and work queue predate later counterexamples,
> safeguards and corrections. In particular, it overstates composition and understates existing
> call-index, differential/mutation and multi-language patch machinery. Use V2 for current status.

**Date:** 2026-10-29 · **Branch:** `arena/4ca3a720-brain` · **Tree:** branch state after `bb36ebae` (see `git log` for subsequent changes)
**Scope:** the owner's question — *what are all the problems* on the way to the most advanced, fastest
software engineer. Document, image, chart and PDF families are measured only so the denominator is
honest; nothing here proposes work on them.

Every number in this document was produced in this session by the instrument named beside it. A number
that no longer reproduces is a bug in this document, not a target. Red is not authority.

---

## 1. The machine today, in seven numbers

| # | measurement | value | instrument |
|---|---|---|---|
| 1 | entries visible in the extended registry (including receipt-projected entries) | **459** | `load_verified_registry(include_extended=True)` |
| 2 | generated plain-goal probe (bound / by id / routed elsewhere / not reached) | **454 / 3 / 1 / 1** | `live_solver_end_to_end_measurement_v1.py --reachability` |
| 3 | hardcore act labels with a lexical `provides` match in the **165-entry static registry** | **69 of 135**, 28 keyword-only, **38 no lexical match** | `hardcore_se_domain_coverage_v1.py` |
| 4 | two-per-family end-to-end sample | too small to quote as a family result; use **n ≥ 4** | `live_solver_end_to_end_measurement_v1.py --per-family 2` |
| 5 | benchmark capability selection (canonical / front door) | **22 / 23** · **21 / 23** | `goal_compilation_benchmark_v1` |
| 6 | evidence blocks: ok / no pointer / dangling | **123 / 34 / 8** | `capability_evidence_probe_v1.py --audit-pointers` |
| 6b | declared external dependencies flagged missing | **6** in the latest run; the transitive `et_xmlfile` import is separately missing | `live_solver_end_to_end_measurement_v1.py`, tool liveness + direct import |
| 7 | red door/compiler tests | **17**, **4 skipped** naming a missing dependency (was 33 this session) | `pytest` on the six door/compiler suites (17 failed / 187 passed / 4 skipped) |

Per-domain lexical classification of 135 predefined act labels against the **165-entry static**
registry (`hardcore_se_domain_coverage_v1.py`, `measure()`). `BOUND` is a substring match in
`provides`, not a successful execution; `NAMED` is a keyword match; `ABSENT` means neither lexical
match was found. It does **not** prove that no implementation exists elsewhere in the repository or
the extended registry:

| domain | bound | named only | absent | domain | bound | named only | absent |
|---|---|---|---|---|---|---|---|
| version control | 10/17 | 4 | 3 | testing | 6/10 | 3 | 1 |
| refactoring | 6/14 | 2 | 6 | static analysis | 10/13 | 1 | 2 |
| dependencies and build | 2/10 | 3 | 5 | dynamic analysis | 5/9 | 2 | 2 |
| data and persistence | 5/9 | 1 | 3 | security and supply chain | 6/9 | 2 | 1 |
| services and concurrency | 3/8 | 0 | **5** | review and delivery flow | 7/8 | 0 | 1 |
| multi-language | 3/7 | 4 | 0 | infrastructure and delivery | **0/6** | 4 | 2 |
| performance engineering | 5/6 | 0 | 1 | observability | **0/5** | 2 | 3 |
| documentation | 1/4 | 0 | 3 | **totals** | **69/135** | 28 | 38 |

The lexical probe finds no `provides` match for infrastructure/delivery (0/6) or observability
(0/5); services/concurrency has 3/8 matches and 5 unmatched labels. These are search priorities,
not proof that the corresponding tools do not exist elsewhere.

Latest tool-liveness run over 165 capabilities: **0 adapters missing**, 9 adapter import failures,
**6 declared external dependencies flagged missing**, 27 executor kernel refusals by source type,
and 19 zero-input composition nodes. The probe can miss transitive dependencies: it marks the XLSX
verifier's declared package present, but importing `openpyxl` here fails on missing `et_xmlfile`.

---

## 2. The problems, ordered by what they cost an engineer

### P0 — Acceptance and re-inspection are not yet a complete trust chain

**Correcting the previous report:** the earlier statement that “at most 192 of 459” have an inspector
and “at least 267” do not was **not measured**. Registry adapter *modules* are not the same thing as
the runtime result's `adapter` field, and a registered inspector may still refuse a particular result.
The asserted bounds are withdrawn; effective runtime coverage remains to be measured.

`raw_goal_trace_acceptance_v1` already has 13 capability-keyed inspectors and one adapter-keyed
inspector (`bound_capability_cli`). The extended registry has 459 visible entries, 248 distinct
`adapter_module` values, and 179 entries declaring `cli_command`; `shell.command.run` is in both the
13 and the 179. The CLI adapter normally reports `bound_capability_cli` when it runs, but these counts
cannot establish how many real goals receive valid independent acceptance. The remaining
`NO_INDEPENDENT_REINSPECTION_FOR:python.repository.acceptance.measure.v1` is one directly observed
coverage gap, not a measurement of the whole registry.

**Fixed: re-inspection itself could mutate the world.** In a disposable tree, each of four calls to
`_inspect_shell_command_run` accepted a matching empty report while it also changed files:
`find -delete`, `sed` with a `w` script, `sort -oFILE`, and a Python file in the tree. A path being
in the tree did not make its script read-only. Re-inspection now uses the **existing**
`zero_ambient_namespace_launcher_v1` and its existing query wrapper: the input tree is read-only,
network is isolated, and inability to confine refuses rather than reruns on the host. Mutating find,
sed and attached-output sort shapes are refused or held to their existing postconditions. A validated,
opt-in `/dev/null` is the only host device exposed, enabling Git readers without exposing `/dev` in
the default policy. `test_command_reinspection_is_read_only_v1.py` exercises the attacks, benign
readers, no-confinement behavior and executable-name spoofing; the namespace's hostile tests also pass.
This secures the **re-inspection**, not arbitrary producer execution.

**Fixed: a matching producer hash was not a semantic check.** For an actual CLI `cat` run that saved
stdout, replacing the destination with `FORGED` and updating its reported sha256 still produced
`RAW_GOAL_ACCEPTANCE_VERIFIED`. The same constructed trace is now refused with
`COMMAND_STDOUT_DESTINATION_MISMATCH`: the destination is reopened and compared with independently
reproduced stdout. The test also checks that the unmodified destination passes.

**Partially fixed: extra instructions inherited credit they had not earned.** The diagnostic
`execution_guard/raw_acceptance_obligation_gap_probe_v1.py` uses real, harmless actions in a temporary
directory and then feeds the verifier constructed traces and contracts. For a **single** explicit
command and for a **single** literal text write, each of four unperformed second actions (delete,
modify, copy, archive) was accepted before; all eight are now refused with zero accepted obligation
IDs. The bounded whole-sentence checks still accept positive single-action controls.

**Still open:** the same diagnostic runs the command twice and supplies a two-step trace. **4 of 4**
unperformed second instructions still receive `semantic_acceptance_complete=True`, while the existing
`raw_task_acceptance_residual_localizer_v1` reports 3–4 semantic residuals per case. This is a
constructed-trace test of the verifier, not a claim that all four reach it through the live front door.
`lossless_raw_task_acceptance_gate_v1` already requires a separate, independently verified receipt for
every obligation; the raw-trace path does not yet provide those proofs. Do not treat this bounded fix,
a passing digest, or the existence of an inspector as proof of complete task semantics.

**Measurements:** `test_command_reinspection_is_read_only_v1.py` and the related verifier, namespace,
command, and hostile suites: **112 passed, 3 deselected, 2 subtests passed**. The deselected command
front-door tests are three pre-existing failures (`TRACE_HAS_NO_CAPABILITY_ACTIONS`); a stash-based
HEAD comparison confirmed all three predate this work. A 174-test ordinary-command subset had
**65 failures / 109 passes**, and all 65 failing IDs also failed on unmodified HEAD. Re-running the 109
passing cases produced **108 passes / 1 failure**; that one also fails alone on unmodified HEAD, routing
the filter request to `python.quality.resource_leak.v1` (the P3 admission issue). Benchmark selection
remains **22/23** and parity/act pins **34 passed**. Run the commands in §6 to remeasure.

**Speed:** reinspection timing, n=12 after one warmup (`execution_guard/reinspection_timing_probe_v1.py`):
plain `cat` median **0.183 ms**, one-file `wc -l` **0.156 ms**, and confined `sort` **116.692 ms** on
this host. Plain `cat` previously used a host subprocess (median **1.39 ms**, n=12). The fast paths
reopen real file bytes; the slower path has the confinement cost. These are microbenchmarks, not
end-to-end family latencies.

**Archive routing, separately:** the naming-mode instrument previously mislabeled zero-output
verifiers as unreachable; plain mode can bind the hardcore verifiers. A generated archive-check
request also routed to its creator; the verb/name fixes below raised the 8-instance archive family to
8/8. Routing the right verifier is not itself proof that its work or the complete task is correct.

**The archive selection defects were fixed by reusing the existing declarations and ranking:**

1. **The verifier did not declare the act it performs.** `_declared_act_words` read the LAST TOKEN of a
   `provides` value, so `archive.tar_gz.verify_manifest_members` declared the act `members` —
   a noun — and nothing else. A sentence built from the verifier's own declaration therefore said
   "members", and the archive *creator* answered it. The rule now reads every token of the final
   segment (71 of 459 entries declare a snake_case phrase), so the verifier declares
   **verify / manifest / members** and the creator declares **create / manifest**. Benchmark 22/23 and
   reachability 454 / 3 / 1 / 1 both held exactly.
2. **F3 preferred an artifact writer over the act the sentence named.** In the front door, a goal that
   names files is served only by candidates with output keys — and the verifier, which writes no file,
   was dropped from the pool while the two INPUT paths were read as things to be produced. Ranked
   first at 63, the verifier lost to a creator at 47. F3 now does not fire when the sentence's own head
   verb is an act the best-ranked candidate DECLARES
   (`F3_NOT_APPLIED__THE_SENTENCE_NAMES_THE_ACT_THE_BEST_CANDIDATE_DECLARES`).

   Measured on the artifact family at that stage: **3 of 4** routed to the verifier. The later
   eight-instance measurement is 8/8. The front-door selection rate pin still holds (21 of 23)
   and the parity suite is 27 green.

3. **A verb has many spellings, and the name rule was reading half a name.** The residual above —
   *"Check the tar.gz archive …"* and *"Audit …"* reaching the creator — was two defects, both fixed:

   - **The spellings of an act were unknown.** The verifier declares the act `verify` and nothing in
     the machine knew that check / audit / inspect / validate / confirm name the same act.
     `_ACT_SYNONYMS` declares those classes and `_declared_act_words` expands them one-directionally,
     so a capability can only gain a spelling of an act it already declares. Measured:
     *Audit / Check / Verify / Inspect / Validate* now all route to `archive.verify.tar_gz.gnu`
     while *Create* still routes to the creator, and the ARCHIVE_VERIFY_GNU family went
     **4 of 6 → 8 of 8**.
   - **The name rule read half a name.** `_name_words` drops the verb segment, so the "whole name" of
     `archive.tar_gz.create_from_manifest` was only its OBJECT {archive, tar, gz, manifest}. A
     sentence using a different verb was therefore counted as naming the creator and was pinned
     ABOVE the verifier that declares the verb: *"Verify the tar.gz archive A against the manifest
     M."* ranked the creator 47 first and the verifier 61 second — the pinned score had already
     picked the verifier and the name rule inverted it. A rival that declares the sentence's head
     verb AND outscores a candidate now strips that candidate's name pin — bounded on both sides by
     measurement: a sentence that opens with a keyword rather than a verb has no rival and keeps
     every pin, and `python.repo.pr_realize.v1` (72) keeps its pin over `vcs.git.branch_list.v1`
     (36), which declares the word but cannot outscore it.

   Guards after all three, measured: archive family **1.0 over 8 fresh goals**; benchmark **22/23**;
   parity **27 passed**; reachability **454 / 3 / 1 / 1**, identical to before, so no capability lost
   its route; six door/compiler suites **17 failed / 187 passed / 4 skipped** with the same failing
   ids as the previous sweep and no new ones.

**Routing still needs object-role investigation.** The archive sample above is repaired; that does not
close the separate acceptance and inspector-coverage gaps described at the start of P0. Object nouns
(bundle, archive, package, manifest) remain an unmeasured ranking question, not an established fix
for either generated-goal miss.

**One measurement caveat.** A whole-corpus run at 2 instances per family is not a rate: in the same
run `JSON_QUERY_JQ` scored 0 of 2 while a direct reproduction of that exact family goal passes and
routes to `json.query.jq`. Quote a family at n≥4 or not at all.

### P1 — CORRECTED: multi-step composition works; a missing dependency was being called an invalid result

The first version of this document said the executor's result contract was broken. It was not. Running the
failing chain directly gave the whole story:

```
status = FAIL__CAPABILITY_DAG_RESULT_INVALID
reason = ModuleNotFoundError: No module named 'et_xmlfile'
```

`et_xmlfile` is openpyxl's own dependency and this box does not have it. The DAG executor crashed, the
entry point converted *any* exception into an invalid-result status, and a missing library was therefore
reported as a defect in the plan. The repo already contained the classifier for exactly this
(`failure_kind`, with its own pinned test file `test_a_defect_is_never_reported_as_a_refusal_v1.py`) and the
live entry point never called it.

**Fixed in this session:** every closed failure from the DAG path and from `_fail` now carries
`failure_kind`, the missing module is named in `blocked_by`, and an environment block reports
`BLOCKED__CAPABILITY_DAG_ENVIRONMENT_BLOCKER` instead of "invalid result":

```
status = BLOCKED__CAPABILITY_DAG_ENVIRONMENT_BLOCKER
failure_kind = ENVIRONMENT_BLOCKER
blocked_by = et_xmlfile
```

The four multi-step tests now skip, naming the dependency, instead of asserting that this box has a library
it does not have — which is the repo's own convention (`environment_blocked_here` in the end-to-end
harness; `ENVIRONMENT_BLOCKED_CAPABILITIES_ARE_NOT_PASSES`). Measured after: **17 red, 201 passed, 4
skipped**, no new failing node id.

What is still genuinely open on composition: `test_f13` returns `FAIL_CLOSED__NO_OBSERVED_EFFECT` — an
intermediate spool step that produced no observed effect. That is one row, and it is a real one.

### P2 — Near-duplicate capabilities can steal each other's sentences

A measured repair/acceptance sentence sometimes routes to `python.repository.acceptance.measure.v1`
rather than `python.software.repair.measured_acceptance.v1`, producing a measurement rather than the
requested repair. The archive creator/verifier collision was separately fixed and is pinned at n=8
above. Multiple capabilities may legitimately perform the same act with different inputs or tools;
the needed rule is correct act, object and binding arbitration, **not** a blanket ban on shared acts.
The object-noun hypothesis and the two generated-goal misses in P10 still need distinct reproductions.

### P3 — A refusal falls through to an admission

`route_admission` records `typed_binding_refused: True` with
`BINDING_REFUSED:NO_SLOT_FOR_THE_STATED_PAYLOAD:ARGV,PATH_DIR,PATH_LIST,PATH_OUTPUT` **and**
`admitted: True` in the same receipt. `test_f1_best_candidate_that_cannot_bind_fails_closed_instead_of_falling_through`
pins the law that this must fail closed; it is red.

### P4 — 38 act labels have no lexical match in the static registry

This is the 135-label `hardcore_se_domain_coverage_v1.py` vocabulary probe over 165 static entries,
not a search of every file or an execution test. An `ABSENT` classification means no configured
`provides`/keyword substring matched; it is **not** proof that the act or an engine is missing from
the Brain, another repository, or the internet. Names below are exactly the probe's ABSENT rows:

| domain | matched / total | labels with no lexical match |
|---|---|---|
| refactoring | 6/14 | extract variable, encapsulate field, pull-up method, replace conditional, remove dead imports, split module |
| dependencies & build | 2/10 | upgrade dependency, reproducible build, monorepo, cache, publish |
| services & concurrency | 3/8 | retry policy, timeout policy, circuit breaker, task graph, local server |
| infrastructure & delivery | 0/6 | IaC, environment fit |
| observability | 0/5 | logging instrumentation, metrics instrumentation, structured log analysis |
| data & persistence | 5/9 | schema migration, transaction, integrity check |
| dynamic analysis | 5/9 | debugger/breakpoint, deadlock detect |
| testing | 6/10 | golden/snapshot |
| version control | 10/17 | cherry-pick, worktree, reflog undo |
| static analysis | 10/13 | call graph, dependency graph |
| security & supply chain | 6/9 | SBOM |
| documentation | 1/4 | docstrings, README, API reference |
| review flow | 7/8 | code-review comment |
| multi-language | 3/7 | none absent by this lexical criterion; 4 are keyword-only |

The six unmatched refactoring labels are promising candidates for a targeted repository/adapter search,
but the cost and whether existing AST engines safely implement each verb have not been measured.

### P5 — 28 acts are NAMED but unbound

Declared in the map, no capability behind them: `build.install`, `build.remove_dependency`,
`build.version_bump`, `data.query_optimise`, `dynamic.race_detect`, `dynamic.syscall_trace`,
`git.merge`, `git.conflict.resolve`, `git.remote`, `git.tag`, `infra.ci_config`, `infra.container`,
`infra.deploy`, `infra.secret_management`, `obs.slo`, `obs.tracing`, `refactor.convert_to_method`,
`refactor.organise_imports`, `security.signature_verify`, `static.dataflow_taint`,
`supplychain.pin_lockfile`, `test.data_generation`, `test.differential`, `test.mutation`,
`lang.{javascript_refactor,go_analysis,rust_analysis,c_cpp_compile}`.

A keyword match is only vocabulary, not a working implementation or evidence that an implementation
can be wired cheaply. `git.merge`, `git.conflict.resolve`, and `test.mutation` are especially relevant
search targets for real engineering.

### P6 — Repair and refactor depth is one language deep

74 of 459 capabilities are `python.*`. The repair loop family (`python.software.repair.*`, 7 entries),
the patch search (`python.patch.*`, 2), fault localisation (`python.fault.*`, 4) and the AST refactor
engine (7) are all Python-only. `code.multilanguage.parse.tree_sitter.v1` parses JS/Go/Rust/C but
nothing *edits* or *tests* them. Measured ceiling: `lang.*` is 3 bound of 7, all three of them
read-only.

### P7 — Missing tools and an incomplete dependency probe

The latest tool-liveness run flags six capabilities with missing declared external dependencies:
`auto.apt.zint`, `document.convert.markdown_pdf.pandoc_weasyprint`, `image.code.decode.zbarimg`,
`image.qr.generate.qrencode`, `pdf.extract.ocr.tesseract`, and **`yaml.to_json.yq`**. Separately,
`import openpyxl` fails on `et_xmlfile` even though the probe reports the XLSX verifier's declared
package present; this is a transitive-import blind spot, not a seventh flagged external dependency.

Most are document/image families and are out of scope by owner instruction. `yaml.to_json.yq` is not:
it is a **data** capability. The current benchmark miss `EXT_JQ_TABLE` selects
`document.convert.markdown_pdf.pandoc_weasyprint`, not `yaml.to_json.yq` (`/tmp/bench.py`, 22/23).
The previous report that yq was the current selected answer was wrong. Install-or-refuse holds at the door; the compiler still does not know it is routing to a tool
that is not installed. Nine adapters additionally fail to import (8 chart readers +
`professional.artifact.visual_observer.v1`), which the executor turns into a source-type refusal 27
times.

### P8 — The most advanced capabilities have the least evidence

`--audit-pointers`: **34 blocks name nothing a reader could check, 8 name files nobody wrote.** The
dangling eight include precisely the composer/orchestrator family that *is* the "advanced engineer"
story: `software.hardcore.kernel.orchestrate.v1`, `software.repair.loop.cegis_hypothesis.v1`,
`software.review.gate.composer.v1`, `software.synthesis.grid_induction.v1`,
`software.repair.choreograph.crossfile.v1`, `software.hardcore.closing.supercomposer.v1`,
`test.slice.never_miss.v1`, `code.multilanguage.parse.tree_sitter.v1`.

A dangling evidence pointer is not a capability defect; it is an unbacked claim, which is worse.

### P9 — The 17 red tests, in four families (a work queue, not a fog)

| family | rows | real cause |
|---|---|---|
| ~~DAG executor returns an invalid result~~ | ~~4~~ | **not a defect** — missing `et_xmlfile`; now `BLOCKED__…_ENVIRONMENT_BLOCKER` and skipped |
| an intermediate spool step observes no effect | 1 | P1 above (real) |
| admission/acceptance laws | 7 | P0 and P3 above |
| stale guard expectations (`R1`/`R3` vs `R12`/`R14`) | 3 | **the guard got better than the pin** — `R12_STATED_ACT_IS_NOT_AN_ACT_THIS_BRAIN_PERFORMS:translate` and `R14_UNHEARD_ACT_WORD:tutorial` are the *correct* verdicts |
| reachability / parity / rate pins | 6 | measurement pins, deliberately moved |

Counted this session on the six door/compiler suites: **17 failed / 187 passed / 4 skipped**, down from 33 failed on the same set when the session began, with **no new failing id** at any point (`comm -13` of the two sweeps is empty).

### P10 — Generated-goal reachability misses and a naming-instrument blind spot

This section said 26 and it was wrong. Re-measured this session, both modes:

- **Plain sentences** (`signature_goal`, every capability asked with its own declaration words plus
  one stated value per input): **454 reached and bound, 3 reached only by spelling the internal id,
  1 routed elsewhere, 1 unreachable** — of 459.
- **Named sentences** (`named_signature_goal`, `--naming`): **431 / 21 no sentence / 4 unreachable / 3 by name**.

The 21 rows the naming mode cannot form a sentence for are **not 21 unreachable capabilities**. That
builder ends every sentence with *"and save it to <destination>"*, so a capability that declares no
output path gets no sentence — and the list is dominated by exactly the shape P0 is about: seven
verifiers (`archive.verify.tar_gz.gnu`, `decision.synthesis.verify.stdlib`,
`plain_goal.bound_capability.grounding.verify.stdlib`,
`sqlite.table.verify_against_json_records`, `xlsx.table.verify_against_json_records`, and the two
`docx.document.verify.*`) plus 14 other rows, including document/image readers. In plain
mode **every one of the hardcore verifiers is reached and bound**, so the P0 defect was never
"cannot be asked" — it was "is asked and answers with a different act", which is what the three
selection fixes closed.

What is left, measured, is small and specific:

| state | capabilities | why |
|---|---|---|
| not reached by the generated plain-goal probe | **2** — `vcs.git.log.v1`, `python.repo.pr_realize.v1` | **homonym pollution**: `vcs.git.log.v1` carries the word "commit" in its own keywords, so a sentence built from its declaration is read as a commit request; `pr_realize` is out-scored by `vcs.git.branch_list.v1` on its own generated sentence |
| by explicit id only | 3 — `python.contract.issue_orchestration.fusion.v1`, `python.pipeline.allowlist_gate.v1`, `python.refactor.test_scaffold.fusion.v1` | zero-input composers whose prose sentence is answered by `software.repair.loop.cegis_hypothesis.v1` |

These two rows are failures of the tested generated sentences, not proof that **no** sentence can
reach either capability. The candidate causes above require targeted checks; no universal sole-owner
law or unit-cost estimate has been established.

### P1b — Two claims in this document's first version were wrong, and are corrected here

1. **"Multi-step composition is broken."** It is not. The reason was `No module named 'et_xmlfile'`. The
   defect was that a missing dependency was reported as an invalid result; that is fixed (P1).
2. **"Archive verify cannot be asked."** It can: *"Verify the tar archive at out/backup.tar.gz against
   the manifest at out/manifest.json."* selects the verifier 64 against 50. What fails is the
   declaration-built sentence, because the verifier declares the act `members` rather than `verify`.

Both corrections came from re-reading the measurement instead of the status word, which is the same law
that produced this document. The lesson is recorded rather than deleted: a red row names an observation,
never a cause.

### P11 — The instruments that are not here are the ceiling

A prior environment probe reported missing optional tools including `docker`, `kubectl`, `terraform`,
`gdb`, `strace`, `hypothesis`, `libcst`, and `rope`. Their availability is host-specific and must be
rechecked before use. On this host `go` and `rustc` are absent from PATH, while **`gcc` exists at
`/usr/bin/gcc`** (`command -v`); the previous claim that gcc was absent was wrong. An unmatched act
is not automatically blocked by any particular tool.
Two consequences worth stating plainly:

1. Existing Python refactor adapters use `ast` and `tokenize`; whether they safely implement each of
   the six unmatched verbs still needs proof. Missing `libcst`/`rope` alone does not prove impossibility.
2. Missing `go`/`rustc` blocks compiler-backed execution on this host, not every possible static
   analysis; report the missing tools by name rather than inventing their results.

### P12 — Speed is measured per operation, not inferred from a tiny family sample

The 2-per-family whole-corpus sample cannot establish a family latency distribution. On this host,
the reproducible 12-iteration reinspection microbenchmark above measures direct file reopens at
0.183 ms (`cat`) and 0.156 ms (`wc -l`), but confined `sort` at 116.692 ms median. Confinement adds a
real cost, and supported fast paths must be justified by independent byte-level checks, not by
unconfined replay. Larger, n≥4 end-to-end samples are still needed before ranking other families by
speed; the earlier claim of a knowledge-family “unbounded loop” was not established.

### P13 — The existing PR cannot currently land

On 2026-10-29, GitHub reports PR #6305 as **CONFLICTING**. Against `origin/main` at `e2d7981d`,
`git merge-tree --write-tree origin/main HEAD` identifies conflicts in
`canonical/runtime/goal_compiler.py` and `canonical/runtime/state/experience_v1.json`. No merge was
attempted. GitHub's integrity/referee and drift-guard checks are red; the same workflows had already
failed on the previous head `bb36ebae`. Downloading their logs returned `EOF`, so their exact remote
failure messages are unavailable.

The local integrity guard, run against the branch's merge base `2754cf0d`, reports
`CAPABILITY_REGISTRATION_FLOOD`: **40** new registry entries against the policy limit of **3 per PR**.
The re-inspection commit added **zero** registry entries. Resolving file conflicts alone cannot resolve
that local policy violation; do not delete capabilities or weaken the guard simply to make a check
pass. Splitting work requires coordination outside this session's fixed branch constraints.

---

## 3. Existing mechanisms to search and reuse

| problem | existing mechanism | remaining evidence or work |
|---|---|---|
| P0 safe reinspection | `zero_ambient_namespace_launcher_v1` plus the read-only query wrapper, `INSPECTORS` / `_ADAPTER_INSPECTORS` | effective coverage unknown; replay checks do not prove all task obligations |
| P0 obligation coverage | `raw_task_acceptance_residual_localizer_v1`, `lossless_raw_task_acceptance_gate_v1` | connect independently verifiable per-obligation evidence; multi-step 4/4 counterexamples remain |
| P2 selection | `_bm25_rerank`, `_order_with_act_flag`, existing declarations | investigate object-role ambiguity and generated-goal misses without assuming unique act ownership |
| P3 refusal | F24 and producer-verification refusals | trace why an admission can coexist with `typed_binding_refused` |
| P4/P5 search | existing `vcs_git_v1`, `toolchain_v1`, `quality_v1`, `dynamic_probe_v1`, `perf_probe_v1`, `packaging_v1` | check each unmatched/keyword-only act against actual engines and evidence; do not infer all 28 are implemented |
| P6 multi-language | tree-sitter parse and patch verification declarations | demonstrate real edit/test execution per language and check each host toolchain |

## 4. Lower priority or constrained by the owner

- **Document / image / chart work** is lower priority by the owner's direction; some related tools are
  missing on this host, but that does not imply every such capability is blocked.
- **`R1`/`R3` test rows.** The guard's newer `R12`/`R14` verdicts require checking the sentence and
  declared acts, rather than blindly restoring earlier status codes.
- **`EXT_JQ_TABLE`** remains a wrong selection to the document converter. The sentence gives no
  `jq_filter`; the machine must not invent one, and the correct handling needs a grounded contract.
- **Generated-goal reachability.** 454 of 459 were bound in the plain-goal probe. That is one
  instrument and does not prove general natural-language reachability; the naming-mode `NO_SENTENCE`
  rows are a separate instrument limitation (P10).

---

## 5. Work queue, evidence before estimates

| priority | work | existing machinery / measured reason |
|---|---|---|
| 1 | **Per-obligation acceptance for composed traces** | reuse the residual localizer and lossless gate; 4/4 two-step constructed traces still credit an unperformed action (P0) |
| 2 | **Measure and expand independent inspector coverage** | inspect actual result contracts and add capability-specific checks; no justified 192/267 coverage bound |
| 3 | **Repair the local-adapter trace identity after acceptance is safe** | `shell.command.run`, `knowledge.consistency.assess`, and `knowledge.json.fetch.external` omit `capability_id` in their templates; the live trace can contain an action but be reported as `TRACE_HAS_NO_CAPABILITY_ACTIONS` |
| 4 | **Resolve the observed refusal/admission contradiction** | reuse F24 and check actual binding evidence (P3) |
| 5 | **Resolve generated-goal misses and object-role ambiguity** | reuse declarations and ranking, with benchmark, parity and reachability guards (P2/P10) |
| 6 | **Search first for unmatched hardcore acts** | start with refactoring, version control, tests and build; registry vocabulary alone is not evidence of absence (P4/P5) |
| 7 | **Audit pointerless and dangling evidence** | 34/8 observed in the pointer probe (P8); do not manufacture receipts |
| 8 | **Measure slow confined readers and optimize only with independent byte checks** | n=12 microbenchmark shows a real confined-replay cost (P12) |

Delivery is separately blocked by the existing PR conflicts and capability-registration limit (P13).
No duration estimates are asserted. Reuse before synthesis; measure rather than assert; red is not
authority; no AI model participates in Brain-credited producer cognition.

## 6. Reproduce

```bash
PYTHONPATH=. .venv/bin/python execution_guard/hardcore_se_domain_coverage_v1.py
# Exits 1 while any unperformed obligation receives acceptance credit:
PYTHONPATH=. .venv/bin/python execution_guard/raw_acceptance_obligation_gap_probe_v1.py
PYTHONPATH=. .venv/bin/python execution_guard/reinspection_timing_probe_v1.py
PYTHONPATH=. .venv/bin/python -m pytest -q canonical/tests/test_command_reinspection_is_read_only_v1.py
PYTHONPATH=. .venv/bin/python execution_guard/hardcore_se_missing_verb_probe_v1.py
PYTHONPATH=. .venv/bin/python execution_guard/capability_evidence_probe_v1.py --audit-pointers
PYTHONPATH=. .venv/bin/python execution_guard/live_solver_end_to_end_measurement_v1.py \
    --reachability canonical/astra_runtime/tmp/reach_work
PYTHONPATH=. .venv/bin/python execution_guard/live_solver_end_to_end_measurement_v1.py \
    --reachability canonical/astra_runtime/tmp/reach_work --naming
PYTHONPATH=. .venv/bin/python execution_guard/live_solver_end_to_end_measurement_v1.py \
    --per-family 2 --oos 2 --entries new --out /tmp/e2e.json
PYTHONPATH=. .venv/bin/python -m pytest -q canonical/tests/test_goal_front_compiler_v1.py \
    canonical/tests/test_live_brain_route_admission_v1.py \
    canonical/tests/test_front_door_selection_parity_v1.py \
    canonical/tests/test_acceptance_clause_front_door_v1.py \
    canonical/tests/test_goal_compiler_world_binding_v1.py
```
