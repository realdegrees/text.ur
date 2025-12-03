import { api } from '$api/client';
import type { Paginated } from '$api/pagination';
import type { MembershipRead } from '$api/types';
import { notification } from '$lib/stores/notificationStore';
import type { BreadcrumbItem } from '$types/breadcrumb';
import type { LayoutLoad } from './$types';

// TODO this can probably be a serverlayout in order to prerender the initial list of groups so it gets loaded instantly
export const load: LayoutLoad = async ({ fetch, parent }) => {
	// Load all groups the user is a member of (endpoint only returns groups for the session user)
	const { sessionUser, routeMembership } = await parent();

	const membershipsResult = await api.get<Paginated<MembershipRead>, 'user'>('/memberships', {
		fetch,
		filters: [
			{ field: 'accepted', operator: '==', value: 'true' },
			{ field: 'user_id', operator: '==', value: sessionUser.id.toString() }
		]
	});
	const invitesResult = await api.get<Paginated<MembershipRead>, 'user'>('/memberships', {
		fetch,
		filters: [
			{ field: 'accepted', operator: '==', value: 'false' },
			{ field: 'user_id', operator: '==', value: sessionUser.id.toString() }
		]
	});

	let memberships: Paginated<MembershipRead, 'user'>;
	let invites: Paginated<MembershipRead, 'user'>;

	if (membershipsResult.success) {
		memberships = membershipsResult.data;
	} else {
		notification(membershipsResult.error);
		return {
			...(await parent()),
			memberships: { data: [], total: 0, offset: 0, limit: 0 }
		};
	}

	if (invitesResult.success) {
		invites = invitesResult.data;
	} else {
		notification(invitesResult.error);
		return {
			...(await parent()),
			invites: { data: [], total: 0, offset: 0, limit: 0 }
		};
	}

	if (
		routeMembership &&
		!memberships.data.find(({ group }) => group.id === routeMembership.group.id)
	)
		memberships.data.unshift(routeMembership);

	return {
		...(await parent()),
		memberships: memberships,
		invites: invites,
		breadcrumbs: [{ label: 'Dashboard' }] satisfies BreadcrumbItem[]
	};
};
