import type { Action } from 'svelte/action';

export const modalFocus: Action<HTMLElement, { onclose: () => void }> = (node, options) => {
	const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
	const focusable = () => [...node.querySelectorAll<HTMLElement>(
		'button:not([disabled]), a[href], input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex="0"]'
	)].filter((element) => element.getClientRects().length > 0);
	queueMicrotask(() => (focusable()[0] ?? node).focus());

	function onkeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			event.preventDefault();
			event.stopPropagation();
			options.onclose();
		}
		if (event.key !== 'Tab') return;
		const elements = focusable();
		const first = elements[0] ?? node;
		const last = elements.at(-1) ?? node;
		if (event.shiftKey && (document.activeElement === first || document.activeElement === node)) {
			event.preventDefault();
			last.focus();
		} else if (!event.shiftKey && (document.activeElement === last || document.activeElement === node)) {
			event.preventDefault();
			first.focus();
		}
	}
	node.addEventListener('keydown', onkeydown);
	return {
		update(next) { options = next; },
		destroy() {
			node.removeEventListener('keydown', onkeydown);
			if (previous?.isConnected) previous.focus();
		}
	};
};
