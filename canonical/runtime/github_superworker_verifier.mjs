import fs from 'node:fs';
import crypto from 'node:crypto';
const S='canonical/superworker_state/SUPERWORKER_GITHUB_1.json';
const E='canonical/superworker_evidence/SUPERWORKER_GITHUB_QUALIFICATION_1.json';
const C='canonical/qualification/SUPERWORKER_GITHUB_1_CRITERIA.json';
const O='canonical/qualification/SUPERWORKER_GITHUB_1_ADJUDICATION.json';
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const D=`canonical/superworker_consumed/${read(S).mission_id}.json`;
const sha=x=>crypto.createHash('sha256').update(typeof x==='string'?x:JSON.stringify(x)).digest('hex');
const now=()=>new Date().toISOString();
const s=read(S),e=read(E),c=read(C),d=read(D);
const checks={
  persistent_identity:s.agent_id==='SUPERWORKER-GITHUB-1',
  canonical_durable_state:s.generation>=2&&s.status==='COMPLETE',
  fresh_run_continuation:s.provider_events.some(x=>x.type==='FRESH_RUN_CONTINUED'),
  provider_failure_recovery:s.provider_events.some(x=>x.type==='PROVIDER_FAILOVER_REQUIRED')&&e.provider==='http-fallback'&&e.provider_failover_observed===true,
  model_independence:s.models_used===false&&e.models_used===false,
  hard_zero_incremental_cost:s.incremental_cost_usd===0&&e.incremental_cost_usd===0,
  durable_evidence:e.verified===true&&s.evidence_sha256===sha(e),
  terminal_completion:s.provider_events.some(x=>x.type==='MISSION_TERMINAL_COMPLETE'),
  exact_assertions:e.assertions?.length===2&&e.assertions.every(x=>x.matched===true),
  dedupe_marker:d.task_id===s.mission_id&&d.agent_id===s.agent_id&&typeof d.task_sha256==='string'&&d.task_sha256.length===64
};
const all=Object.values(checks).every(Boolean);
const out={schema:'PROJECT_BRAIN_DISTINCT_VERIFICATION_V1',verifier_id:'DETERMINISTIC-VERIFIER-GITHUB-1',worker_agent_id:s.agent_id,mission_id:s.mission_id,criteria_version:c.criteria_version,checks,all_required_checks_pass:all,promotion_claim:false,p_superworker_real_after_adjudication:0,reason:all?'QUALIFICATION_PROPERTIES_PASS__PROMOTION_REQUIRES_CANONICAL_ADJUDICATION':'QUALIFICATION_FAILED',verified_at_utc:now()};
fs.mkdirSync(O.split('/').slice(0,-1).join('/'),{recursive:true});fs.writeFileSync(O,JSON.stringify(out,null,2)+'\n');
console.log(JSON.stringify(out));
if(!all)process.exit(4);