From mathcomp Require Import all_ssreflect all_algebra ssrnum.
From mathcomp.real_closed Require Import ordered_qelim qe_rcf.
Require Import M2 M5 M6 M7 M8 M9 M10 M11.

Import GRing.
Open Scope ring_scope.
Close Scope oterm_scope.

Section SourceNURBSSurface.

Variable R : rcfType.

Definition certified_schedule
    (U : seq R) (k p : nat)
    (rows : seq (seq (M8.alpha_pair R))) :
    seq (seq (M6.alpha_desc R)) :=
  M7.compile_kb_schedule R
    (M8.bind_schedule R U k p rows).

Definition source_tensor_val
    (Uu : seq R) (ku pu : nat)
    (rows_u : seq (seq (M8.alpha_pair R)))
    (Uv : seq R) (kv pv : nat)
    (rows_v : seq (seq (M8.alpha_pair R)))
    (grid : seq (seq R))
    (u v : R) : R :=
  M9.source_deboor_val R Uv kv pv v rows_v
    (map
      (fun row =>
        M9.source_deboor_val R Uu ku pu u rows_u row)
      grid).

Lemma source_schedule_kb
    U k p rows :
  M8.source_schedule_valid R U k p rows ->
  M7.kb_schedule_valid R
    (M8.bind_schedule R U k p rows).
Proof.
  by move=> [_ [_ [_ [_ H]]]].
Qed.

Lemma certified_schedule_ok
    U k p rows :
  M8.source_schedule_valid R U k p rows ->
  M6.schedule_ok R (certified_schedule U k p rows).
Proof.
  move=> H.
  rewrite /certified_schedule.
  exact: M7.compile_kb_schedule_ok
    R (M8.bind_schedule R U k p rows)
    (source_schedule_kb U k p rows H).
Qed.

Theorem certified_tensor_source_correct
    Uu ku pu rows_u Uv kv pv rows_v grid u v :
  M8.source_schedule_valid R Uu ku pu rows_u ->
  M8.source_schedule_valid R Uv kv pv rows_v ->
  M10.tensor_surface_val R
    (certified_schedule Uu ku pu rows_u)
    (certified_schedule Uv kv pv rows_v)
    grid u v
  =
  source_tensor_val
    Uu ku pu rows_u Uv kv pv rows_v grid u v.
Proof.
  move=> Hu Hv.
  have Hku := source_schedule_kb Uu ku pu rows_u Hu.
  have Hkv := source_schedule_kb Uv kv pv rows_v Hv.
  rewrite /M10.tensor_surface_val /source_tensor_val
          /certified_schedule.
  rewrite (M9.bound_deboor_source_correct
    R Uv kv pv v rows_v
    (map
      (fun row =>
        M6.deboor_val R u
          (M7.compile_kb_schedule R
            (M8.bind_schedule R Uu ku pu rows_u))
          row)
      grid)
    Hkv).
  have Hmap :
    map
      (fun row =>
        M6.deboor_val R u
          (M7.compile_kb_schedule R
            (M8.bind_schedule R Uu ku pu rows_u))
          row)
      grid
    =
    map
      (fun row =>
        M9.source_deboor_val R Uu ku pu u rows_u row)
      grid.
  - elim: grid => [|row tl IH] //=.
    by rewrite (M9.bound_deboor_source_correct
      R Uu ku pu u rows_u row Hku) IH.
  by rewrite Hmap.
Qed.

Definition compile_source_weighted_nurbs
    Uu ku pu rows_u Uv kv pv rows_v
    (g : seq (seq (M5.weighted_control R))) :
    M2.rational_patch R :=
  M11.compile_weighted_tensor_surface R
    (certified_schedule Uu ku pu rows_u)
    (certified_schedule Uv kv pv rows_v)
    g.

Definition source_weighted_x_sem
    Uu ku pu rows_u Uv kv pv rows_v g u v :=
  source_tensor_val
    Uu ku pu rows_u Uv kv pv rows_v
    (M11.xw_grid R g) u v
  /
  source_tensor_val
    Uu ku pu rows_u Uv kv pv rows_v
    (M11.weight_grid R g) u v.

Definition source_weighted_y_sem
    Uu ku pu rows_u Uv kv pv rows_v g u v :=
  source_tensor_val
    Uu ku pu rows_u Uv kv pv rows_v
    (M11.yw_grid R g) u v
  /
  source_tensor_val
    Uu ku pu rows_u Uv kv pv rows_v
    (M11.weight_grid R g) u v.

Definition source_weighted_z_sem
    Uu ku pu rows_u Uv kv pv rows_v g u v :=
  source_tensor_val
    Uu ku pu rows_u Uv kv pv rows_v
    (M11.zw_grid R g) u v
  /
  source_tensor_val
    Uu ku pu rows_u Uv kv pv rows_v
    (M11.weight_grid R g) u v.

Theorem source_weighted_x_compiler_correct
    Uu ku pu rows_u Uv kv pv rows_v g u v :
  M8.source_schedule_valid R Uu ku pu rows_u ->
  M8.source_schedule_valid R Uv kv pv rows_v ->
  M2.rat_x R
    (compile_source_weighted_nurbs
      Uu ku pu rows_u Uv kv pv rows_v g)
    u v
  =
  source_weighted_x_sem
    Uu ku pu rows_u Uv kv pv rows_v g u v.
Proof.
  move=> Hu Hv.
  rewrite /compile_source_weighted_nurbs
          /source_weighted_x_sem.
  rewrite M11.weighted_tensor_x_compiler_correct /M11.weighted_tensor_x_sem.
  by rewrite
    (certified_tensor_source_correct
      Uu ku pu rows_u Uv kv pv rows_v
      (M11.xw_grid R g) u v Hu Hv)
    (certified_tensor_source_correct
      Uu ku pu rows_u Uv kv pv rows_v
      (M11.weight_grid R g) u v Hu Hv).
Qed.

Theorem source_weighted_y_compiler_correct
    Uu ku pu rows_u Uv kv pv rows_v g u v :
  M8.source_schedule_valid R Uu ku pu rows_u ->
  M8.source_schedule_valid R Uv kv pv rows_v ->
  M2.rat_y R
    (compile_source_weighted_nurbs
      Uu ku pu rows_u Uv kv pv rows_v g)
    u v
  =
  source_weighted_y_sem
    Uu ku pu rows_u Uv kv pv rows_v g u v.
Proof.
  move=> Hu Hv.
  rewrite /compile_source_weighted_nurbs
          /source_weighted_y_sem.
  rewrite M11.weighted_tensor_y_compiler_correct /M11.weighted_tensor_y_sem.
  by rewrite
    (certified_tensor_source_correct
      Uu ku pu rows_u Uv kv pv rows_v
      (M11.yw_grid R g) u v Hu Hv)
    (certified_tensor_source_correct
      Uu ku pu rows_u Uv kv pv rows_v
      (M11.weight_grid R g) u v Hu Hv).
Qed.

Theorem source_weighted_z_compiler_correct
    Uu ku pu rows_u Uv kv pv rows_v g u v :
  M8.source_schedule_valid R Uu ku pu rows_u ->
  M8.source_schedule_valid R Uv kv pv rows_v ->
  M2.rat_z R
    (compile_source_weighted_nurbs
      Uu ku pu rows_u Uv kv pv rows_v g)
    u v
  =
  source_weighted_z_sem
    Uu ku pu rows_u Uv kv pv rows_v g u v.
Proof.
  move=> Hu Hv.
  rewrite /compile_source_weighted_nurbs
          /source_weighted_z_sem.
  rewrite M11.weighted_tensor_z_compiler_correct /M11.weighted_tensor_z_sem.
  by rewrite
    (certified_tensor_source_correct
      Uu ku pu rows_u Uv kv pv rows_v
      (M11.zw_grid R g) u v Hu Hv)
    (certified_tensor_source_correct
      Uu ku pu rows_u Uv kv pv rows_v
      (M11.weight_grid R g) u v Hu Hv).
Qed.

Theorem source_weighted_den_positive
    Uu ku pu rows_u Uv kv pv rows_v g u v :
  M8.source_schedule_valid R Uu ku pu rows_u ->
  M8.source_schedule_valid R Uv kv pv rows_v ->
  M6.in01 R u ->
  M6.in01 R v ->
  M5.control_grid_pos R g ->
  g <> [::] ->
  0%R <
  M2.rat_den R
    (compile_source_weighted_nurbs
      Uu ku pu rows_u Uv kv pv rows_v g)
    u v.
Proof.
  move=> Hu Hv hu hv hg hgne.
  apply: M11.weighted_tensor_den_positive.
  - exact: hu.
  - exact: hv.
  - exact: certified_schedule_ok Uu ku pu rows_u Hu.
  - exact: certified_schedule_ok Uv kv pv rows_v Hv.
  - exact: hg.
  - exact: hgne.
Qed.

End SourceNURBSSurface.
