import {
  createMission, selectProvider, beginDispatch, applyProviderResult, appendKernelEvent
} from './kernel.js';

const AGENT_ID = 'SUPERWORKER-CANDIDATE-Q9';
const STATE_NAME = 'project-brain-superworker-candidate-q9';
const RUNTIME_ID = 'SUPERHERO-RUNTIME-2.5-DO-ALARM-EXTBUS';
const j = (x,s=200)=>Response.json(x,{status:s,headers:{'cache-control':'no-store'}});
const safe=(x,n=60000)=>String(x??'').slice(0,n);
const now=()=>Date.now();
const enc=new TextEncoder();

function auth(req,env){return !!env.CONTROL_TOKEN && req.headers.get('authorization')===`Bearer ${env.CONTROL_TOKEN}`;}
function stateStub(env){return env.STATE.getByName(STATE_NAME);}
function b64urlToBytes(s){s=String(s).replace(/-/g,'+').replace(/_/g,'/');while(s.length%4)s+='=';return Uint8Array.from(atob(s),c=>c.charCodeAt(0));}
function bytesToHex(a){return [...new Uint8Array(a)].map(b=>b.toString(16).padStart(2,'0')).join('');}
function bytesToB64url(a){let s='';for(const b of new Uint8Array(a))s+=String.fromCharCode(b);return btoa(s).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');}
async function sha256hex(s){return bytesToHex(await crypto.subtle.digest('SHA-256',enc.encode(String(s))));}
async function hmacB64url(key,text){const k=await crypto.subtle.importKey('raw',enc.encode(key),{name:'HMAC',hash:'SHA-256'},false,['sign']);return bytesToB64url(await crypto.subtle.sign('HMAC',k,enc.encode(text)));}
async function verifyTaskSignature(env,task,signature){
  try{
    const jwk=JSON.parse(env.TASK_VERIFY_JWK);
    const key=await crypto.subtle.importKey('jwk',jwk,{name:'ECDSA',namedCurve:'P-256'},false,['verify']);
    return await crypto.subtle.verify({name:'ECDSA',hash:'SHA-256'},key,b64urlToBytes(signature),enc.encode(JSON.stringify(task)));
  }catch{return false;}
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
    if(need.metadata?.forcePrimaryFailure){
      return {status:'retry',reason:'INJECTED_PRIMARY_PROVIDER_FAILURE',evidence:{provider:'http-primary',failureInjected:true}};
    }
    return fetchEvidence(need,mission,provider.id);
  }
  if(provider.id==='http-fallback') return fetchEvidence(need,mission,provider.id);
  if(provider.id==='assert-text'){
    const sourceNeedId=String(need.metadata?.sourceNeedId||'');
    const ev=[...mission.evidence].reverse().find(e=>e.needId===sourceNeedId && e.evidence?.body);
    if(!ev) return {status:'blocked',reason:'ASSERT_SOURCE_EVIDENCE_MISSING'};
    const body=String(ev.evidence.body);
    const patterns=Array.isArray(need.metadata?.contains)?need.metadata.contains.map(String):[];
    const matches=patterns.map(p=>({pattern:p,matched:body.toLowerCase().includes(p.toLowerCase())}));
    const ok=matches.length>0 && matches.every(x=>x.matched);
    return ok ? {
      status:'ok',summary:'Required claims found in independently fetched source text.',
      finalAnswer:JSON.stringify({verified:true,source:ev.evidence.url,matches}),
      evidence:{verified:true,matches,sourceEvidenceSeq:ev.seq}
    } : {status:'blocked',reason:'ASSERTION_NOT_SUPPORTED_BY_SOURCE',evidence:{verified:false,matches,sourceEvidenceSeq:ev.seq}};
  }
  return {status:'blocked',reason:`UNKNOWN_PROVIDER:${provider.id}`};
}

async function fetchEvidence(need,mission,providerId){
  const url=String(need.metadata?.url||need.query||'');
  let u;try{u=new URL(url)}catch{return {status:'blocked',reason:'INVALID_URL'}}
  if(!['https:','http:'].includes(u.protocol)) return {status:'blocked',reason:'UNSUPPORTED_SCHEME'};
  try{
    const r=await fetch(u,{headers:{'user-agent':'ProjectBrain-Superworker/2.4'}});
    const body=safe(await r.text());
    if(!r.ok) return {status:'retry',reason:`HTTP_${r.status}`,evidence:{url:r.url,status:r.status,providerId}};
    const newNeeds=[];
    if(Array.isArray(need.metadata?.assertContains)){
      newNeeds.push({id:`assert-${need.id}`,kind:'assert_text',query:`Verify source text for ${mission.goal}`,priority:90,metadata:{sourceNeedId:need.id,contains:need.metadata.assertContains}});
    }
    return {status:'ok',summary:`Fetched ${r.url}`,evidence:{url:r.url,status:r.status,contentType:r.headers.get('content-type'),providerId,body},newNeeds};
  }catch(e){return {status:'retry',reason:`FETCH_ERROR:${String(e).slice(0,240)}`,evidence:{url,providerId}};}
}

async function emitReceipt(env,mission,phase,extra={}){
  if(!env.RECEIPT_URL||!env.RECEIPT_HMAC_KEY)return;
  const snapshot=JSON.stringify(mission);
  const payload={
    schema:'PROJECT_BRAIN_SUPERWORKER_RECEIPT_V1',agentId:AGENT_ID,runtime:RUNTIME_ID,phase,ts:now(),
    missionId:mission.missionId,status:mission.status,generation:mission.generation,cycle:mission.cycle,
    owner:mission.assignment?.owner||null,leaseId:mission.assignment?.leaseId||null,
    modelsUsed:!!mission.provenance?.modelsUsed,evidenceCount:Array.isArray(mission.evidence)?mission.evidence.length:0,
    missionSha256:await sha256hex(snapshot),extra
  };
  const text=JSON.stringify(payload);
  const signature=await hmacB64url(env.RECEIPT_HMAC_KEY,text);
  try{await fetch(env.RECEIPT_URL,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({payload,signature})});}catch{}
}

async function pollCommands(env,ctx){
  if(!env.COMMAND_REQUESTS_URL)return 0;
  let data;try{const r=await fetch(env.COMMAND_REQUESTS_URL,{headers:{accept:'application/json'}});if(!r.ok)return 0;data=await r.json();}catch{return 0;}
  const seen=new Set((await ctx.storage.get('processedCommandIds'))||[]);
  let accepted=0;
  for(const req of Array.isArray(data?.data)?data.data:[]){
    const id=String(req.uuid||'');if(!id||seen.has(id))continue;
    seen.add(id);
    try{
      const wrapper=JSON.parse(String(req.content||''));
      const task=wrapper.task,signature=String(wrapper.signature||'');
      if(!task||!(await verifyTaskSignature(env,task,signature)))continue;
      if(task.agentId!==AGENT_ID||!task.missionId||!task.goal||!Array.isArray(task.frontier))continue;
      if(!(await ctx.storage.get(`mission:${task.missionId}`))){
        const m=createMission({missionId:task.missionId,goal:task.goal,frontier:task.frontier});
        m.agentId=AGENT_ID;
        m.assignment={owner:AGENT_ID,leaseId:crypto.randomUUID(),leaseAcquiredAt:now(),leaseMode:'DURABLE_OBJECT_SINGLE_OWNER',commandRequestId:id};
        m.provenance={submittedBy:'SIGNED_EXTERNAL_COMMAND_QUEUE',runtime:RUNTIME_ID,modelsUsed:false,taskSignatureVerified:true};
        m.externalEvents=[{seq:1,ts:now(),type:'MISSION_ACQUIRED',payload:{owner:AGENT_ID,leaseId:m.assignment.leaseId,commandRequestId:id}}];
        m.updatedAt=now();await ctx.storage.put(`mission:${m.missionId}`,m);accepted++;await emitReceipt(env,m,'MISSION_ACQUIRED_FROM_SIGNED_QUEUE',{commandRequestId:id});
      }
    }catch{}
  }
  await ctx.storage.put('processedCommandIds',[...seen].slice(-500));
  return accepted;
}

export class SuperheroState {
  constructor(ctx,env){this.ctx=ctx;this.env=env;}
  async get(id){return (await this.ctx.storage.get(`mission:${id}`))||null;}
  async put(m){m.updatedAt=now();await this.ctx.storage.put(`mission:${m.missionId}`,m);return m;}
  async create(spec,source='PROJECT_BRAIN_CONTROL_PLANE'){
    if(await this.get(spec.missionId))throw new Error('MISSION_EXISTS');
    const m=createMission({missionId:spec.missionId,goal:spec.goal,frontier:spec.frontier});
    m.agentId=AGENT_ID;m.assignment={owner:AGENT_ID,leaseId:crypto.randomUUID(),leaseAcquiredAt:now(),leaseMode:'DURABLE_OBJECT_SINGLE_OWNER'};
    m.provenance={submittedBy:source,runtime:RUNTIME_ID,modelsUsed:false};
    m.externalEvents=[{seq:1,ts:now(),type:'MISSION_ACQUIRED',payload:{owner:AGENT_ID,leaseId:m.assignment.leaseId}}];
    await this.put(m);await emitReceipt(this.env,m,'MISSION_CREATED');await this.ctx.storage.setAlarm(now()+Number(this.env.ALARM_DELAY_MS||3000));return m;
  }
  async all(){const x=await this.ctx.storage.list({prefix:'mission:'});return [...x.values()];}
  async alarm(){
    await pollCommands(this.env,this.ctx);
    const missions=await this.all();let active=false;
    for(let m of missions){
      const push=(type,payload={})=>{m.externalEvents=Array.isArray(m.externalEvents)?m.externalEvents:[];m.externalEvents.push({seq:m.externalEvents.length+1,ts:now(),type,payload});};
      if(['COMPLETE','FAILED','BLOCKED'].includes(m.status)){await emitReceipt(this.env,m,'TERMINAL_HEARTBEAT');continue;}
      active=true;
      const decision=selectProvider(m,providers());
      if(decision.type==='blocked'){
        m=appendKernelEvent(m,'MISSION_BLOCKED',{reason:decision.reason});m.status='BLOCKED';m.summary=decision.reason;push('MISSION_BLOCKED',{reason:decision.reason});await this.put(m);await emitReceipt(this.env,m,'MISSION_BLOCKED');continue;
      }
      if(decision.type==='idle'){await emitReceipt(this.env,m,'MISSION_IDLE');continue;}
      const started=beginDispatch(m,decision);started.externalEvents=m.externalEvents||[];started.externalEvents.push({seq:started.externalEvents.length+1,ts:now(),type:'PROVIDER_SELECTED',payload:{needId:decision.need.id,providerId:decision.provider.id,score:decision.score}});await this.put(started);
      const result=await dispatch(decision.provider,decision.need,started);
      const next=applyProviderResult(started,decision.need.id,decision.provider,result);next.externalEvents=started.externalEvents||[];next.externalEvents.push({seq:next.externalEvents.length+1,ts:now(),type:'PROVIDER_RESULT',payload:{needId:decision.need.id,providerId:decision.provider.id,status:result.status||'ok',reason:result.reason||null}});
      if(['COMPLETE','FAILED','BLOCKED'].includes(next.status))next.externalEvents.push({seq:next.externalEvents.length+1,ts:now(),type:'MISSION_TERMINAL',payload:{status:next.status,answer:next.answer||null}});
      await this.put(next);await emitReceipt(this.env,next,['COMPLETE','FAILED','BLOCKED'].includes(next.status)?'MISSION_TERMINAL':'MISSION_PROGRESS');
      if(!['COMPLETE','FAILED','BLOCKED'].includes(next.status))active=true;
    }
    const delay=active?Number(this.env.ALARM_DELAY_MS||5000):Number(this.env.IDLE_POLL_MS||60000);
    await this.ctx.storage.setAlarm(now()+Math.max(5000,delay));
  }
  async fetch(req){
    const u=new URL(req.url);
    if(u.pathname==='/wake'&&req.method==='POST'){await this.ctx.storage.setAlarm(now()+5000);return j({ok:true,wake:'SCHEDULED'},202);}
    if(u.pathname==='/create'&&req.method==='POST'){const spec=await req.json();try{return j(await this.create(spec),202)}catch(e){return j({error:String(e.message||e)},409)}}
    const mm=u.pathname.match(/^\/mission\/([^/]+)$/);if(mm){const x=await this.get(mm[1]);return x?j({mission:x,events:x.externalEvents||[]}):j({error:'NOT_FOUND'},404)}
    return j({error:'NOT_FOUND'},404);
  }
}

export default {async fetch(req,env){
  const u=new URL(req.url);
  const stub=stateStub(env);
  if(req.method==='GET'&&u.pathname==='/health'){await stub.fetch(new Request('https://state.internal/wake',{method:'POST'}));return j({ok:true,agentId:AGENT_ID,runtime:RUNTIME_ID,kernel:'MODEL_INDEPENDENT',modelsRequired:false,continuation:'DURABLE_OBJECT_ALARM',externalCommandQueue:true,externalReceiptQueue:true,idlePolling:'PERSISTENT_60S',wakeOnHealth:true,promotionClaim:false});}
  const am=u.pathname.match(/^\/attest\/([^/]+)$/);
  if(req.method==='GET'&&am){
    const rr=await stub.fetch(new Request(`https://state.internal/mission/${encodeURIComponent(am[1])}`));
    if(!rr.ok)return j({error:'NOT_FOUND'},404);
    const data=await rr.json(),m=data.mission;
    const leaseIdHash=m.assignment?.leaseId?await sha256hex(m.assignment.leaseId):null;
    const evidenceHashes=[];
    for(const e of Array.isArray(m.evidence)?m.evidence:[])evidenceHashes.push(await sha256hex(JSON.stringify(e)));
    return j({schema:'PROJECT_BRAIN_SUPERWORKER_PUBLIC_ATTESTATION_V1',agentId:AGENT_ID,runtime:RUNTIME_ID,missionId:m.missionId,status:m.status,generation:m.generation,cycle:m.cycle,owner:m.assignment?.owner||null,leaseIdHash,modelsUsed:!!m.provenance?.modelsUsed,taskSignatureVerified:!!m.provenance?.taskSignatureVerified,evidenceCount:Array.isArray(m.evidence)?m.evidence.length:0,evidenceHashes,eventCount:Array.isArray(m.externalEvents)?m.externalEvents.length:0,lastEventTypes:(m.externalEvents||[]).slice(-8).map(e=>e.type),missionSha256:await sha256hex(JSON.stringify(m)),promotionClaim:false});
  }
  if(!auth(req,env))return j({error:'UNAUTHORIZED'},401);
  if(req.method==='POST'&&u.pathname==='/missions'){
    const b=await req.json();const missionId=String(b.missionId||crypto.randomUUID()),goal=String(b.goal||'').trim();if(!goal)return j({error:'GOAL_REQUIRED'},400);
    return stub.fetch(new Request('https://state.internal/create',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({missionId,goal,frontier:Array.isArray(b.frontier)?b.frontier:[]})}));
  }
  const mm=u.pathname.match(/^\/missions\/([^/]+)$/);if(req.method==='GET'&&mm)return stub.fetch(new Request(`https://state.internal/mission/${encodeURIComponent(mm[1])}`));
  return j({agentId:AGENT_ID,endpoints:{health:'GET /health',create:'POST /missions',mission:'GET /missions/:id'}});
}};