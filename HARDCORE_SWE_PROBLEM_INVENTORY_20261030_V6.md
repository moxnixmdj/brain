# Hardcore software-engineering problem inventory — 2026-10-30 (V6)

**Scope.** One subject: the machine that writes, changes, verifies and reasons about software.
Document editing, PDFs, images, spreadsheets and every other non-code row appear here only as
wrong destinations the router must refuse. The target is a software engineer that is *more
advanced, faster and smarter than the alternative*, so every problem below is judged by exactly
three questions: does it stop the machine from doing hard engineering work, from doing it fast, or
from telling the truth about what it did?

Every number is measured on this tree today. `execution_guard/swe_request_probe_v1.py` reproduces
the 28-sentence probe; `execution_guard/swe_capability_matrix_v1.py` reproduces the 54-case matrix.

---

## 1. Scoreboard

| measurement | value | how |
|---|---|---|
| registry rows / **routable** rows | 419 / **125** | `is_verified_entry()` over `load_verified_registry()` |
| software-engineering rows | **63** (`python.*` 46, `software.*` 12, `code.*` 4, `shell.*` 1) | prefix census |
| designed matrix (54 hardcore SWE requests) | **REAL 17 · FALSE 0 · REFUSED 37 · DAMAGED 0**, median **100 ms**, p90 863 ms, max 1 129 ms | matrix |
| fresh probe (28 advanced sentences, one ordinary tree) | **6 answered (21.4 %)**, 22 refused honestly, **0 damaged** | probe |
| probe latency | **p50 52 ms · p90 379 ms · max 1 288 ms** | probe |
| repository-scale caller map (`canonical/runtime`) | **18.3 s** cold, 2.4 s warm | direct |
| SWE rows by language | `python.*` **46**, `software.*` **12**, `code.*` 4 (one tree-sitter parser), `shell.*` 1; nothing for Rust, Go, Java, C++ | prefix census |
| routable rows that declare no requirements | **41 of 125** (nothing tells the router what to bind); 12 declare five | `requires` census |
| core test modules red at HEAD | **2** (17 + 1 failures, 18 test ids) — **proved identical** with today's change stashed (`git stash` → same 18 ids) | `pytest` |

Matrix by family: `repair 4/7 · refactor 2/8 · tests 0/3 · analysis 7/12 · toolchain 3/7 · git 0/5 ·
feature 0/7 · honesty 1/5`. Probe by family: repair 1/2, refactor 1/7, tests 2/4, debugging 0/2,
measurement 1/3, analysis 1/3, git 0/3, feature 0/2, polyglot 0/2.

**Read it as a spec:** the machine can read a Python tree, measure four things about it, repair one
red test, rename a symbol and extract one stated statement. Everything an engineer would call
*engineering* — writing tests, restructuring code, adding a feature, touching two files, using git,
catching a bug — is refused, silently or with a message that names an unrelated capability.

---

## 2. Closed today (measured, before → after)

**`Remove the dead code from <pkg>/calc.py.` deleted `calc.py` and certified PASS.**

```
argv    ["rm", "<pkg>/calc.py"]                 (composer prose table: remove → rm)
world   calc.py DELETED
answer  pass=True, PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED
```

The acceptance layer was not wrong — `rm` declares a deletion postcondition and the file was
deleted. The defect was in reading the sentence: "remove … from the file X" makes the file the
*place*, not the object. The prose table already refused "remove the duplicate **lines** from the
file X" for exactly this reason, but its noun list held only things that can be *read* inside a
file; the nouns an engineer uses when asking for a **code change** — dead code, unused imports,
docstrings, comments, whitespace, TODOs, statements, variables, functions, classes — were absent.

After: the sentence invents no command, the file survives, and the door refuses
(`FAIL_CLOSED__STATED_ANSWER_NOT_PROVIDED`). `Delete <pkg>/legacy.py`, where the path *is* the
object, still deletes and still certifies. `canonical/tests/test_a_content_request_never_deletes_the_file_v1.py`
pins both directions, and the prose table's other destructive rows were re-checked by hand
("move the function mul from A to B" → no argv; "move A to B" → `mv A B`, correct).

This is the fifth fabricated pass found in four rounds, and the first that destroys user data.

Gates at this commit: matrix **17 REAL / 0 FALSE / 37 REFUSED / 0 DAMAGED** · probe **6/28, 0 damaged** ·
unified model **33/33** (recompiled) · load-bearing admission **PASS** · drift guard
**FAIL — `FRONTIER_PR_SCOPE_TOO_BROAD_RECONCILE_AND_SPLIT`**: 17 non-intent sensitive files have
accumulated on this one session PR across eight rounds, so the guard asks for a split that a
single-branch session cannot perform. Not weakened, not bypassed — open, and reported.

---

## 3. The problems

### T — truth (the machine must not certify what it did not do)

**T1 · A content request could delete the file.** *Closed today* (§2). **Blast radius: total** — it
was one ordinary sentence away from any repository.

**T2 · The ordinary-command lane is red at HEAD.** `test_an_ordinary_sentence_runs_the_command_it_states_v1`
has **17 failures of 345** and `test_a_stated_command_line_runs_and_is_checked_v1` **1 of 11**,
identical without this round's change. Six of them are the same shape: *"Remove the blank lines from
the file X"* → `FAIL_CLOSED__NO_OBSERVED_EFFECT`. The lane that executes ordinary English commands —
the write lane most requests actually need — therefore has no honest green claim, and its red tests
are the only thing standing between a regression and a repeat of T1.

**T3 · A PASS can hide a red suite.** `"Run the test suite in <dir>"` returns
`pass=True, PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED` on a tree whose tests fail; the
verdict (`tests_pass: false`) is in the artifact, not in the answer. "Run" did happen, so the pass is
defensible — but the caller is handed success and must read JSON to discover failure. The answer must
carry the verdict, not just the execution.

**T4 · Wrong-family routes.** 8 of 28 probe sentences compiled to a capability from an unrelated
family: `explain` → `python.fault.provenance.interprocedural.value.v1`; `dead code` → a *test
selector*; `drop dead code` → the same selector; `repair two files` → `python.tests.audit.unittest`;
`type hints` → the semantic-behaviour compiler. Each refusal is honest, but none is *diagnosable*: a
caller cannot learn from it that the machine has no refactoring engine.

**T5 · Composition converts a failure into an unknown.** `test/write_unit` and `debug/debugger` end
at `FAIL_CLOSED__COMPOSED_STEP_RAISED_OUTCOME_UNKNOWN`: a step raised, nobody knows what the world
looks like, and that is presented as a status rather than as an error to be fixed.

### C — capability (the work itself)

**C1 · No test authoring (0/3 matrix, 0/1 probe).** `python.tests.generate.scaffold.v1` (3 inputs)
and `python.refactor.test_scaffold.fusion.v1` (0 inputs) exist; "write a unit test for mul" raises
inside a composed chain. Writing the failing test is how every real change starts.

**C2 · Refactoring is rename + extract only (1/7 probe, 2/8 matrix).** `split`, `inline`, `move`,
`dedupe`, `add type hints`, `add docstrings`, `remove dead code` — none exists, and two of those
shapes previously *passed* by being answered with a reader (§2, and the pre-round behaviour of
`split`).

**C3 · No feature work (0/7 matrix, 0/2 probe).** "Add `--verbose`", "add logging", "add a
parameter", "implement this issue", "thread an argument through three files".

**C4 · No multi-file edit.** `python.source.crossfile_edit.choreograph.v1` needs an `edits_path`;
"repair calc.py and util.py so the tests pass" is answered by a test audit and refused. The one
capability that could do it is one unbound slot away and has no derivation.

**C5 · No git (0/3 probe, 0/5 matrix).** commit, branch, bisect → `RAW_GOAL_COMPILATION_GAP`. Zero
routable rows declare git, although `git` is installed and `shell.command.run` exists.

**C6 · No debugging.** No breakpoint/frame capability. `python.fault.localize.dynamic.dataflow.v1`
(8 inputs) and `python.fault.provenance.interprocedural.value.v1` (7 inputs) are unreachable; "why
does this test fail" is a compilation gap.

**C7 · No build, dependency or CI capability.** 0 rows. Set-up-CI is explicitly refused by a guard
added earlier (honest, and unimplemented).

**C8 · Python only.** 46 routable `python.*` rows and one tree-sitter parser; the 12 routable rows
that mention JS/node are npm *package* work, not code editing. No editing capability exists in
JavaScript, Rust, Go, Java or C++ — while the JS test runner (`node --test`) and the JS linter
(`node`) are installed, and `code.patch.tree_sitter.verify.v1` is a language-agnostic verifier
sitting unused.

**C9 · No explanation and no dead-code analysis.** The symbol index lists definitions; nothing
computes "what this does" or "what is unreachable". Both requests refuse — correctly, because nothing
declares the effect — which also means the machine cannot answer the first question an engineer asks
of unfamiliar code.

**C10 · The measurement gates need a green tree.** Coverage and mutation refused
(`FAIL_CLOSED__REVIEW_RAN_AND_RETURNED_A_VERDICT`) on the probe's red tree. Honest per their
contract, useless at the moment measurement matters most: a failing repository.

**C11 · The advanced rows exist and cannot be asked for.** Among the 125 routable rows, **41
declare no requirements at all**, so the router has nothing to bind and no sentence can reach them —
including `execution.pipeline.8stage.v1`, `orchestration.verify.bridge_enumeration.v1` and
`code.multilanguage.parse.tree_sitter.v1`. The other extreme is 12 rows that declare five
requirements each — every `*supercomposer*` and `python.test.pipeline.verifier.v1` — with no
derivation that supplies them. The most advanced machinery in the repository is unreachable either
because it asks for nothing or because it asks for too much.

### S — speed

**S1 · Repository-scale questions are slow.** A caller map over `canonical/runtime` costs **18.3 s**
cold (2.4 s with the new index cache). A small tree costs 72 ms. Real work happens on the large tree.

**S2 · Nothing is reused between requests.** Each request reloads 419 registry rows, re-derives its
inputs and writes to the *same* fixed spool path (`spool_0_output.json`), so two requests in flight
collide.

**S3 · The expensive steps are serial.** Coverage 504 ms and mutation 1 294 ms are dominated by
copying the tree and running the suite; independent steps never run concurrently.

**S4 · No resumable long work.** There is no plan, no checkpoint, no resume; every request is one
shot. (The 13 zero-argument `*supercomposer*` rows suggest the intent; none is wired.)

### L — learning and planning

**L1 · Nothing learns from a refusal.** 22 of 28 probe requests refuse, the same 22 will refuse next
time, and no queue records that the machine is missing a refactoring engine, a git surface or a
test author.

**L2 · No decomposition.** A request is routed to one capability (or one composed chain). Nothing
plans "write the test, then change the code, then run the suite, then commit".

**L3 · Ranking is lexical.** 8 of 28 sentences pick the wrong family; the ranker scores word overlap,
and the one thing it cannot see is what the sentence asks for as *work*.

### R — the referee

**R1 · Two core modules are red at HEAD** (17 + 1 failures). A referee that is red cannot certify
anything, including the fixes in this branch.

**R2 · The only broad referee is hand-curated.** 54 designed cases, 37 of them refusals; the change
lane is under-measured by construction, which is why the destructive `rm` and the fast wrong answers
were found by *probe* and not by the matrix.

**R3 · Nothing runs on push.** There is no CI gate; regressions are found when someone runs the
suite by hand (this round: `git stash` twice to prove two failures pre-date the change).

---

## 4. Order to fix (each step makes the next cheaper)

1. **T2 + T3** — get the command lane green (17 failures, one shape) and make every answer carry its
   verdict. This is the write lane; nothing else pays off while it is red.
2. **C1 + C4** — derive `edits_path` / `source_root` + symbol for the three existing rows
   (`tests.generate.scaffold`, `crossfile_edit.choreograph`, `patch.search.test_guided`). That is
   test authoring and multi-file editing, from machinery that already exists.
3. **C5** — declare the git family (commit / branch / bisect / history) over `git`, which is
   installed, and let the existing prose→argv reader fill it.
4. **C11** — one derivation per advanced row, starting with `issue_to_pr.orchestrate` and
   `repo.pr_realize`: the whole point of the registry is that these exist.
5. **C8** — JS/TS behind the tree-sitter kernel that is already installed, bound by language.
6. **S1 + S2** — share the index cache across requests and stop writing to one fixed spool name.
7. **L1 + L2** — refusals feed an acquisition queue; the queue feeds a plan.
8. **R1 + R3** — green referee, then a CI gate that keeps it green.

---

## 5. Reproduction

```bash
cd /home/user/brain
python3 execution_guard/swe_request_probe_v1.py                  # 28 sentences: 6 answered
python3 execution_guard/swe_capability_matrix_v1.py              # 54 cases: 17 / 0 / 37 / 0
python3 -m pytest -q canonical/tests/test_a_content_request_never_deletes_the_file_v1.py
python3 -m pytest -q canonical/tests/test_an_ordinary_sentence_runs_the_command_it_states_v1.py   # 17 red at HEAD
python3 canonical/runtime/verify_brain_unified_model_v1.py       # 33/33
```

---

## 6. One sentence

The machine is an **honest Python reader with three verified write operations**, and the hard part of
software engineering — writing tests, restructuring code, adding features across files, using git,
catching bugs — is still out of reach; measured this round it also had one sentence that DELETED a
source file and called it success, which is now closed and pinned, and the census that found it
(`swe_request_probe_v1.py`) is now part of the repository instead of a scratch script.

*Authority: NONE — sandbox measurement, not independent verification.*
