import { type RequestHandler } from '@sveltejs/kit';
import { paginatedEndpointQuery } from '$lib/util/server';
import type { Filter } from '$api/types';
import { filterToSearchParams } from '$lib/util/filters';

export const GET: RequestHandler = async ({ url, params, fetch }) => {
	const groupId: string = params.groupid!;
	const searchParams = new URLSearchParams(url.searchParams);
	const filter = filterToSearchParams({
		field: 'group_id',
		operator: '==',
		value: groupId
	} satisfies Filter);

	// Merge filter and searchParams
	for (const [key, value] of filter.entries()) {
		searchParams.append(key, value);
	}

	return paginatedEndpointQuery(searchParams, '/api/documents', fetch);
};
