import { redirect } from '@sveltejs/kit';
import type { LayoutServerLoad } from './$types';
import type { DocumentRead, MembershipRead } from '$api/types';
import { api } from '$api/client';

const noAuthRoutes = [
	'/login',
	'/',
	'/sharelink/[token]',
	'/password-reset/request',
	'/password-reset/[token]'
];
export const load: LayoutServerLoad = async ({ locals, route, params, fetch, url }) => {
	// Redirect to login if no session user and not on a no-auth route
	if (!locals.sessionUser && !noAuthRoutes.includes(route.id || '')) {
		throw redirect(303, '/login?redirect=' + url.pathname + url.searchParams.toString());
	}

	let groupId = params.groupid;
	const documentId = params.documentid;
	let routeMembership: MembershipRead | null = null;

	if (!groupId && documentId) {
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
			routeMembership = membershipResult.data;
		}
	}
	return { routeMembership, ...locals };
};
