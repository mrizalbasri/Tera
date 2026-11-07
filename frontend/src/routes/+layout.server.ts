import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = ({ locals, url }) => {
	// Track every route change so client navigation rechecks the session in hooks.
	const pathname = url.pathname;
	return {
	user: locals.user,
	admin: locals.admin,
	demoMode: locals.demoMode,
	financeWorkspace: Boolean(locals.admin) && /^\/(admin|reviews?|reports|dashboard|notifikasi)(\/|$)/.test(pathname)
	};
};
