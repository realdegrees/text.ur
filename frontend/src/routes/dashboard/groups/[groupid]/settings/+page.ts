import { validatePermissions } from '$api/validatePermissions';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { membership, sessionUser } = await parent();
	validatePermissions(
		membership,
		['administrator'],
		`/dashboard/groups/${membership.group.id}/documents`
	);
	return { membership, sessionUser };
};
