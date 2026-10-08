// Burned-in subtitles driven by the narration's word timings.
// Each voice line is split at punctuation; short neighbouring pieces are merged
// so a subtitle never flashes by. Exported as E.subs for the SRT file too.
(() => {
  const box = E.h('div', { class: 'subs' });
  const inner = E.h('span', { class: 'subs-in' });
  box.append(inner);
  document.getElementById('overlay').append(box);

  const DROP = /[，。；：、—…]+$/;
  const len = s => [...s.replace(/[\s，。？！；：、—…“”《》]/g, '')].length;
  const sep = p => (/[？！]/.test(p) ? p + ' ' : '  ');
  const tidy = s => s.replace(/^[，。；：、]+/, '').replace(DROP, '').trim();

  E.buildSubs = () => {
    const out = [];
    const vos = E.cues.filter(c => c.type === 'vo');
    vos.forEach((c, i) => {
      const segs = E.segments(c.id);
      const merged = [];
      for (const sg of segs) {
        const last = merged[merged.length - 1];
        if (last && len(last.text + sg.text) <= 15 && sg.end - last.start < 4.2 && !/[。？！]/.test(last.punct)) {
          last.text += sep(last.punct) + sg.text;
          last.end = sg.end;
          last.punct = sg.punct;
        } else merged.push({ ...sg });
      }
      const nextStart = i + 1 < vos.length ? vos[i + 1].at : Infinity;
      merged.forEach((m, j) => {
        const a = c.at + m.start - 0.05;
        const b =
          j + 1 < merged.length
            ? c.at + merged[j + 1].start - 0.05
            : Math.min(c.at + c.dur + 0.4, nextStart - 0.08);
        let text = m.text + (/[？！]/.test(m.punct) ? m.punct.replace(/[^？！]/g, '') : '');
        text = tidy(text);
        if (text) out.push({ a, b, text, show: c.sub, id: c.id });
      });
    });
    E.subsAll = out;
    E.subs = out.filter(x => x.show);
  };

  E.globalUpdaters.push(T => {
    const subs = E.subs || [];
    const it = subs.find(x => T >= x.a && T < x.b);
    if (!it) {
      box.style.opacity = 0;
      return;
    }
    if (inner.textContent !== it.text) inner.textContent = it.text;
    // soft edges only where a subtitle starts/ends next to a gap
    const prev = subs.find(x => Math.abs(x.b - it.a) < 0.02);
    const next = subs.find(x => Math.abs(x.a - it.b) < 0.02);
    let o = 1;
    if (!prev) o = Math.min(o, E.prog(T, it.a, 0.08));
    if (!next) o = Math.min(o, 1 - E.prog(T, it.b - 0.1, 0.1));
    box.style.opacity = o.toFixed(3);
  });
})();
