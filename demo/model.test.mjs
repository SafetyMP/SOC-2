import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateReport,summarize,filterControls,filtersForPage,prioritySort,escapeHTML,sourceURL} from './model.mjs';
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
