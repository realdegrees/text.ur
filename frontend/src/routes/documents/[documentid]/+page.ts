import { api } from '$api/client';
import type { CommentRead, DocumentRead, MembershipRead } from '$api/types';
import { notification } from '$lib/stores/notificationStore';
import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import type { Paginated } from '$api/pagination';

export const load: PageLoad = async ({ params, parent, fetch }) => {
	const { sessionUser } = await parent();
	// Fetch document by param
	const documentResult = await api.get<DocumentRead>(`/documents/${params.documentid}`, {
		fetch
	});
	if (!documentResult.success) {
		notification(documentResult.error);
		throw redirect(303, '/dashboard');
	}
	if (!documentResult.data) {
		notification('error', 'Document not found.'); // TODO i18n
		throw redirect(303, '/dashboard');
	}

	// Fetch user group membership
	const membershipResult = await api.get<MembershipRead>(
		`/groups/${documentResult.data.group_id}/memberships/${sessionUser.id}`,
		{ fetch }
	);
	if (!membershipResult.success) {
		notification(membershipResult.error);
		throw redirect(303, '/dashboard');
	}
	const membership = membershipResult.data;
	if (!membership) {
		notification('error', 'You are not a member of the group that owns this document.'); // TODO i18n
		throw redirect(303, '/dashboard');
	}

	const rootComments: CommentRead[] = [];
	let offset = 0;
	const limit = 50;
	while (true) {
		const result = await api.get<Paginated<CommentRead, 'document'>>(
			`/comments?offset=${offset}&limit=${limit}`,
			{
				filters: [
					{ field: 'parent_id', operator: 'exists', value: 'false' },
					{ field: 'annotation', operator: 'exists', value: 'true' },
					{ field: 'document_id', operator: '==', value: documentResult.data.id }
				],
				fetch
			}
		);

		if (!result.success) {
			notification(result.error);
			throw redirect(303, '/dashboard');
		}

		rootComments.push(...result.data.data);

		if (result.data.total <= result.data.offset + result.data.limit) {
			break;
		}
		offset += limit;
	}

	const documentFileResult = await api.download(`/documents/${params.documentid}/file`, { fetch });
	if (!documentFileResult.success) {
		notification(documentFileResult.error);
		throw redirect(303, '/dashboard');
	}

	// TODO establish a websocket connection to the document for real-time editing,
	// TODO return an interface where the page can listen to and send updates via websocket

	return {
		document: documentResult.data,
		group: membership.group,
		rootComments: rootComments,
		documentFile: documentFileResult.data
	};
};
