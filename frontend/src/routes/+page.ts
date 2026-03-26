import type { EntrySummary } from '$lib/types';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const response = await fetch('/api/entries');

	if (!response.ok) {
		return { entries: [] as EntrySummary[] };
	}

	const entries: EntrySummary[] = await response.json();
	return { entries };
};
