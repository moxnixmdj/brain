from pathlib import Path
_here=Path(__file__).resolve().parent
exec((_here/'rebuild_candidate_v19.py').read_text(),globals())
_ns={};exec((_here/'core_profile_repair_v20.py').read_text(),_ns);_ns['apply'](DST)
