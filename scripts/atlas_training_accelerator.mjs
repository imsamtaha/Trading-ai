// ATLAS Training Accelerator: offline, read-only shadow calibration laboratory.
// Does not import monitor, broker, MT5, or runtime execution modules.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { performance } from 'node:perf_hooks';

const clamp = (x, lo = 0, hi = 1) => Math.min(hi, Math.max(lo, x));
const validDirections = new Set(['BUY', 'SELL', 'HOLD']);
const finiteConfidence = value => typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1;

export function parseJournal(raw) {
  const seen = new Map();
  let duplicates = 0;
  for (const [index, line] of raw.split(/\r?\n/).entries()) {
    if (!line.trim()) continue;
    let item;
    try { item = JSON.parse(line); } catch { throw Error('Invalid JSON at line ' + (index + 1)); }
    if (!item || typeof item !== 'object' || Array.isArray(item)) throw Error('Invalid entry at line ' + (index + 1));
    if (item.execution_environment !== 'PAPER' || item.broker_execution_allowed !== false)
      throw Error('Non-PAPER or broker-enabled entry at line ' + (index + 1));
    if (typeof item.snapshot_id !== 'string' || !item.snapshot_id.trim()) throw Error('Missing snapshot_id at line ' + (index + 1));
    if (!validDirections.has(item.realized_direction)) throw Error('Invalid outcome at line ' + (index + 1));
    if (typeof item.timestamp !== 'string' || !/(Z|[+-]\d\d:\d\d)$/.test(item.timestamp) || !Number.isFinite(Date.parse(item.timestamp)))
      throw Error('Invalid timezone-aware timestamp at line ' + (index + 1));
    if (Date.parse(item.timestamp) > Date.now()) throw Error('Journal timestamp is in the future at line ' + (index + 1));
    if (!Array.isArray(item.opinions) || !item.opinions.length) throw Error('Missing opinions at line ' + (index + 1));
    const agentNames = new Set();
    for (const op of item.opinions) {
      if (!op || typeof op.agent !== 'string' || !op.agent.trim() ||
          !validDirections.has(op.decision) || !finiteConfidence(op.confidence) ||
          agentNames.has(op.agent)) throw Error('Invalid agent opinion at line ' + (index + 1));
      agentNames.add(op.agent);
    }
    const previous = seen.get(item.snapshot_id);
    if (previous) {
      if (previous.realized_direction !== item.realized_direction ||
          JSON.stringify(previous.opinions) !== JSON.stringify(item.opinions))
        throw Error('Conflicting outcome for snapshot_id ' + item.snapshot_id);
      duplicates++;
      continue;
    }
    seen.set(item.snapshot_id, item);
  }
  const examples = Array.from(seen.values()).sort((a, b) =>
    Date.parse(a.timestamp) - Date.parse(b.timestamp) || a.snapshot_id.localeCompare(b.snapshot_id));
  return { examples, duplicates };
}

function rowsForAgent(examples, name) {
  return examples.flatMap(item => item.opinions.filter(op => op.agent === name)
    .map(op => ({ correct: Number(op.decision === item.realized_direction),
      confidence: op.confidence, decision: op.decision, actual: item.realized_direction,
      snapshot_id: item.snapshot_id })));
}
function brier(rows, weight) {
  if (!rows.length) return null;
  return rows.reduce((s, row) => s + (clamp(weight * row.confidence) - row.correct) ** 2, 0) / rows.length;
}
function baseWeight(rows, minimumSamples = 5) {
  if (rows.length < minimumSamples) return 1;
  const correct = rows.reduce((s, x) => s + x.correct, 0);
  const posterior = (correct + 1) / (rows.length + 2);
  const calibration = clamp(1 - brier(rows, 1));
  return clamp(0.5 + 0.7 * posterior + 0.3 * calibration, 0.5, 1.5);
}
function optimizeWeight(rows) {
  let bestWeight = 1;
  let bestLoss = Infinity;
  for (let step = 10; step <= 30; step++) {
    const weight = step / 20;
    const loss = brier(rows, weight);
    if (loss < bestLoss - 1e-12 ||
        (Math.abs(loss - bestLoss) <= 1e-12 && Math.abs(weight - 1) < Math.abs(bestWeight - 1))) {
      bestLoss = loss;
      bestWeight = weight;
    }
  }
  return bestWeight;
}
const round = x => x === null ? null : Number(x.toFixed(5));


function dateMs(value, field) {
  if (typeof value !== 'string' || !/(Z|[+-]\d\d:\d\d)$/.test(value) || !Number.isFinite(Date.parse(value)))
    throw Error('Invalid timezone-aware ' + field);
  return Date.parse(value);
}
export function enrichFromLedger(examples, ledgerRaw) {
  if (ledgerRaw === null) return examples;
  const ledger = typeof ledgerRaw === 'string' ? JSON.parse(ledgerRaw) : ledgerRaw;
  if (!ledger || !Array.isArray(ledger.closed_trades)) throw Error('Invalid settled ledger');
  const bySnapshot = new Map();
  for (const trade of ledger.closed_trades) {
    const intent = trade.training_context?.trade_intent;
    const id = trade.training_context?.council?.snapshot_id || intent?.snapshot_id;
    if (!id) continue;
    if (bySnapshot.has(id)) throw Error('Conflicting settled ledger snapshot ' + id);
    if (trade.status !== 'CLOSED' || trade.broker_execution_allowed === true ||
        intent?.broker_execution_allowed === true ||
        (intent?.execution_environment && intent.execution_environment !== 'PAPER'))
      throw Error('Non-PAPER settled ledger record ' + id);
    const opened = dateMs(trade.opened_at, 'opened_at'), closed = dateMs(trade.closed_at, 'closed_at');
    if (opened > closed || closed > Date.now() || !Number.isFinite(trade.r_multiple))
      throw Error('Invalid settled ledger outcome/time ' + id);
    bySnapshot.set(id, trade);
  }
  return examples.map(example => {
    const trade = bySnapshot.get(example.snapshot_id);
    if (!trade) throw Error('Missing settled ledger snapshot ' + example.snapshot_id);
    if (dateMs(example.timestamp, 'journal timestamp') < dateMs(trade.closed_at, 'closed_at'))
      throw Error('Journal label precedes settlement ' + example.snapshot_id);
    const action = trade.direction === 'LONG' ? 'BUY' : trade.direction === 'SHORT' ? 'SELL' : null;
    if (!action) throw Error('Invalid ledger direction');
    const expected = trade.r_multiple > 0 ? action : trade.r_multiple < 0 ?
      (action === 'BUY' ? 'SELL' : 'BUY') : 'HOLD';
    if (example.realized_direction !== expected) throw Error('Ledger/journal outcome mismatch ' + example.snapshot_id);
    return {...example, opened_at: trade.opened_at, closed_at: trade.closed_at,
      symbol: trade.symbol, strategy: trade.strategy, r_multiple: trade.r_multiple};
  }).sort((a,b) => Date.parse(a.opened_at)-Date.parse(b.opened_at) || a.snapshot_id.localeCompare(b.snapshot_id));
}
function interval95(rows) {
  if (!rows.length) return null;
  const n=rows.length, p=rows.reduce((s,x)=>s+x.correct,0)/n, z=1.959963984540054;
  const denominator=1+z*z/n, center=(p+z*z/(2*n))/denominator;
  const half=z*Math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denominator;
  return {low:round(Math.max(0,center-half)),high:round(Math.min(1,center+half)),
    method:'Wilson; descriptive; overlapping market observations are not independent'};
}
function calibrationBins(rows,weight) {
  const bins=Array.from({length:10},(_,i)=>({lower:i/10,upper:(i+1)/10,samples:0,predicted_sum:0,correct:0}));
  for (const row of rows) {
    const probability=clamp(row.confidence*weight);
    const bin=bins[Math.min(9,Math.floor(probability*10))];
    bin.samples++;bin.predicted_sum+=probability;bin.correct+=row.correct;
  }
  return bins.filter(b=>b.samples).map(b=>({lower:b.lower,upper:b.upper,samples:b.samples,
    mean_confidence:round(b.predicted_sum/b.samples),observed_correct_rate:round(b.correct/b.samples)}));
}
function slices(examples) {
  const result={symbols:{},strategies:{},entry_dates:{}};
  for (const e of examples) {
    for (const [group,key] of [['symbols',e.symbol||'UNKNOWN'],['strategies',e.strategy||'UNKNOWN'],
       ['entry_dates',new Date(Date.parse(e.opened_at||e.timestamp)).toISOString().slice(0,10)]]) {
      const row=result[group][key] ||= {samples:0,sum_paper_r:0};
      row.samples++;
      if (Number.isFinite(e.r_multiple)) row.sum_paper_r+=e.r_multiple;
    }
  }
  return result;
}
function canonicalLocation(value) {
  let existing=path.resolve(value),tail=[];
  while (!fs.existsSync(existing)) {
    const parent=path.dirname(existing);
    if (parent===existing) throw Error('No existing output ancestor');
    tail.unshift(path.basename(existing));existing=parent;
  }
  return path.join(fs.realpathSync(existing),...tail);
}
function within(candidate,base) {
  const relative=path.relative(canonicalLocation(base),canonicalLocation(candidate));
  return relative==='' || (!relative.startsWith('..'+path.sep) && relative!=='..' && !path.isAbsolute(relative));
}

export function analyze(raw, { minExamples = 30, minImprovement = 0.01, minimumDays = 3, minimumValidation = 20, ledgerRaw = null } = {}) {
  if (!Number.isFinite(minImprovement) || minImprovement < 0 || minImprovement > 1)
    throw Error('minImprovement must be between 0 and 1');
  if (!Number.isInteger(minimumDays) || minimumDays < 1 || !Number.isInteger(minimumValidation) || minimumValidation < 1) throw Error('Invalid data sufficiency thresholds');
  const parsed = parseJournal(raw);
  const examples = enrichFromLedger(parsed.examples, ledgerRaw), duplicates = parsed.duplicates;
  if (examples.length < minExamples || examples.length < 30)
    throw Error('Not enough independent settled PAPER samples: minimum ' + Math.max(30, minExamples));
  const trainEnd = Math.floor(examples.length * 0.60);
  const validationEnd = Math.floor(examples.length * 0.80);
  const test = examples.slice(validationEnd);
  const hasEntryTimes = ledgerRaw !== null;
  const unpurgedTrain = examples.slice(0,trainEnd), unpurgedValidation = examples.slice(trainEnd,validationEnd);
  const train = hasEntryTimes ? unpurgedTrain.filter(e=>Date.parse(e.closed_at)<Date.parse(unpurgedValidation[0].opened_at)) : unpurgedTrain;
  const validation = hasEntryTimes ? unpurgedValidation.filter(e=>Date.parse(e.closed_at)<Date.parse(test[0].opened_at)) : unpurgedValidation;
  const days = new Set(examples.map(e=>new Date(Date.parse(e.opened_at||e.timestamp)).toISOString().slice(0,10))).size;
  const agents = Array.from(new Set(train.flatMap(e => e.opinions.map(o => o.agent)))).sort();
  const result = {};
  for (const name of agents) {
    const a = rowsForAgent(train, name);
    const v = rowsForAgent(validation, name);
    const t = rowsForAgent(test, name);
    const baseline = baseWeight(a);
    const candidate = a.length >= 5 ? optimizeWeight(a) : 1;
    const vb = brier(v, baseline);
    const vc = brier(v, candidate);
    const improvement = vb === null || vc === null ? null : vb - vc;
    const reasons = [];
    if (days < minimumDays) reasons.push('minimum_days');
    if (v.length < minimumValidation) reasons.push('minimum_validation_samples');
    if (a.length < 5) reasons.push('minimum_train_samples');
    const accepted = !reasons.length && improvement !== null && improvement >= minImprovement;
    const selected = accepted ? candidate : baseline;
    const hardCases = a.filter(x => !x.correct)
      .sort((x, y) => y.confidence - x.confidence || x.snapshot_id.localeCompare(y.snapshot_id))
      .slice(0, 5).map(x => ({
        snapshot_id: x.snapshot_id, predicted: x.decision, actual: x.actual, confidence: x.confidence
      }));
    result[name] = {
      samples: { train: a.length, validation: v.length, test: t.length },
      accuracy: { train: round(a.reduce((s, x) => s + x.correct, 0) / (a.length || 1)),
        validation: v.length ? round(v.reduce((s, x) => s + x.correct, 0) / v.length) : null,
        test: t.length ? round(t.reduce((s, x) => s + x.correct, 0) / t.length) : null },
      baseline_weight: round(baseline), proposed_weight: round(candidate),
      shadow_weight: round(selected), gate: reasons.length ? 'SHADOW_DEFERRED_DATA' : accepted ? 'SHADOW_ACCEPTED' : 'SHADOW_REJECTED',
      deferral_reasons: reasons,
      accuracy_interval_95: {train: interval95(a), validation: interval95(v), test: interval95(t)},
      calibration_bins: {validation: calibrationBins(v,selected),test:calibrationBins(t,selected)},
      brier: { train_baseline: round(brier(a, baseline)), train_candidate: round(brier(a, candidate)),
        validation_baseline: round(vb), validation_candidate: round(vc),
        validation_improvement: round(improvement),
        test_baseline: round(brier(t, baseline)), test_shadow: round(brier(t, selected)) },
      high_confidence_errors: hardCases
    };
  }
  const unanimous = examples.filter(e => new Set(e.opinions.map(o => o.decision)).size === 1).length;
  return {
    version: 2,
    mode: 'OFFLINE_SHADOW_ONLY',
    automatic_promotion_allowed: false,
    data_quality: {entry_times_verified: hasEntryTimes, unique_entry_days: days, minimum_days: minimumDays,
      minimum_validation_samples: minimumValidation, missing_entry_times_warning: hasEntryTimes ? null : 'Close-time ordering only; overlap purging unavailable'},
    diversity: slices(examples),
    broker_execution_allowed: false,
    runtime_profile_modified: false,
    methodology: 'chronological 60/20/20; purged entry-time splits when ledger supplied; train-only optimization; validation gate; exploratory test audit',
    examples: { unique: examples.length, exact_duplicates_ignored: duplicates,
      train: train.length, validation: validation.length, test: test.length,
      purged_train: unpurgedTrain.length-train.length, purged_validation: unpurgedValidation.length-validation.length,
      unanimous_agent_opinions: unanimous },
    agents: result,
    notice: 'Unique records are not proof of independent samples. Repeated runs reuse historical tests. Replay and weight calibration do not create new market events or improve direction by themselves; paper R excludes broker fees.'
  };
}

function argValue(args, flag, fallback) {
  const idx = args.indexOf(flag);
  if (idx === -1) return fallback;
  if (idx + 1 >= args.length || args[idx + 1].startsWith('--')) throw Error('Missing value for ' + flag);
  return args[idx + 1];
}
export function run(args = process.argv.slice(2)) {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
  const defaultJournal=path.join(root,'.runtime','paper','atlas_council_training.jsonl');
  const journal=path.resolve(argValue(args,'--journal',defaultJournal));
  const defaultLedger=journal===path.resolve(defaultJournal)?path.join(root,'.runtime','paper','atlas_demo_ledger.json'):null;
  const ledgerPath=argValue(args,'--ledger',defaultLedger);
  const outputDir=path.resolve(argValue(args,'--output-dir',path.join(root,'.runtime','research','training-accelerator')));
  const threshold=Number(argValue(args,'--min-improvement','0.01'));
  const minimumDays=Number(argValue(args,'--min-days','3'));
  const minimumValidation=Number(argValue(args,'--min-validation','20'));
  if (!fs.existsSync(journal)) throw Error('Journal does not exist: '+journal);
  const protectedDirs=[path.dirname(journal),path.join(root,'.runtime','paper')];
  if (ledgerPath) protectedDirs.push(path.dirname(path.resolve(ledgerPath)));
  if (protectedDirs.some(base=>within(outputDir,base)))
    throw Error('Refusing to write results into active PAPER runtime directory or descendant');
  const started=performance.now();
  const raw=fs.readFileSync(journal,'utf8');
  const ledgerRaw=ledgerPath?fs.readFileSync(path.resolve(ledgerPath),'utf8'):null;
  const report=analyze(raw,{minImprovement:threshold,minimumDays,minimumValidation,ledgerRaw});
  const sha=crypto.createHash('sha256').update(raw).digest('hex');
  const ledgerSha=ledgerRaw===null?null:crypto.createHash('sha256').update(ledgerRaw).digest('hex');
  fs.mkdirSync(outputDir,{recursive:true});
  const snapshotName='input-'+sha.slice(0,16)+'-'+(ledgerSha||'no-ledger').slice(0,16);
  const snapshotJournal=path.join(outputDir,snapshotName+'.jsonl');
  const snapshotLedger=ledgerRaw===null?null:path.join(outputDir,snapshotName+'-ledger.json');
  function freeze(filename,content) {
    if (!fs.existsSync(filename)) fs.writeFileSync(filename,content,{flag:'wx'});
    else if (fs.readFileSync(filename,'utf8')!==content) throw Error('Snapshot content mismatch');
  }
  freeze(snapshotJournal,raw);
  if (snapshotLedger) freeze(snapshotLedger,ledgerRaw);
  report.source={sha256:sha,ledger_sha256:ledgerSha,journal:path.basename(journal),
    snapshot_journal:path.basename(snapshotJournal),snapshot_journal_sha256:sha,
    snapshot_ledger:snapshotLedger?path.basename(snapshotLedger):null};
  report.replay_duration_ms=round(performance.now()-started);
  report.generated_at=new Date().toISOString();
  report.run_config={minimumDays,minimumValidation,minImprovement:threshold};
  const reportName='report-'+report.generated_at.replace(/[:.]/g,'-')+'-'+crypto.randomUUID()+'.json';
  const archive=path.join(outputDir,reportName);
  const serialized=JSON.stringify(report,null,2)+'\n';
  fs.writeFileSync(archive,serialized,{flag:'wx'});
  const outFile=path.join(outputDir,'latest-report.json'),tmpFile=outFile+'.tmp-'+process.pid;
  try {
    fs.writeFileSync(tmpFile,serialized,{flag:'wx'});
    fs.renameSync(tmpFile,outFile);
  } finally {if(fs.existsSync(tmpFile)) fs.unlinkSync(tmpFile);}
  return {report:archive,latest_report:outFile,examples:report.examples,agents:report.agents,
    replay_duration_ms:report.replay_duration_ms,broker_execution_allowed:false};
}

if (process.argv[1] && fileURLToPath(import.meta.url).toLowerCase() === path.resolve(process.argv[1]).toLowerCase()) {
  try { console.log(JSON.stringify(run())); }
  catch (err) { console.error('TRAINING_ACCELERATOR_ERROR: ' + err.message); process.exitCode = 1; }
}
