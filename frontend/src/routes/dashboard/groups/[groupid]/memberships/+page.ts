import { api } from '$api/client';
import type { Paginated } from '$api/pagination';
import type { MembershipRead } from '$api/types';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params, url }) => {
	const result = await api.get<Paginated<MembershipRead>, 'group'>(
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

	if (!result.success) {
		throw new Error(`Failed to load memberships: ${result.error.detail}`);
	}

	return { memberships: result.data };
};
