const { createServer } = require('node:http');
const { spawn } = require('node:child_process');
const { resolve } = require('node:path');
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const A = '11111111-1111-4111-8111-111111111111';
const B = '22222222-2222-4222-8222-222222222222';
function detail(id) {
  const claim = { id, employee_id: 'synthetic-user', status: 'escalated', currency: 'IDR', declared_amount: '120000', current_decision_id: null, submitted_at: '2026-10-26T00:00:00Z' };
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
  if (req.url.startsWith('/reviews')) return res.end(JSON.stringify({ items: fixtures.map(d => ({ claim: d.claim, review: { id: `review-${d.claim.id}`, status: 'open' }, signals: [], decision: null })), total: 2, snapshot: 'a'.repeat(64) }));
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
    browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome' });
    const page = await browser.newPage();
    await page.goto(`http://127.0.0.1:13001/reviews/${A}`);
    await page.getByRole('heading', { name: `Klaim ${A}`, exact: true }).waitFor();
    const results = [];
    async function check(name, fn) { try { await fn(); results.push({ name, passed: true }); } catch (e) { results.push({ name, passed: false, error: e.message.slice(0, 300) }); } }
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
    console.log(JSON.stringify(results, null, 2));
    process.exitCode = results.every(r => r.passed) ? 0 : 1;
  } finally { if (browser) await browser.close(); frontend.kill(); backend.close(); }
})().catch(e => { console.error(e.message); process.exitCode = 1; backend.close(); });
