import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateReport,summarize,filterControls,filtersForPage,prioritySort,escapeHTML,sourceURL,parseWorkspaceImport,reviewProgress,validateReviewNotes} from './model.mjs';
const sample=JSON.parse(readFileSync(new URL('./data/sample-report.json',import.meta.url)));
const copy=()=>structuredClone(sample);
test('sample agrees with engine and keeps unwired controls outside score',()=>{
  const r=validateReport(copy());
  assert.equal(r.summary.catalog_count,37);assert.equal(r.summary.wired_count,20);
  assert.equal(r.summary.counts.PASS,9);assert.equal(r.summary.counts.FAIL,2);assert.equal(r.summary.counts.MISSING,9);
  assert.equal(r.summary.clean_ratio,.46);assert.equal(r.summary.effective_ratio,.46);
  const altered=copy();altered.summary.clean_ratio=1;
  assert.equal(validateReport(altered).summary.clean_ratio,.46);
});
test('accepted exceptions affect effective score only; missing/expired never pass',()=>{
  const base=sample.controls[0];
  const list=[{...base,status:'PASS',criticality:3},{...base,status:'EXCEPTION',criticality:2},{...base,status:'MISSING',criticality:3},{...base,status:'EXPIRED',criticality:2},{...base,status:'UNWIRED',criticality:3}];
  const s=summarize(list);assert.equal(s.clean_ratio,.3);assert.equal(s.effective_ratio,.5);assert.equal(s.total_weight,10);
  assert.equal(summarize([{...base,status:'UNWIRED'}]).clean_ratio,0);
});
test('invalid status, duplicate IDs, missing fields, nonfinite weights fail closed',()=>{
  for(const mutation of [r=>r.controls[0].status='GREEN',r=>r.controls[0].criticality=NaN,r=>r.controls[0].criticality=0,r=>r.controls[0].findings=null,r=>r.controls[0].source.sensor={},r=>r.controls[0].waiver={reason:[]},r=>r.controls.push({...r.controls[0]}),r=>r.mode='live',r=>r.generated_at='yesterday']){
    const r=copy();mutation(r);assert.throws(()=>validateReport(r));
  }
});
test('search combines status and domain filters and recovers empty results',()=>{
  assert.equal(filterControls(sample.controls,{attention:true}).length,11);
  assert.equal(filterControls(sample.controls,{query:'bob@example.com'}).length,1);
  assert.equal(filterControls(sample.controls,{status:'UNWIRED'}).length,17);
  assert.equal(filterControls(sample.controls,{query:'CC6.6',status:'FAIL'}).length,1);
  assert.equal(filterControls(sample.controls,{query:'does-not-exist'}).length,0);
  assert.equal(filterControls(sample.controls,{query:''}).length,37);
});
test('priority order leads with actual critical failures and does not mutate source',()=>{
  const original=sample.controls.map(c=>c.id);const sorted=prioritySort(sample.controls);
  assert.deepEqual(sorted.slice(0,2).map(c=>c.id),['CTRL-ACCESS-001','CTRL-ACCESS-003']);
  assert.deepEqual(sample.controls.map(c=>c.id),original);
});
test('untrusted text remains text; provenance links reject traversal and unknown origins',()=>{
  assert.equal(escapeHTML('<img src=x onerror="x">'), '&lt;img src=x onerror=&quot;x&quot;&gt;');
  assert.equal(sourceURL(sample.source_commit,'fixtures/access/principals.json'),`https://github.com/SafetyMP/SOC-2/blob/${sample.source_commit}/fixtures/access/principals.json`);
  for(const path of ['javascript:alert(1)','//other.example/x','../secrets','a/../../x'])assert.equal(sourceURL(sample.source_commit,path),null);
  assert.equal(sourceURL('main" onclick="x','fixtures/a.json'),null);
});
test('review annotations cannot alter the measured result',()=>{
  const r=copy();r.review_notes={'CTRL-ACCESS-001':{progress:'Ready for recheck',status:'PASS'}};
  assert.equal(validateReport(r).controls.find(c=>c.id==='CTRL-ACCESS-001').status,'FAIL');
  assert.equal(validateReport(r).summary.clean_ratio,.46);
});
test('coverage navigation cannot hide the action queue with an incompatible filter',()=>{
  const filters=filtersForPage({query:'',status:'UNWIRED',domain:'all'},'attention');
  assert.equal(filters.status,'all');
  assert.equal(filterControls(sample.controls,{...filters,attention:true}).length,11);
});
test('Git-free reports import without links, malformed assessment dates are rejected',()=>{
  const r=copy();r.source_commit=null;assert.equal(validateReport(r).source_commit,null);
  assert.equal(sourceURL(null,'fixtures/access/principals.json'),null);
  for(const date of [{toString:null},'not-a-date',undefined]){r.as_of=date;assert.throws(()=>validateReport(r));}
});
const review=()=>({format:'soc2-workspace-review-v1',report:copy(),review_notes:{'CTRL-ACCESS-001':{
  owner:'Platform team',note:'Replace the sample identity, then rerun.\nKeep the finding.',
  progress:'Ready for recheck',updated_at:'2026-11-14T20:00:00Z'
}}});
test('review export roundtrip preserves planning data without changing measured scores',()=>{
  const original=review(), serialized=JSON.stringify(original);
  const restored=parseWorkspaceImport(JSON.parse(serialized));
  assert.deepEqual(restored.notes['CTRL-ACCESS-001'],original.review_notes['CTRL-ACCESS-001']);
  assert.equal(Object.getPrototypeOf(restored.notes),null);
  assert.deepEqual(restored.report.controls,original.report.controls);
  assert.equal(restored.report.summary.clean_ratio,.46);
  assert.equal(restored.report.controls.find(c=>c.id==='CTRL-ACCESS-001').status,'FAIL');
  restored.notes['CTRL-ACCESS-001'].note='A later browser edit';
  assert.equal(JSON.stringify(original),serialized);
});
test('raw report imports leave existing local notes policy to the caller',()=>{
  const result=parseWorkspaceImport(copy());
  assert.equal(result.notes,null);
  assert.equal(result.report.summary.wired_count,20);
  const empty=review();empty.review_notes={};
  assert.equal(Object.keys(parseWorkspaceImport(empty).notes).length,0);
});
test('invalid review notes and unknown IDs reject the complete import without mutation',()=>{
  for(const mutation of [
    r=>r.review_notes=null,r=>r.review_notes=[],r=>r.review_notes['CTRL-UNKNOWN-999']={},
    r=>r.review_notes['CTRL-ACCESS-001']=null,
    r=>r.review_notes['CTRL-ACCESS-001'].owner='a'.repeat(101),
    r=>r.review_notes['CTRL-ACCESS-001'].note='a'.repeat(3001),
    r=>r.review_notes['CTRL-ACCESS-001'].owner={},
    r=>r.review_notes['CTRL-ACCESS-001'].note=[],
    r=>delete r.review_notes['CTRL-ACCESS-001'].progress,
    r=>r.review_notes['CTRL-ACCESS-001'].progress='PASS',
    r=>r.review_notes['CTRL-ACCESS-001'].updated_at='not-a-date',
    r=>r.review_notes['CTRL-ACCESS-001'].updated_at=null,
    r=>r.format='soc2-workspace-review-v2',
    r=>r.report.controls[0].status='GREEN'
  ]) {
    const input=review();mutation(input);const before=JSON.stringify(input);
    assert.throws(()=>parseWorkspaceImport(input));assert.equal(JSON.stringify(input),before);
  }
});
test('notes accept boundaries and optional timestamps but discard verdict-like extra fields',()=>{
  const input=review(), note=input.review_notes['CTRL-ACCESS-001'];
  note.owner='a'.repeat(100);note.note='b'.repeat(3000);note.status='PASS';delete note.updated_at;
  const result=parseWorkspaceImport(input);
  assert.equal(result.notes['CTRL-ACCESS-001'].owner.length,100);
  assert.equal(result.notes['CTRL-ACCESS-001'].note.length,3000);
  assert.equal(Object.hasOwn(result.notes['CTRL-ACCESS-001'],'status'),false);
  assert.equal(Object.hasOwn(result.notes['CTRL-ACCESS-001'],'updated_at'),false);
  assert.equal(result.report.summary.clean_ratio,.46);
});
test('prototype-shaped notes are rejected and malicious note strings remain escaped text',()=>{
  const input=review();
  input.review_notes=JSON.parse('{"__proto__":{"polluted":true}}');
  assert.throws(()=>parseWorkspaceImport(input));
  input.review_notes={'CTRL-ACCESS-001':JSON.parse('{"owner":"","note":"","progress":"Not started","__proto__":{}}')};
  assert.throws(()=>parseWorkspaceImport(input));
  input.review_notes=Object.create({'CTRL-ACCESS-001':{owner:'',note:'',progress:'Not started'}});
  assert.throws(()=>parseWorkspaceImport(input));
  const malicious=review();malicious.review_notes['CTRL-ACCESS-001'].note='<img src=x onerror="alert(1)">';
  const imported=parseWorkspaceImport(malicious);
  assert.equal(escapeHTML(imported.notes['CTRL-ACCESS-001'].note),'&lt;img src=x onerror=&quot;alert(1)&quot;&gt;');
  assert.equal({}.polluted,undefined);
});
test('review progress uses the existing planning vocabulary with a safe default',()=>{
  for(const progress of ['Not started','In progress','Ready for recheck'])assert.equal(reviewProgress({progress}),progress);
  for(const note of [null,undefined,{},[],{progress:'PASS'},Object.create({progress:'In progress'})])assert.equal(reviewProgress(note),'Not started');
});
test('planning progress filters compose with attention and never change verdicts',()=>{
  const notes={
    'CTRL-ACCESS-001':{owner:'Platform',note:'Assign a reviewer'},
    'CTRL-ACCESS-003':{owner:'Platform',note:'Narrow permissions',progress:'In progress'},
    'CTRL-GOV-001':{owner:'Security',note:'Upload source',progress:'invalid'}
  };
  const active=filterControls(sample.controls,{attention:true,progress:'In progress',notes});
  assert.deepEqual(active.map(c=>c.id),['CTRL-ACCESS-003']);
  assert.equal(active[0].status,'FAIL');
  const pending=filterControls(sample.controls,{attention:true,progress:'Not started',notes});
  assert.equal(pending.length,10);
  assert.ok(pending.some(c=>c.id==='CTRL-ACCESS-001'));
  assert.ok(pending.some(c=>c.id==='CTRL-GOV-001'));
  assert.equal(filterControls(sample.controls,{attention:true,progress:'invalid',notes}).length,0);
  assert.equal(filterControls(sample.controls,{attention:true,progress:'all',notes}).length,11);
  assert.equal(filterControls(sample.controls,{attention:true,progress:'Not started',notes:null}).length,11);
});
test('stored notes use the same sanitization and rejection contract as imported reviews',()=>{
  const input=review(), stored=JSON.parse(JSON.stringify(input.review_notes));
  assert.deepEqual(validateReviewNotes(stored,input.report),parseWorkspaceImport(input).notes);
  stored['CTRL-ACCESS-001'].owner='a'.repeat(101);
  assert.throws(()=>validateReviewNotes(stored,input.report));
  assert.throws(()=>validateReviewNotes({'CTRL-UNKNOWN-999':{}},input.report));
});
