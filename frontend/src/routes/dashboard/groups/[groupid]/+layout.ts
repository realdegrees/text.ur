import { redirect } from '@sveltejs/kit';
import type { LayoutLoad } from './$types';
import { notification } from '$lib/stores/notificationStore';

export const load: LayoutLoad = async ({ parent }) => {
	const data = await parent();
	const membership = data.routeMembership;
	if (!membership) {
		notification('error', 'You are not a member of this group.'); // TODO i18n
		throw redirect(303, '/dashboard');
	}
	return { membership, ...data };
};
