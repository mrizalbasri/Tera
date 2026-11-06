export function reveal(node: HTMLElement) {
	node.classList.add('awaiting-reveal');
	const observer = new IntersectionObserver(
		([entry]) => {
			if (entry.isIntersecting) {
				node.classList.remove('awaiting-reveal');
			} else if (entry.boundingClientRect.top > window.innerHeight + 48) {
				// Only reset once the section is completely below the viewport so it never flickers mid-scroll.
				node.classList.add('awaiting-reveal');
			}
		},
		{ threshold: 0.08, rootMargin: '0px 0px -6% 0px' }
	);
	observer.observe(node);

	return { destroy: () => observer.disconnect() };
}
