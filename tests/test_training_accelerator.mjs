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
  const report = analyze(journal(records));
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
  const report = analyze(journal(records));
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
