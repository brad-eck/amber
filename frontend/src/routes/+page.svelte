<script lang="ts">
	import type { EntrySummary } from '$lib/types';
	import {
		daysInMonth,
		firstDayOffset,
		formatDate,
		MONTH_NAMES,
		WEEKDAYS
	} from '$lib/calendar';

	let { data } = $props();

	// Build a lookup map: date string -> entry summary
	const entryMap = $derived(
		new Map(data.entries.map((e: EntrySummary) => [e.date, e]))
	);

	// Current calendar view state
	const now = new Date();
	let viewYear = $state(now.getFullYear());
	let viewMonth = $state(now.getMonth() + 1); // 1-indexed

	// Derived calendar data
	const totalDays = $derived(daysInMonth(viewYear, viewMonth));
	const offset = $derived(firstDayOffset(viewYear, viewMonth));
	const monthLabel = $derived(`${MONTH_NAMES[viewMonth - 1]} ${viewYear}`);

	// Today's date string for highlighting
	const todayStr = formatDate(now.getFullYear(), now.getMonth() + 1, now.getDate());

	function prevMonth() {
		if (viewMonth === 1) {
			viewMonth = 12;
			viewYear--;
		} else {
			viewMonth--;
		}
	}

	function nextMonth() {
		if (viewMonth === 12) {
			viewMonth = 1;
			viewYear++;
		} else {
			viewMonth++;
		}
	}

	/** Map transcription status to a short indicator character. */
	function statusIndicator(status: EntrySummary['transcription_status']): string {
		switch (status) {
			case 'done': return '●';
			case 'processing': return '◐';
			case 'pending': return '○';
			case 'failed': return '✕';
		}
	}
</script>

<svelte:head>
	<title>Amber</title>
</svelte:head>

<div class="calendar-container">
	<div class="calendar-nav">
		<button onclick={prevMonth} aria-label="Previous month">&larr;</button>
		<h2>{monthLabel}</h2>
		<button onclick={nextMonth} aria-label="Next month">&rarr;</button>
	</div>

	<div class="calendar-grid">
		{#each WEEKDAYS as day}
			<div class="weekday-header">{day}</div>
		{/each}

		{#each Array(offset) as _}
			<div class="day-cell empty"></div>
		{/each}

		{#each Array(totalDays) as _, i}
			{@const dayNum = i + 1}
			{@const dateStr = formatDate(viewYear, viewMonth, dayNum)}
			{@const entry = entryMap.get(dateStr)}
			{@const isToday = dateStr === todayStr}

			{#if entry}
				<a
					href="/entries/{dateStr}"
					class="day-cell has-entry status-{entry.transcription_status}"
					class:today={isToday}
				>
					<span class="day-number">{dayNum}</span>
					<span class="status-dot" title="{entry.transcription_status}">{statusIndicator(entry.transcription_status)}</span>
				</a>
			{:else}
				<div class="day-cell" class:today={isToday}>
					<span class="day-number">{dayNum}</span>
				</div>
			{/if}
		{/each}
	</div>

	<div class="legend">
		<span class="legend-item"><span class="status-dot">●</span> Transcribed</span>
		<span class="legend-item"><span class="status-dot">◐</span> Processing</span>
		<span class="legend-item"><span class="status-dot">○</span> Pending</span>
		<span class="legend-item"><span class="status-dot">✕</span> Failed</span>
	</div>
</div>

<style>
	.calendar-container {
		max-width: 560px;
		margin: 0 auto;
	}

	.calendar-nav {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 1rem;
	}

	.calendar-nav h2 {
		margin: 0;
		font-size: 1.25rem;
		font-weight: 500;
	}

	.calendar-nav button {
		background: var(--surface-2);
		border: 1px solid var(--border);
		color: var(--text);
		padding: 0.4rem 0.75rem;
		border-radius: 4px;
		cursor: pointer;
		font-size: 1rem;
	}

	.calendar-nav button:hover {
		background: var(--surface-3);
	}

	.calendar-grid {
		display: grid;
		grid-template-columns: repeat(7, 1fr);
		gap: 2px;
	}

	.weekday-header {
		text-align: center;
		font-size: 0.75rem;
		font-weight: 600;
		color: var(--text-muted);
		padding: 0.5rem 0;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.day-cell {
		aspect-ratio: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		border-radius: 4px;
		font-size: 0.875rem;
		background: var(--surface-1);
		position: relative;
		text-decoration: none;
		color: var(--text);
	}

	.day-cell.empty {
		background: transparent;
	}

	.day-cell.today {
		outline: 2px solid var(--accent);
		outline-offset: -2px;
	}

	.day-cell.has-entry {
		cursor: pointer;
	}

	.day-cell.has-entry:hover {
		background: var(--surface-3);
	}

	.day-cell.status-done {
		background: var(--surface-done);
	}

	.day-cell.status-processing {
		background: var(--surface-processing);
	}

	.day-cell.status-pending {
		background: var(--surface-pending);
	}

	.day-cell.status-failed {
		background: var(--surface-failed);
	}

	.day-number {
		font-variant-numeric: tabular-nums;
	}

	.status-dot {
		font-size: 0.625rem;
		margin-top: 2px;
		line-height: 1;
	}

	.legend {
		display: flex;
		gap: 1rem;
		justify-content: center;
		margin-top: 1.5rem;
		font-size: 0.75rem;
		color: var(--text-muted);
	}

	.legend-item {
		display: flex;
		align-items: center;
		gap: 0.3rem;
	}
</style>
