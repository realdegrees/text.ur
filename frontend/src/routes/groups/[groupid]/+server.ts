import { type RequestHandler } from '@sveltejs/kit';

export const GET: RequestHandler = async ({ fetch, params }) => {
	const response = await fetch(`/api/groups/${params.groupid}`);

	// Clone the response to make headers mutable for SvelteKit's cookie handling
	return new Response(response.body, {
		status: response.status,
		statusText: response.statusText,
		headers: response.headers
	});
};
