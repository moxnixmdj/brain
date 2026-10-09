From mathcomp Require Import all_ssreflect all_algebra ssrnum.
From mathcomp.real_closed Require Import ordered_qelim qe_rcf.
Require Import M1 M3 M6 M7 M8.

Import GRing.
Import Order.Theory.
Import Num.Internals.
Import Num.Theory.
Open Scope ring_scope.
Close Scope oterm_scope.

Section SourceDeBoorSemantics.

Variable R : rcfType.

Definition source_step_u
    (U : seq R) (k p r j : nat) (q : R) : R :=
  let L := M8.knot_at R U (M8.deboor_lo_index k p r j) in
  M3.lerp_val R q
    (M8.knot_at R U k - L)
    (M8.knot_at R U k.+1 - L)
  + L.

Definition source_alpha
    (U : seq R) (k p r j : nat) (q : R) : R :=
  let L := M8.knot_at R U (M8.deboor_lo_index k p r j) in
  let H := M8.knot_at R U (M8.deboor_hi_index k j) in
  (source_step_u U k p r j q - L) / (H - L).

Lemma bound_alpha_source_correct
    U k p r j a q :
  M7.kb_valid R (M8.bind_step R U k p r j a) ->
  M6.alpha_val R q
    (M7.compile_kb R (M8.bind_step R U k p r j a))
  =
  source_alpha U k p r j q.
Proof.
  move=> H.
  have Hr := M8.bound_step_ratio_correct
    R U k p r j a q H.
  exact: Hr.
Qed.

Fixpoint source_round_val
    (U : seq R) (k p r j : nat) (q : R)
    (row : seq (M8.alpha_pair R)) (vals : seq R) : seq R :=
  match row with
  | a :: tl =>
      match vals with
      | x :: rest =>
          match rest with
          | y :: yt =>
              M3.lerp_val R (source_alpha U k p r j q) x y
              :: source_round_val U k p r j.+1 q tl (y :: yt)
          | [::] => vals
          end
      | [::] => vals
      end
  | [::] => vals
  end.

Lemma bound_round_source_correct
    U k p r j q row vals :
  M7.kb_round_valid R
    (M8.bind_row R U k p r j row) ->
  M6.round_val R q
    (M7.compile_kb_round R
      (M8.bind_row R U k p r j row))
    vals
  =
  source_round_val U k p r j q row vals.
Proof.
  elim: row j vals => [|a tl IH] j [|x [|y yt]] //=.
  move=> [Ha Htl].
  rewrite (bound_alpha_source_correct U k p r j a q Ha).
  congr (_ :: _).
  exact: IH j.+1 (y :: yt) Htl.
Qed.

Fixpoint source_run_val
    (U : seq R) (k p r : nat) (q : R)
    (rows : seq (seq (M8.alpha_pair R))) (vals : seq R) : seq R :=
  if rows is row :: rs
  then source_run_val U k p r.+1 q rs
       (source_round_val U k p r 0 q row vals)
  else vals.

Lemma bound_schedule_source_correct
    U k p r q rows vals :
  M7.kb_schedule_valid R
    (M8.bind_schedule_from R U k p r rows) ->
  M6.run_val R q
    (M7.compile_kb_schedule R
      (M8.bind_schedule_from R U k p r rows))
    vals
  =
  source_run_val U k p r q rows vals.
Proof.
  elim: rows r vals => [|row rs IH] r vals //=.
  move=> [Hrow Hrs].
  rewrite (bound_round_source_correct
    U k p r 0 q row vals Hrow).
  exact: IH r.+1
    (source_round_val U k p r 0 q row vals) Hrs.
Qed.

Definition source_deboor_val
    (U : seq R) (k p : nat) (q : R)
    (rows : seq (seq (M8.alpha_pair R))) (vals : seq R) : R :=
  head 0%R (source_run_val U k p 1 q rows vals).

Lemma bound_deboor_source_correct
    U k p q rows vals :
  M7.kb_schedule_valid R
    (M8.bind_schedule R U k p rows) ->
  M6.deboor_val R q
    (M7.compile_kb_schedule R
      (M8.bind_schedule R U k p rows))
    vals
  =
  source_deboor_val U k p q rows vals.
Proof.
  move=> H.
  rewrite /M6.deboor_val /source_deboor_val /M8.bind_schedule.
  by rewrite (bound_schedule_source_correct
    U k p 1 q rows vals H).
Qed.

Theorem source_knot_deboor_compiler_correct
    U k p rows (vals : seq (M1.poly2 R)) u v :
  M8.source_schedule_valid R U k p rows ->
  M1.poly2_eval R
    (M6.deboor_poly R
      (M7.compile_kb_schedule R
        (M8.bind_schedule R U k p rows))
      vals) u v
  =
  source_deboor_val U k p u rows
    (map (fun x => M1.poly2_eval R x u v) vals).
Proof.
  move=> [_ [_ [_ [_ Hkb]]]].
  rewrite M6.deboor_poly_correct.
  exact: bound_deboor_source_correct
    U k p u rows
    (map (fun x => M1.poly2_eval R x u v) vals) Hkb.
Qed.

End SourceDeBoorSemantics.
