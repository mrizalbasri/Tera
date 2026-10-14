export function reveal(node: HTMLElement) {
	if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
	if (node.getBoundingClientRect().top < window.innerHeight) return;

	node.classList.add('awaiting-reveal');
	const observer = new IntersectionObserver(([entry]) => {
		if (!entry.isIntersecting) return;
		node.classList.remove('awaiting-reveal');
		observer.disconnect();
	}, { threshold: 0, rootMargin: '0px 0px -32px 0px' });
	observer.observe(node);

	return { destroy: () => observer.disconnect() };
}
