import {
  createMission, selectProvider, beginDispatch, applyProviderResult, appendKernelEvent
} from './kernel.js';

const AGENT_ID = 'SUPERWORKER-PERMANENT-1';
const STATE_NAME = 'project-brain-superworker-permanent-1';
const RUNTIME_ID = 'SUPERHERO-RUNTIME-2.6.0-DIRECT-SIGNED-PERMANENT';
const j=(x,s=200)=>Response.json(x,{status:s,headers:{'cache-control':'no-store'}});
const safe=(x,n=60000)=>String(x??'').slice(0,n);
const now=()=>Date.now();
const enc=new TextEncoder();

function stateStub(env){return env.STATE.getByName(STATE_NAME);}
function b64urlToBytes(s){s=String(s).replace(/-/g,'+').replace(/_/g,'/');while(s.length%4)s+='=';return Uint8Array.from(atob(s),c=>c.charCodeAt(0));}
function bytesToHex(a){return [...new Uint8Array(a)].map(b=>b.toString(16).padStart(2,'0')).join('');}
async function sha256hex(s){const b=typeof s==='string'?enc.encode(s):s;return bytesToHex(await crypto.subtle.digest('SHA-256',b));}
async function verifyTaskSignature(env,task,signature){
  try{
    const jwk=JSON.parse(env.TASK_VERIFY_JWK);
    const key=await crypto.subtle.importKey('jwk',jwk,{name:'ECDSA',namedCurve:'P-256'},false,['verify']);
    return await crypto.subtle.verify({name:'ECDSA',hash:'SHA-256'},key,b64urlToBytes(signature),enc.encode(JSON.stringify(task)));
  }catch{return false;}
}
function validateTask(task){
  if(!task||typeof task!=='object')return 'TASK_REQUIRED';
  if(task.agentId!==AGENT_ID)return 'WRONG_AGENT';
  if(!task.missionId||!task.goal||!Array.isArray(task.frontier))return 'BAD_TASK_SHAPE';
  const issued=Date.parse(task.issuedAt||'');
  const expires=Date.parse(task.expiresAt||'');
  const t=now();
  if(!Number.isFinite(issued)||!Number.isFinite(expires))return 'TIME_BOUND_REQUIRED';
  if(issued>t+5*60_000)return 'ISSUED_IN_FUTURE';
  if(expires<=t)return 'TASK_EXPIRED';
  if(expires-issued>24*60*60_000)return 'TASK_TTL_TOO_LONG';
  return null;
}

function providers(){
  return [
    {id:'http-primary',class:'api',kinds:['retrieve_url'],enabled:true,incrementalCost:0,reliability:.99,latencyMs:100,evidenceQuality:.95,independence:.9,retryable:false},
    {id:'http-fallback',class:'api',kinds:['retrieve_url'],enabled:true,incrementalCost:0,reliability:.90,latencyMs:250,evidenceQuality:.95,independence:.9,retryable:false},
    {id:'assert-text',class:'verification',kinds:['assert_text'],enabled:true,incrementalCost:0,reliability:1,latencyMs:1,evidenceQuality:1,independence:1,retryable:false}
  ];
}
async function dispatch(provider,need,mission){
  if(provider.id==='http-primary'){
    if(need.metadata?.forcePrimaryFailure)return {status:'retry',reason:'INJECTED_PRIMARY_PROVIDER_FAILURE',evidence:{provider:'http-primary',failureInjected:true}};
    return fetchEvidence(need,mission,provider.id);
  }
  if(provider.id==='http-fallback')return fetchEvidence(need,mission,provider.id);
  if(provider.id==='assert-text'){
    const sourceNeedId=String(need.metadata?.sourceNeedId||'');
    const ev=[...mission.evidence].reverse().find(e=>e.needId===sourceNeedId&&e.evidence?.body);
    if(!ev)return {status:'blocked',reason:'ASSERT_SOURCE_EVIDENCE_MISSING'};
    const body=String(ev.evidence.body);
    const patterns=Array.isArray(need.metadata?.contains)?need.metadata.contains.map(String):[];
    const matches=patterns.map(p=>({pattern:p,matched:body.toLowerCase().includes(p.toLowerCase())}));
    const ok=matches.length>0&&matches.every(x=>x.matched);
    return ok?{
      status:'ok',summary:'Required claims found in fetched source text.',
      finalAnswer:JSON.stringify({verified:true,source:ev.evidence.url,matches}),
      evidence:{verified:true,matches,sourceEvidenceSeq:ev.seq}
    }:{status:'blocked',reason:'ASSERTION_NOT_SUPPORTED_BY_SOURCE',evidence:{verified:false,matches,sourceEvidenceSeq:ev.seq}};
  }
  return {status:'blocked',reason:`UNKNOWN_PROVIDER:${provider.id}`};
}
async function fetchEvidence(need,mission,providerId){
  const url=String(need.metadata?.url||need.query||'');
  let u;try{u=new URL(url)}catch{return {status:'blocked',reason:'INVALID_URL'}}
  if(!['https:','http:'].includes(u.protocol))return {status:'blocked',reason:'UNSUPPORTED_SCHEME'};
  try{
    const r=await fetch(u,{headers:{'user-agent':'ProjectBrain-Superworker/2.6'}});
    const body=safe(await r.text());
    if(!r.ok)return {status:'retry',reason:`HTTP_${r.status}`,evidence:{url:r.url,status:r.status,providerId}};
    const newNeeds=[];
    if(Array.isArray(need.metadata?.assertContains))newNeeds.push({id:`assert-${need.id}`,kind:'assert_text',query:`Verify source text for ${mission.goal}`,priority:90,metadata:{sourceNeedId:need.id,contains:need.metadata.assertContains}});
    return {status:'ok',summary:`Fetched ${r.url}`,evidence:{url:r.url,status:r.status,contentType:r.headers.get('content-type'),providerId,body},newNeeds};
  }catch(e){return {status:'retry',reason:`FETCH_ERROR:${String(e).slice(0,240)}`,evidence:{url,providerId}};}
}

export class SuperheroState{
  constructor(ctx,env){this.ctx=ctx;this.env=env;}
  async get(id){return (await this.ctx.storage.get(`mission:${id}`))||null;}
  async put(m){m.updatedAt=now();await this.ctx.storage.put(`mission:${m.missionId}`,m);return m;}
  async createSigned(task,commandHash){
    if(await this.get(task.missionId))throw new Error('MISSION_EXISTS');
    if(await this.ctx.storage.get(`command:${commandHash}`))throw new Error('COMMAND_REPLAY');
    const m=createMission({missionId:task.missionId,goal:task.goal,frontier:task.frontier});
    m.agentId=AGENT_ID;
    m.assignment={owner:AGENT_ID,leaseId:crypto.randomUUID(),leaseAcquiredAt:now(),leaseMode:'DURABLE_OBJECT_SINGLE_OWNER'};
    m.provenance={submittedBy:'DIRECT_SIGNED_COMMAND',runtime:RUNTIME_ID,modelsUsed:false,taskSignatureVerified:true,commandHash};
    m.externalEvents=[{seq:1,ts:now(),type:'MISSION_ACQUIRED',payload:{owner:AGENT_ID,leaseId:m.assignment.leaseId,commandHash}}];
    await this.ctx.storage.put(`command:${commandHash}`,{missionId:task.missionId,acceptedAt:now()});
    await this.put(m);
    await this.ctx.storage.setAlarm(now()+Number(this.env.ALARM_DELAY_MS||5000));
    return m;
  }
  async all(){const x=await this.ctx.storage.list({prefix:'mission:'});return [...x.values()];}
  async alarm(){
    const missions=await this.all();let active=false;
    for(let m of missions){
      const push=(type,payload={})=>{m.externalEvents=Array.isArray(m.externalEvents)?m.externalEvents:[];m.externalEvents.push({seq:m.externalEvents.length+1,ts:now(),type,payload});};
      if(['COMPLETE','FAILED','BLOCKED'].includes(m.status))continue;
      active=true;
      const decision=selectProvider(m,providers());
      if(decision.type==='blocked'){
        m=appendKernelEvent(m,'MISSION_BLOCKED',{reason:decision.reason});m.status='BLOCKED';m.summary=decision.reason;push('MISSION_BLOCKED',{reason:decision.reason});await this.put(m);continue;
      }
      if(decision.type==='idle')continue;
      const started=beginDispatch(m,decision);started.externalEvents=m.externalEvents||[];started.externalEvents.push({seq:started.externalEvents.length+1,ts:now(),type:'PROVIDER_SELECTED',payload:{needId:decision.need.id,providerId:decision.provider.id,score:decision.score}});await this.put(started);
      const result=await dispatch(decision.provider,decision.need,started);
      const next=applyProviderResult(started,decision.need.id,decision.provider,result);next.externalEvents=started.externalEvents||[];next.externalEvents.push({seq:next.externalEvents.length+1,ts:now(),type:'PROVIDER_RESULT',payload:{needId:decision.need.id,providerId:decision.provider.id,status:result.status||'ok',reason:result.reason||null}});
      if(['COMPLETE','FAILED','BLOCKED'].includes(next.status))next.externalEvents.push({seq:next.externalEvents.length+1,ts:now(),type:'MISSION_TERMINAL',payload:{status:next.status,answer:next.answer||null}});
      await this.put(next);
      if(!['COMPLETE','FAILED','BLOCKED'].includes(next.status))active=true;
    }
    if(active)await this.ctx.storage.setAlarm(now()+Math.max(5000,Number(this.env.ALARM_DELAY_MS||5000)));
  }
  async fetch(req){
    const u=new URL(req.url);
    if(u.pathname==='/wake'&&req.method==='POST'){await this.ctx.storage.setAlarm(now()+5000);return j({ok:true,wake:'SCHEDULED'},202);}
    if(u.pathname==='/signed-create'&&req.method==='POST'){
      const {task,commandHash}=await req.json();
      try{return j(await this.createSigned(task,commandHash),202)}catch(e){return j({error:String(e.message||e)},409)}
    }
    const mm=u.pathname.match(/^\/mission\/([^/]+)$/);if(mm){const x=await this.get(mm[1]);return x?j({mission:x,events:x.externalEvents||[]}):j({error:'NOT_FOUND'},404)}
    return j({error:'NOT_FOUND'},404);
  }
}

export default{
  async scheduled(controller,env,ctx){ctx.waitUntil(stateStub(env).fetch(new Request('https://state.internal/wake',{method:'POST'})));},
  async fetch(req,env){
    const u=new URL(req.url),stub=stateStub(env);
    if(req.method==='GET'&&u.pathname==='/health')return j({ok:true,agentId:AGENT_ID,runtime:RUNTIME_ID,kernel:'MODEL_INDEPENDENT',modelsRequired:false,continuation:'DURABLE_OBJECT_ALARM_PLUS_CRON',commandTransport:'DIRECT_ECDSA_SIGNED',persistentControlSecret:false,permanentHost:true,promotionClaim:false});
    if(req.method==='POST'&&u.pathname==='/commands'){
      let wrapper;try{wrapper=await req.json()}catch{return j({error:'BAD_JSON'},400)}
      const task=wrapper?.task,signature=String(wrapper?.signature||'');
      const shapeError=validateTask(task);if(shapeError)return j({error:shapeError},400);
      if(!(await verifyTaskSignature(env,task,signature)))return j({error:'INVALID_SIGNATURE'},401);
      const commandHash=await sha256hex(JSON.stringify({task,signature}));
      return stub.fetch(new Request('https://state.internal/signed-create',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({task,commandHash})}));
    }
    const am=u.pathname.match(/^\/attest\/([^/]+)$/);
    if(req.method==='GET'&&am){
      const rr=await stub.fetch(new Request(`https://state.internal/mission/${encodeURIComponent(am[1])}`));if(!rr.ok)return j({error:'NOT_FOUND'},404);
      const {mission:m}=await rr.json();
      const evidenceHashes=[];for(const e of Array.isArray(m.evidence)?m.evidence:[])evidenceHashes.push(await sha256hex(JSON.stringify(e)));
      const evidenceSummary=(m.evidence||[]).map(e=>({seq:e.seq,needId:e.needId,providerId:e.providerId,providerClass:e.providerClass,url:e.evidence?.url||null,status:e.evidence?.status||null,verified:e.evidence?.verified??null,matches:e.evidence?.matches||null}));
      return j({schema:'PROJECT_BRAIN_SUPERWORKER_PUBLIC_ATTESTATION_V2',agentId:AGENT_ID,runtime:RUNTIME_ID,missionId:m.missionId,status:m.status,generation:m.generation,cycle:m.cycle,owner:m.assignment?.owner||null,leaseIdHash:m.assignment?.leaseId?await sha256hex(m.assignment.leaseId):null,modelsUsed:!!m.provenance?.modelsUsed,taskSignatureVerified:!!m.provenance?.taskSignatureVerified,commandHash:m.provenance?.commandHash||null,evidenceCount:(m.evidence||[]).length,evidenceHashes,evidenceSummary,eventCount:(m.externalEvents||[]).length,lastEventTypes:(m.externalEvents||[]).slice(-12).map(e=>e.type),answer:m.answer||null,missionSha256:await sha256hex(JSON.stringify(m)),promotionClaim:false});
    }
    return j({error:'NOT_FOUND'},404);
  }
};
