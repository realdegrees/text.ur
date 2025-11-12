import { api } from '$api/client';
import type { Paginated } from '$api/pagination';
import type { GroupMembershipRead } from '$api/types';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params, url }) => {
	const memberships = await api.fetch<Paginated<GroupMembershipRead>>(
		`/groups/${params.groupid}/memberships?${url.searchParams}`,
		{ fetch }
	);
	return { memberships };
};
