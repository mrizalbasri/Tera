import { env } from '$env/dynamic/private';

export const adminCookie = '__session';
export const backendUrl = () => (env.BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
export const isAdminPath = (path: string) => /^\/(admin|reviews?|reports|dashboard)(\/|$)/.test(path);

export const isEmployeePath = (path: string) => /^\/(pengajuan|riwayat|claims)(\/|$)/.test(path);
