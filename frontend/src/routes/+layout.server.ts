import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = ({ locals, url }) => ({
	user: locals.user,
	admin: locals.admin,
	demoMode: locals.demoMode,
	financeWorkspace: Boolean(locals.admin) && /^\/(admin|reviews?|reports|dashboard)(\/|$)/.test(url.pathname)
});
