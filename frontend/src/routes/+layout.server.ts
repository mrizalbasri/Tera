import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = ({ locals }) => ({ user: locals.user, admin: locals.admin, demoMode: locals.demoMode });
