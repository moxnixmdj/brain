# Aimed actions over the unsolved set (2026-11-16)

**Claim: capability on the classes the instructions and their pages show — not transfer.**
24 derivation operators, written from the taxonomy class descriptions and the in-receipt
utterances, offered alongside the shipped hand in arm **G**, measured on **exactly the 46
unsolved tasks** (`taxonomy.rows`), with arm **A** (shipped hand alone) and arm **D**
(same-count, same-shape randomised decoys) as controls.

## Result (budget 400 acts, seed 1060, one primary run per arm)

| arm | passes |
|-----|--------|
| A shipped hand | **0 / 46** |
| G aimed hand  | **13 / 46** |
| D decoy aimed | **0 / 46** |

| task | acts | rule |
|------|-----:|------|
| choose-date | 72 | DATE_CELL |
| choose-date-nodelay | 72 | DATE_CELL |
| click-menu | 211 | PATH_SEGMENT |
| copy-paste | 3 | COPY_PASTE_VALUE |
| copy-paste-2 | 3 | COPY_PASTE_VALUE |
| draw-line | 9 | GRAB_THE_POINT_TO_DRAW_THROUGH |
| find-word | 3 | NTH_WORD_TYPE |
| odd-or-even | 18 | ODD_EVEN_BY_PARITY |
| read-table-2 | 3 | LABELLED_PAIR_TRANSFER |
| social-media | 3 | REVEAL_CONTROL |
| use-colorwheel | 5 | NAMED_COLOUR_HEX |
| use-colorwheel-2 | 5 | NAMED_COLOUR_HEX |
| visual-addition | 4 | COUNT_THEN_TYPE |

The treatment wins only through its derivations: every win's plan is priced from the aimed
list (finalize `(0,1)`, other aimed `(0,0)`), and the decoy arm — the same number of offers
at the same prices, pointing at random witnesses — passes 0.

## The 33 misses, classified only as far as the evidence reaches

- **OUT_SCORE_FRAME_NOT_STATED (3)** — manual, correct-geometry chains score below the
  full threshold under integer boxes: right-angle `0.9995933`, circle-center `0.942667`,
  find-midpoint (same `(r−d)/r` frame). Precision the observation cannot carry.
- **OUT_NO_STATELESS_PATH (8)** — hot-cold (non-repeatable at 141 acts; a <5px hit on a
  random point is a >400-point grid; pointer position not in the observation), chase-circle
  (sustained mouse), moving-items (verdict arrives only when the page clock fires; the
  exploration lift hides the clock and running it makes states non-repeatable),
  sign-agreement (scroll gate; no scroll primitive), simon-says (non-repeatable timed
  flashes), book-flight ×2 (non-repeatable under the state key at 22 acts), use-slider ×2
  (widget state not stated in any attribute).
- **OPEN_BUDGET_NOT_FOUND (22)** — no goal observed in 400 acts. Where emission was
  verified at reset the receipt says so (social-media-all 7 replies + finalize, text-editor
  select+style+finalize, terminal `ls` with no Enter primitive, drag-shapes-2, email,
  multi-orderings); where nothing emits it says that too (order-food needs a category word
  the rows do not state; multi-layouts needs field-value semantics no lexical tie states).

## Honesty

- **Sources opened** (page source, declared): circle-center, use-slider, right-angle,
  hot-cold, moving-items, chase-circle, use-colorwheel, use-colorwheel-2, and
  `common/ui_utils.js` (the colour name→hex map). Everything else was measured through
  observations and element dumps only. Sources are opened for classes the claim rests on;
  nothing page-source-specific (widget parameters) is encoded in an operator.
- The bridge passes small inline-styled swatches inside the instruction region through as
  **inert** elements (a person can see them); instruction echoes are never actions.
- Partial episode ends are real: a wrong early submit ends the run and the search pays a
  reset.
- Tests: 17/17 aimed; 57 targeted (aimed + exploration); 165 passed + 27 skipped
  (generalisation suite incl. `POINT_AT`); unified model recompiled — 60 passed +
  919 subtests.

Receipt data: `AIMED_ACTIONS_OVER_THE_UNSOLVED_SET_20261116_V1.json`.
