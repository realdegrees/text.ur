import { error } from '@sveltejs/kit';

export async function paginatedEndpointQuery(
	searchParams: URLSearchParams,
	path: string,
	fetch: {
		(input: RequestInfo | URL, init?: RequestInit): Promise<Response>;
		(input: string | URL | globalThis.Request, init?: RequestInit): Promise<Response>;
	}
): Promise<Response> {
	if (!searchParams.has('offset')) {
		searchParams.set('offset', '0');
	}
	if (!searchParams.has('limit')) {
		searchParams.set('limit', '25');
	}

	const response = await fetch(`${path}?${searchParams}`);
	if (!response.ok) {
		console.error(response);
		error(response.status);
	}
	const data = await response.json();
	return new Response(JSON.stringify(data), {
		status: response.status,
		headers: { 'Content-Type': 'application/json' }
	});
}
