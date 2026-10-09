From mathcomp Require Import all_ssreflect all_algebra ssrnum.
From mathcomp.real_closed Require Import ordered_qelim qe_rcf.
Require Import M1 M2 M3.

Import GRing.
Import Order.Theory.
Import Num.Internals.
Import Num.Theory.
Open Scope ring_scope.
Close Scope oterm_scope.

Section TensorBezier.

Variable R : rcfType.

Definition p2 := M1.poly2 R.

Definition row_poly (row : seq R) : p2 :=
  dc_poly R (M1.P2U R) (map (M1.P2Const R) row).

Definition row_val (row : seq R) (u : R) : R :=
  dc_val R u row.

Lemma row_poly_correct row u v :
  M1.poly2_eval R (row_poly row) u v = row_val row u.
Proof.
  by rewrite /row_poly /row_val dc_poly_correct -map_comp /= map_id.
Qed.

Definition grid_poly (grid : seq (seq R)) : p2 :=
  dc_poly R (M1.P2V R) (map row_poly grid).

Definition grid_val (grid : seq (seq R)) (u v : R) : R :=
  dc_val R v (map (fun row => row_val row u) grid).

Lemma grid_poly_correct grid u v :
  M1.poly2_eval R (grid_poly grid) u v = grid_val grid u v.
Proof.
  rewrite /grid_poly /grid_val dc_poly_correct -map_comp.
  apply: f_equal.
  apply: eq_map => row.
  exact: row_poly_correct.
Qed.

Fixpoint grid_all_pos (grid : seq (seq R)) : Prop :=
  if grid is row :: tl
  then all_pos R row /\ row != [::] /\ grid_all_pos tl
  else Logic.True.

Lemma row_val_pos row u :
  0%R <= u -> u <= 1%R ->
  all_pos R row -> row != [::] ->
  0%R < row_val row u.
Proof.
  exact: dc_val_pos.
Qed.

Lemma grid_rows_eval_all_pos grid u :
  0%R <= u -> u <= 1%R ->
  grid_all_pos grid ->
  all_pos R (map (fun row => row_val row u) grid).
Proof.
  move=> hu0 hu1.
  elim: grid => [|row tl IH] //=.
  move=> [hrow [hrow_ne htl]].
  split.
  - exact: row_val_pos hu0 hu1 hrow hrow_ne.
  - exact: IH htl.
Qed.

Lemma grid_val_pos grid u v :
  0%R <= u -> u <= 1%R ->
  0%R <= v -> v <= 1%R ->
  grid_all_pos grid -> grid != [::] ->
  0%R < grid_val grid u v.
Proof.
  move=> hu0 hu1 hv0 hv1 hpos hne.
  apply: dc_val_pos => //.
  - exact: grid_rows_eval_all_pos hu0 hu1 hpos.
  - by case: grid hpos hne => [|row tl].
Qed.

Record homogeneous_bezier_patch := {
  hx_grid : seq (seq R);
  hy_grid : seq (seq R);
  hz_grid : seq (seq R);
  hw_grid : seq (seq R)
}.

Definition bezier_to_rational_patch (b : homogeneous_bezier_patch) :
    rational_patch R :=
  {| rpx_num := grid_poly (hx_grid b);
     rpy_num := grid_poly (hy_grid b);
     rpz_num := grid_poly (hz_grid b);
     rp_den  := grid_poly (hw_grid b) |}.

Definition bezier_den_sem (b : homogeneous_bezier_patch) u v :=
  grid_val (hw_grid b) u v.

Lemma bezier_den_compiler_correct b u v :
  rat_den R (bezier_to_rational_patch b) u v
  = bezier_den_sem b u v.
Proof.
  exact: grid_poly_correct.
Qed.

Lemma bezier_positive_weights_den_positive b u v :
  0%R <= u -> u <= 1%R ->
  0%R <= v -> v <= 1%R ->
  grid_all_pos (hw_grid b) ->
  hw_grid b != [::] ->
  0%R < rat_den R (bezier_to_rational_patch b) u v.
Proof.
  move=> hu0 hu1 hv0 hv1 hpos hne.
  rewrite bezier_den_compiler_correct.
  exact: grid_val_pos hu0 hu1 hv0 hv1 hpos hne.
Qed.

End TensorBezier.
