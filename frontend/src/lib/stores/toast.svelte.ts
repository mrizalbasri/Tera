import type { ToastState, ToastType } from '$lib/types/ui';

/** State toast bersama — satu sumber untuk semua halaman. */
export const toast = $state<ToastState>({ message: '', type: 'info', visible: false });

let timer: ReturnType<typeof setTimeout> | undefined;

export function showToast(message: string, type: ToastType = 'info', durationMs = 3500) {
	clearTimeout(timer);
	toast.message = message;
	toast.type = type;
	toast.visible = true;
	timer = setTimeout(() => {
		toast.visible = false;
	}, durationMs);
}
