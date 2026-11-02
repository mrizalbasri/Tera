import type { Clerk } from '@clerk/clerk-js';

type ClerkUIConstructor = NonNullable<NonNullable<Parameters<Clerk['load']>[0]>['ui']>['ClerkUI'];

let instance: Promise<Clerk> | undefined;
let demoMode = false;

export function setAuthDemoMode(value: boolean) {
	if (typeof window !== 'undefined') demoMode = value;
}

export function getClerk(): Promise<Clerk> {
	if (typeof window === 'undefined') throw new Error('Clerk hanya tersedia di browser.');
	return instance ??= initialize().catch((cause) => { instance = undefined; throw cause; });
}

async function initialize(): Promise<Clerk> {
	const key = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
	if (!key) throw new Error('Login belum dikonfigurasi. Hubungi pengelola Tera.');
	let domain: string;
	try {
		domain = atob(key.split('_')[2]).replace(/\$$/, '');
		if (!/^(pk_test_|pk_live_)/.test(key) || !/^[a-z0-9]+(?:[.-][a-z0-9]+)+$/i.test(domain)) throw new Error();
	} catch { throw new Error('Konfigurasi login tidak valid. Hubungi pengelola Tera.'); }
	const uiWindow = window as unknown as { __internal_ClerkUICtor?: ClerkUIConstructor };
	if (!uiWindow.__internal_ClerkUICtor) {
		await new Promise<void>((resolve, reject) => {
			const script = document.createElement('script');
			const timer = setTimeout(() => { script.remove(); reject(new Error('Login terlalu lama dimuat. Periksa koneksi lalu coba lagi.')); }, 20000);
			script.src = `https://${domain}/npm/@clerk/ui@1/dist/ui.browser.js`;
			script.async = true;
			script.crossOrigin = 'anonymous';
			script.onload = () => { clearTimeout(timer); resolve(); };
			script.onerror = () => { clearTimeout(timer); script.remove(); reject(new Error('Login gagal dimuat. Periksa koneksi lalu coba lagi.')); };
			document.head.appendChild(script);
		});
	}
	const { Clerk } = await import('@clerk/clerk-js');
	const { idID } = await import('@clerk/localizations');
	const clerk = new Clerk(key);
	if (!uiWindow.__internal_ClerkUICtor) throw new Error('Komponen login belum tersedia. Coba muat ulang halaman.');
	await clerk.load({
		ui: { ClerkUI: uiWindow.__internal_ClerkUICtor },
		localization: {
			...idID,
			formFieldInputPlaceholder__emailAddress: 'Masukkan email kerja',
			signIn: { ...idID.signIn, start: { ...idID.signIn?.start, titleCombined: 'Masuk ke {{applicationName}}' } }
		}
	});
	return clerk;
}

export async function authFetch(path: string, init?: RequestInit): Promise<Response> {
	if (typeof window === 'undefined' || demoMode || !/^\/api\/(claims|reviews|reports|auth)(\/|\?|$)/.test(path)) return fetch(path, init);
	const headers = new Headers(init?.headers);
	const clerk = await getClerk();
	const token = await clerk.session?.getToken();
	if (token) headers.set('Authorization', `Bearer ${token}`);
	return fetch(path, { ...init, headers });
}
