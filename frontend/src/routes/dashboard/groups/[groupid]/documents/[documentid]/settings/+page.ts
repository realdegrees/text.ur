import { api } from '$api/client';
import type { DocumentRead } from '$api/types';
import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, parent, fetch }) => {
	const { membership } = await parent();

	// Fetch document details
	const documentResult = await api.get<DocumentRead>(`/documents/${params.documentid}`, { fetch });
	if (!documentResult.success) {
		throw error(404, 'Document not found');
	}

	return {
		document: documentResult.data,
		membership
	};
};
