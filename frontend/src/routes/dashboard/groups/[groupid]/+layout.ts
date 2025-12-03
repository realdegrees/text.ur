import { redirect } from '@sveltejs/kit';
import type { LayoutLoad } from './$types';
import { notification } from '$lib/stores/notificationStore';
import type { BreadcrumbItem } from '$types/breadcrumb';

export const load: LayoutLoad = async ({ parent }) => {
	const data = await parent();
	const membership = data.routeMembership;
	if (!membership) {
		notification('error', 'You are not a member of this group.'); // TODO i18n
		throw redirect(303, '/dashboard');
	}
	return {
		membership,
		...data,
		breadcrumbs: [
			{ label: 'Dashboard', href: '/dashboard' },
			{ label: membership.group.name }
		] satisfies BreadcrumbItem[]
	};
};
