// Evaluator side only. Run AFTER freezing producer output. See reproduction script.
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const [pred, judgeRoot] = process.argv.slice(2);
const {evaluateExecutionTrajectory, countExpectedCalls} = require(path.resolve(judgeRoot, 'js/utils.js'));
const bytes = fs.readFileSync(pred), data = JSON.parse(bytes);
const rows = data.rows.map(r => {
  const e = JSON.parse(fs.readFileSync(path.join(judgeRoot,'examples',r.suite,'evals.json')))[r.index];
  const should = e.expectedCall || [];
  const trace = r.steps ?? [r];
  const calls = trace.filter(s => s.channel === 'webmcp' && s.executed).map(s=>({
    functionName:s.action.name, args:s.action.args, result:s.output}));
  const steps = evaluateExecutionTrajectory(should,calls);
  const unavailable = r.status==='UNMEASURED' || trace.some(s=>['UNMEASURED','UNCONFIRMED_INVOCATION'].includes(s.status));
  const last = trace.at(-1) ?? {};
  return {suite:r.suite,index:r.index,arm:r.arm,name:e.name??null,expected_required:countExpectedCalls(should),
    status:r.status??last.status,actual:calls.map(c=>c.functionName),changed:last.changed??null,
    matched_steps:unavailable?null:steps.filter(s=>s.outcome==='pass').length,
    graded_steps:unavailable?null:steps.length,
    entire_call_match:unavailable?null:steps.every(s=>s.outcome==='pass'),
    matched_executed_case:unavailable?null:calls.length>0 && steps.every(s=>s.outcome==='pass'),
    goal_verified:r.goal_verified??r.pass??false};
});
console.log(JSON.stringify({kind:'upstream trajectory matcher on independently frozen one-action predictions; not OSWorld',
 upstream:'GoogleChromeLabs/webmcp-tools@f3faa835f3fdeab42e41b055209d6954b192f653',
 input_sha256:crypto.createHash('sha256').update(bytes).digest('hex'),rows},null,2));
