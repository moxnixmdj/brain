from pathlib import Path
from canonical.runtime.root3_effect_surface_audit_v1 import audit_file,audit_source

ASTRA=Path("canonical/runtime/astra_runtime.py")
ASTRA_BLOB="7ca7aa3f09e45261f644ef31143dbba5fa7f823e"

def test_live_astra_fails_closed_constructively():
    out=audit_file(ASTRA,ASTRA_BLOB)
    assert out["status"]=="FAIL_CLOSED_UNMEDIATED_EFFECT_SURFACE",out
    kinds=set(out["blocking_effect_classes"])
    assert {"PROCESS_SPAWN","RAW_NETWORK_FALLBACK","FILESYSTEM_MUTATION","DYNAMIC_CODE_EXECUTION","OPTIONAL_BROKER_BOUNDARY"}<=kinds,out
    assert len(out["effect_sites"]["PROCESS_SPAWN"])>=8,out
    assert len(out["effect_sites"]["FILESYSTEM_MUTATION"])>=20,out
    assert out["no_bypass_proven"] is False
    assert out["acceptance_credit_delta"]==0

def test_pure_source_passes():
    out=audit_source("def f(x):\n return x+1\n")
    assert out["status"]=="PASS" and out["effect_site_count"]==0

def test_process_spawn_blocks():
    out=audit_source("import subprocess\ndef f():\n return subprocess.run(['true'])\n")
    assert out["blocking_effect_classes"]==["PROCESS_SPAWN"]

def test_raw_network_fallback_blocks():
    out=audit_source("def f(r):\n return _ORIGINAL_URLOPEN(r)\n")
    assert out["blocking_effect_classes"]==["RAW_NETWORK_FALLBACK"]

def test_read_open_not_mutation_write_open_is():
    assert audit_source("def f(p):\n return p.open('r')\n")["status"]=="PASS"
    assert "FILESYSTEM_MUTATION" in audit_source("def f(p):\n return p.open('a')\n")["blocking_effect_classes"]

def test_dynamic_exec_module_blocks():
    out=audit_source("def f(s,m):\n return s.loader.exec_module(m)\n")
    assert out["blocking_effect_classes"]==["DYNAMIC_CODE_EXECUTION"]

def test_blob_drift_blocks_before_scope_claim():
    out=audit_source("def f():\n return 1\n","0"*40)
    assert out["reason"]=="SOURCE_BLOB_DRIFT" and out["no_bypass_proven"] is False
