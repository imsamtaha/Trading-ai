import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { analyze, parseJournal, run } from '../scripts/atlas_training_accelerator.mjs';

function item(i, { correct = true, confidence = 0.9, paper = true, broker = false } = {}) {
  return { timestamp: new Date(Date.UTC(2026, 9, 8, 0, 0, i)).toISOString(),
    snapshot_id: 'EURUSD:5m:' + i, realized_direction: correct ? 'BUY' : 'SELL',
    opinions: [{ agent: 'technical', decision: 'BUY', confidence },
      { agent: 'confidence', decision: 'BUY', confidence: 0.6 }],
    execution_environment: paper ? 'PAPER' : 'LIVE', broker_execution_allowed: broker };
}
const journal = values => values.map(x => JSON.stringify(x)).join('\n') + '\n';

test('journal sorting, no leakage and duplicate counting', () => {
  const x = item(1), y = item(2);
  const { examples, duplicates } = parseJournal(journal([y, x, x]));
  assert.equal(duplicates, 1);
  assert.deepEqual(examples.map(z => z.snapshot_id), [x.snapshot_id, y.snapshot_id]);
});

test('reject conflicting snapshot outcomes instead of inflating training', () => {
  const a = item(1), b = item(1, { correct: false });
  assert.throws(() => parseJournal(journal([a, b])), /Conflicting outcome/);
});

test('broker execution, live labels, invalid confidence and timestamp are rejected', () => {
  assert.throws(() => parseJournal(journal([item(1, { paper: false })])), /Non-PAPER/);
  assert.throws(() => parseJournal(journal([item(1, { broker: true })])), /Non-PAPER/);
  const bad = item(2); bad.opinions[0].confidence = 12;
  assert.throws(() => parseJournal(journal([bad])), /Invalid agent opinion/);
  const badDate = item(3); badDate.timestamp = '2026-10-08T10:30:00';
  assert.throws(() => parseJournal(journal([badDate])), /timestamp/);
  assert.throws(() => parseJournal('{ "timestamp":NaN }'), /Invalid JSON/);
});

test('requires enough independent settled paper examples', () => {
  assert.throws(() => analyze(journal(Array.from({ length: 29 }, (_, i) => item(i)))), /Not enough/);
});

test('validation gate rejects overfit despite low training Brier', () => {
  const records = Array.from({ length: 60 }, (_, i) =>
    item(i, { correct: i < 36 ? i < 6 : true }));
  const report = analyze(journal(records), {minimumDays: 1, minimumValidation: 6});
  assert.equal(report.examples.train, 36);
  assert.equal(report.examples.validation, 12);
  assert.equal(report.examples.test, 12);
  assert.equal(report.agents.technical.gate, 'SHADOW_REJECTED');
  assert.equal(report.agents.technical.shadow_weight, report.agents.technical.baseline_weight);
  assert.equal(report.broker_execution_allowed, false);
});

test('accepts validated calibration for shadow only, and keeps an untouched test audit', () => {
  const records = Array.from({ length: 60 }, (_, i) =>
    item(i, { correct: i < 36 ? i < 6 : i < 48 ? i < 38 : false }));
  const report = analyze(journal(records), {minimumDays: 1, minimumValidation: 6});
  assert.equal(report.agents.technical.gate, 'SHADOW_ACCEPTED');
  assert.ok(report.agents.technical.brier.validation_improvement > 0.01);
  assert.ok(report.agents.technical.brier.test_shadow !== null);
  assert.equal(report.runtime_profile_modified, false);
  assert.equal(report.examples.unanimous_agent_opinions, 60);
  assert.equal(report.examples.unique, 60);
});

test('writes only research report, does not touch paper live profile or journal', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'atlas-shadow-test-'));
  try {
    const active = path.join(tmp, 'paper');
    const research = path.join(tmp, 'research');
    fs.mkdirSync(active);
    const originalJournal = journal(Array.from({ length: 40 }, (_, i) => item(i, { correct: i % 3 === 0 })));
    fs.writeFileSync(path.join(active, 'atlas_council_training.jsonl'), originalJournal);
    fs.writeFileSync(path.join(active, 'atlas_council_profile.json'), 'DO_NOT_CHANGE');
    const out = run(['--journal', path.join(active, 'atlas_council_training.jsonl'), '--output-dir', research]);
    assert.equal(out.broker_execution_allowed, false);
    assert.equal(fs.readFileSync(path.join(active, 'atlas_council_profile.json'), 'utf8'), 'DO_NOT_CHANGE');
    assert.equal(fs.readFileSync(path.join(active, 'atlas_council_training.jsonl'), 'utf8'), originalJournal);
    const report = JSON.parse(fs.readFileSync(path.join(research, 'latest-report.json'), 'utf8'));
    assert.equal(report.mode, 'OFFLINE_SHADOW_ONLY');
    assert.ok(report.source.sha256.length === 64);
    assert.throws(() => run(['--journal', path.join(active, 'atlas_council_training.jsonl'), '--output-dir', active]),
      /Refusing to write/);
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
});

test('ledger joins enforce entry chronology and purge overlapping outcomes', () => {
  const records = Array.from({ length: 100 }, (_, i) => {
    const x=item(i,{correct:i%2===0});
    x.timestamp=new Date(Date.UTC(2025,0,1,0,0,i*3600+120)).toISOString();
    return x;
  });
  const ledger={closed_trades:records.map((x,i)=>({
    id:String(i),status:'CLOSED',symbol:'EURUSD',direction:'LONG',strategy:'CONTINUATION_5M',
    r_multiple:i%2===0?2:-1,
    opened_at:new Date(Date.UTC(2025,0,1,0,0,i*3600)).toISOString(),
    closed_at:new Date(Date.UTC(2025,0,1,0,0,i*3600+60)).toISOString(),
    training_context:{council:{snapshot_id:x.snapshot_id}}
  }))};
  // This trade is still open when validation begins: its eventual label cannot train.
  ledger.closed_trades[0].closed_at=ledger.closed_trades[65].closed_at;
  records[0].timestamp=ledger.closed_trades[65].closed_at;
  const report=analyze(journal(records),{ledgerRaw:JSON.stringify(ledger)});
  assert.equal(report.data_quality.entry_times_verified,true);
  assert.equal(report.examples.purged_train,1);
  assert.equal(report.examples.train,59);
  assert.equal(report.examples.validation,20);
  assert.equal(report.examples.test,20);
  assert.ok(report.agents.technical.accuracy_interval_95.test.low>=0);
  assert.ok(report.agents.technical.calibration_bins.test.length>0);
  assert.equal(report.automatic_promotion_allowed,false);
});

test('changing test outcomes cannot change fitted or selected weights', () => {
  const records=Array.from({length:100},(_,i)=>item(i,{correct:i%3===0}));
  const config={minimumDays:1,minimumValidation:6};
  const first=analyze(journal(records),config);
  for (const x of records.slice(80)) x.realized_direction=x.realized_direction==='BUY'?'SELL':'BUY';
  const second=analyze(journal(records),config);
  for (const name of Object.keys(first.agents)) {
    assert.equal(first.agents[name].proposed_weight,second.agents[name].proposed_weight);
    assert.equal(first.agents[name].shadow_weight,second.agents[name].shadow_weight);
    assert.equal(first.agents[name].gate,second.agents[name].gate);
  }
});

test('future journal labels and mismatched ledger outcomes are rejected', () => {
  const future=item(1);future.timestamp='2099-01-01T00:00:00Z';
  assert.throws(()=>parseJournal(journal([future])),/future/);
  const records=Array.from({length:40},(_,i)=>item(i));
  const ledger={closed_trades:[]};
  assert.throws(()=>analyze(journal(records),{ledgerRaw:JSON.stringify(ledger)}),/Missing settled ledger/);
});

test('small single-day validation is deferred and never promoted', () => {
  const report=analyze(journal(Array.from({length:60},(_,i)=>item(i,{correct:i%5===0}))));
  assert.equal(report.agents.technical.gate,'SHADOW_DEFERRED_DATA');
  assert.ok(report.agents.technical.deferral_reasons.includes('minimum_days'));
  assert.equal(report.automatic_promotion_allowed,false);
  assert.equal(report.data_quality.entry_times_verified,false);
});

test('nested active output directories are refused and snapshots are immutable', () => {
  const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-v2-'));
  try {
    const active=path.join(tmp,'paper');fs.mkdirSync(active);
    const input=path.join(active,'journal.jsonl');
    fs.writeFileSync(input,journal(Array.from({length:40},(_,i)=>item(i,{correct:i%3===0}))));
    assert.throws(()=>run(['--journal',input,'--output-dir',path.join(active,'nested')]),/Refusing/);
    const output=path.join(tmp,'research');
    const first=run(['--journal',input,'--output-dir',output]);
    const before=fs.readFileSync(first.report,'utf8');
    const second=run(['--journal',input,'--output-dir',output]);
    assert.notEqual(first.report,second.report);
    assert.equal(fs.readFileSync(first.report,'utf8'),before);
    const report=JSON.parse(before);
    assert.equal(report.source.snapshot_journal_sha256,report.source.sha256);
  } finally {fs.rmSync(tmp,{recursive:true,force:true});}
});
