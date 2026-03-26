/** An entry summary as returned by GET /api/entries. */
export interface EntrySummary {
	date: string;
	transcription_status: 'pending' | 'processing' | 'done' | 'failed';
	duration_seconds: number | null;
	file_size_bytes: number | null;
}
