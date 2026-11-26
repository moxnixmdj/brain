"""Evaluator on an exported #7144 head, not a producer, not a benchmark.

Run under the offline root in SINGLE_EPISODE_REPRODUCTION. No task feeds these
inventories or labels to the model. Count names, import results and observed
behavior separately. These inputs carry exactly one underlying observation.
"""
from collections import Counter
import hashlib
import importlib
import json
from pathlib import Path
import sys


def run(root):
    path = root/'canonical/runtime/wave45_46_anytime_valid_quotient_metamorphic_hcu_v1.py'
    contents = path.read_bytes()
    sys.path.insert(0, str(root))
    from canonical.runtime import wave45_46_anytime_valid_quotient_metamorphic_hcu_v1 as w
    if Path(w.__file__).resolve()!=path.resolve():
        raise RuntimeError('wrong code loaded')
    names=list(w.ALL_W40_W46_AWAKENED_DARK_MODULES)
    # Earlier waves list filenames, later waves use dotted import addresses.
    # A literal importlib call on a slash-path is not an importability test.
    modules=[name.removesuffix('.py').replace('/', '.') for name in names]
    imports={}
    for name in dict.fromkeys(modules):
        try:
            mod=importlib.import_module(name)
            imports[name]='imported' if Path(mod.__file__).resolve().is_relative_to(root) else 'other tree'
        except Exception as err:
            imports[name]=f'{type(err).__name__}: {err}'
    m=w.AntiManufacturedConfidenceMemoryEngine();rows=[]
    for label in ('one event','one event','alias for one event'):
        r=m.ingest_fact('lamp','status','on',modality='HEDGED',source_id=label,
                        raw_text='Maybe the lamp is on.',executable_verified=False)
        rows.append({k:r[k] for k in ('quarantined','accepted_as_authoritative','record')})
    one_measurement=True
    bet=w.AnytimeValidEValueEvolutionGateKernel().compute_e_process([one_measurement]*16)
    t=w.ThreeTierZeroForgettingContinualKernel().tier1_doc_to_lora_manifest('d','One paragraph about a lamp.')
    return {'revision':'faea7c3177fc447499e0c7fe2abc5fe0575c23d0','kernel_sha256':hashlib.sha256(contents).hexdigest(),
            'kind':'explicit constructed controls; no task dispatch or model training',
            'inventory':{'listed':len(names),'distinct_labels':len(set(names)),'filename_labels':sum('/' in n for n in names),'distinct_modules':len(imports),'duplicates':{k:n for k,n in Counter(modules).items() if n>1},
                         'plain_python_imports':imports},'hedged_single_observation':rows,
            'one_outcome_copied_16_times':bet,'tier1_return':t}


if __name__=='__main__':
    print(json.dumps(run(Path(sys.argv[1]).resolve(strict=True)),indent=2))
