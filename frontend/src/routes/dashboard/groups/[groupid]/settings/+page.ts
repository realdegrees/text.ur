import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { membership, sessionUser } = await parent();

	// Check if user is admin or owner
	const isAdmin = membership.permissions.includes('administrator') || membership.is_owner;

	if (!isAdmin) {
		throw redirect(302, `/dashboard/groups/${membership.group.id}/documents`);
	}

	return { membership, sessionUser };
};
