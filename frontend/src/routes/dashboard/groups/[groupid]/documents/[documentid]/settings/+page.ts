import { api } from '$api/client';
import type { DocumentRead } from '$api/types';
import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';
import type { BreadcrumbItem } from '$types/breadcrumb';

export const load: PageLoad = async ({ params, parent, fetch }) => {
	const { membership } = await parent();

	// Fetch document details
	const documentResult = await api.get<DocumentRead>(`/documents/${params.documentid}`, { fetch });
	if (!documentResult.success) {
		throw error(404, 'Document not found');
	}

	return {
		document: documentResult.data,
		membership,
		breadcrumbs: [
			{ label: 'Dashboard', href: '/dashboard' },
			{
				label: membership.group.name,
				href: `/dashboard/groups/${membership.group.id}`
			},
			{
				label: 'Documents',
				href: `/dashboard/groups/${membership.group.id}/documents`
			},
			{
				label: documentResult.data.name,
				href: `/documents/${documentResult.data.id}`
			},
			{ label: 'Settings' }
		] satisfies BreadcrumbItem[]
	};
};
