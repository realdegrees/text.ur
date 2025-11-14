import { api } from '$api/client';
import type { Paginated } from '$api/pagination';
import type { DocumentRead, GroupRead } from '$api/types';
import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ fetch, params, parent }) => {
	const data = await parent();
	const group =
		data.memberships.data.find(({ group }) => group.id === params.groupid)?.group ??
		(await api.fetch<GroupRead>(`/groups/${params.groupid}`, { fetch }));

	// Fetch documents for this group
	const documents = await api.fetch<Paginated<DocumentRead>>(`/documents`, {
		fetch,
		filters: [
			{
				field: 'group_id',
				operator: '==',
				value: params.groupid
			}
		]
	});
	return { documents, group, ...data };
};
