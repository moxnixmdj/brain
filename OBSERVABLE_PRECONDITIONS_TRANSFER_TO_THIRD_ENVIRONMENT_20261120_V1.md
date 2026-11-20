# Observable preconditions transfer to a third environment — 2026-11-20

Authority: `NONE__PRODUCER_RUN_SANDBOX`. This is a zero-model, real-process
measurement of an external-store capability. It is not a benchmark score, GUI
success, independent verification, capability credit, or §6 completion.

## 0. Requirements confirmed

Full v3 prompt read as new. Bound requirements: own model/weights/architecture/
agent; zero runtime model calls; parameters only computed mechanisms; instant
knowledge in an external inspectable/editable/deletable store with single-
experience writes that cannot invent conditions; exhaustive project-then-web
research; first-principles bottleneck; ultimate minimal plan with rejected
ideas and a design kill; build; hardest honest tests; continuous §5 until §6;
one branch/one merge; never ask and never claim §6 early. §2 remains resolved:
parameter world-fact lookup and runtime model dependency are forbidden; an
external store plus computed mechanisms is allowed.

## 1. Research findings

### Project

* `THE_PRECONDITION_IS_NOT_IN_THE_TRACE_20261126_V1.json` measured 10 real
  actions: retention 30/30, successes identified 0/10 conditions, contrasts
  reached 0.9464 only where the deciding fact was observable, and 0.5833 on
  `tar_extract`, `gzip_decompress`, `patch_apply`, whose deciding facts were
  outside the sensor vocabulary.
* `WHERE_THE_WALL_ACTUALLY_IS_20261116_V1.json` classified 3/37 worlds as
  "page behaves differently on what looks the same" and named the repair:
  **add the missing observable** or reduce the page to states the look can
  distinguish. 32 other worlds were search-budget limited, not storage limited.
* `CONDITION_TRANSFER_CROSSES_ENVIRONMENTS_20261120_V1.md` proved a contrast-
  bought condition transfers between two real repositories with zero target
  learning, but explicitly left unobservable conditions and exact identification
  open.
* `applicability_v1`, `contrast_selection_v1`, `settlement_v1` and
  `instant_condition_store_v1` already provide the learner, selector, version
  space and external store. No new learner was justified.
* Non-obvious routes checked and not reused for this change: `computer_env_v1`
  (discovers actions, not affordance facts), `jit_knowledge_v1` (document
  retrieval), `skill_precondition_presence_v1` / `what_the_condition_wants_v1`
  (wording), workflow/dataflow and OSWorld ledger stacks (completion proof).

### Web / frontier (inputs only)

* DynAfford/ADAPT [1] treats latent, changing object affordances as implicit
  preconditions that must be detected before action, and reports failures from
  latent-state mis-detection and cascading precondition violations.
* A 2026 agent-tooling analysis [2] reports that deterministic read-only
  pre-execution gates recover a silent wrong-state failure mode; domain-specific
  assertions and production observability beat leaderboard rankings.
* The ACL ADAPT paper [3] stresses seen/unseen environment transfer, but uses a
  fine-tuned VLM. We take only the structural point — explicit affordance
  checks — and use computed read-only programs, not a model.

[1] https://arxiv.org/html/2604.14902
[2] https://www.splunk.com/en_us/blog/artificial-intelligence/agent-evaluation-tool-calling-planning.html
[3] https://aclanthology.org/2026.acl-long.1109/

## 2. §3 verdict

* **True:** retention is solved; transfer of an observable condition across
  repositories with zero target learning was already measured.
* **Newly verified:** the three previously unobservable actions become
  learnable when cheap read-only validity facts are added to the sensor
  vocabulary; their conditions transfer to a third real repository with 48/48
  correct decisions and 0 false applies.
* **False:** one experience identifies a condition. The store still writes an
  explicit `OPEN` condition from one success; contrasts are required.
* **Unproven:** exact identification, GUI/browser, OSWorld 2.1, SWE-bench Pro,
  Terminal-Bench, arbitrary environment classes, sentience.
* **Missing:** independent verification, hidden evaluator, own-agent end-to-end
  benchmark, and dynamic affordance shifts inside one session.

Why not give a model the advanced actions once and let it learn them? A trace
names the instance and the program; it cannot name the set of states where the
program applies. Putting that set in weights would make parameters a world-fact
warehouse and would remove the edit/delete path. Here the set stays in JSON,
the chooser is a subset test, and the only new mechanism is a read-only probe.

What still stops us: PROVISIONAL rules are not proven unique, the probe
vocabulary is domain-specific, and no benchmark harness runs our whole agent.

## 3. Ultimate minimal plan and design kill

Bottleneck: unobservable preconditions, not memory or search.

Plan: (1) add three read-only probes that are distinct from their actions —
`tar -tzf` lists, `gzip -t` tests a stream, `git apply --check` checks a patch;
(2) digest-check that each probe leaves the state byte-identical before its
fact is admitted; (3) augment the existing state vocabulary with the probe
facts; (4) let the unchanged learner/selector buy conditions from contrasts in
one repository and write them to the same external store; (5) reload the store
and score in a third repository with zero target learning.

Killed: a new learner (existing version space works), a model/VLM affordance
judge (forbidden), mutating validity checks (would destroy the state being
observed), storing raw traces in the target (instance, not condition),
retraining or adding parameters (forbidden and unnecessary), accepting a probe
fact without a read-only digest check (would let observation change the truth).

Smartest-approach check: the only new runtime surface is three read-only
program invocations and a pure subset chooser already built. The cheapest fix
for an unobservable condition is to make it observable, not to invent a more
powerful learner.

## 4. Build and hard test

New files: `canonical/runtime/observable_probe_v1.py`,
`canonical/tools/observable_condition_transfer_v1.py`,
`canonical/tests/test_observable_probe_v1.py`, and the measurement receipt.
The existing external store `INSTANT_CONDITION_STORE_V1.json` was extended from
6 to 9 entries without retraining.

Hard test: source = real `pallets/click` clone, target = different third real
repository `psf/requests`, different seeds (23 and 31), 16 real states per
action, real `tar`/`gzip`/`git`/`patch` processes and each action's own exit
status as oracle. Source learning used 13 contrast executions; target learning
used 0.

| quantity | result |
|---|---|
| latent actions taught | 3 (`tar_extract`, `gzip_decompress`, `patch_apply`) |
| source held-out accuracy, each latent action | 1.0 |
| source exact identifications | 0 (all PROVISIONAL) |
| target latent-action decisions | 48/48 correct, 0 false applies |
| target previously-stored actions | 48/48 correct, entries unchanged |
| target unseen action | 16/16 OPEN, 0 false applies |
| target evaluation oracle calls | 112 |
| probe/vs-oracle agreement on latent actions | 1.0 for each probe |
| store digest before → after | `fc8cb293…` → `ee71dd15…` |
| model calls / parameters / spend | 0 / 0 / $0 |

New deterministic suites: 8 passed (3 probe + 5 store). Declaration floor held
at 595. Repo guard: 17 rules, 0 violations.

## 5. Honest limits and next bottleneck

Unverified: exact identification, GUI/browser tasks, OSWorld 2.1, Terminal-
Bench, SWE-bench Pro, dynamic affordance changes, fourth environment, hidden
evaluator, independent verification, benchmark score, and §6 completion. The
unseen action in the target had no APPLIES states (`git_rm_cached_tracked`
needs a `README.rst` that this repository does not have), so its 16/16 OPEN
refusals were not tested against a positive case; the previous round tested
that case with genuine positives. No pinned kernel was edited.

Next §5 bottleneck: make PROVISIONAL rules report their survivor count and
accept a targeted refutation when a new environment disagrees, then test that
repair on a fourth repository and on affordances that change within one run.
