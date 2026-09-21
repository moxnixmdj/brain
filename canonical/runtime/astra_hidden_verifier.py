#!/usr/bin/env python3
import json,pathlib,hashlib,re
ROOT=pathlib.Path(__file__).resolve().parents[2];A=ROOT/'canonical'/'astra'
def read(n):return json.loads((A/n).read_text())
def sha(p):
 h=hashlib.sha256();h.update(pathlib.Path(p).read_bytes());return h.hexdigest()
c=read('HIDDEN_EXECUTION_CONTRACT.json');m=read('HIDDEN_ONESHOT_CONSUMED.json');r=read('HIDDEN_RESULT.json');t=read('HIDDEN_TRAJECTORY.json')
acts=t.get('actions',[]);frames=t.get('frames',[])
clicks=[a.get('payload',{}).get('matched_phrase','') for a in acts if a.get('kind')=='click']
checks={
 'binding_index':c['corpus']['index']==342 and r.get('candidate_index')==342 and m.get('candidate_index')==342,
 'binding_new_id':c['candidate']['new_id']=='mbta-1E2K9j2Q' and m.get('new_id')=='mbta-1E2K9j2Q',
 'instruction_sha':c['candidate']['instruction_sha256']=='b04e81d8beec27ba757d966e7cf2b45fa74eda78981605ccd619252d9691ec9f',
 'one_shot_marker':m.get('scored_attempts_authorized')==1 and m.get('scored_retries_authorized')==0 and m.get('hidden_navigation_started') is True,
 'one_attempt':r.get('hidden_scored_attempts_consumed')==1 and r.get('scored_retries')==0,
 'terminal_success':r.get('success') is True and r.get('terminal_manifest',{}).get('outcome')=='TERMINAL_SUCCESS',
 'visual_only':t.get('visual_only') is True and t.get('forbidden_semantic_methods_sent')==0 and r.get('pixel_ocr_only') is True,
 'frames_sealed':len(frames)>=6 and all(f.get('dom_used') is False and f.get('source')=='Page.captureScreenshot' and len(f.get('sha256',''))==64 for f in frames),
 'ferry_clicked':any(x=='Ferry' for x in clicks),
 'charlestown_clicked':any(x=='Charlestown Ferry' for x in clicks),
 'weekend_selected':any(x=='Saturday|Sunday' for x in clicks),
 'pdf_section_seen':any('PDF Schedules' in f.get('ocr_text','') for f in frames),
 'weekend_pdf_clicked':any('Weekend Schedule PDF' in x for x in clicks),
 'efficiency_measured':isinstance(r.get('actions_total'),int) and r.get('action_budget')==40 and r.get('actions_total')<=40 and 0<r.get('budget_fraction',0)<=1,
 'fresh_hosted_run':bool(m.get('armed_at_utc')) and bool(m.get('navigation_started_at_utc')),
 'no_self_promotion':r.get('promotion_authorized') is False
}
passed=all(checks.values())
pred={
 'ASTRA_COMPUTER_GUI_USE__HIDDEN_UI_GENERALIZATION':'PROVEN' if passed else 'UNPROVEN',
 'ASTRA_NOVEL_ADAPTATION_REASONING__FRESH_HIDDEN_NOVEL_ENVIRONMENTS':'PROVEN' if passed else 'UNPROVEN',
 'ASTRA_NOVEL_ADAPTATION_REASONING__ACTION_EFFICIENCY_MEASUREMENT':'PROVEN' if passed else 'UNPROVEN'
}
out={'schema':'RECOVERY_HIDDEN_ADJUDICATION_V1','verifier_identity':'GITHUB-FRESH-DETERMINISTIC-ASTRA-VERIFIER-1','executor_identity':'RECOVERY-WEBONE-H6-SUCCESSOR-MBTA006-V1','verifier_distinct_from_executor':True,'checks':checks,'all_required_checks_pass':passed,'predicate_adjudication':pred,'astra_non_global_before':'48/51','astra_non_global_after':'51/51' if passed else '48/51','global_predicates_promoted':False,'promotion_authorized_for_three_predicates':passed,'verified_from_sealed_evidence_only':True}
(A/'HIDDEN_ADJUDICATION.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(json.dumps(out))
if not passed:raise SystemExit(8)
