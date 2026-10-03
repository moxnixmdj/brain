from canonical.runtime import retrieval_registry_repository_bridge_v1 as b

assert b.canon_repo("git+https://github.com/microsoft/TypeScript.git")=="microsoft/typescript"
assert b.canon_repo("https://github.com/tokio-rs/tokio")=="tokio-rs/tokio"
assert b.canon_repo("git://github.com/clap-rs/clap.git")=="clap-rs/clap"
assert len(b.CASES)==5
assert all("/" in x["expected_repository"] for x in b.CASES)

print("test_retrieval_registry_repository_bridge_v1: PASS")
