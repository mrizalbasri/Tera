/** Tipe tampilan UI yang dipakai lintas route dan komponen. */

export type AgentStepStatus =
	| 'pending'
	| 'active'
	| 'done'
	| 'warn'
	| 'failed'
	| 'skipped';

export interface AgentStepView {
	label: string;
	detail?: string;
	status: AgentStepStatus;
}

export type ToastType = 'error' | 'success' | 'info';

export interface ToastState {
	message: string;
	type: ToastType;
	visible: boolean;
}
