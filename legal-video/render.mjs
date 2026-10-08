// Frame renderer: drives src/index.html in headless Chromium and pipes frames
// into ffmpeg.
//
//   node render.mjs info                       → print duration, cues, chapters (writes out/cues.json)
//   node render.mjs stills 1.5 10 42.3         → PNG stills into out/stills/
//   node render.mjs video [--workers 3] [--fps 30] [--from S --to S]
//                                              → out/video.mp4 (silent)
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(ROOT, 'out');
fs.mkdirSync(OUT, { recursive: true });
const ONLY = (() => { const i = process.argv.indexOf('--only'); return i >= 0 ? process.argv[i + 1] : ''; })();
const PAGE = 'file://' + path.join(ROOT, 'src/index.html') + (ONLY ? `?only=${ONLY}` : '');

const args = process.argv.slice(2);
const mode = args[0];
const opt = (name, def) => {
  const i = args.indexOf('--' + name);
  return i >= 0 ? args[i + 1] : def;
};

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('[pageerror]', e.message));
  page.on('console', m => m.type() === 'error' && console.error('[console]', m.text()));
  await page.goto(PAGE);
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 60000 });
  return page;
}

async function launch() {
  return chromium.launch({ args: ['--font-render-hinting=none', '--disable-gpu-vsync', '--allow-file-access-from-files'] });
}

if (mode === 'info') {
  const browser = await launch();
  const page = await openPage(browser);
  const info = await page.evaluate(() => ({
    total: window.__total,
    cues: window.__cues,
    subs: window.__subs,
    chapters: window.__chapters,
    scenes: window.__scenes,
  }));
  fs.writeFileSync(path.join(OUT, opt('out', 'cues.json')), JSON.stringify(info, null, 1));
  const fmt = s => `${Math.floor(s / 60)}:${(s % 60).toFixed(1).padStart(4, '0')}`;
  console.log('total', fmt(info.total), info.total.toFixed(2) + 's', 'cues', info.cues.length, 'subs', info.subs.length);
  for (const c of info.scenes) console.log('  scene', fmt(c.start), c.id, c.dur.toFixed(1) + 's');
  await browser.close();
} else if (mode === 'stills') {
  const browser = await launch();
  const page = await openPage(browser);
  const dir = path.join(OUT, 'stills');
  fs.mkdirSync(dir, { recursive: true });
  for (const ts of args.slice(1)) {
    const t = Number(ts);
    await page.evaluate(t => E.seek(t), t);
    const f = path.join(dir, `t${t.toFixed(2).padStart(7, '0')}.png`);
    await page.screenshot({ path: f });
    console.log(f);
  }
  await browser.close();
} else if (mode === 'video') {
  const fps = Number(opt('fps', 30));
  const workers = Number(opt('workers', 3));
  const browser0 = await launch();
  const p0 = await openPage(browser0);
  const total = await p0.evaluate(() => window.__total);
  await browser0.close();
  const from = Number(opt('from', 0));
  const to = Math.min(Number(opt('to', total)), total);
  const f0 = Math.round(from * fps);
  const f1 = Math.round(to * fps);
  const per = Math.ceil((f1 - f0) / workers);
  const segDir = path.join(OUT, 'segs');
  fs.mkdirSync(segDir, { recursive: true });
  const started = Date.now();
  let done = 0;
  const jobs = Array.from({ length: workers }, async (_, w) => {
    const a = f0 + w * per;
    const b = Math.min(f1, a + per);
    if (a >= b) return null;
    const segFile = path.join(segDir, `seg${String(w).padStart(2, '0')}.mp4`);
    const ff = spawn(
      'ffmpeg',
      [
        '-y', '-loglevel', 'error',
        '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'png', '-i', '-',
        '-vf', 'format=yuv420p',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', String(opt('crf', 18)), '-tune', 'film',
        '-r', String(fps), segFile,
      ],
      { stdio: ['pipe', 'inherit', 'inherit'] },
    );
    const browser = await launch();
    const page = await openPage(browser);
    for (let f = a; f < b; f++) {
      await page.evaluate(t => E.seek(t), f / fps);
      const buf = await page.screenshot({ type: 'png' });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      done++;
      if (done % 300 === 0) {
        const el = (Date.now() - started) / 1000;
        const rate = done / el;
        console.log(`frames ${done}/${f1 - f0}  ${rate.toFixed(1)} fps  eta ${((f1 - f0 - done) / rate / 60).toFixed(1)} min`);
      }
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
    await browser.close();
    return segFile;
  });
  const segs = (await Promise.all(jobs)).filter(Boolean);
  const list = path.join(segDir, 'list.txt');
  fs.writeFileSync(list, segs.map(s => `file '${s}'`).join('\n'));
  const outFile = path.join(OUT, opt('out', 'video.mp4'));
  await new Promise((res, rej) => {
    const p = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', outFile], {
      stdio: 'inherit',
    });
    p.on('close', c => (c === 0 ? res() : rej(new Error('concat failed'))));
  });
  console.log('wrote', outFile, `in ${((Date.now() - started) / 60000).toFixed(1)} min`);
} else {
  console.log('usage: node render.mjs info | stills <t...> | video [--workers N]');
}
