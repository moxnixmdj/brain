export const KERNEL_SCHEMA = 'PROJECT_BRAIN_MODEL_INDEPENDENT_KERNEL_V2';

export function createMission({ missionId, goal, frontier = [] }) {
  const needs = frontier.length ? frontier.map(normalizeNeed) : [normalizeNeed({
    id: 'root', kind: 'goal', query: goal, priority: 100
  })];
  return {
    schema: KERNEL_SCHEMA,
    missionId,
    goal,
    status: 'READY',
    generation: 0,
    cycle: 0,
    frontier: needs,
    evidence: [],
    events: [],
    answer: null,
    summary: '',
    updatedAt: Date.now(),
  };
}

export function normalizeNeed(n) {
  return {
    id: String(n.id),
    kind: String(n.kind || 'goal'),
    query: String(n.query || ''),
    priority: Number(n.priority ?? 50),
    status: n.status || 'READY',
    attempts: Array.isArray(n.attempts) ? [...n.attempts] : [],
    metadata: n.metadata && typeof n.metadata === 'object' ? { ...n.metadata } : {},
  };
}

export function providerScore(provider, need) {
  if (!provider.enabled) return -Infinity;
  if (!provider.kinds.includes('*') && !provider.kinds.includes(need.kind)) return -Infinity;
  if (Number(provider.incrementalCost || 0) > 0) return -Infinity;
  const attempted = need.attempts.includes(provider.id);
  if (attempted && !provider.retryable) return -Infinity;
  let score = 1000;
  score += Number(provider.reliability ?? 0.5) * 300;
  score -= Number(provider.latencyMs ?? 1000) / 20;
  score += Number(provider.evidenceQuality ?? 0.5) * 250;
  score += Number(provider.independence ?? 0.5) * 100;
  if (need.kind === 'goal' && ['search','repository','database','documentation','api'].includes(provider.class)) score += 180;
  if (provider.class === 'model') score -= 40;
  if (provider.class === 'invention') score -= 300;
  if (attempted) score -= 250;
  return score;
}

export function selectProvider(mission, providers) {
  const ready = mission.frontier
    .filter(n => n.status === 'READY')
    .sort((a,b) => b.priority - a.priority || a.id.localeCompare(b.id));
  if (!ready.length) return { type: 'idle' };
  const need = ready[0];
  const ranked = providers
    .map(p => ({ provider: p, score: providerScore(p, need) }))
    .filter(x => Number.isFinite(x.score))
    .sort((a,b) => b.score - a.score || a.provider.id.localeCompare(b.provider.id));
  if (!ranked.length) return { type: 'blocked', need, reason: `NO_ZERO_COST_PROVIDER_FOR:${need.kind}` };
  return { type: 'dispatch', need, provider: ranked[0].provider, score: ranked[0].score };
}

export function beginDispatch(mission, decision) {
  if (decision.type !== 'dispatch') return mission;
  const m = clone(mission);
  const n = m.frontier.find(x => x.id === decision.need.id);
  n.status = 'RUNNING';
  n.attempts = [...n.attempts, decision.provider.id];
  m.status = 'RUNNING';
  m.cycle += 1;
  event(m, 'PROVIDER_SELECTED', {
    needId: n.id, needKind: n.kind, providerId: decision.provider.id,
    providerClass: decision.provider.class, score: decision.score
  });
  return touch(m);
}

export function applyProviderResult(mission, needId, provider, result) {
  const m = clone(mission);
  const n = m.frontier.find(x => x.id === needId);
  if (!n) throw new Error('NEED_NOT_FOUND');
  const evidence = result?.evidence ?? null;
  if (evidence !== null) {
    m.evidence.push({
      seq: m.evidence.length + 1,
      needId,
      providerId: provider.id,
      providerClass: provider.class,
      ts: Date.now(),
      evidence,
    });
  }
  if (result?.status === 'retry') {
    n.status = 'READY';
    event(m, 'PROVIDER_RETRY_OR_FAILOVER', { needId, providerId: provider.id, reason: result.reason || 'retry' });
    return touch(m);
  }
  if (result?.status === 'blocked') {
    n.status = 'BLOCKED';
    m.status = 'BLOCKED';
    m.summary = String(result.reason || 'blocked');
    event(m, 'NEED_BLOCKED', { needId, providerId: provider.id, reason: m.summary });
    return touch(m);
  }
  n.status = 'COMPLETE';
  if (Array.isArray(result?.newNeeds)) {
    for (const raw of result.newNeeds) {
      const nn = normalizeNeed(raw);
      if (!m.frontier.some(x => x.id === nn.id)) m.frontier.push(nn);
    }
  }
  if (result?.summary) m.summary = String(result.summary).slice(0, 12000);
  if (result?.finalAnswer != null) {
    m.answer = String(result.finalAnswer);
    m.status = 'COMPLETE';
    event(m, 'MISSION_COMPLETE', { answer: m.answer });
    return touch(m);
  }
  const unresolved = m.frontier.some(x => ['READY','RUNNING'].includes(x.status));
  if (!unresolved) {
    const blocked = m.frontier.some(x => x.status === 'BLOCKED');
    m.status = blocked ? 'BLOCKED' : 'COMPLETE';
    if (!m.answer && !blocked) m.answer = m.summary || 'All frontier needs completed.';
  } else {
    m.status = 'READY';
  }
  event(m, 'PROVIDER_RESULT_ACCEPTED', { needId, providerId: provider.id, newNeeds: result?.newNeeds?.length || 0 });
  return touch(m);
}

export function rollGeneration(mission) {
  const m = clone(mission);
  m.generation += 1;
  if (!['COMPLETE','BLOCKED','FAILED'].includes(m.status)) m.status = 'READY';
  event(m, 'GENERATION_ROLLOVER', { generation: m.generation });
  return touch(m);
}

export function appendKernelEvent(mission, type, payload = {}) {
  const m = clone(mission); event(m, type, payload); return touch(m);
}

function event(m, type, payload) {
  m.events.push({ seq: m.events.length + 1, ts: Date.now(), type, payload });
}
function touch(m) { m.updatedAt = Date.now(); return m; }
function clone(x) { return JSON.parse(JSON.stringify(x)); }
