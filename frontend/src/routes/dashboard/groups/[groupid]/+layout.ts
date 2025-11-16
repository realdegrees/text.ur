import { api } from '$api/client';
import type { MembershipRead } from '$api/types';
import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ fetch, params, parent }) => {
	const data = await parent();
	const membership = data.memberships.data.find(({ group }) => group.id === params.groupid);
	if (!membership) {
		const result = await api.get<MembershipRead>(`/groups/${params.groupid}/memberships/${data.sessionUser.id}`, { fetch });
		if (!result.success) {
			throw new Error(`Failed to load membership for group: ${result.error.detail}`);
		}
		return { membership: result.data, ...data };
	}
	return { membership, ...data };
};
