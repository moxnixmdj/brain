from canonical.runtime.material_effect_reference_monitor_v1 import git_blob_sha


def test_git_blob_sha_known_vector():
    assert git_blob_sha(b"hello\n") == "ce013625030ba8dba906f756967f9e9ca394464a"
