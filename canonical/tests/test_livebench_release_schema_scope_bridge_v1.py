from canonical.runtime import livebench_release_schema_scope_bridge_v1 as s

def test_frozen_schema_scope_bridge():
    out=s.verify()
    assert out["status"].startswith("PASS__FROZEN_PARQUET_SCHEMA_EXCLUDES_SIX")
    assert len(out["schema_excluded_extra_families"])==6
    assert len(out["schema_indistinguishable_noarg_extras"])==4
    assert out["candidate_scope_count_under_paper_faithfulness_assumption"]==5
    assert out["terminal_rows_read"]==0
    assert out["acceptance_credit"] is False

def test_any_missing_required_field_excludes_argument_bearing_family():
    fields=set(s.EXPECTED_KWARGS_FIELDS)
    for family, required in s.ARG_BEARING_EXTRAS.items():
        assert not required <= fields
        assert family in s.schema_excluded_families(fields)

def test_extra_partition_is_exact():
    from canonical.runtime import livebench_union25_archetypes_v1 as u
    assert set(u.EXTRA10)==set(s.ARG_BEARING_EXTRAS)|set(s.NOARG_EXTRAS)
    assert not (set(s.ARG_BEARING_EXTRAS)&set(s.NOARG_EXTRAS))
