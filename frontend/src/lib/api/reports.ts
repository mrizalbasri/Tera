import { apiRequest, BASE_URL, HTTP_STATUS_MESSAGES } from './client';
import { authFetch } from '$lib/auth';

export interface ReportSummary {
	period_from: string | null;
	period_to: string | null;
	total_claims: number;
	approved_claims: number;
	rejected_claims: number;
	pending_claims: number;
	automated_claims: number;
	manual_claims: number;
	duplicate_count: number;
	anomaly_count: number;
	average_duration_ms: number | null;
	estimated_time_saved_minutes: number;
    active_duration_ms?: number | null;
    employee_wait_ms?: number | null;
    reviewer_wait_ms?: number | null;
    measured_claims?: number;
    provider_input_tokens?: number | null;
    provider_output_tokens?: number | null;
    provider_measured_calls?: number;
    provider_models?: string[];
}

export interface ReportFilters {
	periodFrom?: string;
	periodTo?: string;
	employeeId?: string;
}

function query(filters: ReportFilters): string {
	const params = new URLSearchParams();
	if (filters.periodFrom) params.set('period_from', filters.periodFrom);
	if (filters.periodTo) params.set('period_to', filters.periodTo);
	if (filters.employeeId) params.set('employee_id', filters.employeeId);
	const encoded = params.toString();
	return encoded ? `?${encoded}` : '';
}

export function getReportSummary(filters: ReportFilters = {}): Promise<ReportSummary> {
	return apiRequest<ReportSummary>(`/reports/summary${query(filters)}`);
}

export async function downloadReport(filters: ReportFilters = {}): Promise<Blob> {
	const response = await authFetch(`${BASE_URL}/reports/claims.csv${query(filters)}`);
	if (response.status === 401) window.location.assign('/login');
	if (!response.ok) {
		const friendly = HTTP_STATUS_MESSAGES[response.status] ?? 'Gagal mengunduh laporan. Silakan coba lagi nanti.';
		throw new Error(friendly);
	}
	return response.blob();
}
