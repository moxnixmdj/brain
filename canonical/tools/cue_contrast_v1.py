"""Evaluator host: separate projection, producer capture (pinned code), and post-freeze cue-ID grading."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from canonical.tools.stage_harbor_runtime_v1 import stage

SOURCES = '''runtime/brain_unified_model runtime/byte_effect_oracle runtime/demonstration_version_space
runtime/futamura_leapfrog_kernel runtime/memory_policy runtime/pipeline_exec runtime/property
runtime/wave39_leapfrog_unification runtime/bound_capabilities/objective_relevance_bm25.py swe_kernel/__init__.py
swe_kernel/boundary_disjunction_normalization swe_kernel/canonical_memory_crystallizer swe_kernel/concept_library
swe_kernel/dual_program_splicing swe_kernel/egraph_and_deductive_synthesizer swe_kernel/guarded_meaning_ir
swe_kernel/history_induced_edit_grammar swe_kernel/induced_edit_basis swe_kernel/operand_invention
swe_kernel/pytest_contrast_acquisition swe_kernel/repo_native_component_mining swe_kernel/structural_rewrite_induction
swe_kernel/transform_contracts swe_kernel/witness_inversion tools/expressions_from_a_site
tools/identify_a_real_bugs_fix tools/what_a_real_fix_needs_from_the_site'''.split()


def sha(b):return hashlib.sha256(b).hexdigest()


def save(path,obj):
    with path.open('x') as f:print(json.dumps(obj,separators=(',',':'),sort_keys=True),file=f)


def project(rows):
    def texts(k):return sorted({row[k] for row in rows},key=lambda s:sha(s.encode()))
    return {'bank':texts('cue_dialogue'),'queries':texts('trigger_query')}


def capture(rev,packet_path):
    rev=subprocess.check_output(['git','rev-parse','--verify',rev+'^{commit}'],text=True).strip()
    with tempfile.TemporaryDirectory() as td:
        area=Path(td);src=area/'src';base=area/'base';root=area/'root';root.mkdir()
        manifest={}; main='canonical/runtime/brain_unified_model_v1.py'
        for stem in SOURCES:
            name='canonical/'+(stem if stem.endswith('.py') else stem+'_v1.py');target=base/name
            target.parent.mkdir(parents=True,exist_ok=True)
            data=subprocess.check_output(['git','cat-file','blob',rev+':'+name]);target.write_bytes(data);manifest[name]=sha(data)
        manifest.update(stage(src,sources=(main,),source_root=base))
        for name in manifest:
            if not (src/name).is_file():
                (src/name).parent.mkdir(parents=True,exist_ok=True);(src/name).write_bytes((base/name).read_bytes())
        name='canonical/tools/cue_port_worker_v1.py';(src/name).write_bytes(Path(__file__).with_name('cue_port_worker_v1.py').read_bytes())
        manifest[name]=sha((src/name).read_bytes());packet=packet_path.read_bytes()
        run=subprocess.run(['unshare','-Urmpnf','--kill-child','bash',Path(__file__).with_name('screen_port_root_v1.sh'),root,src,'cue'],
                           input=packet,stdout=subprocess.PIPE,timeout=120,check=True,
                           env={'PATH':'/usr/sbin:/usr/bin:/bin','LC_ALL':'C.UTF-8'})
        return {'producer_revision':rev,'producer_manifest':manifest,'packet_sha256':sha(packet),'predictions':json.loads(run.stdout)}


def grade(rows,captures):
    truth={sha(r['trigger_query'].encode()):(sha(r['cue_dialogue'].encode()),r['relation_type']) for r in rows}
    if len(truth)!=len(rows):raise ValueError('nonunique trigger')
    out=[]
    for path in captures:
        raw=path.read_bytes();cap=json.loads(raw); pred=cap['predictions'];modes={}
        for mode in ('empty','rrf','bm25'):
            if pred[mode].keys()!=truth.keys():raise ValueError('prediction set differs')
            counts=collections.defaultdict(lambda:[0,0,0]);ranks={}
            for q,(gold,kind) in truth.items():
                top=pred[mode][q];rank=top.index(gold)+1 if gold in top else None
                ranks[q]=rank
                for bucket in (kind,'all'):
                    v=counts[bucket];v[0]+=1;v[1]+=rank==1;v[2]+=rank is not None
            modes[mode]={'total_at1_at5':counts,'rank_per_query':ranks}
        out.append({'revision':cap['producer_revision'],'capture_sha256':sha(raw),'writes':pred['writes'],'seconds':pred['seconds'],'modes':modes})
    return {'kind':'local contrast retrieval on released cues, NOT official LoCoMo-Plus constraint consistency', 'grades':out}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('op',choices=['project','capture','grade']);p.add_argument('input',type=Path)
    p.add_argument('out',type=Path);p.add_argument('extra',nargs='*');a=p.parse_args()
    if a.op=='capture':result=capture(a.extra[0],a.input)
    else:
        rows=json.loads(a.input.read_bytes());result=project(rows) if a.op=='project' else grade(rows,map(Path,a.extra))
    save(a.out,result)
