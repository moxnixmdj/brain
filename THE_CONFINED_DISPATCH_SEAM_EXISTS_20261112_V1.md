# The confined dispatch seam exists; the corrected diagnosis moves the wall to the compile layer

**2026-11-12.** Branch `arena/9c35dc77-brain`. Base `4325dbfa` (#6749). Follows
`THE_ADMITTED_CONFINEMENT_EXISTS_20261112_V1.md` (the substrate, PR #6733). Authority
NONE — sandbox measurement, `$0`, zero model dependency, `truth.achieved` stays `false`.

## 0. The owner's question, unchanged, and this round's two findings

The owner asks again whether one try per environment teaches everything permanently. The
quantifier pins stand (re-verified this session: 1 demo → 0.10; +chosen questions → 1.00;
one success → 0/200). This round wired the confinement substrate into the door and, in
doing so, **corrected the previous round's diagnosis of where the wall actually is**. Both
findings are measured, and the second one corrects me.

## 1. Finding 1: the seam is wired and measured

`canonical/runtime/confined_dispatch_v1.py` + `CONFINED_EFFECT_DECLARATIONS_V1.json`
(reviewed data: 11 capabilities, each declaring which bound argument is its verified
effect, e.g. `output_path`) + a 9-line seam in `run_adapter_locally`
(`live_brain_route_admission_v1`):

- A capability with a declaration runs its REAL adapter INSIDE the disposable clone
  (imported from the clone's own `canonical` package, `root` = the worktree), with the
  declared effects verified by sha256 inside the worktree, the host's
  `git status --porcelain` byte-identical after, and the SAME expectation check
  (`_check_expectation`) judging the result. The receipt (sha, host head, host_untouched,
  per-effect hashes) travels on the result.
- Fail-closed everywhere: no declaration → the refusal stands; effect unbound → refusal;
  effect bound to an absolute path into the host → refusal; confinement refuses the
  shape → refusal; adapter raises → fail-closed result with the receipt, never a crash,
  never a pass.

Measured (`canonical/tests/test_confined_dispatch_v1.py`, 5/5, plus 23/23 of the
confinement and guard suites): the end-to-end test runs `python.source.symbols.index.ast`
against THIS repository — the clone indexes the clone, `symbols_index.json` verifies
inside the worktree, the host never moves, `output_verified` passes the same ruler the
local path uses, and `dependency.executor = ADMITTED_CONFINEMENT_V1`.

## 2. Finding 2: the corrected diagnosis (the previous round's reading was imprecise)

The previous round read the probe's 19/38 `COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT`
bucket as per-capability boundary refusals waiting for the substrate. This round traced
the door with `sys.settrace` and found the truth:

- `boundary.refuses_execution` is **never consulted** for those goals (patched, zero
  True-returns). The status is emitted by `_serve_by_acting` — the door's
  **program-synthesis discovery fallback**: a goal that names a file output
  ("write ... to symbols_index.json") is read as a request for automatic file-creating
  discovery, which the tree refuses outright until an admitted path exists. The
  capability path (compile → bind → dispatch) never runs for them: their compile already
  failed, and the fallback then masked the compile failure with the boundary status.
- Direct evidence: `boundary.refuses_execution('python.source.symbols.index.ast', …)` is
  **False** (that adapter is not execution-classified at all), yet the door refuses the
  symbols-index sentence with the boundary status — via the fallback.

Re-measured with the seam live (`realistic_goal_reach_probe_v1.py` re-run on the committed
tree): door fates unchanged — 32 NOT_COMPILED / 3 EXECUTED / 3 ROUTED_ELSEWHERE; the
confinement-status bucket reads 21 this run (19 before — compile-layer run variance).
The seam is real and waiting; the compile layer never hands the declared capabilities to
it, because their sentences fail at the front compiler first.

**What this means for the owner's plan:** "give the model the smartest actions" is still
blocked one layer earlier than the last round claimed — not at execution governance
(that now exists, substrate + seam), but at **sentence → compiled plan**: the front
compiler does not yet produce plans for these 38 realistic sentences, and the discovery
fallback then reports a boundary refusal that hides the compilation gap. The honest chain
for the most advanced coding capabilities is now:

```
sentence ─✗→ compile ─→ bind ─✓→ confined dispatch (NEW, measured) ─→ verified receipt
```

## 3. What is real and what is not, after this round

**Real (measured):** the confinement substrate (PR #6733, 9/9); the confined dispatch
seam (5/5, end-to-end with a real adapter against the real host, byte-identical host);
the pinned door refusals untouched (guard suite 23/23, including the pinned
`compress notes.txt` sentence); the corrected decomposition above.

**Not real (pinned):** one-try identification (0.10); one-success applicability (0/200);
cross-kind compounding (0/5); **compile-layer coverage for realistic advanced-coding
sentences (32/38 still fail before any dispatch)**; permanence under drift; sentience.

**Also corrected:** my previous round's doc said the wall was "19/38 … refused for want
of the substrate". The substrate existed; the door never reached it for those goals. The
substrate is necessary (the seam needs it) but the compile layer is the binding
constraint at the door.

## 4. Smartest next steps (by the corrected ordering)

1. **Compile-layer routing for declared capabilities**: teach the front compiler to
   produce single-capability plans for the 38 realistic sentences (the corpus in
   `realistic_goal_reach_probe_v1.py` is the regression fixture). The seam fires
   automatically the moment a plan compiles — the scoreboard is the probe re-run.
2. **Decompose the discovery fallback**: `_serve_by_acting` should report the compile
   failure underneath it (a precise refusal), not the boundary status — otherwise every
   compile gap reads as "sandbox missing" and misdirects the plan (exactly what happened
   to me last round).
3. Then: effect declarations for the repair family (excluded this round — the boundary
   treats repair refusal conditionally and its flow deserves its own diff), and the
   network-gated three (fetch, release-verify) behind an explicit network decision.

## 5. Reproduction

```bash
python3 -m pytest canonical/tests/test_confined_dispatch_v1.py -q                    # 5 passed
python3 -m pytest canonical/tests/test_computer_unconfined_route_guard_v1.py canonical/tests/test_admitted_confinement_v1.py -q  # 23 passed
python3 canonical/tools/realistic_goal_reach_probe_v1.py --out /tmp/rgoal.json       # door fates with the seam live
```
