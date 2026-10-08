// Components used only by the cold open.

// Stylised night map of a city with a pulsing pin on the west side.
C.cityMap = (s, { x = 1490, y = 470, at = s.t, pinAt = at + 0.8, alarmAt = pinAt + 0.6, until = Infinity, size = 420 }) => {
  const { svg, g } = C.layer(s, { at, until, w: size, h: size, x: x - size / 2, y: y - size / 2, din: 0.4 });
  const frame = E.s('rect', { x: 0, y: 0, width: size, height: size, rx: 18, fill: 'rgba(125,156,194,0.06)', stroke: 'rgba(125,156,194,0.35)', 'stroke-width': 1.5 });
  g.append(frame);
  const r = E.rng(5);
  const streets = [];
  for (let i = 1; i < 7; i++) {
    const yy = (i * size) / 7 + (r() - 0.5) * 16;
    streets.push(`M0 ${yy.toFixed(1)} C ${size * 0.3} ${(yy + (r() - 0.5) * 30).toFixed(1)} ${size * 0.6} ${(yy + (r() - 0.5) * 30).toFixed(1)} ${size} ${(yy + (r() - 0.5) * 20).toFixed(1)}`);
    const xx = (i * size) / 7 + (r() - 0.5) * 16;
    streets.push(`M${xx.toFixed(1)} 0 C ${(xx + (r() - 0.5) * 30).toFixed(1)} ${size * 0.35} ${(xx + (r() - 0.5) * 30).toFixed(1)} ${size * 0.65} ${(xx + (r() - 0.5) * 20).toFixed(1)} ${size}`);
  }
  C.draw(s, g, streets, { at: at + 0.05, dur: 0.9, stagger: 0.04, stroke: 'rgba(125,156,194,0.55)', width: 1.4 });
  // river
  C.draw(s, g, [`M${size * 0.62} 0 C ${size * 0.5} ${size * 0.3} ${size * 0.78} ${size * 0.55} ${size * 0.66} ${size}`], {
    at: at + 0.1,
    dur: 1.0,
    stroke: 'rgba(125,156,194,0.35)',
    width: 14,
  });
  const lbl = E.s('text', { x: 18, y: 36, fill: 'rgba(236,229,214,0.6)', 'font-family': 'Noto Sans SC', 'font-size': 22, 'letter-spacing': 4 }, []);
  lbl.textContent = '城西';
  g.append(lbl);
  // pin
  const px = size * 0.28;
  const py = size * 0.56;
  const rings = [0, 1, 2].map(() => E.s('circle', { cx: px, cy: py, r: 10, fill: 'none', stroke: '#e5523f', 'stroke-width': 2 }));
  const pin = E.s('path', { d: C.ICONS.pin, transform: `translate(${px - 22} ${py - 50}) scale(0.44)`, fill: '#e5523f', stroke: 'none' });
  const dot = E.s('circle', { cx: px, cy: py, r: 5, fill: '#e5523f' });
  g.append(...rings, dot, pin);
  s.add(t => {
    const p = E.prog(t, pinAt, 0.45);
    const e = E.ease.back(p);
    pin.setAttribute('opacity', E.clamp(p * 3).toFixed(3));
    pin.setAttribute('transform', `translate(${px - 22} ${py - 50 - (1 - e) * 60}) scale(0.44)`);
    dot.setAttribute('opacity', p > 0.9 ? 1 : 0);
    rings.forEach((c, i) => {
      if (t < alarmAt) {
        c.setAttribute('opacity', 0);
        return;
      }
      const q = ((t - alarmAt) / 1.4 + i / 3) % 1;
      c.setAttribute('r', (10 + q * 90).toFixed(1));
      c.setAttribute('opacity', ((1 - q) * 0.8).toFixed(3));
    });
    frame.setAttribute('stroke', t > alarmAt ? `rgba(229,82,63,${(0.35 + 0.35 * Math.abs(Math.sin((t - alarmAt) * 3))).toFixed(3)})` : 'rgba(125,156,194,0.35)');
  });
  return svg;
};

// Interrogation record on paper with Q/A rows; answers stay blank with a
// blinking caret on the focused row.
C.form = (s, { x = 690, y = 600, at = s.t, until = Infinity, rows = [], width = 840 }) => {
  const el = E.h('div', {
    class: 'center',
    style: {
      left: x + 'px',
      top: y + 'px',
      width: width + 'px',
      padding: '44px 56px 50px',
      background: 'linear-gradient(180deg,#e9e2d1,#d8cfbb)',
      color: '#22252b',
      borderRadius: '6px',
      boxShadow: '0 40px 90px rgba(0,0,0,0.6)',
      rotate: '-1.2deg',
      fontFamily: 'var(--serif)',
    },
  });
  const head = E.h('div', { style: { textAlign: 'center', fontSize: '40px', fontWeight: 900, letterSpacing: '0.6em', marginBottom: '26px', paddingLeft: '0.6em' } }, ['询问笔录']);
  el.append(head);
  const carets = [];
  rows.forEach(([k, v]) => {
    const row = E.h('div', { style: { display: 'flex', alignItems: 'baseline', gap: '18px', fontSize: '36px', lineHeight: '1.25', padding: '14px 0', borderBottom: '1.5px solid rgba(34,37,43,0.25)' } });
    row.append(E.h('span', { style: { fontWeight: 900, color: k === '问' ? '#22252b' : '#9f2a23' } }, [k + '：']));
    if (v) row.append(E.h('span', { style: { fontWeight: 500 } }, [v]));
    else {
      const c = E.h('span', { style: { display: 'inline-block', width: '4px', height: '38px', background: '#9f2a23', translate: '0 6px', opacity: 0 } });
      row.append(c);
      carets.push(c);
    }
    el.append(row);
  });
  s.layer.append(el);
  const focus = [];
  el.focus = (rowIdx, t) => focus.push({ c: carets[rows.slice(0, rowIdx + 1).filter(r => !r[1]).length - 1], t });
  s.fx(el, {
    start: at,
    din: 0.6,
    end: until,
    dout: 0.35,
    update: (t, k) => {
      const e = E.ease.out(E.prog(t, at, 0.8));
      el.style.opacity = k;
      el.style.transform = `translateY(${((1 - e) * 60).toFixed(1)}px)`;
      let cur = null;
      for (const f of focus) if (t >= f.t) cur = f.c;
      for (const c of carets) c.style.opacity = c === cur && Math.floor(t * 2.4) % 2 === 0 ? 1 : 0;
    },
  });
  return el;
};

// One alibi channel: icon + name; at failAt a red X and the reason it fails.
C.alibi = (s, { x, y, at, failAt, until, icon, name, fail }) => {
  const box = s.el('div', { class: 'center', style: { left: x + 'px', top: y + 'px', display: 'flex', alignItems: 'center', gap: '30px', width: '520px' } });
  const icWrap = E.h('div', { style: { position: 'relative', width: '96px', height: '96px', flex: 'none' } });
  const ic = C.icon(icon, { size: 96, width: 4 });
  const xs = E.s('svg', { width: 120, height: 120, viewBox: '0 0 100 100', style: { position: 'absolute', left: '-12px', top: '-12px', overflow: 'visible' } });
  icWrap.append(ic, xs);
  const txt = E.h('div', {}, [
    E.h('div', { style: { fontSize: '44px', fontWeight: 700, letterSpacing: '0.08em' } }, [name]),
    E.h('div', { class: 'fail', style: { fontFamily: 'var(--sans)', fontSize: '28px', color: 'var(--red2)', marginTop: '4px', letterSpacing: '0.06em', opacity: 0 } }, [fail]),
  ]);
  box.append(icWrap, txt);
  const failEl = txt.querySelector('.fail');
  C.cross(s, xs, { at: failAt, size: 76 });
  s.sfx('pop', { at, gain: 0.55 });
  s.sfx('buzz', { at: failAt, gain: 0.5 });
  s.fx(box, {
    start: at,
    din: 0.35,
    end: until,
    dout: 0.3,
    update: (t, k) => {
      const e = E.ease.back(E.prog(t, at, 0.45));
      box.style.opacity = k;
      box.style.transform = `translateX(${((1 - e) * 40).toFixed(1)}px)`;
      const f = E.prog(t, failAt, 0.3);
      ic.style.opacity = (1 - 0.6 * f).toFixed(3);
      txt.firstChild.style.color = f > 0.5 ? 'var(--muted)' : 'var(--paper)';
      failEl.style.opacity = f.toFixed(3);
    },
  });
  return box;
};

// Years rolling back from `from` to `to` along a scale.
C.yearRewind = (s, { at, until, from = 2026, to = 1100 }) => {
  const wrap = s.el('div', { class: 'center', style: { left: '960px', top: '470px', textAlign: 'center' } });
  const num = E.h('div', { style: { fontFamily: 'var(--serif)', fontWeight: 900, fontSize: '230px', color: 'var(--paper)', letterSpacing: '0.04em', lineHeight: 1 } });
  const cap = E.h('div', { class: 'tb-small', style: { marginTop: '18px', fontSize: '36px', letterSpacing: '0.4em' } }, ['公元']);
  wrap.append(num, cap);
  const ruler = s.el('div', { class: 'center', style: { left: '960px', top: '700px', width: '1500px', height: '60px', overflow: 'hidden' } });
  const strip = E.h('div', { style: { position: 'absolute', left: 0, top: 0, height: '60px', width: '9000px' } });
  for (let i = 0; i < 180; i++) {
    const big = i % 10 === 0;
    strip.append(E.h('div', { style: { position: 'absolute', left: i * 50 + 'px', bottom: 0, width: '2px', height: big ? '40px' : '18px', background: big ? 'var(--paper2)' : 'var(--dim)' } }));
  }
  ruler.append(strip);
  s.sfx('rewind', { at, gain: 0.7 });
  s.fx(wrap, {
    start: at,
    din: 0.3,
    end: until,
    dout: 0.4,
    update: (t, k) => {
      wrap.style.opacity = k;
      const p = E.ease.inOut(E.prog(t, at + 0.2, until - at - 0.9));
      const y = Math.round(E.lerp(from, to, p));
      num.textContent = y;
      num.style.filter = p > 0.02 && p < 0.98 ? `blur(${(Math.sin(p * Math.PI) * 3).toFixed(1)}px)` : 'none';
      ruler.style.opacity = k * 0.8;
      strip.style.transform = `translateX(${(-7000 + p * 6800).toFixed(1)}px)`;
    },
  });
  s.fx(ruler, { start: at, din: 0.3, end: until, dout: 0.4, update: (t, k) => (ruler.style.opacity = (k * 0.8).toFixed(3)) });
};

// Trial by ordeal: cauldron, hand, stone; then three days; then the verdicts.
C.ordeal = (s, { L14, until }) => {
  const L15 = L14;
  const at = L14.start - 0.2;
  const { svg, g } = C.layer(s, { at, until, din: 0.5, zoom: { from: 1.0, to: 1.05, dur: until - at, cx: 620, cy: 560 } });
  s.text('{g:神判}', { cls: 'label', x: 210, y: 150, at: L14.w('欧洲'), until, align: 'left', style: { fontSize: '44px', letterSpacing: '0.3em' } });
  s.text('Trial by Ordeal · 中世纪欧洲', { cls: 'small', x: 210, y: 205, at: L14.w('欧洲') + 0.2, until, align: 'left', style: { fontSize: '26px' } });
  const ox = 320;
  const oy = 420;
  C.art(s, g, ART.cauldron, { x: ox, y: oy, scale: 1, at: at + 0.1, dur: 1.4, stagger: 0.1, stroke: '#ece5d6', width: 3 });
  // boiling water surface + bubbles
  const water = E.s('path', { d: `M${ox + 130} ${oy + 200} C ${ox + 220} ${oy + 186} ${ox + 380} ${oy + 214} ${ox + 470} ${oy + 200}`, fill: 'none', stroke: '#cfa95e', 'stroke-width': 3, opacity: 0 });
  g.append(water);
  const r = E.rng(11);
  const bubbles = Array.from({ length: 16 }, () => {
    const b = E.s('circle', { r: 4 + r() * 8, fill: 'none', stroke: '#cfa95e', 'stroke-width': 2 });
    b.d = { x: ox + 150 + r() * 300, ph: r(), sp: 0.6 + r() * 0.8 };
    g.append(b);
    return b;
  });
  const steam = [0, 1, 2].map(i => {
    const p = E.s('path', { fill: 'none', stroke: 'rgba(236,229,214,0.35)', 'stroke-width': 3, 'stroke-linecap': 'round' });
    g.append(p);
    return p;
  });
  // fire flicker colour
  s.add(t => {
    const vis = t > at + 0.6;
    water.setAttribute('opacity', vis ? 0.9 : 0);
    const wob = Math.sin(t * 9) * 5;
    water.setAttribute('d', `M${ox + 130} ${oy + 200 + wob * 0.3} C ${ox + 220} ${oy + 186 + wob} ${ox + 380} ${oy + 214 - wob} ${ox + 470} ${oy + 200}`);
    bubbles.forEach(b => {
      const q = ((t * b.d.sp + b.d.ph) % 1 + 1) % 1;
      b.setAttribute('cx', (b.d.x + Math.sin(q * 9 + b.d.ph * 6) * 6).toFixed(1));
      b.setAttribute('cy', (oy + 196 - q * 120).toFixed(1));
      b.setAttribute('opacity', vis ? ((1 - q) * 0.8).toFixed(3) : 0);
    });
    steam.forEach((p, i) => {
      const bx = ox + 200 + i * 100;
      const ph = t * 1.3 + i;
      p.setAttribute('d', `M${bx} ${oy + 120} C ${bx + 30 * Math.sin(ph)} ${oy + 60} ${bx - 30 * Math.sin(ph + 1)} ${oy + 10} ${bx + 20 * Math.sin(ph + 2)} ${oy - 50}`);
      p.setAttribute('opacity', vis ? (0.45 + 0.2 * Math.sin(ph * 2)).toFixed(3) : 0);
    });
  });
  // stone at the bottom (seen through the pot, gold)
  const stoneG = C.art(s, g, ART.stone, { x: ox + 240, y: oy + 300, scale: 1, at: L14.w('捞石头') - 0.2, dur: 0.5, stroke: '#f0d08a', width: 3 });
  // the hand descends at 伸进, rises at 捞出
  const handG = E.s('g');
  g.append(handG);
  C.draw(s, handG, ART.hand.paths, { at: L14.w('把手') - 0.3, dur: 0.8, stroke: '#ece5d6', width: 3, fill: 'rgba(9,11,16,0.9)', fillAt: L14.w('把手') - 0.3 });
  const down = L14.w('伸进');
  const up = L14.w('捞石头');
  s.add(t => {
    const d = E.ease.inOut(E.prog(t, down, 0.9));
    const u = E.ease.inOut(E.prog(t, up, 1.0));
    const yy = oy - 400 + d * 260 - u * 300;
    handG.setAttribute('transform', `translate(${ox + 190} ${yy.toFixed(1)})`);
    stoneG.setAttribute('transform', `translate(${ox + 240} ${(oy + 300 - u * 300).toFixed(1)}) scale(1)`);
  });
  s.sfx('boil', { at: at + 0.4, gain: 0.5, dur: L14.end - at + 0.5 });
  s.sfx('splash', { at: down + 0.6, gain: 0.6 });
  // three days → verdicts (right side)
  const d3 = L15.w('三天');
  const bandage = L15.w('包匝');
  C.box(s, {
    x: 1380,
    y: 330,
    at: bandage - 0.1,
    until,
    html: '<div style="font-family:var(--sans);font-size:32px;letter-spacing:.3em;color:var(--muted)">包扎</div>',
  });
  const days = s.el('div', { class: 'center', style: { left: '1380px', top: '420px', fontWeight: 900, fontSize: '110px', color: 'var(--paper)' } });
  s.fx(days, {
    start: bandage,
    din: 0.3,
    end: until,
    dout: 0.4,
    update: (t, k) => {
      days.style.opacity = k;
      const n = Math.min(3, 1 + Math.floor(E.prog(t, bandage + 0.1, d3 - bandage + 0.3) * 2.999));
      days.textContent = `第 ${n} 天`;
    },
  });
  C.box(s, {
    x: 1180,
    y: 620,
    at: L15.w('不烂') - 0.1,
    until,
    anim: 'pop',
    html: '<div style="font-size:40px;color:var(--muted)">伤口不烂</div><div style="font-size:84px;font-weight:900;color:var(--paper)">清白</div>',
  });
  C.box(s, {
    x: 1580,
    y: 620,
    at: L15.w('清白') - 0.1,
    until,
    anim: 'pop',
    html: '<div style="font-size:40px;color:var(--muted)">伤口烂了</div><div style="font-size:84px;font-weight:900;color:var(--red2)">有罪</div>',
  });
  s.sfx('pop', { at: L15.w('不烂'), gain: 0.5 });
  s.sfx('thud', { at: L15.w('清白'), gain: 0.8 });
};

// The Tang Code passage on judicial torture + 40 "正" tallies (= 200 strokes).
C.tangCode = (s, { L16, until }) => {
  const L17 = L16;
  const at = L16.start - 0.2;
  const paper = s.el('div', {
    class: 'center',
    style: {
      left: '560px',
      top: '470px',
      width: '600px',
      height: '700px',
      background: 'radial-gradient(ellipse at 40% 30%, #e6d6b2, #c9b48a 70%, #b49b6c)',
      boxShadow: '0 40px 90px rgba(0,0,0,0.65), inset 0 0 60px rgba(90,60,20,0.35)',
      borderRadius: '4px',
      padding: '56px 50px',
      display: 'flex',
      flexDirection: 'row-reverse',
      gap: '30px',
      justifyContent: 'flex-start',
    },
  });
  const cols = ['唐律疏议 · 断狱', '诸拷囚不得过三度', '数总不得过二百', '拷满不承', '取保放之'];
  const colEls = cols.map((c, i) => {
    const el = E.h('div', {
      style: {
        writingMode: 'vertical-rl',
        fontFamily: i === 0 ? 'var(--sans)' : 'var(--kai)',
        fontSize: i === 0 ? '30px' : '54px',
        letterSpacing: i === 0 ? '0.3em' : '0.12em',
        color: i === 0 ? '#7a2a1c' : '#2a1d10',
        fontWeight: i === 0 ? 500 : 700,
        lineHeight: 1.1,
      },
    });
    for (const ch of c) {
      const sp = E.h('span', { style: { display: 'inline-block' } }, [ch]);
      el.append(sp);
    }
    paper.append(el);
    return el;
  });
  s.sfx('paper', { at, gain: 0.8 });
  const hi = [1, 2];
  const hiAt = L17.w('最多三次') - 0.2;
  s.fx(paper, {
    start: at,
    din: 0.7,
    end: until,
    dout: 0.5,
    update: (t, k) => {
      const e = E.ease.out(E.prog(t, at, 1.0));
      paper.style.opacity = k;
      paper.style.transform = `translateY(${((1 - e) * 50).toFixed(1)}px) rotate(${(-1.5 + e * 0.5).toFixed(2)}deg)`;
      colEls.forEach((c, i) => {
        const p = E.ease.out(E.prog(t, at + 0.4 + i * 0.25, 0.8));
        c.style.opacity = (p * (t > hiAt && !hi.includes(i) && i > 0 ? 0.35 : 1)).toFixed(3);
        c.style.color = hi.includes(i) && t > hiAt ? '#a3271c' : i === 0 ? '#7a2a1c' : '#2a1d10';
      });
    },
  });
  // red seal on the paper
  C.seal(s, { text: '唐', x: 90, y: 600, size: 54, rot: 4, at: at + 1.2, parent: paper, end: until, gain: 0.5 });
  s.text('{g:写进律典的拷讯}', { cls: 'label', x: 1360, y: 210, at: L16.w('律典') - 0.1, until, style: { fontSize: '40px', letterSpacing: '0.3em' } });
  // 3 heavy strokes for 三度
  const three = s.el('div', { class: 'center', style: { left: '1360px', top: '330px', display: 'flex', gap: '34px', alignItems: 'center' } });
  const bars = [0, 1, 2].map(() => {
    const b = E.h('div', { style: { width: '22px', height: '110px', background: 'var(--red2)', borderRadius: '4px', opacity: 0 } });
    three.append(b);
    return b;
  });
  const lbl3 = E.h('div', { style: { fontSize: '44px', fontWeight: 700, marginLeft: '20px', opacity: 0 } }, ['最多三次']);
  three.append(lbl3);
  const t3 = L17.w('最多三次') + 0.3;
  bars.forEach((b, i) => s.sfx('thud', { at: t3 + i * 0.16, gain: 0.55 }));
  s.add(t => {
    const vis = t < until + 0.5;
    three.style.opacity = vis ? 1 - E.prog(t, until, 0.5) : 0;
    bars.forEach((b, i) => (b.style.opacity = E.prog(t, t3 + i * 0.16, 0.12)));
    lbl3.style.opacity = E.prog(t, t3 + 0.5, 0.3);
  });
  // 40 正 = 200 strokes
  const t200 = L17.w('两百') - 0.9;
  const grid = s.el('div', { class: 'center', style: { left: '1360px', top: '640px', display: 'grid', gridTemplateColumns: 'repeat(10, 64px)', gap: '6px 6px', fontFamily: 'var(--kai)', fontSize: '56px', color: 'var(--paper)', lineHeight: 1 } });
  const zh = Array.from({ length: 40 }, () => {
    const c = E.h('div', { style: { opacity: 0, textAlign: 'center' } }, ['正']);
    grid.append(c);
    return c;
  });
  const lbl200 = s.el('div', { class: 'center', style: { left: '1360px', top: '820px', fontSize: '38px', fontWeight: 700, opacity: 0 } }, ['四十个“正”字，两百下']);
  for (let i = 0; i < 40; i += 4) s.sfx('scribble', { at: t200 + i * 0.03, gain: 0.25, v: i });
  s.add(t => {
    const out = 1 - E.prog(t, until, 0.5);
    zh.forEach((c, i) => {
      const p = E.prog(t, t200 + i * 0.03, 0.12);
      c.style.opacity = (p * out).toFixed(3);
    });
    lbl200.style.opacity = (E.prog(t, t200 + 1.4, 0.4) * out).toFixed(3);
    grid.style.display = t > until + 0.6 ? 'none' : 'grid';
  });
};
