// Global background: base gradient, slow light blobs, dust, vignette, film
// grain (which also dithers the dark gradients against banding), plus the
// persistent chapter tag. Mood is set per scene (opts.mood) and cross-fades
// across scene boundaries; scenes may also override it locally via opts.moods.
(() => {
  const MOODS = {
    void: { glow: [10, 12, 18], amt: 0.0, dust: 0.25 },
    dark: { glow: [30, 40, 62], amt: 0.55, dust: 0.6 },
    gold: { glow: [70, 54, 26], amt: 0.6, dust: 0.8 },
    red: { glow: [74, 20, 18], amt: 0.65, dust: 0.5 },
    cold: { glow: [22, 40, 66], amt: 0.6, dust: 0.6 },
    warm: { glow: [58, 44, 34], amt: 0.5, dust: 0.7 },
    ink: { glow: [26, 30, 40], amt: 0.35, dust: 0.35 },
    dawn: { glow: [80, 62, 36], amt: 0.75, dust: 1.0 },
  };
  E.MOODS = MOODS;
  const cv = document.getElementById('bgc');
  const ctx = cv.getContext('2d');
  const r = E.rng(7);
  const dust = Array.from({ length: 120 }, () => ({
    x: r() * E.W,
    y: r() * E.H,
    vx: (r() - 0.5) * 6,
    vy: -2 - r() * 7,
    s: 0.6 + r() * 2.2,
    a: 0.15 + r() * 0.5,
    f: r() * 10,
  }));

  // mood at time T: scene mood, optionally keyed inside the scene
  const sceneMood = (sc, local) => {
    const keys = sc.opts.moods; // [[t, 'mood'], ...]
    if (!keys) return { m: MOODS[sc.opts.mood || 'dark'], since: 0, prev: null };
    let idx = -1;
    for (let i = 0; i < keys.length; i++) if (local >= keys[i][0]) idx = i;
    if (idx < 0) return { m: MOODS[sc.opts.mood || 'dark'], since: 0, prev: null };
    const prevName = idx > 0 ? keys[idx - 1][1] : sc.opts.mood || 'dark';
    return { m: MOODS[keys[idx][1]], since: keys[idx][0], prev: MOODS[prevName], fade: keys[idx][2] ?? 2.5 };
  };
  const moodAt = T => {
    const tl = E.timeline;
    let i = tl.findIndex(sc => T >= sc.start && T < sc.start + sc.dur);
    if (i < 0) i = tl.length - 1;
    const sc = tl[i];
    const local = T - sc.start;
    const cur = sceneMood(sc, local);
    let prev;
    let k;
    if (cur.prev) {
      prev = cur.prev;
      k = E.ease.inOut(E.prog(local, cur.since, cur.fade));
    } else {
      const ps = i > 0 ? tl[i - 1] : null;
      prev = ps ? sceneMood(ps, ps.dur).m : cur.m;
      k = E.ease.inOut(E.prog(local, 0, 1.6));
    }
    const mix = (a, b) => a + (b - a) * k;
    return {
      glow: cur.m.glow.map((c, j) => mix(prev.glow[j], c)),
      amt: mix(prev.amt, cur.m.amt),
      dust: mix(prev.dust, cur.m.dust),
    };
  };

  E.globalUpdaters.push(T => {
    const m = moodAt(T);
    ctx.fillStyle = '#090b10';
    ctx.fillRect(0, 0, E.W, E.H);
    const blobs = [
      { x: 0.3 + 0.08 * Math.sin(T * 0.05), y: 0.35 + 0.06 * Math.cos(T * 0.04), rad: 1100 },
      { x: 0.75 + 0.07 * Math.cos(T * 0.037), y: 0.7 + 0.05 * Math.sin(T * 0.045), rad: 900 },
    ];
    for (const b of blobs) {
      const g = ctx.createRadialGradient(b.x * E.W, b.y * E.H, 0, b.x * E.W, b.y * E.H, b.rad);
      const [cr, cg, cb] = m.glow.map(Math.round);
      g.addColorStop(0, `rgba(${cr},${cg},${cb},${(0.55 * m.amt).toFixed(3)})`);
      g.addColorStop(1, `rgba(${cr},${cg},${cb},0)`);
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, E.W, E.H);
    }
    for (const d of dust) {
      const x = (((d.x + d.vx * T) % E.W) + E.W) % E.W;
      const y = (((d.y + d.vy * T) % E.H) + E.H) % E.H;
      const tw = 0.6 + 0.4 * Math.sin(T * 0.8 + d.f);
      ctx.fillStyle = `rgba(236,229,214,${(d.a * tw * m.dust * 0.5).toFixed(3)})`;
      ctx.beginPath();
      ctx.arc(x, y, d.s, 0, Math.PI * 2);
      ctx.fill();
    }
    const v = ctx.createRadialGradient(E.W / 2, E.H / 2, E.H * 0.35, E.W / 2, E.H / 2, E.W * 0.68);
    v.addColorStop(0, 'rgba(0,0,0,0)');
    v.addColorStop(1, 'rgba(0,0,0,0.72)');
    ctx.fillStyle = v;
    ctx.fillRect(0, 0, E.W, E.H);
  });

  // Film grain: a fixed noise tile, re-positioned every frame.
  const gcv = document.getElementById('grain');
  const gctx = gcv.getContext('2d');
  const tile = document.createElement('canvas');
  tile.width = tile.height = 256;
  const tctx = tile.getContext('2d');
  const img = tctx.createImageData(256, 256);
  const gr = E.rng(99);
  for (let i = 0; i < 256 * 256; i++) {
    const v = 128 + E.gauss(gr) * 34;
    img.data[i * 4] = img.data[i * 4 + 1] = img.data[i * 4 + 2] = E.clamp(v, 0, 255);
    img.data[i * 4 + 3] = 255;
  }
  tctx.putImageData(img, 0, 0);
  E.globalUpdaters.push(T => {
    const f = Math.round(T * 30);
    const fr = E.rng(f * 7919 + 13);
    const ox = Math.floor(fr() * 256);
    const oy = Math.floor(fr() * 256);
    gctx.save();
    gctx.translate(-ox, -oy);
    gctx.fillStyle = gctx.createPattern(tile, 'repeat');
    gctx.fillRect(0, 0, E.W + 256, E.H + 256);
    gctx.restore();
  });

  // Chapter tag (top-left), shown inside chapters but hidden on chapter cards.
  const tag = E.h('div', { class: 'chapter-tag' }, [
    E.h('span', { class: 'num' }),
    E.h('span', { class: 'bar' }),
    E.h('span', { class: 'ttl' }),
  ]);
  document.getElementById('overlay').append(tag);
  E.globalUpdaters.push(T => {
    const tl = E.timeline;
    const sc = tl.find(s => T >= s.start && T < s.start + s.dur) || tl[tl.length - 1];
    const ch = sc.opts.tag;
    if (!ch) {
      tag.style.opacity = 0;
      return;
    }
    tag.querySelector('.num').textContent = ch[0];
    tag.querySelector('.ttl').textContent = ch[1];
    const local = T - sc.start;
    const from = sc.opts.tagFrom ?? 0;
    let a = E.prog(local, from + 0.3, 0.8);
    const i = tl.indexOf(sc);
    const same = s => s && s.opts.tag && s.opts.tag[0] === ch[0];
    if (!same(tl[i + 1])) a = Math.min(a, 1 - E.prog(local, sc.dur - 0.8, 0.6));
    tag.style.opacity = (0.85 * a).toFixed(3);
  });
})();
