import type { AppError } from '$api/types';
import { get } from 'svelte/store';
import LL from '$i18n/i18n-svelte';

/**
 * Format a duration in seconds to a localized human-readable string.
 *
 * Examples: 86400 → "24 hours", 3600 → "1 hour", 120 → "2 minutes".
 */
function formatDuration(seconds: number): string {
	const ll = get(LL).duration;

	if (seconds >= 86400) {
		const days = Math.ceil(seconds / 86400);
		return ll.nDays({ count: days });
	}
	if (seconds >= 3600) {
		const hours = Math.ceil(seconds / 3600);
		return ll.nHours({ count: hours });
	}
	if (seconds >= 60) {
		const minutes = Math.ceil(seconds / 60);
		return ll.nMinutes({ count: minutes });
	}
	return ll.nSeconds({ count: seconds });
}

/**
 * Resolve an AppError to a localized user-facing message string.
 *
 * Resolution chain:
 * 1. Translated string for the error_code (via LL.errors[code]),
 *    enriched with any context from response headers (e.g. Retry-After)
 * 2. Raw detail string from the backend response
 * 3. Generic "unknown error" fallback
 */
export function resolveErrorMessage(error: AppError): string {
	const ll = get(LL);

	// Build context for translation interpolation
	const context: Record<string, unknown> = {};

	// Format Retry-After header value (attached by API client) into a
	// localized duration string for the {retryAfter} translation parameter
	if ('retryAfter' in error && typeof (error as any).retryAfter === 'number') {
		context.retryAfter = formatDuration((error as any).retryAfter);
	} else if (error.error_code === 'rate_limited') {
		// Fallback when header is missing (e.g. stripped by proxy)
		context.retryAfter = ll.duration.aFewMinutes();
	}

	const errorTranslations = ll.errors as unknown as Record<
		string,
		((args?: Record<string, unknown>) => string) | undefined
	>;

	return (
		errorTranslations[error.error_code]?.(context) || error.detail || ll.errors.unknown_error()
	);
}
