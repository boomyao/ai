// Reusable visual building blocks shared by the scenes.
const C = (window.C = {});

const PAPER = '#ece5d6';
const GOLD = '#cfa95e';
const GOLD2 = '#f0d08a';
const RED = '#e5523f';
const MUTED = '#8b909b';
C.COL = { PAPER, GOLD, GOLD2, RED, MUTED, BLUE: '#7d9cc2', DIM: '#4a4f5b' };

// ---------------------------------------------------------------------------
// Containers

// An absolutely positioned SVG "layer" with an in/out envelope and optional
// slow zoom. Returns { svg, g, h } where g is the content group.
C.layer = (s, { at = s.t, until = Infinity, din = 0.6, dout = 0.6, w = E.W, h = E.H, x = 0, y = 0, zoom = null, parent = s.layer } = {}) => {
  const svg = E.s('svg', {
    width: w,
    height: h,
    viewBox: `0 0 ${w} ${h}`,
    style: { position: 'absolute', left: x + 'px', top: y + 'px', overflow: 'visible' },
  });
  const g = E.s('g');
  svg.append(g);
  parent.append(svg);
  const handle = s.fx(svg, {
    start: at,
    din,
    end: until,
    dout,
    update: (t, k) => {
      svg.style.opacity = k.toFixed(4);
      if (zoom) {
        const p = E.prog(t, zoom.at ?? at, zoom.dur ?? 10);
        const e = (zoom.ease || E.ease.inOut)(p);
        const sc = E.lerp(zoom.from ?? 1, zoom.to ?? 1.06, e);
        const cx = zoom.cx ?? w / 2;
        const cy = zoom.cy ?? h / 2;
        g.setAttribute('transform', `translate(${cx} ${cy}) scale(${sc.toFixed(4)}) translate(${-cx} ${-cy})`);
      }
    },
  });
  return { svg, g, h: handle };
};

// A div positioned at its centre with an envelope.
C.box = (s, { x = 960, y = 540, at = s.t, until = Infinity, din = 0.6, dout = 0.6, style = {}, cls = '', html = null, anim = 'rise', parent = s.layer } = {}) => {
  const el = E.h('div', { class: 'center ' + cls, style: { left: x + 'px', top: y + 'px', ...style } });
  if (html !== null) el.innerHTML = html;
  parent.append(el);
  const h = s.fx(el, {
    start: at,
    din,
    end: until,
    dout,
    update: (t, k) => {
      el.style.opacity = k.toFixed(4);
      if (anim === 'rise') {
        const e = E.ease.out(E.prog(t, at, din * 1.4));
        el.style.transform = `translateY(${((1 - e) * 28).toFixed(2)}px)`;
        el.style.filter = e < 0.98 ? `blur(${((1 - e) * 8).toFixed(2)}px)` : 'none';
      } else if (anim === 'pop') {
        const e = E.ease.back(E.prog(t, at, 0.45));
        el.style.transform = `scale(${E.lerp(0.6, 1, e).toFixed(4)})`;
      } else if (anim === 'zoom') {
        const e = E.ease.out(E.prog(t, at, din * 1.5));
        el.style.transform = `scale(${E.lerp(1.12, 1, e).toFixed(4)})`;
        el.style.filter = e < 0.98 ? `blur(${((1 - e) * 10).toFixed(2)}px)` : 'none';
      }
    },
  });
  el.h = h;
  return el;
};

// ---------------------------------------------------------------------------
// Line drawing: paths animate their stroke from 0 to full length.
// d: string | string[]; opts.at/dur/stagger/until; style overrides.
C.draw = (s, parent, d, opts = {}) => {
  const o = {
    at: s.t,
    dur: 1.2,
    stagger: 0.12,
    until: Infinity,
    dout: 0.6,
    stroke: PAPER,
    width: 3,
    fill: 'none',
    fillAt: null,
    opacity: 1,
    ease: E.ease.inOut,
    transform: null,
    dash: null,
    ...opts,
  };
  const ds = [].concat(d);
  const g = E.s('g', o.transform ? { transform: o.transform } : {});
  parent.append(g);
  const paths = ds.map(pd =>
    E.s('path', {
      d: pd,
      pathLength: 1,
      fill: o.fill,
      'fill-opacity': 0,
      stroke: o.stroke,
      'stroke-width': o.width,
      'stroke-linecap': 'round',
      'stroke-linejoin': 'round',
      'stroke-dasharray': '1 1',
      'stroke-dashoffset': 1,
      'vector-effect': 'non-scaling-stroke',
    }),
  );
  g.append(...paths);
  s.add(t => {
    const vis = t >= o.at - 0.01 && t <= o.until + o.dout + 0.01;
    g.style.display = vis ? 'inline' : 'none';
    if (!vis) return;
    const out = 1 - E.ease.inOut(E.prog(t, o.until, o.dout));
    g.setAttribute('opacity', (out * o.opacity).toFixed(4));
    paths.forEach((p, i) => {
      const k = o.ease(E.prog(t, o.at + i * o.stagger, o.dur));
      p.setAttribute('stroke-dashoffset', (1 - k).toFixed(4));
      if (o.fill !== 'none') {
        const f = o.fillAt === null ? k : E.ease.out(E.prog(t, o.fillAt, 0.8));
        p.setAttribute('fill-opacity', (f * (o.fillOpacity ?? 1)).toFixed(4));
      }
    });
  });
  g.paths = paths;
  return g;
};

// ---------------------------------------------------------------------------
// Impacts: screen shake + flash. Integrates with the scene camera.

C.impact = (s, { strength = 1, color = 'rgba(229,82,63,0.28)', at = s.t, sfx = 'gavel', gain = 1 } = {}) => {
  if (sfx) s.sfx(sfx, { at, gain });
  const flash = E.h('div', { style: { position: 'absolute', inset: 0, background: color, opacity: 0, pointerEvents: 'none' } });
  s.root.append(flash);
  if (!s._impacts) {
    s._impacts = [];
    s._shake = t => {
      let sx = 0;
      let sy = 0;
      for (const im of s._impacts) {
        const p = t - im.at;
        if (p < 0 || p > 1.5) continue;
        const decay = Math.exp(-p * 7) * im.strength;
        sx += Math.sin(p * 90) * 18 * decay;
        sy += Math.cos(p * 77) * 12 * decay;
      }
      return [sx, sy];
    };
    s.add(t => {
      for (const im of s._impacts) {
        const p = t - im.at;
        im.flash.style.opacity = p < 0 || p > 1.5 ? 0 : (Math.exp(-p * 9) * 0.9).toFixed(3);
      }
    });
    if (!s._hasCamera) s.camera([[0, {}]]);
  }
  s._impacts.push({ at, strength, flash });
};
// remember that a camera exists so impacts do not add a second one
const _cam = E.Scene.prototype.camera;
E.Scene.prototype.camera = function (keys) {
  this._hasCamera = true;
  return _cam.call(this, keys);
};

// ---------------------------------------------------------------------------
// Chapter card: giant faint numeral, title, subtitle.

C.chapterCard = (s, { num, title, sub, dur = 4.6 }) => {
  s.sfx('boom', { gain: 0.7 });
  s.sfx('whoosh', { at: s.t - 0.35, gain: 0.5 });
  const t0 = s.t;
  const big = s.el('div', {
    class: 'center',
    style: { left: '960px', top: '520px', fontSize: '560px', fontWeight: 900, color: 'rgba(207,169,94,0.07)', lineHeight: 1 },
  });
  big.textContent = num;
  s.fx(big, {
    start: t0,
    din: 1.4,
    end: t0 + dur - 0.9,
    dout: 0.8,
    update: (t, k) => {
      big.style.opacity = k;
      big.style.transform = `scale(${(1.08 - 0.08 * E.ease.out(E.prog(t, t0, dur))).toFixed(4)})`;
    },
  });
  const line = s.el('div', { class: 'center', style: { left: '960px', top: '470px', width: '0px', height: '2px', background: 'var(--gold)' } });
  s.fx(line, {
    start: t0 + 0.3,
    din: 0.9,
    end: t0 + dur - 0.9,
    dout: 0.6,
    update: (t, k) => {
      line.style.opacity = k;
      line.style.width = (E.ease.inOut(E.prog(t, t0 + 0.3, 1.0)) * 160).toFixed(1) + 'px';
    },
  });
  s.text(num, { cls: 'label', y: 410, at: t0 + 0.2, until: t0 + dur - 0.9, style: { fontSize: '36px' } });
  s.text(title, { cls: 'big', y: 560, at: t0 + 0.5, until: t0 + dur - 0.9, stagger: 0.09, charDur: 0.9 });
  if (sub) s.text(sub, { cls: 'small', y: 680, at: t0 + 1.1, until: t0 + dur - 0.9 });
  s.t = t0 + dur;
  return t0;
};

// ---------------------------------------------------------------------------
// Law article card.

C.lawCard = (s, { src, right = '', html, x = 960, y = 470, at = s.t, until, seal = null, width = 1280, fontSize = null }) => {
  const card = s.el('div', { class: 'law-card', style: { left: x + 'px', top: y + 'px', width: width + 'px' } });
  card.append(E.h('div', { class: 'src' }, [E.h('span', {}, [src]), E.h('span', {}, [right])]));
  const body = E.h('div', { class: 'body', html });
  if (fontSize) body.style.fontSize = fontSize + 'px';
  card.append(body);
  s.sfx('paper', { at });
  const h = s.fx(card, {
    start: at,
    din: 0.8,
    end: until,
    dout: 0.6,
    update: (t, k) => {
      const e = E.ease.out(E.prog(t, at, 0.9));
      card.style.opacity = k;
      card.style.transform = `translateY(${((1 - e) * 40).toFixed(2)}px)`;
      card.style.filter = k < 0.98 ? `blur(${((1 - k) * 6).toFixed(2)}px)` : 'none';
    },
  });
  // highlight <em> words progressively: they light up when given times arrive
  card.ems = [...body.querySelectorAll('em')];
  if (seal) C.seal(s, { ...seal, parent: card, end: until });
  return { card, h };
};

// Red rubber stamp.
C.seal = (s, { text, x, y, size = 64, rot = -8, at = s.t, parent = s.layer, end = Infinity, gain = 1, color = null, dout = 0.5 }) => {
  const el = E.h('div', { class: 'seal', style: { left: x + 'px', top: y + 'px', fontSize: size + 'px' } });
  if (color) {
    el.style.color = color;
    el.style.borderColor = color;
  }
  el.textContent = text;
  parent.append(el);
  s.sfx('stamp', { at, gain });
  s.add(t => {
    if (t < at) {
      el.style.opacity = 0;
      return;
    }
    const q = E.prog(t, at, 0.2);
    const e = E.ease.out5(q);
    const out = 1 - E.prog(t, end, dout);
    el.style.opacity = (Math.min(1, q * 2) * 0.92 * out).toFixed(3);
    el.style.transform = `scale(${E.lerp(2.4, 1, e).toFixed(3)}) rotate(${rot}deg)`;
  });
  return el;
};

// ---------------------------------------------------------------------------
// Icons (100×100 stroke paths)

C.ICONS = {
  pin: 'M50 90 C 50 90 20 58 20 38 A 30 30 0 0 1 80 38 C 80 58 50 90 50 90 Z M50 26 A 12 12 0 1 0 50.01 26 Z',
  chat: 'M14 22 H86 V66 H44 L26 82 V66 H14 Z M30 40 H70 M30 52 H58',
  cam: 'M10 30 H64 V66 H10 Z M64 40 L90 28 V68 L64 56 M18 72 L30 88 M56 72 L44 88',
  door: 'M24 12 H76 V92 H24 Z M64 52 A3 3 0 1 0 64.01 52',
  badge: 'M50 8 L84 20 V46 C84 68 68 84 50 92 C32 84 16 68 16 46 V20 Z M50 32 L55 44 L68 45 L58 53 L62 66 L50 59 L38 66 L42 53 L32 45 L45 44 Z',
  finger:
    'M30 80 C26 62 26 40 38 28 C50 16 70 20 76 38 C80 52 76 66 72 80 M40 84 C36 70 34 52 42 42 C50 32 64 36 66 48 C68 60 64 72 60 86 M50 86 C48 74 46 60 52 54 C56 50 58 56 58 62 C58 70 56 80 54 88',
  scope: 'M30 88 H78 M54 88 V76 M38 76 H70 M46 70 L60 28 M42 26 L66 34 L62 44 L38 36 Z M56 56 C70 58 76 66 72 76',
  hall: 'M14 88 H86 M18 80 H82 M24 80 V44 M38 80 V44 M50 80 V44 M62 80 V44 M76 80 V44 M18 44 H82 M14 38 L50 14 L86 38 Z',
  person: 'M50 18 A13 13 0 1 0 50.01 18 Z M24 88 C24 62 36 50 50 50 C64 50 76 62 76 88',
  doc: 'M24 10 H62 L78 26 V90 H24 Z M62 10 V26 H78 M34 42 H68 M34 54 H68 M34 66 H58',
  bag: 'M34 26 C30 18 40 12 50 12 C60 12 70 18 66 26 M30 30 H70 C82 44 86 60 84 74 C82 86 70 90 50 90 C30 90 18 86 16 74 C14 60 18 44 30 30 Z M50 42 V76 M42 50 C42 44 58 44 58 52 C58 60 42 58 42 66 C42 74 58 74 58 68',
  lock: 'M28 44 H72 V88 H28 Z M36 44 V32 C36 14 64 14 64 32 V44 M50 60 V72',
  gavel: 'M20 36 L44 12 M28 44 L52 20 M24 40 L48 16 M36 32 L72 68 M60 82 H92 M64 76 H88',
  clock: 'M50 12 A38 38 0 1 0 50.01 12 Z M50 26 V50 L66 60',
  phone: 'M32 8 H68 A6 6 0 0 1 74 14 V86 A6 6 0 0 1 68 92 H32 A6 6 0 0 1 26 86 V14 A6 6 0 0 1 32 8 Z M44 80 H56',
};
C.icon = (name, { size = 120, stroke = PAPER, width = 4, fill = 'none' } = {}) => {
  const svg = E.s('svg', { width: size, height: size, viewBox: '0 0 100 100', style: { overflow: 'visible' } });
  svg.append(E.s('path', { d: C.ICONS[name], fill, stroke, 'stroke-width': width, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }));
  return svg;
};

// Big number counter.
C.counter = (s, { x, y, label, color = 'var(--paper)', parent = s.layer, size = 110 }) => {
  const el = E.h('div', { class: 'counter', style: { left: x + 'px', top: y + 'px' } });
  const lbl = E.h('div', { class: 'lbl' }, [label]);
  const val = E.h('div', { class: 'val', style: { color, fontSize: size + 'px' } }, ['0']);
  el.append(lbl, val);
  parent.append(el);
  el.setVal = v => {
    const sv = String(v);
    if (val.textContent !== sv) val.textContent = sv;
  };
  el.lbl = lbl;
  el.val = val;
  return el;
};

// ---------------------------------------------------------------------------
// Person glyph (SVG group) — head + shoulders. Origin at feet-centre.

C.person = (parent, { x = 0, y = 0, size = 1, fill = PAPER } = {}) => {
  const g = E.s('g');
  const head = E.s('circle', { cx: 0, cy: -118, r: 25, fill });
  const body = E.s('path', { d: 'M -42 0 L -42 -50 Q -42 -84 -10 -86 L 10 -86 Q 42 -84 42 -50 L 42 0 Z', fill });
  g.append(head, body);
  parent.append(g);
  g.st = { x, y, size, rot: 0 };
  g.place = (nx = g.st.x, ny = g.st.y, ns = g.st.size, rot = g.st.rot) => {
    g.st = { x: nx, y: ny, size: ns, rot };
    g.setAttribute('transform', `translate(${nx.toFixed(2)},${ny.toFixed(2)}) rotate(${rot.toFixed(2)}) scale(${ns.toFixed(4)})`);
  };
  g.paint = c => {
    head.setAttribute('fill', c);
    body.setAttribute('fill', c);
  };
  g.place();
  return g;
};

// ---------------------------------------------------------------------------
// Calendar page that flips through days and lands on `day`.

C.calendar = (s, { x = 960, y = 470, at = s.t, until = Infinity, day = 14, from = 1, flipDur = 1.4, label = '上个月', scale = 1, parent = s.layer }) => {
  const el = E.h('div', {
    class: 'center',
    style: {
      left: x + 'px',
      top: y + 'px',
      width: 300 * scale + 'px',
      height: 340 * scale + 'px',
      background: 'linear-gradient(180deg,#efe8d8,#ddd4c1)',
      borderRadius: 14 * scale + 'px',
      boxShadow: '0 30px 70px rgba(0,0,0,0.55)',
      overflow: 'hidden',
      perspective: '900px',
    },
  });
  const head = E.h('div', {
    style: {
      height: 84 * scale + 'px',
      background: 'linear-gradient(180deg,#c2392f,#9f2a23)',
      color: '#fbe9dc',
      fontFamily: 'var(--sans)',
      fontSize: 34 * scale + 'px',
      letterSpacing: '0.3em',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontWeight: 500,
    },
  }, [label]);
  const num = E.h('div', {
    style: {
      position: 'absolute',
      left: 0,
      right: 0,
      top: 96 * scale + 'px',
      textAlign: 'center',
      fontFamily: 'var(--serif)',
      fontWeight: 900,
      fontSize: 190 * scale + 'px',
      lineHeight: 1.1,
      color: '#1b1d22',
      transformOrigin: '50% 0%',
    },
  });
  const rings = E.h('div', { style: { position: 'absolute', left: 0, right: 0, top: 18 * scale + 'px', display: 'flex', justifyContent: 'space-around', padding: `0 ${60 * scale}px` } });
  for (let i = 0; i < 2; i++)
    rings.append(E.h('div', { style: { width: 16 * scale + 'px', height: 16 * scale + 'px', borderRadius: '50%', background: '#2a1210', boxShadow: 'inset 0 2px 3px rgba(0,0,0,.6)' } }));
  el.append(head, rings, num);
  parent.append(el);
  let lastDay = -1;
  const h = s.fx(el, {
    start: at,
    din: 0.5,
    end: until,
    dout: 0.6,
    update: (t, k) => {
      const e = E.ease.back(E.prog(t, at, 0.6));
      el.style.opacity = k;
      el.style.transform = `scale(${E.lerp(0.85, 1, e).toFixed(4)})`;
      const p = E.ease.out(E.prog(t, at + 0.3, flipDur));
      const d = Math.round(E.lerp(from, day, p));
      if (d !== lastDay) {
        num.textContent = d;
        lastDay = d;
      }
      // flip wobble on each change
      const f = (E.lerp(from, day, p) % 1 + 1) % 1;
      num.style.transform = p < 1 ? `rotateX(${(f * 50).toFixed(1)}deg)` : 'none';
    },
  });
  el.h = h;
  return el;
};

// Analog clock that spins to hh:mm, with a digital readout.
C.clock = (s, { x = 960, y = 470, at = s.t, until = Infinity, hh = 21, mm = 0, spin = 1.6, r = 120, digital = true, parent = s.layer }) => {
  const size = r * 2 + 20;
  const wrap = E.h('div', { class: 'center', style: { left: x + 'px', top: y + 'px', width: size + 'px', textAlign: 'center' } });
  const svg = E.s('svg', { width: size, height: size, viewBox: `${-size / 2} ${-size / 2} ${size} ${size}` });
  svg.append(E.s('circle', { r, fill: 'rgba(236,229,214,0.04)', stroke: PAPER, 'stroke-width': 3 }));
  for (let i = 0; i < 60; i++) {
    const a = (i / 60) * Math.PI * 2;
    const long = i % 5 === 0;
    const r1 = r - (long ? 20 : 9);
    svg.append(
      E.s('line', {
        x1: Math.sin(a) * r1,
        y1: -Math.cos(a) * r1,
        x2: Math.sin(a) * (r - 4),
        y2: -Math.cos(a) * (r - 4),
        stroke: long ? PAPER : MUTED,
        'stroke-width': long ? 3 : 1.5,
        'stroke-linecap': 'round',
      }),
    );
  }
  const hour = E.s('line', { x1: 0, y1: 10, x2: 0, y2: -r * 0.5, stroke: PAPER, 'stroke-width': 7, 'stroke-linecap': 'round' });
  const min = E.s('line', { x1: 0, y1: 14, x2: 0, y2: -r * 0.78, stroke: GOLD2, 'stroke-width': 4, 'stroke-linecap': 'round' });
  svg.append(hour, min, E.s('circle', { r: 7, fill: GOLD2 }));
  wrap.append(svg);
  const dig = E.h('div', { style: { fontFamily: 'var(--sans)', fontWeight: 300, fontSize: r * 0.42 + 'px', letterSpacing: '0.12em', color: 'var(--paper2)', marginTop: '14px' } });
  if (digital) wrap.append(dig);
  parent.append(wrap);
  const target = (hh % 12) * 60 + mm + (hh >= 12 ? 0 : 0);
  const h = s.fx(wrap, {
    start: at,
    din: 0.5,
    end: until,
    dout: 0.6,
    update: (t, k) => {
      wrap.style.opacity = k;
      const p = E.ease.out(E.prog(t, at + 0.2, spin));
      const minutes = E.lerp(target - 12 * 60, target, p) + 12 * 60 * 3;
      const hA = ((minutes / 720) * 360) % 360;
      const mA = ((minutes % 60) / 60) * 360;
      hour.setAttribute('transform', `rotate(${hA.toFixed(2)})`);
      min.setAttribute('transform', `rotate(${mA.toFixed(2)})`);
      const shown = Math.round(E.lerp(hh * 60 + mm - 720, hh * 60 + mm, p));
      const H = Math.floor(((shown % 1440) + 1440) % 1440 / 60);
      const M = ((shown % 60) + 60) % 60;
      dig.textContent = `${String(H).padStart(2, '0')}:${String(M).padStart(2, '0')}`;
    },
  });
  wrap.h = h;
  return wrap;
};

// Countdown ring: n seconds starting at `at` (real time unless `speed`).
C.countdown = (s, { x = 1700, y = 170, at = s.t, n = 10, dur = null, r = 70, until = null, parent = s.layer, tickSfx = true }) => {
  const total = dur ?? n;
  const wrap = E.h('div', { class: 'center', style: { left: x + 'px', top: y + 'px', width: r * 2 + 20 + 'px', height: r * 2 + 20 + 'px' } });
  const size = r * 2 + 20;
  const svg = E.s('svg', { width: size, height: size, viewBox: `${-size / 2} ${-size / 2} ${size} ${size}`, style: { position: 'absolute', left: 0, top: 0 } });
  svg.append(E.s('circle', { r, fill: 'rgba(0,0,0,0.25)', stroke: 'rgba(236,229,214,0.15)', 'stroke-width': 6 }));
  const arc = E.s('circle', { r, fill: 'none', stroke: GOLD2, 'stroke-width': 6, pathLength: 1, 'stroke-dasharray': '1 1', transform: 'rotate(-90)', 'stroke-linecap': 'round' });
  svg.append(arc);
  const num = E.h('div', {
    style: { position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--serif)', fontWeight: 900, fontSize: r * 0.9 + 'px', color: PAPER },
  });
  wrap.append(svg, num);
  parent.append(wrap);
  if (tickSfx) for (let i = 0; i < n; i++) s.sfx('tick', { at: at + (i * total) / n, gain: 0.55 + (0.35 * i) / n, v: i });
  const end = until ?? at + total + 0.8;
  s.fx(wrap, {
    start: at - 0.3,
    din: 0.3,
    end,
    dout: 0.5,
    update: (t, k) => {
      wrap.style.opacity = k;
      const p = E.prog(t, at, total);
      arc.setAttribute('stroke-dashoffset', p.toFixed(4));
      const left = Math.max(0, Math.ceil(n - p * n - 1e-6));
      num.textContent = left;
      const urgent = left <= 3;
      arc.setAttribute('stroke', urgent ? RED : GOLD2);
      num.style.color = urgent ? RED : PAPER;
      const pulse = 1 + 0.06 * Math.exp(-(((t - at) * n) / total % 1) * 6);
      wrap.style.transform = `scale(${(t > at && p < 1 ? pulse : 1).toFixed(4)})`;
    },
  });
  return wrap;
};

// Red/blue police light wash.
C.policeLights = (s, { at = s.t, until = s.t + 3, rate = 2.2, strength = 1 } = {}) => {
  const l = E.h('div', { style: { position: 'absolute', inset: 0, pointerEvents: 'none', mixBlendMode: 'screen' } });
  const red = E.h('div', { style: { position: 'absolute', inset: 0, background: 'radial-gradient(ellipse 60% 80% at 0% 50%, rgba(229,40,40,0.55), transparent 70%)' } });
  const blue = E.h('div', { style: { position: 'absolute', inset: 0, background: 'radial-gradient(ellipse 60% 80% at 100% 50%, rgba(50,110,255,0.55), transparent 70%)' } });
  l.append(red, blue);
  s.root.append(l);
  s.fx(l, {
    start: at,
    din: 0.3,
    end: until,
    dout: 0.8,
    update: (t, k) => {
      const ph = (t - at) * rate * Math.PI * 2;
      red.style.opacity = (k * strength * (0.5 + 0.5 * Math.max(0, Math.sin(ph)))).toFixed(3);
      blue.style.opacity = (k * strength * (0.5 + 0.5 * Math.max(0, Math.sin(ph + Math.PI)))).toFixed(3);
    },
  });
  return l;
};

// A red "X" drawn over something.
C.cross = (s, parent, { cx = 50, cy = 50, size = 70, at = s.t, until = Infinity, width = 6 }) => {
  const a = size / 2;
  return C.draw(s, parent, [`M${cx - a} ${cy - a} L${cx + a} ${cy + a}`, `M${cx + a} ${cy - a} L${cx - a} ${cy + a}`], {
    at,
    dur: 0.28,
    stagger: 0.12,
    until,
    stroke: RED,
    width,
    ease: E.ease.out,
  });
};
