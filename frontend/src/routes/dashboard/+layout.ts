import { api } from '$api/client';
import type { Paginated } from '$api/pagination';
import type { MembershipRead } from '$api/types';
import { notification } from '$lib/stores/notificationStore';
import type { LayoutLoad } from './$types';

// TODO this can probably be a serverlayout in order to prerender the initial list of groups so it gets loaded instantly
export const load: LayoutLoad = async ({ fetch, parent, params }) => {
	// Load all groups the user is a member of (endpoint only returns groups for the session user)
	const { sessionUser } = await parent();

	const result = await api.get<Paginated<MembershipRead>, 'user'>('/memberships', {
		fetch,
		filters: [
			{ field: 'accepted', operator: '==', value: 'true' },
			{ field: 'user_id', operator: '==', value: sessionUser.id }
		]
	});

	let memberships: Paginated<MembershipRead, 'user'>;
	if (result.success) {
		memberships = result.data;
	} else {		
		notification(result.error);
		return {
			...(await parent()),
			memberships: { data: [], total: 0, offset: 0, limit: 0 }
		};
	}

	if (params.groupid && !memberships.data.find(({ group }) => group.id === params.groupid)) {
		// If the selected group is not in the list, fetch it directly from the API and add it to the list
		const result = await api.get<MembershipRead>(
			`/groups/${params.groupid}/memberships/${sessionUser.id}`,
			{ fetch }
		);
		if (!result.success) {
			throw new Error(`Failed to load membership for selected group: ${result.error.detail}`);
		}
		memberships.data.unshift(result.data);
	}	

	return {
		...(await parent()),
		memberships: memberships
	};
};
