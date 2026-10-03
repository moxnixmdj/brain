from canonical.runtime import registry_repository_reverse_index_v1 as r

rows=[
 {"ecosystem":"npm","package_id":"typescript","repository_url":"git+https://github.com/microsoft/TypeScript.git"},
 {"ecosystem":"npm","package_id":"native-preview","repository_url":"https://github.com/microsoft/TypeScript"},
 {"ecosystem":"crates","package_id":"tokio","repository_url":"https://github.com/tokio-rs/tokio"},
]
idx=r.build(rows,snapshot_id="toy-partial")
assert idx["negative_lookup_authority"] is False
ts=r.lookup(idx,"https://github.com/microsoft/TypeScript.git")
assert {x["package_id"] for x in ts["packages"]}=={"typescript","native-preview"}
assert ts["unknown_if_empty"] is True
missing=r.lookup(idx,"https://github.com/x/y")
assert missing["package_count"]==0 and missing["negative_authoritative"] is False

try:
 r.build(rows,snapshot_id="x",independently_complete=True)
 raise AssertionError("complete snapshot without receipt accepted")
except ValueError:
 pass

complete=r.build(rows,snapshot_id="toy-complete",independently_complete=True,completeness_receipt="receipt:1")
assert complete["negative_lookup_authority"] is True
assert r.lookup(complete,"https://github.com/x/y")["negative_authoritative"] is True

print("test_registry_repository_reverse_index_v1: PASS")
