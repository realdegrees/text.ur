import { api } from '$api/client';
import type { Paginated } from '$api/pagination';
import type { MembershipRead } from '$api/types';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params, url }) => {
	const memberships = await api.fetch<Paginated<MembershipRead>>(
		`/memberships?${url.searchParams}`,
		{
			fetch,
			filters: [
				{
					field: 'group_id',
					operator: '==',
					value: params.groupid
				}
			]
		}
	);
	return { memberships };
};
