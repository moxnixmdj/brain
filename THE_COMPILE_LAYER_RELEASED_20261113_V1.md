# The compile layer released for declared capabilities: effect-directed routing, measured

**2026-11-13.** Branch `arena/360b15d5-brain`. Base `d314e2fe`. Follows PR #6733 (the
confinement substrate) and PR #6760 (the confined dispatch seam + the corrected diagnosis:
32/38 realistic sentences die at the COMPILE layer, before any dispatch). Authority NONE —
sandbox measurement, $0, zero model dependency, `truth.achieved` stays `false`.

## 0. The owner's question, and what this round does about it

The owner asks: give the model one try in new environments and it learns permanently —
don't we already have the perfect solution, and isn't the missing piece weight-space
learning? This round does the measured thing the last round's diagnosis pointed at
(release the compile wall), and answers the theory question with freshly fetched 2026
research (§4). The theory answer first, in one line: **the field's own papers say one try
teaches nothing permanently — what persists is distillation of VERIFIED experience, and
the verification half is exactly what this tree now has.**

## 1. The mechanism: effect-directed compile routing

`canonical/runtime/effect_directed_compile_v1.py` releases the layer ABOVE the R29 seam:
sentence → compiled plan, with **no sentence table and no benchmark-specific routing**.
Its data is the same reviewed data the seam already gates on:

1. `CONFINED_EFFECT_DECLARATIONS_V1.json` — which capabilities may run confined (11 rows
   from R29 + `code.index.tree_sitter.incremental.v1`, added this round after review: it is
   a `VERIFIED_BOUND_CAPABILITY` with an independent test).
2. The verified bound-capability registry — each row's own `keywords`/`provides`
   (the capability's declared interface) and `action_template` (its argument names).

A sentence routes only if EVERY gate holds:

- it names an output artifact whose format the verifier table can actually check — the
  SAME evidence bar the carrier gate enforces;
- **IDF-weighted lexical agreement**: the sum of `1/df` over the stemmed content tokens
  shared by the sentence and the candidate's declared `keywords`/`provides` must reach
  0.8 (df computed over the declared candidate pool; tokens from mentioned repo paths are
  excluded — paths bind arguments, they do not vote on identity). Two mid-frequency
  tokens, or one rare and one common, open the gate; word soup does not;
- **every non-knob argument binds from the sentence** (artifact, repository anchor,
  mentioned paths) — an argument that cannot bind honestly disqualifies the candidate;
  numeric knobs are omitted (adapters read them with defaults); an `operation`-shaped
  argument is never guessed.

Execution goes through the R29 confined seam: the adapter runs on the disposable clone,
the declared effect verifies inside the worktree, the host tracked state is byte-identical,
and the door's own expectation ruler judges the result. The FIRST verified candidate wins;
every attempt is recorded; a run that fails verification is a fail-closed result WITH its
receipt and — new this round — with the adapter's own named reason
(`CONFINED_ADAPTER_RAISED:<type>:<error>` in `confined_dispatch_v1`), because silence
about *why* is how a compile gap got misread as a sandbox gap last round.

The door insertion is 9 lines in `_solve_public`, between the honest-contract-refusal
check and the carrier gate: the usual path keeps absolute priority; the route fires only
when the usual path did not answer; when the route does not bind, the carrier refusal
stands exactly as before.

## 2. PR2 — pre-registered BEFORE the confirmatory probe run

Instrument: `canonical/tools/realistic_goal_reach_probe_v1.py` (the 38 realistic
sentences), run on the committed tree with the router live. Development e2e (10 routed
sentences through `door.solve`) measured before this registration: **5 verified confined
passes** (ast symbol index, test selection, taint flow, crosshair contract check, crosshair
concrete-execution oracle) and **5 honest fail-closed runs with receipts** (tree-sitter
index: the adapter's own `SOURCE_FILE_LIMIT_EXCEEDED` on this 5,604-file repository;
merge-conflict resolution, cross-file choreography, dynamic fault localization,
interprocedural provenance: the material a clean clone lacks — no conflict markers, no
defect spec, no failing tests).

**PR2a**: at least 8 of the 38 sentences reach EXECUTED (pass=True) — the 3 that already
executed before this round plus at least 5 of the newly routed rows.
**PR2b**: every routed-but-unverified row returns a NAMED fail-closed status with a
confinement receipt — never a fabricated pass, never an unnamed shrug.
**PR2c**: the pinned refusals survive unchanged: `compress notes.txt into notes.txt.gz`
keeps its refusal; the guard suite stays at its clean-tree baseline (one pre-existing
controller subtest failure, reproduced on the unmodified tree this round and not chased).
**PR2d**: the remaining not-routed sentences stay refused with named statuses.

Falsification: EXECUTED < 8, or any routed row unnamed, or any pinned refusal moved.

## 3. Measured (filled after the probe run)

See §6 below — filled in after the run; the pre-registration above was committed first.

## 4. The theory answer: token-space, weight-space, and what is actually real

Freshly fetched and read this round (the owner's four cited sources are all real):

- **Experience Distillation** (arXiv 2607.21051, Jul 23 2026): converts transient
  in-context gains into permanent weight updates via model-free one-step branch
  distillation. Retains **64.8–93.4% of ICL gains**; direct SFT on the same experience
  recovers only **3.8%**; matches classical RL with ≥**9.6× fewer** environment samples;
  continual cycles accumulate (7.1 → 47.0 over five cycles, ~20 samples per task).
- **ASCENT** (arXiv 2610.05303, Oct 4 2026): Online Agentic Test-Time Training — trains
  the LLM's weights on its own deployment trajectories via self-distillation of VERIFIED
  experience into LoRA fast weights (+22 points exact success on ALFWorld/WebShop;
  transfers to held-out scenes). Its central negative result: **"directly imitating or
  reinforcing the generated tokens of this single attempt destabilizes the policy"** —
  naive one-try learning from raw experience FAILS; only verifier-accepted experience is
  distilled, and failed episodes are skipped.
- **Memory Models** (Letta, Jun 25 2026) + MemoPilot (arXiv 2606.08656): token-space
  memory trained with memory-native RL; expertise as token-space representations that
  transfer across model generations.

What this means for the owner's claims, scored honestly:

- **"One try → permanent learning"**: WRONG as stated — ASCENT's own negative result plus
  this tree's pins (1 demo → 0.10 applicability; one success → 0/200 on unseen; cross-kind
  0/5). RIGHT in a narrower form: one VERIFIED success, distilled, persists — and the
  distillation needs a trainer, a verifier, and more than one sample to be stable.
- **"We already solved those perfectly"**: the execution-governance half is now genuinely
  solved end-to-end (substrate → seam → compile routing → receipts, this round); the
  compile layer serves 10 of 38 realistic sentences, weight-space learning does not exist
  in this tree (zero model dependency is a deliberate property), and the 4 routed rows this
  repo's material cannot serve fail honestly. "Perfectly" is not measured anywhere.
- **"Sentient creature"**: unchanged — no consciousness indicator is measurable here;
  `truth.achieved` stays `false`.
- **The honest boundary of this sandbox**: no weights exist here to update ($0, no model).
  What THIS tree can contribute to the weight-space pipeline is the half both papers
  require and most harnesses lack: **verified, receipted experience** — confinement
  receipts with sha256-verified effects are exactly the "verification result" ASCENT
  conditions on. That is real, shipped, and reusable by any future trainer.

## 5. What is real and what is not, after this round

**Real (measured):** the full chain sentence → reviewed declaration → sentence-bound
arguments → confined execution on the disposable clone → sha256-verified effect →
expectation-judged receipt, through the public door, for 5 realistic advanced-coding
sentences (8/8 new tests; seam suite 5/5; guards at clean-tree baseline). The IDF gate's
precision: 0 phantoms on the 38-sentence corpus, compress/garbage/unserved refused.

**Not real (pinned):** one-try identification (0.10); one-success applicability (0/200);
cross-kind compounding (0/5); compile-layer coverage beyond the declared 10 (28/38 still
refuse — repair family, network fetchers, diff-gated rows, unbindable operations);
permanence under drift; weight updates; sentience.

## 6. Probe scoreboard (measured after PR2 was committed)

PENDING — filled in by the probe run on the committed tree.

## 7. Reproduction

```bash
pip3 install --break-system-packages pytest opencv-python-headless sympy pydantic langdetect python-docx tree-sitter tree-sitter-languages crosshair-tool
python3 -m pytest canonical/tests/test_effect_directed_compile_v1.py canonical/tests/test_confined_dispatch_v1.py -q
python3 canonical/tools/realistic_goal_reach_probe_v1.py --out /tmp/rgoal_r30.json
python3 canonical/runtime/effect_directed_compile_v1.py "<any sentence>"
```
