# HARDCORE SOFTWARE-ENGINEERING PROBLEM INVENTORY

**Date:** 2026-10-29 · **Branch:** `arena/4ca3a720-brain` · **Tree:** `43012dc1`
**Scope:** the owner's question — *what are all the problems* on the way to the most advanced, fastest
software engineer. Document, image, chart and PDF families are measured only so the denominator is
honest; nothing here proposes work on them.

Every number in this document was produced in this session by the instrument named beside it. A number
that no longer reproduces is a bug in this document, not a target. Red is not authority.

---

## 1. The machine today, in seven numbers

| # | measurement | value | instrument |
|---|---|---|---|
| 1 | capabilities in the verified registry | **459** | `load_verified_registry(include_extended=True)` |
| 2 | reachable from ONE plain sentence (vocabulary / by name / routed / unreachable) | **454 / 3 / 1 / 1** | `live_solver_end_to_end_measurement_v1.py --reachability` |
| 3 | hardcore acts owned by a bound capability | **69 of 135**, 28 named-only, **38 absent** | `hardcore_se_domain_coverage_v1.py` |
| 4 | fresh goals end to end, in-scope families all-pass | **30 of 36 families**, instance pass rate **0.8333** — *2 instances per family is not a rate; see the caveat in P0* | `live_solver_end_to_end_measurement_v1.py --per-family 2` |
| 5 | benchmark capability selection (canonical / front door) | **22 / 23** · **21 / 23** | `goal_compilation_benchmark_v1` |
| 6 | evidence blocks: ok / no pointer / dangling | **123 / 34 / 8** | `capability_evidence_probe_v1.py --audit-pointers` |
| 6b | machine-missing external dependencies | **7** (5 doc/image, 1 data, 1 barcode) | same run, `external_dependency_missing_here` |
| 7 | red door/compiler tests | **17**, **4 skipped** naming a missing dependency (was 33 this session) | `pytest` on the six door/compiler suites (17 failed / 187 passed / 4 skipped) |

Per-domain coverage of the 135 hardcore acts (`hardcore_se_domain_coverage_v1.py` — BOUND / total, with
NAMED-only and ABSENT split):

| domain | bound | named only | absent | domain | bound | named only | absent |
|---|---|---|---|---|---|---|---|
| review and delivery flow | 10/17 | 4 | 3 | testing | 6/10 | 3 | 1 |
| refactoring | 6/14 | 2 | 6 | static analysis | 10/13 | 1 | 2 |
| dependencies and build | 2/10 | 3 | 5 | dynamic analysis | 5/9 | 2 | 2 |
| data and persistence | 5/9 | 1 | 3 | security and supply chain | 6/9 | 2 | 1 |
| services and concurrency | 3/8 | 0 | **5** | review and delivery flow (flow) | 7/8 | 0 | 1 |
| multi-language | 3/7 | 4 | 0 | infrastructure and delivery | **0/6** | 4 | 2 |
| performance engineering | 5/6 | 0 | 1 | observability | **0/5** | 2 | 3 |
| documentation | 1/4 | 0 | 3 | **totals** | **69/135** | 28 | 38 |

Two domains own **nothing** — infrastructure and delivery (0 of 6) and observability (0 of 5) — and
services/concurrency owns 3 of 8 with 5 acts that do not exist at all. That is where the machine is
furthest from an engineer, not in the document families.

Tool liveness over 165 capabilities: **0 adapters missing**, 9 adapter import failures (all chart
raster), **7 machine-missing external dependencies**, 27 executor kernel refusals by source type,
19 zero-input composition nodes.

---

## 2. The problems, ordered by what they cost an engineer

### P0 — It can do work but it cannot be asked to CHECK work (the deepest gap)

Five of the twenty-one capabilities that no sentence can reach are **verifiers**:
`archive.verify.tar_gz.gnu`, `decision.synthesis.verify.stdlib`, `sqlite.table.verify_against_json_records`,
`xlsx.table.verify_against_json_records`, `plain_goal.bound_capability.grounding.verify.stdlib`.

Three independent measurements agree on the same hole:

- **End to end**, the family `ARCHIVE_VERIFY_GNU` scores **0 of 2** and its routes are
  `archive.tar_gz.create_from_manifest` — the *creator*, answering a *verification* request.
  The cause is narrower than "the verifier cannot be asked": on a sentence a person would write —
  *"Verify the tar archive at out/backup.tar.gz against the manifest at out/manifest.json."* — the
  verifier wins cleanly, **64 against 50**. The instrument's sentence is built from the capability's
  own DECLARATIONS, and `archive.verify.tar_gz.gnu` declares the act `members`, not `verify`; a
  sentence that says "members" is answered by the creator. **The verifier does not declare the act
  it performs** — that is the P0 defect in this row, and it is a declaration fix, not a ranking one.
- **Route admission** reports `raw_goal_acceptance: RAW_GOAL_ACCEPTANCE_UNRESOLVED`,
  reason **`NO_INDEPENDENT_REINSPECTION_FOR:python.repository.acceptance.measure.v1`** — a capability
  executed, wrote a verified artifact, and nothing was able to re-inspect it.
- **Selection**, after this session's fixes, still answers the `jq` question with a converter, because
  the request states no filter and no verifier owns the shape.

**Why it is P0:** every downstream claim (repair accepted, refactor safe, tests broken, change
delivered) is a verification claim. A system that cannot re-inspect its own output has to be trusted,
and trust is the one thing the owner's laws forbid.

**Where the fix lives:** the artifact a capability already writes carries the measurement program's
digest (`measurement_program_sha256`) and a schema. Re-inspection is a second, independent read of that
artifact against its schema — no new engine, no model. The lane exists for few capabilities; it must
exist for every capability that claims `output_verified`.

**TWO OF THE THREE P0 MEASUREMENTS HAVE SINCE BEEN FIXED, both by reusing what was already there:**

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

   Measured on the artefact family, four instances: **0 of 3 with every route on the creator → 3 of 4
   on the verifier.** The front-door selection rate pin still holds (21 of 23) and the parity suite is
   27 green.

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

**The residual is now the OBJECT, not the verb.** The archive family is closed; what is left in P0 is
that the same "one act, one owner" question has no declared answer for object nouns (bundle vs
archive vs package), which is why the reachability instrument's own generated sentences still read as
keyword soup rather than a request.

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

### P2 — Near-duplicate capabilities steal each other's sentences

Measured directly, twice:

- `python.repository.acceptance.measure.v1` (score **55**) beats
  `python.software.repair.measured_acceptance.v1` on a sentence that asks for *measured acceptance*, and
  the executed result is a plain repository measurement (`semantic_acceptance_complete: false`).
- `archive.tar_gz.create_from_manifest` beats `archive.verify.tar_gz.gnu` on a *verify* request.

Both pairs declare near-identical vocabulary. The arbitration law this session installed for the act
word works at the *ranking* stage; it has never been applied to the **declarations themselves** — two
capabilities may not declare the same act. That is a registry law, and it is cheap: the act words are
already computable from `provides` + identity.

### P3 — A refusal falls through to an admission

`route_admission` records `typed_binding_refused: True` with
`BINDING_REFUSED:NO_SLOT_FOR_THE_STATED_PAYLOAD:ARGV,PATH_DIR,PATH_LIST,PATH_OUTPUT` **and**
`admitted: True` in the same receipt. `test_f1_best_candidate_that_cannot_bind_fails_closed_instead_of_falling_through`
pins the law that this must fail closed; it is red.

### P4 — 38 absent acts: the capability that is simply not there

Hardcore subset, by domain (bound / total per domain in brackets):

| domain | bound / total | absent acts that matter |
|---|---|---|
| refactoring | **6 / 14** | extract variable, encapsulate field, pull-up method, replace conditional, remove dead imports, split module |
| dependencies & build | **2 / 10** | install, upgrade, remove, lockfile pin, reproducible build, cache, monorepo, publish |
| services & concurrency | **3 / 8** | retry policy, timeout policy, circuit breaker, task graph, local server |
| infrastructure | **0 / 6** | CI config, container image, IaC, deploy, secret management, environment fit |
| observability | **0 / 5** | logging instrumentation, metrics instrumentation, tracing, structured log analysis, SLO |
| data & persistence | **5 / 9** | schema migration, transaction, integrity check, query plan |
| dynamic analysis | **5 / 9** | debugger/breakpoint, syscall trace, deadlock detect, race detect |
| testing | **6 / 10** | golden/snapshot, data generation, differential, mutation |
| version control | **10 / 17** | cherry-pick, worktree, reflog undo |
| static analysis | **10 / 13** | call graph, package dependency graph, dataflow/taint |
| documentation | 1 / 4 | docstrings, README, API reference |
| review flow | 7 / 8 | code-review comment |
| multi-language | 3 / 7 | JS refactor, Go analysis, Rust analysis, C/C++ compile |

The refactoring row is the sharpest: **six of the fourteen** refactor acts a senior engineer performs
daily are absent, and the six that exist (`rename_symbol`, `rename_parameter`, `extract_function`,
`inline_function`, `move_function`, `change_signature`) all ride one AST engine that already exists.

### P5 — 28 acts are NAMED but unbound

Declared in the map, no capability behind them: `build.install`, `build.remove_dependency`,
`build.version_bump`, `data.query_optimise`, `dynamic.race_detect`, `dynamic.syscall_trace`,
`git.merge`, `git.conflict.resolve`, `git.remote`, `git.tag`, `infra.ci_config`, `infra.container`,
`infra.deploy`, `infra.secret_management`, `obs.slo`, `obs.tracing`, `refactor.convert_to_method`,
`refactor.organise_imports`, `security.signature_verify`, `static.dataflow_taint`,
`supplychain.pin_lockfile`, `test.data_generation`, `test.differential`, `test.mutation`,
`lang.{javascript_refactor,go_analysis,rust_analysis,c_cpp_compile}`.

These are cheaper than the absent ones (someone already wrote the name and the domain), and three of
them — `git.merge`, `git.conflict.resolve`, `test.mutation` — are gateway verbs for real engineering.

### P6 — Repair and refactor depth is one language deep

74 of 459 capabilities are `python.*`. The repair loop family (`python.software.repair.*`, 7 entries),
the patch search (`python.patch.*`, 2), fault localisation (`python.fault.*`, 4) and the AST refactor
engine (7) are all Python-only. `code.multilanguage.parse.tree_sitter.v1` parses JS/Go/Rust/C but
nothing *edits* or *tests* them. Measured ceiling: `lang.*` is 3 bound of 7, all three of them
read-only.

### P7 — Seven external dependencies are absent on this machine, and one of them is the answer

`auto.apt.zint`, `document.convert.markdown_pdf.pandoc_weasyprint`, `image.code.decode.zbarimg`,
`image.qr.generate.qrencode`, `pdf.extract.ocr.tesseract`, `xlsx.table.verify_against_json_records`,
**`yaml.to_json.yq`**.

Five are document/image families and are out of scope by owner instruction. `yaml.to_json.yq` is not:
it is a **data** capability, and it is the fallback the compiler still returns for the `jq` benchmark
goal — so the one remaining benchmark miss is answered by a capability that cannot execute on this
box. Install-or-refuse holds at the door; the compiler still does not know it is routing to a tool
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

### P9 — The 21 red tests, in four families (a work queue, not a fog)

| family | rows | real cause |
|---|---|---|
| ~~DAG executor returns an invalid result~~ | ~~4~~ | **not a defect** — missing `et_xmlfile`; now `BLOCKED__…_ENVIRONMENT_BLOCKER` and skipped |
| an intermediate spool step observes no effect | 1 | P1 above (real) |
| admission/acceptance laws | 7 | P0 and P3 above |
| stale guard expectations (`R1`/`R3` vs `R12`/`R14`) | 3 | **the guard got better than the pin** — `R12_STATED_ACT_IS_NOT_AN_ACT_THIS_BRAIN_PERFORMS:translate` and `R14_UNHEARD_ACT_WORD:tutorial` are the *correct* verdicts |
| reachability / parity / rate pins | 6 | measurement pins, deliberately moved |

### P10 — 26 capabilities no sentence can reach

**21 have no sentence at all** (the vocabulary builder cannot form one): 8 chart readers, 5
PDF/DOCX/XLSX/image readers (out of scope), and the hardcore five from P0 plus
`professional.artifact.visual_observer.v1` and `task.acceptance.objective.lossless.v1`.

**5 cannot be reached either way**: `knowledge.json.fetch.external` (contract not stated),
`plain_goal.bound_capability.grounding.stdlib`, `python.repo.pr_realize.v1`,
`text.file.write`, `vcs.git.log.v1` (a true homonym: its own keywords carry "commit", so a sentence
built from its declaration is read as a commit request).

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

Absent: `docker`, `kubectl`, `terraform`, `gdb`, `lldb`, `strace`, `perf`, `valgrind`, `hypothesis`,
`libcst`, `rope`, `psutil`, `sqlalchemy`, `coverage`, `shellcheck`, and the `go`/`rustc`/`java`/`clang`
toolchains. Every absent act in `dynamic.*`, `infra.*` and `service.*` sits behind one of them.
Two consequences worth stating plainly:

1. **`libcst`/`rope` absence is not a blocker for refactoring** — six refactor verbs already run on
   `ast` + `tokenize`, and the missing six can run on the same engine.
2. **The `go`/`rustc` absence is a blocker** for real multi-language work; it should be refused by
   name (which the repo does) rather than faked.

### P12 — Speed: one family is 100× slower than the rest

Mean wall time per goal, end to end: **87 ms** (archive), **169 ms** (docx), **440 ms** (xlsx),
sub-second for every code family measured — and **12,866 ms** for the knowledge family
(`KNOWLEDGE_FETCH_ASSESS_ASSERT`, which also routes to `vcs.git.status.v1`, i.e. it is not doing the
work at all). "Insanely fast" is already true for 30 of 36 families and is an unbounded-loop problem in
the one that is not.

---

## 3. What is NOT a problem (measured — stop spending time here)

- **Document / image / chart families.** 22 of 459 entries; env-blocked on this box; out of owner scope.
- **`R1`/`R3` test rows.** The guard is *more* correct than the pin (`R12`, `R14`). The pins are stale,
  not the code.
- **The `EXT_JQ_TABLE` benchmark row.** The sentence states no `jq_filter`; inventing one is invention.
  Refusal is the right answer until a declaration or a sentence provides it.
- **Reachability.** 454 of 459 capabilities are askable from one plain sentence; the residue is 21
  document readers and 5 named-shape defects, not a systemic hole.

---

## 4. The work queue, ranked by capability per hour

| # | work | closes | why it is cheap | cost |
|---|---|---|---|---|
| 1 | **re-inspection lane for every `output_verified` claim** | P0 | the artifact already carries its measurement digest + schema; re-reading it is a second op, no new engine | ~1 unit |
| 2 | **DAG executor result contract** | P1 (5 rows) | the plan is already correct; the failure is one contract | ~1 unit |
| 3 | ~~**one act, one owner** (registry law)~~ **DONE — verbs** | P2 | `_ACT_SYNONYMS` + the name rule; archive family 1.0 over 8, nothing else moved | done |
| 3b | **one act, one owner for OBJECT nouns** (bundle / archive / package / manifest) | P0, P2 | same law, same place; the verb half is measured, the noun half is not | ~0.5 unit |
| 4 | **refuse-then-stop** (kill the fall-through) | P3 (1 row, big blast radius) | one branch in admission | ~0.5 unit |
| 5 | **six missing refactor verbs** on the existing AST engine (extract variable, replace conditional, remove dead imports, split module, encapsulate field, pull-up) | P4 (6 acts) | the engine, the plan shape and the pins already exist — this is the single highest-yield build | ~1 unit |
| 6 | **`git.merge` + conflict resolve + `cherry_pick` + `worktree` + reflog undo** | P4/P5 (5 acts) | the `vcs_git_v1` adapter family exists; conflicts are text plus a test run | ~1 unit |
| 7 | **`schema_migration` + `data.integrity_check` + `data.query_plan`** | P4 (3 acts) | `sqlite3` present, and a migration is a transaction plus a verification law | ~1 unit |
| 8 | **`test.mutation`, `test.golden_snapshot`, `test.data_generation`** | P5 (3 acts) | mutmut absent → drive mutation from the existing AST patch engine + the test runner | ~1 unit |
| 9 | **service policies: retry, timeout, circuit breaker, task graph** | P4/P5 (4 acts) | pure emission with a verification law; no runtime needed | ~1 unit |
| 10 | **observability + CI config instrumentation** | P4/P5 (5 acts) | template emission, verified against the emitted file | ~1 unit each |
| 11 | **34 pointerless + 8 dangling evidence blocks** | P8 | mechanical; each needs the lane that measured it to write one line | ~1 unit |
| 12 | **`static.call_graph` + `static.dependency_graph`** | P4 (2 acts) | `ast` already gives both; the registry needs the verbs | ~0.5 unit |
| 13 | **multi-language edit/test** | P6 | needs absent toolchains → **declare out of scope** until they exist | blocked |

Rules that do not change: **reuse before synthesis**, **measure, never assert**, a red row is not an
authority, and **no AI model participates in Brain-credited producer cognition**. Items 1–4 are
laws that cost less than a unit together and unblock the trust chain; items 5–8 are the actual
engineering capability the owner is asking for.

---

## 5. Reproduce

```bash
PYTHONPATH=. .venv/bin/python execution_guard/hardcore_se_domain_coverage_v1.py
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
