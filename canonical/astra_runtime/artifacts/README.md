# Declared artifact finalization root

This directory is the only repository-local durable destination admitted by
`root3_declared_artifact_finalizer_v1.py`.

Files may become durable here only after exact plan/payload/prestate validation
and a canonical final-effect authorization. The directory itself grants no
write, execution, promotion, or acceptance authority.
