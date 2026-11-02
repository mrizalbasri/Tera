export function motionInView(node: Element) {
	const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
	let inView = false;
	const update = () => {
		node.classList.toggle('motion-active', inView && !document.hidden && !preference.matches);
	};
	const observer = new IntersectionObserver(([entry]) => {
		inView = entry.isIntersecting;
		update();
	});
	observer.observe(node);
	document.addEventListener('visibilitychange', update);
	preference.addEventListener('change', update);

	return {
		destroy() {
			observer.disconnect();
			document.removeEventListener('visibilitychange', update);
			preference.removeEventListener('change', update);
		}
	};
}
