import fs from 'node:fs';
import crypto from 'node:crypto';

const TASK='canonical/tasks/SUPERWORKER_GITHUB_QUALIFICATION_1.json';
const STATE='canonical/superworker_state/SUPERWORKER_GITHUB_1.json';
const EVIDENCE='canonical/superworker_evidence/SUPERWORKER_GITHUB_QUALIFICATION_1.json';
const AGENT='SUPERWORKER-GITHUB-1';
const RUNTIME='SUPERHERO-RUNTIME-2.7-GITHUB-ACTIONS-PERSISTENT';

const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const write=(p,x)=>{fs.mkdirSync(p.split('/').slice(0,-1).join('/'),{recursive:true});fs.writeFileSync(p,JSON.stringify(x,null,2)+'\n')};
const sha=x=>crypto.createHash('sha256').update(typeof x==='string'?x:JSON.stringify(x)).digest('hex');
const now=()=>new Date().toISOString();

async function main(){
  const mode=process.argv[2];
  const task=read(TASK);
  if(mode==='acquire'){
    const consumedPath=`canonical/superworker_consumed/${task.task_id}.json`;
    if(fs.existsSync(consumedPath)){
      const prior=read(consumedPath);
      if(process.env.GITHUB_OUTPUT) fs.appendFileSync(process.env.GITHUB_OUTPUT,'should_continue=false\n');
      console.log(JSON.stringify({ok:true,mode,status:'DUPLICATE_REJECTED',task_id:task.task_id,prior}));
      return;
    }
    if(process.env.GITHUB_OUTPUT) fs.appendFileSync(process.env.GITHUB_OUTPUT,'should_continue=true\n');
    const s={
      schema:'PROJECT_BRAIN_SUPERWORKER_STATE_V1',
      agent_id:AGENT,runtime:RUNTIME,mission_id:task.task_id,status:'CHECKPOINTED_FOR_FRESH_RUN_CONTINUATION',
      generation:1,cycle:1,models_used:false,incremental_cost_usd:0,
      ownership:{owner:AGENT,lease_id:crypto.randomUUID(),acquired_at_utc:now()},
      provider_events:[
        {seq:1,type:'MISSION_ACQUIRED',at_utc:now()},
        {seq:2,type:'PROVIDER_SELECTED',provider:'http-primary',at_utc:now()},
        {seq:3,type:'PROVIDER_FAILOVER_REQUIRED',provider:'http-primary',reason:'INJECTED_PRIMARY_PROVIDER_FAILURE',at_utc:now()}
      ],
      next_action:'FRESH_RUN_FETCH_WITH_HTTP_FALLBACK',
      task_sha256:sha(task),
      checkpointed_at_utc:now()
    };
    write(STATE,s);
    write(consumedPath,{
      schema:'PROJECT_BRAIN_SUPERWORKER_DEDUPE_MARKER_V1',
      task_id:task.task_id,
      task_sha256:sha(task),
      agent_id:AGENT,
      lease_id:s.ownership.lease_id,
      consumed_at_utc:now()
    });
    console.log(JSON.stringify({ok:true,mode,state:STATE,status:s.status,dedupe_marker:consumedPath}));
    return;
  }
  if(mode==='continue'){
    const s=read(STATE);
    if(s.status!=='CHECKPOINTED_FOR_FRESH_RUN_CONTINUATION') throw new Error('BAD_PREVIOUS_STATE:'+s.status);
    const n=task.frontier[0];
    const url=n.metadata.url;
    const r=await fetch(url,{headers:{'user-agent':'ProjectBrain-Superworker-GitHub/2.7'}});
    if(!r.ok) throw new Error('FALLBACK_HTTP_'+r.status);
    const body=await r.text();
    const patterns=n.metadata.assertContains||[];
    const matches=patterns.map(pattern=>({pattern,matched:body.toLowerCase().includes(String(pattern).toLowerCase())}));
    const verified=matches.length>0&&matches.every(x=>x.matched);
    const evidence={
      schema:'PROJECT_BRAIN_SUPERWORKER_EVIDENCE_V1',
      mission_id:task.task_id,agent_id:AGENT,runtime:RUNTIME,
      source_url:r.url,http_status:r.status,provider:'http-fallback',
      provider_failover_observed:true,models_used:false,incremental_cost_usd:0,
      source_body_sha256:sha(body),source_bytes:Buffer.byteLength(body),
      assertions:matches,verified,
      fetched_at_utc:now()
    };
    write(EVIDENCE,evidence);
    s.generation=2;s.cycle=2;s.status=verified?'COMPLETE':'BLOCKED';
    s.provider_events.push({seq:4,type:'FRESH_RUN_CONTINUED',provider:'http-fallback',at_utc:now()});
    s.provider_events.push({seq:5,type:'SOURCE_FETCHED',source_url:r.url,body_sha256:evidence.source_body_sha256,at_utc:now()});
    s.provider_events.push({seq:6,type:verified?'MISSION_TERMINAL_COMPLETE':'MISSION_TERMINAL_BLOCKED',at_utc:now()});
    s.evidence_path=EVIDENCE;s.evidence_sha256=sha(evidence);s.completed_at_utc=now();
    write(STATE,s);
    console.log(JSON.stringify({ok:verified,mode,state:s.status,evidence:EVIDENCE}));
    if(!verified) process.exit(3);
    return;
  }
  throw new Error('UNKNOWN_MODE');
}
main().catch(e=>{console.error(e.stack||String(e));process.exit(2)});