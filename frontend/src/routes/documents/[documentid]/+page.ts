import { api } from '$api/client';
import type { DocumentRead, MembershipRead } from '$api/types';
import { goto } from '$app/navigation';
import { notification } from '$lib/stores/notificationStore';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, parent, fetch }) => {
	const { sessionUser } = await parent();
	// Fetch document by param
	const documentResult = await api.get<DocumentRead>(`/documents/${params.documentid}`, {
		fetch
	});
	if (!documentResult.success) {
		notification(documentResult.error);
		throw goto('/dashboard');
	}
	if (!documentResult.data) {
		notification('error', 'Document not found.'); // TODO i18n
		throw goto('/dashboard');
	}

	// Fetch user group membership
	const membershipResult = await api.get<MembershipRead>(
		`/groups/${documentResult.data.group_id}/memberships/${sessionUser.id}`,
		{ fetch }
	);
	if (!membershipResult.success) {
		notification(membershipResult.error);
		throw goto('/dashboard');
	}
	const membership = membershipResult.data;
	if (!membership) {
		notification('error', 'You are not a member of the group that owns this document.'); // TODO i18n
		throw goto('/dashboard');
	}

	// TODO establish a websocket connection to the document for real-time editing,
	// TODO return an interface where the page can listen to and send updates via websocket

	return {
		document: documentResult.data,
		membership: membership,
		group: membership.group
	};
};
