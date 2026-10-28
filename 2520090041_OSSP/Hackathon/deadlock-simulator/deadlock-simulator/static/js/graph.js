/* Resource Allocation Graph rendering (SVG) with pan + wheel zoom. */
function drawGraph(S, o = {}) {
  const m = S.matrices, dead = new Set(S.multi.deadlocked), done = new Set(o.finished || []);
  const cyc = new Set(S.single.cycle || []);
  if (!m.pids.length && !m.res.length) return '<div class="empty">Nothing to draw yet. Load a scenario or add processes/resources.</div>';
  const px = {}, rx = {}, W = Math.max(m.pids.length, m.res.length, 3) * 120;
  const pos = (i, n) => n === 1 ? W / 2 : 70 + i * (W - 140) / (n - 1);
  m.pids.forEach((p, i) => px[p] = pos(i, m.pids.length));
  m.res.forEach((r, i) => rx[r] = pos(i, m.res.length));
  let e = '';
  const line = (x1, y1, x2, y2, cls, label, color, dash) => {
    const dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy) || 1, sx = x1 + dx / L * 28, sy = y1 + dy / L * 28, ex = x2 - dx / L * 30, ey = y2 - dy / L * 30;
    return `<line x1="${sx}" y1="${sy}" x2="${ex}" y2="${ey}" stroke="${color}" stroke-width="2" ${dash ? 'stroke-dasharray="6 4"' : ''} marker-end="url(#ar${color.slice(1)})"/>
      <text x="${(sx + ex) / 2 + 6}" y="${(sy + ey) / 2 - 4}" font-size="12" fill="${color}">${label}</text>`;
  };
  m.pids.forEach((p, i) => m.res.forEach((r, k) => {
    const rq = m.request[i][k], al = m.alloc[i][k], bad = dead.has(p);
    if (rq) e += line(px[p], 70, rx[r], 270, 'req', `request ${rq}`, bad ? '#b42318' : '#a35a00', true);
    if (al) e += line(rx[r], 270, px[p], 70, 'alloc', `alloc ${al}`, bad ? '#b42318' : '#2457c5', false);
  }));
  const nodesP = m.pids.map(p => {
    const bad = dead.has(p), ok = done.has(p);
    return `<circle cx="${px[p]}" cy="70" r="28" fill="${bad ? '#fdeceb' : ok ? '#e6f5ed' : '#fff'}" stroke="${bad ? '#b42318' : ok ? '#16794a' : '#1c2433'}" stroke-width="${bad || cyc.has(p) ? 3 : 2}"/>
      <text x="${px[p]}" y="75" text-anchor="middle" font-weight="700">${p}</text>`;
  }).join('');
  const nodesR = m.res.map((r, k) => `<rect x="${rx[r] - 32}" y="250" width="64" height="40" rx="4" fill="#fff" stroke="#1c2433" stroke-width="2"/>
    <text x="${rx[r]}" y="268" text-anchor="middle" font-weight="700">${r}</text>
    <text x="${rx[r]}" y="283" text-anchor="middle" font-size="11">${m.available[k]}/${m.total[k]} free</text>`).join('');
  const mk = c => `<marker id="ar${c.slice(1)}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="${c}"/></marker>`;
  const legend = `<g font-size="11"><circle cx="20" cy="330" r="8" fill="#fff" stroke="#000"/><text x="34" y="334">process</text><rect x="100" y="322" width="16" height="16" fill="#fff" stroke="#000"/><text x="122" y="334">resource (free/total)</text>
    <line x1="260" y1="330" x2="290" y2="330" stroke="#a35a00" stroke-dasharray="6 4" stroke-width="2"/><text x="296" y="334">request P&#8594;R</text>
    <line x1="380" y1="330" x2="410" y2="330" stroke="#2457c5" stroke-width="2"/><text x="416" y="334">allocation R&#8594;P</text><text x="520" y="334" fill="#b42318">red = deadlocked</text></g>`;
  return `<svg class="graph" id="rag" viewBox="0 0 ${W} 350"><defs>${mk('#b42318')}${mk('#a35a00')}${mk('#2457c5')}</defs><g id="vp">${e}${nodesP}${nodesR}${legend}</g></svg>
    <p class="note">Drag to pan, mouse wheel to zoom. Processes are circles, resources are rectangles.</p>`;
}
function attachPanZoom() {
  const svg = document.getElementById('rag'); if (!svg) return;
  const vp = svg.querySelector('#vp'); let x = 0, y = 0, k = 1, drag = null;
  const up = () => vp.setAttribute('transform', `translate(${x},${y}) scale(${k})`);
  svg.onwheel = ev => { ev.preventDefault(); k = Math.min(3, Math.max(.4, k * (ev.deltaY < 0 ? 1.1 : .9))); up(); };
  svg.onpointerdown = ev => { drag = [ev.clientX - x, ev.clientY - y]; svg.setPointerCapture(ev.pointerId); };
  svg.onpointermove = ev => { if (drag) { x = ev.clientX - drag[0]; y = ev.clientY - drag[1]; up(); } };
  svg.onpointerup = () => drag = null;
}
