const { createServer } = require('node:http');
const { spawn } = require('node:child_process');
const { resolve } = require('node:path');
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const A = '11111111-1111-4111-8111-111111111111';
const B = '22222222-2222-4222-8222-222222222222';
function detail(id) {
  const claim = { id, employee_id: 'synthetic-user', status: 'escalated', currency: 'IDR', declared_amount: null, amount: { value: '120000', source: 'extraction', complete: true, conflict: false }, current_decision_id: null, submitted_at: '2026-10-26T00:00:00Z' };
  const receipts = [1, 2].map(n => ({ id: `${id}-${n}`, claim_id: id, original_filename: `synthetic-${n}.png`, media_type: 'image/png', quality_findings: [], quality_score: 1 }));
  const extractions = receipts.map((r, i) => ({ id: `ex-${r.id}`, receipt_id: r.id, processing_run_id: 'run', vendor: { value: `Vendor ${id === A ? 'A' : 'B'}${i+1}`, confidence: 1 }, receipt_date: { value: '2026-10-26', confidence: 1 }, total: { value: '60000', confidence: 1 }, currency: { value: 'IDR', confidence: 1 }, category: { value: 'meal', confidence: 1 }, line_items: [], warnings: [], provider: 'mock', provider_degraded: false }));
  return { claim, receipts, extractions, attempts: [], validation_findings: [], policy_evaluations: [], signals: [], decisions: [] };
}
const fixtures = [detail(A), detail(B)];
const backend = createServer((req, res) => {
  if (req.url.endsWith('/content')) {
    res.setHeader('content-type', 'image/png');
    return res.end(Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a8H8AAAAASUVORK5CYII=', 'base64'));
  }
  res.setHeader('content-type', 'application/json');
  if (req.url.startsWith('/auth/session')) return res.end(JSON.stringify({ username: 'synthetic', role: 'admin', demo_mode: true }));
  if (req.url.startsWith('/reviews')) return res.end(JSON.stringify({ items: fixtures.map(d => ({ claim: d.claim, review: { id: `review-${d.claim.id}`, status: 'open', created_at: '2026-10-26T00:00:00Z' }, signals: [], decision: null })), total: 2, snapshot: 'a'.repeat(64) }));
  if (req.url.startsWith('/claims?')) return res.end(JSON.stringify({ items: fixtures.map(d => d.claim), total: fixtures.length }));
  if (/^\/claims\/[^/]+\/(timeline|clarifications)$/.test(req.url)) return res.end(JSON.stringify({ items: [] }));
  const d = fixtures.find(d => req.url === `/claims/${d.claim.id}`);
  if (d) return res.end(JSON.stringify(d));
  res.statusCode = 404; res.end('{}');
});
(async () => {
  await new Promise(r => backend.listen(18081, '127.0.0.1', r));
  const frontend = spawn(process.execPath, ['build'], { cwd: resolve(__dirname, '..'), env: { ...process.env, HOST: '127.0.0.1', PORT: '13001', ORIGIN: 'http://127.0.0.1:13001', BACKEND_URL: 'http://127.0.0.1:18081' }, stdio: 'ignore' });
  let browser;
  try {
    for (let i=0; i<100; i++) { try { await fetch('http://127.0.0.1:13001/'); break; } catch { await new Promise(r => setTimeout(r, 100)); } }
    browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_CHANNEL ? { channel: process.env.PLAYWRIGHT_CHANNEL } : {}) });
    const page = await browser.newPage();
    await page.goto(`http://127.0.0.1:13001/reviews/${A}`);
    await page.getByRole('heading', { name: `Klaim ${A}`, exact: true }).waitFor();
    const results = [];
    async function check(name, fn) { try { await fn(); results.push({ name, passed: true }); } catch (e) { results.push({ name, passed: false, error: e.message }); } }
    await check('all receipt evidence can be selected and matches extraction', async () => {
      const selector = page.getByLabel('Pilih nota yang diperiksa');
      await selector.waitFor({ timeout: 2000 });
      await selector.selectOption(`${A}-1`);
      await page.getByText('Vendor A1', { exact: true }).waitFor();
      assert.match(await page.locator('.receipt-preview img').getAttribute('src'), /-1\/content$/);
    });
    await check('client navigation loads the requested claim instead of stale evidence', async () => {
      await page.evaluate(id => { const a = document.createElement('a'); a.href = `/reviews/${id}`; a.textContent = 'Synthetic next claim'; document.body.append(a); }, B);
      await page.getByRole('link', { name: 'Synthetic next claim' }).click();
      await page.waitForURL(`**/reviews/${B}`);
      await page.getByRole('heading', { name: `Klaim ${B}`, exact: true }).waitFor({ timeout: 2500 });
      await page.getByText('Vendor B2', { exact: true }).waitFor();
      assert.equal(await page.getByText('Vendor A1', { exact: true }).count(), 0);
    });
    await check('late claim responses do not overwrite the new claim', async () => {
      let release;
      const gate = new Promise(r => { release = r; });
      let started;
      const requested = new Promise(r => { started = r; });
      await page.route(`**/api/claims/${A}`, async route => { started(); await gate; await route.fulfill({ json: detail(A) }); });
      async function navigate(id) {
        await page.evaluate(id => { const a = document.createElement('a'); a.href = `/reviews/${id}`; a.id = 'synthetic-nav'; document.getElementById(a.id)?.remove(); document.body.append(a); a.click(); }, id);
        await page.waitForURL(`**/reviews/${id}`);
      }
      await navigate(A);
      await requested;
      await navigate(B);
      await page.getByRole('heading', { name: `Klaim ${B}`, exact: true }).waitFor();
      const delivered = page.waitForResponse(`**/api/claims/${A}`);
      release();
      await delivered;
      await page.waitForTimeout(100);
      assert.equal(await page.getByRole('heading', { name: `Klaim ${B}`, exact: true }).count(), 1);
      await page.unroute(`**/api/claims/${A}`);
    });
    await check('navigation clears a decision draft and enforces the API reason limit', async () => {
      await page.getByRole('button', { name: 'Setujui klaim', exact: true }).click();
      const reason = page.getByRole('textbox', { name: 'Alasan keputusan' });
      await reason.fill('Synthetic draft for claim B');
      assert.equal(await reason.getAttribute('maxlength'), '2000');
      await page.evaluate(id => { const a = document.createElement('a'); a.href = `/reviews/${id}`; document.body.append(a); a.click(); }, A);
      await page.waitForURL(`**/reviews/${A}`);
      await page.getByRole('heading', { name: `Klaim ${A}`, exact: true }).waitFor();
      assert.equal(await reason.count(), 0);
      await page.getByRole('button', { name: 'Setujui klaim', exact: true }).click();
      assert.equal(await reason.inputValue(), '');
    });
    await check('late saved decisions do not replace another claim', async () => {
      let release;
      const gate = new Promise(r => { release = r; });
      let started;
      const requested = new Promise(r => { started = r; });
      const endpoint = `**/api/reviews/${A}/decision`;
      await page.route(endpoint, async route => {
        started();
        await gate;
        const saved = detail(A);
        await route.fulfill({ json: { claim: { ...saved.claim, status: 'approved' }, review: { id: 'saved-review', status: 'decided' }, decision: { id: 'synthetic-saved-decision', claim_id: A, outcome: 'approved' } } });
      });
      await page.getByRole('textbox', { name: 'Alasan keputusan' }).fill('Synthetic approval for claim A');
      await page.getByRole('button', { name: 'Ya, simpan persetujuan' }).click();
      await requested;
      await page.evaluate(id => { const a = document.createElement('a'); a.href = `/reviews/${id}`; document.body.append(a); a.click(); }, B);
      await page.waitForURL(`**/reviews/${B}`);
      await page.getByRole('heading', { name: `Klaim ${B}`, exact: true }).waitFor();
      const delivered = page.waitForResponse(endpoint);
      release();
      await delivered;
      await page.waitForTimeout(100);
      assert.equal(await page.getByRole('heading', { name: `Klaim ${B}`, exact: true }).count(), 1);
      await page.getByRole('button', { name: 'Setujui klaim', exact: true }).waitFor();
      await page.unroute(endpoint);
    });
    await check('history matches OCR to the selected receipt after a replacement', async () => {
      const claim = detail(A);
      claim.extractions.pop();
      await page.route(`**/api/claims/${A}`, route => route.fulfill({ json: claim }));
      await page.goto(`http://127.0.0.1:13001/riwayat/${A}`);
      await page.getByRole('img', { name: 'Bukti nota synthetic-2.png' }).waitFor();
      assert.equal(await page.getByText('Vendor A1').count(), 0);
      await page.getByLabel('Pilih nota').selectOption(`${A}-1`);
      await page.getByRole('img', { name: 'Bukti nota synthetic-1.png' }).waitFor();
      await page.getByText('Vendor A1').waitFor();
      await page.unroute(`**/api/claims/${A}`);
    });
    await check('a missing timeline leaves claim evidence accessible and can be retried', async () => {
      const endpoint = `**/api/claims/${B}/timeline`;
      await page.route(endpoint, route => route.fulfill({ status: 404, json: {} }));
      await page.goto(`http://127.0.0.1:13001/admin/claims/${B}`);
      await page.getByRole('img', { name: 'Bukti nota synthetic-2.png' }).waitFor({ timeout: 3000 });
      await page.getByText('Vendor B2').waitFor();
      await page.getByText('Jejak pemeriksaan gagal dimuat.').waitFor();
      await page.unroute(endpoint);
      const retried = page.waitForResponse(endpoint);
      await page.getByRole('button', { name: 'Muat ulang jejak pemeriksaan' }).click();
      assert.equal((await retried).status(), 200);
      await page.getByText('Jejak pemeriksaan gagal dimuat.').waitFor({ state: 'hidden' });
    });
    await check('clarification uses explicit vendor and date fields', async () => {
      const question = { id: 'synthetic-question', claim_id: A, status: 'open', fields: ['vendor', 'receipt_date'], question: 'Lengkapi nama toko dan tanggal nota.' };
      const endpoint = `**/api/claims/${A}/clarifications`;
      await page.route(endpoint, route => route.fulfill({ json: { items: [question], total: 1 } }));
      await page.goto(`http://127.0.0.1:13001/claims/${A}/clarification`);
      await page.getByLabel('Nama toko', { exact: true }).fill('Toko Sinar Jaya');
      const date = page.getByLabel('Tanggal nota', { exact: true });
      assert.equal(await date.getAttribute('type'), 'date');
      await date.fill('2026-01-01');
      let submitted;
      await page.route(`**/api/claims/${A}/clarifications/synthetic-question/answer`, async route => {
        submitted = route.request().postDataJSON();
        await route.fulfill({ json: {} });
      });
      await page.getByRole('button', { name: 'Kirim jawaban', exact: true }).click();
      await page.waitForURL(`**/claims/${A}`);
      assert.deepEqual(submitted.confirmed_fields, { vendor: 'Toko Sinar Jaya', receipt_date: '2026-01-01' });
      await page.unroute(endpoint);
    });
    for (const width of [320, 375, 414, 768, 1440]) {
      await check(`claim pages fit viewport ${width}px`, async () => {
        await page.setViewportSize({ width, height: 900 });
        for (const route of ['/reviews', `/reviews/${A}`, '/admin/claims', `/claims/${A}`]) {
          await page.goto(`http://127.0.0.1:13001${route}`);
          await page.locator('.claim-value').first().waitFor({ state: 'attached', timeout: 4000 }).catch(async () => {
            throw new Error(`${route}: ${await page.locator('body').innerText()}`);
          });
          const overflow = await page.evaluate(() => {
            const width = document.documentElement.clientWidth;
            return [...document.querySelectorAll('main, .panel, .table-card, .table-container, .table-wrap')]
              .some(element => element.getBoundingClientRect().right > width + 1);
          });
          assert.equal(overflow, false, `${route} overflows ${width}px`);
        }
      });
    }
    console.log(JSON.stringify(results, null, 2));
    process.exitCode = results.every(r => r.passed) ? 0 : 1;
  } finally { if (browser) await browser.close(); frontend.kill(); backend.close(); }
})().catch(e => { console.error(e.message); process.exitCode = 1; backend.close(); });
