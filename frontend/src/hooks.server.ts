import { error, redirect, type Handle } from '@sveltejs/kit';
import { adminCookie, backendUrl, isAdminPath, isEmployeePath } from '$lib/server/admin';

export const handle: Handle = async ({ event, resolve }) => {
	const token = event.cookies.get(adminCookie);
	event.locals.admin = null;
	event.locals.user = null;
	const protectedPage = isAdminPath(event.url.pathname) || isEmployeePath(event.url.pathname);
	event.locals.demoMode = false;
	if (!event.url.pathname.startsWith('/api/')) {
		let response: Response;
		try {
			response = await event.fetch(`${backendUrl()}/auth/session`, { headers: token ? { cookie: `${adminCookie}=${token}` } : {} });
		} catch {
			if (protectedPage) error(503, 'Layanan login belum dapat dihubungi. Coba lagi nanti.');
			response = new Response(null, { status: 503 });
		}
		if (response.ok) {
			const session = await response.json();
			event.locals.demoMode = session.demo_mode === true;
			event.locals.user = session;
			if (session.role === 'admin') event.locals.admin = session;
		} else if (response.status !== 401 && protectedPage) error(503, 'Sesi login belum dapat diperiksa. Coba lagi nanti.');
	}
	if (event.locals.demoMode && ['/login', '/sso-callback'].includes(event.url.pathname)) redirect(303, '/reviews');
	if (protectedPage && !event.locals.user) redirect(303, '/login');
	if (isAdminPath(event.url.pathname) && !event.locals.admin) error(403, 'Akses admin diperlukan.');
	const response = await resolve(event);
	if (token || event.locals.demoMode || protectedPage || event.url.pathname === '/login') response.headers.set('Cache-Control', 'no-store');
	return response;
};
