import { describe, it, expect, vi, beforeEach } from 'vitest';
import { reveal } from './reveal';
import { motionInView } from './motionInView';

describe('DOM actions', () => {
	let observerCallback: (entries: Array<{ isIntersecting: boolean; boundingClientRect: { top: number } }>) => void;
	const observe = vi.fn();
	const disconnect = vi.fn();

	beforeEach(() => {
		observe.mockClear();
		disconnect.mockClear();
		vi.stubGlobal(
			'IntersectionObserver',
			class {
				constructor(cb: typeof observerCallback) {
					observerCallback = cb;
				}
				observe = observe;
				disconnect = disconnect;
			}
		);
		vi.stubGlobal('window', { innerHeight: 800 });
	});

	it('reveal toggles awaiting-reveal class based on intersection and scroll position', () => {
		const classes = new Set<string>();
		const node = {
			classList: {
				add: (c: string) => classes.add(c),
				remove: (c: string) => classes.delete(c)
			}
		} as unknown as HTMLElement;

		const handle = reveal(node);
		expect(classes.has('awaiting-reveal')).toBe(true);
		expect(observe).toHaveBeenCalledWith(node);

		observerCallback([{ isIntersecting: true, boundingClientRect: { top: 200 } }]);
		expect(classes.has('awaiting-reveal')).toBe(false);

		observerCallback([{ isIntersecting: false, boundingClientRect: { top: 400 } }]);
		expect(classes.has('awaiting-reveal')).toBe(false);

		observerCallback([{ isIntersecting: false, boundingClientRect: { top: 900 } }]);
		expect(classes.has('awaiting-reveal')).toBe(true);

		handle.destroy();
		expect(disconnect).toHaveBeenCalledTimes(1);
	});

	it('motionInView toggles motion-active class on intersection and document visibility', () => {
		const classes = new Set<string>();
		const node = {
			classList: {
				toggle: (c: string, force: boolean) => (force ? classes.add(c) : classes.delete(c))
			}
		} as unknown as Element;

		let visibilityHandler: (() => void) | undefined;
		const doc = {
			hidden: false,
			addEventListener: vi.fn((_evt: string, cb: () => void) => {
				visibilityHandler = cb;
			}),
			removeEventListener: vi.fn()
		};
		vi.stubGlobal('document', doc);

		const handle = motionInView(node);
		expect(observe).toHaveBeenCalledWith(node);

		observerCallback([{ isIntersecting: true, boundingClientRect: { top: 0 } }]);
		expect(classes.has('motion-active')).toBe(true);

		doc.hidden = true;
		visibilityHandler?.();
		expect(classes.has('motion-active')).toBe(false);

		doc.hidden = false;
		observerCallback([{ isIntersecting: false, boundingClientRect: { top: 0 } }]);
		expect(classes.has('motion-active')).toBe(false);

		handle.destroy();
		expect(disconnect).toHaveBeenCalledTimes(1);
		expect(doc.removeEventListener).toHaveBeenCalledWith('visibilitychange', visibilityHandler);
	});
});
