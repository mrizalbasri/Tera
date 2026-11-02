export function reveal(node: HTMLElement) {
	if (typeof window === 'undefined') return;
	if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

	node.classList.add('awaiting-reveal');

	const observer = new IntersectionObserver(([entry]) => {
		if (!entry.isIntersecting) return;
		node.classList.remove('awaiting-reveal');
		observer.disconnect();
	}, { threshold: 0.05, rootMargin: '0px 0px -40px 0px' });

	requestAnimationFrame(() => {
		observer.observe(node);
	});

	return {
		destroy() {
			observer.disconnect();
		}
	};
}
