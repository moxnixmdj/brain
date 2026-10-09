From mathcomp Require Import all_ssreflect all_algebra ssrnum.
From mathcomp.real_closed Require Import ordered_qelim qe_rcf.
Require Import M1 M6 M7.

Import GRing.
Import Order.Theory.
Import Num.Internals.
Import Num.Theory.
Open Scope ring_scope.
Close Scope oterm_scope.

Section IndexedKnotSchedule.

Variable R : rcfType.

Record alpha_pair := {
  ap0 : R;
  ap1 : R
}.

Definition knot_at (U : seq R) (i : nat) : R :=
  nth 0%R U i.

Definition deboor_lo_index
    (k p r j : nat) : nat :=
  (k - p + r + j)%N.

Definition deboor_hi_index
    (k j : nat) : nat :=
  (k + j + 1)%N.

Definition bind_step
    (U : seq R) (k p r j : nat) (a : alpha_pair) :
    M7.knot_blend_cert R :=
  {| M7.kb_span_lo := knot_at U k;
     M7.kb_span_hi := knot_at U k.+1;
     M7.kb_knot_lo := knot_at U (deboor_lo_index k p r j);
     M7.kb_knot_hi := knot_at U (deboor_hi_index k j);
     M7.kb_alpha0 := ap0 a;
     M7.kb_alpha1 := ap1 a |}.

Fixpoint bind_row
    (U : seq R) (k p r j : nat) (row : seq alpha_pair) :
    seq (M7.knot_blend_cert R) :=
  if row is a :: tl
  then bind_step U k p r j a ::
       bind_row U k p r j.+1 tl
  else [::].

Fixpoint bind_schedule_from
    (U : seq R) (k p r : nat)
    (rows : seq (seq alpha_pair)) :
    seq (seq (M7.knot_blend_cert R)) :=
  if rows is row :: rs
  then bind_row U k p r 0 row ::
       bind_schedule_from U k p r.+1 rs
  else [::].

Definition bind_schedule
    (U : seq R) (k p : nat)
    (rows : seq (seq alpha_pair)) :=
  bind_schedule_from U k p 1 rows.

Fixpoint triangular_shape
    (n : nat) (rows : seq (seq alpha_pair)) : Prop :=
  match n, rows with
  | 0, [::] => Logic.True
  | n'.+1, row :: rs =>
      size row = n'.+1 /\ triangular_shape n' rs
  | _, _ => Logic.False
  end.

Definition source_schedule_valid
    (U : seq R) (k p : nat)
    (rows : seq (seq alpha_pair)) : Prop :=
  (p <= k)%N /\
  (k.+1 < size U)%N /\
  (k + p < size U)%N /\
  triangular_shape p rows /\
  M7.kb_schedule_valid R (bind_schedule U k p rows).

Lemma bind_step_span_lo U k p r j a :
  M7.kb_span_lo R (bind_step U k p r j a) = knot_at U k.
Proof. by []. Qed.

Lemma bind_step_span_hi U k p r j a :
  M7.kb_span_hi R (bind_step U k p r j a) = knot_at U k.+1.
Proof. by []. Qed.

Lemma bind_step_knot_lo U k p r j a :
  M7.kb_knot_lo R (bind_step U k p r j a)
  = knot_at U (deboor_lo_index k p r j).
Proof. by []. Qed.

Lemma bind_step_knot_hi U k p r j a :
  M7.kb_knot_hi R (bind_step U k p r j a)
  = knot_at U (deboor_hi_index k j).
Proof. by []. Qed.

Lemma bind_step_alpha0 U k p r j a :
  M7.kb_alpha0 R (bind_step U k p r j a) = ap0 a.
Proof. by []. Qed.

Lemma bind_step_alpha1 U k p r j a :
  M7.kb_alpha1 R (bind_step U k p r j a) = ap1 a.
Proof. by []. Qed.

Lemma source_schedule_kb_valid U k p rows :
  source_schedule_valid U k p rows ->
  M7.kb_schedule_valid R (bind_schedule U k p rows).
Proof.
  by move=> [_ [_ [_ [_ H]]]].
Qed.

Theorem source_schedule_compiles_ok U k p rows :
  source_schedule_valid U k p rows ->
  M6.schedule_ok R
    (M7.compile_kb_schedule R (bind_schedule U k p rows)).
Proof.
  move=> [_ [_ [_ [_ Hkb]]]].
  exact: M7.compile_kb_schedule_ok
    R (bind_schedule U k p rows) Hkb.
Qed.

Theorem source_schedule_deboor_correct
    U k p rows (vals : seq (M1.poly2 R)) u v :
  source_schedule_valid U k p rows ->
  M1.poly2_eval R
    (M6.deboor_poly R
      (M7.compile_kb_schedule R (bind_schedule U k p rows))
      vals) u v
  =
  M6.deboor_val R u
    (M7.compile_kb_schedule R (bind_schedule U k p rows))
    (map (fun x => M1.poly2_eval R x u v) vals).
Proof.
  move=> _.
  exact: M6.deboor_poly_correct.
Qed.

Lemma bound_step_ratio_correct
    U k p r j a q :
  M7.kb_valid R (bind_step U k p r j a) ->
  M6.alpha_val R q
    (M7.compile_kb R (bind_step U k p r j a))
  =
  (M7.kb_span_u R q (bind_step U k p r j a)
     - knot_at U (deboor_lo_index k p r j))
  /
  (knot_at U (deboor_hi_index k j)
     - knot_at U (deboor_lo_index k p r j)).
Proof.
  move=> H.
  exact: M7.compile_kb_ratio_correct q _ H.
Qed.

End IndexedKnotSchedule.
