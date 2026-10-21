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

export type ActorType = 'system' | 'agent' | 'employee' | 'reviewer';

export type SignalType = 'duplicate' | 'anomaly' | 'provider_degraded';

export type Severity = 'info' | 'warning' | 'blocking';

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
	processing_run_id: string | null;
	vendor: FieldConfidence;
	receipt_date: FieldConfidence;
	total: FieldConfidence;
	currency: FieldConfidence;
	category: FieldConfidence;
	line_items: ExtractedLineItem[];
	warnings: string[];
	provider: string;
	provider_degraded: boolean;
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

/** Permintaan klarifikasi ringkas dari respons process. */
export interface ClarificationRequest {
	code: string;
	message: string;
	fields: string[];
}

/** Klarifikasi tersimpan — memiliki id dan status (FR-09/FR-15). */
export interface Clarification {
	id: string;
	claim_id: string;
	processing_run_id: string | null;
	code: string;
	fields: string[];
	question: string;
	answer: string | null;
	status: ClarificationStatus;
	created_at: string;
	answered_at: string | null;
}

/** Keputusan resmi — hanya dibuat oleh backend (FR-08). */
export interface Decision {
	id: string;
	claim_id: string;
	processing_run_id: string;
	outcome: DecisionOutcome;
	reason_codes: string[];
	explanation: string;
	confidence: Numeric | null;
	anomaly_score: Numeric | null;
	source_signal_ids: string[];
	policy_version: number | null;
	created_by: ActorType;
	created_at: string;
}

export interface Review {
	id: string;
	claim_id: string;
	status: 'open' | 'decided' | 'cancelled';
	reviewer_reference: string | null;
	action: string | null;
	reason: string | null;
	created_at: string;
	decided_at: string | null;
}

/** Bukti duplikat/anomali terstruktur dari backend (FR-06/FR-07). */
export interface Signal {
	id: string;
	claim_id: string;
	processing_run_id: string;
	signal_type: SignalType;
	severity: Severity;
	confidence: Numeric | null;
	match_type: 'exact_hash' | 'likely_attributes' | null;
	matched_claim_ids: string[];
	compared_fields: string[];
	score: Numeric | null;
	triggered_rules: string[];
	evidence: Record<string, unknown>;
	detector_version: string;
	explanation: string;
	created_at: string;
}

export interface CreateClaimResponse {
	claim: Claim;
	receipts: Receipt[];
	idempotent_replay: boolean;
}

export interface ReplacementReceiptResponse {
	claim: Claim;
	receipt: Receipt;
}

/** Satu langkah terurut & redacted dalam kisah pemrosesan klaim (FR-12). */
export interface TimelineEntry {
	sequence: number;
	timestamp: string | null;
	step_name: string;
	status: string;
	summary: string;
	processing_run_id: string | null;
	duration_ms?: number | null;
	error_code: string | null;
	detail?: Record<string, unknown>;
	related_ids?: Record<string, string>;
}

export interface TimelineResponse {
	items: TimelineEntry[];
	total: number;
}

export interface ClaimListResponse {
	items: Claim[];
	total: number;
}

export interface Finding {
	processing_run_id: string;
	rule_id: string;
	passed: boolean;
	explanation: string;
	severity: Severity;
}

export interface ValidationFinding extends Finding {
	claim_id?: string;
	extraction_id?: string | null;
	actual?: unknown;
	expected?: string | null;
	reason_code?: string | null;
}

export interface PolicyEvaluation extends Finding {
	claim_id?: string;
	policy_id?: string;
	policy_version?: number;
	rule_type?: string;
	clarifiable?: boolean;
	actual_value?: unknown;
	limit?: unknown;
	reason_code?: string | null;
}

export interface ClaimDetailResponse {
	claim: Claim;
	receipts: Receipt[];
	extractions: ExtractionResult[];
	attempts: ExtractionAttempt[];
	validation_findings: ValidationFinding[];
	policy_evaluations: PolicyEvaluation[];
	signals: Signal[];
	decisions: Decision[];
}

export interface ProcessClaimResponse {
	claim: Claim;
	extractions: ExtractionResult[];
	attempts: ExtractionAttempt[];
	clarification: ClarificationRequest | null;
	decision: Decision | null;
}

export interface ClarificationListResponse {
	items: Clarification[];
	total: number;
}

export interface ReviewQueueItem {
	review: Review;
	claim: Claim;
	decision: Decision | null;
	signals: Signal[];
}

export interface ReviewQueueResponse {
	items: ReviewQueueItem[];
	total: number;
	snapshot?: string;
}

export interface ReviewDecisionResponse {
	claim: Claim;
	decision: Decision;
	review: Review;
}
