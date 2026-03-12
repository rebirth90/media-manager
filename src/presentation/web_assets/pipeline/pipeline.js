const SVG = document.getElementById('arrows-svg');
const PAGE = document.getElementById('page');

let _pipelineState = {};

const ARROW_PAIRS = [
  ['p1-input', 'p1-queue', 'a-p1-inq'],
  ['p1-queue', 'p2-dequeue', 'a-p1-p2'],
  ['p2-dequeue', 'p2-pass', 'a-p2-pass'],
  ['p2-pass', 'p3-router', 'a-p2-p3'],
  ['p3-router', 'p3-movie', 'a-p3-mov'],
  ['p3-router', 'p3-tv', 'a-p3-tv'],
  ['p3-movie', 'p4-movie', 'a-p3-p4m'],
  ['p3-tv', 'p4-tv', 'a-p3-p4t'],
  ['p4-movie', 'p5-check', 'a-p4-p5m'],
  ['p4-tv', 'p5-check', 'a-p4-p5t'],
  ['p5-check', 'p5-fail', 'a-p5-fail'],
  ['p5-check', 'p5-pass', 'a-p5-pass'],
  ['p5-fail', 'p2-dequeue', 'a-p5-loop'],
  ['p5-pass', 'p6-discovery', 'a-p5-p6'],
  ['p6-discovery', 'p6-vobsub', 'a-p6-vob'],
  ['p6-discovery', 'p6-text', 'a-p6-txt'],
  ['p6-vobsub', 'p7-heuristics', 'a-p6-p7v'],
  ['p6-text', 'p7-heuristics', 'a-p6-p7t'],
  ['p7-heuristics', 'p7-audio', 'a-p7-ha'],
  ['p7-audio', 'p7-tiers', 'a-p7-at'],
  ['p7-tiers', 'p7-outcome', 'a-p7-to'],
  ['p7-outcome', 'p8-relocate', 'a-p7-p8'],
  ['p8-relocate', 'p8-movie', 'a-p8-rm'],
  ['p8-relocate', 'p8-tv', 'a-p8-rt'],
  ['p8-movie', 'p8-cleanup', 'a-p8-mc'],
  ['p8-tv', 'p8-cleanup', 'a-p8-tc'],
  ['p8-cleanup', 'p8-complete', 'a-p8-cc'],
];

let _activeArrows = new Set();
let _failedArrows = new Set();
let _inactiveArrows = new Set();

window.setPipelineState = function (stages) {
  _pipelineState = stages || {};

  let latestId = null;
  let latestNum = -1;

  Object.entries(_pipelineState).forEach(([id, state]) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove('stage-success', 'stage-fail', 'stage-skip');
    if (state === 'pass') {
      el.classList.add('stage-success');
      let m = id.match(/p(\d+)/);
      if (m) {
        let num = parseInt(m[1]);
        if (num >= latestNum) {
          latestNum = num;
          latestId = id;
        }
      }
    }
    else if (state === 'fail') el.classList.add('stage-fail');
    else if (state === 'skip') el.classList.add('stage-skip');
  });

  document.querySelectorAll('.hg-icon').forEach(e => e.remove());

  const hasFail = Object.values(_pipelineState).includes('fail');
  if (latestId && latestId !== 'p8-complete' && !hasFail) {
    const targetEl = document.getElementById(latestId);
    if (targetEl) {
      const titleEl = targetEl.querySelector('.sc-title');
      if (titleEl) {
        titleEl.insertAdjacentHTML('beforeend', '<svg class="hg-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20"/><path d="M5 2h14"/><path d="M5 22h14"/><path d="M5 6l7 6 7-6"/><path d="M5 18l7-6 7 6"/></svg>');
      }
    }
  }

  _activeArrows.clear();
  _failedArrows.clear();
  _inactiveArrows.clear();

  ARROW_PAIRS.forEach(([from, to, key]) => {
    const fs = _pipelineState[from] || 'pending';
    const ts = _pipelineState[to] || 'pending';

    if (fs === 'fail' || ts === 'fail') {
      _failedArrows.add(key);
    } else if (fs === 'pass' && ts === 'pass') {
      _activeArrows.add(key);
    } else if (fs === 'skip' || ts === 'skip') {
      _inactiveArrows.add(key);
    }
  });

  safeDraw();
};

window.resetPipelineState = function () {
  window.setPipelineState({});
};

let _zoom = 1, _naturalW = 0, _naturalH = 0;

function applyZoom() {
  PAGE.style.zoom = 1;
  _naturalW = PAGE.scrollWidth;
  _naturalH = PAGE.scrollHeight;
  const avail = document.documentElement.clientWidth;
  _zoom = _naturalW > avail ? avail / _naturalW : 1;
  PAGE.style.zoom = _zoom;
}

function G(id) {
  const el = document.getElementById(id);
  if (!el) return null;
  const pg = PAGE.getBoundingClientRect();
  const er = el.getBoundingClientRect();
  if (er.width === 0 || er.height === 0) return null;
  const left = (er.left - pg.left) / _zoom;
  const top = (er.top - pg.top) / _zoom;
  const right = (er.right - pg.left) / _zoom;
  const bottom = (er.bottom - pg.top) / _zoom;
  const w = er.width / _zoom;
  const h = er.height / _zoom;
  return { top, bottom, left, right, cx: left + w / 2, cy: top + h / 2, w, h };
}

function mp(d, stroke, dashed, marker, arrowKey) {
  const ns = 'http://www.w3.org/2000/svg';
  const p = document.createElementNS(ns, 'path');
  const active = arrowKey && _activeArrows.has(arrowKey);
  const failed = arrowKey && _failedArrows.has(arrowKey);
  const inactive = arrowKey && _inactiveArrows.has(arrowKey);

  p.setAttribute('d', d);

  if (active) {
    p.setAttribute('stroke', '#4ade80');
    p.setAttribute('opacity', '1');
  } else if (failed) {
    p.setAttribute('stroke', '#f43f5e');
    p.setAttribute('opacity', '1');
  } else {
    p.setAttribute('stroke', stroke);
    if (inactive) {
      p.classList.add('arrow-inactive');
    } else {
      p.setAttribute('opacity', '0.75');
    }
  }

  p.setAttribute('stroke-width', (active || failed) ? '3px' : '1.6px');
  p.setAttribute('fill', 'none');
  p.setAttribute('stroke-linecap', 'square');
  p.setAttribute('stroke-linejoin', 'miter');

  if (dashed || active) p.setAttribute('stroke-dasharray', active ? '10 5' : '5 4');
  if (active) p.style.animation = 'march 1s linear infinite';

  if (marker) {
    if (active) p.setAttribute('marker-end', `url(#m-green)`);
    else if (failed) p.setAttribute('marker-end', `url(#m-red)`);
    else p.setAttribute('marker-end', `url(#${marker})`);
  }
  SVG.appendChild(p);
}

function colOf(id) { return document.getElementById(id).closest('.phase-col'); }

function gapCX(id) {
  const gap = colOf(id).nextElementSibling;
  if (!gap) return null;
  const pg = PAGE.getBoundingClientRect();
  const gr = gap.getBoundingClientRect();
  return ((gr.left + gr.right) / 2 - pg.left) / _zoom;
}
function colRX(id) {
  return (colOf(id).getBoundingClientRect().right - PAGE.getBoundingClientRect().left) / _zoom;
}
function colLX(id) {
  return (colOf(id).getBoundingClientRect().left - PAGE.getBoundingClientRect().left) / _zoom;
}

function V(fromId, toId, c, m, x, arrowKey) {
  const f = G(fromId), t = G(toId);
  if (!f || !t) return;
  const px = (x !== undefined) ? x : f.cx;
  mp(`M ${px} ${f.bottom + 4} L ${px} ${t.top - 7}`, c, false, m, arrowKey);
}

function FWD(fromId, toId, c, m, gapOff, yFromFrac, yToFrac, exitSide, arrowKey) {
  const f = G(fromId), t = G(toId);
  if (!f || !t) return;
  const gx = gapCX(fromId) + (gapOff || 0);
  const yE = t.top + t.h * (yToFrac !== undefined ? yToFrac : 0.5);

  if (exitSide === 'bottom') {
    const yS = f.bottom + 10;
    mp(`M ${f.cx} ${f.bottom + 2} L ${f.cx} ${yS} L ${gx} ${yS} L ${gx} ${yE} L ${t.left - 2} ${yE}`, c, false, m, arrowKey);
  } else {
    const yS = f.top + f.h * (yFromFrac !== undefined ? yFromFrac : 0.5);
    mp(`M ${f.right + 2} ${yS} L ${gx} ${yS} L ${gx} ${yE} L ${t.left - 2} ${yE}`, c, false, m, arrowKey);
  }
}

function SKIP(fromId, toId, c, m, gOff, arrowKey) {
  const f = G(fromId), t = G(toId);
  if (!f || !t) return;
  const gx = colRX(fromId) + 10 + (gOff || 0);
  mp(`M ${f.right + 2} ${f.cy} L ${gx} ${f.cy} L ${gx} ${t.top - 14} L ${t.cx} ${t.top - 14} L ${t.cx} ${t.top - 2}`, c, false, m, arrowKey);
}

function LOOP_UP(fromId, toId, c, m, xOff, arrowKey) {
  const f = G(fromId), t = G(toId);
  if (!f || !t) return;
  const gx = colRX(fromId) + 26;
  const tx = t.cx + (xOff || 0);
  mp(`M ${f.right + 2} ${f.cy} L ${gx} ${f.cy} L ${gx} ${t.top - 22} L ${tx} ${t.top - 22} L ${tx} ${t.top - 2}`, c, true, m, arrowKey);
}

function LOOP_BACK(fromId, toId, c, m, laneOff, xOff, arrowKey) {
  const f = G(fromId), t = G(toId);
  if (!f || !t) return;

  let maxB = 0;
  document.querySelectorAll('.sc').forEach(sc => {
    const r = sc.getBoundingClientRect();
    const pgr = PAGE.getBoundingClientRect();
    // Divides by _zoom so loop coordinates align perfectly on small screens
    const left = (r.left - pgr.left) / _zoom;
    const right = (r.right - pgr.left) / _zoom;

    if (right >= t.left - 20 && left <= f.right + 20) {
      const b = (r.bottom - pgr.top) / _zoom;
      if (b > maxB) maxB = b;
    }
  });

  const laneY = maxB + 24 + (laneOff || 0) * 18;
  const rx = colRX(fromId) + 26;
  const lx = colLX(toId) - 18;
  const tx = t.cx + (xOff || 0);

  mp(`M ${f.right + 2} ${f.cy} L ${rx} ${f.cy} L ${rx} ${laneY} L ${lx} ${laneY} L ${lx} ${t.top - 22} L ${tx} ${t.top - 22} L ${tx} ${t.top - 2}`, c, true, m, arrowKey);
}

function draw() {
  [...SVG.querySelectorAll('path')].forEach(e => e.remove());

  // Removed the safeH distortion which was forcefully shrinking the SVG scaling
  SVG.setAttribute('width', _naturalW);
  SVG.setAttribute('height', _naturalH);
  SVG.setAttribute('viewBox', `0 0 ${_naturalW} ${_naturalH}`);

  const T = 'rgba(45,212,191,.85)';
  const Y = 'rgba(251,191,36,.85)';
  const Re = 'rgba(244,63,94,.85)';
  const B = 'rgba(59,130,246,.85)';
  const Pu = 'rgba(192,132,252,.85)';

  V('p1-input', 'p1-queue', T, 'm-teal', undefined, 'a-p1-inq');
  FWD('p1-queue', 'p2-dequeue', T, 'm-teal', undefined, undefined, undefined, undefined, 'a-p1-p2');
  V('p2-dequeue', 'p2-pass', T, 'm-teal', undefined, 'a-p2-pass');
  FWD('p2-pass', 'p3-router', T, 'm-teal', undefined, undefined, undefined, undefined, 'a-p2-p3');

  const m3 = G('p3-movie'), tv3 = G('p3-tv');
  V('p3-router', 'p3-movie', B, 'm-blue', m3.cx, 'a-p3-mov');
  V('p3-router', 'p3-tv', Y, 'm-yellow', tv3.cx, 'a-p3-tv');

  FWD('p3-movie', 'p4-movie', B, 'm-blue', -8, 0.5, 0.35, 'bottom', 'a-p3-p4m');
  FWD('p3-tv', 'p4-tv', Y, 'm-yellow', 8, 0.5, 0.65, undefined, 'a-p3-p4t');
  FWD('p4-movie', 'p5-check', B, 'm-blue', -8, 0.5, 0.32, undefined, 'a-p4-p5m');
  FWD('p4-tv', 'p5-check', Y, 'm-yellow', 8, 0.5, 0.68, undefined, 'a-p4-p5t');

  V('p5-check', 'p5-fail', Re, 'm-red', undefined, 'a-p5-fail');
  SKIP('p5-check', 'p5-pass', T, 'm-teal', undefined, 'a-p5-pass');
  LOOP_BACK('p5-fail', 'p2-dequeue', Re, 'm-red', 0, -15, 'a-p5-loop');
  FWD('p5-pass', 'p6-discovery', T, 'm-teal', undefined, undefined, undefined, undefined, 'a-p5-p6');

  V('p6-discovery', 'p6-vobsub', Pu, 'm-purple', undefined, 'a-p6-vob');
  SKIP('p6-discovery', 'p6-text', Pu, 'm-purple', undefined, 'a-p6-txt');
  FWD('p6-vobsub', 'p7-heuristics', Pu, 'm-purple', -8, 0.5, 0.32, undefined, 'a-p6-p7v');
  FWD('p6-text', 'p7-heuristics', Pu, 'm-purple', 8, 0.5, 0.68, undefined, 'a-p6-p7t');

  V('p7-heuristics', 'p7-audio', T, 'm-teal', undefined, 'a-p7-ha');
  V('p7-audio', 'p7-tiers', Pu, 'm-purple', undefined, 'a-p7-at');
  V('p7-tiers', 'p7-outcome', Y, 'm-yellow', undefined, 'a-p7-to');
  FWD('p7-outcome', 'p8-relocate', T, 'm-teal', undefined, undefined, undefined, undefined, 'a-p7-p8');

  const m8 = G('p8-movie'), tv8 = G('p8-tv');
  V('p8-relocate', 'p8-movie', B, 'm-blue', m8.cx, 'a-p8-rm');
  V('p8-relocate', 'p8-tv', Y, 'm-yellow', tv8.cx, 'a-p8-rt');
  V('p8-movie', 'p8-cleanup', B, 'm-blue', m8.cx, 'a-p8-mc');
  V('p8-tv', 'p8-cleanup', Y, 'm-yellow', tv8.cx, 'a-p8-tc');
  V('p8-cleanup', 'p8-complete', T, 'm-teal', undefined, 'a-p8-cc');
}

function safeDraw() {
  applyZoom();
  requestAnimationFrame(() => requestAnimationFrame(() => {
    const testCard = document.querySelector('.sc');
    if (testCard && testCard.getBoundingClientRect().width > 0) draw();

    let maxB = 0;
    document.querySelectorAll('.sc').forEach(sc => {
      const r = sc.getBoundingClientRect();
      if (r.bottom > maxB) maxB = r.bottom;
    });
    const pageTop = PAGE.getBoundingClientRect().top;
    if (maxB > 0) {
      const actualHeight = Math.ceil(maxB - pageTop);
      document.title = "PIPELINE_HEIGHT:" + actualHeight;
    }
  }));
}

document.fonts.ready.then(() => {
  safeDraw();
  const ro = new ResizeObserver(safeDraw);
  ro.observe(PAGE);
  ro.observe(document.body);
});

window.addEventListener('resize', safeDraw);
setTimeout(safeDraw, 300);