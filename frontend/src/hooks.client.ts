import type { HandleClientError } from '@sveltejs/kit';

/**
 * Catch unhandled client-side errors (null references, failed parses, etc.)
 * and ensure they are logged and surfaced with a safe message via +error.svelte.
 */
export const handleError: HandleClientError = ({ error }) => {
	console.error('Unhandled client error:', error);

	return {
		message: 'An unexpected error occurred'
	};
};
