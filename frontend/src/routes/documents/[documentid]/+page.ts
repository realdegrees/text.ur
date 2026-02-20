import { api } from '$api/client';
import type { CommentRead, DocumentRead, ScoreConfigRead } from '$api/types';
import { notification } from '$lib/stores/notificationStore';
import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import type { Paginated } from '$api/pagination';
import type { BreadcrumbItem } from '$types/breadcrumb';

export const load: PageLoad = async ({ params, parent, fetch, depends }) => {
	depends('app:document-view');
	const { routeMembership: membership } = await parent();
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

	const [documentFileResult, scoreConfigResult] = await Promise.all([
		api.download(`/documents/${params.documentid}/file`, { fetch }),
		api.get<ScoreConfigRead>(`/groups/${documentResult.data.group_id}/score-config`, { fetch })
	]);
	if (!documentFileResult.success) {
		notification(documentFileResult.error);
		throw redirect(303, '/dashboard');
	}

	const scoreConfig = scoreConfigResult.success ? scoreConfigResult.data : null;

	return {
		document: documentResult.data,
		group: membership.group,
		rootComments: rootComments,
		documentFile: documentFileResult.data,
		scoreConfig,
		breadcrumbs: [
			{
				label: membership.group.name,
				href: `/dashboard/groups/${membership.group.id}`
			},
			{
				label: 'Documents',
				href: `/dashboard/groups/${membership.group.id}/documents`
			},
			{
				label: documentResult.data.name
			}
		] satisfies BreadcrumbItem[]
	};
};
