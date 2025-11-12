import { api } from '$api/client';
import type { Paginated } from '$api/pagination';
import type { Filter, GroupRead } from '$api/types';
import { filterToSearchParams } from '$lib/util/filters';
import type { LayoutLoad } from './$types';

// TODO this can probably be a serverlayout in order to prerender the initial list of groups so it gets loaded instantly
export const load: LayoutLoad = async ({ fetch, parent, params, url }) => {
	// Load all groups the user is a member of (endpoint only returns groups for the session user)
	const searchParams = new URLSearchParams({
		...Object.fromEntries(url.searchParams),
		...Object.fromEntries(
			filterToSearchParams({ field: 'accepted', operator: '==', value: 'true' } as Filter)
		)
	});

	const group_data = await api.fetch<Paginated<GroupRead>>('/groups?' + searchParams, { fetch });
	let selectedGroup: GroupRead | undefined = group_data.data.find((g) => g.id === params.groupid);

	if (!selectedGroup && params.groupid) {
		selectedGroup = await api.fetch(`/groups/${params.groupid}`, { fetch });
	}

	return {
		...(await parent()),
		groups: group_data,
		selectedGroup
	};
};
