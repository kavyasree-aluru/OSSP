/* Step-by-step playground: walks through the detection algorithm's recorded steps. */
const Sim = { idx: 0, timer: null };
function simSteps() { return S.multi.steps || []; }
function simStop() { clearInterval(Sim.timer); Sim.timer = null; }
function simStep() { if (Sim.idx < simSteps().length) Sim.idx++; else simStop(); render(); }
function simPlay() { if (Sim.timer) return simStop(); Sim.timer = setInterval(() => { if (Sim.idx >= simSteps().length) { simStop(); render(); } else simStep(); }, 1500); render(); }
function simReset() { simStop(); Sim.idx = 0; render(); }
function playgroundHTML() {
  const st = simSteps(), shown = st.slice(0, Sim.idx), fin = shown.length ? shown[shown.length - 1].finished : [];
  return `<div class="row"><select id="pgsc">${scOpts()}</select><button data-act="loadsc" data-sel="pgsc" class="p">Load scenario</button>
    <button data-act="simplay">${Sim.timer ? 'Pause' : 'Start'}</button><button data-act="simstep">Step</button><button data-act="simreset">Reset</button></div>
    <p class="note">Each step shows what the detection algorithm checks (Request &le; Work?) and why it acts. Step ${Sim.idx}/${st.length}.</p>
    ${drawGraph(S, { finished: fin })}
    <h3>Timeline</h3>${shown.length ? shown.map((s, i) => `<div class="step"><b>Step ${i + 1}.</b> ${esc(s.text)}</div>`).join('') : '<div class="empty">Press Step or Start.</div>'}`;
}
