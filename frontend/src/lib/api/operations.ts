import { apiRequest } from './client';
import type { ClaimStatus } from '$lib/types/claim';

export interface CheckpointSummary {
	claim_id: string;
	employee_id: string;
	status: ClaimStatus;
	declared_amount: string | null;
	currency: string;
	submitted_at: string;
	stage: string | null;
	next_nodes: string[];
	checkpoint_id: string | null;
	created_at: string | null;
}

export interface CheckpointHistoryEntry {
	checkpoint_id: string | null;
	stage: string | null;
	next: string[];
	step: number | null;
	source: string | null;
	created_at: string | null;
	has_interrupts: boolean;
}

export interface CheckpointDetail {
	claim_id: string;
	status: ClaimStatus;
	run_status: string | null;
	stage: string | null;
	next_nodes: string[];
	checkpoint_id: string | null;
	created_at: string | null;
	values: Record<string, unknown>;
	history: CheckpointHistoryEntry[];
}

export async function listCheckpoints(stage?: string): Promise<CheckpointSummary[]> {
	const params = stage ? `?stage=${encodeURIComponent(stage)}` : '';
	return apiRequest<CheckpointSummary[]>(`/operations/checkpoints${params}`);
}

export async function getCheckpoint(claimId: string): Promise<CheckpointDetail> {
	return apiRequest<CheckpointDetail>(`/operations/checkpoints/${encodeURIComponent(claimId)}`);
}

export async function resumeCheckpoint(claimId: string): Promise<{ status: string; claim_id: string; outcome?: string }> {
	return apiRequest<{ status: string; claim_id: string; outcome?: string }>(
		`/operations/checkpoints/${encodeURIComponent(claimId)}/resume`,
		{ method: 'POST' }
	);
}
