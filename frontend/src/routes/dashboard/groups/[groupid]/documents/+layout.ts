import { api } from '$api/client';
import type { Paginated } from '$api/pagination';
import type { DocumentRead } from '$api/types';
import { notification } from '$lib/stores/notificationStore';
import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ fetch, params, parent }) => {
	const data = await parent();

	// Fetch documents for this group
	const results = await api.get<Paginated<DocumentRead>>(`/documents`, {
		fetch,
		filters: [
			{
				field: 'group_id',
				operator: '==',
				value: params.groupid
			}
		]
	});
	if (!results.success) {
		notification(results.error);
		return { documents: { data: [], total: 0, offset: 0, limit: 0 }, ...data };
	}
	const documents = results.data;
	return { documents, ...data };
};
