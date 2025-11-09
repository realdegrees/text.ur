import type { Paginated } from '$api/pagination';
import type { DocumentRead } from '$api/types';
import type { LayoutLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: LayoutLoad = async ({ params, fetch, parent, url }) => {
	const data = await parent();

	// If not selectedGroup is not provided by parent, fetch it directly from the API
	if (!data.selectedGroup) {
		const res = await fetch(`/groups/${params.groupid}`);
		if (!res.ok) throw error(res.status, 'Group not found');
		data.selectedGroup = await res.json();
	}

	// Fetch documents for this group
	const documentsRes = await fetch(`/groups/${params.groupid}/documents?${url.searchParams}`);
	if (!documentsRes.ok) throw error(documentsRes.status, 'Failed to load documents');
	const documents: Paginated<DocumentRead> = await documentsRes.json();

	return { documents, ...data };
};
