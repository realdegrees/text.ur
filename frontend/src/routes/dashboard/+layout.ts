import { api } from '$api/client';
import type { Paginated } from '$api/pagination';
import type { MembershipRead } from '$api/types';
import type { LayoutLoad } from './$types';

// TODO this can probably be a serverlayout in order to prerender the initial list of groups so it gets loaded instantly
export const load: LayoutLoad = async ({ fetch, parent, params }) => {
	// Load all groups the user is a member of (endpoint only returns groups for the session user)
	const { sessionUser } = await parent();

	const memberships = await api.fetch<Paginated<MembershipRead>>('/memberships', {
		fetch,
		filters: [
			{ field: 'accepted', operator: '==', value: 'true' },
			{ field: 'user_id', operator: '==', value: sessionUser.id }
		]
	});

	if (params.groupid && !memberships.data.find(({ group }) => group.id === params.groupid)) {
		// If the selected group is not in the list, fetch it directly from the API and add it to the list
		const membershipForSelectedGroup = await api.fetch<MembershipRead>(
			`/groups/${params.groupid}/memberships/${sessionUser.id}`,
			{ fetch }
		);
		memberships.data.unshift(membershipForSelectedGroup);
	}

	return {
		...(await parent()),
		memberships: memberships
	};
};
