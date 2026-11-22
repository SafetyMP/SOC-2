import {reviewWorkpaper,packetTrace,quarterDeployments,quarterPackets,releasePackets,evidenceActions,evidenceReturns,evidenceDecision,pilotHours,ATTENTION,LABELS,STATUSES,domainLabel,escapeHTML as h,summarize,validateReport,filterControls,filtersForPage,parseWorkspaceImport,validateReviewNotes,REVIEW_PROGRESS,reviewProgress,prioritySort,sourceURL,nextAction,isLocalWorkspace} from './model.mjs';

const paths={grid:'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',flag:'M5 21V3m0 1h13l-3 5 3 5H5',shield:'M12 3l8 3v6c0 5-8 9-8 9s-8-4-8-9V6z M8 12l3 3 5-6',file:'M14 3H5v18h14V8z M14 3v5h5 M8 12h8 M8 16h6',layers:'M12 3l9 5-9 5-9-5z M3 12l9 5 9-5 M3 16l9 5 9-5',arrow:'M5 12h14 M13 6l6 6-6 6',down:'M12 3v12 M7 10l5 5 5-5 M4 16v5h16v-5',search:'M21 21l-5-5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',book:'M12 5v16 M12 5C8 2 4 3 2 4v15c4-2 7-1 10 2 3-3 6-4 10-2V4c-3-1-6-2-10 1',check:'M5 12l4 4L19 6',close:'M6 6l12 12 M6 18L18 6',clock:'M12 8v5l3 2 M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0',key:'M14 4a5 5 0 1 1-3 9L4 20H1v-3l8-8a5 5 0 0 1 5-5z',info:'M12 11v6 M12 7h.01 M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0',refresh:'M20 7v5h-5 M4 17v-5h5 M5 7a8 8 0 0 1 13-2l2 2 M4 17l2 2a8 8 0 0 0 13-2',code:'M8 5l-6 7 6 7 M16 5l6 7-6 7',external:'M14 3h7v7 M21 3L10 14 M10 3H3v18h18v-7'};
const icon=name=>`<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[name]||paths.shield}"/></svg>`;
const status=c=>`<span class="status ${c.status.toLowerCase()}">${LABELS[c.status]}</span>`;
const date=value=>value&&Number.isFinite(Date.parse(value))?new Date(value).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'}):'Not available';
const percent=n=>`${Math.round(n*100)}%`;
const repo='https://github.com/SafetyMP/SOC-2';
const localWorkspace=isLocalWorkspace(location);
const realReviews=new Map();
const real=()=>report?.mode==='github';
const checkTitles={'CTRL-CHG-001':'Branch protection and force-push settings','CTRL-CHG-002':'Required reviews and status checks','CTRL-CHG-008':'Active GitHub Actions workflow'};
const controlTitle=c=>real()&&c.status!=='UNWIRED'?(checkTitles[c.id]||c.title):c.title;
const planStorage=()=>real()?'Kept in this tab only. Export your review before closing or reloading.':storageAvailable?'Saved only in this browser. Export your review to reopen these plans later.':'Browser storage is unavailable. Export your review before closing this tab.';

let report, sample, notes={}, storageKey='', storageAvailable=true, imported=false, page='overview', filters={query:'',status:'all',domain:'all',progress:'all'}, toastTimer, pendingImport=null, pristineForm=null;
const main=document.querySelector('main'), detail=document.querySelector('#detail'), help=document.querySelector('#help');
const navItems=[['overview','grid','Overview'],['attention','flag','Action queue'],['controls','shield','Control library'],['evidence','file','Evidence'],['guide','book','How it works']];

function notify(message) {const toast=document.querySelector('#toast');toast.textContent=message;toast.classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>toast.classList.remove('visible'),4500);}
async function setReport(data,restoredNotes=null,isImported=false) {
  const validated=validateReport(data);
  const bytes=new TextEncoder().encode(JSON.stringify(validated.mode==='fixture'?validated.controls:[validated.mode,validated.target,validated.controls]));
  const hash=await crypto.subtle.digest('SHA-256',bytes);
  report=validated;
  imported=isImported;
  storageKey='soc2-review-v1-'+Array.from(new Uint8Array(hash),b=>b.toString(16).padStart(2,'0')).join('');
  notes=real()?(realReviews.get(storageKey)||{}):{};storageAvailable=true;
  if(!real()){try {const saved=JSON.parse(localStorage.getItem(storageKey)||'{}');notes=validateReviewNotes(saved,report);} catch {storageAvailable=false;}}
  if(restoredNotes!==null){notes=validateReviewNotes(restoredNotes,report);if(!real()){try{localStorage.setItem(storageKey,JSON.stringify(notes));}catch{storageAvailable=false;}}}
  if(real())realReviews.set(storageKey,notes);
  filters={query:'',status:'all',domain:'all',progress:'all'};
  document.querySelector('#mode-pill').textContent=real()?'REAL REPOSITORY · LOCAL':imported?'IMPORTED FIXTURE':'SAMPLE DATA';
  document.querySelector('#mode-pill').classList.toggle('real-mode',real());
  document.querySelector('.workspace-label').innerHTML=`<span class="workspace-avatar">${real()?'R':'S'}</span><span>${real()?'Repository assessment':'Sensor pack'}<span>${real()?'Local workspace':'Reference workspace'}</span></span><span class="workspace-dot"></span>`;
  document.querySelector('.sidebar-bottom').innerHTML=`<div class="sample-mark"><span></span>${real()?'Real repository results':'Interactive sample'}</div><p>${real()?'Evidence stays local.<br>Notes stay in this tab.':'Real policy checks.<br>Synthetic source data.'}</p><a href="${repo}" target="_blank" rel="noreferrer">View source repository ↗</a>`;
  document.title=real()?`${report.target.repository} · Local assessment`:'SOC-2 readiness workspace · Interactive sample';
  render();
}
function header(title,description,eyebrow='READINESS AT A GLANCE',extra='') {return `<div class="page-heading"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p>${description}</p></div><div class="heading-actions">${extra}<button class="button secondary" data-action="export">${icon('down')} Export review</button></div></div>`;}
function visibleNavItems() {return canShowCase() ? [['case','book','Release case'], ['technical','code','Technical guide']] : navItems;}
function nav() {document.querySelector('#navigation').innerHTML=visibleNavItems().map(([id,i,label])=>`<a href="#${id}" class="${page===id?'active':''}" ${page===id?'aria-current="page"':''}>${icon(i)}<span>${label}</span>${id==='attention'?`<span class="count">${report.controls.filter(c=>ATTENTION.includes(c.status)).length}</span>`:''}</a>`).join('');document.querySelector('#breadcrumb').textContent=visibleNavItems().find(n=>n[0]===page)[2];}
function row(c) {const note=notes[c.id];const saved=note && (note.owner||note.note||reviewProgress(note)!=='Not started');return `<tr><td><div class="control-title-row"><span class="control-icon">${icon(c.kind==='technical'?'shield':'file')}</span><div><button class="control-title" data-control="${c.id}">${h(controlTitle(c))}</button><span class="control-id">${c.id}</span>${saved?`<div class="plan-summary"><span class="plan-badge">${icon('check')} Plan saved · ${h(reviewProgress(note))}</span>${note.owner?`<span>${h(note.owner)}</span>`:''}${note.note?`<span class="plan-excerpt">${h(note.note.length>110?note.note.slice(0,107)+'…':note.note)}</span>`:''}</div>`:''}</div></div></td><td class="domain-col">${h(domainLabel(c.domain))}</td><td>${status(c)}</td><td class="criticality-col"><span class="criticality ${c.criticality<3?'medium':''}"><i aria-hidden="true"><b></b><b></b><b></b></i>${c.criticality===3?'High':c.criticality===2?'Medium':'Low'}</span></td><td><button class="row-open" data-control="${c.id}" aria-label="Inspect ${c.id}">${icon('arrow')}</button></td></tr>`;}
function table(controls) {return `<div class="table-wrap"><table class="control-table"><thead><tr><th scope="col">Control</th><th scope="col" class="domain-col">Domain</th><th scope="col">Result</th><th scope="col" class="criticality-col">Priority</th><th scope="col"><span class="muted" aria-label="Actions"></span></th></tr></thead><tbody>${controls.map(row).join('')}</tbody></table></div>`;}
const requests = {
  settings: {label: 'Settings at collection', evidence: ['Settings snapshot']},
  release: {label: 'One production release', evidence: ['Settings snapshot','Release approvals']},
  quarter: {label: 'Changes throughout the quarter', evidence: ['Settings snapshot','Release approvals','Quarter’s release population']}
};

let selectedRequest = 'release';
let selectedAction = '';
let returnedEvidence = 'pending';
const pilotAssumptions = {repositories: 8, manualMinutes: 25, collectorMinutes: 10, setupHours: 4};
const canShowCase = () => !real() && !imported && !(localWorkspace && ['1','viewer'].includes(new URLSearchParams(location.search).get('local')));
function caseResponse(control) {
  const request = requests[selectedRequest];
  const question = {
    settings: 'What review settings were in place when you collected the evidence?',
    release: 'Who approved the change deployed in REL-204 before it was merged?',
    quarter: 'What can you show about production change reviews from April through June?'
  }[selectedRequest];
  const axis = selectedRequest === 'settings' ? ['Settings observed', date(control.collected_at), 'Point in time']
    : selectedRequest === 'release' ? ['Review events', 'Merge', 'Deploy REL-204'] : ['April', 'Review period', 'June'];
  return `<figure class="scope-figure scope-${selectedRequest}"><figcaption>${request.label}</figcaption>
    <div class="scope-track" aria-hidden="true"><i></i><i></i><i></i></div>
    <div class="scope-axis">${axis.map(label => `<span>${label}</span>`).join('')}</div>
    <blockquote>“${question}”</blockquote></figure>`;
}

const marks = {supported: 'Approvals supported', gap: 'Evidence gap', exception: 'Late approval'};
const profiles = {
  team: {label:'One team · 3 repositories', repositories:3},
  platform: {label:'Shared platform · 8 repositories', repositories:8}
};

function actionOutcome() {
  const outcome = evidenceDecision(selectedRequest, selectedAction, returnedEvidence);
  if (!outcome) return '';
  const response = `<h3>${outcome.title}</h3><dl><dt>Customer reply · ${requests[selectedRequest].label}</dt><dd>${outcome.claim}</dd>
    <dt>Next owner · ${outcome.owner}</dt><dd>${outcome.next}</dd>
    ${outcome.packetFinding && selectedRequest !== selectedAction ? `<dt>Separate packet finding</dt><dd>${outcome.packetFinding}</dd>` : ''}</dl>`;
  if (!outcome.simulated) return `<div class="case-disposition" role="status">${response}</div>`;
  const review = reviewWorkpaper(selectedAction, returnedEvidence, mark);
  return `${selectedAction === 'release' ? releasePacketView() : quarterPacketView()}
    <div class="paper-signoff"><h3 id="mark-prompt">What does this packet document?</h3>
      <div class="case-picks" role="group" aria-labelledby="mark-prompt">${Object.entries(marks).map(([key,label]) =>
        `<button type="button" data-mark="${key}" aria-pressed="${mark===key}">${label}</button>`).join('')}</div>
      <div role="status" aria-live="polite">${review ? `<p><b>${review.accepted ? 'Second reviewer accepts the finding.' : 'Second reviewer returns the finding.'}</b> ${review.feedback}</p>` : ''}</div>
      ${review?.accepted ? `<div class="case-disposition">${response}</div>` : ''}
      ${review?.accepted && returnedEvidence==='missing' ? `<button class="case-primary" id="owner-follow-up">${selectedAction==='quarter' ? 'Request the archived register entry' : 'Request the linked release records'}</button>` : ''}
    </div>`;
}

function releasePacketView() {
  const packet = releasePackets[returnedEvidence];
  return `<figure class="release-packet"><figcaption>${packet.label} · REL-204</figcaption>
    <p>Read the owner’s records in time order. All times are UTC.</p>
    <ol>${packet.events.map(record => `<li><time>${record.time}</time><span>${record.event}</span></li>`).join('')}</ol></figure>`;
}

function quarterPacketView() {
  const packet = quarterPackets[returnedEvidence];
  return `<figure class="release-packet quarter-packet"><figcaption>${packet.label} · April–June 2026</figcaption>
    <p>Match the change register to the deployment log. The agreed sample takes every other release, starting with the first, after the lists reconcile.</p>
    <dl class="period-records"><dt>Deployment log</dt><dd>${quarterDeployments.join(' · ')}</dd><dt>Change register</dt><dd>${packet.register.join(' · ')}</dd></dl>
    ${packet.sample.length ? `<h4>Documented approvals before merge</h4><dl class="sample-approvals">${packet.sample.map(row => `<div><dt>${row.release}</dt><dd>${row.approvals.join(' and ')}</dd></div>`).join('')}</dl>` : '<p>No sample records enclosed.</p>'}</figure>`;
}

function returnOptions() {
  const choices = evidenceReturns[selectedAction];
  if (!choices) return '';
  return `<label class="case-select">Illustrative owner return<select id="evidence-return">
    ${Object.entries(choices).map(([key,label]) => `<option value="${key}" ${returnedEvidence===key?'selected':''}>${label}</option>`).join('')}</select></label>`;
}

function decisionForm(control) {
  return `<div class="inbox-grid"><figure class="settings-card"><figcaption>Platform file · Branch settings on ${date(control.collected_at)}</figcaption>
    <dl><div><dt>core-service</dt><dd>2 reviews required</dd></div><div><dt>infra-modules</dt><dd>2 reviews required</dd></div></dl>
    <p>Both production branches require status checks.</p></figure>
    <fieldset class="case-actions"><legend>How will you respond to the request?</legend>
    ${Object.entries(evidenceActions).map(([key,label]) => `<label><input type="radio" name="evidence-action" value="${key}" ${selectedAction===key?'checked':''}>${label}</label>`).join('')}</fieldset></div>
    ${selectedAction ? `<section class="method-slip" aria-labelledby="method-title"><p class="eyebrow">SOC 2 readiness · Change management</p>
    <h3 id="method-title">Test what the evidence can support</h3>
    <p>CC8.1 covers how a service provider authorizes and manages changes. Cedarline’s own rule calls for two reviewers before merge. Its local policy check reads repository settings.</p>
    <dl class="method-steps"><div><dt>Policy check</dt><dd>${h(control.id)} · ${h(control.status)}</dd></div><div><dt>What it establishes</dt><dd>The captured branches require reviews and status checks.</dd></div><div><dt>Customer’s scope</dt><dd>${requests[selectedRequest].label}</dd></div></dl>
    </section><div id="return-options">${returnOptions()}${ownerFollowUp ? '<p role="status">In this follow-up, the owner supplied the missing records. Review the new packet before updating Eastbank.</p>' : ''}</div><div id="action-outcome">${actionOutcome()}</div>` : ''}`;
}

function barRow(label, value, max, display) {
  return `<div class="case-bar"><span>${label}</span><progress aria-label="${label}" value="${value}" max="${max}"></progress><b>${display}</b></div>`;
}
function pilotResult() {
  const result = pilotHours(pilotAssumptions);
  const format = value => value.toLocaleString('en-US', {maximumFractionDigits: 2});
  const scale = Math.max(1, result.manual, result.collector);
  return `<figure class="case-chart"><figcaption>Staff time over three months</figcaption>
    ${barRow('Manual collection',result.manual,scale,format(result.manual)+' h')}
    ${barRow('Local pilot with setup',result.collector,scale,format(result.collector)+' h')}</figure>
    <strong>${result.saved===0 ? 'Both options take the same time.' : `The pilot takes ${format(Math.abs(result.saved))} hours ${result.saved>0?'less':'more'}.`}</strong>`;
}

function sponsorView() {
  const accepted = reviewWorkpaper(selectedAction,returnedEvidence,mark)?.accepted;
  if (!selectedAction || (returnedEvidence !== 'pending' && !accepted)) return '';
  return `<section class="case-section"><p class="eyebrow">Priya’s proposal · Three monthly collections</p>
    <h2>Should the team collect settings locally?</h2><p>Engineering now gathers the same settings by hand for each customer review. The proposed pilot collects them once a month. Release owners still supply the approval records.</p>
    <div class="pilot-desk"><div><h3>Choose a pilot scope</h3><div class="case-picks" role="group" aria-label="Pilot scope">${Object.entries(profiles).map(([key,profile]) =>
      `<button data-profile="${key}" aria-pressed="${pilotAssumptions.repositories===profile.repositories}">${profile.label}</button>`).join('')}</div>
      <p>Illustrative assumptions for ${pilotAssumptions.repositories} repositories: ${pilotAssumptions.manualMinutes} minutes each by hand, ${pilotAssumptions.collectorMinutes} minutes with the collector, and ${pilotAssumptions.setupHours} hours to set up.</p></div>
      <div class="case-response" id="pilot-result" aria-live="polite">${pilotResult()}</div></div>
    <label class="case-select">What would you fund?<select id="sponsor">${Object.entries({'':'Choose a recommendation',hold:'Retain manual collection',pilot:'Authorize the measured pilot',expand:'Consider expansion'}).map(([key,label])=>`<option value="${key}" ${sponsor===key?'selected':''}>${label}</option>`).join('')}</select></label><p id="sponsor-memo" aria-live="polite">${sponsorMemo()}</p></section>`;
}

function caseView() {
  const control = report.controls.find(item => item.id === 'CTRL-CHG-002');
  return `<article class="change-case">
    <header class="case-head"><div class="case-intro"><p class="eyebrow">Cedarline Dispatch · Fictional customer assurance case</p>
    <h1>The Friday rollout review</h1><p>Cedarline sells dispatch software to regional fleets. Eastbank Food Co-op uses it to assign morning deliveries at one depot. On Friday, its procurement team meets to decide whether two more depots can join.</p>
    <p>Priya, Cedarline’s compliance lead, prepares the evidence for Alex, Eastbank’s vendor-risk reviewer. A vague answer sends the question back through sales and engineering while the rollout decision waits.</p></div>
    <aside class="review-letter"><p>Eastbank Food Co-op · Review agenda</p><blockquote>“Our dispatchers are using the June update. Before we expand, can you show who approved the change we received?”</blockquote><span>Alex · Vendor-risk reviewer</span></aside></header>
    <section class="case-section case-journey"><h2>How a change reaches Eastbank</h2>
    <ol><li><b>Engineering reviews</b><span>Reviewers sign off on a pull request. The merge records which version entered the production branch.</span></li><li><b>Platform deploys</b><span>The release owner logs the version sent to customers under a release ID.</span></li><li><b>Assurance responds</b><span>Sales forwards Eastbank’s question to Priya. She has the settings export. Platform keeps the release log and review history.</span></li></ol>
    <p>When the records arrive separately, Priya and a release engineer both stop to reconstruct the change. Alex needs an answer another reviewer can trace before Friday.</p>
    <button class="case-primary" id="open-brief">Open Eastbank’s request</button></section>
    ${briefOpen ? `<section class="case-section" aria-labelledby="brief-title"><p class="eyebrow">Priya’s review file</p><h2 id="brief-title" tabindex="-1">Eastbank’s evidence request</h2>
    <label class="case-select">Requested scope<select id="case-request">${Object.entries(requests).map(([key,entry])=>`<option value="${key}" ${selectedRequest===key?'selected':''}>${entry.label}</option>`).join('')}</select></label>
    <div id="case-response">${caseResponse(control)}</div>${decisionForm(control)}</section>${sponsorView()}
    <p class="case-links"><a href="#technical">Trace this evidence in the technical guide</a></p>` : ''}
    <details class="case-reading"><summary>Case background and sources</summary><p>Cedarline, Eastbank and their records are fictional. The case draws on how provider assurance teams handle customer reviews and how GitHub records required reviews. SOC 2 examinations and opinions belong to independent CPAs.</p><p><a href="https://handbook.gitlab.com/handbook/security/security-assurance/field-security/customer-security-assessment-process/">Customer assessment workflow</a> · <a href="https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets">GitHub review rules</a> · <a href="https://www.aicpa-cima.com/resources/download/illustrative-soc-2-r-report-with-description-and-assertion">AICPA illustrative report</a></p></details>
  </article>`;
}

const traceStages = ['Collection', 'Reconciliation', 'Handoff'];
let stage = 0;
let trial = 'matched';
let sponsor = '';
let mark = '';
let ownerFollowUp = false;
const caseQuery = new URLSearchParams(location.search);
let briefOpen = caseQuery.has('action') || caseQuery.has('scope') || caseQuery.get('brief') === 'open';
if (Object.hasOwn(requests, caseQuery.get('scope'))) selectedRequest = caseQuery.get('scope');
if (Object.hasOwn(evidenceActions, caseQuery.get('action'))) selectedAction = caseQuery.get('action');
if (Object.hasOwn(evidenceReturns[selectedAction] || {}, caseQuery.get('packet'))) returnedEvidence = caseQuery.get('packet');
if (['matched','missing','exception'].includes(caseQuery.get('trial'))) trial = caseQuery.get('trial');
if (selectedRequest === 'settings' && trial === 'exception') trial = 'matched';
if (['0','1','2'].includes(caseQuery.get('stage'))) stage = Number(caseQuery.get('stage'));
if (['hold','pilot','expand'].includes(caseQuery.get('sponsor'))) sponsor = caseQuery.get('sponsor');
for (const key of Object.keys(pilotAssumptions)) {
  if (!caseQuery.has(key)) continue;
  const n = Number(caseQuery.get(key));
  if (Number.isInteger(n) && n >= (key==='repositories'?1:0) && n<=10000) pilotAssumptions[key] = n;
}
if (reviewWorkpaper(selectedAction, returnedEvidence, caseQuery.get('mark'))) mark = caseQuery.get('mark');
ownerFollowUp = caseQuery.get('followup')==='1' && returnedEvidence==='matched' && ['release','quarter'].includes(selectedAction);
function saveSelection() {
  const url = new URL(location.href);
  for (const [key,value] of Object.entries({scope:briefOpen ? selectedRequest : '',brief:briefOpen ? 'open' : '',action:selectedAction,packet:returnedEvidence,stage,trial,sponsor,mark,followup:ownerFollowUp ? '1' : '',...pilotAssumptions})) {
    if (value === '' || Number.isNaN(value)) url.searchParams.delete(key);
    else url.searchParams.set(key,value);
  }
  history.replaceState(null,'',url);
}
function sponsorMemo() {
  const hours = pilotHours(pilotAssumptions);
  if (!sponsor || !hours) return '';
  const savings = Math.abs(hours.saved).toLocaleString('en-US',{maximumFractionDigits:2});
  if (sponsor === 'hold') return `Manual collection continues. Record the modeled three-month difference (${savings} hours ${hours.saved >= 0 ? 'saved' : 'added'} by the pilot) and review again after timing the next collection.`;
  if (sponsor === 'pilot') return hours.saved <= 0
    ? `The pilot uses ${savings} extra hours at this scope. Proceed only if the trial shows a traceability benefit worth that time.`
    : `The model releases ${savings} hours. Before expanding, ask a second reviewer to retrieve each dated observation and flag every unreadable setting.`;
  return hours.saved <= 0 ? 'Expansion returns to the sponsor. The model shows no net hours recovered; remeasure collection effort before broadening scope.' : `Expansion remains conditional. The model recovers ${savings} hours. Verify source retrieval and record every unreadable setting before authorizing additional repositories.`;
}
function caseGuide() {
  const control = report.controls.find(c => c.id === 'CTRL-CHG-002');
  const scope = selectedRequest;
  const packets = scope === 'quarter' ? quarterPackets : releasePackets;
  const response = evidenceDecision(scope, selectedAction, returnedEvidence);
  const selected = evidenceReturns[selectedAction]?.[returnedEvidence] || 'Dated settings only';
  let detail;
  const prepared = reviewWorkpaper(selectedAction,returnedEvidence,mark);
  if (stage === 0) {
    detail = `<p><b>${control.status} · ${control.id}</b> evaluated the review and status-check settings for two repositories. The fixture captures no event-level approvals.</p><code>${h(control.source.payload)}</code>`;
  } else if (stage === 1) {
    const selectedTrace = returnedEvidence !== 'pending' && ['release','quarter'].includes(selectedAction)
      ? packetTrace(selectedAction, returnedEvidence) : '';
    detail = `<p>${scope === 'quarter' ? 'Reconcile the April–June deployment inventory to the change register, then inspect the agreed sample.' : scope === 'release' ? 'Follow REL-204 to its deployed commit, then compare PR #62 approval times to the merge.' : 'Match the dated configuration observation to its repository and policy.'}</p><p>Selected owner return: <b>${selected}</b>.</p>${selectedTrace}`;
  } else {
    detail = response ? `<p><b>${response.owner}</b> · ${response.next}</p><p>${response.claim}</p>` : '<p>Return to the case and choose the platform owner’s response to trace the handoff to a named owner.</p>';
  }
  const target = scope === 'quarter' ? 'April–June 2026' : scope === 'release' ? 'REL-204' : 'Settings at collection';
  const tabs = traceStages.map((name,i) => `<button data-stage="${i}" aria-pressed="${i===stage}">${name}</button>`).join('');
  const configurationTrials = {matched:'Readable settings',missing:'Unavailable settings'};
  const choices = scope === 'settings' ? configurationTrials : Object.fromEntries(Object.entries(packets).map(([key,p])=>[key,p.label]));
  const comparison = scope === 'settings' ? (trial === 'missing' ? 'An unreadable branch configuration leaves the check missing. Request access or ask the repository owner to collect it locally.' : 'The fixture records a two-review requirement on core-service and infra-modules. The policy returns PASS for these configuration fields.') : packetTrace(scope, trial);
  return `<article class="change-case trace-guide"><p class="eyebrow">Implementation evidence · Synthetic case</p><h1>Trace ${target}</h1>
    <p>Customer request: <b>${requests[scope].label}</b> · Platform response: <b>${evidenceActions[selectedAction] || 'Undecided'}</b> · Owner return: <b>${selected}</b>.</p>
    <div class="trace-stages" role="group" aria-label="Trace stage">${tabs}</div><div class="trace-record" id="trace-record">${detail}${stage===2 && prepared ? `<p><b>Workpaper · ${prepared.accepted ? 'accepted' : 'returned for revision'}</b> · ${marks[mark]}</p>` : ''}</div>
    <h2>Compare evidence returns</h2><label class="case-select">Illustrative comparison for ${target}<select id="trace-trial">${Object.entries(choices).map(([key,label])=>`<option value="${key}" ${trial===key?'selected':''}>${label}</option>`).join('')}</select></label>
    <div class="trace-comparison">${comparison}</div>
    <details><summary>Components, fixture and research</summary><p><a href="${repo}/blob/main/scripts/assess_github.py">Python collector</a> reads three GitHub settings checks locally. <a href="${repo}/blob/main/policies/change_mgmt/branch_protection_enforced.rego">OPA policy</a> evaluates branch settings. <a href="${repo}/blob/main/scripts/export_workspace.py">Fixture exporter</a> produces the <a href="./data/sample-report.json">bundled JSON report</a>. The operating records compared above are illustrative.</p><p><a href="https://www.aicpa-cima.com/resources/download/illustrative-soc-2-r-report-with-description-and-assertion">AICPA’s illustrative Type 2 report</a> distinguishes control tests and results. <a href="https://csrc.nist.gov/pubs/sp/800/53/a/r5/final">NIST SP 800-53A</a> frames assessment objectives and evidence procedures.</p></details>
    <p><a href="#case">Return to the customer and funding decision</a></p></article>`;
}
function refreshTrace(selector) {
  saveSelection();
  main.innerHTML = caseGuide();
  main.querySelector(selector)?.focus({preventScroll:true});
}
document.addEventListener('click',event=>{
  const button = event.target.closest('[data-stage]');
  if (!button) return;
  stage = Number(button.dataset.stage);
  refreshTrace(`[data-stage="${stage}"]`);
});
document.addEventListener('change',event=>{
  if (event.target.id === 'trace-trial') {
    trial = event.target.value;
    refreshTrace('#trace-trial');
  } else if (event.target.id === 'sponsor') {
    sponsor = event.target.value;
    document.querySelector('#sponsor-memo').textContent = sponsorMemo();
    saveSelection();
  }
});
function overview() {
  const s=report.summary, attention=prioritySort(report.controls.filter(c=>ATTENTION.includes(c.status))), wired=report.controls.filter(c=>c.status!=='UNWIRED');
  const tech=wired.filter(c=>c.kind==='technical').length, proc=wired.length-tech;
  const domains=[...new Set(wired.map(c=>c.domain))].map(domain=>({domain,...summarize(wired.filter(c=>c.domain===domain))}));
  return header(real()?'Your repository. Clear next steps.':'A clearer path to readiness.',real()?'Review the observed GitHub settings, investigate missing evidence, and plan your next fix.':'No setup needed. Open a sample finding, plan the next action, and save your review.','YOUR READINESS WORKSPACE',`<button class="button" data-action="queue">Review findings ${icon('arrow')}</button>`)+
  `<div class="snapshot-line"><span class="dot"></span>${real()?h(report.target.repository):imported?'Imported fixture report':'Reference environment'} <span>·</span> ${!real()&&report.as_of!==report.generated_at?'Simulated as of':'Evaluated'} ${date(report.as_of)} <span>·</span> ${real()?'Read-only GitHub collection · no sample evidence':imported?'Open until reload · export to resume later':'Synthetic sample · no live systems connected'}</div>
  <section class="metrics" aria-label="Assessment summary">
  <div class="metric"><div class="metric-label">${real()?'Passing check weight':'Clean readiness'} <button class="info-button" data-action="scoring" aria-label="How readiness is calculated">${icon('info')}</button></div><div class="metric-value">${percent(s.clean_ratio)}</div><div class="metric-note"><span class="good">${s.counts.PASS} passing ${s.counts.PASS===1?'control':'controls'}</span> · passing checks only, weighted</div></div>
  <div class="metric"><div class="metric-label">Need attention ${icon('flag')}</div><div class="metric-value">${attention.length}<span>${attention.length===1?'control':'controls'}</span></div><div class="metric-note"><span class="warm">${s.counts.FAIL} failed</span> · ${s.counts.MISSING} missing · ${s.counts.EXPIRED} expired</div></div>
  <div class="metric"><div class="metric-label">Control coverage ${icon('layers')}</div><div class="metric-value">${s.wired_count}<span>/ ${s.catalog_count}</span></div><div class="metric-note">${s.unwired_count} catalog controls not evaluated</div></div>
  ${real()?`<div class="metric"><div class="metric-label">Collection completeness ${icon('file')}</div><div class="metric-value">${s.wired_count-s.counts.MISSING}<span>/ ${s.wired_count}</span></div><div class="metric-note">${s.counts.MISSING?'Missing evidence needs follow-up':'All scoped checks have evidence'}</div></div>`:`<div class="metric"><div class="metric-label">With accepted exceptions <button class="info-button" data-action="scoring" aria-label="About readiness with exceptions">${icon('info')}</button></div><div class="metric-value">${percent(s.effective_ratio)}</div><div class="metric-note">Effective readiness · ${s.counts.EXCEPTION} exceptions</div></div>`}</section>
  <div class="hero-grid"><section class="focus-card"><div class="eyebrow">${attention.length?'YOUR NEXT BEST STEP':'KEEP YOUR EVIDENCE CURRENT'}</div><h2>${real()?(attention.length?'Review your repository findings.':'Check the scope behind each pass.'):attention.some(c=>c.id==='CTRL-ACCESS-001')?'Start with access controls.':attention.length?'Close the evidence gaps.':'Review the passing evidence.'}</h2><p>${attention.length?'A score is a starting point. Open a finding to understand the evidence and plan a concrete fix.':'Review source records and expiry dates before relying on this assessment.'}</p><button class="button light" ${attention.length?`data-control="${attention[0].id}"`:'data-action="evidence"'}>${attention.length?'Inspect first finding':'Explore evidence'} ${icon('arrow')}</button></section>
  <section class="panel coverage-card"><div class="panel-heading"><div><h2>Know what’s in scope</h2><p>Coverage is separate from readiness.</p></div><div class="coverage-total"><strong>${percent(s.wired_count/s.catalog_count)}</strong> evaluated</div></div><div class="coverage-bar" role="img" aria-label="${tech} technical, ${proc} procedural, ${s.unwired_count} not evaluated"><span style="width:${100*tech/s.catalog_count}%"></span><span style="width:${100*proc/s.catalog_count}%"></span></div><div class="legend"><span><i></i>Technical · ${tech}</span><span><i></i>Procedural · ${proc}</span><span><i></i>Not evaluated · ${s.unwired_count}</span></div><p class="muted">Unevaluated controls never count as a pass. <button class="text-button" data-action="unwired">Explore coverage ${icon('arrow')}</button></p></section></div>
  <section><div class="section-heading"><div><h2>Focus your next review <span class="number">${attention.length}</span></h2><p>Failed checks first, then gaps in evidence.</p></div><a class="text-button" href="#attention">View action queue ${icon('arrow')}</a></div><div class="panel">${attention.length?table(attention.slice(0,4)):'<div class="empty">No findings in this snapshot. Review coverage before drawing conclusions.</div>'}<div class="table-footer"><span>${attention.length?`Showing ${Math.min(4,attention.length)} of ${attention.length} controls needing attention`:'No controls need attention'}</span><span>Changes to notes don’t change results</span></div></div></section>
  <div class="bottom-grid"><section class="panel domain-panel"><div class="panel-heading"><h2>Readiness by domain</h2><button class="text-button" data-action="scoring">How it’s calculated ${icon('info')}</button></div><div class="domain-list">${domains.map(d=>`<div class="domain-row"><span>${h(domainLabel(d.domain))}</span><div class="mini-bar"><span style="width:${d.clean_ratio*100}%"></span></div><strong>${percent(d.clean_ratio)}</strong></div>`).join('')}</div></section><section class="explain-card">${icon('book')}<h2>Evidence you can understand.</h2><p>${real()?'Each result describes a specific setting observed through the GitHub API. Review the exact check before relying on it.':'Every result connects to a source, a policy, and a next step. Explore the sample, or assess a real repository locally.'}</p><p>This workspace helps you interpret checks. It does not provide an audit opinion or certification.</p><a class="text-button" href="#guide">See how it works ${icon('arrow')}</a></section></div>`;
}
function listView() {const attention=page==='attention';return header(attention?'Turn findings into next steps.':'Every control. A clearer picture.',attention?'Inspect the evidence, capture a plan, and verify the fix in your next assessment.':'Explore the evaluated slice and the catalog that sits beyond it.',attention?'ACTION QUEUE':'CONTROL LIBRARY')+(!attention?`<div class="tabs" aria-label="Control result filter">${[['all','All controls'],['FAIL','Failed'],['MISSING','Missing'],['PASS','Passing'],['UNWIRED','Not evaluated']].map(([value,label])=>`<button class="tab ${filters.status===value?'active':''}" data-filter-status="${value}" aria-pressed="${filters.status===value}">${label} <span>· ${value==='all'?report.controls.length:report.summary.counts[value]}</span></button>`).join('')}</div>`:`<div class="notice">${icon('info')}<span>${real()?'Real review notes stay in this tab only. Export before closing or reloading.':'Review progress is saved in this browser.'} Only a new assessment can change a control’s result.</span></div>`)+`<section class="panel"><div class="filter-bar"><label class="search-wrap">${icon('search')}<input id="search" type="search" placeholder="Search controls, findings, or framework references…" aria-label="Search controls" value="${h(filters.query)}"></label><select id="status-filter" aria-label="Filter by result"><option value="all">All results</option>${(attention?ATTENTION:STATUSES).map(s=>`<option value="${s}" ${filters.status===s?'selected':''}>${LABELS[s]}</option>`).join('')}</select><select id="domain-filter" aria-label="Filter by domain"><option value="all">All domains</option>${[...new Set(report.controls.map(c=>c.domain))].sort().map(d=>`<option value="${h(d)}" ${filters.domain===d?'selected':''}>${h(domainLabel(d))}</option>`).join('')}</select>${attention?`<select id="progress-filter" aria-label="Filter by review progress"><option value="all">All review progress</option>${REVIEW_PROGRESS.map(p=>`<option ${filters.progress===p?'selected':''}>${h(p)}</option>`).join('')}</select>`:''}<button class="text-button" data-action="clear">Clear filters</button></div><div id="results"></div></section>`;}
function renderResults() {const results=prioritySort(filterControls(report.controls,{...filters,notes,progress:page==='attention'?filters.progress:'all',attention:page==='attention'}));document.querySelector('#results').innerHTML=results.length?`${table(results)}<div class="table-footer" role="status"><span>${results.length} ${results.length===1?'control':'controls'} shown</span><span>Open a control to inspect its evidence</span></div>`:`<div class="empty" role="status">${icon('search')}<h2>No matching controls</h2><p>Try a different term or clear the filters to see the full list.</p><button class="button secondary" data-action="clear">Clear filters</button></div>`;}
function evidenceView() {const s=report.summary;return header('See the evidence behind the result.','Follow each check back to its source. Keep collection, assessment, and review separate.','EVIDENCE EXPLORER')+`<div class="notice">${icon('info')}<span>${real()?'Real GitHub API observations · local files only':imported?'Imported fixture data':'Synthetic demonstration data'} · ${s.wired_count} evaluated records. Fingerprints identify source records; this browser does not verify signatures, custody, or production storage.</span></div><div class="evidence-cards"><section class="panel evidence-card">${icon('file')}<h2>Source records</h2><p>One record for each evaluated control.</p><div class="evidence-value">${s.wired_count}</div><ul class="info-list"><li><span>Collected</span>${date(report.generated_at)}</li><li><span>Assessment date</span>${date(report.as_of||report.generated_at)}</li><li><span>Source</span>${real()?h(report.target.repository):'Repository fixtures'}</li></ul></section><section class="panel evidence-card">${icon('clock')}<h2>Evidence health</h2><p>A missing source never becomes a pass.</p><div class="evidence-value">${s.counts.MISSING}<small style="font-size:12px;color:var(--muted)"> missing</small></div><ul class="info-list"><li><span>Passing</span>${s.counts.PASS}</li><li><span>Expired</span>${s.counts.EXPIRED}</li><li><span>Failed</span>${s.counts.FAIL}</li></ul></section><section class="panel evidence-card">${icon('code')}<h2>${real()?'Reassess after a change':'Reproducible by design'}</h2><p>${real()?'Rerun the local assessment after fixing a setting. Each run creates a new private folder; current results never change when you edit a plan.':'Run the policy engine locally to create a new fixture snapshot. Import it here without uploading its contents.'}</p><pre class="code-block">${real()?`python3 scripts/assess_github.py --repo ${h(report.target.repository)}`:`python3 scripts/export_workspace.py --output workspace-report.json`}</pre><button class="text-button" data-action="import">Open a report or review ${icon('arrow')}</button></section></div><section style="margin-top:28px"><div class="section-heading"><div><h2>Evaluated records</h2><p>Inspect source paths, raw findings, and validity dates.</p></div><button class="text-button" data-action="download-report">Download snapshot ${icon('down')}</button></div><div class="panel">${table(prioritySort(report.controls.filter(c=>c.status!=='UNWIRED')))}</div></section>`;}
function guideView() {return header('From a check to a confident next step.','A small, transparent workspace for the open-source policy and sensor pack.','HOW IT WORKS')+workflowPanel()+`<div class="section-heading"><div><h2>Explore the sample workflow</h2><p>Synthetic inputs help you learn the workspace without connecting a repository.</p></div></div><div class="guide-grid"><section class="panel guide-card"><div class="guide-step">01 / COLLECT</div>${icon('code')}<h2>Run the checks locally</h2><p>Use the existing Python and OPA engine to evaluate fixture payloads and procedural manifests.</p><pre>python3 scripts/export_workspace.py \
  --output workspace-report.json</pre><p>Requires Python, PyYAML, and OPA. The export command never connects to a provider.</p></section><section class="panel guide-card"><div class="guide-step">02 / UNDERSTAND</div>${icon('search')}<h2>Follow the evidence</h2><p>Open the JSON report or a saved review. Open a finding to see the affected resource, control guidance, framework references, and source record.</p><p>Clean readiness counts passes. Effective readiness also includes active accepted exceptions. Both exclude unevaluated controls.</p><button class="text-button" data-action="scoring">Understand the calculation ${icon('arrow')}</button></section><section class="panel guide-card"><div class="guide-step">03 / ACT</div>${icon('flag')}<h2>Plan, fix, and reassess</h2><p>Save an owner, next action, and progress note. Fix the source, refresh the input, then rerun the checks to produce a new assessment.</p><p>Sample review notes stay in this browser. Real repository notes stay in tab memory only. Both are included when you explicitly export a review. Reopen an exported review to resume your plans. They never change a policy verdict.</p><a class="text-button" href="#attention">Explore the action queue ${icon('arrow')}</a></section></div><section class="panel guide-note"><h2>A clear boundary around the demo</h2><ul><li>The sample uses synthetic repository fixtures. It is not a live assessment of any company.</li><li>Procedural checks inspect document presence and review dates. They do not verify signatures, approval, or content quality.</li><li>Catalog mappings are references, not a claim of complete framework coverage. No result is a SOC 2 report, CPA opinion, or certification.</li><li>Imported reports remain in browser memory. The public demo accepts only fixture reports. Real reports open in the local workspace; the browser never receives your GitHub credentials.</li></ul><div class="heading-actions"><a class="button secondary" href="${repo}" target="_blank" rel="noreferrer">Explore the source ${icon('external')}</a><button class="button secondary" data-action="reset">${icon('refresh')} Reset sample & notes</button></div></section>`;}
function repositoryBanner(){return real()?`<section class="assessment-banner" aria-label="Real repository assessment"><div><strong>Real repository · ${h(report.target.repository)}</strong><span>${h(report.target.branch||'Branch unavailable')} · ${report.target.commit?h(report.target.commit.slice(0,12)):'Commit unavailable'} · ${h(report.target.visibility||'Visibility unavailable')}</span></div><p>3 GitHub checks in scope · ${report.summary.unwired_count} catalog controls outside scope. Evidence and notes stay local; notes are lost on reload unless exported.</p>${report.assessment.incomplete?'<p class="collection-warning">Collection incomplete. Unreadable settings are missing evidence, not passing checks.</p>':''}</section>`:'';}
function workflowPanel(){return `<section class="panel real-workflow"><div class="eyebrow">YOUR REPOSITORY · ON YOUR COMPUTER</div><h2>Assess a real GitHub repository</h2><p>Run from a local checkout of this project. Requires Python, PyYAML, OPA, and the GitHub CLI. Use your existing <code>gh</code> login, or sign in locally with <code>gh auth login --hostname github.com</code>.</p><ol><li><strong>Collect and assess one repository.</strong><pre>python3 scripts/assess_github.py --repo OWNER/REPO</pre><p>The command prints the private report path and the command to open it. GitHub requests are read-only. Credentials remain with your local GitHub CLI.</p></li><li><strong>Open the local workspace.</strong><pre>python3 scripts/serve_workspace.py --report /absolute/path/report.json</pre><p>Open the localhost URL printed in your terminal. Reports and sanitized evidence stay outside the checkout; the public demo does not accept real reports.</p></li><li><strong>Review, fix, and rerun.</strong><p>Inspect branch protection, required reviews and status checks, and active workflow presence. These three checks do not establish deployment reproducibility or complete SOC 2 readiness. Unreadable settings appear as missing evidence. Export a review to keep your notes.</p></li></ol><a class="text-button" href="${repo}/blob/main/docs/local-github-assessment.md" target="_blank" rel="noreferrer">Setup, permissions & privacy ${icon('external')}</a></section>`;}
function showWorkflow(){help.innerHTML=`<div class="help-body"><div class="help-header"><span class="eyebrow">LOCAL ASSESSMENT</span><button class="close-button" data-action="close-help" aria-label="Close local assessment instructions">${icon('close')}</button></div><h2 id="help-title">Bring your own repository.</h2>${workflowPanel()}</div>`;help.showModal();}
function render() {
  if (['case','technical'].includes(page) && !canShowCase()) page = 'overview';
  const readingCase = page === 'case' || page === 'technical';
  document.body.classList.toggle('case-layout', readingCase);
  document.querySelector('#case-switch').href = page === 'technical' ? '#case' : '#technical';
  document.querySelector('#case-switch').textContent = page === 'technical' ? 'Back to the case' : 'Technical guide';
  filters = filtersForPage(filters, page);
  if (readingCase) {
    main.innerHTML = page === 'case' ? caseView() : caseGuide();
    return;
  }
  nav();
  const view = page === 'overview' ? overview() : ['attention','controls'].includes(page) ? listView() : page === 'evidence' ? evidenceView() : guideView();
  main.innerHTML = repositoryBanner() + view;
  if (['attention','controls'].includes(page)) renderResults();
}
function navigate(target) {if(location.hash===`#${target}`){page=target;render();}else location.hash=target;}
function openDetail(id) {
  const c=report.controls.find(c=>c.id===id);if(!c)return;
  const n=notes[id]||{},src=c.source||{},url=real()?null:sourceURL(report.source_commit,src.payload),refs=[...c.soc2.map(s=>`SOC 2 ${s}`),...c.iso27001.map(s=>`ISO 27001 ${s}`)];
  detail.innerHTML=`<div class="dialog-header"><div class="dialog-top"><span class="control-id">${c.id} · ${h(domainLabel(c.domain))}</span><button class="close-button" data-action="close-detail" aria-label="Close control details">${icon('close')}</button></div><h2 id="detail-title">${h(controlTitle(c))}</h2><div style="margin-top:12px">${status(c)}</div></div><div class="dialog-body">${real()?`<div class="check-scope"><h3>${c.status==='UNWIRED'?'Outside this assessment':'What this check measures'}</h3><p>${h(c.check_scope||c.scope_reason)}</p></div>`:''}<h3>What the check found</h3>${c.findings.length?`<ul class="finding-list">${c.findings.map(f=>`<li>${h(f)}</li>`).join('')}</ul>`:`<p>${c.status==='UNWIRED'?'No evaluation is available for this catalog control.':c.status==='PASS'?'No policy finding in this snapshot. This result applies only to the supplied evidence.':'No finding detail was supplied. Inspect the source and assessment status.'}</p>`}<div class="next-action"><h3>Recommended next step</h3><p>${h(real()&&c.status==='UNWIRED'?'This workflow assesses GitHub repository settings only. Assess this control separately using an appropriate source.':nextAction(c))}</p></div><h3>Catalog control</h3><p>${h(c.title)}</p><h3>Control guidance</h3><p>${h(c.guidance)}</p><h3>Evidence trail</h3><dl class="metadata"><dt>Sensor</dt><dd>${h(src.sensor||'Not connected')}</dd><dt>Repository reference</dt><dd>${url?`<a href="${url}" target="_blank" rel="noreferrer">${h(src.payload)} ↗</a>`:h(src.payload||'No source payload')}${!url && src.payload?' (local source; no exact commit link)':''}</dd><dt>Policy / query</dt><dd><code>${h(src.query||'Not evaluated')}</code></dd><dt>Collected</dt><dd>${date(c.collected_at)}</dd><dt>Valid until</dt><dd>${date(c.valid_until)}</dd><dt>Collected verdict</dt><dd>${h(c.evidence_status||'Not available')} · before expiry or exception overlays</dd><dt>Fingerprint</dt><dd><code>${h(c.fingerprint||'No evidence record')}</code><br>Identifies the collected record, before assessment overlays.</dd><dt>Framework refs</dt><dd>${h(refs.join(' · ')||'None')}</dd></dl>${c.waiver?`<h3>Accepted exception</h3><p>${h(c.waiver.reason||'No reason supplied')} · Expires ${h(c.waiver.expires||'not supplied')}</p>`:''}<form class="local-review" id="review-form" data-id="${c.id}"><h3>Your next action</h3><p class="review-note">${planStorage()}</p><div class="form-row"><label class="field">Owner or team<input name="owner" maxlength="100" placeholder="e.g. Platform team" value="${h(n.owner ?? c.owner ?? '')}"></label><label class="field">Review progress<select name="progress">${REVIEW_PROGRESS.map(p=>`<option ${n.progress===p?'selected':''}>${p}</option>`).join('')}</select></label></div><label class="field">Next action or review note<textarea name="note" maxlength="3000" placeholder="What needs to change, and how will you verify it?">${h(n.note||'')}</textarea></label><div class="dialog-actions"><span class="muted review-note">Progress never changes the check result.</span><button class="button" type="submit">Save next action ${icon('check')}</button></div></form></div>`;
  const form=detail.querySelector('#review-form');
  detail.querySelector('.next-action').after(form);
  const evidence=document.createElement('details');
  evidence.className='evidence-details';
  evidence.innerHTML='<summary>Evidence trail & control guidance</summary>';
  while(form.nextSibling) evidence.append(form.nextSibling);
  form.after(evidence);
  pristineForm=JSON.stringify([...new FormData(form)]);
  detail.showModal();
  detail.scrollTop=0;
}
function requestCloseDetail(){
  const form=detail.querySelector('#review-form');
  if(form && pristineForm!==null && JSON.stringify([...new FormData(form)])!==pristineForm){
    help.innerHTML=`<div class="help-body"><h2 id="help-title">Keep your unfinished action plan?</h2><p>You have unsaved edits. Keep editing to save them, or discard the changes and close this control.</p><div class="dialog-actions"><button class="button secondary" data-action="discard-edit">Discard changes</button><button class="button" data-action="close-help" autofocus>Keep editing</button></div></div>`;
    help.showModal();
  }else{pristineForm=null;detail.close();}
}
function openImport(error=''){
  help.innerHTML=`<div class="help-body"><div class="help-header"><div class="eyebrow">CONTINUE YOUR WORK</div><button class="close-button" data-action="close-help" aria-label="Close open report">${icon('close')}</button></div><h2 id="help-title">Open a report or saved review</h2><p>${localWorkspace?'Choose a local repository report, a fixture report, or an exported review. Real reports and their notes stay in this tab only.':'Choose a fixture report or reopen a <strong>soc2-review.json</strong> sample review. Real repository reports open only in the local workspace.'}</p><p>No file? Explore the sample, or <button class="text-button" data-action="assess">assess your repository locally</button>.</p>${error?`<p class="import-error" role="alert">${h(error)}</p>`:''}<div class="dialog-actions"><button class="button secondary" data-action="close-help">Back to workspace</button><button class="button" data-action="choose-file">Choose JSON file</button></div><p class="review-note">Files stay in this browser. Imported reports stay open until reload.</p></div>`;
  if(!help.open)help.showModal();
}
detail.addEventListener('cancel',e=>{e.preventDefault();requestCloseDetail();});
function scoring() {const s=report.summary;help.innerHTML=`<div class="help-body"><div class="help-header"><div class="eyebrow">READINESS, EXPLAINED</div><button class="close-button" data-action="close-help" aria-label="Close explanation">${icon('close')}</button></div><h2 id="help-title">A score with a visible denominator.</h2><p>Each evaluated control contributes its catalog priority weight (1–3). Unevaluated controls are excluded from the score and shown separately as coverage.</p><ul class="info-list"><li><span>Clean readiness</span>${s.clean_weight} passing weight ÷ ${s.total_weight} = ${percent(s.clean_ratio)}</li><li><span>Effective readiness</span>${s.effective_weight} passing + exception weight ÷ ${s.total_weight} = ${percent(s.effective_ratio)}</li><li><span>Control coverage</span>${s.wired_count} evaluated ÷ ${s.catalog_count} catalog controls</li></ul><p>Failed, missing, and expired evidence contribute zero passing weight. Active accepted exceptions only increase effective readiness. Local notes never affect either score.</p><p>These are results for the wired checks in this ${real()?'repository assessment':'fixture snapshot'}, not a percentage of SOC 2 compliance.</p><button class="button" data-action="close-help">Got it</button></div>`;help.showModal();}
function download(data,name) {const blob=new Blob([JSON.stringify(data,null,2)+'\n'],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);notify('Download prepared.');}
document.addEventListener('click',async event=>{
  if(event.target.closest('.skip-link')){event.preventDefault();main.focus();return;}
  const control=event.target.closest('[data-control]');if(control){openDetail(control.dataset.control);return;}
  const filter=event.target.closest('[data-filter-status]');if(filter){filters.status=filter.dataset.filterStatus;render();document.querySelector(`[data-filter-status="${filters.status}"]`)?.focus();return;}
  const action=event.target.closest('[data-action]')?.dataset.action;if(!action)return;
  if(action==='queue')navigate('attention');
  if(action==='evidence')navigate('evidence');
  if(action==='unwired'){filters={query:'',status:'UNWIRED',domain:'all',progress:'all'};navigate('controls');}
  if(action==='clear'){filters={query:'',status:'all',domain:'all',progress:'all'};render();document.querySelector('#search')?.focus();}
  if(action==='close-detail')requestCloseDetail();
  if(action==='discard-edit'){help.close();pristineForm=null;detail.close();}
  if(action==='close-help')help.close();
  if(action==='scoring')scoring();
  if(action==='import')openImport();
  if(action==='assess')showWorkflow();
  if(action==='choose-file')document.querySelector('#import-file').click();
  if(action==='restore-review' && pendingImport){const data=pendingImport;pendingImport=null;help.close();await setReport(data.report,data.notes,true);notify(`Restored ${Object.keys(data.notes).length} saved ${Object.keys(data.notes).length===1?'action plan':'action plans'}. Check results are unchanged.`);}
  if(action==='export')download({format:'soc2-workspace-review-v1',exported_at:new Date().toISOString(),notice:real()?'Real GitHub repository assessment with local planning notes. Contains repository evidence; keep this file private. Notes do not change results. Not an audit opinion or certification.':'Synthetic fixture assessment with browser-local planning notes. Notes do not change measured verdicts. Not an audit opinion or certification.',report,review_notes:notes},real()?'soc2-repository-review.json':'soc2-review.json');
  if(action==='download-report')download(report,real()?'soc2-repository-report.json':'soc2-fixture-report.json');
  if(action==='reset'){
    help.innerHTML=`<div class="help-body"><h2 id="help-title">Reset this workspace?</h2><p>This clears review notes for the current report from this browser and reopens the bundled sample. Export your review first if you want to keep the notes.</p><div class="dialog-actions"><button class="button secondary" data-action="close-help">Keep working</button><button class="button" data-action="confirm-reset">Reset workspace</button></div></div>`;help.showModal();
  }
  if(action==='confirm-reset'){if(real())realReviews.delete(storageKey);if(!real()){try{localStorage.removeItem(storageKey);}catch{}}imported=false;help.close();await setReport(sample);navigate('overview');notify('Current report’s notes cleared. Sample restored.');}
});
function refreshBrief(selector, scroll = false) {
  saveSelection();
  main.innerHTML = caseView();
  main.querySelector(selector)?.focus({preventScroll: !scroll});
}
document.addEventListener('click',event=>{
  if (page !== 'case' || !canShowCase()) return;
  if (event.target.closest('#open-brief')) {
    briefOpen = true;
    refreshBrief('#brief-title', true);
    return;
  }
  if (event.target.closest('#owner-follow-up')) {
    returnedEvidence = 'matched';
    trial = 'matched';
    ownerFollowUp = true;
    mark = '';
    refreshBrief('#evidence-return', true);
    return;
  }
  const tick = event.target.closest('[data-mark]');
  if (tick && Object.hasOwn(marks,tick.dataset.mark)) {
    mark = tick.dataset.mark;
    refreshBrief(`[data-mark="${mark}"]`);
    return;
  }
  const preset = event.target.closest('[data-profile]');
  if (preset && Object.hasOwn(profiles,preset.dataset.profile)) {
    Object.assign(pilotAssumptions, {repositories:profiles[preset.dataset.profile].repositories, manualMinutes:25,collectorMinutes:10,setupHours:4});
    refreshBrief(`[data-profile="${preset.dataset.profile}"]`);
  }
});
document.addEventListener('change',event=>{
  const field = event.target;
  if (page !== 'case' || !canShowCase()) return;
  if (field.id === 'case-request') {
    selectedRequest = field.value;
    selectedAction = '';
    returnedEvidence = 'pending';
    trial = 'matched';
  } else if (field.name === 'evidence-action') {
    selectedAction = field.value;
    returnedEvidence = evidenceReturns[selectedAction] ? 'matched' : 'pending';
    trial = 'matched';
  } else if (field.id === 'evidence-return') {
    returnedEvidence = field.value;
    if (returnedEvidence !== 'pending' && (selectedRequest !== 'settings' || returnedEvidence !== 'exception')) trial = returnedEvidence;
  } else return;
  mark = '';
  ownerFollowUp = false;
  refreshBrief(field.id ? '#'+field.id : `[name="evidence-action"][value="${selectedAction}"]`);
});
document.addEventListener('input',e=>{if(e.target.id==='search'){filters.query=e.target.value;renderResults();}});
document.addEventListener('change',e=>{if(['status-filter','domain-filter','progress-filter'].includes(e.target.id)){const id=e.target.id;filters[{'status-filter':'status','domain-filter':'domain','progress-filter':'progress'}[id]]=e.target.value;render();document.getElementById(id)?.focus();}});
document.addEventListener('submit',e=>{if(e.target.id!=='review-form')return;e.preventDefault();const form=new FormData(e.target);notes[e.target.dataset.id]={owner:form.get('owner').trim(),progress:form.get('progress'),note:form.get('note').trim(),updated_at:new Date().toISOString()};if(!real()){try{localStorage.setItem(storageKey,JSON.stringify(notes));}catch{storageAvailable=false;}}const id=e.target.dataset.id;pristineForm=null;detail.close();render();(document.querySelector(`[data-control="${id}"]`)||document.querySelector('#progress-filter')||main).focus();notify(!real()&&storageAvailable?'Next action saved in this browser.':'Saved for this tab only. Export your review to keep it.');});
document.querySelector('#import-button').addEventListener('click',()=>openImport());
document.querySelector('#import-file').addEventListener('change',async e=>{
  const file=e.target.files[0];if(!file)return;
  try{
    if(file.size>2_000_000)throw new Error('Choose a JSON file smaller than 2 MB.');
    const data=parseWorkspaceImport(JSON.parse(await file.text()),{allowReal:localWorkspace});
    if(data.notes!==null){
      pendingImport=data;
      help.innerHTML=`<div class="help-body"><h2 id="help-title">Resume this saved review?</h2><p>This restores ${Object.keys(data.notes).length} ${Object.keys(data.notes).length===1?'action plan':'action plans'} with the report they belong to. It replaces this browser’s saved plans for that same report. Assessment results stay unchanged.</p><p>Imported reports stay open until reload. Export again to keep your latest work.</p><div class="dialog-actions"><button class="button secondary" data-action="close-help">Cancel</button><button class="button" data-action="restore-review">Resume review</button></div></div>`;
      if(!help.open)help.showModal();
      help.querySelector('[data-action="close-help"]').focus();
    }else{help.close();await setReport(data.report,null,true);notify('Report opened locally. Nothing was uploaded.');}
  }catch(error){pendingImport=null;openImport(error instanceof SyntaxError?'This file is not valid JSON. Your current workspace is unchanged.':error.message);}
  finally{e.target.value='';}
});
window.addEventListener('hashchange',()=>{const next=location.hash.slice(1);if(next==='main'){main.focus({preventScroll:true});return;}page=visibleNavItems().some(n=>n[0]===next)?next:(canShowCase()?'case':'overview');render();main.focus({preventScroll:true});window.scrollTo(0,0);});
for(const dialog of [detail,help])dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom){if(dialog===detail)requestCloseDetail();else dialog.close();}}});
try {const response=await fetch('./data/sample-report.json');if(!response.ok)throw new Error('Sample report could not be loaded.');sample=validateReport(await response.json());const target=location.hash.slice(1);page=visibleNavItems().some(n=>n[0]===target)?target:(canShowCase()?'case':'overview');if(new URLSearchParams(location.search).get('local')==='1'){if(!localWorkspace)throw new Error('Real reports open only in the local workspace.');const localResponse=await fetch('./local-report.json');if(!localResponse.ok)throw new Error('Local report could not be loaded. Restart the local server with --report.');const localData=parseWorkspaceImport(await localResponse.json(),{allowReal:true});await setReport(localData.report,localData.notes);}else await setReport(sample);}catch(error){main.innerHTML=`<div class="empty"><h1>Unable to open the workspace</h1><p>${h(error.message)}</p><p>Serve the demo through HTTP, or use the hosted GitHub Pages demo.</p><a class="button secondary" href="${repo}">Open repository</a></div>`;}
