export const STATUSES = ['PASS', 'FAIL', 'MISSING', 'EXPIRED', 'EXCEPTION', 'UNWIRED'];
export const ATTENTION = ['FAIL', 'MISSING', 'EXPIRED'];
export const REVIEW_PROGRESS = ['Not started', 'In progress', 'Ready for recheck'];
export const LABELS = {PASS:'Passing', FAIL:'Needs attention', MISSING:'Missing evidence', EXPIRED:'Expired evidence', EXCEPTION:'Accepted exception', UNWIRED:'Not evaluated'};
export const DOMAINS = {access_control:'Access control',access:'Access control',encryption:'Encryption',network:'Network security',logging:'Audit logging',change_mgmt:'Change management',backup:'Backup & recovery',procedural:'Governance',governance:'Governance',vulnerability_mgmt:'Vulnerability management'};
export function domainLabel(domain) { return DOMAINS[domain] || domain.replaceAll('_',' ').replaceAll('-',' ').replace(/^./, c=>c.toUpperCase()); }
export function escapeHTML(value) { return String(value ?? '').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
export function summarize(controls) {
  const wired = controls.filter(c=>c.status !== 'UNWIRED');
  const weight = list=>list.reduce((sum,c)=>sum+c.criticality,0);
  const total = weight(wired), clean = weight(wired.filter(c=>c.status==='PASS'));
  const effective = weight(wired.filter(c=>['PASS','EXCEPTION'].includes(c.status)));
  return {catalog_count:controls.length,wired_count:wired.length,unwired_count:controls.length-wired.length,counts:Object.fromEntries(STATUSES.map(s=>[s,controls.filter(c=>c.status===s).length])),clean_ratio:total?clean/total:0,effective_ratio:total?effective/total:0,total_weight:total,clean_weight:clean,effective_weight:effective};
}
function text(value, max=20000) { return typeof value==='string' && value.length<=max; }
function textList(value) { return Array.isArray(value) && value.length<=200 && value.every(v=>text(v)); }
export function validateReport(input) {
  if (!input || input.schema_version!==1 || input.mode!=='fixture' || !text(input.title,200) || !text(input.generated_at,100) || !Number.isFinite(Date.parse(input.generated_at)) || !text(input.as_of,100) || !Number.isFinite(Date.parse(input.as_of)) || (input.source_commit!==null && !/^[a-f0-9]{40}$/.test(input.source_commit)) || !Array.isArray(input.controls) || !input.controls.length || input.controls.length>1000) throw new Error('Choose a version 1 fixture report created by export_workspace.py.');
  const ids = new Set();
  for (const c of input.controls) {
    if (!c || !text(c.id,100) || !/^CTRL-[A-Z0-9-]+$/.test(c.id) || ids.has(c.id) || !text(c.title,500) || !text(c.domain,100) || !STATUSES.includes(c.status) || !Number.isInteger(c.criticality) || c.criticality<1 || c.criticality>3 || !textList(c.findings) || !textList(c.soc2) || !textList(c.iso27001) || !text(c.guidance) || !text(c.kind,100)) throw new Error('The report contains an invalid control. No data was imported.');
    if (c.source!=null && (typeof c.source!=='object' || ['sensor','query','payload'].some(k=>c.source[k]!=null && !text(c.source[k])))) throw new Error('The report contains an invalid evidence source.');
    for (const k of ['valid_until','collected_at','fingerprint','owner']) if(c[k]!=null && !text(c[k])) throw new Error('The report contains invalid evidence metadata.');
    if (c.waiver!=null && (typeof c.waiver!=='object' || ['approver','reason','expires'].some(k=>c.waiver[k]!=null && !text(c.waiver[k])))) throw new Error('The report contains invalid exception metadata.');
    if(c.evidence_status!=null && !STATUSES.includes(c.evidence_status)) throw new Error('The report contains an invalid collected verdict.');
    ids.add(c.id);
  }
  // Recompute from measured verdicts; never trust supplied percentages.
  return {...input, summary:summarize(input.controls)};
}
function plainRecord(value) {
  return value!==null && typeof value==='object' && !Array.isArray(value) &&
    [Object.prototype,null].includes(Object.getPrototypeOf(value));
}
export function reviewProgress(note) {
  return plainRecord(note) && Object.hasOwn(note,'progress') && REVIEW_PROGRESS.includes(note.progress)?note.progress:'Not started';
}
export function parseWorkspaceImport(input) {
  if(!plainRecord(input)) throw new Error('Choose a fixture report or an exported workspace review.');
  if(!Object.hasOwn(input,'format')) return {report:validateReport(input),notes:null};
  if(input.format!=='soc2-workspace-review-v1') throw new Error('This workspace review format is not supported.');
  const report=validateReport(input.report);
  return {report,notes:validateReviewNotes(input.review_notes,report)};
}
export function validateReviewNotes(input,report) {
  if(!plainRecord(input)) throw new Error('The review notes must be a control ID map. No data was imported.');
  const ids=new Set(report.controls.map(c=>c.id)), notes=Object.create(null);
  for(const [id,note] of Object.entries(input)) {
    if(!ids.has(id)) throw new Error('A review note refers to a control outside this report. No data was imported.');
    if(!plainRecord(note) || !Object.hasOwn(note,'owner') || !text(note.owner,100) ||
       !Object.hasOwn(note,'note') || !text(note.note,3000) ||
       !Object.hasOwn(note,'progress') || !REVIEW_PROGRESS.includes(note.progress) ||
       ['__proto__','prototype','constructor'].some(key=>Object.hasOwn(note,key)) ||
       (Object.hasOwn(note,'updated_at') && (!text(note.updated_at,100) || !Number.isFinite(Date.parse(note.updated_at))))) {
      throw new Error('The review contains invalid notes. No data was imported.');
    }
    // Copy planning fields only. Imported verdict-like fields cannot enter notes
    // or overwrite the separately validated report, and no input object is mutated.
    notes[id]={owner:note.owner,note:note.note,progress:note.progress};
    if(Object.hasOwn(note,'updated_at')) notes[id].updated_at=note.updated_at;
  }
  return notes;
}
export function filtersForPage(filters,page) { return {...filters,status:page==='attention' && !ATTENTION.includes(filters.status)?'all':filters.status}; }
export function filterControls(controls,{query='',status='all',domain='all',attention=false,progress='all',notes={}}={}) {
  const q=query.trim().toLowerCase();
  return controls.filter(c=>(!attention || ATTENTION.includes(c.status)) && (status==='all'||c.status===status) && (domain==='all'||c.domain===domain) && (progress==='all'||reviewProgress(notes?.[c.id])===progress) && (!q || [c.id,c.title,domainLabel(c.domain),...c.soc2,...c.iso27001,...c.findings].join(' ').toLowerCase().includes(q)));
}
export function prioritySort(controls) { const order={FAIL:0,MISSING:1,EXPIRED:2,EXCEPTION:3,PASS:4,UNWIRED:5}; return [...controls].sort((a,b)=>order[a.status]-order[b.status]||b.criticality-a.criticality||a.id.localeCompare(b.id)); }
export function sourceURL(commit,path) { return /^[a-f0-9]{40}$/.test(commit) && typeof path==='string' && /^[a-zA-Z0-9_./-]+$/.test(path) && !path.split('/').includes('..') && !path.startsWith('/') ? `https://github.com/SafetyMP/SOC-2/blob/${commit}/${path}` : null; }
export function nextAction(c) {
  if(c.status==='UNWIRED') return 'This catalog control has no evaluation in this snapshot. Implement and test its policy and sensor before including it in readiness.';
  if(c.status==='PASS') return 'Keep the evidence current. Recollect and rerun the local assessment after a system change or before the evidence expires.';
  if(c.status==='EXCEPTION') return 'Review the compensating control and exception expiry. An accepted exception contributes to effective readiness, but never to clean readiness.';
  if(c.status==='EXPIRED') return 'Refresh the source evidence and its review date, then rerun the local assessment. An expired result cannot count as passing.';
  if(c.status==='MISSING' && c.kind!=='technical') return 'Provide the non-empty repository document referenced in the procedural manifest, verify its review due date, then rerun. File presence and dates do not verify approval or document quality.';
  if(c.id==='CTRL-ACCESS-001') return 'Enroll the affected human or privileged identity in MFA, refresh the sensor payload, and rerun the assessment to verify the change.';
  if(c.id==='CTRL-ACCESS-003') return 'Replace wildcard actions and resources with scoped permissions. Refresh the sensor payload and rerun; a time-boxed exception is not a clean pass.';
  return 'Inspect the finding and the control guidance below. Correct the source configuration or missing evidence, then collect and evaluate again.';
}
