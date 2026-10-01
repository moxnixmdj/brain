from canonical.runtime.execution_surface_package_parity import assess_surface_parity

def base():
    return {
        "os_image": "ubuntu-24.04-task-image",
        "architecture": "x86_64",
        "python_provenance": "debian-managed-python-3.12",
        "environment_management_policy": "externally-managed",
        "package_install_policy": "venv-required",
        "pep668_externally_managed": True,
        "required_native_libraries": ["ffmpeg"],
        "available_native_libraries": ["ffmpeg", "libsndfile"],
    }

def test_exact_surface_passes():
    p=base()
    a=base()
    assert assess_surface_parity(p,a)["pass"] is True

def test_rank19_setup_python_vs_debian_pep668_fails():
    pre=base()
    pre["python_provenance"]="actions-setup-python-cpython-3.12"
    pre["environment_management_policy"]="unmanaged"
    pre["package_install_policy"]="system-pip-allowed"
    pre["pep668_externally_managed"]=False
    actual=base()
    out=assess_surface_parity(pre,actual)
    assert out["pass"] is False
    assert any(x.startswith("python_provenance:") for x in out["mismatches"])
    assert any(x.startswith("environment_management_policy:") for x in out["mismatches"])
    assert any(x.startswith("package_install_policy:") for x in out["mismatches"])
    assert any(x.startswith("pep668_externally_managed:") for x in out["mismatches"])

def test_unknown_policy_fails_closed():
    pre=base()
    pre["package_install_policy"]="unknown"
    out=assess_surface_parity(pre,base())
    assert out["pass"] is False
    assert "package_install_policy" in out["unknown"]

def test_missing_native_library_fails():
    pre=base()
    pre["available_native_libraries"]=[]
    out=assess_surface_parity(pre,base())
    assert out["pass"] is False
    assert "missing_native_libraries:ffmpeg" in out["mismatches"]
