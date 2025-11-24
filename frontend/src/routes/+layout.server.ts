import { redirect } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';
import { sessionStore } from '$lib/runes/session.svelte';
import type { DocumentRead, MembershipRead } from '$api/types';
import { api } from '$api/client';

const noAuthRoutes = ['/login', '/'];
export const load: LayoutServerLoad = async ({ locals, route, params, fetch }) => {
	// Redirect to login if no session user and not on a no-auth route
	if (!locals.sessionUser && !noAuthRoutes.includes(route.id || '')) {
		throw redirect(303, '/login');
	}
	sessionStore.currentUser = locals.sessionUser;

	let groupId = params.groupid;
	let routeMembership: MembershipRead | null = null;

	if (!groupId && params.documentid) {
		// Fetch document to get group ID
		const documentResult = await api.get<DocumentRead>(`/documents/${params.documentid}`, {
			fetch
		});
		if (documentResult.success && documentResult.data) {
			groupId = documentResult.data.group_id;
		}
	}

	if (groupId) {
		// Fetch membership for the group
		const membershipResult = await api.get<MembershipRead>(
			`/groups/${groupId}/memberships/${locals.sessionUser?.id}`,
			{ fetch }
		);
		if (membershipResult.success && membershipResult.data) {
			sessionStore.routeMembership = membershipResult.data;
			routeMembership = membershipResult.data;
		}
	}
	return { routeMembership, ...locals };
};
