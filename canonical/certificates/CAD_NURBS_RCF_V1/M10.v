From mathcomp Require Import all_ssreflect all_algebra ssrnum.
From mathcomp.real_closed Require Import ordered_qelim qe_rcf.
Require Import M1 M3 M6.

Import GRing.
Open Scope ring_scope.
Close Scope oterm_scope.

Section ParametricScheduleCompiler.

Variable R : rcfType.

Definition p2 := M1.poly2 R.

Definition alpha_poly_on
    (param : p2) (a : M6.alpha_desc R) : p2 :=
  M3.lerp_poly R param
    (M1.P2Const R (M6.alpha0 R a))
    (M1.P2Const R (M6.alpha1 R a)).

Lemma alpha_poly_on_correct param a u v :
  M1.poly2_eval R (alpha_poly_on param a) u v
  =
  M6.alpha_val R (M1.poly2_eval R param u v) a.
Proof.
  by rewrite /alpha_poly_on /M6.alpha_val M3.lerp_poly_correct /=.
Qed.

Fixpoint round_poly_on
    (param : p2)
    (alphas : seq (M6.alpha_desc R))
    (vals : seq p2) : seq p2 :=
  match alphas with
  | a :: ars =>
      match vals with
      | x :: rest =>
          match rest with
          | y :: yt =>
              M3.lerp_poly R (alpha_poly_on param a) x y
              :: round_poly_on param ars (y :: yt)
          | [::] => vals
          end
      | [::] => vals
      end
  | [::] => vals
  end.

Lemma round_poly_on_correct param alphas vals u v :
  map (fun p => M1.poly2_eval R p u v)
      (round_poly_on param alphas vals)
  =
  M6.round_val R (M1.poly2_eval R param u v) alphas
    (map (fun p => M1.poly2_eval R p u v) vals).
Proof.
  elim: alphas vals => [|a ars IH] [|x [|y yt]] //=.
  by rewrite /M3.lerp_poly /alpha_poly_on /M6.alpha_val /M3.lerp_val /= IH.
Qed.

Fixpoint run_poly_on
    (param : p2)
    (sched : seq (seq (M6.alpha_desc R)))
    (vals : seq p2) : seq p2 :=
  if sched is row :: rs
  then run_poly_on param rs (round_poly_on param row vals)
  else vals.

Lemma run_poly_on_correct param sched vals u v :
  map (fun p => M1.poly2_eval R p u v)
      (run_poly_on param sched vals)
  =
  M6.run_val R (M1.poly2_eval R param u v) sched
    (map (fun p => M1.poly2_eval R p u v) vals).
Proof.
  elim: sched vals => [|row rs IH] vals //=.
  rewrite IH round_poly_on_correct.
  by [].
Qed.

Definition deboor_poly_on
    (param : p2)
    (sched : seq (seq (M6.alpha_desc R)))
    (vals : seq p2) : p2 :=
  head (M1.P2Const R 0%R) (run_poly_on param sched vals).

Lemma deboor_poly_on_correct param sched vals u v :
  M1.poly2_eval R (deboor_poly_on param sched vals) u v
  =
  M6.deboor_val R (M1.poly2_eval R param u v) sched
    (map (fun p => M1.poly2_eval R p u v) vals).
Proof.
  rewrite /deboor_poly_on /M6.deboor_val M6.head_poly_eval.
  by rewrite run_poly_on_correct.
Qed.

Definition const_polys (s : seq R) : seq p2 :=
  map (M1.P2Const R) s.

Lemma eval_const_polys s u v :
  map (fun p => M1.poly2_eval R p u v) (const_polys s) = s.
Proof.
  rewrite /const_polys -map_comp /=.
  by rewrite map_id.
Qed.

Definition compile_row_u
    (sched_u : seq (seq (M6.alpha_desc R)))
    (row : seq R) : p2 :=
  deboor_poly_on (M1.P2U R) sched_u (const_polys row).

Lemma compile_row_u_correct sched_u row u v :
  M1.poly2_eval R (compile_row_u sched_u row) u v
  =
  M6.deboor_val R u sched_u row.
Proof.
  rewrite /compile_row_u deboor_poly_on_correct /=.
  by rewrite eval_const_polys.
Qed.

Definition compile_rows_u
    (sched_u : seq (seq (M6.alpha_desc R)))
    (grid : seq (seq R)) : seq p2 :=
  map (compile_row_u sched_u) grid.

Lemma eval_compile_rows_u sched_u grid u v :
  map (fun p => M1.poly2_eval R p u v)
      (compile_rows_u sched_u grid)
  =
  map (fun row => M6.deboor_val R u sched_u row) grid.
Proof.
  elim: grid => [|row tl IH] //=.
  by rewrite compile_row_u_correct IH.
Qed.

Definition compile_tensor_surface
    (sched_u sched_v : seq (seq (M6.alpha_desc R)))
    (grid : seq (seq R)) : p2 :=
  deboor_poly_on (M1.P2V R) sched_v
    (compile_rows_u sched_u grid).

Definition tensor_surface_val
    (sched_u sched_v : seq (seq (M6.alpha_desc R)))
    (grid : seq (seq R)) (u v : R) : R :=
  M6.deboor_val R v sched_v
    (map (fun row => M6.deboor_val R u sched_u row) grid).

Theorem compile_tensor_surface_correct
    sched_u sched_v grid u v :
  M1.poly2_eval R
    (compile_tensor_surface sched_u sched_v grid) u v
  =
  tensor_surface_val sched_u sched_v grid u v.
Proof.
  rewrite /compile_tensor_surface /tensor_surface_val
          deboor_poly_on_correct /=.
  by rewrite eval_compile_rows_u.
Qed.

End ParametricScheduleCompiler.
