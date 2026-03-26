<script lang="ts">
	let { data } = $props();
</script>

<svelte:head>
	<title>Amber - {data.date}</title>
</svelte:head>

<div class="entry-placeholder">
	<a href="/">&larr; Back to calendar</a>
	<h1>{data.date}</h1>
	<p class="placeholder-msg">Coming in Weekend 5</p>
</div>

<style>
	.entry-placeholder {
		max-width: 480px;
	}

	h1 {
		font-size: 1.5rem;
		font-weight: 500;
		margin: 1rem 0 0.5rem;
		font-variant-numeric: tabular-nums;
	}

	.placeholder-msg {
		color: var(--text-muted);
		font-style: italic;
	}
</style>
