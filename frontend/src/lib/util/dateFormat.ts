/**
 * Format a date string to include time: "13. Sept 2025, 14:30"
 */
export function formatDateTime(dateString?: string | null): string {
	if (!dateString) return 'Never expires';

	const date = new Date(dateString);
	const day = date.getDate();
	const month = date.toLocaleString('en', { month: 'short' });
	const year = date.getFullYear();
	const hours = date.getHours().toString().padStart(2, '0');
	const minutes = date.getMinutes().toString().padStart(2, '0');

	return `${day}. ${month} ${year}, ${hours}:${minutes}`;
}

/**
 * Get the current date/time in ISO format for datetime-local inputs (YYYY-MM-DDTHH:MM)
 */
export function getCurrentDateTimeLocal(): string {
	const now = new Date();
	const year = now.getFullYear();
	const month = (now.getMonth() + 1).toString().padStart(2, '0');
	const day = now.getDate().toString().padStart(2, '0');
	const hours = now.getHours().toString().padStart(2, '0');
	const minutes = now.getMinutes().toString().padStart(2, '0');

	return `${year}-${month}-${day}T${hours}:${minutes}`;
}
