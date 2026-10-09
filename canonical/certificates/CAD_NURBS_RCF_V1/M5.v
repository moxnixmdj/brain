From mathcomp Require Import all_ssreflect all_algebra ssrnum.
From mathcomp.real_closed Require Import ordered_qelim qe_rcf.
Require Import M1 M2 M3 M4.

Import GRing.
Import Order.Theory.
Import Num.Internals.
Import Num.Theory.
Open Scope ring_scope.
Close Scope oterm_scope.

Section WeightedBezier.

Variable R : rcfType.

Record weighted_control := {
  wc_x : R;
  wc_y : R;
  wc_z : R;
  wc_w : R
}.

Definition xw (c : weighted_control) := wc_w c * wc_x c.
Definition yw (c : weighted_control) := wc_w c * wc_y c.
Definition zw (c : weighted_control) := wc_w c * wc_z c.

Definition grid_map (f : weighted_control -> R)
    (g : seq (seq weighted_control)) : seq (seq R) :=
  map (fun row => map f row) g.

Definition controls_to_homogeneous
    (g : seq (seq weighted_control)) : homogeneous_bezier_patch R :=
  {| hx_grid := grid_map xw g;
     hy_grid := grid_map yw g;
     hz_grid := grid_map zw g;
     hw_grid := grid_map wc_w g |}.

Fixpoint control_row_pos (row : seq weighted_control) : Prop :=
  if row is c :: tl
  then 0%R < wc_w c /\ control_row_pos tl
  else Logic.True.

Fixpoint control_grid_pos (g : seq (seq weighted_control)) : Prop :=
  if g is row :: tl
  then control_row_pos row /\ row <> [::] /\ control_grid_pos tl
  else Logic.True.

Lemma weight_row_all_pos row :
  control_row_pos row ->
  all_pos R (map wc_w row).
Proof.
  elim: row => [|c tl IH] //=.
  by move=> [hc htl]; split=> //; exact: IH htl.
Qed.

Lemma weight_grid_all_pos g :
  control_grid_pos g ->
  grid_all_pos R (grid_map wc_w g).
Proof.
  elim: g => [|row tl IH] //=.
  move=> [hrow [hne htl]].
  split.
  - exact: weight_row_all_pos hrow.
  - split.
    + by case: row hrow hne => [|c rt].
    + exact: IH htl.
Qed.

Lemma weight_grid_nonempty g :
  g <> [::] -> grid_map wc_w g != [::].
Proof.
  by case: g => [|row tl].
Qed.

Definition weighted_bezier_x_sem
    (g : seq (seq weighted_control)) u v :=
  grid_val R (grid_map xw g) u v /
  grid_val R (grid_map wc_w g) u v.

Definition weighted_bezier_y_sem
    (g : seq (seq weighted_control)) u v :=
  grid_val R (grid_map yw g) u v /
  grid_val R (grid_map wc_w g) u v.

Definition weighted_bezier_z_sem
    (g : seq (seq weighted_control)) u v :=
  grid_val R (grid_map zw g) u v /
  grid_val R (grid_map wc_w g) u v.

Lemma weighted_bezier_x_compiler_correct g u v :
  rat_x R
    (bezier_to_rational_patch R (controls_to_homogeneous g)) u v
  = weighted_bezier_x_sem g u v.
Proof.
  rewrite /weighted_bezier_x_sem /controls_to_homogeneous /grid_map
          /rat_x /rat_den /=.
  by rewrite !grid_poly_correct.
Qed.

Lemma weighted_bezier_y_compiler_correct g u v :
  rat_y R
    (bezier_to_rational_patch R (controls_to_homogeneous g)) u v
  = weighted_bezier_y_sem g u v.
Proof.
  rewrite /weighted_bezier_y_sem /controls_to_homogeneous /grid_map
          /rat_y /rat_den /=.
  by rewrite !grid_poly_correct.
Qed.

Lemma weighted_bezier_z_compiler_correct g u v :
  rat_z R
    (bezier_to_rational_patch R (controls_to_homogeneous g)) u v
  = weighted_bezier_z_sem g u v.
Proof.
  rewrite /weighted_bezier_z_sem /controls_to_homogeneous /grid_map
          /rat_z /rat_den /=.
  by rewrite !grid_poly_correct.
Qed.

Theorem positive_control_weights_den_positive g u v :
  0%R <= u -> u <= 1%R ->
  0%R <= v -> v <= 1%R ->
  control_grid_pos g ->
  g <> [::] ->
  0%R <
    rat_den R
      (bezier_to_rational_patch R (controls_to_homogeneous g)) u v.
Proof.
  move=> hu0 hu1 hv0 hv1 hpos hne.
  apply: bezier_positive_weights_den_positive => //.
  - exact: weight_grid_all_pos hpos.
  - exact: weight_grid_nonempty hne.
Qed.

End WeightedBezier.
