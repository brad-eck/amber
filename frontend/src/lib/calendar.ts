/** Calendar utility functions. */

/** Get the number of days in a given month (1-indexed). */
export function daysInMonth(year: number, month: number): number {
	return new Date(year, month, 0).getDate();
}

/**
 * Get the day of the week the first of the month falls on.
 * Returns 0 = Monday, 6 = Sunday (ISO week convention).
 */
export function firstDayOffset(year: number, month: number): number {
	const day = new Date(year, month - 1, 1).getDay();
	// JS: 0=Sun, 1=Mon ... 6=Sat -> convert to 0=Mon ... 6=Sun
	return day === 0 ? 6 : day - 1;
}

/** Format a date as YYYY-MM-DD. */
export function formatDate(year: number, month: number, day: number): string {
	const m = String(month).padStart(2, '0');
	const d = String(day).padStart(2, '0');
	return `${year}-${m}-${d}`;
}

/** Month names for display. */
export const MONTH_NAMES = [
	'January', 'February', 'March', 'April', 'May', 'June',
	'July', 'August', 'September', 'October', 'November', 'December'
];

/** Short weekday headers (Monday-first). */
export const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
