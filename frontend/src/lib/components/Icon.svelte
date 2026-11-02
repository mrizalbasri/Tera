<script lang="ts">
	export type IconName = 'grid' | 'receipt' | 'review' | 'chart' | 'shield' | 'bell' | 'plus' | 'search' | 'clock' | 'check' | 'alert' | 'eye' | 'edit' | 'home' | 'menu' | 'close' | 'upload' | 'refresh' | 'user' | 'chevron-down';
	let { name, size = 20 }: { name: IconName; size?: number } = $props();
	const paths: Record<IconName, string> = {
		'chevron-down': 'M6 9l6 6 6-6',
		grid: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
		receipt: 'M5 3l2 1 2-1 3 1 3-1 2 1 2-1v18l-2-1-2 1-3-1-3 1-2-1-2 1z M9 8h6 M9 12h6 M9 16h3',
		review: 'M9 5H5v16h14V5h-4 M9 3h6v4H9z M8 14l3 3 5-6',
		chart: 'M4 3v18h17 M8 16v-5 M13 16V7 M18 16v-8',
		shield: 'M12 3l8 3v6c0 5-8 9-8 9s-8-4-8-9V6z M8 12l3 3 5-6',
		bell: 'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9 M10 21h4',
		plus: 'M12 5v14 M5 12h14',
		search: 'M21 21l-5-5 M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
		clock: 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0 M12 6v6l4 2',
		check: 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0 M7 12l3 3 7-7',
		alert: 'M12 3L2 21h20z M12 9v4 M12 17h.01',
		eye: 'M2 12s3-7 10-7 10 7 10 7-3 7-10 7S2 12 2 12 M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0',
		edit: 'M12 5H4v15h15v-8 M15 4l5 5 M10 14l1-5 7-7 4 4-7 7z',
		home: 'M3 10l9-7 9 7 M5 9v12h5v-7h4v7h5V9',
		menu: 'M4 6h16 M4 12h16 M4 18h16',
		close: 'M6 6l12 12 M6 18L18 6',
		upload: 'M12 16V3 M7 8l5-5 5 5 M4 16v5h16v-5',
		refresh: 'M20 7v5h-5 M4 17v-5h5 M6 6a8 8 0 0 1 14 6 M4 12a8 8 0 0 0 14 6',
		user: 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M4 21v-2a8 8 0 0 1 16 0v2'
	};
</script>

<svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d={paths[name]} /></svg>
