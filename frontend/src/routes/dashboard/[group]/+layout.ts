import type { LayoutLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: LayoutLoad = async ({ params, fetch, parent, url }) => {
	const data = await parent();

	// Try to find group in the parent paginated list
	let selectedGroup = data.groups.data.find((g) => g.id === params.group);

	// If not found, fetch directly from the API
	if (!selectedGroup) {
		const res = await fetch(`/groups/${params.group}`);
		if (!res.ok) throw error(res.status, 'Group not found');
		selectedGroup = await res.json();
	}

	// Fetch documents for this group
	const documentsRes = await fetch(`/dashboard/${params.group}/documents?${url.searchParams}`);
	if (!documentsRes.ok) throw error(documentsRes.status, 'Failed to load documents');
	const documents = await documentsRes.json();

	return { group: selectedGroup, documents, ...data };
};
