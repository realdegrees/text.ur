import { type RequestHandler } from '@sveltejs/kit';
import { paginatedEndpointQuery } from '$lib/util/server';

export const GET: RequestHandler = async ({ url, params, fetch }) => {
	const groupId: string = params.groupid!;
	const searchParams = new URLSearchParams(url.searchParams);

	return paginatedEndpointQuery(searchParams, '/api/groups/' + groupId + '/memberships', fetch);
};
