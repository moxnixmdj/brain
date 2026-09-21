import {
  createMission, selectProvider, beginDispatch, applyProviderResult, appendKernelEvent
} from './kernel.js';

const AGENT_ID = 'SUPERWORKER-CANDIDATE-1';
const STATE_NAME = 'project-brain-superworker-candidate-1';
const j = (x,s=200)=>Response.json(x,{status:s,headers:{'cache-control':'no-store'}});
const safe=(x,n=60000)=>String(x??'').slice(0,n);
const now=()=>Date.now();

function auth(req,env){return !!env.CONTROL_TOKEN && req.headers.get('authorization')===`Bearer ${env.CONTROL_TOKEN}`;}
function stateStub(env){return env.STATE.getByName(STATE_NAME);}

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
      status:'ok',
      summary:'Required claims found in independently fetched source text.',
      finalAnswer:JSON.stringify({verified:true,source:ev.evidence.url,matches}),
      evidence:{verified:true,matches,sourceEvidenceSeq:ev.seq}
    } : {
      status:'blocked',
      reason:'ASSERTION_NOT_SUPPORTED_BY_SOURCE',
      evidence:{verified:false,matches,sourceEvidenceSeq:ev.seq}
    };
  }
  return {status:'blocked',reason:`UNKNOWN_PROVIDER:${provider.id}`};
}

async function fetchEvidence(need,mission,providerId){
  const url=String(need.metadata?.url||need.query||'');
  let u; try{u=new URL(url)}catch{return {status:'blocked',reason:'INVALID_URL'}}
  if(!['https:','http:'].includes(u.protocol)) return {status:'blocked',reason:'UNSUPPORTED_SCHEME'};
  try{
    const r=await fetch(u,{headers:{'user-agent':'ProjectBrain-Superworker/2.3'}});
    const body=safe(await r.text());
    if(!r.ok) return {status:'retry',reason:`HTTP_${r.status}`,evidence:{url:r.url,status:r.status,providerId}};
    const newNeeds=[];
    if(Array.isArray(need.metadata?.assertContains)){
      newNeeds.push({id:`assert-${need.id}`,kind:'assert_text',query:`Verify source text for ${mission.goal}`,priority:90,metadata:{sourceNeedId:need.id,contains:need.metadata.assertContains}});
    }
    return {status:'ok',summary:`Fetched ${r.url}`,evidence:{url:r.url,status:r.status,contentType:r.headers.get('content-type'),providerId,body},newNeeds};
  }catch(e){return {status:'retry',reason:`FETCH_ERROR:${String(e).slice(0,240)}`,evidence:{url,providerId}};}
}

export class SuperheroState {
  constructor(ctx,env){this.ctx=ctx;this.env=env;ctx.storage.sql.exec(`
    CREATE TABLE IF NOT EXISTS missions(mission_id TEXT PRIMARY KEY, mission_json TEXT NOT NULL, updated_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, mission_id TEXT NOT NULL, ts INTEGER NOT NULL, type TEXT NOT NULL, payload_json TEXT NOT NULL);
  `);}
  get(id){const r=this.ctx.storage.sql.exec('SELECT mission_json FROM missions WHERE mission_id=?',id).toArray();return r.length?JSON.parse(String(r[0].mission_json)):null;}
  put(m){m.updatedAt=now();this.ctx.storage.sql.exec('INSERT OR REPLACE INTO missions(mission_id,mission_json,updated_at) VALUES(?,?,?)',m.missionId,JSON.stringify(m),m.updatedAt);return m;}
  event(id,type,payload={}){this.ctx.storage.sql.exec('INSERT INTO events(mission_id,ts,type,payload_json) VALUES(?,?,?,?)',id,now(),type,JSON.stringify(payload));}
  events(id){return this.ctx.storage.sql.exec('SELECT seq,ts,type,payload_json FROM events WHERE mission_id=? ORDER BY seq',id).toArray();}
  async create(spec){
    if(this.get(spec.missionId)) throw new Error('MISSION_EXISTS');
    const m=createMission({missionId:spec.missionId,goal:spec.goal,frontier:spec.frontier});
    m.agentId=AGENT_ID;
    m.assignment={owner:AGENT_ID,leaseId:crypto.randomUUID(),leaseAcquiredAt:now(),leaseMode:'DURABLE_OBJECT_SINGLE_OWNER'};
    m.provenance={submittedBy:'PROJECT_BRAIN_CONTROL_PLANE',runtime:'SUPERHERO-RUNTIME-2.3-DO-ALARM',modelsUsed:false};
    this.put(m);this.event(m.missionId,'MISSION_ACQUIRED',{owner:AGENT_ID,leaseId:m.assignment.leaseId});
    await this.ctx.storage.setAlarm(Date.now()+Number(this.env.ALARM_DELAY_MS||1200));
    return m;
  }
  async alarm(){
    const rows=this.ctx.storage.sql.exec("SELECT mission_json FROM missions ORDER BY updated_at LIMIT 20").toArray();
    let reschedule=false;
    for(const row of rows){
      let m=JSON.parse(String(row.mission_json));
      if(['COMPLETE','FAILED','BLOCKED'].includes(m.status)) continue;
      const decision=selectProvider(m,providers());
      if(decision.type==='blocked'){
        m=appendKernelEvent(m,'MISSION_BLOCKED',{reason:decision.reason});m.status='BLOCKED';m.summary=decision.reason;this.put(m);this.event(m.missionId,'MISSION_BLOCKED',{reason:decision.reason});continue;
      }
      if(decision.type==='idle') continue;
      const started=beginDispatch(m,decision);this.put(started);this.event(m.missionId,'PROVIDER_SELECTED',{needId:decision.need.id,providerId:decision.provider.id,score:decision.score});
      const result=await dispatch(decision.provider,decision.need,started);
      const next=applyProviderResult(started,decision.need.id,decision.provider,result);this.put(next);this.event(m.missionId,'PROVIDER_RESULT',{needId:decision.need.id,providerId:decision.provider.id,status:result.status||'ok',reason:result.reason||null});
      if(!['COMPLETE','FAILED','BLOCKED'].includes(next.status)) reschedule=true;
      else this.event(m.missionId,'MISSION_TERMINAL',{status:next.status,answer:next.answer||null});
    }
    if(reschedule) await this.ctx.storage.setAlarm(Date.now()+Number(this.env.ALARM_DELAY_MS||1200));
  }
  async fetch(req){
    const u=new URL(req.url);
    if(u.pathname==='/create'&&req.method==='POST'){
      const spec=await req.json();try{return j(await this.create(spec),202)}catch(e){return j({error:String(e.message||e)},409)}
    }
    const m=u.pathname.match(/^\/mission\/([^/]+)$/);if(m){const x=this.get(m[1]);return x?j({mission:x,events:this.events(m[1])}):j({error:'NOT_FOUND'},404)}
    return j({error:'NOT_FOUND'},404);
  }
}

export default {async fetch(req,env){
  const u=new URL(req.url);
  if(req.method==='GET'&&u.pathname==='/health') return j({ok:true,agentId:AGENT_ID,runtime:'SUPERHERO-RUNTIME-2.3-DO-ALARM',kernel:'MODEL_INDEPENDENT',modelsRequired:false,continuation:'DURABLE_OBJECT_ALARM',promotionClaim:false});
  if(!auth(req,env)) return j({error:'UNAUTHORIZED'},401);
  const stub=stateStub(env);
  if(req.method==='POST'&&u.pathname==='/missions'){
    const b=await req.json();
    const missionId=String(b.missionId||crypto.randomUUID());const goal=String(b.goal||'').trim();
    if(!goal) return j({error:'GOAL_REQUIRED'},400);
    return stub.fetch(new Request('https://state.internal/create',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({missionId,goal,frontier:Array.isArray(b.frontier)?b.frontier:[]})}));
  }
  const mm=u.pathname.match(/^\/missions\/([^/]+)$/);if(req.method==='GET'&&mm)return stub.fetch(new Request(`https://state.internal/mission/${encodeURIComponent(mm[1])}`));
  return j({agentId:AGENT_ID,endpoints:{health:'GET /health',create:'POST /missions',mission:'GET /missions/:id'}});
}};
