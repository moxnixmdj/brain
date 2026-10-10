from pathlib import Path
_here=Path(__file__).resolve().parent
exec((_here/'rebuild_candidate_v12.py').read_text(),globals())
_ns={};exec((_here/'canonical_ast_serialize_v13.py').read_text(),_ns);_ns['apply'](DST)
