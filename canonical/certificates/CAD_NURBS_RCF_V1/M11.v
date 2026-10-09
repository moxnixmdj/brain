From mathcomp Require Import all_ssreflect all_algebra ssrnum.
From mathcomp.real_closed Require Import ordered_qelim qe_rcf.
Require Import M1 M2 M3 M5 M6 M10.

Import GRing.
Open Scope ring_scope.
Close Scope oterm_scope.

Section WeightedTensorNURBS.

Variable R : rcfType.

Definition weight_grid
    (g : seq (seq (M5.weighted_control R))) :=
  M5.grid_map R (M5.wc_w R) g.

Definition xw_grid
    (g : seq (seq (M5.weighted_control R))) :=
  M5.grid_map R (M5.xw R) g.

Definition yw_grid
    (g : seq (seq (M5.weighted_control R))) :=
  M5.grid_map R (M5.yw R) g.

Definition zw_grid
    (g : seq (seq (M5.weighted_control R))) :=
  M5.grid_map R (M5.zw R) g.

Definition compile_weighted_tensor_surface
    (sched_u sched_v : seq (seq (M6.alpha_desc R)))
    (g : seq (seq (M5.weighted_control R))) :
    M2.rational_patch R :=
  {| M2.rpx_num :=
       M10.compile_tensor_surface R sched_u sched_v (xw_grid g);
     M2.rpy_num :=
       M10.compile_tensor_surface R sched_u sched_v (yw_grid g);
     M2.rpz_num :=
       M10.compile_tensor_surface R sched_u sched_v (zw_grid g);
     M2.rp_den :=
       M10.compile_tensor_surface R sched_u sched_v (weight_grid g) |}.

Definition weighted_tensor_x_sem
    sched_u sched_v g u v :=
  M10.tensor_surface_val R sched_u sched_v (xw_grid g) u v
  /
  M10.tensor_surface_val R sched_u sched_v (weight_grid g) u v.

Definition weighted_tensor_y_sem
    sched_u sched_v g u v :=
  M10.tensor_surface_val R sched_u sched_v (yw_grid g) u v
  /
  M10.tensor_surface_val R sched_u sched_v (weight_grid g) u v.

Definition weighted_tensor_z_sem
    sched_u sched_v g u v :=
  M10.tensor_surface_val R sched_u sched_v (zw_grid g) u v
  /
  M10.tensor_surface_val R sched_u sched_v (weight_grid g) u v.

Lemma weighted_tensor_x_compiler_correct
    sched_u sched_v g u v :
  M2.rat_x R
    (compile_weighted_tensor_surface sched_u sched_v g) u v
  =
  weighted_tensor_x_sem sched_u sched_v g u v.
Proof.
  rewrite /compile_weighted_tensor_surface /weighted_tensor_x_sem
          /M2.rat_x /M2.rat_den /=.
  by rewrite !M10.compile_tensor_surface_correct.
Qed.

Lemma weighted_tensor_y_compiler_correct
    sched_u sched_v g u v :
  M2.rat_y R
    (compile_weighted_tensor_surface sched_u sched_v g) u v
  =
  weighted_tensor_y_sem sched_u sched_v g u v.
Proof.
  rewrite /compile_weighted_tensor_surface /weighted_tensor_y_sem
          /M2.rat_y /M2.rat_den /=.
  by rewrite !M10.compile_tensor_surface_correct.
Qed.

Lemma weighted_tensor_z_compiler_correct
    sched_u sched_v g u v :
  M2.rat_z R
    (compile_weighted_tensor_surface sched_u sched_v g) u v
  =
  weighted_tensor_z_sem sched_u sched_v g u v.
Proof.
  rewrite /compile_weighted_tensor_surface /weighted_tensor_z_sem
          /M2.rat_z /M2.rat_den /=.
  by rewrite !M10.compile_tensor_surface_correct.
Qed.

Lemma mapped_weights_nonempty
    (row : seq (M5.weighted_control R)) :
  row <> [::] ->
  map (M5.wc_w R) row <> [::].
Proof.
  by case: row.
Qed.

Lemma positive_weight_row_deboor
    sched_u row u :
  M6.in01 R u ->
  M6.schedule_ok R sched_u ->
  M5.control_row_pos R row ->
  row <> [::] ->
  0%R <
  M6.deboor_val R u sched_u
    (map (M5.wc_w R) row).
Proof.
  move=> hu hs hpos hne.
  apply: M6.deboor_val_pos => //.
  - exact: M5.weight_row_all_pos R row hpos.
  - exact: mapped_weights_nonempty row hne.
Qed.

Lemma all_positive_u_rows
    sched_u g u :
  M6.in01 R u ->
  M6.schedule_ok R sched_u ->
  M5.control_grid_pos R g ->
  M3.all_pos R
    (map
      (fun row =>
        M6.deboor_val R u sched_u
          (map (M5.wc_w R) row))
      g).
Proof.
  move=> hu hs.
  elim: g => [|row tl IH] //=.
  move=> [hrow [hne htl]].
  split.
  - exact: positive_weight_row_deboor
      sched_u row u hu hs hrow hne.
  - exact: IH htl.
Qed.

Lemma row_results_nonempty
    sched_u (g : seq (seq (M5.weighted_control R))) u :
  g <> [::] ->
  map
    (fun row =>
      M6.deboor_val R u sched_u
        (map (M5.wc_w R) row))
    g <> [::].
Proof.
  by case: g.
Qed.

Theorem weighted_tensor_den_positive
    sched_u sched_v g u v :
  M6.in01 R u ->
  M6.in01 R v ->
  M6.schedule_ok R sched_u ->
  M6.schedule_ok R sched_v ->
  M5.control_grid_pos R g ->
  g <> [::] ->
  0%R <
  M2.rat_den R
    (compile_weighted_tensor_surface sched_u sched_v g) u v.
Proof.
  move=> hu hv hsu hsv hg hgne.
  rewrite /compile_weighted_tensor_surface /M2.rat_den /weight_grid /=.
  rewrite M10.compile_tensor_surface_correct
          /M10.tensor_surface_val /M5.grid_map.
  apply: M6.deboor_val_pos => //.
  - rewrite -map_comp /comp.
    exact: all_positive_u_rows sched_u g u hu hsu hg.
  - rewrite -map_comp /comp.
    exact: row_results_nonempty sched_u g u hgne.
Qed.

End WeightedTensorNURBS.
