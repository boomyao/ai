// Render cover HTML files to PNG (1920×1200) plus a 1146×717 export.
//   node cover/shot.mjs a b c
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const DIR = path.dirname(fileURLToPath(import.meta.url));
const browser = await chromium.launch({ args: ['--allow-file-access-from-files', '--font-render-hinting=none'] });
for (const name of process.argv.slice(2)) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1200 } });
  page.on('pageerror', e => console.error('[pageerror]', e.message));
  await page.goto('file://' + path.join(DIR, `${name}.html`));
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 30000 });
  await page.waitForTimeout(300);
  const out = path.join(DIR, 'out', `cover-${name}.png`);
  await page.screenshot({ path: out });
  console.log(out);
  await page.close();
}
await browser.close();
