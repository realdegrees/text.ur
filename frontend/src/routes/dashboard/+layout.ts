import { api } from '$api/client';
import type { Paginated } from '$api/pagination';
import type { GroupRead } from '$api/types';
import type { LayoutLoad } from './$types';

// TODO this can probably be a serverlayout in order to prerender the initial list of groups so it gets loaded instantly
export const load: LayoutLoad = async ({ fetch, parent, params }) => {
	// Load all groups the user is a member of (endpoint only returns groups for the session user)

	const group_data = await api.fetch<Paginated<GroupRead>>('/groups', {
		fetch,
		filters: [{ field: 'accepted', operator: '==', value: 'true' }]
	});

	if (params.groupid && !group_data.data.find((g) => g.id === params.groupid)) {
		// If the selected group is not in the list, fetch it directly from the API and add it to the list
		const selectedGroup = await api.fetch<GroupRead>(`/groups/${params.groupid}`, { fetch });
		group_data.data.unshift(selectedGroup);
	}

	return {
		...(await parent()),
		groups: group_data
	};
};
