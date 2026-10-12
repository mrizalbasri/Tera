<svelte:head>
	<title>Expense Agent</title>
	<meta
		name="description"
		content="Expense reimbursement automation prototype"
	/>
</svelte:head>

<main>
	<p class="eyebrow">Expense Reimbursement Agent</p>
	<h1>Expense Agent</h1>
	<p class="intro">
		A workspace for submitting, validating, and reviewing expense claims.
	</p>
	<div class="status" aria-live="polite">
		<span class="dot"></span>
		Prototype foundation is ready
	</div>
</main>

<style>
	:global(body) {
		margin: 0;
		min-width: 320px;
		background: #f6f7f2;
		color: #172018;
		font-family:
			Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
			sans-serif;
	}

	main {
		box-sizing: border-box;
		display: grid;
		align-content: center;
		min-height: 100vh;
		max-width: 760px;
		margin: 0 auto;
		padding: 2rem;
	}

	.eyebrow {
		margin: 0 0 1rem;
		color: #55745a;
		font-size: 0.8rem;
		font-weight: 700;
		letter-spacing: 0.12em;
		text-transform: uppercase;
	}

	h1 {
		margin: 0;
		font-size: clamp(3.5rem, 12vw, 7rem);
		letter-spacing: -0.08em;
		line-height: 0.9;
	}

	.intro {
		max-width: 34rem;
		margin: 2rem 0;
		color: #5b665c;
		font-size: clamp(1.1rem, 2vw, 1.35rem);
		line-height: 1.5;
	}

	.status {
		display: inline-flex;
		align-items: center;
		gap: 0.6rem;
		width: fit-content;
		padding: 0.65rem 0.9rem;
		border: 1px solid #cbd9c9;
		border-radius: 999px;
		background: #eaf2e7;
		color: #36593b;
		font-size: 0.9rem;
		font-weight: 600;
	}

	.dot {
		width: 0.55rem;
		height: 0.55rem;
		border-radius: 50%;
		background: #4e9b5a;
	}
</style>
