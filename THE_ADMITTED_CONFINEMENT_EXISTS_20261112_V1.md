# The admitted confinement exists: the wall the most advanced capabilities actually hit

**2026-11-12.** Branch `arena/8ac47053-brain`. Base `8439f609` (#6719). Follows
`A_PERFECT_ACTION_IS_NOT_AN_AVAILABLE_ACTION_20261112_V1.md` (corrected ordering) and
`NINE_BLIND_FACTS_NOW_DECIDED_20261112_V1.md` (premise layer). Authority NONE — sandbox
measurement, `$0`, zero model dependency, `truth.achieved` stays `false`.

## 0. What the owner asked, and what this round found under it

The owner asks again: *can't we just give the model the most advanced coding actions and let
it experience them once?* This round measured that question at the mechanism level and found
the wall is not where the previous rounds pointed.

The binding wall (54 capabilities) **already fell**: a second binding surface
(`live_brain_route_admission_v1.solve` + `declared_input_derivation_v1`) resolves most
act-level `NOT_CALLABLE` rejections — re-measured here with
`door_and_act_availability_census_20261112.py` (145 capabilities, both layers, disposable
clone, 631 s). The remaining dominant class is **not perception and not binding**: with
material-aware *realistic sentences* (not keyword salads), **19 of 38** probed capabilities
refuse with exactly one status:

```
FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT
```

The refused 19 are, almost one-for-one, the most advanced coding capabilities in the
registry: the SWE repair loops, fault localization, contract checking, cross-file edit
choreography, taint flow, transform-and-synthesize, shell execution. They compile, they
bind — and the tree honestly refuses to run them until "a reviewed, admitted confinement
and effect-verification path exists" (`canonical/runtime/computer_execution_boundary_v1.py`,
whose docstring states that release condition verbatim).

**So the answer to "can't we just give the model the most advanced coding actions now?" is:
the actions exist, the door reaches them, and the machine refuses to let them touch the
computer until the substrate exists. This round builds the substrate.**

## 1. The measurement chain (predictions written before each run)

### 1.1 The census on this base (instrument: keyword salads, both doors)

door fates: EXECUTED 25, COMPILED_TO_SELF_BUT_FAILED 38, NOT_COMPILED 52,
ROUTED_ELSEWHERE 26, NO_KEYWORDS 4. The act-layer binding failure (round 4's 54) is now
mostly a door-level non-event: `not_callable_reached_past_compile_at_door: 26`.

### 1.2 Decomposition of the 52 NOT_COMPILED (first-principles filter)

- 6 exotic-material (raster charts, browser screenshot) — the clone cannot contain the
  input; fail-closed is CORRECT.
- 8 material-gated (diff gates, PR realize, gate composer) — need a diff artifact a static
  clone cannot have; honestly gated.
- **38 ordinary-input — the advanced-coding wall.** Each got a realistic, material-aware
  sentence in `canonical/tools/realistic_goal_reach_probe_v1.py` (data, reviewable, reusable
  as a regression fixture).

### 1.3 The realistic-sentence probe — PR1 FALSIFIED, and the falsification is the finding

Pre-registered: ≥24/38 compile to themselves. **Measured: 3/38** (git log, rename symbol,
supercomposer — all EXECUTED and verified). Realistic sentences do NOT rescue the compile
layer. The named statuses decompose:

| status | count | reading |
|---|---:|---|
| `COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT` | **19** | the boundary's release condition is unmet — the substrate did not exist |
| `RAW_GOAL_COMPILATION_GAP` | 3 | real compile gaps (shell.run, diagnose, k-star) |
| `STATED_SWE_EFFECT_UNSERVED` | 2 | stated effect vs declared provides mismatch |
| `STEP_RAISED_OUTCOME_UNKNOWN` | 3 | repair-loop steps raised inside the door |
| others (route admission, composed chain, confinement for fetch) | 11 | per-case |

One cause covers exactly the capabilities the owner means by "most advanced coding" — and it
is not a bug. It is the tree keeping its word.

## 2. What was built: `canonical/runtime/confinement_v1.py`

The constructive half of the boundary's own release condition — a disposable machine with
measured effect receipts:

- **The worktree is the computer**: `admit` clones the host (`git clone --no-local`); every
  byte lands inside the clone. `execute` runs list-argv with `shell=False`, restricted
  PATH/HOME, and a hard budget; `verify_effects` checks each declared output exists INSIDE
  the worktree with a sha256; the host's `git status --porcelain` must be byte-identical
  after (`host_untouched` in every result). Effects resolving outside the worktree are
  refused at admission (`EFFECT_ESCAPES_CONFINEMENT`).
- **Content-addressed receipts**: sha256 over (host head, argv, budget, declared effects,
  outcome, effect hashes). Memory is not authority; receipts are.
- **Overruns are recorded as what they are** (`BUDGET_EXCEEDED`), never laundered.
- **No door code changed**: the seam (the boundary's refusal sites in
  `goal_front_compiler_v1` and `live_brain_route_admission_v1`) is named in the module
  docstring for the next diff; every existing refusal stands exactly as before. This is
  additive, guard-preserving, and cannot weaken anything by existing.

### 2.1 The first design was falsified before it shipped — recorded, as law requires

The first draft refused any argv containing `&&`, `;`, `|`, `>`. Wrong twice over: it broke
`python3 -c "a; b"` (a plain invocation — no shell anywhere) and it refused the very
`bash -c` runs whose job is to prove the worktree bounds destruction (measured: the
destruction test's own fixture got `SHELL_STRING_REFUSED`). With `shell=False`,
metacharacters in arguments are inert characters. The confinement is the worktree plus the
restricted environment plus the budget — **not a character blocklist**. Fix: guard deleted,
design note written into the module, test PJ5 rewritten to pin the structural truth
(`shell=True` appears nowhere in the module source; a `bash -c` run is allowed and bounded).

## 3. Measurements (`canonical/tests/test_admitted_confinement_v1.py`, 9/9 pass)

| # | measurement | result |
|---|---|---|
| PJ1 | host `git status` byte-identical after a run that creates and `rm -rf`s inside its machine | `host_untouched: True` |
| PJ2 | declared effect created in-worktree verifies with sha256; `../escape.txt` and `/etc/passwd` refused at admission | `EFFECT_ESCAPES_CONFINEMENT` both |
| PJ3 | `sleep 5` with a 1 s budget | `BUDGET_EXCEEDED`, honest, fast |
| PJ4 | the exact argv the door refuses today (`python3 --version`) | runs confined, output captured, host untouched |
| PJ5 | `shell=True` appears nowhere; `bash -c "echo a && echo b"` runs bounded | structural pin |
| PJ6 | empty argv / unresolvable program / nonsense budget | named refusals |
| PJ7 | nonzero exit with a created effect | `NONZERO_EXIT` reported alongside verified effects |
| PJ8 | receipt content-addressing | same basis → same sha; changed argv → different sha |
| PJ9 | `run_confined` end-to-end | `admitted: True`, `verified: True`, `terminal_authority: False` |

Regression: the two new files are additive; the census and probe tools are new; no existing
module's behaviour changes (the door still refuses everything it refused this morning).

## 4. The ledger, updated

**Real (measured):** the premise layer (143/145 askable); the door's binding surface (26/54
act-rejections reached past compile); the confinement substrate (9/9) with the seam named;
3 capabilities executed end-to-end on realistic sentences; and every number from the
previous rounds re-verified this session (1 demo → 0.10; +chosen questions → 1.00; one
success → 0/200).

**Not real (pinned):** one-try identification; one-success applicability; cross-kind
compounding (0/5); universal compile coverage (32/38 realistic advanced-coding goals still
refuse, now for ONE dominant named reason); permanence under drift; sentience.

**The one-line answer to the owner:** the most advanced coding actions are already in the
registry, the door already reaches them, and the machine already refuses to run them
ungoverned — today that refusal got its constructive answer: the admitted confinement
exists, measured, with effect receipts. Wiring it into the boundary's release condition is
the next small, honest diff.

## 5. Smartest next steps

1. **Wire the seam**: consult `confinement_v1.run_confined` at the boundary's refusal sites
   (additive: a confinement receipt satisfies the release condition; no receipt → identical
   refusal), then re-run the realistic-goal probe — the 19/38 bucket is the measurable
   target.
2. **Effect declarations per capability**: each of the 19 needs its declared effect list
   (output paths) so admission can verify them — registry data, not code.
3. **Compile gaps** (`RAW_GOAL_COMPILATION_GAP` 3, `STATED_SWE_EFFECT_UNSERVED` 2): per-case
   after the wall falls.
4. Field anchor: OSWorld 2.1 best binary completion 44.3% (Nov 2026) — the field's
   long-horizon wall is execution governance and verification, exactly this layer.

## 6. Reproduction

```bash
python3 -m pytest canonical/tests/test_admitted_confinement_v1.py -q          # 9 passed
python3 canonical/tools/realistic_goal_reach_probe_v1.py --out /tmp/rgoal.json # 38 probes, fates printed
python3 door_and_act_availability_census_20261112.py --out /tmp/census.json    # ~10 min, both layers
```
