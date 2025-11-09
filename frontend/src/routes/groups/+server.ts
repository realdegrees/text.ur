import { type RequestHandler } from '@sveltejs/kit';
import { paginatedEndpointQuery } from '$lib/util/server';

export const GET: RequestHandler = async ({ url, fetch }) => {
	return paginatedEndpointQuery(url.searchParams, '/api/groups', fetch);
};
