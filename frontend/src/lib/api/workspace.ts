import { apiRequest } from './client';

export interface Notification {
	id: string;
	created_at: string;
	revision: number;
	payload: { claim_id: string; status: string; message: string; read_at: string | null; resolved: boolean; reminder: boolean };
}

export interface PolicyRule {
	rule_id: string;
	rule_type: string;
	limit?: string | number | null;
	currency?: string;
	required_terms?: string[];
	prohibited_terms?: string[];
}

export interface PolicyDraft {
	category: string;
	effective_from: string;
	effective_to: string | null;
	source: string;
	rules: PolicyRule[];
}

export interface PolicyVersion {
	id: string;
	revision: number;
	created_at: string;
	payload: { draft: PolicyDraft; status: 'draft' | 'published'; policy?: { version: number }; published_at?: string; published_by?: string };
}

const json = (body: unknown, method = 'POST'): RequestInit => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
export const getNotifications = (offset = 0) => apiRequest<{ items: Notification[] }>(`/notifications?limit=50&offset=${offset}`);
export const markNotificationRead = (id: string) => apiRequest<Notification>(`/notifications/${encodeURIComponent(id)}/read`, json({}));
export const getPolicyVersions = (offset = 0) => apiRequest<{ items: PolicyVersion[] }>(`/policies?limit=50&offset=${offset}`);
export const createPolicy = (draft: PolicyDraft) => apiRequest<PolicyVersion>('/policies', json(draft));
export const editPolicy = (id: string, draft: PolicyDraft, revision: number) => apiRequest<PolicyVersion>(`/policies/${encodeURIComponent(id)}`, json({ draft, revision }, 'PUT'));
export const publishPolicy = (id: string, revision: number) => apiRequest<PolicyVersion>(`/policies/${encodeURIComponent(id)}/publish`, json({ revision }));
export const importBaselinePolicies = () => apiRequest<{ items: PolicyVersion[] }>('/policies/import-baseline', json({}));
export const getPolicyAudit = (id: string) => apiRequest<{ items: { event_type: string; timestamp: string; safe_payload: { actor_reference?: string } }[] }>(`/policies/${encodeURIComponent(id)}/audit`);
