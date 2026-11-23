import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateReport,summarize,filterControls,filtersForPage,prioritySort,escapeHTML,sourceURL,parseWorkspaceImport,reviewProgress,validateReviewNotes,GITHUB_CONTROL_IDS,isLocalWorkspace} from './model.mjs';
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
function realReport() {
  const report=copy();report.mode='github';report.source_commit=null;
  report.target={host:'github.com',repository:'ExampleOrg/service-api',branch:'main',commit:'a'.repeat(40),visibility:'private'};
  report.assessment={kind:'github-repository',control_ids:[...GITHUB_CONTROL_IDS],limitations:['Repository settings only; no SOC 2 opinion.']};
  for(const c of report.controls) {
    c.status=GITHUB_CONTROL_IDS.includes(c.id)?'MISSING':'UNWIRED';
    c.findings=[];c.waiver=null;c.valid_until=null;c.collected_at=null;c.fingerprint=null;c.evidence_id=null;c.evidence_status=null;
    c.source=GITHUB_CONTROL_IDS.includes(c.id)?{sensor:'github-api',query:'Repository settings',payload:'evidence.json'}:null;
    if(c.status==='MISSING'){c.check_scope='Default branch settings';c.scope_reason='API access unavailable';}
  }
  return report;
}
test('real repository reports contain exactly three checks and never borrow fixture passes',()=>{
  const result=validateReport(realReport());
  assert.equal(result.mode,'github');assert.equal(result.summary.wired_count,3);
  assert.equal(result.summary.counts.MISSING,3);assert.equal(result.summary.counts.UNWIRED,34);
  assert.equal(result.summary.clean_ratio,0);assert.equal(result.summary.effective_ratio,0);
  assert.equal(result.source_commit,null);
  const mixed=realReport();mixed.controls.find(c=>c.id==='CTRL-ACCESS-001').status='PASS';
  assert.throws(()=>validateReport(mixed),/mix/);
  const stale=realReport();stale.controls.find(c=>c.id==='CTRL-ACCESS-001').fingerprint='sha256:fixture';
  assert.throws(()=>validateReport(stale),/mix/);
  const mislabeled=realReport();mislabeled.mode='fixture';
  assert.throws(()=>validateReport(mislabeled),/fixture report cannot contain/);
});
test('real target metadata, declared scope, and measured source must agree',()=>{
  for(const mutate of [
    r=>delete r.target,r=>r.target.host='github.example.com',r=>r.target.repository='owner/repo/extra',
    r=>r.target.repository='../secrets',r=>r.target.repository='owner/..',r=>r.target.repository='-owner/repo',
    r=>delete r.target.visibility,r=>r.target.visibility='unknown',r=>delete r.target.branch,
    r=>r.target.branch='',r=>r.target.commit='main',r=>r.source_commit='a'.repeat(40),
    r=>r.assessment.control_ids=['CTRL-CHG-001','CTRL-CHG-001','CTRL-CHG-008'],
    r=>r.assessment.control_ids.push('CTRL-ACCESS-001'),r=>r.assessment.kind='fixture',
    r=>r.assessment.limitations='none',r=>r.controls=r.controls.filter(c=>c.id!=='CTRL-CHG-008'),
    r=>r.controls.find(c=>c.id==='CTRL-CHG-001').status='EXCEPTION',
    r=>r.controls.find(c=>c.id==='CTRL-CHG-001').source.sensor='fixture',
    r=>r.controls.find(c=>c.id==='CTRL-CHG-001').source.payload='fixtures/change/repos.json',
    r=>r.controls.find(c=>c.id==='CTRL-CHG-001').waiver={reason:'Fixture waiver'},
    r=>r.controls.find(c=>c.id==='CTRL-CHG-001').evidence_status='PASS'
  ]) {const r=realReport();mutate(r);assert.throws(()=>validateReport(r));}
  const unavailable=realReport();unavailable.target.branch=null;unavailable.target.commit=null;unavailable.target.visibility=null;
  assert.equal(validateReport(unavailable).summary.counts.MISSING,3);
});
test('real report exports whitelist fields and discard token-shaped provider baggage',()=>{
  const input=realReport();input.access_token='top-secret';input.provider_response={authorization:'Bearer secret'};
  input.target.token='target-secret';input.assessment.credentials='assessment-secret';
  const c=input.controls.find(c=>c.id==='CTRL-CHG-001');c.token='control-secret';c.source.authorization='source-secret';
  const normalized=validateReport(input), serialized=JSON.stringify(normalized);
  for(const baggage of ['top-secret','Bearer secret','target-secret','assessment-secret','control-secret','source-secret'])assert.ok(!serialized.includes(baggage));
  assert.equal(normalized.controls.find(control=>control.id===c.id).check_scope,'Default branch settings');
  assert.equal(normalized.controls.find(control=>control.id===c.id).scope_reason,'API access unavailable');
  assert.notEqual(normalized.controls,input.controls);
  assert.notEqual(normalized.target,input.target);
});
test('hosted import rejects real raw reports and review wrappers before applying data',()=>{
  const raw=realReport(), wrapper={format:'soc2-workspace-review-v1',report:raw,review_notes:{}};
  for(const input of [raw,wrapper]) {
    const before=JSON.stringify(input);
    assert.throws(()=>parseWorkspaceImport(input),/Real repository reports open only in local workspace/);
    assert.equal(JSON.stringify(input),before);
    assert.equal(parseWorkspaceImport(input,{allowReal:true}).report.mode,'github');
  }
  assert.equal(parseWorkspaceImport(copy()).report.mode,'fixture');
});
test('real review roundtrip retains mode, repository scope, and planning without synthetic relabeling',()=>{
  const report=realReport();report.controls.find(c=>c.id==='CTRL-CHG-001').status='PASS';
  const wrapper={format:'soc2-workspace-review-v1',report,review_notes:{'CTRL-CHG-002':{owner:'Engineering',note:'Review required approvals',progress:'In progress'}}};
  const restored=parseWorkspaceImport(JSON.parse(JSON.stringify(wrapper)),{allowReal:true});
  assert.equal(restored.report.mode,'github');assert.equal(restored.report.target.repository,'ExampleOrg/service-api');
  assert.equal(restored.report.summary.counts.PASS,1);assert.equal(restored.report.summary.counts.MISSING,2);
  assert.equal(restored.notes['CTRL-CHG-002'].progress,'In progress');
  assert.equal(restored.report.controls.find(c=>c.id==='CTRL-CHG-002').status,'MISSING');
});
test('local workspace detection allows only HTTP(S) loopback hosts',()=>{
  for(const host of ['127.0.0.1','localhost','::1','[::1]'])for(const protocol of ['http:','https:'])assert.equal(isLocalWorkspace({hostname:host,protocol}),true);
  for(const url of ['http://127.0.0.1:8765/?local=1','https://localhost:8765','http://[::1]:8765'])assert.equal(isLocalWorkspace(url),true);
  for(const url of ['https://safetymp.github.io/SOC-2/','http://localhost.evil.example','http://0.0.0.0','file:///local/report.json','ws://localhost','localhost'])assert.equal(isLocalWorkspace(url),false);
  for(const host of ['127.0.0.2','0.0.0.0','dev.localhost','192.168.1.2'])assert.equal(isLocalWorkspace({hostname:host,protocol:'http:'}),false);
  assert.equal(isLocalWorkspace({hostname:'localhost'}),false);assert.equal(isLocalWorkspace(null),false);
});

test('three-month pilot includes setup, break-even and slower collection', async () => {
  const {pilotHours} = await import('./model.mjs');
  const inputs = {repositories: 8, manualMinutes: 25, collectorMinutes: 10, setupHours: 4};
  assert.deepEqual(pilotHours(inputs), {manual: 10, collector: 8, saved: 2, threshold: 10});
  assert.equal(pilotHours({...inputs, collectorMinutes: 15}).saved, 0);
  assert.equal(pilotHours({...inputs, collectorMinutes: 30}).saved, -6);
  for (const repositories of [0, -1, 0.5, NaN]) assert.equal(pilotHours({...inputs, repositories}), null);
});

test('customer requests and owner actions route all nine initial dispositions without inventing evidence', async () => {
  const {evidenceActions, evidenceDecision} = await import('./model.mjs');
  const cases = ['settings', 'release', 'quarter'];
  const titles = new Set();
  for (const scope of cases) {
    for (const action of Object.keys(evidenceActions)) {
      const result = evidenceDecision(scope, action);
      assert.equal(result.simulated, false);
      assert.match(result.claim, /^At collection, both fixture repositories required two reviews\./);
      assert.ok(result.owner && result.next);
      titles.add(result.title);
    }
  }
  assert.equal(titles.size, 9);
  assert.equal(evidenceDecision('bad','release'), null);
  assert.equal(evidenceDecision('release','bad'), null);
  assert.equal(evidenceDecision('release','release','unknown'), null);
});

test('hypothetical returns preserve gaps, exceptions and the boundaries of individual and sample claims', async () => {
  const {evidenceDecision} = await import('./model.mjs');
  for (const action of ['release','quarter']) {
    assert.match(evidenceDecision(action, action, 'missing').claim, /incomplete/);
    const exception = evidenceDecision(action, action, 'exception');
    assert.equal(exception.title, action === 'quarter' ? 'Request the missing sample evidence' : 'Escalate the observed exception');
    assert.equal(exception.simulated, true);
    assert.equal(exception.owner, 'Change owner');
  }
  assert.equal(evidenceDecision('release','release','matched').title, 'Answer for this release');
  assert.equal(evidenceDecision('quarter','quarter','matched').title, 'Report the sample results');
  assert.match(evidenceDecision('quarter','quarter','matched').claim, /tested sample/);
  assert.equal(evidenceDecision('quarter','release','matched').title, 'One release cannot cover the quarter');
  assert.equal(evidenceDecision('release','quarter','matched').title, 'The named release still needs a trace');
  assert.equal(evidenceDecision('release','snapshot','matched').simulated,false);
});

test('a returned release trace leaves a settings-only handoff with the compliance lead', async () => {
  const {evidenceDecision} = await import('./model.mjs');
  const result = evidenceDecision('settings', 'release', 'matched');
  assert.equal(result.owner, 'Compliance lead');
  assert.equal(result.next, 'Answer the settings question with the dated observation. Ask whether the customer also needs release-specific evidence.');
  assert.equal(result.claim, 'At collection, both fixture repositories required two reviews.');
  assert.match(result.packetFinding, /Lee approved at 09:12 UTC/);
});

test('release packets present the sequence before their conditional interpretation', async () => {
  const {releasePackets, evidenceReturns, evidenceDecision} = await import('./model.mjs');
  assert.deepEqual(Object.values(evidenceReturns.release).slice(1), ['Packet A', 'Packet B', 'Packet C']);
  for (const key of ['matched', 'exception']) {
    const events = releasePackets[key].events;
    const times = events.map(record => record.time);
    assert.deepEqual(times, [...times].sort());
    const merge = events.find(record => record.event.includes('merged'));
    const approvals = events.filter(record => record.event.includes('approved'));
    assert.equal(approvals.length, 2);
    assert.equal(approvals.filter(record => record.time < merge.time).length, key === 'matched' ? 2 : 1);
    assert.match(events.at(-1).event, /REL-204 deployed commit 7c4f9ac/);
  }
  assert.equal(releasePackets.missing.events.length, 1);
  assert.match(releasePackets.missing.events[0].event, /fields are empty/);
  assert.match(evidenceDecision('release','release','missing').claim, /incomplete/);
});

test('quarter packets expose the reconciled population and sample before its interpretation', async () => {
  const {quarterDeployments, quarterPackets, evidenceReturns, evidenceDecision} = await import('./model.mjs');
  assert.deepEqual(Object.values(evidenceReturns.quarter).slice(1), ['Packet D','Packet E','Packet F']);
  for (const key of ['matched','exception']) {
    const packet = quarterPackets[key];
    assert.deepEqual(packet.register, quarterDeployments);
    assert.deepEqual(packet.sample.map(row => row.release), quarterDeployments.filter((_, i) => i % 2 === 0));
    const short = packet.sample.filter(row => new Set(row.approvals).size < 2);
    assert.deepEqual(short.map(row => row.release), key === 'matched' ? [] : ['REL-203']);
    assert.ok(!packet.sample.some(row => row.release === 'REL-204'));
  }
  assert.deepEqual(quarterDeployments.filter(id => !quarterPackets.missing.register.includes(id)), ['REL-204']);
  assert.equal(quarterPackets.missing.sample.length, 0);
  assert.deepEqual(quarterPackets.exception.sample.find(row => row.release === 'REL-203').approvals, ['Patel']);
  const exception = evidenceDecision('quarter','quarter','exception');
  assert.match(exception.claim, /REL-203, the packet documents one of the two required approvals before merge/);
  assert.match(exception.claim, /Whether a second approval occurred before merge is unknown/);
  assert.match(evidenceDecision('release','quarter','matched').title, /named release still needs a trace/);
});

test('technical comparison traces the selected scope and counts distinct premerge identities', async () => {
  const {packetTrace, releasePackets} = await import('./model.mjs');
  assert.match(packetTrace('quarter','missing'),/Unmatched: REL-204/);
  assert.match(packetTrace('quarter','exception'),/REL-203 · 1 distinct/);
  assert.match(packetTrace('release','matched'),/2 distinct reviewers/);
  const repeated = {...releasePackets.exception.events[0], time:'09:15'};
  releasePackets.exception.events.push(repeated);
  try {
    assert.match(packetTrace('release','exception'),/1 distinct reviewer before/);
  } finally {
    releasePackets.exception.events.pop();
  }
});

test('working paper marks distinguish documented deviations from incomplete records', async () => {
  const {reviewWorkpaper} = await import('./model.mjs');
  for (const [scope, packet, expected] of [
    ['release','matched','supported'], ['release','missing','gap'], ['release','exception','exception'],
    ['quarter','matched','supported'], ['quarter','missing','gap'], ['quarter','exception','gap']
  ]) {
    for (const mark of ['supported','gap','exception']) {
      const result = reviewWorkpaper(scope,packet,mark);
      assert.equal(result.accepted, mark === expected);
      assert.ok(result.feedback);
    }
  }
  assert.match(reviewWorkpaper('release','exception','exception').feedback, /09:37.*09:30/);
  assert.match(reviewWorkpaper('quarter','missing','gap').feedback, /REL-204/);
  assert.match(reviewWorkpaper('quarter','exception','gap').feedback, /REL-203/);
  for (const params of [['snapshot','matched','gap'],['release','pending','gap'],['quarter','toString','gap'],['release','matched','']]) {
    assert.equal(reviewWorkpaper(...params), null);
  }
});

test('working paper follows the deployed commit and distinct approvals on its PR before merge', async () => {
  const {reviewWorkpaper, releasePackets} = await import('./model.mjs');
  const packet = releasePackets.matched;
  const events = packet.events;
  try {
    for (const patch of [{pr:61}, {reviewer:'Lee'}, {time:'09:30'}]) {
      packet.events = events.map((row,i) => i===1 ? {...row,...patch} : row);
      assert.equal(reviewWorkpaper('release','matched','gap').accepted,true);
    }
    packet.events = events.map(row => row.kind === 'deploy' ? {...row,commit:'0000000'} : row);
    assert.equal(reviewWorkpaper('release','matched','gap').accepted,true);
  } finally {
    packet.events = events;
  }
});

test('quarter review requires the reconciled inventory and distinct reviewers for every selected release', async () => {
  const {reviewWorkpaper, quarterPackets} = await import('./model.mjs');
  const packet = quarterPackets.matched;
  const {register, sample} = packet;
  try {
    packet.register = [...register.slice(1), register[1]];
    assert.equal(reviewWorkpaper('quarter','matched','gap').accepted,true);
    packet.register = register;
    packet.sample = sample.slice(0,2);
    assert.equal(reviewWorkpaper('quarter','matched','gap').accepted,true);
    packet.sample = sample.map((row,i) => i === 1 ? {...row,approvals:['Lee','Lee']} : row);
    assert.match(reviewWorkpaper('quarter','matched','gap').feedback, /REL-203 has 1 documented/);
  } finally {
    packet.register = register;
    packet.sample = sample;
  }
});

test('customer release reply identifies both named reviewers and their timing relative to merge', async () => {
  const {evidenceDecision} = await import('./model.mjs');
  const onTime = evidenceDecision('release','release','matched');
  const late = evidenceDecision('release','release','exception');
  for (const result of [onTime, late]) {
    assert.match(result.claim, /REL-204.*7c4f9ac.*PR #62.*09:30 UTC/);
    assert.match(result.claim, /Lee approved at 09:12 UTC \(before merge\)/);
  }
  assert.match(onTime.claim, /Chen approved at 09:24 UTC \(before merge\)/);
  assert.match(late.claim, /Chen approved at 09:37 UTC \(after merge\)/);
});

test('customer replies keep an off-scope finding separate and route the original unanswered request', async () => {
  const {evidenceDecision} = await import('./model.mjs');
  for (const returned of ['matched', 'missing', 'exception']) {
    const named = evidenceDecision('release','quarter',returned);
    assert.equal(named.title,'The named release still needs a trace');
    assert.equal(named.owner,'Release owner');
    assert.match(named.claim,/reviewers for REL-204 remain unconfirmed/);
    assert(!named.claim.includes('REL-203'));
    assert.equal(named.packetFinding,evidenceDecision('quarter','quarter',returned).claim);

    const period = evidenceDecision('quarter','release',returned);
    assert.equal(period.owner,'Change owner');
    assert.match(period.claim,/April–June population and sampled approvals still need review/);
    assert.equal(period.packetFinding,evidenceDecision('release','release',returned).claim);
    assert.match(period.next,/quarter’s release population/);

    for (const action of ['release', 'quarter']) {
      const settings = evidenceDecision('settings',action,returned);
      assert.equal(settings.owner,'Compliance lead');
      assert.equal(settings.claim, 'At collection, both fixture repositories required two reviews.');
    }
  }
});
