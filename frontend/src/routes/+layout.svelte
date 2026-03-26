<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<div class="app">
	<header>
		<nav>
			<a href="/" class="brand">Amber</a>
		</nav>
	</header>

	<main>
		{@render children()}
	</main>
</div>

<style>
	:global(:root) {
		--bg: #0f0f0f;
		--surface-1: #1a1a1a;
		--surface-2: #242424;
		--surface-3: #2e2e2e;
		--border: #333;
		--text: #e0e0e0;
		--text-muted: #888;
		--accent: #c8a44e;
		--surface-done: #1a2a1a;
		--surface-processing: #1a1a2a;
		--surface-pending: #222218;
		--surface-failed: #2a1a1a;
		--font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
		--font-mono: 'SF Mono', 'Fira Code', monospace;
	}

	:global(*) {
		box-sizing: border-box;
	}

	:global(body) {
		margin: 0;
		font-family: var(--font-sans);
		background: var(--bg);
		color: var(--text);
		line-height: 1.5;
		-webkit-font-smoothing: antialiased;
	}

	:global(a) {
		color: var(--accent);
		text-decoration: none;
	}

	:global(a:hover) {
		text-decoration: underline;
	}

	.app {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
	}

	header {
		border-bottom: 1px solid var(--border);
		padding: 0.75rem 1.5rem;
	}

	nav {
		max-width: 960px;
		margin: 0 auto;
	}

	.brand {
		font-size: 1.125rem;
		font-weight: 600;
		letter-spacing: 0.04em;
		text-decoration: none;
	}

	main {
		flex: 1;
		max-width: 960px;
		width: 100%;
		margin: 0 auto;
		padding: 2rem 1.5rem;
	}
</style>
