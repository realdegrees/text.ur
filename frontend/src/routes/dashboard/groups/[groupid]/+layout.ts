import { api } from '$api/client';
import type { Paginated } from '$api/pagination';
import type { DocumentRead, Filter, GroupRead } from '$api/types';
import { filterToSearchParams } from '$lib/util/filters';
import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ fetch, params, parent, url }) => {
	const data = await parent();

	// If not selectedGroup is not provided by parent, fetch it directly from the API
	if (!data.selectedGroup) {
		const group = await api.fetch<GroupRead>(`/groups/${params.groupid}`, { fetch });
		data.selectedGroup = group;
	}

	const searchParams = new URLSearchParams({
		...Object.fromEntries(url.searchParams),
		...filterToSearchParams({
			field: 'group_id',
			operator: '==',
			value: params.groupid
		} satisfies Filter)
	});

	// Fetch documents for this group
	const documents = await api.fetch<Paginated<DocumentRead>>(
		`/documents?` + searchParams.toString(),
		{ fetch }
	);
	return { documents, ...data };
};
