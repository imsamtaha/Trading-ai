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

export function analyze(raw, { minExamples = 30, minImprovement = 0.01 } = {}) {
  if (!Number.isFinite(minImprovement) || minImprovement < 0 || minImprovement > 1)
    throw Error('minImprovement must be between 0 and 1');
  const { examples, duplicates } = parseJournal(raw);
  if (examples.length < minExamples || examples.length < 30)
    throw Error('Not enough independent settled PAPER samples: minimum ' + Math.max(30, minExamples));
  const trainEnd = Math.floor(examples.length * 0.60);
  const validationEnd = Math.floor(examples.length * 0.80);
  const train = examples.slice(0, trainEnd);
  const validation = examples.slice(trainEnd, validationEnd);
  const test = examples.slice(validationEnd);
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
    const accepted = v.length >= 6 && improvement !== null && improvement >= minImprovement && a.length >= 5;
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
      shadow_weight: round(selected), gate: accepted ? 'SHADOW_ACCEPTED' : 'SHADOW_REJECTED',
      brier: { train_baseline: round(brier(a, baseline)), train_candidate: round(brier(a, candidate)),
        validation_baseline: round(vb), validation_candidate: round(vc),
        validation_improvement: round(improvement),
        test_baseline: round(brier(t, baseline)), test_shadow: round(brier(t, selected)) },
      high_confidence_errors: hardCases
    };
  }
  const unanimous = examples.filter(e => new Set(e.opinions.map(o => o.decision)).size === 1).length;
  return {
    mode: 'OFFLINE_SHADOW_ONLY',
    broker_execution_allowed: false,
    runtime_profile_modified: false,
    methodology: 'chronological 60/20/20; optimize on train only; validate before shadow acceptance; untouched test for audit',
    examples: { unique: examples.length, exact_duplicates_ignored: duplicates,
      train: train.length, validation: validation.length, test: test.length,
      unanimous_agent_opinions: unanimous },
    agents: result,
    notice: 'No new labeled market events were generated; replay and recalibration do not improve directional accuracy by themselves.'
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
  const journal = path.resolve(argValue(args, '--journal', path.join(root, '.runtime', 'paper', 'atlas_council_training.jsonl')));
  const outputDir = path.resolve(argValue(args, '--output-dir', path.join(root, '.runtime', 'research', 'training-accelerator')));
  const threshold = Number(argValue(args, '--min-improvement', '0.01'));
  if (!fs.existsSync(journal)) throw Error('Journal does not exist: ' + journal);
  if (path.resolve(outputDir) === path.dirname(journal) ||
      path.resolve(outputDir) === path.dirname(path.join(root, '.runtime', 'paper', 'atlas_council_profile.json')))
    throw Error('Refusing to write results into active PAPER runtime directory');
  const started = performance.now();
  const raw = fs.readFileSync(journal, 'utf8');
  const report = analyze(raw, { minImprovement: threshold });
  report.source = { sha256: crypto.createHash('sha256').update(raw).digest('hex'),
    journal: path.basename(journal) };
  report.replay_duration_ms = round(performance.now() - started);
  report.generated_at = new Date().toISOString();
  fs.mkdirSync(outputDir, { recursive: true });
  const outFile = path.join(outputDir, 'latest-report.json');
  const tmpFile = outFile + '.tmp-' + process.pid;
  try {
    fs.writeFileSync(tmpFile, JSON.stringify(report, null, 2) + '\n', { flag: 'wx' });
    fs.renameSync(tmpFile, outFile);
  } finally {
    if (fs.existsSync(tmpFile)) fs.unlinkSync(tmpFile);
  }
  return { report: outFile, examples: report.examples, agents: report.agents,
    replay_duration_ms: report.replay_duration_ms, broker_execution_allowed: false };
}

if (process.argv[1] && fileURLToPath(import.meta.url).toLowerCase() === path.resolve(process.argv[1]).toLowerCase()) {
  try { console.log(JSON.stringify(run())); }
  catch (err) { console.error('TRAINING_ACCELERATOR_ERROR: ' + err.message); process.exitCode = 1; }
}
