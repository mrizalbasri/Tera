<script lang="ts">
	import { motionInView } from '$lib/actions/motionInView';
	let { dark = false }: { dark?: boolean } = $props();
	const id = $props.id();
</script>

<svg use:motionInView class="brand-ribbon" class:dark viewBox="0 0 1200 760" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
	<defs>
		<linearGradient id={`${id}-ribbon`} x1=".15" x2=".95" y1="1" y2="0">
			<stop offset="0" stop-color="#008779" /><stop offset=".48" stop-color="#25bd98" /><stop offset="1" stop-color="#c4efaa" />
		</linearGradient>
		<linearGradient id={`${id}-veil`} x1="0" x2="1"><stop offset=".29" stop-color="white" stop-opacity="0" /><stop offset=".68" stop-color="white" stop-opacity=".85" /><stop offset="1" stop-color="white" /></linearGradient>
		<linearGradient id={`${id}-fade`} x1="0" y1="1" x2=".85" y2="0"><stop stop-color="white" stop-opacity=".9" /><stop offset=".5" stop-color="white" /><stop offset="1" stop-color="white" stop-opacity=".15" /></linearGradient>
		<pattern id={`${id}-dots`} width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(-16)"><circle cx="2" cy="2" r="1.65" fill="white" /><circle cx="6" cy="6" r="1.15" fill="white" /></pattern>
		<filter id={`${id}-grain`} x="0" y="0" width="100%" height="100%">
			<feTurbulence type="fractalNoise" baseFrequency=".48" numOctaves="3" stitchTiles="stitch" seed="12" />
			<feColorMatrix type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  7 0 0 0 -3.1" result="ink" />
			<feFlood flood-color={dark ? '#002e29' : '#087d66'} /><feComposite in2="ink" operator="in" />
		</filter>
		<mask id={`${id}-sweep`}><path d="M280 920C520 800 455 560 780 470S1110 230 1330 -150" fill="none" stroke={`url(#${id}-fade)`} stroke-width="330" /></mask>
		<mask id={`${id}-halftone`}><rect width="1200" height="760" fill={`url(#${id}-dots)`} /></mask>
		<mask id={`${id}-right`}><rect width="1200" height="760" fill={`url(#${id}-veil)`} /></mask>
	</defs>
	<g mask={dark ? undefined : `url(#${id}-right)`}>
		<ellipse cx="1180" cy="20" rx="390" ry="370" fill={dark ? '#00544d' : '#cdeee1'} />
		<path d="M410 930C610 740 555 550 850 450S1150 210 1330 -180" fill="none" stroke={`url(#${id}-ribbon)`} stroke-width="350" opacity={dark ? '.95' : '.68'} />
		<path d="M565 900C745 710 690 540 960 415S1230 120 1330 -150" fill="none" stroke="#00695e" stroke-width="160" opacity={dark ? '.8' : '.5'} />
		<path d="M300 900C540 770 470 550 790 450S1120 220 1270 -120" fill="none" stroke="#b6f0d2" stroke-width="155" opacity={dark ? '.36' : '.65'} />
		<g mask={`url(#${id}-sweep)`}>
			<rect width="1200" height="760" fill={dark ? '#9ee8c7' : '#087d66'} mask={`url(#${id}-halftone)`} opacity={dark ? '.65' : '.5'} />
			<rect width="1200" height="760" filter={`url(#${id}-grain)`} opacity={dark ? '.7' : '.4'} />
		</g>
		<path d="M650 870C810 610 1070 650 1310 340" fill="none" stroke={dark ? '#002f2c' : '#daf4e7'} stroke-width="150" opacity={dark ? '.55' : '.5'} />
	</g>
</svg>

<style>
	/* The reference's curved halftone ribbon repeats the receipt fold at architectural scale. */
	.brand-ribbon { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; z-index: -1; }
	@keyframes ribbon-drift { from { transform: scale(1.08) translate(-1%, 1.5%) rotate(-1deg); } to { transform: scale(1.08) translate(1%, -1.5%) rotate(1deg); } }
	.brand-ribbon { animation: ribbon-drift 14s ease-in-out infinite alternate; animation-play-state: paused; transform-origin: 75% 50%; }
	.brand-ribbon:global(.motion-active) { animation-play-state: running; }
</style>
