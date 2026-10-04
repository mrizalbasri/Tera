/**
 * Tipe respons API yang mengikuti kontrak backend (backend/app/schemas/core.py).
 * Backend mengirim Decimal sebagai number atau string, jadi bidang nominal
 * memakai Numeric dan dinormalkan lewat toNumber() sebelum ditampilkan.
 */

export type Numeric = number | string;

export type ClaimStatus =
	| 'received'
	| 'processing'
	| 'needs_clarification'
	| 'escalated'
	| 'approved'
	| 'rejected';

export type DecisionOutcome =
	| 'approved'
	| 'rejected'
	| 'needs_clarification'
	| 'escalated';

export type ClarificationStatus = 'open' | 'answered' | 'cancelled';

export interface Claim {
	id: string;
	employee_id: string;
	status: ClaimStatus;
	submitted_at: string;
	currency: string;
	declared_amount: Numeric | null;
	current_decision_id: string | null;
	created_at: string;
	updated_at: string;
}

export interface Receipt {
	id: string;
	claim_id: string;
	original_filename: string;
	media_type: string;
	storage_reference: string;
	content_hash: string;
	quality_score: Numeric | null;
	quality_findings: string[];
	created_at: string;
}

export interface FieldConfidence {
	value: unknown;
	confidence: Numeric;
}

export interface ExtractedLineItem {
	description: string;
	quantity: Numeric;
	unit_price: Numeric;
	total: Numeric;
}

export interface ExtractionResult {
	id: string;
	receipt_id: string;
	vendor: FieldConfidence;
	receipt_date: FieldConfidence;
	total: FieldConfidence;
	currency: FieldConfidence;
	category: FieldConfidence;
	line_items: ExtractedLineItem[];
	warnings: string[];
	provider: string;
	created_at: string;
}

export interface ExtractionAttempt {
	attempt: number;
	preprocessing: string[];
	confidence: Record<string, Numeric>;
	extraction_id: string | null;
	error_code: string | null;
	message: string | null;
	created_at: string;
}

export interface ClarificationRequest {
	code: string;
	message: string;
	fields: string[];
}

export interface CreateClaimResponse {
	claim: Claim;
	receipts: Receipt[];
	idempotent_replay: boolean;
}

export interface ClaimListResponse {
	items: Claim[];
	total: number;
}

export interface ClaimDetailResponse {
	claim: Claim;
	receipts: Receipt[];
	extractions: ExtractionResult[];
	attempts: ExtractionAttempt[];
}

export interface ProcessClaimResponse {
	claim: Claim;
	extractions: ExtractionResult[];
	attempts: ExtractionAttempt[];
	clarification: ClarificationRequest | null;
}
