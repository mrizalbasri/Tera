// Run after pnpm build:
// ego-browser nodejs -e "await import('file:///ABSOLUTE_PATH/frontend/scripts/verify-claim-processing.mjs')"
// Uses a real built frontend and an isolated synthetic API, never production.
import { createServer } from 'node:http';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const id = '11111111-1111-4111-8111-111111111111';
const claim = { id, employee_id: 'synthetic', status: 'processing', currency: 'IDR' };
let uploads = 0;
let attempts = 0;
const backend = createServer(async (req, res) => {
	res.setHeader('content-type', 'application/json');
	if (req.url.startsWith('/auth/session')) {
		return res.end(JSON.stringify({ username: 'synthetic', role: 'employee', demo_mode: true }));
	}
	if (req.url === '/claims' && req.method === 'POST') {
		for await (const _chunk of req) { /* drain the synthetic upload */ }
		uploads++;
		res.statusCode = 201;
		return res.end(JSON.stringify({
			claim, receipts: [{ original_filename: 'synthetic.png', quality_score: 1 }],
		}));
	}
	if (req.url === `/claims/${id}/process`) {
		attempts++;
		await new Promise((resolve) => setTimeout(resolve, 200));
		if (attempts <= 2) {
			res.statusCode = 504;
			return res.end(JSON.stringify({ code: 'provider_timeout' }));
		}
		return res.end(JSON.stringify({
			claim, extractions: [], attempts: [], clarification: null, decision: null,
		}));
	}
	res.end(JSON.stringify({ items: [], total: 0 }));
});

await new Promise((resolve) => backend.listen(18082, '127.0.0.1', resolve));
const frontend = spawn('node', ['build'], {
	cwd: fileURLToPath(new URL('..', import.meta.url)),
	env: {
		...process.env, HOST: '127.0.0.1', PORT: '13002',
		ORIGIN: 'http://127.0.0.1:13002', BACKEND_URL: 'http://127.0.0.1:18082',
	},
	stdio: 'ignore',
});
const task = await taskSpace('Tera OCR retry regression');
console.log({ taskSpaceId: task.spaceId });
const page = task.page('p1');
try {
	let ready = false;
	for (let index = 0; index < 100; index++) {
		if (frontend.exitCode !== null) throw new Error(`Frontend exited: ${frontend.exitCode}`);
		try {
			await fetch('http://127.0.0.1:13002/');
			ready = true;
			break;
		} catch {
			await new Promise((resolve) => setTimeout(resolve, 100));
		}
	}
	assert.ok(ready, 'built frontend must start');
	await page.goto('http://127.0.0.1:13002/pengajuan');
	console.log(await page.snapshot());
	await page.waitForSelector('#file-upload', { state: 'attached' });
	await page.evaluate(() => {
		const data = new DataTransfer();
		data.items.add(new File(['synthetic'], 'synthetic.png', { type: 'image/png' }));
		const input = document.querySelector('#file-upload');
		input.files = data.files;
		input.dispatchEvent(new Event('change', { bubbles: true }));
	});
	await page.click("loc=role:button[name='Periksa nota']");
	await page.waitForFunction(() => document.body.textContent.includes('Pembacaan belum selesai'));
	assert.equal(await page.evaluate(() =>
		[...document.querySelectorAll('.steps-host button')].filter(
			(button) => button.textContent.trim() === 'Coba proses lagi',
		).length,
	), 1, 'retry action must live in the status card, not a separate error bubble');
	for (let retry = 0; retry < 2; retry++) {
		await page.click("loc=role:button[name='Coba proses lagi']");
		await page.waitForFunction(() =>
			document.querySelectorAll('.steps-host').length === 1
			&& document.querySelector('.task-status')?.textContent.trim() === 'Hasil pemeriksaan',
		);
		if (retry === 0) {
			await page.waitForSelector('.steps-host .message-actions button');
		}
		assert.equal(await page.evaluate(() => document.querySelectorAll('.steps-host').length), 1);
		assert.equal(await page.evaluate(() => document.querySelectorAll('.error-bubble').length), 0);
	}
	await page.waitForFunction(() => ![...document.querySelectorAll('button')].some(
		(button) => button.textContent.trim() === 'Coba proses lagi',
	));
	assert.equal(uploads, 1, 'retry must not upload or create a second claim');
	assert.equal(attempts, 3, 'retries must be explicit and bounded');
	console.log({ passed: true, uploads, attempts, scenario: 'timeout twice, then success in one card' });
	await task.finish({ keep: [] });
} finally {
	frontend.kill();
	await new Promise((resolve) => backend.close(resolve));
}
