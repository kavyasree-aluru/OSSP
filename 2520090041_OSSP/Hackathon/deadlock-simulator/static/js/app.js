const PAGES = ['Dashboard', 'Process Manager', 'Resource Manager', 'Allocation Graph', 'Deadlock Detection', 'Recovery Center', "Banker's Algorithm", 'Simulation Playground', 'History & Reports', 'Learn / About'];
let S = null, page = 0, SC = [], REC = null, LASTREC = null, WHAT = null, CH = null;
const $ = s => document.querySelector(s), esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const val = id => $('#' + id).value, num = id => parseInt(val(id), 10);

async function api(path, method = 'GET', body) {
  const r = await fetch('/api' + path, { method, headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined });
  const j = await r.json(); if (!r.ok) throw new Error(j.error || 'Request failed'); return j;
}
function toast(msg, err) { const t = $('#toast'); t.textContent = msg; t.style.background = err ? '#b42318' : '#16794a'; t.style.display = 'block'; clearTimeout(t.h); t.h = setTimeout(() => t.style.display = 'none', 3500); }
async function act(fn, okMsg) {
  try { const r = await fn(); S = r && r.state ? r.state : (r && r.matrices ? r : await api('/state')); if (okMsg) toast(okMsg); render(); return r; }
  catch (e) { toast(e.message, true); }
}
function status(p) {
  const v = S.processes[p]; if (v.status !== 'active') return `<span class="tag t-mut">${v.status}</span>`;
  if (S.multi.deadlocked.includes(p)) return '<span class="tag t-bad">DEADLOCKED</span>';
  if (Object.values(v.req).some(x => x)) return '<span class="tag t-warn">waiting</span>';
  return '<span class="tag t-ok">active</span>';
}
const vec = (o) => Object.entries(o).map(([k, v]) => `${k}:${v}`).join(' ') || '-';
const scOpts = () => SC.map(s => `<option value="${s.id}">${esc(s.name)}</option>`).join('');
const resOpts = () => Object.keys(S.resources).map(r => `<option>${esc(r)}</option>`).join('');
const procOpts = () => S.matrices.pids.map(p => `<option>${esc(p)}</option>`).join('');

function procTable(actions) {
  const ids = Object.keys(S.processes); if (!ids.length) return '<div class="empty">No processes yet. Add one or load a scenario.</div>';
  return `<table><tr><th>Process</th><th>Status</th><th>Max</th><th>Allocated</th><th>Outstanding request</th><th>Priority</th><th>Cost</th><th>Progress</th>${actions ? '<th></th>' : ''}</tr>` +
    ids.map(p => { const v = S.processes[p]; return `<tr><td><b>${esc(p)}</b></td><td>${status(p)}</td><td>${vec(v.max)}</td><td>${vec(v.alloc)}</td><td>${vec(v.req)}</td><td>${v.priority}</td><td>${v.cost}</td><td>${v.progress}</td>
    ${actions ? `<td><button class="d" data-act="rmproc" data-pid="${esc(p)}">Remove</button></td>` : ''}</tr>`; }).join('') + '</table>';
}
function resTable(actions) {
  const rs = Object.keys(S.resources); if (!rs.length) return '<div class="empty">No resource types yet.</div>';
  return '<table><tr><th>Resource</th><th>Total</th><th>Allocated</th><th>Available</th>' + (actions ? '<th>Change total</th><th></th>' : '') + '</tr>' +
    rs.map(r => `<tr><td><b>${esc(r)}</b></td><td>${S.resources[r]}</td><td>${S.resources[r] - S.available[r]}</td><td>${S.available[r]}</td>${actions ? `<td><input type="number" min="1" id="t_${esc(r)}" value="${S.resources[r]}"> <button data-act="settotal" data-r="${esc(r)}">Set</button></td><td><button class="d" data-act="rmres" data-r="${esc(r)}">Delete</button></td>` : ''}</tr>`).join('') + '</table>';
}
const matTable = (names, cols, rows) => `<table><tr><th></th>${cols.map(c => `<th>${esc(c)}</th>`).join('')}</tr>${rows.map((r, i) => `<tr><td><b>${esc(names[i])}</b></td>${r.map(x => `<td>${x}</td>`).join('')}</tr>`).join('')}</table>`;

const PAGES_HTML = [
  // Dashboard
  () => { const P = Object.values(S.processes), c = s => P.filter(p => p.status === s).length, dead = S.multi.deadlocked.length,
      wait = P.filter(p => p.status === 'active' && Object.values(p.req).some(x => x)).length - dead;
    return `<div class="grid">${[['Processes (active)', c('active')], ['Resource types', Object.keys(S.resources).length], ['Waiting', Math.max(0, wait)], ['Deadlocked', dead], ['Completed', c('completed')], ['Terminated', c('terminated')]]
      .map(([k, v]) => `<div class="card stat"><b>${v}</b><span>${k}</span></div>`).join('')}</div>
    <div class="card"><div class="row"><b>Load scenario:</b><select id="dsc">${scOpts()}</select><button class="p" data-act="loadsc" data-sel="dsc">Load</button><button data-act="detect">Run detection</button><button class="d" data-act="reset">Reset everything</button></div>
    <p>Deadlock Risk Indicator: <span class="tag ${S.risk.score >= 60 ? 't-bad' : S.risk.score >= 30 ? 't-warn' : 't-ok'}">${S.risk.score}/100 ${S.risk.label}</span>
    <span class="note">${S.risk.heuristic ? 'Heuristic only (waiting ratio, contention, wait-for cycles) - not a probability.' : 'Confirmed by the detection algorithm.'}</span></p></div>
    <div class="card"><h3>Processes</h3>${procTable()}</div><div class="card"><h3>Resources</h3>${resTable()}</div>
    <div class="card"><h3>Recovery history</h3>${(LASTREC ? `<p>${esc(LASTREC.message)}</p>` : '<span class="note">No recoveries yet.</span>')}</div>`; },
  // Process manager
  () => `<div class="card"><h3>Add process</h3>${Object.keys(S.resources).length ? `<div class="row"><input id="np" placeholder="P1" style="width:70px">${Object.keys(S.resources).map(r => `max ${esc(r)} <input type="number" min="0" class="mx" data-r="${esc(r)}" value="0" style="width:60px">`).join('')}
    priority <input id="npr" type="number" min="1" value="1" style="width:60px"> cost <input id="nco" type="number" min="1" value="1" style="width:60px"><button class="p" data-act="addproc">Add</button></div>` : '<div class="empty">Create a resource type first.</div>'}</div>
    <div class="card"><h3>Request / release</h3>${S.matrices.pids.length ? `<div class="row"><select id="rp">${procOpts()}</select><select id="rr">${resOpts()}</select><input id="rn" type="number" min="1" value="1">
    <button class="p" data-act="request">Request</button><button data-act="release">Release</button><button data-act="finish">Complete process</button></div><p class="note">Requests that cannot be met become pending (the process waits). Requests above the declared maximum claim are rejected.</p>` : '<div class="empty">No active processes.</div>'}</div>
    <div class="card">${procTable(true)}</div>`,
  // Resource manager
  () => `<div class="card"><h3>Add resource type</h3><div class="row"><input id="nr" placeholder="R1" style="width:80px"> instances <input id="nrc" type="number" min="1" value="1"><button class="p" data-act="addres">Add</button></div></div><div class="card">${resTable(true)}</div>`,
  // Graph
  () => `<div class="card"><h3>Resource Allocation Graph</h3>${drawGraph(S)}</div><div class="card"><h3>Wait-for dependencies</h3>${S.single.edges.length ? '<ul>' + S.single.edges.map(e => `<li>${esc(e.from)} &rarr; ${esc(e.to)} (via ${esc(e.resource)})</li>`).join('') + '</ul>' : '<span class="note">No wait-for edges.</span>'}</div>`,
  // Detection
  () => { const s = S.single, m = S.multi; return `<div class="card"><div class="row"><button class="p" data-act="detect">Run detection (logs to history)</button></div>
    <h3>Algorithm 1: Wait-for graph cycle detection</h3><p><span class="tag ${s.verdict === 'deadlock' ? 't-bad' : s.verdict === 'inconclusive' ? 't-warn' : 't-ok'}">${s.verdict.replace('_', ' ')}</span> ${esc(s.note)}</p>
    ${s.path.length ? '<p><b>Dependency path:</b></p>' + s.path.map(p => `<div class="step">${esc(p)}</div>`).join('') : ''}
    <h3>Algorithm 2: Multiple-instance detection (Work / Finish)</h3>
    <p>Available: <code>${vec(S.available)}</code> &nbsp; Verdict: ${m.has_deadlock ? `<span class="tag t-bad">DEADLOCK: ${m.deadlocked.join(', ')}</span>` : '<span class="tag t-ok">no deadlock</span>'}</p>
    <p class="note">Waiting but able to finish: ${m.waiting.join(', ') || 'none'}. Deadlocked processes can never finish; merely waiting ones will once resources are released.</p>
    ${m.steps.map((x, i) => `<div class="step"><b>${i + 1}.</b> ${esc(x.text)}</div>`).join('') || '<div class="empty">No processes.</div>'}
    ${Object.entries(m.why_blocked).map(([p, w]) => `<div class="step" style="border-color:#b42318"><b>${esc(p)}</b> ${esc(w)}</div>`).join('')}</div>`; },
  // Recovery
  () => { const d = S.multi.deadlocked; return `<div class="card"><h3>Recovery Center</h3>${d.length ? `<div class="row"><button class="p" data-act="recommend">Recommend victim</button></div>` : '<div class="empty">No deadlock detected. Load "Recoverable Deadlock" to try recovery.</div>'}
    ${REC && REC.ranking && REC.ranking.length ? `<p>${esc(REC.message)}</p><table><tr><th>Process</th><th>Score</th><th>priority</th><th>held</th><th>cost</th><th>progress</th></tr>${REC.ranking.map(r => `<tr><td>${esc(r.pid)}</td><td><b>${r.score}</b></td><td>${r.parts.priority}</td><td>${r.parts.held}</td><td>${r.parts.cost}</td><td>${r.parts.progress}</td></tr>`).join('')}</table>
      <div class="row"><button class="d" data-act="recover" data-s="terminate" data-pid="${esc(REC.victim)}">Terminate ${esc(REC.victim)}</button>
      ${REC.preempt_option ? `<button data-act="recover" data-s="preempt" data-pid="${esc(REC.preempt_option.pid)}" data-r="${esc(REC.preempt_option.resource)}" data-n="${REC.preempt_option.count}">Preempt ${REC.preempt_option.count} x ${esc(REC.preempt_option.resource)} from ${esc(REC.preempt_option.pid)}</button>` : ''}
      <button class="d" data-act="recover" data-s="terminate_all">Terminate all deadlocked</button></div>` : ''}</div>
    ${LASTREC ? `<div class="card"><h3>Before vs after</h3><p><span class="tag ${LASTREC.resolved ? 't-ok' : 't-bad'}">${LASTREC.resolved ? 'RESOLVED' : 'NOT RESOLVED'}</span> ${esc(LASTREC.message)}</p>
      <table><tr><th></th><th>Deadlocked</th><th>Available</th><th>Allocated</th><th>Active processes</th></tr>${['before', 'after'].map(k => `<tr><td><b>${k}</b></td><td>${LASTREC[k].deadlocked.join(', ') || 'none'}</td><td>${vec(LASTREC[k].available)}</td><td>${vec(LASTREC[k].allocated)}</td><td>${LASTREC[k].active}</td></tr>`).join('')}</table>
      <p class="note">Affected: ${LASTREC.affected.join(', ')}. Resources freed/preempted: ${vec(LASTREC.freed)}.</p></div>` : ''}
    <div class="card"><h3>What-if analysis (does not change the real state)</h3>${S.matrices.pids.length ? `<div class="row"><select id="wa"><option value="terminate">Terminate process</option><option value="preempt">Preempt resource</option><option value="add_instance">Add resource instance(s)</option><option value="cancel_request">Cancel request</option></select>
      <select id="wp">${procOpts()}</select><select id="wr">${resOpts()}</select><input id="wn" type="number" min="1" value="1"><button class="p" data-act="whatif">Simulate</button></div>` : '<div class="empty">No processes.</div>'}
      ${WHAT ? `<p><b>${esc(WHAT.text)}</b> Before: ${WHAT.before.deadlocked.join(', ') || 'none'} &rarr; After: ${WHAT.after.deadlocked.join(', ') || 'none'}.</p>` : ''}</div>`; },
  // Banker
  () => { const b = S.banker, m = S.matrices; return `<div class="card"><h3>Banker's safety algorithm (avoidance)</h3><div class="row"><select id="bsc">${scOpts()}</select><button class="p" data-act="loadsc" data-sel="bsc">Load</button></div>
    ${b.error ? `<p class="tag t-bad">${esc(b.error)}</p>` : m.pids.length ? `<p><span class="tag ${b.safe ? 't-ok' : 't-bad'}">${b.safe ? 'SAFE' : 'UNSAFE'}</span> ${b.safe ? 'Safe sequence: <b>' + b.sequence.join(' &rarr; ') + '</b>' : ''}</p><p class="note">${esc(b.note)}</p>
    <h4>Max</h4>${matTable(m.pids, m.res, m.max)}<h4>Allocation</h4>${matTable(m.pids, m.res, m.alloc)}<h4>Need = Max &minus; Allocation</h4>${matTable(m.pids, m.res, b.need)}${b.steps.map(x => `<div class="step">${esc(x.text)}</div>`).join('')}` : '<div class="empty">No processes.</div>'}
    <p class="note"><b>Detection</b> finds an existing deadlock; <b>avoidance</b> (Banker's) refuses states that might lead to one; a <b>cycle</b> is only a graph pattern. Unsafe &ne; deadlocked.</p></div>`; },
  () => `<div class="card"><h3>Simulation Playground</h3>${playgroundHTML()}</div>`,
  // History
  () => `<div class="card"><h3>History & Reports</h3><div class="row"><a href="/api/export/events.csv"><button>Export event log (CSV)</button></a><a href="/api/export/state.csv"><button>Export state (CSV)</button></a><a href="/report" target="_blank"><button class="p">Printable report</button></a></div>
    <div id="hist"><p class="note">Loading...</p></div></div>`,
  // Learn
  () => `<div class="card"><h3>Learn</h3><p><b>Coffman conditions</b> (all four needed): mutual exclusion, hold and wait, no preemption, circular wait.</p>
    <p><b>Detection:</b> let the system reach any state, then check for deadlock (wait-for graph, or Work/Finish for multiple instances). <b>Avoidance:</b> Banker's algorithm only grants requests leading to safe states. <b>Recovery:</b> terminate processes or preempt resources, then re-check.</p>
    <p><b>Cycle vs deadlock:</b> a cycle always means deadlock with single-instance resources; with multiple instances it is only necessary.</p></div>
    <div class="card"><h3>Challenge mode</h3>${!CH ? '<button class="p" data-act="challenge">Start challenge</button>' : `<p>A scenario is loaded (see the Allocation Graph / Dashboard tables). <b>Is it deadlocked?</b> (answer is hidden on this page until you guess; avoid other tabs)</p>
      ${matTable(S.matrices.pids, S.matrices.res, S.matrices.alloc.map((r, i) => r.map((x, k) => x + '/' + S.matrices.request[i][k])))}<p class="note">Cells show allocated/requested. Available: ${vec(S.available)}</p>
      ${CH.guess === null ? '<div class="row"><button data-act="guess" data-g="1">Deadlocked</button><button data-act="guess" data-g="0">Not deadlocked</button></div>' : `<p><span class="tag ${CH.guess === S.multi.has_deadlock ? 't-ok' : 't-bad'}">${CH.guess === S.multi.has_deadlock ? 'Correct!' : 'Not quite.'}</span> Algorithm result: ${S.multi.has_deadlock ? 'deadlocked: ' + S.multi.deadlocked.join(', ') : 'no deadlock'}. <button data-act="challenge">Next</button></p>`}`}</div>
    <div class="card"><h3>About</h3><p>Educational OSSP hackathon project. Algorithms run in the Flask backend (<code>backend/</code>); this UI only displays backend state. See README and docs/.</p></div>`
];

function render() {
  $('#nav').innerHTML = PAGES.map((p, i) => `<button class="${i === page ? 'on' : ''}" data-act="nav" data-i="${i}">${p}</button>`).join('');
  const d = S.multi.deadlocked;
  const hide = CH && CH.guess === null;
  $('#banner').innerHTML = hide ? '' : d.length ? `<div class="b bad">&#9888; DEADLOCK DETECTED: ${d.join(', ')}</div>` : (S.matrices.pids.length ? '<div class="b ok">&#10003; System state: no deadlock</div>' : '');
  $('#page').innerHTML = PAGES_HTML[page]();
  attachPanZoom();
  if (page === 8) api('/history').then(h => { const el = $('#hist'); if (el) el.innerHTML = `<h4>Detection & recovery records: ${h.records.length}</h4><table><tr><th>Time</th><th>Kind</th><th>Event</th></tr>${h.events.slice().reverse().slice(0, 200).map(e => `<tr><td>${e.time}</td><td>${e.kind}</td><td>${esc(e.message)}</td></tr>`).join('') || '<tr><td colspan=3 class="empty">No events yet.</td></tr>'}</table>`; });
}

document.addEventListener('click', async ev => {
  const b = ev.target.closest('[data-act]'); if (!b) return; const a = b.dataset.act, d = b.dataset;
  const rpn = () => ({ pid: val('rp'), resource: val('rr'), count: num('rn') });
  if (a === 'nav') { page = +d.i; Sim.idx = 0; simStop(); return render(); }
  if (a === 'loadsc') { Sim.idx = 0; simStop(); REC = LASTREC = WHAT = null; return act(() => api(`/scenarios/${val(d.sel)}/load`, 'POST'), 'Scenario loaded'); }
  if (a === 'reset') { if (!confirm('Clear all processes, resources and history?')) return; REC = LASTREC = null; return act(() => api('/reset', 'POST'), 'Reset'); }
  if (a === 'rmproc') { if (!confirm(`Remove ${d.pid}? Its resources are released.`)) return; return act(() => api('/processes/' + encodeURIComponent(d.pid), 'DELETE')); }
  if (a === 'rmres') { if (!confirm(`Delete resource ${d.r}?`)) return; return act(() => api('/resources/' + encodeURIComponent(d.r), 'DELETE')); }
  if (a === 'addres') return act(() => api('/resources', 'POST', { name: val('nr'), total: num('nrc') }), 'Resource added');
  if (a === 'settotal') return act(() => api('/resources/' + encodeURIComponent(d.r), 'PUT', { total: parseInt($('#t_' + d.r).value, 10) }), 'Updated');
  if (a === 'addproc') { const max = {}; document.querySelectorAll('.mx').forEach(i => max[i.dataset.r] = parseInt(i.value, 10)); return act(() => api('/processes', 'POST', { pid: val('np'), max, priority: num('npr'), cost: num('nco') }), 'Process added'); }
  if (a === 'request') return act(async () => { const r = await api('/request', 'POST', rpn()); toast(r.result === 'granted' ? 'Granted' : 'Blocked: process is now waiting'); return r; });
  if (a === 'release') return act(() => api('/release', 'POST', rpn()), 'Released');
  if (a === 'finish') return act(() => api('/finish', 'POST', { pid: val('rp') }), 'Process completed');
  if (a === 'detect') return act(() => api('/detect', 'POST'), 'Detection complete');
  if (a === 'recommend') { try { REC = await api('/recommend'); render(); } catch (e) { toast(e.message, true); } return; }
  if (a === 'recover') { if (!confirm('Execute this recovery action?')) return; return act(async () => { const r = await api('/recover', 'POST', { strategy: d.s, pid: d.pid, resource: d.r, count: d.n ? +d.n : undefined }); LASTREC = r.recovery; REC = null; return r; }, 'Recovery executed'); }
  if (a === 'whatif') { try { WHAT = await api('/whatif', 'POST', { action: val('wa'), pid: val('wp'), resource: val('wr'), count: num('wn') }); render(); } catch (e) { toast(e.message, true); } return; }
  if (a === 'simplay') return simPlay(); if (a === 'simstep') return simStep(); if (a === 'simreset') return simReset();
  if (a === 'challenge') { const ids = SC.filter(s => !s.id.startsWith('bankers')).map(s => s.id); CH = { guess: null }; return act(() => api(`/scenarios/${ids[Math.floor(Math.random() * ids.length)]}/load`, 'POST')); }
  if (a === 'guess') { CH.guess = d.g === '1'; return render(); }
});

(async () => { try { SC = await api('/scenarios'); S = await api('/state'); render(); } catch (e) { $('#page').innerHTML = `<div class="card">Could not reach the backend: ${esc(e.message)}</div>`; } })();
