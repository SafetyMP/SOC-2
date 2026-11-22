export const STATUSES = ['PASS', 'FAIL', 'MISSING', 'EXPIRED', 'EXCEPTION', 'UNWIRED'];
export const ATTENTION = ['FAIL', 'MISSING', 'EXPIRED'];
export const REVIEW_PROGRESS = ['Not started', 'In progress', 'Ready for recheck'];
export const GITHUB_CONTROL_IDS = ['CTRL-CHG-001', 'CTRL-CHG-002', 'CTRL-CHG-008'];
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
  if (!input || input.schema_version!==1 || !['fixture','github'].includes(input.mode) || !text(input.title,200) || !text(input.generated_at,100) || !Number.isFinite(Date.parse(input.generated_at)) || !text(input.as_of,100) || !Number.isFinite(Date.parse(input.as_of)) || (input.source_commit!==null && !/^[a-f0-9]{40}$/.test(input.source_commit)) || !Array.isArray(input.controls) || !input.controls.length || input.controls.length>1000) throw new Error('Choose a version 1 fixture or local GitHub assessment report.');
  const ids = new Set();
  for (const c of input.controls) {
    if (!c || !text(c.id,100) || !/^CTRL-[A-Z0-9-]+$/.test(c.id) || ids.has(c.id) || !text(c.title,500) || !text(c.domain,100) || !STATUSES.includes(c.status) || !Number.isInteger(c.criticality) || c.criticality<1 || c.criticality>3 || !textList(c.findings) || !textList(c.soc2) || !textList(c.iso27001) || !text(c.guidance) || !text(c.kind,100)) throw new Error('The report contains an invalid control. No data was imported.');
    if (c.source!=null && (typeof c.source!=='object' || ['sensor','query','payload'].some(k=>c.source[k]!=null && !text(c.source[k])))) throw new Error('The report contains an invalid evidence source.');
    for (const k of ['valid_until','collected_at','fingerprint','owner']) if(c[k]!=null && !text(c[k])) throw new Error('The report contains invalid evidence metadata.');
    if (c.waiver!=null && (typeof c.waiver!=='object' || ['approver','reason','expires'].some(k=>c.waiver[k]!=null && !text(c.waiver[k])))) throw new Error('The report contains invalid exception metadata.');
    if(c.evidence_status!=null && !STATUSES.includes(c.evidence_status)) throw new Error('The report contains an invalid collected verdict.');
    ids.add(c.id);
  }
  if(input.mode==='github') return validateGitHubReport(input);
  if(input.target!=null || input.assessment?.kind==='github-repository') throw new Error('A fixture report cannot contain a real repository assessment target.');
  // Recompute from measured verdicts; never trust supplied percentages.
  return {...input, summary:summarize(input.controls)};
}
function plainRecord(value) {
  return value!==null && typeof value==='object' && !Array.isArray(value) &&
    [Object.prototype,null].includes(Object.getPrototypeOf(value));
}
function validateGitHubReport(input) {
  const target=input.target, assessment=input.assessment;
  const repositoryPattern=/^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?\/[A-Za-z0-9_.-]{1,100}$/;
  if(input.source_commit!==null || !plainRecord(target) || target.host!=='github.com' ||
     !text(target.repository,140) || !repositoryPattern.test(target.repository) ||
     ['.','..'].includes(target.repository.split('/')[1]) ||
     !(target.branch===null || (text(target.branch,1000) && target.branch.length>0 && !/[\u0000-\u001f\u007f]/.test(target.branch))) ||
     !(target.commit===null || (text(target.commit,40) && /^[a-f0-9]{40}$/.test(target.commit))) ||
     ![null,'public','private','internal'].includes(target.visibility)) {
    throw new Error('The GitHub report contains an invalid repository target or source reference.');
  }
  if(!plainRecord(assessment) || assessment.kind!=='github-repository' ||
     !Array.isArray(assessment.control_ids) || assessment.control_ids.length!==GITHUB_CONTROL_IDS.length ||
     new Set(assessment.control_ids).size!==GITHUB_CONTROL_IDS.length ||
     !assessment.control_ids.every(id=>GITHUB_CONTROL_IDS.includes(id)) || !textList(assessment.limitations) ||
     (assessment.incomplete!=null && typeof assessment.incomplete!=='boolean')) {
    throw new Error('The GitHub report must declare exactly the three supported repository checks.');
  }
  const assessed=new Set();
  for(const c of input.controls) {
    for(const key of ['evidence_id','check_scope','scope_reason']) if(c[key]!=null && !text(c[key])) throw new Error('The GitHub report contains invalid check metadata.');
    if(c.waiver!==null) throw new Error('GitHub repository reports cannot apply fixture exceptions.');
    if(GITHUB_CONTROL_IDS.includes(c.id)) {
      if(!['PASS','FAIL','MISSING'].includes(c.status) || c.kind!=='technical' ||
         !plainRecord(c.source) || c.source.sensor!=='github-api' || c.source.payload!=='evidence.json' ||
         (c.evidence_status!=null && c.evidence_status!==c.status)) {
        throw new Error('A GitHub repository check contains fixture or unsupported evidence.');
      }
      assessed.add(c.id);
    } else if(c.status!=='UNWIRED' || c.findings.length ||
              ['collected_at','valid_until','fingerprint','evidence_id','evidence_status'].some(key=>c[key]!=null) ||
              (c.source!=null && (!plainRecord(c.source) || ['sensor','query','payload'].some(key=>c.source[key]!=null)))) {
      throw new Error('A GitHub report cannot mix repository checks with fixture-derived results.');
    }
  }
  if(assessed.size!==GITHUB_CONTROL_IDS.length) throw new Error('The GitHub report is missing one or more supported repository checks.');
  if(input.caveats!=null && !textList(input.caveats)) throw new Error('The GitHub report contains invalid limitations.');
  // Rebuild the real report from known fields. Tokens, raw provider responses,
  // and other unknown baggage must not survive into browser review exports.
  const controls=input.controls.map(c=>({
    id:c.id,title:c.title,domain:c.domain,status:c.status,criticality:c.criticality,kind:c.kind,
    soc2:[...c.soc2],iso27001:[...c.iso27001],guidance:c.guidance,owner:c.owner??null,
    source:c.source==null?null:{sensor:c.source.sensor??null,query:c.source.query??null,payload:c.source.payload??null},
    findings:[...c.findings],valid_until:c.valid_until??null,collected_at:c.collected_at??null,
    fingerprint:c.fingerprint??null,evidence_id:c.evidence_id??null,evidence_status:c.evidence_status??null,
    waiver:null,...(c.check_scope!=null?{check_scope:c.check_scope}:{}),...(c.scope_reason!=null?{scope_reason:c.scope_reason}:{})
  }));
  return {schema_version:1,mode:'github',title:input.title,generated_at:input.generated_at,as_of:input.as_of,
    source_commit:null,target:{host:'github.com',repository:target.repository,branch:target.branch,commit:target.commit,visibility:target.visibility},
    source_state:'local-github-collection',
    assessment:{kind:'github-repository',control_ids:[...assessment.control_ids],limitations:[...assessment.limitations],incomplete:assessment.incomplete===true||controls.some(c=>c.status==='MISSING')},
    controls,summary:summarize(controls),caveats:[...(input.caveats??[])]};
}
export function isLocalWorkspace(locationLike) {
  let location=locationLike;
  if(typeof locationLike==='string') {try {location=new URL(locationLike);}catch {return false;}}
  if(!location || !['http:','https:'].includes(location.protocol) || typeof location.hostname!=='string') return false;
  const hostname=location.hostname.toLowerCase().replace(/^\[(.*)\]$/,'$1');
  return ['127.0.0.1','localhost','::1'].includes(hostname);
}
export function reviewProgress(note) {
  return plainRecord(note) && Object.hasOwn(note,'progress') && REVIEW_PROGRESS.includes(note.progress)?note.progress:'Not started';
}
export function parseWorkspaceImport(input,{allowReal=false}={}) {
  if(!plainRecord(input)) throw new Error('Choose an assessment report or an exported workspace review.');
  const candidate=Object.hasOwn(input,'format')?input.report:input;
  if(candidate?.mode==='github' && allowReal!==true) throw new Error('Real repository reports open only in local workspace. Run python3 scripts/serve_workspace.py --report /path/to/report.json.');
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

// One pass per repository in each of the three monthly pilot cycles.
export function pilotHours({repositories, manualMinutes, collectorMinutes, setupHours}) {
  const inputs = [repositories, manualMinutes, collectorMinutes, setupHours];
  if (!inputs.every(Number.isFinite) || inputs.some(value => value < 0) ||
      !Number.isInteger(repositories) || repositories < 1) return null;
  const collections = 3 * repositories;
  const manual = collections * manualMinutes / 60;
  const collector = setupHours + collections * collectorMinutes / 60;
  return {manual, collector, saved: manual - collector, threshold: setupHours * 60 / collections};
}

// Decisions apply only to the fictional customer request. They never alter report controls.
export const evidenceActions = {
  snapshot: 'Send the settings snapshot',
  release: 'Request the release record',
  quarter: 'Sample the quarter'
};

// Alternative synthetic returns for the same release, shown independently.
export const releasePackets = {
  matched: {label: 'Packet A', events: [
    {time: '09:12', event: 'Reviewer Lee approved PR #62'},
    {time: '09:24', event: 'Reviewer Chen approved PR #62'},
    {time: '09:30', event: 'PR #62 merged as commit 7c4f9ac'},
    {time: '09:46', event: 'Release REL-204 deployed commit 7c4f9ac'}
  ]},
  missing: {label: 'Packet B', events: [
    {time: '09:46', event: 'Release ticket REL-204 marked deployed. Commit and pull request fields are empty.'}
  ]},
  exception: {label: 'Packet C', events: [
    {time: '09:12', event: 'Reviewer Lee approved PR #62'},
    {time: '09:30', event: 'PR #62 merged as commit 7c4f9ac'},
    {time: '09:37', event: 'Reviewer Chen approved PR #62'},
    {time: '09:46', event: 'Release REL-204 deployed commit 7c4f9ac'}
  ]}
};

export const evidenceReturns = {
  release: {
    pending: 'Waiting for the release owner',
    ...Object.fromEntries(Object.entries(releasePackets).map(([key, packet]) => [key, packet.label]))
  },
  quarter: {
    pending: 'Waiting for the change owner',
    matched: 'Reconciled population and two approvals on each sampled change',
    missing: 'Incomplete deployment list',
    exception: 'One sampled change lacks approval evidence'
  }
};

const initialDisposition = {
  settings: {
    snapshot: ['Answer the configuration question', 'Compliance lead', 'Attach the dated settings record with both repository names.'],
    release: ['Release review exceeds the request', 'Compliance lead', 'Answer the settings question with the dated observation. Ask whether the customer also needs release-specific evidence.'],
    quarter: ['Period sampling exceeds the request', 'Compliance lead', 'Send the settings observation and ask whether the customer also needs evidence of operation over time.']
  },
  release: {
    snapshot: ['Release request stays open', 'Release owner', 'Obtain the deployed commit, the merged pull request and approvals dated before merge.'],
    release: ['Collect the release evidence', 'Release owner', 'Trace the deployed commit to the pull request and compare each approval timestamp with its merge time.'],
    quarter: ['The named release still needs a trace', 'Release owner', 'Identify the named release and its pull request. A period sample can omit this particular change.']
  },
  quarter: {
    snapshot: ['Period request stays open', 'Change owner', 'Identify the changes deployed during the quarter and the evidence held for each.'],
    release: ['One release cannot cover the quarter', 'Change owner', 'Reconcile the quarter’s release population, agree the sample and obtain records for selected changes.'],
    quarter: ['Plan the period review', 'Change owner', 'Agree the period and sampling method with the reviewer. Reconcile the release list and retrieve the selected approval records.']
  }
};

export function evidenceDecision(scope, action, returned = 'pending') {
  if (!Object.hasOwn(initialDisposition, scope) || !Object.hasOwn(evidenceActions, action)) return null;
  if (action !== 'snapshot' && !Object.hasOwn(evidenceReturns[action], returned)) return null;
  const [title, owner, next] = initialDisposition[scope][action];
  const observation = 'At collection, both fixture repositories required two reviews.';
  const baseline = {title, owner, next, claim: observation, simulated: false};
  if (action === 'snapshot' || returned === 'pending') return baseline;

  if (returned === 'missing') {
    return {...baseline, simulated: true, title: 'Evidence gap remains open',
      owner: action === 'release' ? 'Release owner' : 'Change owner',
      next: action === 'release' ? 'Locate the release identifier and its source records, or document why the link is unavailable.' : 'Reconcile the deployment list against the delivery system before selecting a sample.',
      claim: observation + ' The requested follow-up records are incomplete.'};
  }

  if (returned === 'exception') {
    return {...baseline, simulated: true, title: 'Escalate the observed exception', owner: 'Change owner',
      next: 'Preserve the reviewed record, check for a documented exception and agree follow-up with the compliance lead.',
      claim: action === 'release' ? 'One of the two recorded approvals occurred after this release was merged.' : 'One sampled change lacks evidence of timely approval. The result for the remaining population is undetermined.'};
  }

  const claim = action === 'release' ? 'The linked release has two approvals recorded before merge.' :
    'Each change in the agreed sample has two documented approvals. This conclusion applies to the tested sample.';
  if (scope !== action) return {...baseline, simulated: true, claim: observation + ' ' + claim};
  return {title: action === 'release' ? 'Answer for this release' : 'Report the sample results', owner: 'Compliance lead',
    next: action === 'release' ? 'Provide the dated trace for the named release.' : 'Disclose the dates, population reconciliation, selection method and tested results. The independent auditor determines any examination conclusion.',
    claim, simulated: true};
}
