# The perceptual-property class: three pages solved, two terminals accounted

Receipts: `canonical/verification/A_PERCEPTUAL_PROPERTY_FIVE_PAGES_20261117_V1.json`
(account), `canonical/verification/PERCEPTUAL_PROPERTY_CLASS_RECEIPT_20261117_V1.json`
(consolidated arms), measure `canonical/verification/PERCEPTUAL_PROPERTY_CLASS_MEASURE_20261117_V1.jsonl`
(budget 900, seed 1060, all three arms, adjudicating run).

## What was asked

Rank-3 of the ranked plan: the `A_PERCEPTUAL_PROPERTY` coverage class -- five pages that
failed the aim operator on perception-shaped wording. Complete the class: every page either
solved with a measured arm differential, or given a terminal, evidenced account.

## What was built

1. **`CLICK_INSTRUCTED_SHADE`**: the shade instruction names a swatch position
   ("2nd swatch on the top row"); the offered rows are the page's own swatch boxes and the
   shade box, ranked by box centre, offered at the row's centre y -- the whole row is a
   button, so the exact swatch is free. `GRAB_FOR_BOX_PARTITION` prices the re-grab once a
   box is in hand (`placed()` skips the grab), which cut the drag plan from 40 to 30 acts.
2. **`DOUBLE_AT_THE_NAMED_RUN` + `DRAG_OVER_THE_NAMED_RUN` + `CLEAR_A_WRONG_SELECTION`** for
   the text-editor: a Quill field is not a form input (`can_type` is false), so the only way
   to hand the page a selection is a pointer gesture inside the editor. Chrome double-click
   selects a word but never its trailing period, and Quill will not style a period-only
   selection -- so the period must be inside the SAME selection: a horizontal drag across the
   named run. A drag does not take while another selection shows; a press on the page's own
   blank collapses it, and the next look starts clean. Selection-gated style: the underlining
   only fires when the editor already shows exactly the named run, so a wrong gesture cannot
   spend the button. The bridge gained `doubleat@` and `dragat@x1,y1,x2,y2` (dispatch only;
   the page and the suite predicate are untouched).
3. **Prices**: `AimedPrices._partition_release` now prices the non-aimed release form
   `drop@`/`dropat@` on partition pages, so an aimed arm cannot win by falling back to the
   shipped drop while the hand still holds the shape.

## What was proven BEFORE the arms ran

- **hover-shape is predicate-unreachable at every seed** (3rd such page after circle-center
  and right-angle): the page pays `endEpisode(0,false)` only from `core.startStep`, nothing
  ever calls `done()`, and `core/core.js` turns any wait into `endEpisode(-1,false)` at the
  time limit. Observed: 0 success events across every run; A and D end
  `ENVIRONMENT_NOT_REPEATABLE` (clock) and G opens the budget. There is no act to aim.
- **click-checkboxes-soft refuses with measurements**: reward is `r/elems` at
  `FULL_REWARD=1.0`, so every box must be right. The page's 34 groups are hand-rolled
  thesaurus clusters; two free lexical sources were measured against all 492 within-group
  pairs -- WordNet-3 co-synset 158/492 (0.321, 2 cross-group false pairs), Roget section
  membership 312/492 (0.634, **2644** cross-group false pairs) -- and BOTH miss the
  seed-1060 instance's required pair `unhappy~sad`. The module's declared refusal ("needs a
  model of meaning, not an algebra over structure") now carries measurements instead of a
  prior. No partial-tick strategy reaches `r = elems`.

## What the arms measured (budget 900, seed 1060)

| page | A_shipped_hand | G_aimed_hand | D_decoy_aimed |
|---|---|---|---|
| click-shades | fail 900a | **PASS 775a [CLICK_INSTRUCTED_SHADE]** | fail 900a |
| drag-shapes-2 | fail 900a | **PASS 30a [GRAB_FOR_BOX_PARTITION]** | fail 900a |
| text-editor | fail 900a | **PASS 49a [DOUBLE_AT_THE_NAMED_RUN]** | fail 105a |
| hover-shape | fail 92a (clock) | fail 415a (page cannot end) | fail 122a (clock) |
| click-checkboxes-soft | fail 900a | fail 900a (refused, measured) | fail 900a |

G passes 3/5, A 0/5, D 0/5 -- gain over BOTH control arms on all three solved pages, every
pass `verified_on_fresh_page`. Unsolved frontier 30 -> 28 with both terminals accounted.

## Regressions

`REGRESSION_TASKS` at budget 400, all three arms: 11/12 pass every arm; `simple-arithmetic`
fails all arms at 400 exactly as in the pass-16 baseline. Tests: the three existing files
plus the new operator pins.

## What is NOT claimed

No benchmark credit, no capability-family credit, no weight change, no predicate change,
no external model called. hover-shape and click-checkboxes-soft are NOT claimed as solved;
they are claimed as accounted. The verdict receipt
`ONE_LOOP_ONE_TAIL_VERDICT_20261117_V1` is untouched.
