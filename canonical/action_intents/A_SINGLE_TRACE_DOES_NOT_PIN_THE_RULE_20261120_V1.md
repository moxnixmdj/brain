# A single trace does not pin the rule

Three counters added to the demand instrument: the **live set** (how many candidates produce the demanded
value), the **contrast masks** (which passing rows each candidate preserves, counted at every depth), and the
**ambiguity of the gate** (how many distinct rules the corpus's own suite accepts at the same site).

30 real commits, 93.2 s, 0 parameters:

- 150,809 to 154,157 candidates offered per row;
- **zero** produce the demanded value on **13 of 15** in-class rows — the binding failure here is coverage,
  not over-permissiveness;
- on the one verifiable row, **2** do, and the suite accepts **both** (`'{name}'` and `{name!r}`), 47 tests green;
- one row runs the site **109 times** inside a single failing test, and that is repetition, not contrast.

**Law:** one trace teaches a tape; only a contrast teaches a rule. The binding quantity is the supply of pairs
in which exactly one feature varies and the outcome flips.

**Next, with acceptance declared first:** a perturbation harness — perturb one input at the site, require the
candidate's value to move with it. Acceptance: live set >= 1 on >= 8 of 15 rows, distinct green rules must fall
to 1, and every verified patch must still name a frame-bound value.
