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

## 6. The next bottleneck (one)

**The oracle covers one shape of goal.** "Produce this artifact from that source"
is verified; a GUI state, a database row, a sent service, an edited document are
not — and OSWorld-Science's 60.6% "no graded artifact" figure says the same gap
exists everywhere. The next single step is to **derive the effect oracle from the
environment itself for other shapes** (for a GUI: the accessibility tree's own
action-and-readback; for a document: the application's own reopen-and-compare),
so that "the goal is an effect" is a law of the system rather than a rule about
gzip. That, and only that, is what turns this from one honest capability into a
general one.

Second, smaller, and already designed: the boundary is rung 2. gVisor or a
microVM turns "one kernel bug from escape" into a real hardware boundary, and the
interface here (`run`/`probe`) does not change to get it.
