# Exact stated geometry, and the score frames no hand can reach

Receipt: `canonical/verification/EXACT_STATED_GEOMETRY_20261117_V1.json` (schema
`BRAIN_EXACT_STATED_GEOMETRY_MEASURE_V1`). Run 3 is the adjudicating run; runs 1 and 2 are
preserved beside it with their kills, under the amendment recorded in the receipt.

## What was asked

Three pages failed with `OUT_SCORE_FRAME_NOT_STATED`: a manual, visually correct press scores
0.9427 (circle-center), a midpoint press cannot reach 1.0 (find-midpoint), and a right-angle
vertex scores 0.9995933 < 1.0-1e-9 (right-angle). The hand proposed the right PLACE; the
observation had already rounded it away (`Math.round` on `getBoundingClientRect`).

## What was built

1. **The bridge now carries the page's own numbers unrounded**: additive `box_f` (the
   `getBoundingClientRect` rectangle, no rounding) and `geom` (the element's own stated
   `cx`/`cy`/`r`, `x1`/`y1`, `x2`/`y2`, `width`/`height`), plus **`pointer`** -- where the
   hand last was, the first piece of proprioception the observation has ever had (the
   `MotorState` gap, agent-interface issue #27). `box` stays rounded: every previously
   measured hand depends on it, and the tests prove their action lists are unchanged.
2. **Exact operators** in `aimed_action_v1` (`EXACT_CENTER_OF`, `EXACT_MIDPOINT_OF_TWO_POINTS`,
   `EXACT_RIGHT_ANGLE_VERTEX`, plus measured `*_NUDGE` rules): the exact math in canvas
   coordinates, offered at each plausible page y-offset (the printed `QUERY_PADDING` is the
   one number the DOM does not state), at **integer** presses -- the DOM truncates fractional
   page coordinates on arrival -- and, once the page has shown its own blue mark, at the
   **measured** offset: `svgTop + pointer.y - markTop - r`.
3. **`ExactGeometryPrices`**: exact derivations free and first; previously derived places
   paid; with a mark on the page finalize is free and every press that would move the mark is
   paid, so the free run ends at the mark that exists instead of wandering an infinite
   lattice; without a mark finalize keeps its shipped price exactly.

## What was proven BEFORE the arms ran

- **circle-center and right-angle: FULL_REWARD is unreachable by any click, at every seed.**
  The optimum sits half-way between integer lattice points (the blue mark's radius differs
  from the printed padding by a half; the user's mark radius differs from the initial marks'
  by a half), and `MouseEvent.pageX/pageY` are `long` in the DOM: every press is truncated.
  The proof is arithmetic and arm-independent; the reachable ceiling it predicts (0.980889 at
  seed 1060 for circle-center, 0.999924 for right-angle) was then MEASURED to five decimals.
  The pages' own authors say the same from the other side: their env docstrings tell
  evaluators to binarize with `get_thresholded_reward`, not `get_binary_reward`.
- **find-midpoint is parity-dependent**: at odd coordinate sums (seed 1060) the true
  midpoint is a half-pixel the actuator cannot press -- ceiling 0.983333, measured exactly;
  at even sums (seed 1062, chosen by the declared rule "lowest seed >= 1061 with both sums
  even") the optimum IS an integer point.

## What the arms decided (run 3, budget 400, seed 1060, three arms, 17 pages)

- **`pass_primary` TRUE**: on both every-seed-proof pages G2's candidate set reaches the
  arithmetic ceiling within 1e-3 (circle-center 0.980889 = window; right-angle 0.999922 vs
  window 0.999924) and beats A's candidate set there (A reaches neither -- A offers no point
  presses at all).
- **`pass_full_reward` TRUE**: find-midpoint at seed 1062 passes in G2 in **8 actions** with
  rule `EXACT_MIDPOINT_OF_TWO_POINTS`, while A and D2 fail it -- full reward exactly where
  the actuator can express the optimum, and the decoy buys nothing.
- **`kill_fired` FALSE**: no verdict regression on the regression set, ceiling never lost to
  A, attribution intact. Spend drift, reported as declared: G2 is *faster* than A on
  read-table (270 -> 156) and email-inbox (174 -> 144), +3 on form-sequence-3.
- **Runs 1 and 2 fired the same kill (read-table: A passed, G2 failed)** and are preserved:
  both causes were PRICING only (free derived places stealing a working hand's search; then
  finalize priced away from its shipped price). No offer ever changed between runs. The
  amendment naming run 3 as adjudicating was recorded in the receipt BEFORE run 3 ran.
- Primary and secondary pages at seed 1060 all report `False` -- correctly: the predicate is
  unreachable there, and the ceiling rows are how the treatment's optimality is judged.

## What this does to the accounting

The 33-page unsolved frontier (pass-15) loses three entries to a NEW honest category:
- `find-midpoint` -- **solved where expressible** (even-parity seeds; full reward, exact
  rule, clean attribution).
- `circle-center`, `right-angle` -- **PREDICATE_UNREACHABLE**: the suite's FULL_REWARD
  predicate demands a point the actuator cannot express. This is the pass-15
  `OUT_SCORE_FRAME` diagnosis completed to its root: not a wrong-place guess and not even a
  rounded observation -- the third barrier (synthesis-verification asymmetry) living inside
  our own instrument, where the verifier asks for something no DOM click can deliver. The
  remedy belongs to the instrument (threshold, as the page authors themselves instruct), not
  to the hand, and changing the predicate is a decision for the goal hierarchy, not for a
  feature branch.
- `draw-circle`, `bisect-angle` (secondary): still need choreography, honestly unsolved.

The remaining unsolved count under the UNCHANGED predicate is 30, of which 2 are
predicate-unreachable and 28 are ordinary capability gaps.

## What this is, against the central claim

The merged verdict `ONE_LOOP_ONE_TAIL_VERDICT_20261117_V1` already answers the thesis
(FALSE as stated; one loop + one long tail; revolutionary in the loop, refuted in the
one-shot form). This pass adds one brick to the loop axis: the instrument now sees the
page's own numbers, knows where its own hand is, and -- when the page's frame is honest --
lands the hand on the exact point in 8 actions; and when the page's frame is NOT honest, the
instrument PROVES it is unreachable instead of burning four hundred actions pretending to
try. That is what "the smartest actions, experience once, learn permanently" has to mean in
practice: never confuse a wall for a search.
