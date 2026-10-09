From mathcomp Require Import all_ssreflect all_algebra ssrnum.
From mathcomp.real_closed Require Import ordered_qelim qe_rcf.
Require Import M6.

Import GRing.
Import Order.Theory.
Import Num.Internals.
Import Num.Theory.
Open Scope ring_scope.
Close Scope oterm_scope.

Section KnotStep.

Variable R : rcfType.

Record knot_step := {
  ks_knot_lo : R;
  ks_span_lo : R;
  ks_span_hi : R;
  ks_knot_hi : R
}.

Definition knot_step_ok (s : knot_step) : Prop :=
  ks_knot_lo s <= ks_span_lo s /\
  ks_span_lo s <= ks_span_hi s /\
  ks_span_hi s <= ks_knot_hi s /\
  ks_knot_lo s < ks_knot_hi s.

Definition normalized_at (lo hi x : R) : R :=
  (x - lo) / (hi - lo).

Definition compile_knot_step (s : knot_step) : alpha_desc R :=
  {| alpha0 := normalized_at (ks_knot_lo s) (ks_knot_hi s)
                            (ks_span_lo s);
     alpha1 := normalized_at (ks_knot_lo s) (ks_knot_hi s)
                            (ks_span_hi s) |}.

Lemma normalized_at_in01 lo hi x :
  lo <= x -> x <= hi -> lo < hi ->
  in01 R (normalized_at lo hi x).
Proof.
  move=> hlo hhi hlt.
  have hden : 0%R < hi - lo by rewrite subr_gt0.
  split.
  - rewrite /normalized_at ler_pdivlMr // mul0r subr_ge0.
    exact: hlo.
  - rewrite /normalized_at ler_pdivrMr // mul1r.
    exact: lerD hhi (lexx (- lo)).
Qed.

Lemma compile_knot_step_ok s :
  knot_step_ok s ->
  alpha_ok R (compile_knot_step s).
Proof.
  move=> [h0 [hspan [h1 hstrict]]].
  split.
  - apply: normalized_at_in01 => //.
    exact: le_trans hspan h1.
  - apply: normalized_at_in01 => //.
    exact: le_trans h0 hspan.
Qed.

End KnotStep.
