// 00 冷开场 + 片名
// Text markup: {r:红} {g:金} {w:白粗} {m:灰} {b:蓝} {s:删除线}

E.scene(
  'cold',
  s => {
    s.music('tick', { at: 0, fade: 0.3 });

    // c02 date / time / place — visible from the very first frame
    s.at(0.35);
    const L2 = s.say('c02', { pause: 0.9 });
    const tDay = L2.w('十四号');
    const tTime = L2.w('九点');
    const tPlace = L2.w('城西');
    const tKill = L2.w('杀');
    const gone = L2.end + 0.5;
    C.calendar(s, { x: 430, y: 470, at: 0, day: 14, from: 1, flipDur: tDay + 0.25 - 0.3, until: gone, scale: 1.1 });
    C.clock(s, { x: 960, y: 450, at: 0, hh: 21, mm: 0, spin: tTime + 0.2, r: 135, until: gone });
    C.cityMap(s, { x: 1490, y: 470, at: Math.max(0, tPlace - 0.6), pinAt: L2.w('仓库'), alarmAt: tKill, until: gone, size: 440 });
    s.sfx('pop', { at: tDay, gain: 0.5 });
    s.sfx('pop', { at: tTime, gain: 0.5 });
    s.sfx('pin', { at: L2.w('仓库') });
    s.sfx('hit', { at: tKill, gain: 0.9 });
    s.text('{m:上个月}', { cls: 'small', x: 430, y: 720, at: tDay, until: gone });
    s.text('{m:晚上}', { cls: 'small', x: 960, y: 720, at: tTime, until: gone });
    s.text('{m:城西 · 仓库}', { cls: 'small', x: 1490, y: 720, at: L2.w('仓库'), until: gone });

    // c03 police at the door
    s.sfx('knock', { at: s.t - 0.75, gain: 0.9 });
    const L3 = s.say('c03', { sub: false });
    C.policeLights(s, { at: L3.start - 0.5, until: L3.end + 0.8, strength: 0.9 });
    s.sfx('siren', { at: L3.start - 0.4, gain: 0.35 });
    s.text('警察找到了你。', { sync: L3, until: L3.end + 0.45, cls: 'body', style: { fontSize: '84px' } });

    // c04 the demand
    const L4 = s.say('c04', { sub: false });
    const demand1 = s.text('{g:请你证明：}', { cls: 'lead', y: 400, sync: L4, anim: 'type', typeSfx: false });
    const demand2 = s.text('那天晚上9点，你{r:不在}那间仓库。', { cls: 'body', y: 520, sync: L4, anim: 'type' });
    // c05 ten seconds
    const L5 = s.say('c05', { sub: false });
    const t5 = s.text('你有{r:十秒钟}。', { cls: 'lead', y: 650, sync: L5 });
    const cdStart = s.t;
    const cdEnd = cdStart + 10;
    const hdrAt = L5.end + 0.05;
    s.add(t => {
      const p = E.ease.inOut(E.prog(t, hdrAt, 0.7));
      for (const [h, y0, y1, s1] of [
        [demand1, 400, 118, 0.62],
        [demand2, 520, 192, 0.66],
      ]) {
        h.el.style.top = E.lerp(y0, y1, p).toFixed(1) + 'px';
        h.el.style.scale = E.lerp(1, s1, p).toFixed(4);
      }
    });
    t5.exit(hdrAt, 0.4);
    C.countdown(s, { x: 1720, y: 160, at: cdStart, n: 10, until: cdEnd + 0.15 });
    // a quiet clock has been ticking since the first frame
    for (let t = 0.5, i = 0; t < cdStart - 0.2; t += 1, i++) s.sfx('tick', { at: t, gain: 0.32, v: i % 2 });
    s.music('tension', { at: cdStart, fade: 1.2 });

    const form = C.form(s, {
      x: 690,
      y: 600,
      at: cdStart + 0.3,
      until: cdEnd + 0.1,
      rows: [
        ['问', '那天晚上9点，你在干什么？'],
        ['答', null],
        ['问', '有人能给你作证吗？'],
        ['答', null],
      ],
    });
    s.t = cdStart + 0.1;
    const L6 = s.say('c06', { pause: 0.2 });
    form.focus(1, L6.start);
    const L8 = s.say('c08');
    form.focus(3, L8.start);
    const items = [
      { icon: 'phone', name: '手机定位', fail: '那天没开定位', w: '手机定位' },
      { icon: 'chat', name: '聊天记录', fail: '那晚没和人聊天', w: '聊天记录' },
      { icon: 'cam', name: '监控录像', fail: '早已循环覆盖', w: '监控录像' },
    ];
    items.forEach((it, i) => {
      const at = L8.w(it.w) - 0.1;
      const failAt = L8.w(it.w, 'end') + 0.25;
      C.alibi(s, { x: 1440, y: 410 + i * 170, at, failAt, until: cdEnd + 0.1, ...it });
    });
    // pure ticking, then the last question just before zero
    const L9 = s.say('c09', { at: cdEnd - 1.25 });
    form.focus(1, L9.start);
    s.t = cdEnd;
    demand1.exit(cdEnd, 0.25);
    demand2.exit(cdEnd, 0.25);

    // c10 那么—— (everything stops)
    s.music('silence', { at: cdEnd, fade: 0.08 });
    s.sfx('stop', { at: cdEnd, gain: 0.8 });
    s.at(cdEnd + 0.25);
    const L10 = s.say('c10', { sub: false });
    s.text('那么——', { cls: 'lead', sync: L10, until: L10.end + 0.75, exitDur: 0.3 });

    // c11 就是你干的。
    const L11 = s.say('c11', { sub: false });
    C.impact(s, { strength: 1.5, at: L11.start + 0.02, gain: 1.2 });
    s.sfx('hit', { at: L11.start + 0.02, gain: 0.8 });
    s.music('drone', { at: L11.start + 0.1, fade: 2.5 });
    const guilty = s.text('{r:就是你干的。}', { cls: 'huge', anim: 'slam', at: L11.start, style: { fontSize: '170px' } });
    const L12 = s.say('c12');
    guilty.exit(L12.start + 0.2, 0.9);

    // c13 → back in time
    const L13 = s.say('c13');
    s.opts.moods = [[L13.start, 'ink', 3]];
    C.yearRewind(s, { at: L13.start - 0.1, until: L13.end + 0.3, from: 2026, to: 1100 });
    s.music('ancient', { at: L13.start + 0.6, fade: 3 });

    // c14 trial by ordeal
    const L14 = s.say('c14');
    C.ordeal(s, { L14, until: L14.end + 0.35 });

    // c16 the Tang Code on judicial torture
    const L16 = s.say('c16');
    s.music('tang', { at: L16.start - 0.3, fade: 2.5 });
    C.tangCode(s, { L16, until: L16.end + 0.45 });

    // c18 presumption of guilt
    const L18 = s.say('c18', { sub: false });
    s.music('drone', { at: L18.start, fade: 2 });
    const tStamp = L18.w('先当你');
    s.text('方式不同，逻辑一样：', { cls: 'lead', y: 330, sync: L18, until: L18.end + 0.4 });
    C.seal(s, { text: '有罪推定', x: 960, y: 530, size: 128, rot: -6, at: tStamp, end: L18.end + 0.35, gain: 1.2 });
    C.impact(s, { strength: 0.6, at: tStamp, sfx: null, color: 'rgba(229,82,63,0.12)' });
    s.text('先当你{r:有罪}，再让你{r:自证清白}。', { cls: 'lead', y: 730, sync: L18, until: L18.end + 0.35 });

    // c19 直到有人开始算一笔账——
    const L19 = s.say('c19', { sub: false });
    s.sfx('riser', { at: L19.end + 0.5 - 2.6, gain: 0.9 });
    s.music('silence', { at: L19.start + 0.2, fade: 1.4 });
    s.text('直到有人开始算一笔{g:账}——', { cls: 'lead', sync: L19, until: L19.end + 0.3 });
  },
  { mood: 'void' },
);

// =====================================================================
// 片名
E.scene(
  'title',
  s => {
    s.music('theme', { at: 0, fade: 0.05 });
    s.sfx('boom', { at: 0.05, gain: 1.2 });
    // narrator reads the title, then the promise
    s.t = 3.0;
    const T2 = s.say('t02', { sub: false });
    const out = T2.end + 0.1;
    const chars = ['宁', '可', '错', '放'];
    const box = s.el('div', { class: 'center', style: { left: '960px', top: '470px', display: 'flex', gap: '70px' } });
    const spans = chars.map(c => {
      const sp = E.h('div', { style: { fontSize: '210px', fontWeight: 900, color: 'var(--gold2)', lineHeight: 1, textShadow: '0 0 60px rgba(240,208,138,0.25)' } }, [c]);
      box.append(sp);
      return sp;
    });
    const sweep = E.h('div', {
      style: {
        position: 'absolute',
        inset: '-40px -200px',
        background: 'linear-gradient(100deg, transparent 40%, rgba(255,240,200,0.55) 50%, transparent 60%)',
        mixBlendMode: 'overlay',
        pointerEvents: 'none',
      },
    });
    box.append(sweep);
    s.fx(box, {
      start: 0.05,
      din: 0.01,
      end: out,
      dout: 0.9,
      update: (t, k) => {
        box.style.opacity = k;
        spans.forEach((sp, i) => {
          const p = E.ease.out(E.prog(t, 0.05 + i * 0.22, 1.6));
          sp.style.opacity = p.toFixed(3);
          sp.style.filter = p < 0.99 ? `blur(${((1 - p) * 18).toFixed(1)}px)` : 'none';
          sp.style.transform = `translateY(${((1 - p) * 30).toFixed(1)}px)`;
        });
        const sw = E.prog(t, 1.6, 2.2);
        sweep.style.transform = `translateX(${E.lerp(-900, 900, E.ease.inOut(sw)).toFixed(0)}px)`;
        box.style.transform = `scale(${(1.0 + 0.03 * E.prog(t, 0, 8)).toFixed(4)})`;
      },
    });
    for (const [y, d] of [
      [322, 1.2],
      [618, 1.3],
    ]) {
      const ln = s.el('div', { class: 'center', style: { left: '960px', top: y + 'px', height: '1px', background: 'var(--gold)', width: '0' } });
      s.fx(ln, {
        start: d,
        din: 0.5,
        end: out,
        dout: 0.9,
        update: (t, k) => {
          ln.style.opacity = (k * 0.7).toFixed(3);
          ln.style.width = (E.ease.inOut(E.prog(t, d, 1.6)) * 980).toFixed(0) + 'px';
        },
      });
    }
    s.text('法律最反直觉的设计，以及它背后的精妙', { cls: 'lead', y: 700, at: 1.6, until: T2.w('听起来') - 0.3, style: { fontSize: '44px', letterSpacing: '0.2em' } });
    s.text('听起来，像是对坏人的{s:仁慈}？', { cls: 'lead', y: 760, sync: T2, at: T2.w('听起来') - 0.05, until: out, style: { fontSize: '50px' } });

    const T3 = s.say('t03', { sub: false, at: out + 0.5 });
    s.text('但看到最后你会发现：', { cls: 'small', y: 450, sync: T3, until: T3.end + 0.8, style: { fontSize: '40px', color: 'var(--paper2)' } });
    s.text('这笔账，护着的是{g:你自己}。', { cls: 'body', y: 560, sync: T3, until: T3.end + 0.8, style: { fontSize: '86px' } });
  },
  { mood: 'gold' },
);
