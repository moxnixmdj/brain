from pathlib import Path
_here=Path(__file__).resolve().parent
exec((_here/'rebuild_candidate_v20.py').read_text(),globals())
_ns={};exec((_here/'noncore_profile_repair_v21.py').read_text(),_ns);_ns['apply'](DST)
