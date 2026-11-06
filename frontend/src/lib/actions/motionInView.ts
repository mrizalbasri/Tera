export function motionInView(node: Element) {
	let inView = false;
	const update = () => {
		node.classList.toggle('motion-active', inView && !document.hidden);
	};
	const observer = new IntersectionObserver(([entry]) => {
		inView = entry.isIntersecting;
		update();
	});
	observer.observe(node);
	document.addEventListener('visibilitychange', update);

	return {
		destroy() {
			observer.disconnect();
			document.removeEventListener('visibilitychange', update);
		}
	};
}
