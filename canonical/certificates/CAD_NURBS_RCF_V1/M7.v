From mathcomp Require Import all_ssreflect all_algebra ssrnum.
From mathcomp.real_closed Require Import ordered_qelim qe_rcf.
Require Import M2 M3 M6.

Import GRing.
Import Order.Theory.
Import Num.Internals.
Import Num.Theory.
Open Scope ring_scope.
Close Scope oterm_scope.

Section KnotBlendCertificates.

Variable R : rcfType.

Record knot_blend_cert := {
  kb_span_lo : R;
  kb_span_hi : R;
  kb_knot_lo : R;
  kb_knot_hi : R;
  kb_alpha0  : R;
  kb_alpha1  : R
}.

Definition kb_den (c : knot_blend_cert) :=
  kb_knot_hi c - kb_knot_lo c.

Definition kb_valid (c : knot_blend_cert) : Prop :=
  kb_knot_lo c < kb_knot_hi c /\
  kb_span_lo c <= kb_span_hi c /\
  M6.in01 R (kb_alpha0 c) /\
  M6.in01 R (kb_alpha1 c) /\
  kb_alpha0 c * kb_den c = kb_span_lo c - kb_knot_lo c /\
  kb_alpha1 c * kb_den c = kb_span_hi c - kb_knot_lo c.

Definition compile_kb (c : knot_blend_cert) : M6.alpha_desc R :=
  {| M6.alpha0 := kb_alpha0 c;
     M6.alpha1 := kb_alpha1 c |}.

Lemma compile_kb_ok c :
  kb_valid c -> M6.alpha_ok R (compile_kb c).
Proof.
  by move=> [_ [_ [h0 [h1 _]]]].
Qed.

Definition kb_span_u (q : R) (c : knot_blend_cert) :=
  M3.lerp_val R q
    (kb_span_lo c - kb_knot_lo c)
    (kb_span_hi c - kb_knot_lo c)
  + kb_knot_lo c.

Lemma kb_span_u_minus_lo q c :
  kb_span_u q c - kb_knot_lo c =
  M3.lerp_val R q
    (kb_span_lo c - kb_knot_lo c)
    (kb_span_hi c - kb_knot_lo c).
Proof.
  by rewrite /kb_span_u addrK.
Qed.

Lemma lerp_mul_const q x0 x1 d :
  M3.lerp_val R q x0 x1 * d =
  M3.lerp_val R q (x0 * d) (x1 * d).
Proof.
  by rewrite /M3.lerp_val mulrDl !mulrA.
Qed.

Lemma compile_kb_cross_correct q c :
  kb_valid c ->
  M6.alpha_val R q (compile_kb c) * kb_den c =
  kb_span_u q c - kb_knot_lo c.
Proof.
  move=> [_ [_ [_ [_ [h0 h1]]]]].
  rewrite /M6.alpha_val /compile_kb /=.
  rewrite lerp_mul_const h0 h1.
  exact: esym (kb_span_u_minus_lo q c).
Qed.

Lemma kb_den_pos c :
  kb_valid c -> 0%R < kb_den c.
Proof.
  move=> [h _].
  by rewrite /kb_den subr_gt0.
Qed.

Lemma compile_kb_ratio_correct q c :
  kb_valid c ->
  M6.alpha_val R q (compile_kb c)
  =
  (kb_span_u q c - kb_knot_lo c) / kb_den c.
Proof.
  move=> hc.
  have hdpos := kb_den_pos c hc.
  have hd : kb_den c != 0%R := lt0r_neq0 hdpos.
  have hcross := compile_kb_cross_correct q c hc.
  have hone : (1%R != 0%R) := @oner_neq0 R.
  have H := proj2
    (M2.div_eq_cross R
      (M6.alpha_val R q (compile_kb c)) 1%R
      (kb_span_u q c - kb_knot_lo c) (kb_den c)
      hone hd).
  have Hr :
      M6.alpha_val R q (compile_kb c) / 1%R
      =
      (kb_span_u q c - kb_knot_lo c) / kb_den c.
  - apply H.
    by rewrite mulr1.
  by rewrite divr1 in Hr.
Qed.

Fixpoint kb_round_valid (r : seq knot_blend_cert) : Prop :=
  if r is c :: tl then kb_valid c /\ kb_round_valid tl else Logic.True.

Definition compile_kb_round (r : seq knot_blend_cert) :
    seq (M6.alpha_desc R) :=
  map compile_kb r.

Lemma compile_kb_round_ok r :
  kb_round_valid r ->
  M6.all_alpha_ok R (compile_kb_round r).
Proof.
  elim: r => [|c tl IH] //=.
  move=> [hc htl].
  split.
  - exact: compile_kb_ok hc.
  - exact: IH htl.
Qed.

Fixpoint kb_schedule_valid
    (s : seq (seq knot_blend_cert)) : Prop :=
  if s is r :: rs
  then kb_round_valid r /\ kb_schedule_valid rs
  else Logic.True.

Definition compile_kb_schedule
    (s : seq (seq knot_blend_cert)) :
    seq (seq (M6.alpha_desc R)) :=
  map compile_kb_round s.

Lemma compile_kb_schedule_ok s :
  kb_schedule_valid s ->
  M6.schedule_ok R (compile_kb_schedule s).
Proof.
  elim: s => [|r rs IH] //=.
  move=> [hr hrs].
  split.
  - exact: compile_kb_round_ok hr.
  - exact: IH hrs.
Qed.

Theorem certified_knot_schedule_deboor_correct
    (s : seq (seq knot_blend_cert))
    (vals : seq (M1.poly2 R)) u v :
  kb_schedule_valid s ->
  M1.poly2_eval R
    (M6.deboor_poly R (compile_kb_schedule s) vals) u v
  =
  M6.deboor_val R u (compile_kb_schedule s)
    (map (fun p => M1.poly2_eval R p u v) vals).
Proof.
  move=> _.
  exact: M6.deboor_poly_correct.
Qed.

End KnotBlendCertificates.
