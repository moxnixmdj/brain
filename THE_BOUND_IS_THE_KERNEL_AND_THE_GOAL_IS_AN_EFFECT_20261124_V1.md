# The bound is the kernel, and the goal is an effect — 2026-11-24

Authority: `NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT`. Everything below was run on
this machine, in this session, on branch `arena/9026f2bc-brain`. Nothing here is
independently verified, nothing here is a benchmark score, and nothing here is
§6 "done". The numbers are the numbers; the failures are listed with the numbers.

---

## 0. Requirements read, and the §2 contradiction resolved

The mission as given: one algorithm that enters an arbitrary environment, learns
from a single experience, keeps what it learned permanently, and knows what it
does not know — with **zero model calls at runtime**, **no world-facts warehouse
in weights**, knowledge from an instant-knowledge store, and honesty above
encouragement. "Elon's law": the best part is no part.

**The contradiction** (permanent learning implies persistence; zero-knowledge
implies no store) is resolved by the boundary this repository already draws, and
this session did not move it:

| | Where it lives | What it may contain | Test it must pass |
|---|---|---|---|
| **Mechanism** | code (weights, when there are weights) | scan, ask, bind, plan, verify, lift, admit | removable without losing a fact |
| **Knowledge** | `canonical/astra_runtime/state/PERFECT_ALGORITHM_MEMORY_V1.json` | priors (observed facts), plan rules, **lifted operators** (contracts) | add or delete a row without retraining |
| **Instant knowledge** | local guides → web, read-only, provenance-carrying | documents | never counted as capability; never authorises an action |

No evidence in this session showed a better boundary. One refinement was
forced by measurement and is recorded in §2.

---

## 1. Research

### 1.1 This project — including what the prompt claims exists and does not

The tree holds **2,261 runtime modules**, **5,605 Python files**, 23 Perfect
Algorithm tests, 35 environment-learning tests, and ~700 dated documents. The
loop the owner asked for already exists in pieces:
`perfect_algorithm_v1.py` (scan → right question → plan → act+verify → learn →
admit → save), `environment_learning_v1.py` (affordance model, shortest plan),
`settlement_v1.py` (expected information gain), `local_guide_v1.py` +
`jit_knowledge_v1.py` (instant knowledge), `computer_env_v1.py` (a real
directory, real programs discovered from `PATH`), `confinement_v1.py` (the
substrate), and `computer_execution_boundary_v1.py` (the fail-closed door).

**Names in the brief that do not exist in this tree** (checked by search, not by
memory): `typed_invention_v1.py`, `epistemic_scan_acquire_compress_v1.py`,
`BRAIN_POLYGLOT_CST_SKILL_STORE_V1`, `verified_skill_crystallizer_ir_bridge_v1`,
`CUMentalWorldModel`, `BELIEFWEAVER`, commit `209bbc6c`, "Iteration 70/71/75",
"447 skills", "0.35 s". Those belong to another session's narration. The
capability they describe is partly real under other names; the specific
artefacts are not here, and I did not build on them.

### 1.2 Frontier — used as ideas, never as runtime

* **Isolation.** The 2026 consensus is unambiguous: a plain subprocess is *"not a
  security boundary. Fine for demos only"*; hardened containers are defensible
  for low-risk tools and one kernel bug from escape; gVisor and Firecracker are
  the stronger rungs ([3](https://opennash.com/blog/where-agent-code-actually-runs-choosing-a-sandbox-for-ai/),
  [1](https://amux.io/guides/ai-agent-sandboxing/)). The repository's own
  2026-11-24 review had measured exactly this: a "confined" command wrote outside
  its worktree while the receipt said `host_untouched=True`.
* **Verification.** OSWorld-Science (2026) reports 26.3% full credit, **60.6% of
  failing runs ending with no graded artifact**, and — the sentence that matters
  here — *"When agents do verify, they mostly confirm that the output exists and
  has the expected structure"*
  ([1](https://arxiv.org/html/2609.39903v1)). The failure this session found in
  our own loop is the frontier's failure too.
* **Benchmark surface.** OSWorld 2.0's public leaderboard tops out near 20.6%
  (Opus 4.8, max effort) while vendor tables quote ~70; Terminal-Bench 2.1's
  verified top is 83.8% (Fable 5 in Claude Code), with ±3.4 pts of harness effect
  ([2](https://www.digitalapplied.com/blog/osworld-terminal-bench-agent-benchmarks-explained)).
  Reported numbers need their surface named. None of these were run here.

---

## 2. Verdict: what is real, what is not, and the real bottleneck

**Measured this session, in this order:**

1. **The substrate was the first wall.** `confinement_v1` ran a plain
   `subprocess` and `host_untouched` meant "git porcelain is unchanged". Every
   route above it — curriculum, front door, computer exploration — refused with
   `FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT`, correctly.
   Three tests in `test_computer_env_v1.py` still fail for exactly that reason
   (they are listed in §5 and were **not** touched).
2. **With a real boundary, the loop runs — and it was confidently wrong.** Given
   "compress the input into out.gz" on a real computer, the Perfect Algorithm
   scanned 11 states / 36 transitions in 0.45 s, planned `run_xz`, saw a file
   called `out.gz`, reported `PASS`, admitted the rule on two fresh instances,
   saved it, and replayed it instantly on two more — **four passes, four wrong
   artifacts**: xz bytes (and in a later run, a zip container) inside a file
   named `out.gz`. `gzip` refuses both.

**So the real bottleneck is not learning, not planning, not isolation, and not
knowledge.** It is this: **the goal was a name in an observation, not an effect
in the world.** Instant learning does not fix that. It makes it faster, and then
makes it permanent.

---

## 3. One plan, minimal, and what was rejected

The plan, in the order the measurement forced it:

1. **A boundary the kernel enforces** — `os_isolation_v1.py`: user + mount + pid
   + net + ipc + uts namespaces, a tmpfs root, read-only `/usr` `/bin` `/lib*`,
   a **built** `/etc` (not the host's), a chroot, and **every capability dropped**
   before the payload starts. Admission is by **attack**: `probe()` runs a
   payload that tries to read a host canary, write a host path, list a host
   directory, open TCP/UDP/DNS, mount, chroot again, read `/dev/mem`, and reach
   `host_home`. `ISOLATED` only if every one is blocked **and** the payload is
   measured holding no capabilities.
2. **The goal is an effect** — `effect_oracle_v1.py`: an artifact is correct iff
   (a) its header is what **this machine's compressor writes** for the format its
   name declares, and (b) the machine's reader for that format returns **exactly
   the source bytes**. Both parts are derived from the machine, not remembered.
3. **The durable unit is a contract** — `lifted_operator_v1.py`: program + roles
   + precondition + checkable effect, bound at use time to *this* environment's
   vocabulary and re-verified *here*; refused when ambiguous, refuted (and
   counted, never deleted) when the effect does not hold.
4. **Wiring, not a new organ** — `learn_model()` takes a live `goal_check`; the
   Perfect Algorithm takes `goal_check` and `effect_contract`, consults the
   operator before falling back to a full scan, and lifts a contract only when
   the effect was verified. No new store, no new gate, no second learner.

**Rejected, and why:**

* **A new curriculum / a new learner / a new admission gate** — the ones that
  exist are sufficient; the defect was a missing check, not a missing organ.
* **Opening the front door** (`live_brain_route_admission_v1`) now that isolation
  is real — the 2026-11-24 review requires a reviewed design, trustworthy
  effect/receipt validation, independent capability evidence and pre-registered
  tests before retrying. Two of the four now exist; **independent verification
  does not**, so the door stays shut. Routing around it would have been the
  exact failure mode the review documented.
* **Trusting `gzip -dc` as proof of gzip** — measured and wrong: gzip(1)
  extracts zip archives. A liberal reader is not a format check.
* **Storing the action list** — measured below: it transfers on 1 of 2
  renamed-vocabulary instances; the contract transfers on 2 of 2.
* **Scanning everything, always** — kept as the fallback, not the method; the
  contract replay is 60–100× cheaper.
* **A cgroup/seccomp pass, or gVisor/Firecracker** — a real strengthening, and
  the honest next rung; not attempted here (no bwrap, no runsc, no KVM in this
  sandbox), and the current boundary must be labelled for what it is (see §5).

---

## 4. What was built

| File | Role |
|---|---|
| `canonical/runtime/os_isolation_v1.py` | namespaces + chroot + capability drop, with an 18-attempt escape probe as its admission test |
| `canonical/runtime/effect_oracle_v1.py` | header-derivation + round-trip oracle; `NOT_A_GOAL` / `WRONG_FORMAT` / `NO_READER` / `NO_ORACLE` are answers |
| `canonical/runtime/lifted_operator_v1.py` | lift / bind / find_action / apply / refute |
| `canonical/runtime/confinement_v1.py` | **substrate replaced**: `execute()` runs under `os_isolation_v1` or refuses; `host_untouched` now means the kernel said so *and* the porcelain agrees |
| `canonical/runtime/environment_learning_v1.py` | `learn_model(goal_check=…)`, `drive(goal_check=…)`: a goal state is recorded where the world said yes |
| `canonical/swe_kernel/perfect_algorithm_v1.py` | `run(goal_check=…, effect_contract=…)`; operator replay before full rescan; contract lifted only when verified |
| `canonical/tools/learn_in_a_real_computer_probe_v1.py` | three real instances in three sandboxes, A/B/renamed |
| `canonical/tools/literal_or_lifted_transfer_probe_v1.py` | literal vs lifted vs system, four conditions, one external judge |
| `canonical/tests/test_os_isolation_v1.py`, `test_effect_oracle_v1.py`, `test_lifted_operator_v1.py`, `test_learning_needs_a_verified_effect_v1.py` | 30 new tests, no mocks |

Receipts: `canonical/verification/OS_ISOLATION_PROBE_RECEIPT_20261124_V1.json`,
`REAL_COMPUTER_LEARNING_RECEIPT_20261124_V1.json`,
`LITERAL_OR_LIFTED_TRANSFER_RECEIPT_20261124_V1.json`.

---

## 5. Results, honest

**The boundary measures as a boundary.** 18 attempts, every escape blocked,
`CapEff = 0000000000000000`, fresh pid namespace (2 pids), no route. `gzip -t` on
the artifact produced *inside* it passes on the host afterwards, and the host
canary is never written.

**What the boundary is NOT.** It shares the host kernel. Rung 2 of the four-rung
ladder the 2026 literature describes, not rung 3 (gVisor) or 4 (microVM). Kernel
exploits, and any bug in this module's own ordering, are outside its promise. It
is a real boundary of the class the review demanded, not a stronger one.

**Learning, measured (three sandboxes, one goal):**

| stage | instance | time | scan | plan | admitted | artifact (external check) |
|---|---|---|---|---|---|---|
| A | first, learned from scratch | 0.68 s | 11 states / 36 transitions | `run_gzip` | ADMIT (2 fresh) | real gzip, round-trip identical |
| B | new bytes, same names | 0.09 s | none | recall | — | real gzip, identical |
| C | source **renamed** (`report.txt`) | 0.11 s | none | recall | — | real gzip, identical |

**What the artifact is worth, with and without the oracle** (same fixture,
`test_learning_needs_a_verified_effect_v1.py` + the A/B/C run above):

| goal checked by | reported | artifact |
|---|---|---|
| the name in the observation | PASS ×3, saved, replayed | xz/zip bytes in `out.gz` — **wrong, 4 times** |
| the effect oracle | PASS ×3, saved, replayed | real gzip, round-trip identical ×3 |

**Literal vs lifted, one rule learned once, three fresh instances:**

| condition | vocabulary | literal replay | lifted contract | the system |
|---|---|---|---|---|
| b same vocab, source renamed | `run_gzip`, … | ✅ | ✅ | **0.006 s** replay-from-memory |
| c renamed vocab, program named | `pack_with_gzip`, … | ❌ no such action | ✅ rebinds + re-verifies | **0.009 s** replay-from-**operator** |
| d vocabulary names nothing | `a`, `b`, `c` | ❌ | ❌ refuses (honest) | 0.579 s — rescans, still correct |

That table is the answer to "what should be saved": the contract transfers where
the action list does not, costs 60–100× less than relearning, and **refuses**
rather than guesses when the world gives it nothing to bind to. It is also its
own limit: a rule that names a program cannot survive a machine where the
program has no name — and condition d shows the loop stays correct by falling
back to scanning.

**Suites run:** 127 passed across
`test_perfect_algorithm_v1` (23), `test_perfect_algorithm_probe_restore_v1`,
`test_environment_learning_v1` (35), `test_admitted_confinement_v1`,
`test_confine_mount_failure_v1`, `test_confined_dispatch_v1`,
`test_jit_knowledge_v1`; 30 new tests pass; `repo_integrity_guard_v1.py
--base main` → **PASS, 0 violations**.

**Still failing, unchanged and deliberately not hidden:**
`test_computer_env_v1.py::TransferTests` — 3 failures, all
`FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT`, because the
curriculum channel still routes through the closed front door (§3, rejected
idea). The substrate it demands now exists; the front door was not opened
without the independent verification the review requires.

---

### The effect has a negative half

A goal is not only "this artifact appeared"; it is also "nothing I was not asked
to touch was destroyed". `run(preserve=[...])` checks it after the plan: a plan
that reaches the goal by deleting the input is reported as
`OPEN__PLAN_DESTROYED_A_PRESERVED_FILE`, is not a pass, and writes no rule
(measured in `test_learning_needs_a_verified_effect_v1.py::DestructiveSuccessTests`).
Without this, `gzip input.txt` is a success that costs the user their file, and
instant learning makes it the thing the system knows.

## 5b. Second iteration — the hand-holding removed

The first iteration's probes were given the source's name and the effect
contract by me. That is hand-solving, so it did not count. This iteration
deletes it.

**The format table is gone.** It held `gz -> gzip`, `bz2 -> bzip2` — memorised
world knowledge in the costume of a derivation, and it broke on the first
compound name. What replaced it is derivation plus proof:

* candidates come from the machine's own naming (`computer_env_v1.programs_for`),
  and every candidate is only a **guess**;
* a guess becomes a **reader** only by carrying a scratch copy of the source out
  and bringing it back byte-identical, in a scratch room;
* a compound name is a **chain**, decoded outermost-first, each layer proven
  separately — `out.tar.gz` is verified through `[gzip, tar]`;
* the artifact's header must match the **invariant** header the encoder itself
  writes. Measured while building this: a fixed 4-byte signature wrongly
  rejected a real `.tar.gz`, because byte 4 is gzip's FLG (0x08 when a filename
  is stored, 0x00 when piping) — an option, not the format. The invariant is now
  computed by invoking the same encoder two different ways and taking what stays
  the same.

**The instruction now supplies the contract.** `effect_oracle_v1.oracle_from_goal`
reads the output name from the sentence (`into out.gz`), reads the source from
the world (a file the sentence names, else the only file that is not the output),
and returns a live predicate plus `.contract(env)`. Two candidates and no named
input is a refusal, not a choice. Both probes now take **a sentence and nothing
else**, and reproduce the previous results:

| stage | status | derived contract | artifact |
|---|---|---|---|
| a | PASS, 0.85 s, 14 states / 39 transitions | `{source: input.txt, output: out.gz}` | EFFECT_VERIFIED, operator lifted |
| b | replay 0.09 s | `{source: input.txt, …}` | identical |
| c (renamed source) | replay 0.10 s | `{source: report.txt, …}` | identical |

Transfer with goal-only input is unchanged: literal fails on the renamed
vocabulary, the operator replays in **0.03 s**, opaque vocabulary refuses and
the loop rescans in 0.647 s.

**An integrity defect found while doing it, and closed.** Asked for
`out.tar.gz`, the local-guide tier answered with
`canonical/governance/EXPLORE_CHANNEL_STATE_20261019_V1.md` — a file recording an
**earlier run of the same goal, including the plan that worked**. On any machine
that carries our own results, the "guide" is the answer key, and reading it is
self-answering. `local_guide_v1` now classifies our own records (verification,
evidence, state, receipts, baselines, ledgers) and excludes them **by default**;
reading them requires saying so explicitly. A real guide in the same tree is
still served. Four tests.

**A reach limit, measured and left standing.** `archive the input into out.tar.gz`
returns `OPEN__NO_PLAN_AFTER_SCAN` on a vocabulary whose `tar` action writes a
plain archive: the artifact is a tar, the name promises gzip, the oracle refuses,
and the loop says OPEN. That is the correct answer — the oracle can verify a
compound effect that the **action vocabulary cannot yet produce**. It is exactly
the composition gap, now with a receipt instead of a hypothesis.

## 5c. Two lessons, one format neither makes

The compound goal was the measured gap, so it was closed by composition, not by
a new action.

* A contract now carries its **argv shape**, because a contract that names a
  program but not how it was called can be replayed and never composed.
* `compose(O1, O2)` fills the slots, carries a **stream** program's stdout to a
  file (the gzip step prints; without capture the second layer vanishes and the
  failure looks like a format problem), and then hands the outcome to the chain
  oracle. Composition is trusted by the **effect**, on a format no action offers.
* The goal-derived binding outranks the operator's own precondition, and a
  world with two candidate sources is still a refusal.

Receipt (`COMPOSED_LESSONS_RECEIPT_20261124_V1.json`): teach
`archive the input into out.tar` (tar, operator lifted, admitted), then
`compress the input into out.gz` (gzip, lifted, admitted), then ask for
`out.tar.gz` — an environment whose every action writes one layer.
Result `PASS__COMPOSED_A_NEW_FORMAT`: `tar -c input.txt` → `out.tar`,
`gzip -c out.tar` → `out.tar.gz`, chain `[gzip, tar]`, and the judge outside all
of it, `gzip -dc out.tar.gz | tar -xOf -`, returns the source's bytes exactly.

**A soundness bug was found on the way and closed.** The caller's program list
was used as the candidate set for *every* layer, so with `["tar","gzip"]` handed
in, `tar` proved itself as the reader for `gz` (`tar -xOf` returns the source
bytes) and a **plain tar named `out.gz` came back EFFECT_VERIFIED**. Candidates
are now filtered per layer: a hint list may say which programs exist, never lend
a layer a reader. Two tests pin it. A second one: the memory-replay path still
judged by the artifact's **name**, so replaying a tar plan into `out.tar.gz`
passed and produced a file that was not one; replay is now judged by the effect.

## 5d. Composition is transitive, and the four proposed mechanisms audited

Two layers was an arbitrary stopping point in my own code. `out.tar.gz.xz`
declares three, and the fold handles any number: each contract's output name
becomes the next one's source, the last writes the goal's own name, and the
chain oracle -- which decodes the whole stack outermost-first -- decides.

Receipt: teach `out.tar` (tar), `out.gz` (gzip), `out.xz` (xz), each lifted and
admitted, then ask for `out.tar.gz.xz` -- a format **no action in that
environment offers**. Result `PASS__COMPOSED_A_NEW_FORMAT`, layers
`[tar, gzip, xz]`, chain `[xz, gzip, tar]`, and the judge outside all of it
(`xz -dc out.tar.gz.xz | gzip -dc | tar -xOf -`) returns the source bytes exactly.
Four tests, including one where a single wrong link refutes the whole chain and
one where a missing shape stops the fold **before anything runs**.

**The layer is matched by proof, not by name.** `gz` in `gzip` is pattern
matching, and it fails in both directions: it let `tar` stand in for the gz layer
(a plain tar named `out.gz` came back EFFECT_VERIFIED), and it refuses an alias
called `zpack` that really is gzip. `prove_layer` asks the behavioural question --
encode the source, decode the artifact back to the same bytes, write the header
the format actually has (empty for tar, so the round trip carries it alone).
Measured: `prove_layer("gzip","gz")` proved, `prove_layer("tar","gz")` refused,
`prove_layer("/tmp/.../zpack","gz")` proved, and a store whose gzip contract is
named `zpack` composes a verified `out.tar.gz` with chain `[gzip, tar]`.

### The four mechanisms in the brief, audited

| claim | state |
|---|---|
| `zygote_worker_pool_v1.py` exists, CoW forks ~1-2 ms | **verified**: prewarm 234.94 s->ms, dispatch median **2.12 ms** (min 1.83, max 6.00), 16-way sharded **18.77 ms**, 447 capabilities in the registry |
| `witness_inversion_v1.py` exists, and the **75.2%** reach ceiling is a repo measurement | **verified as a repo measurement** (2,178 fix pieces from 500 SWE-bench Verified tasks; 18.7% asymptote). Not independently re-measured here |
| "repo-native component mining" as a *new* play | **already the core of `witness_inversion_v1`**: it reads its alphabet from the failing frame's own locals, attributes and the module's callables. Rebuilding it would be the duplication the brief forbids |
| "dual-program splicing" via a separating guard | **unbuilt here, unverified**: plausible, but it needs `witness_inversion_v1`'s candidate chain to produce partial-passing programs first. Doing it before that exists would be inventing a mechanism with nothing to merge |
| "16-way parallel CoW rollouts scored by residual reduction" | **the substrate is verified** (18.77 ms for 16 branches). The *scoring function* is the open part: our effects are oracle-checkable, so branches can be verified, not merely scored |
| "unified Petri net across GUI/CLI/SQL/code" | **not attempted**: `MealyAPICompiler`, `simulate_plan`, `MultiLayerSnapshot`, `CUMentalWorldModel`, `typed_invention_v1`, `epistemic_scan_acquire_compress_v1`, `BELIEFWEAVER` do **not exist** in this tree, and the six commit hashes in the brief (including `209bbc6c` and the five `click@`/`werkzeug@` heads) are **not valid git objects**. Nothing is claimed about them |

## 6. The next bottleneck (one)

**Composition: the loop cannot yet invent a missing action.** The compound
goal above is verifiable and unreachable because no offered action performs
`tar` *and* `gzip`. The next single step is typed composition of the operators
already in the store — two proven contracts (`gzip`, `tar`) composed into the
third, with the chain oracle deciding whether the composition is right. That is
the brief's "algebraic skill composition", now demanded by a measurement rather
than by a hunch.

**And the oracle still covers one shape of goal.** "Produce this artifact from
that source" is verified; a GUI state, a database row, a sent service, an edited
document are not — and OSWorld-Science's 60.6% "no graded artifact" figure says the same gap
exists everywhere. The next single step is to **derive the effect oracle from the
environment itself for other shapes** (for a GUI: the accessibility tree's own
action-and-readback; for a document: the application's own reopen-and-compare),
so that "the goal is an effect" is a law of the system rather than a rule about
gzip. That, and only that, is what turns this from one honest capability into a
general one.

Second, smaller, and already designed: the boundary is rung 2. gVisor or a
microVM turns "one kernel bug from escape" into a real hardware boundary, and the
interface here (`run`/`probe`) does not change to get it.
